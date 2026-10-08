"""Read-only, explicitly scoped catalog and Working Set sharing formats."""
import csv
from datetime import datetime, timezone
from io import StringIO
import json

from ddk_chapter_normalization import publication_classification_counts
from ddk_supplementary import publication_supplements
from ddk_review import database_revision, audit_revision, persisted_problem_policy, review_guard, GRAMMAR_VERSION


def unpack(value,default=None):
    try:return json.loads(value) if value else (default if default is not None else {})
    except (ValueError,TypeError):return default if default is not None else {}


def catalog_context(db,work_id,item=None):
    work=db.work(work_id)
    if not work:raise ValueError('Select a linked catalog work.')
    latest=db.latest_audit(work_id)
    audit=db.audit(item['pinned_audit_id'],work_id) if item else latest
    pub=unpack(audit['publication_json']) if audit else {}
    identity=pub.get('catalog_identity') or {}
    context=pub.get('context') or {}
    problems=[];affected=set()
    for h in db.holes('All',audit_ids=[audit['id']] if audit else []):
        if h['work_id']!=work_id:continue
        details=unpack(h['details_json'])
        cls,action,_,_=persisted_problem_policy(h,details)
        problems.append({'code':h['code'],'class':cls,'next_action':action,'message':h['message'],
                         'details':details})
        affected.update(str(v) for v in (details.get('chapters') or ()))
    canonical_unmapped={str(r.get('chapter') or r.get('id')) for r in pub.get('unmapped') or ()}
    unclassified={str(r.get('chapter') if r.get('chapter') is not None else r.get('id'))
                  for r in pub.get('unclassified_acquisition') or ()}
    if not unclassified:
        labels=(pub.get('normalization') or {}).get('labels') or ()
        unclassified={str(r.get('chapter') if r.get('chapter') is not None else r.get('id'))
                      for r,label in zip(pub.get('projection') or (),labels)
                      if label=='unclassified'}
    affected.update(canonical_unmapped)
    affected.update(unclassified)
    affected.update(str(v) for v in pub.get('conflicting_chapters') or ())
    affected.update(str(v) for v in pub.get('missing_reference_chapters') or ())
    rows=db.catalog.rows(work_id,audit=audit) if audit else []
    relevant=[{'chapter':r['key'],'automatic':r['automatic'],'curated':r['curated'],
               'effective':r['effective'],'status':r['status']} for r in rows
              if r['key'] in affected or r['curated'] or r['conflict'] or r['missing']]
    curation=(dict(revision=pub.get('curation_revision',0),
                   fields=(pub.get('curated_database') or {}).get('fields') or [],
                   evidence=(pub.get('curated_database') or {}).get('evidence') or [])
              if item else db.catalog.state(work_id))
    counts=publication_classification_counts(pub) if audit else {}
    result={'database_uuid':db.database_uuid,'database_path':str(db.path),
            'database_revision':database_revision(db),'work_uuid':work['work_uuid'],
            'working_set_uuid':item['working_set_uuid'] if item else None,
            'working_set_item_uuid':item['working_set_item_uuid'] if item else None,
            'title':work['input_title'],'edition':work['edition'],'language':work['language'],
            'catalog_status':work['lifecycle_status'],'acceptance_state':db.acceptance.state(work_id),
            'latest_global_audit_id':latest['id'] if latest else None,
            'pin_state': 'UNPINNED' if not audit else 'SUPERSEDED' if latest and audit['id']!=latest['id'] else 'CURRENT',
            'duplicate_of_item_uuid':item.get('duplicate_of_item_uuid') if item else None,
            'canonical_identity':identity.get('canonical_work_id'),
            'external_ids':identity.get('external_ids') or {},'creator':context.get('creator'),
            'aliases':context.get('trusted_aliases') or [],'health':unpack(audit['health_json']) if audit else {},
            'health_basis':'persisted_disposition_adjusted_audit',
            'selected_provider':audit['selected_source_name'] or audit['selected_source'] if audit else None,
            'selected_acquisition':pub.get('selected_acquisition_ref'),
            'canonical_chapters':pub.get('logical_chapters'),'volumes':pub.get('final_volumes'),
            'canonical_main_chapters':pub.get('canonical_main_chapters',pub.get('canonical_chapters')),
            'logical_publication_units':pub.get('logical_chapters'),
            'acquired_specials':pub.get('recognized_specials'),
            'mapped_main_chapters':pub.get('mapped_main_chapters'),
            'unassigned_specials':pub.get('unassigned_specials'),
            'mapped':pub.get('mapped_chapters'),'uncompiled':pub.get('uncompiled_chapters',0),'unmapped':pub.get('unmapped_chapters'),
            'uncompiled_identifiers':pub.get('uncompiled_identifiers') or [],
            'recognized_specials':pub.get('recognized_special_records') or [],
            'supplementary_identity':db.supplementary.for_audit(work_id,audit) if audit else publication_supplements(pub),
            'supplementary_current_review':db.supplementary.for_audit(work_id,current=True) if latest else {},
            'missing_special_acquisition':pub.get('missing_special_acquisition') or [],
            'canonical_unmapped_identifiers':sorted(canonical_unmapped),
            'unclassified_acquisition_identifiers':sorted(unclassified-canonical_unmapped),
            'conflicts':pub.get('conflicting_chapters') or [],
            'missing_acquisition':pub.get('missing_reference_chapters') or [],
            'provider_artifacts':counts.get('classified_provider_artifacts',0),
            'provider_group_acquisition':pub.get('provider_group_acquisition') or {},
            'unclassified':counts.get('unclassified_records',0),
            'reference_states':{k:v.get('status') for k,v in (pub.get('references') or {}).items() if isinstance(v,dict)},
            'structural_coverage':pub.get('structural_coverage') or {},
            'catalog_freshness':pub.get('catalog_freshness') or {},
            'release_boundary':pub.get('release_boundary') or {},
            'uncompiled_evidence':pub.get('uncompiled_evidence') or {},
            'source_fingerprints':pub.get('source_fingerprints') or {},
            'reported_totals':pub.get('reported_count_provenance') or [],
            'problems':problems,'affected_records':relevant,
            'curation_revision':pub.get('curation_revision',0) if item else curation['revision'],
            'curated_verifications':sorted({r['verification'] for r in curation['fields']}),
            'curated_evidence':curation['evidence'],
            'curated_fields':len(curation['fields']),
            'audit_id':audit['id'] if audit else None,
            'audit_revision':audit_revision(db,audit) if audit else None}
    if audit:
        result['guard']=f"guard database_uuid {db.database_uuid} audit {audit['id']} revision {audit_revision(db,audit)} database {database_revision(db)}"
    return result


