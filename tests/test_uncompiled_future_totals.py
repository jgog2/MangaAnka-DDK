"""A known future bibliography total must not impersonate released coverage."""
import unittest
from test_publication_states import fixture, resolved


class FutureTotals(unittest.TestCase):
    def resolve(self, total=3, volumes=None, change=None):
        res,bundle=fixture(extras=False)
        res.primary.result['volume_context']=[dict(reported_total_volumes=total)]
        bundle['wikipedia']['volumes']+=volumes if volumes is not None else [
            dict(number='3',confidence='explicit',release_date='2030-11-04')]
        if change:change(bundle)
        return resolved(res,bundle,as_of='2030-10-07')

    def test_explicit_future_row_accounts_for_reported_total(self):
        p=self.resolve()
        self.assertEqual((20,10,0,2),tuple(p[k] for k in
            ('mapped_chapters','uncompiled_chapters','unmapped_chapters','final_volumes')))
        self.assertEqual(['3'],p['release_boundary']['future_volumes'])

    def test_unknown_larger_total_remains_blocking(self):
        self.assertEqual(0,self.resolve(total=4)['uncompiled_chapters'])

    def test_undated_empty_listing_cannot_account_for_total(self):
        self.assertEqual(0,self.resolve(volumes=[dict(number='3',confidence='explicit')])['uncompiled_chapters'])

    def test_gap_between_released_and_future_cannot_account_for_total(self):
        self.assertEqual(0,self.resolve(total=4,volumes=[
            dict(number='4',confidence='explicit',release_date='2030-11-04')])['uncompiled_chapters'])

    def test_date_crossing_requires_new_membership_before_uncompiled(self):
        self.assertEqual(0,self.resolve(volumes=[
            dict(number='3',confidence='explicit',release_date='2030-10-07')])['uncompiled_chapters'])

    def test_explicit_future_membership_still_blocks_uncollected_claim(self):
        def change(bundle):
            next(r for r in bundle['wikipedia']['chapters'] if r['number']=='21').update(kind='chapter',volume='3')
        self.assertEqual(0,self.resolve(change=change)['uncompiled_chapters'])

    def test_internal_membership_hole_still_blocks_suffix(self):
        def change(bundle):
            next(r for r in bundle['wikipedia']['chapters'] if r['number']=='11')['volume']=''
        self.assertEqual(0,self.resolve(change=change)['uncompiled_chapters'])

    def test_conflicting_reference_still_blocks_suffix(self):
        def change(bundle):
            bundle['mangadex_structure'].update(status='valid',cache_contract='mangadex-structure-v1',
                canonical_work_id='fixture:serialized',edition_profile='standard',cache_state='refreshed',
                integrity_contract='mangadex-aggregate-integrity-v1',mappings={'11':'1'},volume_count=2)
        p=self.resolve(change=change)
        self.assertIn('11',p['conflicting_chapters'])
        self.assertEqual(0,p['uncompiled_chapters'])

    def test_huge_unexplained_total_is_bounded_and_blocks(self):
        self.assertEqual(0,self.resolve(total=10**12)['uncompiled_chapters'])


if __name__=='__main__':unittest.main()
