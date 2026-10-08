"""Standalone orchestration of the plugin's post-selection publication path."""
from concurrent.futures import CancelledError
from dataclasses import asdict
from decimal import Decimal
import hashlib
import sys

from mangaanka_search_core import PLUGIN_ROOT
from mangaanka_search_core.canonical_identity import edition_identity, edition_classification
from mangaanka_search_core.enrichment_model import EditionClass
from mangaanka_search_core.cross_source_fallback import normalize_chapter_number
from mangaanka_search_core.reference_integration import (
    ReferenceMetadataService, canonical_family_publication_context,
    canonical_reference_alias,
)
from mangaanka_search_core.enrichment_matching import trusted_alias_for_query
from mangaanka_search_core.publication_manifest import (
    PublicationManifestBuilder, build_publication_projection,
)
from mangaanka_search_core.unified_volume import build_unified_volume_plan
from mangaanka_search_core.chapter_workflow import chapter_sort_key
from mangaanka_search_core.atsu_acquisition import resolve_atsu_acquisition
from mangaanka_search_core.publication_specials import inventory_coverage
from ddk_catalog import identity_for
from ddk_curated_resolution import apply_curated
from ddk_duplicate_projection import reconcile_duplicates
from ddk_chapter_normalization import normalize_acquisition, effective_counts, unclassified_rows
from ddk_publisher_reference import PublisherReferenceAdapter, membership_evidence, publisher_fingerprint
from ddk_publication_states import (trusted_wikipedia_records,
                                   derive_publication_states, state_summary)
from ddk_supplementary import collect_supplements


def core_provenance():
    files = {}
    for name, module in tuple(sys.modules.items()):
        path = getattr(module, '__file__', None)
        if name.startswith('mangaanka_search_core.') and path:
            from pathlib import Path
            source = Path(path)
            files[source.name] = hashlib.sha256(source.read_bytes()).hexdigest()
    return {'worktree': str(PLUGIN_ROOT), 'sha256': files}


def selected_acquisition_edition(result):
    """Check the selected provider's own explicit fields, never its aliases."""
    selected=dict(result or {})
    native={key:selected.get(key) for key in ('title','full_title','badge','is_colored')}
    if selected.get('_provider_native_title'):
        native['title']=selected['_provider_native_title']
    native_class=edition_classification(native)
    explicit_class=edition_classification(selected)
    if native_class in (EditionClass.FAN_COLOR,EditionClass.OFFICIAL_COLOR):
        return native_class.value
    if explicit_class in (EditionClass.FAN_COLOR,EditionClass.OFFICIAL_COLOR):
        return explicit_class.value
    return 'standard'


def evaluate_structure_coverage(publication, reported_totals=()):
    """Describe structural sufficiency separately from reference parse status."""
    logical=int(publication.get('logical_chapters') or 0) - int(publication.get('uncompiled_chapters') or 0) - int(publication.get('unassigned_specials') or 0)
    mapped=int(publication.get('mapped_chapters') or 0)
    volumes=int(publication.get('final_volumes') or 0)
    reported_volumes={int(row['reported_total_volumes']) for row in reported_totals or ()
                      if isinstance(row.get('reported_total_volumes'),int) and row['reported_total_volumes']>0}
    expected_volume=next(iter(reported_volumes)) if len(reported_volumes)==1 else None
    def quality(count, volume_count=0):
        if not logical: return 'unknown'
        if count==0 or count/logical<0.25 or (expected_volume and volume_count and
                                               volume_count/expected_volume<0.25): return 'sparse'
        if count>=logical and not (expected_volume and volume_count and
                                   volume_count/expected_volume<0.5): return 'complete'
        return 'partial'
    refs=publication.get('references') or {}
    projection=publication.get('projection') or ()
    acquired={normalize_chapter_number(row.get('chapter')) for row in projection
              if normalize_chapter_number(row.get('chapter')) is not None}
    sources={}
    md=refs.get('mangadex_structure') or {}
    wiki=refs.get('wikipedia') or {}
    for name,reference,assignments in (
        ('mangadex_structure',md,(md.get('mappings') or {}).items()),
        ('wikipedia',wiki,((row.get('number') or row.get('chapter'),row.get('volume'))
                           for row in wiki.get('chapters') or ()))):
        pairs=[(key,volume) for raw,volume in assignments
               if (key:=normalize_chapter_number(raw)) in acquired and volume not in (None,'')]
        matched=len({key for key,_ in pairs})
        source_volumes=len({str(volume) for _,volume in pairs})
        sources[name]={'status':reference.get('status') or 'not_run','mapped_acquisition_keys':matched,
                       'resolved_volumes':source_volumes,
                       'coverage_ratio':round(matched/logical,3) if logical else None,
                       'coverage':quality(matched,source_volumes)}
    return {'coverage':quality(mapped,volumes),'coverage_ratio':round(mapped/logical,3) if logical else None,
            'mapped_chapters':mapped,'expected_chapters':logical,'resolved_volumes':volumes,
            'uncompiled_chapters':publication.get('uncompiled_chapters',0),
            'reported_volume_count':expected_volume,
            'volume_coverage_ratio':round(volumes/expected_volume,3) if expected_volume else None,
            'sources':sources,'fallback_considered':bool(wiki.get('status'))}


