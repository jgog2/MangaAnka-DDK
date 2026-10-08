"""Characterize the selection evidence gap, without authorizing a new policy.

The expected outcomes document current behavior, including its limitation.
Independent publication facts are supplied only to post-selection normalization;
the production search resolver has no input for those facts today.
"""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from ddk_chapter_normalization import normalize_acquisition
from mangaanka_search_core.canonical_identity import group_canonical_results
from mangaanka_search_core.inventory_comparison import SourceInventory, compare_inventories
from mangaanka_search_core.publication_specials import inventory_coverage
from mangaanka_search_core.search_resolution import _choose_primary, resolve_search_group


FIXTURE = json.loads((Path(__file__).parent/'fixtures/provider_selection_boundary.json')
                     .read_text(encoding='utf-8'))


def inventory(source, keys, title='Synthetic work', edition='original', complete=True, typed_special=()):
    result = dict(source_id=source, source_name=source, id=source+':work',
        url='https://'+source+'.invalid/work', title=title, full_title=title,
        edition=edition, media_type='manga', available_languages=['en'], adult=False)
    rows = tuple(dict(id=source+':reader:'+str(i), chapter=key, title='', volume=None,
                      **({'type':'bonus'} if key in typed_special else {}))
                 for i,key in enumerate(keys))
    return SourceInventory(source, source, result, 'en', edition, chapter_records=rows,
        chapter_count=len(rows), usable=bool(rows), complete=complete)


def pair(case, title='Synthetic work'):
    base = FIXTURE['base_keys']
    return (inventory('zeta', base+case['extra'], title, case.get('edition','original'),
                      case.get('complete',True), case.get('typed_special',())),
            inventory('alpha', base, title))


def current_selection(rows, workflow='volume', specials=()):
    decision = compare_inventories(rows, 'original', workflow, specials)
    # Production callers supply a canonical group of one compatible edition.
    eligible = tuple(r for r in rows if r.edition=='original')
    return decision.selected or _choose_primary(eligible, workflow, specials)


def normalize_after_selection(selected, other, reference_extra=()):
    manifest = SimpleNamespace(chapters=(), runtime_publication=dict(publication_records=[
        dict(key=key, kind='chapter') for key in FIXTURE['base_keys']+list(reference_extra)]))
    # Two other independent providers make absence fail closed, matching the
    # existing normalizer's evidence threshold. No peer evidence is invented
    # in the ranking itself.
    third = replace(other, source_id='third')
    result = normalize_acquisition(selected.chapter_records, (selected,other,third), manifest, selected.source_id)
    return dict(zip((r['chapter'] for r in selected.chapter_records),result['labels']))


