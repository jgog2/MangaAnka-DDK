"""Sequential batch forcing uses the real auditor with disposable offline inputs."""
import json
import queue
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtCore import Qt
from qt_app.workers import AuditWorker
import mangaanka_database_development_kit as ddk
from test_force_reaudit import seed
from test_force_transactions import SQLTrace
from test_working_set_audit_recovery import offline_pipeline,publication
from ddk_commands import parse
from ddk_review import GRAMMAR_VERSION
from ddk_writer_lock import WriterLock


class ForceAll(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.db=ddk.DB(Path(temp.name)/'batch.db',role='TEST')
        self.wid,self.old,self.sid,self.uid=seed(self.db)
        self.db.working_sets.add_requests(self.sid,['Fire Force','MF Ghost'])
        self.items=self.db.working_sets.items(self.sid)
        self.ids=[i['working_set_item_uuid'] for i in self.items]
        self.before={uid:dict(self.db.working_sets.item(uid)) for uid in self.ids}
        self.before_search=None;self.after_item=None;self.bad_title=None
        self.events=[]

    def factory(self,db,events):
        test=self
        class Offline(ddk.SearchAuditor):
            def audit_many(self,ids,workflow):
                with offline_pipeline(self):
                    search=self._parallel_provider_search
                    def controlled(query,*args,**kwargs):
                        if test.before_search:test.before_search(self,query)
                        if query==test.bad_title:raise RuntimeError('Injected provider failure')
                        return search(query,*args,**kwargs)
                    with patch.object(self,'_parallel_provider_search',side_effect=controlled):
                        super().audit_many(ids,workflow)
                if test.after_item:test.after_item(self,ids[0])
        return Offline(db,events)

    def run_batch(self,plan=None):
        plan=plan or self.db.working_sets.force_audit_plan(self.sid)
        self.worker=AuditWorker(self.db,[i['working_set_item_uuid'] for i in plan['items']],
            auditor_factory=self.factory,force_all_plan=plan)
        self.worker.event.connect(lambda k,p:self.events.append((k,p)),Qt.DirectConnection)
        self.worker.run()
        return self.worker.force_summary(final=True)

    def test_all_active_statuses_include_accepted_pending_queued_audited(self):
        for state in ('REVIEW','READY','ACCEPTED','REJECTED','ERROR','PENDING','QUEUED','AUDITED'):
            with self.subTest(state=state):
                with self.db.con() as c:c.execute('UPDATE working_set_items SET processing_status=? WHERE working_set_item_uuid=?',(state,self.uid))
                self.assertIn(self.uid,[i['working_set_item_uuid'] for i in self.db.working_sets.force_audit_plan(self.sid)['items']])
        self.assertEqual(3,len(self.run_batch()['new_audit_ids']))

    def test_all_success_immutable_audits_exact_pins_and_unrelated_set(self):
        other=self.db.working_sets.create('Unrelated');self.db.working_sets.add_requests(other,['Monster'])
        uid=self.db.working_sets.items(other)[0]['working_set_item_uuid'];self.db.working_sets.pin(uid,self.wid,self.old)
        outside=dict(self.db.working_sets.item(uid));old=dict(self.db.audit(self.old,self.wid))
        summary=self.run_batch()
        self.assertEqual((3,0,0),(summary['successful'],summary['failed'],summary['reused']))
        self.assertEqual(3,len(set(summary['new_audit_ids'])))
        self.assertEqual(old,dict(self.db.audit(self.old,self.wid)))
        current=self.db.working_sets.item(uid)
        self.assertEqual((outside['pinned_audit_id'],outside['pinned_audit_revision']),
                         (current['pinned_audit_id'],current['pinned_audit_revision']))
        for row in summary['results']:
            self.assertEqual(row['audit_id'],self.db.working_sets.item(row['working_set_item_uuid'])['pinned_audit_id'])
            self.assertIsNotNone(row['audit_revision'])
        batch_events=[p for k,p in self.events if k=='batch']
        self.assertEqual(self.ids,[p['work_id'] for p in batch_events])
        self.assertEqual(['1/3','2/3','3/3'],[p['text'].split('  ')[0] for p in batch_events])
        self.assertEqual(1,sum(k=='done' for k,p in self.events))

    def test_accepted_history_and_lifecycle_remain_while_approval_stales(self):
        self.db.working_sets.accept([self.uid])
        with self.db.con() as c:history=[dict(r) for r in c.execute('SELECT * FROM catalog_acceptances')]
        result=self.run_batch()['results'][0]
        self.assertEqual(('SUCCESS','STALE','READY'),(result['result'],result['acceptance'],result['set_state']))
        self.assertEqual('ACCEPTED',self.db.work(self.wid)['lifecycle_status'])
        with self.db.con() as c:self.assertEqual(history,[dict(r) for r in c.execute('SELECT * FROM catalog_acceptances')])

    def test_accepted_new_review_findings_visible_without_revocation(self):
        self.db.working_sets.accept([self.uid])
        pub=publication('Monster');pub['mapped_chapters']=0;pub['unmapped_chapters']=1
        pub['projection'][0]['_effective_volume']=None;pub['unmapped']=pub['projection']
        def research(auditor,query):
            if query=='Monster':
                # Existing resolver is patched inside offline_pipeline; alter its result only.
                original=ddk.resolve_publication.side_effect
                def resolve(*args,**kwargs):
                    original(*args,**kwargs)
                    return pub
                ddk.resolve_publication.side_effect=resolve
        self.before_search=research
        summary=self.run_batch();item=self.db.working_sets.item(self.uid)
        self.assertEqual('REVIEW',item['processing_status'])
        self.assertEqual('ACCEPTED',self.db.work(self.wid)['lifecycle_status'])
        self.assertEqual('STALE',self.db.acceptance.state(self.wid))
        with self.db.con() as c:self.assertTrue(c.execute('SELECT 1 FROM audit_holes WHERE audit_id=? AND code=?',
            (item['pinned_audit_id'],'UNMAPPED_CHAPTERS')).fetchone())
        self.assertEqual('SUCCESS',summary['results'][0]['result'])

    def test_curated_fields_evidence_and_history_preserved(self):
        self.db.catalog.apply(self.db.catalog.preview(self.wid,[
            dict(entity='chapter',key='1',field='volume',value='1',verification='VERIFIED'),
            dict(entity='evidence',key='proof',field='add',target_key='1',source_name='Publisher',source_url='https://example.org/toc')]))
        state=self.db.catalog.state(self.wid);history=self.db.catalog.history(self.wid)
        self.run_batch()
        self.assertEqual(state,self.db.catalog.state(self.wid));self.assertEqual(history,self.db.catalog.history(self.wid))

    def test_provider_failure_continues_old_pin_and_retry_succeeds(self):
        self.bad_title='Monster';result=self.run_batch()
        self.assertEqual((2,1),(result['successful'],result['failed']))
        item=self.db.working_sets.item(self.uid);self.assertEqual(self.old,item['pinned_audit_id'])
        self.assertEqual('ERROR',item['processing_status'])
        self.assertIn('Injected provider failure',self.db.working_sets.latest_observation(self.uid)['record']['resolution_error'])
        self.bad_title=None;self.assertEqual(3,self.run_batch()['successful'])

    def test_pin_failure_rolls_back_and_remaining_titles_run(self):
        original=self.db.working_sets.pin
        def pin(uid,*args,**kwargs):
            if uid==self.uid:raise RuntimeError('Injected pin failure')
            return original(uid,*args,**kwargs)
        with patch.object(self.db.working_sets,'pin',side_effect=pin):result=self.run_batch()
        self.assertEqual((2,1),(result['successful'],result['failed']))
        self.assertEqual(self.old,self.db.latest_audit(self.wid)['id'])
        self.assertEqual(self.old,self.db.working_sets.item(self.uid)['pinned_audit_id'])
        with self.db.con() as c:self.assertEqual(3,c.execute('SELECT count(*) FROM search_audits').fetchone()[0])

    def test_cancel_between_titles_leaves_unprocessed_exactly_unchanged(self):
        self.after_item=lambda auditor,uid:self.worker.cancel()
        summary=self.run_batch()
        self.assertEqual((1,0,2),(summary['successful'],summary['failed'],summary['not_run']))
        for uid in self.ids[1:]:self.assertEqual(self.before[uid],dict(self.db.working_sets.item(uid)))
        self.assertGreater(self.db.working_sets.item(self.uid)['pinned_audit_id'],self.old)

    def test_cancel_during_provider_rolls_back_current_and_leaves_rest_unchanged(self):
        self.before_search=lambda auditor,query:self.worker.cancel()
        summary=self.run_batch()
        self.assertEqual((0,1,2),(summary['successful'],summary['cancelled'],summary['not_run']))
        self.assertEqual(self.old,self.db.working_sets.item(self.uid)['pinned_audit_id'])
        self.assertEqual('QUEUED',self.db.working_sets.item(self.uid)['processing_status'])
        for uid in self.ids[1:]:self.assertEqual(self.before[uid],dict(self.db.working_sets.item(uid)))

    def test_removed_duplicate_and_auditing_items_excluded(self):
        self.db.working_sets.remove_item(self.ids[2])
        with self.db.con() as c:c.execute("UPDATE working_set_items SET processing_status='DUPLICATE' WHERE working_set_item_uuid=?",(self.ids[1],))
        plan=self.db.working_sets.force_audit_plan(self.sid)
        self.assertEqual([self.uid],[i['working_set_item_uuid'] for i in plan['items']])
        self.assertEqual([self.ids[1]],[i['working_set_item_uuid'] for i in plan['skipped']])
        with self.db.con() as c:c.execute("UPDATE working_set_items SET processing_status='AUDITING' WHERE working_set_item_uuid=?",(self.uid,))
        self.assertEqual([],self.db.working_sets.force_audit_plan(self.sid)['items'])

    def test_removed_after_confirmation_skipped_at_turn(self):
        plan=self.db.working_sets.force_audit_plan(self.sid)
        self.db.working_sets.remove_item(self.ids[1]);result=self.run_batch(plan)
        self.assertEqual((2,1),(result['successful'],result['skipped']))
        self.assertIsNone(self.db.working_sets.item(self.ids[1])['pinned_audit_id'])

    def test_no_write_transaction_during_provider_and_gui_reads_allowed(self):
        trace=SQLTrace(self.db)
        def check(auditor,query):
            self.assertFalse(any(c.in_transaction for c in trace.active.values()))
            self.db.working_sets.items(self.sid)
            self.db.working_sets.create('Independent short write '+query)
        self.before_search=check
        with trace.enabled():self.assertEqual(3,self.run_batch()['successful'])
        self.assertEqual({},trace.active)

    def test_curation_race_uses_existing_superseded_retry(self):
        calls=[]
        def curate(auditor,query):
            if not calls:
                calls.append(query)
                self.db.catalog.apply(self.db.catalog.preview(self.wid,[dict(entity='chapter',key='1',field='volume',value='1')]))
        self.before_search=curate;result=self.run_batch()
        self.assertEqual(3,result['successful'])
        self.assertEqual(1,self.db.catalog.state(self.wid)['revision'])
        with self.db.con() as c:self.assertEqual(4,c.execute('SELECT count(*) FROM search_audits').fetchone()[0])

    def test_second_sequential_batch_creates_distinct_history(self):
        first=self.run_batch();second=self.run_batch()
        self.assertEqual(3,second['successful']);self.assertTrue(set(first['new_audit_ids']).isdisjoint(second['new_audit_ids']))
        with self.db.con() as c:
            for aid in first['new_audit_ids']:self.assertIsNotNone(c.execute('SELECT 1 FROM search_audits WHERE id=?',(aid,)).fetchone())

    def test_writer_instance_lock_and_protected_set_guards_unchanged(self):
        first=WriterLock(self.db.path)
        try:
            with self.assertRaises(ValueError):WriterLock(self.db.path)
        finally:first.close()
        self.db.working_sets.set_status(self.sid,'ARCHIVED')
        with self.assertRaises(ValueError):self.db.working_sets.force_audit_plan(self.sid)

    def test_grammar_3_not_extended(self):
        self.assertEqual(4,GRAMMAR_VERSION);self.assertEqual('audit',parse('audit')['action'])
        with self.assertRaises(ValueError):parse('audit all')


if __name__=='__main__':unittest.main()