def resolve_publication(resolution, family_rows, external_candidates=(),
                        metadata_cache=None, should_cancel=None, service=None, catalog=None, catalog_work_id=None,
                        on_identity=None, as_of=None):
    """Use selected acquisition only, as main.py's unified-volume path does."""
    should_cancel = should_cancel or (lambda: False)
    if should_cancel():
        raise CancelledError()
    primary = resolution.primary
    selected = dict(primary.result)
    edition = edition_identity(selected)
    context = canonical_family_publication_context(selected, family_rows, edition)
    catalog_identity = identity_for(selected, asdict(context), resolution.language)
    if on_identity is not None:catalog_work_id=on_identity(catalog_identity)
    curated = catalog.lookup(catalog_identity, catalog_work_id) if catalog else {'status':'absent','fields':[]}
    metadata = next((dict(value) for (source, ref), value in (metadata_cache or {}).items()
                     if source == primary.source_id and
                     str(ref) in {str(selected.get('id')), str(selected.get('url'))}), {})
    title = metadata.get('title') or selected.get('title') or ''
    aliases = list(metadata.get('alternate_titles') or selected.get('alternate_titles') or ())
    aliases.extend(str(r.get('title') or '') for r in metadata.get('titles') or () if isinstance(r, dict))
    aliases.extend((canonical_reference_alias(title, external_candidates),
                    trusted_alias_for_query(title, external_candidates)))
    if context.shareable:
        evidence = context.lookup_evidence()
        evidence['requested_language'] = resolution.language
    else:
        evidence = {'title': title, 'aliases': tuple(dict.fromkeys(a for a in aliases if a)),
                    'author': metadata.get('author') or selected.get('author') or '', 'edition': edition}
    work_id = context.canonical_work_id or selected.get('canonical_work_id') or (
        primary.source_id + ':' + str(selected.get('id') or selected.get('url')))
    rows = tuple(dict(r) for r in primary.chapter_records)
    fallback = resolution.fallback_plan
    if (fallback and fallback.can_execute and fallback.language == resolution.language
            and fallback.primary_source_id == primary.source_id):
        rows = tuple(sorted((dict(item.reference, _source_id=item.source_id,
                                  _source_name=item.source_name, _fallback_reason=item.reason)
                             for item in fallback.items), key=chapter_sort_key))
    default_service = service is None
    service = service or ReferenceMetadataService(
        None, madb_enabled=True, mangadex_structure_enabled=True, mangadex_artwork_enabled=True)
    bundle = service.lookup(context.reference_key or work_id, evidence,
                            should_cancel=should_cancel,
                            acquisition={'source_id': primary.source_id,
                                         'chapters': rows, 'covers': {}})
    if default_service:
        bundle['publisher_publication'] = PublisherReferenceAdapter().lookup(evidence, should_cancel)
    if should_cancel():
        raise CancelledError()
    builder = PublicationManifestBuilder(
        {'canonical_identity': work_id, 'title': title, 'aliases': aliases,
         'creator': metadata.get('author') or selected.get('author') or '',
         'creator_source': 'provider', 'language': resolution.language,
         'publication_context':asdict(context)}, edition, as_of=as_of)
    by_source = {}
    for row in rows:
        by_source.setdefault(row.get('_source_id') or row.get('source_id') or primary.source_id, []).append(row)
    for source_id, source_rows in by_source.items():
        builder.apply_provider_inventory(source_rows, source_id)
    builder.apply_madb(bundle.get('madb')).apply_mangadex_structure(bundle.get('mangadex_structure'))
    builder.apply_wikipedia(bundle.get('wikipedia'))
    builder.apply_mangadex_artwork(bundle.get('mangadex_artwork'))
    builder.apply_bookwalker(bundle.get('bookwalker')).apply_google_books(bundle.get('google_books'))
    builder.apply_enrichment(selected)
    manifest = builder.build(resolution.language)
    group_acquisition=resolve_atsu_acquisition(rows,manifest,resolution.inventories)
    rows=tuple(group_acquisition['rows'])
    projection = build_publication_projection(rows, manifest, primary.source_id, primary.source_id)
    projection, duplicate_structure_conflicts = reconcile_duplicates(rows, manifest, projection)
    plan = build_unified_volume_plan({}, rows, projection, primary.source_id, primary.source_name)
    # Volume-only acquisition records are volumes, not invented chapter counts.
    chapters = [r for r in projection.chapters if r.acquisition.get('_unit_kind') != 'volume']
    unmapped = [r.as_row() for r in chapters if not r.effective_volume.present]
    conflicts = set(manifest.ambiguous_chapter_keys)
    conflicts.update(duplicate_structure_conflicts)
    # Lower-priority reference ambiguity is diagnostic when higher-priority
    # evidence already resolves the selected acquisition.
    if not any(s.source == 'mangadex_structure' and s.status == 'incompatible'
               for s in manifest.source_states):
        conflicts.update((bundle.get('mangadex_structure') or {}).get('ambiguous_chapters') or ())
    unresolved_conflicts = sorted(set(duplicate_structure_conflicts) | {r.canonical_key for r in chapters
                                   if not r.effective_volume.present and r.canonical_key in conflicts})
    acquired = {r.canonical_key for r in chapters if r.canonical_key}
    missing_reference_chapters = sorted({r.key for r in manifest.chapters
        if r.volume.present and r.volume.source in ('mangadex_structure', 'wikipedia')
        and r.key not in acquired}) if len(chapters) == len(rows) else []
    reference_records = trusted_wikipedia_records(bundle, catalog_identity, asdict(context))
    specials = {r['key']:r for r in manifest.runtime_publication.get('special_records',())}
    publisher_membership = membership_evidence(bundle.get('publisher_publication') or {}, catalog_identity,
        manifest.runtime_publication.get('publication_records') or (),
        as_of=manifest.runtime_publication.get('as_of'), context=asdict(context))
    # A conflicting/ambiguous structural model cannot acquire closure authority.
    if conflicts or unresolved_conflicts or manifest.runtime_publication.get('reference_conflicts'):
        publisher_membership['status'] = 'conflict'
        publisher_membership['closed_main_keys'] = []
    normalization = normalize_acquisition(rows, resolution.inventories, manifest, primary.source_id, specials,
        {r['key'] for r in reference_records if r.get('kind') in ('chapter', 'uncollected')}, publisher_membership)
    if publisher_membership.get('status') == 'closed':
        final = Decimal(publisher_membership['final_chapter']['key'])
        newer = sorted({normalize_chapter_number(r.get('chapter')) for r,label in
            zip(rows,normalization['labels']) if label == 'main' and
            Decimal(normalize_chapter_number(r.get('chapter'))) > final},key=Decimal)
        if newer:
            publisher_membership.update(status='conflict', conflicts=newer, closed_main_keys=[])
            normalization = normalize_acquisition(rows, resolution.inventories, manifest, primary.source_id, specials,
                {r['key'] for r in reference_records if r.get('kind') in ('chapter', 'uncollected')}, publisher_membership)
    normalized_counts = effective_counts([r.as_row() for r in projection.chapters], normalization)
    result = {
        'status': 'complete', 'edition': {'original': 'standard'}.get(edition, edition),
        'acquisition_edition':selected_acquisition_edition(selected),
        'selected_acquisition_title':selected.get('_provider_native_title') or selected.get('title') or '',
        'selected_acquisition_ref':selected.get('url') or selected.get('id') or '',
        'edition_classification': edition_classification(selected).value,
        'logical_chapters': len(chapters), 'final_volumes': len(plan['volumes']),
        'mapped_chapters': len(chapters) - len(unmapped), 'unmapped_chapters': len(unmapped),
        'native_volumes': plan['native_volume_count'], 'derived_volumes': plan['derived_volume_count'],
        'volume_only_units': len(rows) - len(chapters),
        'coverage': projection.coverage, 'unmapped': unmapped,
        'conflicting_chapters': unresolved_conflicts,
        'reference_conflicts': manifest.runtime_publication.get('reference_conflicts') or [],
        'missing_reference_chapters': missing_reference_chapters,
        'context': asdict(context), 'evidence': evidence, 'manifest': asdict(manifest),
        'references': bundle, 'projection': [r.as_row() for r in projection.chapters],
        'volumes': plan['volumes'], 'core': core_provenance(),
        'catalog_identity': catalog_identity,
        'normalization': normalization, 'raw_acquisition_records': group_acquisition['raw_count'],
        'publisher_membership': publisher_membership,
        'provider_group_acquisition':{k:v for k,v in group_acquisition.items() if k!='rows'},
        'as_of': manifest.runtime_publication.get('as_of'),
        'raw_final_volumes': len(plan['volumes']), 'raw_unmapped': unmapped,
    }
    result.update(normalized_counts)
    # Keep release/count evidence available before deriving states, including
    # direct standalone adapter callers that do not use SearchAuditor.
    result['reported_count_provenance'] = [dict(c) for r in family_rows for c in
        r.get('volume_context') or () if isinstance(c, dict)]
    for row, label in zip(result['projection'], normalization['labels']):
        if label == 'recognized_special':
            row['type'] = specials[normalize_chapter_number(row.get('chapter'))]['kind']
    derive_publication_states(result)
    result['recognized_special_records']=list(specials.values())
    result['missing_special_acquisition']=sorted(set(specials)-acquired,key=Decimal)
    result['provider_coverage']=[dict(source_id=inv.source_id,**inventory_coverage(inv,specials.values())) for inv in resolution.inventories]
    result.update(effective_counts(result['projection'], normalization))
    result.update(state_summary(result))
    result['unclassified_acquisition']=unclassified_rows(result['projection'],normalization)
    if not normalized_counts['logical_chapters'] and result['volume_only_units']:
        result['final_volumes'] = len(plan['volumes'])
    # Opaque publication identities never enter Decimal-based chapter structures.
    # No captured research observation or stored VERIFIED flag binds a reader.
    result['supplementary_identity'] = collect_supplements(
        bundle.get('publisher_publication') or {}, rows, catalog_identity)
    result=apply_curated(result, rows, manifest, projection, curated, primary) if catalog else result
    from mangaanka_search_core.publication_freshness import catalog_freshness, source_fingerprints
    result['source_fingerprints']=source_fingerprints(bundle)
    if bundle.get('publisher_publication'):
        result['source_fingerprints']['publisher_publication'] = publisher_fingerprint(bundle['publisher_publication'])
    automatic=result.get('automatic') or result
    automatic['source_fingerprints']=result['source_fingerprints']
    result['catalog_freshness']=catalog_freshness(curated, automatic)
    result.update(state_summary(result))
    result['structural_coverage']=evaluate_structure_coverage(result)
    if catalog and catalog_work_id is not None:
        result['supplementary_revision']=catalog.db.supplementary.revision(catalog_work_id)
        result['supplementary_identity']=catalog.db.supplementary.resolve(result,catalog_work_id)
    return result


