"""Main, special, artifact and acquisition coverage are distinct units."""
from dataclasses import replace
import unittest

from test_publication_states import fixture, resolved
from ddk_publication import publication_holes
from ddk_review import health


def publication(keys,refs=()):
    res,bundle=fixture(extras=False)
    rows=tuple(dict(chapter=k,id='reader:'+k) for k in keys)
    inv=replace(res.primary,source_id='mangapill',chapter_records=rows,chapter_count=len(rows))
    res=replace(res,primary=inv,inventories=(inv,))
    base=[r for r in bundle['wikipedia']['chapters'] if r['number'] in keys]
    base.extend(dict(number=k,kind='chapter',volume='1',source='wikipedia',confidence='explicit',source_page='List of Serialized fixture chapters',source_record_id='main:'+k) for k in keys if k.isdigit() and int(k)>30)
    base.extend(dict(number=r['key'],kind=r['kind'],volume=r.get('volume',''),title='',
        source='wikipedia',confidence='explicit',source_page='List of Serialized fixture chapters',
        source_record_id='special:'+r['key']) for r in refs)
    bundle['wikipedia']['chapters']=base
    bundle['wikipedia']['volumes']=bundle['wikipedia']['volumes'][:1]
    return resolved(res,bundle),inv


class CanonicalSpecials(unittest.TestCase):
    def test_integer_main_sequence(self):
        p,_=publication(['1','2','3','4'])
        self.assertEqual((4,0,4),(p['canonical_main_chapters'],p['recognized_specials'],p['logical_chapters']))

    def test_bonus_counts_order_and_membership(self):
        p,inv=publication(['1','2','2.5','3'],[dict(key='2.5',kind='bonus',volume='1')])
        self.assertEqual((3,1,4),(p['canonical_main_chapters'],p['recognized_specials'],p['logical_chapters']))
        row=next(r for r in p['projection'] if r['chapter']=='2.5')
        self.assertEqual(('bonus','1'),(row['type'],row['_effective_volume']))
        self.assertNotIn('UNMAPPED_CHAPTERS',[h['code'] for h in publication_holes(p,inv)])

    def test_unknown_special_volume_is_not_guessed_or_main_publication_hole(self):
        p,inv=publication(['1','2','2.5','3'],[dict(key='2.5',kind='bonus')])
        row=next(r for r in p['projection'] if r['chapter']=='2.5')
        self.assertNotIn('_effective_volume',row)
        self.assertEqual(0,p['unmapped_chapters']);self.assertEqual(1,p['unassigned_specials'])
        self.assertEqual('PASS',health(p,[dict(problem_type=h['code']) for h in publication_holes(p,inv)])['publication'])

    def test_unsupported_fraction_stays_artifact(self):
        p,_=publication(['1','2','2.5','3'])
        self.assertEqual((3,0,1),(p['canonical_main_chapters'],p['recognized_specials'],p['classified_provider_artifacts']))

    def test_missing_bonus_acquisition_is_acquisition_only(self):
        p,inv=publication(['1','2','3'],[dict(key='2.5',kind='bonus',volume='1')])
        holes=publication_holes(p,inv)
        self.assertEqual(['2.5'],p['missing_special_acquisition'])
        self.assertIn('MISSING_SPECIAL_ACQUISITION',[h['code'] for h in holes])
        self.assertEqual('PASS',health(p,[dict(problem_type=h['code']) for h in holes])['publication'])

    def test_nonfractional_named_bonus_remains_supported(self):
        from ddk_chapter_normalization import normalize_acquisition,effective_counts
        from mangaanka_search_core.publication_manifest import PublicationManifestBuilder,build_publication_projection
        rows=[dict(chapter='Bonus',id='actual-bonus',type='bonus',title='Extra pages')]
        manifest=PublicationManifestBuilder({'canonical_identity':'named'},'original').apply_provider_inventory(rows,'mangapill').build()
        normalization=normalize_acquisition(rows,(),manifest,'mangapill')
        projection=build_publication_projection(rows,manifest,'mangapill','mangapill')
        counts=effective_counts(projection.rows,normalization)
        self.assertEqual((0,1,1,0,1),tuple(counts[k] for k in ('canonical_main_chapters','recognized_specials','logical_chapters','unmapped_chapters','unassigned_specials')))

    def test_246_main_plus_four_proven_bonuses_not_250_main(self):
        keys=[str(n) for n in range(1,247)]+['5.5','14.5','23.5','32.5']
        p,_=publication(keys,[dict(key=k,kind='extra',volume='1') for k in keys[-4:]])
        self.assertEqual((246,4,250),tuple(p[k] for k in ('canonical_main_chapters','recognized_specials','logical_chapters')))

    def test_exact_source_record_alias_propagates_through_ddk(self):
        res,bundle=fixture(extras=False)
        from mangaanka_search_core.reference_integration import canonical_family_publication_context
        from dataclasses import asdict
        work=canonical_family_publication_context(res.primary.result,[res.primary.result],'original').canonical_work_id
        proof=dict(key='2.5',kind='bonus',volume='1',source='mangadex_structure',confidence='explicit',
            source_page='https://mangadex.org/chapter/fixture',source_record_id='fixture',
            aliases=[dict(source='mangapill',record_id='actual-reader',identifier='2.1')])
        bundle['mangadex_structure']=dict(status='valid',cache_contract='mangadex-structure-v1',canonical_work_id=work,
            edition_profile='standard',manga_id='11111111-1111-1111-1111-111111111111',
            mappings={'2.5':'1'},special_metadata_contract='mangadex-specials-v1',special_records=[proof])
        rows=tuple([dict(id='actual-reader',chapter='2.1')]+list(res.primary.chapter_records))
        inv=replace(res.primary,source_id='mangapill',chapter_records=rows,chapter_count=len(rows))
        res=replace(res,primary=inv,inventories=(inv,))
        p=resolved(res,bundle)
        self.assertEqual((30,1,31),tuple(p[k] for k in ('canonical_main_chapters','recognized_specials','logical_chapters')))
        self.assertEqual(('2.5','2.1','actual-reader'),tuple(p['projection'][0][k] for k in ('chapter','_acquisition_chapter','id')))
        self.assertEqual([],p['missing_special_acquisition'])


