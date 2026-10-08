"""Guarded, work-UUID-targeted permanent catalog maintenance."""
import hashlib
import json
from pathlib import Path

from ddk_review import database_revision
from ddk_working_sets import stamp


# If a later schema adds an owned foreign key, stop rather than silently
# cascading rows that the impact preview did not count.
OWNED_FOREIGN_KEYS = {
    ('works', 'conceptual_works', 'conceptual_work_uuid'),
    ('search_audits', 'works', 'work_id'),
    ('audit_holes', 'search_audits', 'audit_id'),
    ('audit_holes', 'works', 'work_id'),
    ('problem_dispositions', 'audit_holes', 'problem_row_id'),
    ('problem_dispositions', 'works', 'work_id'),
    ('problem_dispositions', 'search_audits', 'audit_id'),
    ('curated_catalog', 'works', 'work_id'),
    ('curated_fields', 'works', 'work_id'),
    ('curated_evidence', 'works', 'work_id'),
    ('curated_changes', 'works', 'work_id'),
    ('curated_events', 'curated_changes', 'change_id'),
    ('working_set_items', 'works', 'linked_work_uuid'),
    ('working_set_items', 'search_audits', 'pinned_audit_id'),
    ('edition_structure_relationships', 'works', 'source_work_uuid'),
    ('edition_structure_relationships', 'works', 'target_work_uuid'),
    ('catalog_acceptances', 'works', 'work_uuid'),
    ('catalog_acceptances', 'search_audits', 'audit_id'),
}
OWNED_PARENTS = {
    'works', 'search_audits', 'audit_holes', 'problem_dispositions',
    'curated_catalog', 'curated_fields', 'curated_evidence', 'curated_changes',
    'curated_events', 'edition_structure_relationships', 'conceptual_works', 'catalog_acceptances',
}
SUPPLEMENTARY_TABLES=('supplementary_current','supplementary_events','supplementary_changes',
    'supplementary_assertions','supplementary_identities','supplementary_catalog')
OWNED_PARENTS.update(SUPPLEMENTARY_TABLES)
OWNED_FOREIGN_KEYS.update((table,'works','work_id') for table in SUPPLEMENTARY_TABLES)
OWNED_FOREIGN_KEYS.update({
    ('supplementary_identities','search_audits','created_audit_id'),
    ('supplementary_identities','search_audits','work_id'),
    ('supplementary_assertions','search_audits','created_audit_id'),
    ('supplementary_assertions','search_audits','work_id'),
    ('supplementary_assertions','supplementary_identities','work_id'),
    ('supplementary_assertions','supplementary_identities','opaque_id'),
    ('supplementary_current','supplementary_assertions','assertion_uuid'),
    ('supplementary_current','supplementary_assertions','work_id'),
    ('supplementary_current','supplementary_assertions','kind'),
    ('supplementary_current','supplementary_assertions','target_key'),
    ('supplementary_events','supplementary_changes','work_id'),
    ('supplementary_events','supplementary_changes','change_id')})