def publication_holes(publication, primary, expected_edition='standard'):
    """Aggregate final-result failures; provider diagnostics are not holes."""
    holes = []
    def add(code, message, severity='warning', **details):
        holes.append({'code': code, 'severity': severity, 'message': message, 'details': details})
    expected = {'original': 'standard', 'colored': 'official_color',
                'color': 'official_color', 'fan_colored': 'fan_color'}.get(expected_edition, expected_edition)
    selected_edition=publication.get('acquisition_edition') or publication.get('edition')
    wrong_edition=bool(selected_edition and selected_edition != expected)
    if wrong_edition:
        add('WRONG_EDITION_MATCH', f"Requested {expected}; selected acquisition is {selected_edition}.", 'error',
            selected_title=publication.get('selected_acquisition_title') or '')
    if publication.get('status') != 'complete':
        add('SOURCE_FAILURE', publication.get('error') or 'Publication resolution did not finish.', 'error')
        return holes
    if wrong_edition:
        if not primary.complete:
            add('SOURCE_FAILURE', f'Selected acquisition is partial: {primary.error or primary.summary}')
        return holes
    curated = publication.get('curated_database') or {}
    if curated.get('status') in ('ambiguous','incompatible'):
        add('CURATED_IDENTITY_CONFLICT', curated.get('reason') or 'Curated identity could not be safely applied.')
    freshness=publication.get('catalog_freshness') or {}
    if freshness.get('blocking'):
        add('REFERENCE_CONFLICT','Trusted live evidence contradicts reviewed curated fields.',
            conflicts=freshness.get('conflicts') or [])
    if not primary.complete:
        add('SOURCE_FAILURE', f'Selected acquisition is partial: {primary.error or primary.summary}')
    missing = publication['unmapped_chapters']
    conflicts = publication['conflicting_chapters']
    if conflicts:
        add('REFERENCE_CONFLICT', 'Ambiguous chapter evidence prevents final mapping.',
            chapters=conflicts, reference_conflicts=publication.get('reference_conflicts') or [])
    publisher_conflicts = (publication.get('publisher_membership') or {}).get('conflicts') or []
    if publisher_conflicts:
        add('REFERENCE_CONFLICT', 'Independent main chapter identities contradict current publisher completion evidence.',
            chapters=publisher_conflicts, publisher_membership=publication['publisher_membership'])
    boundary=publication.get('release_boundary') or {}
    if boundary.get('conflicts'):
        add('REFERENCE_CONFLICT','Trusted references disagree about current volume release state.',
            volumes=boundary['conflicts'])
    conflict_keys = set(conflicts)
    independent_unmapped = [r for r in publication.get('unmapped') or ()
                            if str(r.get('chapter') or '') not in conflict_keys]
    reported_volumes={r.get('reported_total_volumes') for r in publication.get('reported_count_provenance') or ()
                      if isinstance(r.get('reported_total_volumes'),int) and r['reported_total_volumes']>0}
    no_structure=bool(independent_unmapped and not publication.get('mapped_chapters') and
                      not publication.get('final_volumes') and reported_volumes)
    if no_structure:
        add('MISSING_REFERENCE_STRUCTURE',
            f'No usable chapter-to-volume structure reached the projection; {len(independent_unmapped)} chapters affected.',
            affected=len(independent_unmapped), reported_volumes=sorted(reported_volumes),
            reference_status={k:v.get('status') for k,v in publication.get('references',{}).items()
                              if k in ('mangadex_structure','wikipedia')})
    elif independent_unmapped:
        add('UNMAPPED_CHAPTERS', f'{len(independent_unmapped)} canonical chapters remain unmapped after publication resolution.',
            affected=len(independent_unmapped), chapters=[r.get('chapter') for r in independent_unmapped],
            structural_coverage=publication.get('structural_coverage') or {})
    if boundary.get('complete') and not publication.get('volume_only_units'):
        effective_volumes={normalize_chapter_number(str(r.get('_effective_volume'))) for r in
                           publication.get('projection') or () if r.get('_effective_volume') not in (None,'')}
        absent=set(boundary.get('released_volumes') or ())-effective_volumes
        if absent and not any(h['code'] in ('MISSING_REFERENCE_STRUCTURE','UNMAPPED_CHAPTERS') for h in holes):
            add('MISSING_REFERENCE_STRUCTURE','Released volumes are known but their chapter membership is unresolved.',
                volumes=sorted(absent),release_boundary=boundary)
    normalization=publication.get('normalization') or {}
    group_pending=[r for r in (publication.get('provider_group_acquisition') or {}).get('alternatives') or ()
                   if r.get('requires_review')]
    if group_pending:
        add('PROVIDER_GROUP_CANDIDATE',f'{len(group_pending)} alternate-group acquisitions need independent identity evidence.',
            affected=len(group_pending),chapters=[r.get('chapter') for r in group_pending],
            records=group_pending)
    artifact_codes={'provider_range_bundle':'PROVIDER_RANGE_BUNDLE',
                    'provider_split_candidate':'PROVIDER_SPLIT_CANDIDATE',
                    'provider_fractional_candidate':'PROVIDER_FRACTIONAL_CANDIDATE'}
    for group in normalization.get('artifact_groups') or ():
        code=artifact_codes.get(group.get('classification'))
        if code:
            add(code,f"{group['count']} {group['provider'] or 'provider'} acquisition records match {group['pattern_family']}.",
                affected=group['count'],chapters=group['identifiers'],provider=group['provider'],
                classification=group['classification'],pattern_family=group['pattern_family'],
                representative_identifiers=group['representative_identifiers'],
                confidence=group['confidence'],reason=group['reason'])
    unresolved=[r for r in publication.get('unclassified_acquisition') or ()
                if r.get('classification') in ('unclassified','provisional')]
    if unresolved:
        add('UNCLASSIFIED_ACQUISITION',f'{len(unresolved)} acquisition records lack independent canonical chapter evidence.',
            affected=len(unresolved),chapters=[r.get('chapter') or r.get('id') for r in unresolved])
    pending_provider_records=(publication.get('unclassified_records',0)+
                              publication.get('classified_provider_artifacts',0))
    created=publication.get('curated_publication_records') or []
    if created:
        add('ACQUISITION_COVERAGE_GAP',f'{len(created)} curated publication chapters have no acquisition record.',
            affected=len(created), chapters=[r['chapter'] for r in created])
    missing_specials = publication.get('missing_special_acquisition') or []
    if missing_specials:
        add('MISSING_SPECIAL_ACQUISITION',
            f'{len(missing_specials)} trusted specials are absent from selected acquisition.',
            affected=len(missing_specials), chapters=missing_specials)
    absent = [k for k in publication.get('missing_reference_chapters') or [] if k not in missing_specials]
    if absent:
        add('CHAPTER_COUNT_DISAGREEMENT',
            f'{len(absent)} explicitly referenced chapters are absent from selected acquisition.',
            chapters=absent)
    counts=(publication.get('effective_catalog') or {}).get('work') or {}
    for field,actual,code in (('expected_chapters','logical_chapters','CHAPTER_COUNT_DISAGREEMENT'),
                              ('expected_volumes','final_volumes','VOLUME_COUNT_DISAGREEMENT')):
        if field in counts and counts[field]!=publication.get(actual):
            # An explicit snapshot contract can prove that a larger current
            # count is an extension. Legacy sparse count corrections retain
            # their conservative disagreement diagnostic.
            if (freshness.get('state')=='EXTENSION_AVAILABLE' and
                    publication.get(actual,0)>counts[field] and not missing and
                    not pending_provider_records and not freshness.get('blocking')):
                continue
            message=f"Curated {field}: {counts[field]}; final {actual}: {publication.get(actual)}."
            existing=next((h for h in holes if h['code']==code),None)
            if existing: existing['message']+=' '+message
            else: add(code,message,expected=counts[field],actual=publication.get(actual))
    if missing or pending_provider_records:
        failed = {name: row.get('error') or row.get('status')
                  for name, row in publication.get('references', {}).items()
                  if name in ('mangadex_structure', 'wikipedia') and
                  row.get('status') in ('transient_failure', 'rate_limited')}
        if failed:
            add('SOURCE_FAILURE', 'Structural reference request failed; mapping remains incomplete.',
                sources=failed)
    return holes
