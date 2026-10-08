"""Typed, non-numeric supplementary publication evidence.

This projection is deliberately separate from Decimal chapter keys. It never
changes main chapters, structural precedence, release gates or acceptance.
The pure evidence model is read-only. Schema-8/Grammar-4 persistence is supplied
by ddk_supplementary_store; numeric Grammar-3 commands cannot target these IDs.
"""
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
import re
from urllib.parse import parse_qs, urlsplit


CONTRACT = 'opaque-supplementary-v1'
SHA = re.compile(r'[0-9a-f]{64}')


@dataclass(frozen=True)
class Scope:
    work: str
    edition: str
    language: str


@dataclass(frozen=True)
class Provenance:
    source_url: str
    captured_at: str
    payload_sha256: str
    evidence_type: str
    confidence: str
    locator: str = ''
    publication_role: str = 'supplementary_book'
    volume: str = ''
    related_work_id: str = ''


@dataclass(frozen=True)
class SupplementaryIdentity:
    opaque_id: str
    scope: Scope
    publisher: str
    publication_id: str
    publication_title: str
    story_title: str
    original_label: str
    kind: str
    provenance: Provenance
    publisher_content_id: str = ''


@dataclass(frozen=True)
class AcquisitionBinding:
    supplement_id: str
    provider: str
    record_id: str
    original_label: str
    url: str
    method: str
    acquisition: dict
    proof: dict


@dataclass(frozen=True)
class CollectionMembership:
    supplement_id: str
    scope: Scope
    relation: str
    publication_id: str
    volume: str
    provenance: Provenance
    related_work_id: str = ''


def official_url(url, publication_id):
    """Exact publisher record, not an arbitrary official-domain page."""
    parsed = urlsplit(str(url))
    if (parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port or
            parsed.fragment or parsed.hostname not in ('www.shueisha.co.jp', 'www.s-manga.net') or
            parsed.path not in ('/books/items/contents.html', '/items/contents.html')):
        return False
    kind, _, value = str(publication_id).partition(':')
    params = parse_qs(parsed.query)
    if kind == 'isbn' and re.fullmatch(r'978-\d-\d{2}-\d{6}-\d', value):
        return params == {'isbn': [value]}
    if kind == 'jdcn' and re.fullmatch(r'[0-9A-Z]{15,24}', value):
        return params == {'jdcn': [value]}
    return False


def checked_provenance(value, publication_id):
    if not isinstance(value, dict): raise ValueError('Missing publication provenance')
    proof = Provenance(**{k: v for k, v in value.items() if k in Provenance.__dataclass_fields__})
    stamp = datetime.fromisoformat(proof.captured_at)
    if (stamp.tzinfo is None or not SHA.fullmatch(proof.payload_sha256) or
            proof.confidence != 'explicit' or
            proof.evidence_type not in ('official_toc', 'official_volume_toc') or
            not official_url(proof.source_url, publication_id)):
        raise ValueError('Incompatible authoritative publication provenance')
    if proof.publication_role not in ('supplementary_book', 'standard_volume', 'standalone', 'related_work'):
        raise ValueError('Unknown collection role')
    if proof.publication_role == 'standard_volume' and (
            proof.evidence_type != 'official_volume_toc' or not re.fullmatch(r'[1-9]\d*', str(proof.volume))):
        raise ValueError('Standard membership requires explicit numbered-volume evidence')
    return proof


