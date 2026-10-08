"""Qt presentation of derived serialization state; disposable catalog only."""
import importlib.util
import os
import tempfile
import unittest
if importlib.util.find_spec('PySide6') is None:
    raise unittest.SkipTest('Qt tests require requirements-qt.txt')
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication, QLabel
from qt_app.main_window import MainWindow
from qt_app.session import Session
from qt_app.theme import apply_theme, status_color, TOKENS
from test_publication_states import fixture, resolved, stored

APP=QApplication.instance() or QApplication([])
apply_theme(APP)


class QtPublicationStates(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.session=Session(self.root/'catalog.db',create=True,role='TEST')
        self.addCleanup(self.cleanup)
        res,bundle=fixture();self.pub=resolved(res,bundle)
        self.wid,self.audit=stored(self.session.db,self.pub,res.primary)
        self.window=MainWindow(self.session,QSettings(str(self.root/'ui.ini'),QSettings.IniFormat))
        self.window.show();self.window.catalog.set_scope('all');self.window.catalog.refresh();APP.processEvents()

    def cleanup(self):
        self.window.close();APP.processEvents();self.session.close();self.temp.cleanup()

    def test_map_keeps_uncompiled_volumes_and_provider_records_separate(self):
        self.window.open_curate(self.wid,'all');APP.processEvents()
        model=self.window.curate.map.publication
        names=[n.values[0] for n in model.root.children]
        self.assertTrue(any(n.startswith('Volume 1') for n in names))
        group=next(n for n in model.root.children if n.values[0].startswith('Uncompiled'))
        self.assertEqual('UNCOMPILED',group.values[1]);self.assertEqual(10,len(group.children))
        self.assertEqual('21 · Chapter 21',group.children[0].values[0])
        self.assertEqual(TOKENS['blue'],status_color('UNCOMPILED'))
        provider=next(n for n in model.root.children if n.values[0].startswith('Provider-only'))
        self.assertEqual({'19.5','92.5'},{n.row['key'] for n in provider.children})
        special=model.by_iid['31']
        self.assertIn('89.1',special.values[0]);self.assertIn('RECOGNIZED SPECIAL',special.values[1])

    def test_catalog_breakdown_and_inspector(self):
        rows=self.window.session.catalog_rows('all')
        self.assertEqual('21 mapped · 10 uncompiled',rows[0]['chapter_display'])
        self.window.catalog.table.selectRow(0);APP.processEvents()
        texts=' '.join(l.text() for l in self.window.catalog.inspector.findChildren(QLabel))
        self.assertIn('uncompiled',texts.casefold());self.assertIn('10',texts)

    def test_problems_keep_unsupported_fraction_but_not_safe_suffix(self):
        self.window.problems.set_scope('all');self.window.problems.refresh();APP.processEvents()
        rows=self.window.problems.table.records.records
        text=str(rows)
        self.assertNotIn('UNMAPPED_CHAPTERS',text)
        self.assertIn('PROVIDER_FRACTIONAL_CANDIDATE',text)
        self.assertIn('MISSING_SPECIAL_ACQUISITION',text)

    def test_details_show_uncompiled_identifiers_and_specials(self):
        self.window.open_details(self.wid,'all');APP.processEvents()
        texts=' '.join(l.text() for l in self.window.details.panes['Overview'].findChildren(QLabel))
        self.assertIn('uncompiled identifiers',texts.casefold());self.assertIn('21',texts);self.assertIn('89.1',texts)
        raw=self.window.details.panes['Raw Data'].toPlainText()
        self.assertIn('recognized_special',raw);self.assertIn('uncompiled_identifiers',raw)

    def test_map_scrolling_and_minimum_geometry(self):
        self.window.resize(1120,720);self.window.open_details(self.wid,'all');APP.processEvents()
        view=self.window.details.panes['Publication']
        self.assertEqual(Qt.ScrollBarAlwaysOn,view.verticalScrollBarPolicy())
        self.assertTrue(self.window.details.tabs.tabBar().usesScrollButtons())
        self.assertTrue(self.window.details.scope_box.isVisible())
