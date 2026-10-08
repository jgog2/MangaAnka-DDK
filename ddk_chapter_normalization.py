"""Conservative audit view of acquisition rows; never rewrites source evidence."""
from collections import Counter, defaultdict
import re

from mangaanka_search_core.cross_source_fallback import (
    chapter_identity, chapter_identities_match, normalize_chapter_number,
)

from mangaanka_search_core.publication_specials import match_special

SPECIAL_TYPES = {'bonus', 'extra', 'omake', 'special', 'prologue', 'epilogue'}
ARTIFACT_LABELS = {'provider_range_bundle','provider_split_candidate','provider_fractional_candidate'}
UNCLASSIFIED_LABELS = {'unclassified','provisional'}
_RANGE = re.compile(r'^\s*(\d+)\s*[-\u2013\u2014]\s*(\d+)\s*$')
_FRACTION = re.compile(r'^(\d+)\.(\d+)$')


def _provider(row, selected_source):
    return str(row.get('_source_id') or row.get('source_id') or selected_source or '')


def _artifact_groups(rows, labels, selected_source):
    by_group=defaultdict(list)
    artifact_rows=[None]*len(rows)
    policies={
        'provider_range_bundle':('integer_range_bundle','An integer range is a provider bundle identifier, not a single canonical chapter.','syntax'),
        'provider_split_candidate':('paired_fractional_suffix','Adjacent .1/.2 records repeat under a provider base; their publication identity is unverified.','candidate'),
        'provider_fractional_candidate':('repeated_fractional_numbering','Repeated fractional provider identifiers lack independent canonical chapter evidence.','candidate'),
    }
    for index,(row,label) in enumerate(zip(rows,labels)):
        if label not in ARTIFACT_LABELS: continue
        provider=_provider(row,selected_source)
        pattern,reason,confidence=policies[label]
        chapter=str(row.get('chapter') or '')
        match=_FRACTION.fullmatch(chapter)
        base=match[1] if match else None
        member={'identifier':chapter,'record_id':row.get('id'),'title':row.get('title') or '',
                'provider':provider,'base_chapter':base}
        artifact_rows[index]=dict(member,classification=label,pattern_family=pattern,
                                  confidence=confidence,reason=reason)
        by_group[(provider,label,pattern,reason,confidence)].append(member)
    result=[]
    for (provider,label,pattern,reason,confidence),members in sorted(by_group.items()):
        identifiers=[r['identifier'] for r in members]
        result.append({'provider':provider,'classification':label,'pattern_family':pattern,
                       'count':len(members),'identifiers':identifiers,
                       'representative_identifiers':identifiers[:6],
                       'base_chapters':sorted({r['base_chapter'] for r in members if r['base_chapter']},key=int),
                       'member_records':members,'confidence':confidence,'reason':reason})
    return artifact_rows,result


