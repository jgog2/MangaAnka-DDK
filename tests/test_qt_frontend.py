"""Offline Qt UX/backend parity checks; every database and settings file is temporary."""
import importlib.util
import os
if importlib.util.find_spec('PySide6') is None:
    import unittest
    raise unittest.SkipTest('Qt frontend tests: install requirements-qt.txt in .venv-qt')
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch,call
from PySide6.QtCore import Qt,QSettings,QItemSelectionModel
from PySide6.QtWidgets import QApplication,QPushButton,QDialog
from PySide6.QtTest import QTest
from qt_app.session import Session
from qt_app.main_window import MainWindow
from qt_app.theme import apply_theme,font_family,TOKENS
from qt_app.dialogs import ReconciliationDialog,DeleteDialog
from qt_app.models.publication import PublicationModel
from ddk_editor import CatalogEditor
from ddk_command_controller import CommandLogic
from ddk_commands import parse_batch
from qt_app.widgets.command_drawer import HELP
from test_working_sets import publication
from test_pre_catalog_hardening import fixture
from mangaanka_database_development_kit import SearchAuditor
from test_working_set_audit_recovery import offline_pipeline

APP=QApplication.instance() or QApplication([])
apply_theme(APP)


class OfflineAuditor(SearchAuditor):
    def audit_many(self,ids,workflow):
        with offline_pipeline(self):super().audit_many(ids,workflow)


class MockAuditor:
    gate=threading.Event()
    failure=False
    def __init__(self,db,events):self.db=db;self.events=events;self.stopped=threading.Event();self.calls=0
    def stop(self):self.stopped.set()
    def audit_many(self,ids,workflow):
        self.calls+=1
        self.events.put(('batch',{'text':'1/1  Monster'}))
        self.events.put(('status',{'text':'Resolving publication references','progress':82,'work_id':ids[0]}))
        while not self.gate.wait(.02) and not self.stopped.is_set():pass
        if self.failure:raise ValueError('Deterministic provider timeout')
        self.events.put(('done',{'text':'Run complete · 1 READY · 0 REVIEW · 0 ERROR'}))


