"""Offline group policy through the shared provider and full DDK publication path."""
from copy import deepcopy
from dataclasses import asdict, replace
import json
from pathlib import Path
import unittest

from mangaanka_search_core.atsu_source import AtsuSource
from mangaanka_search_core.atsu_acquisition import resolve_atsu_acquisition
from mangaanka_search_core.wikipedia_reference import WikipediaPublicationAdapter
from mangaanka_search_core.inventory_comparison import SourceInventory
from mangaanka_search_core.search_resolution import SearchResolution
from ddk_publication import resolve_publication, publication_holes
from ddk_review import health, problem_policy
from test_publication_states import fixture, resolved, Service


class AtsuAcquisition(unittest.TestCase):
    def test_captured_dandadan_primary_preserves_completed_publication(self):
        root=Path(__file__).parent/'fixtures'
        feed=json.loads((root/'publication_freshness_evidence/atsu_dandadan_allchapters.json').read_text(encoding='utf-8'))
        page=json.loads((root/'atsu_group_page.json').read_text(encoding='utf-8'))
        source=AtsuSource();source._api=lambda path,**kw:deepcopy(page if path.endswith('/page') else feed)
        rows=source.get_chapters('https://atsu.moe/manga/m7bps','en')
        old=json.loads((root/'dandadan_audit18_review.json').read_text(encoding='utf-8'))['publication']
        bundle=deepcopy(old['references'])
        text=json.loads((root/'publication_freshness_evidence/wikipedia_audit18_revision.json').read_text(encoding='utf-8'))['parse']['wikitext']['*']
        wiki=WikipediaPublicationAdapter();wiki._wikitext=lambda _:text
        bundle['wikipedia']['volumes']=[asdict(v) for v,_ in wiki._parse_graphic_lists('List of Dandadan chapters','Dandadan')]
        selected=dict(source_id='atsu',id='m7bps',url='https://atsu.moe/manga/m7bps',title='Dandadan',
            canonical_title='Dandadan',canonical_work_id=old['catalog_identity']['canonical_work_id'],
            canonical_creators=['Yukinobu Tatsu'],author='Yukinobu Tatsu',_canonical_identity_confidence='high',media_type='manga')
        inv=SourceInventory('atsu','Atsu',selected,'en','original',chapter_count=len(rows),usable=True,complete=True,chapter_records=tuple(rows))
        res=SearchResolution((selected,),(inv,),primary=inv,language='en')
        p=resolve_publication(res,[selected],service=Service(bundle),as_of='2026-10-04')
        self.assertEqual((248,221,27,0,25),tuple(p[k] for k in ('canonical_main_chapters','mapped_main_chapters','uncompiled_chapters','unmapped_chapters','final_volumes')))
        groups=p['provider_group_acquisition'];self.assertEqual((481,233),(groups['raw_count'],len(groups['alternatives'])))
        decimals=[r for r in groups['alternatives'] if r['classification']=='alternate_fractional']
        self.assertEqual(['19.5','89.1','92.5'],[r['chapter'] for r in decimals])
        self.assertFalse(any(r['requires_review'] for r in groups['alternatives']))
        holes=publication_holes(p,inv);self.assertEqual(['CHAPTER_COUNT_DISAGREEMENT'],[h['code'] for h in holes])
        self.assertEqual(['14.5','201.5','23.5','49.5','5.5','58.5','67.5','76.5','85.5'],p['missing_reference_chapters'])
        self.assertEqual(('ACQUISITION','ACQUISITION_ONLY'),problem_policy(holes[0]['code'],holes[0]['details'])[:2])
        self.assertEqual(dict(identity='PASS',publication='PASS',normalization='PASS',acquisition='PARTIAL'),
            health(p,[dict(problem_type=h['code']) for h in holes]))

    def test_incomplete_primary_keeps_alternate_uncertainty_blocking(self):
        res,bundle=fixture(extras=False)
        primary=[dict(id='a19',chapter='19',title='',volume=None,_scanlation_id='a',_atsu_group_role='primary')]
        primary[0]['_atsu_group_inventory']=dict(contract='atsu-groups-v1',primary_group='a',recommendation_basis='api_recommended_order',
            edition='original',language='en',alternatives=[dict(id='b195',chapter='19.5',title='',volume=None,_scanlation_id='b',_atsu_group_compatible=True)])
        inv=replace(res.primary,chapter_records=tuple(primary),chapter_count=1);res=replace(res,primary=inv,inventories=(inv,))
        p=resolved(res,bundle);holes=publication_holes(p,inv)
        self.assertNotIn('19.5',[r['chapter'] for r in p['projection']])
        issue=next(h for h in holes if h['code']=='PROVIDER_GROUP_CANDIDATE')
        self.assertEqual(('CODE','CODE_REVIEW_REQUIRED'),problem_policy(issue['code'],issue['details'])[:2])
        self.assertTrue(p['provider_group_acquisition']['alternatives'][0]['requires_review'])

    def test_two_independent_peers_recover_but_same_provider_does_not(self):
        res,_=fixture(extras=False)
        rows=[dict(chapter='1',id='a1',_atsu_group_role='primary',_scanlation_id='a')]
        rows[0]['_atsu_group_inventory']=dict(contract='atsu-groups-v1',primary_group='a',recommendation_basis='api_recommended_order',
            edition='original',language='en',alternatives=[dict(chapter='2',id='b2',_atsu_group_compatible=True,_scanlation_id='b')])
        peers=[replace(res.primary,source_id=s,chapter_records=(dict(chapter='2'),)) for s in ('mangapill','weebcentral')]
        self.assertEqual(['1','2'],[r['chapter'] for r in resolve_atsu_acquisition(rows,independent_inventories=peers)['rows']])
        for bad in ([peers[0]], [peers[0],replace(peers[1],language='ja')], [peers[0],replace(peers[1],edition='fan_color')]):
            self.assertEqual(['1'],[r['chapter'] for r in resolve_atsu_acquisition(rows,independent_inventories=bad)['rows']])


if __name__=='__main__':unittest.main()
