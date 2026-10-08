"""Explicit provider links resolve identity; inventory counts never choose a work."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mangaanka_search_core.mangadex_source import MangaDexSource
from mangaanka_search_core.enrichment_model import ExternalMangaCandidate
from mangaanka_search_core.enrichment_matching import enrich_content_results
from mangaanka_search_core.canonical_identity import edition_identity, group_canonical_results
from mangaanka_search_core.reference_integration import canonical_family_publication_context
from ddk_catalog import identity_for
from mangaanka_database_development_kit import DB
from test_publication_states import fixture, resolved


TITLE = 'Serialized fixture'
MD_ID = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
LINKS = {'al':'101', 'kt':'201', 'mal':'301'}
IDS = {'anilist_id':'101', 'kitsu_id':'201', 'mal_id':'301'}


def metadata(links=LINKS, title=TITLE):
    return dict(id=MD_ID, attributes=dict(title={'en':title}, year=2015, links=deepcopy(links),
        availableTranslatedLanguages=['en'], contentRating='safe'),
        relationships=[dict(type='author', attributes=dict(name='Fixture Author'))])


def provider(links=LINKS, title=TITLE):
    data = metadata(links, title)
    adapter = MangaDexSource(api_json=lambda *a, **kw:dict(data=[data], total=1))
    row = adapter.search(TITLE, availability_cache={MD_ID:True})['rows'][0]
    return dict(row, source_id='mangadex', source_name='MangaDex', media_type='manga')


def candidates():
    return tuple(ExternalMangaCandidate(service=service, external_id=key, primary_title=TITLE,
        authors=('Fixture Author',) if service == 'anilist' else (),
        start_year=2014 if pilot else 2015, format='ONE_SHOT' if pilot else 'MANGA',
        reported_chapter_count=1 if pilot else 392, reported_volume_count=None if pilot else 38,
        cross_ids={service+'_id':key, **({'mal_id':'302' if pilot else '301'} if service=='anilist' else {})})
        for service, key, pilot in (('anilist','101',False), ('anilist','102',True),
                                   ('kitsu','201',False), ('kitsu','202',True)))


def selected_row():
    return dict(source_id='mangapill', source_name='MangaPill', id='reader', title=TITLE,
                author='', media_type='manga')


class IntakeIdentityLinks(unittest.TestCase):
    def setUp(self):
        guard = patch('urllib.request.urlopen', side_effect=AssertionError('Unexpected network'))
        guard.start(); self.addCleanup(guard.stop)

    def test_search_preserves_only_explicit_supported_ids(self):
        self.assertEqual(IDS, provider()['external_ids'])

    def test_metadata_preserves_same_ids(self):
        adapter = MangaDexSource(api_json=lambda *a, **kw:dict(data=metadata()))
        self.assertEqual(IDS, adapter.get_manga('https://mangadex.org/title/'+MD_ID)['external_ids'])

    def test_absent_and_malformed_links_never_create_ids(self):
        for links in (None, {}, [], '101'):
            with self.subTest(links=links):
                self.assertEqual({}, provider(links).get('external_ids', {}))

    def test_urls_slugs_zero_negative_and_unknown_keys_are_not_inferred(self):
        for value in ('https://anilist.co/manga/101', 'some-work', '0', '-1', '101x', True):
            with self.subTest(value=value):
                self.assertEqual({}, provider({'al':value, 'kt':value, 'mal':value}).get('external_ids', {}))
        self.assertEqual({}, provider({'raw':'101', 'engtl':'201', 'ap':'301'}).get('external_ids', {}))

    def test_numeric_link_ids_use_existing_identity_authority(self):
        self.assertEqual(IDS, provider({'al':101, 'kt':'201', 'mal':'301'}).get('external_ids'))

    def test_direct_links_resolve_both_services_serial_pilot_ambiguity(self):
        rows = enrich_content_results((provider(), selected_row()), candidates())
        self.assertTrue(all(r['canonical_work_id']=='anilist:101|kitsu:201' for r in rows))
        self.assertTrue(all(r['_canonical_identity_confidence']=='high' for r in rows))
        context = canonical_family_publication_context(rows[1], rows)
        self.assertTrue(context.shareable)
        self.assertTrue(identity_for(rows[1], context.__dict__, 'en')['trusted'])

    def test_without_direct_links_existing_ambiguity_stays_fail_closed(self):
        rows = enrich_content_results((provider({}), selected_row()), candidates())
        self.assertEqual('ambiguous', rows[1]['_canonical_identity_confidence'])
        self.assertEqual(['anilist:101','anilist:102','kitsu:201','kitsu:202'],
                         rows[1]['canonical_identity_conflict_candidates'])
        self.assertFalse(canonical_family_publication_context(rows[1],rows).shareable)

    def test_conflicting_direct_service_links_remain_ambiguous(self):
        rows = enrich_content_results((provider({'al':'101','kt':'202'}), selected_row()), candidates())
        self.assertEqual('ambiguous', rows[1]['_canonical_identity_confidence'])
        self.assertNotIn('canonical_work_id',rows[1])

    def test_two_distinct_directly_linked_same_title_works_remain_ambiguous(self):
        other = dict(provider({'al':'102','kt':'202'}), id='bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb')
        rows = enrich_content_results((provider(),other,selected_row()), candidates())
        self.assertEqual('ambiguous', rows[-1]['_canonical_identity_confidence'])

    def test_missing_external_candidate_does_not_promote_link_to_canonical_identity(self):
        row = enrich_content_results((provider(),), ())[0]
        self.assertFalse(canonical_family_publication_context(row,(row,)).shareable)

    def test_native_creator_contradiction_still_prevents_shareable_identity(self):
        row = dict(provider(), author='Unrelated Creator')
        enriched = enrich_content_results((row,), candidates())[0]
        self.assertFalse(canonical_family_publication_context(enriched,(enriched,)).shareable)

    def test_alias_only_unrelated_card_cannot_inherit_direct_anchor(self):
        other = dict(selected_row(), id='unrelated', title='Other work', alternate_titles=[TITLE])
        rows = enrich_content_results((provider(),other), candidates())
        self.assertFalse(rows[-1].get('canonical_work_id'))

    def test_colored_edition_stays_distinct(self):
        colored = provider({}, TITLE+' (Fan Colored)')
        rows = enrich_content_results((provider(),colored), candidates())
        self.assertEqual('fan_color', edition_identity(rows[1]))
        self.assertEqual(2, len(group_canonical_results(rows)))

    def test_disposable_intake_links_and_pins_only_after_trusted_resolution(self):
        base, bundle = fixture(extras=False)
        def publication(links):
            family = enrich_content_results((provider(links),selected_row()), candidates())
            inv = replace(base.primary, source_id='mangapill', source_name='MangaPill', result=family[1])
            return resolved(replace(base, primary=inv, inventories=(inv,)),bundle)
        old, new = publication({}), publication(LINKS)
        with tempfile.TemporaryDirectory() as folder:
            db = DB(Path(folder)/'intake.db',role='TEST')
            ws = db.working_sets.create('Identity offline')
            db.working_sets.add_requests(ws,[TITLE,'Other request'])
            item, unrelated = db.working_sets.items(ws)
            uid = item['working_set_item_uuid']
            def record(pub): return dict(query=TITLE,workflow='volume',match_title=TITLE,
                requested_edition='standard',requested_language='en',publication=pub)
            self.assertIsNone(db.working_sets.persist_item_audit(uid,old['catalog_identity'],record(old),[]))
            db.working_sets.observe_unresolved(uid,record(old),[])
            self.assertFalse(db.working_sets.item(uid)['linked_work_uuid'])
            work_id,audit_id = db.working_sets.persist_item_audit(uid,new['catalog_identity'],record(new),[])
            self.assertEqual(audit_id, db.working_sets.item(uid)['pinned_audit_id'])
            self.assertIsNone(db.working_sets.item(unrelated['working_set_item_uuid'])['pinned_audit_id'])
            self.assertEqual('NONE',db.acceptance.state(work_id))
            self.assertEqual(json.loads(json.dumps(old)), db.working_sets.latest_observation(uid)['record']['publication'])
            with db.con() as con:
                self.assertEqual(8,con.execute('PRAGMA user_version').fetchone()[0])
                self.assertEqual(1,con.execute('SELECT count(*) FROM works').fetchone()[0])
                self.assertEqual(1,con.execute('SELECT count(*) FROM search_audits').fetchone()[0])


if __name__ == '__main__': unittest.main()
