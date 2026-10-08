"""Disposable schema-v6 permanent-work maintenance regressions."""
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import mangaanka_database_development_kit as ddk
from ddk_catalog_maintenance import format_delete_preview


def publication(title, edition='standard', language='en', canonical='fixture:one'):
    identity = {'canonical_work_id': canonical, 'edition': edition,
                'language': language, 'trusted': True, 'publication_context': '',
                'external_ids': {'fixture': canonical.split(':',1)[1]}}
    row = {'id': '1', 'chapter': '1', 'volume': '1', 'type': 'chapter'}
    data = {'status': 'complete', 'catalog_identity': identity, 'edition': edition,
            'context': {'shareable': True}, 'projection': [row],
            'normalization': {'status': 'established'}, 'raw_acquisition_records': 1,
            'logical_chapters': 1, 'mapped_chapters': 1, 'unmapped_chapters': 0,
            'final_volumes': 1, 'curation_revision': 0}
    return dict(data, automatic=dict(data))


class CatalogMaintenanceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / 'catalog.db'
        self.db = ddk.DB(self.path, role='TEST')

    def add(self, title='Example', edition='standard', language='en'):
        self.db.add_titles([title], edition, language)
        return next(r for r in self.db.works() if r['input_title'] == title and
                    r['edition'] == edition and r['language'] == language)

    def audit(self, work_id, problem=False):
        work = self.db.work(work_id)
        holes = [{'code': 'UNMAPPED_CHAPTERS', 'severity': 'warning',
                  'message': 'Fixture problem'}] if problem else []
        return self.db.save_audit(work_id, {'query': work['input_title'],
            'match_title': work['input_title'], 'publication': publication(
                work['input_title'], work['edition'], work['language'], canonical='fixture:'+work['input_title'])}, holes)

    def preview(self, work_id=1):
        return self.db.maintenance.preview(self.db.work(work_id)['work_uuid'])

    def counts(self):
        with self.db.con() as c:
            return {name: c.execute(f'SELECT count(*) FROM {name}').fetchone()[0] for name in
                ('works', 'search_audits', 'audit_holes', 'problem_dispositions',
                 'curated_catalog', 'curated_fields', 'curated_evidence',
                 'curated_changes', 'curated_events', 'working_set_items',
                 'working_set_observations', 'edition_structure_relationships',
                 'conceptual_works', 'database_events')}

    def assert_integrity(self):
        with self.db.con() as c:
            self.assertEqual([], c.execute('PRAGMA foreign_key_check').fetchall())
            self.assertEqual('ok', c.execute('PRAGMA integrity_check').fetchone()[0])

    def curate(self, evidence=False):
        changes = [{'entity': 'chapter', 'key': '1', 'field': 'volume',
                    'value': '2', 'verification': 'VERIFIED'}]
        if evidence:
            changes += [{'entity': 'evidence', 'key': key, 'field': 'add',
                         'target_key': '1', 'source_name': name,
                         'source_url': f'https://example.org/{key}'}
                        for key, name in (('e1', 'Publisher'), ('e2', 'Bibliography'))]
        self.db.catalog.apply(self.db.catalog.preview(1, changes))

    def test_simple_staged_work_and_final_parent_deleted_with_journal(self):
        work = self.add(); parent = work['conceptual_work_uuid']
        preview = self.preview()
        self.assertEqual(1, preview['counts']['conceptual_parent_removed'])
        result = self.db.maintenance.delete(preview, 'DELETE')
        self.assertIsNone(self.db.work(work['id']))
        self.assertEqual(0, self.counts()['conceptual_works'])
        with self.db.con() as c:
            row = c.execute("SELECT * FROM database_events WHERE origin='DELETE_WORK'").fetchone()
            details = json.loads(row['details_json'])
        self.assertEqual((work['work_uuid'], parent),
                         (details['work_uuid'], details['conceptual_work_uuid']))
        self.assertEqual(result['backup'], details['backup'])
        self.assert_integrity()

    def test_audits_problems_and_review_records_removed_only_for_target(self):
        first = self.add(); other = self.add('Other')
        self.audit(first['id'], problem=True); self.audit(first['id'], problem=True)
        self.audit(other['id'], problem=True)
        with self.db.con() as c:
            hole = c.execute('SELECT id,audit_id FROM audit_holes WHERE work_id=? LIMIT 1',
                             (first['id'],)).fetchone()
            c.execute('''INSERT INTO problem_dispositions(problem_row_id,work_id,audit_id,signature,
                status,reason,verification,created_at) VALUES(?,?,?,?,?,?,?,?)''',
                (hole['id'], first['id'], hole['audit_id'], 'fixture', 'REVIEWED',
                 'fixture', 'REVIEWED', ddk.now()))
        preview = self.preview(first['id'])
        self.assertEqual((2, 2, 1), tuple(preview['counts'][key] for key in
                         ('audit_revisions', 'problems', 'review_records')))
        self.db.maintenance.delete(preview, 'DELETE')
        self.assertEqual((1, 1, 0), tuple(self.counts()[key] for key in
                         ('search_audits', 'audit_holes', 'problem_dispositions')))
        self.assertIsNotNone(self.db.work(other['id']))
        self.assert_integrity()

    def test_curation_evidence_verification_history_and_fresh_backup(self):
        self.add(); self.audit(1); self.curate(evidence=True)
        before = self.counts()
        self.assertEqual(2, before['curated_evidence'])
        preview = self.preview()
        self.assertTrue(preview['strong_warning'])
        self.assertIn('STRONG WARNING', format_delete_preview(preview))
        self.assertEqual(2, preview['counts']['curated_evidence'])
        old_backups = list((self.path.parent / 'backups').glob('*.db'))
        result = self.db.maintenance.delete(preview, 'DELETE')
        self.assertEqual(len(old_backups) + 1,
                         len(list((self.path.parent / 'backups').glob('*.db'))))
        for key in ('curated_catalog', 'curated_fields', 'curated_evidence',
                    'curated_changes', 'curated_events'):
            self.assertEqual(0, self.counts()[key], key)
        backup = ddk.DB(Path(result['backup']), role='TEST')
        self.assertEqual(2, len(backup.catalog.evidence(1)))
        self.assertEqual('VERIFIED', backup.catalog.state(1)['fields'][0]['verification'])
        self.assert_integrity()

    def test_two_working_sets_keep_intake_and_observations_after_detach(self):
        work = self.add(); self.audit(1)
        sets = [self.db.working_sets.create(name) for name in ('Batch A', 'Batch B')]
        item_ids = []
        for set_uuid in sets:
            self.db.working_sets.add_requests(set_uuid, ['Example'])
            item = self.db.working_sets.items(set_uuid)[0]
            item_ids.append(item['working_set_item_uuid'])
            self.db.working_sets.pin(item_ids[-1], 1, self.db.latest_audit(1)['id'])
            self.db.working_sets.observe_unresolved(item_ids[-1], {'query': 'Example'}, [])
        preview = self.preview()
        self.assertEqual(2, preview['counts']['working_set_memberships'])
        self.assertEqual(2, preview['counts']['working_set_observations_preserved'])
        self.db.maintenance.delete(preview, 'DELETE')
        self.assertEqual(2, len(self.db.working_sets.list()))
        for set_uuid, item_uuid in zip(sets, item_ids):
            self.assertEqual(1, len(self.db.working_sets.items(set_uuid)))
            item = self.db.working_sets.item(item_uuid)
            self.assertEqual(('Example', 'REVIEW', None, None, None),
                (item['original_query'], item['processing_status'], item['linked_work_uuid'],
                 item['pinned_audit_id'], item['pinned_audit_revision']))
            self.assertIsNotNone(self.db.working_sets.latest_observation(item_uuid))
        self.assert_integrity()

    def test_three_edition_conceptual_group_preserves_siblings(self):
        selected = self.add('Series', 'standard', 'en')
        other = self.add('Series', 'standard', 'ja')
        color = self.add('Series', 'official_color', 'ja')
        with self.db.con() as c:
            c.execute('UPDATE works SET conceptual_work_uuid=? WHERE id IN (?,?)',
                      (selected['conceptual_work_uuid'], other['id'], color['id']))
        preview = self.preview(selected['id'])
        self.assertEqual(2, preview['counts']['sibling_editions_preserved'])
        self.assertEqual(0, preview['counts']['conceptual_parent_removed'])
        self.db.maintenance.delete(preview, 'DELETE')
        self.assertEqual({other['work_uuid'], color['work_uuid']},
                         {r['work_uuid'] for r in self.db.works()})
        with self.db.con() as c:
            self.assertIsNotNone(c.execute('SELECT 1 FROM conceptual_works WHERE conceptual_work_uuid=?',
                                           (selected['conceptual_work_uuid'],)).fetchone())
        self.assert_integrity()

    def test_relationships_touching_work_removed_unrelated_one_survives(self):
        works = [self.add('Series', edition) for edition in
                 ('standard', 'official_color', 'fan_color', 'omnibus')]
        for work in works: self.audit(work['id'])
        self.db.working_sets.relate_structure(works[0]['id'], works[1]['id'], 'fixture')
        self.db.working_sets.relate_structure(works[0]['id'], works[2]['id'], 'fixture')
        self.db.working_sets.relate_structure(works[2]['id'], works[3]['id'], 'fixture')
        preview = self.preview(works[0]['id'])
        self.assertEqual(2, preview['counts']['structure_relationships'])
        self.db.maintenance.delete(preview, 'DELETE')
        with self.db.con() as c:
            links = c.execute('SELECT * FROM edition_structure_relationships').fetchall()
        self.assertEqual(1, len(links))
        self.assertEqual(works[2]['work_uuid'], links[0]['source_work_uuid'])
        self.assert_integrity()

    def test_accepted_work_warns_but_can_be_deleted(self):
        work = self.add()
        with self.db.con() as c:
            c.execute("UPDATE works SET lifecycle_status='ACCEPTED' WHERE id=?", (work['id'],))
        preview = self.preview()
        self.assertTrue(preview['strong_warning'])
        self.assertIn('ACCEPTED', format_delete_preview(preview))
        self.db.maintenance.delete(preview, 'DELETE')
        self.assertEqual(0, self.counts()['works'])

    def test_preview_and_cancel_are_read_only(self):
        self.add(); before = self.counts()
        preview = self.preview()
        self.assertIn('Work UUID: ' + preview['work_uuid'], format_delete_preview(preview))
        self.assertEqual(before, self.counts())
        self.assertFalse((self.path.parent / 'backups').exists())

    def test_confirmation_must_be_exact_and_creates_no_backup(self):
        self.add(); preview = self.preview()
        for value in ('', 'delete', 'DELETE '):
            with self.assertRaisesRegex(ValueError, 'Type DELETE'):
                self.db.maintenance.delete(preview, value)
        self.assertEqual(1, self.counts()['works'])
        self.assertFalse((self.path.parent / 'backups').exists())

    def test_backup_failure_leaves_database_unchanged(self):
        self.add(); self.audit(1); preview = self.preview(); before = self.counts()
        with patch.object(self.db.catalog, '_backup', side_effect=OSError('backup denied')):
            with self.assertRaisesRegex(OSError, 'backup denied'):
                self.db.maintenance.delete(preview, 'DELETE')
        self.assertEqual(before, self.counts())

    def test_each_deletion_forces_its_own_fresh_backup(self):
        first = self.add(); second = self.add('Other')
        folder = self.path.parent / 'backups'
        before = len(list(folder.glob('*.db')))
        self.db.maintenance.delete(self.preview(first['id']), 'DELETE')
        self.db.maintenance.delete(self.preview(second['id']), 'DELETE')
        self.assertEqual(before + 2, len(list(folder.glob('*.db'))))
        self.assert_integrity()

    def test_injected_failure_after_dependents_delete_rolls_back_everything(self):
        self.add(); self.audit(1); self.curate(evidence=True)
        set_uuid = self.db.working_sets.create('Batch')
        self.db.working_sets.add_requests(set_uuid, ['Example'])
        item = self.db.working_sets.items(set_uuid)[0]
        self.db.working_sets.pin(item['working_set_item_uuid'], 1, self.db.latest_audit(1)['id'])
        with self.db.con() as c:
            c.execute('''CREATE TRIGGER block_work_delete BEFORE DELETE ON works
                BEGIN SELECT RAISE(ABORT, 'injected failure'); END''')
        preview = self.preview(); before = self.counts()
        with self.assertRaisesRegex(sqlite3.DatabaseError, 'injected failure'):
            self.db.maintenance.delete(preview, 'DELETE')
        self.assertEqual(before, self.counts())
        self.assertIsNotNone(self.db.working_sets.item(item['working_set_item_uuid'])['pinned_audit_id'])
        self.assert_integrity()

    def test_stale_audit_and_membership_previews_fail_before_backup(self):
        self.add(); preview = self.preview(); self.audit(1)
        with self.assertRaisesRegex(ValueError, 'changed after preview'):
            self.db.maintenance.delete(preview, 'DELETE')
        set_uuid = self.db.working_sets.create('Batch')
        preview = self.preview()
        self.db.working_sets.add_requests(set_uuid, ['Example'])
        item = self.db.working_sets.items(set_uuid)[0]
        self.db.working_sets.pin(item['working_set_item_uuid'], 1, self.db.latest_audit(1)['id'])
        backups_before = list((self.path.parent / 'backups').glob('*.db'))
        with self.assertRaisesRegex(ValueError, 'changed after preview'):
            self.db.maintenance.delete(preview, 'DELETE')
        self.assertEqual(backups_before, list((self.path.parent / 'backups').glob('*.db')))

    def test_database_switch_preview_is_rejected(self):
        self.add(); preview = self.preview()
        other = ddk.DB(self.path.parent / 'another.db', role='TEST')
        other.add_titles(['Example'], 'standard', 'en')
        with self.assertRaisesRegex(ValueError, 'Database changed'):
            other.maintenance.delete(preview, 'DELETE')
        self.assertEqual(1, self.counts()['works'])
        self.assertEqual(1, len(other.works()))

    def test_unrelated_database_write_invalidates_open_preview(self):
        self.add(); self.add('Other')
        preview = self.preview()
        backups_before = list((self.path.parent / 'backups').glob('*.db'))
        with self.db.con() as c:
            c.execute("UPDATE works SET lifecycle_status='REVIEWING' WHERE id=2")
        with self.assertRaisesRegex(ValueError, 'changed after preview'):
            self.db.maintenance.delete(preview, 'DELETE')
        self.assertEqual(2, self.counts()['works'])
        self.assertEqual(backups_before, list((self.path.parent / 'backups').glob('*.db')))

    def test_uuid_targeting_does_not_use_title_ambiguously(self):
        target = self.add('Same', 'standard')
        sibling = self.add('Same', 'official_color')
        self.db.maintenance.delete(self.db.maintenance.preview(target['work_uuid']), 'DELETE')
        self.assertIsNone(self.db.work(target['id']))
        self.assertEqual(sibling['work_uuid'], self.db.work(sibling['id'])['work_uuid'])

    def test_unknown_owned_foreign_key_fails_closed(self):
        self.add()
        with self.db.con() as c:
            c.execute('CREATE TABLE new_dependent(work_id INTEGER REFERENCES works(id))')
        with self.assertRaisesRegex(ValueError, 'Unknown catalog dependency'):
            self.preview()

    def test_remove_from_working_set_remains_non_destructive(self):
        work = self.add(); self.audit(1)
        set_uuid = self.db.working_sets.create('Batch')
        self.db.working_sets.add_requests(set_uuid, ['Example'])
        item = self.db.working_sets.items(set_uuid)[0]
        self.db.working_sets.pin(item['working_set_item_uuid'], 1, self.db.latest_audit(1)['id'])
        self.db.working_sets.remove_item(item['working_set_item_uuid'])
        self.assertIsNotNone(self.db.work(work['id']))
        self.assertIsNotNone(self.db.latest_audit(work['id']))
        self.assertEqual([], self.db.working_sets.items(set_uuid))


if __name__ == '__main__': unittest.main()