class ProviderSelectionBoundary(unittest.TestCase):
    def setUp(self):
        guard = patch('urllib.request.urlopen', side_effect=AssertionError('Unexpected network'))
        guard.start()
        self.addCleanup(guard.stop)

    def test_zero_and_canonical_zero_are_indistinguishable_to_ranking(self):
        cases = {c['name']:c for c in FIXTURE['cases']}
        unverified = pair(cases['provider_only_zero'])
        canonical = pair(cases['independently_canonical_zero'])
        self.assertEqual(unverified, canonical)
        self.assertEqual('zeta', current_selection(unverified).source_id)
        self.assertEqual('unclassified', normalize_after_selection(*unverified)['0'])
        self.assertEqual('main', normalize_after_selection(*canonical,reference_extra=['0'])['0'])

    def test_positive_integer_has_the_same_evidence_gap(self):
        a,b = pair(dict(extra=['999']))
        self.assertEqual('zeta', current_selection((a,b)).source_id)
        self.assertEqual('unclassified', normalize_after_selection(a,b)['999'])
        self.assertEqual('main', normalize_after_selection(a,b,['999'])['999'])

    def test_special_identity_hook_credits_specials_without_main_inflation(self):
        a,b = pair(dict(extra=['21'],typed_special=['21']))
        proof = [dict(key='21',kind='bonus')]
        self.assertEqual(dict(main=20,specials=1,unresolved=0,raw=21),inventory_coverage(a,proof))
        self.assertEqual('zeta', current_selection((a,b),specials=proof).source_id)
        # resolve_search_group does not currently obtain/pass reference specials.
        self.assertEqual('alpha', current_selection((a,b)).source_id)

    def test_no_peer_consensus_policy_can_certify_unique_legitimate_tail(self):
        a,b = pair(dict(extra=['21']))
        self.assertEqual('main', normalize_after_selection(a,b,['21'])['21'])
        self.assertNotIn('21', {r['chapter'] for r in b.chapter_records})
        self.assertEqual('zeta', current_selection((a,b)).source_id)

    def test_edition_mismatch_is_separated_at_canonical_group_boundary(self):
        a,b = pair(dict(extra=['21'],edition='official_color'))
        groups = group_canonical_results((a.result,b.result))
        self.assertEqual(2,len(groups))
        self.assertIs(b,compare_inventories((a,b),'original','volume').selected)

    def test_native_provider_membership_preference_is_preserved(self):
        a,b = pair(dict(extra=[]))
        a = replace(a, chapter_records=tuple(dict(r,volume='1') for r in a.chapter_records),
                    native_volumes=1,volume_ids=('1',))
        self.assertIs(a,current_selection((a,b)))

    def test_equal_counts_are_deterministic_under_input_permutation(self):
        a,b = pair(dict(extra=[]))
        self.assertIs(b,current_selection((a,b)))
        self.assertIs(b,current_selection((b,a)))

    def test_counterfactual_tie_break_discards_verified_small_completeness_advantage(self):
        a,b = pair(dict(extra=['21']))
        self.assertTrue(compare_inventories((a,b),'original','volume').ambiguous)
        self.assertEqual('main',normalize_after_selection(a,b,['21'])['21'])
        # Ignoring all marginal coverage would fix neither chapter identity nor
        # this genuine advantage; it would select alpha in both scenarios.
        self.assertIs(b,sorted((a,b),key=lambda row:row.source_id)[0])
        self.assertIs(a,current_selection((a,b)))

    def test_actual_resolver_uses_inventory_before_any_reference_evidence(self):
        a,b = pair(dict(extra=['0']))
        calls = []
        def source(inv):
            def chapters(*args,**kwargs):
                calls.append(('inventory',inv.source_id))
                return list(inv.chapter_records)
            return SimpleNamespace(source_id=inv.source_id,display_name=inv.source_name,
                capabilities=frozenset({'chapters'}),content_languages=('en',),
                parse_manga_ref=lambda value:inv.result['id'],
                get_download_plan=lambda *args,**kwargs:{},get_chapters=chapters)
        sources = {r.source_id:source(r) for r in (a,b)}
        before = deepcopy((a,b))
        result = resolve_search_group(SimpleNamespace(get=sources.get),
            (a.result,b.result),'en','volume')
        self.assertEqual([('inventory','zeta'),('inventory','alpha')],calls)
        self.assertEqual('zeta',result.primary.source_id)
        self.assertTrue(result.decision.ambiguous)
        self.assertEqual(before,(a,b))


def add_case_test(case):
    def test(self):
        # Same inventories under unrelated names must have identical ranking.
        for title in ('Synthetic work','Different invented series'):
            with self.subTest(title=title):
                a,b = pair(case,title)
                self.assertEqual(case['expected_main'],inventory_coverage(a)['main'])
                self.assertEqual(case['expected_unknown'],inventory_coverage(a)['unresolved'])
                self.assertEqual(case['expected'],current_selection((a,b)).source_id)
    test.__doc__ = case.get('meaning','Current generic selection characterization.')
    return test


for _case in FIXTURE['cases']:
    setattr(ProviderSelectionBoundary,'test_fixture_'+_case['name'],add_case_test(_case))


if __name__ == '__main__':
    unittest.main()
