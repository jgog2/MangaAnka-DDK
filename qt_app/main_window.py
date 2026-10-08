"""Qt shell and human action orchestration; policy lives in existing services."""
import csv
from datetime import datetime, timezone
from io import StringIO
import json
import time
from pathlib import Path
from PySide6.QtCore import Qt, QSettings, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QShortcut, QKeySequence
from PySide6.QtWidgets import (QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,
    QStackedWidget,QSplitter,QMenu,QFileDialog,QDialog,QMessageBox,QPlainTextEdit,QDialogButtonBox)
from qt_app.commands import CommandController
from qt_app.dialogs import FormDialog,ReconciliationDialog,DeleteDialog
from qt_app.widgets.common import button,StatusChip,RawData,pretty
from qt_app.widgets.command_drawer import CommandDrawer
from qt_app.pages.catalog import CatalogPage
from qt_app.pages.audit import AuditPage
from qt_app.pages.problems import ProblemsPage
from qt_app.pages.curate import CuratePage
from qt_app.pages.history import HistoryPage
from qt_app.pages.details import DetailsPage
from qt_app.pages.workflow import WorkflowPage
from qt_app.orchestration import capture, resolve
from qt_app import export_receipts
from qt_app.workers import AuditWorker
from qt_app.icons import icon
from qt_app.preferences import remember_session, restore_working_set
from ddk_exports import (catalog_summary,review_context,working_set_csv,working_set_title_list,
                        working_set_review_context,working_set_packet)