def catalog_summary(db,work_id,item=None):
    c=catalog_context(db,work_id,item)
    lines=[f"{c['title']} · {c['edition']} / {c['language']}",
           f"Work UUID: {c['work_uuid']} · {c['catalog_status']}",
           f"Canonical: {c['canonical_identity'] or 'unresolved'}",
           'Health: '+', '.join(f'{k} {v}' for k,v in c['health'].items()),
           f"Provider: {c['selected_provider'] or 'none'}",
           f"Chapters: {c['canonical_chapters']} · Volumes: {c['volumes']} · Mapped: {c['mapped']} · Uncompiled: {c['uncompiled']} · Unmapped: {c['unmapped']}",
           f"Artifacts: {c['provider_artifacts']} · Unclassified: {c['unclassified']}",
           f"Curated fields: {c['curated_fields']} · Revision: {c['curation_revision']}",
           f"Snapshot audit: {c['audit_id']} / revision {c['audit_revision']} · Latest global: {c['latest_global_audit_id']} · {c['pin_state']}",
           f"Acceptance: {c['acceptance_state']}"]
    if c['canonical_unmapped_identifiers']:
        lines.append('Canonical unmapped chapters: '+', '.join(c['canonical_unmapped_identifiers'][:60])+
                     (f' (+{len(c["canonical_unmapped_identifiers"])-60} more)' if len(c['canonical_unmapped_identifiers'])>60 else ''))
    if c['uncompiled_identifiers']:
        lines.append('Uncompiled / serialized chapters: '+', '.join(c['uncompiled_identifiers']))
    if c['unclassified_acquisition_identifiers']:
        lines.append('Unclassified acquisition: '+', '.join(c['unclassified_acquisition_identifiers'][:20])+
                     (f' (+{len(c["unclassified_acquisition_identifiers"])-20} more)' if len(c['unclassified_acquisition_identifiers'])>20 else ''))
    if c['problems']:lines.extend(f"{p['code']} → {p['next_action']}: {p['message']}" for p in c['problems'])
    return '\n'.join(lines)


