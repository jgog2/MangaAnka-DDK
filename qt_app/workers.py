"""Worker calls the existing sequential auditor; queued events reach Qt safely."""
import queue
import threading
import traceback
from PySide6.QtCore import QThread, Signal
from mangaanka_database_development_kit import SearchAuditor


class ForceBatchEvents:
    """Capture exact item context when emitted, before the Qt relay can lag."""
    def __init__(self,worker):self.worker=worker
    def put(self,event):
        kind,payload=event;worker=self.worker
        if kind=='done':return
        if kind=='batch':
            payload=dict(payload,text=f'{worker.batch_position}/{len(worker.ids)}  '+payload['text'].split('  ',1)[-1],
                         work_id=worker.batch_item)
        worker.events.put((kind,payload))


class AuditWorker(QThread):
    event = Signal(str, dict)
    failed = Signal(str, str)
    completed = Signal()

    def __init__(self, db, ids, workflow='volume', auditor_factory=SearchAuditor, parent=None, force_reaudit=False,
                 force_all_plan=None):
        super().__init__(parent)
        self.ids = ids; self.workflow = workflow
        self.db=db;self.auditor_factory=auditor_factory
        self.events = queue.Queue(); self.auditor = None
        self.cancel_requested = threading.Event()
        self.force_reaudit=force_reaudit
        self.force_all_plan=force_all_plan
        self.batch_results=[];self.batch_position=0;self.batch_item=None
        self.previous_pins={uid:db.working_sets.item(uid)['pinned_audit_id'] for uid in ids} if force_reaudit else {}

    def cancel(self):
        self.cancel_requested.set()
        if self.auditor:self.auditor.stop()

    def run(self):
        # The existing auditor clears its stop flag at entry. A monitor keeps a
        # cancellation requested during startup asserted until the run exits.
        finished = threading.Event()
        def monitor():
            while not finished.wait(.03):
                if self.cancel_requested.is_set(): self.auditor.stop()
                self.drain()
            self.drain()
        relay = None
        failure = None
        try:
            self.auditor=self.auditor_factory(self.db,ForceBatchEvents(self) if self.force_all_plan is not None else self.events)
            relay=threading.Thread(target=monitor,daemon=True);relay.start()
            if self.force_all_plan is not None:self.run_force_all()
            elif not self.cancel_requested.is_set(): self.auditor.audit_many(self.ids, self.workflow)
        except Exception as exc: failure = (str(exc), traceback.format_exc())
        finally:
            finished.set()
            if relay:relay.join()
            if failure: self.failed.emit(*failure)
            self.completed.emit()

    def force_summary(self,final=False):
        results=[dict(r) for r in self.batch_results]
        counts={key:sum(r['result']==key for r in results) for key in ('SUCCESS','FAILED','SKIPPED','CANCELLED','NOT_RUN')}
        total=len(self.ids);completed=sum(r['result'] in ('SUCCESS','FAILED') for r in results)
        text=(f'Force Re-Audit All {"ended" if final else "running"} · Completed {completed}/{total} · '
              f'Success {counts["SUCCESS"]} · Failed {counts["FAILED"]} · Skipped {counts["SKIPPED"]} · '
              f'Cancelled {counts["CANCELLED"]} · Not run {counts["NOT_RUN"]}')
        return dict(force_all=True,text=text,completed=completed,total=total,results=results,
                    successful=counts['SUCCESS'],failed=counts['FAILED'],skipped=counts['SKIPPED'],
                    cancelled=counts['CANCELLED'],not_run=counts['NOT_RUN'],new=sum(bool(r.get('audit_id')) for r in results),
                    reused=0,new_audit_ids=[r['audit_id'] for r in results if r.get('audit_id')])

    def run_force_all(self):
        """Queue just in time, then use the exact same single-item audit lifecycle."""
        self.batch_results=[dict(r) for r in self.force_all_plan['skipped']]
        for position,uid in enumerate(self.ids,1):
            saved=next(i for i in self.force_all_plan['items'] if i['working_set_item_uuid']==uid)
            result=dict(working_set_item_uuid=uid,title=saved['original_query'],audit_id=None,audit_revision=None)
            if self.cancel_requested.is_set():
                self.batch_results.append(dict(result,result='NOT_RUN',reason='Cancelled before this title; unchanged.'))
                continue
            self.batch_position=position;self.batch_item=uid
            self.events.put(('force_progress',dict(self.force_summary(),current_title=result['title'])))
            try:
                # Validate membership/set again immediately before the short queue transaction.
                item=self.db.working_sets.force_audit_candidate(uid,include_pending=True)
                if item['working_set_uuid']!=self.force_all_plan['working_set_uuid']:
                    raise ValueError('Working Set context changed.')
                old_pin=item['pinned_audit_id']
                self.db.working_sets.queue_force_audit(uid,include_pending=True)
            except Exception as exc:
                self.batch_results.append(dict(result,result='SKIPPED' if isinstance(exc,ValueError) else 'FAILED',reason=str(exc)))
                self.events.put(('force_progress',self.force_summary()));continue
            error=''
            try:self.auditor.audit_many([uid],item['requested_workflow'])
            except Exception as exc:
                error=str(exc)
                # Ordinary provider/persistence failures are already handled by
                # audit_many. Retain a recoverable observation if it itself failed.
                current=self.db.working_sets.item(uid)
                if current and current['processing_status'] in ('AUDITING','QUEUED'):
                    try:self.db.working_sets.observe_unresolved(uid,
                        dict(query=item['original_query'],resolution_error=error),
                        [dict(code='AUDIT_ERROR',severity='error',message=error)],status='ERROR')
                    except Exception as recovery:error+='; recovery: '+str(recovery)
            current=self.db.working_sets.item(uid)
            new_pin=current['pinned_audit_id'] if current else None
            if new_pin and new_pin!=old_pin:
                audit=self.db.audit(new_pin,current['work_id'])
                result.update(result='FAILED' if current['processing_status']=='ERROR' else 'SUCCESS',
                    audit_id=new_pin,audit_revision=audit['audit_revision'],set_state=current['processing_status'],
                    acceptance=self.db.acceptance.state(current['work_id']))
            else:
                observation=self.db.working_sets.latest_observation(uid) or {}
                reason=error or (observation.get('record') or {}).get('resolution_error') or 'No new audit persisted; previous pin preserved.'
                result.update(result='CANCELLED' if self.cancel_requested.is_set() else 'FAILED',reason=reason,
                    set_state=current['processing_status'] if current else 'Removed')
            self.batch_results.append(result)
            self.events.put(('force_progress',self.force_summary()))
        self.events.put(('done',self.force_summary(final=True)))

    def drain(self):
        while True:
            try: kind, payload = self.events.get_nowait()
            except queue.Empty: break
            if self.force_all_plan is not None:
                if kind=='done' and not payload.get('force_all'):continue
            elif kind=='done' and self.force_reaudit:
                items=[self.db.working_sets.item(uid) for uid in self.ids]
                new_ids=[i['pinned_audit_id'] for i in items if i and i['pinned_audit_id'] and
                    i['pinned_audit_id']!=self.previous_pins[i['working_set_item_uuid']]]
                payload=dict(payload,new=len(new_ids),reused=0,new_audit_ids=new_ids,
                    text=f'Forced re-audit ended · New {len(new_ids)} · Reused 0 · '
                    f'Audit IDs {", ".join(map(str,new_ids)) or "none"} · '
                    + ' · '.join(f'{i["original_query"]}: {i["processing_status"]}' for i in items if i))
            self.event.emit(kind, payload)
