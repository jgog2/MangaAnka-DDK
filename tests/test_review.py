"""Review workflow tests use only disposable SQLite files and fixture references."""
import csv
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

import mangaanka_database_development_kit as ddk
from ddk_commands import parse_batch
from ddk_review import (database_revision, detailed_csv, packet_markdown,
                        problem_policy, review_packet, write_packet, suggestion, health)
import test_catalog as fixtures
from ddk_publication import publication_holes


class ReviewCase(unittest.TestCase):
    setUp=fixtures.CatalogCase.setUp
    resolve=fixtures.CatalogCase.resolve
    refresh=fixtures.CatalogCase.refresh
    edit=fixtures.CatalogCase.edit

    def test_packet_selection_and_complete_affected_rows(self):
        self.db.add_titles(['Other'],'standard','en')
        self.db.save_audit(2,{'query':'Other','publication':{'status':'complete','edition':'standard'}},
                           [{'code':'SOURCE_FAILURE','severity':'error','message':'Fixture error'}])
        all_packet=review_packet(self.db)
        self.assertEqual([1,2],[w['work_id'] for w in all_packet['works']])
        packet=review_packet(self.db,work_ids={1})
        self.assertEqual(1,len(packet['works']))
        issues=packet['works'][0]['issues']
        self.assertTrue(issues)
        self.assertEqual(packet['database_revision'],database_revision(self.db))
        for issue in issues:
            self.assertEqual(issue['audit_id'],packet['works'][0]['audit_id'])
            self.assertIn('problem_class',issue)
            self.assertIn('next_action',issue)
        chapter_issues=[i for i in issues if i['problem_type']=='UNMAPPED_CHAPTERS']
        if chapter_issues:
            self.assertEqual(chapter_issues[0]['affected_count'],len(chapter_issues[0]['affected_rows']))
        text=packet_markdown(packet)
        self.assertIn('Guard for proposed edit batches',text)
        self.assertIn('Re-audit diff',text)
        with tempfile.TemporaryDirectory() as tmp:
            md,js=write_packet(packet,Path(tmp)/'packet.md')
            self.assertEqual(packet,json.loads(js.read_text(encoding='utf-8')))
            self.assertEqual(text,md.read_text(encoding='utf-8'))
            path=Path(tmp)/'detail.csv';count=detailed_csv(packet,path)
            with path.open(encoding='utf-8-sig',newline='') as inp:
                rows=list(csv.DictReader(inp))
            self.assertEqual(count,len(rows))
            self.assertTrue(rows)
            self.assertIn('provider_title',rows[0])

    def test_guard_rejects_changed_audit_and_database(self):
        packet=review_packet(self.db,work_ids={1})
        guard=parse_batch(packet['works'][0]['guard']+'\nset volume 24 chapter 222')[0]
        change=[{'entity':'chapter','key':'222','field':'volume','value':'24'}]
        preview=self.store.preview(1,change,guard=guard)
        self.assertEqual(guard,preview['guard'])
        with self.assertRaisesRegex(ValueError,'first line'):
            parse_batch('set volume 24 chapter 222\n'+packet['works'][0]['guard'])
        with self.assertRaisesRegex(ValueError,'revision guard needs'):
            parse_batch(packet['works'][0]['guard'])
        self.refresh()
        with self.assertRaisesRegex(ValueError,'Stale'):
            self.store.preview(1,change,guard=guard)
        with self.assertRaisesRegex(ValueError,'Stale'):
            self.store.apply(preview)
        self.assertEqual([],self.store.state(1)['fields'])

    def test_guard_apply_rechecks_disposition_revision(self):
        pub=self.resolve()
        self.db.save_audit(1,{'query':'Example','publication':pub},
                           [{'code':'UNCLASSIFIED_ACQUISITION','severity':'warning',
                             'message':'fixture unknown','details':{'affected':1,'chapters':['222']}}])
        packet=review_packet(self.db,work_ids={1})
        guard=parse_batch(packet['works'][0]['guard']+'\nset volume 24 chapter 222')[0]
        preview=self.store.preview(1,[{'entity':'chapter','key':'222','field':'volume','value':'24'}],guard=guard)
        problem=self.db.holes('UNCLASSIFIED_ACQUISITION')[0]
        self.db.dispose_problem(problem['id'],'Verified alternate provider record',pattern='split x.1/x.2')
        with self.assertRaisesRegex(ValueError,'Stale review packet'):
            self.store.apply(preview)
        self.assertEqual([],self.store.state(1)['fields'])

    def test_packet_after_curation_requires_reaudit(self):
        self.store.apply(self.edit())
        packet=review_packet(self.db,work_ids={1})
        self.assertFalse(packet['works'][0]['audit_fresh'])
        guard=parse_batch(packet['works'][0]['guard']+'\nset volume 25 chapter 223')[0]
        with self.assertRaisesRegex(ValueError,'re-audit'):
            self.store.preview(1,[{'entity':'chapter','key':'223','field':'volume','value':'25'}],guard=guard)

    def test_disposition_suppression_and_signature_carry_forward(self):
        pub=self.resolve()
        hole={'code':'UNCLASSIFIED_ACQUISITION','severity':'warning','message':'fixture unknown',
              'details':{'affected':1,'chapters':['222']}}
        self.db.save_audit(1,{'query':'Example','publication':pub},[hole])
        row=self.db.holes('UNCLASSIFIED_ACQUISITION')[0]
        with self.assertRaisesRegex(ValueError,'reason'): self.db.dispose_problem(row['id'],'')
        self.db.dispose_problem(row['id'],'Provider extra verified','VERIFIED','split x.1/x.2')
        self.assertFalse(self.db.holes('UNCLASSIFIED_ACQUISITION'))
        self.assertEqual('IGNORED_WITH_REASON',self.db.problem_disposition(row['id'])['status'])
        self.db.save_audit(1,{'query':'Example','publication':pub},[hole])
        self.assertFalse(self.db.holes('UNCLASSIFIED_ACQUISITION'))
        self.assertEqual(1,len(self.db.holes('UNCLASSIFIED_ACQUISITION',include_ignored=True)))
        self.db.add_titles(['Other'],'standard','en')
        other_pub=json.loads(json.dumps(pub))
        other_pub['catalog_identity']['canonical_work_id']='fixture:other'
        other_pub['catalog_identity']['external_ids']={'fixture':'other'}
        self.db.save_audit(2,{'query':'Other','publication':other_pub},[hole])
        other=next(h for h in self.db.holes('UNCLASSIFIED_ACQUISITION') if h['work_id']==2)
        self.db.dispose_problem(other['id'],'Same provider pattern','REVIEWED','split x.1/x.2')
        self.assertEqual(1,len(self.db.code_review_candidates()))
        with self.assertRaisesRegex(ValueError,'reason'):
            self.db.reopen_problem(other['id'],'')
        self.db.reopen_problem(other['id'],'Classification needs another look')
        self.assertEqual('REOPENED',self.db.problem_disposition(other['id'])['status'])
        self.assertEqual(1,len(self.db.holes('UNCLASSIFIED_ACQUISITION')))
        self.assertEqual([],self.db.code_review_candidates())
        diff=self.db.audit_diff(1)
        self.assertIn('health',diff)
        self.assertIn('problem_count',diff)

    def test_disposition_does_not_hide_publication_or_identity_error(self):
        pub=self.resolve()
        self.db.save_audit(1,{'query':'Example','publication':pub},
                           [{'code':'UNMAPPED_CHAPTERS','severity':'warning','message':'fixture'}])
        with self.assertRaisesRegex(ValueError,'Only unclassified'):
            self.db.dispose_problem(self.db.holes()[0]['id'],'Not important')
        self.assertEqual(1,len(self.db.holes()))
        self.assertEqual(('IDENTITY','BLOCKED_IDENTITY','blocking',False),
                         problem_policy('WRONG_EDITION_MATCH'))

    def test_deterministic_suggestion_requires_trusted_exact_agreement(self):
        row={'identifier':'222','mangadex_value':'24','wikipedia_value':'24',
             'automatic_volume':None,'curated_volume':None,'reference_conflict':False,
             'normalization_class':'main'}
        issue={'problem_type':'UNMAPPED_CHAPTERS','affected_rows':[row]}
        pub={'status':'complete','edition':'standard',
             'catalog_identity':{'trusted':True,'edition':'standard'},'references':{
            'mangadex_structure':{'status':'valid'},'wikipedia':{'status':'valid_complete'}}}
        self.assertEqual('set volume 24 chapter 222',suggestion(issue,pub)['command'])
        self.assertIsNone(suggestion(issue,dict(pub,references={}))['command'])
        self.assertIsNone(suggestion(dict(issue,affected_rows=[dict(row,wikipedia_value='25')]),pub)['command'])
        self.assertIsNone(suggestion(issue,dict(pub,catalog_identity={'trusted':False}))['command'])

    def test_health_dimensions_separate_provider_and_publication(self):
        pub={'status':'complete','edition':'standard','context':{'shareable':True},
             'catalog_identity':{'language':'en','trusted':True},'raw_acquisition_records':10,
             'normalization':{'status':'established'},
             'unmapped_chapters':0,'conflicting_chapters':[]}
        self.assertEqual({'identity':'PASS','publication':'PASS','normalization':'REVIEW','acquisition':'PASS'},
                         health(pub,[{'problem_type':'UNCLASSIFIED_ACQUISITION'}]))
        self.assertEqual({'identity':'PASS','publication':'PASS','normalization':'PASS','acquisition':'PARTIAL'},
                         health(pub,[{'problem_type':'CHAPTER_COUNT_DISAGREEMENT'}]))
        self.assertEqual('ERROR',health(pub,[{'problem_type':'WRONG_EDITION_MATCH'}])['identity'])
        self.db.save_audit(1,{'query':'Example','publication':dict(pub,curation_revision=0)},[])
        self.assertEqual('PASS',ddk.audit_status(self.db.works()[0]))
        self.db.save_audit(1,{'query':'Example','publication':dict(pub,context={'shareable':False},curation_revision=0)},[])
        self.assertEqual('REVIEW',ddk.audit_status(self.db.works()[0]))

    def test_additive_legacy_schema_migration(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'old.db'
            with sqlite3.connect(path) as con:
                con.executescript(ddk.SCHEMA.split('CREATE TABLE IF NOT EXISTS problem_dispositions')[0])
                con.execute("INSERT INTO works(id,input_title,edition,language) VALUES(1,'Old','standard','en')")
            migrated=ddk.DB(path,migrate_schema8=True)
            self.assertEqual('Old',migrated.work(1)['input_title'])
            backups=list((Path(tmp)/'backups').glob('old_before_schema_v6_*.db'))
            self.assertEqual(1,len(backups))
            with closing(sqlite3.connect(backups[0])) as original:
                self.assertEqual('Old',original.execute('SELECT input_title FROM works WHERE id=1').fetchone()[0])
            with migrated.con() as con:
                self.assertIn('audit_revision',{r['name'] for r in con.execute('PRAGMA table_info(search_audits)')})
                self.assertEqual(8,con.execute('PRAGMA user_version').fetchone()[0])
                self.assertTrue(migrated.database_uuid)


if __name__=='__main__': unittest.main()
