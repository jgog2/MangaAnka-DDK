from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
                              QComboBox, QPlainTextEdit, QDialogButtonBox, QLabel)
from qt_app.widgets.common import button, RawData, Inspector


class FormDialog(QDialog):
    def __init__(self, parent, title, fields, explanation=''):
        super().__init__(parent);self.setWindowTitle(title);self.setMinimumWidth(470)
        layout=QVBoxLayout(self)
        if explanation:
            text=QLabel(explanation);text.setWordWrap(True);layout.addWidget(text)
        form=QFormLayout();layout.addLayout(form);self.inputs={}
        for key,label,value,choices in fields:
            if choices:
                widget=QComboBox();widget.addItems(choices);widget.setCurrentText(str(value))
            else:widget=QLineEdit(str(value or ''))
            widget.setAccessibleName(label);form.addRow(label,widget);self.inputs[key]=widget
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);layout.addWidget(buttons)

    def values(self):return {k:w.currentText() if isinstance(w,QComboBox) else w.text() for k,w in self.inputs.items()}


class ReconciliationDialog(QDialog):
    def __init__(self,window,wid):
        super().__init__(window);self.setWindowTitle('Re-evaluate Acceptance');self.resize(720,640)
        self.window=window;self.wid=wid;self.evaluation=window.db.acceptance.evaluate(wid)
        with window.db.con() as c:
            self.history=[dict(r) for r in c.execute('SELECT * FROM catalog_acceptances WHERE work_uuid=? ORDER BY id DESC',(self.evaluation['work_uuid'],))]
            self.memberships=[dict(r) for r in c.execute('SELECT * FROM working_set_items WHERE linked_work_uuid=?',(self.evaluation['work_uuid'],))]
        layout=QVBoxLayout(self);note=QLabel('Global catalog approval. Membership decisions and pinned audits stay fixed.');note.setWordWrap(True);layout.addWidget(note)
        inspector=Inspector();inspector.display(window.db.work(wid)['input_title'],{'Current state':{'Catalog':window.db.work(wid)['lifecycle_status'],'Approval':window.db.acceptance.state(wid),
            'Eligible':self.evaluation['eligible'],'Audit':self.evaluation['audit_id'],'Curation revision':self.evaluation['curation_revision']},
            'Blockers':{'Reasons':'\n'.join(self.evaluation['blockers']) or 'None'},'Warnings':{'Reasons':'\n'.join(self.evaluation['warnings']) or 'None'},
            'Provenance':{'Approval records':len(self.history),'Linked memberships':len(self.memberships)}},raw=dict(evaluation=self.evaluation,history=self.history,memberships=self.memberships))
        layout.addWidget(inspector);bar=QHBoxLayout();layout.addLayout(bar)
        self.approve_button=button('Confirm Safe Snapshot',lambda:window.safe(self.approve),primary=True);self.approve_button.setEnabled(self.evaluation['eligible']);bar.addWidget(self.approve_button)
        bar.addWidget(button('Revoke Acceptance',lambda:window.safe(self.revoke)));bar.addWidget(button('Close',self.reject))

    def approve(self):
        self.window.db.acceptance.accept(work_ids=[self.wid],expected={str(self.wid):self.evaluation['fingerprint']});self.window.refresh_all();self.accept()

    def revoke(self):
        values=self.window.form('Revoke Acceptance',[('reason','Reason','',None)],'Return this global catalog work to STAGED; prior approvals remain in history.')
        if values:
            self.window.db.acceptance.revoke(self.wid,values['reason']);self.window.refresh_all();self.accept()


class DeleteDialog(QDialog):
    def __init__(self,window,preview):
        from ddk_catalog_maintenance import format_delete_preview
        super().__init__(window);self.setWindowTitle('Permanently Delete Catalog Work');self.resize(740,620)
        self.window=window;self.preview=preview
        layout=QVBoxLayout(self);raw=RawData();raw.show_data(format_delete_preview(preview));layout.addWidget(raw)
        text=QLabel('Type DELETE to permanently remove this work. The backend rechecks this preview and creates a fresh backup.');text.setWordWrap(True);layout.addWidget(text)
        self.confirmation=QLineEdit();self.confirmation.setPlaceholderText('DELETE');self.confirmation.setAccessibleName('Type DELETE');layout.addWidget(self.confirmation)
        bar=QHBoxLayout();layout.addLayout(bar);bar.addWidget(button('Cancel',self.reject))
        self.delete_button=button('Permanently Delete',lambda:window.safe(self.apply));self.delete_button.setProperty('destructive',True);self.delete_button.setEnabled(False);bar.addWidget(self.delete_button)
        self.confirmation.textChanged.connect(lambda t:self.delete_button.setEnabled(t=='DELETE'))

    def apply(self):
        self.window.db.maintenance.delete(self.preview,self.confirmation.text());self.window.command.cancel();self.window.refresh_all();self.accept()