def review_context(db,work_id,item=None):
    return '# MangaAnkā DDK Selected Review Context\n\n```json\n'+json.dumps(
        catalog_context(db,work_id,item),ensure_ascii=False,indent=2,default=str)+'\n```\n'


def working_set_rows(db,set_uuid,mode='pinned'):
    if mode not in ('pinned','current'):raise ValueError('Choose pinned or current Working Set state.')
    ws=db.working_sets.get(set_uuid)
    if not ws:raise ValueError('Unknown Working Set in active database.')
    result=[]
    with db.con() as c:
        for item in db.working_sets.items(set_uuid):
            work=db.work(item['work_id']) if item['work_id'] else None
            latest=db.latest_audit(work['id']) if work else None
            audit_id=item['pinned_audit_id'] if mode=='pinned' else (
                db.latest_audit(work['id'])['id'] if work and db.latest_audit(work['id']) else None)
            audit=c.execute('SELECT * FROM search_audits WHERE id=?',(audit_id,)).fetchone() if audit_id else None
            pub=unpack(audit['publication_json']) if audit else {}
            health=unpack(audit['health_json']) if audit else {}
            counts=publication_classification_counts(pub) if audit else {}
            result.append({'database_uuid':db.database_uuid,'working_set_uuid':set_uuid,
                'working_set_name':ws['name'],'working_set_item_uuid':item['working_set_item_uuid'],
                'query':item['original_query'],'work_uuid':work['work_uuid'] if work else '',
                'catalog_status':work['lifecycle_status'] if work else 'UNLINKED',
                'acceptance_state':db.acceptance.state(work['id']) if work else 'NONE',
                'latest_global_audit_id':latest['id'] if latest else None,
                'pin_state':'UNPINNED' if not item['pinned_audit_id'] else 'CURRENT' if latest and latest['id']==item['pinned_audit_id'] else 'SUPERSEDED',
                'duplicate_of_item_uuid':item['duplicate_of_item_uuid'],
                'edition':item['requested_edition'],'language':item['requested_language'],
                'canonical_identity':(pub.get('catalog_identity') or {}).get('canonical_work_id') or '',
                'identity_health':health.get('identity',''),'publication_health':health.get('publication',''),
                'normalization_health':health.get('normalization',''),'acquisition_health':health.get('acquisition',''),
                'selected_provider':audit['selected_source_name'] or audit['selected_source'] if audit else '',
                'chapters':pub.get('logical_chapters'),'volumes':pub.get('final_volumes'),
                'mapped':pub.get('mapped_chapters'),'uncompiled':pub.get('uncompiled_chapters',0),'unmapped':pub.get('unmapped_chapters'),
                'provider_artifacts':counts.get('classified_provider_artifacts',0),
                'unclassified':counts.get('unclassified_records',0),
                'curated_fields':len(db.catalog.state(work['id'])['fields']) if work and mode=='current' else
                    len((pub.get('curated_database') or {}).get('fields') or ()) if audit else 0,
                'curation_revision':pub.get('curation_revision'),
                'pinned_audit_id':item['pinned_audit_id'],'audit_id':audit_id,
                'pinned_audit_revision':item['pinned_audit_revision'],
                'audit_revision':audit['audit_revision'] if audit else None,
                'audit_ddk_version':audit['ddk_version'] if audit else None,
                'audit_search_core_version':audit['search_core_version'] if audit else None,
                'audit_schema_version':audit['schema_version'] if audit else None,
                'audit_requested_edition':audit['requested_edition'] if audit else None,
                'audit_requested_language':audit['requested_language'] if audit else None,
                'audit_workflow':audit['workflow'] if audit else None,
                'audit_freshness':'NOT AUDITED' if not audit else 'PINNED' if mode=='pinned' else 'CURRENT',
                'item_status':item['processing_status']})
    return result


def working_set_csv(db,set_uuid,mode='pinned'):
    rows=working_set_rows(db,set_uuid,mode)
    from mangaanka_database_development_kit import VERSION,SEARCH_CORE_VERSION
    out=StringIO(newline='');writer=csv.writer(out)
    fields=list(rows[0]) if rows else ['database_uuid','working_set_uuid','working_set_name','query']
    writer.writerow(['exported_at','ddk_version','search_core_version','mode',*fields])
    date=datetime.now(timezone.utc).isoformat()
    for row in rows:writer.writerow([date,VERSION,SEARCH_CORE_VERSION,mode,*(row.get(k) for k in fields)])
    return out.getvalue()


