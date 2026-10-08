"""Display-only opaque rows cannot become Grammar 3 chapter selections."""
import unittest
from PySide6.QtWidgets import QLabel
from ddk_supplementary import collect_supplements
from test_supplementary_integration import book
import test_qt_publication_states as previous

APP=previous.APP


class QtSupplementary(unittest.TestCase):
    setUp=previous.QtPublicationStates.setUp
    cleanup=previous.QtPublicationStates.cleanup

    def install(self):
        pub=self.pub
        pub['supplementary_identity']=collect_supplements(dict(supplementary_publications=[book()]),
                                                       pub['projection'],pub['catalog_identity'])
        self.session.db.save_audit(self.wid,dict(query='Serialized fixture',match_title='Serialized fixture',publication=pub),[])
        return pub['supplementary_identity']['identities'][0]['identity']['opaque_id']

    def test_publication_map_separates_opaque_evidence_from_volumes(self):
        key=self.install();self.window.open_curate(self.wid,'all');APP.processEvents()
        model=self.window.curate.map.publication
        self.assertIn(key,model.by_iid)
        self.assertTrue(model.by_iid[key].parent.values[0].startswith('Supplementary'))
        self.assertNotIn(key,[r['key'] for r in self.window.curate.rows])
        self.assertIsNone(model.by_iid[key].row['effective']['volume'])
        self.assertEqual('Supplement · A supplementary story',model.by_iid[key].values[0])

    def test_supplementary_selection_cannot_target_chapter_commands(self):
        key=self.install();self.window.open_curate(self.wid,'all');APP.processEvents()
        self.window.command.selection={'0'}
        self.window.curate.map.focus_keys([key]);APP.processEvents()
        self.assertEqual(set(),self.window.command.selection)
        text=' '.join(w.text() for w in self.window.curate.inspector.findChildren(QLabel))
        self.assertIn('Grammar 3',text)

    def test_details_includes_independent_states_and_raw_proof(self):
        key=self.install();self.window.open_details(self.wid,'all');APP.processEvents()
        pane=self.window.details.panes['Publication']
        pane.focus_keys([key]);APP.processEvents()
        text=' '.join(w.text() for w in self.window.details.inspector.findChildren(QLabel))
        for token in ('unresolved','separate_publication','language_or_edition_unverified'):self.assertIn(token,text)
        self.assertIn(key,self.window.details.panes['Raw Data'].toPlainText())

    def test_old_audit_has_no_opaque_map_nodes(self):
        self.window.open_curate(self.wid,'all');APP.processEvents()
        self.assertFalse(any(n.row.get('supplementary') for n in self.window.curate.map.publication.by_iid.values()))


if __name__=='__main__':unittest.main()
