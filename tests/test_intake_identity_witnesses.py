"""Identity evidence boundaries modeled on sparse catalogs and creator lists."""
from dataclasses import replace
import unittest
from unittest.mock import patch
from mangaanka_search_core.mangak_source import MangaKSource
from mangaanka_search_core.enrichment_model import ExternalMangaCandidate
from mangaanka_search_core.enrichment_matching import enrich_content_results, effective_search_rows
from mangaanka_search_core.reference_integration import canonical_family_publication_context
from mangaanka_search_core.canonical_identity import group_canonical_results, edition_identity
from ddk_catalog import identity_for


def candidate(service, key, **kw):
    return ExternalMangaCandidate(service=service, external_id=key, primary_title='Witness Serial',
        cross_ids={service+'_id':key}, start_year=2020, format='MANGA', **kw)


def witnesses():
    return (candidate('anilist','101',authors=('Alpha Writer','Beta Artist')),
            candidate('kitsu','201',reported_volume_count=29))


def card(source='mangadex', **kw):
    return dict(dict(source_id=source,id=source,title='Witness Serial',author=''), **kw)


def resolve(rows, candidates=None):
    enriched=enrich_content_results(rows,candidates or witnesses())
    overlays={(r['source_id'],r['id']):r for r in enriched}
    return effective_search_rows(rows,overlays)


