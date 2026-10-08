"""Explicit source syntax and search→inventory contract regressions."""
import unittest
from test_wikipedia_days_membership import rows, volume
from test_wikipedia_membership_audit import audited
from mangaanka_search_core.wikipedia_reference import WikipediaPublicationAdapter
from mangaanka_search_core.mangadex_source import MangaDexSource
from mangaanka_search_core.inventory_comparison import inspect_source_inventory


class ExplicitMembershipSyntax(unittest.TestCase):
    def test_scene_number_is_explicit_main_identity(self):
        self.assertEqual([('1', [('1', 'Opening', 'chapter'), ('2', 'Next', 'chapter')])],
                         rows(volume(1, '* Scene 1. {{nihongo|Opening|原題}}\n* Scene 2: Next')))

    def test_scene_does_not_promote_last_extra_nested_or_prose(self):
        self.assertEqual([], rows(volume(1, '*Last Scene. End\n*Extra Scene 5. Bonus\n**Scene 8. Nested\nScene 9. Prose'))[0][1])

    def test_plural_numeric_membership_uses_bounded_expansion(self):
        self.assertEqual(['1','2','3','7'], [r[0] for _,cs in rows(volume(1,'* Chapters 1–3, 7')) for r in cs])

    def test_bad_plural_range_never_partially_maps(self):
        for expression in ('1–3.1', '1–9999', '1–3, nope'):
            with self.subTest(expression=expression):
                result=rows(volume(1,'* Chapters '+expression))[0][1]
                self.assertFalse(any(r[2]=='chapter' for r in result))

    def test_plural_bonus_prose_and_unbounded_are_not_main(self):
        for line in ('* Bonus Chapters 1–3','** Chapters 1–3','Chapters 1–3','* Chapters 1–3 are missing','* Chapters 1 onward'):
            with self.subTest(line=line): self.assertFalse(rows(volume(1,line))[0][1])

    def test_actual_manifest_projection_uses_ranges_and_scene(self):
        _,pub=audited(volume(1,'* Chapters 1–3')+volume(2,'* Scene 4. Fourth'), ['1','2','3','4','5'])
        self.assertEqual((4,1,2), tuple(pub[k] for k in ('mapped_main_chapters','unmapped_chapters','final_volumes')))

    def test_conflicts_and_future_remain_fail_closed(self):
        _,pub=audited(volume(1,'* Chapters 1–3')+volume(2,'* Scene 2. Other'), ['1','2','3'])
        self.assertIn('2',pub['conflicting_chapters'])
        _,pub=audited(volume(1,'* Chapters 1–3','January 1, 2099'), ['1','2','3'])
        self.assertEqual(0,pub['mapped_main_chapters'])

    def test_old_syntax_cache_invalidated(self):
        self.assertNotEqual('8',WikipediaPublicationAdapter.parser_version)


class StructuralPageSyntax(unittest.TestCase):
    def test_colon_within_exact_work_title_is_not_a_namespace(self):
        adapter=WikipediaPublicationAdapter()
        self.assertTrue(adapter._is_related_chapter_page('Fixture: A Tale','List of Fixture: A Tale chapters'))
        self.assertTrue(adapter._is_publication_index_page('Fixture: A Tale','List of Fixture: A Tale volumes'))

    def test_real_namespaces_and_different_works_are_excluded(self):
        adapter=WikipediaPublicationAdapter()
        for candidate in ('Category:List of Fixture: A Tale chapters','Template:List of Fixture: A Tale chapters',
                          'File:List of Fixture: A Tale chapters','List of Other: A Tale chapters'):
            self.assertFalse(adapter._is_collection_node('Fixture: A Tale',candidate))

    def test_reldate_is_explicit_original_release_field(self):
        adapter=WikipediaPublicationAdapter();adapter._wikitext=lambda page: '{{Graphic novel list|VolumeNumber=1|RelDate=January 1, 2020<ref>Accessed January 1, 2099</ref>|ChapterList=\n* Chapters 1–2\n}}'
        v,_=adapter._parse_graphic_lists('Fixture')[0]
        self.assertEqual('2020-01-01',v.release_date);self.assertEqual('RelDate',v.release_evidence)

    def test_no_release_is_inferred_from_citations_or_licensed_date(self):
        adapter=WikipediaPublicationAdapter()
        for field in ('RelDate=<ref>January 1, 2020</ref>','LicensedRelDate=January 1, 2020',
                      'RelDate=January 1, 2020 (regular edition)<br/>January 2, 2020 (limited edition)'):
            adapter._wikitext=lambda page,field=field: '{{Graphic novel list|VolumeNumber=1|'+field+'|ChapterList=\n* Chapters 1–2\n}}'
            self.assertEqual('',adapter._parse_graphic_lists('Fixture')[0][0].release_date)

    def test_explicit_original_date_not_replaced_by_different_reldate(self):
        adapter=WikipediaPublicationAdapter();adapter._wikitext=lambda page: '{{Graphic novel list|VolumeNumber=1|OriginalRelDate=January 1, 2099|RelDate=January 1, 2020|ChapterList=\n* Chapters 1–2\n}}'
        self.assertEqual('2099-01-01',adapter._parse_graphic_lists('Fixture')[0][0].release_date)


class MangaDexSearchInventoryContract(unittest.TestCase):
    def test_actual_search_result_is_usable_by_own_inventory_adapter(self):
        uid='fa3e0b2f-4e1f-48ee-9af0-1de9dc28ca51';calls=[]
        def api(url,**kwargs):
            calls.append(url)
            if '/feed?' in url:
                return {'data':[{'id':'chapter-id','attributes':{'chapter':'1','volume':'1','pages':20,'externalUrl':None}}]}
            return {'total':1,'data':[{'id':uid,'attributes':{'title':{'en':'Roundtrip fixture'},'availableTranslatedLanguages':['en']},'relationships':[]}]}
        source=MangaDexSource(api_json=api)
        row=source.search('Roundtrip fixture',limit=1,availability_cache={uid:True})['rows'][0]
        self.assertEqual(uid,row['id'])
        inv=inspect_source_inventory(source,row,'en',workflow='chapter')
        self.assertTrue(inv.usable,inv.error)
        self.assertEqual(1,inv.chapter_count)
        self.assertTrue(any('/manga/'+uid+'/feed?' in v for v in calls))

    def test_direct_invalid_reference_is_still_rejected(self):
        source=MangaDexSource(api_json=lambda *a,**k:self.fail('Unexpected network'))
        for value in ('fa3e0b2f-4e1f-48ee-9af0-1de9dc28ca51','https://evil.example/title/fa3e0b2f-4e1f-48ee-9af0-1de9dc28ca51'):
            with self.assertRaises(ValueError):source.get_chapters(value,'en')


if __name__=='__main__':unittest.main()
