"""Acquisition presence cannot promote an opaque structural range."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from test_wikipedia_membership_audit import TEXT, audited


class MixedTailInvestigation(unittest.TestCase):
    def setUp(self):
        net=patch('urllib.request.urlopen',side_effect=AssertionError('Unexpected network'))
        net.start();self.addCleanup(net.stop)

    def test_acquired_integer_intersection_does_not_invent_uncollected_members(self):
        for endpoint in ('134.1','134.5'):
            _,pub=audited(TEXT.replace('128–134','128–'+endpoint))
            self.assertEqual((127,0,7,17),tuple(pub[k] for k in
                ('mapped_main_chapters','uncompiled_chapters','unmapped_chapters','final_volumes')))
            self.assertEqual([str(n) for n in range(128,135)],pub['unmapped_identifiers'])
            self.assertTrue(all(not row.get('_effective_volume') for row in pub['projection'][127:]))

    def test_missing_acquisition_and_internal_gap_do_not_establish_release_completeness(self):
        for missing in ('129','31'):
            keys=[str(n) for n in range(1,135) if str(n)!=missing]
            _,pub=audited(TEXT.replace('128–134','128–134.1'),keys)
            self.assertEqual(0,pub['uncompiled_chapters'])
            self.assertNotIn(missing,[row['chapter'] for row in pub['projection']])

    def test_future_row_and_opaque_expression_remain_separate_provenance(self):
        _,pub=audited(TEXT.replace('128–134','128–134.1'))
        row=next(r for r in pub['references']['wikipedia']['chapters'] if r['number']=='128–134.1')
        before=deepcopy(row)
        self.assertEqual('uncollected_range',row['kind']);self.assertFalse(row['volume'])
        self.assertTrue(row['source_record_id'].endswith('uncollected:0'))
        self.assertEqual(['18'],pub['release_boundary']['future_volumes'])
        self.assertEqual(before,row)


if __name__=='__main__':unittest.main()
