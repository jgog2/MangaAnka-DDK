"""Offline Tk smoke for the new workflow; only disposable databases are opened."""
from pathlib import Path
import sys
import tempfile
import tkinter as tk
from tkinter import ttk
from unittest.mock import patch
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import mangaanka_database_development_kit as ddk
from test_working_set_audit_recovery import offline_pipeline,publication


def finish(app):
    app.worker.join(timeout=15)
    assert not app.worker.is_alive()
    app.update();app.refresh_all();app.update()


with tempfile.TemporaryDirectory() as folder:
    app=ddk.App(workspace=folder)
    try:
        app.geometry('1120x720')
        with patch('tkinter.simpledialog.askstring',return_value='Workflow Batch'):
            app.new_working_set()
        uid=app.active_set_uuid
        app.input.insert('1.0','MF Ghost\nMonster');app.add_titles()
        assert 'Active Working Set' in app.shared_scope.get()
        with offline_pipeline(app.auditor):app.run_working_set();finish(app)
        items=app.db.working_sets.items(uid)
        mf,monster=items
        assert all(i['processing_status']=='READY' for i in items)
        with patch.object(ddk.messagebox,'askyesno',return_value=True):app.accept_all_safe()
        assert all(i['processing_status']=='ACCEPTED' for i in app.db.working_sets.items(uid))
        assert app.catalog_tree.set('i:'+monster['working_set_item_uuid'],'acceptance_state')=='CURRENT'
        app.catalog_tree.selection_set('i:'+mf['working_set_item_uuid']);app.reopen_selected_items()
        old_pin=mf['pinned_audit_id']
        assert app.db.working_sets.item(mf['working_set_item_uuid'])['pinned_audit_id']==old_pin
        with offline_pipeline(app.auditor):app.run_working_set();finish(app)
        mf=app.db.working_sets.item(mf['working_set_item_uuid'])
        assert mf['pinned_audit_id']!=old_pin and mf['processing_status']=='READY'
        assert app.db.acceptance.state(mf['work_id'])=='STALE'

        # Apply through the active set automatically audits exactly that membership.
        app.editor.open(mf['work_id'])
        before_monster=app.db.working_sets.item(monster['working_set_item_uuid'])['pinned_audit_id']
        app.editor.preview([dict(entity='chapter',key='275',field='volume',value='23')],'Publisher correction')
        with offline_pipeline(app.auditor):app.editor.apply();finish(app)
        after_apply=app.db.working_sets.item(mf['working_set_item_uuid'])
        assert after_apply['processing_status']=='READY'
        assert app.db.working_sets.item(monster['working_set_item_uuid'])['pinned_audit_id']==before_monster
        assert app.db.catalog.state(mf['work_id'])['revision']==1
        assert app.db.latest_audit(mf['work_id'])['audit_revision']==3
        for redo in (False,True):
            app.editor.preview_reverse(redo)
            with offline_pipeline(app.auditor):app.editor.apply();finish(app)
        assert app.db.catalog.state(mf['work_id'])['revision']==3
        assert app.db.latest_audit(mf['work_id'])['audit_revision']==5

        # A curation-triggered failed audit retains the committed human evidence/pin.
        pin=app.db.working_sets.item(mf['working_set_item_uuid'])['pinned_audit_id']
        app.editor.preview([dict(entity='chapter',key='275',field='source_note',value='Publisher checked')],'Note')
        with offline_pipeline(app.auditor),patch.object(app.db.working_sets,'pin',side_effect=RuntimeError('Injected UI failure')):
            app.editor.apply();finish(app)
        assert app.db.catalog.state(mf['work_id'])['revision']==4
        assert app.db.working_sets.item(mf['working_set_item_uuid'])['processing_status']=='ERROR'
        assert app.db.working_sets.item(mf['working_set_item_uuid'])['pinned_audit_id']==pin
        with offline_pipeline(app.auditor):app.retry_errors();finish(app)
        assert app.db.working_sets.item(mf['working_set_item_uuid'])['processing_status']=='READY'

        # Raw acquisition cannot be approved; a grounded disposition recalculates immediately.
        pub=publication('MF Ghost');pub['curation_revision']=4
        pub['unclassified_acquisition']=[{'chapter':'275.1'}]
        hole=dict(code='UNCLASSIFIED_ACQUISITION',severity='warning',message='Provider-only record')
        audit=app.db.save_audit(mf['work_id'],{'query':'MF Ghost','publication':pub},[hole])
        app.db.working_sets.pin(mf['working_set_item_uuid'],mf['work_id'],audit)
        app.refresh_all();app.nb.select(app.catalog_tab)
        app.catalog_tree.selection_set('i:'+mf['working_set_item_uuid'])
        with patch.object(ddk.messagebox,'showerror') as error:app.preview_accept_selected()
        assert error.called and 'UNCLASSIFIED' in str(error.call_args)
        problem=app.db.holes('UNCLASSIFIED_ACQUISITION')[0]
        app.db.dispose_problem(problem['id'],'Publisher confirms split extra; not a missing canonical chapter','VERIFIED',item_uuid=mf['working_set_item_uuid'])
        app.refresh_all()
        with patch.object(ddk.messagebox,'askyesno',return_value=True):app.accept_all_safe()
        assert app.db.acceptance.state(mf['work_id'])=='CURRENT'
        app.change_working_set_status('COMPLETE');app.update()
        assert app.db.working_sets.get(uid)['status']=='COMPLETE'
        app.change_working_set_status('ARCHIVED');app.update()
        assert app.set_menu.entrycget(4,'state')=='normal'
        with patch.object(ddk.messagebox,'showerror') as error:app.run_working_set()
        assert error.called
        protected_pin=app.db.working_sets.item(mf['working_set_item_uuid'])['pinned_audit_id']
        app.catalog_view.set('All Catalog');app.refresh_all();app.editor.open(mf['work_id'])
        with offline_pipeline(app.auditor):app.editor.reaudit();finish(app)
        assert app.db.working_sets.get(uid)['status']=='ARCHIVED'
        assert app.db.working_sets.item(mf['working_set_item_uuid'])['pinned_audit_id']==protected_pin
        app.catalog_view.set('Active Working Set');app.refresh_all()
        app.reopen_working_set();app.update()
        assert app.db.working_sets.get(uid)['status']=='REVIEW'
        assert app.db.working_sets.item(mf['working_set_item_uuid'])['pinned_audit_id']==protected_pin
        app.catalog_tree.selection_set('i:'+mf['working_set_item_uuid']);app.reopen_selected_items()
        with patch.object(ddk.messagebox,'showerror') as error:app.change_working_set_status('COMPLETE')
        assert error.called

        # Historical pinned views remain unchanged after a new global audit.
        pub=publication('MF Ghost');pub['curation_revision']=4
        app.db.save_audit(mf['work_id'],{'query':'MF Ghost','publication':pub},[])
        app.refresh_all();app.update()
        assert app.catalog_tree.set('i:'+mf['working_set_item_uuid'],'freshness')=='SUPERSEDED'
        app.catalog_tree.selection_set('i:'+mf['working_set_item_uuid']);app.catalog_selected()
        assert 'latest_global_audit_id' in app.catalog_text.get('1.0','end')
        app.reevaluate_acceptance();app.update()
        dialogs=[w for w in app.winfo_children() if isinstance(w,tk.Toplevel)]
        assert any(w.title()=='Reevaluate Acceptance' for w in dialogs)
        for w in dialogs:w.destroy()
        app.editor.refresh_history()
        assert any(app.editor.history.set(iid,'action')=='REOPEN_WORKING_SET' for iid in app.editor.history.get_children())
        # Busy-run curation is deferred, then processed once when the run ends.
        app.editor.open(mf['work_id'])
        app.editor.preview([dict(entity='chapter',key='275',field='source_note',value='Deferred note')],'Deferred edit')
        app.worker=SimpleNamespace(is_alive=lambda:True)
        app.editor.apply()
        assert mf['working_set_item_uuid'] in app.deferred_curation_items
        deferred_pin=app.db.working_sets.item(mf['working_set_item_uuid'])['pinned_audit_id']
        app.worker=None
        with offline_pipeline(app.auditor):
            app.events.put(('done',{'text':'Previous run ended'}));app.poll()
            ready=tk.BooleanVar(value=False);app.after(250,lambda:ready.set(True));app.wait_variable(ready)
            finish(app)
        assert not app.deferred_curation_items
        assert app.db.working_sets.item(mf['working_set_item_uuid'])['pinned_audit_id']!=deferred_pin
        assert app.db.working_sets.item(mf['working_set_item_uuid'])['processing_status']=='READY'
        assert app.db.catalog.state(mf['work_id'])['revision']==5
        print('v7 UI: run, bulk acceptance, explicit reopen, curation/undo/redo auto-audit, retry, blocked reason, stale/current pins, reconciliation and scoped history OK')
    finally:app.destroy()