def identity_from_observation(value, scope):
    """A book's exact story title is a discriminator, never an acquisition match.

    Page numbers are evidence locators only. Without a publisher content ID,
    identical headings within one book are ambiguous and quarantined later.
    """
    if not isinstance(value, dict) or value.get('scope') != asdict(scope):
        raise ValueError('Supplementary work / edition / language scope mismatch')
    if not all(isinstance(v, str) and v.strip() for v in asdict(scope).values()):
        raise ValueError('Incomplete supplementary scope')
    if (value.get('publisher') != 'shueisha' or
            value.get('kind') not in ('special', 'pilot_or_oneshot', 'bonus', 'oneshot') or
            not str(value.get('story_title') or '').strip() or not value.get('publication_title')):
        raise ValueError('Incomplete supplementary publication identity')
    provenance = checked_provenance(value, value.get('publication_id'))
    if provenance.publication_role == 'related_work' and (
            not provenance.related_work_id or provenance.related_work_id == scope.work):
        raise ValueError('Related publication needs a distinct canonical work identity')
    title = ' '.join(value['story_title'].split())
    content_id = str(value.get('publisher_content_id') or '')
    seed = [asdict(scope), value['publisher'], value['publication_id'], content_id or title]
    key = hashlib.sha256(json.dumps(seed, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
    return SupplementaryIdentity('supplement:'+key, scope, value['publisher'], value['publication_id'],
        value['publication_title'], title, value.get('original_label') or title, value['kind'], provenance, content_id)


def empty_projection():
    return dict(contract=CONTRACT, identities=[], diagnostics=[], summary=dict(
        recognized=0, verified_acquired=0, standard_volume_memberships=0,
        separate_publication_memberships=0, unresolved_acquisition=0, unresolved_membership=0),
        numeric_projection_effect='none', reviewed_binding_persistence='unsupported_grammar_3')


def binding_from_assertion(value, identity, rows, scope, review_context):
    """Validate a reviewed exact assertion without writing or inventing a guard.

    The caller must independently supply the current review context. Stored
    self-declared guards/VERIFIED flags alone cannot authorize a binding.
    The persistence adapter must supply this context independently of the stored
    assertion; self-declared flags or guards are never sufficient authority.
    """
    if (identity.scope != scope or value.get('scope') != asdict(scope) or
            value.get('supplement_id') != identity.opaque_id or
            value.get('method') != 'reviewed_exact' or value.get('verification') != 'VERIFIED' or
            not review_context or value.get('review_guard') != review_context or
            not all(review_context.get(k) is not None for k in
                    ('database_uuid', 'audit_id', 'audit_revision', 'database_revision')) or
            not str(value.get('reviewer') or '').strip() or not str(value.get('note') or '').strip() or
            value.get('source_url') != identity.provenance.source_url or
            value.get('publication_sha256') != identity.provenance.payload_sha256 or
            value.get('captured_at') != identity.provenance.captured_at or
            not SHA.fullmatch(str(value.get('acquisition_sha256') or ''))):
        raise ValueError('Unverified, stale, incompatible or incomplete exact binding')
    matches = [row for row in rows if (
        str(row.get('_source_id') or row.get('source_id') or '') == value.get('provider') and
        str(row.get('id') or '') == value.get('record_id') and
        str(row.get('chapter') if row.get('chapter') is not None else '') == value.get('original_label') and
        row.get('url') == value.get('url'))]
    parsed = urlsplit(str(value.get('url') or ''))
    if (len(matches) != 1 or not value.get('provider') or not value.get('record_id') or
            parsed.scheme not in ('http', 'https') or not parsed.hostname):
        raise ValueError('Acquisition record is absent or ambiguous')
    row = matches[0]
    if (row.get('language') != scope.language or row.get('edition') != scope.edition or
            row.get('_canonical_main') or row.get('_canonical_numeric_special')):
        raise ValueError('Contrary numeric identity or incompatible acquisition scope')
    return AcquisitionBinding(identity.opaque_id, value['provider'], value['record_id'],
        value['original_label'], value['url'], value['method'], dict(row), dict(value))


def membership_from_assertion(value, identity):
    if (value.get('scope') != asdict(identity.scope) or value.get('supplement_id') != identity.opaque_id or
            value.get('publication_id') != identity.publication_id):
        raise ValueError('Collection identity / scope mismatch')
    proof = checked_provenance(value.get('provenance'), identity.publication_id)
    if proof != identity.provenance:
        raise ValueError('Membership must identify the captured official story record')
    relation = value.get('relation')
    volume = str(value.get('volume') or '')
    if relation == 'standard_volume':
        if proof.publication_role != 'standard_volume' or proof.volume != volume:
            raise ValueError('Missing independent numbered-volume authority')
    elif relation in ('separate_publication', 'standalone', 'related_work'):
        allowed = {'separate_publication':'supplementary_book', 'standalone':'standalone', 'related_work':'related_work'}
        if volume or proof.publication_role != allowed[relation]:
            raise ValueError('Separate publication must not acquire a standard volume')
    else: raise ValueError('Unknown membership relationship')
    return CollectionMembership(identity.opaque_id, identity.scope, relation, identity.publication_id, volume, proof, proof.related_work_id)


def project_supplements(identities, acquisitions, bindings, memberships, scope, review_context=None):
    result = empty_projection()
    by_id = defaultdict(list)
    for ident in identities:
        try:
            raw = asdict(ident)
            checked = identity_from_observation({**raw, **raw['provenance']}, ident.scope)
            if checked != ident or ident.scope.work != scope.work or ident.scope.edition != scope.edition:
                raise ValueError('Invalid identity or incompatible canonical work / edition')
            by_id[ident.opaque_id].append(ident)
        except (ValueError, TypeError, KeyError) as exc:
            result['diagnostics'].append(dict(authority='identity', reason=str(exc)))
    owners = defaultdict(set)
    for key, observations in sorted(by_id.items()):
        # Repeated observations are fine; different locators with the same
        # heading could be different stories, and must not be merged silently.
        def semantic(item):
            value = asdict(item)
            value['provenance'].pop('captured_at'); value['provenance'].pop('payload_sha256')
            return json.dumps(value, sort_keys=True)
        conflict = len({semantic(i) for i in observations}) > 1
        ident = observations[0]
        row = dict(identity=asdict(ident), observations=[asdict(i) for i in observations],
                   acquisition_state='conflict' if conflict else 'unresolved',
                   membership_state='conflict' if conflict else 'unresolved', bindings=[], memberships=[],
                   applicability='compatible' if ident.scope == scope else 'language_or_edition_unverified')
        for values, destination in ((bindings, 'bindings'), (memberships, 'memberships')):
            for value in values:
                if not isinstance(value, dict) or value.get('supplement_id') != key: continue
                try:
                    if conflict: raise ValueError('Ambiguous supplementary story observations')
                    item = (binding_from_assertion(value, ident, acquisitions, scope, review_context)
                            if destination == 'bindings' else membership_from_assertion(value, ident))
                    item = asdict(item)
                    if item not in row[destination]: row[destination].append(item)
                except (ValueError, TypeError, KeyError) as exc:
                    result['diagnostics'].append(dict(supplement_id=key, authority=destination,
                        reason=str(exc), rejected_assertion=value))
        for item in row['bindings']:
            owners[(item['provider'], item['record_id'])].add(key)
        if not conflict:
            if row['bindings']: row['acquisition_state'] = 'verified'
            relations = {(v['relation'], v['publication_id'], v['volume']) for v in row['memberships']}
            if len(relations) > 1: row['membership_state'] = 'conflict'
            elif relations: row['membership_state'] = next(iter(relations))[0]
        result['identities'].append(row)
    for row in result['identities']:
        if any(len(owners[(v['provider'], v['record_id'])]) > 1 for v in row['bindings']):
            row['acquisition_state'] = 'conflict'
            result['diagnostics'].append(dict(supplement_id=row['identity']['opaque_id'],
                authority='bindings', reason='One acquisition claims different supplementary identities'))
    summary = result['summary']
    summary.update(recognized=len(result['identities']),
        verified_acquired=sum(r['acquisition_state'] == 'verified' for r in result['identities']),
        standard_volume_memberships=sum(r['membership_state'] == 'standard_volume' and r['applicability'] == 'compatible' for r in result['identities']),
        separate_publication_memberships=sum(r['membership_state'] in ('separate_publication', 'standalone', 'related_work') for r in result['identities']),
        unresolved_acquisition=sum(r['acquisition_state'] != 'verified' for r in result['identities']),
        unresolved_membership=sum(r['membership_state'] in ('unresolved', 'conflict') for r in result['identities']))
    return result


def collect_supplements(publisher, acquisitions, identity):
    """Consume scoped official TOC observations; never trust a captured binding.

    Legacy payloads without the new scope/capture fields remain readable raw
    observations, but cannot acquire authority by migration or guessed scope.
    """
    result = empty_projection()
    if not isinstance(identity, dict) or not identity.get('trusted') or not isinstance(publisher, dict): return result
    scope = Scope(identity.get('canonical_work_id'), identity.get('edition'), identity.get('language'))
    identities, memberships, errors = [], [], []
    books = publisher.get('supplementary_publications') or ()
    if not isinstance(books, (list, tuple)):
        result['diagnostics'].append(dict(authority='publisher_observation', reason='Invalid publisher book collection'))
        return result
    for book in books:
        try:
            if not isinstance(book, dict): raise ValueError('Invalid publisher book observation')
            if book.get('canonical_work_id') != scope.work or book.get('edition') != scope.edition:
                raise ValueError('Legacy or incompatible publisher book scope; re-audit required')
            language = book.get('language')
            publication_id = book.get('publication_id')
            records = book.get('records') or ()
            if not isinstance(records, (list, tuple)): raise ValueError('Invalid supplementary story collection')
            for record in records:
                if not isinstance(record, dict): raise ValueError('Invalid supplementary story record')
                observation = dict(scope=asdict(Scope(scope.work, scope.edition, language)), publisher='shueisha',
                    publication_id=publication_id, publication_title=book.get('title'),
                    story_title=record.get('title'), original_label=record.get('title'),
                    kind=record.get('publication_role'), source_url=book.get('source_page'),
                    captured_at=book.get('captured_at'), payload_sha256=book.get('payload_sha256'),
                    evidence_type=book.get('evidence_type'), confidence='explicit',
                    publication_role=book.get('publication_role'), volume=book.get('volume') or '',
                    related_work_id=book.get('related_work_id') or '',
                    locator='TOC page '+str(record.get('book_page') or ''),
                    publisher_content_id=record.get('publisher_content_id') or '')
                ident = identity_from_observation(observation, Scope(**observation['scope']))
                identities.append(ident)
                relation = {'supplementary_book':'separate_publication', 'standard_volume':'standard_volume',
                            'standalone':'standalone', 'related_work':'related_work'}[ident.provenance.publication_role]
                memberships.append(dict(supplement_id=ident.opaque_id, scope=asdict(ident.scope), relation=relation,
                    publication_id=ident.publication_id, volume=ident.provenance.volume,
                    provenance=asdict(ident.provenance)))
        except (TypeError, ValueError, KeyError) as exc:
            errors.append(dict(authority='publisher_observation', reason=str(exc), observation=book))
    result = project_supplements(identities, acquisitions, [], memberships, scope)
    result['diagnostics'].extend(errors)
    return result


def publication_supplements(publication):
    """Read a stored audit or conservatively adapt its older publisher evidence."""
    value = publication.get('supplementary_identity')
    if isinstance(value, dict) and value.get('contract') == CONTRACT:
        identity = publication.get('catalog_identity') or {}
        if not identity.get('trusted'): return empty_projection()
        scope = Scope(identity.get('canonical_work_id'), identity.get('edition'), identity.get('language'))
        identities, memberships, errors = [], [], list(value.get('diagnostics') or [])
        try:
            for row in value.get('identities') or ():
                for raw in row.get('observations') or [row['identity']]:
                    ident = identity_from_observation({**raw, **raw['provenance']}, Scope(**raw['scope']))
                    if ident.opaque_id != raw['opaque_id']: raise ValueError('Stored opaque identity hash mismatch')
                    identities.append(ident)
                memberships.extend(row.get('memberships') or [])
                if row.get('bindings'):
                    errors.append(dict(authority='bindings', reason='Stored binding requires independent current review context'))
            result = project_supplements(identities, [], [], memberships, scope)
            result['diagnostics'].extend(errors)
            return result
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            result = empty_projection()
            result['diagnostics'].append(dict(authority='stored_projection', reason=str(exc)))
            return result
    return collect_supplements((publication.get('references') or {}).get('publisher_publication') or {},
                              publication.get('projection') or [], publication.get('catalog_identity') or {})


def inspector_summary(publication):
    result = publication_supplements(publication)
    return {**result['summary'], 'Scope / policy':'Separate from numeric chapters; no automatic research bindings',
            'Binding commands':'Grammar 4 supplementary review; numeric selection is separate',
            'Evidence diagnostics':len(result['diagnostics'])}


def map_rows(result):
    """Display-only records; deliberately never enter Catalog.rows/commands."""
    rows = []
    for row in result.get('identities') or ():
        ident = row['identity']; key = ident['opaque_id']
        effective = dict(chapter='', title=ident['story_title'], volume=None, type='supplementary')
        rows.append(dict(key=key, iid=key, automatic=effective, effective=effective, curated={},
            source=ident['provenance']['source_url'], conflict='conflict' in (row['membership_state'], row['acquisition_state']),
            missing=False, ambiguous=False, supplementary=True, evidence=row,
            status='SUPPLEMENTARY · acquisition '+row['acquisition_state']+' · membership '+row['membership_state']+
                   ' · '+row['applicability']))
    return rows
