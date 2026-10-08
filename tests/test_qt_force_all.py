"""Workflow batch action, confirmation, responsive worker and duplicate guards."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import time
import threading
import unittest
from unittest.mock import patch
from PySide6.QtCore import QTimer
import test_qt_force_reaudit as qt_reference
import test_force_all as batch_reference
from test_qt_force_reaudit import APP,OfflineAuditor


class QtForceAll(unittest.TestCase):
    setUp=qt_reference.QtForceReaudit.setUp
    cleanup=qt_reference.QtForceReaudit.cleanup
    wait_idle=qt_reference.QtForceReaudit.wait_idle

    def add_pending(self):
        self.session.db.working_sets.add_requests(self.sid,['Fire Force','MF Ghost'])
        self.window.refresh_all()

    def start(self):
        with patch.object(self.window,'confirm_force_all',return_value=True):return self.window.force_reaudit_all()

    def test_actions_menu_no_selection_needed_and_filtered_rows_do_not_limit_batch(self):
        self.add_pending();page=self.window.workflow
        self.assertIn(page.force_all_action,page.batch_menu.actions());self.assertTrue(page.force_all_action.isEnabled())
        self.assertEqual('Force Re-Audit All',page.force_all_action.text())
        page.search.setText('not a title');APP.processEvents()
        self.assertEqual(0,page.table.proxy.rowCount())
        self.assertEqual(3,len(self.window.force_all_plan()['items']))
        self.start();self.wait_idle()
        self.assertEqual(3,self.window.last_force_all['successful'])

    def test_real_confirmation_title_count_accepted_and_cancel_default(self):
        self.add_pending();self.session.db.working_sets.accept([self.uid]);before=self.session.db.path.read_bytes();seen=[]
        def cancel():
            box=APP.activeModalWidget();seen.append((box.windowTitle(),box.text(),box.defaultButton().text()));box.defaultButton().click()
        QTimer.singleShot(0,cancel)
        self.assertFalse(self.window.force_reaudit_all())
        title,text,default=seen[0]
        self.assertEqual(('Force Re-Audit All','Cancel'),(title,default))
        self.assertIn('3 titles',text);self.assertIn('1 ACCEPTED',text);self.assertIn('immutable audit',text);self.assertIn('STALE',text)
        self.assertEqual(before,self.session.db.path.read_bytes());self.assertIsNone(self.window.worker)

    def test_duplicate_confirmation_and_other_audit_launches_blocked(self):
        self.add_pending();before=self.session.db.working_sets.items(self.sid)
        def confirm(plan):
            self.assertFalse(self.window.workflow.force_all_action.isEnabled())
            with self.assertRaises(ValueError):self.window.force_reaudit_all()
            self.assertFalse(self.window.start_audit([self.uid]));self.window.retry_errors();self.window.run_working_set()
            return False
        with patch.object(self.window,'confirm_force_all',side_effect=confirm):self.assertFalse(self.window.force_reaudit_all())
        self.assertEqual(before,self.session.db.working_sets.items(self.sid))

    def test_worker_duplicate_launch_guard_and_result_report(self):
        self.add_pending();OfflineAuditor.gate.clear();self.start();worker=self.window.worker
        try:
            self.assertTrue(self.window.busy);self.assertFalse(self.window.workflow.force_all_action.isEnabled())
            self.assertTrue(self.window.workflow.cancel_all_action.isEnabled())
            with self.assertRaises(ValueError):self.window.force_reaudit_all()
            self.assertFalse(self.window.start_audit([self.uid]));self.assertIs(worker,self.window.worker)
        finally:OfflineAuditor.gate.set();self.wait_idle()
        summary=self.window.last_force_all
        self.assertEqual((3,3,0),(summary['total'],summary['successful'],summary['failed']))
        self.assertIn('Completed 3/3',self.window.audit.stage.text())
        self.assertTrue(self.window.workflow.results_action.isEnabled())
        with patch.object(self.window,'show_text') as show:self.window.show_force_all_results()
        show.assert_called_once_with('Force Re-Audit All results',summary)

    def test_changed_confirmation_snapshot_requires_reconfirmation(self):
        def change(plan):
            self.session.db.working_sets.add_requests(self.sid,['Fire Force']);return True
        with patch.object(self.window,'confirm_force_all',side_effect=change):
            with self.assertRaisesRegex(ValueError,'changed during confirmation'):self.window.force_reaudit_all()
        self.assertIsNone(self.window.worker);self.assertEqual(self.old,self.session.db.working_sets.item(self.uid)['pinned_audit_id'])

    def test_new_membership_during_running_batch_is_not_silently_added(self):
        OfflineAuditor.gate.clear();self.start()
        try:self.session.db.working_sets.add_requests(self.sid,['Fire Force'])
        finally:OfflineAuditor.gate.set();self.wait_idle()
        other=next(i for i in self.session.db.working_sets.items(self.sid) if i['original_query']=='Fire Force')
        self.assertEqual(('PENDING',None),(other['processing_status'],other['pinned_audit_id']))
        self.assertEqual(1,self.window.last_force_all['successful'])

    def test_current_provider_work_runs_off_gui_and_gui_remains_responsive(self):
        self.add_pending();entered=threading.Event();release=threading.Event();threads=[]
        fixture=batch_reference.ForceAll();fixture.before_search=None;fixture.after_item=None;fixture.bad_title=None
        def gate(auditor,query):
            threads.append(threading.get_ident());entered.set()
            if not release.wait(5):raise RuntimeError('Timeout')
        fixture.before_search=gate;self.window.auditor_factory=fixture.factory
        self.start()
        try:
            for _ in range(200):
                APP.processEvents();time.sleep(.005)
                if entered.is_set():break
            self.assertTrue(entered.is_set());self.window.refresh_all();APP.processEvents()
            self.assertEqual(self.old,self.session.db.working_sets.item(self.uid)['pinned_audit_id'])
            self.assertNotEqual(threading.get_ident(),threads[0])
        finally:release.set();self.wait_idle()
        self.assertEqual(3,self.window.last_force_all['successful'])

    def test_deferred_work_and_protected_sets_disable_action(self):
        self.window.deferred.add(self.uid);self.window.workflow.update_actions()
        self.assertFalse(self.window.workflow.force_all_action.isEnabled())
        with self.assertRaises(ValueError):self.window.force_reaudit_all()
        self.window.deferred.clear();self.session.db.working_sets.set_status(self.sid,'ARCHIVED');self.window.refresh_all()
        self.assertFalse(self.window.workflow.force_all_action.isEnabled())
        with self.assertRaises(ValueError):self.window.force_reaudit_all()


if __name__=='__main__':unittest.main()
