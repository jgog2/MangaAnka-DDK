"""Real Wikipedia adapter -> trusted manifest identity -> DDK classification."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from test_artifact_authority import pattern
from ddk_publication import resolve_publication
from mangaanka_search_core.wikipedia_reference import WikipediaPublicationAdapter
from mangaanka_search_core.reference_integration import ReferenceMetadataService
from mangaanka_search_core.reference_metadata import PublicationMatch


class NoBooks:
    def match_publication(self,evidence):
        return PublicationMatch('bookwalker','','','no_match','offline')


class WikipediaPageIdentity(unittest.TestCase):
    def test_actual_adapter_list_and_main_collision_reaches_supported_fractions(self):
        res,_=pattern(['58','58.1','58.2'],['58.1','58.2'])
        result=dict(res.primary.result)
        result['alternate_titles']=['List of Serialized fixture chapters']
        from dataclasses import replace
        primary=replace(res.primary,result=result)
        res=replace(res,primary=primary,inventories=(primary,))
        text='''{{Graphic novel list|VolumeNumber=1|ChapterListCol1=
* 58. Main
* 58.1. First published fraction
* 58.2. Second published fraction
}}'''
        searches=[dict(pageid=1,title='Serialized fixture'),dict(pageid=2,title='List of Serialized fixture chapters')]
        calls=[]
        def request(params):
            calls.append(dict(params))
            if params['action']=='query': return {'query':{'search':deepcopy(searches)}}
            self.assertEqual('List of Serialized fixture chapters',params['page'])
            return {'parse':{'title':params['page'],'pageid':2,'revid':20,'wikitext':{'*':text}}}
        service=ReferenceMetadataService(None,WikipediaPublicationAdapter(request),NoBooks())
        acquisitions=deepcopy(primary.chapter_records)
        with patch('urllib.request.urlopen',side_effect=AssertionError('Unexpected network')):
            pub=resolve_publication(res,[result],service=service,as_of='2026-10-05')
        self.assertEqual('List of Serialized fixture chapters',pub['references']['wikipedia']['match']['title'])
        self.assertEqual(['main']*3,pub['normalization']['labels'])
        self.assertEqual(3,pub['mapped_main_chapters'])
        self.assertFalse(pub['normalization']['artifact_groups'])
        self.assertEqual(acquisitions,primary.chapter_records)
        self.assertEqual(['reader:58','reader:58.1','reader:58.2'],[r['id'] for r in pub['projection']])
        for proof in pub['normalization']['publication_identity_rows']:
            self.assertEqual('List of Serialized fixture chapters',proof['evidence'][0]['source_page'])
        self.assertEqual(1,sum(p['action']=='query' for p in calls))


if __name__=='__main__': unittest.main()