def format_delete_preview(preview):
    counts = preview['counts']
    lines = ['PERMANENT CATALOG WORK DELETION', '']
    if preview['strong_warning']:
        lines += ['STRONG WARNING: This work is ACCEPTED or has curated fields/evidence.', '']
    lines += [f"Title: {preview['title']}", f"Edition: {preview['edition']}",
              f"Language: {preview['language']}", f"Work UUID: {preview['work_uuid']}",
              f"Conceptual Work UUID: {preview['conceptual_work_uuid'] or 'none'}",
              f"Catalog Status: {preview['catalog_status']}", '', 'ROWS REMOVED']
    for key, label in (
        ('work_rows', 'Catalog work'), ('audit_revisions', 'Audit revisions'),
        ('problems', 'Audit problems'), ('review_records', 'Problem review/disposition records'),
        ('curated_catalog', 'Curation state rows'), ('curated_fields', 'Curated fields (including verification)'),
        ('curated_evidence', 'Curated evidence records'), ('curated_changes', 'Curation history changes'),
        ('curated_events', 'Curation history events'),
        ('acceptance_history', 'Catalog acceptance history'),
        ('structure_relationships', 'Edition structure relationships involving this work'),
        ('conceptual_parent_removed', 'Conceptual parent, if final edition')):
        lines.append(f"{label}: {counts[key]}")
    lines += ['', f"WORKING SET ITEMS DETACHED, NOT DELETED: {counts['working_set_memberships']}"]
    for table in SUPPLEMENTARY_TABLES:
        lines.append(f"{table}: {counts[table]}")
    for item in preview['memberships']:
        lines.append(f"  {item['working_set']} [{item['status']}] · item {item['item_uuid']}")
    lines += [f"Existing intake observations preserved: {counts['working_set_observations_preserved']}",
              '', 'IDENTITY VALUES INSIDE REMOVED ROWS',
              f"Work external-ID columns populated: {counts['work_external_id_values']}",
              f"Curated alias/external-ID fields: {counts['curated_alias_external_id_fields']}",
              'There is no separate work-owned alias/external-ID table.', '',
              'PRESERVED', f"Sibling editions of this conceptual work: {counts['sibling_editions_preserved']}",
              'Other catalog works, unrelated audits/curation, Working Sets and intake requests remain.',
              'Existing intake observations remain; affected items become unlinked REVIEW items.',
              'Their pinned audit IDs/revisions are cleared; the owned audit payloads above are removed.', '',
              'This cannot be undone through normal Undo/Redo. Restore the pre-delete backup to recover it.',
              'For normal catalog exclusion, use REJECTED / ARCHIVED instead.']
    return '\n'.join(lines)


