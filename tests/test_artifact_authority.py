"""Exact current publication identity precedes residual provider syntax."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_publication_states import fixture, resolved
from ddk_chapter_normalization import normalize_acquisition
from ddk_publication import publication_holes
from mangaanka_database_development_kit import DB

PATTERN = json.loads((Path(__file__).parent/'fixtures/artifact_authority_pattern.json').read_text())


def pattern(keys=None, supported=None, volume='1', kind='chapter'):
    res, bundle = fixture(extras=False)
    keys = PATTERN['acquisitions'] if keys is None else keys
    supported = PATTERN['supported_fractions'] if supported is None else supported
    rows = tuple(dict(chapter=k, id='reader:'+k, url='https://reader.invalid/'+k, title='') for k in keys)
    primary = replace(res.primary, source_id='mangapill', source_name='MangaPill',
        chapter_records=rows, chapter_count=len(rows))
    res = replace(res, primary=primary, inventories=(primary,))
    original = bundle['wikipedia']['chapters'][0]
    bundle['wikipedia']['chapters'] = [dict(original, number=k, kind=kind if k in supported else 'chapter',
        volume=volume, source_record_id='publication:'+k, language='en')
        for k in keys if k in supported or k.isdigit()]
    return res, bundle


def labels(publication):
    return dict(zip((r['chapter'] for r in publication['projection']), publication['normalization']['labels']))


class ArtifactAuthority(unittest.TestCase):
    def setUp(self):
        guard = patch('urllib.request.urlopen', side_effect=AssertionError('Unexpected network'))
        guard.start(); self.addCleanup(guard.stop)

    def test_official_fraction_pattern_and_negative_residue(self):
        res,bundle=pattern();pub=resolved(res,bundle)
        for key in PATTERN['supported_fractions']: self.assertEqual('main', labels(pub)[key])
        for key in PATTERN['unsupported_fractions']: self.assertEqual('provider_split_candidate', labels(pub)[key])
        grouped={k for g in pub['normalization']['artifact_groups'] for k in g['identifiers']}
        self.assertEqual(set(PATTERN['unsupported_fractions']), grouped)

    def test_supported_records_have_complete_per_acquisition_provenance(self):
        res,bundle=pattern();pub=resolved(res,bundle)
        proofs=pub['normalization']['publication_identity_rows']
        for acquisition,proof in zip(res.primary.chapter_records,proofs):
            if acquisition['chapter'] not in PATTERN['supported_fractions']: continue
            self.assertEqual(acquisition['chapter'],proof['original_identifier'])
            self.assertEqual(acquisition['id'],proof['record_id'])
            self.assertEqual(acquisition['url'],proof['url'])
            self.assertEqual('mangapill',proof['provider'])
            self.assertEqual(acquisition['chapter'],proof['canonical_identifier'])
            self.assertEqual('main',proof['classification'])
            self.assertEqual('wikipedia',proof['evidence'][0]['source'])
            self.assertEqual('publication:'+acquisition['chapter'],proof['evidence'][0]['source_record_id'])
            self.assertIn('exact',proof['reason'])
        self.assertEqual([(r['id'],r['url']) for r in res.primary.chapter_records],
                         [(r['id'],r['url']) for r in pub['projection']])

    def test_identity_without_volume_does_not_require_membership(self):
        res,bundle=pattern(['58.1','58.2'],['58.1','58.2'],volume='')
        pub=resolved(res,bundle)
        self.assertEqual(['main','main'],pub['normalization']['labels'])
        self.assertEqual(2,pub['canonical_main_chapters'])
        self.assertEqual(0,pub['mapped_chapters'])
        self.assertEqual(2,len(pub['manifest']['runtime_publication']['publication_records']))

    def test_manifest_identity_survives_without_ddk_bare_key_side_channel(self):
        from mangaanka_search_core.publication_manifest import PublicationManifestBuilder
        res,bundle=pattern(['58.1','58.2'],['58.1','58.2'],volume='')
        work=dict(canonical_identity='fixture:serialized', title='Serialized fixture',language='en',
            publication_context=dict(shareable=True,canonical_work_id='fixture:serialized',canonical_title='Serialized fixture'))
        manifest=PublicationManifestBuilder(work,'original').apply_provider_inventory(res.primary.chapter_records,'mangapill').apply_wikipedia(bundle['wikipedia']).build('en')
        result=normalize_acquisition(res.primary.chapter_records,(),manifest,'mangapill')
        self.assertEqual(['main','main'],result['labels'])

    def test_base_does_not_suppress_fractional_main(self):
        res,bundle=pattern(['58','58.1','58.2'],['58.1','58.2'])
        self.assertEqual(['main']*3,resolved(res,bundle)['normalization']['labels'])

    def test_no_independent_evidence_preserves_pairs(self):
        res,bundle=pattern(['100','100.1','100.2'],[])
        self.assertEqual(['main','provider_split_candidate','provider_split_candidate'],resolved(res,bundle)['normalization']['labels'])

    def test_recognized_fractional_special_wins(self):
        res,bundle=pattern(['58','58.1','58.2'],['58.1','58.2'],kind='omake')
        pub=resolved(res,bundle)
        self.assertEqual(['main','recognized_special','recognized_special'],pub['normalization']['labels'])
        self.assertEqual(2,pub['recognized_specials'])
        self.assertFalse(pub['normalization']['artifact_groups'])

    def test_wrong_work_does_not_rescue(self):
        res,bundle=pattern(['58.1','58.2']);bundle['wikipedia']['match']['title']='Other work'
        self.assertEqual(['provider_split_candidate']*2,resolved(res,bundle)['normalization']['labels'])

    def test_wrong_edition_does_not_rescue(self):
        res,bundle=pattern(['58.1','58.2']);bundle['wikipedia']['match']['edition']='omnibus'
        self.assertEqual(['provider_split_candidate']*2,resolved(res,bundle)['normalization']['labels'])

    def test_wrong_language_does_not_rescue(self):
        res,bundle=pattern(['58.1','58.2'])
        for row in bundle['wikipedia']['chapters']: row['language']='ja'
        self.assertEqual(['provider_split_candidate']*2,resolved(res,bundle)['normalization']['labels'])

    def test_stale_failed_and_quarantined_do_not_rescue(self):
        for change in (dict(cache_state='last_known_good'),dict(refresh_status='transient_failure'),
                       dict(status='transient_failure'),dict(collection={'quarantined_groups':[{'display_key':'58.1'}]})):
            res,bundle=pattern(['58.1','58.2']);bundle['wikipedia'].update(change)
            with self.subTest(change=change):
                self.assertEqual(['provider_split_candidate']*2,resolved(res,bundle)['normalization']['labels'])

    def test_ambiguous_taxonomy_does_not_rescue(self):
        res,bundle=pattern(['58.1','58.2'])
        bundle['wikipedia']['chapters'] += [dict(r,kind='omake') for r in bundle['wikipedia']['chapters']]
        self.assertEqual(['provider_split_candidate']*2,resolved(res,bundle)['normalization']['labels'])

    def test_equivalent_acquisitions_count_once_and_preserve_both(self):
        res,bundle=pattern(['58.1','58.1'],['58.1'])
        rows=(dict(res.primary.chapter_records[0],id='first'),dict(res.primary.chapter_records[1],id='second'))
        primary=replace(res.primary,chapter_records=rows);res=replace(res,primary=primary,inventories=(primary,))
        pub=resolved(res,bundle)
        self.assertEqual(['main','duplicate'],pub['normalization']['labels'])
        self.assertEqual(1,pub['logical_chapters'])
        self.assertEqual(['first','second'],[r['id'] for r in pub['projection']])

    def test_range_components_do_not_promote_bundle(self):
        res,bundle=pattern(['1','2','3','1-3'],[])
        self.assertEqual('provider_range_bundle',resolved(res,bundle)['normalization']['labels'][-1])

    def test_unknown_decimal_remains_candidate(self):
        res,bundle=pattern(['58','58.7'],[])
        self.assertEqual('provider_fractional_candidate',resolved(res,bundle)['normalization']['labels'][-1])

    def test_isolated_supported_decimal_beats_generic_fraction_candidate(self):
        res,bundle=pattern(['58','58.7'],['58.7'])
        pub=resolved(res,bundle)
        self.assertEqual('main',pub['normalization']['labels'][-1])
        self.assertFalse(pub['normalization']['artifact_groups'])
        self.assertFalse(any(h['code'] in ('PROVIDER_FRACTIONAL_CANDIDATE','PROVIDER_SPLIT_CANDIDATE')
                             for h in publication_holes(pub,res.primary)))

    def test_exact_fraction_identity_does_not_resolve_volume_disagreement(self):
        res,bundle=pattern(['58.1','58.2'],['58.1','58.2'])
        bundle['mangadex_structure']=dict(status='valid',cache_contract='mangadex-structure-v1',
            canonical_work_id='fixture:serialized',edition_profile='standard',manga_id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
            mappings={'58.1':'2','58.2':'2'},ambiguous_chapters=[],cache_state='refreshed')
        pub=resolved(res,bundle)
        self.assertEqual(['main']*2,pub['normalization']['labels'])
        self.assertEqual(['58.1','58.2'],pub['conflicting_chapters'])
        self.assertEqual(0,pub['mapped_chapters'])
        self.assertEqual(1,sum(h['code']=='REFERENCE_CONFLICT' for h in publication_holes(pub,res.primary)))

    def test_conflicting_acquisitions_keep_review_without_syntax_reclassification(self):
        res,bundle=pattern(['58.1','58.1'],['58.1'])
        primary=replace(res.primary,chapter_records=(dict(res.primary.chapter_records[0],title='one'),
            dict(res.primary.chapter_records[1],title='different')))
        res=replace(res,primary=primary,inventories=(primary,))
        pub=resolved(res,bundle)
        self.assertEqual(['unclassified']*2,pub['normalization']['labels'])
        self.assertFalse(pub['normalization']['artifact_groups'])
        self.assertIn('UNCLASSIFIED_ACQUISITION',[h['code'] for h in publication_holes(pub,primary)])

    def test_v2_label_remains_unclassified(self):
        res,bundle=pattern(['58','58 V2'],[])
        self.assertEqual('unclassified',resolved(res,bundle)['normalization']['labels'][-1])

    def test_bare_key_cannot_promote_fraction(self):
        rows=[dict(id=k,chapter=k) for k in ('58.1','58.2')]
        out=normalize_acquisition(rows,(),SimpleNamespace(chapters=()),'mangapill',reference_chapters={'58.1','58.2'})
        self.assertEqual(['provider_split_candidate']*2,out['labels'])

    def test_code_candidates_contain_only_unresolved_residue(self):
        res,bundle=pattern();pub=resolved(res,bundle)
        with tempfile.TemporaryDirectory() as folder:
            db=DB(Path(folder)/'catalog.db');db.add_titles(['Serialized fixture'],'standard','en');wid=db.works()[0]['id']
            db.save_audit(wid,dict(query='Serialized fixture',publication=pub),publication_holes(pub,res.primary))
            candidates=db.code_review_candidates()
            self.assertEqual(1,len(candidates));self.assertEqual(2,candidates[0]['records'])

    def test_new_audit_reevaluates_identity_and_history_is_immutable(self):
        res,bundle=pattern(['58.1','58.2'],[]);unsupported=resolved(res,bundle)
        _,bundle=pattern(['58.1','58.2'],['58.1','58.2']);supported=resolved(res,bundle)
        bundle['wikipedia']['cache_state']='last_known_good';lost=resolved(res,bundle)
        self.assertEqual(['main']*2,supported['normalization']['labels'])
        self.assertEqual(unsupported['normalization']['labels'],lost['normalization']['labels'])
        with tempfile.TemporaryDirectory() as folder:
            db=DB(Path(folder)/'catalog.db');db.add_titles(['Serialized fixture'],'standard','en');wid=db.works()[0]['id']
            ids=[];old=None
            for pub in (unsupported,supported,lost):
                ids.append(db.save_audit(wid,dict(query='Serialized fixture',publication=pub),publication_holes(pub,res.primary)))
                with db.con() as c:
                    current=dict(c.execute('SELECT * FROM search_audits WHERE id=?',(ids[0],)).fetchone())
                    if old is None: old=current
                    self.assertEqual(old,current)
            self.assertEqual(3,len(set(ids)))

    def test_inputs_not_mutated(self):
        res,bundle=pattern();before=deepcopy(bundle);rows=deepcopy(res.primary.chapter_records)
        resolved(res,bundle)
        self.assertEqual(before,bundle);self.assertEqual(rows,res.primary.chapter_records)


if __name__=='__main__': unittest.main()
