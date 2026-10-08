"""Disposable Tk smoke for the low-prominence catalog maintenance action."""
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mangaanka_database_development_kit as ddk


with tempfile.TemporaryDirectory() as folder:
    app = ddk.App(workspace=folder)
    try:
        app.db.add_titles(['Same'], 'standard', 'en')
        app.db.add_titles(['Same'], 'official_color', 'en')
        target = app.db.work(1)
        sibling = app.db.work(2)
        with app.db.con() as c:
            c.execute('UPDATE works SET conceptual_work_uuid=? WHERE id=?',
                      (target['conceptual_work_uuid'], sibling['id']))
        app.db.save_audit(1, {'query': 'Same', 'match_title': 'Same'}, [])
        set_uuid = app.db.working_sets.create('Maintenance fixture')
        app.db.working_sets.set_active(set_uuid)
        app.active_set_uuid = set_uuid
        app.db.working_sets.add_requests(set_uuid, ['Same'])
        item = app.db.working_sets.items(set_uuid)[0]
        item_uuid = item['working_set_item_uuid']
        app.db.working_sets.pin(item_uuid, 1, app.db.latest_audit(1)['id'])
        app.catalog_view.set('All Catalog')
        app.refresh_all(); app.update()
        app.catalog_tree.selection_set(str(target['id']))
        app.load_details(target['id'])
        app.editor.open(target['id'])
        app.nb.select(app.catalog_tab)
        assert app.catalog_maintenance_menu.entrycget(0, 'label') == 'Delete Catalog Work...'

        app.catalog_tree.selection_remove(app.catalog_tree.selection())
        with patch.object(ddk.messagebox, 'showerror') as error:
            app.catalog_maintenance_menu.invoke(0)
        assert error.called
        app.catalog_tree.selection_set((str(target['id']), str(sibling['id'])))
        with patch.object(ddk.messagebox, 'showerror') as error:
            app.catalog_maintenance_menu.invoke(0)
        assert error.called
        app.catalog_tree.selection_set(str(target['id']))

        def open_dialog():
            app.catalog_maintenance_menu.invoke(0)
            app.update()
            dialogs = [w for w in app.winfo_children()
                       if isinstance(w, ddk.tk.Toplevel) and 'impact preview' in w.title()]
            assert len(dialogs) == 1
            return dialogs[0]

        before = (len(app.db.works()), len(app.db.working_sets.items(set_uuid)))
        backups = list((Path(folder) / 'backups').glob('*.db'))
        dialog = open_dialog()
        text = dialog.impact_text.get('1.0', 'end')
        assert target['work_uuid'] in text and 'Audit revisions: 1' in text
        assert 'WORKING SET ITEMS DETACHED, NOT DELETED: 1' in text
        assert 'Sibling editions of this conceptual work: 1' in text
        assert str(dialog.delete_button.cget('state')) == 'disabled'
        dialog.destroy(); app.update()
        assert before == (len(app.db.works()), len(app.db.working_sets.items(set_uuid)))
        assert backups == list((Path(folder) / 'backups').glob('*.db'))

        dialog = open_dialog()
        app.catalog_tree.selection_set(str(sibling['id']))
        dialog.confirmation_var.set('DELETE')
        with patch.object(ddk.messagebox, 'showerror') as error:
            dialog.delete_button.invoke()
        assert error.called and app.db.work(target['id']) is not None
        assert backups == list((Path(folder) / 'backups').glob('*.db'))
        app.catalog_tree.selection_set(str(target['id']))

        original_path = app.db.path
        other_path = Path(folder) / 'other.db'
        ddk.DB(other_path, role='TEST')
        dialog = open_dialog()
        app.switch_database(other_path)
        dialog.confirmation_var.set('DELETE')
        with patch.object(ddk.messagebox, 'showerror') as error:
            dialog.delete_button.invoke()
        assert error.called and len(app.db.works()) == 0
        app.switch_database(original_path)
        assert app.db.work(target['id']) is not None
        app.catalog_view.set('All Catalog'); app.refresh_all(); app.update()
        app.catalog_tree.selection_set(str(target['id']))

        dialog = open_dialog()
        dialog.confirmation_var.set('delete'); app.update()
        assert str(dialog.delete_button.cget('state')) == 'disabled'
        dialog.confirmation_var.set('DELETE'); app.update()
        assert str(dialog.delete_button.cget('state')) == 'normal'
        dialog.delete_button.invoke(); app.update()
        assert app.db.work(target['id']) is None
        assert app.db.work(sibling['id'])['work_uuid'] == sibling['work_uuid']
        assert len(app.db.working_sets.items(set_uuid)) == 1
        detached = app.db.working_sets.item(item_uuid)
        assert detached['linked_work_uuid'] is None and detached['processing_status'] == 'REVIEW'
        assert app.catalog_tree.get_children() == (str(sibling['id']),)
        assert app.editor.current is None and app._active_work_id is None
        assert app.detail_header.get() == 'Select a title'
        assert target['work_uuid'] not in app.catalog_text.get('1.0', 'end')
        assert list((Path(folder) / 'backups').glob('*.db'))
        app.catalog_view.set('Active Working Set'); app.refresh_all(); app.update()
        assert app.catalog_tree.exists('i:' + item_uuid)
        assert app.catalog_tree.set('i:' + item_uuid, 'item_status') == 'REVIEW'
        app.nb.select(app.catalog_tab)
        print('Catalog maintenance menu, preview/cancel, typed delete, sibling/intake preservation, refresh OK')
    finally:
        app.destroy()
