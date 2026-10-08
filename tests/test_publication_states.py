"""Evidence-driven uncompiled/special regressions using the real projection."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ddk_publication import resolve_publication, publication_holes
from ddk_publication_states import derive_publication_states, verified_uncompiled_identifiers
from ddk_review import health, problem_policy, review_packet
from ddk_exports import catalog_context
from mangaanka_database_development_kit import DB
from mangaanka_search_core.inventory_comparison import SourceInventory
from mangaanka_search_core.search_resolution import SearchResolution
from mangaanka_search_core.reference_integration import WIKIPEDIA_CACHE_CONTRACT


def fixture(dandadan=False, extras=True):
    compiled = [str(n) for n in (range(0,220) if dandadan else range(1,21))]
    if dandadan: compiled.append('219.5')  # Explicit main record; count-shaped fixture, not live numbering.
    tail = [str(n) for n in (range(220,247) if dandadan else range(21,31))]
    volume_count = 25 if dandadan else 2
    title = 'Dandadan-style offline fixture' if dandadan else 'Serialized fixture'
    selected = dict(source_id='atsu', id='offline', title=title, canonical_title=title,
        canonical_work_id='fixture:serialized', canonical_creators=['Fixture Author'],
        author='Fixture Author', _canonical_identity_confidence='high', media_type='manga')
    def reference(key, kind, volume=''):
        return dict(number=key, title='Chapter '+key, volume=volume, kind=kind, source='wikipedia',
            source_page='List of Serialized fixture chapters', confidence='explicit',
            source_page_id='10', source_revision_id='20', source_record_id='row:'+key)
    mappings = {k: str(min(volume_count, 1 + i*volume_count//len(compiled))) for i,k in enumerate(compiled)}
    refs = [reference(k,'chapter',v) for k,v in mappings.items()]+[reference(k,'uncollected') for k in tail]
    rows = [dict(id=k,chapter=k,title='Chapter '+k) for k in compiled+tail]
    if extras:
        rows += [dict(id=k,chapter=k,title='Provider '+k) for k in ('19.5','89.1','92.5')]
        refs += [reference('89.1','special',str(volume_count)), reference('14.5','special','2'),
                 reference('92.1','special',str(volume_count))]
    wiki = dict(cache_contract=WIKIPEDIA_CACHE_CONTRACT,status='valid_complete',cache_state='refreshed',
        match=dict(source='wikipedia',confidence='confident',edition='original',title=title,publication_id='offline'),
        chapters=refs,volumes=[dict(number=str(n),confidence='explicit',release_status='released') for n in range(1,volume_count+1)])
    bundle = dict(wikipedia=wiki,mangadex_structure=dict(status='unavailable',mappings={}))
    inv = SourceInventory('atsu','Atsu',selected,'en','original',chapter_count=len(rows),usable=True,
        complete=True,chapter_records=tuple(rows))
    res = SearchResolution((selected,),(inv,),primary=inv,language='en')
    return res,bundle


class Service:
    def __init__(self,bundle): self.bundle=bundle
    def lookup(self,*args,**kwargs): return deepcopy(self.bundle)


def resolved(res=None,bundle=None,**kwargs):
    if res is None: res,bundle=fixture()
    return resolve_publication(res,[res.primary.result],service=Service(bundle),**kwargs)


def stored(db,pub,primary):
    db.add_titles(['Serialized fixture'],'standard','en');wid=db.works()[0]['id']
    holes=publication_holes(pub,primary)
    audit=db.save_audit(wid,dict(query='Serialized fixture',match_title='Serialized fixture',
        publication=pub,selected_source='atsu',workflow='volume'),holes)
    return wid,audit


class PublicationStates(unittest.TestCase):
    def setUp(self):
        self.net=patch('urllib.request.urlopen',side_effect=AssertionError('Unexpected network'));self.net.start()
        self.addCleanup(self.net.stop)

    def test_trailing_explicit_uncollected_is_safe_not_mapped(self):
        res,bundle=fixture(extras=False);p=resolved(res,bundle)
        self.assertEqual((30,20,10,0,2),tuple(p[k] for k in
            ('canonical_main_chapters','mapped_chapters','uncompiled_chapters','unmapped_chapters','final_volumes')))
        self.assertEqual([str(n) for n in range(21,31)],p['uncompiled_identifiers'])
        self.assertEqual([],publication_holes(p,res.primary))
        self.assertEqual('PASS',health(p,[])['publication'])
        self.assertTrue(all(r.get('_effective_volume') in (None,'') for r in p['projection'][20:]))

    def test_internal_hole_remains_review(self):
        res,bundle=fixture(extras=False)
        next(r for r in bundle['wikipedia']['chapters'] if r['number']=='11')['volume']=''
        p=resolved(res,bundle)
        self.assertEqual(0,p['uncompiled_chapters']);self.assertIn('11',p['unmapped_identifiers'])
        self.assertIn('UNMAPPED_CHAPTERS',[h['code'] for h in publication_holes(p,res.primary)])

    def test_trailing_without_explicit_release_boundary_stays_unmapped(self):
        res,bundle=fixture(extras=False);bundle['wikipedia']['volumes']=[]
        p=resolved(res,bundle);self.assertEqual((0,10),(p['uncompiled_chapters'],p['unmapped_chapters']))

    def test_trailing_without_explicit_uncollected_is_not_enough(self):
        res,bundle=fixture(extras=False)
        for r in bundle['wikipedia']['chapters']:
            if r['kind']=='uncollected':r['kind']='chapter'
        self.assertEqual(0,resolved(res,bundle)['uncompiled_chapters'])

    def test_trusted_mapping_claim_prevents_uncompiled(self):
        p=resolved(*fixture(extras=False))
        p['references']['mangadex_structure']['mappings']={'22':'2'}
        derive_publication_states(p);self.assertEqual([],p['uncompiled_identifiers'])

    def test_partial_stale_conflicting_wrong_edition_language_and_identity_fail_closed(self):
        for field,value in [('status','valid_partial'),('cache_state','last_known_good'),
                ('collection',{'failed_segments':1}),('collection',{'conflicts':['22']})]:
            with self.subTest(field=field,value=value):
                res,bundle=fixture(extras=False);bundle['wikipedia'][field]=value
                self.assertEqual(0,resolved(res,bundle)['uncompiled_chapters'])
        res,bundle=fixture(extras=False);bundle['wikipedia']['match']['edition']='fan_color'
        self.assertEqual(0,resolved(res,bundle)['uncompiled_chapters'])
        res,bundle=fixture(extras=False);bundle['wikipedia']['match']['title']='Unrelated fixture'
        self.assertEqual(0,resolved(res,bundle)['uncompiled_chapters'])
        res,bundle=fixture(extras=False)
        for r in bundle['wikipedia']['chapters']:r['language']='ja'
        self.assertEqual(0,resolved(res,bundle)['uncompiled_chapters'])
        res,bundle=fixture(extras=False);res.primary.result['_canonical_identity_confidence']='ambiguous'
        self.assertEqual(0,resolved(res,bundle)['uncompiled_chapters'])

    def test_additional_released_volume_or_reported_count_blocks_inference(self):
        for kind in ('volume','reported'):
            res,bundle=fixture(extras=False)
            if kind=='volume':bundle['wikipedia']['volumes'].append(dict(number='3',confidence='explicit',release_status='released'))
            else:res.primary.result['volume_context']=[dict(reported_total_volumes=3)]
            self.assertEqual(0,resolved(res,bundle)['uncompiled_chapters'])

    def test_exact_supported_special_and_unsupported_decimal(self):
        res,bundle=fixture();p=resolved(res,bundle)
        labels={r['chapter']:l for r,l in zip(p['projection'],p['normalization']['labels'])}
        self.assertEqual('recognized_special',labels['89.1'])
        self.assertEqual('provider_fractional_candidate',labels['92.5'])
        self.assertEqual('provider_fractional_candidate',labels['19.5'])
        group=next(h for h in publication_holes(p,res.primary) if h['code']=='PROVIDER_FRACTIONAL_CANDIDATE')
        self.assertEqual({'19.5','92.5'},set(group['details']['chapters']))
        self.assertEqual(30,p['canonical_main_chapters']);self.assertEqual(1,p['recognized_specials'])
        self.assertEqual('special',next(r for r in p['projection'] if r['chapter']=='89.1')['type'])

    def test_provider_special_type_alone_cannot_trust_fraction(self):
        res,bundle=fixture();rows=[dict(r,type='special') if r['chapter']=='92.5' else r for r in res.primary.chapter_records]
        inv=replace(res.primary,chapter_records=tuple(rows));res=replace(res,primary=inv,inventories=(inv,))
        p=resolved(res,bundle);self.assertEqual('provider_fractional_candidate',p['normalization']['labels'][-1])

    def test_missing_special_is_acquisition_only_and_publication_safe(self):
        res,bundle=fixture();p=resolved(res,bundle);holes=publication_holes(p,res.primary)
        missing=next(h for h in holes if h['code']=='MISSING_SPECIAL_ACQUISITION')
        self.assertEqual({'14.5','92.1'},set(missing['details']['chapters']))
        self.assertNotIn('CHAPTER_COUNT_DISAGREEMENT',[h['code'] for h in holes])
        self.assertEqual(('ACQUISITION','ACQUISITION_ONLY'),problem_policy(missing['code'])[:2])
        issues=[dict(problem_type=h['code']) for h in holes]
        self.assertEqual('PASS',health(p,issues)['publication']);self.assertEqual('PARTIAL',health(p,issues)['acquisition'])

    def test_dandadan_shape_keeps_all_three_decimals_evidence_driven(self):
        res,bundle=fixture(dandadan=True);p=resolved(res,bundle)
        self.assertEqual((248,222,27,0,25),tuple(p[k] for k in
            ('canonical_main_chapters','mapped_chapters','uncompiled_chapters','unmapped_chapters','final_volumes')))
        self.assertEqual([str(n) for n in range(220,247)],p['uncompiled_identifiers'])
        self.assertEqual(221,len([r for r,l in zip(p['projection'],p['normalization']['labels'])
                                  if l=='main' and r.get('_effective_volume') not in (None,'')]))
        self.assertEqual(1,p['recognized_specials']);self.assertEqual(2,p['classified_provider_artifacts'])

    def test_acceptance_uses_safe_states_and_human_approval_stays_explicit(self):
        res,bundle=fixture(extras=False);p=resolved(res,bundle)
        with tempfile.TemporaryDirectory() as folder:
            db=DB(Path(folder)/'test.db',role='TEST');wid,audit=stored(db,p,res.primary)
            uid=db.working_sets.create('Offline');db.working_sets.add_requests(uid,['Serialized fixture'])
            item=db.working_sets.items(uid)[0]['working_set_item_uuid'];db.working_sets.pin(item,wid,audit)
            self.assertEqual('READY',db.working_sets.item(item)['processing_status'])
            self.assertTrue(db.acceptance.evaluate(wid,item)['eligible'])
            self.assertEqual('NONE',db.acceptance.state(wid));self.assertEqual('STAGED',db.work(wid)['lifecycle_status'])
            self.assertEqual([],db.catalog.validate(wid)['unmapped'])

    def test_fake_uncompiled_counts_cannot_bypass_acceptance(self):
        res,bundle=fixture(extras=False);bundle['wikipedia']['volumes']=[];p=resolved(res,bundle)
        p['uncompiled_chapters']=10;p['unmapped_chapters']=0;p['unmapped']=[]
        for r in p['projection'][20:]:r['_publication_state']='UNCOMPILED'
        self.assertEqual([],verified_uncompiled_identifiers(p))
        with tempfile.TemporaryDirectory() as folder:
            db=DB(Path(folder)/'test.db',role='TEST');wid,_=stored(db,p,res.primary)
            self.assertFalse(db.acceptance.evaluate(wid)['eligible'])

    def test_curated_override_preserves_automatic_evidence(self):
        res,bundle=fixture(extras=False);p=resolved(res,bundle)
        with tempfile.TemporaryDirectory() as folder:
            db=DB(Path(folder)/'test.db',role='TEST');wid,_=stored(db,p,res.primary)
            db.catalog.apply(db.catalog.preview(wid,[dict(entity='chapter',key='21',field='volume',value='2',verification='VERIFIED')]))
            current=resolved(res,bundle,catalog=db.catalog,catalog_work_id=wid)
            self.assertEqual((21,9,0),(current['mapped_chapters'],current['uncompiled_chapters'],current['unmapped_chapters']))
            self.assertIn('21',current['automatic']['uncompiled_identifiers'])
            self.assertNotIn('21',current['uncompiled_identifiers'])
            self.assertEqual('curated_database',current['projection'][20]['_volume_source'])

    def test_packets_and_context_expose_breakdown(self):
        res,bundle=fixture();p=resolved(res,bundle)
        with tempfile.TemporaryDirectory() as folder:
            db=DB(Path(folder)/'test.db',role='TEST');wid,_=stored(db,p,res.primary)
            context=catalog_context(db,wid);packet=review_packet(db,work_ids=[wid])['works'][0]
            self.assertEqual(10,context['uncompiled']);self.assertEqual(10,len(packet['mapping']['uncompiled_identifiers']))
            self.assertTrue(packet['mapping']['recognized_specials']);self.assertTrue(packet['mapping']['missing_acquisition_specials'])
            self.assertFalse(any(i['problem_type']=='UNMAPPED_CHAPTERS' for i in packet['issues']))

    def test_actual_wikipedia_volume_contract_uses_collection_validation(self):
        res,bundle=fixture(extras=False)
        for v in bundle['wikipedia']['volumes']:v.update(source='wikipedia',confidence='unknown')
        self.assertEqual(10,resolved(res,bundle)['uncompiled_chapters'])

    def test_reference_missing_main_still_blocks_release_completeness(self):
        res,bundle=fixture(extras=False)
        rows=tuple(r for r in res.primary.chapter_records if r['chapter']!='11')
        inv=replace(res.primary,chapter_records=rows);res=replace(res,primary=inv,inventories=(inv,))
        self.assertEqual(0,resolved(res,bundle)['uncompiled_chapters'])

    def test_native_fraction_without_independent_evidence_is_candidate(self):
        res,bundle=fixture()
        rows=tuple(dict(r,volume='2') if r['chapter']=='92.5' else r for r in res.primary.chapter_records)
        inv=replace(res.primary,chapter_records=rows);res=replace(res,primary=inv,inventories=(inv,))
        self.assertEqual('provider_fractional_candidate',resolved(res,bundle)['normalization']['labels'][-1])

    def test_missing_special_without_other_blockers_allows_ready(self):
        res,bundle=fixture()
        rows=tuple(r for r in res.primary.chapter_records if r['chapter'] not in ('19.5','92.5'))
        inv=replace(res.primary,chapter_records=rows);res=replace(res,primary=inv,inventories=(inv,))
        p=resolved(res,bundle)
        with tempfile.TemporaryDirectory() as folder:
            db=DB(Path(folder)/'test.db',role='TEST');wid,_=stored(db,p,res.primary)
            self.assertTrue(db.acceptance.evaluate(wid)['eligible'])
            self.assertEqual('NONE',db.acceptance.state(wid))

    def test_unsupported_fraction_still_blocks_acceptance(self):
        res,bundle=fixture();p=resolved(res,bundle)
        with tempfile.TemporaryDirectory() as folder:
            db=DB(Path(folder)/'test.db',role='TEST');wid,_=stored(db,p,res.primary)
            self.assertFalse(db.acceptance.evaluate(wid)['eligible'])

    def test_clean_serialized_packet_includes_informational_identifiers(self):
        res,bundle=fixture(extras=False);p=resolved(res,bundle)
        with tempfile.TemporaryDirectory() as folder:
            db=DB(Path(folder)/'test.db',role='TEST');wid,_=stored(db,p,res.primary)
            entry=review_packet(db,work_ids=[wid])['works'][0]
            self.assertEqual([],entry['issues']);self.assertEqual(10,len(entry['mapping']['uncompiled_identifiers']))

    def test_nonmonotonic_or_gapped_released_sequence_cannot_establish_tail(self):
        res,bundle=fixture(extras=False)
        next(r for r in bundle['wikipedia']['chapters'] if r['number']=='1')['volume']='2'
        self.assertEqual(0,resolved(res,bundle)['uncompiled_chapters'])
        res,bundle=fixture(extras=False)
        for r in bundle['wikipedia']['chapters']:
            if r['volume']=='2':r['volume']='3'
        bundle['wikipedia']['volumes'][1]['number']='3'
        self.assertEqual(0,resolved(res,bundle)['uncompiled_chapters'])

    def test_explicit_mapping_lost_by_projection_remains_a_real_hole(self):
        from mangaanka_search_core.publication_manifest import build_publication_projection,FieldEvidence
        res,bundle=fixture(extras=False)
        r=next(r for r in bundle['wikipedia']['chapters'] if r['number']=='22')
        r.update(kind='chapter',volume='2')
        def failed_projection(*args,**kwargs):
            p=build_publication_projection(*args,**kwargs)
            return replace(p,chapters=tuple(replace(c,effective_volume=FieldEvidence())
                if c.canonical_key=='22' else c for c in p.chapters))
        with patch('ddk_publication.build_publication_projection',side_effect=failed_projection):
            p=resolved(res,bundle)
        self.assertEqual(0,p['uncompiled_chapters']);self.assertIn('22',p['unmapped_identifiers'])
        self.assertIn('UNMAPPED_CHAPTERS',[h['code'] for h in publication_holes(p,res.primary)])
