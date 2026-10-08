"""Offline Working Set audit orchestration and per-item rollback controls."""
from contextlib import contextmanager
import json
from pathlib import Path
import queue
import tempfile
import unittest
from unittest.mock import patch

import mangaanka_database_development_kit as ddk
from ddk_exports import working_set_packet, working_set_review_context, working_set_rows
from mangaanka_search_core.inventory_comparison import SourceInventory
from mangaanka_search_core.search_resolution import SearchResolution


TITLES=('MF Ghost','Fire Force','Monster')
CHAPTERS={'MF Ghost':('275',),'Fire Force':('303','304'),'Monster':('1',),
          'New Series':('1',)}


def canonical(title):
    return 'fixture:'+title.casefold().replace(' ','-')


def publication(title):
    chapters=CHAPTERS[title]
    rows=[{'id':number,'chapter':number,'title':'','type':'chapter','volume':'1',
           '_effective_volume':'1','_acquisition_provider':'mangapill'} for number in chapters]
    identity={'canonical_work_id':canonical(title),'edition':'standard','language':'en',
              'publication_context':'','external_ids':{'fixture':canonical(title).split(':',1)[1]},
              'trusted':True}
    result={'status':'complete','edition':'standard','catalog_identity':identity,
            'context':{'shareable':True},'normalization':{'status':'established',
                'labels':['main']*len(rows)},'projection':rows,'logical_chapters':len(rows),
            'mapped_chapters':len(rows),'unmapped_chapters':0,'final_volumes':1,
            'conflicting_chapters':[],
            'raw_acquisition_records':len(rows),'curation_revision':0}
    return dict(result,automatic=dict(result))


@contextmanager
def offline_pipeline(auditor):
    def search(query,language,*_args,**_kwargs):
        row={'source_id':'mangapill','source_name':'MangaPill','id':canonical(query),
             'title':query,'canonical_title':query,'canonical_work_id':canonical(query),
             'canonical_creators':['Fixture Creator'],'author':'Fixture Creator',
             '_canonical_identity_confidence':'high','media_type':'manga',
             'volume_context':[{'provenance':'fixture','reported_total_chapters':len(CHAPTERS[query])}]}
        return [row],{'providers':[{'source_id':'mangapill','status':'complete'}]}
    def resolution(_registry,group_rows,*_args,**_kwargs):
        row=group_rows[0];title=row['title']
        chapters=tuple({'id':number,'chapter':number,'volume':'1'} for number in CHAPTERS[title])
        inventory=SourceInventory('mangapill','MangaPill',row,'en','original',
            chapter_count=len(chapters),usable=True,complete=True,chapter_records=chapters)
        return SearchResolution((row,),(inventory,),primary=inventory,
                                language='en',expected_source_ids=('mangapill',))
    def resolved_publication(resolved,*_args,**kwargs):
        pub=publication(resolved.primary.result['title'])
        target=kwargs['on_identity'](pub['catalog_identity']) if kwargs.get('on_identity') else kwargs.get('catalog_work_id')
        if target:
            from ddk_curated_resolution import apply_curated
            # Use the same effective curation boundary as the production pipeline.
            state=auditor.db.catalog.lookup(pub['catalog_identity'],target)
            pub['curation_revision']=auditor.db.catalog.state(target)['revision']
            for row in pub['projection']:
                for entry in state.get('fields') or []:
                    if entry['entity']=='chapter' and entry['record_key']==row['chapter'] and entry['field']=='volume':
                        row['volume']=row['_effective_volume']=entry['value']
            pub['curated_database']=state
        return pub
    with patch.object(auditor,'_parallel_provider_search',side_effect=search), \
         patch.object(ddk.DEFAULT_ENRICHMENT_REGISTRY,'search',return_value=((),{})), \
         patch.object(ddk,'resolve_search_group',side_effect=resolution), \
         patch.object(ddk,'resolve_publication',side_effect=resolved_publication):
        yield


def counts(db):
    with db.con() as c:
        return (c.execute('SELECT count(*) FROM works').fetchone()[0],
                c.execute('SELECT count(*) FROM search_audits').fetchone()[0])


