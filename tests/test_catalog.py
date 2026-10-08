import json
from pathlib import Path
import tempfile
import unittest
from dataclasses import replace

import mangaanka_database_development_kit as ddk
from ddk_catalog import Catalog, compatible, identity_for
from ddk_publication import resolve_publication, publication_holes
from test_publication_audit import resolution, selected, service, FIXTURE


class CatalogCase(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.db=ddk.DB(Path(self.temp.name)/'catalog.db')
        self.db.add_titles(['Example'], 'standard','en')
        self.store=self.db.catalog
        self.res=resolution([{'id':str(n),'chapter':str(n)} for n in range(222,233)])
        self.family=[self.res.primary.result,dict(selected(source='mangadex'),id=FIXTURE['title']['id'])]
        self.refresh()

    def resolve(self,res=None):
        return resolve_publication(res or self.res,self.family,
            service=service({'result':'ok','volumes':{}}),catalog=self.store)

    def refresh(self):
        pub=self.resolve()
        self.db.save_audit(1,{'query':'Example','publication':pub},publication_holes(pub,self.res.primary))
        return pub

    def edit(self, keys=('222',), field='volume', value='24', **kwargs):
        return self.store.preview(1,[{'entity':'chapter','key':k,'field':field,'value':value} for k in keys],**kwargs)

    def test_preview_no_mutation_apply_and_backup(self):
        before=self.db.latest_audit(1)['publication_json']
        preview=self.edit()
        self.assertEqual([],self.store.state(1)['fields'])
        self.store.apply(preview)
        self.assertEqual('24',self.store.rows(1)[0]['effective']['volume'])
        self.assertEqual(before,self.db.latest_audit(1)['publication_json'])
        self.assertEqual(1,len(list((Path(self.temp.name)/'backups').glob('*.db'))))

    def test_bulk_mapping_becomes_pass_and_survives_refresh(self):
        self.store.apply(self.edit(tuple(str(n) for n in range(222,233))))
        pub=self.refresh()
        self.assertEqual(0,pub['unmapped_chapters'])
        self.assertEqual(11,pub['automatic']['unmapped_chapters'])
        self.assertEqual([],publication_holes(pub,self.res.primary))
        self.assertEqual(11,len(self.store.state(1)['fields']))
        volume=next(v for v in pub['manifest']['volumes'] if v['key']=='24')
        self.assertEqual(11,len(volume['chapter_keys']))

    def test_overrides_provider_and_preserves_acquisition(self):
        self.store.apply(self.edit())
        rows=({'id':'222','chapter':'222','volume':'99','page_urls':['original']},)
        res=replace(self.res,primary=replace(self.res.primary,chapter_records=rows))
        pub=self.resolve(res)
        self.assertEqual('24',pub['projection'][0]['_effective_volume'])
        self.assertEqual('mangapill',pub['projection'][0]['_acquisition_provider'])
        self.assertEqual(['original'],pub['projection'][0]['page_urls'])
        self.assertEqual('99',pub['automatic']['projection'][0]['volume'])

    def test_curated_resolves_conflicting_lower_reference_without_rewriting_it(self):
        self.store.apply(self.edit())
        result=resolve_publication(self.res,self.family,
            service=service({'result':'ok','volumes':{}},wiki=(('222','98'),('222','99'))),catalog=self.store)
        self.assertIn('222',result['automatic']['conflicting_chapters'])
        self.assertNotIn('222',result['conflicting_chapters'])
        self.assertEqual('24',result['projection'][0]['_effective_volume'])
        self.assertEqual(['98','99'],[r['volume'] for r in result['references']['wikipedia']['chapters']])

    def test_edition_language_ids_fail_closed(self):
        self.store.apply(self.edit())
        identity=self.store.state(1)['identity']
        for edition in ('official_color','fan_color','omnibus','deluxe','bunkobon','kanzenban'):
            self.assertEqual('incompatible',self.store.lookup(dict(identity,edition=edition))['status'])
        self.assertFalse(compatible(identity,dict(identity,language='ja'))[0])
        self.assertFalse(compatible(identity,dict(identity,external_ids={'kitsu':'wrong'}))[0])
        for context in ('deluxe','omnibus','unrelated-alias'):
            self.assertFalse(compatible(identity,dict(identity,publication_context=context))[0])
        self.assertEqual('absent',self.store.lookup(dict(identity,canonical_work_id='unrelated:123'))['status'])

    def test_undo_redo_persistent_and_history(self):
        self.store.apply(self.edit())
        self.store=Catalog(self.db)
        self.store.reverse(1)
        self.assertEqual([],self.store.state(1)['fields'])
        self.assertEqual('reverted',self.store.history()[0]['state'])
        self.store.reverse(1,redo=True)
        self.assertEqual('24',self.store.rows(1)[0]['effective']['volume'])

    def test_bulk_type_clear_and_reset(self):
        self.store.apply(self.edit(('222','223'),'type','bonus'))
        self.assertEqual('bonus',self.store.rows(1)[1]['effective']['type'])
        self.store.apply(self.edit(value=None))
        self.assertIsNone(self.store.rows(1)[0]['effective']['volume'])
        preview=self.store.preview(1,[{'entity':'chapter','key':'222','field':'volume','reset':True}])
        self.store.apply(preview)
        self.assertNotIn('volume',self.store.rows(1)[0]['curated'])

    def test_stale_preview_rejected(self):
        preview=self.edit();self.refresh()
        with self.assertRaisesRegex(ValueError,'Stale'): self.store.apply(preview)

    def test_stale_undo_preview_rejected_after_new_audit(self):
        self.store.apply(self.edit())
        audit_id=self.store.snapshot(1)[1]
        revision=self.store.state(1)['revision']
        self.refresh()
        with self.assertRaisesRegex(ValueError,'Stale'):
            self.store.reverse(1,expected_revision=revision,expected_audit_id=audit_id)

    def test_curated_creation_is_publication_without_acquisition(self):
        changes=[{'entity':'chapter','key':'233','field':'exists','value':True},
                 {'entity':'chapter','key':'233','field':'volume','value':'24'}]
        preview=self.store.preview(1,changes)
        self.assertEqual([],self.store.state(1)['fields'])
        self.store.apply(preview)
        self.assertTrue(next(r for r in self.store.rows(1) if r['key']=='233')['missing'])
        pub=self.refresh()
        self.assertEqual(12,pub['logical_chapters'])
        self.assertEqual(1,len(pub['curated_publication_records']))
        self.assertIn('233',[r['key'] for r in pub['manifest']['chapters']])
        self.assertIn('233',next(v for v in pub['manifest']['volumes'] if v['key']=='24')['chapter_keys'])
        self.assertIn('ACQUISITION_COVERAGE_GAP',[h['code'] for h in publication_holes(pub,self.res.primary)])
        self.store.reverse(1)
        self.assertFalse(any(r['key']=='233' for r in self.store.rows(1)))

    def test_atomic_batch_and_history_undo_redo(self):
        changes=[{'entity':'chapter','key':str(n),'field':'volume','value':str(24+(n>=228))}
                 for n in range(222,233)]
        preview=self.store.preview(1,changes,operation='Batch: 2 commands')
        self.store.apply(preview)
        self.assertEqual(1,len(self.store.history(1)))
        self.assertEqual(11,len(self.store.state(1)['fields']))
        self.store.reverse(1)
        self.assertEqual([],self.store.state(1)['fields'])
        self.store.reverse(1,redo=True)
        self.assertEqual(11,len(self.store.state(1)['fields']))
        bad=changes+[{'entity':'chapter','key':'999','field':'volume','value':'25'}]
        before=self.store.state(1)
        with self.assertRaises(ValueError): self.store.preview(1,bad)
        self.assertEqual(before,self.store.state(1))

    def test_volume_creation_and_safe_removal(self):
        self.store.apply(self.store.preview(1,[{'entity':'volume','key':'24','field':'exists','value':True},
                                                {'entity':'volume','key':'24','field':'title','value':'Exact'}]))
        self.assertEqual(2,len(self.store.state(1)['fields']))
        self.store.apply(self.store.preview(1,[{'entity':'volume','key':'24','field':'title','reset':True},
                                                {'entity':'volume','key':'24','field':'exists','reset':True}]))
        self.assertEqual([],self.store.state(1)['fields'])

    def test_invalid_and_duplicate_rename_rejected(self):
        for field,value in [('volume','NaN'),('chapter','oops'),('type','unknown')]:
            with self.assertRaises(ValueError): self.edit(field=field,value=value)
        with self.assertRaisesRegex(ValueError,'Duplicate'): self.edit(field='chapter',value='223')

    def test_export_only_trusted_layer(self):
        self.store.apply(self.edit())
        self.store.apply(self.edit(('223',),verification='UNVERIFIED'))
        data=json.loads(self.store.export(1).read_text())
        self.assertEqual(1,len(data['fields']))
        self.assertNotIn('automatic',data)

    def test_schema_reinitialization_retains_curation(self):
        self.store.apply(self.edit())
        restored=ddk.DB(self.db.path)
        self.assertEqual('24',restored.catalog.rows(1)[0]['effective']['volume'])
        self.assertEqual(1,len(restored.catalog.history()))

    def test_verified_override_agrees_but_is_not_deleted(self):
        self.store.apply(self.edit(verification='VERIFIED'))
        rows=({'id':'222','chapter':'222','volume':'24'},)
        res=replace(self.res,primary=replace(self.res.primary,chapter_records=rows))
        pub=self.resolve(res)
        self.db.save_audit(1,{'query':'Example','publication':pub},[])
        self.assertIn('AGREES',self.store.rows(1)[0]['status'])
        self.assertEqual('VERIFIED',self.store.state(1)['fields'][0]['verification'])

    def test_work_and_volume_metadata_export_and_effective_counts(self):
        self.store.apply(self.edit())
        self.store.apply(self.store.preview(1,[
            {'entity':'work','key':'work','field':'canonical_title','value':'Curated title'},
            {'entity':'work','key':'work','field':'aliases','value':['Exact alias']},
            {'entity':'work','key':'work','field':'expected_volumes','value':2},
            {'entity':'volume','key':'24','field':'title','value':'Volume title'},
        ]))
        pub=self.resolve()
        self.assertEqual('Curated title',pub['manifest']['work']['title'])
        self.assertEqual('Volume title',pub['effective_catalog']['volumes']['24']['title'])
        self.assertIn('VOLUME_COUNT_DISAGREEMENT',[h['code'] for h in publication_holes(pub,self.res.primary)])

    def test_canonical_id_contradiction_rejected(self):
        with self.assertRaisesRegex(ValueError,'contradicts'):
            self.store.preview(1,[{'entity':'work','key':'work','field':'external_ids','value':{'kitsu':'999'}}])

    def test_native_format_marker_is_quarantined_without_alias_contamination(self):
        context={'canonical_work_id':'test:1','edition_profile':'standard','shareable':True}
        for marker in ('Omnibus','Deluxe','Bunkobon','Kanzenban'):
            self.assertEqual(marker.lower(),identity_for({'title':'Example '+marker},context,'en')['edition'])
        self.assertEqual('standard',identity_for({'title':'Example','alternate_titles':['Example Deluxe']},context,'en')['edition'])

    def test_redo_branch_and_nonlatest_revert_are_safe(self):
        self.store.apply(self.edit())
        first=self.store.history()[0]['id']
        self.store.apply(self.edit(('223',)))
        with self.assertRaises(ValueError): self.store.reverse(1,change_id=first)
        self.store.reverse(1)
        self.store.apply(self.edit(('224',)))
        with self.assertRaises(ValueError): self.store.reverse(1,redo=True)
        self.assertEqual(1,sum(r['state']=='superseded' for r in self.store.history()))


if __name__=='__main__': unittest.main()
