"""Persistent intake batches, explicit catalog acceptance and edition relationships."""
import json
import re
import uuid
from contextlib import nullcontext
from datetime import datetime, timezone


SCHEMA = '''
CREATE UNIQUE INDEX IF NOT EXISTS works_uuid_idx ON works(work_uuid);
CREATE INDEX IF NOT EXISTS works_conceptual_idx ON works(conceptual_work_uuid,edition,language);
CREATE INDEX IF NOT EXISTS works_lifecycle_idx ON works(lifecycle_status,id);
CREATE INDEX IF NOT EXISTS works_canonical_claim_idx ON works(canonical_work_id,edition,language);
CREATE INDEX IF NOT EXISTS works_external_ids_idx ON works(anilist_id,mal_id,mangadex_id);
CREATE TABLE IF NOT EXISTS working_sets(
 working_set_uuid TEXT PRIMARY KEY,
 database_uuid TEXT NOT NULL,
 name TEXT NOT NULL,
 description TEXT NOT NULL DEFAULT '',
 status TEXT NOT NULL DEFAULT 'OPEN',
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 created_with_ddk_version TEXT NOT NULL,
 created_with_search_core_version TEXT NOT NULL,
 schema_version INTEGER NOT NULL,
 default_language TEXT NOT NULL DEFAULT 'en',
 default_workflow TEXT NOT NULL DEFAULT 'volume'
);
CREATE INDEX IF NOT EXISTS working_sets_status_idx ON working_sets(status,updated_at);
CREATE TABLE IF NOT EXISTS working_set_items(
 working_set_item_uuid TEXT PRIMARY KEY,
 working_set_uuid TEXT NOT NULL REFERENCES working_sets(working_set_uuid) ON DELETE CASCADE,
 request_key TEXT NOT NULL,
 original_query TEXT NOT NULL,
 requested_edition TEXT NOT NULL,
 requested_language TEXT NOT NULL,
 requested_workflow TEXT NOT NULL,
 processing_status TEXT NOT NULL DEFAULT 'PENDING',
 linked_work_uuid TEXT REFERENCES works(work_uuid) ON DELETE SET NULL,
 pinned_audit_id INTEGER REFERENCES search_audits(id) ON DELETE SET NULL,
 pinned_audit_revision INTEGER,
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 removed_at TEXT,
 UNIQUE(working_set_uuid,request_key)
);
CREATE INDEX IF NOT EXISTS working_set_items_status_idx ON working_set_items(working_set_uuid,processing_status);
CREATE INDEX IF NOT EXISTS working_set_items_work_idx ON working_set_items(linked_work_uuid);
CREATE INDEX IF NOT EXISTS working_set_items_audit_idx ON working_set_items(pinned_audit_id);
CREATE TABLE IF NOT EXISTS working_set_observations(
 id INTEGER PRIMARY KEY,
 working_set_item_uuid TEXT NOT NULL REFERENCES working_set_items(working_set_item_uuid) ON DELETE CASCADE,
 created_at TEXT NOT NULL,
 record_json TEXT NOT NULL,
 holes_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS working_set_observations_item_idx ON working_set_observations(working_set_item_uuid,id DESC);
CREATE TABLE IF NOT EXISTS edition_structure_relationships(
 source_work_uuid TEXT NOT NULL REFERENCES works(work_uuid),
 target_work_uuid TEXT NOT NULL REFERENCES works(work_uuid),
 status TEXT NOT NULL CHECK(status IN ('REVIEWED','VERIFIED')),
 source_note TEXT NOT NULL,
 created_at TEXT NOT NULL,
 source_context TEXT NOT NULL DEFAULT '',
 target_context TEXT NOT NULL DEFAULT '',
 PRIMARY KEY(source_work_uuid,target_work_uuid),
 CHECK(source_work_uuid<>target_work_uuid)
);
CREATE INDEX IF NOT EXISTS edition_structure_target_idx ON edition_structure_relationships(target_work_uuid,status);
'''


def stamp():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


class IntakeIdentityReview(ValueError):
    """Trusted intake identity needs human resolution before a catalog audit can be saved."""

class AuditSuperseded(ValueError):
    """An effective catalog dependency changed while the audit was running."""

class DuplicateIntake(Exception):
    """Exact identity already belongs to a primary membership in this set."""


