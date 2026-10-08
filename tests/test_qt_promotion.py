"""Promotion regressions; no real catalog or network access."""
import importlib.util
import os
import unittest
if importlib.util.find_spec('PySide6') is None:
    raise unittest.SkipTest('Install requirements-qt.txt in the workspace environment')
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
from unittest.mock import patch
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication, QLabel, QPushButton
from qt_app.main_window import MainWindow
from qt_app.session import Session
from qt_app.theme import apply_theme, font_assets, font_family
from qt_app.icons import icon
from ddk_build import qt_assets, qt_runtime_binaries

APP = QApplication.instance() or QApplication([])
apply_theme(APP)
ROOT = Path(__file__).resolve().parents[1]


class Promotion(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.session = Session(self.root/'catalog.db', create=True, role='TEST')
        self.window = MainWindow(self.session, QSettings(str(self.root/'ui.ini'), QSettings.IniFormat))
        self.window.show(); APP.processEvents()
        self.addCleanup(self.cleanup)

    def cleanup(self):
        self.window.close(); APP.processEvents(); self.session.close(); self.temp.cleanup()

    def test_selection_error_stays_in_curate_and_remains_visible(self):
        self.window.navigate('Curate')
        def blocked(): raise ValueError('Select one exact chapter.')
        with patch('qt_app.main_window.QMessageBox.exec') as dialog:
            self.window.safe(blocked)
            dialog.assert_called_once()
        self.assertEqual('Select one exact chapter.', self.window.status_label.text())
        for page in ('Catalog', 'Audit', 'Problems', 'History', 'Details'):
            self.window.navigate(page)
            self.assertNotIn('Select one exact chapter.', self.window.status_label.text())
        self.window.navigate('Curate')
        self.assertEqual('Select one exact chapter.', self.window.status_label.text())

    def test_async_audit_feedback_does_not_overwrite_history(self):
        self.window.navigate('History'); self.window.feedback('Copied event')
        self.window.audit_feedback('Running… resolving publication')
        self.assertEqual('Copied event', self.window.status_label.text())
        for page in ('Catalog', 'Audit'):
            self.window.navigate(page); self.assertIn('Running…', self.window.status_label.text())

    def test_database_switch_clears_old_feedback(self):
        self.window.feedback('Old database guidance')
        self.window.switch_database(self.root/'other.db', create=True, role='TEST')
        self.assertNotIn('Old database guidance', self.window.status_label.text())

    def test_sidebar_has_navigation_style_and_exclusive_state(self):
        for name, button in self.window.sidebar_buttons.items():
            self.assertTrue(button.property('navigation')); self.assertFalse(button.icon().isNull())
            self.window.navigate(name); APP.processEvents()
            self.assertEqual(1, sum(b.isChecked() for b in self.window.sidebar_buttons.values()))
            self.assertGreaterEqual(button.height(), 36)

    def test_only_run_is_primary_catalog_action(self):
        self.assertTrue(self.window.catalog.run_button.property('primary'))
        self.assertFalse(self.window.catalog.accept_all_button.property('primary'))
        for text in ('Open Review Items', 'Retry Errors'):
            action=next(b for b in self.window.catalog.findChildren(QPushButton) if b.text()==text)
            self.assertFalse(action.property('primary'));self.assertIsNone(action.menu())

    def test_empty_inspector_is_centered_without_layout_jump(self):
        inspector = self.window.catalog.inspector
        width = inspector.width()
        inspector.display('Select a row', {})
        self.assertTrue(inspector.property('empty'))
        label = next(l for l in inspector.findChildren(QLabel) if l.text()=='Select a row')
        self.assertEqual(Qt.AlignCenter, label.alignment()); self.assertFalse(label.property('pageTitle'))
        inspector.display('Work', {'Identity': {'Edition': 'standard'}}); APP.processEvents()
        self.assertFalse(inspector.property('empty')); self.assertEqual(width, inspector.width())

    def test_catalog_inspector_clears_when_switching_to_empty_set(self):
        from test_working_sets import publication
        db=self.session.db; db.add_titles(['Monster'],'standard','en')
        wid=db.works()[0]['id']
        audit=db.save_audit(wid,dict(query='Monster',match_title='Monster',publication=publication()),[])
        uid=db.working_sets.create('With work');db.working_sets.add_requests(uid,['Monster'])
        item=db.working_sets.items(uid)[0]['working_set_item_uuid'];db.working_sets.pin(item,wid,audit)
        self.window.activate_set(uid);self.window.catalog.table.selectRow(0);APP.processEvents()
        self.assertFalse(self.window.catalog.inspector.property('empty'))
        self.window.activate_set(db.working_sets.create('Empty'))
        self.assertEqual(0,self.window.catalog.table.proxy.rowCount())
        self.assertTrue(self.window.catalog.inspector.property('empty'))

    def test_filter_context_visible_and_backend_values_preserved(self):
        captions = [l.text() for l in self.window.problems.findChildren(QLabel)]
        for text in ('Class', 'Action', 'Disposition'): self.assertIn(text, captions)
        self.assertIn('Event Type', [l.text() for l in self.window.pages['History'].findChildren(QLabel)])
        self.assertEqual('All', self.window.problems.filters['class'].currentText())
        self.window.problems.filters['class'].setCurrentText('RESEARCH')
        self.assertEqual('RESEARCH', self.window.problems.filters['class'].currentText())

    def test_controls_fit_minimum_and_scopes_stay_beside_heading(self):
        self.window.resize(1120, 720)
        for name, page in self.window.pages.items():
            self.window.navigate(name); APP.processEvents()
            if name=='Workflow':
                self.assertFalse(page.scope_box.isVisible())
                self.assertTrue(self.window.set_button.isVisible())
            else:self.assertTrue(page.scope_box.isVisible())
            title = next(l for l in page.findChildren(QLabel) if l.text()==name and l.property('pageTitle'))
            self.assertLess(page.scope_box.x()-title.geometry().right(), 40)
            for layout in (page.toolbar, page.filterbar):
                for i in range(layout.count()):
                    widget=layout.itemAt(i).widget()
                    if widget and widget.isVisible():
                        self.assertLessEqual(widget.geometry().right(), page.width())
        self.assertEqual(9, self.window.details.tabs.count())
        self.assertTrue(self.window.details.tabs.tabBar().usesScrollButtons())

    def test_font_paths_optional_assets_and_icons(self):
        self.assertEqual(ROOT/'qt_app'/'assets'/'fonts', font_assets())
        self.assertTrue(font_family()); self.assertTrue(font_family(True))
        for name in self.window.pages: self.assertFalse(icon(name).pixmap(24,24).isNull())
        self.assertEqual([], qt_assets(self.root))
        fonts=self.root/'qt_app'/'assets'/'fonts'; fonts.mkdir(parents=True)
        self.assertEqual([(str(fonts), 'qt_app/assets/fonts')], qt_assets(self.root))

    def test_primary_and_legacy_launch_and_specs(self):
        primary=(ROOT/'Launch_MangaAnka_DDK.bat').read_text()
        self.assertIn('dist\\MangaAnka-Database-Development-Kit.exe', primary)
        self.assertIn('start ""', primary)
        self.assertIn('Launch_MangaAnka_DDK_Qt.bat', primary)
        self.assertIn('mangaanka_qt.py', (ROOT/'Launch_MangaAnka_DDK_Qt.bat').read_text())
        self.assertIn('mangaanka_database_development_kit.py', (ROOT/'Launch_MangaAnka_DDK_Legacy_Tk.bat').read_text())
        spec=(ROOT/'MangaAnka-Database-Development-Kit.spec').read_text()
        self.assertIn('/mangaanka_qt.py', spec); self.assertIn("startswith('mangaanka_search_core.')", spec)
        import mangaanka_database_development_kit as legacy
        self.assertTrue(callable(legacy.App))

    def test_windows_bundle_does_not_shadow_system_icu(self):
        entries=[('icuuc.dll','poppler/icuuc.dll','BINARY'),('icudt78.dll','poppler/icudt78.dll','BINARY'),
                 ('PySide6/Qt6Core.dll','qt/Qt6Core.dll','BINARY'),('PySide6/plugins/platforms/qwindows.dll','qt/qwindows.dll','BINARY')]
        self.assertEqual(entries[2:], qt_runtime_binaries(entries, 'win32'))

    def test_non_windows_dependencies_unchanged(self):
        entries=[('libicuuc.so','libicuuc.so','BINARY')]
        self.assertEqual(entries, qt_runtime_binaries(entries, 'linux'))


if __name__ == '__main__': unittest.main()
