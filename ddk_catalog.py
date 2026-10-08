"""SQLite curation, exact identity bindings, previews and reversible transactions.

Audit snapshots are immutable inputs. Only tables prefixed curated_ are edited.
"""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import uuid

from mangaanka_search_core.cross_source_fallback import normalize_chapter_number

SCHEMA = '''
CREATE TABLE IF NOT EXISTS curated_catalog(
 work_id INTEGER PRIMARY KEY REFERENCES works(id) ON DELETE CASCADE,
 identity_json TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS curated_fields(
 work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
 entity TEXT NOT NULL, record_key TEXT NOT NULL, field TEXT NOT NULL,
 value_json TEXT NOT NULL, verification TEXT NOT NULL, note TEXT NOT NULL DEFAULT '',
 source_name TEXT NOT NULL DEFAULT '', source_url TEXT NOT NULL DEFAULT '', accessed_at TEXT NOT NULL DEFAULT '',
 PRIMARY KEY(work_id,entity,record_key,field));
CREATE TABLE IF NOT EXISTS curated_evidence(
 evidence_uuid TEXT PRIMARY KEY,
 work_id INTEGER NOT NULL REFERENCES works(id),
 entity TEXT NOT NULL,
 record_key TEXT NOT NULL,
 field TEXT NOT NULL,
 assertion_revision INTEGER NOT NULL,
 source_name TEXT NOT NULL,
 source_url TEXT NOT NULL DEFAULT '',
 accessed_at TEXT NOT NULL,
 note TEXT NOT NULL DEFAULT '',
 verification TEXT NOT NULL,
 created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS curated_evidence_target_idx ON curated_evidence(work_id,entity,record_key,field,assertion_revision);
CREATE TABLE IF NOT EXISTS curated_changes(
 id INTEGER PRIMARY KEY, work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
 timestamp TEXT NOT NULL, operation TEXT NOT NULL, changes_json TEXT NOT NULL,
 identity_before TEXT, identity_after TEXT NOT NULL,
 state TEXT NOT NULL DEFAULT 'active', revision INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS curated_events(
 id INTEGER PRIMARY KEY, change_id INTEGER NOT NULL REFERENCES curated_changes(id),
 timestamp TEXT NOT NULL, action TEXT NOT NULL);
'''
VERIFICATIONS = ('UNVERIFIED', 'REVIEWED', 'VERIFIED')
TYPES = ('chapter', 'bonus', 'extra', 'omake', 'special', 'prologue', 'epilogue')
FIELDS = {
 'chapter': {'exists', 'chapter', 'title', 'type', 'volume', 'source_note'},
 'volume': {'exists', 'title', 'external_ids', 'source_note'},
 'work': {'canonical_title', 'canonical_work_id', 'edition', 'language', 'publication_context',
          'aliases', 'external_ids', 'expected_chapters', 'expected_volumes', 'publication_status', 'source_note'},
}