class WorkingSetAuditRecovery(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.db=ddk.DB(Path(temp.name)/'audit-recovery.db',role='TEST')
        self.auditor=ddk.SearchAuditor(self.db,queue.Queue())
        self.ws=self.db.working_sets.create('Catalog Batch 001')
        self.assertEqual(8,self.db.working_sets.get(self.ws)['schema_version'])

    def intake(self,titles):
        self.db.working_sets.add_requests(self.ws,titles,'standard','en')
        items=self.db.working_sets.items(self.ws)
        for item in items:self.db.working_sets.set_item_status(item['working_set_item_uuid'],'QUEUED')
        return [item['working_set_item_uuid'] for item in items]

    def seed_existing(self):
        self.db.add_titles(TITLES,'standard','en')
        for wid,title in enumerate(TITLES,1):
            self.db.save_audit(wid,{'query':title,'match_title':title,
                'requested_edition':'standard','requested_language':'en',
                'publication':publication(title)},[])
        for wid,numbers,volume in ((1,('275',),'23'),(2,('303','304'),'34')):
            changes=[{'entity':'chapter','key':number,'field':'volume','value':volume,
                      'verification':'VERIFIED'} for number in numbers]
            changes.append({'entity':'evidence','key':f'evidence-{wid}','field':'add',
                            'target_key':numbers[0],'source_name':'Publisher',
                            'source_url':'https://example.org/toc'})
            self.db.catalog.apply(self.db.catalog.preview(wid,changes))

    def test_three_existing_titles_use_queue_path_and_preserve_curation(self):
        self.seed_existing()
        original={r['input_title']:r['work_uuid'] for r in self.db.works()}
        before={wid:(self.db.catalog.state(wid)['revision'],
                     self.db.catalog.state(wid)['fields'],self.db.catalog.evidence(wid),
                     len(self.db.catalog.history(wid))) for wid in (1,2)}
        items=self.intake(TITLES)
        with offline_pipeline(self.auditor):self.auditor.audit_many(items,'volume')
        self.assertEqual((3,6),counts(self.db))
        self.assertEqual(original,{r['input_title']:r['work_uuid'] for r in self.db.works()})
        for item_uuid in items:
            item=self.db.working_sets.item(item_uuid)
            self.assertEqual(original[item['original_query']],item['linked_work_uuid'])
            self.assertEqual(2,item['pinned_audit_revision'])
            self.assertEqual(self.db.latest_audit(item['work_id'])['id'],item['pinned_audit_id'])
            self.assertIn(item['processing_status'],('READY','REVIEW'))
            audit=self.db.latest_audit(item['work_id'])
            self.assertEqual((ddk.VERSION,ddk.SEARCH_CORE_VERSION,8,'standard','en','volume'),
                (audit['ddk_version'],audit['search_core_version'],audit['schema_version'],
                 audit['requested_edition'],audit['requested_language'],audit['workflow']))
            self.assertIsNotNone(audit['created_at'])
        for wid in (1,2):
            state=self.db.catalog.state(wid)
            self.assertEqual(before[wid],(state['revision'],state['fields'],state['evidence'],
                                          len(self.db.catalog.history(wid))))
        effective={r['key']:r['effective']['volume'] for r in self.db.catalog.rows(2)}
        self.assertEqual({'303':'34','304':'34'},effective)
        self.assertEqual('23',self.db.catalog.rows(1)[0]['effective']['volume'])
        self.assertEqual([],self.db.working_sets.audit_errors(self.ws))

    def test_new_title_creates_one_work_after_trusted_identity(self):
        item=self.intake(['New Series'])[0]
        with offline_pipeline(self.auditor):self.auditor.audit_many([item],'volume')
        self.assertEqual((1,1),counts(self.db))
        linked=self.db.working_sets.item(item);work=self.db.work(linked['work_id'])
        self.assertEqual(work['work_uuid'],linked['linked_work_uuid'])
        self.assertEqual(work['work_uuid'],work['conceptual_work_uuid'])
        self.assertEqual(self.db.latest_audit(work['id'])['id'],linked['pinned_audit_id'])
        self.assertEqual(1,len(self.db.working_sets.items(self.ws)))

    def test_untrusted_new_title_stays_intake_without_catalog_work(self):
        item=self.intake(['New Series'])[0]
        unresolved=publication('New Series')
        unresolved['catalog_identity']=dict(unresolved['catalog_identity'],trusted=False)
        with offline_pipeline(self.auditor),patch.object(ddk,'resolve_publication',
             return_value=unresolved):
            self.auditor.audit_many([item],'volume')
        self.assertEqual((0,0),counts(self.db))
        self.assertEqual('REVIEW',self.db.working_sets.item(item)['processing_status'])
        self.assertIsNone(self.db.working_sets.item(item)['linked_work_uuid'])
        self.assertEqual([],self.db.working_sets.audit_errors(self.ws))

    def test_linked_work_identity_conflict_does_not_replace_existing_claim(self):
        self.db.add_titles(['Monster'],'standard','en')
        self.db.save_audit(1,{'query':'Monster','match_title':'Monster',
            'publication':publication('Monster')},[])
        item=self.intake(['Monster'])[0]
        original=self.db.work(1)['work_uuid']
        self.db.working_sets.pin(item,1,self.db.latest_audit(1)['id'])
        mismatch=publication('Monster')
        mismatch['catalog_identity']=dict(mismatch['catalog_identity'],
                                          canonical_work_id='fixture:other-work')
        with offline_pipeline(self.auditor),patch.object(ddk,'resolve_publication',
             return_value=mismatch):
            self.auditor.audit_many([item],'volume')
        self.assertEqual((1,1),counts(self.db))
        self.assertEqual(original,self.db.work(1)['work_uuid'])
        self.assertEqual('REVIEW',self.db.working_sets.item(item)['processing_status'])
        self.assertEqual(1,self.db.working_sets.item(item)['pinned_audit_revision'])

    def test_pin_failure_rolls_back_new_work_and_retry_succeeds(self):
        item=self.intake(['New Series'])[0]
        with offline_pipeline(self.auditor),patch.object(self.db.working_sets,'pin',
             side_effect=RuntimeError('Injected pin failure')):
            self.auditor.audit_many([item],'volume')
        self.assertEqual((0,0),counts(self.db))
        failed=self.db.working_sets.item(item)
        self.assertEqual('ERROR',failed['processing_status'])
        self.assertIsNone(failed['linked_work_uuid']);self.assertIsNone(failed['pinned_audit_id'])
        self.assertEqual('Injected pin failure',self.db.working_sets.audit_errors(self.ws)[0]['hole']['message'])
        self.assertIsNone(working_set_rows(self.db,self.ws)[0]['audit_id'])
        self.assertEqual('NOT AUDITED',working_set_rows(self.db,self.ws)[0]['audit_freshness'])
        self.assertEqual('ERROR',working_set_rows(self.db,self.ws)[0]['item_status'])
        self.assertIn('AUDIT_ERROR',working_set_review_context(self.db,self.ws))
        self.assertIsNone(working_set_packet(self.db,self.ws)['entries'][0]['audit'])
        with offline_pipeline(self.auditor):self.auditor.audit_many([item],'volume')
        self.assertEqual((1,1),counts(self.db))
        recovered=self.db.working_sets.item(item)
        self.assertEqual(failed['working_set_item_uuid'],recovered['working_set_item_uuid'])
        self.assertEqual(self.db.latest_audit(recovered['work_id'])['id'],recovered['pinned_audit_id'])
        self.assertEqual([],self.db.working_sets.audit_errors(self.ws))

    def test_existing_pin_advances_only_after_success_and_freezes_on_complete(self):
        self.db.add_titles(['Monster'],'standard','en')
        self.db.save_audit(1,{'query':'Monster','match_title':'Monster',
            'publication':publication('Monster')},[])
        item=self.intake(['Monster'])[0]
        self.db.working_sets.pin(item,1,self.db.latest_audit(1)['id'])
        with offline_pipeline(self.auditor):self.auditor.audit_many([item],'volume')
        pinned=self.db.working_sets.item(item)['pinned_audit_id']
        self.assertEqual(2,self.db.working_sets.item(item)['pinned_audit_revision'])
        with offline_pipeline(self.auditor),patch.object(self.db.working_sets,'pin',
             side_effect=RuntimeError('Injected pin failure')):
            self.auditor.audit_many([item],'volume')
        self.assertEqual((1,2),counts(self.db))
        self.assertEqual('ERROR',self.db.working_sets.item(item)['processing_status'])
        self.assertEqual(pinned,self.db.working_sets.item(item)['pinned_audit_id'])
        self.assertIn('AUDIT_ERROR',working_set_review_context(self.db,self.ws))
        with offline_pipeline(self.auditor):self.auditor.audit_many([item],'volume')
        self.assertEqual((1,3),counts(self.db))
        self.assertEqual(3,self.db.working_sets.item(item)['pinned_audit_revision'])
        self.db.working_sets.accept([item])
        self.db.working_sets.set_status(self.ws,'COMPLETE')
        with offline_pipeline(self.auditor):self.auditor.audit_many([1],'volume')
        self.assertEqual(4,self.db.latest_audit(1)['audit_revision'])
        self.assertEqual(3,self.db.working_sets.item(item)['pinned_audit_revision'])


if __name__=='__main__':unittest.main()
