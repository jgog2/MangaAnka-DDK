"""Existing Qt inspectors and problem actions share audit health/provenance."""
import json
import unittest
from PySide6.QtWidgets import QGroupBox, QFormLayout
import test_qt_publication_states as previous
from ddk_publication import publication_holes
from test_publication_states import fixture

APP=previous.APP


def health_fields(inspector):
    group=next(g for g in inspector.findChildren(QGroupBox) if g.title()=='Health')
    form=group.layout()
    return {form.itemAt(i,QFormLayout.LabelRole).widget().text().casefold():
            form.itemAt(i,QFormLayout.FieldRole).widget().text() for i in range(form.rowCount())}


class QtAtsuHealth(unittest.TestCase):
    setUp=previous.QtPublicationStates.setUp
    cleanup=previous.QtPublicationStates.cleanup

    def test_catalog_and_details_render_identical_persisted_health(self):
        expected=json.loads(self.session.db.audit(self.audit,self.wid)['health_json'])
        self.window.catalog.table.selectRow(0);APP.processEvents()
        self.assertEqual(expected,health_fields(self.window.catalog.inspector))
        self.window.open_details(self.wid,'all');APP.processEvents()
        self.assertEqual(expected,health_fields(self.window.details.panes['Overview']))

    def test_selected_problem_copy_and_export_context_have_whole_audit_health(self):
        self.window.problems.set_scope('all');self.window.problems.refresh();APP.processEvents()
        expected=json.loads(self.session.db.audit(self.audit,self.wid)['health_json'])
        for row in range(self.window.problems.table.proxy.rowCount()):
            self.window.problems.table.selectRow(row);APP.processEvents()
            self.assertEqual(expected,self.window.problems.packet()['works'][0]['health'])
            text=self.window.problems.diagnostic()
            self.assertIn('"normalization": "REVIEW"',text)
            self.assertIn('"acquisition": "PARTIAL"',text)

    def test_acquisition_table_retains_provider_inspection_and_group_provenance(self):
        res,_=fixture();pub=dict(self.pub,provider_group_acquisition=dict(primary_group='a',raw_count=33,
            recommendation_basis='api_recommended_order',alternatives=[dict(chapter='19.5',_scanlation_id='b',
            recovered=False,requires_review=False,classification='alternate_fractional')]))
        self.session.db.save_audit(self.wid,dict(query='Serialized fixture',publication=pub,
            inventories=[dict(source_id='atsu',source_name='Atsu',chapter_count=31,usable=True)]),publication_holes(pub,res.primary))
        self.window.open_details(self.wid,'all');APP.processEvents()
        table=self.window.details.panes['Acquisition'];self.assertEqual(1,table.proxy.rowCount())
        table.selectRow(0);APP.processEvents()
        from PySide6.QtWidgets import QLabel
        text=' '.join(l.text() for l in self.window.details.inspector.findChildren(QLabel))
        self.assertIn('Scanlation groups',str([g.title() for g in self.window.details.inspector.findChildren(QGroupBox)]))
        self.assertIn('33',text);self.assertIn('api_recommended_order',text)


if __name__=='__main__':unittest.main()
