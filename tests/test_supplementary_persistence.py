"""Disposable schema-8 reviewed workflow; all positive proofs are synthetic."""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from mangaanka_database_development_kit import DB
from ddk_schema import migrate_v8
from ddk_supplementary import collect_supplements
from ddk_supplementary_store import acquisitions,fingerprint
from ddk_commands import parse_batch
from ddk_review import database_revision,review_guard,review_packet
from ddk_exports import catalog_context
from test_publication_states import fixture,resolved,stored
from test_supplementary_integration import book


TABLES=('supplementary_current','supplementary_events','supplementary_changes',
        'supplementary_assertions','supplementary_identities','supplementary_catalog')


def schema7(db):
    with db.con() as c:
        for table in TABLES:c.execute('DROP TABLE '+table)
        c.execute('DROP INDEX supplementary_audit_owner_idx')
        c.execute('PRAGMA user_version=7')


def seed(db):
    res,bundle=fixture();pub=resolved(res,bundle)
    for row in pub['projection']:
        row['url']='https://example.org/read/'+row['id']
        row['page_urls']=['https://example.org/image/'+row['id']]
    pub['supplementary_identity']=collect_supplements(dict(supplementary_publications=[book(language='en'),
        dict(book(language='en'),records=[dict(title='Second story',publication_role='special',book_page=320)])]),
        pub['projection'],pub['catalog_identity'])
    wid,aid=stored(db,pub,res.primary)
    return wid,aid,pub


def binding_payload(db,wid,key=None,reader='19.5'):
    pub=json.loads(db.latest_audit(wid)['publication_json']);context=db.supplementary.guard(wid)
    row=next(r for r in acquisitions(pub) if r['id']==reader)
    identity=next(r['identity'] for r in pub['supplementary_identity']['identities'] if key is None or r['identity']['opaque_id']==key)
    p=identity['provenance'];g={k:context[k] for k in ('database_uuid','audit_id','audit_revision','database_revision')}
    return dict(supplement_id=identity['opaque_id'],scope=identity['scope'],provider=row['_source_id'],
        record_id=row['id'],original_label=row['chapter'],url=row['url'],method='reviewed_exact',verification='VERIFIED',
        review_guard=g,reviewer='SYNTHETIC fixture reviewer',note='SYNTHETIC complete-content equivalence; not production evidence.',
        source_url=p['source_url'],captured_at=p['captured_at'],publication_sha256=p['payload_sha256'],
        acquisition_sha256=fingerprint(row),equivalence=dict(method='complete_content_review',complete=True,
            source_url='https://example.org/synthetic-review',payload_sha256='c'*64,
            captured_at='2026-10-07T12:00:00+00:00',note='SYNTHETIC full contents reviewed.'))


