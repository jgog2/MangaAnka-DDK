"""Scoped publisher language-family authority, never fuzzy creator matching."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import json
import unittest
from unittest.mock import patch

import ddk_publisher_reference as p
from test_publisher_reference import message

EVIDENCE=dict(canonical_work_id='fixture:creator',canonical_title='Fixture work',
    creators=['Kouhei Fixture'],creator_aliases=[],canonical_aliases=[],
    identity_confidence='high',edition_profile='standard',requested_language='en')


def row(ident=1,creator='Kohei Fixture',language=0,name='Fixture work'):
    return dict(id=ident,title=name,creator=creator,language=language)


def encoded(r):
    return message((1,r['id']),(2,r['title']),(3,r['creator']),(7,r['language']))


def fixtures(primary=None,secondary=None,links=None,secondary_links=None,extra=()):
    primary=primary or row();secondary=secondary or row(2,'Kōhei Fixture',1)
    links=links if links is not None else [(1,0),(2,1)]
    secondary_links=secondary_links if secondary_links is not None else links
    listing=message((1,message((25,message((1,message(*[(2,encoded(r)) for r in
        (primary,secondary,*extra)])))))))
    def detail(r,ls):
        chapter=message((1,r['id']),(2,100+r['id']),(3,'#4'),(4,'No. 4: Story'),(6,1700000000))
        return message((1,message((8,message((1,encoded(r)),(10,chapter),
            (32,message((1,8))),*[(27,message((1,i),(2,lang))) for i,lang in ls])))))
    return listing,{primary['id']:detail(primary,links),secondary['id']:detail(secondary,secondary_links)}


class PublisherCreatorEquivalence(unittest.TestCase):
    def setUp(self):
        guard=patch('urllib.request.urlopen',side_effect=AssertionError('Unexpected network'))
        guard.start();self.addCleanup(guard.stop)

    def lookup(self,**kwargs):
        listing,details=fixtures(**kwargs);requests=[]
        def read(url):
            from urllib.parse import urlsplit,parse_qs
            requests.append(url)
            return listing if 'allV2' in url else details[int(parse_qs(urlsplit(url).query)['title_id'][0])]
        value=p.PublisherReferenceAdapter(read).lookup(EVIDENCE)
        return value,requests

    def current(self,value,**context_changes):
        context=dict(canonical_title=EVIDENCE['canonical_title'],canonical_aliases=[],
            canonical_creators=EVIDENCE['creators'],canonical_creator_aliases=[])
        context.update(context_changes)
        return p.current_evidence(value,dict(trusted=True,canonical_work_id='fixture:creator',
            edition='standard',language='en'),context=context)

    def test_reciprocal_publisher_family_proves_scoped_macron_equivalence(self):
        value,requests=self.lookup()
        self.assertEqual('current',value['status']);self.assertEqual(3,len(requests))
        self.assertTrue(self.current(value))
        self.assertEqual('Kohei Fixture',value['creator'])
        self.assertEqual(2,value['creator_equivalence']['secondary']['id'])

    def test_no_secondary_language_chapters_or_false_final_boundary(self):
        value,_=self.lookup()
        self.assertEqual([101],[r['publisher_record_id'] for r in value['chapters']])
        self.assertNotIn('final_chapter',value)

    def test_global_short_vowel_matching_remains_rejected(self):
        self.assertFalse(p.creators_match('Kohei Fixture',EVIDENCE))

    def test_missing_reverse_link_fails_closed(self):
        self.assertNotEqual('current',self.lookup(secondary_links=[(2,1)])[0]['status'])

    def test_wrong_link_language_fails_closed(self):
        self.assertNotEqual('current',self.lookup(links=[(1,0),(2,2)])[0]['status'])

    def test_missing_primary_link_fails_closed(self):
        self.assertNotEqual('current',self.lookup(links=[(2,1)])[0]['status'])

    def test_no_explicit_macron_authority_fails_closed(self):
        self.assertNotEqual('current',self.lookup(secondary=row(2,'Kouhei Fixture',1))[0]['status'])

    def test_other_creator_not_macron_equivalence(self):
        self.assertNotEqual('current',self.lookup(primary=row(creator='Other Fixture'))[0]['status'])

    def test_secondary_title_must_match_exact_trusted_work(self):
        self.assertNotEqual('current',self.lookup(secondary=row(2,'Kōhei Fixture',1,'Fixture sequel'))[0]['status'])

    def test_multiple_english_work_candidates_remain_ambiguous(self):
        self.assertNotEqual('current',self.lookup(extra=(row(3),))[0]['status'])

    def test_multiple_macron_authorities_remain_ambiguous(self):
        self.assertNotEqual('current',self.lookup(extra=(row(3,'Kōhei Fixture',2),))[0]['status'])

    def test_normal_exact_creator_keeps_two_request_path(self):
        value,requests=self.lookup(primary=row(creator='Kouhei Fixture'))
        self.assertEqual('current',value['status']);self.assertEqual(2,len(requests))
        self.assertNotIn('creator_equivalence',value)

    def test_catalog_detail_creator_inconsistency_rejected(self):
        listing,details=fixtures();_,bad=fixtures(primary=row(creator='Other Fixture'))
        details[1]=bad[1]
        def read(url):return listing if 'allV2' in url else details[1 if 'title_id=1&' in url else 2]
        self.assertNotEqual('current',p.PublisherReferenceAdapter(read).lookup(EVIDENCE)['status'])

    def test_stored_proof_cannot_be_reused_for_another_creator(self):
        value,_=self.lookup();self.assertFalse(self.current(value,canonical_creators=['Other Author']))

    def test_stored_primary_identity_must_equal_observation(self):
        value,_=self.lookup();value['creator']='Other Fixture'
        self.assertFalse(self.current(value))

    def test_stored_secondary_hash_and_url_are_required(self):
        for field,replacement in (('payload_sha256','bad'),('url','https://example.com')):
            value,_=self.lookup();value['creator_equivalence']['secondary'][field]=replacement
            with self.subTest(field=field):self.assertFalse(self.current(value))

    def test_primary_payload_hash_must_equal_parent(self):
        value,_=self.lookup();value['creator_equivalence']['primary']['payload_sha256']='b'*64
        self.assertFalse(self.current(value))

    def test_secondary_identity_cannot_equal_primary(self):
        value,_=self.lookup();value['creator_equivalence']['secondary']['id']=1
        self.assertFalse(self.current(value))

    def test_stored_duplicate_conflicting_language_link_rejected(self):
        value,_=self.lookup();value['creator_equivalence']['primary']['language_links'].append(dict(id=2,language=2))
        self.assertFalse(self.current(value))

    def test_stored_unilateral_or_inconsistent_links_rejected(self):
        value,_=self.lookup();value['creator_equivalence']['secondary']['language_links']=[]
        self.assertFalse(self.current(value))

    def test_stale_equivalence_cannot_make_stale_publisher_current(self):
        value,_=self.lookup();value['checked_at']='2020-01-01T00:00:00+00:00'
        self.assertFalse(self.current(value))

    def test_fingerprint_tracks_equivalence_provenance(self):
        value,_=self.lookup();other=deepcopy(value)
        other['creator_equivalence']['secondary']['payload_sha256']='b'*64
        self.assertNotEqual(p.publisher_fingerprint(value),p.publisher_fingerprint(other))

    def test_absent_equivalence_keeps_existing_fingerprint(self):
        import hashlib
        value,_=self.lookup(primary=row(creator='Kouhei Fixture'))
        facts={key:value.get(key) for key in ('contract','status','source','canonical_work_id',
            'edition','language','publication_id','url','title','creator','release_schedule',
            'completed','chapters','final_chapter','supplementary_publications')}
        expected=hashlib.sha256(json.dumps(facts,sort_keys=True,ensure_ascii=False).encode('utf-8')).hexdigest()
        self.assertEqual(expected,p.publisher_fingerprint(value))

    def test_malformed_stored_proofs_fail_closed(self):
        for proof in (None,[],{},dict(primary=[],secondary={}),dict(primary={},secondary='bad')):
            value,_=self.lookup();value['creator_equivalence']=proof
            with self.subTest(proof=proof):self.assertFalse(self.current(value))

    def test_captured_official_language_family(self):
        root=Path(__file__).parent/'fixtures'/'publisher_creator'
        listing=(root/'catalog.bin').read_bytes()
        def read(url):
            return listing if 'allV2' in url else (root/('200019.bin' if '200019' in url else '100017.bin')).read_bytes()
        evidence=dict(EVIDENCE,canonical_title='My Hero Academia',creators=['Kouhei Horikoshi'],
            canonical_work_id='fixture:captured-mha')
        value=p.PublisherReferenceAdapter(read).lookup(evidence)
        self.assertEqual('current',value['status']);self.assertEqual('100017',value['publication_id'])
        self.assertEqual('Kohei Horikoshi',value['creator'])
        self.assertNotIn('final_chapter',value)


if __name__=='__main__':unittest.main()
