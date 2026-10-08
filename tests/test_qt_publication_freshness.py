"""Freshness diagnostics on the existing dark, scrollable Qt surfaces."""
import unittest
from PySide6.QtWidgets import QLabel
import test_qt_publication_states as previous
APP=previous.APP


class QtPublicationFreshness(unittest.TestCase):
    setUp=previous.QtPublicationStates.setUp
    cleanup=previous.QtPublicationStates.cleanup

    def test_catalog_inspector_does_not_invent_coverage(self):
        self.window.catalog.table.selectRow(0);APP.processEvents()
        text=' '.join(w.text() for w in self.window.catalog.inspector.findChildren(QLabel))
        self.assertIn('Latest Released',text)
        self.assertIn('absent',text)
        self.assertNotIn('through chapter',text.casefold())

    def test_reference_details_show_runtime_boundary(self):
        self.window.open_details(self.wid,'all');APP.processEvents()
        text=' '.join(w.text() for w in self.window.details.panes['References'].findChildren(QLabel))
        self.assertIn('Latest Released Volume',text)
        raw=self.window.details.panes['Raw Data'].toPlainText()
        self.assertIn('release_boundary',raw);self.assertIn('catalog_freshness',raw)


if __name__=='__main__':unittest.main()
