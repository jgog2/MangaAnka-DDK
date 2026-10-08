"""Disposable schema-v6 and MF Ghost-style semantic regressions."""
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import mangaanka_database_development_kit as ddk
from ddk_commands import parse
from ddk_exports import catalog_context, working_set_rows


ODD=('0','4 V2 : 2 Days Left Until Kanata S Race',
     '7 V2 : Attention Flag','9 V2 : The Legacy Of The Downhill Specialist (Fixed)')


def fixture(title='MF Ghost',edition='standard',language='en',context='',unmapped=True,odd=()):
    rows=[{'id':str(n),'chapter':str(n),'title':'','type':'chapter',
           'volume':str(min(23,(n-1)//12+1)) if n<275 or not unmapped else None,
           '_effective_volume':str(min(23,(n-1)//12+1)) if n<275 or not unmapped else None,
           '_acquisition_provider':'fixture'} for n in range(1,276)]
    rows += [{'id':'provider:'+str(n),'chapter':text,'title':'','type':'chapter','volume':None,
              '_effective_volume':None,'_acquisition_provider':'fixture'} for n,text in enumerate(odd)]
    identity={'canonical_work_id':'fixture:mf','edition':edition,'language':language,
              'publication_context':context,'external_ids':{'fixture':'mf'},'trusted':True}
    data={'status':'complete','edition':edition,'catalog_identity':identity,
          'context':{'shareable':True},'normalization':{'status':'established',
          'labels':['main']*275+['unclassified']*len(odd),
          'counts':{'main':275,'unclassified':len(odd)}},
          'projection':rows,'logical_chapters':275,'mapped_chapters':274 if unmapped else 275,
          'unmapped_chapters':1 if unmapped else 0,'final_volumes':23,
          'unmapped':[rows[274]] if unmapped else [],
          'unclassified_acquisition':[{'chapter':value,'classification':'unclassified'} for value in odd],
          'raw_acquisition_records':len(rows),'curation_revision':0}
    return dict(data,automatic=dict(data))


class Hardening(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.db=ddk.DB(Path(temp.name)/'fixture.db',role='TEST')

    def save(self,wid=1,pub=None,holes=(),version=None):
        work=self.db.work(wid)
        pub=pub or fixture(edition=work['edition'],language=work['language'])
        pub=json.loads(json.dumps(pub))
        if work['input_title'] in ('Conflict','Stale','Identity','Publication','Data','Invalid','Unknown'):
            pub['catalog_identity']['canonical_work_id']=f'fixture:{wid}'
            pub['catalog_identity']['external_ids']={'fixture':str(wid)}
            if pub.get('automatic'):pub['automatic']['catalog_identity']=dict(pub['catalog_identity'])
        return self.db.save_audit(wid,{'query':work['input_title'],'match_title':work['input_title'],
            'requested_edition':work['edition'],'requested_language':work['language'],
            'search_core_version':version,'publication':pub},list(holes))

    def test_mf_ghost_logical_validation_and_review_context_are_separate(self):
        self.db.add_titles(['MF Ghost'],'standard','en')
        self.save(pub=fixture(odd=ODD),holes=[
            {'code':'UNMAPPED_CHAPTERS','severity':'warning','message':'One canonical chapter'},
            {'code':'UNCLASSIFIED_ACQUISITION','severity':'warning','message':'Four provider rows'}])
        context=catalog_context(self.db,1)
        self.assertEqual(['275'],context['canonical_unmapped_identifiers'])
        self.assertEqual(set(ODD),set(context['unclassified_acquisition_identifiers']))
        self.assertNotIn('unmapped_identifiers',context)
        changes=[{'entity':'chapter','key':'275','field':'volume','value':'23','verification':'VERIFIED'},
                 {'entity':'chapter','key':'275','field':'source_note',
                  'value':'Verified structural evidence','verification':'VERIFIED'}]
        preview=self.db.catalog.preview(1,changes)
        self.assertEqual([],preview['validation']['unmapped'])
        self.assertEqual(4,len(preview['validation']['unclassified_acquisition']))
        self.assertFalse(any('3 chapters remain unmapped' in w for w in preview['validation']['warnings']))
        self.assertEqual([],self.db.catalog.state(1)['fields'])

    def test_multi_source_evidence_preview_apply_undo_redo_and_reaudit(self):
        self.db.add_titles(['MF Ghost'],'standard','en');self.save()
        first=parse('add evidence source "Publisher" url "https://example.org/toc" selected')
        second=parse('add evidence source "Bibliography" note "Volume 23" chapter 275')
        self.assertEqual('evidence',first['action']);self.assertEqual('evidence',second['action'])
        changes=[{'entity':'chapter','key':'275','field':'volume','value':'23'},
                 {'entity':'evidence','key':'evidence-a','field':'add','target_key':'275',
                  'source_name':'Publisher','source_url':'https://example.org/toc','note':'',
                  'accessed_at':''},
                 {'entity':'evidence','key':'evidence-b','field':'add','target_key':'275',
                  'source_name':'Bibliography','source_url':'','note':'Volume 23',
                  'accessed_at':''}]
        preview=self.db.catalog.preview(1,changes)
        self.assertEqual([],self.db.catalog.evidence(1))
        with self.assertRaises(ValueError):
            self.db.catalog.preview(1,changes+[{'entity':'evidence','key':'bad-source',
                'field':'add','target_key':'275','source_name':'Invalid URL',
                'source_url':'not-a-url'}])
        self.assertEqual([],self.db.catalog.evidence(1))
        self.db.catalog.apply(preview)
        evidence=self.db.catalog.evidence(1,'chapter','275','volume')
        self.assertEqual({'Publisher','Bibliography'},{r['source_name'] for r in evidence})
        self.assertTrue(all(r['accessed_at'] and r['evidence_uuid'] for r in evidence))
        with self.assertRaises(ValueError):
            self.db.catalog.preview(1,[
                {'entity':'chapter','key':'275','field':'volume','reset':True},
                {'entity':'evidence','key':'reset-source','field':'add','target_key':'275',
                 'source_name':'No assertion','source_url':''}])
        self.db.catalog.reverse(1)
        self.assertEqual([],self.db.catalog.evidence(1))
        self.db.catalog.reverse(1,redo=True)
        self.assertEqual(2,len(self.db.catalog.evidence(1)))
        self.save(pub=fixture(unmapped=False))
        self.assertEqual(2,len(self.db.catalog.evidence(1)))
        self.save(pub=fixture(unmapped=True))
        self.assertEqual(2,len(self.db.catalog.evidence(1)))

    def test_accept_catalog_truth_with_provider_noise_but_block_conflicts(self):
        self.db.add_titles(['MF Ghost'],'standard','en')
        pub=fixture(unmapped=False,odd=ODD)
        self.save(pub=pub,holes=[
            {'code':'ACQUISITION_COVERAGE_GAP','severity':'warning','message':'Provider coverage'},
            {'code':'UNCLASSIFIED_ACQUISITION','severity':'warning','message':'Unclassified provider rows'}])
        health=json.loads(self.db.latest_audit(1)['health_json'])
        self.assertEqual('PASS',health['identity']);self.assertEqual('PASS',health['publication'])
        self.assertEqual('REVIEW',health['normalization']);self.assertEqual('PARTIAL',health['acquisition'])
        self.assertEqual('STAGED',self.db.work(1)['lifecycle_status'])
        with self.assertRaisesRegex(ValueError,'UNCLASSIFIED'):self.db.working_sets.accept(work_ids=[1])
        problem=self.db.holes('UNCLASSIFIED_ACQUISITION')[0]
        self.db.dispose_problem(problem['id'],'Provider extra verified against publisher chapters','VERIFIED')
        self.db.working_sets.accept(work_ids=[1])
        self.assertEqual('ACCEPTED',self.db.work(1)['lifecycle_status'])
        self.db.add_titles(['Conflict'],'standard','en')
        self.save(2,pub=fixture(unmapped=False),holes=[
            {'code':'REFERENCE_CONFLICT','severity':'warning','message':'Structure contradiction'}])
        with self.assertRaises(ValueError):self.db.working_sets.accept(work_ids=[2])
        self.db.add_titles(['Stale'],'standard','en');self.save(3,pub=fixture(unmapped=False))
        self.db.catalog.apply(self.db.catalog.preview(3,[
            {'entity':'chapter','key':'275','field':'volume','value':'23'}]))
        with self.assertRaises(ValueError):self.db.working_sets.accept(work_ids=[3])

    def test_accept_blocks_identity_publication_data_and_invalid_curation(self):
        self.db.add_titles(['Identity','Publication','Data','Invalid','Unknown'],'standard','en')
        complete=fixture(unmapped=False)
        self.save(1,pub=complete,holes=[
            {'code':'WRONG_EDITION_MATCH','severity':'warning','message':'Wrong edition'}])
        self.save(2,pub=complete,holes=[
            {'code':'REFERENCE_CONFLICT','severity':'warning','message':'Conflicting structure'}])
        self.save(3,pub=complete,holes=[
            {'code':'CATALOG_DATA_CONTRADICTION','severity':'warning','message':'Contradictory data'}])
        with self.db.con() as c:
            c.execute("UPDATE audit_holes SET problem_class='DATA' WHERE work_id=3")
        self.save(4,pub=complete)
        self.save(5,pub=complete,holes=[
            {'code':'NEW_UNTRIAGED_PROBLEM','severity':'warning','message':'Untriaged issue'}])
        self.db.catalog.apply(self.db.catalog.preview(4,[
            {'entity':'chapter','key':'275','field':'volume','value':'23'}]))
        self.save(4,pub=complete)
        with self.db.con() as c:
            c.execute('''UPDATE curated_fields SET value_json='"invalid"'
                WHERE work_id=4 AND record_key='275' AND field='volume' ''')
        self.assertTrue(self.db.catalog.validate(4)['errors'])
        for work_id in range(1,6):
            with self.subTest(work_id=work_id),self.assertRaises(ValueError):
                self.db.working_sets.accept(work_ids=[work_id])
            self.assertEqual('STAGED',self.db.work(work_id)['lifecycle_status'])

    def test_pin_freezes_and_audit_environment_is_per_revision(self):
        self.db.add_titles(['MF Ghost'],'standard','en')
        ws=self.db.working_sets.create('Batch')
        self.db.working_sets.add_requests(ws,['MF Ghost'])
        item=self.db.working_sets.items(ws)[0]['working_set_item_uuid']
        for revision,status,version in ((1,'OPEN','fake-core-a'),(2,'REVIEW','fake-core-b'),
                                        (3,'REVIEW','fake-core-c')):
            self.db.working_sets.set_status(ws,status)
            audit=self.save(pub=fixture(unmapped=False),version=version)
            self.db.working_sets.pin(item,1,audit,ready=True)
            self.assertEqual(revision,self.db.working_sets.item(item)['pinned_audit_revision'])
        self.db.working_sets.accept([item])
        self.db.working_sets.set_status(ws,'COMPLETE')
        self.save(pub=fixture(unmapped=False),version='fake-core-d')
        self.assertEqual(3,self.db.working_sets.item(item)['pinned_audit_revision'])
        with self.assertRaises(ValueError):self.db.working_sets.set_status(ws,'OPEN')
        self.assertEqual('fake-core-c',working_set_rows(self.db,ws)[0]['audit_search_core_version'])
        self.assertEqual('fake-core-d',working_set_rows(self.db,ws,'current')[0]['audit_search_core_version'])
        self.assertEqual(8,working_set_rows(self.db,ws)[0]['audit_schema_version'])
        self.assertEqual('0.3.0',working_set_rows(self.db,ws)[0]['audit_ddk_version'])
        self.assertEqual('standard',working_set_rows(self.db,ws)[0]['audit_requested_edition'])
        self.assertEqual('en',working_set_rows(self.db,ws)[0]['audit_requested_language'])
        self.db.working_sets.set_status(ws,'ARCHIVED')
        with self.assertRaises(ValueError):self.db.working_sets.pin(item,1,self.db.latest_audit(1)['id'])
        with self.assertRaises(ValueError):self.db.working_sets.set_status(ws,'REVIEW')

    def test_app_audit_routes_active_items_only_while_set_is_editable(self):
        self.db.add_titles(['MF Ghost'],'standard','en')
        ws=self.db.working_sets.create('Batch')
        self.db.working_sets.add_requests(ws,['MF Ghost'])
        item=self.db.working_sets.items(ws)[0]['working_set_item_uuid']
        self.save(pub=fixture(unmapped=False))
        self.db.working_sets.pin(item,1,self.db.latest_audit(1)['id'])
        routed=[]
        class FakeThread:
            def __init__(self,target,args,daemon):self.args=args
            def start(self):routed.append(self.args[0])
            def is_alive(self):return False
        app=SimpleNamespace(worker=None,db=self.db,active_set_uuid=ws,queue_ids=[],
            selected_queue_ids=lambda:[],refresh_audit=lambda:None,
            start_button=SimpleNamespace(configure=lambda **_kw:None),
            stop_button=SimpleNamespace(configure=lambda **_kw:None),
            auditor=SimpleNamespace(audit_many=lambda *_args:None),
            workflow=SimpleNamespace(get=lambda:'volume'))
        with patch.object(ddk.threading,'Thread',FakeThread):
            for status,expected in (('OPEN',item),('REVIEW',item),('COMPLETE',1),('ARCHIVED',1)):
                if status=='COMPLETE':self.db.working_sets.set_item_status(item,'REJECTED')
                self.db.working_sets.set_status(ws,status)
                ddk.App.start_audit(app,[1])
                self.assertEqual([expected],routed[-1])

    def test_conceptual_identity_and_edition_acceptance_are_distinct(self):
        self.db.add_titles(['MF Ghost'],'standard','ja')
        self.db.add_titles(['MF Ghost'],'official_color','ja')
        self.db.add_titles(['MF Ghost'],'standard','en')
        self.db.add_titles(['MF Ghost'],'omnibus','en')
        for wid in range(1,5):
            work=self.db.work(wid)
            self.save(wid,pub=fixture(edition=work['edition'],language=work['language'],unmapped=False))
        before={r['id']:r['conceptual_work_uuid'] for r in self.db.works()}
        self.assertEqual(4,len(set(before.values())))
        self.db.working_sets.relate_structure(1,2,'Reviewed Japanese chapter numbering')
        self.assertEqual(self.db.work(1)['conceptual_work_uuid'],self.db.work(2)['conceptual_work_uuid'])
        self.assertNotEqual(self.db.work(1)['work_uuid'],self.db.work(2)['work_uuid'])
        self.assertNotEqual(self.db.work(1)['conceptual_work_uuid'],self.db.work(3)['conceptual_work_uuid'])
        with self.assertRaises(ValueError):self.db.working_sets.relate_structure(1,4,'Wrong language')
        self.db.working_sets.accept(work_ids=[1])
        self.assertEqual('ACCEPTED',self.db.work(1)['lifecycle_status'])
        self.assertEqual('STAGED',self.db.work(2)['lifecycle_status'])

    def test_structure_relationship_requires_exact_publication_context(self):
        self.db.add_titles(['MF Ghost'],'standard','ja')
        self.db.add_titles(['MF Ghost'],'official_color','ja')
        source=fixture(edition='standard',language='ja',context='serial-ja')
        color=fixture(edition='official_color',language='ja',context='color-ja')
        self.save(1,pub=source);self.save(2,pub=color)
        self.db.catalog.apply(self.db.catalog.preview(1,[
            {'entity':'chapter','key':'275','field':'volume','value':'34',
             'verification':'VERIFIED'}]))
        self.db.working_sets.relate_structure(1,2,'Reviewed exact chapter mapping')
        self.assertTrue(self.db.catalog.lookup(color['catalog_identity'],2)['structure_shared'])
        changed=fixture(edition='official_color',language='ja',context='alternate-color-ja')
        self.save(2,pub=changed)
        self.assertNotEqual('matched',self.db.catalog.lookup(changed['catalog_identity'],2)['status'])
        self.assertEqual([],self.db.catalog.state(2)['fields'])

    def test_v5_migration_preserves_fire_force_curation_history_and_source(self):
        self.db.add_titles(['Fire Force'],'standard','en')
        pub=fixture(title='Fire Force',unmapped=True)
        pub['projection']=[dict(pub['projection'][0],id=str(n),chapter=str(n),volume=None,
                                _effective_volume=None) for n in (303,304)]
        pub['normalization']['labels']=['main','main']
        pub['logical_chapters']=2;pub['mapped_chapters']=0;pub['unmapped_chapters']=2
        pub['unmapped']=list(pub['projection'])
        pub['automatic']=dict(pub)
        self.save(pub=pub)
        self.db.catalog.apply(self.db.catalog.preview(1,[
            {'entity':'chapter','key':str(n),'field':'volume','value':'34',
             'verification':'VERIFIED','source_name':'Publisher',
             'source_url':'https://example.org/fire-force','accessed_at':'2026-10-03'}
            for n in (303,304)]))
        original_uuid=self.db.work(1)['work_uuid']
        original_database_uuid=self.db.database_uuid
        original_history=self.db.catalog.history(1)
        from test_supplementary_persistence import schema7
        schema7(self.db)
        with sqlite3.connect(self.db.path) as c:
            c.execute('DROP INDEX works_conceptual_idx')
            c.execute('ALTER TABLE works DROP COLUMN conceptual_work_uuid')
            c.execute('DROP TABLE conceptual_works')
            c.execute('DROP TABLE curated_evidence')
            for column in ('ddk_version','search_core_version','schema_version',
                           'requested_edition','requested_language'):
                c.execute(f'ALTER TABLE search_audits DROP COLUMN {column}')
            for column in ('source_context','target_context'):
                c.execute(f'ALTER TABLE edition_structure_relationships DROP COLUMN {column}')
            c.execute('PRAGMA user_version=5')
        migrated=ddk.DB(self.db.path,role='TEST',migrate_schema8=True)
        with migrated.con() as c:
            self.assertEqual(8,c.execute('PRAGMA user_version').fetchone()[0])
            self.assertEqual('ok',c.execute('PRAGMA quick_check').fetchone()[0])
            self.assertIsNone(c.execute('PRAGMA foreign_key_check').fetchone())
            self.assertIn('conceptual_work_uuid',
                          {r['name'] for r in c.execute('PRAGMA table_info(works)')})
        self.assertEqual(original_database_uuid,migrated.database_uuid)
        self.assertEqual(original_uuid,migrated.work(1)['work_uuid'])
        self.assertEqual(original_uuid,migrated.work(1)['conceptual_work_uuid'])
        self.assertEqual(len(original_history),len(migrated.catalog.history(1)))
        rows={r['key']:r for r in migrated.catalog.rows(1)}
        self.assertEqual('34',rows['303']['effective']['volume'])
        self.assertEqual('34',rows['304']['effective']['volume'])
        self.assertTrue(all(rows[key]['curated']['volume']['verification']=='VERIFIED'
                            for key in ('303','304')))
        self.assertEqual(2,len(migrated.catalog.evidence(1)))
        backups=list((self.db.path.parent/'backups').glob('*before_schema_v6*.db'))
        self.assertEqual(1,len(backups))
        with sqlite3.connect(backups[0]) as c:
            self.assertEqual(5,c.execute('PRAGMA user_version').fetchone()[0])


if __name__=='__main__':unittest.main()
