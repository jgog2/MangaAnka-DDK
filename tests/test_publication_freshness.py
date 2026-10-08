"""Deterministic shared release, sparse curation and extension regressions."""
from copy import deepcopy
import unittest
import json
from dataclasses import asdict
from pathlib import Path

from mangaanka_search_core.publication_freshness import release_boundary, catalog_freshness
from tests.test_publication_states import fixture, resolved


class PublicationFreshness(unittest.TestCase):
    def test_actual_scoped_audit18_with_release_dates_recovers_the_tail(self):
        from mangaanka_search_core.wikipedia_reference import WikipediaPublicationAdapter
        from mangaanka_search_core.publication_freshness import derive_publication_states
        root=Path(__file__).parent/'fixtures'
        data=json.loads((root/'dandadan_audit18_review.json').read_text(encoding='utf-8'))
        self.assertEqual((10,18,'39491816-09a0-42e3-9100-07e3d048adf1'),
            (data['work_id'],data['audit_id'],data['work_uuid']))
        publication=data['publication'];publication['as_of']='2026-10-04'
        adapter=WikipediaPublicationAdapter()
        wikitext=json.loads((root/'publication_freshness_evidence/wikipedia_audit18_revision.json').read_text())['parse']['wikitext']['*']
        adapter._wikitext=lambda _:wikitext
        publication['references']['wikipedia']['volumes']=[asdict(v) for v,_ in
            adapter._parse_graphic_lists('List of Dandadan chapters','Dandadan')]
        derive_publication_states(publication)
        self.assertEqual([str(n) for n in range(220,247)],publication['uncompiled_identifiers'])
        self.assertEqual('25',publication['release_boundary']['latest_released_volume'])
        self.assertEqual(['26','27'],publication['release_boundary']['listed_unreleased_volumes'])

    def test_actual_atsu_feed_retains_fractional_records_and_group_counts(self):
        from collections import Counter
        from mangaanka_search_core.atsu_source import AtsuSource
        root=Path(__file__).parent/'fixtures/publication_freshness_evidence'
        data=json.loads((root/'atsu_dandadan_allchapters.json').read_text())
        self.assertEqual([233,248],sorted(Counter(r['scanlationMangaId'] for r in data['chapters']).values()))
        source=AtsuSource();source._api=lambda *a,**kw:deepcopy(data)
        rows=source.get_chapters('https://atsu.moe/manga/m7bps','en')
        self.assertEqual(481,len(rows))
        self.assertTrue({'19.5','89.1','92.5'}<={r['chapter'] for r in rows})
        self.assertTrue(all(r.get('volume') in (None,'') for r in rows))
    def test_future_volume_changes_only_at_release(self):
        _, bundle = fixture(extras=False)
        bundle['wikipedia']['volumes'].append(dict(number='3', release_date='2026-11-04'))
        before = release_boundary(bundle, as_of='2026-10-04')
        after = release_boundary(bundle, as_of='2026-11-05')
        self.assertEqual('2', before['latest_released_volume'])
        self.assertEqual(['3'], before['future_volumes'])
        self.assertEqual('3', after['latest_released_volume'])

    def test_listed_unknown_is_not_released(self):
        _, bundle = fixture(extras=False)
        bundle['wikipedia']['volumes'].append(dict(number='3'))
        result = release_boundary(bundle, as_of='2026-10-04')
        self.assertEqual(['3'], result['listed_unreleased_volumes'])
        self.assertEqual('2', result['latest_released_volume'])

    def test_explicit_complete_snapshot_extends_without_a_ceiling(self):
        patch = dict(status='matched', fields=[], coverage_contract=dict(
            kind='complete_publication_snapshot', complete=True,
            volumes=['1'], chapter_identifiers=['1']))
        live = dict(projection=[dict(chapter='1', _effective_volume='1', _volume_source='wikipedia'),
                                dict(chapter='2', _effective_volume='2', _volume_source='wikipedia')],
                    release_boundary=dict(released_volumes=['1','2']))
        result = catalog_freshness(patch, live)
        self.assertEqual('EXTENSION_AVAILABLE', result['state'])
        self.assertEqual(['2'], result['extension_volumes'])
        self.assertEqual(['2'], result['extension_chapters'])

    def test_sparse_correction_has_no_coverage_boundary(self):
        patch = dict(status='matched',fields=[dict(entity='chapter',record_key='275',
            field='volume',value='23',verification='VERIFIED')])
        live = dict(projection=[dict(chapter='275',_effective_volume='23',_volume_source='wikipedia'),
                                dict(chapter='276',_effective_volume='24',_volume_source='wikipedia')])
        result = catalog_freshness(patch,live)
        self.assertEqual('CURRENT',result['state'])
        self.assertEqual('sparse',result['coverage_kind'])
        self.assertIsNone(result['curated_coverage'])
        self.assertEqual([],result['extension_chapters'])

    def test_curated_conflict_and_revision_only_change_are_distinct(self):
        patch = dict(status='matched',fields=[dict(entity='chapter',record_key='100',
            field='volume',value='12',verification='VERIFIED')],source_fingerprints={'wiki':'old'})
        live = dict(projection=[dict(chapter='100',_effective_volume='12',_volume_source='wikipedia')],
                    source_fingerprints={'wiki':'new'})
        self.assertEqual('SOURCE_CHANGED',catalog_freshness(patch,live)['state'])
        live['projection'][0]['_effective_volume']='13'
        self.assertEqual('CONFLICT_REVIEW',catalog_freshness(patch,live)['state'])

    def test_dandadan_shape_future_records_do_not_block_explicit_tail(self):
        res,bundle=fixture(dandadan=True,extras=False)
        bundle['wikipedia']['volumes'] += [dict(number='26',release_date='2026-11-04'),
                                         dict(number='27',release_status='listed')]
        publication=resolved(res,bundle,as_of='2026-10-04')
        self.assertEqual((221,27,0,25),tuple(publication[k] for k in
            ('mapped_main_chapters','uncompiled_chapters','unmapped_chapters','final_volumes')))

    def test_null_tail_and_internal_hole_stay_unresolved(self):
        for internal in (False,True):
            res,bundle=fixture(extras=False)
            if internal: bundle['wikipedia']['chapters'][10]['volume']=''
            else:
                for chapter in bundle['wikipedia']['chapters']:
                    if chapter['kind']=='uncollected':chapter['kind']='chapter'
            self.assertEqual(0,resolved(res,bundle)['uncompiled_chapters'])

    def test_uncompiled_becomes_mapped_in_a_new_audit(self):
        res,bundle=fixture(extras=False)
        first=resolved(res,bundle,as_of='2026-10-04')
        bundle['wikipedia']['volumes'].append(dict(number='3',release_date='2026-11-04'))
        for chapter in bundle['wikipedia']['chapters']:
            if chapter['number'] in ('21','22','23'):
                chapter.update(kind='chapter',volume='3')
        second=resolved(res,bundle,as_of='2026-11-05')
        self.assertEqual(10,first['uncompiled_chapters'])
        self.assertEqual((23,7,0),tuple(second[k] for k in
            ('mapped_main_chapters','uncompiled_chapters','unmapped_chapters')))

    def test_explicit_snapshot_counts_are_not_a_ceiling(self):
        from ddk_publication import publication_holes
        res,bundle=fixture(extras=False)
        class Catalog:
            def lookup(self,identity,work_id):
                return dict(status='matched',identity=identity,work_id=1,revision=1,
                    fields=[dict(entity='work',record_key='work',field='expected_chapters',
                        value=20,verification='VERIFIED')],coverage_contract=dict(
                        kind='complete_publication_snapshot',complete=True,volumes=['1','2'],
                        chapter_identifiers=[str(n) for n in range(1,21)]))
        publication=resolved(res,bundle,catalog=Catalog(),as_of='2026-10-04')
        self.assertEqual('EXTENSION_AVAILABLE',publication['catalog_freshness']['state'])
        self.assertEqual([],publication_holes(publication,res.primary))


if __name__=='__main__':unittest.main()