class IntakeIdentityWitnesses(unittest.TestCase):
    def metadata(self, authors):
        source=MangaKSource()
        with patch.object(source,'_title',return_value=(dict(id='fixture',name='Witness Serial',authors=authors),'https://mangak.io/witness-serial')):
            return source.get_manga('https://mangak.io/witness-serial')

    def test_provider_placeholder_entity_is_not_a_creator(self):
        row=self.metadata([dict(id='writer-alpha',name='Alpha Writer'),dict(id='updating',slug='updating',name='Updating')])
        self.assertEqual('Alpha Writer',row['author'])

    def test_placeholder_only_metadata_yields_missing_creator(self):
        self.assertEqual('',self.metadata([dict(id='updating',name='Updating')])['author'])

    def test_similar_creator_names_are_not_placeholders(self):
        for item in (dict(id='real-artist',name='Updating'),dict(id='updating',name='Updating Artist'),dict(name='Updating')):
            self.assertEqual(item['name'],self.metadata([item])['author'])

    def test_joint_explicit_links_resolve_sparse_ongoing_catalogs(self):
        rows=resolve((card(external_ids={'anilist_id':'101','kitsu_id':'201'}),card('reader')))
        self.assertEqual('anilist:101|kitsu:201',rows[-1]['canonical_work_id'])
        self.assertTrue(canonical_family_publication_context(rows[-1],rows).shareable)

    def test_joint_links_allow_ordinary_completed_count_drift(self):
        a,k=witnesses()
        cs=(replace(a,reported_chapter_count=236,reported_volume_count=27),
            replace(k,reported_chapter_count=232,reported_volume_count=26))
        row=resolve((card(external_ids={'anilist_id':'101','kitsu_id':'201'}),),cs)[0]
        self.assertEqual('high',row['_canonical_identity_confidence'])

    def test_sparse_pair_without_links_stays_ambiguous(self):
        row=resolve((card(author='Alpha Writer',year=2020),))[0]
        self.assertFalse(canonical_family_publication_context(row,(row,)).shareable)

    def test_two_separate_cards_are_not_a_joint_link_witness(self):
        rows=resolve((card(external_ids={'anilist_id':'101'}),
                      card('reader',external_ids={'kitsu_id':'201'})))
        self.assertTrue(all(r['_canonical_identity_confidence']=='ambiguous' for r in rows))

    def test_malformed_links_do_not_bridge_sparse_candidates(self):
        row=resolve((card(author='Alpha Writer',year=2020,external_ids={'anilist_id':'https://anilist.co/manga/101','kitsu_id':'x201'}),))[0]
        self.assertFalse(canonical_family_publication_context(row,(row,)).shareable)

    def test_joint_witness_cannot_override_creator_contradiction(self):
        a,k=witnesses();k=replace(k,authors=('Unrelated Author',))
        row=resolve((card(external_ids={'anilist_id':'101','kitsu_id':'201'}),),(a,k))[0]
        self.assertEqual('ambiguous',row['_canonical_identity_confidence'])

    def test_joint_witness_cannot_merge_pilot_with_serial(self):
        a,k=witnesses();k=replace(k,format='ONE_SHOT',reported_chapter_count=1)
        row=resolve((card(external_ids={'anilist_id':'101','kitsu_id':'201'}),),(a,k))[0]
        self.assertEqual('ambiguous',row['_canonical_identity_confidence'])

    def test_joint_witness_cannot_override_explicit_cross_id_conflict(self):
        a,k=witnesses();a=replace(a,cross_ids={'anilist_id':'101','kitsu_id':'999'})
        row=resolve((card(external_ids={'anilist_id':'101','kitsu_id':'201'}),),(a,k))[0]
        self.assertEqual('ambiguous',row['_canonical_identity_confidence'])

    def test_joint_witness_cannot_merge_different_core_titles(self):
        a,k=witnesses();k=replace(k,primary_title='Unrelated Work')
        row=resolve((card(external_ids={'anilist_id':'101','kitsu_id':'201'}),),(a,k))[0]
        self.assertEqual('ambiguous',row['_canonical_identity_confidence'])

    def test_conflicting_same_service_anchors_remain_ambiguous(self):
        a,k=witnesses();other=replace(a,external_id='102',cross_ids={'anilist_id':'102'})
        rows=resolve((card(external_ids={'anilist_id':'101','kitsu_id':'201'}),
                      card('reader',external_ids={'anilist_id':'102'})),(a,k,other))
        self.assertTrue(all(r['_canonical_identity_confidence']=='ambiguous' for r in rows))

    def test_serial_and_spinoff_alias_do_not_share_a_group_or_identity(self):
        a,k=witnesses();a2=replace(a,external_id='102',primary_title='Witness Serial: Reboot',cross_ids={'anilist_id':'102'})
        # Build distinct native titles with an intentionally contaminated alias.
        spinoff=dict(card('spinoff',external_ids={'anilist_id':'102'}),title='Witness Serial: Reboot',alternate_titles=['Witness Serial'])
        rows=resolve((spinoff,card(external_ids={'anilist_id':'101','kitsu_id':'201'}),card('reader')), (a,k,a2))
        self.assertEqual('anilist:102',rows[0]['canonical_work_id'])
        self.assertEqual('anilist:101|kitsu:201',rows[-1]['canonical_work_id'])
        self.assertFalse(any({r['source_id'] for r in g.results}>={'spinoff','reader'} for g in group_canonical_results(rows)))

    def test_joint_identity_preserves_explicit_colored_edition(self):
        colored=dict(card('colored'),title='Witness Serial (Fan Colored)')
        rows=resolve((card(external_ids={'anilist_id':'101','kitsu_id':'201'}),colored))
        self.assertEqual('fan_color',edition_identity(rows[1]))
        self.assertEqual(2,len(group_canonical_results(rows)))

    def context(self,native):
        row=dict(card('reader'),author=native,canonical_work_id='anilist:101',
                 canonical_title='Witness Serial',canonical_creators=['Alpha Writer','Beta Artist'],
                 canonical_author='Alpha Writer, Beta Artist',_canonical_identity_confidence='high')
        return canonical_family_publication_context(row,(row,))

    def test_reordered_duplicate_creator_list_is_compatible(self):
        ctx=self.context('Alpha Writer, Beta Artist, ARTIST Beta, WRITER Alpha')
        self.assertTrue(ctx.shareable)
        self.assertTrue(identity_for({},ctx.__dict__,'en')['trusted'])

    def test_native_known_creator_subset_is_compatible(self):
        self.assertTrue(self.context('WRITER Alpha').shareable)

    def test_unknown_component_in_creator_list_remains_contradiction(self):
        self.assertFalse(self.context('Alpha Writer, Unrelated Artist').shareable)

    def test_unrelated_creator_remains_contradiction(self):
        self.assertFalse(self.context('Unrelated Author').shareable)

    def test_surname_given_comma_spelling_is_not_a_creator_list(self):
        row=dict(card(),author='Writer, Alpha',canonical_work_id='anilist:101',canonical_title='Witness Serial',
                 canonical_creators=['Alpha Writer'],_canonical_identity_confidence='high')
        self.assertTrue(canonical_family_publication_context(row,(row,)).shareable)

    def test_explicit_creator_array_and_single_name_pseudonym(self):
        row=dict(card(),author='Penname, WRITER Alpha',canonical_work_id='anilist:101',canonical_title='Witness Serial',
                 canonical_creators=['Penname','Alpha Writer'],_canonical_identity_confidence='high')
        self.assertTrue(canonical_family_publication_context(row,(row,)).shareable)
