"""Offline end-to-end audits against the live plugin's pure implementation."""
import json
from pathlib import Path
import queue
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from dataclasses import replace
from concurrent.futures import CancelledError

import ddk_publication as publication
import mangaanka_database_development_kit as ddk
from mangaanka_search_core import PLUGIN_ROOT
from mangaanka_search_core.inventory_comparison import SourceInventory
from mangaanka_search_core.search_resolution import SearchResolution
from mangaanka_search_core.reference_integration import ReferenceMetadataService
from mangaanka_search_core.mangadex_structure_reference import MangaDexStructureResolver
from mangaanka_search_core.reference_metadata import PublicationMatch, PublicationChapter, PublicationVolume
from mangaanka_search_core.google_books_reference import GoogleBooksArtworkResolver
from mangaanka_search_core.cross_source_fallback import CrossSourcePlan, PlannedChapter, chapter_identity
from mangaanka_search_core.search_ranking import rank_canonical_results
from mangaanka_search_core.enrichment_matching import effective_search_rows


FIXTURE = json.loads((PLUGIN_ROOT / 'tests/fixtures/patch1c_mangadex_structure.json').read_text(encoding='utf-8'))


def selected(title='The World Is Mine', source='mangapill'):
    return {'source_id': source, 'source_name': source, 'id': 'selected', 'title': title,
            'author': 'Hideki Arai', 'canonical_work_id': 'kitsu:3021',
            'canonical_title': 'The World Is Mine', 'canonical_creators': ['Hideki Arai'],
            '_canonical_identity_confidence': 'high', 'media_type': 'manga'}


def resolution(rows=None, title='The World Is Mine'):
    rows = rows if rows is not None else [{'id': str(n), 'chapter': str(n)} for n in range(1, 164)]
    inv = SourceInventory('mangapill', 'MangaPill', selected(title), 'en', 'original',
                          chapter_count=len(rows), usable=True, complete=True, chapter_records=tuple(rows))
    return SearchResolution((inv.result,), (inv,), primary=inv, language='en', expected_source_ids=('mangapill',))


class EmptyBook:
    def match_publication(self, evidence):
        return PublicationMatch('bookwalker', '', '', 'unmatched', 'offline')


class Wiki:
    pattern_id = 'offline'
    parser_version = '1'
    def __init__(self, pairs=()):
        self.pairs = pairs
    def match_publication(self, evidence):
        return PublicationMatch('wikipedia', 'test', evidence['title'],
                                'confident' if self.pairs else 'unmatched', 'offline')
    def get_structure_page(self, match):
        return 'offline'
    def get_chapter_list(self, match):
        return tuple(PublicationChapter(str(n), volume=str(v)) for n, v in self.pairs)
    def get_volume_list(self, match):
        return tuple(PublicationVolume(str(v)) for v in set(v for n, v in self.pairs))


def service(aggregate=None, wiki=()):
    return ReferenceMetadataService(None, wikipedia=Wiki(wiki), bookwalker=EmptyBook(),
        google_books=GoogleBooksArtworkResolver(enabled=False),
        mangadex_structure=MangaDexStructureResolver(request_json=lambda url:
            FIXTURE['aggregate'] if aggregate is None else aggregate))


def resolve(res=None, svc=None):
    res = res or resolution()
    md = dict(selected(source='mangadex'), id=FIXTURE['title']['id'])
    return publication.resolve_publication(res, [res.primary.result, md], service=svc or service())


