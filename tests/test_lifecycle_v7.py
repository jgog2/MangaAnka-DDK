"""Lifecycle policy, transaction and snapshot regressions on disposable databases."""
from contextlib import contextmanager
import json
from pathlib import Path
import queue
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import mangaanka_database_development_kit as ddk
from ddk_schema import migrate_v7
from ddk_working_sets import AuditSuperseded
from ddk_exports import working_set_rows, catalog_context
from ddk_review import review_packet
from test_working_sets import publication as _publication
from test_working_set_audit_recovery import offline_pipeline
from test_pre_catalog_hardening import fixture as mf_fixture, ODD


def publication(*args,**kwargs):
    pub=_publication(*args,**kwargs)
    identity=pub['catalog_identity']
    identity['external_ids']={'fixture':identity['canonical_work_id'].split(':',1)[1]}
    return pub


def downgrade_fixture(db):
    """Reconstruct the original v6 constraint; preserve all child rows."""
    from test_supplementary_persistence import schema7
    schema7(db)
    with db.con() as c:
        c.execute('PRAGMA foreign_keys=OFF')
        c.execute('BEGIN IMMEDIATE')
        c.execute('DROP TABLE catalog_acceptances')
        c.execute('DROP INDEX works_canonical_unique_idx')
        c.execute('DROP INDEX working_set_duplicate_idx')
        c.execute('ALTER TABLE working_set_items DROP COLUMN duplicate_of_item_uuid')
        sql=c.execute("SELECT sql FROM sqlite_master WHERE name='works'").fetchone()[0]
        indexes=[r[0] for r in c.execute("SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='works' AND sql IS NOT NULL")]
        sql=sql.replace('CREATE TABLE "works"','CREATE TABLE works_v6').replace('CREATE TABLE works(', 'CREATE TABLE works_v6(')
        sql=sql.rstrip()[:-1]+', UNIQUE(input_title,edition,language))'
        c.execute(sql)
        c.execute('INSERT INTO works_v6 SELECT * FROM works')
        c.execute('DROP TABLE works')
        c.execute('ALTER TABLE works_v6 RENAME TO works')
        for statement in indexes:c.execute(statement)
        c.execute('PRAGMA user_version=6')


