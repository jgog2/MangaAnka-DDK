"""Explicit numbered publication labels, without work-specific inference."""
import unittest

from test_wikipedia_membership_audit import audited
from mangaanka_search_core.wikipedia_reference import WikipediaPublicationAdapter
from mangaanka_search_core.reference_integration import _usable_wikipedia_cache


def rows(text, work='Serialized fixture'):
    adapter = WikipediaPublicationAdapter()
    adapter._wikitext = lambda page: text
    return [(volume.number, list(chapters)) for volume, chapters in
            adapter._parse_graphic_lists('List of Serialized fixture chapters', work)]


def volume(number, contents, date='January 1, 2020'):
    return ('{{Graphic novel list|VolumeNumber=' + str(number) +
            '|OriginalRelDate=' + date + '|ChapterList=\n' + contents + '\n}}')


class DaysMembership(unittest.TestCase):
    def test_explicit_numbered_label_with_nested_title(self):
        self.assertEqual([('1', [('1', 'Opening', 'chapter'), ('2', 'Next', 'chapter')])],
            rows(volume(1, '*Days 1: {{Nihongo|"Opening"|原題}}\n*Days 2: "Next"')))

    def test_explicit_label_decimal_stays_decimal(self):
        self.assertEqual('22.1', rows(volume(3, '*Days 22.1: Extra'))[0][1][0][0])

    def test_explicit_membership_range_is_bounded(self):
        self.assertEqual(['7', '8', '9'], [r[0] for r in rows(volume(2, '*Days: 7–9'))[0][1]])

    def test_malformed_range_is_not_partially_promoted(self):
        self.assertEqual('range', rows(volume(2, '*Days: 7–9.1'))[0][1][0][2])

    def test_multiple_tables_keep_explicit_volumes(self):
        self.assertEqual(['1', '4'], [v for v, c in rows(
            volume(1, '*Days 1: First') + volume(4, '*Days 32: Later')) if c])

    def test_sibling_work_is_excluded(self):
        text = ("== Serialized fixture ==\n" + volume(1, '*Days 1: Main') +
                '\n== Other fixture ==\n' + volume(1, '*Days 99: Other'))
        self.assertEqual(['1'], [r[0] for v, cs in rows(text) for r in cs])

    def test_ambiguous_duplicate_work_sections_fail_closed(self):
        text = ('== Serialized fixture ==\n' + volume(1, '*Days 1: First') +
                '\n== Serialized fixture volumes ==\n' + volume(2, '*Days 1: Second'))
        self.assertEqual([], rows(text))

    def test_supplementary_nested_and_prose_are_not_main(self):
        text = volume(1, '*Bonus Days 7: Extra\n**Days 8: Nested\nDays 9: prose\n'
                           '*Future Days 10: Other\n*Days eleven: Invalid')
        self.assertEqual([], rows(text)[0][1])

    def test_empty_future_volume_does_not_infer_membership(self):
        self.assertEqual([('9', [])], rows(volume(9, '', 'January 1, 2099')))

    def test_real_reference_manifest_projection_pipeline(self):
        _, pub = audited(volume(1, '*Days 1: First\n*Days 2: Second'), ['1', '2', '3'])
        self.assertEqual((2, 1, 1), tuple(pub[k] for k in
            ('mapped_main_chapters', 'unmapped_chapters', 'final_volumes')))
        self.assertEqual('valid_with_data', pub['references']['wikipedia']['status'])

    def test_future_explicit_contents_do_not_assign_current_acquisition(self):
        _, pub = audited(volume(1, '*Days 1: First', 'January 1, 2099'), ['1'])
        self.assertEqual((0, 1), (pub['mapped_main_chapters'], pub['unmapped_chapters']))

    def test_conflicting_explicit_memberships_remain_ambiguous(self):
        _, pub = audited(volume(1, '*Days 1: First') + volume(2, '*Days 1: Other'), ['1'])
        self.assertEqual(['1'], pub['conflicting_chapters'])
        self.assertEqual(0, pub['mapped_main_chapters'])
        # Internal Wikipedia ambiguity is represented separately from a
        # reconciler's cross-source conflict claims; an empty array is safe.
        self.assertEqual([], pub['reference_conflicts'])

    def test_explicit_uncollected_days_remain_volume_free(self):
        text = (volume(1, '*Days 1: First') +
                "\n=== Chapters not yet in ''tankōbon'' format ===\n*Days 2: Next")
        adapter = WikipediaPublicationAdapter()
        adapter._wikitext = lambda page: text
        self.assertEqual((('2', 'Next', 'uncollected'),),
                         adapter._parse_uncollected_chapters('fixture'))

    def test_previous_parser_collection_cache_cannot_be_reused(self):
        _, pub = audited(volume(1, '*Days 1: First'), ['1'])
        value = dict(pub['references']['wikipedia'])
        adapter = WikipediaPublicationAdapter()
        self.assertTrue(_usable_wikipedia_cache(value, adapter))
        value['parser_version'] = '7'
        self.assertFalse(_usable_wikipedia_cache(value, adapter))


if __name__ == '__main__':
    unittest.main()
