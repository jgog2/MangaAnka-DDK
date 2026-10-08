"""Exact membership forcing through the real offline audit pipeline."""
import json
from pathlib import Path
import queue
import tempfile
import unittest
from unittest.mock import patch
import mangaanka_database_development_kit as ddk
from test_working_set_audit_recovery import offline_pipeline, publication


def seed(db,title='Monster'):
    db.add_titles([title],'standard','en')
    wid=db.works()[0]['id']
    aid=db.save_audit(wid,dict(query=title,match_title=title,publication=publication(title)),[])
    sid=db.working_sets.create('Force audit fixture');db.working_sets.set_active(sid)
    db.working_sets.add_requests(sid,[title])
    uid=db.working_sets.items(sid)[0]['working_set_item_uuid']
    db.working_sets.pin(uid,wid,aid)
    return wid,aid,sid,uid


class ForceReaudit(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.db=ddk.DB(Path(temp.name)/'force.db',role='TEST')
        self.wid,self.old,self.sid,self.uid=seed(self.db)
        self.auditor=ddk.SearchAuditor(self.db,queue.Queue())

    def run_force(self):
        self.db.working_sets.queue_force_audit(self.uid)
        with offline_pipeline(self.auditor):self.auditor.audit_many([self.uid],'volume')
        return self.db.working_sets.item(self.uid)

    def status(self,state):
        with self.db.con() as c:c.execute('UPDATE working_set_items SET processing_status=? WHERE working_set_item_uuid=?',(state,self.uid))

    def test_current_review_gets_new_immutable_audit_and_pin(self):
        self.status('REVIEW')
        self.assertEqual([],self.db.working_sets.run_candidates(self.sid))
        prior=dict(self.db.audit(self.old,self.wid))
        item=self.run_force()
        self.assertGreater(item['pinned_audit_id'],self.old)
        self.assertEqual(2,item['pinned_audit_revision'])
        self.assertEqual(prior,dict(self.db.audit(self.old,self.wid)))
        with self.db.con() as c:self.assertEqual(2,c.execute('SELECT count(*) FROM search_audits').fetchone()[0])

    def test_pipeline_failure_preserves_old_pin_and_history(self):
        prior=dict(self.db.audit(self.old,self.wid))
        self.db.working_sets.queue_force_audit(self.uid)
        with patch.object(self.auditor,'_parallel_provider_search',side_effect=RuntimeError('Offline failure')):
            self.auditor.audit_many([self.uid],'volume')
        item=self.db.working_sets.item(self.uid)
        self.assertEqual('ERROR',item['processing_status']);self.assertEqual(self.old,item['pinned_audit_id'])
        self.assertEqual(prior,dict(self.db.audit(self.old,self.wid)))
        self.assertEqual(self.old,self.db.latest_audit(self.wid)['id'])

    def test_pin_failure_rolls_back_new_audit(self):
        self.db.working_sets.queue_force_audit(self.uid)
        with offline_pipeline(self.auditor),patch.object(self.db.working_sets,'pin',side_effect=RuntimeError('Pin failure')):
            self.auditor.audit_many([self.uid],'volume')
        self.assertEqual(self.old,self.db.latest_audit(self.wid)['id'])
        self.assertEqual(self.old,self.db.working_sets.item(self.uid)['pinned_audit_id'])
        self.assertEqual('ERROR',self.db.working_sets.item(self.uid)['processing_status'])

    def test_curation_evidence_and_effective_mapping_survive(self):
        # MF Ghost 275 -> 23 uses the real curation boundary of the offline pipeline.
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        db=ddk.DB(Path(temp.name)/'curated.db',role='TEST');wid,old,sid,uid=seed(db,'MF Ghost')
        db.catalog.apply(db.catalog.preview(wid,[dict(entity='chapter',key='275',field='volume',value='23',verification='VERIFIED'),
            dict(entity='chapter',key='275',field='source_note',value='Reviewed publisher TOC'),
            dict(entity='evidence',key='publisher-proof',field='add',target_key='275',source_name='Publisher',source_url='https://example.org/toc')]))
        before=db.catalog.state(wid);history=db.catalog.history(wid)
        db.working_sets.queue_force_audit(uid);auditor=ddk.SearchAuditor(db,queue.Queue())
        with offline_pipeline(auditor):auditor.audit_many([uid],'volume')
        self.assertEqual(before,db.catalog.state(wid));self.assertEqual(history,db.catalog.history(wid))
        self.assertGreater(db.working_sets.item(uid)['pinned_audit_id'],old)
        self.assertEqual('23',db.catalog.rows(wid)[0]['effective']['volume'])

    def test_accepted_becomes_stale_without_new_acceptance(self):
        self.db.working_sets.accept([self.uid]);self.assertEqual('CURRENT',self.db.acceptance.state(self.wid))
        with self.db.con() as c:before=[dict(r) for r in c.execute('SELECT * FROM catalog_acceptances')]
        item=self.run_force()
        self.assertGreater(item['pinned_audit_id'],self.old);self.assertNotEqual('ACCEPTED',item['processing_status'])
        self.assertEqual('STALE',self.db.acceptance.state(self.wid))
        with self.db.con() as c:self.assertEqual(before,[dict(r) for r in c.execute('SELECT * FROM catalog_acceptances')])

    def test_ready_state_comes_from_fresh_results(self):
        self.assertEqual('READY',self.db.working_sets.item(self.uid)['processing_status'])
        self.assertEqual('READY',self.run_force()['processing_status'])
        self.status('READY');self.db.working_sets.queue_force_audit(self.uid)
        bad=publication('Monster');bad['unmapped_chapters']=1;bad['mapped_chapters']=0;bad['projection'][0]['_effective_volume']=None
        with offline_pipeline(self.auditor),patch.object(ddk,'resolve_publication',return_value=bad):
            self.auditor.audit_many([self.uid],'volume')
        self.assertEqual('REVIEW',self.db.working_sets.item(self.uid)['processing_status'])

    def test_error_and_rejected_are_eligible(self):
        for state in ('ERROR','REJECTED'):
            with self.subTest(state=state):
                old=self.db.working_sets.item(self.uid)['pinned_audit_id'];self.status(state)
                self.assertGreater(self.run_force()['pinned_audit_id'],old)

    def test_other_membership_pin_is_not_advanced(self):
        other=self.db.working_sets.create('Other set');self.db.working_sets.add_requests(other,['Monster'])
        other_uid=self.db.working_sets.items(other)[0]['working_set_item_uuid']
        self.db.working_sets.pin(other_uid,self.wid,self.old)
        self.run_force()
        self.assertEqual(self.old,self.db.working_sets.item(other_uid)['pinned_audit_id'])
        self.assertEqual(1,self.db.working_sets.item(other_uid)['pinned_audit_revision'])

    def test_unstable_duplicate_and_missing_items_rejected(self):
        for state in ('PENDING','QUEUED','AUDITING','DUPLICATE'):
            with self.subTest(state=state):
                self.status(state)
                with self.assertRaises(ValueError):self.db.working_sets.queue_force_audit(self.uid)
                self.assertEqual(self.old,self.db.latest_audit(self.wid)['id'])
        for value in (None,self.wid,'missing'):
            with self.assertRaises(ValueError):self.db.working_sets.queue_force_audit(value)

    def test_queue_claim_rejects_duplicate_start(self):
        self.db.working_sets.queue_force_audit(self.uid)
        with self.assertRaises(ValueError):self.db.working_sets.queue_force_audit(self.uid)
        self.assertEqual(self.old,self.db.working_sets.item(self.uid)['pinned_audit_id'])

    def test_inactive_and_protected_sets_rejected(self):
        other=self.db.working_sets.create('Inactive');self.db.working_sets.set_active(other)
        with self.assertRaises(ValueError):self.db.working_sets.queue_force_audit(self.uid)
        self.db.working_sets.set_active(self.sid);self.db.working_sets.accept([self.uid])
        self.db.working_sets.set_status(self.sid,'COMPLETE')
        with self.assertRaises(ValueError):self.db.working_sets.queue_force_audit(self.uid)

    def test_normal_candidates_and_retry_behavior_unchanged(self):
        self.assertEqual([],self.db.working_sets.run_candidates(self.sid))
        self.status('REVIEW');self.assertEqual([],self.db.working_sets.run_candidates(self.sid))
        self.status('ERROR');self.assertEqual([self.uid],self.db.working_sets.retry_errors(self.sid))
        self.assertEqual([self.uid],self.db.working_sets.run_candidates(self.sid))

    def test_cancellation_preserves_previous_pin(self):
        self.db.working_sets.queue_force_audit(self.uid)
        with patch.object(self.auditor,'audit_one',side_effect=ddk.CancelledError()):self.auditor.audit_many([self.uid],'volume')
        item=self.db.working_sets.item(self.uid)
        self.assertEqual('QUEUED',item['processing_status']);self.assertEqual(self.old,item['pinned_audit_id'])


if __name__=='__main__':unittest.main()
