"""Publisher protocol, compatibility, freshness and supplementary observations."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import unittest
from unittest.mock import patch
from concurrent.futures import CancelledError

import ddk_publisher_reference as publisher
from test_logical_membership_authority import scenario, publisher_value
from test_publication_states import resolved
from ddk_publication import publication_holes


def varint(value):
    result = bytearray()
    while value > 127: result.append((value & 127)|128); value >>= 7
    result.append(value); return bytes(result)


def message(*values):
    result = b''
    for key, value in values:
        if isinstance(value,str): value = value.encode('utf-8')
        result += varint(key*8+(2 if isinstance(value,bytes) else 0))
        result += varint(len(value))+value if isinstance(value,bytes) else varint(value)
    return result


def payloads(schedule=8, candidates=None, ident=5000, creator='Fixture Author', name='Serialized fixture'):
    def title(i=ident,n=name,a=creator): return message((1,i),(2,n),(3,a),(7,0))
    listing = message((1,message((25,message((1,message(*[(2,title(*c)) for c in
        (candidates or [(ident,name,creator)])])))))))
    chapter = message((1,ident),(2,9000),(3,'#100'),(4,'Final page'),(6,1700000000))
    detail = message((1,message((8,message((1,title()),(10,chapter),(32,message((1,schedule))))))))
    return listing, detail


EVIDENCE = dict(canonical_work_id='fixture:serialized', canonical_title='Serialized fixture',
    canonical_aliases=['Serialized fixture'],creators=['Fixture Author'],creator_aliases=[],
    identity_confidence='high',edition_profile='standard',requested_language='en')


class PublisherProtocol(unittest.TestCase):
    def setUp(self):
        guard=patch('urllib.request.urlopen',side_effect=AssertionError('Unexpected network'))
        guard.start();self.addCleanup(guard.stop)

    def lookup(self, **kwargs):
        listing, detail = payloads(**kwargs)
        requests=[]
        def read(url): requests.append(url); return listing if 'allV2' in url else detail
        return publisher.PublisherReferenceAdapter(read).lookup(EVIDENCE), requests

    def test_exact_title_creator_and_explicit_completed_enum(self):
        value, requests = self.lookup()
        self.assertEqual(('current',True,'100',9000),(value['status'],value['completed'],
            value['final_chapter']['key'],value['final_chapter']['publisher_record_id']))
        self.assertEqual(2,len(requests))
        self.assertEqual(64,len(value['payload_sha256']))

    def test_disabled_display_label_is_not_completion_authority(self):
        value,_=self.lookup(schedule=0)
        self.assertFalse(value['completed']);self.assertNotIn('final_chapter',value)

    def test_ongoing_and_oneshot_do_not_close(self):
        for schedule in (2,9,10):
            with self.subTest(schedule=schedule):self.assertFalse(self.lookup(schedule=schedule)[0]['completed'])

    def test_different_author_does_not_match(self):
        value,requests=self.lookup(creator='Other Author')
        self.assertEqual('unmatched',value['status']);self.assertEqual(1,len(requests))

    def test_two_exact_compatible_works_are_ambiguous(self):
        value,_=self.lookup(candidates=[(5000,'Serialized fixture','Fixture Author'),
                                       (5001,'Serialized fixture','Fixture Author')])
        self.assertEqual('ambiguous',value['status'])

    def test_no_fuzzy_title_link(self):
        self.assertEqual('unmatched',self.lookup(name='Serialized fixture sequel')[0]['status'])

    def test_explicit_macron_creator_spelling_not_general_fuzzy_matching(self):
        evidence=dict(creators=['Yuuki Tabata'],creator_aliases=[])
        self.assertTrue(publisher.creators_match('Yūki Tabata',evidence))
        self.assertFalse(publisher.creators_match('Yuki Other',evidence))
        self.assertFalse(publisher.creators_match('Yuki Tabata',evidence))

    def test_unsafe_identity_edition_and_language_do_not_request(self):
        for change in (dict(identity_confidence='low'),dict(edition_profile='fan_color'),
                       dict(requested_language='ja'),dict(canonical_work_id='')):
            with self.subTest(change=change):
                adapter=publisher.PublisherReferenceAdapter(lambda _:self.fail('Unexpected request'))
                self.assertEqual('incompatible_identity',adapter.lookup(dict(EVIDENCE,**change))['status'])

    def test_transport_failure_is_observed_without_closure(self):
        adapter=publisher.PublisherReferenceAdapter(lambda _:(_ for _ in ()).throw(OSError('offline')))
        value=adapter.lookup(EVIDENCE)
        self.assertEqual('unavailable',value['status']);self.assertNotIn('completed',value)

    def test_cancel_propagates(self):
        with self.assertRaises(CancelledError):
            publisher.PublisherReferenceAdapter().lookup(EVIDENCE,lambda:True)

    def test_api_error_and_truncated_protocol_rejected(self):
        for raw in (message((2,message((1,'error')))),b'\x0a\xff',b'\x00',b'\x0b'):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):publisher.catalog(raw)

    def test_unknown_fields_are_skipped_without_recursive_guessing(self):
        listing,_=payloads()
        self.assertEqual(5000,publisher.catalog(listing+message((99,b'not protobuf')))[0]['id'])

    def test_size_limit_is_enforced(self):
        with self.assertRaises(ValueError):publisher.wire(b'0'*(publisher.MAX_BYTES+1))

    def test_scalar_protocol_ambiguity_is_rejected(self):
        with self.assertRaises(ValueError):publisher.one(publisher.wire(message((1,1),(1,2))),1)

    def test_detail_identity_must_match_selected_catalog_record(self):
        listing,_=payloads();_,other=payloads(ident=5001)
        value=publisher.PublisherReferenceAdapter(lambda u: listing if 'allV2' in u else other).lookup(EVIDENCE)
        self.assertEqual('incompatible_detail',value['status'])

    def test_catalog_language_must_be_english(self):
        self.assertFalse(publisher.compatible(dict(id=1,title='Serialized fixture',creator='Fixture Author',language=1),EVIDENCE))


class PublisherMembership(unittest.TestCase):
    def test_absent_completion_retains_existing_tail_behavior(self):
        res,bundle=scenario();bundle.pop('publisher_publication')
        self.assertEqual(101,resolved(res,bundle)['logical_chapters'])

    def test_stale_failed_wrong_work_edition_language_or_creator_cannot_close(self):
        stamp=(datetime.now(timezone.utc)-timedelta(days=3)).isoformat()
        for change in (dict(checked_at=stamp),dict(status='unavailable'),dict(contract='old'),
                       dict(canonical_work_id='different'),dict(edition='omnibus'),
                       dict(language='ja'),dict(creator='Other Author'),dict(title='Other work'),
                       dict(payload_sha256='wrong'),dict(publication_id='other')):
            res,bundle=scenario();bundle['publisher_publication'].update(change)
            with self.subTest(change=change):
                pub=resolved(res,bundle)
                self.assertEqual('unavailable',pub['publisher_membership']['status'])
                self.assertEqual(101,pub['logical_chapters'])

    def test_future_check_and_future_chapter_cannot_close(self):
        res,bundle=scenario();bundle['publisher_publication']['checked_at']='2099-01-01T00:00:00+00:00'
        self.assertEqual(101,resolved(res,bundle)['logical_chapters'])
        res,bundle=scenario();bundle['publisher_publication']['chapters'][0]['published_at']=4102444800
        self.assertNotEqual('closed',resolved(res,bundle)['publisher_membership']['status'])

    def test_partial_backbone_does_not_close_or_fill_gap(self):
        res,bundle=scenario()
        bundle['wikipedia']['chapters']=[r for r in bundle['wikipedia']['chapters'] if r['number']!='50']
        pub=resolved(res,bundle)
        self.assertEqual('open',pub['publisher_membership']['status'])
        self.assertIn('50',pub['unmapped_identifiers'])
        self.assertIn('101',pub['unmapped_identifiers'])

    def test_new_independent_chapter_contradicts_completed_boundary(self):
        res,bundle=scenario(independently_supported=True,kind='uncollected')
        pub=resolved(res,bundle)
        self.assertEqual('conflict',pub['publisher_membership']['status'])
        self.assertEqual(['101'],pub['publisher_membership']['conflicts'])
        self.assertEqual(101,pub['canonical_main_chapters'])
        self.assertIn('REFERENCE_CONFLICT',[h['code'] for h in publication_holes(pub,res.primary)])

    def test_independent_peer_extension_is_not_suppressed_by_completion(self):
        from dataclasses import replace
        res,bundle=scenario()
        peers=tuple(replace(res.primary,source_id=s) for s in ('mangapill','weebcentral'))
        res=replace(res,inventories=(res.primary,*peers));pub=resolved(res,bundle)
        self.assertEqual(('conflict',['101']),(pub['publisher_membership']['status'],pub['publisher_membership']['conflicts']))
        self.assertEqual(101,pub['canonical_main_chapters'])

    def test_publisher_positive_identity_can_extend_stale_structure(self):
        res,bundle=scenario()
        bundle['wikipedia']['cache_state']='last_known_good'
        bundle['publisher_publication']=publisher_value('101',completed=False)
        pub=resolved(res,bundle)
        self.assertEqual('main',pub['normalization']['labels'][-1])
        self.assertIn('101',pub['unmapped_identifiers'])
        self.assertNotIn('101',[r['chapter'] for r in pub['unclassified_acquisition']])

    def test_internal_structure_conflict_prevents_closure(self):
        res,bundle=scenario()
        bundle['wikipedia']['chapters'].append(dict(bundle['wikipedia']['chapters'][0],volume='2'))
        pub=resolved(res,bundle)
        self.assertNotEqual('closed',pub['publisher_membership']['status'])
        self.assertIn('101',pub['unmapped_identifiers'])

    def test_publisher_main_vs_reference_special_fails_closed(self):
        res,bundle=scenario()
        next(r for r in bundle['wikipedia']['chapters'] if r['number']=='100')['kind']='special'
        pub=resolved(res,bundle)
        self.assertEqual(('conflict',['100']),(pub['publisher_membership']['status'],pub['publisher_membership']['conflicts']))
        self.assertIn('REFERENCE_CONFLICT',[h['code'] for h in publication_holes(pub,res.primary)])

    def test_stale_structure_alone_cannot_supply_closed_membership(self):
        res,bundle=scenario();bundle['wikipedia']['cache_state']='last_known_good'
        pub=resolved(res,bundle)
        self.assertEqual('open',pub['publisher_membership']['status'])
        self.assertEqual(101,pub['logical_chapters'])

    def test_future_final_record_cannot_close(self):
        res,bundle=scenario()
        bundle['publisher_publication']['chapters'][0]['published_at']=4102444800
        pub=resolved(res,bundle)
        self.assertEqual('open',pub['publisher_membership']['status'])
        self.assertEqual(101,pub['logical_chapters'])

    def test_fingerprint_tracks_facts_without_refresh_clock_noise(self):
        value=publisher_value();other=deepcopy(value)
        other['checked_at']='2026-10-07T23:00:00+00:00'
        self.assertEqual(publisher.publisher_fingerprint(value),publisher.publisher_fingerprint(other))
        other['completed']=False
        self.assertNotEqual(publisher.publisher_fingerprint(value),publisher.publisher_fingerprint(other))

    def test_default_orchestration_collects_publisher_evidence(self):
        from test_publication_states import Service
        from ddk_publication import resolve_publication
        res,bundle=scenario();value=bundle.pop('publisher_publication')
        adapter=publisher.PublisherReferenceAdapter(lambda _:self.fail('Unexpected real request'))
        with patch('ddk_publication.ReferenceMetadataService',return_value=Service(bundle)),\
             patch('ddk_publication.PublisherReferenceAdapter',return_value=adapter),\
             patch.object(adapter,'lookup',return_value=value) as lookup:
            pub=resolve_publication(res,[res.primary.result])
        lookup.assert_called_once()
        self.assertEqual('closed',pub['publisher_membership']['status'])
        self.assertIn('publisher_publication',pub['source_fingerprints'])


class PublisherSupplements(unittest.TestCase):
    def test_book_search_requires_exact_typed_work_and_guidebook(self):
        item=dict(isbn='978-4-08-885227-0',item_name='Fixture guide',item_name_2='作品',
            item_name_3='公式ガイドブック',ssid=1,release_date='2026-01-01')
        series=dict(series_name_2='作品',item_kbn='1',label_name='ジャンプコミックス',item_datas=[item])
        html='var ssd = '+json.dumps(dict(datas=[series]))+';'
        evidence=dict(canonical_title='Fixture',canonical_aliases=['作品'])
        self.assertEqual(1,len(publisher.supplementary_books(html,evidence)))
        self.assertEqual([],publisher.supplementary_books(html,dict(canonical_title='Other')))
        series['item_datas'][0]['item_name_2']='作品 外伝'
        self.assertEqual([],publisher.supplementary_books('var ssd = '+json.dumps(dict(datas=[series])),evidence))

    def test_toc_page_is_not_a_canonical_chapter_or_volume(self):
        html='<div>●描きおろし漫画 Fixture Coronation　303<br>・読切版 Fixture　156<br>目次 4</div>'
        rows=publisher.supplementary_contents(html,dict(isbn='978-4-08-885227-0'),'https://www.shueisha.co.jp/books/items/contents.html?jdcn=123456789012345')
        self.assertEqual(['special','pilot_or_oneshot'],[r['publication_role'] for r in rows])
        self.assertTrue(all(r['canonical_identifier'] is None and r['acquisition_binding']=='unresolved' for r in rows))
        self.assertTrue(all('volume' not in r and 'key' not in r for r in rows))

    def test_script_cannot_supply_fake_toc(self):
        rows=publisher.supplementary_contents('<script>読切版 Fake 156</script><div>Contents 4</div>',dict(isbn='978-4-08-885227-0'),'official')
        self.assertEqual([],rows)


if __name__=='__main__':unittest.main()
