"""Disposable transaction tracing; never connects to the user's live catalog."""
from contextlib import contextmanager, closing
import json
import itertools
from pathlib import Path
import queue
import sqlite3
import tempfile
import threading
import traceback
import unittest
from unittest.mock import patch

import mangaanka_database_development_kit as ddk
from test_force_reaudit import seed
from test_working_set_audit_recovery import offline_pipeline, publication


@contextmanager
def large_offline_pipeline(auditor):
    with offline_pipeline(auditor):
        original=ddk.resolve_publication
        def large(*args,**kwargs):
            result=original(*args,**kwargs)
            result['diagnostic_fixture_padding']='x'*4000000
            return result
        with patch.object(ddk,'resolve_publication',side_effect=large):yield


class SQLTrace:
    def __init__(self, db):
        self.db=db;self.events=[];self.active={};self.fail=None;self.pause=None
        self.real_connect=sqlite3.connect;self._ids=itertools.count(1)

    @contextmanager
    def enabled(self):
        trace=self
        class Connection(sqlite3.Connection):
            def execute(self,sql,parameters=()):
                event={'connection':self.number,'thread':threading.get_ident(),
                       'sql':' '.join(sql.split()),'in_transaction':self.in_transaction,
                       'other_transactions':[n for n,c in trace.active.copy().items()
                                             if c is not self and c.in_transaction]}
                trace.events.append(event)
                if trace.pause:trace.pause(event,self)
                if trace.fail and trace.fail(event):raise RuntimeError('Injected '+trace.stage)
                try:return super().execute(sql,parameters)
                except sqlite3.OperationalError as exc:
                    event['error']=str(exc);event['traceback']=''.join(traceback.format_stack(limit=20))+traceback.format_exc();raise
            def close(self):
                trace.events.append(dict(connection=self.number,thread=threading.get_ident(),
                                         sql='CLOSE',in_transaction=self.in_transaction))
                trace.active.pop(self.number,None);super().close()
        def connect(path,*args,**kwargs):
            if Path(path).resolve()!=trace.db.path:return trace.real_connect(path,*args,**kwargs)
            kwargs['factory']=Connection
            c=trace.real_connect(path,*args,**kwargs);c.number=next(trace._ids)
            trace.active[c.number]=c
            trace.events.append(dict(connection=c.number,thread=threading.get_ident(),sql='OPEN',
                                     isolation_level=c.isolation_level,opened_at=traceback.format_stack(limit=10)))
            c.set_trace_callback(lambda sql:trace.events.append(dict(connection=c.number,
                thread=threading.get_ident(),sql=sql)) if sql in ('BEGIN ','BEGIN','COMMIT','ROLLBACK') else None)
            return c
        with patch.object(ddk.sqlite3,'connect',side_effect=connect):yield self


