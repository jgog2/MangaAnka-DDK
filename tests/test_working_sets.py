"""Disposable Working Set, catalog lifecycle, export, and writer regressions."""
import csv
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

import mangaanka_database_development_kit as ddk
from ddk_exports import (catalog_summary, review_context, working_set_csv,
                         working_set_packet, working_set_title_list, working_set_review_context)
from ddk_writer_lock import WriterLock


def publication(canonical='fixture:shared',edition='standard',volume='1',provider='provider-a'):
    identity={'canonical_work_id':canonical,'edition':edition,'language':'en',
              'publication_context':'','external_ids':{'fixture':canonical.split(':',1)[-1]},'trusted':True}
    row={'id':'1','chapter':'1','title':'','type':'chapter','volume':volume,
         '_effective_volume':volume,'_acquisition_provider':provider}
    data={'status':'complete','catalog_identity':identity,'edition':edition,
          'context':{'shareable':True},'normalization':{'status':'established'},
          'raw_acquisition_records':1,'projection':[row],
          'logical_chapters':1,'mapped_chapters':int(volume is not None),
          'unmapped_chapters':int(volume is None),'final_volumes':int(volume is not None),
          'curation_revision':0}
    return dict(data,automatic=dict(data))


class WorkingSetTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.path=Path(tmp.name)/'catalog.db'
        self.db=ddk.DB(self.path,role='TEST')
        self.ws=self.db.working_sets

    def audit(self,wid,edition='standard',volume='1',provider='provider-a',canonical='fixture:shared'):
        pub=publication(canonical,edition,volume,provider)
        pub['curation_revision']=self.db.catalog.state(wid)['revision']
        return self.db.save_audit(wid,{'query':self.db.work(wid)['input_title'],
            'match_title':self.db.work(wid)['input_title'],'requested_edition':edition,
            'selected_source':provider,'publication':pub},[])

    def test_large_catalog_has_scoped_intake_and_conservative_lifecycle(self):
        self.db.add_titles([f'Existing {n}' for n in range(1000)],'standard','en')
        with self.db.con() as c:c.execute("UPDATE works SET lifecycle_status='ACCEPTED'")
        set_id=self.ws.create('Batch 11')
        self.ws.set_active(set_id)
        report=self.ws.add_requests(set_id,[f'New {n}' for n in range(100)])
        self.assertEqual(100,report['new_items'])
        self.assertEqual(100,len(self.ws.items(set_id)))
        self.assertEqual(1000,len(self.db.works()))
        self.assertEqual(0,len(self.db.works(accepted_only=True)))
        self.assertTrue(all(r['acceptance_state']=='LEGACY_REVIEW_REQUIRED' for r in self.db.works()))
        self.assertTrue(all(i['linked_work_uuid'] is None for i in self.ws.items(set_id)))
        self.assertEqual(set_id,ddk.DB(self.path).working_sets.active_uuid())

    def test_intake_idempotence_context_restore_and_no_title_prelink(self):
        self.db.add_titles(['Example'],'standard','en')
        set_id=self.ws.create('Batch')
        first=self.ws.add_requests(set_id,['Example','Example','Other'])
        self.assertEqual((3,2,2,1),(first['input_lines'],first['unique_requests'],
                                     first['new_items'],first['duplicate_input_lines']))
        self.assertIsNone(self.ws.items(set_id)[0]['linked_work_uuid'])
        self.assertEqual(0,self.ws.add_requests(set_id,['Example'])['new_items'])
        self.ws.add_requests(set_id,['Example'],'official_color')
        self.ws.add_requests(set_id,['Example'],'standard','ja')
        self.assertEqual(4,len(self.ws.items(set_id)))
        item=self.ws.items(set_id)[0]
        self.ws.remove_item(item['working_set_item_uuid'])
        self.assertEqual(3,len(self.ws.items(set_id)))
        self.assertEqual(1,self.ws.add_requests(set_id,['Example'])['restored_items'])
        self.assertEqual(item['working_set_item_uuid'],self.ws.items(set_id)[0]['working_set_item_uuid'])
        self.assertEqual(1,len(self.db.works()))
        with self.assertRaisesRegex(ValueError,'edition'):
            self.ws.add_requests(set_id,['Example'],'invented_color')

    def test_canonical_link_new_work_and_pinned_history_across_sets(self):
        self.db.add_titles(['Existing'],'standard','en');self.audit(1)
        original_uuid=self.db.work(1)['work_uuid']
        set_a=self.ws.create('A');set_b=self.ws.create('B')
        self.ws.add_requests(set_a,['Existing']);self.ws.add_requests(set_b,['Existing','New'])
        item_a=self.ws.items(set_a)[0];item_b=self.ws.items(set_b)[0]
        identity=publication()['catalog_identity']
        self.assertEqual(1,self.ws.resolve_work(item_a,identity))
        self.assertIsNone(self.ws.resolve_work(item_a,dict(identity,canonical_work_id='different')))
        self.ws.pin(item_a['working_set_item_uuid'],1,self.db.latest_audit(1)['id'],ready=True)
        revision_one=self.ws.item(item_a['working_set_item_uuid'])['pinned_audit_revision']
        second=self.audit(1,volume='2')
        self.ws.pin(item_b['working_set_item_uuid'],1,second,ready=True)
        self.assertEqual(revision_one,self.ws.item(item_a['working_set_item_uuid'])['pinned_audit_revision'])
        self.assertEqual(2,self.ws.item(item_b['working_set_item_uuid'])['pinned_audit_revision'])
        self.assertEqual(original_uuid,self.db.work(1)['work_uuid'])
        new=next(i for i in self.ws.items(set_b) if i['original_query']=='New')
        new_identity=dict(identity,canonical_work_id='fixture:new')
        self.assertIsNone(self.ws.resolve_work(new,new_identity))
        new_id=self.ws.create_work(new,new_identity)
        self.assertNotEqual(original_uuid,self.db.work(new_id)['work_uuid'])
        self.assertEqual('STAGED',self.db.work(new_id)['lifecycle_status'])
        self.assertEqual(2,len(self.db.works()))

    def test_accept_requires_fresh_pass_and_archive_keeps_catalog(self):
        self.db.add_titles(['Example'],'standard','en')
        wid=1;self.audit(wid)
        set_id=self.ws.create('A');self.ws.add_requests(set_id,['Example'])
        item=self.ws.items(set_id)[0]
        self.ws.pin(item['working_set_item_uuid'],wid,self.db.latest_audit(wid)['id'],ready=True)
        self.assertEqual('STAGED',self.db.work(wid)['lifecycle_status'])
        self.ws.accept([item['working_set_item_uuid']])
        self.assertEqual('ACCEPTED',self.db.work(wid)['lifecycle_status'])
        self.assertEqual('ACCEPTED',self.ws.item(item['working_set_item_uuid'])['processing_status'])
        self.ws.set_status(set_id,'ARCHIVED')
        self.assertEqual(1,len(self.db.works()))
        self.assertEqual(1,len(self.ws.items(set_id)))
        with self.assertRaisesRegex(ValueError,'Reopen'):
            self.ws.add_requests(set_id,['Another'])
        with self.assertRaisesRegex(ValueError,'Reopen'):
            self.ws.pin(item['working_set_item_uuid'],wid,self.db.latest_audit(wid)['id'],ready=True)
        self.db.add_titles(['Stale'],'standard','en');self.audit(2,canonical='fixture:stale')
        self.db.catalog.apply(self.db.catalog.preview(2,[{'entity':'chapter','key':'1','field':'volume','value':'3'}]))
        with self.assertRaisesRegex(ValueError,'stale after curation'):
            self.ws.accept(work_ids=[2])
        self.assertEqual('STAGED',self.db.work(2)['lifecycle_status'])

    def test_explicit_edition_structure_only_and_distinct_acquisition(self):
        self.db.add_titles(['Example'],'standard','en')
        self.db.add_titles(['Example'],'official_color','en')
        self.audit(1,provider='standard-only')
        self.audit(2,edition='official_color',volume=None,provider='color-only')
        self.db.catalog.apply(self.db.catalog.preview(1,[{'entity':'chapter','key':'1','field':'volume',
                                                          'value':'34','verification':'VERIFIED'}]))
        identity=publication(edition='official_color')['catalog_identity']
        self.assertNotEqual('matched',self.db.catalog.lookup(identity,2)['status'])
        self.ws.relate_structure(1,2,'Same official chapter numbering','VERIFIED')
        shared=self.db.catalog.lookup(identity,2)
        self.assertTrue(shared['structure_shared'])
        self.assertEqual('34',shared['fields'][0]['value'])
        self.assertEqual([],self.db.catalog.state(2)['fields'])
        color=self.db.catalog.rows(2)[0]
        self.assertEqual('34',color['effective']['volume'])
        self.assertEqual('color-only',json.loads(self.db.latest_audit(2)['publication_json'])['projection'][0]['_acquisition_provider'])
        self.assertEqual('standard-only',json.loads(self.db.latest_audit(1)['publication_json'])['projection'][0]['_acquisition_provider'])
        resolved=publication(edition='official_color',volume='34',provider='color-only')
        resolved['curated_database']=shared
        self.db.save_audit(2,{'query':'Example','requested_edition':'official_color','publication':resolved},[])
        self.assertEqual('PASS',ddk.audit_status(self.db.works([2])[0]))
        self.db.catalog.apply(self.db.catalog.preview(1,[{'entity':'chapter','key':'1','field':'volume','value':'35'}]))
        self.assertEqual('RERUN REQUIRED',ddk.audit_status(self.db.works([2])[0]))
        self.audit(1,canonical='fixture:other')
        self.assertNotEqual('matched',self.db.catalog.lookup(identity,2)['status'])
        self.db.add_titles(['Example'],'fan_color','en');self.audit(3,edition='fan_color',volume=None)
        self.assertNotEqual('matched',self.db.catalog.lookup(publication(edition='fan_color')['catalog_identity'],3)['status'])

    def test_external_id_claim_changes_keep_work_uuid_and_history(self):
        self.db.add_titles(['Example'],'standard','en');self.audit(1)
        stable=self.db.work(1)['work_uuid']
        for claim in ('123','456'):
            self.db.catalog.apply(self.db.catalog.preview(1,[
                {'entity':'work','key':'work','field':'external_ids',
                 'value':{'fixture':'shared','anilist':claim}}]))
            self.assertEqual(stable,self.db.work(1)['work_uuid'])
        self.assertEqual(2,len(self.db.catalog.history(1)))
        self.assertEqual('456',self.db.catalog.state(1)['fields'][0]['value']['anilist'])

    def test_exports_use_selected_work_and_pinned_audit_without_writes(self):
        self.db.add_titles(['One','Two'],'standard','en')
        self.audit(1);self.audit(2,canonical='fixture:two')
        set_a=self.ws.create('A');set_b=self.ws.create('B')
        self.ws.add_requests(set_a,['One']);self.ws.add_requests(set_b,['Two'])
        item=self.ws.items(set_a)[0]
        self.ws.pin(item['working_set_item_uuid'],1,self.db.latest_audit(1)['id'],ready=True)
        old_audit=self.db.latest_audit(1)['id']
        self.audit(1,volume='2')
        before=self.path.read_bytes()
        summary=catalog_summary(self.db,1,item)
        context=review_context(self.db,1,item)
        self.assertIn('One',summary);self.assertNotIn('Two',summary)
        self.assertIn(self.db.work(1)['work_uuid'],context)
        self.assertNotIn(self.db.work(2)['work_uuid'],context)
        pinned=list(csv.DictReader(StringIO(working_set_csv(self.db,set_a))))
        current=list(csv.DictReader(StringIO(working_set_csv(self.db,set_a,'current'))))
        self.assertEqual(1,len(pinned));self.assertEqual('One',pinned[0]['query'])
        self.assertEqual(str(old_audit),pinned[0]['audit_id'])
        self.assertNotEqual(pinned[0]['audit_id'],current[0]['audit_id'])
        packet=working_set_packet(self.db,set_a)
        self.assertEqual(old_audit,packet['entries'][0]['audit']['id'])
        self.assertEqual('One',working_set_title_list(self.db,set_a))
        readable=working_set_review_context(self.db,set_a)
        self.assertIn('One',readable);self.assertNotIn('Two',readable)
        self.assertIn(str(old_audit),readable)
        self.assertEqual(before,self.path.read_bytes())

    def test_unresolved_intake_evidence_remains_in_scoped_exports(self):
        set_id=self.ws.create('Unresolved')
        self.ws.add_requests(set_id,['Unknown'])
        item=self.ws.items(set_id)[0]
        issue={'code':'NO_CANONICAL_RESULT','message':'No trusted provider result','severity':'error'}
        self.ws.observe_unresolved(item['working_set_item_uuid'],{'query':'Unknown'},[issue])
        self.assertEqual('REVIEW',self.ws.item(item['working_set_item_uuid'])['processing_status'])
        self.assertEqual('NO_CANONICAL_RESULT',self.ws.latest_observation(item['working_set_item_uuid'])['holes'][0]['code'])
        self.assertIn('NO_CANONICAL_RESULT',working_set_review_context(self.db,set_id))
        self.assertEqual('NO_CANONICAL_RESULT',working_set_packet(self.db,set_id)['entries'][0]
                         ['unresolved_observation']['holes'][0]['code'])
        self.assertEqual([],self.db.works())

    def test_v4_migration_preserves_fire_force_like_curation_and_history(self):
        old_path=self.path.parent/'v4.db'
        old=ddk.DB(old_path,role='PRODUCTION')
        old.add_titles(['Fixture Publication'],'standard','en')
        p=publication(canonical='fixture:fire',volume=None)
        p['catalog_identity']['external_ids']={'fixture':'fire'}
        p['projection']=[dict(p['projection'][0],id=str(n),chapter=str(n)) for n in (303,304)]
        p['automatic']=dict(p,projection=list(p['projection']))
        old.save_audit(1,{'query':'Fixture Publication','match_title':'Fixture Publication',
                          'requested_edition':'standard','publication':p},[])
        old.catalog.apply(old.catalog.preview(1,[
            {'entity':'chapter','key':str(n),'field':'volume','value':'34'} for n in (303,304)]))
        original_uuid=old.database_uuid
        original_history=len(old.catalog.history(1))
        from test_supplementary_persistence import schema7
        schema7(old)
        with old.con() as c:
            for table in ('catalog_acceptances','working_set_observations','working_set_items','working_sets',
                          'edition_structure_relationships'):
                c.execute(f'DROP TABLE {table}')
            for index in ('works_canonical_unique_idx','works_uuid_idx','works_lifecycle_idx','works_canonical_claim_idx',
                          'works_external_ids_idx'):
                c.execute(f'DROP INDEX {index}')
            for column in ('work_uuid','canonical_work_id','lifecycle_status'):
                c.execute(f'ALTER TABLE works DROP COLUMN {column}')
            c.execute('ALTER TABLE database_meta DROP COLUMN active_working_set_uuid')
            for column in ('source_name','source_url','accessed_at'):
                c.execute(f'ALTER TABLE curated_fields DROP COLUMN {column}')
            c.execute('PRAGMA user_version=4')
        migrated=ddk.DB(old_path,migrate_schema8=True)
        self.assertEqual(original_uuid,migrated.database_uuid)
        self.assertEqual('PRODUCTION',migrated.role)
        self.assertEqual('STAGED',migrated.work(1)['lifecycle_status'])
        self.assertTrue(migrated.work(1)['work_uuid'])
        self.assertEqual('fixture:fire',migrated.work(1)['canonical_work_id'])
        self.assertEqual(original_history,len(migrated.catalog.history(1)))
        self.assertEqual(['34','34'],[r['effective']['volume'] for r in migrated.catalog.rows(1)])
        backups=list((old_path.parent/'backups').glob('v4_before_schema_v6_*.db'))
        self.assertEqual(1,len(backups))
        with migrated.con() as c:
            self.assertEqual(8,c.execute('PRAGMA user_version').fetchone()[0])
            self.assertEqual('ok',c.execute('PRAGMA quick_check').fetchone()[0])

    def test_writer_lock_blocks_second_writer_and_recovers(self):
        first=WriterLock(self.path)
        try:
            with self.assertRaisesRegex(ValueError,'already open'):
                WriterLock(self.path)
        finally:first.close()
        second=WriterLock(self.path);second.close()


if __name__=='__main__':unittest.main()