def working_set_title_list(db,set_uuid):
    return '\n'.join(item['original_query'] for item in db.working_sets.items(set_uuid))


def working_set_review_context(db,set_uuid,mode='pinned'):
    """Compact human-readable batch context; the raw packet remains an advanced export."""
    ws=db.working_sets.get(set_uuid)
    if not ws:raise ValueError('Select a Working Set.')
    rows=working_set_rows(db,set_uuid,mode)
    lines=[f'# {ws["name"]} — {mode.title()} Audit Context',
           f'Database UUID: {db.database_uuid}',f'Working Set UUID: {set_uuid}',
           f'Status: {ws["status"]} · Items: {len(rows)}','']
    with db.con() as c:
        for row in rows:
            lines.append(f'## {row["query"]} · {row["edition"]} / {row["language"]}')
            lines.append(f'Item: {row["item_status"]} · Catalog: {row["catalog_status"]} · Acceptance: {row["acceptance_state"]} · Work UUID: {row["work_uuid"] or "unlinked"}')
            lines.append(f'Item UUID: {row["working_set_item_uuid"]} · Pin: {row["pinned_audit_id"]} / revision {row["pinned_audit_revision"]} · Latest global: {row["latest_global_audit_id"]} · {row["pin_state"]} · Curation revision: {row["curation_revision"]} · Duplicate of: {row["duplicate_of_item_uuid"] or "none"}')
            lines.append(f'Audit: {row["audit_id"] or "none"} · Revision: {row["audit_revision"] or "none"} · {row["audit_freshness"]}')
            lines.append(f'Identity: {row["canonical_identity"] or "unresolved"} · Provider: {row["selected_provider"] or "none"}')
            lines.append(f'Chapters: {row["chapters"]} · Volumes: {row["volumes"]} · Mapped: {row["mapped"]} · Unmapped: {row["unmapped"]}')
            if row['audit_id']:
                holes=c.execute('SELECT code,message FROM audit_holes WHERE audit_id=? ORDER BY code',
                                (row['audit_id'],)).fetchall()
                for hole in holes:lines.append(f'- {hole["code"]}: {hole["message"]}')
            if not row['audit_id'] or row['item_status']=='ERROR':
                observation=db.working_sets.latest_observation(row['working_set_item_uuid'])
                for hole in (observation or {}).get('holes') or ():
                    lines.append(f'- {hole.get("code","INTAKE_REVIEW")}: {hole.get("message","")}')
            lines.append('')
    return '\n'.join(lines)


def working_set_packet(db,set_uuid,mode='pinned'):
    if mode not in ('pinned','current'):raise ValueError('Choose pinned or current Working Set state.')
    entries=[]
    with db.con() as c:
        # One read snapshot binds pins, immutable audits and the existing token.
        # This is deferred/read-only; exporting never takes a writer transaction.
        c.execute('BEGIN')
        ws=db.working_sets.get(set_uuid,con=c)
        if not ws:raise ValueError('Select a Working Set.')
        token=database_revision(db,c)
        for item in db.working_sets.items(set_uuid,con=c):
            latest=db.latest_audit(item['work_id'],con=c) if item['work_id'] else None
            audit_id=item['pinned_audit_id'] if mode=='pinned' else (latest['id'] if latest else None)
            row=c.execute('SELECT * FROM search_audits WHERE id=? AND work_id=?',
                          (audit_id,item['work_id'])).fetchone() if audit_id else None
            if audit_id and not row:raise ValueError('Pinned audit does not belong to the linked work.')
            audit=dict(row) if row else None
            holes=[dict(r) for r in c.execute('SELECT * FROM audit_holes WHERE audit_id=?',(audit_id,))] if audit else []
            entries.append({'item':item,'audit':audit,'holes':holes,
                            'review_guard':review_guard(db,item['work_id'],audit,con=c) if audit else None,
                            'unresolved_observation':db.working_sets.latest_observation(item['working_set_item_uuid'],con=c)
                            if not audit or item['processing_status']=='ERROR' else None})
    return {'format':'mangaanka-ddk-working-set-review-v1','database_uuid':db.database_uuid,
            'database_revision':token,'command_grammar_version':GRAMMAR_VERSION,
            'working_set':ws,'mode':mode,'entries':entries}