def captured_dandadan(provider='mangapill'):
    """Public metadata, separate from any serialized live Audit 20 snapshot."""
    from pathlib import Path
    from copy import deepcopy
    from dataclasses import asdict
    import json
    from mangaanka_search_core.mangadex_structure_reference import MangaDexStructureResolver
    from mangaanka_search_core.wikipedia_reference import WikipediaPublicationAdapter
    from mangaanka_search_core.inventory_comparison import SourceInventory
    from mangaanka_search_core.search_resolution import SearchResolution
    from mangaanka_search_core.atsu_source import AtsuSource
    from test_publication_states import Service
    from ddk_publication import resolve_publication
    root=Path(__file__).parent/'fixtures'
    old=json.loads((root/'dandadan_audit18_review.json').read_text(encoding='utf-8'))['publication']
    bundle=deepcopy(old['references'])
    text=json.loads((root/'publication_freshness_evidence/wikipedia_audit18_revision.json').read_text(encoding='utf-8'))['parse']['wikitext']['*']
    wiki=WikipediaPublicationAdapter();wiki._wikitext=lambda _:text
    bundle['wikipedia']['volumes']=[asdict(v) for v,_ in wiki._parse_graphic_lists('List of Dandadan chapters','Dandadan')]
    fixture=root/'canonical_specials'
    aggregate=json.loads((fixture/'mangadex-aggregate.json').read_text())
    metadata=json.loads((fixture/'mangadex-fractional-0.json').read_text())
    evidence=dict(canonical_work_id=old['catalog_identity']['canonical_work_id'],identity_confidence='high',
        edition_profile='standard',mangadex_title_ids=['68112dc1-2b80-4f20-beb8-2f2a8716a430'],media_type='manga')
    bundle['mangadex_structure']=MangaDexStructureResolver(request_json=lambda url:aggregate if url.endswith('/aggregate') else metadata).lookup(evidence)
    rows=json.loads((fixture/'mangapill-chapters.json').read_text())
    if provider=='atsu':
        feed=json.loads((root/'publication_freshness_evidence/atsu_dandadan_allchapters.json').read_text())
        page=json.loads((root/'atsu_group_page.json').read_text())
        source=AtsuSource();source._api=lambda path,**kw:deepcopy(page if path.endswith('/page') else feed)
        rows=source.get_chapters('https://atsu.moe/manga/m7bps','en')
    selected=dict(source_id=provider,id='5460' if provider=='mangapill' else 'm7bps',title='Dandadan',canonical_title='Dandadan',
        canonical_work_id=evidence['canonical_work_id'],canonical_creators=['Yukinobu Tatsu'],author='Yukinobu Tatsu',
        _canonical_identity_confidence='high',media_type='manga')
    inv=SourceInventory(provider,provider,selected,'en','original',chapter_count=len(rows),usable=True,complete=True,chapter_records=tuple(rows))
    res=SearchResolution((selected,),(inv,),primary=inv,language='en')
    return resolve_publication(res,[selected],service=Service(bundle),as_of='2026-10-04'),inv


