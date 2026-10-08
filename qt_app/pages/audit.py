from PySide6.QtWidgets import QLabel, QProgressBar
from qt_app.pages.base import Page
from qt_app.widgets.common import RecordTable


class AuditPage(Page):
    def __init__(self, window):
        super().__init__(window, 'Audit')
        self.run_button = self.add_action('Run Working Set', window.run_working_set, True)
        self.retry_button = self.add_action('Retry Errors', window.retry_errors)
        self.stop_button = self.add_action('Cancel Run', window.cancel_run); self.stop_button.setEnabled(False)
        self.stage = QLabel('Idle · run the active Working Set to audit pending or stale items.'); self.stage.setWordWrap(True)
        self.layout.insertWidget(2, self.stage)
        self.progress = QProgressBar(); self.progress.setRange(0,100); self.progress.setValue(0); self.layout.insertWidget(3,self.progress)
        self.table = RecordTable([('time','UTC Time',170,False),('title','Title',210,False),('result','Result',110,True),('audit_id','Audit',65,False),('duration','Duration',80,False)])
        self.set_content(self.table); self.search.textChanged.connect(lambda s:self.table.proxy.update(s))
        self.table.selectionModel().selectionChanged.connect(self.selected)
        self.runtime_activity = []

    def refresh(self):
        self.update_scopes(); rows = []
        for w in self.window.session.works(self.scope):
            a = self.window.db.audit(w['audit_id'],w['id']) if w['audit_id'] else None
            if a: rows.append(dict(time=a['created_at'],title=w['input_title'],result=a['final_state'],audit_id=a['id'],duration='—',_work_id=w['id'],_audit=a))
        allowed={w['id'] for w in self.window.session.works(self.scope)}
        set_uuid=self.window.session.set_uuid(self.scope)
        rows += [r for r in self.runtime_activity if self.scope=='all' or
                 self.scope=='accepted' and r.get('_work_id') in allowed or
                 set_uuid and r.get('_set_uuid')==set_uuid]
        self.table.records.replace(sorted(rows,key=lambda r:r['time'],reverse=True))
        self.empty.setText('No audit activity in this scope. Add intake and Run Working Set.' if not rows else 'Selected evidence follows the visible scope; live run status appears above.')

    def selected(self):
        row = self.table.current()
        if not row:self.inspector.display('Select an audit',{});return
        if row: self.inspector.display(row['title'], {'Audit':{k:row[k] for k in ('result','audit_id','time','duration')}}, raw=row.get('_audit',row),
            publication_rows=self.window.db.catalog.rows(row['_work_id'],audit=row['_audit']) if row.get('_work_id') and row.get('audit_id') else [])
