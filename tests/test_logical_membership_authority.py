"""Acquisition identifiers cannot extend an established publication model."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_publication_states import fixture, resolved, stored
from ddk_publication import publication_holes
from ddk_review import health
from mangaanka_database_development_kit import DB
from ddk_publisher_reference import CONTRACT


def publisher_value(final='100', completed=True):
    stamp = datetime.now(timezone.utc)
    record = dict(key=final, publisher_record_id=9000, title='Final page',
                  published_at=int(stamp.timestamp())-3600, label='#'+final)
    return dict(contract=CONTRACT,status='current',source='mangaplus',
        canonical_work_id='fixture:serialized', edition='standard',language='en',
        publication_id='5000',url='https://mangaplus.shueisha.co.jp/titles/5000',
        payload_sha256='a'*64,title='Serialized fixture',creator='Fixture Author',
        checked_at=stamp.isoformat(), completed=completed, release_schedule=8 if completed else 2,
        chapters=[record],final_chapter=record)


def scenario(extra='101', independently_supported=False, kind='chapter'):
    res, bundle = fixture(extras=False)
    template = bundle['wikipedia']['chapters'][0]
    bundle['wikipedia']['chapters'] = [dict(template, number=str(n), volume='1',
        kind='chapter', source_record_id='main:'+str(n)) for n in range(1, 101)]
    bundle['wikipedia']['volumes'] = bundle['wikipedia']['volumes'][:1]
    bundle['publisher_publication'] = publisher_value()
    rows = [dict(id='reader:'+str(n), chapter=str(n)) for n in range(1, 101)]
    rows.append(dict(id='reader:'+extra, chapter=extra))
    if independently_supported:
        bundle['wikipedia']['chapters'].append(dict(template, number=extra,
            volume='' if kind == 'uncollected' else '1', kind=kind,
            source_record_id='independent:'+extra))
    primary = replace(res.primary, chapter_records=tuple(rows), chapter_count=len(rows))
    return replace(res, primary=primary, inventories=(primary,)), bundle


class LogicalMembershipAuthority(unittest.TestCase):
    def setUp(self):
        network = patch('urllib.request.urlopen', side_effect=AssertionError('Unexpected network'))
        network.start(); self.addCleanup(network.stop)

    def test_completed_main_set_plus_unsupported_integer_is_acquisition_only(self):
        res, bundle = scenario()
        # A completion assertion is not chapter-level identity. The policy
        # needs neither a numeric ceiling nor an inferred closed-world set.
        res.primary.result['status'] = 'FINISHED'
        pub = resolved(res, bundle)
        self.assertEqual((101, 100, 100, 100, 0), tuple(pub[k] for k in
            ('raw_acquisition_records', 'canonical_main_chapters', 'logical_chapters',
             'mapped_chapters', 'unmapped_chapters')))
        self.assertEqual('101', pub['unclassified_acquisition'][0]['chapter'])
        self.assertEqual('reader:101', pub['projection'][-1]['id'])
        self.assertEqual('unclassified', pub['normalization']['labels'][-1])
        self.assertEqual([], pub['unmapped_identifiers'])
        self.assertEqual([str(n) for n in range(1, 101)], pub['mapped_identifiers'])

    def test_ongoing_supported_new_serialization_is_uncompiled(self):
        res, bundle = scenario(independently_supported=True, kind='uncollected')
        bundle['publisher_publication'] = publisher_value('101', completed=False)
        pub = resolved(res, bundle)
        self.assertEqual((101, 101, 100, 1, 0), tuple(pub[k] for k in
            ('canonical_main_chapters', 'logical_chapters', 'mapped_chapters',
             'uncompiled_chapters', 'unmapped_chapters')))
        self.assertEqual(['101'], pub['uncompiled_identifiers'])

    def test_stale_reference_does_not_suppress_independent_new_provider_membership(self):
        res, bundle = scenario()
        bundle['wikipedia']['cache_state'] = 'last_known_good'
        bundle['publisher_publication'] = publisher_value('101', completed=False)
        rows = tuple(dict(r, volume='1' if r['chapter'] != '101' else '2')
                     for r in res.primary.chapter_records)
        primary = replace(res.primary, chapter_records=rows)
        res = replace(res, primary=primary, inventories=(primary,))
        pub = resolved(res, bundle)
        self.assertEqual(101, pub['canonical_main_chapters'])
        self.assertEqual('main', pub['normalization']['labels'][-1])
        self.assertEqual('2', pub['projection'][-1]['_effective_volume'])

    def test_unsupported_zero_derivation_does_not_expand_logical_model(self):
        res, bundle = scenario(extra='0')
        pub = resolved(res, bundle)
        self.assertEqual('derived_pre_chapter_one', pub['projection'][-1]['_projection_state'])
        self.assertEqual((100, 100, 100), tuple(pub[k] for k in
            ('canonical_main_chapters', 'logical_chapters', 'mapped_chapters')))
        self.assertNotIn('0', pub['mapped_identifiers'])
        self.assertEqual('0', pub['unclassified_acquisition'][0]['chapter'])

    def test_independently_established_main_zero_is_supported(self):
        res, bundle = scenario(extra='0', independently_supported=True)
        pub = resolved(res, bundle)
        self.assertEqual((101, 101, 101), tuple(pub[k] for k in
            ('canonical_main_chapters', 'logical_chapters', 'mapped_chapters')))
        self.assertEqual('main', pub['normalization']['labels'][-1])

    def test_proven_pilot_uses_existing_special_taxonomy(self):
        res, bundle = scenario(extra='0', independently_supported=True, kind='special')
        pub = resolved(res, bundle)
        self.assertEqual((100, 1, 101), tuple(pub[k] for k in
            ('canonical_main_chapters', 'recognized_specials', 'logical_chapters')))
        self.assertEqual('recognized_special', pub['normalization']['labels'][-1])
        self.assertEqual('special', pub['projection'][-1]['type'])

    def test_post_final_provider_artifact_is_retained_without_main_inflation(self):
        res, bundle = scenario(extra='101.1')
        pub = resolved(res, bundle)
        self.assertEqual(100, pub['logical_chapters'])
        self.assertEqual('provider_fractional_candidate', pub['normalization']['labels'][-1])
        self.assertEqual('reader:101.1', pub['projection'][-1]['id'])
        self.assertIn('PROVIDER_FRACTIONAL_CANDIDATE',
                      [h['code'] for h in publication_holes(pub, res.primary)])

    def test_pending_acquisition_still_blocks_normalization_pass(self):
        res, bundle = scenario()
        pub = resolved(res, bundle)
        holes = publication_holes(pub, res.primary)
        self.assertEqual(['UNCLASSIFIED_ACQUISITION'], [h['code'] for h in holes])
        self.assertEqual({'identity':'PASS', 'publication':'PASS',
                          'normalization':'REVIEW', 'acquisition':'PASS'},
                         health(pub, [dict(problem_type=h['code']) for h in holes]))

    def test_no_established_main_model_retains_unverified_acquisition_fallback(self):
        res, bundle = scenario()
        bundle['wikipedia']['chapters'] = []
        bundle['wikipedia']['volumes'] = []
        bundle.pop('publisher_publication')
        pub = resolved(res, bundle)
        self.assertEqual(0, pub['canonical_main_chapters'])
        self.assertEqual(101, pub['logical_chapters'])
        self.assertEqual('unverified', pub['normalization']['status'])
        self.assertEqual({'provisional':101}, pub['normalization']['counts'])

    def test_independent_two_peer_confirmation_can_extend_current_reference(self):
        res, bundle = scenario()
        peers = tuple(replace(res.primary, source_id=source)
                      for source in ('mangapill', 'weebcentral'))
        res = replace(res, inventories=(res.primary, *peers))
        pub = resolved(res, bundle)
        self.assertEqual(101, pub['canonical_main_chapters'])
        self.assertEqual('main', pub['normalization']['labels'][-1])
        self.assertIn('101', pub['unmapped_identifiers'])

    def test_special_only_evidence_does_not_infer_a_complete_main_model(self):
        res, bundle = scenario(extra='0', independently_supported=True, kind='special')
        bundle.pop('publisher_publication')
        bundle['wikipedia']['chapters'] = bundle['wikipedia']['chapters'][-1:]
        pub = resolved(res, bundle)
        self.assertEqual(0, pub['canonical_main_chapters'])
        self.assertEqual('provisional', pub['normalization']['labels'][0])

    def test_disposable_persistence_preserves_all_acquisition_and_no_acceptance(self):
        res, bundle = scenario()
        pub = resolved(res, bundle)
        raw = deepcopy(pub['projection'])
        with tempfile.TemporaryDirectory(prefix='ddk-membership-') as folder:
            db = DB(Path(folder)/'test.db', role='TEST')
            wid, aid = stored(db, pub, res.primary)
            import json
            saved = json.loads(db.audit(aid, wid)['publication_json'])
            self.assertEqual(raw, saved['projection'])
            self.assertEqual(100, saved['logical_chapters'])
            self.assertEqual('NONE', db.acceptance.state(wid))
            with db.con() as con:
                self.assertEqual(8, con.execute('PRAGMA user_version').fetchone()[0])


if __name__ == '__main__':
    unittest.main()
