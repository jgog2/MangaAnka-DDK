"""Local evidence review form; delegates every mutation to Preview/Apply."""
from copy import deepcopy
from datetime import datetime,timezone
import json
import shlex
import hashlib
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QFormLayout,QComboBox,QLineEdit,
    QCheckBox,QLabel,QHBoxLayout,QScrollArea,QWidget,QFileDialog)
from qt_app.widgets.common import RawData,button
from ddk_supplementary_commands import command_text


class SupplementaryReview(QDialog):
    def __init__(self,window,work_id,scope,opaque_id):
        super().__init__(window);self.window=window;self.work_id=work_id;self.scope=scope;self.opaque_id=opaque_id
        self.setWindowTitle('Review Supplementary Identity');self.resize(820,690)
        layout=QVBoxLayout(self);scroll=QScrollArea();scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn);body=QWidget();inside=QVBoxLayout(body)
        scroll.setWidget(body);layout.addWidget(scroll)
        store=window.db.supplementary
        self.item=window.session.mutation_item(work_id,scope)
        self.context=store.guard(work_id,self.item)
        self.evidence=next(r for r in store.for_audit(work_id,current=True)['identities'] if r['identity']['opaque_id']==opaque_id)
        self.identity=self.evidence['identity'];self.candidates=store.candidates(work_id,opaque_id)
        title=QLabel(self.identity['story_title']);title.setWordWrap(True);inside.addWidget(title)
        note=QLabel('Publication identity, exact acquired contents and collection membership are independent. '
            'This form only prepares commands. Review Preview, then use explicit Apply in the command drawer. '
            'Titles, decimals, page counts and OCR alone are insufficient.');note.setWordWrap(True);inside.addWidget(note)
        self.raw=RawData();self.raw.setMinimumHeight(180);inside.addWidget(self.raw)
        form=QFormLayout();inside.addLayout(form)
        self.candidate=QComboBox();self.candidate.setMinimumContentsLength(24)
        for i,row in enumerate(self.candidates):
            if not row['contrary_numeric_identity']:
                self.candidate.addItem(f"{row['provider']} · {row['original_label']} · {row['record_id']}",i)
        form.addRow('Exact acquisition',self.candidate)
        self.candidate.currentIndexChanged.connect(self.show_candidate)
        self.reviewer=QLineEdit();form.addRow('Reviewer',self.reviewer)
        self.note=QLineEdit();form.addRow('Decision / contradictions reviewed',self.note)
        self.evidence_url=QLineEdit();form.addRow('Complete equivalence evidence URL',self.evidence_url)
        form.addRow(button('Load Captured Evidence File…',lambda:window.safe(self.choose_evidence_file)))
        self.evidence_status=QLabel('Load an independently captured comparison file to calculate its hash and import time. '
            'The source URL, reviewer explanation and complete-content verification are still required. '
            'Provider titles or page counts alone do not prove equivalence.');self.evidence_status.setWordWrap(True);form.addRow(self.evidence_status)
        self.evidence_hash=QLineEdit();form.addRow('Equivalence evidence SHA-256',self.evidence_hash)
        self.captured=QLineEdit(datetime.now(timezone.utc).isoformat());form.addRow('Evidence capture / import time (ISO)',self.captured)
        self.complete=QCheckBox('I independently verified complete contents and compatible edition/language.');form.addRow(self.complete)
        self.decision=QComboBox()
        for row in self.evidence.get('reviewed_decisions',[]):
            self.decision.addItem(row['kind']+' · '+row['effective_state']+' · '+row['assertion_uuid'],row['assertion_uuid'])
        form.addRow('Exact current decision',self.decision)
        for labels in ([('Preview Binding',self.preview_binding),('Preview Membership',self.preview_membership)],
                       [('Preview Reject',lambda:self.preview_decision('reject')),('Preview Withdraw',lambda:self.preview_decision('withdraw'))],
                       [('Preview Supplement Undo',lambda:self.preview_reverse(False)),('Preview Supplement Redo',lambda:self.preview_reverse(True))]):
            actions=QHBoxLayout()
            for text,callback in labels:actions.addWidget(button(text,lambda checked=False,cb=callback:window.safe(cb)))
            inside.addLayout(actions)
        inside.addWidget(button('Close',self.reject));self.show_candidate()

    def choose_evidence_file(self):
        filename,_=QFileDialog.getOpenFileName(self,'Load independently captured comparison evidence','','Evidence files (*)')
        if filename:self.load_evidence_file(Path(filename))

    def load_evidence_file(self,path):
        # Bounded local provenance capture only: never fetch on the GUI thread
        # or certify that the selected bytes establish content equivalence.
        path=Path(path)
        limit=5*1024*1024
        with path.open('rb') as stream:payload=stream.read(limit+1)
        if not payload:raise ValueError('The evidence file is empty.')
        if len(payload)>limit:raise ValueError('Evidence files must be at most 5 MiB; use a bounded comparison capture.')
        self.evidence_hash.setText(hashlib.sha256(payload).hexdigest())
        self.captured.setText(datetime.now(timezone.utc).isoformat())
        self.evidence_status.setText(f'Loaded {path.name} ({len(payload):,} bytes). Hash and import time generated. '
            'This is provenance only: inspect the evidence, supply its source URL and explicitly verify complete equivalence.')

    def show_candidate(self):
        index=self.candidate.currentData()
        candidate=self.candidates[index] if index is not None else None
        self.raw.show_data(dict(identity=self.evidence,selected_acquisition=candidate,
            history=self.window.db.supplementary.history(self.work_id,self.opaque_id)))

    def guard_command(self):
        c=self.context
        return f"guard database_uuid {c['database_uuid']} audit {c['audit_id']} revision {c['audit_revision']} database {c['database_revision']}"

    def send(self,text):
        self.window.drawer.set_expanded(True);self.window.drawer.input.setPlainText(text);self.window.drawer.preview()
        if self.window.command.pending:self.accept()

    def preview_binding(self):
        index=self.candidate.currentData()
        if index is None:raise ValueError('Choose an exact acquisition candidate.')
        r=self.candidates[index];i=self.identity;p=i['provenance'];c=self.context
        payload=dict(supplement_id=self.opaque_id,scope=i['scope'],provider=r['provider'],record_id=r['record_id'],
            original_label=r['original_label'],url=r['url'],method='reviewed_exact',verification='VERIFIED',
            review_guard={k:c[k] for k in ('database_uuid','audit_id','audit_revision','database_revision')},
            reviewer=self.reviewer.text(),note=self.note.text(),source_url=p['source_url'],
            captured_at=p['captured_at'],publication_sha256=p['payload_sha256'],acquisition_sha256=r['acquisition_sha256'],
            equivalence=dict(method='complete_content_review',complete=self.complete.isChecked(),source_url=self.evidence_url.text(),
                payload_sha256=self.evidence_hash.text(),captured_at=self.captured.text(),note=self.note.text()))
        self.send(command_text(self.guard_command(),'bind',self.opaque_id,payload))

    def preview_membership(self):
        values=self.evidence.get('memberships') or []
        if len(values)!=1:raise ValueError('Membership requires one independently established official collection relationship.')
        payload=deepcopy(values[0]);payload.update(verification='VERIFIED',reviewer=self.reviewer.text(),note=self.note.text())
        self.send(command_text(self.guard_command(),'membership',self.opaque_id,payload))

    def preview_decision(self,action):
        if not self.decision.currentData():raise ValueError('Choose an exact current assertion.')
        self.send(self.guard_command()+'\nsupplement '+action+' '+self.decision.currentData()+
            ' reviewer '+shlex.quote(self.reviewer.text())+' note '+shlex.quote(self.note.text()))

    def preview_reverse(self,redo):
        self.send(self.guard_command()+'\nsupplement '+('redo' if redo else 'undo'))
