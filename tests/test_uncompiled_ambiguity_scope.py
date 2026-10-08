"""Bounded tail proof through the real manifest, reconciliation and projection."""
from copy import deepcopy
from dataclasses import replace
import unittest
from unittest.mock import patch

from test_publication_states import fixture, resolved
from ddk_publication_states import derive_publication_states, verified_uncompiled_identifiers
from mangaanka_search_core.mangadex_structure_reference import aggregate_mappings


def scoped_fixture(key=None, volumes=('1', '2')):
    res, bundle = fixture(extras=False)
    for row in bundle['wikipedia']['chapters']:
        if row['kind'] == 'chapter':
            row['volume'] = str(1 + (int(row['number']) - 1) // 5)
    bundle['wikipedia']['volumes'] = [dict(number=str(n), release_status='released')
                                     for n in range(1, 5)]
    payload = dict(result='ok', volumes=[dict(volume=v, chapters=[dict(chapter=key)])
                                        for v in volumes] if key else [])
    mappings, ambiguous, diagnostics = aggregate_mappings(payload, with_diagnostics=True)
    bundle['mangadex_structure'] = dict(status='valid', cache_contract='mangadex-structure-v1',
        canonical_work_id='fixture:serialized', edition_profile='standard', cache_state='refreshed',
        integrity_contract='mangadex-aggregate-integrity-v1', mappings=mappings,
        ambiguous_chapters=ambiguous, integrity_diagnostics=diagnostics, volume_count=0)
    return res, bundle


class UncompiledAmbiguityScope(unittest.TestCase):
    def setUp(self):
        guard = patch('urllib.request.urlopen', side_effect=AssertionError('Unexpected network'))
        guard.start(); self.addCleanup(guard.stop)

    def assert_tail(self, pub, count=10):
        self.assertEqual(count, pub['uncompiled_chapters'])
        self.assertEqual([str(n) for n in range(21, 31)] if count else [],
                         pub['uncompiled_identifiers'])
        self.assertEqual(20, pub['mapped_chapters'])
        self.assertEqual(4, pub['final_volumes'])

    def test_early_quarantined_volume_ambiguity_with_independent_wiki(self):
        res, bundle = scoped_fixture('3')
        pub = resolved(res, bundle)
        self.assert_tail(pub)
        self.assertEqual(['3'], pub['references']['mangadex_structure']['ambiguous_chapters'])
        self.assertNotIn('3', pub['manifest']['ambiguous_chapter_keys'])
        row = next(r for r in pub['projection'] if r['chapter'] == '3')
        self.assertEqual(('1', 'wikipedia'), (row['_effective_volume'], row['_volume_source']))
        self.assertEqual(['3'], pub['uncompiled_evidence']['ambiguity_scope']['independently_resolved'])
        self.assertEqual(pub['uncompiled_identifiers'], verified_uncompiled_identifiers(pub))

    def test_immediate_predecessor_blocks(self):
        self.assert_tail(resolved(*scoped_fixture('20', ('3', '4'))), 0)

    def test_inside_tail_blocks(self):
        self.assert_tail(resolved(*scoped_fixture('22')), 0)

    def test_final_released_volume_blocks(self):
        self.assert_tail(resolved(*scoped_fixture('17', ('3', '4'))), 0)

    def test_independently_recognized_special_namespace_is_separable(self):
        res, bundle = scoped_fixture('3.5', ('1', '4'))
        bundle['wikipedia']['chapters'].append(dict(bundle['wikipedia']['chapters'][0],
            number='3.5', kind='special', volume='1', source_record_id='special:3.5'))
        pub = resolved(res, bundle)
        self.assert_tail(pub)
        self.assertEqual(['3.5'], pub['missing_special_acquisition'])
        self.assertEqual(['3.5'], pub['uncompiled_evidence']['ambiguity_scope']['independently_resolved'])

    def test_other_work_or_edition_is_excluded_by_manifest(self):
        for field, value in (('canonical_work_id', 'unrelated:work'), ('edition_profile', 'omnibus')):
            with self.subTest(field=field):
                res, bundle = scoped_fixture('22')
                bundle['mangadex_structure'][field] = value
                bundle['mangadex_structure'].update(mappings={'23': '9'}, volume_count=9)
                pub = resolved(res, bundle)
                self.assert_tail(pub)
                self.assertIn(dict(source='mangadex_structure', status='incompatible',
                    source_identity='', contract='', parser_version='', cache_state='', last_validated=None),
                    pub['manifest']['source_states'])

    def test_no_ambiguity_preserves_explicit_tail(self):
        self.assert_tail(resolved(*scoped_fixture()))

    def test_no_explicit_uncollected_evidence_blocks(self):
        res, bundle = scoped_fixture('3')
        for row in bundle['wikipedia']['chapters']:
            if row['kind'] == 'uncollected': row['kind'] = 'chapter'
        self.assert_tail(resolved(res, bundle), 0)

    def test_future_listed_volume_is_never_assigned(self):
        res, bundle = scoped_fixture('3')
        bundle['wikipedia']['volumes'].append(dict(number='5', release_date='2099-01-01'))
        pub = resolved(res, bundle, as_of='2026-10-06')
        self.assert_tail(pub)
        self.assertEqual(['5'], pub['release_boundary']['future_volumes'])
        self.assertTrue(all(not r.get('_effective_volume') for r in pub['projection'][20:]))

    def test_gapped_tail_blocks(self):
        res, bundle = scoped_fixture('3')
        inv = replace(res.primary, chapter_records=tuple(r for r in res.primary.chapter_records
                                                       if r['chapter'] != '25'))
        pub = resolved(replace(res, primary=inv, inventories=(inv,)), bundle)
        self.assert_tail(pub, 0)

    def test_explicit_tail_mapping_claim_blocks(self):
        res, bundle = scoped_fixture('3')
        bundle['mangadex_structure']['mappings']['22'] = '4'
        pub = resolved(res, bundle)
        self.assertEqual(0, pub['uncompiled_chapters'])
        self.assertEqual(21, pub['mapped_chapters'])

    def test_complete_wikipedia_boundary_is_required_despite_early_quarantine(self):
        res, bundle = scoped_fixture('3')
        bundle['wikipedia']['chapters'] = [r for r in bundle['wikipedia']['chapters']
                                          if r['number'] != '3']
        self.assertEqual(0, resolved(res, bundle)['uncompiled_chapters'])

    def test_early_ambiguity_claim_reaching_final_or_future_volume_blocks(self):
        for volume in ('4', '5'):
            with self.subTest(volume=volume):
                self.assert_tail(resolved(*scoped_fixture('3', ('1', volume))), 0)

    def test_release_identity_conflict_cannot_be_scoped_as_volume_only(self):
        res, bundle = scoped_fixture('3')
        bundle['mangadex_structure']['integrity_diagnostics'].append(dict(
            reason='conflicting_release_identifier', chapters=['3', '22'], records=[]))
        self.assert_tail(resolved(res, bundle), 0)

    def test_absent_or_unknown_diagnostics_fail_closed(self):
        for diagnostics in ([], [dict(reason='unknown', chapter='3')]):
            res, bundle = scoped_fixture('3')
            bundle['mangadex_structure']['integrity_diagnostics'] = diagnostics
            self.assert_tail(resolved(res, bundle), 0)

    def test_stale_or_partial_wikipedia_cannot_resolve_early_ambiguity(self):
        for field, value in (('cache_state', 'last_known_good'), ('status', 'valid_partial')):
            res, bundle = scoped_fixture('3')
            bundle['wikipedia'][field] = value
            self.assertEqual(0, resolved(res, bundle)['uncompiled_chapters'])

    def test_unresolved_manifest_or_reference_conflicts_remain_global_blockers(self):
        clean = resolved(*scoped_fixture())
        for location, field in (('manifest', 'ambiguous_chapter_keys'), ('root', 'conflicting_chapters')):
            pub = deepcopy(clean)
            (pub['manifest'] if location == 'manifest' else pub)[field] = ['3']
            derive_publication_states(pub)
            self.assertEqual([], pub['uncompiled_identifiers'])

    def test_actual_cross_reference_disagreement_is_still_quarantined(self):
        res, bundle = scoped_fixture('3')
        bundle['mangadex_structure']['mappings']['7'] = '3'
        pub = resolved(res, bundle)
        self.assertEqual(['7'], pub['conflicting_chapters'])
        self.assertEqual(0, pub['uncompiled_chapters'])
        self.assertFalse(next(r for r in pub['projection'] if r['chapter'] == '7').get('_effective_volume'))


if __name__ == '__main__': unittest.main()
