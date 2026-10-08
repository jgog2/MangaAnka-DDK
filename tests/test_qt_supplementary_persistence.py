"""Actual Qt review form → drawer → Apply/undo/redo on a disposable catalog."""
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtCore import QSettings,Qt
from PySide6.QtWidgets import QLabel
from qt_app.session import Session
from qt_app.main_window import MainWindow
from qt_app.widgets.supplementary_review import SupplementaryReview
from ddk_supplementary_commands import command_text
from test_qt_publication_states import APP
from test_supplementary_persistence import seed,binding_payload


class QtPersistentSupplementary(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.session=Session(self.root/'catalog.db',create=True,role='TEST');self.db=self.session.db
        self.wid,self.aid,self.pub=seed(self.db)
        self.key=self.pub['supplementary_identity']['identities'][0]['identity']['opaque_id']
        self.window=MainWindow(self.session,QSettings(str(self.root/'ui.ini'),QSettings.IniFormat))
        self.window.show();self.window.open_curate(self.wid,'all');APP.processEvents()
        self.addCleanup(self.cleanup)

    def cleanup(self):
        self.window.close();APP.processEvents();self.session.close();self.tmp.cleanup()

    def dialog(self):
        dialog=SupplementaryReview(self.window,self.wid,'all',self.key)
        dialog.reviewer.setText('SYNTHETIC Qt reviewer');dialog.note.setText('SYNTHETIC complete content review, not production.')
        for i in range(dialog.candidate.count()):
            row=dialog.candidates[dialog.candidate.itemData(i)]
            if row['original_label']=='19.5':dialog.candidate.setCurrentIndex(i);break
        dialog.evidence_url.setText('https://example.org/synthetic-proof');dialog.evidence_hash.setText('c'*64)
        dialog.captured.setText('2026-10-07T12:00:00+00:00');dialog.complete.setChecked(True)
        return dialog

    def apply_binding(self):
        dialog=self.dialog();dialog.preview_binding();self.assertTrue(self.window.command.pending)
        self.assertEqual(0,self.db.supplementary.revision(self.wid))
        self.window.drawer.apply();APP.processEvents();dialog.deleteLater()
        self.assertEqual(1,self.db.supplementary.revision(self.wid))

    def test_complete_form_preview_apply_persists_effective_binding(self):
        self.apply_binding()
        self.assertIsNone(self.window.command.pending)
        self.assertEqual(1,self.db.supplementary.for_audit(self.wid,current=True)['summary']['verified_acquired'])
        self.assertEqual(self.pub['canonical_main_chapters'],json.loads(self.db.latest_audit(self.wid)['publication_json'])['canonical_main_chapters'])

    def test_form_undo_redo_use_separate_journal_and_explicit_apply(self):
        self.apply_binding()
        for redo,expected in ((False,0),(True,1)):
            dialog=self.dialog();dialog.preview_reverse(redo)
            self.assertTrue(self.window.command.pending);self.window.drawer.apply();APP.processEvents();dialog.deleteLater()
            self.assertEqual(expected,self.db.supplementary.for_audit(self.wid,current=True)['summary']['verified_acquired'])
        self.assertEqual([],self.db.catalog.history(self.wid))
        self.assertEqual(3,len(self.db.supplementary.history(self.wid)))

    def test_incomplete_content_review_blocks_preview_and_apply(self):
        dialog=self.dialog();dialog.complete.setChecked(False);dialog.preview_binding()
        self.assertIsNone(self.window.command.pending);self.assertFalse(self.window.drawer.apply_button.isEnabled())
        self.assertIn('complete-content',self.window.drawer.output.toPlainText());dialog.deleteLater()

    def test_selection_stays_opaque_and_review_action_available(self):
        self.window.curate.map.focus_keys([self.key]);APP.processEvents()
        self.assertEqual(set(),self.window.command.selection)
        from PySide6.QtWidgets import QPushButton
        texts=[b.text() for b in self.window.curate.inspector.findChildren(QPushButton)]
        self.assertIn('Review Supplementary',texts)
        with self.assertRaises(ValueError):self.window.command.execute('set volume 38 chapter '+self.key)

    def test_membership_form_is_independent_and_reversible(self):
        dialog=self.dialog();dialog.preview_membership();self.assertTrue(self.window.command.pending)
        self.window.drawer.apply();APP.processEvents();dialog.deleteLater()
        current=self.db.supplementary.for_audit(self.wid,current=True)
        self.assertEqual(0,current['summary']['verified_acquired'])
        self.assertEqual('membership',current['reviewed_state']['decisions'][0]['kind'])

    def test_mixed_numeric_and_supplementary_batch_rejected(self):
        with self.assertRaisesRegex(ValueError,'cannot share'):
            self.window.command.execute('select chapter 1\nsupplement list')

    def test_dialog_scroll_and_scope_guard_without_network(self):
        with patch('urllib.request.urlopen',side_effect=AssertionError('GUI network forbidden')):
            dialog=self.dialog();dialog.show();APP.processEvents()
            from PySide6.QtWidgets import QScrollArea
            scroll=dialog.findChild(QScrollArea)
            self.assertEqual(Qt.ScrollBarAlwaysOn,scroll.verticalScrollBarPolicy())
            self.assertGreater(scroll.verticalScrollBar().maximum(),0)
            self.assertTrue(dialog.raw.toPlainText());dialog.close();dialog.deleteLater()

    def test_guardless_mutation_is_blocked(self):
        payload=binding_payload(self.db,self.wid)
        text=command_text('ignored','bind',self.key,payload).split('\n',1)[1]
        with self.assertRaisesRegex(ValueError,'current guard'):self.window.command.execute(text)

    def test_preview_invalidated_when_guard_changes(self):
        dialog=self.dialog();dialog.preview_binding();dialog.deleteLater()
        self.db.save_audit(self.wid,dict(publication=self.pub),[])
        self.window.drawer.apply();APP.processEvents()
        self.assertEqual(0,self.db.supplementary.revision(self.wid))
        self.assertIn('Stale',self.window.drawer.output.toPlainText())


if __name__=='__main__':unittest.main()
