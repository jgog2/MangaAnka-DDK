"""Forced audit Qt flow uses the existing worker; no network or live database."""
import importlib.util
import os
import unittest
if importlib.util.find_spec('PySide6') is None:raise unittest.SkipTest('Qt environment required')
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import tempfile
import threading
import time
from unittest.mock import patch
from PySide6.QtCore import QSettings,QTimer
from PySide6.QtWidgets import QApplication,QMessageBox
from qt_app.main_window import MainWindow
from qt_app.session import Session
from qt_app.workers import AuditWorker
from test_force_reaudit import seed
from test_working_set_audit_recovery import offline_pipeline
from mangaanka_database_development_kit import SearchAuditor
from ddk_commands import parse_batch
from ddk_review import GRAMMAR_VERSION

APP=QApplication.instance() or QApplication([])


class OfflineAuditor(SearchAuditor):
    gate=threading.Event()
    def audit_many(self,ids,workflow):
        self.gate.wait(3)
        with offline_pipeline(self):super().audit_many(ids,workflow)


class QtForceReaudit(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.session=Session(self.root/'force.db',create=True,role='TEST')
        self.wid,self.old,self.sid,self.uid=seed(self.session.db)
        OfflineAuditor.gate.set()
        self.window=MainWindow(self.session,QSettings(str(self.root/'ui.ini'),QSettings.IniFormat),auditor_factory=OfflineAuditor)
        self.window.show();APP.processEvents();self.addCleanup(self.cleanup)

    def cleanup(self):
        OfflineAuditor.gate.set()
        if self.window.worker:self.window.worker.cancel();self.window.worker.wait(4000);APP.processEvents()
        self.window.close();APP.processEvents();self.session.close();self.temp.cleanup()

    def select(self):self.window.catalog.table.selectRow(0);APP.processEvents()

    def wait_idle(self):
        for _ in range(500):
            APP.processEvents();time.sleep(.01)
            if not self.window.busy:return
        self.fail('Audit worker remained busy')

    def test_action_location_label_and_no_selection(self):
        action=self.window.catalog.force_audit_action
        self.assertEqual('Force Re-Audit Selected',action.text());self.assertIn(action,self.window.catalog.more_menu.actions())
        self.assertFalse(action.isEnabled())
        with self.assertRaises(ValueError):self.window.force_reaudit_selected()
        self.assertIsNone(self.window.worker)
        self.select();self.assertTrue(action.isEnabled())
        self.window.catalog.set_scope('all');self.window.catalog.refresh();self.select()
        self.assertFalse(action.isEnabled())

    def test_eligible_states_and_unstable_states(self):
        for state in ('REVIEW','READY','ACCEPTED','REJECTED','ERROR','PENDING','QUEUED','AUDITING','DUPLICATE'):
            with self.subTest(state=state):
                with self.session.db.con() as c:c.execute('UPDATE working_set_items SET processing_status=? WHERE working_set_item_uuid=?',(state,self.uid))
                self.window.catalog.refresh();self.select()
                self.assertEqual(state in ('REVIEW','READY','ACCEPTED','REJECTED','ERROR'),self.window.catalog.force_audit_action.isEnabled())

    def test_confirmation_actual_dialog_includes_title_and_cancel_is_default(self):
        seen=[]
        def cancel_dialog():
            dialog=APP.activeModalWidget()
            seen.append((dialog.windowTitle(),dialog.text(),dialog.defaultButton().text(),[b.text() for b in dialog.buttons()]))
            dialog.defaultButton().click()
        self.select();QTimer.singleShot(0,cancel_dialog)
        self.assertFalse(self.window.force_reaudit_selected())
        title,text,default,buttons=seen[0]
        self.assertEqual('Force Re-Audit Selected',title);self.assertIn('Monster',text)
        self.assertIn('Previous audits, curation, and evidence will be preserved',text)
        self.assertIn('stale',text);self.assertEqual('Cancel',default);self.assertIn('Force Re-Audit',buttons)
        self.assertEqual(self.old,self.session.db.latest_audit(self.wid)['id'])

    def test_force_uses_worker_progress_new_summary_and_refreshes_pin(self):
        self.select();OfflineAuditor.gate.clear();events=[]
        with patch.object(self.window,'confirm_force_reaudit',return_value=True):
            self.assertTrue(self.window.force_reaudit_selected())
        self.assertIsInstance(self.window.worker,AuditWorker);self.assertTrue(self.window.busy)
        self.assertIn('Running',self.window.audit.stage.text());self.assertFalse(self.window.catalog.force_audit_action.isEnabled())
        worker=self.window.worker;worker.event.connect(lambda k,p:events.append((k,p)))
        self.assertFalse(self.window.start_audit([self.uid],force_reaudit=True));self.assertIs(worker,self.window.worker)
        with self.assertRaises(ValueError):self.window.force_reaudit_selected()
        OfflineAuditor.gate.set();self.wait_idle()
        item=self.session.db.working_sets.item(self.uid)
        self.assertGreater(item['pinned_audit_id'],self.old)
        self.assertIn('New 1',self.window.audit.stage.text());self.assertIn('Reused 0',self.window.audit.stage.text())
        done=next(p for k,p in events if k=='done')
        self.assertEqual((1,0),(done['new'],done['reused']));self.assertEqual([item['pinned_audit_id']],done['new_audit_ids'])
        self.assertEqual(item['pinned_audit_id'],self.window.catalog.table.current()['audit_id'])
        self.assertTrue(self.window.catalog.force_audit_action.isEnabled())

    def test_cancel_confirmation_and_second_confirmation_are_guarded(self):
        self.select()
        def reject(title):
            self.assertEqual('Monster',title);self.assertFalse(self.window.catalog.force_audit_action.isEnabled())
            with self.assertRaises(ValueError):self.window.force_reaudit_selected()
            return False
        with patch.object(self.window,'confirm_force_reaudit',side_effect=reject):self.assertFalse(self.window.force_reaudit_selected())
        self.assertIsNone(self.window.worker);self.assertEqual(self.old,self.session.db.working_sets.item(self.uid)['pinned_audit_id'])

    def test_normal_run_and_audit_command_unchanged(self):
        self.window.run_working_set();self.assertIsNone(self.window.worker)
        self.assertEqual(4,GRAMMAR_VERSION);self.assertEqual('audit',parse_batch('audit')[0]['action'])
        self.window.open_curate(self.wid,'active')
        with patch.object(self.window,'start_audit',return_value=True) as start:
            self.window.command.execute('audit')
        start.assert_called_once_with([self.uid])

    def test_failed_worker_reports_zero_new_and_keeps_old_pin(self):
        self.select()
        with patch.object(self.window,'confirm_force_reaudit',return_value=True), \
             patch.object(SearchAuditor,'audit_one',side_effect=RuntimeError('Offline request failed')):
            self.window.force_reaudit_selected();self.wait_idle()
        item=self.session.db.working_sets.item(self.uid)
        self.assertEqual(self.old,item['pinned_audit_id']);self.assertEqual('ERROR',item['processing_status'])
        self.assertIn('New 0',self.window.audit.stage.text());self.assertIn('Reused 0',self.window.audit.stage.text())
        self.assertTrue(self.window.catalog.force_audit_action.isEnabled())

    def test_multiple_selected_items_are_rejected(self):
        self.session.db.working_sets.add_requests(self.sid,['MF Ghost'])
        self.window.catalog.refresh();self.window.catalog.table.selectAll();APP.processEvents()
        self.assertEqual(2,len(self.window.catalog.table.selected()))
        self.assertFalse(self.window.catalog.force_audit_action.isEnabled())
        with self.assertRaises(ValueError):self.window.force_reaudit_selected()
        self.assertIsNone(self.window.worker)


if __name__=='__main__':unittest.main()