def normalize_acquisition(rows, inventories, manifest, selected_source='', reference_specials=None,
                          reference_chapters=(), publisher_membership=None):
    """Classify rows using exact plugin identities and independent evidence.

    Exact current manifest publication identities precede residual syntax.
    A reported total alone never identifies which chapter is canonical. A
    compatible reference or two other provider inventories can.
    Unknown records remain visible and block an unqualified PASS.
    """
    publication_records = (getattr(manifest, 'runtime_publication', {}) or {}).get('publication_records') or ()
    supported = defaultdict(list)
    for record in publication_records:
        supported[record['key']].append(record)
    publisher_membership = publisher_membership or {}
    for record in publisher_membership.get('main_records') or ():
        supported[record['key']].append(record)
    groups = defaultdict(list)
    for index, row in enumerate(rows):
        proof = match_special(row, (reference_specials or {}).values(), selected_source)
        key = proof['key'] if proof else normalize_chapter_number(row.get('chapter'))
        if key is not None and row.get('_unit_kind') != 'volume':
            groups[key].append(index)
    explicit = {c.key for c in manifest.chapters if c.volume.present and
                c.volume.source in ('mangadex_structure', 'wikipedia') and not _FRACTION.fullmatch(c.key)}
    explicit.update(k for k, proofs in supported.items() if any(r.get('volume') not in (None, '') for r in proofs))
    peers = defaultdict(list)
    complete_peers = set()
    for inv in inventories or ():
        if not inv.usable or not inv.complete:
            continue
        if inv.source_id != selected_source: complete_peers.add(inv.source_id)
        for row in inv.chapter_records or ():
            key = normalize_chapter_number(row.get('chapter'))
            if key is not None:
                peers[key].append((inv.source_id, chapter_identity(row)))
    labels = ['unclassified'] * len(rows)
    evidence = {}
    identity_rows = [None] * len(rows)
    for index, row in enumerate(rows):
        if row.get('_unit_kind') == 'volume': labels[index] = 'volume_only'
        elif (normalize_chapter_number(row.get('chapter')) is None and
              str(row.get('type') or row.get('chapter_type') or '').casefold() in SPECIAL_TYPES and
              row.get('id')):
            labels[index] = 'special'
            evidence['@'+str(row['id'])] = 'explicit provider special type and stable acquisition ID'
    for key, indexes in groups.items():
        first = chapter_identity(rows[indexes[0]])
        equivalent = all(chapter_identities_match(first, chapter_identity(rows[i])) for i in indexes[1:])
        peer_sources = {source for source, identity in peers.get(key, ())
                        if chapter_identities_match(first, identity)}
        # Selected provider is not independent corroboration.
        selected_sources = {selected_source} | {str(rows[i].get('_source_id') or rows[i].get('source_id') or '') for i in indexes}
        independent = peer_sources - selected_sources
        row = rows[indexes[0]]
        provider_explicit = row.get('volume') not in (None, '')
        trusted = key in supported or key in explicit or (key in reference_chapters and not _FRACTION.fullmatch(key)) or len(independent) >= 2 or (
            provider_explicit and not _FRACTION.fullmatch(key) and len(complete_peers)<2)
        is_special = str(row.get('type') or row.get('chapter_type') or '').casefold() in SPECIAL_TYPES
        if not equivalent:
            evidence[key] = 'conflicting acquisition identities'
            continue
        supported_special = next((r for r in supported.get(key, ()) if r.get('kind') in SPECIAL_TYPES),
                                 (reference_specials or {}).get(key))
        if supported_special:
            labels[indexes[0]] = 'recognized_special'
            evidence[key] = 'exact compatible independent reference special: '+supported_special['source_page']
        elif is_special and not _FRACTION.fullmatch(key):
            labels[indexes[0]] = 'special'
            evidence[key] = 'explicit provider special type'
        elif trusted:
            labels[indexes[0]] = 'main'
            evidence[key] = ('exact compatible trusted publication identity' if key in supported else
                             'explicit chapter structure' if key in explicit else
                             'provider explicit membership' if provider_explicit else
                             'two independent provider inventories')
        else:
            labels[indexes[0]] = 'unclassified' if len(complete_peers)>=2 else 'provisional'
            evidence[key] = ('conflicts with independent provider chapter sets' if len(complete_peers)>=2
                             else 'no independent chapter-level confirmation')
        for index in indexes[1:]:
            labels[index] = 'duplicate' if labels[indexes[0]]!='unclassified' else 'unclassified'
        proofs = supported.get(key) or ([supported_special] if supported_special else [])
        if proofs:
            for index in indexes:
                acquisition = rows[index]
                identity_rows[index] = dict(original_identifier=acquisition.get('chapter'),
                    record_id=acquisition.get('id'),url=acquisition.get('url'),
                    provider=_provider(acquisition,selected_source),canonical_identifier=key,
                    classification=labels[indexes[0]],duplicate=labels[index]=='duplicate',
                    evidence=proofs,reason='exact compatible trusted publication identity suppresses provider-pattern classification')
    # Only a current publisher-backed completed model supplies negative
    # membership evidence. Open, partial, stale or contradictory models keep
    # the existing provisional fallback. Positive identity above takes priority.
    if publisher_membership.get('status') == 'closed':
        closed = set(publisher_membership['closed_main_keys'])
        for index, label in enumerate(labels):
            key = normalize_chapter_number(rows[index].get('chapter'))
            if label == 'provisional' and key not in closed:
                labels[index] = 'unclassified'
                evidence[key] = 'provider-only identifier outside current publisher-backed completed main membership'
    # Syntactic provider artifacts are classified only after independent
    # structural evidence has had the chance to establish real chapters.
    for index,row in enumerate(rows):
        if labels[index] not in ('unclassified','provisional') or normalize_chapter_number(row.get('chapter')) in supported: continue
        match=_RANGE.fullmatch(str(row.get('chapter') or ''))
        if match and int(match[1])<int(match[2]):
            labels[index]='provider_range_bundle'
    pairs=defaultdict(lambda:defaultdict(list))
    for index,row in enumerate(rows):
        if labels[index] not in ('unclassified','provisional') or normalize_chapter_number(row.get('chapter')) in supported: continue
        match=_FRACTION.fullmatch(str(row.get('chapter') or ''))
        if match and match[2] in ('1','2'):
            pairs[(_provider(row,selected_source),match[1])][match[2]].append(index)
    for members in pairs.values():
        if len(members['1'])==1 and len(members['2'])==1:
            for index in members['1']+members['2']:
                labels[index]='provider_split_candidate'
    fractions=defaultdict(list)
    for index,row in enumerate(rows):
        if labels[index] not in ('unclassified','provisional') or normalize_chapter_number(row.get('chapter')) in supported: continue
        if _FRACTION.fullmatch(str(row.get('chapter') or '')):
            fractions[_provider(row,selected_source)].append(index)
    for indexes in fractions.values():
        for index in indexes: labels[index]='provider_fractional_candidate'
    artifact_rows,artifact_groups=_artifact_groups(rows,labels,selected_source)
    return {'labels': labels, 'evidence': evidence, 'counts': dict(Counter(labels)),
            'explicit_reference_keys': sorted(explicit),
            'publication_identity_rows': identity_rows,
            'artifact_rows':artifact_rows,'artifact_groups':artifact_groups,
            'status': 'established' if any(x in ('main', 'special', 'recognized_special') for x in labels) else 'unverified'}


