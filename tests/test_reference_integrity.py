"""Final audit propagation, preserved snapshots, and scoped curation controls."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_publication_states import fixture, resolved
from ddk_publication import publication_holes
from ddk_review import health
from mangaanka_database_development_kit import DB


PATTERN = json.loads((Path(__file__).parent/'fixtures/reference_integrity_pattern.json').read_text(encoding='utf-8'))


def shaped(disagree=True, native=None):
    res, bundle = fixture(extras=False)
    rows = [dict(id='reader:'+str(n), chapter=str(n), title='Chapter '+str(n))
            for n in range(1, PATTERN['main_count']+1)]
    rows += [dict(id='reader:'+k, chapter=k) for k in PATTERN['provider_artifacts']]
    base = {str(n): str(min(PATTERN['volume_count'], 1+(n-1)//10))
            for n in range(1, PATTERN['main_count']+1)}
    md = dict(base)
    wiki = dict(base)
    for key, values in PATTERN['disagreements'].items():
        wiki[key] = values['wikipedia']
        md[key] = values['mangadex'] if disagree else values['wikipedia']
        if native: next(r for r in rows if r['chapter']==key)['volume'] = native[key]
    primary = replace(res.primary, source_id='mangapill', source_name='MangaPill',
        chapter_records=tuple(rows), chapter_count=len(rows))
    res = replace(res, primary=primary, inventories=(primary,))
    original = bundle['wikipedia']['chapters'][0]
    bundle['wikipedia']['chapters'] = [dict(original, number=k, volume=v, source_record_id='wiki:'+k)
                                     for k,v in wiki.items()]
    bundle['wikipedia']['chapters'].append(dict(original, number=PATTERN['missing_special'],
        kind='extra', volume='1', source_record_id='extra'))
    bundle['wikipedia']['volumes'] = [dict(number=str(n), confidence='explicit', release_status='released')
                                     for n in range(1, PATTERN['volume_count']+1)]
    bundle['mangadex_structure'] = dict(status='valid', cache_contract='mangadex-structure-v1',
        canonical_work_id='fixture:serialized', edition_profile='standard',
        manga_id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', mappings=md,
        ambiguous_chapters=[], cache_state='refreshed')
    return res, bundle


class ReferenceIntegrityAudit(unittest.TestCase):
    def setUp(self):
        guard = patch('urllib.request.urlopen', side_effect=AssertionError('Unexpected network'))
        guard.start(); self.addCleanup(guard.stop)

    def test_reported_chainsaw_pattern_is_230_of_232_and_only_four_projection_changes(self):
        res, bundle = shaped()
        # Uncontested MD control recreates the previously selected bad volumes
        # without keeping a second production implementation in the tests.
        old_bundle = deepcopy(bundle)
        old_bundle['wikipedia']['chapters'] = [r for r in old_bundle['wikipedia']['chapters']
            if r['number'] not in PATTERN['disagreements']]
        old = resolved(res, old_bundle)
        self.assertEqual(232,old['mapped_main_chapters'])
        self.assertEqual(['20','1','20','20'], [r['_effective_volume'] for r in old['projection']
            if r['chapter'] in ('203','232','203.1','203.2')])
        new = resolved(res, bundle)
        self.assertEqual((232,230,2), (new['canonical_main_chapters'],new['mapped_main_chapters'],new['unmapped_chapters']))
        self.assertEqual(['203','232'], new['conflicting_chapters'])
        changed = [a['chapter'] for a,b in zip(old['projection'],new['projection'])
                   if a.get('_effective_volume')!=b.get('_effective_volume')]
        self.assertEqual(['203','232','203.1','203.2'], changed)
        holes = publication_holes(new, res.primary)
        self.assertEqual(1, sum(h['code']=='REFERENCE_CONFLICT' for h in holes))
        states = health(new, [dict(problem_type=h['code']) for h in holes])
        self.assertEqual(dict(identity='PASS',publication='REVIEW',normalization='REVIEW',acquisition='PARTIAL'),
                         {k:states[k] for k in ('identity','publication','normalization','acquisition')})
        self.assertEqual([(r['id'],r['chapter']) for r in res.primary.chapter_records],
                         [(r['id'],r['chapter']) for r in new['projection']])

    def test_provider_authority_preserves_both_choices(self):
        for native in ({'203':'22','232':'24'}, {'203':'20','232':'1'}):
            res,bundle=shaped(native=native)
            new=resolved(res,bundle)
            self.assertEqual([], new['conflicting_chapters'])
            for key, volume in native.items():
                row=next(r for r in new['projection'] if r['chapter']==key)
                self.assertEqual(volume,row['_effective_volume'])
                self.assertEqual('provider_explicit',row['_projection_state'])

    def test_reviewed_and_verified_curation_resolve_effective_not_automatic_conflicts(self):
        res,bundle=shaped()
        for verification in ('REVIEWED','VERIFIED'):
            fields=[dict(entity='chapter',record_key=k,field='volume',value=v['wikipedia'],verification=verification)
                    for k,v in PATTERN['disagreements'].items()]
            catalog=SimpleNamespace(lookup=lambda *args:dict(status='matched',work_id=1,revision=1,fields=fields))
            new=resolved(res,bundle,catalog=catalog)
            self.assertEqual([],new['conflicting_chapters'])
            self.assertEqual(['203','232'],new['automatic']['conflicting_chapters'])
            self.assertEqual(2,len(new['automatic']['reference_conflicts']))
            self.assertEqual({'curated_database'}, {c['resolved_by'] for c in new['reference_conflicts']})
            self.assertEqual(232,new['mapped_main_chapters'])
            holes=publication_holes(new,res.primary)
            self.assertEqual('PASS',health(new,[dict(problem_type=h['code']) for h in holes])['publication'])
            for key in PATTERN['disagreements']:
                self.assertEqual('curated_database',next(r for r in new['projection'] if r['chapter']==key)['_volume_source'])

    def test_persisted_conflict_blocks_acceptance_and_preserves_old_audit(self):
        res, clean_bundle=shaped(False)
        clean=resolved(res,clean_bundle)
        _, conflict_bundle=shaped()
        conflict=resolved(res,conflict_bundle)
        with tempfile.TemporaryDirectory() as folder:
            db=DB(Path(folder)/'catalog.db')
            db.add_titles(['Serialized fixture'],'standard','en');wid=db.works()[0]['id']
            with db.con() as c:
                c.execute('UPDATE works SET canonical_work_id=? WHERE id=?',('fixture:serialized',wid))
            def save(pub):
                return db.save_audit(wid,dict(query='Serialized fixture',workflow='volume',
                    match_title='Serialized fixture',publication=pub),publication_holes(pub,res.primary))
            first=save(clean)
            with db.con() as c: previous=dict(c.execute('SELECT * FROM search_audits WHERE id=?',(first,)).fetchone())
            second=save(conflict)
            self.assertGreater(second,first)
            with db.con() as c:
                self.assertEqual(previous,dict(c.execute('SELECT * FROM search_audits WHERE id=?',(first,)).fetchone()))
                self.assertEqual(8,c.execute('PRAGMA user_version').fetchone()[0])
            evaluation=db.acceptance.evaluate(wid)
            self.assertTrue(evaluation['blockers'])
            self.assertTrue(any('conflict' in s.lower() or 'unmapped' in s.lower() or 'publication' in s.lower()
                                for s in evaluation['blockers']))
            self.assertEqual(['203','232'],json.loads(db.latest_audit(wid)['publication_json'])['conflicting_chapters'])

    def test_clean_world_control_remains_pass(self):
        from test_publication_audit import resolve, resolution
        p=resolve()
        self.assertEqual((163,14,163,0),(p['logical_chapters'],p['final_volumes'],p['mapped_chapters'],p['unmapped_chapters']))
        self.assertEqual([],publication_holes(p,resolution().primary))


if __name__=='__main__': unittest.main()
