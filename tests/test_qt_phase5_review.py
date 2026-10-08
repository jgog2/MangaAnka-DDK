"""Small review UX changes preserve independent evidence and Preview/Apply."""
import hashlib
import unittest
from unittest.mock import patch
import test_qt_supplementary_persistence as baseline
from PySide6.QtWidgets import QPushButton
from ddk_schema import SCHEMA_VERSION
from ddk_review import GRAMMAR_VERSION


class ReviewEvidenceUX(unittest.TestCase):
    setUp=baseline.QtPersistentSupplementary.setUp
    cleanup=baseline.QtPersistentSupplementary.cleanup
    dialog=baseline.QtPersistentSupplementary.dialog
    def test_loaded_evidence_generates_hash_time_without_claiming_equivalence(self):
        dialog=self.dialog();dialog.complete.setChecked(False);dialog.evidence_url.clear();dialog.evidence_hash.clear();dialog.captured.clear()
        evidence=self.root/'captured-proof.txt';evidence.write_bytes(b'SYNTHETIC independent comparison capture')
        dialog.load_evidence_file(evidence)
        self.assertEqual(hashlib.sha256(evidence.read_bytes()).hexdigest(),dialog.evidence_hash.text())
        self.assertTrue(dialog.captured.text())
        self.assertFalse(dialog.complete.isChecked());self.assertEqual('',dialog.evidence_url.text())
        self.assertIn(evidence.name,dialog.evidence_status.text())
        dialog.preview_binding();self.assertIsNone(self.window.command.pending);dialog.deleteLater()

    def test_empty_evidence_file_does_not_replace_provenance(self):
        dialog=self.dialog();prior=dialog.evidence_hash.text();evidence=self.root/'empty';evidence.write_bytes(b'')
        with self.assertRaisesRegex(ValueError,'empty'):dialog.load_evidence_file(evidence)
        self.assertEqual(prior,dialog.evidence_hash.text());dialog.deleteLater()

    def test_evidence_file_limit_preserves_gui_responsiveness(self):
        dialog=self.dialog();evidence=self.root/'too-large';evidence.write_bytes(b'0'*(5*1024*1024+1))
        with self.assertRaisesRegex(ValueError,'5 MiB'):dialog.load_evidence_file(evidence)
        dialog.deleteLater()

    def test_cancel_file_picker_preserves_review(self):
        dialog=self.dialog();prior=dialog.evidence_hash.text()
        with patch('qt_app.widgets.supplementary_review.QFileDialog.getOpenFileName',return_value=('','')):dialog.choose_evidence_file()
        self.assertEqual(prior,dialog.evidence_hash.text());dialog.deleteLater()

    def test_about_uses_actual_schema_and_grammar_contracts(self):
        with patch.object(self.window,'show_text') as show:self.window.show_about()
        text=show.call_args.args[1];self.assertIn(f'Schema v{SCHEMA_VERSION}',text);self.assertIn(f'Grammar {GRAMMAR_VERSION}',text)

if __name__=='__main__':unittest.main()
