"""Reduced six-title packet cases; all reference lookups are deterministic fixtures."""
import json
import csv
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import mangaanka_database_development_kit as ddk
from ddk_chapter_normalization import (normalize_acquisition, effective_counts,
                                       publication_classification_counts, unclassified_rows)
from ddk_publication import resolve_publication, publication_holes
from ddk_review import health, problem_policy, suggestion, review_packet, packet_markdown, affected_rows, detailed_csv
from mangaanka_search_core.inventory_comparison import SourceInventory
from mangaanka_search_core.search_resolution import SearchResolution
import test_publication_audit as examples


FIXTURE=json.loads((Path(__file__).parent/'fixtures/review_packet_regressions.json').read_text(encoding='utf-8'))


def acquisition(rows, provider='mangak'):
    selected=examples.selected(source=provider)
    inv=SourceInventory(provider,provider,selected,'en','original',chapter_count=len(rows),
                        usable=True,complete=True,chapter_records=tuple(rows))
    return SearchResolution((inv.result,),(inv,),primary=inv,language='en',expected_source_ids=(provider,))


def resolve_rows(rows,wiki):
    res=acquisition(rows)
    family=[res.primary.result,dict(examples.selected(source='mangadex'),id=examples.FIXTURE['title']['id'])]
    return res,resolve_publication(res,family,service=examples.service({'result':'ok','volumes':{}},wiki=wiki))


