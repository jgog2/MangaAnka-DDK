"""Offline safeguards for mixed-content MangaK numbering; never authorizes repairs.

Only identifiers/counts are captured. Peer records deliberately model the six
keys corroborated in Audit 40; they are not recovered provider inventories.
Reader-image observations stay in the investigation report, not runtime rules.
"""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from ddk_chapter_normalization import normalize_acquisition, effective_counts
from ddk_review import problem_policy
from mangaanka_search_core.inventory_comparison import SourceInventory
from mangaanka_search_core.mangak_source import MangaKSource
from mangaanka_search_core.publication_specials import inventory_coverage
from mangaanka_search_core.search_resolution import _choose_primary


FIXTURE = json.loads((Path(__file__).parent / 'fixtures' /
                     'haikyu_provider_residue.json').read_text(encoding='utf-8'))


def captured_pattern():
    rows = tuple(dict(id='reader:'+key, chapter=key, title='')
                 for key in FIXTURE['acquisition_keys'])
    selected = SourceInventory('mangak', 'MangaK', {}, 'en', 'original',
        chapter_count=len(rows), chapter_records=rows, usable=True, complete=True)
    peer_keys = FIXTURE['reference_keys'] + FIXTURE['peer_supported_fraction_keys']
    peer_rows = tuple(dict(id='peer:'+key, chapter=key, title='') for key in peer_keys)
    peers = tuple(replace(selected, source_id=source, chapter_records=peer_rows,
                          chapter_count=len(peer_rows)) for source in ('atsu', 'mangapill'))
    manifest = SimpleNamespace(chapters=(), runtime_publication=dict(
        publication_records=[dict(key=key, kind='chapter') for key in FIXTURE['reference_keys']]))
    return selected, peers, manifest


class MixedProviderNumbering(unittest.TestCase):
    def setUp(self):
        guard = patch('urllib.request.urlopen', side_effect=AssertionError('Unexpected network'))
        guard.start()
        self.addCleanup(guard.stop)

    def test_captured_pattern_retains_every_unresolved_record_and_two_code_categories(self):
        selected, peers, manifest = captured_pattern()
        before = deepcopy(selected.chapter_records)
        result = normalize_acquisition(selected.chapter_records, (selected,)+peers, manifest, 'mangak')
        self.assertEqual(FIXTURE['expected_counts'], result['counts'])
        self.assertEqual(FIXTURE['expected_artifact_identifiers'],
                         {g['classification']:g['identifiers'] for g in result['artifact_groups']})
        self.assertEqual(2, len(result['artifact_groups']))
        for group in result['artifact_groups']:
            code = group['classification'].upper()
            self.assertEqual(('CODE', 'CODE_REVIEW_REQUIRED'), problem_policy(code)[:2])
        self.assertEqual(before, selected.chapter_records)
        self.assertEqual(511, len(result['labels']))

    def test_parent_volume_projection_cannot_establish_fraction_identity(self):
        selected, peers, manifest = captured_pattern()
        result = normalize_acquisition(selected.chapter_records, peers, manifest, 'mangak')
        projection = [dict(row, _effective_volume=volume) for row, volume in
                      zip(selected.chapter_records, FIXTURE['projected_volumes'])]
        counts = effective_counts(projection, result)
        self.assertEqual((408, 408, 0, 45), tuple(counts[k] for k in
            ('logical_chapters', 'mapped_chapters', 'unmapped_chapters', 'final_volumes')))
        self.assertEqual(102, counts['classified_provider_artifacts'])
        self.assertEqual(1, counts['unclassified_records'])

    def test_unknown_fractions_do_not_buy_source_coverage(self):
        selected, peers, manifest = captured_pattern()
        self.assertEqual(dict(main=403, specials=0, unresolved=108, raw=511),
                         inventory_coverage(selected))
        self.assertEqual(dict(main=402, specials=0, unresolved=6, raw=408),
                         inventory_coverage(peers[0]))

    def test_current_primary_advantage_is_integer_zero_not_fraction_count(self):
        selected, peers, manifest = captured_pattern()
        self.assertIs(selected, _choose_primary((selected,)+peers, 'volume'))
        integer_rows = tuple(r for r in selected.chapter_records if r['chapter'].isdigit())
        integers_only = replace(selected, chapter_records=integer_rows, chapter_count=len(integer_rows))
        self.assertIs(integers_only, _choose_primary((integers_only,)+peers, 'volume'))
        no_zero = tuple(r for r in selected.chapter_records if r['chapter']!='0')
        without_zero = replace(selected, chapter_records=no_zero, chapter_count=len(no_zero))
        self.assertIs(peers[0], _choose_primary((without_zero,)+peers, 'volume'))

    def test_selected_source_and_one_peer_cannot_self_corroborate(self):
        selected, peers, manifest = captured_pattern()
        result = normalize_acquisition(selected.chapter_records, (selected, peers[0]), manifest, 'mangak')
        labels = dict(zip(FIXTURE['acquisition_keys'], result['labels']))
        for key in FIXTURE['peer_supported_fraction_keys']:
            self.assertIn(labels[key], ('provider_fractional_candidate', 'provider_split_candidate'))
        self.assertNotIn('recognized_special', result['labels'])

    def test_adapter_preserves_provider_labels_instead_of_internal_upload_indexes(self):
        source = MangaKSource()
        samples = FIXTURE['adapter_samples']
        with patch.object(source, '_title', return_value=({'id':'08AG9bBD'}, 'https://mangak.io/haikyu')), \
             patch.object(source, '_json', return_value={'data':{'chapters':samples}}):
            rows = source.get_chapters('https://mangak.io/haikyu', 'en')
        self.assertEqual({'0', '1.2', '2.1', '402.5'}, {r['chapter'] for r in rows})
        self.assertEqual({'https://mangak.io'+r['url'] for r in samples}, {r['id'] for r in rows})
        self.assertTrue(all(r['title']=='' and r['volume'] is None for r in rows))


if __name__ == '__main__':
    unittest.main()