def effective_counts(projection_rows, normalization):
    labels = normalization['labels']
    if len(labels) != len(projection_rows):
        raise ValueError('Normalization and projection row counts differ.')
    included = [(r, label) for r, label in zip(projection_rows, labels) if label in ('main', 'special', 'recognized_special', 'provisional')]
    mapped = [(r, label) for r, label in included if r.get('_effective_volume') not in (None, '')]
    unassigned_specials = [r for r, label in included if label in ('special', 'recognized_special') and r.get('_effective_volume') in (None, '')]
    uncompiled = [r for r, label in included if label not in ('special', 'recognized_special') and r.get('_effective_volume') in (None, '') and r.get('_publication_state') == 'UNCOMPILED']
    unmapped = [r for r, label in included if label not in ('special', 'recognized_special') and r.get('_effective_volume') in (None, '') and r.get('_publication_state') != 'UNCOMPILED']
    volumes = {str(r['_effective_volume']) for r, _ in mapped}
    return {'logical_chapters': len(included), 'canonical_main_chapters': sum(label == 'main' for _, label in included),
            'recognized_specials': sum(label in ('special', 'recognized_special') for _, label in included),
            'canonical_chapters': sum(label == 'main' for _, label in included),
            'mapped_main_chapters': sum(label == 'main' for _, label in mapped),
            'unassigned_specials': len(unassigned_specials),
            'unassigned_special_identifiers': [str(r.get('chapter') or r.get('id')) for r in unassigned_specials],
            'uncompiled_chapters': len(uncompiled),
            'uncompiled_identifiers': [str(r['chapter']) for r in uncompiled],
            'mapped_chapters': len(mapped), 'unmapped_chapters': len(unmapped),
            'unmapped': unmapped, 'final_volumes': len(volumes),
            **classification_counts(normalization),
            'duplicate_records': normalization['counts'].get('duplicate', 0)}


def classification_counts(normalization, fallback_unclassified=0):
    """Read current or stored normalization labels without changing raw evidence."""
    counts=(normalization or {}).get('counts') or dict(Counter((normalization or {}).get('labels') or ()))
    if not counts:
        return {'classified_provider_artifacts':0,'provider_artifact_breakdown':{},
                'unclassified_records':fallback_unclassified or 0}
    breakdown={label:int(count) for label,count in sorted(counts.items())
               if (label in ARTIFACT_LABELS or label.startswith('provider_')) and int(count)>0}
    return {'classified_provider_artifacts':sum(breakdown.values()),
            'provider_artifact_breakdown':breakdown,
            'unclassified_records':sum(int(counts.get(label,0)) for label in UNCLASSIFIED_LABELS)}


def publication_classification_counts(publication):
    return classification_counts((publication or {}).get('normalization'),
                                 (publication or {}).get('unclassified_records',0))


def unclassified_rows(projection_rows, normalization):
    artifacts=normalization.get('artifact_rows') or ()
    result=[]
    for index,(row,label) in enumerate(zip(projection_rows,normalization['labels'])):
        if label not in UNCLASSIFIED_LABELS: continue
        artifact=artifacts[index] if index<len(artifacts) else None
        result.append({'chapter':row.get('chapter'),'id':row.get('id'),'title':row.get('title'),
                       'provider':row.get('_acquisition_provider') or row.get('_source_id') or row.get('source_id'),
                       'classification':label,'pattern_family':(artifact or {}).get('pattern_family'),
                       'reason':(artifact or {}).get('reason') or
                         normalization['evidence'].get(normalize_chapter_number(row.get('chapter')), 'unclassified')})
    return result
