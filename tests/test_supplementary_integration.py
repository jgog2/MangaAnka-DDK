"""Schema-v7 persistence, authority separation and old evidence compatibility."""
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from ddk_supplementary import collect_supplements, publication_supplements, Scope
from ddk_review import review_packet, packet_markdown
from ddk_exports import catalog_context
from ddk_publisher_reference import publisher_fingerprint, supplementary_contents
from mangaanka_database_development_kit import DB
from test_publication_states import fixture, resolved, stored


def book(work='fixture:serialized', language='ja'):
    return dict(canonical_work_id=work, edition='standard', language=language,
        title='Official fixture guidebook', publication_id='isbn:978-4-08-885227-0',
        source_page='https://www.shueisha.co.jp/books/items/contents.html?isbn=978-4-08-885227-0',
        captured_at='2026-10-07T12:00:00+00:00', payload_sha256='a'*64,
        evidence_type='official_toc', publication_role='supplementary_book',
        records=[dict(title='A supplementary story', publication_role='special', book_page=303)])


class SupplementaryIntegration(unittest.TestCase):
    def setUp(self):
        guard=patch('urllib.request.urlopen', side_effect=AssertionError('Unexpected network'))
        guard.start();self.addCleanup(guard.stop)

    def test_real_pipeline_keeps_all_numeric_counts_health_and_code_findings(self):
        from ddk_publication import publication_holes
        from ddk_review import health
        res,bundle=fixture();before=resolved(res,bundle)
        bundle['publisher_publication']=dict(supplementary_publications=[book()])
        after=resolved(res,bundle)
        for key in ('canonical_main_chapters','recognized_specials','logical_chapters','mapped_chapters',
                    'unmapped_chapters','uncompiled_chapters','final_volumes','normalization','projection'):
            self.assertEqual(before[key],after[key],key)
        holes=publication_holes(before,res.primary)
        self.assertEqual(holes,publication_holes(after,res.primary))
        issues=[dict(problem_type=h['code']) for h in holes]
        self.assertEqual(health(before,issues),health(after,issues))
        evidence=after['supplementary_identity']
        self.assertEqual(1,evidence['summary']['recognized'])
        self.assertEqual(0,evidence['summary']['verified_acquired'])
        self.assertEqual('language_or_edition_unverified',evidence['identities'][0]['applicability'])

    def test_schema_seven_immutable_audit_roundtrip_and_exports(self):
        res,bundle=fixture();bundle['publisher_publication']=dict(supplementary_publications=[book()])
        pub=resolved(res,bundle)
        with tempfile.TemporaryDirectory() as folder:
            db=DB(Path(folder)/'catalog.db',role='TEST')
            try:
                wid,aid=stored(db,pub,res.primary)
                state=db.catalog.state(wid)
                c=catalog_context(db,wid)
                expected=db.supplementary.for_audit(wid,db.audit(aid,wid))
                self.assertEqual(expected,c['supplementary_identity'])
                self.assertEqual(pub['supplementary_identity']['summary'],expected['summary'])
                packet=review_packet(db,work_ids=[wid],include_ignored=True)
                self.assertEqual(c['supplementary_identity'],packet['works'][0]['supplementary_identity'])
                self.assertIn('supplement:',packet_markdown(packet))
                with db.con() as con:
                    self.assertEqual(8,con.execute('PRAGMA user_version').fetchone()[0])
                    self.assertEqual('ok',con.execute('PRAGMA integrity_check').fetchone()[0])
                    self.assertEqual(0,con.execute('SELECT count(*) FROM catalog_acceptances').fetchone()[0])
                self.assertEqual(state,db.catalog.state(wid))
                self.assertEqual(expected,json.loads(db.audit(aid,wid)['publication_json'])['supplementary_identity'])
            finally:pass  # DB connections are scoped to individual operations.

    def test_old_audits_are_readable_without_promoting_missing_scope(self):
        res,bundle=fixture();pub=resolved(res,bundle)
        pub.pop('supplementary_identity')
        old=book();old.pop('canonical_work_id');old.pop('captured_at')
        pub['references']['publisher_publication']=dict(supplementary_publications=[old])
        value=publication_supplements(pub)
        self.assertEqual(0,value['summary']['recognized'])
        self.assertTrue(value['diagnostics'])
        self.assertNotIn('supplementary_identity',pub)

    def test_wrong_work_edition_and_untrusted_identity_do_not_ingest(self):
        identity=dict(trusted=True,canonical_work_id='fixture:serialized',edition='standard',language='en')
        for change in (dict(canonical_work_id='other'),dict(edition='fan_color')):
            data=dict(supplementary_publications=[dict(book(),**change)])
            self.assertEqual(0,collect_supplements(data,[],identity)['summary']['recognized'])
        self.assertEqual(0,collect_supplements(dict(supplementary_publications=[book()]),[],dict(identity,trusted=False))['summary']['recognized'])

    def test_capture_clock_does_not_invalidate_semantic_fingerprint(self):
        first=dict(supplementary_publications=[book()]);other=deepcopy(first)
        other['supplementary_publications'][0]['captured_at']='2026-10-08T00:00:00+00:00'
        self.assertEqual(publisher_fingerprint(first),publisher_fingerprint(other))
        other['supplementary_publications'][0]['records'][0]['title']='Different story'
        self.assertNotEqual(publisher_fingerprint(first),publisher_fingerprint(other))

    def test_current_special_one_shot_toc_heading_is_not_missed(self):
        rows=supplementary_contents('<div>描き下ろし特別読切 319</div>',dict(isbn='978-4-08-884309-4'),'official')
        self.assertEqual('pilot_or_oneshot',rows[0]['publication_role'])
        self.assertIsNone(rows[0]['canonical_identifier'])

    def test_open_series_supplements_are_independent_of_completion(self):
        from ddk_publisher_reference import PublisherReferenceAdapter
        from test_publisher_reference import payloads, EVIDENCE
        listing,detail=payloads(schedule=2)
        adapter=PublisherReferenceAdapter(lambda url:listing if 'allV2' in url else detail)
        with patch.object(adapter,'supplements',return_value=[book()]) as supplements:
            value=adapter.lookup(EVIDENCE)
        supplements.assert_called_once()
        self.assertFalse(value['completed']);self.assertNotIn('final_chapter',value)
        self.assertEqual([book()],value['supplementary_publications'])

    def test_captured_batch_observations_stay_unbound(self):
        path=Path(__file__).parent/'fixtures'/'opaque_supplementary'/'observations.json'
        values=json.loads(path.read_text(encoding='utf-8'))
        for subject in values:
            with self.subTest(title=subject['title']):
                value=collect_supplements(dict(supplementary_publications=subject['books']),[],subject['identity'])
                self.assertEqual(subject['expected_recognized'],value['summary']['recognized'])
                self.assertEqual(0,value['summary']['verified_acquired'])
                self.assertTrue(all(r['acquisition_state']=='unresolved' for r in value['identities']))
                self.assertEqual(0,value['summary']['standard_volume_memberships'])

    def test_stored_binding_claim_cannot_authorize_itself(self):
        value=book(language='en');value['bindings']=[dict(verification='VERIFIED',review_guard={'audit_id':1})]
        data=collect_supplements(dict(supplementary_publications=[value]),[],
            dict(trusted=True,canonical_work_id='fixture:serialized',edition='standard',language='en'))
        self.assertEqual(0,data['summary']['verified_acquired'])

    def test_malformed_optional_evidence_never_crashes_audit_projection(self):
        identity=dict(trusted=True,canonical_work_id='fixture:serialized',edition='standard',language='en')
        for value in (None, 'wrong', dict(supplementary_publications=7),
                      dict(supplementary_publications=['wrong']),
                      dict(supplementary_publications=[dict(book(),records='wrong')])):
            self.assertEqual(0,collect_supplements(value,[],identity)['summary']['recognized'])

    def test_stored_projection_is_revalidated_not_trusted_by_contract_label(self):
        identity=dict(trusted=True,canonical_work_id='fixture:serialized',edition='standard',language='en')
        data=collect_supplements(dict(supplementary_publications=[book()]),[],identity)
        data['identities'][0]['identity']['opaque_id']='supplement:fake'
        data['identities'][0]['observations'][0]['opaque_id']='supplement:fake'
        data['summary']['verified_acquired']=1
        result=publication_supplements(dict(catalog_identity=identity,supplementary_identity=data))
        self.assertEqual(0,result['summary']['verified_acquired'])
        self.assertEqual(0,result['summary']['recognized'])
        self.assertTrue(result['diagnostics'])


if __name__=='__main__':unittest.main()
