"""Thin application context: backend services remain authoritative."""
import json
from pathlib import Path
from mangaanka_database_development_kit import DB
from ddk_workspace import validate_database
from ddk_writer_lock import WriterLock
from ddk_exports import catalog_context, working_set_rows

class Session:
    def __init__(self, path, create=False, role='SCRATCH', migrate_schema8=False):
        self.writer_lock = None
        self.open(path, create, role, migrate_schema8)

    def open(self, path, create=False, role='SCRATCH', migrate_schema8=False):
        path = Path(path).resolve()
        if create:
            if path.exists(): raise ValueError('New Database requires a new file path.')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch(exist_ok=False)  # Existing DB.create_new requires an empty reservation.
        else: validate_database(path)
        lock = WriterLock(path)
        try:
            db = DB(path, role=role, create_new=create, migrate_schema8=migrate_schema8)
            db.working_sets.recover_interrupted()
        except Exception:
            lock.close()
            raise
        old = self.writer_lock
        self.db = db; self.writer_lock = lock; self._restored_working_set_uuid = None
        if old: old.close()

    def close(self):
        if self.writer_lock: self.writer_lock.close()

    @property
    def active_uuid(self):
        uid = self._restored_working_set_uuid or self.db.working_sets.active_uuid()
        return uid if self.db.working_sets.get(uid) else None

    def restore_working_set(self, uid):
        # Selection is application context only. Protected COMPLETE/ARCHIVED
        # sets may be viewed; existing backend guards still block mutations.
        self._restored_working_set_uuid = uid if isinstance(uid, str) and self.db.working_sets.get(uid) else None

    def activate_working_set(self, uid):
        self.db.working_sets.set_active(uid)
        self._restored_working_set_uuid = None

    def scopes(self):
        return [('Active Working Set', 'active'), ('All Catalog', 'all'), ('Accepted Master Catalog', 'accepted')] + [
            (f"{s['name']} · {s['working_set_uuid'][:8]}", s['working_set_uuid']) for s in self.db.working_sets.list()]

    def set_uuid(self, scope): return self.active_uuid if scope == 'active' else scope if scope not in ('all', 'accepted') else None

    def items(self, scope):
        uid = self.set_uuid(scope)
        return self.db.working_sets.items(uid) if uid else []

    def audit_map(self, scope):
        if scope in ('all', 'accepted'): return None
        return {i['work_id']: i['pinned_audit_id'] for i in self.items(scope) if i['work_id'] and i['processing_status'] != 'DUPLICATE'}

    def works(self, scope):
        pins = self.audit_map(scope)
        return self.db.works(work_ids=list(pins) if pins is not None else None,
                             accepted_only=scope == 'accepted', audit_by_work=pins)

    def catalog_rows(self, scope):
        uid = self.set_uuid(scope)
        if uid:
            rows = working_set_rows(self.db, uid)
            items = {i['working_set_item_uuid']: i for i in self.items(scope)}
            for r in rows: r['_item'] = items[r['working_set_item_uuid']]; r['_work_id'] = r['_item']['work_id']
        elif scope not in ('all', 'accepted'): return []
        else:
            rows = []
            for work in self.works(scope):
                c = catalog_context(self.db, work['id'])
                rows.append(dict(c, query=c['title'], item_status='—',
                    chapters=c['canonical_chapters'], _work_id=work['id'], _item=None,
                    **{k+'_health': v for k, v in c['health'].items()}))
        for r in rows:
            audit=self.db.audit(r['audit_id'],r['_work_id']) if r.get('audit_id') and r['_work_id'] else None
            r['audit_created_at']=audit['created_at'] if audit else None
            r['chapter_display'] = f"{r.get('mapped') if r.get('mapped') is not None else '—'}/{r.get('chapters') if r.get('chapters') is not None else '—'}"
            pub = json.loads(audit['publication_json'] or '{}') if audit else {}
            r['uncompiled'] = pub.get('uncompiled_chapters', 0)
            if r['uncompiled']:
                r['chapter_display'] = f"{r.get('mapped',0)} mapped · {r['uncompiled']} uncompiled"
        return rows

    def context(self, wid, scope, item=None):
        if scope not in ('all', 'accepted') and item is None:
            item = next((i for i in self.items(scope) if i['work_id'] == wid and i['processing_status'] != 'DUPLICATE'), None)
            if not item: raise ValueError('No exact linked membership in this scope.')
        return catalog_context(self.db, wid, item), item

    def mutation_item(self, wid, scope):
        if scope in ('all', 'accepted'): return None
        matches = [i for i in self.items(scope) if i['work_id'] == wid and i['processing_status'] != 'DUPLICATE']
        if len(matches) != 1: raise ValueError('Choose one exact primary membership.')
        item = matches[0]
        self.db.working_sets.editable_item(item['working_set_item_uuid'], wid)
        if item['working_set_uuid'] != self.active_uuid: raise ValueError('Activate this Working Set before editing, or use All Catalog for global curation.')
        return item['working_set_item_uuid']

    def history(self, scope):
        works = self.works(scope); allowed = {w['id'] for w in works}
        uuids = {w['work_uuid'] for w in works}; uid = self.set_uuid(scope)
        entries = []
        with self.db.con() as c:
            for a in c.execute('SELECT a.*,w.input_title FROM search_audits a JOIN works w ON w.id=a.work_id'):
                if scope != 'all' and a['work_id'] not in allowed: continue
                entries.append(dict(time=a['created_at'], title=a['input_title'], category='Audit',
                                    event=f"Audit {a['id']} · {a['final_state'] or 'saved'}", _data=dict(a)))
            for e in c.execute('SELECT e.*,h.work_id,h.operation,h.changes_json,h.revision,h.state,w.input_title FROM curated_events e JOIN curated_changes h ON h.id=e.change_id JOIN works w ON w.id=h.work_id'):
                if scope != 'all' and e['work_id'] not in allowed: continue
                entries.append(dict(time=e['timestamp'], title=e['input_title'], category='Curation', event=e['action']+' · '+e['operation'], _data=dict(e)))
            for e in c.execute('SELECT * FROM database_events'):
                d = json.loads(e['details_json'] or '{}')
                if scope != 'all' and d.get('work_uuid') not in uuids and not (uid and (
                        d.get('working_set_uuid') == uid or uid in d.get('working_set_uuids', []))): continue
                origin = e['origin']
                category = 'Acceptance' if 'ACCEPT' in origin or 'REVOKE' in origin else 'Maintenance' if 'DELETE' in origin or 'MIGRAT' in origin else 'Working Set'
                entries.append(dict(time=e['timestamp'], title=d.get('title') or d.get('work_uuid') or 'Working Set',
                                    category=category, event=e['description'], _data=dict(e)))
        return sorted(entries, key=lambda r: r['time'], reverse=True)
