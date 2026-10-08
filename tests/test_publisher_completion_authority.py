"""A completed series' available previews do not identify its final chapter."""
from pathlib import Path
import unittest

import ddk_publisher_reference as publisher
from test_publisher_reference import payloads, message, EVIDENCE
from test_logical_membership_authority import scenario
from test_publication_states import resolved
from ddk_publication import publication_holes


class CompletionAuthority(unittest.TestCase):
    def lookup(self, records):
        listing, _ = payloads()
        title = message((1,5000),(2,'Serialized fixture'),(3,'Fixture Author'),(7,0))
        chapters = [(9,message((1,5000),(2,9000+i),(3,'#'+key),(4,name),(6,1700000000)))
                    for i,(key,name) in enumerate(records)]
        detail = message((1,message((8,message((1,title),*chapters,(32,message((1,8))))))))
        return publisher.PublisherReferenceAdapter(lambda url: listing if 'allV2' in url else detail).lookup(EVIDENCE)

    def test_completed_free_previews_are_not_final_identity(self):
        value = self.lookup([(str(n),'Chapter '+str(n)+': Preview') for n in range(1,5)])
        self.assertTrue(value['completed'])
        self.assertEqual(4,len(value['chapters']))
        self.assertNotIn('final_chapter',value)

    def test_explicit_terminal_chapter_is_retained(self):
        value = self.lookup([('1','Chapter 1: Start'),('100','Final Chapter: End')])
        self.assertEqual('100',value['final_chapter']['key'])

    def test_final_story_word_is_not_a_terminal_label(self):
        for name in ('Chapter 4: The Final Battle','Final Battle','Final Pageant',
                     'Final Chapter Preview','Not the Final Chapter'):
            with self.subTest(name=name):
                self.assertNotIn('final_chapter',self.lookup([('4',name)]))

    def test_two_terminal_identities_are_ambiguous(self):
        self.assertNotIn('final_chapter',self.lookup([('99','Final Chapter: End'),('100','Final Page: End')]))

    def test_stored_preview_final_cannot_raise_false_reference_conflict(self):
        res,bundle = scenario()
        value = bundle['publisher_publication']
        record = dict(value['chapters'][0],key='4',label='#004',title='Chapter 4: Preview')
        value.update(chapters=[record],final_chapter=record)
        pub = resolved(res,bundle)
        self.assertEqual('open',pub['publisher_membership']['status'])
        self.assertEqual([],pub['publisher_membership']['conflicts'])
        self.assertNotIn('REFERENCE_CONFLICT',[h['code'] for h in publication_holes(pub,res.primary)])

    def test_stored_unmarked_maximum_cannot_close_membership(self):
        res,bundle = scenario()
        bundle['publisher_publication']['chapters'][0]['title']='Chapter 100: Story'
        pub = resolved(res,bundle)
        self.assertEqual('open',pub['publisher_membership']['status'])
        self.assertEqual(101,pub['logical_chapters'])

    def test_stored_disputed_terminal_candidate_cannot_close(self):
        res,bundle = scenario()
        value = bundle['publisher_publication']
        value['chapters'].append(dict(value['chapters'][0],key='99',label='#99',publisher_record_id=9001))
        self.assertEqual('open',resolved(res,bundle)['publisher_membership']['status'])

    def test_explicit_terminal_does_not_hide_newer_trusted_main(self):
        res,bundle = scenario(independently_supported=True)
        pub = resolved(res,bundle)
        self.assertEqual('conflict',pub['publisher_membership']['status'])
        self.assertEqual(['101'],pub['publisher_membership']['conflicts'])

    def test_explicit_final_page_keeps_closed_membership(self):
        res,bundle = scenario()
        self.assertEqual('closed',resolved(res,bundle)['publisher_membership']['status'])

    def test_future_terminal_identity_is_not_authority(self):
        res,bundle = scenario()
        bundle['publisher_publication']['chapters'][0]['published_at']=4102444800
        self.assertEqual('open',resolved(res,bundle)['publisher_membership']['status'])

    def test_captured_completed_preview_responses_have_no_final_identity(self):
        root=Path(__file__).parent/'fixtures/publisher_completion'
        for ident in (100010,100014,100026):
            with self.subTest(publication_id=ident):
                value=publisher.detail((root/f'{ident}.bin').read_bytes())
                self.assertEqual(8,value['release_schedule'])
                self.assertEqual(['1','2','3','4'],[r['key'] for r in value['chapters']])
                self.assertIsNone(publisher.terminal_chapter(value['chapters']))

    def test_captured_explicit_final_page_is_not_lost(self):
        data=(Path(__file__).parent/'fixtures/publisher_completion/100003.bin').read_bytes()
        value=publisher.detail(data)
        self.assertEqual(8,value['release_schedule'])
        final=publisher.terminal_chapter(value['chapters'])
        self.assertEqual(('392',1027803),(final['key'],final['publisher_record_id']))


if __name__=='__main__': unittest.main()
