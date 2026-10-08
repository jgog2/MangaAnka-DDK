"""Offline checks for the 26-title corpus' edition, coverage and candidate cases."""
import queue
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import mangaanka_database_development_kit as ddk
from ddk_chapter_normalization import normalize_acquisition, effective_counts
from ddk_publication import (resolve_publication, publication_holes,
                             selected_acquisition_edition, evaluate_structure_coverage)
from ddk_review import review_packet, health
from mangaanka_search_core.inventory_comparison import SourceInventory
from mangaanka_search_core.search_resolution import SearchResolution
from mangaanka_search_core.enrichment_matching import enrich_content_results

import test_publication_audit as examples

FIXTURES=json.loads((Path(__file__).parent/'fixtures/corpus_systemic_regressions.json').read_text(encoding='utf-8'))


class CorpusSystemicTests(unittest.TestCase):
    def setUp(self):
        network=patch('urllib.request.urlopen',side_effect=AssertionError('Unexpected network'))
        network.start();self.addCleanup(network.stop)

    def test_same_source_serial_and_one_shot_must_not_merge(self):
        case=FIXTURES['same_title_distinct_work']
        row=enrich_content_results([case['provider']],case['external'])[0]
        self.assertEqual('',row.get('canonical_work_id',''))

    def test_related_part_alias_must_not_establish_identity(self):
        case=FIXTURES['related_part_alias']
        row=enrich_content_results([case['provider']],case['external'])[0]
        self.assertEqual('anilist:part-eight-id',row.get('canonical_work_id',''))

    def test_clean_main_identity_keeps_144_chapter_14_volume_projection(self):
        provider={'source_id':'mangapill','source_name':'MangaPill','id':'main',
                  'title':'Example Main','author':'Main Creator','media_type':'manga'}
        candidates=[{'service':'anilist','external_id':'main','primary_title':'Example Main',
                     'authors':['Main Creator'],'reported_chapter_count':144,'reported_volume_count':14},
                    {'service':'anilist','external_id':'side','primary_title':'Example Main',
                     'authors':['Main Creator'],'reported_chapter_count':1,'format':'ONE_SHOT'},
                    {'service':'kitsu','external_id':'main','primary_title':'Example Main',
                     'authors':['Main Creator'],'reported_chapter_count':144,'reported_volume_count':14}]
        selected=enrich_content_results([provider],candidates)[0]
        self.assertEqual('anilist:main|kitsu:main',selected['canonical_work_id'])
        rows=tuple({'id':str(number),'chapter':str(number)} for number in range(1,145))
        inv=SourceInventory('mangapill','MangaPill',selected,'en','original',
                            chapter_count=144,usable=True,complete=True,chapter_records=rows)
        resolution=SearchResolution((selected,),(inv,),primary=inv,language='en')
        wiki=tuple((str(number),str((number-1)//11+1)) for number in range(1,145))
        result=resolve_publication(resolution,[selected],
            service=examples.service({'result':'ok','volumes':{}},wiki=wiki))
        self.assertEqual((144,14,144,0),tuple(result[field] for field in
            ('logical_chapters','final_volumes','mapped_chapters','unmapped_chapters')))

    def test_selected_explicit_color_blocks_standard_even_if_overlay_says_standard(self):
        selected=dict(examples.selected(title='Example (Fan Colored) (Colored)'),
                      edition_class='standard')
        row={'id':'chapter-1','chapter':'1'}
        inv=SourceInventory('mangapill','MangaPill',selected,'en','original',
                            chapter_count=1,usable=True,complete=True,chapter_records=(row,))
        resolution=SearchResolution((selected,),(inv,),primary=inv,language='en')
        publication=resolve_publication(resolution,[selected],
                                        service=examples.service({'result':'ok','volumes':{}}))
        self.assertEqual('fan_color',selected_acquisition_edition(selected))
        self.assertEqual('fan_color',publication['acquisition_edition'])
        self.assertEqual(['WRONG_EDITION_MATCH'],
                         [h['code'] for h in publication_holes(publication,inv,'standard')])

    def test_colored_alias_cannot_change_selected_standard_edition(self):
        selected=dict(examples.selected(),alternate_titles=['Example (Fan Colored)'])
        self.assertEqual('standard',selected_acquisition_edition(selected))

    def test_inventory_report_uses_inspected_result_not_first_search_hit(self):
        selected=dict(examples.selected(title='One Punch Man'),id='standard',url='https://provider.test/standard')
        inv=SourceInventory('mangak','MangaK',selected,'en','original',
                            chapter_count=2,usable=True,complete=True,chapter_records=({'chapter':'1'},))
        auditor=ddk.SearchAuditor(SimpleNamespace(),queue.Queue())
        actual=auditor._inventory_rows(SimpleNamespace(inventories=(inv,)))[0]
        self.assertEqual('One Punch Man',actual['result_title'])
        self.assertEqual('https://provider.test/standard',actual['result_ref'])
        with tempfile.TemporaryDirectory() as tmp:
            db=ddk.DB(Path(tmp)/'catalog.db');db.add_titles(['One Punch Man'],'standard','en')
            work=db.works()[0]
            db.save_audit(work['id'],{'query':'One Punch Man','match_title':'One Punch Man',
                'selected_source':'mangak','inventories':[actual],
                'provider_rows':[{'source_id':'mangak','title':'One Punch Man (Fan Colored)',
                                  'canonical_work_id':'same'}],
                'publication':{'status':'complete','edition':'standard','acquisition_edition':'standard',
                    'selected_acquisition_title':'One Punch Man',
                    'selected_acquisition_ref':'https://provider.test/standard',
                    'raw_acquisition_records':2,
                    'catalog_identity':{'trusted':True,'language':'en'},
                    'context':{'shareable':True},'normalization':{'status':'established'}}},
                [{'code':'UNCLASSIFIED_ACQUISITION','severity':'warning','message':'fixture'}])
            packet=review_packet(db)
            self.assertEqual('One Punch Man',packet['works'][0]['providers'][0]['result_title'])
            self.assertEqual('One Punch Man',packet['works'][0]['selected_acquisition_title'])
            self.assertEqual('https://provider.test/standard',
                             packet['works'][0]['selected_acquisition_ref'])

    def test_sparse_valid_mangadex_allows_wikipedia_fill(self):
        rows=[{'id':str(n),'chapter':str(n)} for n in range(1,11)]
        resolution=examples.resolution(rows)
        md=dict(examples.selected(source='mangadex'),id=examples.FIXTURE['title']['id'])
        sparse={'result':'ok','volumes':{'1':{'volume':'1','chapters':{'one':{'chapter':'1'}}}}}
        wiki=tuple((str(n),str((n-1)//2+1)) for n in range(1,11))
        result=resolve_publication(resolution,[resolution.primary.result,md],
                                   service=examples.service(sparse,wiki=wiki))
        coverage=result['structural_coverage']
        self.assertEqual('valid',result['references']['mangadex_structure']['status'])
        self.assertEqual('sparse',coverage['sources']['mangadex_structure']['coverage'])
        self.assertEqual('complete',coverage['coverage'])
        self.assertEqual((10,0),(result['mapped_chapters'],result['unmapped_chapters']))
        self.assertTrue(coverage['fallback_considered'])

    def test_valid_sparse_reference_without_fallback_remains_publication_review(self):
        rows=[{'id':str(n),'chapter':str(n)} for n in range(1,11)]
        resolution=examples.resolution(rows)
        md=dict(examples.selected(source='mangadex'),id=examples.FIXTURE['title']['id'])
        sparse={'result':'ok','volumes':{'1':{'volume':'1','chapters':{'one':{'chapter':'1'}}}}}
        result=resolve_publication(resolution,[resolution.primary.result,md],
                                   service=examples.service(sparse,wiki=()))
        holes=publication_holes(result,resolution.primary)
        self.assertEqual('valid',result['references']['mangadex_structure']['status'])
        self.assertEqual('sparse',result['structural_coverage']['coverage'])
        self.assertEqual((1,9),(result['mapped_chapters'],result['unmapped_chapters']))
        self.assertIn('UNMAPPED_CHAPTERS',{hole['code'] for hole in holes})
        self.assertEqual('REVIEW',health(result,[{'problem_type':hole['code']} for hole in holes])['publication'])

    def test_sparse_and_partial_final_structure_remain_review(self):
        for logical,mapped,volumes,reported,expected in (
            (113,1,1,16,'sparse'),(253,32,6,29,'sparse'),
            (149,54,8,None,'partial'),(129,29,4,16,'sparse'),
            (142,142,34,34,'complete'),(232,232,24,24,'complete')):
            pub={'logical_chapters':logical,'mapped_chapters':mapped,
                 'unmapped_chapters':logical-mapped,'final_volumes':volumes,'references':{},
                 'projection':[]}
            totals=[{'reported_total_volumes':reported}] if reported else []
            coverage=evaluate_structure_coverage(pub,totals)
            self.assertEqual(expected,coverage['coverage'])
            self.assertEqual(reported,coverage['reported_volume_count'])
        all_numbered={'logical_chapters':113,'mapped_chapters':113,'final_volumes':1,
                      'projection':[],'references':{}}
        self.assertEqual('sparse',evaluate_structure_coverage(
            all_numbered,[{'reported_total_volumes':16}])['coverage'])

    def test_titled_fractional_extras_remain_candidates_without_evidence(self):
        rows=[{'id':'mission-37-5','chapter':'37.5','title':'Mission 37.5'},
              {'id':'mission-44-5','chapter':'44.5','title':'Mission 44.5'}]
        norm=normalize_acquisition(rows,(),SimpleNamespace(chapters=()),'atsu')
        counts=effective_counts(rows,norm)
        self.assertEqual(['provider_fractional_candidate']*2,norm['labels'])
        self.assertEqual('candidate',norm['artifact_groups'][0]['confidence'])
        self.assertEqual((0,0,2),(counts['canonical_main_chapters'],
                                 counts['recognized_specials'],counts['classified_provider_artifacts']))
        self.assertEqual(['mission-37-5','mission-44-5'],
                         [row['record_id'] for row in norm['artifact_groups'][0]['member_records']])


if __name__=='__main__': unittest.main()