class CapturedDandadanSpecials(unittest.TestCase):
    def test_captured_mangapill_taxonomy_and_completed_structure(self):
        from mangaanka_search_core.chapter_workflow import chapter_sort_key
        p,inv=captured_dandadan()
        self.assertEqual((250,246,2,2,248,219,221,27,0,25),tuple(p[k] for k in ('raw_acquisition_records',
            'canonical_main_chapters','recognized_specials','classified_provider_artifacts','logical_chapters',
            'mapped_main_chapters','mapped_chapters','uncompiled_chapters','unmapped_chapters','final_volumes')))
        acquired={r['chapter']:r for r in p['projection']}
        for key,volume in (('32.5','4'),('40.5','5')):
            self.assertEqual(('special',volume,'mangadex_structure'),tuple(acquired[key][k] for k in ('type','_effective_volume','_type_source')))
            self.assertIn('Extras',acquired[key]['title'])
        labels=p['normalization']['labels']
        for key in ('26.5','193.1'):
            i=next(i for i,r in enumerate(p['projection']) if r['chapter']==key)
            self.assertEqual('provider_fractional_candidate',labels[i])
            self.assertNotIn('_type_source',p['projection'][i])
        self.assertEqual({'5.5','14.5','23.5','49.5','58.5','67.5','76.5','85.5','201.5'},set(p['missing_special_acquisition']))
        holes=publication_holes(p,inv)
        self.assertEqual({'PROVIDER_FRACTIONAL_CANDIDATE','MISSING_SPECIAL_ACQUISITION'},{h['code'] for h in holes})
        self.assertEqual(dict(identity='PASS',publication='PASS',normalization='REVIEW',acquisition='PARTIAL'),health(p,[dict(problem_type=h['code']) for h in holes]))
        order=[r['chapter'] for r in sorted(p['projection'],key=chapter_sort_key)]
        self.assertLess(order.index('32'),order.index('32.5'));self.assertLess(order.index('32.5'),order.index('33'))
        self.assertEqual(dict(source_id='mangapill',main=246,specials=2,unresolved=2,raw=250),p['provider_coverage'][0])

    def test_typed_metadata_preserves_atsu_primary_and_alternatives(self):
        p,inv=captured_dandadan('atsu')
        self.assertEqual((246,2,248,219,221,27,0,25),tuple(p[k] for k in ('canonical_main_chapters','recognized_specials','logical_chapters',
            'mapped_main_chapters','mapped_chapters','uncompiled_chapters','unmapped_chapters','final_volumes')))
        groups=p['provider_group_acquisition']
        self.assertEqual((481,233),(groups['raw_count'],len(groups['alternatives'])))
        self.assertFalse(any(r['requires_review'] for r in groups['alternatives']))
        holes=publication_holes(p,inv)
        self.assertEqual(['MISSING_SPECIAL_ACQUISITION'],[h['code'] for h in holes])
        self.assertEqual(dict(identity='PASS',publication='PASS',normalization='PASS',acquisition='PARTIAL'),health(p,[dict(problem_type=h['code']) for h in holes]))


if __name__=='__main__':unittest.main()
