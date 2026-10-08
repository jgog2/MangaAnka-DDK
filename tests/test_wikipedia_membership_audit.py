"""Labeled Wikipedia fields through the real reference/manifest/DDK pipeline."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import unittest
from unittest.mock import patch

from test_artifact_authority import pattern
from test_publication_states import resolved
from test_wikipedia_page_identity import NoBooks
from ddk_publication import resolve_publication, publication_holes
from mangaanka_search_core import PLUGIN_ROOT
from mangaanka_search_core.wikipedia_reference import WikipediaPublicationAdapter
from mangaanka_search_core.reference_integration import ReferenceMetadataService


TEXT=(PLUGIN_ROOT/'tests/fixtures/wikipedia_labeled_membership.wiki').read_text(encoding='utf-8')
TITLE='List of Serialized fixture chapters'


def audited(text=TEXT, keys=None, native=None):
    keys=[str(n) for n in range(1,135)] if keys is None else keys
    res,_=pattern(keys,[])
    if native:
        primary=replace(res.primary,chapter_records=tuple(dict(r,volume=native[r['chapter']])
            if r['chapter'] in native else r for r in res.primary.chapter_records))
        res=replace(res,primary=primary,inventories=(primary,))
    def request(params):
        if params['action']=='query':
            return {'query':{'search':[dict(pageid=1,title='Serialized fixture'),dict(pageid=2,title=TITLE)]}}
        return {'parse':dict(title=TITLE,pageid=2,revid=20,wikitext={'*':text})}
    service=ReferenceMetadataService(None,WikipediaPublicationAdapter(request),NoBooks())
    pub=resolve_publication(res,[res.primary.result],service=service,as_of='2026-10-06')
    return res,pub


class WikipediaMembershipAudit(unittest.TestCase):
    def setUp(self):
        guard=patch('urllib.request.urlopen',side_effect=AssertionError('Unexpected network'))
        guard.start();self.addCleanup(guard.stop)

    def test_actual_adapter_maps_127_main_and_preserves_seven_uncompiled(self):
        res,pub=audited()
        self.assertEqual((134,127,7,0,17),tuple(pub[k] for k in
            ('canonical_main_chapters','mapped_main_chapters','uncompiled_chapters','unmapped_chapters','final_volumes')))
        self.assertEqual([str(n) for n in range(128,135)],pub['uncompiled_identifiers'])
        self.assertEqual([],publication_holes(pub,res.primary))
        self.assertTrue(all(not r.get('_effective_volume') for r in pub['projection'][127:]))
        wiki=pub['references']['wikipedia']
        self.assertEqual(('valid_with_data','8'),(wiki['status'],wiki['parser_version']))
        self.assertEqual('6',next(r for r in wiki['chapters'] if r['number']=='Short Mission 4')['volume'])
        self.assertEqual(0,pub['recognized_specials'])
        self.assertEqual([r['id'] for r in res.primary.chapter_records],[r['id'] for r in pub['projection']])

    def test_mixed_decimal_tail_stays_unmapped_without_invented_volume_or_decimals(self):
        _,pub=audited(TEXT.replace('128–134','128–140.1'))
        self.assertEqual((127,0,7,17),tuple(pub[k] for k in
            ('mapped_main_chapters','uncompiled_chapters','unmapped_chapters','final_volumes')))
        row=next(r for r in pub['references']['wikipedia']['chapters'] if r['number']=='128–140.1')
        self.assertEqual(('uncollected_range',''),(row['kind'],row['volume']))

    def test_listed_empty_volume_is_not_a_released_or_inferred_tail_volume(self):
        _,pub=audited(TEXT.replace('November 4, 2099',''))
        self.assertEqual((127,7,0,17),tuple(pub[k] for k in
            ('mapped_main_chapters','uncompiled_chapters','unmapped_chapters','final_volumes')))
        self.assertTrue(all(not r.get('_effective_volume') for r in pub['projection'][127:]))

    def test_fraction_identity_uses_existing_authority_and_short_alias_is_not_invented(self):
        text='{{Graphic novel list|VolumeNumber=1|ChapterList=*Mission: 58.1, 58.2\n*Short Mission: 4}}'
        _,pub=audited(text,['58.1','58.2','100.1','100.2'])
        self.assertEqual(['main','main','provider_split_candidate','provider_split_candidate'],pub['normalization']['labels'])
        self.assertEqual(2,pub['mapped_main_chapters'])
        self.assertEqual(0,pub['recognized_specials'])
        self.assertTrue(all(p['evidence'][0]['source_page']==TITLE
            for p in pub['normalization']['publication_identity_rows'][:2]))

    def test_new_memberships_corroborate_or_conflict_with_mangadex(self):
        res,pub=audited()
        for volume in ('6','7'):
            bundle=deepcopy(pub['references'])
            bundle['mangadex_structure']=dict(status='valid',cache_contract='mangadex-structure-v1',
                canonical_work_id='fixture:serialized',edition_profile='standard',
                manga_id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',mappings={'31':volume},
                ambiguous_chapters=[],cache_state='refreshed')
            current=resolved(res,bundle,as_of='2026-10-06')
            self.assertEqual([] if volume=='6' else ['31'],current['conflicting_chapters'])
            if volume=='7':
                self.assertEqual(1,sum(h['code']=='REFERENCE_CONFLICT' for h in publication_holes(current,res.primary)))
                self.assertFalse(next(r for r in current['projection'] if r['chapter']=='31').get('_effective_volume'))

    def test_provider_explicit_membership_keeps_existing_precedence(self):
        _,pub=audited(native={'31':'7'})
        row=next(r for r in pub['projection'] if r['chapter']=='31')
        self.assertEqual(('7','provider_explicit'),(row['_effective_volume'],row['_projection_state']))

    def test_internal_gap_and_stale_failed_quarantine_remain_reviewable(self):
        res,pub=audited(TEXT.replace('Mission: 31–37','Mission: 32–37'))
        self.assertIn('31',pub['unmapped_identifiers'])
        self.assertEqual(0,pub['uncompiled_chapters'])
        res,pub=audited()
        for change in (dict(cache_state='last_known_good'),dict(refresh_status='transient_failure'),
                       dict(status='transient_failure'),dict(collection={'quarantined_groups':[{'display_key':'31'}]})):
            bundle=deepcopy(pub['references']);bundle['wikipedia'].update(change)
            current=resolved(res,bundle,as_of='2026-10-06')
            self.assertEqual(0,current['uncompiled_chapters'])
            self.assertTrue(current['unmapped_chapters'])


if __name__=='__main__':unittest.main()
