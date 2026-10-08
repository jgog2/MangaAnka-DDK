"""Existing Grammar 3 authority exported without catalog writes."""
import json
import unittest
from unittest.mock import patch

import test_catalog as fixtures
from test_working_sets import publication
from ddk_commands import parse_batch
from ddk_exports import working_set_packet
from ddk_review import database_revision, review_packet
import ddk_exports


class WorkingSetReviewGuards(unittest.TestCase):
    def setUp(self):
        fixtures.CatalogCase.setUp(self)
        self.sid = self.db.working_sets.create('Guard export fixture')
        self.db.working_sets.add_requests(self.sid, ['Example', 'Unlinked'])
        self.uid = self.db.working_sets.items(self.sid)[0]['working_set_item_uuid']
        self.db.working_sets.pin(self.uid, 1, self.db.latest_audit(1)['id'], ready=True)

    resolve = fixtures.CatalogCase.resolve
    refresh = fixtures.CatalogCase.refresh
    edit = fixtures.CatalogCase.edit

    def entry(self, mode='pinned'):
        return working_set_packet(self.db, self.sid, mode)['entries'][0]

    def guard(self, mode='pinned'):
        return parse_batch(self.entry(mode)['review_guard']['command'] +
                           '\nset volume 24 chapter 222')[0]

    def preview(self, guard=None, wid=1):
        return self.store.preview(wid, [dict(entity='chapter', key='222', field='volume', value='24')],
                                  guard=guard or self.guard())

    def test_current_pinned_guard_matches_existing_per_work_authority(self):
        entry = self.entry(); guard = entry['review_guard']
        existing = review_packet(self.db, work_ids={1})['works'][0]
        self.assertEqual(existing['guard'], guard['command'])
        self.assertEqual(database_revision(self.db), guard['database_revision'])
        self.assertEqual((1, self.db.work(1)['work_uuid'], 'standard', 'en'),
            tuple(guard[k] for k in ('work_id', 'work_uuid', 'edition', 'language')))
        self.assertTrue(guard['audit_is_current'])
        self.assertEqual(entry['audit']['id'], self.preview()['audit_id'])

    def test_reaudit_changes_guard_and_pinned_export_preserves_old_guard_scope(self):
        old = self.guard(); self.refresh()
        self.assertEqual(old['audit_id'], self.guard()['audit_id'])
        current = self.guard('current')
        self.assertGreater(current['audit_id'], old['audit_id'])
        self.assertGreater(current['audit_revision'], old['audit_revision'])
        self.assertFalse(self.entry()['review_guard']['audit_is_current'])
        with self.assertRaisesRegex(ValueError, 'Stale'): self.preview(old)
        self.preview(current)

    def test_curation_changes_existing_event_token_and_dependency(self):
        old = self.guard(); self.store.apply(self.preview(old))
        new = self.entry()['review_guard']
        self.assertEqual(1, new['curation_revision'])
        self.assertEqual(0, new['audit_curation_revision'])
        self.assertNotEqual(old['database_revision'], new['database_revision'])
        with self.assertRaisesRegex(ValueError, 'Stale'): self.preview(old)

    def test_wrong_database_uuid_rejected(self):
        g = self.guard(); g['database_uuid'] = '00000000-0000-0000-0000-000000000000'
        with self.assertRaisesRegex(ValueError, 'Stale'): self.preview(g)

    def test_wrong_audit_id_rejected(self):
        g = self.guard(); g['audit_id'] += 100
        with self.assertRaisesRegex(ValueError, 'Stale'): self.preview(g)

    def test_wrong_revision_rejected(self):
        g = self.guard(); g['audit_revision'] += 1
        with self.assertRaisesRegex(ValueError, 'Stale'): self.preview(g)

    def test_stale_database_token_rejected(self):
        g = self.guard(); g['database_revision'] = 'a0-e0-d0-w0'
        with self.assertRaisesRegex(ValueError, 'Stale'): self.preview(g)

    def test_other_working_set_item_cannot_reuse_work_guard(self):
        old = self.guard()
        self.db.add_titles(['Other'], 'standard', 'en')
        self.db.save_audit(2, dict(query='Other', publication=publication('fixture:other')), [])
        self.db.working_sets.add_requests(self.sid, ['Other'])
        item = self.db.working_sets.items(self.sid)[-1]
        self.db.working_sets.pin(item['working_set_item_uuid'], 2, self.db.latest_audit(2)['id'], ready=True)
        old['database_revision'] = database_revision(self.db)
        with self.assertRaisesRegex(ValueError, 'Stale'): self.preview(old, 2)

    def test_other_edition_or_language_cannot_reuse_guard(self):
        for edition, language in (('official_color', 'en'), ('standard', 'ja')):
            self.db.add_titles(['Example'], edition, language)
            wid = self.db.works()[-1]['id']
            self.db.save_audit(wid, dict(query='Example', publication=publication(edition=edition)), [])
            g = self.guard()
            with self.assertRaisesRegex(ValueError, 'Stale'): self.preview(g, wid)

    def test_accepted_work_scope_does_not_advance_acceptance(self):
        self.db.add_titles(['Clean'],'standard','en')
        self.db.save_audit(2,dict(query='Clean',publication=publication('fixture:clean')),[])
        self.db.working_sets.add_requests(self.sid,['Clean'])
        uid=self.db.working_sets.items(self.sid)[-1]['working_set_item_uuid']
        self.db.working_sets.pin(uid,2,self.db.latest_audit(2)['id'])
        self.db.working_sets.accept([uid])  # Explicit human action simulated only in this fixture.
        with self.db.con() as c: before=list(c.execute('SELECT * FROM catalog_acceptances'))
        entry=working_set_packet(self.db,self.sid)['entries'][-1]
        self.assertEqual(self.db.work(2)['work_uuid'],entry['review_guard']['work_uuid'])
        self.assertEqual('CURRENT',self.db.acceptance.state(2))
        with self.db.con() as c: self.assertEqual(before,list(c.execute('SELECT * FROM catalog_acceptances')))

    def test_unlinked_item_has_no_mutation_guard(self):
        entry = working_set_packet(self.db, self.sid)['entries'][1]
        self.assertIsNone(entry['review_guard'])

    def test_unresolved_observation_has_no_fabricated_work_scope(self):
        uid = self.db.working_sets.items(self.sid)[1]['working_set_item_uuid']
        self.db.working_sets.observe_unresolved(uid, dict(query='Unlinked'), [])
        entry = working_set_packet(self.db, self.sid)['entries'][1]
        self.assertIsNotNone(entry['unresolved_observation'])
        self.assertIsNone(entry['review_guard'])

    def test_export_and_preview_perform_zero_database_mutation(self):
        with self.db.con() as c: before = '\n'.join(c.iterdump())
        self.preview()
        with self.db.con() as c: self.assertEqual(before, '\n'.join(c.iterdump()))

    def test_packet_is_additive_and_old_entries_remain_readable(self):
        packet = working_set_packet(self.db, self.sid)
        self.assertEqual(('mangaanka-ddk-working-set-review-v1', 'pinned', 4),
            (packet['format'], packet['mode'], packet['command_grammar_version']))
        old = json.loads(json.dumps(packet))
        for entry in old['entries']: entry.pop('review_guard', None)
        self.assertEqual([e['audit'] for e in old['entries']], [e['audit'] for e in packet['entries']])

    def test_guard_rechecked_at_apply_after_export_preview(self):
        preview = self.preview()
        self.refresh()
        with self.assertRaisesRegex(ValueError, 'Stale'): self.store.apply(preview)

    def test_concurrent_writer_cannot_mix_export_snapshot_dependencies(self):
        # WAL is fixture-only, allowing a second connection to commit while the
        # exporter holds its read snapshot. Product journal settings stay intact.
        with self.db.con() as c: c.execute('PRAGMA journal_mode=WAL')
        original=ddk_exports.review_guard
        before=database_revision(self.db)
        def interleave(db,wid,audit,con=None):
            self.assertTrue(con.in_transaction)
            self.db.add_titles(['Concurrent work'],'standard','en')
            return original(db,wid,audit,con=con)
        with patch.object(ddk_exports,'review_guard',side_effect=interleave):
            packet=working_set_packet(self.db,self.sid)
        guard=packet['entries'][0]['review_guard']
        self.assertEqual(before,packet['database_revision'])
        self.assertEqual(before,guard['database_revision'])
        self.assertNotEqual(before,database_revision(self.db))
        with self.assertRaisesRegex(ValueError,'Stale'):
            self.preview(parse_batch(guard['command']+'\nset volume 24 chapter 222')[0])

    def test_corrupt_pin_to_other_work_fails_closed(self):
        self.db.add_titles(['Other'],'standard','en')
        self.db.save_audit(2,dict(query='Other',publication=publication('fixture:other')),[])
        with self.db.con() as c:
            c.execute('UPDATE working_set_items SET pinned_audit_id=? WHERE working_set_item_uuid=?',
                      (self.db.latest_audit(2)['id'],self.uid))
        with self.assertRaisesRegex(ValueError,'does not belong'):
            self.entry()


if __name__ == '__main__': unittest.main()
