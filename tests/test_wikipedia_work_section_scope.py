"""Exact publication-section scoping; no work-specific parser conditions."""
from dataclasses import asdict
import unittest
from unittest.mock import patch

from mangaanka_search_core.wikipedia_reference import WikipediaPublicationAdapter
from mangaanka_search_core.reference_metadata import PublicationMatch
from test_publication_states import fixture, resolved


TITLE='List of Serialized fixture chapters'


def volume(number, chapters):
    return '{{Graphic novel list|VolumeNumber='+str(number)+'|OriginalRelDate=January 1, 2024|ChapterList='+chapters+'}}\n'


TEXT=("== ''Serialized fixture'' volumes ==\n"+
      volume(1,'*1. Main A\n*2. Main B\n')+
      volume(2,'*3. Main C\n*4. Main D\n')+
      "=== Chapters not yet in ''tankōbon'' format ===\n*5. Tail\n"+
      "== ''Serialized fixture: Side Story'' volumes ==\n"+
      volume(1,'*1. Side A\n*2. Side B\n*3. Side C\n')+
      "=== Chapters not yet in ''tankōbon'' format ===\n*4. Side Tail\n"+
      '== References ==\n')


def parsed(text=TEXT, title=TITLE):
    def request(params):
        return {'parse':dict(title=title,pageid=10,revid=20,wikitext={'*':text})}
    adapter=WikipediaPublicationAdapter(request)
    return adapter.resolve_publication(PublicationMatch(
        'wikipedia','10',title,'confident','exact fixture',edition='original'))


class WorkSectionScope(unittest.TestCase):
    def setUp(self):
        guard=patch('urllib.request.urlopen',side_effect=AssertionError('Unexpected network'))
        guard.start();self.addCleanup(guard.stop)

    def test_exact_volumes_heading_excludes_other_work_and_its_tail(self):
        result=parsed()
        self.assertEqual(['1','2','3','4','5'],[r.number for r in result['chapters']])
        self.assertEqual(['Main A','Main B','Main C','Main D','Tail'],[r.title for r in result['chapters']])
        self.assertEqual(['1','2'],[r.number for r in result['volumes']])
        self.assertEqual('uncollected',result['chapters'][-1].kind)

    def test_exact_side_work_selects_its_own_section(self):
        result=parsed(title='List of Serialized fixture: Side Story chapters')
        self.assertEqual(['Side A','Side B','Side C','Side Tail'],[r.title for r in result['chapters']])

    def test_ambiguous_duplicate_main_headings_fail_closed(self):
        self.assertFalse(parsed(TEXT+"== Serialized fixture volumes ==\n"+volume(3,'*6. Other\n'))['chapters'])

    def test_bare_and_volumes_heading_candidates_remain_ambiguous(self):
        self.assertFalse(parsed(TEXT+"== Serialized fixture ==\n"+volume(3,'*6. Other\n'))['chapters'])

    def test_typography_only_equivalence_is_preserved(self):
        text='== Alpha × Beta volumes ==\nMain\n== Alpha x Beta: Side Story volumes ==\nOther'
        self.assertEqual('\nMain\n',WikipediaPublicationAdapter._main_series_section(text,'List of Alpha x Beta chapters'))

    def test_child_uncollected_section_is_retained_but_peer_excluded(self):
        text='== Work volumes ==\nMain\n=== Chapters not yet collected ===\nTail\n== Other volumes ==\nOther'
        self.assertEqual('\nMain\n=== Chapters not yet collected ===\nTail\n',WikipediaPublicationAdapter._main_series_section(text,'Work'))

    def test_other_work_prefix_is_not_a_target_heading(self):
        text='== Work volumes ==\nMain\n== Work Extended volumes ==\nOther'
        self.assertEqual('\nMain\n',WikipediaPublicationAdapter._main_series_section(text,'Work'))

    def test_omnibus_is_not_a_standard_heading(self):
        text='== Work omnibus volumes ==\nOther\n== Work volumes ==\nMain'
        self.assertEqual('\nMain',WikipediaPublicationAdapter._main_series_section(text,'Work'))

    def test_existing_exact_heading_and_unsectioned_layout_are_preserved(self):
        self.assertEqual('\nMain\n',WikipediaPublicationAdapter._main_series_section('== Work ==\nMain\n== Other ==\nOther','Work'))
        text=volume(1,'*1. Main\n')
        self.assertEqual(text,WikipediaPublicationAdapter._main_series_section(text,'Work'))

    def test_scoped_claims_reach_real_manifest_without_fabricating_conflicts(self):
        res,bundle=fixture(extras=False)
        result=parsed()
        bundle['wikipedia']['chapters']=[asdict(r) for r in result['chapters']]
        bundle['wikipedia']['volumes']=[asdict(r) for r in result['volumes']]
        pub=resolved(res,bundle,as_of='2026-10-06')
        rows={r['chapter']:r for r in pub['projection']}
        self.assertEqual('2',rows['3']['_effective_volume'])
        self.assertNotIn('3',pub['conflicting_chapters'])
        proof=next(r for r in bundle['wikipedia']['chapters'] if r['number']=='3')
        self.assertEqual(('10','20',TITLE),(proof['source_page_id'],proof['source_revision_id'],proof['source_page']))

    def test_real_reference_disagreement_stays_fail_closed(self):
        res,bundle=fixture(extras=False)
        result=parsed()
        bundle['wikipedia']['chapters']=[asdict(r) for r in result['chapters']]
        bundle['wikipedia']['volumes']=[asdict(r) for r in result['volumes']]
        bundle['mangadex_structure']=dict(status='valid',cache_contract='mangadex-structure-v1',
            canonical_work_id='fixture:serialized',edition_profile='standard',
            manga_id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',mappings={'3':'1'},ambiguous_chapters=[])
        pub=resolved(res,bundle,as_of='2026-10-06')
        self.assertIn('3',pub['conflicting_chapters'])
        self.assertFalse(next(r for r in pub['projection'] if r['chapter']=='3').get('_effective_volume'))


if __name__=='__main__':unittest.main()