class Persistence(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'test.db';self.db=DB(self.path,role='TEST')
        self.wid,self.aid,self.pub=seed(self.db);self.store=self.db.supplementary
        self.key=self.pub['supplementary_identity']['identities'][0]['identity']['opaque_id']
        no_net=patch('urllib.request.urlopen',side_effect=AssertionError('No network in disposable regression'))
        no_net.start();self.addCleanup(no_net.stop)

    def preview(self,payload=None,key=None,item=None):
        value=payload or binding_payload(self.db,self.wid,key)
        return self.store.preview(self.wid,[dict(action='bind',opaque_id=value['supplement_id'],payload=value)],value['review_guard'],item)

    def apply(self):
        preview=self.preview();self.store.apply(preview);return preview

    def current(self):return self.store.for_audit(self.wid,current=True)

    def test_preview_is_read_only_then_apply_survives_reopen(self):
        before=self.db.latest_audit(self.wid)['publication_json'];preview=self.preview()
        self.assertEqual(0,self.store.revision(self.wid));self.assertEqual([],self.store.history(self.wid))
        self.store.apply(preview)
        again=DB(self.path);self.assertEqual(1,again.supplementary.revision(self.wid))
        self.assertEqual(1,again.supplementary.for_audit(self.wid,current=True)['summary']['verified_acquired'])
        self.assertEqual(before,self.db.latest_audit(self.wid)['publication_json'])

    def test_guard_token_changes_and_previous_numeric_guard_is_stale(self):
        token=database_revision(self.db);guard=review_guard(self.db,self.wid,self.db.latest_audit(self.wid))
        self.apply();self.assertNotEqual(token,database_revision(self.db))
        self.assertIn('-s1',database_revision(self.db))
        with self.assertRaisesRegex(ValueError,'Stale'):
            self.db.catalog.preview(self.wid,[dict(entity='chapter',key='1',field='title',value='x')],guard=guard)

    def test_new_audit_revalidates_without_erasing_decision(self):
        self.apply();old=self.db.latest_audit(self.wid)['publication_json']
        aid=self.db.save_audit(self.wid,dict(query='fixture',publication=self.pub),[])
        self.assertNotEqual(aid,self.aid)
        pub=json.loads(self.db.audit(aid,self.wid)['publication_json'])
        self.assertEqual(1,pub['supplementary_revision'])
        self.assertEqual(1,pub['supplementary_identity']['summary']['verified_acquired'])
        self.assertEqual(old,self.db.audit(self.aid,self.wid)['publication_json'])
        for key in ('canonical_main_chapters','logical_chapters','mapped_chapters','final_volumes','normalization','projection'):
            self.assertEqual(self.pub[key],pub[key])

    def test_undo_redo_and_historical_reconstruction(self):
        self.apply();self.assertEqual(1,self.current()['summary']['verified_acquired'])
        self.store.apply(self.store.preview_reverse(self.wid));self.assertEqual(0,self.current()['summary']['verified_acquired'])
        self.assertEqual(1,self.store.resolve(self.pub,self.wid,revision=1)['summary']['verified_acquired'])
        self.store.apply(self.store.preview_reverse(self.wid,True));self.assertEqual(1,self.current()['summary']['verified_acquired'])
        self.assertEqual(['apply','undo','redo'],[r['action'] for r in self.store.history(self.wid)])

    def test_new_mutation_supersedes_redo_without_deleting_history(self):
        self.apply();self.store.apply(self.store.preview_reverse(self.wid))
        payload=binding_payload(self.db,self.wid);payload['note']='Another synthetic decision';self.store.apply(self.preview(payload))
        with self.assertRaisesRegex(ValueError,'Nothing to redo'):self.store.preview_reverse(self.wid,True)
        self.assertEqual(3,len(self.store.history(self.wid)))

    def test_reject_withdraw_and_undo_preserve_assertions(self):
        self.apply()
        for action in ('reject','withdraw'):
            current=self.store.state(self.wid)['decisions'][0]
            guard=self.store.guard(self.wid)
            p=self.store.preview(self.wid,[dict(action=action,assertion_uuid=current['assertion_uuid'],reviewer='Fixture',note='Synthetic correction')],guard)
            self.store.apply(p)
            self.assertEqual('rejected' if action=='reject' else 'withdrawn',self.current()['identities'][0]['acquisition_state'])
            self.store.apply(self.store.preview_reverse(self.wid))
            self.assertEqual(1,self.current()['summary']['verified_acquired'])
        with self.db.con() as c:self.assertEqual(3,c.execute('SELECT count(*) FROM supplementary_assertions').fetchone()[0])

    def test_independent_membership_review_never_proves_acquisition(self):
        membership=deepcopy(self.pub['supplementary_identity']['identities'][0]['memberships'][0])
        membership.update(verification='VERIFIED',reviewer='Synthetic reviewer',note='Official collection independently checked')
        guard=self.store.guard(self.wid)
        p=self.store.preview(self.wid,[dict(action='membership',opaque_id=self.key,payload=membership)],guard)
        self.store.apply(p)
        self.assertEqual(0,self.current()['summary']['verified_acquired'])
        self.assertEqual('verified',self.current()['reviewed_state']['decisions'][0]['effective_state'])
        self.store.apply(self.store.preview_reverse(self.wid));self.assertEqual([],self.store.state(self.wid)['decisions'])

    def test_stale_preview_after_audit_or_numeric_curation(self):
        for which in ('audit','curation'):
            p=self.preview()
            if which=='audit':self.db.save_audit(self.wid,dict(publication=self.pub),[])
            else:self.db.catalog.apply(self.db.catalog.preview(self.wid,[dict(entity='chapter',key='1',field='title',value='Synthetic edited')]))
            with self.assertRaisesRegex(ValueError,'Stale'):self.store.apply(p)
        self.assertEqual(0,self.store.revision(self.wid))

    def test_conflicting_reader_and_duplicate_targets_fail_closed(self):
        self.apply();other=self.pub['supplementary_identity']['identities'][1]['identity']['opaque_id']
        with self.assertRaisesRegex(ValueError,'Conflicting'):self.preview(binding_payload(self.db,self.wid,other))
        value=binding_payload(self.db,self.wid);op=dict(action='bind',opaque_id=value['supplement_id'],payload=value)
        with self.assertRaises(ValueError):self.store.preview(self.wid,[op,op],value['review_guard'])

    def test_multiple_readers_count_once(self):
        self.apply();value=binding_payload(self.db,self.wid,self.key,reader='92.5')
        self.store.apply(self.preview(value))
        self.assertEqual(1,self.current()['summary']['verified_acquired'])
        self.assertEqual(2,len(self.current()['identities'][0]['bindings']))

    def test_duplicate_raw_readers_rejected(self):
        self.pub['projection'].append(deepcopy(next(r for r in self.pub['projection'] if r['id']=='19.5')))
        self.pub['normalization']['labels'].append('unclassified')
        self.db.save_audit(self.wid,dict(publication=self.pub),[])
        with self.assertRaisesRegex(ValueError,'ambiguous'):self.preview()

    def test_numeric_main_and_special_cannot_be_rebound(self):
        for reader in ('1','89.1'):
            value=binding_payload(self.db,self.wid,self.key,reader)
            with self.assertRaisesRegex(ValueError,'numeric'):self.preview(value)

    def test_stale_unavailable_and_conflicting_revalidation(self):
        self.apply();base=deepcopy(self.pub)
        changed=deepcopy(base);next(r for r in changed['projection'] if r['id']=='19.5')['page_urls']=['https://example.org/changed']
        self.assertEqual('stale',self.store.resolve(changed,self.wid)['identities'][0]['acquisition_state'])
        changed=deepcopy(base);changed['projection']=[r for r in changed['projection'] if r['id']!='19.5']
        changed['normalization']['labels']=['unclassified']*len(changed['projection'])
        self.assertEqual('unavailable',self.store.resolve(changed,self.wid)['identities'][0]['acquisition_state'])
        changed=deepcopy(base);next(r for r in changed['projection'] if r['id']=='19.5')['language']='ja'
        self.assertEqual('conflicting',self.store.resolve(changed,self.wid)['identities'][0]['acquisition_state'])

    def test_capture_timestamp_refresh_does_not_stale_unchanged_payload(self):
        self.apply();changed=deepcopy(self.pub)
        for row in changed['supplementary_identity']['identities']:
            for raw in [row['identity']]+row['observations']:raw['provenance']['captured_at']='2026-10-08T00:00:00+00:00'
            for membership in row['memberships']:membership['provenance']['captured_at']='2026-10-08T00:00:00+00:00'
        self.assertEqual(1,self.store.resolve(changed,self.wid)['summary']['verified_acquired'])

    def test_membership_cannot_reassign_guidebook_to_numbered_volume(self):
        value=deepcopy(self.pub['supplementary_identity']['identities'][0]['memberships'][0])
        value.update(verification='VERIFIED',reviewer='Fixture',note='Synthetic',relation='standard_volume',volume='38')
        with self.assertRaises(ValueError):self.store.preview(self.wid,[dict(action='membership',opaque_id=self.key,payload=value)],self.store.guard(self.wid))

    def test_exact_membership_target_pin_and_protected_set(self):
        ws=self.db.working_sets;uid=ws.create('Fixture batch');ws.add_requests(uid,['Serialized fixture'])
        item=ws.items(uid)[0]['working_set_item_uuid'];ws.pin(item,self.wid,self.db.latest_audit(self.wid)['id'])
        p=self.preview(item=item)
        with self.db.con() as c:c.execute("UPDATE working_sets SET status='COMPLETE' WHERE working_set_uuid=?",(uid,))
        with self.assertRaisesRegex(ValueError,'protected'):self.store.apply(p)
        self.assertEqual(0,self.store.revision(self.wid))

    def test_acceptance_requires_new_audit_and_never_becomes_eligible_from_binding(self):
        before=self.db.acceptance.evaluate(self.wid)
        self.apply();after=self.db.acceptance.evaluate(self.wid)
        self.assertFalse(after['eligible']);self.assertTrue(after['needs_reaudit'])
        self.assertTrue(set(before['blockers'])<=set(after['blockers']))
        with self.db.con() as c:self.assertEqual(0,c.execute('SELECT count(*) FROM catalog_acceptances').fetchone()[0])

    def test_exports_distinguish_pinned_snapshot_and_current_review(self):
        self.apply();context=catalog_context(self.db,self.wid)
        self.assertEqual(0,context['supplementary_identity']['summary']['verified_acquired'])
        self.assertEqual(1,context['supplementary_current_review']['summary']['verified_acquired'])
        packet=review_packet(self.db,work_ids=[self.wid],include_ignored=True)
        self.assertEqual(4,packet['command_grammar_version'])
        self.assertEqual(1,packet['works'][0]['supplementary_current_review']['summary']['verified_acquired'])

    def test_apply_failure_rolls_back_and_retry_succeeds(self):
        preview=self.preview();original=self.db.con
        @contextmanager
        def broken():
            with original() as c:
                def authorizer(action,a,b,d,e):
                    if action==sqlite3.SQLITE_INSERT and a=='supplementary_events':return sqlite3.SQLITE_DENY
                    return sqlite3.SQLITE_OK
                c.set_authorizer(authorizer);yield c
        with patch.object(self.db,'con',broken),self.assertRaises(sqlite3.DatabaseError):self.store.apply(preview)
        self.assertEqual(0,self.store.revision(self.wid));self.assertEqual([],self.store.state(self.wid)['decisions'])
        self.store.apply(preview);self.assertEqual(1,self.store.revision(self.wid))

    def test_preview_tampering_is_revalidated(self):
        p=self.preview();p['assertions'][0]['payload']['equivalence']['complete']=False
        with self.assertRaises(ValueError):self.store.apply(p)
        self.assertEqual(0,self.store.revision(self.wid))

    def test_missing_official_evidence_retains_history_and_allows_withdrawal(self):
        self.apply();changed=deepcopy(self.pub);changed.pop('supplementary_identity')
        value=self.store.resolve(changed,self.wid)
        self.assertEqual('unavailable',value['identities'][0]['acquisition_state'])
        self.assertEqual(1,len(value['reviewed_state']['decisions']))
        self.db.save_audit(self.wid,dict(publication=changed),[])
        current=self.store.state(self.wid)['decisions'][0]
        p=self.store.preview(self.wid,[dict(action='withdraw',assertion_uuid=current['assertion_uuid'],reviewer='Fixture',note='Evidence unavailable')],self.store.guard(self.wid))
        self.store.apply(p);self.assertEqual('withdrawn',self.current()['identities'][0]['acquisition_state'])

    def test_changed_publisher_payload_is_stale_and_no_automatic_reapproval(self):
        self.apply();changed=deepcopy(self.pub)
        for row in changed['supplementary_identity']['identities']:
            for raw in [row['identity']]+row['observations']:raw['provenance']['payload_sha256']='e'*64
            for membership in row['memberships']:membership['provenance']['payload_sha256']='e'*64
        self.assertEqual('stale',self.store.resolve(changed,self.wid)['identities'][0]['acquisition_state'])
        self.assertEqual(1,len(self.store.history(self.wid)))

    def test_untrusted_current_identity_quarantines_without_losing_decisions(self):
        self.apply();changed=deepcopy(self.pub);changed['catalog_identity']['trusted']=False
        value=self.store.resolve(changed,self.wid)
        self.assertEqual(0,value['summary']['verified_acquired'])
        self.assertEqual('conflicting',value['reviewed_state']['decisions'][0]['effective_state'])

    def test_sql_immutability_and_foreign_key_ownership(self):
        self.apply()
        for table,column in (('supplementary_assertions','payload_json'),('supplementary_identities','identity_json'),('supplementary_events','guard_json')):
            with self.assertRaises(sqlite3.IntegrityError),self.db.con() as c:
                c.execute('UPDATE '+table+' SET '+column+"='{}'")
        with self.assertRaises(sqlite3.IntegrityError),self.db.con() as c:
            c.execute('UPDATE supplementary_current SET target_key=?',('other-reader',))

    def test_existing_writer_lock_serializes_threads_and_stales_second_preview(self):
        import threading
        first=self.preview();value=binding_payload(self.db,self.wid,self.key,'92.5');second=self.preview(value)
        started=threading.Event();finished=threading.Event();errors=[]
        def writer():
            started.set()
            try:self.store.apply(second)
            except ValueError as exc:errors.append(str(exc))
            finally:finished.set()
        with self.db.lock:
            thread=threading.Thread(target=writer);thread.start();self.assertTrue(started.wait(2))
            self.assertFalse(finished.wait(.05));self.store.apply(first)
        thread.join(5);self.assertFalse(thread.is_alive());self.assertEqual(1,len(errors))
        self.assertIn('Stale',errors[0]);self.assertEqual(1,self.store.revision(self.wid))

    def test_apply_uses_one_short_writer_connection_without_self_lock(self):
        from test_force_transactions import SQLTrace
        trace=SQLTrace(self.db);preview=self.preview()
        with trace.enabled():self.store.apply(preview)
        self.assertEqual({},trace.active)
        self.assertFalse(any(r.get('error') for r in trace.events))
        for event in trace.events:
            if event.get('sql','').startswith('INSERT INTO supplementary_'):
                self.assertFalse(event.get('other_transactions'))

    def test_maintenance_previews_and_removes_only_owned_supplementary_history(self):
        self.apply();self.db.add_titles(['Unrelated'],'standard','en')
        preview=self.db.maintenance.preview(self.db.work(self.wid)['work_uuid'])
        self.assertEqual(1,preview['counts']['supplementary_assertions']);self.assertTrue(preview['strong_warning'])
        self.db.maintenance.delete(preview,'DELETE')
        self.assertEqual(['Unrelated'],[w['input_title'] for w in self.db.works()])
        with self.db.con() as c:
            for table in TABLES:self.assertEqual(0,c.execute('SELECT count(*) FROM '+table).fetchone()[0])
            self.assertFalse(c.execute('PRAGMA foreign_key_check').fetchall())

    def test_grammar_4_family_and_numeric_grammar_preserved(self):
        for text in ('supplement list','supplement history','supplement inspect '+self.key,
                     'supplement candidates '+self.key,'supplement undo','supplement redo'):
            self.assertEqual('supplement',parse_batch(text)[0]['action'])
        self.assertEqual('edit',parse_batch('set volume 24 chapter 206')[0]['action'])
        for text in ('select chapter '+self.key,'supplement bind 393 "{}"','supplement membership '+self.key+' "[]"'):
            with self.assertRaises(ValueError):parse_batch(text)

    def test_duplicate_json_keys_are_not_silently_overwritten(self):
        from ddk_supplementary_commands import parse_supplement
        with self.assertRaisesRegex(ValueError,'quoted JSON'):
            parse_supplement(['supplement','bind',self.key,'{"reviewer":"one","reviewer":"two"}'])

    def test_publisher_identifier_requires_current_official_story_id(self):
        value=binding_payload(self.db,self.wid)
        value['equivalence'].update(method='publisher_identifier',publisher_content_id='invented-id')
        with self.assertRaisesRegex(ValueError,'official story content identifier'):self.preview(value)

    def test_publisher_identifier_mismatch_is_rejected(self):
        from types import SimpleNamespace
        from ddk_supplementary_store import equivalence
        value=binding_payload(self.db,self.wid);row=acquisitions(self.pub)[0]
        value['acquisition_sha256']=fingerprint(row)
        value['equivalence'].update(method='publisher_identifier',publisher_content_id='wrong-id')
        identity=SimpleNamespace(publisher_content_id='official-id',scope=SimpleNamespace(language='en',edition='standard'))
        with self.assertRaisesRegex(ValueError,'official story content identifier'):equivalence(value,identity,row)

    def test_exact_publisher_identifier_still_requires_complete_review(self):
        from types import SimpleNamespace
        from ddk_supplementary_store import equivalence
        value=binding_payload(self.db,self.wid);row=acquisitions(self.pub)[0]
        value['acquisition_sha256']=fingerprint(row)
        value['equivalence'].update(method='publisher_identifier',publisher_content_id='official-id')
        identity=SimpleNamespace(publisher_content_id='official-id',scope=SimpleNamespace(language='en',edition='standard'))
        equivalence(value,identity,row)
        value['equivalence']['complete']=False
        with self.assertRaises(ValueError):equivalence(value,identity,row)


def negative_test(field,value):
    def test(self):
        payload=binding_payload(self.db,self.wid)
        if field.startswith('equivalence.'):
            payload['equivalence'][field.split('.')[1]]=value
        else:payload[field]=value
        with self.assertRaises(ValueError):self.preview(payload)
        self.assertEqual(0,self.store.revision(self.wid))
    return test


for index,(field,value) in enumerate([
    ('reviewer',''),('note',''),('verification','REVIEWED'),('method','ocr'),
    ('provider','other'),('record_id','other'),('original_label','393'),('url','https://example.org/other'),
    ('publication_sha256','b'*64),('acquisition_sha256','b'*64),('captured_at','2020-01-01T00:00:00+00:00'),
    ('scope',dict(work='other',edition='standard',language='en')),
    ('scope',dict(work='fixture:serialized',edition='deluxe',language='en')),
    ('scope',dict(work='fixture:serialized',edition='standard',language='ja')),
    ('equivalence.complete',False),('equivalence.method','title_match'),('equivalence.payload_sha256','bad'),
    ('equivalence.source_url','file:///bad'),('equivalence.captured_at','invalid'),('equivalence.note','')]):
    setattr(Persistence,'test_reject_bad_binding_%02d_%s'%(index,field.replace('.','_')),negative_test(field,value))


class Migration(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'catalog.db';self.db=DB(self.path,role='TEST')
        self.wid,self.aid,self.pub=seed(self.db);schema7(self.db)

    def test_normal_open_refuses_upgrade_without_writing(self):
        before=self.path.read_bytes()
        with self.assertRaisesRegex(ValueError,'explicit schema-8'):DB(self.path)
        self.assertEqual(before,self.path.read_bytes())

    def test_migration_preserves_every_old_row_and_is_repeat_safe(self):
        with self.db.con() as c:
            c.execute('CREATE TABLE custom_fixture(value TEXT)');c.execute("INSERT INTO custom_fixture VALUES('preserve')")
            names=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            before={name:[tuple(r) for r in c.execute('SELECT * FROM "'+name+'"')] for name in names if name!='database_events'}
        migrated=DB(self.path,migrate_schema8=True)
        with migrated.con() as c:
            self.assertEqual(8,c.execute('PRAGMA user_version').fetchone()[0])
            for name,rows in before.items():self.assertEqual(rows,[tuple(r) for r in c.execute('SELECT * FROM "'+name+'"')],name)
            self.assertEqual('ok',c.execute('PRAGMA integrity_check').fetchone()[0])
        backups=list((self.path.parent/'backups').glob('*before_schema_v8*.db'));self.assertEqual(1,len(backups))
        with sqlite3.connect(backups[0]) as c:self.assertEqual(7,c.execute('PRAGMA user_version').fetchone()[0])
        DB(self.path);self.assertEqual(1,len(list((self.path.parent/'backups').glob('*before_schema_v8*.db'))))

    def test_migration_interruption_rolls_back_ddl_version_and_event(self):
        original=self.db.con
        @contextmanager
        def broken():
            with original() as c:
                def authorizer(action,a,b,d,e):
                    if action==sqlite3.SQLITE_CREATE_TABLE and a=='supplementary_events':return sqlite3.SQLITE_DENY
                    return sqlite3.SQLITE_OK
                c.set_authorizer(authorizer);yield c
        with patch.object(self.db,'con',broken),self.assertRaises(sqlite3.DatabaseError):migrate_v8(self.db)
        with original() as c:
            self.assertEqual(7,c.execute('PRAGMA user_version').fetchone()[0])
            self.assertFalse(set(TABLES)&{r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")})
            self.assertEqual('ok',c.execute('PRAGMA integrity_check').fetchone()[0])
        migrate_v8(self.db)
        with original() as c:self.assertEqual(8,c.execute('PRAGMA user_version').fetchone()[0])

    def test_newer_schema_is_never_downgraded(self):
        with self.db.con() as c:c.execute('PRAGMA user_version=9')
        before=self.path.read_bytes()
        with self.assertRaisesRegex(ValueError,'newer'):DB(self.path,migrate_schema8=True)
        self.assertEqual(before,self.path.read_bytes())

    def test_schema7_current_acceptance_and_pins_survive_upgrade(self):
        path=self.path.parent/'accepted.db';db=DB(path,role='TEST')
        res,bundle=fixture(extras=False);wid,aid=stored(db,resolved(res,bundle),res.primary)
        db.acceptance.accept(work_ids=[wid]);self.assertEqual('CURRENT',db.acceptance.state(wid))
        uid=db.working_sets.create('Acceptance control');db.working_sets.add_requests(uid,['Serialized fixture'])
        item=db.working_sets.items(uid)[0]['working_set_item_uuid'];db.working_sets.pin(item,wid,aid)
        with db.con() as c:before=[tuple(r) for r in c.execute('SELECT * FROM catalog_acceptances')]
        schema7(db);migrated=DB(path,migrate_schema8=True)
        self.assertEqual('CURRENT',migrated.acceptance.state(wid))
        self.assertEqual(aid,migrated.working_sets.item(item)['pinned_audit_id'])
        with migrated.con() as c:self.assertEqual(before,[tuple(r) for r in c.execute('SELECT * FROM catalog_acceptances')])

    def test_phase3_older_reader_refuses_schema8_without_downgrade(self):
        import importlib.util
        migrate_v8(self.db)
        path=Path(__file__).resolve().parents[1]/'build/supplementary-binding-persistence/originals/ddk_workspace.py'
        spec=importlib.util.spec_from_file_location('workspace_before_v8',path);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
        before=self.path.read_bytes()
        with self.assertRaisesRegex(ValueError,'newer'):old.validate_database(self.path)
        self.assertEqual(before,self.path.read_bytes())


if __name__=='__main__':unittest.main()