class LifecycleV7(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.path=Path(tmp.name)/'catalog.db'
        self.db=ddk.DB(self.path,role='TEST');self.ws=self.db.working_sets

    def seed(self,title='Series',canonical='fixture:series',holes=(),pub=None):
        self.db.add_titles([title],'standard','en')
        wid=next(w['id'] for w in self.db.works() if w['input_title']==title)
        self.save(wid,pub or publication(canonical=canonical),holes)
        return wid

    def save(self,wid,pub=None,holes=()):
        pub=pub or publication(canonical=self.db.work(wid)['canonical_work_id'])
        return self.db.save_audit(wid,{'query':self.db.work(wid)['input_title'],
            'publication':pub,'workflow':'volume'},list(holes))

    def membership(self,wid,name='Batch',query=None,pin=True):
        uid=self.ws.create(name);self.ws.add_requests(uid,[query or self.db.work(wid)['input_title']])
        item=self.ws.items(uid)[0]['working_set_item_uuid']
        if pin:self.ws.pin(item,wid,self.db.latest_audit(wid)['id'])
        return uid,item

    def history(self):
        with self.db.con() as c:return [dict(r) for r in c.execute('SELECT * FROM catalog_acceptances ORDER BY id')]

    def test_clean_normalization_review_and_partial_are_safe(self):
        wid=self.seed();uid,item=self.membership(wid)
        with self.db.con() as c:c.execute('UPDATE search_audits SET health_json=? WHERE work_id=?',
            (json.dumps(dict(identity='PASS',publication='PASS',normalization='REVIEW',acquisition='PARTIAL')),wid))
        result=self.db.acceptance.evaluate(wid,item)
        self.assertTrue(result['eligible'],result['blockers']);self.assertEqual(2,len(result['warnings']))
        self.assertEqual('READY',self.ws.item(item)['processing_status'])

    def test_problem_classes_and_actions_fail_closed(self):
        cases=[('NEW_UNKNOWN',None,None),('REFERENCE_CONFLICT',None,None),
               ('PROVIDER_RANGE_BUNDLE',None,None),('UNCLASSIFIED_ACQUISITION',None,None),
               ('CUSTOM_DATA','DATA','CURATION_READY'),('CUSTOM_IDENTITY','IDENTITY',None),
               ('CUSTOM_CODE','ACQUISITION','CODE_REVIEW_REQUIRED')]
        wid=self.seed()
        for code,cls,action in cases:
            with self.subTest(code=code):
                self.save(wid,holes=[dict(code=code,severity='warning',message='Unresolved')])
                if cls:
                    with self.db.con() as c:c.execute('UPDATE audit_holes SET problem_class=?,next_action=? WHERE audit_id=?',
                        (cls,action,self.db.latest_audit(wid)['id']))
                self.assertFalse(self.db.acceptance.evaluate(wid)['eligible'])
                with self.assertRaises(ValueError):self.db.acceptance.accept(work_ids=[wid])
        self.assertEqual([],self.history())

    def test_raw_unclassified_without_issue_row_cannot_escape_policy(self):
        pub=publication(canonical='fixture:series');pub['unclassified_acquisition']=[{'chapter':'999'}]
        wid=self.seed(pub=pub)
        self.assertFalse(self.db.acceptance.evaluate(wid)['eligible'])

    def test_mf_ghost_disposition_recalculates_membership_without_network(self):
        pub=mf_fixture(unmapped=False,odd=ODD)
        hole=dict(code='UNCLASSIFIED_ACQUISITION',severity='warning',message='Provider extras',details={'chapters':list(ODD)})
        wid=self.seed('MF Ghost','fixture:mf',[hole],pub);uid,item=self.membership(wid)
        audit_before=dict(self.db.latest_audit(wid));pin_before=self.ws.item(item)['pinned_audit_id']
        self.assertEqual((275,275,23,0),(audit_before['logical_chapters'],audit_before['mapped_chapters'],audit_before['final_volumes'],audit_before['unmapped_chapters']))
        self.assertEqual('REVIEW',self.ws.item(item)['processing_status'])
        with self.assertRaises(ValueError):self.ws.accept([item])
        self.assertEqual(audit_before,dict(self.db.latest_audit(wid)));self.assertEqual(pin_before,self.ws.item(item)['pinned_audit_id'])
        self.assertEqual('STAGED',self.db.work(wid)['lifecycle_status']);self.assertEqual([],self.history())
        problem=self.db.holes()[0]['id'];pin=self.ws.item(item)['pinned_audit_id']
        self.db.dispose_problem(problem,'Publisher contents confirms provider-only split record','VERIFIED',item_uuid=item)
        self.assertEqual('READY',self.ws.item(item)['processing_status']);self.assertEqual(pin,self.ws.item(item)['pinned_audit_id'])
        self.ws.accept([item]);self.assertEqual('CURRENT',self.db.acceptance.state(wid))
        self.ws.reopen_items([item])
        # Workflow reevaluation only changes audited/reviewed items, never a queued item.
        self.ws.pin(item,wid,pin)
        self.db.reopen_problem(problem,'New evidence disputes the classification',item_uuid=item)
        self.assertEqual('REVIEW',self.ws.item(item)['processing_status']);self.assertEqual('STALE',self.db.acceptance.state(wid))

    def test_disposition_signature_and_verification_are_required(self):
        wid=self.seed(holes=[dict(code='UNCLASSIFIED_ACQUISITION',severity='warning',message='Extra')])
        problem=self.db.holes()[0]['id'];self.db.dispose_problem(problem,'Publisher extra verified','VERIFIED')
        self.assertTrue(self.db.acceptance.evaluate(wid)['eligible'])
        with self.db.con() as c:c.execute("UPDATE problem_dispositions SET signature='wrong' WHERE problem_row_id=?",(problem,))
        self.assertFalse(self.db.acceptance.evaluate(wid)['eligible'])

    def test_shared_work_acceptance_changes_only_exact_membership(self):
        wid=self.seed();a,ia=self.membership(wid,'A');b,ib=self.membership(wid,'B')
        self.ws.accept([ia]);self.assertEqual('ACCEPTED',self.ws.item(ia)['processing_status'])
        self.assertEqual('READY',self.ws.item(ib)['processing_status'])
        self.ws.accept([ib]);self.assertEqual('ACCEPTED',self.ws.item(ib)['processing_status'])
        self.assertEqual(1,len(self.history()));self.assertEqual(1,len(self.db.works()))

    def test_new_clean_audit_stales_approval_until_human_reaccepts(self):
        wid=self.seed();uid,item=self.membership(wid)
        self.ws.accept([item]);first=self.history()[0]
        self.save(wid)
        self.assertEqual('STALE',self.db.acceptance.state(wid));self.assertEqual([],self.db.works(accepted_only=True))
        self.assertEqual(first,self.history()[0])
        self.ws.reopen_items([item]);self.ws.pin(item,wid,self.db.latest_audit(wid)['id'])
        self.ws.accept([item]);self.assertEqual('CURRENT',self.db.acceptance.state(wid));self.assertEqual(2,len(self.history()))

    def test_curation_invalidates_acceptance_and_undo_redo_preserve_history(self):
        wid=self.seed();self.db.acceptance.accept(work_ids=[wid])
        preview=self.db.catalog.preview(wid,[dict(entity='chapter',key='1',field='volume',value='2')])
        self.db.catalog.apply(preview)
        self.assertEqual('STALE',self.db.acceptance.state(wid));self.assertFalse(self.db.acceptance.evaluate(wid)['eligible'])
        self.db.catalog.reverse(wid);self.db.catalog.reverse(wid,redo=True)
        self.assertEqual(3,self.db.catalog.state(wid)['revision']);self.assertEqual(1,len(self.history()))

    def test_unmapped_conflict_and_incompatible_identity_block(self):
        wid=self.seed()
        for field,value in (('unmapped_chapters',1),('conflicting_chapters',['1']),('status','failed'),('final_volumes',0)):
            pub=publication(canonical='fixture:series');pub[field]=value;self.save(wid,pub)
            self.assertFalse(self.db.acceptance.evaluate(wid)['eligible'],field)
        self.save(wid)
        self.db.catalog.apply(self.db.catalog.preview(wid,[dict(entity='work',key='work',field='edition',value='fan_color')]))
        self.assertFalse(self.db.acceptance.evaluate(wid)['eligible'])

    def test_selected_acceptance_rolls_back_every_write_on_failure(self):
        a=self.seed('A','fixture:a');b=self.seed('B','fixture:b');ua,ia=self.membership(a);ub,ib=self.membership(b)
        original=self.db.acceptance._record;calls=[]
        def fail_second(*args):
            original(*args);calls.append(True)
            if len(calls)==2:raise RuntimeError('Injected acceptance failure')
        with patch.object(self.db.acceptance,'_record',side_effect=fail_second),self.assertRaises(RuntimeError):
            self.ws.accept([ia,ib])
        self.assertEqual([],self.history());self.assertEqual('STAGED',self.db.work(a)['lifecycle_status'])
        self.assertEqual('STAGED',self.db.work(b)['lifecycle_status']);self.assertEqual('READY',self.ws.item(ia)['processing_status'])
        with self.db.con() as c:self.assertFalse(c.execute("SELECT 1 FROM database_events WHERE description LIKE 'ACCEPT%'").fetchone())

    def test_selected_validation_failure_is_atomic(self):
        wid=self.seed();uid,item=self.membership(wid)
        bad=self.seed('Bad','fixture:bad',[dict(code='REFERENCE_CONFLICT',severity='warning',message='Conflict')])
        ub,ib=self.membership(bad)
        with self.assertRaises(ValueError):self.ws.accept([item,ib])
        self.assertEqual('READY',self.ws.item(item)['processing_status']);self.assertEqual([],self.history())

    def test_acceptance_failure_injection_at_each_sql_boundary(self):
        wid=self.seed();uid,item=self.membership(wid)
        triggers=[('BEFORE','INSERT','catalog_acceptances','1'),
                  ('AFTER','UPDATE','works',"NEW.lifecycle_status='ACCEPTED'"),
                  ('BEFORE','UPDATE','working_set_items',"NEW.processing_status='ACCEPTED'")]
        for timing,action,table,condition in triggers:
            with self.db.con() as c:c.execute(f"CREATE TRIGGER fail_acceptance {timing} {action} ON {table} WHEN {condition} BEGIN SELECT RAISE(ABORT,'Injected write failure'); END")
            with self.assertRaises(sqlite3.IntegrityError):self.ws.accept([item])
            self.assertEqual('STAGED',self.db.work(wid)['lifecycle_status']);self.assertEqual('READY',self.ws.item(item)['processing_status'])
            self.assertEqual([],self.history())
            with self.db.con() as c:c.execute('DROP TRIGGER fail_acceptance')
        with patch.object(self.db.acceptance,'_record',side_effect=RuntimeError('After evaluation before first write')):
            with self.assertRaises(RuntimeError):self.ws.accept([item])
        self.assertEqual([],self.history());self.ws.accept([item])
        self.assertEqual('CURRENT',self.db.acceptance.state(wid))

    def test_bulk_revalidates_ready_and_skips_stale_preview(self):
        a=self.seed('A','fixture:a');b=self.seed('B','fixture:b');uid=self.ws.create('Bulk')
        self.ws.add_requests(uid,['A','B']);items=self.ws.items(uid)
        for wid,item in zip((a,b),items):self.ws.pin(item['working_set_item_uuid'],wid,self.db.latest_audit(wid)['id'])
        preview=self.db.acceptance.bulk_preview(uid)
        self.save(b)
        result=self.db.acceptance.accept(preview['ready_items'],expected=preview['candidates'],bulk=True)
        self.assertEqual(1,len(result['accepted']));self.assertEqual(1,len(result['skipped']))
        self.assertEqual('ACCEPTED',self.ws.item(items[0]['working_set_item_uuid'])['processing_status'])
        self.assertEqual('REVIEW',self.ws.item(items[1]['working_set_item_uuid'])['processing_status'])

    def test_revoke_is_explicit_and_journalled(self):
        wid=self.seed();self.db.acceptance.accept(work_ids=[wid])
        self.db.acceptance.revoke(wid,'Incorrect supporting reference')
        self.assertEqual('STAGED',self.db.work(wid)['lifecycle_status']);self.assertEqual('REVOKED',self.db.acceptance.state(wid))
        self.assertEqual(['ACCEPT','REVOKE'],[r['decision'] for r in self.history()])

    def test_complete_gate_and_reopen_preserve_pins_and_ids(self):
        wid=self.seed();uid,item=self.membership(wid)
        for status in ('PENDING','QUEUED','AUDITING','REVIEW','READY','ERROR'):
            with self.db.con() as c:c.execute('UPDATE working_set_items SET processing_status=? WHERE working_set_item_uuid=?',(status,item))
            with self.assertRaises(ValueError):self.ws.set_status(uid,'COMPLETE')
        self.ws.pin(item,wid,self.db.latest_audit(wid)['id']);self.ws.accept([item]);old=self.ws.item(item)
        self.ws.set_status(uid,'COMPLETE');self.ws.reopen(uid)
        self.assertEqual('REVIEW',self.ws.get(uid)['status']);self.assertEqual(old['pinned_audit_id'],self.ws.item(item)['pinned_audit_id'])
        self.ws.set_status(uid,'ARCHIVED');self.ws.reopen(uid);self.ws.reopen_items([item])
        self.assertEqual('QUEUED',self.ws.item(item)['processing_status']);self.assertEqual(old['pinned_audit_id'],self.ws.item(item)['pinned_audit_id'])
        self.assertEqual(1,len(self.history()));self.assertEqual(1,self.db.latest_audit(wid)['audit_revision'])
        self.ws.set_status(uid,'OPEN');self.ws.add_requests(uid,['Another'])

    def test_empty_set_cannot_complete_but_can_archive(self):
        uid=self.ws.create('Empty')
        with self.assertRaises(ValueError):self.ws.set_status(uid,'COMPLETE')
        self.ws.set_status(uid,'ARCHIVED');self.ws.reopen(uid)

    def test_protected_mutations_fail_in_backend_and_exports_work(self):
        wid=self.seed();uid,item=self.membership(wid);pin=self.ws.item(item)['pinned_audit_id']
        preview=self.db.catalog.preview(wid,[dict(entity='chapter',key='1',field='volume',value='2')])
        preview['working_set_item_uuid']=item
        self.ws.accept([item]);self.ws.set_status(uid,'COMPLETE')
        for state in ('COMPLETE','ARCHIVED'):
            if state=='ARCHIVED':self.ws.set_status(uid,state)
            actions=[lambda:self.ws.add_requests(uid,['New']),lambda:self.ws.remove_item(item),
                     lambda:self.ws.set_item_status(item,'QUEUED'),lambda:self.ws.set_item_status(item,'REJECTED'),
                     lambda:self.ws.pin(item,wid,pin),lambda:self.ws.accept([item]),
                     lambda:self.ws.observe_unresolved(item,{},[]),lambda:self.ws.run_candidates(uid),
                     lambda:self.ws.retry_errors(uid),lambda:self.ws.reopen_items([item]),
                     lambda:self.db.catalog.apply(preview)]
            for action in actions:
                with self.assertRaises(ValueError):action()
            self.assertEqual(pin,working_set_rows(self.db,uid)[0]['audit_id'])
        # Explicit global curation remains authorized even when historical sets refer to it.
        preview.pop('working_set_item_uuid');self.db.catalog.apply(preview)
        self.assertEqual(1,self.db.catalog.state(wid)['revision'])

    def test_review_allows_workflow_but_not_membership_changes(self):
        wid=self.seed();uid,item=self.membership(wid);self.ws.set_status(uid,'REVIEW')
        with self.assertRaises(ValueError):self.ws.add_requests(uid,['New'])
        with self.assertRaises(ValueError):self.ws.remove_item(item)
        self.ws.set_item_status(item,'REJECTED');self.ws.reopen_items([item])

    def test_same_title_distinct_identity_and_exact_canonical_reuse(self):
        a=self.seed('Title X','fixture:a');uid,item=self.membership(a,pin=False)
        request=self.ws.item(item);identity=publication(canonical='fixture:b')['catalog_identity']
        b=self.ws.create_work(request,identity)
        self.assertNotEqual(self.db.work(a)['work_uuid'],self.db.work(b)['work_uuid'])
        self.assertEqual('Title X',self.db.work(b)['input_title']);self.assertEqual(b,self.ws.create_work(request,identity))
        with self.db.con() as c:
            with self.assertRaises(sqlite3.IntegrityError):c.execute('UPDATE works SET canonical_work_id=? WHERE id=?',('fixture:a',b))

    def test_alias_duplicate_preserves_query_without_audit_or_pin(self):
        wid=self.seed();uid,item=self.membership(wid)
        self.ws.add_requests(uid,['Trusted alias']);second=self.ws.items(uid)[1]['working_set_item_uuid']
        identity=publication(canonical='fixture:series')['catalog_identity']
        self.assertTrue(self.ws.mark_duplicate_if_known(second,identity))
        duplicate=self.ws.item(second);self.assertEqual('DUPLICATE',duplicate['processing_status'])
        self.assertEqual(item,duplicate['duplicate_of_item_uuid']);self.assertIsNone(duplicate['pinned_audit_id'])
        self.assertEqual(1,self.db.latest_audit(wid)['audit_revision']);self.assertEqual(1,len(self.db.works()))
        self.ws.accept([item]);self.ws.set_status(uid,'COMPLETE')
        other,other_item=self.membership(wid,'Other');self.assertEqual('READY',self.ws.item(other_item)['processing_status'])

    def test_pinned_rows_context_and_packet_do_not_substitute_new_global(self):
        wid=self.seed(holes=[dict(code='REFERENCE_CONFLICT',severity='warning',message='Old reference')]);uid,item=self.membership(wid)
        old=self.ws.item(item)['pinned_audit_id'];pub=publication(canonical='fixture:series',volume='2')
        self.save(wid,pub)
        row=working_set_rows(self.db,uid)[0];self.assertEqual(old,row['audit_id']);self.assertEqual('SUPERSEDED',row['pin_state'])
        self.assertNotEqual(row['audit_id'],row['latest_global_audit_id'])
        self.assertEqual(old,catalog_context(self.db,wid,self.ws.item(item))['audit_id'])
        packet=review_packet(self.db,work_ids={wid},audit_by_work={wid:old})
        self.assertEqual(old,packet['works'][0]['audit_id']);self.assertEqual('Old reference',packet['works'][0]['issues'][0]['why_flagged'])
        self.assertEqual('1',self.db.catalog.rows(wid,audit=self.db.audit(old,wid))[0]['effective']['volume'])
        self.assertEqual('2',self.db.catalog.rows(wid)[0]['effective']['volume'])

    def test_captured_audit_guard_rejects_changed_title_but_not_unrelated_title(self):
        wid=self.seed();uid,item=self.membership(wid);guard=self.db.catalog.audit_guard(wid)
        self.seed('Other','fixture:other')
        record={'query':'Series','publication':publication(canonical='fixture:series'),'catalog_guard':guard}
        self.ws.persist_item_audit(item,record['publication']['catalog_identity'],record,[])
        pin=self.ws.item(item)['pinned_audit_id'];guard=self.db.catalog.audit_guard(wid)
        self.db.catalog.apply(self.db.catalog.preview(wid,[dict(entity='chapter',key='1',field='volume',value='3')]))
        record['catalog_guard']=guard
        with self.assertRaises(AuditSuperseded):self.ws.persist_item_audit(item,record['publication']['catalog_identity'],record,[])
        self.assertEqual(pin,self.ws.item(item)['pinned_audit_id']);self.assertEqual(2,self.db.latest_audit(wid)['audit_revision'])

    def test_run_candidates_and_explicit_error_retry(self):
        wid=self.seed();uid,item=self.membership(wid)
        self.ws.add_requests(uid,['Pending','Queued','Error','Human Review'])
        entries={i['original_query']:i for i in self.ws.items(uid)}
        self.ws.set_item_status(entries['Queued']['working_set_item_uuid'],'QUEUED')
        self.ws.set_item_status(entries['Error']['working_set_item_uuid'],'ERROR')
        self.ws.set_item_status(entries['Human Review']['working_set_item_uuid'],'REVIEW')
        candidates=self.ws.run_candidates(uid)
        self.assertEqual({entries[k]['working_set_item_uuid'] for k in ('Pending','Queued')},set(candidates))
        self.save(wid);self.assertIn(item,self.ws.run_candidates(uid))
        self.assertEqual([entries['Error']['working_set_item_uuid']],self.ws.retry_errors(uid))

    def test_interruption_recovers_once_preserving_pin_and_protected_items(self):
        wid=self.seed();uid,item=self.membership(wid);pin=self.ws.item(item)['pinned_audit_id']
        other,other_item=self.membership(wid,'Archived');self.ws.set_status(other,'ARCHIVED')
        self.ws.set_item_status(item,'AUDITING')
        with self.db.con() as c:c.execute("UPDATE working_set_items SET processing_status='AUDITING' WHERE working_set_item_uuid=?",(other_item,))
        reopened=ddk.DB(self.path,role='TEST');self.assertEqual(1,reopened.working_sets.recover_interrupted())
        self.assertEqual(0,reopened.working_sets.recover_interrupted());self.assertEqual(pin,reopened.working_sets.item(item)['pinned_audit_id'])
        self.assertEqual('AUDITING',reopened.working_sets.item(other_item)['processing_status'])

    def test_recovered_run_finishes_once_and_preserves_exact_membership(self):
        uid=self.ws.create('Interrupted');self.ws.add_requests(uid,['Monster']);item=self.ws.items(uid)[0]['working_set_item_uuid']
        self.ws.set_item_status(item,'AUDITING')
        reopened=ddk.DB(self.path,role='TEST');reopened.working_sets.recover_interrupted()
        auditor=ddk.SearchAuditor(reopened,queue.Queue())
        with offline_pipeline(auditor):auditor.audit_many(reopened.working_sets.run_candidates(uid),'volume')
        self.assertEqual(1,len(reopened.works()));self.assertEqual(1,len(reopened.working_sets.items(uid)))
        self.assertEqual('READY',reopened.working_sets.item(item)['processing_status'])
        self.assertEqual(1,reopened.latest_audit(reopened.working_sets.item(item)['work_id'])['audit_revision'])
        self.assertEqual([],reopened.working_sets.run_candidates(uid))

    def test_curation_during_real_orchestration_discards_old_result_and_requeues(self):
        wid=self.seed('Monster','fixture:monster');uid,item=self.membership(wid)
        auditor=ddk.SearchAuditor(self.db,queue.Queue());calls=[]
        with offline_pipeline(auditor):
            normal=ddk.resolve_publication.side_effect
            def racing(*args,**kwargs):
                pub=normal(*args,**kwargs);calls.append(pub['curation_revision'])
                if len(calls)==1:self.db.catalog.apply(self.db.catalog.preview(wid,[dict(entity='chapter',key='1',field='volume',value='2')]))
                return pub
            with patch.object(ddk,'resolve_publication',side_effect=racing):auditor.audit_many([item],'volume')
        self.assertEqual([0,1],calls);self.assertEqual(2,self.db.latest_audit(wid)['audit_revision'])
        self.assertEqual(1,json.loads(self.db.latest_audit(wid)['publication_json'])['curation_revision'])
        self.assertEqual('READY',self.ws.item(item)['processing_status'])

    def test_alias_duplicate_stops_before_publication_resolution(self):
        uid=self.ws.create('Alias');self.ws.add_requests(uid,['Monster','New Series'])
        ids=[i['working_set_item_uuid'] for i in self.ws.items(uid)];auditor=ddk.SearchAuditor(self.db,queue.Queue())
        calls=[]
        with offline_pipeline(auditor):
            normal=ddk.resolve_publication.side_effect
            def canonical_resolution(resolved,*args,**kwargs):
                if resolved.primary.result['title']=='New Series':
                    identity=publication(canonical='fixture:monster')['catalog_identity']
                    kwargs['on_identity'](identity)
                calls.append(resolved.primary.result['title'])
                return normal(resolved,*args,**kwargs)
            with patch.object(ddk,'resolve_publication',side_effect=canonical_resolution):auditor.audit_many(ids,'volume')
        self.assertEqual(['Monster'],calls);self.assertEqual('DUPLICATE',self.ws.item(ids[1])['processing_status'])
        self.assertEqual(ids[0],self.ws.item(ids[1])['duplicate_of_item_uuid']);self.assertEqual(1,len(self.db.works()))
        self.assertEqual(1,self.db.latest_audit(self.ws.item(ids[0])['work_id'])['audit_revision'])

    def test_cancelled_run_restores_queued_without_losing_pin(self):
        wid=self.seed('Monster','fixture:monster');uid,item=self.membership(wid);pin=self.ws.item(item)['pinned_audit_id']
        auditor=ddk.SearchAuditor(self.db,queue.Queue())
        with offline_pipeline(auditor):
            search=auditor._parallel_provider_search.side_effect
            def cancelled(*args,**kwargs):
                result=search(*args,**kwargs);auditor.stop();return result
            with patch.object(auditor,'_parallel_provider_search',side_effect=cancelled):auditor.audit_many([item],'volume')
        self.assertEqual('QUEUED',self.ws.item(item)['processing_status']);self.assertEqual(pin,self.ws.item(item)['pinned_audit_id'])
        self.assertEqual(1,self.db.latest_audit(wid)['audit_revision'])

    def test_source_dependency_changes_make_target_require_reaudit(self):
        wid=self.seed();self.db.catalog.apply(self.db.catalog.preview(wid,[dict(entity='chapter',key='1',field='volume',value='2')]))
        self.db.add_titles(['Series'],'official_color','en');color=2
        pub=publication(canonical='fixture:series',edition='official_color');self.save(color,pub)
        self.ws.relate_structure(wid,color,'Identical reviewed chapter membership','VERIFIED')
        pub['catalog_dependencies']=self.db.catalog.audit_guard(color)
        pub['curated_database']=self.db.catalog.lookup(pub['catalog_identity'],color)
        self.save(color,pub)
        self.assertTrue(self.db.acceptance.evaluate(color)['eligible'])
        # A different source audit is a meaningful dependency even without a source curation revision change.
        source_pub=publication(canonical='fixture:series');source_pub['curation_revision']=1
        self.save(wid,source_pub)
        result=self.db.acceptance.evaluate(color)
        self.assertFalse(result['eligible']);self.assertTrue(result['needs_reaudit'])

    def test_v6_migration_preserves_identity_children_pins_and_legacy_status(self):
        wid=self.seed(holes=[dict(code='UNCLASSIFIED_ACQUISITION',severity='warning',message='Extra')]);uid,item=self.membership(wid)
        self.db.dispose_problem(self.db.holes()[0]['id'],'Publisher confirms extra')
        self.db.catalog.apply(self.db.catalog.preview(wid,[dict(entity='chapter',key='1',field='volume',value='34')]))
        self.db.catalog.apply(self.db.catalog.preview(wid,[dict(entity='evidence',key='publisher-toc',field='add',target_key='1',
            source_name='Publisher',source_url='https://example.org/contents')]))
        self.db.add_titles(['Series'],'official_color','en');color=2
        color_pub=publication(canonical='fixture:series',edition='official_color')
        self.save(color,color_pub);self.ws.relate_structure(wid,color,'Verified identical chapter numbering','VERIFIED')
        self.ws.add_requests(uid,['Removed request']);removed=self.ws.items(uid)[1]['working_set_item_uuid'];self.ws.remove_item(removed)
        self.ws.set_status(uid,'ARCHIVED')
        with self.db.con() as c:c.execute("UPDATE works SET lifecycle_status='ACCEPTED' WHERE id=?",(wid,))
        tables=('works','search_audits','audit_holes','curated_catalog','curated_fields','curated_evidence','curated_changes','curated_events','problem_dispositions','working_sets','working_set_items','edition_structure_relationships','working_set_observations')
        downgrade_fixture(self.db)
        with self.db.con() as c:before={table:[dict(r) for r in c.execute('SELECT * FROM '+table)] for table in tables}
        migrated=ddk.DB(self.path,role='TEST',migrate_schema8=True)
        self.assertEqual(self.db.database_uuid,migrated.database_uuid)
        with migrated.con() as c:
            for table in tables:
                rows=[dict(r) for r in c.execute('SELECT * FROM '+table)]
                if table=='working_set_items':
                    for r in rows:r.pop('duplicate_of_item_uuid')
                self.assertEqual(before[table],rows,table)
            self.assertFalse(c.execute('PRAGMA foreign_key_check').fetchall());self.assertEqual('ok',c.execute('PRAGMA integrity_check').fetchone()[0])
        self.assertEqual('LEGACY_REVIEW_REQUIRED',migrated.acceptance.state(wid));self.assertEqual([],migrated.works(accepted_only=True))
        backups=list((self.path.parent/'backups').glob('*before_schema_v7*.db'));self.assertEqual(1,len(backups))
        self.assertEqual(6,sqlite3.connect(backups[0]).execute('PRAGMA user_version').fetchone()[0])

    def test_migration_duplicate_claim_aborts_with_exact_ids_and_uuids(self):
        a=self.seed('A','fixture:a');b=self.seed('B','fixture:b');downgrade_fixture(self.db)
        with self.db.con() as c:c.execute("UPDATE works SET canonical_work_id='fixture:a' WHERE id=?",(b,))
        with self.assertRaises(ValueError) as caught:ddk.DB(self.path,role='TEST',migrate_schema8=True)
        for wid in (a,b):self.assertIn(self.db.work(wid)['work_uuid'],str(caught.exception))
        with self.db.con() as c:self.assertEqual(6,c.execute('PRAGMA user_version').fetchone()[0])

    def test_migration_failure_rolls_back_table_rebuild_and_children(self):
        wid=self.seed();uid,item=self.membership(wid);downgrade_fixture(self.db)
        normal_con=self.db.con
        class FailingConnection:
            def __init__(self,c):self.c=c
            def execute(self,sql,*args):
                if 'CREATE TABLE IF NOT EXISTS catalog_acceptances' in sql:raise RuntimeError('Injected migration failure')
                return self.c.execute(sql,*args)
            def __getattr__(self,key):return getattr(self.c,key)
        @contextmanager
        def failing_con():
            with normal_con() as c:yield FailingConnection(c)
        with patch.object(self.db,'con',failing_con),self.assertRaises(RuntimeError):migrate_v7(self.db)
        with normal_con() as c:
            self.assertEqual(6,c.execute('PRAGMA user_version').fetchone()[0]);self.assertEqual('ok',c.execute('PRAGMA integrity_check').fetchone()[0])
            self.assertFalse(c.execute('PRAGMA foreign_key_check').fetchall())
            self.assertIn('UNIQUE(input_title,edition,language)',c.execute("SELECT sql FROM sqlite_master WHERE name='works'").fetchone()[0])
            self.assertIsNone(c.execute("SELECT 1 FROM sqlite_master WHERE name='catalog_acceptances'").fetchone())
        self.assertEqual(1,self.ws.item(item)['pinned_audit_revision'])

    def test_permanent_delete_v7_removes_acceptances_preserving_intake(self):
        wid=self.seed();uid,item=self.membership(wid);self.ws.accept([item])
        preview=self.db.maintenance.preview(self.db.work(wid)['work_uuid'])
        self.assertEqual(1,preview['counts']['acceptance_history'])
        self.db.maintenance.delete(preview,'DELETE')
        self.assertEqual([],self.history());self.assertIsNone(self.ws.item(item)['linked_work_uuid'])
        with self.db.con() as c:self.assertFalse(c.execute('PRAGMA foreign_key_check').fetchall())


if __name__=='__main__':unittest.main()
