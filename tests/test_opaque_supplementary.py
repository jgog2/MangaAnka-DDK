"""Opaque identity authority is independent of numeric chapter projection."""
from copy import deepcopy
from dataclasses import asdict, replace
import unittest

from ddk_supplementary import (Scope, identity_from_observation, project_supplements,
                               collect_supplements, empty_projection)


SCOPE = Scope('fixture:work', 'standard', 'en')
IDENTITY = dict(trusted=True, canonical_work_id=SCOPE.work, edition='standard', language='en')


def observation(title='A bonus', language='en', publication='978-4-08-885227-0'):
    return dict(scope=asdict(Scope(SCOPE.work, 'standard', language)), publisher='shueisha',
        publication_id='isbn:'+publication, publication_title='Official book', story_title=title,
        original_label=title, kind='special', source_url='https://www.shueisha.co.jp/books/items/contents.html?isbn='+publication,
        captured_at='2026-10-07T12:00:00+00:00', payload_sha256='a'*64,
        evidence_type='official_toc', confidence='explicit', locator='page 303')


def acquired(ident='reader-one', label='393'):
    return dict(id=ident, chapter=label, url='https://example.org/'+ident, source_id='fixture',
                language='en', edition='standard')


GUARD = dict(database_uuid='fixture-db', audit_id=1, audit_revision=2, database_revision='a1-e0-d0-w1')


def binding(ident, row=None):
    row = row or acquired()
    return dict(supplement_id=ident.opaque_id, scope=asdict(SCOPE), provider=row['source_id'],
        record_id=row['id'], original_label=row['chapter'], url=row['url'],
        method='reviewed_exact', verification='VERIFIED', review_guard=GUARD.copy(),
        reviewer='Fixture review', note='Complete contents compared against official publication.',
        source_url=ident.provenance.source_url, captured_at=ident.provenance.captured_at,
        publication_sha256='a'*64, acquisition_sha256='b'*64)


def membership(ident, relation='separate_publication', volume=None):
    return dict(supplement_id=ident.opaque_id, scope=asdict(SCOPE), relation=relation,
        publication_id=ident.publication_id, volume=volume, provenance=asdict(ident.provenance))


class OpaqueIdentity(unittest.TestCase):
    def test_stable_and_page_positions_are_not_identity(self):
        first=identity_from_observation(observation(), SCOPE)
        other=observation();other.update(locator='page 999', captured_at='2026-10-08T00:00:00+00:00', payload_sha256='b'*64)
        self.assertEqual(first.opaque_id, identity_from_observation(other,SCOPE).opaque_id)
        self.assertTrue(first.opaque_id.startswith('supplement:'))

    def test_work_edition_language_and_story_are_distinct(self):
        first=identity_from_observation(observation(),SCOPE)
        for field,value in [('work','other:work'),('edition','deluxe'),('language','ja')]:
            item=observation();item['scope'][field]=value
            scope=Scope(**item['scope'])
            self.assertNotEqual(first.opaque_id,identity_from_observation(item,scope).opaque_id)
        self.assertNotEqual(first.opaque_id,identity_from_observation(observation('Another bonus'),SCOPE).opaque_id)

    def test_reject_untrusted_source_scope_hash_or_empty_title(self):
        for changes in (dict(source_url='https://fake.example/book'),dict(payload_sha256='bad'),
                        dict(publisher='unknown'),dict(story_title=''),dict(confidence='candidate'),
                        dict(evidence_type='ocr'),dict(captured_at='invalid')):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                identity_from_observation(dict(observation(),**changes),SCOPE)
        with self.assertRaises(ValueError):identity_from_observation(observation(),Scope('other','standard','en'))

    def test_legacy_empty_is_readable(self):
        self.assertEqual(empty_projection(),collect_supplements({},[],IDENTITY))

    def test_repeated_capture_changes_provenance_not_identity_or_count(self):
        first=identity_from_observation(observation(),SCOPE)
        second=identity_from_observation(dict(observation(),captured_at='2026-10-08T00:00:00+00:00',payload_sha256='b'*64),SCOPE)
        result=project_supplements([first,second],[],[],[],SCOPE)
        self.assertEqual(1,result['summary']['recognized'])
        self.assertEqual('unresolved',result['identities'][0]['acquisition_state'])

    def test_dataclass_does_not_bypass_consumer_validation(self):
        first=identity_from_observation(observation(),SCOPE)
        result=project_supplements([replace(first,opaque_id='supplement:fake')],[],[],[],SCOPE)
        self.assertEqual(0,result['summary']['recognized']);self.assertTrue(result['diagnostics'])

    def test_foreign_work_identity_is_not_projected(self):
        raw=observation();raw['scope']['work']='other:work'
        ident=identity_from_observation(raw,Scope(**raw['scope']))
        self.assertEqual(0,project_supplements([ident],[],[],[],SCOPE)['summary']['recognized'])

    def test_related_work_requires_distinct_canonical_target(self):
        raw=dict(observation(),publication_role='related_work')
        with self.assertRaises(ValueError):identity_from_observation(raw,SCOPE)
        with self.assertRaises(ValueError):identity_from_observation(dict(raw,related_work_id=SCOPE.work),SCOPE)
        ident=identity_from_observation(dict(raw,related_work_id='fixture:spin-off'),SCOPE)
        result=project_supplements([ident],[],[],[membership(ident,'related_work')],SCOPE)
        self.assertEqual('fixture:spin-off',result['identities'][0]['memberships'][0]['related_work_id'])
        self.assertEqual(0,result['summary']['standard_volume_memberships'])

    def test_duplicate_official_headings_are_ambiguous(self):
        first=identity_from_observation(observation(),SCOPE)
        second=identity_from_observation(dict(observation(),locator='page 304'),SCOPE)
        result=project_supplements([first,second],[],[],[],SCOPE)
        self.assertEqual('conflict',result['identities'][0]['acquisition_state'])


