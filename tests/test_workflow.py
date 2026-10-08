"""Workflow orchestration contracts; offline, disposable catalogs/settings only."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from qt_app.session import Session
from qt_app.main_window import MainWindow
from qt_app.orchestration import capture, resolve
from qt_app import export_receipts as receipts
from qt_app.workflow_presentation import next_action, summary, health_label
from test_working_set_audit_recovery import publication
from test_working_set_audit_recovery import offline_pipeline
import mangaanka_database_development_kit as ddk
from test_qt_frontend import OfflineAuditor, MockAuditor

APP=QApplication.instance() or QApplication([])


class CycleAuditor(ddk.SearchAuditor):
    def audit_many(self,ids,workflow):
        with offline_pipeline(self):
            resolved=ddk.resolve_publication.side_effect
            def resolve_fixture(*args,**kwargs):
                pub=resolved(*args,**kwargs)
                title=args[0].primary.result['title']
                if title=='New Series' or title=='Fire Force' and not pub['curation_revision']:
                    for row in pub['projection']:row['volume']=row['_effective_volume']=None
                    pub['mapped_chapters']=0;pub['unmapped_chapters']=pub['logical_chapters'];pub['final_volumes']=0
                    pub['unmapped']=list(pub['projection']);pub['automatic']=dict(pub)
                return pub
            with patch.object(ddk,'resolve_publication',side_effect=resolve_fixture):super().audit_many(ids,workflow)


class WorkflowPresentation(unittest.TestCase):
    def item(self,state='REVIEW',work_id=1):return dict(processing_status=state,work_id=work_id)
    def test_running_precedes_queued_and_protection(self):self.assertEqual('Auditing…',next_action(self.item('QUEUED'),'ARCHIVED',running=True))
    def test_persisted_auditing(self):self.assertEqual('Auditing…',next_action(self.item('AUDITING'),'OPEN'))
    def test_queued_precedes_protection(self):self.assertEqual('Re-Audit queued',next_action(self.item('QUEUED'),'COMPLETE'))
    def test_protected_set(self):self.assertEqual('Reopen Working Set',next_action(self.item(),'ARCHIVED'))
    def test_protected_terminal_item(self):self.assertEqual('Reopen selected for review',next_action(self.item('REJECTED'),'OPEN'))
    def test_accepted_stale(self):self.assertEqual('Reopen selected for review',next_action(self.item('ACCEPTED'),'OPEN',dict(needs_reaudit=True)))
    def test_error_retry(self):self.assertEqual('Retry error',next_action(self.item('ERROR'),'OPEN'))
    def test_pending_run(self):self.assertEqual('Run Working Set',next_action(self.item('PENDING',None),'OPEN'))
    def test_needs_reaudit(self):self.assertEqual('Run Working Set',next_action(self.item(),'OPEN',dict(needs_reaudit=True)))
    def test_code_review(self):self.assertEqual('Code review',next_action(self.item(),'OPEN',problems=[dict(next_action='CODE_REVIEW_REQUIRED')]))
    def test_research(self):self.assertEqual('Research required',next_action(self.item(),'OPEN',problems=[dict(next_action='RESEARCH_REQUIRED')]))
    def test_curation(self):self.assertEqual('Open Curate',next_action(self.item(),'OPEN',problems=[dict(next_action='CURATION_READY')]))
    def test_acquisition_only(self):self.assertEqual('Acquisition only',next_action(self.item(),'OPEN',problems=[dict(next_action='ACQUISITION_ONLY')]))
    def test_identity_block(self):self.assertEqual('Identity review',next_action(self.item(),'OPEN',problems=[dict(next_action='BLOCKED_IDENTITY'),dict(next_action='CODE_REVIEW_REQUIRED')]))
    def test_eligible(self):self.assertEqual('Accept eligible title',next_action(self.item('READY'),'OPEN',dict(eligible=True)))
    def test_accepted_current(self):self.assertEqual('In Catalog',next_action(self.item('ACCEPTED'),'OPEN',dict(eligible=True)))
    def test_duplicate(self):self.assertEqual('Duplicate intake',next_action(self.item('DUPLICATE',None),'OPEN'))
    def test_unlinked(self):self.assertEqual('Inspect intake',next_action(self.item('REVIEW',None),'OPEN'))
    def test_health_never_implies_acceptance(self):
        self.assertEqual('Good',health_label(dict(identity='PASS')))
        self.assertEqual('Inspect evidence',next_action(self.item('READY'),'OPEN',dict(eligible=False)))
    def test_mixed_summary(self):
        states=['PENDING','QUEUED','AUDITING','ERROR','REVIEW','ACCEPTED','REJECTED','DUPLICATE','READY']
        result=summary([self.item(s,None if s=='DUPLICATE' else 1) for s in states],{'exact':{}})
        self.assertEqual((9,1,1),(result['total'],result['eligible'],result['unlinked']))
        self.assertEqual(dict.fromkeys(states,1),result['counts'])
    def test_empty_summary(self):self.assertEqual(dict(total=0,eligible=0,counts={},unlinked=0),summary([],{}))


class Workflow(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.session=Session(self.root/'A 漫画 catalog.db',create=True,role='TEST');self.db=self.session.db
        self.db.add_titles(['Monster','Fire Force'],'standard','en')
        self.audits={}
        for wid,title in ((1,'Monster'),(2,'Fire Force')):
            self.audits[wid]=self.db.save_audit(wid,dict(query=title,match_title=title,publication=publication(title)),[])
        self.sid=self.db.working_sets.create('Batch A3');self.session.activate_working_set(self.sid)
        self.db.working_sets.add_requests(self.sid,['Monster','Fire Force'])
        self.items=self.db.working_sets.items(self.sid)
        for item,wid in zip(self.items,(1,2)):self.db.working_sets.pin(item['working_set_item_uuid'],wid,self.audits[wid])
        self.settings=QSettings(str(self.root/'ui.ini'),QSettings.IniFormat)
        self.w=MainWindow(self.session,self.settings,auditor_factory=OfflineAuditor);self.w.safe=lambda cb:cb()
        self.w.show();APP.processEvents();self.page=self.w.workflow
        self.addCleanup(self.cleanup)
        guard=patch('urllib.request.urlopen',side_effect=AssertionError('Unexpected network'));guard.start();self.addCleanup(guard.stop)

    def cleanup(self):
        MockAuditor.gate.set()
        if self.w.busy:self.w.cancel_run();self.wait_idle()
        self.w.close();APP.processEvents();self.session.close();self.temp.cleanup()

    def wait_idle(self):
        limit=time.monotonic()+15
        while self.w.busy and time.monotonic()<limit:APP.processEvents();time.sleep(.01)
        self.assertFalse(self.w.busy)

    def select(self,wid=1):
        self.page.table.select_record(lambda r:r['_work_id']==wid);APP.processEvents()
        return self.page.selected_context()

    def export(self,mode='pinned'):
        path=self.root/(mode+'.json')
        with patch('qt_app.main_window.QFileDialog.getSaveFileName',return_value=(str(path),'JSON')):
            self.w.export_review_packet(self.page.batch_context(),mode)
        return path

    def state(self,iid,state):
        with self.db.con() as c:c.execute('UPDATE working_set_items SET processing_status=? WHERE working_set_item_uuid=?',(state,iid))
        self.w.refresh_all()

    def digest(self,mode='pinned'):return receipts.fingerprint(self.db,self.sid,mode)

    def fresh(self,mode='pinned'):return receipts.status(self.settings,self.db,self.sid,mode)[0]

    def new_audit(self,wid=1):return self.db.save_audit(wid,dict(query=self.db.work(wid)['input_title'],match_title=self.db.work(wid)['input_title'],publication=publication(self.db.work(wid)['input_title'])),[])

    def test_landing_seven_pages(self):
        self.assertEqual('Workflow',self.w.stack.currentWidget().name)
        self.assertEqual(['Workflow','Catalog','Audit','Problems','Curate','History','Details'],list(self.w.pages))

    def test_exact_uuid_differs_from_catalog(self):
        self.w.catalog.table.select_record(lambda r:r['_work_id']==2);selection=self.select(1)
        self.assertEqual(self.items[0]['working_set_item_uuid'],self.w.force_selected_item(selection)['working_set_item_uuid'])
        self.assertEqual(2,self.w.catalog.table.current()['_work_id'])

    def test_force_targets_workflow_and_not_stale_catalog(self):
        self.w.catalog.table.select_record(lambda r:r['_work_id']==2);selection=self.select(1)
        with patch.object(self.w,'confirm_force_reaudit',return_value=True),patch.object(self.w,'start_audit',return_value=True) as start:
            self.w.force_reaudit_selected(selection)
        start.assert_called_once_with([self.items[0]['working_set_item_uuid']],force_reaudit=True)

    def test_context_rejects_database_switch(self):
        selection=self.select();s=Session(self.root/'B.db',create=True,role='TEST');s.close()
        self.w.switch_database(self.root/'B.db')
        self.assertEqual([],self.page.table.selected())
        with self.assertRaisesRegex(ValueError,'database'):resolve(self.session,selection)

    def test_context_rejects_working_set_switch(self):
        selection=self.select();other=self.db.working_sets.create('Other');self.w.activate_set(other)
        self.assertFalse(self.page.table.selected())
        with self.assertRaisesRegex(ValueError,'context changed'):resolve(self.session,selection)

    def test_context_rejects_changed_pin(self):
        selection=self.select();aid=self.new_audit();self.db.working_sets.pin(self.items[0]['working_set_item_uuid'],1,aid)
        with self.assertRaisesRegex(ValueError,'pin changed'):resolve(self.session,selection)

    def test_empty_no_active_set(self):
        self.session.activate_working_set(None);self.w.refresh_all()
        self.assertEqual('Workflow',self.w.stack.currentWidget().name)
        self.assertIn('New Batch',self.page.empty.text());self.assertTrue(self.page.new_button.isEnabled())
        self.assertFalse(self.page.export_button.isEnabled())

    def test_mixed_states_use_persisted_memberships(self):
        self.db.working_sets.add_requests(self.sid,['Pending','Error','Review'])
        extra=self.db.working_sets.items(self.sid)[2:]
        for i,s in zip(extra,('PENDING','ERROR','REVIEW')):self.state(i['working_set_item_uuid'],s)
        self.assertEqual(5,self.page.summary['total']);self.assertEqual(2,self.page.summary['eligible'])
        self.assertEqual(3,self.page.summary['unlinked']);self.assertIn('PENDING 1',self.page.states.text())

    def test_ready_ineligible_count_is_not_ready_count(self):
        with self.db.con() as c:c.execute("UPDATE search_audits SET publication_json='{}' WHERE id=?",(self.audits[1],))
        self.w.refresh_all()
        self.assertEqual('READY',self.db.working_sets.item(self.items[0]['working_set_item_uuid'])['processing_status'])
        self.assertEqual(1,self.page.summary['eligible'])

    def test_protected_complete_and_archived(self):
        for state in ('COMPLETE','ARCHIVED'):
            with self.db.con() as c:c.execute('UPDATE working_sets SET status=? WHERE working_set_uuid=?',(state,self.sid))
            self.w.refresh_all();self.select()
            self.assertFalse(self.page.run_button.isEnabled());self.assertFalse(self.page.commands_button.isEnabled())
            self.assertFalse(self.page.accept_button.isEnabled());self.assertTrue(self.page.export_button.isEnabled())
        self.w.reopen_set();self.assertTrue(self.page.run_button.isEnabled())

    def test_inspector_exact_pin_and_four_health(self):
        self.select();text=' '.join(l.text() for l in self.page.inspector.findChildren(__import__('PySide6.QtWidgets',fromlist=['QLabel']).QLabel))
        for term in ('Monster','standard','en','Identity','Publication','Normalization','Acquisition'):self.assertIn(term,text)
        self.assertIn(self.items[0]['working_set_item_uuid'],self.page.inspector.findChildren(__import__('qt_app.widgets.common',fromlist=['RawData']).RawData)[0].toPlainText())

    def test_health_filter_and_clear(self):
        self.page.health_filter.setCurrentText('Unknown');self.assertEqual(0,self.page.table.proxy.rowCount())
        self.page.clear_filters();self.assertEqual(2,self.page.table.proxy.rowCount())

    def test_narrow_inspector_toggle_reachable(self):
        self.w.resize(1120,720);APP.processEvents();self.assertTrue(self.page.right.isHidden())
        self.page.toggle_inspector();self.assertTrue(self.page.right.isVisibleTo(self.page));self.assertTrue(self.page.export_button.isVisibleTo(self.page))
        self.page.toggle_inspector();self.assertTrue(self.page.right.isHidden())

    def test_details_uses_workflow_item(self):
        self.w.catalog.table.select_record(lambda r:r['_work_id']==2);self.select()
        self.page.open_tool('Details');self.assertEqual(1,self.w.details.work_id)
        self.assertEqual(self.items[0]['working_set_item_uuid'],self.w.details.item['working_set_item_uuid'])

    def test_problems_scoped_to_exact_work(self):
        for wid in (1,2):
            aid=self.db.save_audit(wid,dict(query=self.db.work(wid)['input_title'],publication=publication(self.db.work(wid)['input_title'])),[dict(code='UNMAPPED_CHAPTERS',severity='warning',message='Research',details=dict(chapters=['1']))])
            self.db.working_sets.pin(self.items[wid-1]['working_set_item_uuid'],wid,aid)
        self.w.refresh_all();self.select();self.page.open_tool('Problems')
        self.assertEqual([1],list({r['_hole']['work_id'] for r in self.w.problems.table.records.records}))
        self.w.problems.clear_title_focus();self.assertEqual(2,len(self.w.problems.table.records.records))

    def test_export_json_exact_scope_readonly(self):
        before=self.db.path.read_bytes();path=self.export();packet=json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual('mangaanka-ddk-working-set-review-v1',packet['format'])
        self.assertEqual(self.sid,packet['working_set']['working_set_uuid']);self.assertEqual('pinned',packet['mode'])
        self.assertEqual(before,self.db.path.read_bytes());self.assertEqual('.json',path.suffix)

    def test_current_mode_does_not_advance_pin(self):
        aid=self.new_audit();path=self.export('current');packet=json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(aid,packet['entries'][0]['audit']['id'])
        self.assertEqual(self.audits[1],self.db.working_sets.item(self.items[0]['working_set_item_uuid'])['pinned_audit_id'])

    def test_no_receipt_is_unknown(self):self.assertIn('Unknown',self.fresh())
    def test_success_receipt_current_and_small(self):
        self.export();self.assertEqual('Review packet current',self.fresh())
        value=self.settings.value(receipts.key(self.db,self.sid,'pinned'));self.assertLess(len(value),600)
        self.assertNotIn('publication_json',value)
    def test_cancel_no_receipt(self):
        with patch('qt_app.main_window.QFileDialog.getSaveFileName',return_value=('','JSON')):self.assertIsNone(self.page.export())
        self.assertIn('Unknown',self.fresh())
    def test_failed_export_no_receipt(self):
        with patch.object(self.w,'save_text',side_effect=OSError('Disk full')):
            with self.assertRaises(OSError):self.page.export()
        self.assertIn('Unknown',self.fresh())
    def test_unchanged_fingerprint(self):self.assertEqual(self.digest(),self.digest())
    def test_new_audit_stales_pinned_receipt(self):self.export();self.new_audit();self.assertIn('stale',self.fresh())
    def test_changed_pin_stales_receipt(self):
        aid=self.new_audit();self.export();self.db.working_sets.pin(self.items[0]['working_set_item_uuid'],1,aid);self.assertIn('stale',self.fresh())
    def test_curation_stales_receipt(self):
        self.export();self.db.catalog.apply(self.db.catalog.preview(1,[dict(entity='chapter',key='1',field='title',value='Verified',verification='REVIEWED')]))
        self.assertIn('stale',self.fresh())
    def test_membership_stales_receipt(self):self.export();self.db.working_sets.add_requests(self.sid,['New']);self.assertIn('stale',self.fresh())
    def test_receipt_separate_sets(self):
        self.export();sid=self.db.working_sets.create('B');self.assertIn('Unknown',receipts.status(self.settings,self.db,sid)[0])
    def test_receipt_separate_database(self):
        self.export();s=Session(self.root/'other.db',create=True,role='TEST')
        try:sid=s.db.working_sets.create('B');self.assertIn('Unknown',receipts.status(self.settings,s.db,sid)[0])
        finally:s.close()
    def test_mode_difference(self):self.export();self.assertIn('Unknown',self.fresh('current'));self.assertNotEqual(self.digest(),self.digest('current'))
    def test_deleted_set_receipt_unknown(self):
        self.export()
        with self.db.con() as c:c.execute('DELETE FROM working_sets WHERE working_set_uuid=?',(self.sid,))
        self.assertIn('Unknown',self.fresh())
    def test_receipt_restart(self):
        self.export();other=QSettings(str(self.root/'ui.ini'),QSettings.IniFormat)
        self.assertEqual('Review packet current',receipts.status(other,self.db,self.sid)[0])
    def test_malformed_receipt(self):
        self.settings.setValue(receipts.key(self.db,self.sid,'pinned'),'{}');self.assertIn('Unknown',self.fresh())
    def test_membership_status_stales_receipt(self):self.export();self.state(self.items[0]['working_set_item_uuid'],'ERROR');self.assertIn('stale',self.fresh())
    def test_acceptance_stales_receipt(self):
        self.export();self.db.acceptance.accept(item_uuids=[self.items[0]['working_set_item_uuid']]);self.assertIn('stale',self.fresh())
    def test_evidence_stales_receipt(self):
        self.db.catalog.apply(self.db.catalog.preview(1,[dict(entity='chapter',key='1',field='volume',value='1',verification='VERIFIED')]))
        self.export();self.db.catalog.apply(self.db.catalog.preview(1,[dict(entity='evidence',key='proof',field='add',target_key='1',source_name='Publisher',source_url='https://example.org/toc')]))
        self.assertIn('stale',self.fresh())

    def test_commands_exact_target_and_preview_no_write(self):
        self.w.catalog.table.select_record(lambda r:r['_work_id']==2);self.select();self.page.commands()
        before=self.db.path.read_bytes();self.w.drawer.input.setPlainText('set title "Review title" chapter 1');self.w.drawer.preview()
        self.assertEqual(1,self.w.command.pending['work_id']);self.assertEqual(before,self.db.path.read_bytes())
        self.assertIn('Monster',self.w.drawer.context.text());self.assertIn(self.items[0]['working_set_item_uuid'],self.w.drawer.context.text())
    def test_stale_guard_rejected(self):
        self.select();self.page.commands();guard=self.page.snapshots[self.items[0]['working_set_item_uuid']]['guard'];self.new_audit()
        self.w.drawer.input.setPlainText(guard+'\nset title "No" chapter 1');self.w.drawer.preview()
        self.assertIsNone(self.w.command.pending);self.assertIn('blocked',self.w.drawer.output.toPlainText())
    def test_switch_selection_cancels_preview(self):
        self.select();self.page.commands();self.w.drawer.input.setPlainText('set title "Draft" chapter 1');self.w.drawer.preview();self.assertTrue(self.w.command.pending)
        self.select(2);self.assertIsNone(self.w.command.pending);self.assertFalse(self.w.drawer.apply_button.isEnabled())
    def test_refresh_same_selection_preserves_preview(self):
        self.select();self.page.commands();self.w.drawer.input.setPlainText('set title "Draft" chapter 1');self.w.drawer.preview();self.w.refresh_all();self.assertTrue(self.w.command.pending)
    def test_apply_reaudit_once_and_receipt_stale(self):
        self.export();self.select();self.page.commands();old=self.audits[1]
        self.w.drawer.input.setPlainText('set volume 2 chapter 1');self.w.drawer.preview();self.assertEqual(old,self.db.latest_audit(1)['id'])
        self.w.drawer.apply();self.assertTrue(self.w.busy);self.wait_idle()
        with self.db.con() as c:self.assertEqual(2,c.execute('SELECT count(*) FROM search_audits WHERE work_id=1').fetchone()[0])
        self.assertGreater(self.db.working_sets.item(self.items[0]['working_set_item_uuid'])['pinned_audit_id'],old)
        self.assertIn('stale',self.page.receipt_label.text());self.assertEqual(self.audits[2],self.db.working_sets.item(self.items[1]['working_set_item_uuid'])['pinned_audit_id'])
    def test_deferred_reaudit_display_without_second_queue(self):
        self.select();self.page.commands()
        self.w.busy=True;self.w.current_key=self.items[1]['working_set_item_uuid'];self.w.audit.stage.setText('Auditing other item')
        try:
            self.w.command.execute('set volume 2 chapter 1');self.w.command.apply()
            self.assertEqual({self.items[0]['working_set_item_uuid']},self.w.deferred)
            row=next(r for r in self.page.table.records.records if r['_work_id']==1);self.assertEqual('Re-Audit queued',row['next_action'])
        finally:self.w.busy=False;self.w.deferred.clear()
    def test_acceptance_requires_human_and_does_not_block_unresolved(self):
        self.state(self.items[1]['working_set_item_uuid'],'REVIEW')
        with self.db.con() as c:self.assertEqual(0,c.execute('SELECT count(*) FROM catalog_acceptances').fetchone()[0])
        with patch.object(self.w,'confirm',return_value=True):self.w.accept_all_safe(self.page.batch_context())
        self.assertEqual('ACCEPTED',self.db.working_sets.item(self.items[0]['working_set_item_uuid'])['processing_status'])
        self.assertEqual('REVIEW',self.db.working_sets.item(self.items[1]['working_set_item_uuid'])['processing_status'])
    def test_cancel_acceptance_writes_nothing(self):
        before=self.db.path.read_bytes()
        with patch.object(self.w,'confirm',return_value=False):self.w.accept_all_safe(self.page.batch_context())
        self.assertEqual(before,self.db.path.read_bytes())
    def test_complete_requires_terminal_items_then_new_batch(self):
        self.assertFalse(self.page.complete_button.isEnabled())
        with patch.object(self.w,'confirm',return_value=True):self.w.accept_all_safe(self.page.batch_context())
        self.assertTrue(self.page.complete_button.isEnabled())
        with patch.object(self.w,'confirm',return_value=True):self.w.set_status('COMPLETE')
        self.assertFalse(self.page.intake_button.isEnabled())
        with patch.object(self.w,'form',return_value=dict(name='Next Batch',description='',language='en',workflow='volume')):self.w.new_set()
        self.assertNotEqual(self.sid,self.session.active_uuid);self.assertTrue(self.page.intake_button.isEnabled())
    def test_keyboard_selection_focus_and_scrollbars(self):
        self.page.table.setFocus();self.page.table.selectRow(0);QTest.keyClick(self.page.table,Qt.Key_Down);APP.processEvents()
        self.assertTrue(self.page.table.current());self.page.commands();self.assertTrue(self.w.drawer.input.hasFocus())
        self.assertEqual(Qt.ScrollBarAlwaysOn,self.page.table.verticalScrollBarPolicy())
        self.assertEqual(Qt.ScrollBarAlwaysOn,self.page.inspector.verticalScrollBarPolicy())

    def test_complete_operator_cycle_with_unresolved_remainder(self):
        self.w.auditor_factory=CycleAuditor
        with patch.object(self.w,'form',return_value=dict(name='Production cycle',description='',language='en',workflow='volume')):self.w.new_set()
        sid=self.session.active_uuid
        def paste(dialog):
            from PySide6.QtWidgets import QPlainTextEdit,QDialog
            dialog.findChild(QPlainTextEdit).setPlainText('Monster\nFire Force\nNew Series\nMonster')
            return QDialog.Accepted
        with patch.object(self.w,'form',return_value=dict(edition='standard',language='en',workflow='volume')),patch('qt_app.main_window.QDialog.exec',new=paste):self.w.intake()
        self.assertEqual(3,self.page.summary['total']);self.assertIn("'duplicate_input_lines': 1",self.w.status_label.text())
        self.w.run_working_set();self.wait_idle()
        entries=self.db.working_sets.items(sid);by_title={i['original_query']:i for i in entries}
        self.assertEqual('REVIEW',by_title['Fire Force']['processing_status']);self.assertEqual('REVIEW',by_title['New Series']['processing_status'])
        path=self.root/'cycle.json'
        with patch('qt_app.main_window.QFileDialog.getSaveFileName',return_value=(str(path),'JSON')):self.page.export()
        self.assertEqual('Review packet current',self.page.receipt_label.text().split(' · ')[0])
        self.page.table.select_record(lambda r:r['query']=='Fire Force');self.page.commands()
        guard=self.page.snapshots[by_title['Fire Force']['working_set_item_uuid']]['guard']
        commands=guard+'\nselect chapters 303,304\nset volume 1 selected\nset verification verified selected'
        self.w.drawer.input.setPlainText(commands);before=self.db.path.read_bytes();self.w.drawer.preview()
        self.assertTrue(self.w.command.pending);self.assertEqual(before,self.db.path.read_bytes())
        self.w.drawer.apply();self.assertTrue(self.w.busy);self.wait_idle();self.w.drawer.set_expanded(False)
        self.assertIn('stale',self.page.receipt_label.text())
        with patch('qt_app.main_window.QFileDialog.getSaveFileName',return_value=(str(path),'JSON')):self.page.export()
        self.assertIn('current',self.page.receipt_label.text())
        self.assertEqual(2,self.page.summary['eligible'])
        with patch.object(self.w,'confirm',return_value=True):self.w.accept_all_safe(self.page.batch_context())
        self.assertEqual('REVIEW',self.db.working_sets.item(by_title['New Series']['working_set_item_uuid'])['processing_status'])
        self.assertFalse(self.page.complete_button.isEnabled())
        self.w.navigate('Catalog');self.w.catalog.table.select_record(lambda r:r['query']=='New Series')
        with patch.object(self.w,'confirm',return_value=True):self.w.reject_items()
        self.w.navigate('Workflow');self.assertTrue(self.page.complete_button.isEnabled())
        with patch.object(self.w,'confirm',return_value=True):self.w.set_status('COMPLETE')
        with patch.object(self.w,'form',return_value=dict(name='Next Batch',description='',language='en',workflow='volume')):self.w.new_set()
        self.assertNotEqual(sid,self.session.active_uuid);self.assertEqual(0,self.page.summary['total'])


if __name__=='__main__':unittest.main()
