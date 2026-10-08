"""Startup/session restoration with isolated settings and disposable catalogs."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication
from qt_app.app import main
from qt_app.main_window import MainWindow
from qt_app.preferences import database_key, remember_session, restore_session, restore_working_set
from qt_app.session import Session

APP=QApplication.instance() or QApplication([])


class SessionRestore(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.settings=QSettings(str(self.root/'preferences.ini'),QSettings.IniFormat)
        self.sessions=[];self.windows=[]
        self.addCleanup(self.cleanup)
        guard=patch('urllib.request.urlopen',side_effect=AssertionError('Unexpected network'))
        guard.start();self.addCleanup(guard.stop)

    def cleanup(self):
        for w in self.windows:w.close()
        APP.processEvents()
        for s in self.sessions:s.close()
        self.temp.cleanup()

    def create(self,name='catalog.db'):
        session=Session(self.root/name,create=True,role='TEST');self.sessions.append(session)
        return session

    def remember(self,session):
        remember_session(session,self.settings);session.close()

    def restore(self):
        s,note=restore_session(self.settings)
        if s:self.sessions.append(s)
        return s,note

    def test_first_launch_no_remembered_database_opens_nothing(self):
        with patch('qt_app.preferences.Session') as opening:
            self.assertEqual((None,''),self.restore());opening.assert_not_called()

    def test_valid_path_with_spaces_restores_without_catalog_mutation(self):
        s=self.create('My catalog.db');uid=s.db.working_sets.create('A3');s.activate_working_set(uid)
        self.remember(s);before=s.db.path.read_bytes()
        restored,note=self.restore()
        self.assertEqual('',note);self.assertEqual(s.db.path,restored.db.path)
        self.assertEqual(uid,restored.active_uuid);self.assertEqual('TEST',restored.db.role)
        self.assertEqual(before,s.db.path.read_bytes())

    def test_unicode_path_is_exact_and_restores(self):
        s=self.create('漫画 MangaAnkā.db');self.remember(s)
        restored,note=self.restore();self.assertEqual('',note)
        self.assertEqual(s.db.path,restored.db.path)

    def test_missing_database_is_not_created_or_substituted(self):
        path=self.root/'missing.db';self.settings.setValue('session/last_database',str(path))
        restored,note=self.restore();self.assertIsNone(restored);self.assertIn('Could not reopen',note)
        self.assertFalse(path.exists());self.assertFalse(Path(str(path)+'.writer.lock').exists())
        self.assertEqual(str(path),self.settings.value('session/last_database'))

    def test_invalid_corrupt_newer_schema_and_directory_fail_without_replacement(self):
        for kind in ('invalid','corrupt','newer','directory'):
            path=self.root/(kind+'.db')
            if kind=='corrupt':path.write_bytes(b'not sqlite')
            elif kind=='directory':path.mkdir()
            elif kind=='newer':
                s=self.create(path.name);s.close()
                with sqlite3.connect(path) as c:c.execute('PRAGMA user_version=9')
            else:
                with sqlite3.connect(path) as c:c.execute('CREATE TABLE unrelated(id)')
            before=path.read_bytes() if path.is_file() else None
            self.settings.setValue('session/last_database',str(path));restored,note=self.restore()
            self.assertIsNone(restored);self.assertTrue(note)
            if before is not None:self.assertEqual(before,path.read_bytes())

    def test_inaccessible_database_falls_back_without_creation(self):
        s=self.create();self.remember(s)
        with patch('qt_app.session.validate_database',side_effect=PermissionError('Access denied')):
            restored,note=self.restore()
        self.assertIsNone(restored);self.assertIn('Access denied',note)

    def test_another_writer_is_not_bypassed(self):
        s=self.create();remember_session(s,self.settings)
        restored,note=self.restore();self.assertIsNone(restored);self.assertIn('another DDK instance',note)
        s.close();self.assertIsNotNone(self.restore()[0])

    def test_per_database_working_sets_survive_a_b_switches(self):
        a=self.create('A.db');a3=a.db.working_sets.create('A3');a.activate_working_set(a3)
        remember_session(a,self.settings)
        b=self.create('B.db');b7=b.db.working_sets.create('B7');b.activate_working_set(b7)
        remember_session(b,self.settings)
        for s,uid in ((a,a3),(b,b7),(a,a3)):
            s.restore_working_set(None);restore_working_set(s,self.settings);self.assertEqual(uid,s.active_uuid)
        self.assertNotEqual(database_key(a.db.path),database_key(b.db.path))

    def test_remembered_selection_does_not_write_backend_active_selection(self):
        s=self.create();one=s.db.working_sets.create('One');two=s.db.working_sets.create('Two')
        s.activate_working_set(one);remember_session(s,self.settings)
        s.activate_working_set(two);before=s.db.path.read_bytes()
        restore_working_set(s,self.settings)
        self.assertEqual(one,s.active_uuid);self.assertEqual(two,s.db.working_sets.active_uuid())
        self.assertEqual(before,s.db.path.read_bytes())
        s.activate_working_set(two);self.assertEqual(two,s.active_uuid)

    def test_deleted_remembered_set_falls_back_to_existing_active(self):
        s=self.create();one=s.db.working_sets.create('One');two=s.db.working_sets.create('Two')
        s.activate_working_set(one);remember_session(s,self.settings)
        s.activate_working_set(two)
        with s.db.con() as c:c.execute('DELETE FROM working_sets WHERE working_set_uuid=?',(one,))
        restore_working_set(s,self.settings);self.assertEqual(two,s.active_uuid)

    def test_complete_and_archived_restore_view_without_reopening_or_accepting(self):
        for status in ('COMPLETE','ARCHIVED'):
            s=self.create(status+'.db');uid=s.db.working_sets.create(status);s.activate_working_set(uid)
            with s.db.con() as c:c.execute('UPDATE working_sets SET status=? WHERE working_set_uuid=?',(status,uid))
            self.remember(s);before=s.db.path.read_bytes();restored,_=self.restore()
            self.assertEqual(uid,restored.active_uuid);self.assertEqual(status,restored.db.working_sets.get(uid)['status'])
            with self.assertRaisesRegex(ValueError,'protected'):restored.db.working_sets.guard(set_uuid=uid)
            self.assertEqual(before,s.db.path.read_bytes())

    def test_replaced_database_at_same_path_cannot_restore_foreign_uuid(self):
        s=self.create();uid=s.db.working_sets.create('One');s.activate_working_set(uid);self.remember(s)
        old_uuid=s.db.database_uuid
        other=self.create('other.db');other.close()
        # Simulate external path replacement, only inside this disposable directory.
        s.db.path.write_bytes(other.db.path.read_bytes())
        restored,_=self.restore();self.assertIsNone(restored.active_uuid)
        self.assertNotEqual(old_uuid,restored.db.database_uuid)

    def test_main_window_remembers_successful_switch_and_explicit_set_selection(self):
        s=self.create();w=MainWindow(s,self.settings);self.windows.append(w)
        uid=s.db.working_sets.create('A3');w.activate_set(uid)
        self.assertEqual(uid,self.settings.value('session/databases/'+database_key(s.db.path)+'/working_set_uuid'))
        old=s.db.path;w.switch_database(self.root/'B.db',create=True,role='TEST')
        self.assertEqual(str(s.db.path),self.settings.value('session/last_database'))
        w.switch_database(old);self.assertEqual(uid,s.active_uuid)

    def test_failed_switch_keeps_open_session_and_successful_preference(self):
        s=self.create();w=MainWindow(s,self.settings);self.windows.append(w);old=s.db.path
        with self.assertRaises(ValueError):w.switch_database(self.root/'missing.db')
        self.assertEqual(old,s.db.path);self.assertEqual(str(old),self.settings.value('session/last_database'))

    def test_predictable_workflow_landing_ignores_arbitrary_last_page(self):
        self.settings.setValue('last_page','Curate');s=self.create()
        w=MainWindow(s,self.settings);self.windows.append(w)
        self.assertEqual('Workflow',w.stack.currentWidget().name)
        self.assertEqual(7,w.stack.count());self.assertIn('Workflow',w.pages)

    def test_auto_restore_failure_uses_nonblocking_picker_explanation(self):
        self.settings.setValue('session/last_database',str(self.root/'missing.db'));self.settings.sync()
        with patch('qt_app.app.QApplication',return_value=APP),patch('qt_app.app.QDialog.exec',return_value=0),\
             patch('qt_app.app.QMessageBox.critical') as critical,patch('qt_app.app.QMessageBox.warning') as warning,\
             patch('qt_app.app.QLabel',wraps=__import__('PySide6.QtWidgets',fromlist=['QLabel']).QLabel) as label:
            self.assertEqual(0,main(['--ui-settings',str(self.root/'preferences.ini')]))
        critical.assert_not_called();warning.assert_not_called()
        self.assertIn('Could not reopen',label.call_args.args[0])

    def test_startup_restores_normal_session_without_database_picker(self):
        s=self.create();self.remember(s)
        with patch('qt_app.app.QApplication',return_value=APP),patch.object(APP,'exec',return_value=0),\
             patch('qt_app.app.QDialog.exec') as picker,patch('qt_app.app.MainWindow') as window:
            self.assertEqual(0,main(['--ui-settings',str(self.root/'preferences.ini')]))
        picker.assert_not_called()
        opened=window.call_args.args[0];self.sessions.append(opened)
        self.assertEqual(s.db.path,opened.db.path)

    def test_explicit_database_overrides_remembered_path(self):
        a=self.create('A.db');self.remember(a);b=self.create('B.db');b.close()
        with patch('qt_app.app.QApplication',return_value=APP),patch.object(APP,'exec',return_value=0),\
             patch('qt_app.app.MainWindow') as window:
            self.assertEqual(0,main(['--database',str(b.db.path),'--ui-settings',str(self.root/'preferences.ini')]))
        opened=window.call_args.args[0];self.sessions.append(opened)
        self.assertEqual(b.db.path,opened.db.path)

    def test_missing_backend_and_remembered_selection_is_safe_empty_context(self):
        s=self.create();uid=s.db.working_sets.create('Gone');s.activate_working_set(uid);remember_session(s,self.settings)
        with s.db.con() as c:c.execute('DELETE FROM working_sets WHERE working_set_uuid=?',(uid,))
        restore_working_set(s,self.settings);self.assertIsNone(s.active_uuid)

    def test_malformed_working_set_preference_is_ignored(self):
        s=self.create();uid=s.db.working_sets.create('One');s.activate_working_set(uid);remember_session(s,self.settings)
        self.settings.setValue('session/databases/'+database_key(s.db.path)+'/working_set_uuid',['bad','value'])
        restore_working_set(s,self.settings);self.assertEqual(uid,s.active_uuid)

    def test_settings_write_failure_is_nonblocking(self):
        s=self.create()
        with patch.object(self.settings,'sync',side_effect=OSError('Preferences unavailable')):
            w=MainWindow(s,self.settings);self.windows.append(w)
        self.assertIn('preferences could not be saved',w.status_label.text())
        self.assertEqual(s.db,w.db)


if __name__=='__main__':unittest.main()