def request_key(query,edition,language,workflow):
    return '\x1f'.join((str(query).strip().casefold(),str(edition),str(language),str(workflow)))


EDITIONS=('standard','official_color','fan_color','omnibus','deluxe','bunkobon','kanzenban')


def validate_context(edition,language,workflow):
    if edition not in EDITIONS:raise ValueError('Choose an exact supported edition.')
    if not re.fullmatch(r'[a-z]{2,3}(?:-[A-Za-z0-9]+)?',language or ''):
        raise ValueError('Choose a valid requested language.')
    if workflow not in ('volume','chapter'):raise ValueError('Choose a valid workflow.')


class WorkingSets:
    def __init__(self,db):
        self.db=db

    @staticmethod
    def event(con, operation, details):
        con.execute('INSERT INTO database_events(timestamp,origin,description,details_json) VALUES(?,?,?,?)',
                    (stamp(),operation,operation.replace('_',' ').title(),json.dumps(details,ensure_ascii=False,default=str)))

    def guard(self,set_uuid=None,item_uuid=None,membership=False,con=None):
        if con is None:
            with self.db.con() as c:return self.guard(set_uuid,item_uuid,membership,c)
        item=self.item(item_uuid,con=con) if item_uuid else None
        if item_uuid and (not item or item['removed_at']):raise ValueError('Working Set item is missing or removed.')
        set_uuid=item['working_set_uuid'] if item else set_uuid
        current=con.execute('''SELECT * FROM working_sets WHERE working_set_uuid=? AND database_uuid=
            (SELECT database_uuid FROM database_meta WHERE singleton=1)''',(set_uuid,)).fetchone()
        if not current:raise ValueError('Working Set does not belong to the active database.')
        if current['status'] not in ('OPEN','REVIEW'):
            raise ValueError('Complete/archived Working Set is protected; Reopen for Review first.')
        if membership and current['status']!='OPEN':raise ValueError('Move the Working Set to OPEN before changing intake membership.')
        return item if item else dict(current)

    def active_uuid(self):
        with self.db.con() as c:
            return c.execute('SELECT active_working_set_uuid FROM database_meta WHERE singleton=1').fetchone()[0]

    def set_active(self,set_uuid):
        with self.db.lock,self.db.con() as c:
            if set_uuid and not c.execute('SELECT 1 FROM working_sets WHERE working_set_uuid=? AND database_uuid=?',
                                          (set_uuid,self.db.database_uuid)).fetchone():
                raise ValueError('Working Set does not belong to the active database.')
            c.execute('UPDATE database_meta SET active_working_set_uuid=? WHERE singleton=1',(set_uuid,))

    def create(self,name,description='',language='en',workflow='volume'):
        name=str(name or '').strip()
        if not name:raise ValueError('Working Set needs a name.')
        validate_context('standard',language,workflow)
        from mangaanka_database_development_kit import VERSION,SEARCH_CORE_VERSION,SCHEMA_VERSION
        set_uuid=str(uuid.uuid4());date=stamp()
        with self.db.lock,self.db.con() as c:
            c.execute('INSERT INTO working_sets VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                      (set_uuid,self.db.database_uuid,name,str(description or ''),'OPEN',date,date,
                      VERSION,SEARCH_CORE_VERSION,SCHEMA_VERSION,language,workflow))
        return set_uuid

    def get(self,set_uuid,con=None):
        if not set_uuid:return None
        with (self.db.con() if con is None else nullcontext(con)) as c:
            row=c.execute('SELECT * FROM working_sets WHERE working_set_uuid=? AND database_uuid=?',
                          (set_uuid,self.db.database_uuid)).fetchone()
            return dict(row) if row else None

    def list(self):
        with self.db.con() as c:
            return [dict(r) for r in c.execute('SELECT * FROM working_sets WHERE database_uuid=? ORDER BY created_at DESC',
                                               (self.db.database_uuid,))]

    def add_requests(self,set_uuid,queries,edition='standard',language=None,workflow=None):
        current=self.get(set_uuid)
        if not current:raise ValueError('Select an active Working Set first.')
        self.guard(set_uuid=set_uuid,membership=True)
        language=language or current['default_language'];workflow=workflow or current['default_workflow']
        validate_context(edition,language,workflow)
        original=[str(q or '').strip() for q in queries if str(q or '').strip()]
        unique={}
        for query in original:unique.setdefault(request_key(query,edition,language,workflow),query)
        added=0;restored=0;date=stamp()
        if unique:self.db.catalog._backup()
        with self.db.lock,self.db.con() as c:
            c.execute('BEGIN IMMEDIATE')
            self.guard(set_uuid=set_uuid,membership=True,con=c)
            for key,query in unique.items():
                old=c.execute('''SELECT removed_at FROM working_set_items WHERE working_set_uuid=? AND request_key=?''',
                              (set_uuid,key)).fetchone()
                if old:
                    if old['removed_at']:
                        c.execute('''UPDATE working_set_items SET removed_at=NULL,processing_status='PENDING',
                            updated_at=? WHERE working_set_uuid=? AND request_key=?''',(date,set_uuid,key))
                        restored+=1
                    continue
                added+=c.execute('''INSERT OR IGNORE INTO working_set_items(
                    working_set_item_uuid,working_set_uuid,request_key,original_query,requested_edition,
                    requested_language,requested_workflow,processing_status,created_at,updated_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?)''',
                    (str(uuid.uuid4()),set_uuid,key,query,edition,language,workflow,'PENDING',date,date)).rowcount
            if added or restored:c.execute('UPDATE working_sets SET updated_at=? WHERE working_set_uuid=?',(date,set_uuid))
        return {'input_lines':len(original),'unique_requests':len(unique),'new_items':added,
                'restored_items':restored,'already_in_set':len(unique)-added-restored,
                'duplicate_input_lines':len(original)-len(unique)}

    def items(self,set_uuid,include_removed=False,con=None):
        with (self.db.con() if con is None else nullcontext(con)) as c:
            if not self.get(set_uuid,con=c):return []
            return [dict(r) for r in c.execute('''SELECT i.*,w.id work_id,w.lifecycle_status,
                w.canonical_work_id,w.canonical_title FROM working_set_items i
                LEFT JOIN works w ON w.work_uuid=i.linked_work_uuid
                WHERE i.working_set_uuid=? '''+('' if include_removed else 'AND i.removed_at IS NULL ')+
                'ORDER BY i.created_at,i.rowid',(set_uuid,))]

    def item(self,item_uuid,con=None):
        with (self.db.con() if con is None else nullcontext(con)) as c:
            row=c.execute('''SELECT i.*,w.id work_id FROM working_set_items i
                LEFT JOIN works w ON w.work_uuid=i.linked_work_uuid
                WHERE i.working_set_item_uuid=?''',(item_uuid,)).fetchone()
            return dict(row) if row else None

    def latest_observation(self,item_uuid,con=None):
        with (self.db.con() if con is None else nullcontext(con)) as c:
            row=c.execute('''SELECT * FROM working_set_observations WHERE working_set_item_uuid=?
                ORDER BY id DESC LIMIT 1''',(item_uuid,)).fetchone()
        if not row:return None
        result=dict(row)
        result['record']=json.loads(result.pop('record_json'))
        result['holes']=json.loads(result.pop('holes_json'))
        return result

    def audit_errors(self,set_uuid=None):
        """Current execution failures, separate from persisted audit_holes."""
        sets=[self.get(set_uuid)] if set_uuid else self.list()
        failures=[]
        for working_set in sets:
            if not working_set:continue
            for item in self.items(working_set['working_set_uuid']):
                if item['processing_status']!='ERROR':continue
                observation=self.latest_observation(item['working_set_item_uuid'])
                for hole in (observation or {}).get('holes') or ():
                    if hole.get('code')=='AUDIT_ERROR' and hole.get('severity')=='error':
                        failures.append({'working_set':working_set,'item':item,
                                         'observation':observation,'hole':hole})
        return failures

    def set_item_status(self,item_uuid,status):
        if status not in ('PENDING','QUEUED','AUDITING','AUDITED','REVIEW','READY','ACCEPTED','REJECTED','ERROR','DUPLICATE'):
            raise ValueError('Invalid Working Set item status.')
        with self.db.lock,self.db.con() as c:
            c.execute('BEGIN IMMEDIATE')
            item=self.guard(item_uuid=item_uuid,con=c)
            if status in ('READY','ACCEPTED','DUPLICATE'):
                raise ValueError('Use eligibility, explicit acceptance, or duplicate resolution to set this status.')
            if item['processing_status'] in ('ACCEPTED','REJECTED','DUPLICATE') and status!=item['processing_status']:
                raise ValueError('Reopen the terminal item for review before changing it.')
            c.execute('UPDATE working_set_items SET processing_status=?,updated_at=? WHERE working_set_item_uuid=?',
                      (status,stamp(),item_uuid))

    def editable_item(self,item_uuid,work_id=None,con=None):
        item=self.guard(item_uuid=item_uuid,con=con)
        if item['processing_status'] in ('ACCEPTED','REJECTED','DUPLICATE'):
            raise ValueError('Reopen the terminal item for review before editing or auditing.')
        if work_id is not None and item['work_id']!=work_id:
            raise ValueError('Working Set item does not own this catalog work.')
        return item

    def resolve_work(self,item,identity,con=None):
        """Link only on trusted canonical identity, never on query text alone."""
        if item['work_id']:
            with (self.db.con() if con is None else nullcontext(con)) as c:
                linked=c.execute('SELECT canonical_work_id,edition,language FROM works WHERE id=?',
                                 (item['work_id'],)).fetchone()
            if (not linked or not identity.get('trusted') or not identity.get('canonical_work_id') or
                linked['canonical_work_id']!=identity.get('canonical_work_id') or
                linked['edition']!=identity.get('edition') or
                linked['language']!=identity.get('language')):
                raise ValueError('Linked catalog work conflicts with the new trusted edition identity.')
            return item['work_id']
        if not identity.get('trusted') or not identity.get('canonical_work_id'):
            return None
        if identity.get('edition')!=item['requested_edition'] or identity.get('language')!=item['requested_language']:
            return None
        with (self.db.con() if con is None else nullcontext(con)) as c:
            rows=c.execute('''SELECT id FROM works WHERE canonical_work_id=? AND edition=? AND language=?''',
                           (identity['canonical_work_id'],item['requested_edition'],item['requested_language'])).fetchall()
        if len(rows)>1:raise ValueError('Canonical identity matches multiple works; human relink is required.')
        return rows[0][0] if rows else None

    def create_work(self,item,identity,con=None):
        if not identity.get('trusted') or not identity.get('canonical_work_id') or \
                identity.get('edition')!=item['requested_edition'] or \
                identity.get('language')!=item['requested_language']:
            raise ValueError('A trusted edition/language identity is required to create a catalog candidate.')
        date=stamp()
        with self.db.lock,(self.db.con() if con is None else nullcontext(con)) as c:
            if con is None:c.execute('BEGIN IMMEDIATE')
            item=self.editable_item(item['working_set_item_uuid'],con=c)
            if identity.get('edition')!=item['requested_edition'] or identity.get('language')!=item['requested_language']:
                raise ValueError('Trusted identity differs from the current intake context.')
            matches=c.execute('SELECT id FROM works WHERE canonical_work_id=? AND edition=? AND language=?',
                              (identity['canonical_work_id'],item['requested_edition'],item['requested_language'])).fetchall()
            if len(matches)>1:raise ValueError('Multiple canonical works require human review.')
            if matches:return matches[0]['id']
            row=c.execute('''INSERT INTO works(input_title,edition,language,work_uuid,canonical_work_id,
                conceptual_work_uuid,lifecycle_status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)''',
                (item['original_query'],item['requested_edition'],item['requested_language'],
                 str(uuid.uuid4()),identity['canonical_work_id'],None,'STAGED',date,date))
            work_uuid=c.execute('SELECT work_uuid FROM works WHERE id=?',(row.lastrowid,)).fetchone()[0]
            c.execute('INSERT INTO conceptual_works VALUES(?,?)',(work_uuid,date))
            c.execute('UPDATE works SET conceptual_work_uuid=? WHERE id=?',(work_uuid,row.lastrowid))
            return row.lastrowid

    def persist_item_audit(self,item_uuid,identity,record,holes):
        """Resolve, append the audit, link and pin as one per-item transaction."""
        with self.db.lock,self.db.con() as c:
            c.execute('BEGIN IMMEDIATE')
            item=self.editable_item(item_uuid,con=c)
            try:
                if self.mark_duplicate_if_known(item_uuid,identity,con=c):return ('DUPLICATE',None)
                target=self.resolve_work(item,identity,con=c)
                if target is None and identity.get('trusted') and \
                        identity.get('edition')==item['requested_edition'] and \
                        identity.get('language')==item['requested_language']:
                    target=self.create_work(item,identity,con=c)
            except ValueError as exc:
                raise IntakeIdentityReview(str(exc)) from exc
            if target is None:return None
            captured=record.get('catalog_guard')
            current_guard=self.db.catalog.audit_guard(target,con=c)
            if captured and captured!=current_guard and not (
                    captured.get('work_id') is None and current_guard['revision']==0 and not current_guard['sources']):
                raise AuditSuperseded('Curation/structure changed while auditing; fresh audit queued.')
            if record['publication'].get('curation_revision',0)!=current_guard['revision']:
                raise AuditSuperseded('Audit used an older curation revision; fresh audit queued.')
            if captured and captured.get('work_id') is None:record['catalog_guard']=current_guard
            audit_id=self.db.save_audit(target,record,holes,con=c)
            self.pin(item_uuid,target,audit_id,con=c)
            return target,audit_id

    def observe_unresolved(self,item_uuid,record,holes,status='REVIEW'):
        if status not in ('REVIEW','ERROR'):raise ValueError('Invalid intake observation status.')
        with self.db.lock,self.db.con() as c:
            c.execute('BEGIN IMMEDIATE')
            self.editable_item(item_uuid,con=c)
            c.execute('''INSERT INTO working_set_observations(working_set_item_uuid,created_at,record_json,holes_json)
                VALUES(?,?,?,?)''',(item_uuid,stamp(),json.dumps(record,ensure_ascii=False,default=str),
                                    json.dumps(holes,ensure_ascii=False,default=str)))
            c.execute('UPDATE working_set_items SET processing_status=?,updated_at=? WHERE working_set_item_uuid=?',
                      (status,stamp(),item_uuid))

    def pin(self,item_uuid,work_id,audit_id,ready=False,con=None):
        with self.db.lock,(self.db.con() if con is None else nullcontext(con)) as c:
            if con is None:c.execute('BEGIN IMMEDIATE')
            item=self.editable_item(item_uuid,con=c)
            work=c.execute('SELECT * FROM works WHERE id=?',(work_id,)).fetchone()
            audit=c.execute('SELECT id,audit_revision FROM search_audits WHERE work_id=? ORDER BY id DESC LIMIT 1',
                            (work_id,)).fetchone()
            if not item or not work or item['removed_at'] or item['requested_edition']!=work['edition'] or \
                    item['requested_language']!=work['language']:
                raise ValueError('Pinned work must match the active intake edition and language.')
            if item['linked_work_uuid'] and item['linked_work_uuid']!=work['work_uuid']:
                raise ValueError('Cannot replace an existing membership with a different catalog work.')
            current=c.execute('SELECT status FROM working_sets WHERE working_set_uuid=?',
                              (item['working_set_uuid'],)).fetchone()
            if not current or current['status'] not in ('OPEN','REVIEW'):
                raise ValueError('Complete or archived Working Sets cannot pin a new audit.')
            if not audit or audit['id']!=audit_id:raise ValueError('Cannot pin a different work or audit.')
            c.execute('''UPDATE working_set_items SET linked_work_uuid=?,pinned_audit_id=?,
                pinned_audit_revision=?,processing_status=?,updated_at=? WHERE working_set_item_uuid=?''',
                (work['work_uuid'],audit_id,audit['audit_revision'],'REVIEW',stamp(),item_uuid))
            evaluated=self.db.acceptance.evaluate(work_id,item_uuid,con=c)
            fatal=c.execute('SELECT final_state FROM search_audits WHERE id=?',(audit_id,)).fetchone()[0]=='ERROR'
            c.execute('UPDATE working_set_items SET processing_status=? WHERE working_set_item_uuid=?',
                      ('ERROR' if fatal else 'READY' if evaluated['eligible'] else 'REVIEW',item_uuid))

    def remove_item(self,item_uuid):
        self.db.catalog._backup()
        with self.db.lock,self.db.con() as c:
            c.execute('BEGIN IMMEDIATE')
            self.guard(item_uuid=item_uuid,membership=True,con=c)
            c.execute('UPDATE working_set_items SET removed_at=?,updated_at=? WHERE working_set_item_uuid=?',
                      (stamp(),stamp(),item_uuid))

    def set_status(self,set_uuid,status):
        if status not in ('OPEN','REVIEW','COMPLETE','ARCHIVED'):raise ValueError('Invalid Working Set status.')
        self.db.catalog._backup()
        with self.db.lock,self.db.con() as c:
            c.execute('BEGIN IMMEDIATE')
            current=c.execute('SELECT * FROM working_sets WHERE working_set_uuid=?',(set_uuid,)).fetchone()
            if not current:raise ValueError('Unknown Working Set.')
            if current['status'] in ('COMPLETE','ARCHIVED') and status!=current['status']:
                if not (current['status']=='COMPLETE' and status=='ARCHIVED'):
                    raise ValueError('Use Reopen for Review to unlock a protected Working Set.')
            if status=='COMPLETE':
                rows=c.execute('SELECT processing_status FROM working_set_items WHERE working_set_uuid=? AND removed_at IS NULL',(set_uuid,)).fetchall()
                unresolved=[r[0] for r in rows if r[0] not in ('ACCEPTED','REJECTED','DUPLICATE')]
                if not rows or unresolved:
                    from collections import Counter
                    raise ValueError('Complete requires at least one item and terminal decisions for every item: '+str(dict(Counter(unresolved))))
            if status!=current['status']:
                c.execute('UPDATE working_sets SET status=?,updated_at=? WHERE working_set_uuid=?',(status,stamp(),set_uuid))
                self.event(c,'WORKING_SET_STATUS',{'working_set_uuid':set_uuid,'before':current['status'],'after':status})

    def reopen(self,set_uuid):
        with self.db.lock,self.db.con() as c:
            c.execute('BEGIN IMMEDIATE')
            current=c.execute('SELECT status FROM working_sets WHERE working_set_uuid=?',(set_uuid,)).fetchone()
            if not current or current['status'] not in ('COMPLETE','ARCHIVED'):
                raise ValueError('Select a COMPLETE or ARCHIVED set to reopen.')
            c.execute("UPDATE working_sets SET status='REVIEW',updated_at=? WHERE working_set_uuid=?",(stamp(),set_uuid))
            self.event(c,'REOPEN_WORKING_SET',{'working_set_uuid':set_uuid,'before':current['status']})

    def reopen_items(self,item_uuids):
        with self.db.lock,self.db.con() as c:
            c.execute('BEGIN IMMEDIATE')
            items=[self.guard(item_uuid=uid,con=c) for uid in dict.fromkeys(item_uuids)]
            if not items or any(i['processing_status'] not in ('ACCEPTED','REJECTED') for i in items):
                raise ValueError('Select ACCEPTED or REJECTED items to reopen for review.')
            for item in items:
                c.execute("UPDATE working_set_items SET processing_status='QUEUED',updated_at=? WHERE working_set_item_uuid=?",(stamp(),item['working_set_item_uuid']))
                self.event(c,'REOPEN_ITEM',{'working_set_uuid':item['working_set_uuid'],'working_set_item_uuid':item['working_set_item_uuid'],
                    'work_uuid':item['linked_work_uuid'],'audit_id':item['pinned_audit_id'],'before':item['processing_status']})
        return [i['working_set_item_uuid'] for i in items]

    def accept(self,item_uuids=(),work_ids=(),expected=None):
        return self.db.acceptance.accept(item_uuids=item_uuids,work_ids=work_ids,expected=expected)

    def mark_duplicate_if_known(self,item_uuid,identity,con=None):
        with self.db.lock,(self.db.con() if con is None else nullcontext(con)) as c:
            if con is None:c.execute('BEGIN IMMEDIATE')
            item=self.editable_item(item_uuid,con=c)
            target=self.resolve_work(item,identity,con=c)
            if target is None:return False
            work=c.execute('SELECT work_uuid FROM works WHERE id=?',(target,)).fetchone()
            primary=c.execute("""SELECT * FROM working_set_items WHERE working_set_uuid=? AND linked_work_uuid=?
                AND removed_at IS NULL AND processing_status<>'DUPLICATE' AND working_set_item_uuid<>?
                ORDER BY created_at,rowid LIMIT 1""",(item['working_set_uuid'],work['work_uuid'],item_uuid)).fetchone()
            if not primary:return False
            c.execute("""UPDATE working_set_items SET linked_work_uuid=?,duplicate_of_item_uuid=?,processing_status='DUPLICATE',
                pinned_audit_id=NULL,pinned_audit_revision=NULL,updated_at=? WHERE working_set_item_uuid=?""",
                (work['work_uuid'],primary['working_set_item_uuid'],stamp(),item_uuid))
            details={'query':item['original_query'],'work_uuid':work['work_uuid'],'duplicate_of_item_uuid':primary['working_set_item_uuid']}
            c.execute('INSERT INTO working_set_observations(working_set_item_uuid,created_at,record_json,holes_json) VALUES(?,?,?,?)',
                (item_uuid,stamp(),json.dumps(details),json.dumps([{'code':'DUPLICATE_INTAKE','severity':'info','message':'Exact canonical work already has a primary membership in this set.'}])))
            self.event(c,'DUPLICATE_INTAKE',dict(details,working_set_uuid=item['working_set_uuid'],working_set_item_uuid=item_uuid))
            return True

    def recover_interrupted(self):
        with self.db.lock,self.db.con() as c:
            c.execute('BEGIN IMMEDIATE')
            rows=c.execute("""SELECT i.* FROM working_set_items i JOIN working_sets s USING(working_set_uuid)
                WHERE i.processing_status='AUDITING' AND i.removed_at IS NULL AND s.status IN ('OPEN','REVIEW')""").fetchall()
            for item in rows:
                self.guard(item_uuid=item['working_set_item_uuid'],con=c)
                c.execute("UPDATE working_set_items SET processing_status='QUEUED',updated_at=? WHERE working_set_item_uuid=?",(stamp(),item['working_set_item_uuid']))
                self.event(c,'INTERRUPTED',{'working_set_uuid':item['working_set_uuid'],'working_set_item_uuid':item['working_set_item_uuid'],'audit_id':item['pinned_audit_id']})
            return len(rows)

    def run_candidates(self,set_uuid):
        self.guard(set_uuid=set_uuid)
        candidates=[]
        for item in self.items(set_uuid):
            if item['processing_status'] in ('PENDING','QUEUED','AUDITED'):candidates.append(item['working_set_item_uuid'])
            elif item['processing_status'] in ('AUDITED','READY','REVIEW') and item['pinned_audit_id']:
                result=self.db.acceptance.evaluate(item['work_id'],item['working_set_item_uuid'])
                if result['needs_reaudit']:
                    candidates.append(item['working_set_item_uuid'])
        return candidates

    def retry_errors(self,set_uuid):
        self.guard(set_uuid=set_uuid)
        ids=[i['working_set_item_uuid'] for i in self.items(set_uuid) if i['processing_status']=='ERROR']
        for uid in ids:self.set_item_status(uid,'QUEUED')
        return ids

    def force_audit_candidate(self,item_uuid,con=None,include_pending=False):
        """Validate one stable membership, without changing its snapshot."""
        if not isinstance(item_uuid,str) or not item_uuid:
            raise ValueError('Select one exact Working Set item.')
        if con is None:
            with self.db.con() as c:return self.force_audit_candidate(item_uuid,con=c,include_pending=include_pending)
        item=self.guard(item_uuid=item_uuid,con=con)
        active=con.execute('SELECT active_working_set_uuid FROM database_meta WHERE singleton=1').fetchone()[0]
        if item['working_set_uuid']!=active:
            raise ValueError('Activate the exact Working Set first.')
        eligible=('REVIEW','READY','ACCEPTED','REJECTED','ERROR')
        if include_pending:eligible+=('PENDING','QUEUED','AUDITED')
        if item['processing_status'] not in eligible:
            raise ValueError('Force Re-Audit requires a stable REVIEW, READY, ACCEPTED, REJECTED, or ERROR item.')
        if include_pending:
            validate_context(item['requested_edition'],item['requested_language'],item['requested_workflow'])
            if not item['original_query'].strip():raise ValueError('Intake query is empty.')
        return item

    def force_audit_plan(self,set_uuid):
        """Read-only exact active-set snapshot; never queue the whole batch."""
        with self.db.con() as c:
            current=self.guard(set_uuid=set_uuid,con=c)
            active=c.execute('SELECT active_working_set_uuid FROM database_meta WHERE singleton=1').fetchone()[0]
            if active!=set_uuid:raise ValueError('Activate the exact Working Set first.')
            eligible=[];skipped=[]
            for item in self.items(set_uuid,con=c):
                try:eligible.append(self.force_audit_candidate(item['working_set_item_uuid'],con=c,include_pending=True))
                except ValueError as exc:
                    skipped.append(dict(working_set_item_uuid=item['working_set_item_uuid'],
                        title=item['original_query'],result='SKIPPED',reason=str(exc),audit_id=None,audit_revision=None))
            return dict(working_set_uuid=set_uuid,name=current['name'],items=eligible,skipped=skipped)

    def queue_force_audit(self,item_uuid,include_pending=False):
        """Explicitly reopen/queue only this item for the normal fresh worker."""
        with self.db.lock,self.db.con() as c:
            c.execute('BEGIN IMMEDIATE')
            item=self.force_audit_candidate(item_uuid,con=c,include_pending=include_pending)
            c.execute("UPDATE working_set_items SET processing_status='QUEUED',updated_at=? WHERE working_set_item_uuid=?",
                      (stamp(),item_uuid))
            self.event(c,'FORCE_REAUDIT',{'working_set_uuid':item['working_set_uuid'],
                'working_set_item_uuid':item_uuid,'work_uuid':item['linked_work_uuid'],
                'audit_id':item['pinned_audit_id'],'before':item['processing_status']})
        return item_uuid

    def relate_structure(self,source_work_id,target_work_id,note,verification='REVIEWED',item_uuid=None):
        note=str(note or '').strip()
        if not note:raise ValueError('Reviewed structure compatibility needs a source note.')
        if verification not in ('REVIEWED','VERIFIED'):raise ValueError('Relationship must be reviewed or verified.')
        source=self.db.work(source_work_id);target=self.db.work(target_work_id)
        if not source or not target or source['id']==target['id']:
            raise ValueError('Choose two distinct existing edition records.')
        if source['edition']==target['edition'] or source['language']!=target['language']:
            raise ValueError('Structure sharing requires distinct editions in the same language.')
        if not source['canonical_work_id'] or source['canonical_work_id']!=target['canonical_work_id']:
            raise ValueError('Structure relationship requires the same trusted canonical work claim.')
        def context(work_id):
            audit=self.db.latest_audit(work_id)
            return (json.loads(audit['publication_json'] or '{}').get('catalog_identity') or {}).get('publication_context','') if audit else ''
        source_context=context(source_work_id);target_context=context(target_work_id)
        self.db.catalog._backup()
        with self.db.lock,self.db.con() as c:
            c.execute('BEGIN IMMEDIATE')
            if item_uuid:self.editable_item(item_uuid,target_work_id,con=c)
            c.execute('''INSERT INTO edition_structure_relationships(
                source_work_uuid,target_work_uuid,status,source_note,created_at,source_context,target_context)
                VALUES(?,?,?,?,?,?,?)
                ON CONFLICT(source_work_uuid,target_work_uuid) DO UPDATE SET
                status=excluded.status,source_note=excluded.source_note,
                source_context=excluded.source_context,target_context=excluded.target_context''',
                (source['work_uuid'],target['work_uuid'],verification,note,stamp(),source_context,target_context))
            c.execute('UPDATE works SET conceptual_work_uuid=? WHERE id=?',
                      (source['conceptual_work_uuid'],target_work_id))
            self.db.acceptance.recalculate(target_work_id,con=c)

    def structure_source(self,target_work_id,con=None):
        target=self.db.work(target_work_id,con=con)
        if not target:return None
        with (self.db.con() if con is None else nullcontext(con)) as c:
            rows=c.execute('''SELECT r.*,w.id source_work_id FROM edition_structure_relationships r
                JOIN works w ON w.work_uuid=r.source_work_uuid WHERE r.target_work_uuid=?''',
                (target['work_uuid'],)).fetchall()
        if len(rows)>1:raise ValueError('Multiple structure sources need human review.')
        return dict(rows[0]) if rows else None
