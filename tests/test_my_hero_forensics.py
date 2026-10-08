"""Exact evidence and generic parser regression; no provider-pattern curation."""
import unittest

from mangaanka_search_core.wikipedia_reference import _numbered_list_rows


class NestedTitleAssignment(unittest.TestCase):
    def test_nested_transliteration_equals_is_not_outer_named_argument(self):
        # Minimal form of the exact Audit 39 source defect. No work/number
        # constant belongs in the implementation.
        text = '{{Numbered list|start=118|{{nihongo|"Meaningless Battle"|意味のない戦い|Iminonai Tat=-p[akai}}}}'
        self.assertEqual((('118','Meaningless Battle','chapter'),),_numbered_list_rows(text))

    def test_nested_equals_cannot_drop_and_renumber_following_chapter(self):
        text = '{{Numbered list|start=7|{{nihongo|"First"|名|key=value}}|Second}}'
        self.assertEqual((('7','First','chapter'),('8','Second','chapter')),_numbered_list_rows(text))

    def test_outer_named_parameters_remain_excluded(self):
        text = '{{Numbered list|style=decimal|start=7|First|label=not a chapter|Second}}'
        self.assertEqual((('7','First','chapter'),('8','Second','chapter')),_numbered_list_rows(text))

    def test_deeply_nested_assignment_does_not_change_outer_start(self):
        text = '{{Numbered list|start=3|{{nihongo|"First"|名|{{lang|code=ja|x=y}}}}|Second}}'
        self.assertEqual((('3','First','chapter'),('4','Second','chapter')),_numbered_list_rows(text))


if __name__ == '__main__':
    unittest.main()
