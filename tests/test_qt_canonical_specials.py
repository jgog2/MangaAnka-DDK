"""Existing publication badges expose shared types without a Qt redesign."""
import unittest
import test_qt_publication_states as previous
from test_canonical_specials import captured_dandadan
from ddk_publication import publication_holes
APP=previous.APP

class QtCanonicalSpecials(unittest.TestCase):
    setUp=previous.QtPublicationStates.setUp
    cleanup=previous.QtPublicationStates.cleanup

    def install(self):
        pub,inv=captured_dandadan()
        db=self.session.db
        db.save_audit(self.wid,dict(query='Serialized fixture',match_title='Serialized fixture',publication=pub,selected_source='mangapill'),publication_holes(pub,inv))
        return pub

    def test_map_shows_acquired_and_missing_special_types(self):
        self.install();self.window.open_curate(self.wid,'all');APP.processEvents()
        nodes={n.row['key']:n for n in self.window.curate.map.publication.by_iid.values()}
        for key in ('32.5','40.5'):
            self.assertEqual('special',nodes[key].row['effective']['type'])
            self.assertIn('RECOGNIZED SPECIAL',nodes[key].values[1])
        self.assertEqual('extra',nodes['201.5'].row['effective']['type'])
        self.assertIn('MISSING ACQUISITION',nodes['201.5'].values[1])
        self.assertIn('PROVIDER ARTIFACT',nodes['193.1'].values[1])
        self.assertEqual('chapter',nodes['193'].row['effective']['type'])

    def test_details_raw_data_retains_type_evidence_and_coverage(self):
        self.install();self.window.open_details(self.wid,'all');APP.processEvents()
        raw=self.window.details.panes['Raw Data'].toPlainText()
        for token in ('provider_coverage','special_records','_type_source_identity','missing_special_acquisition'):
            self.assertIn(token,raw)

    def test_inspectors_distinguish_main_special_and_logical_counts(self):
        from PySide6.QtWidgets import QLabel
        from ddk_exports import catalog_context
        self.install();c=catalog_context(self.session.db,self.wid)
        self.assertEqual((246,2,248,219),tuple(c[k] for k in ('canonical_main_chapters','acquired_specials','logical_publication_units','mapped_main_chapters')))
        self.window.open_details(self.wid,'all');APP.processEvents()
        texts=[w.text() for w in self.window.details.panes['Overview'].findChildren(QLabel)]
        for text in ('Canonical Main Chapters','Acquired Specials','Logical Publication Units','246','248','2'):
            self.assertIn(text,texts)
        self.assertNotIn('Canonical Chapters',texts)
        self.window.catalog.refresh();self.window.catalog.table.selectRow(0);APP.processEvents()
        texts=[w.text() for w in self.window.catalog.inspector.findChildren(QLabel)]
        self.assertIn('Canonical Main Chapters',texts);self.assertIn('Logical Publication Units',texts)

if __name__=='__main__':unittest.main()