class ExactBindings(unittest.TestCase):
    def setUp(self):self.ident=identity_from_observation(observation(),SCOPE)

    def project(self, proofs=(), rows=None, memberships=(), guard=GUARD):
        return project_supplements([self.ident],rows or [acquired()],proofs,memberships,SCOPE,guard)

    def test_identity_does_not_prove_acquisition_or_membership(self):
        row=self.project()['identities'][0]
        self.assertEqual(('unresolved','unresolved'),(row['acquisition_state'],row['membership_state']))

    def test_binding_does_not_prove_membership(self):
        row=self.project([binding(self.ident)])['identities'][0]
        self.assertEqual(('verified','unresolved'),(row['acquisition_state'],row['membership_state']))

    def test_membership_does_not_prove_acquisition(self):
        row=self.project(memberships=[membership(self.ident)])['identities'][0]
        self.assertEqual(('unresolved','separate_publication'),(row['acquisition_state'],row['membership_state']))

    def test_multiple_exact_acquisitions_count_one_identity(self):
        rows=[acquired(),acquired('reader-two','0')]
        result=self.project([binding(self.ident,r) for r in rows],rows)
        self.assertEqual(1,result['summary']['verified_acquired'])
        self.assertEqual(2,len(result['identities'][0]['bindings']))

    def test_original_metadata_is_preserved(self):
        rows=[acquired()];before=deepcopy(rows)
        result=self.project([binding(self.ident)],rows)
        self.assertEqual(before,rows)
        self.assertEqual('393',result['identities'][0]['bindings'][0]['acquisition']['chapter'])

    def test_every_exact_acquisition_field_is_checked(self):
        for field in ('provider','record_id','original_label','url'):
            proof=binding(self.ident);proof[field]='different'
            with self.subTest(field=field):self.assertEqual(0,self.project([proof])['summary']['verified_acquired'])

    def test_stale_unverified_unguarded_and_insufficient_proofs_fail_closed(self):
        for changes in (dict(verification='REVIEWED'),dict(method='ocr'),dict(review_guard={}),
                        dict(acquisition_sha256='bad'),dict(publication_sha256='b'*64),
                        dict(note=''),dict(source_url='https://fake.example')):
            with self.subTest(changes=changes):
                self.assertEqual(0,self.project([dict(binding(self.ident),**changes)])['summary']['verified_acquired'])
        self.assertEqual(0,self.project([binding(self.ident)],guard=None)['summary']['verified_acquired'])

    def test_each_revision_guard_field_is_exact(self):
        for field in GUARD:
            guard=GUARD.copy();guard[field]=str(guard[field])+'changed'
            with self.subTest(field=field):
                self.assertEqual(0,self.project([binding(self.ident)],guard=guard)['summary']['verified_acquired'])

    def test_duplicate_reader_records_are_not_guessed(self):
        self.assertEqual(0,self.project([binding(self.ident)],rows=[acquired(),acquired()])['summary']['verified_acquired'])

    def test_numeric_special_authority_is_not_overridden(self):
        row=acquired();row['_canonical_numeric_special']=True
        self.assertEqual(0,self.project([binding(self.ident)],rows=[row])['summary']['verified_acquired'])

    def test_same_label_is_not_binding(self):
        self.assertEqual(0,self.project(rows=[acquired('different','393')])['summary']['verified_acquired'])

    def test_cross_language_and_edition_fail_closed(self):
        for field,value in [('language','ja'),('edition','deluxe')]:
            row=acquired();row[field]=value
            self.assertEqual(0,self.project([binding(self.ident)],rows=[row])['summary']['verified_acquired'])

    def test_conflicting_bindings_quarantine_both(self):
        other=identity_from_observation(observation('Other bonus'),SCOPE)
        result=project_supplements([self.ident,other],[acquired()],
            [binding(self.ident),binding(other)],[],SCOPE,GUARD)
        self.assertEqual(0,result['summary']['verified_acquired'])
        self.assertTrue(all(r['acquisition_state']=='conflict' for r in result['identities']))

    def test_numeric_main_proof_blocks_supplement_binding(self):
        row=acquired();row['_canonical_main']=True
        self.assertEqual(0,self.project([binding(self.ident)],rows=[row])['summary']['verified_acquired'])

    def test_standard_volume_requires_exact_membership_evidence(self):
        obs=dict(observation(), publication_role='standard_volume', volume='27', evidence_type='official_volume_toc')
        self.ident=identity_from_observation(obs,SCOPE)
        result=self.project([binding(self.ident)],memberships=[membership(self.ident,'standard_volume','27')])
        self.assertEqual('standard_volume',result['identities'][0]['membership_state'])
        self.assertEqual(1,result['summary']['standard_volume_memberships'])
        self.assertNotIn('final_volumes',result)

    def test_conflicting_membership_does_not_choose_a_winner(self):
        obs=dict(observation(), publication_role='standard_volume', volume='27', evidence_type='official_volume_toc')
        first=identity_from_observation(obs,SCOPE)
        second=identity_from_observation(dict(obs,volume='28'),SCOPE)
        result=project_supplements([first,second],[],[],[],SCOPE)
        self.assertEqual('conflict',result['identities'][0]['membership_state'])

    def test_wrong_scope_and_invalid_volume_cannot_establish_membership(self):
        for changes in (dict(volume='27.5'),dict(publication_id='other'),dict(scope=asdict(Scope('other','standard','en')))):
            row=dict(membership(self.ident,'standard_volume','27'),**changes)
            self.assertEqual('unresolved',self.project(memberships=[row])['identities'][0]['membership_state'])


if __name__=='__main__':unittest.main()
