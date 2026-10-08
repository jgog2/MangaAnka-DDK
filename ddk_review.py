"""Evidence-only review model shared by Problems, exports, and clipboard."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path

from mangaanka_search_core.cross_source_fallback import normalize_chapter_number
from ddk_chapter_normalization import publication_classification_counts
from ddk_supplementary import publication_supplements

PACKET_FORMAT = 'mangaanka-ddk-review-v1'
GRAMMAR_VERSION = 4
CLASSES = ('DATA','CODE','ACQUISITION','RESEARCH','IDENTITY','UNKNOWN')
ACTIONS = ('AUTO_RESOLVABLE','CURATION_READY','RESEARCH_REQUIRED',
           'CODE_REVIEW_REQUIRED','ACQUISITION_ONLY','BLOCKED_IDENTITY','UNKNOWN')
IDENTITY_CODES = {'WRONG_EDITION_MATCH','NO_CANONICAL_RESULT','WEAK_SEARCH_MATCH','CURATED_IDENTITY_CONFLICT'}
PUBLICATION_CODES = {'UNMAPPED_CHAPTERS','REFERENCE_CONFLICT','MISSING_REFERENCE_STRUCTURE',
                     'VOLUME_COUNT_DISAGREEMENT'}
ARTIFACT_CODES = {'PROVIDER_RANGE_BUNDLE','PROVIDER_SPLIT_CANDIDATE','PROVIDER_FRACTIONAL_CANDIDATE','PROVIDER_GROUP_CANDIDATE'}
BENIGN_DISPOSITION_CODES = {'UNCLASSIFIED_ACQUISITION'}


def unpack(value, fallback=None):
    try: return json.loads(value) if isinstance(value,str) and value else (value if value is not None else fallback)
    except (ValueError,TypeError): return fallback


def database_revision(db, con=None):
    if con is None:
        with db.con() as c: return database_revision(db,c)
    def stat(sql): return con.execute(sql).fetchone()[0] or 0
    token = 'a%d-e%d-d%d-w%d' % (
        stat('SELECT max(id) FROM search_audits'),
        stat('SELECT max(id) FROM curated_events'),
        stat('SELECT max(id) FROM problem_dispositions'),
        stat('SELECT count(*) FROM works'))
    if con.execute('PRAGMA user_version').fetchone()[0]>=8:
        supplementary=stat('SELECT max(id) FROM supplementary_events')
        if supplementary:token+='-s%d'%supplementary
    return token


def audit_revision(db, audit, con=None):
    if audit['audit_revision'] is not None: return audit['audit_revision']
    if con is None:
        with db.con() as c: return audit_revision(db,audit,c)
    return con.execute('SELECT count(*) FROM search_audits WHERE work_id=? AND id<=?',
                         (audit['work_id'],audit['id'])).fetchone()[0]


def review_guard(db, work_id, audit, con=None):
    """Serialize the existing Grammar 3 authority for this exact audit/work.

    Scope metadata describes the snapshot; only the existing command fields
    authorize edits. Historical pins remain historical and Preview rejects them.
    """
    if con is None:
        with db.con() as c:
            c.execute('BEGIN')
            return review_guard(db,work_id,audit,c)
    work=db.work(work_id,con=con)
    if not work or audit['work_id']!=work_id:
        raise ValueError('Review audit does not belong to the linked work.')
    publication=unpack(audit['publication_json'],{})
    identity=publication.get('catalog_identity') or {}
    latest=db.latest_audit(work_id,con=con)
    revision=audit_revision(db,audit,con)
    token=database_revision(db,con)
    return {'database_uuid':db.database_uuid,'work_id':work_id,'work_uuid':work['work_uuid'],
            'audit_id':audit['id'],'audit_revision':revision,'database_revision':token,
            'edition':work['edition'],'language':work['language'],
            'publication_context':identity.get('publication_context'),
            'curation_revision':db.catalog.state(work_id,con=con)['revision'],
            'audit_curation_revision':publication.get('curation_revision',
                (publication.get('curated_database') or {}).get('revision',0)),
            'supplementary_revision':db.supplementary.revision(work_id,con),
            'audit_supplementary_revision':publication.get('supplementary_revision',0),
            'latest_global_audit_id':latest['id'] if latest else None,
            'audit_is_current':bool(latest and latest['id']==audit['id']),
            'command':f"guard database_uuid {db.database_uuid} audit {audit['id']} revision {revision} database {token}"}


def problem_policy(code, details=None):
    details=details or {}
    if code in IDENTITY_CODES: return ('IDENTITY','BLOCKED_IDENTITY','blocking',False)
    if code in ARTIFACT_CODES:
        return ('CODE','CODE_REVIEW_REQUIRED','root',False)
    if code=='UNCLASSIFIED_ACQUISITION': return ('UNKNOWN','RESEARCH_REQUIRED','root',False)
    if code in ('ACQUISITION_COVERAGE_GAP','MISSING_SPECIAL_ACQUISITION'): return ('ACQUISITION','ACQUISITION_ONLY','root',True)
    if code=='CHAPTER_COUNT_DISAGREEMENT' and details.get('chapters'):
        return ('ACQUISITION','ACQUISITION_ONLY','root',True)
    if code=='REFERENCE_CONFLICT': return ('RESEARCH','RESEARCH_REQUIRED','root',False)
    if code in ('UNMAPPED_CHAPTERS','MISSING_REFERENCE_STRUCTURE','VOLUME_COUNT_DISAGREEMENT'):
        return ('RESEARCH','RESEARCH_REQUIRED','root',False)
    if code in ('SOURCE_FAILURE','NO_USABLE_PROVIDER'): return ('ACQUISITION','ACQUISITION_ONLY','root',False)
    return ('UNKNOWN','UNKNOWN','root',False)


def persisted_problem_policy(row, details=None):
    """Read saved class/action, using the existing policy only for legacy nulls.

    Matches the acceptance evaluator's authority; does not classify or write rows.
    """
    row=dict(row)
    cls,action,role,sufficient=problem_policy(row['code'],details)
    return (row.get('problem_class') or cls,row.get('next_action') or action,role,sufficient)


def health(publication, issues, requested_edition='standard'):
    codes={i['problem_type'] for i in issues if i.get('disposition')!='IGNORED_WITH_REASON'}
    context=publication.get('context') or {}
    catalog_identity=publication.get('catalog_identity') or {}
    identity_ok=bool(context.get('shareable') and publication.get('edition')==requested_edition and
                     catalog_identity.get('trusted') and catalog_identity.get('language'))
    identity='PASS' if identity_ok and not codes & IDENTITY_CODES else 'REVIEW'
    if codes & {'NO_CANONICAL_RESULT','WRONG_EDITION_MATCH'}: identity='ERROR'
    normalized=publication.get('normalization') or {}
    normalization='PASS' if normalized.get('status')=='established' and not codes & (ARTIFACT_CODES | {'UNCLASSIFIED_ACQUISITION'}) else 'REVIEW'
    if publication.get('status') not in ('complete',None): normalization='ERROR'
    publication_health='PASS' if (identity=='PASS' and
        not codes & PUBLICATION_CODES and not (codes & {'CURATED_IDENTITY_CONFLICT'}) and
        publication.get('unmapped_chapters',0)==0 and not publication.get('conflicting_chapters')) else 'REVIEW'
    if publication.get('status') not in ('complete',None): publication_health='ERROR'
    acquisition='ERROR' if codes & {'NO_USABLE_PROVIDER','SOURCE_FAILURE'} and not publication.get('raw_acquisition_records') else (
        'PARTIAL' if codes & {'ACQUISITION_COVERAGE_GAP','MISSING_SPECIAL_ACQUISITION','CHAPTER_COUNT_DISAGREEMENT','SOURCE_FAILURE'} else 'PASS')
    if not publication.get('raw_acquisition_records') and not publication.get('volume_only_units') and acquisition=='PASS':
        acquisition='REVIEW'
    return {'identity':identity,'publication':publication_health,'normalization':normalization,
            'acquisition':acquisition}


def _reference_value(publication, source, key):
    value=(publication.get('references') or {}).get(source) or {}
    if source=='mangadex_structure':
        return (value.get('mappings') or {}).get(key)
    if source=='wikipedia':
        values={str(ch.get('volume')) for ch in value.get('chapters') or ()
                if str(ch.get('number') or ch.get('chapter'))==key and ch.get('volume') not in (None,'')}
        return next(iter(values)) if len(values)==1 else None
    return None


def affected_rows(publication, details, catalog_rows):
    keys=[str(k) for k in details.get('chapters') or () if k is not None]
    by_key=defaultdict(list)
    for row in catalog_rows: by_key[str(row['key'])].append(row)
    projection=list(publication.get('projection') or ())
    normalization=(publication.get('normalization') or {}).get('labels') or ()
    raw=defaultdict(list)
    artifact_metadata=(publication.get('normalization') or {}).get('artifact_rows') or ()
    for index,row in enumerate(projection):
        key=normalize_chapter_number(row.get('chapter')) or str(row.get('chapter') or row.get('id') or '')
        raw[key].append((row,normalization[index] if index<len(normalization) else None,
                         artifact_metadata[index] if index<len(artifact_metadata) else None))
    for row in (publication.get('provider_group_acquisition') or {}).get('alternatives') or ():
        key=normalize_chapter_number(row.get('chapter')) or str(row.get('chapter') or row.get('id') or '')
        if key not in raw:
            raw[key].append((row,'provider_group_alternative',dict(reason=row.get('reason'))))
    if not keys and details.get('affected'):
        keys=[str(r.get('chapter') or r.get('id')) for r in (publication.get('unmapped') or ())]
    keys=list(dict.fromkeys(keys))
    rows=[]
    for key in keys:
        normalized_key=normalize_chapter_number(key) or key
        match=by_key.get(normalized_key) or [None]
        sources=raw.get(normalized_key) or [(None,None,None)]
        for index,item in enumerate(match):
            source,label,artifact=sources[min(index,len(sources)-1)]
            auto=item['automatic'] if item else {}
            curated=item['curated'] if item else {}
            effective=item['effective'] if item else {}
            rows.append({'identifier':key,'provider':(source or {}).get('_acquisition_provider'),
                'provider_record_id':(source or {}).get('id'),'provider_title':(source or {}).get('title'),
                'scanlation_group_id':(source or {}).get('_scanlation_id'),
                'scanlation_group_name':(source or {}).get('_atsu_group_name'),
                'provider_url':(source or {}).get('url'),
                'reference_title':auto.get('title') if item and item.get('missing') else None,
                'normalization_class':label,
                'pattern_family':(artifact or {}).get('pattern_family'),
                'artifact_reason':(artifact or {}).get('reason'),
                'automatic_type':auto.get('type'),'curated_type':curated.get('type',{}).get('value'),
                'effective_type':effective.get('type'),
                'automatic_volume':auto.get('volume'),'curated_volume':curated.get('volume',{}).get('value'),
                'effective_volume':effective.get('volume'),
                'verification_state':sorted({v['verification'] for v in curated.values()}),
                'curated_source_notes':[v.get('note') for v in curated.values() if v.get('note')],
                'mangadex_value':_reference_value(publication,'mangadex_structure',normalized_key),
                'wikipedia_value':_reference_value(publication,'wikipedia',normalized_key),
                'reference_conflict':normalized_key in (publication.get('conflicting_chapters') or ())})
    return rows


def suggestion(issue, publication):
    code=issue['problem_type'];cls=issue.get('problem_class');action=issue.get('next_action')
    if action=='BLOCKED_IDENTITY' or code in IDENTITY_CODES:
        return {'command':None,'reason':'Identity is blocked. Resolve the exact work and edition selection before publication curation.'}
    if code in ARTIFACT_CODES or action=='CODE_REVIEW_REQUIRED':
        return {'command':None,'reason':'Provider numbering suggests an acquisition normalization/code review candidate; no title-specific mapping is justified.'}
    if code in ('ACQUISITION_COVERAGE_GAP','CHAPTER_COUNT_DISAGREEMENT','MISSING_SPECIAL_ACQUISITION') and (
            cls=='ACQUISITION' or code in ('ACQUISITION_COVERAGE_GAP','MISSING_SPECIAL_ACQUISITION') or issue.get('affected_identifiers')):
        return {'command':None,'reason':'Publication structure is complete; acquisition lacks these reference records. No publication database correction is required.'}
    if code=='REFERENCE_CONFLICT':
        return {'command':None,'reason':'Trusted structural evidence conflicts or is incomplete. Research the exact mapping before curation.'}
    if code=='UNCLASSIFIED_ACQUISITION':
        return {'command':None,'reason':'Provider records lack independent canonical evidence. Review normalization patterns or research their identity before curation.'}
    if code!='UNMAPPED_CHAPTERS':
        return {'command':None,'reason':'This problem has no evidence-backed deterministic catalog command; inspect its source evidence.'}
    if len(issue['affected_rows'])!=1:
        return {'command':None,'reason':'Unmapped publication chapters need individual, unambiguous trusted volume evidence before curation.'}
    row=issue['affected_rows'][0]
    md,wiki=row['mangadex_value'],row['wikipedia_value']
    refs=publication.get('references') or {}
    md_ref=refs.get('mangadex_structure') or {};wiki_ref=refs.get('wikipedia') or {}
    identity=publication.get('catalog_identity') or {}
    if (publication.get('status')=='complete' and identity.get('trusted') and
            identity.get('edition')==publication.get('edition') and
            md_ref.get('status')=='valid' and
            wiki_ref.get('status') in ('valid_with_data','valid_complete','valid_partial') and
            row['identifier'] not in (md_ref.get('ambiguous_chapters') or ()) and
            row['normalization_class'] in ('main','special','recognized_special') and
            md is not None and wiki is not None and str(md)==str(wiki) and
            row['automatic_volume'] in (None,'') and row['curated_volume'] is None and
            not row['reference_conflict'] and normalize_chapter_number(row['identifier']) and
            len({r['identifier'] for r in issue['affected_rows']})==1):
        return {'command':f"set volume {md} chapter {row['identifier']}",
                'reason':'MangaDex and Wikipedia explicitly agree; preview still required.',
                'sources':['mangadex_structure','wikipedia']}
    return {'command':None,'reason':'Reference agreement is absent, ambiguous, or already applied.'}


def issue_signature(hole, publication):
    details=unpack(hole['details_json'],{}) or {}
    identity=publication.get('catalog_identity') or {}
    basis={'code':hole['code'],'details':details,'canonical_work_id':identity.get('canonical_work_id'),
           'edition':identity.get('edition'),'language':identity.get('language'),
           'source':(publication.get('projection') or [{}])[0].get('_acquisition_provider')}
    if hole['code']=='UNCLASSIFIED_ACQUISITION':
        basis['raw_unclassified_rows']=[row for row in publication.get('unclassified_acquisition') or []
                                        if row.get('classification') in (None,'unclassified','provisional')]
    return hashlib.sha256(json.dumps(basis,sort_keys=True,default=str).encode()).hexdigest()


def issue_from_row(db, hole, audit=None, catalog_rows=None):
    audit=audit or db.latest_audit(hole['work_id'])
    publication=unpack(audit['publication_json'],{}) or {}
    details=unpack(hole['details_json'],{}) or {}
    cls,action,role,sufficient=persisted_problem_policy(hole,details)
    disposition=db.problem_disposition(hole['id'])
    if disposition and disposition['status']=='IGNORED_WITH_REASON':
        cls=disposition['problem_class'] or cls
        action='CODE_REVIEW_REQUIRED' if disposition['pattern'] else 'ACQUISITION_ONLY'
    rows=affected_rows(publication,details,catalog_rows if catalog_rows is not None else db.catalog.rows(hole['work_id']))
    issue={'problem_id':f"audit:{audit['id']}:problem:{hole['id']}",'problem_row_id':hole['id'],
           'audit_id':audit['id'],'audit_revision':audit_revision(db,audit),
           'work_id':hole['work_id'],'problem_type':hole['code'],'problem_class':cls,
           'next_action':action,'problem_role':role,'evidence_sufficient':sufficient,
           'severity':hole['severity'],'why_flagged':hole['message'],
           'confidence':details.get('confidence'),
           'affected_count':details.get('affected') or len(details.get('chapters') or ()),
           'affected_identifiers':details.get('chapters') or [],'affected_rows':rows,
           'details':details,'disposition':disposition['status'] if disposition else None,
           'disposition_reason':disposition['reason'] if disposition else None,
           'verification_state':disposition['verification'] if disposition else None}
    issue['suggestion']=suggestion(issue,publication)
    if issue['suggestion']['command']:
        issue['problem_class']='DATA';issue['next_action']='CURATION_READY';issue['evidence_sufficient']=True
    return issue


def review_packet(db, problem_ids=None, work_ids=None, include_ignored=False, audit_by_work=None):
    all_scope=problem_ids is None and work_ids is None
    revision_at_start=database_revision(db)
    from mangaanka_database_development_kit import audit_status
    audited=[row for row in db.works(audit_by_work=audit_by_work) if row['audit_id']]
    holes=db.holes('All',include_ignored=include_ignored,
                   audit_ids=list(audit_by_work.values()) if audit_by_work is not None else None)
    if problem_ids is not None:
        problem_ids=set(problem_ids);holes=[h for h in holes if h['id'] in problem_ids]
    if work_ids is not None:
        work_ids=set(work_ids);holes=[h for h in holes if h['work_id'] in work_ids]
    groups=defaultdict(list)
    for h in holes: groups[h['work_id']].append(h)
    if all_scope:
        for row in audited:
            if audit_status(row)!='PASS': groups[row['id']]
    if work_ids is not None and problem_ids is None:
        for row in audited:
            if row['id'] in work_ids and (audit_status(row)!='PASS' or
                    (unpack(row['publication_json'],{}) or {}).get('uncompiled_chapters')): groups[row['id']]
    if not all_scope:
        scoped_ids=set(work_ids) if work_ids is not None else set(groups)
        audited=[row for row in audited if row['id'] in scoped_ids]
    states=Counter('PASS' if audit_status(row)=='PASS' else
                   'ERROR' if audit_status(row)=='ERROR' else 'REVIEW' for row in audited)
    clean_omitted=[{'title':row['input_title'],'state':'PASS'} for row in audited
                   if audit_status(row)=='PASS' and row['id'] not in groups]
    works=[]
    for work_id in sorted(groups):
        work=db.work(work_id);audit=db.audit(audit_by_work.get(work_id),work_id) if audit_by_work is not None else db.latest_audit(work_id)
        publication=unpack(audit['publication_json'],{}) or {}
        rows=db.catalog.rows(work_id,audit=audit)
        issues=[issue_from_row(db,h,audit,rows) for h in groups[work_id]]
        curation=db.catalog.state(work_id)
        audit_fresh=bool(publication.get('catalog_identity') and
            publication.get('curation_revision',
                            (publication.get('curated_database') or {}).get('revision',0))==curation['revision'])
        current_curation_revision=curation['revision']
        if audit_by_work is not None:
            patch=publication.get('curated_database') or {}
            curation={'identity':publication.get('catalog_identity'),'revision':publication.get('curation_revision',0),
                      'fields':patch.get('fields') or [],'evidence':patch.get('evidence') or []}
        current_row=db.works([work_id],audit_by_work=audit_by_work)[0]
        if db.latest_audit(work_id)['id']!=audit['id']:audit_fresh=False
        if audit_status(current_row)=='RERUN REQUIRED':audit_fresh=False
        if not audit_fresh:
            for issue in issues:
                issue['suggestion']={'command':None,'reason':'RERUN REQUIRED: audit predates the current catalog state.'}
                issue['evidence_sufficient']=False
                if issue['next_action']=='CURATION_READY': issue['next_action']='UNKNOWN'
        context=publication.get('context') or {};identity=publication.get('catalog_identity') or {}
        manifest=publication.get('manifest') or {}
        structure_sources=dict(Counter(str((ch.get('volume') or {}).get('source'))
            for ch in manifest.get('chapters') or ()
            if (ch.get('volume') or {}).get('present') and (ch.get('volume') or {}).get('source')))
        normalization=publication.get('normalization') or {}
        affected={str(key) for issue in issues for key in issue['affected_identifiers']}
        normalization_summary={'status':normalization.get('status'),
                               'counts':normalization.get('counts') or {},
                               'artifact_groups':normalization.get('artifact_groups') or [],
                               'affected_evidence':{str(key):value for key,value in
                                   (normalization.get('evidence') or {}).items() if str(key) in affected}}
        inventories=unpack(audit['inventories_json'],[]) or []
        providers=[]
        for inv in inventories:
            # Stored inventory selection is authoritative. The first search
            # result from a provider may be an entirely different edition.
            providers.append(dict(inv,result_title=inv.get('result_title') or None))
        entry={'work_id':work_id,'audit_id':audit['id'],'audit_revision':audit_revision(db,audit),
               'latest_global_audit_id':db.latest_audit(work_id)['id'],
               'pin_state':'CURRENT' if db.latest_audit(work_id)['id']==audit['id'] else 'SUPERSEDED',
               'current_curation_revision':current_curation_revision,
               'audit_date':audit['created_at'],'database_revision':database_revision(db),
               'query':audit['query'],'matched_title':audit['match_title'],
               'canonical_title':context.get('canonical_title') or work['canonical_title'],
               'requested_edition':work['edition'],'selected_edition':publication.get('edition'),
               'language':work['language'],'publication_context':identity.get('publication_context'),
               'aliases':context.get('trusted_aliases') or [],'external_ids':identity.get('external_ids') or {},
               'selected_provider':audit['selected_source'],'match_tier':audit['match_tier'],
               'selected_acquisition_title':publication.get('selected_acquisition_title') or None,
               'selected_acquisition_edition':publication.get('acquisition_edition') or None,
               'selected_acquisition_ref':publication.get('selected_acquisition_ref') or None,
               'group_confidence':audit['group_confidence'],'group_reason':audit['group_reason'],
               'identity_status':context.get('shareability_reason'),'alias_retry':audit['alias_retry'],
               'providers':providers,'normalization':normalization_summary,
               'provider_group_acquisition':publication.get('provider_group_acquisition') or {},
               'counts':dict({k:publication.get(k) for k in ('raw_acquisition_records','canonical_main_chapters',
                   'recognized_specials','duplicate_records','logical_chapters',
                   'final_volumes','mapped_chapters','uncompiled_chapters','unmapped_chapters')},
                   **publication_classification_counts(publication)),
               'unclassified_acquisition':[row for row in publication.get('unclassified_acquisition') or []
                                           if row.get('classification') in (None,'unclassified','provisional')],
               'reference_states':dict({k:v.get('status') for k,v in (publication.get('references') or {}).items()
                                   if isinstance(v,dict)},curated_database=(publication.get('curated_database') or {}).get('status')),
               'structural_source_counts':structure_sources,
               'reported_totals':publication.get('reported_count_provenance') or [],
               'manifest_identity':manifest.get('work'),
               'manifest_edition':manifest.get('edition'),
               'mapping':{'mapped_identifiers':publication.get('mapped_identifiers') or [],
                          'uncompiled_identifiers':publication.get('uncompiled_identifiers') or [],
                          'unmapped_identifiers':[r.get('chapter') or r.get('id') for r in publication.get('unmapped') or ()],
                          'conflict_identifiers':publication.get('conflicting_chapters') or [],
                          'missing_acquisition_identifiers':publication.get('missing_reference_chapters') or [],
                          'missing_acquisition_specials':publication.get('missing_special_acquisition') or [],
                          'recognized_specials':publication.get('recognized_special_records') or []},
               'structural_coverage':publication.get('structural_coverage') or {},
               'supplementary_identity':db.supplementary.for_audit(work_id,audit),
               'supplementary_current_review':db.supplementary.for_audit(work_id,current=True),
               'catalog_freshness':publication.get('catalog_freshness') or {},
               'release_boundary':publication.get('release_boundary') or {},
               'uncompiled_evidence':publication.get('uncompiled_evidence') or {},
               'source_fingerprints':publication.get('source_fingerprints') or {},
               'curation':curation,'audit_fresh':audit_fresh,
               # Problem filters affect issue detail, never semantic audit health.
               'health':unpack(audit['health_json'],{}) or {},
               'health_basis':'persisted_disposition_adjusted_audit',
               'issues':issues,'reaudit_diff':db.audit_diff(work_id),
               'guard':review_guard(db,work_id,audit)['command']}
        works.append(entry)
    if database_revision(db)!=revision_at_start:
        raise ValueError('Database changed during review packet generation. Retry the export.')
    from mangaanka_database_development_kit import VERSION, SEARCH_CORE_VERSION
    with db.con() as con: schema_version=con.execute('PRAGMA user_version').fetchone()[0]
    return {'format':PACKET_FORMAT,'generated_at':datetime.now(timezone.utc).isoformat(),
            'ddk_version':VERSION,'search_core_version':SEARCH_CORE_VERSION,
            'command_grammar_version':GRAMMAR_VERSION,'database_schema_version':schema_version,
            'database_revision':revision_at_start,
            'database_uuid':db.database_uuid,'database_path':str(db.path),'database_role':db.role,
            'audit_summary':{'titles_audited':len(audited),'pass':states['PASS'],
                             'review':states['REVIEW'],'error':states['ERROR'],
                             'detailed_works_included':len(works),
                             'clean_works_omitted':len(clean_omitted)},
            'clean_works_omitted':clean_omitted,
            'code_review_candidates':db.code_review_candidates() if all_scope else [],
            'works':works}


def packet_markdown(packet):
    lines=['# MangaAnkā DDK Review Packet','',
           f"Generated: {packet['generated_at']}",
           f"DDK {packet['ddk_version']} · Search core {packet['search_core_version']} · Grammar {packet['command_grammar_version']}",
           f"Database revision: `{packet['database_revision']}`",
           f"Database UUID: `{packet['database_uuid']}` · {packet['database_role']} · {packet['database_path']}",
           f"Schema version: {packet['database_schema_version']}",'']
    summary=packet.get('audit_summary') or {}
    if summary:
        lines.extend(['## Audit summary','',
                      f"Titles audited: {summary['titles_audited']}",
                      f"PASS: {summary['pass']}",f"REVIEW: {summary['review']}",
                      f"ERROR: {summary['error']}",
                      f"Detailed works included: {summary['detailed_works_included']}",
                      f"Clean works omitted: {summary['clean_works_omitted']}",''])
        if packet.get('clean_works_omitted'):
            lines.extend(['Clean works omitted from detailed review:',''])
            lines.extend(f"- {work['title']} — {work['state']}" for work in packet['clean_works_omitted'])
            lines.append('')
    if packet.get('code_review_candidates'):
        lines.extend(['## Repeated provider patterns for code review',''])
        for candidate in packet['code_review_candidates']:
            lines.append('- '+json.dumps({k:v for k,v in candidate.items()
                if k not in ('all_identifiers','members')},ensure_ascii=False,sort_keys=True))
        lines.append('')
    for work in packet['works']:
        artifact_summary=[{k:v for k,v in group.items() if k not in ('identifiers','member_records','base_chapters')}
                          for group in work['normalization'].get('artifact_groups') or []]
        lines.extend([f"## {work['query']}",'',
          f"Audit `{work['audit_id']}` revision `{work['audit_revision']}` · Work `{work['work_id']}` · {work['audit_date']}",
          f"Audit freshness: {'current' if work['audit_fresh'] else 'RERUN REQUIRED'}",
          f"Identity: {work['matched_title']} / {work['canonical_title']} · {work['requested_edition']} → {work['selected_edition']} · {work['language']}",
          f"Health: {json.dumps(work['health'],ensure_ascii=False)}",
          f"Counts: {json.dumps(work['counts'],ensure_ascii=False)}",
          f"Selected provider: {work['selected_provider']} · Match: {work['match_tier']} · Identity: {work['identity_status']}",
          f"Selected acquisition: {work.get('selected_acquisition_title') or 'not recorded'} · Edition: {work.get('selected_acquisition_edition') or 'not recorded'}",
          f"Selected acquisition reference: {work.get('selected_acquisition_ref') or 'not recorded'}",
          f"Structural coverage: {json.dumps(work.get('structural_coverage') or {},ensure_ascii=False)}",
          f"Catalog freshness: {json.dumps(work.get('catalog_freshness') or {},ensure_ascii=False)}",
          f"Released / future / listed boundary: {json.dumps(work.get('release_boundary') or {},ensure_ascii=False)}",
          f"Uncompiled evidence: {json.dumps(work.get('uncompiled_evidence') or {},ensure_ascii=False)}",
          f"Source fingerprints: {json.dumps(work.get('source_fingerprints') or {},ensure_ascii=False)}",
          f"Reference states: {json.dumps(work['reference_states'],ensure_ascii=False)}",
          f"Structural source counts: {json.dumps(work['structural_source_counts'],ensure_ascii=False)}",
          f"Reported totals: {json.dumps(work['reported_totals'],ensure_ascii=False)}",
          f"Manifest identity: {json.dumps(work['manifest_identity'],ensure_ascii=False)}",
          f"Manifest edition: {json.dumps(work['manifest_edition'],ensure_ascii=False)}",
          f"Mapping: {json.dumps(work['mapping'],ensure_ascii=False)}",
          f"Supplementary identity / binding / membership evidence: {json.dumps(work.get('supplementary_identity') or {},ensure_ascii=False)}",
          f"Current supplementary review (separate from pinned audit): {json.dumps(work.get('supplementary_current_review') or {},ensure_ascii=False)}",
          f"Provider inventories: {json.dumps(work['providers'],ensure_ascii=False)}",
          f"Normalization: {json.dumps({k:v for k,v in work['normalization'].items() if k!='artifact_groups'},ensure_ascii=False)}",
          f"Artifact groups: {json.dumps(artifact_summary,ensure_ascii=False)}",
          f"Curation: {json.dumps(work['curation'],ensure_ascii=False)}",
          f"Re-audit diff: {json.dumps(work['reaudit_diff'],ensure_ascii=False)}",
          f"Guard for proposed edit batches: `{work['guard']}`",''])
        for issue in work['issues']:
            identifiers=issue['affected_identifiers']
            shown=identifiers[:12]
            suffix=f' (+{len(identifiers)-len(shown)} in JSON)' if len(identifiers)>len(shown) else ''
            lines.extend([f"### {issue['problem_type']} · `{issue['problem_id']}`",
              f"{issue['severity'].upper()} · {issue['problem_class']} · {issue['next_action']} · {issue['problem_role']}",
              f"Confidence: {issue['confidence']}" if issue.get('confidence') else 'Confidence: not specified',
              issue['why_flagged'],f"Affected ({issue['affected_count']}): {', '.join(map(str,shown)) or 'not enumerated'}{suffix}",
              f"Suggested command: {issue['suggestion']['command'] or 'none'} — {issue['suggestion']['reason']}"])
            for row in issue['affected_rows'][:12]:
                lines.append('- '+json.dumps(row,ensure_ascii=False,sort_keys=True))
            if len(issue['affected_rows'])>12:
                lines.append(f"- {len(issue['affected_rows'])-12} additional exact rows in the paired JSON packet.")
            if issue['disposition']:
                lines.append(f"Disposition: {issue['disposition']} — {issue['disposition_reason']}")
            lines.append('')
    return '\n'.join(lines).rstrip()+'\n'


CSV_COLUMNS=('audit_id','audit_revision','problem_id','work_id','query','canonical_title','edition',
 'language','raw_acquisition_records','canonical_main_chapters','classified_provider_artifacts',
 'provider_artifact_breakdown','unclassified_records',
 'severity','problem_class','problem_type','problem_role','next_action','confidence','affected_identifier',
 'provider','provider_record_id','provider_title','provider_url','reference_title',
 'automatic_type','curated_type','effective_type',
 'automatic_volume','curated_volume','effective_volume','mangadex_status','mangadex_value',
 'wikipedia_status','wikipedia_value','curated_db_status','reference_conflict',
 'normalization_class','pattern_family','artifact_reason','why_flagged','verification_state','audit_date')


def detailed_csv(packet, path):
    count=0
    with open(path,'w',newline='',encoding='utf-8-sig') as output:
        writer=csv.DictWriter(output,fieldnames=CSV_COLUMNS);writer.writeheader()
        for work in packet['works']:
            for issue in work['issues']:
                for row in issue['affected_rows'] or [{}]:
                    item={'audit_id':work['audit_id'],'audit_revision':work['audit_revision'],
                      'problem_id':issue['problem_id'],'work_id':work['work_id'],'query':work['query'],
                      'canonical_title':work['canonical_title'],'edition':work['selected_edition'],
                      'language':work['language'],
                      'raw_acquisition_records':work['counts']['raw_acquisition_records'],
                      'canonical_main_chapters':work['counts']['canonical_main_chapters'],
                      'classified_provider_artifacts':work['counts']['classified_provider_artifacts'],
                      'provider_artifact_breakdown':json.dumps(work['counts']['provider_artifact_breakdown'],
                                                              ensure_ascii=False,sort_keys=True),
                      'unclassified_records':work['counts']['unclassified_records'],
                      'severity':issue['severity'],
                      'problem_class':issue['problem_class'],'problem_type':issue['problem_type'],
                      'problem_role':issue['problem_role'],'next_action':issue['next_action'],
                      'confidence':issue.get('confidence'),
                      'affected_identifier':row.get('identifier'),'provider':row.get('provider'),
                      'provider_record_id':row.get('provider_record_id'),'provider_title':row.get('provider_title'),
                      'provider_url':row.get('provider_url'),'reference_title':row.get('reference_title'),
                      'automatic_type':row.get('automatic_type'),'curated_type':row.get('curated_type'),
                      'effective_type':row.get('effective_type'),'automatic_volume':row.get('automatic_volume'),
                      'curated_volume':row.get('curated_volume'),'effective_volume':row.get('effective_volume'),
                      'mangadex_status':work['reference_states'].get('mangadex_structure'),
                      'mangadex_value':row.get('mangadex_value'),
                      'wikipedia_status':work['reference_states'].get('wikipedia'),
                      'wikipedia_value':row.get('wikipedia_value'),
                      'curated_db_status':work['curation'].get('identity') and 'bound' or 'absent',
                      'reference_conflict':row.get('reference_conflict'),
                      'normalization_class':row.get('normalization_class'),
                      'pattern_family':row.get('pattern_family'),
                      'artifact_reason':row.get('artifact_reason'),
                      'why_flagged':issue['why_flagged'],
                      'verification_state':','.join(row.get('verification_state') or []),
                      'audit_date':work['audit_date']}
                    writer.writerow(item);count+=1
    return count


def write_packet(packet, base_path):
    base=Path(base_path)
    if base.suffix.lower() in ('.md','.json'): base=base.with_suffix('')
    md=base.with_suffix('.md');js=base.with_suffix('.json')
    md.write_text(packet_markdown(packet),encoding='utf-8')
    js.write_text(json.dumps(packet,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return md,js
