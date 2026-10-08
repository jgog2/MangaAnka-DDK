"""Focused Tk Working Set workflow on disposable databases only."""
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
import tkinter as tk
from tkinter import ttk

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import mangaanka_database_development_kit as ddk
from test_working_sets import publication


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


with tempfile.TemporaryDirectory() as folder:
    app=ddk.App(workspace=folder)
    try:
        try:ddk.App(workspace=folder)
        except ValueError as exc:assert 'already open' in str(exc)
        else:raise AssertionError('Second writable DDK instance opened the same database')
        app.geometry('1120x720');app.update()
        buttons={w.cget('text'):w for w in descendants(app) if isinstance(w,(ttk.Button,ttk.Menubutton))}
        for label in ('New Working Set','Switch Working Set','Status: NONE','Copy Selected ▾',
                      'Copy Working Set ▾','Export Working Set ▾','Intake ▾'):
            assert label in buttons,label
        assert str(app.set_more['state'])=='disabled'
        with patch('tkinter.simpledialog.askstring',return_value='Batch A'):
            app.new_working_set()
        set_a=app.active_set_uuid
        assert set_a and app.db.working_sets.get(set_a)['name']=='Batch A'
        assert str(app.set_more['text'])=='Status: OPEN ▾'
        app.input.insert('1.0','Alpha\nBeta\nAlpha')
        app.add_titles();app.update()
        assert len(app.db.working_sets.items(set_a))==2
        assert len(app.db.works())==0, 'Intake prematurely created catalog work'
        assert len(app.catalog_tree.get_children())==2
        assert len(app.audit_tree.get_children())==2
        alpha=next(i for i in app.db.working_sets.items(set_a) if i['original_query']=='Alpha')
        app.db.working_sets.observe_unresolved(alpha['working_set_item_uuid'],{'query':'Alpha'},
            [{'code':'NO_CANONICAL_RESULT','message':'Offline fixture unresolved'}])
        app.refresh_all();app.catalog_tree.selection_set('i:'+alpha['working_set_item_uuid'])
        app.catalog_selected()
        assert 'NO_CANONICAL_RESULT' in app.catalog_text.get('1.0','end')
        app.input.insert('1.0','Alpha\nBeta')
        app.add_titles();app.update()
        assert len(app.db.working_sets.items(set_a))==2
        assert 'already in set' in app.batch.get()

        app.db.add_titles(['Linked'],'standard','en')
        pub=publication(canonical='fixture:linked')
        pub['catalog_identity']['external_ids']={'fixture':'linked'}
        audit=app.db.save_audit(1,{'query':'Linked','match_title':'Linked',
            'requested_edition':'standard','publication':pub},[])
        app.db.working_sets.add_requests(set_a,['Linked'])
        linked=next(i for i in app.db.working_sets.items(set_a) if i['original_query']=='Linked')
        app.db.working_sets.pin(linked['working_set_item_uuid'],1,audit,ready=True)
        app.refresh_all();app.update()
        assert len(app.catalog_tree.get_children())==3
        iid='i:'+linked['working_set_item_uuid']
        app.catalog_tree.selection_set(iid);app.catalog_selected()
        for kind in ('summary','review','csv','full'):
            app.copy_catalog_selected(kind)
            assert 'Linked' in app.clipboard_get(),kind
        for kind in ('summary','csv','titles','review'):
            app.copy_working_set(kind)
            assert 'Alpha' in app.clipboard_get(),kind
        app.catalog_view.set('Accepted Master Catalog');app.refresh_all();app.update()
        assert not app.catalog_tree.get_children()
        app.db.working_sets.accept([linked['working_set_item_uuid']]);app.refresh_all();app.update()
        assert len(app.catalog_tree.get_children())==1
        app.catalog_view.set('All Catalog');app.refresh_all();app.update()
        assert len(app.catalog_tree.get_children())==1
        app.catalog_view.set('Active Working Set');app.refresh_all();app.update()
        assert len(app.catalog_tree.get_children())==3

        app.change_working_set_status('REVIEW');app.update()
        assert str(app.set_more['text'])=='Status: REVIEW ▾'
        set_b=app.db.working_sets.create('Batch B')
        app.activate_working_set(set_b);app.update()
        assert app.active_set_uuid==set_b and 'Batch B' in app.working_set_label.get()
        assert str(app.set_more['text'])=='Status: OPEN ▾'
        assert not app.catalog_tree.get_children()
        app.activate_working_set(set_a);app.update()
        assert str(app.set_more['text'])=='Status: REVIEW ▾'
        assert len(app.catalog_tree.get_children())==3
        assert app.editor.history_scope.get()=='Active Working Set'
        app.nb.select(app.catalog_tab);app.update()
        visible=[w for w in descendants(app.catalog_tab) if isinstance(w,(ttk.Button,ttk.Menubutton)) and w.winfo_ismapped()]
        assert all(w.winfo_rootx()+w.winfo_width()<=app.winfo_rootx()+app.winfo_width() for w in visible)
        app.geometry('1920x1080');app.update()
        assert all(w.winfo_rootx()+w.winfo_width()<=app.winfo_rootx()+app.winfo_width() for w in visible)
        second=Path(folder)/'another.db'
        for item in app.db.working_sets.items(set_a):
            if item['processing_status']!='ACCEPTED':app.db.working_sets.set_item_status(item['working_set_item_uuid'],'REJECTED')
        app.change_working_set_status('COMPLETE');app.update()
        assert str(app.set_more['text'])=='Status: COMPLETE ▾'
        assert app.set_menu.entrycget(0,'state')=='disabled'
        assert app.set_menu.entrycget(3,'state')=='normal'
        app.change_working_set_status('ARCHIVED');app.update()
        assert str(app.set_more['text'])=='Status: ARCHIVED ▾'
        assert all(app.set_menu.entrycget(index,'state')=='disabled' for index in range(4))
        app.create_database(second,'TEST');app.update()
        assert app.active_set_uuid is None and not app.catalog_tree.get_children()
        assert str(app.set_more['text'])=='Status: NONE' and str(app.set_more['state'])=='disabled'
        app.switch_database(Path(folder)/'mangaanka_catalog.db');app.update()
        assert app.active_set_uuid==set_a and len(app.catalog_tree.get_children())==3
        assert str(app.set_more['text'])=='Status: ARCHIVED ▾'
        print('Working Set intake, context-aware dedupe, scoped Catalog, copy, acceptance, switching, and 1120px toolbar OK')
    finally:
        app.destroy()
    restored=ddk.App(workspace=folder)
    try:
        assert restored.active_set_uuid==set_a
        assert str(restored.set_more['text'])=='Status: ARCHIVED ▾'
    finally:
        restored.destroy()