class MainWindow(QMainWindow):
    def __init__(self,session,settings=None,auditor_factory=None):
        super().__init__();self.session=session;self.settings=settings if settings is not None else QSettings('MangaAnka','DDK-Qt')
        self.auditor_factory=auditor_factory;self.worker=None;self.busy=False;self.deferred=set();self.run_failed=False
        self.force_confirmation_pending=False
        self.last_force_all=None;self.force_all_progress='';self.run_force_all=False
        self.deferred_run_ids=[];self.deferred_timer=QTimer(self);self.deferred_timer.setSingleShot(True);self.deferred_timer.timeout.connect(self.run_deferred)
        self.page_feedback={};self.command=CommandController(self);self.setWindowTitle('MangaAnkā Database Development Kit · 0.3.0 · Qt')
        self.setMinimumSize(1120,720);self.resize(1440,900)
        root=QWidget();self.setCentralWidget(root);layout=QVBoxLayout(root);layout.setContentsMargins(12,12,12,8)
        context=QHBoxLayout();layout.addLayout(context)
        brand=QLabel('MangaAnkā');brand.setStyleSheet('font-size:18px; font-weight:600;');context.addWidget(brand)
        self.database_button=QPushButton();self.database_button.setMaximumWidth(280);context.addWidget(self.database_button)
        self.set_button=QPushButton();self.set_button.setMaximumWidth(330);context.addWidget(self.set_button)
        context.addStretch();self.role_chip=StatusChip();context.addWidget(self.role_chip)
        options=QPushButton('Options');menu=QMenu(options);options.setMenu(menu)
        menu.addAction('Refresh',lambda:self.safe(self.refresh_all));menu.addAction('Open Database Folder',lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.db.path.parent))))
        menu.addAction('Reset Layout',self.reset_layout);menu.addAction('About',self.show_about)
        context.addWidget(options)
        self.outer=QSplitter(Qt.Vertical);layout.addWidget(self.outer,1)
        body=QWidget();body_layout=QHBoxLayout(body);body_layout.setContentsMargins(0,6,0,0)
        nav=QWidget();nav.setFixedWidth(140);nav_layout=QVBoxLayout(nav);nav_layout.setContentsMargins(0,0,0,0)
        self.stack=QStackedWidget();self.sidebar_buttons={};self.pages={}
        for name in ('Workflow','Catalog','Audit','Problems','Curate','History','Details'):
            b=button(name,lambda checked=False,n=name:self.navigate(n));b.setCheckable(True);b.setProperty('navigation',True);b.setIcon(icon(name));nav_layout.addWidget(b);self.sidebar_buttons[name]=b
            if name=='Workflow':b.setStyleSheet('QPushButton:checked {background:#202E40;color:#9BCBFF;border-left:2px solid #438DF0;}')
        nav_layout.addStretch();body_layout.addWidget(nav);body_layout.addWidget(self.stack,1)
        for cls in (WorkflowPage,CatalogPage,AuditPage,ProblemsPage,CuratePage,HistoryPage,DetailsPage):
            page=cls(self);self.pages[page.name]=page;self.stack.addWidget(page)
        self.workflow=self.pages['Workflow'];self.catalog=self.pages['Catalog'];self.audit=self.pages['Audit'];self.problems=self.pages['Problems'];self.curate=self.pages['Curate'];self.details=self.pages['Details']
        self.outer.addWidget(body);self.drawer=CommandDrawer(self);self.outer.addWidget(self.drawer);self.outer.setStretchFactor(0,1)
        self.status_label=QLabel('Ready');self.status_label.setWordWrap(True);self.statusBar().addWidget(self.status_label,1)
        self.shortcuts=[]
        for sequence,callback in [('Ctrl+F',self.focus_search),('Escape',lambda:self.drawer.set_expanded(False))]:
            shortcut=QShortcut(QKeySequence(sequence),self);shortcut.activated.connect(callback);self.shortcuts.append(shortcut)
        for table,callback in ((self.workflow.table,lambda:self.workflow.open_tool('Details')),
                              (self.catalog.table,self.catalog.open_details),(self.problems.table,self.problems.open_curate)):
            shortcut=QShortcut(QKeySequence('Return'),table);shortcut.setContext(Qt.WidgetWithChildrenShortcut)
            shortcut.activated.connect(lambda cb=callback:self.safe(cb));self.shortcuts.append(shortcut)
        restore_working_set(self.session,self.settings)
        self.refresh_all();self.restore_ui();self.bound_window();self.workflow.narrow=None;self.workflow.adapt();self.navigate('Workflow')
        self.remember_session()

    def show_about(self):
        from ddk_schema import SCHEMA_VERSION
        from ddk_review import GRAMMAR_VERSION
        self.show_text('About',f'MangaAnkā DDK 0.3.0 · Qt Widgets frontend\nSchema v{SCHEMA_VERSION} · Grammar {GRAMMAR_VERSION} · existing validated DDK backend')

    @property
    def db(self):return self.session.db

    def safe(self,callback):
        try:return callback()
        except Exception as exc:
            self.feedback(str(exc));box=QMessageBox(QMessageBox.Warning,'Action blocked',str(exc),QMessageBox.Ok,self);box.exec()

    def navigate(self,name):
        if name not in self.pages:name='Catalog'
        self.stack.setCurrentWidget(self.pages[name])
        for n,b in self.sidebar_buttons.items():b.setChecked(n==name)
        self.status_label.setText(self.page_feedback.get(name, 'Ready · '+name))

    def feedback(self,message,page=None):
        page=page or self.stack.currentWidget().name
        self.page_feedback[page]=str(message)
        if self.stack.currentWidget().name==page:self.status_label.setText(str(message))

    def audit_feedback(self,message):
        # Catalog owns the Run action too; unrelated pages retain their context.
        for page in ('Workflow','Audit','Catalog'):self.feedback(message,page)

    def focus_search(self):self.stack.currentWidget().search.setFocus();self.stack.currentWidget().search.selectAll()

    def form(self,title,fields,explanation=''):
        dialog=FormDialog(self,title,fields,explanation)
        return dialog.values() if dialog.exec()==QDialog.Accepted else None

    def confirm(self,title,text):return QMessageBox.question(self,title,text,QMessageBox.Yes|QMessageBox.No,QMessageBox.No)==QMessageBox.Yes

    def show_text(self,title,value):
        dialog=QDialog(self);dialog.setWindowTitle(title);dialog.resize(850,620);layout=QVBoxLayout(dialog)
        text=RawData();text.show_data(value);layout.addWidget(text);layout.addWidget(button('Copy',lambda:self.copy_text(text.toPlainText())));layout.addWidget(button('Close',dialog.accept));dialog.exec()

    def update_context(self):
        old_database_menu=getattr(self,'database_menu',None);old_working_set_menu=getattr(self,'working_set_menu',None)
        self.database_button.setText(self.db.path.name+' ▾');self.database_button.setToolTip(str(self.db.path));self.database_button.setAccessibleName('Database selector')
        menu=QMenu(self.database_button);menu.setToolTipsVisible(True)
        menu.addAction('Switch Database…',lambda:self.safe(self.choose_database));menu.addAction('New Database…',lambda:self.safe(self.new_database))
        menu.addAction('Open Folder',lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.db.path.parent))));menu.addSeparator()
        with self.db.con() as c:
            schema=c.execute('PRAGMA user_version').fetchone()[0];counts=[c.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in ('works','search_audits')]
        for text in (self.db.role,f'Schema {schema}',f'{counts[0]} works · {counts[1]} audits'):
            a=menu.addAction(text);a.setEnabled(False)
        menu.addAction('Copy Database UUID',lambda:self.copy_text(self.db.database_uuid));self.database_button.setMenu(menu);self.database_menu=menu
        ws=self.db.working_sets.get(self.session.active_uuid)
        self.set_button.setText((f"{ws['name']} · {ws['status']}" if ws else 'No active Working Set')+' ▾');self.set_button.setAccessibleName('Working Set selector')
        menu=QMenu(self.set_button);menu.setToolTipsVisible(True)
        switch=menu.addMenu('Switch Working Set');self.working_set_switch_menu=switch
        for s in self.db.working_sets.list():switch.addAction(s['name']+' · '+s['status'],lambda checked=False,uid=s['working_set_uuid']:self.safe(lambda:self.activate_set(uid)))
        menu.addAction('New Working Set…',lambda:self.safe(self.new_set));menu.addSeparator()
        for state in ('OPEN','REVIEW','COMPLETE','ARCHIVED'):
            a=menu.addAction(state,lambda checked=False,target=state:self.safe(lambda:self.set_status(target)))
            allowed=bool(ws and not self.busy and (ws['status'] in ('OPEN','REVIEW') or ws['status']=='COMPLETE' and state=='ARCHIVED') and ws['status']!=state)
            if state=='COMPLETE' and allowed:
                items=self.db.working_sets.items(self.session.active_uuid);allowed=bool(items) and all(i['processing_status'] in ('ACCEPTED','REJECTED','DUPLICATE') for i in items)
            a.setEnabled(allowed);a.setToolTip('Explicit human status change' if allowed else 'Protected sets require Reopen for Review; COMPLETE requires all items terminal.')
        a=menu.addAction('Reopen for Review',lambda:self.safe(self.reopen_set));a.setEnabled(bool(ws and ws['status'] in ('COMPLETE','ARCHIVED') and not self.busy))
        self.set_button.setMenu(menu);self.working_set_menu=menu;self.database_button.setEnabled(not self.busy);self.set_button.setEnabled(not self.busy);self.role_chip.setText(self.db.role)
        if old_database_menu:old_database_menu.deleteLater()
        if old_working_set_menu:old_working_set_menu.deleteLater()

    def refresh_all(self):
        self.update_context()
        for page in self.pages.values():page.refresh()

    def selection(self,page=None,required=True):
        page=page or self.catalog
        rows=page.table.selected()
        if required and not rows:raise ValueError('Select exact title rows first.')
        return capture(self.session,page.scope,rows)

    def activate_set(self,uid):
        if self.busy:raise ValueError('Wait for the current run before switching context.')
        self.command.cancel();self.drawer.apply_button.setEnabled(False);self.session.activate_working_set(uid);self.refresh_all();self.remember_session()

    def new_set(self):
        v=self.form('New Working Set',[('name','Name','',None),('description','Description','',None),('language','Language','en',None),('workflow','Workflow','volume',['volume','chapter'])])
        if v:
            uid=self.db.working_sets.create(v['name'],v['description'],v['language'],v['workflow']);self.activate_set(uid)

    def set_status(self,state):
        if self.busy:raise ValueError('Wait for the current audit run.')
        if state in ('COMPLETE','ARCHIVED') and not self.confirm(state+' Working Set','Record this human status decision? Pins and item decisions remain intact.'):return
        self.db.working_sets.set_status(self.session.active_uuid,state);self.refresh_all()

    def reopen_set(self):
        self.db.working_sets.reopen(self.session.active_uuid);self.refresh_all()

    def choose_database(self):
        path,_=QFileDialog.getOpenFileName(self,'Switch Database',str(self.db.path.parent),'SQLite databases (*.db *.sqlite)')
        if path:self.switch_database(path)

    def new_database(self):
        path,_=QFileDialog.getSaveFileName(self,'New Database',str(self.db.path.parent/'scratch.db'),'SQLite databases (*.db)')
        if not path:return
        v=self.form('New Database',[('role','Role','SCRATCH',['SCRATCH','TEST','PRODUCTION'])],'Create a separate empty catalog. Existing files are never overwritten.')
        if v:self.switch_database(path,True,v['role'])

    def switch_database(self,path,create=False,role='SCRATCH'):
        if self.busy:raise ValueError('Cancel or finish the current run before switching databases.')
        self.session.open(path,create,role);self.page_feedback.clear();self.command.current=None;self.command.rows=[];self.command.selection=set();self.drawer.cancel();self.curate.work_id=None;self.details.work_id=None;self.details.item=None
        self.last_force_all=None;self.force_all_progress=''
        restore_working_set(self.session,self.settings)
        self.deferred_timer.stop();self.deferred_run_ids=[];self.deferred=set()
        self.audit.runtime_activity=[];self.audit.stage.setText('Idle · choose a Working Set to run.');self.audit.progress.setValue(0)
        for page in self.pages.values():page.set_scope('active')
        self.refresh_all()
        self.navigate(self.stack.currentWidget().name)
        self.remember_session()

    def intake(self):
        self.db.working_sets.guard(set_uuid=self.session.active_uuid,membership=True)
        v=self.form('Intake Context',[('edition','Edition','standard',['standard','official_color','fan_color','omnibus','deluxe','bunkobon','kanzenban']),('language','Language','en',None),('workflow','Workflow','volume',['volume','chapter'])])
        if not v:return
        dialog=QDialog(self);dialog.setWindowTitle('Intake · one title per line');dialog.resize(600,400);layout=QVBoxLayout(dialog);text=QPlainTextEdit();layout.addWidget(text)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);layout.addWidget(buttons)
        layout.addWidget(button('Load Title File',lambda:self.load_intake_file(text)))
        if dialog.exec()==QDialog.Accepted:
            result=self.db.working_sets.add_requests(self.session.active_uuid,text.toPlainText().splitlines(),v['edition'],v['language'],v['workflow'])
            self.feedback(str(result));self.catalog.set_scope('active');self.refresh_all()

    def load_intake_file(self,widget):
        path,_=QFileDialog.getOpenFileName(self,'Load Titles','','Text files (*.txt)')
        if path:widget.setPlainText(Path(path).read_text(encoding='utf-8-sig'))

    def selected_entries(self,selection=None):
        rows=resolve(self.session,selection or self.selection())
        if not rows:raise ValueError('Select catalog rows first.')
        return rows

    def selected_work(self):
        row=self.selected_entries()[0]
        if not row['_work_id']:raise ValueError('Select a linked catalog work.')
        return row['_work_id'],row['_item']

    def accept_selected(self,selection=None):
        items=[];works=[];expected={};lines=[]
        selection=selection or self.selection()
        for r in self.selected_entries(selection):
            wid=r['_work_id'];item=r['_item']
            if not wid:raise ValueError('Unlinked intake cannot be accepted.')
            uid=item['working_set_item_uuid'] if item else None;result=self.db.acceptance.evaluate(wid,uid)
            if not result['eligible']:raise ValueError('\n'.join(result['blockers']))
            key=uid or wid;(items if item else works).append(key);expected[str(key)]=result['fingerprint']
            lines.append(f"{r['query']}: audit {result['audit_id']} · curation {result['curation_revision']}")
        if self.confirm('Accept Selected','Approve these exact safe snapshots?\n\n'+'\n'.join(lines)):
            resolve(self.session,selection)
            self.db.acceptance.accept(items,works,expected);self.refresh_all()

    def accept_all_safe(self,selection=None):
        selection=selection or capture(self.session,'active')
        resolve(self.session,selection)
        p=self.db.acceptance.bulk_preview(selection.set_uuid)
        if p['ready_items'] and self.confirm('Accept All Safe',f"{len(p['candidates'])} safe · {p['review']} review · {p['error']} error · {p['stale']} stale. Recheck every snapshot and accept safe items?"):
            resolve(self.session,selection)
            self.db.acceptance.accept(p['ready_items'],expected=p['candidates'],bulk=True);self.refresh_all()
        elif not p['ready_items']:self.feedback('No READY items to approve. Review problems or run stale intake.')

    def reevaluate(self):
        wid,_=self.selected_work();dialog=ReconciliationDialog(self,wid);dialog.exec()

    def reopen_items(self,selection=None):
        selection=selection or self.selection()
        ids=[r['_item']['working_set_item_uuid'] for r in self.selected_entries(selection) if r['_item']]
        if not ids:raise ValueError('Select exact accepted/rejected intake items.')
        if self.confirm('Reopen Selected for Review','Queue selected terminal items for review? Old pins and decision history remain.'):
            resolve(self.session,selection)
            self.db.working_sets.reopen_items(ids);self.refresh_all()

    def reject_items(self):
        if self.confirm('Reject Intake','Record selected intake items as REJECTED?'):
            for r in self.selected_entries():
                if r['_item']:self.db.working_sets.set_item_status(r['_item']['working_set_item_uuid'],'REJECTED')
            self.refresh_all()

    def remove_items(self):
        if self.confirm('Remove Intake','Remove selected requests from this set? Catalog evidence remains.'):
            for r in self.selected_entries():
                if r['_item']:self.db.working_sets.remove_item(r['_item']['working_set_item_uuid'])
            self.refresh_all()

    def open_review(self):
        self.catalog.set_scope('active');self.catalog.filters['item_status'].setCurrentText('REVIEW');self.catalog.refresh();self.navigate('Catalog')

    def run_working_set(self):
        if self.busy or self.force_confirmation_pending:return
        self.db.working_sets.recover_interrupted();ids=self.db.working_sets.run_candidates(self.session.active_uuid)
        if ids:self.start_audit(ids)
        else:self.audit.stage.setText('No pending or stale items. Accept All Safe / Open Review Items / Retry Errors.');self.audit_feedback(self.audit.stage.text())

    def retry_errors(self):
        if not self.busy and not self.force_confirmation_pending:self.start_audit(self.db.working_sets.retry_errors(self.session.active_uuid))

    def force_selected_item(self,selection=None):
        if self.busy or self.force_confirmation_pending:raise ValueError('Wait for the current audit or confirmation.')
        selection=selection or self.selection()
        rows=resolve(self.session,selection)
        if len(rows)!=1 or not rows[0].get('_item'):
            raise ValueError('Select one exact Working Set item in Catalog.')
        item=self.db.working_sets.force_audit_candidate(rows[0]['_item']['working_set_item_uuid'])
        if selection.set_uuid!=item['working_set_uuid']:
            raise ValueError('Select the item in its exact Working Set scope.')
        return item

    def confirm_force_reaudit(self,title):
        box=QMessageBox(QMessageBox.Question,'Force Re-Audit Selected',
            f'Force a new audit for {title}?\n\nA new audit will be created using the current audit logic.\n'
            'Previous audits, curation, and evidence will be preserved.\nExisting acceptance may become stale.',
            QMessageBox.NoButton,self)
        force=box.addButton('Force Re-Audit',QMessageBox.AcceptRole)
        cancel=box.addButton('Cancel',QMessageBox.RejectRole)
        box.setDefaultButton(cancel);box.setEscapeButton(cancel);box.exec()
        return box.clickedButton()==force

    def force_reaudit_selected(self,selection=None):
        selection=selection or self.selection()
        item=self.force_selected_item(selection)
        self.force_confirmation_pending=True;self.catalog.update_force_action()
        try:confirmed=self.confirm_force_reaudit(item['original_query'])
        finally:
            self.force_confirmation_pending=False;self.catalog.update_force_action()
        if confirmed:
            self.force_selected_item(selection)
            return self.start_audit([item['working_set_item_uuid']],force_reaudit=True)
        return False

    def force_all_plan(self):
        if self.busy or self.force_confirmation_pending or self.deferred or self.deferred_run_ids:
            raise ValueError('Wait for the current audit, queued re-audit, or confirmation.')
        return self.db.working_sets.force_audit_plan(self.session.active_uuid)

    def confirm_force_all(self,plan):
        accepted=sum(i['processing_status']=='ACCEPTED' for i in plan['items'])
        box=QMessageBox(QMessageBox.Question,'Force Re-Audit All',
            f'Force new audits for {len(plan["items"])} titles in {plan["name"]}?\n\n'
            f'Includes {accepted} ACCEPTED titles. {len(plan["skipped"])} ineligible items will be skipped.\n'
            'New immutable audit records will be created; previous audits, curated corrections, evidence, '
            'and acceptance history will be preserved.\n'
            'Existing approvals may become STALE; new findings remain visible. No title will be automatically accepted.\n'
            'Titles run sequentially. Cancel Run safely stops the current audit; unprocessed titles stay unchanged.',
            QMessageBox.NoButton,self)
        force=box.addButton('Force Re-Audit All',QMessageBox.AcceptRole)
        cancel=box.addButton('Cancel',QMessageBox.RejectRole)
        box.setDefaultButton(cancel);box.setEscapeButton(cancel);box.exec()
        return box.clickedButton()==force

    def force_reaudit_all(self):
        plan=self.force_all_plan()
        if not plan['items']:raise ValueError('No eligible active titles in this Working Set.')
        self.force_confirmation_pending=True;self.workflow.update_actions();self.catalog.update_force_action()
        try:confirmed=self.confirm_force_all(plan)
        finally:
            self.force_confirmation_pending=False;self.workflow.update_actions();self.catalog.update_force_action()
        if not confirmed:return False
        if self.force_all_plan()!=plan:
            raise ValueError('Working Set changed during confirmation; confirm a fresh batch.')
        return self.start_audit([i['working_set_item_uuid'] for i in plan['items']],force_all_plan=plan)

    def show_force_all_results(self):
        if self.last_force_all:self.show_text('Force Re-Audit All results',self.last_force_all)

    def start_audit(self,ids,force_reaudit=False,force_all_plan=None):
        if self.busy or self.force_confirmation_pending:return False
        if not ids:return False
        if force_all_plan is not None:
            if force_reaudit or force_all_plan!=self.force_all_plan() or ids!=[i['working_set_item_uuid'] for i in force_all_plan['items']]:
                raise ValueError('Force Re-Audit All requires the current exact Working Set snapshot.')
        if force_reaudit:
            if len(ids)!=1:raise ValueError('Force Re-Audit requires one exact item.')
            self.db.working_sets.queue_force_audit(ids[0])
        for uid in (() if force_reaudit or force_all_plan is not None else ids):
            if isinstance(uid,str):
                item=self.db.working_sets.item(uid);self.db.working_sets.editable_item(uid)
                if item['working_set_uuid']!=self.session.active_uuid:raise ValueError('Activate the exact Working Set first.')
                self.db.working_sets.set_item_status(uid,'QUEUED')
        self.busy=True;self.run_failed=False;self.run_started=time.monotonic();self.current_started=self.run_started;self.current_title='Starting';self.current_key=None;self.batch_progress=f'0/{len(ids)}';self.run_ids=list(ids)
        self.run_force_all=force_all_plan is not None;self.force_all_progress=''
        if self.run_force_all:self.last_force_all=None
        self.run_set_uuid=self.session.active_uuid if any(isinstance(uid,str) for uid in ids) else None
        self.audit.stage.setText(f'Running… 0 / {len(ids)} · Starting audit');self.audit.progress.setRange(0,0);self.audit_feedback('Running…')
        for b in (self.catalog.run_button,self.audit.run_button):b.setText('Running…');b.setEnabled(False)
        self.catalog.accept_all_button.setEnabled(False);self.audit.retry_button.setEnabled(False);self.audit.stop_button.setEnabled(True);self.update_context()
        self.catalog.update_force_action()
        kwargs={'auditor_factory':self.auditor_factory} if self.auditor_factory else {}
        if force_reaudit:kwargs['force_reaudit']=True
        if force_all_plan is not None:kwargs['force_all_plan']=force_all_plan
        self.worker=AuditWorker(self.db,list(ids),parent=self,**kwargs)
        self.worker.event.connect(self.audit_event);self.worker.failed.connect(self.audit_failed);self.worker.finished.connect(self.audit_finished)
        self.workflow.runtime();self.worker.start();return True

    def cancel_run(self):
        if self.worker:self.worker.cancel();self.audit.stage.setText('Cancelling… waiting for the current provider request to finish.');self.audit.stop_button.setEnabled(False)

    def audit_event(self,kind,payload):
        if kind=='batch':
            text=payload.get('text','');self.audit.stage.setText('Running '+text);self.current_title=text.split('  ',1)[-1];self.batch_progress=text.split('  ',1)[0];self.current_started=time.monotonic()
            self.current_key=next((key for key in self.run_ids if (
                (self.db.working_sets.item(key) or {}).get('original_query') if isinstance(key,str) else (self.db.work(key) or {}).get('input_title'))==self.current_title),None)
            if payload.get('work_id') is not None:self.current_key=payload['work_id']
        elif kind=='status':
            if self.run_failed:return
            key=payload.get('work_id')
            if isinstance(key,str) or not isinstance(self.current_key,str):self.current_key=key if key is not None else self.current_key
            self.audit.stage.setText(f"Running {self.batch_progress} · {self.current_title} · {payload.get('text','')}"+
                (f'\n{self.force_all_progress}' if self.force_all_progress else ''));self.audit.progress.setRange(0,100);self.audit.progress.setValue(payload.get('progress',0));self.audit_feedback(self.audit.stage.text())
        elif kind=='refresh':
            key=self.current_key;item=self.db.working_sets.item(key) if isinstance(key,str) else None
            wid=item['work_id'] if item else key if isinstance(key,int) else None;latest=self.db.latest_audit(wid) if wid else None
            self.audit.runtime_activity.append(dict(time=datetime.now(timezone.utc).isoformat(timespec='seconds'),title=self.current_title,
                result=item['processing_status'] if item else latest['final_state'] if latest else 'Finished',audit_id=latest['id'] if latest else None,
                duration=f'{time.monotonic()-self.current_started:.1f}s',_work_id=wid,_set_uuid=self.run_set_uuid,_audit=dict(latest) if latest else payload))
            self.refresh_all()
        elif kind=='force_progress':
            self.force_all_progress=payload['text'];self.audit.stage.setText(payload['text']+f' · {payload.get("current_title",self.current_title)}');self.audit_feedback(self.audit.stage.text())
        elif kind=='done':
            if payload.get('force_all'):self.last_force_all=payload
            self.audit.stage.setText(payload.get('text','Run complete'));self.audit_feedback(self.audit.stage.text())
        self.workflow.runtime()

    def audit_failed(self,message,details):
        self.run_failed=True;self.audit.stage.setText('Audit failed: '+message);self.audit_feedback('Audit failed: '+message)
        self.audit.inspector.display('Run failure',{'Error':{'Reason':message,'Next action':'Retry Errors, or run queued intake after correcting the cause.'}},raw=details)

    def audit_finished(self):
        worker=self.worker;cancelled=bool(worker and worker.cancel_requested.is_set());self.worker=None;self.busy=False
        if worker:worker.deleteLater()
        for b in (self.catalog.run_button,self.audit.run_button):b.setText('Run Working Set');b.setEnabled(True)
        self.catalog.accept_all_button.setEnabled(True);self.audit.retry_button.setEnabled(True);self.audit.stop_button.setEnabled(False);self.audit.progress.setRange(0,100)
        if cancelled and not self.run_force_all:self.audit.stage.setText('Run cancelled · previous successful pins preserved.');self.audit_feedback(self.audit.stage.text())
        elif not self.run_failed and self.audit.stage.text().startswith(('Running','Starting')):self.audit.stage.setText('Run complete');self.audit_feedback('Run complete')
        self.refresh_all()
        if self.run_force_all and self.last_force_all:
            self.audit.inspector.display('Force Re-Audit All results',{'Summary':{'Result':self.last_force_all['text']}},raw=self.last_force_all)
        deferred=self.deferred;self.deferred=set()
        if deferred:
            candidates=set(self.db.working_sets.run_candidates(self.session.active_uuid));ids=sorted(deferred & candidates)
            if ids:self.deferred_run_ids=ids;self.deferred_timer.start(150)

    def run_deferred(self):
        ids=self.deferred_run_ids;self.deferred_run_ids=[]
        if self.busy:self.deferred.update(ids)
        elif ids:self.safe(lambda:self.start_audit(ids))

    def post_curation(self,item):
        if not item:return
        self.db.working_sets.guard(item_uuid=item);self.db.working_sets.set_item_status(item,'QUEUED')
        if self.busy:
            self.deferred.add(item);self.feedback('Curation saved; fresh audit queued after this run.','Curate');self.workflow.runtime()
        else:self.start_audit([item])

    def open_curate(self,wid,scope,keys=()):
        if not wid:raise ValueError('Open a linked title first.')
        self.curate.set_scope(scope);self.curate.refresh();self.curate.open(wid);self.navigate('Curate')
        if keys:self.curate.map.focus_keys(keys)

    def open_details(self,wid,scope,item=None):
        self.details.set_scope(scope);self.details.refresh();self.details.open(wid,item);self.navigate('Details')

    def drawer_command(self,text):
        self.drawer.input.setPlainText(text);self.drawer.preview()

    def preview_fields(self,fields,title):
        if self.command.current is None:raise ValueError('Open a title first.')
        self.command.preview(fields,title);self.drawer.set_expanded(True);self.drawer.output.show_data(self.command.preview_text());self.drawer.apply_button.setEnabled(True)

    def edit_chapter(self):
        rows=[r for r in self.command.rows if r['iid'] in self.command.selection]
        if len(rows)!=1:raise ValueError('Select one exact chapter.')
        row=rows[0];v=self.form('Edit Chapter',[(k,k.replace('_',' ').title(),row['effective'].get(k),None) for k in ('volume','title','type','source_note')]+[('verification','Verification','REVIEWED',['UNVERIFIED','REVIEWED','VERIFIED'])])
        if v:self.preview_fields([dict(entity='chapter',key=row['key'],field=k,value=v[k] or None,verification=v['verification']) for k in ('volume','title','type','source_note') if v[k]!=(str(row['effective'].get(k) or ''))],'Edit Chapter')

    def verify_chapters(self):
        v=self.form('Verify Curated Fields',[('verification','Verification','VERIFIED',['UNVERIFIED','REVIEWED','VERIFIED'])])
        if v:self.drawer_command('set verification '+v['verification'].lower()+' selected')

    def edit_evidence(self):
        v=self.form('Add Evidence',[('source','Source','',None),('url','URL','',None),('note','Note','',None),('accessed','Accessed at (UTC)','',None)])
        if v:
            import shlex
            self.drawer_command('add evidence source '+shlex.quote(v['source'])+' url '+shlex.quote(v['url'])+' note '+shlex.quote(v['note'])+(' accessed '+shlex.quote(v['accessed']) if v['accessed'] else '')+' selected')

    def edit_identity(self):
        if self.command.current is None:raise ValueError('Open a title first.')
        work=self.db.work(self.command.current);state=self.db.catalog.state(self.command.current)
        values={k:work[k] for k in ('canonical_title','canonical_work_id','edition','language')}
        auto,_=self.db.catalog.snapshot(self.command.current);identity=state['identity'] or auto.get('catalog_identity') or {}
        values.update(publication_context=identity.get('publication_context',''),aliases='',external_ids=identity.get('external_ids',{}),expected_chapters='',expected_volumes='',publication_status='',source_note='')
        for field in state['fields']:
            if field['entity']=='work':values[field['field']]=field['value']
        values['aliases']='; '.join(values['aliases']) if isinstance(values['aliases'],list) else values['aliases']
        values['external_ids']='; '.join(f'{k}={v}' for k,v in values['external_ids'].items()) if isinstance(values['external_ids'],dict) else values['external_ids']
        v=self.form('Edit Work Identity',[(k,k.replace('_',' ').title(),value,None) for k,value in values.items()]+[('verification','Verification','REVIEWED',['UNVERIFIED','REVIEWED','VERIFIED'])])
        if v:
            verification=v.pop('verification');changes=[]
            for key,value in v.items():
                if str(value)==str(values[key] or ''):continue
                if key=='aliases':value=[s.strip() for s in value.split(';') if s.strip()]
                elif key=='external_ids':value=self.command.ids(value)
                changes.append(dict(entity='work',key='work',field=key,value=value,verification=verification))
            self.preview_fields(changes,'Edit Work Identity')

    def edit_volume(self):
        v=self.form('Edit Volume',[('volume','Exact volume','',None),('title','Volume title','',None),('external_ids','External IDs (source=value; …)','',None),('source_note','Source note','',None),('verification','Verification','REVIEWED',['UNVERIFIED','REVIEWED','VERIFIED'])])
        if v:
            v['external_ids']=self.command.ids(v['external_ids'])
            self.preview_fields([dict(entity='volume',key=v['volume'],field=k,value=v[k],verification=v['verification']) for k in ('title','external_ids','source_note')],'Edit Volume')

    def share_structure(self):
        if self.command.current is None:raise ValueError('Open a target edition first.')
        v=self.form('Share Reviewed Structure',[('source','Source work UUID','',None),('note','Evidence / reason','',None),('verification','Verification','REVIEWED',['REVIEWED','VERIFIED'])], 'Explicit related-edition structure sharing. Backend validates exact canonical work, language and edition separation.')
        if v:
            item=self.session.mutation_item(self.command.current,self.curate.scope)
            source=next((w for w in self.db.works() if w['work_uuid']==v['source']),None)
            if not source:raise ValueError('Choose an exact existing source work UUID.')
            self.db.working_sets.relate_structure(source['id'],self.command.current,v['note'],v['verification'],item_uuid=item);self.refresh_all();self.post_curation(item)

    def export_patch(self):
        if self.command.current is None:raise ValueError('Open a title first.')
        path,_=QFileDialog.getSaveFileName(self,'Export Curated Patch',str(self.db.path.parent/'curated-patch.json'),'JSON (*.json)')
        if path:self.feedback('Exported '+str(self.db.catalog.export(self.command.current,path)))

    def disposition(self,reopen):
        row=self.problems.table.current()
        if not row or not row['_hole']:raise ValueError('Choose a linked problem; intake observations cannot receive dispositions.')
        h=row['_hole'];item=self.session.mutation_item(h['work_id'],self.problems.scope)
        v=self.form('Reopen Problem' if reopen else 'Record Disposition',[('reason','Evidence-grounded reason','',None),('verification','Verification','REVIEWED',['REVIEWED','VERIFIED'])])
        if v:
            if reopen:self.db.reopen_problem(h['id'],v['reason'],v['verification'],item_uuid=item)
            else:self.db.dispose_problem(h['id'],v['reason'],v['verification'],item_uuid=item)
            self.refresh_all()

    def delete_work(self):
        if self.busy:raise ValueError('Finish or cancel the run before maintenance.')
        wid,_=self.selected_work();preview=self.db.maintenance.preview(self.db.work(wid)['work_uuid']);DeleteDialog(self,preview).exec()

    def copy_text(self,text):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(text);self.feedback('Copied to clipboard')

    def copy_selected(self,kind):
        rows=self.selected_entries();texts=[]
        if kind=='csv':
            out=StringIO();writer=csv.DictWriter(out,[c[0] for c in self.catalog.table.records.columns],extrasaction='ignore');writer.writeheader();writer.writerows(rows);self.copy_text(out.getvalue());return
        for r in rows:
            if kind=='title':texts.append(r['query'])
            elif kind=='uuid':texts.append(r.get('work_uuid') or '')
            elif r['_work_id']:
                if kind=='full':
                    c,item=self.session.context(r['_work_id'],self.catalog.scope,r['_item']);a=self.db.audit(c['audit_id'],r['_work_id']) if c['audit_id'] else None
                    texts.append(pretty(dict(context=c,audit=dict(a) if a else None,latest_attempt=self.db.working_sets.latest_observation(item['working_set_item_uuid']) if item else None)))
                else:texts.append((catalog_summary if kind=='summary' else review_context)(self.db,r['_work_id'],r['_item']))
        self.copy_text('\n\n'.join(texts))

    def export_set(self,kind,copy=False,mode='pinned'):
        uid=self.session.set_uuid(self.catalog.scope)
        if not uid:raise ValueError('Choose a Working Set scope before exporting a set.')
        text=working_set_title_list(self.db,uid) if kind=='titles' else working_set_csv(self.db,uid,mode) if kind=='csv' else pretty(working_set_packet(self.db,uid,mode)) if kind=='packet' else working_set_review_context(self.db,uid,mode)
        if copy:self.copy_text(text)
        else:self.save_text('Working Set '+kind,text,'csv' if kind=='csv' else 'txt' if kind=='titles' else 'md')

    def export_review_packet(self,selection,mode='pinned'):
        resolve(self.session,selection)
        uid=selection.set_uuid;db=self.db
        if not uid:raise ValueError('Choose a Working Set before exporting.')
        digest=export_receipts.fingerprint(db,uid,mode)
        packet=working_set_packet(db,uid,mode)
        if digest!=export_receipts.fingerprint(db,uid,mode):
            raise ValueError('Set changed while preparing export; export again.')
        path=self.save_text('Review Packet · '+mode,pretty(packet),'json')
        if path:
            try:
                export_receipts.remember(self.settings,db,uid,mode,digest,path)
                if self.settings.status()!=QSettings.NoError:raise OSError('Preferences could not be saved.')
            except Exception as exc:self.feedback('File exported; local receipt could not be saved: '+str(exc),'Workflow')
            self.workflow.refresh()
        return path

    def export_catalog(self):
        rows=self.session.catalog_rows(self.catalog.scope);out=StringIO();keys=[c[0] for c in self.catalog.table.records.columns]
        writer=csv.DictWriter(out,keys,extrasaction='ignore');writer.writeheader();writer.writerows(rows);self.save_text('Catalog CSV',out.getvalue(),'csv')

    def save_text(self,title,text,suffix):
        path,_=QFileDialog.getSaveFileName(self,title,str(self.db.path.parent/('export.'+suffix)),f'{suffix.upper()} (*.{suffix})')
        if path:Path(path).write_text(text,encoding='utf-8');self.feedback('Exported '+path)
        return path or None

    def bound_window(self):
        screen=self.screen()
        if screen and not self.isMaximized():
            area=screen.availableGeometry()
            self.resize(max(self.minimumWidth(),min(self.width(),area.width()-40)),
                        max(self.minimumHeight(),min(self.height(),area.height()-70)))

    def save_ui(self):
        self.remember_session()
        s=self.settings;s.setValue('geometry',self.saveGeometry());s.setValue('maximized',self.isMaximized());s.setValue('last_page',self.stack.currentWidget().name)
        s.setValue('outer_splitter',self.outer.saveState());s.setValue('drawer_expanded',not self.drawer.body.isHidden())
        for name,page in self.pages.items():
            s.setValue(name+'/splitter',page.splitter.saveState());s.setValue(name+'/inspector',not page.inspector.isHidden())
            if hasattr(page,'table'):s.setValue(name+'/header',page.table.horizontalHeader().saveState())
        s.setValue('Catalog/columns',[not self.catalog.table.isColumnHidden(i) for i in range(len(self.catalog.column_actions))]);s.sync()

    def remember_session(self):
        try:
            remember_session(self.session,self.settings)
            if self.settings.status()!=QSettings.NoError:
                self.feedback('Session preferences could not be saved. The database remains open.')
        except Exception as exc:
            self.feedback('Session preferences could not be saved: '+str(exc))

    def restore_ui(self):
        s=self.settings
        if s.value('geometry'):self.restoreGeometry(s.value('geometry'))
        if s.value('maximized',False,type=bool):self.showMaximized()
        self.drawer.set_expanded(s.value('drawer_expanded',False,type=bool))
        if s.value('outer_splitter'):self.outer.restoreState(s.value('outer_splitter'))
        for name,page in self.pages.items():
            if s.value(name+'/splitter'):page.splitter.restoreState(s.value(name+'/splitter'))
            page.inspector.setVisible(s.value(name+'/inspector',name!='Details',type=bool))
            if hasattr(page,'table') and s.value(name+'/header'):page.table.horizontalHeader().restoreState(s.value(name+'/header'))
        values=s.value('Catalog/columns',[])
        for i,v in enumerate(values):
            if i<len(self.catalog.column_actions):self.catalog.column_actions[i].setChecked(str(v).lower()=='true')

    def reset_layout(self):
        self.resize(1440,900);self.drawer.set_expanded(False)
        for name,page in self.pages.items():page.splitter.setSizes([900,310]);page.inspector.setVisible(name!='Details')
        for i,a in enumerate(self.catalog.column_actions):a.setChecked(i<8);self.catalog.table.setColumnWidth(i,self.catalog.table.records.columns[i][2])

    def closeEvent(self,event):
        if self.busy:
            self.cancel_run();self.feedback('Cancelling audit; close again after it finishes.');event.ignore();return
        self.deferred_timer.stop();self.deferred_run_ids=[];self.save_ui();self.session.close();event.accept()
