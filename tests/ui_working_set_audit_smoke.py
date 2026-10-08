"""Disposable Tk smoke for Working Set batch audit, intake error, and retry."""
from pathlib import Path
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import mangaanka_database_development_kit as ddk
from test_working_set_audit_recovery import TITLES,counts,offline_pipeline,publication
from unittest.mock import patch


with tempfile.TemporaryDirectory() as folder:
    app=ddk.App(workspace=folder)
    try:
        app.db.add_titles(TITLES,'standard','en')
        for wid,title in enumerate(TITLES,1):
            app.db.save_audit(wid,{'query':title,'match_title':title,
                'publication':publication(title)},[])
        original={r['input_title']:r['work_uuid'] for r in app.db.works()}
        with patch('tkinter.simpledialog.askstring',return_value='Catalog Batch 001'):
            app.new_working_set()
        app.input.insert('1.0','\n'.join(TITLES));app.add_titles();app.update()
        item_ids=[i['working_set_item_uuid'] for i in app.db.working_sets.items(app.active_set_uuid)]
        assert len(item_ids)==3 and counts(app.db)==(3,3)
        with offline_pipeline(app.auditor),patch.object(app.db.working_sets,'pin',
             side_effect=RuntimeError('Batch persistence failure')):
            app.start_audit();app.worker.join(timeout=10)
            assert not app.worker.is_alive()
        app.refresh_all();app.update()
        assert counts(app.db)==(3,3)
        assert all(app.db.working_sets.item(item)['processing_status']=='ERROR' for item in item_ids)
        assert 'Error 3' in app.working_set_label.get()
        assert 'ERROR 3' in app.working_set_label.get()
        assert sum(app.hole_tree.set(iid,'code')=='AUDIT_ERROR'
                   for iid in app.hole_tree.get_children())==3
        assert all(app.catalog_tree.set('i:'+item,'freshness')=='NOT AUDITED' for item in item_ids)
        with offline_pipeline(app.auditor):
            app.start_audit();app.worker.join(timeout=10)
            assert not app.worker.is_alive()
        app.refresh_all();app.update()
        assert counts(app.db)==(3,6)
        assert {r['input_title']:r['work_uuid'] for r in app.db.works()}==original
        assert len(app.db.working_sets.items(app.active_set_uuid))==3
        assert not any(app.hole_tree.set(iid,'code')=='AUDIT_ERROR'
                       for iid in app.hole_tree.get_children())
        for item_uuid in item_ids:
            item=app.db.working_sets.item(item_uuid)
            iid='i:'+item_uuid
            assert item['linked_work_uuid']==original[item['original_query']]
            assert item['pinned_audit_id']==app.db.latest_audit(item['work_id'])['id']
            assert app.catalog_tree.exists(iid)
            assert app.catalog_tree.set(iid,'freshness')!='NOT AUDITED'
        failed=item_ids[0]
        pinned=app.db.working_sets.item(failed)['pinned_audit_id']
        with offline_pipeline(app.auditor),patch.object(app.db.working_sets,'pin',
             side_effect=RuntimeError('UI injected pin failure')):
            app.start_audit([failed]);app.worker.join(timeout=10)
            assert not app.worker.is_alive()
        app.refresh_all();app.update()
        assert counts(app.db)==(3,6)
        assert app.db.working_sets.item(failed)['processing_status']=='ERROR'
        assert app.db.working_sets.item(failed)['pinned_audit_id']==pinned
        assert 'Error 1' in app.working_set_label.get()
        assert 'ERROR 1' in app.working_set_label.get()
        iid='i:'+failed
        assert app.hole_tree.exists(iid)
        assert app.hole_tree.set(iid,'code')=='AUDIT_ERROR'
        assert app.hole_tree.set(iid,'severity')=='ERROR'
        app.hole_tree.selection_set(iid);app.problem_selected()
        detail=app.problem_text.get('1.0','end')
        assert 'UI injected pin failure' in detail and 'working_set_item_uuid' in detail
        assert app.catalog_tree.set(iid,'item_status')=='ERROR'
        app.catalog_view.set('All Catalog');app.refresh_all();app.update()
        assert len(app.catalog_tree.get_children())==3
        app.catalog_view.set('Active Working Set');app.refresh_all();app.update()
        assert len(app.catalog_tree.get_children())==3
        assert app.audit_tree.exists(iid)
        app.audit_tree.selection_set(iid)
        with offline_pipeline(app.auditor):
            app.start_audit();app.worker.join(timeout=10)
            assert not app.worker.is_alive()
        app.refresh_all();app.update()
        assert counts(app.db)==(3,7)
        assert app.db.working_sets.item(failed)['pinned_audit_id']!=pinned
        assert app.db.working_sets.item(failed)['processing_status'] in ('READY','REVIEW')
        assert not app.hole_tree.exists(iid)
        app.input.insert('1.0','New Series');app.add_titles();app.update()
        new=next(i['working_set_item_uuid'] for i in app.db.working_sets.items(app.active_set_uuid)
                 if i['original_query']=='New Series')
        with offline_pipeline(app.auditor),patch.object(app.db.working_sets,'pin',
             side_effect=RuntimeError('New title persistence failure')):
            app.start_audit([new]);app.worker.join(timeout=10)
            assert not app.worker.is_alive()
        app.refresh_all();app.update()
        new_iid='i:'+new
        assert counts(app.db)==(3,7)
        assert app.catalog_tree.set(new_iid,'item_status')=='ERROR'
        assert app.catalog_tree.set(new_iid,'freshness')=='NOT AUDITED'
        assert app.hole_tree.exists(new_iid)
        assert 'Error 1' in app.working_set_label.get()
        assert app.audit_tree.exists(new_iid)
        app.audit_tree.selection_set(new_iid)
        with offline_pipeline(app.auditor):
            app.start_audit();app.worker.join(timeout=10)
            assert not app.worker.is_alive()
        app.refresh_all();app.update()
        assert counts(app.db)==(4,8)
        assert app.catalog_tree.set(new_iid,'freshness')!='NOT AUDITED'
        assert not app.hole_tree.exists(new_iid)
        print('Working Set batch link/pin, intake ERROR, Problems, scopes, and retry UI OK')
    finally:
        app.destroy()