class QtFrontend(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.session=Session(self.root/'catalog.db',create=True,role='TEST');self.db=self.session.db
        self.db.add_titles(['Monster'],'standard','en');self.wid=self.db.works()[0]['id'];self.save()
        self.uid=self.db.working_sets.create('Batch 003');self.db.working_sets.set_active(self.uid)
        self.db.working_sets.add_requests(self.uid,['Monster']);self.item=self.db.working_sets.items(self.uid)[0]['working_set_item_uuid']
        self.db.working_sets.pin(self.item,self.wid,self.db.latest_audit(self.wid)['id'])
        MockAuditor.gate.clear();MockAuditor.failure=False
        self.settings=QSettings(str(self.root/'ui.ini'),QSettings.IniFormat)
        self.window=MainWindow(self.session,self.settings,auditor_factory=MockAuditor);self.window.show();APP.processEvents()
        # A UI callback failure must fail the smoke, not wait in a modal box.
        self.window.safe=lambda callback:callback()
        self.addCleanup(self.cleanup)

    def cleanup(self):
        MockAuditor.gate.set()
        if self.window.worker:
            self.window.worker.cancel();self.window.worker.wait(4000);APP.processEvents()
        self.window.close();APP.processEvents();self.session.close();self.temp.cleanup()

    def save(self,pub=None,holes=(),inventories=()):
        pub=pub or publication(canonical='fixture:monster')
        return self.db.save_audit(self.wid,dict(query='Monster',match_title='Monster',publication=pub,selected_source='fixture',selected_source_name='Fixture',inventories=list(inventories)),list(holes))

    def select_catalog(self):
        self.window.navigate('Catalog');self.window.catalog.table.selectRow(0);APP.processEvents()

    def wait_idle(self):
        for _ in range(1000):
            APP.processEvents();time.sleep(.01)
            if not self.window.busy:return
        self.fail('Worker did not return to idle')

    def global_curate(self):self.window.open_curate(self.wid,'all')

    def test_shell_all_seven_pages(self):
        self.assertEqual(7,self.window.stack.count())
        for name in self.window.pages:
            self.window.sidebar_buttons[name].click();self.assertIs(self.window.stack.currentWidget(),self.window.pages[name])
            self.assertTrue(self.window.sidebar_buttons[name].isChecked())

    def test_context_menus_and_secondary_uuid(self):
        texts=[a.text() for a in self.window.database_button.menu().actions()]
        self.assertIn('Switch Database…',texts);self.assertIn('New Database…',texts);self.assertIn('Copy Database UUID',texts)
        self.assertNotIn(self.db.database_uuid,self.window.database_button.text())
        self.assertEqual('TEST',self.window.role_chip.text())

    def test_set_menu_allowed_and_reopen(self):
        self.db.working_sets.set_status(self.uid,'ARCHIVED');self.window.refresh_all()
        actions={a.text():a for a in self.window.set_button.menu().actions()}
        self.assertFalse(actions['OPEN'].isEnabled());self.assertTrue(actions['Reopen for Review'].isEnabled())
        self.window.reopen_set();self.assertEqual('REVIEW',self.db.working_sets.get(self.uid)['status'])
        self.assertEqual(1,self.db.working_sets.item(self.item)['pinned_audit_id'])

    def test_compact_catalog_and_advanced_columns(self):
        self.window.resize(1440,900);self.window.navigate('Catalog');APP.processEvents()
        table=self.window.catalog.table
        self.assertEqual(8,sum(not table.isColumnHidden(i) for i in range(table.model().columnCount())))
        APP.processEvents();self.assertEqual(0,table.horizontalScrollBar().maximum())
        self.window.catalog.column_actions[-1].setChecked(True);self.assertFalse(table.isColumnHidden(table.model().columnCount()-1))

    def test_inspector_updates_on_selection(self):
        self.select_catalog();labels=[label.text() for label in self.window.catalog.inspector.findChildren(__import__('PySide6.QtWidgets',fromlist=['QLabel']).QLabel)]
        self.assertIn('Monster',labels);self.assertIn('CURRENT',labels);self.assertIn('Publication',[g.title() for g in self.window.catalog.inspector.findChildren(__import__('PySide6.QtWidgets',fromlist=['QGroupBox']).QGroupBox)])

    def test_publication_model_edge_cases(self):
        self.global_curate();base=self.window.curate.rows[0]
        rows=[dict(base,key='10.5',iid='fraction',effective=dict(base['effective'],chapter='10.5',title='Fraction',volume='2')),
              dict(base,key='extra',iid='extra',effective=dict(base['effective'],chapter='Extra A',volume=None),status='UNMAPPED'),
              dict(base,key='11',iid='conflict',conflict=True,status='CONFLICT',effective=dict(base['effective'],chapter='11',volume='2')),
              dict(base,key='provider:x',iid='provider',status='UNCLASSIFIED AUTOMATIC')]
        model=PublicationModel();model.replace(rows,[{'key':'3'}])
        self.assertEqual(4,len(model.root.children));self.assertIn('10.5 · Fraction',model.data(model.row_index('fraction')))
        self.assertTrue(any('Unmapped' in n.values[0] for n in model.root.children));self.assertTrue(any('Provider-only' in n.values[0] for n in model.root.children))
        self.assertEqual('CONFLICT',model.data(model.row_index('conflict').siblingAtColumn(1)))

    def test_mf_275_curated_title_verification(self):
        p=fixture(unmapped=True);p['catalog_identity']=publication(canonical='fixture:monster')['catalog_identity'];p['automatic']['catalog_identity']=p['catalog_identity']
        self.save(p);self.global_curate()
        self.window.drawer.input.setPlainText('select chapter 275\nset volume 23 selected\nset title "Delving Into the Future" chapter 275\nset verification verified selected')
        self.window.drawer.preview();self.assertTrue(self.window.drawer.apply_button.isEnabled());self.window.drawer.apply()
        model=self.window.curate.map.publication;node=next(n for n in model.by_iid.values() if n.row['key']=='275')
        self.assertEqual(275,len(self.window.curate.rows));self.assertEqual(23,sum(n.values[0].startswith('Volume ') for n in model.root.children))
        self.assertIn('275 · Delving Into the Future',node.values[0]);self.assertIn('VERIFIED',node.values[1]);self.assertEqual('23',node.row['effective']['volume']);self.assertIsNone(node.row['automatic']['volume'])

    def test_problem_to_curate_exact_focus(self):
        self.save(holes=[dict(code='UNMAPPED_CHAPTERS',severity='warning',message='Inspect chapter one',details={'chapters':['1']})])
        self.db.working_sets.pin(self.item,self.wid,self.db.latest_audit(self.wid)['id']);self.window.refresh_all()
        self.window.problems.table.selectRow(0);self.window.problems.open_curate()
        self.assertEqual('Curate',self.window.stack.currentWidget().name);self.assertEqual(['1'],[r['key'] for r in self.window.curate.map.selected_rows()])

    def test_drawer_preview_apply_and_invalid_batch(self):
        self.global_curate();self.window.drawer.input.setPlainText('select chapter 1\nset title "New name" chapter 1')
        self.window.drawer.preview();self.assertFalse(self.window.drawer.body.isHidden());self.assertTrue(self.window.command.pending)
        self.assertEqual([],self.db.catalog.state(self.wid)['fields']);self.window.drawer.apply();self.assertEqual('New name',self.db.catalog.rows(self.wid)[0]['effective']['title'])
        revision=self.db.catalog.state(self.wid)['revision'];self.window.drawer.input.setPlainText('set volume 2 chapter 1\ninvalid command');self.window.drawer.preview()
        self.assertFalse(self.window.drawer.apply_button.isEnabled());self.assertIsNone(self.window.command.pending);self.assertEqual(revision,self.db.catalog.state(self.wid)['revision']);self.assertIn('blocked',self.window.drawer.output.toPlainText())

    def test_command_help_history_and_shortcut(self):
        self.global_curate();self.window.drawer.set_expanded(True);self.window.drawer.input.setPlainText('select chapter 1')
        QTest.keyClick(self.window.drawer.input,Qt.Key_Return,Qt.ControlModifier);APP.processEvents()
        self.assertIn('select chapter 1',self.window.drawer.history);self.window.drawer.input.clear();QTest.keyClick(self.window.drawer.input,Qt.Key_Up);self.assertEqual('select chapter 1',self.window.drawer.input.toPlainText())
        QTest.keyClick(self.window.drawer.input,Qt.Key_Down);self.assertEqual('',self.window.drawer.input.toPlainText())
        with patch.object(self.window,'show_text') as show:
            next(b for b in self.window.drawer.findChildren(QPushButton) if b.text()=='Command Help').click();show.assert_called_once_with('Command Help',HELP)

    def test_atomic_multiline_single_transaction(self):
        self.global_curate();self.window.command.execute('select chapter 1\nset volume 2 selected\nset title "Name" chapter 1\nset verification verified selected')
        self.assertEqual([],self.db.catalog.state(self.wid)['fields']);self.window.command.apply()
        self.assertEqual(1,self.db.catalog.state(self.wid)['revision']);self.assertEqual(1,len(self.db.catalog.history(self.wid)))

    def test_shared_command_logic_is_used_by_tk_and_qt(self):
        self.assertIs(CatalogEditor.compile_batch,CommandLogic.compile_batch);self.assertIs(type(self.window.command).command_changes,CommandLogic.command_changes)
        self.global_curate()
        for text in ('show ids','show aliases','show expected','show provenance chapter 1','explain work','show volume 1','select all'):
            self.window.command.execute(text)

    def test_undo_redo_are_previewed(self):
        self.global_curate();self.window.command.execute('set title "Name" chapter 1');self.window.command.apply()
        self.window.drawer.reverse(False);self.assertEqual('Name',self.db.catalog.rows(self.wid)[0]['effective']['title']);self.window.drawer.apply()
        self.assertEqual('',self.db.catalog.rows(self.wid)[0]['effective']['title']);self.window.drawer.reverse(True);self.window.drawer.apply();self.assertEqual('Name',self.db.catalog.rows(self.wid)[0]['effective']['title'])

    def test_long_run_immediate_busy_progress_duplicate_completion(self):
        self.assertTrue(self.window.start_audit([self.item]));worker=self.window.worker
        self.assertTrue(self.window.busy);self.assertFalse(self.window.catalog.run_button.isEnabled());self.assertEqual('Running…',self.window.catalog.run_button.text())
        self.assertFalse(self.window.start_audit([self.item]));self.assertIs(worker,self.window.worker)
        for _ in range(100):
            time.sleep(.01);APP.processEvents()
            if self.window.audit.progress.value()==82:break
        self.assertIn('Resolving publication',self.window.audit.stage.text());self.assertEqual(82,self.window.audit.progress.value())
        MockAuditor.gate.set();self.wait_idle();self.assertTrue(self.window.catalog.run_button.isEnabled());self.assertIn('Run complete',self.window.audit.stage.text())

    def test_worker_failure_returns_idle(self):
        MockAuditor.failure=True;self.window.start_audit([self.item]);MockAuditor.gate.set();self.wait_idle()
        self.assertIn('Deterministic provider timeout',self.window.audit.stage.text());self.assertTrue(self.window.audit.retry_button.isEnabled())

    def test_cancel_returns_idle_and_retains_pin(self):
        pin=self.db.working_sets.item(self.item)['pinned_audit_id'];self.window.start_audit([self.item]);self.window.cancel_run();self.wait_idle()
        self.assertIn('cancelled',self.window.audit.stage.text());self.assertEqual(pin,self.db.working_sets.item(self.item)['pinned_audit_id'])

    def test_accept_selected_calls_central_evaluator(self):
        self.select_catalog()
        with patch.object(self.window,'confirm',return_value=True),patch.object(self.db.acceptance,'evaluate',wraps=self.db.acceptance.evaluate) as evaluate:
            self.window.accept_selected();self.assertTrue(evaluate.called)
        self.assertEqual('CURRENT',self.db.acceptance.state(self.wid));self.assertEqual('ACCEPTED',self.db.working_sets.item(self.item)['processing_status'])

    def test_accept_all_safe_preserves_service_semantics(self):
        with patch.object(self.window,'confirm',return_value=True),patch.object(self.db.acceptance,'bulk_preview',wraps=self.db.acceptance.bulk_preview) as preview:
            self.window.accept_all_safe();self.assertEqual([call(self.uid),call(self.uid)],preview.call_args_list)
        self.assertEqual('CURRENT',self.db.acceptance.state(self.wid))

    def test_reconciliation_dialog(self):
        d=ReconciliationDialog(self.window,self.wid);self.assertTrue(d.approve_button.isEnabled());d.approve();self.assertEqual('CURRENT',self.db.acceptance.state(self.wid));self.assertEqual('READY',self.db.working_sets.item(self.item)['processing_status'])

    def test_stale_and_superseded_do_not_replace_pin(self):
        self.db.acceptance.accept(item_uuids=[self.item]);old=self.db.working_sets.item(self.item)['pinned_audit_id']
        self.save(publication(canonical='fixture:monster',volume='2'));self.window.refresh_all();self.select_catalog();r=self.window.catalog.table.current()
        self.assertEqual(old,r['audit_id']);self.assertEqual('SUPERSEDED',r['pin_state']);self.assertEqual('STALE',r['acceptance_state']);self.assertEqual(2,r['latest_global_audit_id'])
        self.window.open_details(self.wid,'active');self.assertIn('SUPERSEDED',self.window.details.empty.text());self.assertEqual('1',next(iter(self.window.details.panes['Publication'].publication.by_iid.values())).row['effective']['volume'])

    def test_reopen_selected_keeps_audit(self):
        self.db.acceptance.accept(item_uuids=[self.item]);self.window.refresh_all();self.select_catalog()
        with patch.object(self.window,'confirm',return_value=True):self.window.reopen_items()
        self.assertEqual('QUEUED',self.db.working_sets.item(self.item)['processing_status']);self.assertEqual(1,self.db.working_sets.item(self.item)['pinned_audit_id'])

    def test_history_and_raw_event_inspector(self):
        self.db.acceptance.accept(item_uuids=[self.item]);self.window.refresh_all();h=self.window.pages['History']
        self.assertTrue(h.table.records.records);self.assertTrue(any(r['category']=='Acceptance' for r in h.table.records.records));h.table.selectRow(0)
        self.assertTrue(h.inspector.findChildren(__import__('PySide6.QtWidgets',fromlist=['QLabel']).QLabel));self.assertTrue(h.inspector.findChildren(__import__('qt_app.widgets.common',fromlist=['RawData']).RawData))

    def test_details_sections_raw_and_provider_inventory(self):
        self.save(inventories=[dict(source_name='Fixture',chapter_count=1,native_volumes=0,standalone_chapters=1,usable=True,summary='qualified')]);self.window.details.set_scope('all');self.window.details.refresh()
        d=self.window.details;self.assertEqual(9,d.tabs.count());self.assertIn('publication_json',d.panes['Raw Data'].toPlainText())
        row=d.panes['Acquisition'].records.records[0];self.assertEqual(0,row['native_volumes']);self.assertEqual(1,row['chapters']);self.assertEqual('qualified',row['qualification'])
        self.assertEqual(Qt.ScrollBarAlwaysOn,d.panes['Raw Data'].verticalScrollBarPolicy())

    def test_typed_delete_guard(self):
        p=self.db.maintenance.preview(self.db.work(self.wid)['work_uuid']);dialog=DeleteDialog(self.window,p)
        self.assertFalse(dialog.delete_button.isEnabled());dialog.confirmation.setText('delete');self.assertFalse(dialog.delete_button.isEnabled())
        dialog.confirmation.setText('DELETE');self.assertTrue(dialog.delete_button.isEnabled())
        with self.assertRaises(ValueError):self.db.maintenance.delete(p,'delete')
        self.assertIsNotNone(self.db.work(self.wid));dialog.reject()

    def test_window_sizes_and_visible_scrollbars(self):
        for width,height in ((1120,720),(1440,900),(1920,1080)):
            self.window.resize(width,height);APP.processEvents();self.assertEqual(width,self.window.width())
            for page in self.window.pages.values():
                self.window.navigate(page.name);APP.processEvents();self.assertGreater(page.width(),500)
                self.assertLess(page.toolbar.geometry().right(),page.width()+1)
                if hasattr(page,'table'):self.assertEqual(Qt.ScrollBarAlwaysOn,page.table.verticalScrollBarPolicy())

    def test_keyboard_focus_and_escape(self):
        self.window.activateWindow();self.window.navigate('Catalog');QTest.keyClick(self.window,Qt.Key_F,Qt.ControlModifier);APP.processEvents();self.assertTrue(self.window.catalog.search.hasFocus())
        self.window.drawer.set_expanded(True);QTest.keyClick(self.window.drawer.input,Qt.Key_Escape);APP.processEvents();self.assertTrue(self.window.drawer.body.isHidden())

    def test_qsettings_ui_only_roundtrip(self):
        self.window.catalog.column_actions[-1].setChecked(True);self.window.catalog.table.setColumnWidth(0,243);self.window.catalog.splitter.setSizes([700,390]);self.window.drawer.set_expanded(True);self.window.navigate('Details');self.window.save_ui()
        self.assertTrue(self.settings.contains('Catalog/header'))
        self.assertFalse(any('acceptance' in k.lower() for k in self.settings.allKeys()))
        # Session preferences may retain stable selection IDs, never lifecycle
        # state, acceptance decisions, pins, or live object handles.
        set_keys=[k for k in self.settings.allKeys() if 'working_set' in k.lower()]
        self.assertTrue(set_keys)
        self.assertTrue(all(k.startswith('session/databases/') and k.endswith('/working_set_uuid') for k in set_keys))
        self.assertTrue(all(isinstance(self.settings.value(k),str) for k in set_keys))
        self.window.catalog.column_actions[-1].setChecked(False);self.window.restore_ui();self.assertTrue(self.window.catalog.column_actions[-1].isChecked());self.assertEqual(243,self.window.catalog.table.columnWidth(0))

    def test_database_switch_and_new_never_overwrite(self):
        old_uuid=self.db.database_uuid;self.window.switch_database(self.root/'other.db',True,'SCRATCH')
        self.assertNotEqual(old_uuid,self.window.db.database_uuid);self.assertEqual('SCRATCH',self.window.db.role)
        with self.assertRaises(ValueError):self.window.switch_database(self.root/'other.db',True)

    def test_explicit_database_path_uses_validator_and_lock(self):
        # Promotion allows explicit human selection. Never touch a live file in tests.
        path=self.root/'explicit.db'
        with patch('qt_app.session.DB') as ctor,patch('qt_app.session.validate_database') as validate,patch('qt_app.session.WriterLock') as lock:
            session=Session(path)
            validate.assert_called_once_with(path.resolve());lock.assert_called_once_with(path.resolve())
            ctor.assert_called_once_with(path.resolve(),role='SCRATCH',create_new=False,migrate_schema8=False)
            session.close()

    def test_scope_visibility_and_unpinned_no_fallback(self):
        uid=self.db.working_sets.create('Unpinned');self.db.working_sets.add_requests(uid,['Monster']);item=self.db.working_sets.items(uid)[0]
        with self.db.con() as c:c.execute('UPDATE working_set_items SET linked_work_uuid=? WHERE working_set_item_uuid=?',(self.db.work(self.wid)['work_uuid'],item['working_set_item_uuid']))
        self.window.refresh_all();self.window.catalog.set_scope(uid);row=self.window.catalog.table.records.records[0]
        self.assertIsNone(row['audit_id']);self.assertIsNone(row['chapters']);self.assertEqual('UNPINNED',row['pin_state'])
        for name,page in self.window.pages.items():
            if name!='Workflow':self.assertTrue(page.scope_box.isVisibleTo(page))
        self.assertTrue(self.window.set_button.isVisible())

    def test_curation_scope_protected_and_invalid_atomic(self):
        self.db.working_sets.set_status(self.uid,'ARCHIVED');self.window.open_curate(self.wid,'active')
        with self.assertRaises(ValueError):self.window.command.execute('set title "Unsafe" chapter 1')
        self.assertEqual([],self.db.catalog.state(self.wid)['fields'])

    def test_acceptance_blockers_render_and_block(self):
        self.save(holes=[dict(code='UNCLASSIFIED_ACQUISITION',severity='warning',message='Research required')]);self.db.working_sets.pin(self.item,self.wid,self.db.latest_audit(self.wid)['id']);self.window.refresh_all();self.select_catalog()
        with self.assertRaises(ValueError):self.window.accept_selected()
        dialog=ReconciliationDialog(self.window,self.wid);self.assertFalse(dialog.approve_button.isEnabled());self.assertEqual('NONE',self.db.acceptance.state(self.wid))

    def test_copy_and_export_use_backend_scopes(self):
        self.select_catalog();self.window.copy_selected('summary');self.assertIn('Snapshot audit: 1',APP.clipboard().text())
        with patch.object(self.window,'save_text') as save:
            self.window.export_set('packet');payload=json.loads(save.call_args.args[1]);self.assertEqual('pinned',payload['mode']);self.assertEqual(1,payload['entries'][0]['audit']['id'])

    def test_theme_installed_font_fallback(self):
        self.assertTrue(font_family());self.assertTrue(font_family(True));self.assertEqual('#F4F5F7',TOKENS['text'])

    def test_real_auditor_post_curation_advances_only_selected_pin(self):
        uid2=self.db.working_sets.create('Other');self.db.working_sets.add_requests(uid2,['Monster']);other=self.db.working_sets.items(uid2)[0]['working_set_item_uuid'];self.db.working_sets.pin(other,self.wid,1)
        self.window.auditor_factory=OfflineAuditor;self.window.open_curate(self.wid,'active')
        self.window.command.execute('set volume 2 chapter 1');self.window.command.apply();self.assertTrue(self.window.busy);self.wait_idle()
        self.assertEqual(2,self.db.working_sets.item(self.item)['pinned_audit_id']);self.assertEqual(1,self.db.working_sets.item(other)['pinned_audit_id']);self.assertEqual('2',self.db.catalog.rows(self.wid)[0]['effective']['volume'])
        self.assertEqual('READY',self.db.working_sets.item(self.item)['processing_status'])

    def test_real_auditor_undo_and_redo_trigger_reaudit(self):
        self.window.auditor_factory=OfflineAuditor;self.window.open_curate(self.wid,'active');self.window.command.execute('set volume 2 chapter 1');self.window.command.apply();self.wait_idle()
        self.window.drawer.reverse(False);self.window.drawer.apply();self.wait_idle();self.assertEqual(3,self.db.working_sets.item(self.item)['pinned_audit_id'])
        self.window.drawer.reverse(True);self.window.drawer.apply();self.wait_idle();self.assertEqual(4,self.db.working_sets.item(self.item)['pinned_audit_id']);self.assertEqual('2',self.db.catalog.rows(self.wid)[0]['effective']['volume'])

    def test_busy_curation_defers_exact_membership(self):
        self.window.start_audit([self.item]);self.window.open_curate(self.wid,'active');self.window.command.execute('set title "Saved" chapter 1');self.window.command.apply()
        self.assertIn(self.item,self.window.deferred);self.assertEqual('Saved',self.db.catalog.rows(self.wid)[0]['effective']['title'])
        self.window.auditor_factory=OfflineAuditor;MockAuditor.gate.set();self.wait_idle()
        QTest.qWait(250);APP.processEvents();self.wait_idle();self.assertEqual(2,self.db.working_sets.item(self.item)['pinned_audit_id'])

    def test_qaction_status_and_switch_callbacks(self):
        menu=self.window.set_button.menu();next(a for a in menu.actions() if a.text()=='REVIEW').trigger();self.assertEqual('REVIEW',self.db.working_sets.get(self.uid)['status'])
        new=self.db.working_sets.create('Another');self.window.update_context();switch=self.window.working_set_switch_menu
        next(a for a in switch.actions() if a.text().startswith('Another')).trigger();self.assertEqual(new,self.session.active_uuid)

    def test_export_detailed_csv_and_patch(self):
        self.save(holes=[dict(code='UNMAPPED_CHAPTERS',severity='warning',message='Inspect',details={'chapters':['1']})]);self.db.working_sets.pin(self.item,self.wid,2);self.window.refresh_all()
        path=self.root/'problems.csv'
        with patch('PySide6.QtWidgets.QFileDialog.getSaveFileName',return_value=(str(path),'CSV')):self.window.problems.export_csv()
        self.assertIn('UNMAPPED_CHAPTERS',path.read_text(encoding='utf-8-sig'))
        self.global_curate();self.window.command.execute('set title "Name" chapter 1');self.window.command.apply();path=self.root/'patch.json'
        with patch('PySide6.QtWidgets.QFileDialog.getSaveFileName',return_value=(str(path),'JSON')):self.window.export_patch()
        self.assertEqual('mangaanka-curated-patch',json.loads(path.read_text())['format'])

    def test_enter_opens_read_only_details(self):
        self.select_catalog();self.window.catalog.table.setFocus();QTest.keyClick(self.window.catalog.table,Qt.Key_Return);APP.processEvents();self.assertEqual('Details',self.window.stack.currentWidget().name)

    def test_disposition_and_reopen_use_exact_membership(self):
        self.save(holes=[dict(code='UNCLASSIFIED_ACQUISITION',severity='warning',message='Research',details={'chapters':['1']})]);self.db.working_sets.pin(self.item,self.wid,2);self.window.refresh_all();self.window.problems.table.selectRow(0)
        with patch.object(self.window,'form',return_value={'reason':'Grounded official evidence','verification':'VERIFIED'}):self.window.disposition(False)
        self.window.problems.table.selectRow(0);self.assertEqual('IGNORED',self.window.problems.table.current()['disposition'])
        with patch.object(self.window,'form',return_value={'reason':'Evidence changed','verification':'REVIEWED'}):self.window.disposition(True)
        self.assertEqual('OPEN',self.window.problems.table.records.records[0]['disposition'])

    def test_linked_execution_failure_retains_pin_and_is_visible(self):
        self.db.working_sets.observe_unresolved(self.item,{'resolution_error':'Timeout on the fresh attempt'},
            [dict(code='AUDIT_ERROR',severity='error',message='Timeout on the fresh attempt')],status='ERROR');self.window.refresh_all()
        row=next(r for r in self.window.problems.table.records.records if r['code']=='AUDIT_ERROR');self.assertEqual(self.item,row['_item']['working_set_item_uuid'])
        self.window.problems.table.select_record(lambda r:r['code']=='AUDIT_ERROR');self.window.problems.copy();self.assertIn('Timeout on the fresh attempt',APP.clipboard().text())
        self.window.open_details(self.wid,'active');self.assertIn('Timeout on the fresh attempt',self.window.details.panes['Raw Data'].toPlainText());self.assertEqual(1,self.db.working_sets.item(self.item)['pinned_audit_id'])

    def test_safe_preview_survives_unrelated_refresh_but_stale_cancels(self):
        self.global_curate();self.window.command.execute('set title "Preview" chapter 1');pending=self.window.command.pending
        self.window.refresh_all();self.assertIs(pending,self.window.command.pending);self.assertTrue(self.window.drawer.apply_button.isEnabled())
        self.save();self.window.refresh_all();self.assertIsNone(self.window.command.pending);self.assertFalse(self.window.drawer.apply_button.isEnabled())

    def test_delete_dialog_uses_backend_backup_and_detaches_intake(self):
        preview=self.db.maintenance.preview(self.db.work(self.wid)['work_uuid']);dialog=DeleteDialog(self.window,preview);dialog.confirmation.setText('DELETE');dialog.apply()
        self.assertIsNone(self.db.work(self.wid));item=self.db.working_sets.item(self.item);self.assertIsNone(item['pinned_audit_id']);self.assertIsNone(item['work_id']);self.assertTrue(list((self.root/'backups').glob('*.db')))

    def test_more_menu_copy_callback(self):
        self.select_catalog();next(a for a in self.window.catalog.more_menu.actions() if a.text()=='Copy Selected Title').trigger();self.assertEqual('Monster',APP.clipboard().text())

    def test_worker_initialization_failure_returns_idle(self):
        def broken_factory(db,events):raise ValueError('Provider setup unavailable')
        self.window.auditor_factory=broken_factory;self.window.start_audit([self.item]);self.assertTrue(self.window.busy);self.wait_idle()
        self.assertFalse(self.window.busy);self.assertIn('Provider setup unavailable',self.window.audit.stage.text());self.assertTrue(self.window.catalog.run_button.isEnabled())


if __name__=='__main__':unittest.main()