class PublicationTests(unittest.TestCase):
    def setUp(self):
        # Any accidental real network call makes offline validation fail.
        self.network = patch('urllib.request.urlopen', side_effect=AssertionError('Unexpected network'))
        self.network.start()
        self.addCleanup(self.network.stop)

    def test_live_modules_not_snapshot(self):
        from mangaanka_search_core import search_resolution, publication_manifest
        for module in (search_resolution, publication_manifest):
            self.assertEqual(PLUGIN_ROOT, Path(module.__file__).parent)

    def test_world_163_chapters_14_derived_volumes_pass(self):
        result = resolve()
        self.assertEqual((163, 14, 163, 0), tuple(result[k] for k in
            ('logical_chapters', 'final_volumes', 'mapped_chapters', 'unmapped_chapters')))
        self.assertEqual(14, result['derived_volumes'])
        self.assertEqual([], publication.publication_holes(result, resolution().primary))
        self.assertEqual({'mangapill'}, {r['_acquisition_provider'] for r in result['projection']})
        self.assertTrue(result['core']['sha256'])

    def test_live_shaped_world_identity_cannot_use_fixture_mapping(self):
        res=resolution()
        res.primary.result.pop('_canonical_identity_confidence')
        res.primary.result.pop('canonical_creators')
        result=publication.resolve_publication(res,[res.primary.result],service=service())
        self.assertEqual('unavailable_identity',result['references']['mangadex_structure']['status'])
        self.assertEqual(0,result['mapped_chapters'])
        self.assertEqual(163,result['unclassified_records'])

    def test_effective_search_rows_enable_trusted_structure_discovery(self):
        raw=[{'source_id':source,'id':str(i),'title':'The World Is Mine','media_type':'manga'}
             for i,source in enumerate(('mangapill','weebcentral','mangak'))]
        overlays={(r['source_id'],r['id']):dict(r,
            canonical_work_id='anilist:31408|kitsu:3021',canonical_title='The World Is Mine',
            work_family_id='the world is mine',external_ids={'anilist':'31408','kitsu':'3021'}) for r in raw}
        family=effective_search_rows(raw,overlays)
        self.assertTrue(all(r.get('_canonical_identity_confidence')=='high' for r in family))
        res=resolution()
        res=replace(res,primary=replace(res.primary,result=family[0]))
        def request(url):
            if '/aggregate' in url: return FIXTURE['aggregate']
            return {'result':'ok','data':[{'id':FIXTURE['title']['id'],
                'attributes':{'title':{'en':'The World Is Mine'},'altTitles':[],'tags':[]},
                'relationships':[]}]}
        svc=ReferenceMetadataService(None,wikipedia=Wiki(),bookwalker=EmptyBook(),
            google_books=GoogleBooksArtworkResolver(enabled=False),
            mangadex_structure=MangaDexStructureResolver(request_json=request))
        result=publication.resolve_publication(res,family,service=svc)
        self.assertEqual('valid',result['references']['mangadex_structure']['status'])
        self.assertEqual((163,14,163),tuple(result[k] for k in ('logical_chapters','final_volumes','mapped_chapters')))

    def test_peer_chapter_sets_block_inflated_selected_inventory_pass(self):
        selected_rows=[{'chapter':str(n)} for n in range(1,5)]
        res=resolution(selected_rows)
        peers=[]
        for source in ('atsu','weebcentral'):
            peers.append(SourceInventory(source,source,selected(source=source),'en','original',
                chapter_count=3,usable=True,complete=True,
                chapter_records=tuple({'chapter':str(n)} for n in range(1,4))))
        res=replace(res,inventories=(res.primary,*peers))
        result=publication.resolve_publication(res,[res.primary.result],
            service=service({'result':'ok','volumes':{}},wiki=tuple((str(n),'1') for n in range(1,5))))
        # A structural mapping on all four would be authoritative. Without it,
        # peer agreement must exclude the unsupported fourth selected row.
        no_reference=publication.resolve_publication(res,[res.primary.result],
            service=service({'result':'ok','volumes':{}}))
        self.assertEqual(4,result['logical_chapters'])
        self.assertEqual(3,no_reference['logical_chapters'])
        self.assertEqual(1,no_reference['unclassified_records'])
        self.assertIn('UNCLASSIFIED_ACQUISITION',
                      [h['code'] for h in publication.publication_holes(no_reference,res.primary)])

    def test_wrong_edition_owns_dependent_mapping_failure(self):
        res=resolution(title='Example Adventure (Fan Colored)')
        result=resolve(res,service({'result':'ok','volumes':{}}))
        self.assertEqual(['WRONG_EDITION_MATCH'],
                         [h['code'] for h in publication.publication_holes(result,res.primary)])

    def test_explicit_nonnumeric_special_remains_in_publication(self):
        res=resolution([{'id':'main','chapter':'1'},
                        {'id':'bonus-1','chapter':'Bonus','type':'extra'}])
        result=resolve(res)
        self.assertEqual(1,result['recognized_specials'])
        self.assertEqual(2,result['logical_chapters'])
        self.assertEqual(0,result['unclassified_records'])

    def test_unmapped_is_one_aggregated_category(self):
        result = resolve(svc=service({'result': 'ok', 'volumes': {}}))
        holes = publication.publication_holes(result, resolution().primary)
        self.assertEqual(['UNMAPPED_CHAPTERS','UNCLASSIFIED_ACQUISITION'], [h['code'] for h in holes])
        self.assertEqual(163, holes[0]['details']['affected'])
        self.assertEqual(163, len(result['unmapped']))

    def test_precedence_provider_then_mangadex_then_wikipedia(self):
        res = resolution([{'chapter': '1', 'volume': '9'}, {'chapter': '2'}, {'chapter': '999'}])
        result = resolve(res, service(wiki=(('1','7'), ('2','7'), ('999','7'))))
        self.assertEqual(['9', '1', '7'], [str(r['_effective_volume']) for r in result['projection']])

    def test_safe_fractional_derivation(self):
        result = resolve(resolution([{'chapter':'1'}, {'chapter':'1.5'}, {'chapter':'0.5'}]))
        self.assertEqual(0, result['unmapped_chapters'])
        self.assertEqual('derived_fractional', result['projection'][1]['_projection_state'])
        self.assertEqual('derived_pre_chapter_one', result['projection'][2]['_projection_state'])

    def test_equivalent_duplicate_chapters_keep_trusted_structure(self):
        res = resolution([{'chapter':'1'}, {'chapter':'1'}])
        result = resolve(res)
        self.assertEqual(0, result['unmapped_chapters'])
        self.assertEqual(1, result['mapped_chapters'])
        self.assertEqual(1, result['duplicate_records'])
        self.assertNotIn('REFERENCE_CONFLICT', [h['code'] for h in publication.publication_holes(result, res.primary)])

    def test_native_resolves_lower_priority_ambiguity(self):
        result = resolve(resolution([{'chapter':'1','volume':'2'}, {'chapter':'1','volume':'2'}]))
        self.assertEqual([], result['conflicting_chapters'])

    def test_wrong_edition_generic_not_title_specific(self):
        res = resolution(title='Example Adventure (Fan Colored)')
        result = resolve(res, service({'result':'ok','volumes':{}}))
        self.assertEqual('fan_color', result['edition'])
        self.assertIn('WRONG_EDITION_MATCH', [h['code'] for h in publication.publication_holes(result, res.primary)])
        self.assertNotIn('WRONG_EDITION_MATCH', [h['code'] for h in publication.publication_holes(result, res.primary, 'fan_color')])

    def test_colored_alias_does_not_change_edition(self):
        res = resolution()
        res.primary.result['alternate_titles'] = ['The World Is Mine (Fan Colored)']
        self.assertEqual('standard', resolve(res)['edition'])

    def test_reference_missing_acquisition_is_reported_without_invention(self):
        res = resolution([{'chapter':'1'}])
        result = resolve(res)
        self.assertEqual(1, result['logical_chapters'])
        self.assertEqual(162, len(result['missing_reference_chapters']))
        self.assertIn('CHAPTER_COUNT_DISAGREEMENT', [h['code'] for h in publication.publication_holes(result,res.primary)])

    def test_volume_units_are_not_chapters(self):
        result = resolve(resolution([{'_unit_kind':'volume','volume':'1','id':'v1'}]))
        self.assertEqual((0,1,0), (result['logical_chapters'],result['final_volumes'],result['unmapped_chapters']))
        self.assertEqual([], result['missing_reference_chapters'])

    def test_cancellation_propagates(self):
        with self.assertRaises(CancelledError):
            publication.resolve_publication(resolution(), (), should_cancel=lambda: True)

    def test_executable_chapter_fallback_uses_plugin_plan_provenance(self):
        first, second = {'id':'one','chapter':'1'}, {'id':'two','chapter':'2'}
        plan = CrossSourcePlan('mangapill','MangaPill','en','original', (
            PlannedChapter('mangapill','MangaPill',first,chapter_identity(first)),
            PlannedChapter('atsu','Atsu',second,chapter_identity(second),'missing_primary'),
        ), ())
        result = resolve(replace(resolution([first]), fallback_plan=plan))
        self.assertEqual(2,result['logical_chapters'])
        self.assertEqual(['mangapill','atsu'],[r['_acquisition_provider'] for r in result['projection']])

    def test_standard_candidate_ranks_before_fan_color(self):
        plain = selected('Example Adventure')
        colored = selected('Example Adventure (Fan Colored)')
        ranked = rank_canonical_results('Example Adventure',[colored,plain],False)
        self.assertEqual('Example Adventure',ranked[0].group.display_title)

    def test_structural_transport_failure_reported_only_when_unmapped(self):
        class FailedService:
            def lookup(self, *args, **kwargs):
                return {'mangadex_structure':{'status':'transient_failure','error':'offline'},
                        'wikipedia':{'status':'unmatched'}}
        res = resolution([{'chapter':'1'}])
        result = resolve(res, FailedService())
        self.assertEqual({'UNMAPPED_CHAPTERS','UNCLASSIFIED_ACQUISITION','SOURCE_FAILURE'},
                         {h['code'] for h in publication.publication_holes(result,res.primary)})
        native = resolution([{'chapter':'1','volume':'1'}])
        self.assertEqual([],publication.publication_holes(resolve(native,FailedService()),native.primary))

    def test_adapter_failure_is_error_but_preserves_provider_evidence(self):
        self._audit(service_error=RuntimeError('reference unavailable'))

    def test_audit_end_to_end_persists_final_result(self):
        self._audit()

    def test_working_set_audit_creates_then_reuses_canonical_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=ddk.DB(Path(tmp)/'working.db',role='TEST')
            first=db.working_sets.create('First')
            second=db.working_sets.create('Second')
            db.working_sets.add_requests(first,['The World Is Mine'])
            db.working_sets.add_requests(second,['The World Is Mine'])
            item_a=db.working_sets.items(first)[0]['working_set_item_uuid']
            item_b=db.working_sets.items(second)[0]['working_set_item_uuid']
            auditor=ddk.SearchAuditor(db,queue.Queue())
            res=resolution()
            with patch.object(auditor,'_parallel_provider_search',return_value=([res.primary.result],{'providers':[]})), \
                 patch.object(ddk.DEFAULT_ENRICHMENT_REGISTRY,'search',return_value=((),{})), \
                 patch.object(ddk,'resolve_search_group',return_value=res), \
                 patch.object(ddk,'resolve_publication',return_value=resolve(res)):
                auditor.audit_one(None,item_uuid=item_a)
                self.assertEqual(1,len(db.works()))
                original_uuid=db.work(1)['work_uuid']
                self.assertEqual('STAGED',db.work(1)['lifecycle_status'])
                self.assertEqual(1,db.working_sets.item(item_a)['pinned_audit_revision'])
                auditor.audit_one(None,item_uuid=item_b)
            self.assertEqual(1,len(db.works()))
            self.assertEqual(original_uuid,db.work(1)['work_uuid'])
            self.assertEqual(1,db.working_sets.item(item_a)['pinned_audit_revision'])
            self.assertEqual(2,db.working_sets.item(item_b)['pinned_audit_revision'])
            self.assertEqual(2,db.latest_audit(1)['audit_revision'])

    def _audit(self, service_error=None):
        with tempfile.TemporaryDirectory() as tmp:
            db = ddk.DB(Path(tmp)/'audit.db')
            db.add_titles(['The World Is Mine'], 'standard','en')
            auditor = ddk.SearchAuditor(db, queue.Queue())
            res = resolution()
            kwargs = {'side_effect':service_error} if service_error else {'return_value':resolve(res)}
            with patch.object(auditor, '_parallel_provider_search', return_value=([res.primary.result],{'providers':[]})), \
                 patch.object(ddk.DEFAULT_ENRICHMENT_REGISTRY, 'search', return_value=((),{})), \
                 patch.object(ddk, 'resolve_search_group', return_value=res), \
                 patch.object(ddk, 'resolve_publication', **kwargs):
                auditor.audit_one(1)
            audit = db.latest_audit(1)
            if service_error:
                self.assertEqual('ERROR',audit['final_state'])
                self.assertIsNone(audit['final_volumes'])
                self.assertEqual('SOURCE_FAILURE',db.holes()[0]['code'])
            else:
                self.assertEqual('PASS',audit['final_state'])
                self.assertEqual(14,audit['final_volumes'])
                self.assertEqual([],db.holes())
            self.assertEqual(163,audit['selected_chapters'])
            db.audit_summary_csv(Path(tmp)/'summary.csv')
            self.assertIn('Final Volumes',(Path(tmp)/'summary.csv').read_text(encoding='utf-8-sig'))