class ForceTransactions(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.db=ddk.DB(Path(tmp.name)/'transactions.db',role='TEST')
        self.wid,self.old,self.sid,self.uid=seed(self.db)
        self.auditor=ddk.SearchAuditor(self.db,queue.Queue());self.trace=SQLTrace(self.db)

    def run_force(self):
        self.db.working_sets.queue_force_audit(self.uid)
        with large_offline_pipeline(self.auditor):self.auditor.audit_many([self.uid],'volume')

    def audit_count(self):
        with self.db.con() as c:return c.execute('SELECT count(*) FROM search_audits').fetchone()[0]

    def test_real_force_trace_releases_claim_before_long_work(self):
        seen=[]
        with self.trace.enabled(),offline_pipeline(self.auditor):
            original=self.auditor._parallel_provider_search
            def search(*args,**kwargs):
                seen.append(self.db.working_sets.item(self.uid)['processing_status'])
                self.assertFalse(any(c.in_transaction for c in self.trace.active.values()))
                self.assertEqual({},self.trace.active)
                return original(*args,**kwargs)
            self.db.working_sets.queue_force_audit(self.uid)
            with patch.object(self.auditor,'_parallel_provider_search',side_effect=search):
                self.auditor.audit_many([self.uid],'volume')
        self.assertEqual(['AUDITING'],seen);self.assertEqual({},self.trace.active)
        self.assertFalse(any(e.get('error') for e in self.trace.events))
        self.assertGreater(self.db.working_sets.item(self.uid)['pinned_audit_id'],self.old)

    def test_negative_control_detects_nested_connection_self_lock(self):
        # Deliberately manufacture the proposed anti-pattern. This is NOT a
        # reproduction of the unmodified application workflow.
        with self.trace.enabled(),self.db.lock,self.db.con() as owner:
            owner.execute('BEGIN IMMEDIATE')
            self.trace.pause=lambda event,c:c.execute('PRAGMA busy_timeout=20') if event['sql']=='BEGIN IMMEDIATE' and c is not owner else None
            with self.assertRaisesRegex(sqlite3.OperationalError,'database is locked'):
                self.db.working_sets.set_item_status(self.uid,'AUDITING')
            failure=next(e for e in self.trace.events if e.get('error'))
            self.assertEqual('BEGIN IMMEDIATE',failure['sql'])
            self.assertEqual([owner.number],failure['other_transactions'])
            self.assertEqual(threading.get_ident(),failure['thread'])
            self.trace.pause=None
        self.assertEqual({},self.trace.active)
        self.run_force();self.assertEqual(2,self.audit_count())

    def test_sequential_force_preserves_two_immutable_audits(self):
        before=dict(self.db.audit(self.old,self.wid))
        self.run_force();first=self.db.working_sets.item(self.uid)['pinned_audit_id']
        first_record=dict(self.db.audit(first,self.wid))
        self.run_force();second=self.db.working_sets.item(self.uid)['pinned_audit_id']
        self.assertEqual((self.old+1,self.old+2),(first,second))
        self.assertEqual(before,dict(self.db.audit(self.old,self.wid)))
        self.assertEqual(first_record,dict(self.db.audit(first,self.wid)))
        self.assertEqual(3,self.audit_count());self.assertEqual(3,self.db.working_sets.item(self.uid)['pinned_audit_revision'])

    def test_gui_read_and_second_writer_during_long_work(self):
        entered=threading.Event();release=threading.Event();errors=[]
        def search(*args,**kwargs):
            entered.set();self.assertTrue(release.wait(4));raise RuntimeError('Provider fixture ended')
        def work():
            try:self.auditor.audit_many([self.uid],'volume')
            except Exception as exc:errors.append(exc)
        self.db.working_sets.queue_force_audit(self.uid)
        with patch.object(self.auditor,'_parallel_provider_search',side_effect=search):
            thread=threading.Thread(target=work);thread.start()
            try:
                self.assertTrue(entered.wait(4))
                self.assertEqual(self.old,self.db.latest_audit(self.wid)['id'])
                self.assertEqual('AUDITING',self.db.working_sets.item(self.uid)['processing_status'])
                self.db.working_sets.create('Independent writer during provider work')
            finally:release.set();thread.join(5)
        self.assertFalse(thread.is_alive());self.assertEqual([],errors)
        self.assertEqual('ERROR',self.db.working_sets.item(self.uid)['processing_status'])
        self.run_force();self.assertEqual(2,self.audit_count())

    def test_second_writer_serialized_during_persistence(self):
        entered=threading.Event();release=threading.Event();second_done=threading.Event();errors=[]
        def pause(event,c):
            if event['sql'].startswith('INSERT INTO search_audits('):
                entered.set();self.assertTrue(release.wait(4))
        def run():
            try:self.run_force()
            except Exception as exc:errors.append(exc)
        def second():
            try:self.db.working_sets.create('Serialized writer');second_done.set()
            except Exception as exc:errors.append(exc)
        self.trace.pause=pause
        with self.trace.enabled():
            thread=threading.Thread(target=run);thread.start();writer=None
            try:
                self.assertTrue(entered.wait(4));writer=threading.Thread(target=second);writer.start()
                self.assertFalse(second_done.wait(.05))
                self.assertEqual(self.old,self.db.latest_audit(self.wid)['id'])
            finally:
                release.set();thread.join(5)
                if writer:writer.join(5)
        self.assertEqual([],errors);self.assertTrue(second_done.is_set());self.assertEqual({},self.trace.active)
        self.assertEqual(2,self.audit_count())

    def test_stranded_auditing_recovery_preserves_pin(self):
        self.db.working_sets.set_item_status(self.uid,'AUDITING')
        self.assertEqual(1,self.db.working_sets.recover_interrupted())
        self.assertEqual('QUEUED',self.db.working_sets.item(self.uid)['processing_status'])
        self.assertEqual(self.old,self.db.working_sets.item(self.uid)['pinned_audit_id'])
        with offline_pipeline(self.auditor):self.auditor.audit_many([self.uid],'volume')
        self.assertEqual(2,self.audit_count())

    def test_run_working_set_and_retry_errors_share_safe_path(self):
        self.db.working_sets.set_item_status(self.uid,'QUEUED')
        with self.trace.enabled(),large_offline_pipeline(self.auditor):
            self.auditor.audit_many(self.db.working_sets.run_candidates(self.sid),'volume')
        self.assertEqual(2,self.audit_count())
        self.db.working_sets.set_item_status(self.uid,'ERROR')
        with self.trace.enabled(),large_offline_pipeline(self.auditor):
            self.auditor.audit_many(self.db.working_sets.retry_errors(self.sid),'volume')
        self.assertEqual(3,self.audit_count());self.assertFalse(any(e.get('error') for e in self.trace.events))

    def test_exact_item_and_unrelated_pins_remain_unchanged(self):
        other=self.db.working_sets.create('Unrelated pins')
        self.db.working_sets.add_requests(other,['MF Ghost','Fire Force','Monster'])
        for title in ('MF Ghost','Fire Force'):
            self.db.add_titles([title],'standard','en')
            wid=next(r['id'] for r in self.db.works() if r['input_title']==title)
            aid=self.db.save_audit(wid,dict(query=title,publication=publication(title)),[])
            uid=next(i['working_set_item_uuid'] for i in self.db.working_sets.items(other) if i['original_query']==title)
            self.db.working_sets.pin(uid,wid,aid)
        uid=next(i['working_set_item_uuid'] for i in self.db.working_sets.items(other) if i['original_query']=='Monster')
        self.db.working_sets.pin(uid,self.wid,self.old)
        before=self.db.working_sets.items(other)
        self.run_force();after=self.db.working_sets.items(other)
        self.assertEqual(before[:2],after[:2])
        # Another membership of the SAME global work keeps its old pin but
        # normal v7 recalculation flags that pin as superseded (READY -> REVIEW).
        self.assertEqual(before[2]['pinned_audit_id'],after[2]['pinned_audit_id'])
        self.assertEqual(before[2]['pinned_audit_revision'],after[2]['pinned_audit_revision'])

    def test_captured_dandadan_revision_five_keeps_canonical_special_result(self):
        from copy import deepcopy
        from test_canonical_specials import captured_dandadan
        from test_working_set_audit_recovery import CHAPTERS
        from ddk_publication import publication_holes
        pub,inventory=captured_dandadan()
        self.db.add_titles(['Dandadan'],'standard','en')
        wid=next(r['id'] for r in self.db.works() if r['input_title']=='Dandadan')
        holes=publication_holes(pub,inventory)
        old=self.db.save_audit(wid,dict(query='Dandadan',match_title='Dandadan',publication=pub),holes)
        self.db.working_sets.add_requests(self.sid,['Dandadan'])
        uid=next(i['working_set_item_uuid'] for i in self.db.working_sets.items(self.sid) if i['original_query']=='Dandadan')
        self.db.working_sets.pin(uid,wid,old)
        for revision in range(5):
            preview=self.db.catalog.preview(wid,[dict(entity='chapter',key='1',field='source_note',
                value='Disposable curation revision '+str(revision+1),verification='VERIFIED')])
            self.db.catalog.apply(preview)
        before=self.db.catalog.state(wid)
        def resolved(*args,**kwargs):
            self.assertFalse(any(c.in_transaction for c in self.trace.active.values()))
            kwargs['on_identity'](pub['catalog_identity'])
            result=deepcopy(pub);result['curation_revision']=5
            return result
        with patch.dict(CHAPTERS,{'Dandadan':tuple(str(n) for n in range(1,247)),'dand':()}),self.trace.enabled(),offline_pipeline(self.auditor), \
                patch.object(ddk,'resolve_publication',side_effect=resolved):
            self.db.working_sets.queue_force_audit(uid);self.auditor.audit_many([uid],'volume')
        item=self.db.working_sets.item(uid);self.assertGreater(item['pinned_audit_id'],old)
        audit=self.db.audit(item['pinned_audit_id'],wid);stored=json.loads(audit['publication_json'])
        self.assertEqual((246,2,248,2,219,221,27,0,25),tuple(stored[k] for k in (
            'canonical_main_chapters','recognized_specials','logical_chapters','classified_provider_artifacts',
            'mapped_main_chapters','mapped_chapters','uncompiled_chapters','unmapped_chapters','final_volumes')))
        self.assertEqual(dict(identity='PASS',publication='PASS',normalization='REVIEW',acquisition='PARTIAL'),json.loads(audit['health_json']))
        self.assertEqual(before,self.db.catalog.state(wid));self.assertEqual({},self.trace.active)

    def test_large_snapshot_force_has_no_nested_reader_lock(self):
        large=publication('Monster');large['diagnostic_fixture_padding']='x'*4000000
        self.db.working_sets.queue_force_audit(self.uid)
        with self.trace.enabled(),offline_pipeline(self.auditor),patch.object(ddk,'resolve_publication',return_value=large):
            self.auditor.audit_many([self.uid],'volume')
        item=self.db.working_sets.item(self.uid)
        self.assertGreater(item['pinned_audit_id'],self.old,
            str(self.db.working_sets.latest_observation(self.uid)))
        self.assertFalse(any(e.get('error') for e in self.trace.events))
        self.assertFalse(any(e.get('other_transactions') for e in self.trace.events
                             if e['sql']=='PRAGMA foreign_keys=ON'))
        self.assertEqual(2,self.audit_count());self.assertEqual({},self.trace.active)

    def test_cache_spill_control_proves_exclusive_writer_blocks_nested_reader(self):
        # A pager-level control, not a production PRAGMA change. Before a large
        # write a separate reader succeeds; after cache spill it is blocked.
        with self.db.con() as owner:
            owner.execute('BEGIN IMMEDIATE')
            with closing(sqlite3.connect(self.db.path,timeout=.02)) as reader:
                self.assertEqual(1,reader.execute('SELECT count(*) FROM search_audits').fetchone()[0])
            owner.execute('UPDATE search_audits SET provider_rows_json=? WHERE id=?',('x'*4000000,self.old))
            with closing(sqlite3.connect(self.db.path,timeout=.02)) as reader:
                with self.assertRaisesRegex(sqlite3.OperationalError,'database is locked'):
                    reader.execute('SELECT count(*) FROM search_audits').fetchone()
            owner.rollback()
        with self.db.con() as owner:
            owner.execute('PRAGMA cache_spill=OFF')
            owner.execute('BEGIN IMMEDIATE')
            owner.execute('UPDATE search_audits SET provider_rows_json=? WHERE id=?',('x'*4000000,self.old))
            with closing(sqlite3.connect(self.db.path,timeout=.02)) as reader:
                self.assertEqual(1,reader.execute('SELECT count(*) FROM search_audits').fetchone()[0])
            owner.rollback()

    def test_large_force_stales_acceptance_without_changing_decisions(self):
        self.db.working_sets.accept([self.uid]);self.assertEqual('CURRENT',self.db.acceptance.state(self.wid))
        with self.db.con() as c:before=[dict(r) for r in c.execute('SELECT * FROM catalog_acceptances')]
        self.run_force();self.assertEqual('STALE',self.db.acceptance.state(self.wid))
        with self.db.con() as c:self.assertEqual(before,[dict(r) for r in c.execute('SELECT * FROM catalog_acceptances')])

    def test_large_force_requeues_curation_race_without_duplicate_audit(self):
        self.db.working_sets.queue_force_audit(self.uid);calls=[]
        with large_offline_pipeline(self.auditor):
            original=ddk.resolve_publication
            def racing(*args,**kwargs):
                result=original(*args,**kwargs);calls.append(1)
                if len(calls)==1:
                    self.db.catalog.apply(self.db.catalog.preview(self.wid,[dict(entity='chapter',key='1',
                        field='source_note',value='Concurrent reviewed note',verification='VERIFIED')]))
                return result
            with patch.object(ddk,'resolve_publication',side_effect=racing):
                self.auditor.audit_many([self.uid],'volume')
        self.assertEqual(2,len(calls));self.assertEqual(2,self.audit_count())
        self.assertEqual(1,self.db.catalog.state(self.wid)['revision'])
        item=self.db.working_sets.item(self.uid);self.assertGreater(item['pinned_audit_id'],self.old)
        self.assertNotEqual('AUDITING',item['processing_status'])
        audit=self.db.audit(item['pinned_audit_id'],self.wid)
        self.assertEqual(1,json.loads(audit['publication_json'])['curation_revision'])

    def check_failure(self,stage):
        previous=dict(self.db.audit(self.old,self.wid));self.trace.stage=stage
        sql={'audit_insert':'INSERT INTO search_audits(', 'problem_insert':'INSERT INTO audit_holes(',
             'before_pin':'UPDATE working_set_items SET linked_work_uuid=',
             'after_audit_insert':'UPDATE search_audits SET ddk_version='}
        self.trace.fail=lambda e:stage in sql and e['sql'].startswith(sql[stage])
        large=publication('Monster');large['diagnostic_fixture_padding']='x'*4000000
        self.db.working_sets.queue_force_audit(self.uid)
        with self.trace.enabled(),offline_pipeline(self.auditor),patch.object(ddk,'resolve_publication',return_value=large),patch.object(ddk,'publication_holes',return_value=[
                dict(code='ACQUISITION_COVERAGE_GAP',severity='warning',message='Fixture')]):
            if stage=='before_provider':
                context=patch.object(self.auditor,'audit_one',side_effect=RuntimeError('Injected '+stage))
            elif stage=='during_provider':
                context=patch.object(self.auditor,'_parallel_provider_search',side_effect=RuntimeError('Injected '+stage))
            elif stage=='before_persistence':
                context=patch.object(self.db.working_sets,'persist_item_audit',side_effect=RuntimeError('Injected '+stage))
            else:
                from contextlib import nullcontext
                context=nullcontext()
            with context:self.auditor.audit_many([self.uid],'volume')
        item=self.db.working_sets.item(self.uid)
        self.assertEqual((self.old,'ERROR'),(item['pinned_audit_id'],item['processing_status']))
        self.assertEqual(previous,dict(self.db.audit(self.old,self.wid)));self.assertEqual(1,self.audit_count())
        with self.db.con() as c:self.assertEqual(0,c.execute('SELECT count(*) FROM audit_holes').fetchone()[0])
        observation=self.db.working_sets.latest_observation(self.uid)
        self.assertEqual('Injected '+stage,observation['record']['resolution_error'])
        self.assertEqual('AUDIT_ERROR',observation['holes'][0]['code']);self.assertEqual({},self.trace.active)
        self.trace.fail=None;self.run_force();self.assertEqual(2,self.audit_count())
        self.assertEqual(observation['id'],self.db.working_sets.latest_observation(self.uid)['id'])


for stage in ('before_provider','during_provider','before_persistence','audit_insert','problem_insert','before_pin','after_audit_insert'):
    def test(self,stage=stage):self.check_failure(stage)
    setattr(ForceTransactions,'test_failure_'+stage,test)

if __name__=='__main__':unittest.main()