class PacketRegressions(unittest.TestCase):
    def setUp(self):
        network=patch('urllib.request.urlopen',side_effect=AssertionError('Unexpected network'))
        network.start();self.addCleanup(network.stop)

    def test_duplicate_acquisition_keeps_trusted_mapping_and_raw_provenance(self):
        fixture=FIXTURE['duplicate_trusted_mapping']
        res,pub=resolve_rows(fixture['rows'],((fixture['chapter'],fixture['trusted_wikipedia_volume']),))
        self.assertEqual(2,pub['raw_acquisition_records'])
        self.assertEqual(1,pub['canonical_main_chapters'])
        self.assertEqual(1,pub['duplicate_records'])
        self.assertEqual(1,pub['mapped_chapters'])
        self.assertEqual(0,pub['unmapped_chapters'])
        self.assertNotIn('125',pub['conflicting_chapters'])
        self.assertEqual({r['id'] for r in fixture['rows']},{r['id'] for r in pub['projection']})
        self.assertFalse(any(h['code']=='REFERENCE_CONFLICT' for h in publication_holes(pub,res.primary)))

    def test_conflicting_structural_values_still_fail_closed(self):
        fixture=FIXTURE['structural_conflict']
        res,pub=resolve_rows([{'id':'primary','chapter':'125'}],
                             tuple((fixture['chapter'],v) for v in fixture['wikipedia_volumes']))
        self.assertIn('125',pub['conflicting_chapters'])
        self.assertTrue(any(h['code']=='REFERENCE_CONFLICT' for h in publication_holes(pub,res.primary)))
        provider_rows=[{'id':'release-a','chapter':'125','volume':'31'},
                       {'id':'release-b','chapter':'125','volume':'32'}]
        res,pub=resolve_rows(provider_rows,())
        self.assertIn('125',pub['conflicting_chapters'])
        self.assertEqual(0,pub['mapped_chapters'])
        self.assertTrue(any(h['code']=='REFERENCE_CONFLICT' for h in publication_holes(pub,res.primary)))

    def test_provider_explicit_membership_keeps_precedence_on_duplicate_rows(self):
        rows=[{'id':'provider-explicit','chapter':'125','volume':'31'},
              {'id':'provider-duplicate','chapter':'125'}]
        res,pub=resolve_rows(rows,(('125','32'),))
        self.assertEqual(1,pub['mapped_chapters'])
        self.assertEqual(0,pub['unmapped_chapters'])
        self.assertEqual({'31'},{r['_effective_volume'] for r in pub['projection']})
        self.assertFalse(pub['conflicting_chapters'])
        self.assertFalse(any(h['code']=='REFERENCE_CONFLICT' for h in publication_holes(pub,res.primary)))

    def test_range_bundle_does_not_inflate_canonical_chapters(self):
        rows=FIXTURE['range_bundle']['records']
        norm=normalize_acquisition(rows,(),SimpleNamespace(chapters=()),'mangak')
        self.assertEqual(['provider_range_bundle']*2,norm['labels'])
        self.assertEqual(0,effective_counts(rows,norm)['logical_chapters'])
        self.assertEqual(2,norm['artifact_groups'][0]['count'])
        self.assertEqual('syntax',norm['artifact_groups'][0]['confidence'])

    def test_split_candidate_detected_without_canonicalizing(self):
        rows=FIXTURE['split_candidate']['records']
        norm=normalize_acquisition(rows,(),SimpleNamespace(chapters=()),'mangak')
        self.assertEqual(['provider_split_candidate']*4,norm['labels'])
        self.assertEqual(0,effective_counts(rows,norm)['logical_chapters'])
        self.assertEqual(['141.1','141.2','142.1','142.2'],norm['artifact_groups'][0]['identifiers'])
        self.assertEqual('candidate',norm['artifact_groups'][0]['confidence'])

    def test_fractional_provider_candidates_remain_unresolved(self):
        rows=[{'id':f'extra-{number}','chapter':number} for number in
              FIXTURE['publication_complete_unclassified']['provider_fractional']]
        norm=normalize_acquisition(rows,(),SimpleNamespace(chapters=()),'mangak')
        self.assertEqual(['provider_fractional_candidate']*len(rows),norm['labels'])
        self.assertEqual(0,effective_counts(rows,norm)['logical_chapters'])
        self.assertEqual('repeated_fractional_numbering',norm['artifact_groups'][0]['pattern_family'])
        self.assertEqual('candidate',norm['artifact_groups'][0]['confidence'])
        self.assertEqual(('CODE','CODE_REVIEW_REQUIRED','root',False),
                         problem_policy('PROVIDER_FRACTIONAL_CANDIDATE'))

    def test_count_semantics_for_chainsaw_and_attack_shapes(self):
        for canonical,artifacts,unknown in ((232,{'provider_fractional_candidate':12,
                'provider_range_bundle':11,'provider_split_candidate':134},1),
                (142,{'provider_fractional_candidate':2},3)):
            labels=['main']*canonical+sum(([label]*count for label,count in artifacts.items()),[])+['unclassified']*unknown
            rows=[{'chapter':str(index),'_effective_volume':'1' if label=='main' else None}
                  for index,label in enumerate(labels)]
            counts=effective_counts(rows,{'labels':labels,'counts':{label:labels.count(label) for label in set(labels)}})
            self.assertEqual(canonical,counts['canonical_main_chapters'])
            self.assertEqual(canonical,counts['logical_chapters'])
            self.assertEqual(sum(artifacts.values()),counts['classified_provider_artifacts'])
            self.assertEqual(artifacts,counts['provider_artifact_breakdown'])
            self.assertEqual(unknown,counts['unclassified_records'])
            self.assertEqual(canonical+sum(artifacts.values())+unknown,len(rows))
            unknown_rows=unclassified_rows(rows,{'labels':labels,'counts':{label:labels.count(label)
                                                                    for label in set(labels)},'evidence':{}})
            self.assertEqual(unknown,len(unknown_rows))
            self.assertTrue(all(row['classification']=='unclassified' for row in unknown_rows))
        self.assertEqual(390,len(['main']*232+['x']*157+['unclassified']))

    def test_attack_shaped_publication_health_stays_pass(self):
        pub={'status':'complete','edition':'standard','context':{'shareable':True},
             'catalog_identity':{'trusted':True,'language':'en'},
             'normalization':{'status':'established'},'raw_acquisition_records':147,
             'canonical_main_chapters':142,'logical_chapters':142,'mapped_chapters':142,
             'unmapped_chapters':0,'final_volumes':34,'conflicting_chapters':[],
             'classified_provider_artifacts':2,'unclassified_records':3}
        result=health(pub,[{'problem_type':'PROVIDER_FRACTIONAL_CANDIDATE'},
                           {'problem_type':'UNCLASSIFIED_ACQUISITION'}])
        self.assertEqual(('PASS','PASS','REVIEW','PASS'),
                         tuple(result[key] for key in ('identity','publication','normalization','acquisition')))

    def test_stored_old_aggregate_is_corrected_on_read(self):
        publication={'unclassified_records':158,'normalization':{'counts':{
            'main':232,'provider_fractional_candidate':12,'provider_range_bundle':11,
            'provider_split_candidate':134,'unclassified':1}}}
        counts=publication_classification_counts(publication)
        self.assertEqual(157,counts['classified_provider_artifacts'])
        self.assertEqual(1,counts['unclassified_records'])

    def test_artifact_presentation_is_code_with_uncertainty_preserved(self):
        for code in ('PROVIDER_RANGE_BUNDLE','PROVIDER_SPLIT_CANDIDATE',
                     'PROVIDER_FRACTIONAL_CANDIDATE'):
            self.assertEqual(('CODE','CODE_REVIEW_REQUIRED','root',False),problem_policy(code))
        self.assertEqual('RESEARCH',problem_policy('REFERENCE_CONFLICT')[0])
        self.assertEqual('UNKNOWN',problem_policy('UNCLASSIFIED_ACQUISITION')[0])

    def test_packet_summarizes_clean_omission_and_export_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=ddk.DB(Path(tmp)/'catalog.db')
            db.add_titles(['Clean Work','Review Work','Error Work'],'standard','en')
            def publication(edition='standard'):
                return {'status':'complete','edition':edition,'logical_chapters':232,
                    'canonical_main_chapters':232,'mapped_chapters':232,'unmapped_chapters':0,
                    'final_volumes':24,'raw_acquisition_records':390,'unclassified_records':158,
                    'normalization':{'status':'established','counts':{'main':232,
                        'provider_fractional_candidate':12,'provider_range_bundle':11,
                        'provider_split_candidate':134,'unclassified':1}},
                    'catalog_identity':{'trusted':True,'edition':edition,'language':'en'},
                    'context':{'shareable':True},'curation_revision':0,
                    'projection':[{'chapter':'1','id':'one','_acquisition_provider':'mangak'}]}
            works={row['input_title']:row for row in db.works()}
            db.save_audit(works['Clean Work']['id'],{'query':'Clean Work','match_title':'Clean Work',
                'publication':publication()},[])
            db.save_audit(works['Review Work']['id'],{'query':'Review Work','match_title':'Review Work',
                'publication':publication()},[{'code':'PROVIDER_RANGE_BUNDLE','severity':'warning',
                'message':'Range','details':{'affected':1,'chapters':['8-16'],
                                            'confidence':'syntax'}}])
            db.save_audit(works['Error Work']['id'],{'query':'Error Work','match_title':'Error Work',
                'publication':publication()},[{'code':'SOURCE_FAILURE','severity':'error',
                'message':'Source unavailable'}])
            packet=review_packet(db)
            self.assertEqual({'titles_audited':3,'pass':1,'review':1,'error':1,
                'detailed_works_included':2,'clean_works_omitted':1},packet['audit_summary'])
            self.assertEqual([{'title':'Clean Work','state':'PASS'}],packet['clean_works_omitted'])
            self.assertEqual({'Review Work','Error Work'},{w['query'] for w in packet['works']})
            selected_clean=review_packet(db,work_ids={works['Clean Work']['id']})
            self.assertEqual([],selected_clean['works'])
            self.assertEqual([{'title':'Clean Work','state':'PASS'}],
                             selected_clean['clean_works_omitted'])
            review_work=next(w for w in packet['works'] if w['query']=='Review Work')
            self.assertEqual((157,1),(review_work['counts']['classified_provider_artifacts'],
                                      review_work['counts']['unclassified_records']))
            self.assertEqual(('CODE','CODE_REVIEW_REQUIRED','syntax'),
                (review_work['issues'][0]['problem_class'],review_work['issues'][0]['next_action'],
                 review_work['issues'][0]['confidence']))
            markdown=packet_markdown(packet)
            self.assertIn('Titles audited: 3',markdown)
            self.assertIn('- Clean Work — PASS',markdown)
            self.assertNotIn('## Clean Work',markdown)
            path=Path(tmp)/'detail.csv';detailed_csv(packet,path)
            with path.open(encoding='utf-8-sig',newline='') as f: csv_rows=list(csv.DictReader(f))
            review_row=next(row for row in csv_rows if row['query']=='Review Work')
            self.assertEqual('157',review_row['classified_provider_artifacts'])
            self.assertEqual('1',review_row['unclassified_records'])
            self.assertEqual('390',review_row['raw_acquisition_records'])
            self.assertEqual('syntax',review_row['confidence'])
            summary_path=Path(tmp)/'summary.csv';db.audit_summary_csv(summary_path)
            with summary_path.open(encoding='utf-8-sig',newline='') as f:
                summary_rows={row['Query']:row for row in csv.DictReader(f)}
            self.assertEqual('157',summary_rows['Review Work']['Classified Provider Artifacts'])
            self.assertEqual('1',summary_rows['Review Work']['Unclassified Records'])

    def test_packet_affected_rows_preserve_fractional_identifier_and_provider(self):
        rows=FIXTURE['split_candidate']['records']
        norm=normalize_acquisition(rows,(),SimpleNamespace(chapters=()),'mangak')
        projection=[dict(row,_acquisition_provider='mangak') for row in rows]
        affected=affected_rows({'projection':projection,'normalization':norm},
                               {'chapters':['0141.1']},[])
        self.assertEqual('0141.1',affected[0]['identifier'])
        self.assertEqual('mangak',affected[0]['provider'])
        self.assertEqual(rows[0]['id'],affected[0]['provider_record_id'])
        self.assertEqual('paired_fractional_suffix',affected[0]['pattern_family'])

    def test_artifact_holes_aggregate_without_publication_mapping_noise(self):
        rows=[{'id':'main','chapter':'1'},*FIXTURE['range_bundle']['records'],
              *FIXTURE['split_candidate']['records']]
        res,pub=resolve_rows(rows,(('1','1'),))
        codes={h['code'] for h in publication_holes(pub,res.primary)}
        self.assertIn('PROVIDER_RANGE_BUNDLE',codes)
        self.assertIn('PROVIDER_SPLIT_CANDIDATE',codes)
        self.assertNotIn('REFERENCE_CONFLICT',codes)
        self.assertEqual(1,pub['logical_chapters'])
        self.assertEqual(1,pub['mapped_chapters'])
        self.assertEqual(len(rows),pub['raw_acquisition_records'])

    def test_chainsaw_packet_counts_remain_publication_complete(self):
        counts=FIXTURE['publication_complete_provider_artifacts']
        pub={'status':'complete','edition':'standard','context':{'shareable':True},
             'catalog_identity':{'trusted':True,'language':'en'},
             'normalization':{'status':'established'},'raw_acquisition_records':counts['raw'],
             'canonical_main_chapters':counts['canonical'],'logical_chapters':counts['canonical'],
             'mapped_chapters':counts['mapped'],'final_volumes':counts['volumes'],
             'unclassified_records':counts['artifact_records'],'unmapped_chapters':0,
             'conflicting_chapters':[]}
        dimensions=health(pub,[{'problem_type':'PROVIDER_SPLIT_CANDIDATE'},
                               {'problem_type':'CHAPTER_COUNT_DISAGREEMENT'}])
        self.assertEqual('PASS',dimensions['publication'])
        self.assertEqual('REVIEW',dimensions['normalization'])
        self.assertEqual('PARTIAL',dimensions['acquisition'])

    def test_health_separates_publication_normalization_acquisition_and_identity(self):
        jjk=FIXTURE['publication_complete_unclassified']
        demon=FIXTURE['publication_complete_acquisition_partial']
        pub={'status':'complete','edition':'standard','context':{'shareable':True},
             'catalog_identity':{'trusted':True,'language':'en'},
             'normalization':{'status':'established'},'raw_acquisition_records':277,
             'mapped_chapters':jjk['mapped'],'logical_chapters':jjk['canonical'],
             'final_volumes':jjk['volumes'],'unmapped_chapters':0,'conflicting_chapters':[]}
        self.assertEqual('PASS',health(pub,[{'problem_type':'UNCLASSIFIED_ACQUISITION'}])['publication'])
        self.assertEqual('REVIEW',health(pub,[{'problem_type':'UNCLASSIFIED_ACQUISITION'}])['normalization'])
        demon_pub=dict(pub,raw_acquisition_records=demon['canonical'],mapped_chapters=demon['mapped'],
                       logical_chapters=demon['canonical'],final_volumes=demon['volumes'])
        self.assertEqual('PASS',health(demon_pub,[{'problem_type':'CHAPTER_COUNT_DISAGREEMENT'}])['publication'])
        self.assertEqual('PARTIAL',health(demon_pub,[{'problem_type':'CHAPTER_COUNT_DISAGREEMENT'}])['acquisition'])
        wrong=dict(pub,edition='fan_color')
        self.assertEqual('ERROR',health(wrong,[{'problem_type':'WRONG_EDITION_MATCH'}])['identity'])
        self.assertEqual(('IDENTITY','BLOCKED_IDENTITY','blocking',False),problem_policy('WRONG_EDITION_MATCH'))

    def test_problem_specific_recommendations(self):
        pub={'status':'complete','edition':'standard','catalog_identity':{'trusted':True,'edition':'standard'}}
        for problem,needle in (('WRONG_EDITION_MATCH','edition'),('CHAPTER_COUNT_DISAGREEMENT','acquisition'),
                               ('REFERENCE_CONFLICT','structural'),('PROVIDER_SPLIT_CANDIDATE','normalization')):
            issue={'problem_type':problem,'affected_rows':[],
                   'problem_class':('IDENTITY' if problem=='WRONG_EDITION_MATCH' else
                                    'ACQUISITION' if problem=='CHAPTER_COUNT_DISAGREEMENT' else 'RESEARCH'),
                   'next_action':'BLOCKED_IDENTITY' if problem=='WRONG_EDITION_MATCH' else 'RESEARCH_REQUIRED'}
            with self.subTest(problem=problem):
                result=suggestion(issue,pub)
                self.assertIsNone(result['command'])
                self.assertIn(needle,result['reason'].lower())

    def test_packet_code_candidates_group_one_and_multiple_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=ddk.DB(Path(tmp)/'catalog.db');db.add_titles(['Fixture A','Fixture B'],'standard','en')
            group={'provider':'mangak','classification':'provider_split_candidate',
                   'pattern_family':'paired_fractional_suffix','count':4,
                   'identifiers':['141.1','141.2','142.1','142.2'],
                   'representative_identifiers':['141.1','141.2'],
                   'confidence':'candidate','reason':'Repeated adjacent suffix pairs outside canonical set.'}
            for work in db.works():
                pub={'status':'complete','edition':'standard','normalization':{'status':'established','artifact_groups':[group]},
                     'catalog_identity':{'trusted':True,'edition':'standard','language':'en'},
                     'context':{'shareable':True},'raw_acquisition_records':4,'unmapped_chapters':0}
                db.save_audit(work['id'],{'query':work['input_title'],'match_title':work['input_title'],
                    'selected_source':'mangak','publication':pub},[{'code':'PROVIDER_SPLIT_CANDIDATE',
                    'severity':'warning','message':'Split candidate','details':{'affected':4,'chapters':group['identifiers']}}])
            packet=review_packet(db)
            candidate=next(c for c in packet['code_review_candidates'] if c.get('pattern_family')=='paired_fractional_suffix')
            self.assertEqual(2,candidate['works'])
            self.assertEqual(8,candidate['records'])
            self.assertEqual('mangak',candidate['provider'])
            self.assertEqual(8,len(candidate['all_identifiers']))
            self.assertIn('paired_fractional_suffix',packet_markdown(packet))
            self.assertIn(f'guard database_uuid {db.database_uuid} audit',packet['works'][0]['guard'])

    def test_code_candidate_requires_valid_identity_and_tracks_latest_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=ddk.DB(Path(tmp)/'catalog.db');db.add_titles(['Fixture A','Fixture B'],'standard','en')
            group={'provider':'mangak','classification':'provider_range_bundle',
                   'pattern_family':'integer_range_bundle','count':2,
                   'identifiers':['8-16','80-88'],'member_records':[
                       {'identifier':'8-16','record_id':'a'},
                       {'identifier':'80-88','record_id':'b'}]}
            works=db.works()
            def save(work,holes):
                db.save_audit(work['id'],{'query':work['input_title'],
                    'match_title':work['input_title'],'selected_source':'mangak',
                    'publication':{'status':'complete','edition':'standard',
                                   'normalization':{'artifact_groups':[group]}}},holes)
            save(works[0],[])
            self.assertEqual(1,len(db.code_review_candidates()))
            save(works[1],[{'code':'WRONG_EDITION_MATCH','severity':'error','message':'Wrong edition'}])
            self.assertEqual(1,db.code_review_candidates()[0]['works'])
            save(works[0],[])
            self.assertEqual(1,db.code_review_candidates()[0]['works'])
            self.assertEqual(2,db.code_review_candidates()[0]['records'])

    def test_world_control(self):
        pub=examples.resolve()
        expected=FIXTURE['world_control']
        self.assertEqual((expected['canonical'],expected['volumes'],expected['mapped'],expected['holes']),
                         (pub['logical_chapters'],pub['final_volumes'],pub['mapped_chapters'],len(publication_holes(pub,examples.resolution().primary))))


if __name__=='__main__': unittest.main()