class MigrationTests(unittest.TestCase):
    def test_legacy_database_rows_survive_idempotent_migration(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'legacy.db'
            with sqlite3.connect(path) as con:
                con.executescript(ddk.SCHEMA)
                con.execute("INSERT INTO works(id,input_title,edition,language) VALUES(1,'Existing','standard','en')")
                con.execute("INSERT INTO search_audits(id,work_id,query,workflow,created_at) VALUES(1,1,'Existing','volume','yesterday')")
                con.execute("INSERT INTO audit_holes(audit_id,work_id,code,severity,message,created_at) VALUES(1,1,'REFERENCE_STRUCTURE_NEEDED','warning','legacy','yesterday')")
                con.execute('CREATE TABLE legacy_custom_data(value TEXT)')
                con.execute("INSERT INTO legacy_custom_data VALUES('keep')")
            con.close()
            db=ddk.DB(path,migrate_schema8=True)
            db.init()
            self.assertIsNone(db.latest_audit(1)['final_state'])
            self.assertEqual('RERUN REQUIRED',ddk.App.audit_state(None,db.works()[0]))
            self.assertEqual(1,len(db.holes()))
            with db.con() as con:
                self.assertEqual('keep',con.execute('SELECT value FROM legacy_custom_data').fetchone()[0])
                self.assertEqual('ok',con.execute('PRAGMA integrity_check').fetchone()[0])
                self.assertEqual([],con.execute('PRAGMA foreign_key_check').fetchall())


if __name__ == '__main__':
    unittest.main()