def dumps(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def stamp():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def edition_key(value):
    return {'original':'standard', 'color':'official_color', 'colored':'official_color',
            'fan_colored':'fan_color'}.get(str(value), str(value))


def identity_for(selected, context, language):
    explicit = selected.get('edition_class') or selected.get('edition')
    edition = edition_key(explicit or context.get('edition_profile') or 'unknown')
    # The core currently distinguishes color editions but not every print format.
    # At this new authority boundary, native format markers must never receive a
    # standard patch. Aliases and enrichment titles are deliberately excluded.
    native=' '.join(str(selected.get(k) or '') for k in ('_provider_native_title','full_title','badge'))
    if not selected.get('_provider_native_title'): native+=' '+str(selected.get('title') or '')
    formats=set(re.findall(r'\b(omnibus|deluxe|bunkobon|kanzenban)\b',native.casefold()))
    if formats:
        edition=next(iter(formats)) if len(formats)==1 and edition in ('standard',next(iter(formats))) else 'unknown'
    ids = {str(k): str(v) for k,v in (selected.get('external_ids') or {}).items() if v}
    canonical = str(context.get('canonical_work_id') or selected.get('canonical_work_id') or '')
    if ':' in canonical:
        source, value = canonical.split(':', 1)
        ids.setdefault(source, value)
    return {'canonical_work_id':canonical, 'edition':edition, 'language':str(language or ''),
            'publication_context':str(selected.get('publication_context') or ''), 'external_ids':ids,
            'trusted':bool(context.get('shareable') and canonical and language and edition not in ('','unknown'))}


def compatible(bound, incoming):
    if not bound.get('trusted') or not incoming.get('trusted'):
        return False, 'Canonical identity is not trusted; no curated fields applied.'
    for key in ('canonical_work_id','edition','language','publication_context'):
        if bound.get(key) != incoming.get(key):
            return False, f'Incompatible {key}: catalog={bound.get(key)!r}, current={incoming.get(key)!r}.'
    left, right = bound.get('external_ids', {}), incoming.get('external_ids', {})
    if any(str(left[k]) != str(right[k]) for k in left.keys() & right.keys()):
        return False, 'Contradictory trusted external IDs.'
    return True, 'Exact compatible work, edition, language and publication context.'


def chapter_key(row):
    number = normalize_chapter_number(row.get('chapter'))
    if number is not None:
        return number
    source = row.get('_acquisition_provider') or row.get('_source_id') or row.get('source_id') or ''
    return '@' + source + ':' + str(row.get('id') or row.get('chapter') or '')


def numeric(value, field):
    text = str(value).strip()
    if not re.fullmatch(r'\d+(?:\.\d+)?', text):
        raise ValueError(f'{field} must be a non-negative decimal number.')
    parsed = Decimal(text)
    if not parsed.is_finite():
        raise ValueError(f'Invalid {field}.')
    return format(parsed.normalize(), 'f')


def checked_value(entity, field, value):
    if field not in FIELDS.get(entity, set()):
        raise ValueError(f'Unsupported {entity} field: {field}')
    if value is None:
        if field not in ('volume','title','source_note'):
            raise ValueError(f'{field} cannot be cleared.')
        return None
    if field == 'exists':
        if value is not True: raise ValueError('Curated record existence must be true.')
        return True
    if field in ('volume','chapter'):
        return numeric(value,field)
    if field == 'type' and value not in TYPES:
        raise ValueError('Unknown chapter type.')
    if field in ('expected_chapters','expected_volumes'):
        if not str(value).isdigit():
            raise ValueError('Expected counts must be non-negative integers.')
        return int(value)
    if field == 'aliases':
        if not isinstance(value, list) or not all(isinstance(v,str) for v in value):
            raise ValueError('Aliases must be a list of exact strings.')
        return list(dict.fromkeys(v.strip() for v in value if v.strip()))
    if field == 'external_ids':
        if not isinstance(value,dict) or not all(isinstance(k,str) and isinstance(v,str) and k and v for k,v in value.items()):
            raise ValueError('External IDs must have nonempty source and ID strings.')
        return value
    if field in ('canonical_work_id','canonical_title','edition','language') and not str(value).strip():
        raise ValueError(f'{field} cannot be empty.')
    return str(value).strip()


class Catalog:
    def __init__(self, db):
        self.db = db
        self.backed_up = False
        with db.con() as c:
            tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {'curated_catalog','curated_fields','curated_changes','curated_events'} <= tables:
                raise ValueError('DDK curated schema is incomplete.')

    def state(self, work_id, con=None):
        if con is None:
            with self.db.con() as c:
                return self.state(work_id,c)
        bound = con.execute('SELECT * FROM curated_catalog WHERE work_id=?',(work_id,)).fetchone()
        fields = [dict(r) for r in con.execute('SELECT * FROM curated_fields WHERE work_id=? ORDER BY entity,record_key,field',(work_id,))]
        for row in fields:
            row['value'] = json.loads(row.pop('value_json'))
        evidence=[dict(r) for r in con.execute('SELECT * FROM curated_evidence WHERE work_id=? ORDER BY created_at,evidence_uuid',(work_id,))]
        return {'identity':json.loads(bound['identity_json']) if bound else None,
                'revision':bound['revision'] if bound else 0, 'fields':fields,'evidence':evidence}

    def evidence(self,work_id,entity=None,key=None,field=None):
        rows=self.state(work_id)['evidence']
        return [r for r in rows if (entity is None or r['entity']==entity) and
                (key is None or r['record_key']==str(key)) and (field is None or r['field']==field)]

    def lookup(self, incoming, work_id=None, con=None):
        if con is None:
            with self.db.con() as c:return self.lookup(incoming,work_id,con=c)
        candidates = [dict(r) for r in con.execute('SELECT * FROM curated_catalog cc WHERE EXISTS (SELECT 1 FROM curated_fields cf WHERE cf.work_id=cc.work_id)')]
        same = [r for r in candidates if json.loads(r['identity_json']).get('canonical_work_id') == incoming.get('canonical_work_id')]
        local=next((r for r in candidates if r['work_id']==work_id),None)
        if local and not compatible(json.loads(local['identity_json']),incoming)[0]:
            return {'status':'incompatible','reason':compatible(json.loads(local['identity_json']),incoming)[1], 'fields':[]}
        accepted = [r for r in same if compatible(json.loads(r['identity_json']),incoming)[0]]
        if len(accepted) > 1:
            return {'status':'ambiguous','reason':'Multiple exact-compatible curated catalog records.', 'fields':[]}
        if not accepted:
            if work_id is not None and hasattr(self.db,'working_sets'):
                relation=self.db.working_sets.structure_source(work_id,con=con)
                if relation:
                    source=self.db.work(relation['source_work_id'],con=con);target=self.db.work(work_id,con=con)
                    state=self.state(source['id'],con=con)
                    bound=state['identity'] or {}
                    latest=self.db.latest_audit(source['id'],con=con)
                    source_identity=(json.loads(latest['publication_json'] or '{}').get('catalog_identity') or {}) if latest else {}
                    if (target and source['canonical_work_id']==target['canonical_work_id']==incoming.get('canonical_work_id')
                        and incoming.get('trusted') and incoming.get('edition')==target['edition']
                        and incoming.get('language')==target['language']
                        and bound.get('trusted') and bound.get('canonical_work_id')==incoming.get('canonical_work_id')
                        and bound.get('edition')==source['edition'] and bound.get('language')==target['language']
                        and relation['target_context']==incoming.get('publication_context','')
                        and relation['source_context']==source_identity.get('publication_context','')
                        and compatible(bound,source_identity)[0]):
                        shared=[f for f in state['fields'] if f['entity']=='chapter' and f['field']=='volume'
                                and f['verification'] in ('REVIEWED','VERIFIED')]
                        if shared:return {'status':'matched','reason':'Explicit reviewed same-structure relationship.',
                            'fields':shared,'work_id':source['id'],'structure_shared':True,
                            'relationship':relation,'revision':state['revision']}
            reason = compatible(json.loads(same[0]['identity_json']), incoming)[1] if same else 'No exact catalog identity.'
            return {'status':'incompatible' if same else 'absent','reason':reason,'fields':[]}
        row = accepted[0]
        state = self.state(row['work_id'],con=con)
        latest=self.db.latest_audit(row['work_id'],con=con)
        previous=json.loads(latest['publication_json'] or '{}') if latest else {}
        from mangaanka_search_core.publication_freshness import source_fingerprints
        fingerprints=(source_fingerprints(previous.get('references') or {}) if
                      compatible(previous.get('catalog_identity') or {},incoming)[0] else {})
        return dict(state, work_id=row['work_id'], status='matched',
                    source_fingerprints=fingerprints,
                    fields=[f for f in state['fields'] if f['verification'] in ('REVIEWED','VERIFIED')],
                    draft_count=sum(f['verification']=='UNVERIFIED' for f in state['fields']))

    def audit_guard(self, work_id, con=None):
        if con is None:
            with self.db.con() as c: return self.audit_guard(work_id, c)
        work=con.execute('SELECT work_uuid,canonical_work_id,edition,language FROM works WHERE id=?',(work_id,)).fetchone()
        if not work:return {'work_id':None,'revision':0,'sources':[]}
        state=self.state(work_id,con)
        sources=[]
        for relation in con.execute('''SELECT r.*,w.id source_work_id,w.canonical_work_id,
            COALESCE(cc.revision,0) revision,(SELECT max(id) FROM search_audits WHERE work_id=w.id) audit_id
            FROM edition_structure_relationships r JOIN works w ON w.work_uuid=r.source_work_uuid
            LEFT JOIN curated_catalog cc ON cc.work_id=w.id WHERE r.target_work_uuid=? ORDER BY r.source_work_uuid''',
            (work['work_uuid'],)):
            sources.append(dict(relation))
        return {'work_id':work_id,'work':dict(work),'revision':state['revision'],
                'curated_identity':state['identity'],'sources':sources,
                **({'supplementary_revision':self.db.supplementary.revision(work_id,con)}
                   if self.db.supplementary.revision(work_id,con) else {})}

    def snapshot(self, work_id, audit=None, con=None):
        audit = audit if audit is not None else self.db.latest_audit(work_id,con=con)
        data = json.loads(audit['publication_json'] or '{}') if audit else {}
        return data.get('automatic',data), audit['id'] if audit else None

    def rows(self, work_id, state=None, audit=None, con=None):
        automatic, audit_id = self.snapshot(work_id,audit,con=con)
        historical = audit is not None and state is None
        if historical:
            final = json.loads(audit['publication_json'] or '{}')
            patch = final.get('curated_database') or {}
            state = {'identity':final.get('catalog_identity'), 'fields':patch.get('fields') or [],
                     'revision':final.get('curation_revision',0), 'evidence':patch.get('evidence') or []}
        state = state or self.state(work_id,con=con)
        bound = state['identity']
        incoming = automatic.get('catalog_identity') or {}
        applicable = bool(bound and compatible(bound,incoming)[0])
        fields = {(r['entity'],r['record_key'],r['field']):r for r in state['fields']}
        shared=False
        if not historical and not fields and not bound and hasattr(self.db,'working_sets'):
            relationship=self.lookup(incoming,work_id,con=con)
            if relationship.get('structure_shared'):
                fields={(r['entity'],r['record_key'],r['field']):r for r in relationship['fields']}
                applicable=True;shared=True
        result=[]
        projection = automatic.get('projection') or []
        latest=audit if audit is not None else self.db.latest_audit(work_id,con=con)
        final=json.loads(latest['publication_json'] or '{}') if latest else {}
        final_revision=final.get('curation_revision',final.get('curated_database',{}).get('revision',0))
        final_rows=final.get('projection') or []
        counts=Counter(chapter_key(r) for r in projection)
        conflicts=set(automatic.get('conflicting_chapters') or [])
        for index, original in enumerate(projection):
            if original.get('_unit_kind') == 'volume':
                continue
            key=chapter_key(original)
            auto={'chapter':str(original.get('chapter') or ''), 'title':original.get('title') or '',
                  'volume':original.get('_effective_volume',original.get('volume')), 'type':original.get('type') or 'chapter',
                  'source_note':''}
            edits={field:r for (entity,k,field),r in fields.items() if entity=='chapter' and k==key}
            effective=dict(auto)
            if final.get('automatic') is not None and final_revision==state['revision'] and index<len(final_rows):
                resolved=final_rows[index]
                effective.update(chapter=str(resolved.get('chapter') or ''),title=resolved.get('title') or '',
                                 volume=resolved.get('_effective_volume',resolved.get('volume')),type=resolved.get('type') or 'chapter')
            for field,r in edits.items():
                if applicable and counts[key]==1 and r['verification'] != 'UNVERIFIED':
                    effective[field]=r['value']
            status=[]
            labels=(automatic.get('normalization') or {}).get('labels') or []
            if index<len(labels) and labels[index] in ('unclassified','provisional'):
                status.append('UNCLASSIFIED AUTOMATIC')
            elif index<len(labels) and labels[index].startswith('provider_'):
                status.append('PROVIDER ARTIFACT')
            if counts[key]>1: status.append('DUPLICATE / CONFLICT')
            if key in conflicts and not ('volume' in edits and applicable and edits['volume']['verification']!='UNVERIFIED'):
                status.append('CONFLICT')
            uncompiled = bool(original.get('_publication_state') == 'UNCOMPILED' and
                effective.get('volume') in (None,'') and not any(
                    f in edits and applicable and edits[f]['verification']!='UNVERIFIED'
                    for f in ('volume','chapter','type')))
            if uncompiled: status.append('UNCOMPILED')
            elif effective.get('volume') in (None,''): status.append('UNMAPPED')
            if index<len(labels) and labels[index]=='recognized_special': status.append('RECOGNIZED SPECIAL')
            if edits:
                status.append('SHARED STRUCTURE' if shared else 'CURATED' if applicable else 'INCOMPATIBLE CURATION')
                status.append('/'.join(sorted({r['verification'] for r in edits.values()})))
                if all(r['value']==auto.get(f) for f,r in edits.items()): status.append('AGREES WITH AUTOMATIC')
                elif applicable: status.append('DIFFERS FROM AUTOMATIC')
            result.append({'key':key,'iid':str(index),'automatic':auto,'curated':edits,'effective':effective,
                           'source':original.get('_volume_source') or 'unmapped','status':', '.join(status) or 'AUTOMATIC',
                           'conflict':'CONFLICT' in ','.join(status),'missing':False,'ambiguous':counts[key]>1})
        present={r['key'] for r in result}
        for chapter in automatic.get('manifest',{}).get('chapters',[]):
            key=chapter['key']
            if key not in present:
                auto={'chapter':key,'title':chapter.get('title',{}).get('value') or '',
                      'volume':chapter.get('volume',{}).get('value'),'type':chapter.get('kind') or 'chapter'}
                result.append({'key':key,'iid':'missing:'+key,'automatic':auto,'curated':{},'effective':auto,
                               'source':chapter.get('volume',{}).get('source'),'status':'MISSING ACQUISITION',
                               'conflict':False,'missing':True,'ambiguous':False})
        present={r['key'] for r in result}
        for (entity,key,field),entry in fields.items():
            if entity!='chapter' or field!='exists' or not entry['value'] or key in present:
                continue
            auto={'chapter':key,'title':'','volume':None,'type':'chapter','source_note':''}
            edits={name:r for (e,k,name),r in fields.items() if e=='chapter' and k==key}
            effective=dict(auto)
            if applicable:
                for name,r in edits.items():
                    if name!='exists' and r['verification']!='UNVERIFIED': effective[name]=r['value']
            result.append({'key':key,'iid':'curated:'+key,'automatic':auto,'curated':edits,
                           'effective':effective,'source':'curated_database',
                           'status':'CURATED PUBLICATION / NO ACQUISITION','conflict':False,
                           'missing':True,'ambiguous':False})
        return result

    def preview(self, work_id, changes, operation='Manual edit', verification='REVIEWED', note='', guard=None):
        if verification not in VERIFICATIONS: raise ValueError('Invalid verification state.')
        automatic,audit_id=self.snapshot(work_id)
        state=self.state(work_id)
        if guard:
            from ddk_review import database_revision, audit_revision
            audit=self.db.latest_audit(work_id)
            if (guard.get('database_uuid')!=self.db.database_uuid or not audit or audit['id']!=guard['audit_id'] or
                audit_revision(self.db,audit)!=guard['audit_revision'] or
                database_revision(self.db)!=guard['database_revision']):
                raise ValueError('Stale review packet: audit or database revision changed. Export a fresh packet.')
            if automatic.get('curation_revision',automatic.get('curated_database',{}).get('revision',0))!=state['revision']:
                raise ValueError('Stale review packet: re-audit after the last curated change before using packet commands.')
        binding=state['identity'] or automatic.get('catalog_identity')
        if not binding or not binding.get('trusted'):
            raise ValueError('RERUN REQUIRED: a trusted canonical identity is needed before curation.')
        before={(r['entity'],r['record_key'],r['field']):r for r in state['fields']}
        rows=self.rows(work_id)
        available={r['key']:r for r in rows}
        created={str(c['key']) for c in changes if c['entity']=='chapter' and c['field']=='exists'
                 and not c.get('reset') and c.get('value') is True}
        operations=[]
        seen=set()
        for change in changes:
            entity,key,field=change['entity'],str(change['key']),change['field']
            if entity=='evidence':
                if field!='add' or change.get('reset'):
                    raise ValueError('Evidence command must add one source.')
                target_key=str(change.get('target_key') or '')
                target_field=change.get('target_field','volume')
                if target_field!='volume' or target_key not in available:
                    raise ValueError('Evidence needs an existing chapter-volume assertion.')
                if any(prior['entity']=='chapter' and str(prior['key'])==target_key and
                       prior['field']==target_field and prior.get('reset') for prior in changes):
                    raise ValueError('Evidence cannot target an assertion reset in the same batch.')
                if (('chapter',target_key,target_field) not in before and not any(
                    prior['entity']=='chapter' and str(prior['key'])==target_key and prior['field']==target_field
                    and not prior.get('reset') for prior in changes)):
                    raise ValueError('Set a curated volume before attaching evidence.')
                source=str(change.get('source_name') or '').strip()
                url=str(change.get('source_url') or '').strip()
                if not source or (url and not re.fullmatch(r'https?://\S+',url)):
                    raise ValueError('Evidence requires a source name and a valid optional HTTP(S) URL.')
                accessed=str(change.get('accessed_at') or '')
                if accessed and not re.fullmatch(r'\d{4}-\d{2}-\d{2}',accessed):
                    raise ValueError('Evidence accessed date must use YYYY-MM-DD.')
                evidence_uuid=str(change.get('key') or uuid.uuid4())
                if any(r['evidence_uuid']==evidence_uuid for r in state['evidence']):
                    raise ValueError('Evidence ID already exists.')
                if evidence_uuid in seen:raise ValueError('Duplicate evidence ID in one preview.')
                seen.add(evidence_uuid)
                record={'evidence_uuid':evidence_uuid,'work_id':work_id,'entity':'chapter',
                        'record_key':target_key,'field':target_field,'assertion_revision':state['revision']+1,
                        'source_name':source,'source_url':url,'accessed_at':accessed,
                        'note':str(change.get('note') or ''),
                        'verification':change.get('verification',verification),'created_at':''}
                if record['verification'] not in VERIFICATIONS:raise ValueError('Invalid evidence verification.')
                operations.append({'entity':'evidence','key':evidence_uuid,'field':'add','before':None,
                                   'after':record,'effective_before':None,'effective_after':source})
                continue
            ident=(entity,key,field)
            if ident in seen: raise ValueError('Duplicate field mutation in one preview.')
            seen.add(ident)
            old=before.get(ident)
            if entity=='chapter':
                if field=='exists': numeric(key,'chapter')
                if field=='exists':
                    if change.get('reset'):
                        if not old or not old['value']: raise ValueError('Only curated-created chapters can be removed.')
                    elif key in available:
                        raise ValueError('Cannot create a chapter over source/reference evidence.')
                elif key not in available and key not in created: raise ValueError(f'Unknown chapter: {key}')
                if key in available and available[key]['ambiguous']: raise ValueError(f'Duplicate chapter identity {key}; resolve source ambiguity before editing.')
                if key in available and available[key]['missing'] and not before.get(('chapter',key,'exists')):
                    raise ValueError('Missing acquisition rows are reference evidence, not editable acquisition records.')
            elif entity=='volume':
                numeric(key,'volume')
                if field=='exists':
                    if change.get('reset'):
                        if not old or not old['value']: raise ValueError('Only curated-created volumes can be removed.')
                        if any(str(r['effective'].get('volume'))==key for r in rows):
                            raise ValueError('Remove chapter memberships before removing this curated volume.')
                    elif key in {str(r['effective'].get('volume')) for r in rows}:
                        raise ValueError('Cannot create a volume over existing publication evidence.')
                elif key not in {str(r['effective'].get('volume')) for r in rows} and key not in {
                        k for (e,k,f),r in before.items() if e=='volume' and f=='exists'} and key not in {
                        str(c['key']) for c in changes if c['entity']=='volume' and c['field']=='exists' and not c.get('reset')}:
                    raise ValueError('Create volume membership by assigning chapters first.')
            elif entity!='work' or key!='work': raise ValueError('Invalid record scope.')
            if change.get('reset'):
                new=None
            else:
                value=checked_value(entity,field,change['value'])
                selected_verification=change.get('verification',verification)
                if selected_verification not in VERIFICATIONS: raise ValueError('Invalid verification state.')
                source_name=str(change.get('source_name',old.get('source_name','') if old else ''))
                source_url=str(change.get('source_url',old.get('source_url','') if old else ''))
                accessed_at=str(change.get('accessed_at',old.get('accessed_at','') if old else ''))
                if source_url and not re.fullmatch(r'https?://\S+',source_url):
                    raise ValueError('Evidence URL must use http:// or https://.')
                if accessed_at and not re.fullmatch(r'\d{4}-\d{2}-\d{2}',accessed_at):
                    raise ValueError('Evidence accessed date must use YYYY-MM-DD.')
                if (source_url or accessed_at) and not source_name:
                    raise ValueError('Evidence source name is required when URL/date is set.')
                new={'work_id':work_id,'entity':entity,'record_key':key,'field':field,
                     'value':value,'verification':selected_verification,'note':str(note) if note else (old['note'] if old else ''),
                     'source_name':source_name,'source_url':source_url,'accessed_at':accessed_at}
            if old!=new:
                prior=(available[key]['effective'].get(field) if entity=='chapter' and key in available else (old['value'] if old else None))
                following=(available[key]['automatic'].get(field) if entity=='chapter' and key in available and new is None
                           else new['value'] if new else None)
                operations.append({'entity':entity,'key':key,'field':field,'before':old,'after':new,
                                   'effective_before':prior,'effective_after':following})
        if not operations: raise ValueError('No changes to apply.')
        if any(o['field']=='chapter' for o in operations) and len({o['key'] for o in operations})>1:
            raise ValueError('Chapter-number changes are single-record only.')
        candidate=deepcopy(state)
        merged=dict(before)
        identity=deepcopy(binding)
        for op in operations:
            if op['entity']=='evidence':continue
            ident=(op['entity'],op['key'],op['field'])
            if op['after'] is None: merged.pop(ident,None)
            else: merged[ident]=op['after']
        for op in operations:
            if op['entity']=='evidence':continue
            if op['field']=='exists' and op['after'] is None and any(
                    entity==op['entity'] and key==op['key'] for entity,key,field in merged):
                raise ValueError('Reset all curated record fields before removing its existence marker.')
        # Identity changes rebind this title's curation explicitly; no other work is changed.
        for field in ('canonical_work_id','edition','language','publication_context','external_ids'):
            entry=merged.get(('work','work',field))
            if entry and entry['verification']!='UNVERIFIED': identity[field]=entry['value']
        candidate.update(identity=identity,fields=list(merged.values()))
        validation=self.validate(work_id,candidate)
        if validation['errors']: raise ValueError('\n'.join(validation['errors']))
        return {'database_uuid':self.db.database_uuid,'work_id':work_id,'audit_id':audit_id,'revision':state['revision'],'operation':operation,
                'changes':operations,'identity_before':state['identity'],'identity_after':identity,
                'validation':validation,'guard':guard,
                'high_impact':any(o['entity']=='work' or o['field'] in ('chapter','exists') for o in operations)}

    def _backup(self, force=False):
        if self.backed_up and not force: return
        folder=self.db.path.parent/'backups'
        folder.mkdir(exist_ok=True)
        path=folder/('mangaanka_catalog_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.db')
        with self.db.con() as source:
            target=sqlite3.connect(path)
            try: source.backup(target)
            finally: target.close()
        self.backed_up=True
        return path

    @staticmethod
    def _write(c, work_id, op, side):
        row=op[side]
        if op['entity']=='evidence':
            if row is None:
                c.execute('DELETE FROM curated_evidence WHERE evidence_uuid=? AND work_id=?',(op['key'],work_id))
            else:
                c.execute('''INSERT OR REPLACE INTO curated_evidence(
                    evidence_uuid,work_id,entity,record_key,field,assertion_revision,source_name,
                    source_url,accessed_at,note,verification,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',
                    tuple(row[k] for k in ('evidence_uuid','work_id','entity','record_key','field',
                        'assertion_revision','source_name','source_url','accessed_at','note','verification','created_at')))
            return
        c.execute('DELETE FROM curated_fields WHERE work_id=? AND entity=? AND record_key=? AND field=?',
                  (work_id,op['entity'],op['key'],op['field']))
        if row is not None:
            c.execute('''INSERT INTO curated_fields(work_id,entity,record_key,field,value_json,verification,
                note,source_name,source_url,accessed_at) VALUES(?,?,?,?,?,?,?,?,?,?)''',
                      (work_id,op['entity'],op['key'],op['field'],dumps(row['value']),row['verification'],row['note'],
                       row.get('source_name',''),row.get('source_url',''),row.get('accessed_at','')))

    def apply(self, preview):
        if preview.get('database_uuid')!=self.db.database_uuid:
            raise ValueError('Preview belongs to another database; preview again in the active database.')
        work_id=preview['work_id']
        with self.db.lock:
            self._backup()
            with self.db.con() as c:
                c.execute('BEGIN IMMEDIATE')
                if preview.get('working_set_item_uuid'):
                    self.db.working_sets.editable_item(preview['working_set_item_uuid'],work_id,con=c)
                state=self.state(work_id,c)
                latest=c.execute('SELECT max(id) FROM search_audits WHERE work_id=?',(work_id,)).fetchone()[0]
                if state['revision']!=preview['revision'] or latest!=preview['audit_id']:
                    raise ValueError('Stale preview: data changed. Preview again.')
                if preview.get('guard'):
                    from ddk_review import database_revision
                    if (preview['guard'].get('database_uuid')!=self.db.database_uuid or
                        database_revision(self.db,c)!=preview['guard']['database_revision']):
                        raise ValueError('Stale review packet: database revision changed before Apply.')
                revision=state['revision']+1
                for op in preview['changes']:
                    if op['entity']=='evidence' and op['after']:
                        if not op['after']['accessed_at']:
                            op['after']['accessed_at']=datetime.now(timezone.utc).date().isoformat()
                        if not op['after']['created_at']:op['after']['created_at']=stamp()
                c.execute('INSERT OR REPLACE INTO curated_catalog VALUES(?,?,?)',
                          (work_id,dumps(preview['identity_after']),revision))
                for op in preview['changes']: self._write(c,work_id,op,'after')
                persisted=self.state(work_id,c)
                actual={(r['entity'],r['record_key'],r['field']):r for r in persisted['fields']}
                for op in preview['changes']:
                    observed=(next((r for r in persisted['evidence'] if r['evidence_uuid']==op['key']),None)
                              if op['entity']=='evidence' else actual.get((op['entity'],op['key'],op['field'])))
                    if observed!=op['after']:
                        raise ValueError('Post-write field validation failed; transaction rolled back.')
                if persisted['identity']!=preview['identity_after']:
                    raise ValueError('Post-write identity validation failed; transaction rolled back.')
                checked=self.validate(work_id,persisted,con=c)
                if checked['errors']:
                    raise ValueError('Post-write effective validation failed; transaction rolled back: '+
                                     '; '.join(checked['errors']))
                if c.execute('PRAGMA foreign_key_check').fetchone() or c.execute('PRAGMA quick_check').fetchone()[0]!='ok':
                    raise ValueError('Database integrity validation failed; transaction rolled back.')
                c.execute("UPDATE curated_changes SET state='superseded' WHERE work_id=? AND state='reverted'",(work_id,))
                cur=c.execute('''INSERT INTO curated_changes(work_id,timestamp,operation,changes_json,identity_before,identity_after,revision)
                                 VALUES(?,?,?,?,?,?,?)''', (work_id,stamp(),preview['operation'],dumps(preview['changes']),
                                 dumps(preview['identity_before']),dumps(preview['identity_after']),revision))
                c.execute('INSERT INTO curated_events(change_id,timestamp,action) VALUES(?,?,?)',(cur.lastrowid,stamp(),'apply'))
        if hasattr(self.db,'acceptance'):self.db.acceptance.recalculate(work_id)
        return self.validate(work_id)

    def history(self, work_id=None):
        with self.db.con() as c:
            return [dict(r) for r in c.execute('''SELECT h.*,w.input_title FROM curated_changes h
                JOIN works w ON w.id=h.work_id '''+('WHERE h.work_id=? ' if work_id else '')+'ORDER BY h.id DESC',
                (work_id,) if work_id else ())]

    def reverse(self, work_id, redo=False, change_id=None, expected_revision=None, expected_audit_id=None, item_uuid=None):
        """Persistent per-title LIFO undo/redo; reject stale historical reverts."""
        with self.db.lock:
            self._backup()
            with self.db.con() as c:
                c.execute('BEGIN IMMEDIATE')
                if item_uuid:self.db.working_sets.editable_item(item_uuid,work_id,con=c)
                row=c.execute("SELECT * FROM curated_changes WHERE work_id=? AND state=? ORDER BY id "+
                              ('ASC' if redo else 'DESC')+' LIMIT 1',(work_id,'reverted' if redo else 'active')).fetchone()
                if not row: raise ValueError('Nothing to redo.' if redo else 'Nothing to undo.')
                if change_id and row['id']!=change_id: raise ValueError('Revert newer active changes for this title first.')
                state=self.state(work_id,c)
                if expected_revision is not None and state['revision']!=expected_revision:
                    raise ValueError('Stale undo/redo preview.')
                if expected_audit_id is not None:
                    latest=c.execute('SELECT max(id) FROM search_audits WHERE work_id=?',(work_id,)).fetchone()[0]
                    if latest!=expected_audit_id: raise ValueError('Stale undo/redo preview: audit changed.')
                current={(r['entity'],r['record_key'],r['field']):r for r in state['fields']}
                current.update({('evidence',r['evidence_uuid'],'add'):r for r in state['evidence']})
                changes=json.loads(row['changes_json'])
                expected,side=('before','after') if redo else ('after','before')
                for op in changes:
                    if current.get((op['entity'],op['key'],op['field']))!=op[expected]:
                        raise ValueError('History conflict: curated state differs from the journal.')
                for op in changes: self._write(c,work_id,op,side)
                identity=json.loads(row['identity_after'] if redo else row['identity_before'])
                # Keep the original binding after the first undo, but increment revision.
                c.execute('UPDATE curated_catalog SET identity_json=?,revision=revision+1 WHERE work_id=?',
                          (dumps(identity or json.loads(row['identity_after'])),work_id))
                c.execute('UPDATE curated_changes SET state=? WHERE id=?',('active' if redo else 'reverted',row['id']))
                c.execute('INSERT INTO curated_events(change_id,timestamp,action) VALUES(?,?,?)',
                          (row['id'],stamp(),'redo' if redo else 'undo'))
        if hasattr(self.db,'acceptance'):self.db.acceptance.recalculate(work_id)
        return self.validate(work_id)

    def validate(self, work_id, state=None, audit=None, con=None):
        # Cache spill during a large write can hold an exclusive SQLite lock.
        # Nested reads must use the caller's transaction connection.
        state=state or self.state(work_id,con=con)
        rows=self.rows(work_id,state,audit,con=con)
        automatic,_=self.snapshot(work_id,audit,con=con)
        labels=(automatic.get('normalization') or {}).get('labels') or []
        def logical(row):
            if row['missing']:return False
            if 'exists' in row['curated']:return True
            try:index=int(row['iid'])
            except (TypeError,ValueError):return False
            return not labels or (index<len(labels) and labels[index] in ('main','special','recognized_special','provisional'))
        canonical_rows=[row for row in rows if logical(row)]
        errors=[]; warnings=[]
        keys=[]
        for row in canonical_rows:
            value=row['effective']; number=normalize_chapter_number(value.get('chapter'))
            if number is None and value.get('type') not in ('bonus','extra','omake','special','prologue','epilogue'):
                warnings.append(f"Chapter {value.get('chapter')!r} is nonnumeric; classify a special explicitly.")
            if number is not None: keys.append(number)
            if value.get('volume') is not None:
                try: numeric(value['volume'],'volume')
                except ValueError as exc: errors.append(str(exc))
        duplicates=[key for key,count in Counter(keys).items() if count>1]
        # Existing source duplicates are warnings; a curated rename creating one is rejected.
        if duplicates:
            message='Duplicate chapter identities: '+', '.join(duplicates)
            (errors if any(r['field']=='chapter' for r in state['fields']) else warnings).append(message)
        if state['identity']:
            ok,reason=compatible(state['identity'],automatic.get('catalog_identity') or {})
            if not ok: warnings.append(reason+' Re-audit required.')
        for row in state['fields']:
            try: checked_value(row['entity'],row['field'],row['value'])
            except ValueError as exc: errors.append(str(exc))
        identity=state.get('identity') or {}
        canonical=identity.get('canonical_work_id','')
        if ':' in canonical:
            source,number=canonical.split(':',1)
            identifier=identity.get('external_ids',{}).get(source)
            if identifier and identifier!=number: errors.append('Canonical work ID contradicts curated external IDs.')
        available={r['key'] for r in rows}
        orphans={r['record_key'] for r in state['fields'] if r['entity']=='chapter' and r['record_key'] not in available}
        if orphans: warnings.append('Overrides have no current record: '+', '.join(sorted(orphans)))
        unmapped=[r['key'] for r in canonical_rows if r['effective'].get('volume') in (None,'') and 'UNCOMPILED' not in r['status']]
        conflicts=[r['key'] for r in canonical_rows if r['conflict']]
        unclassified=[r['key'] for r in rows if not r['missing'] and not logical(r)]
        if unmapped: warnings.append(f'{len(unmapped)} logical publication chapters remain unmapped.')
        if unclassified:warnings.append(f'{len(unclassified)} unclassified acquisition records remain separate.')
        if conflicts: warnings.append(f'{len(conflicts)} unresolved conflicting rows.')
        if any(r['missing'] for r in rows): warnings.append('Reference chapters lack acquisition; curation cannot create pages.')
        return {'valid':not errors,'errors':list(dict.fromkeys(errors)),'warnings':list(dict.fromkeys(warnings)),
                'unmapped':unmapped,'unclassified_acquisition':unclassified,
                'conflicts':conflicts,'reaudit_required':bool(state['fields'])}

    def export(self, work_id, path=None):
        state=self.state(work_id)
        if not state['identity']: raise ValueError('No curated catalog record to export.')
        validation=self.validate(work_id)
        if validation['errors']: raise ValueError('Validation errors block export.')
        trusted=[r for r in state['fields'] if r['verification'] in ('REVIEWED','VERIFIED')]
        if not trusted: raise ValueError('No reviewed or verified overrides to export.')
        payload={'format':'mangaanka-curated-patch','version':2,'database_uuid':self.db.database_uuid,
                 'database_path':str(self.db.path),'identity':state['identity'],
                 'revision':state['revision'],'fields':[{k:v for k,v in r.items() if k!='work_id'} for r in trusted],
                 'evidence':[{k:v for k,v in r.items() if k!='work_id'} for r in state['evidence']]}
        if path is None:
            folder=self.db.path.parent/'exports'/'curated-patches';folder.mkdir(parents=True,exist_ok=True)
            work=self.db.work(work_id)
            slug=re.sub(r'[^a-z0-9]+','-',work['input_title'].lower()).strip('-') or 'title'
            identity=state['identity']
            suffix=re.sub(r'[^a-zA-Z0-9_-]','-',identity['edition']+'-'+identity['language'])
            path=folder/f'{slug}-{suffix}-{work_id}.json'
        Path(path).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        return Path(path)