class CatalogMaintenance:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def _check_schema(con):
        for row in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
            table = row['name']
            for fk in con.execute(f'PRAGMA foreign_key_list("{table}")'):
                edge = (table, fk['table'], fk['from'])
                if fk['table'] in OWNED_PARENTS and edge not in OWNED_FOREIGN_KEYS:
                    raise ValueError(f'Unknown catalog dependency {table}.{fk["from"]}; deletion needs a new impact review.')

    def _snapshot(self, con, work_uuid):
        self._check_schema(con)
        work = con.execute('SELECT * FROM works WHERE work_uuid=?', (work_uuid,)).fetchone()
        if not work:
            raise ValueError('Selected catalog work no longer exists; preview again.')
        work = dict(work)
        work_id = work['id']
        conceptual = work['conceptual_work_uuid']
        digest = hashlib.sha256()
        counts = {'work_rows': 1}

        def feed(label, row):
            digest.update(json.dumps([label, dict(row)], sort_keys=True, default=str,
                                     ensure_ascii=False).encode('utf-8'))
            digest.update(b'\n')

        def scan(label, sql, args=(), collect=False):
            rows = []
            count = 0
            for row in con.execute(sql, args):
                feed(label, row)
                count += 1
                if collect:
                    rows.append(dict(row))
            counts[label] = count
            return rows

        feed('work', work)
        scan('audit_revisions', 'SELECT * FROM search_audits WHERE work_id=? ORDER BY id', (work_id,))
        scan('acceptance_history','SELECT * FROM catalog_acceptances WHERE work_uuid=? ORDER BY id',(work_uuid,))
        scan('problems', 'SELECT * FROM audit_holes WHERE work_id=? ORDER BY id', (work_id,))
        scan('review_records', 'SELECT * FROM problem_dispositions WHERE work_id=? ORDER BY id', (work_id,))
        scan('curated_catalog', 'SELECT * FROM curated_catalog WHERE work_id=?', (work_id,))
        fields = scan('curated_fields', 'SELECT * FROM curated_fields WHERE work_id=? ORDER BY rowid',
                      (work_id,), collect=True)
        scan('curated_evidence', 'SELECT * FROM curated_evidence WHERE work_id=? ORDER BY rowid', (work_id,))
        scan('curated_changes', 'SELECT * FROM curated_changes WHERE work_id=? ORDER BY id', (work_id,))
        scan('curated_events', '''SELECT e.* FROM curated_events e JOIN curated_changes h ON h.id=e.change_id
                                 WHERE h.work_id=? ORDER BY e.id''', (work_id,))
        for table in SUPPLEMENTARY_TABLES:
            scan(table,'SELECT * FROM '+table+' WHERE work_id=? ORDER BY rowid',(work_id,))
        memberships = scan('working_set_memberships', '''SELECT i.*,s.name working_set_name FROM working_set_items i
            JOIN working_sets s ON s.working_set_uuid=i.working_set_uuid
            WHERE i.linked_work_uuid=? OR i.pinned_audit_id IN
                (SELECT id FROM search_audits WHERE work_id=?) ORDER BY i.working_set_item_uuid''',
            (work_uuid, work_id), collect=True)
        scan('working_set_observations_preserved', '''SELECT o.* FROM working_set_observations o
            JOIN working_set_items i ON i.working_set_item_uuid=o.working_set_item_uuid
            WHERE i.linked_work_uuid=? OR i.pinned_audit_id IN
                (SELECT id FROM search_audits WHERE work_id=?) ORDER BY o.id''',
            (work_uuid, work_id))
        scan('structure_relationships', '''SELECT * FROM edition_structure_relationships
            WHERE source_work_uuid=? OR target_work_uuid=? ORDER BY rowid''', (work_uuid, work_uuid))
        siblings = scan('sibling_editions_preserved', '''SELECT * FROM works
            WHERE conceptual_work_uuid=? AND work_uuid<>? ORDER BY id''',
            (conceptual, work_uuid), collect=True) if conceptual else []
        parent = scan('conceptual_parent', '''SELECT * FROM conceptual_works
            WHERE conceptual_work_uuid=?''', (conceptual,), collect=True) if conceptual else []
        counts['conceptual_parent_removed'] = int(bool(parent) and not siblings)
        counts['work_external_id_values'] = sum(bool(work.get(key)) for key in
                                                 ('anilist_id', 'mal_id', 'mangadex_id'))
        counts['curated_alias_external_id_fields'] = sum(
            row['entity'] == 'work' and row['field'] in ('aliases', 'external_ids') for row in fields)
        file_stat = self.db.path.stat()
        guard = {'database_uuid': self.db.database_uuid, 'database_path': str(self.db.path),
                 'database_revision': database_revision(self.db, con),
                 'database_file_mtime_ns': file_stat.st_mtime_ns,
                 'database_file_size': file_stat.st_size,
                 'schema_revision': con.execute('PRAGMA schema_version').fetchone()[0],
                 'impact_digest': digest.hexdigest()}
        return {'work_uuid': work_uuid, 'work_id': work_id,
                'title': work['input_title'], 'edition': work['edition'], 'language': work['language'],
                'conceptual_work_uuid': conceptual, 'catalog_status': work['lifecycle_status'],
                'counts': counts,
                'memberships': [{'working_set': row['working_set_name'],
                                 'working_set_uuid': row['working_set_uuid'],
                                 'item_uuid': row['working_set_item_uuid'],
                                 'status': row['processing_status']} for row in memberships],
                'sibling_editions': [{'title': row['input_title'], 'edition': row['edition'],
                                      'language': row['language'], 'work_uuid': row['work_uuid']}
                                     for row in siblings],
                'strong_warning': work['lifecycle_status'] == 'ACCEPTED' or
                                  counts['curated_fields'] > 0 or counts['curated_evidence'] > 0 or
                                  counts['supplementary_assertions'] > 0,
                'guard': guard}

    def preview(self, work_uuid):
        if not work_uuid:
            raise ValueError('Select one catalog work with a work UUID.')
        with self.db.lock, self.db.con() as con:
            con.execute('BEGIN')
            return self._snapshot(con, work_uuid)

    def delete(self, preview, confirmation):
        if confirmation != 'DELETE':
            raise ValueError('Type DELETE exactly to confirm permanent deletion.')
        if not preview or not preview.get('work_uuid'):
            raise ValueError('Open a fresh impact preview first.')
        if (preview.get('guard', {}).get('database_uuid') != self.db.database_uuid or
                preview['guard'].get('database_path') != str(self.db.path)):
            raise ValueError('Database changed after preview; preview again.')
        work_uuid = preview['work_uuid']

        def check(con):
            current = self._snapshot(con, work_uuid)
            if current != preview:
                raise ValueError('Catalog changed after preview; preview again before deleting.')
            return current

        with self.db.lock:
            with self.db.con() as con:
                con.execute('BEGIN')
                check(con)
            # Force a fresh backup even if a curation edit already made one this session.
            backup = self.db.catalog._backup(force=True)
            if not backup or not Path(backup).is_file() or not Path(backup).stat().st_size:
                raise ValueError('Database backup failed; catalog work was not deleted.')
            with self.db.con() as con:
                con.execute('BEGIN IMMEDIATE')
                current = check(con)
                counts = current['counts']
                work_id = current['work_id']

                def run(label, sql, args):
                    changed = con.execute(sql, args).rowcount
                    if changed != counts[label]:
                        raise ValueError(f'{label} changed during deletion; transaction rolled back.')

                run('working_set_memberships', '''UPDATE working_set_items SET linked_work_uuid=NULL,
                    pinned_audit_id=NULL,pinned_audit_revision=NULL,duplicate_of_item_uuid=NULL,processing_status='REVIEW',updated_at=?
                    WHERE linked_work_uuid=? OR pinned_audit_id IN
                        (SELECT id FROM search_audits WHERE work_id=?)''', (stamp(), work_uuid, work_id))
                run('structure_relationships', '''DELETE FROM edition_structure_relationships
                    WHERE source_work_uuid=? OR target_work_uuid=?''', (work_uuid, work_uuid))
                run('curated_events', '''DELETE FROM curated_events WHERE change_id IN
                    (SELECT id FROM curated_changes WHERE work_id=?)''', (work_id,))
                run('curated_evidence', 'DELETE FROM curated_evidence WHERE work_id=?', (work_id,))
                run('curated_fields', 'DELETE FROM curated_fields WHERE work_id=?', (work_id,))
                run('curated_changes', 'DELETE FROM curated_changes WHERE work_id=?', (work_id,))
                run('curated_catalog', 'DELETE FROM curated_catalog WHERE work_id=?', (work_id,))
                for table in SUPPLEMENTARY_TABLES:
                    run(table,'DELETE FROM '+table+' WHERE work_id=?',(work_id,))
                run('review_records', 'DELETE FROM problem_dispositions WHERE work_id=?', (work_id,))
                run('acceptance_history','DELETE FROM catalog_acceptances WHERE work_uuid=?',(work_uuid,))
                run('problems', 'DELETE FROM audit_holes WHERE work_id=?', (work_id,))
                run('audit_revisions', 'DELETE FROM search_audits WHERE work_id=?', (work_id,))
                run('work_rows', 'DELETE FROM works WHERE work_uuid=? AND id=?', (work_uuid, work_id))
                if counts['conceptual_parent_removed']:
                    run('conceptual_parent_removed', '''DELETE FROM conceptual_works
                        WHERE conceptual_work_uuid=? AND NOT EXISTS
                            (SELECT 1 FROM works WHERE conceptual_work_uuid=?)''',
                        (current['conceptual_work_uuid'], current['conceptual_work_uuid']))
                event = {'operation': 'DELETE_WORK', 'work_uuid': work_uuid,
                         'title': current['title'], 'edition': current['edition'],
                         'language': current['language'],
                         'conceptual_work_uuid': current['conceptual_work_uuid'],
                         'counts': counts, 'backup': str(backup)}
                con.execute('''INSERT INTO database_events(timestamp,origin,description,details_json)
                    VALUES(?,?,?,?)''', (stamp(), 'DELETE_WORK',
                    f'Permanently deleted catalog work {work_uuid}',
                    json.dumps(event, ensure_ascii=False, sort_keys=True)))
                if (con.execute('PRAGMA foreign_key_check').fetchone() or
                        con.execute('PRAGMA integrity_check').fetchone()[0] != 'ok'):
                    raise ValueError('Database integrity validation failed; deletion rolled back.')
            return {'backup': str(backup), 'work_uuid': work_uuid,
                    'work_id': work_id, 'counts': counts,
                    'detached_item_uuids': [row['item_uuid'] for row in current['memberships']]}
