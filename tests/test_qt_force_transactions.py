"""Qt worker ownership and sequential forcing on a disposable catalog."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import threading
import time
import unittest
from unittest.mock import patch

import test_qt_force_reaudit as qt_reference
from test_qt_force_reaudit import APP, OfflineAuditor
from test_working_set_audit_recovery import offline_pipeline
from test_force_transactions import SQLTrace, large_offline_pipeline
from mangaanka_database_development_kit import SearchAuditor


class LargeOfflineAuditor(SearchAuditor):
    def audit_many(self,ids,workflow):
        with large_offline_pipeline(self):super().audit_many(ids,workflow)


class ProviderGateAuditor(SearchAuditor):
    entered=threading.Event();release=threading.Event()
    def audit_many(self,ids,workflow):
        with large_offline_pipeline(self):
            original=self._parallel_provider_search
            def search(*args,**kwargs):
                self.entered.set()
                if not self.release.wait(5):raise RuntimeError('Provider gate timed out')
                return original(*args,**kwargs)
            with patch.object(self,'_parallel_provider_search',side_effect=search):
                super().audit_many(ids,workflow)


class QtForceTransactions(unittest.TestCase):
    setUp=qt_reference.QtForceReaudit.setUp
    cleanup=qt_reference.QtForceReaudit.cleanup
    select=qt_reference.QtForceReaudit.select
    wait_idle=qt_reference.QtForceReaudit.wait_idle

    def test_two_sequential_qt_forces_create_distinct_frozen_history(self):
        self.window.auditor_factory=LargeOfflineAuditor
        self.select();db=self.session.db;trace=SQLTrace(db);self.trace=trace;gui_thread=threading.get_ident()
        prior=dict(db.audit(self.old,self.wid))
        with trace.enabled(),patch.object(self.window,'confirm_force_reaudit',return_value=True):
            self.window.force_reaudit_selected();self.wait_idle()
            first=db.working_sets.item(self.uid)['pinned_audit_id'];record=dict(db.audit(first,self.wid))
            self.select();self.window.force_reaudit_selected();self.wait_idle()
        second=db.working_sets.item(self.uid)['pinned_audit_id']
        self.assertEqual((self.old+1,self.old+2),(first,second))
        self.assertEqual(prior,dict(db.audit(self.old,self.wid)));self.assertEqual(record,dict(db.audit(first,self.wid)))
        self.assertIn('New 1',self.window.audit.stage.text());self.assertIn(str(second),self.window.audit.stage.text())
        self.assertFalse(any(e.get('error') for e in trace.events));self.assertEqual({},trace.active)
        audit_inserts=[e for e in trace.events if e['sql'].startswith('INSERT INTO search_audits(')]
        self.assertEqual(2,len(audit_inserts));self.assertTrue(all(e['thread']!=gui_thread for e in audit_inserts))
        owners={e['connection']:e['thread'] for e in trace.events if e['sql']=='OPEN'}
        self.assertTrue(all(owners[e['connection']]==e['thread'] for e in trace.events))

    def test_gui_reads_and_independent_write_during_actual_provider_stage(self):
        db=self.session.db;trace=SQLTrace(db);self.trace=trace;self.window.auditor_factory=ProviderGateAuditor
        ProviderGateAuditor.entered.clear();ProviderGateAuditor.release.clear();self.select()
        with trace.enabled(),patch.object(self.window,'confirm_force_reaudit',return_value=True):
            self.window.force_reaudit_selected()
            try:
                for _ in range(300):
                    APP.processEvents();time.sleep(.005)
                    if ProviderGateAuditor.entered.is_set():break
                self.assertTrue(ProviderGateAuditor.entered.is_set())
                self.assertEqual('AUDITING',db.working_sets.item(self.uid)['processing_status'])
                self.assertFalse(any(c.in_transaction for c in trace.active.values()))
                self.window.refresh_all()
                self.assertEqual(self.old,self.window.catalog.table.current()['audit_id'])
                db.working_sets.create('GUI independent writer')
            finally:ProviderGateAuditor.release.set();self.wait_idle()
        self.assertGreater(db.working_sets.item(self.uid)['pinned_audit_id'],self.old)
        self.assertEqual({},trace.active);self.assertFalse(any(e.get('error') for e in trace.events))


if __name__=='__main__':unittest.main()
