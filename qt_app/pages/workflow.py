"""Production actions over exact memberships, with no independent audit policy."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QHBoxLayout, QVBoxLayout, QGridLayout, QWidget, QComboBox, QHeaderView, QGroupBox, QMenu
from qt_app.pages.base import Page
from qt_app.widgets.common import RecordTable, button
from qt_app.orchestration import capture, resolve
from qt_app.workflow_presentation import health_label, next_action, summary, intake_problems
from qt_app import export_receipts
from qt_app.widgets.workflow import SummaryCard,Guide,BLUE_BUTTON,PANEL


COLUMNS = [('query','Title',210,False),('health_display','Health',70,True),
    ('chapter_display','Chapters',95,False),('volumes','Volumes',65,False),
    ('item_status','Set State',105,True),('next_action','Next Action',175,False)]


class WorkflowPage(Page):
    def __init__(self,window):
        super().__init__(window,'Workflow')
        self.layout.setSpacing(6);self.layout.setContentsMargins(12,8,12,8)
        self.scope_box.hide();self.context_key=None;self.snapshots={};self.evaluations={}
        self.header=QLabel();self.header.setWordWrap(True);self.layout.insertWidget(1,self.header)
        self.new_button=self.add_action('New Batch',window.new_set)
        self.intake_button=self.add_action('Paste Titles',window.intake)
        self.run_button=self.add_action('Run Working Set',window.run_working_set,True)
        self.complete_button=self.add_action('Complete Set',lambda:window.set_status('COMPLETE'))
        self.select_button=self.add_action('Select Working Set',lambda:window.set_button.showMenu())
        self.batch_actions_button=self.add_action('Actions',lambda:None)
        self.batch_menu=QMenu(self.batch_actions_button);self.batch_actions_button.setMenu(self.batch_menu)
        self.force_all_action=self.batch_menu.addAction('Force Re-Audit All',lambda:window.safe(window.force_reaudit_all))
        self.cancel_all_action=self.batch_menu.addAction('Cancel Run',window.cancel_run)
        self.results_action=self.batch_menu.addAction('View Last Force Re-Audit Results',window.show_force_all_results)
        cards=QWidget();self.cards=QGridLayout(cards);self.cards.setContentsMargins(0,0,0,0)
        self.summaries={}
        for key,label,glyph,color in [('total','Titles','Catalog','#438DF0'),('accepted','Accepted','History','#49CB77'),
            ('eligible','Eligible','Details','#438DF0'),('review','Review','Audit','#EAC04B'),('error','Error','Problems','#F16D68')]:
            chip=SummaryCard(label,glyph,color)
            self.summaries[key]=chip
        self.layout.insertWidget(2,cards)
        self.guide=Guide();self.layout.insertWidget(3,self.guide)
        self.states=QLabel();self.states.setWordWrap(True);self.states.setProperty('secondary',True)
        self.layout.insertWidget(4,self.states)
        production=QWidget();self.production=QGridLayout(production);self.production.setContentsMargins(0,0,0,0)
        self.export_button=button('Export Review Packet',lambda:window.safe(self.export),primary=True)
        self.commands_button=button('Paste Fix Commands',lambda:window.safe(self.commands),primary=True)
        self.accept_button=button('Accept Eligible Titles',lambda:window.safe(lambda:window.accept_all_safe(self.batch_context())))
        self.production_buttons=[self.export_button,self.commands_button,self.accept_button]
        self.production_widget=production
        for b in (self.export_button,self.commands_button):b.setStyleSheet(BLUE_BUTTON)
        self.layout.insertWidget(5,production)
        self.receipt_label=QLabel();self.receipt_label.setWordWrap(True);self.layout.insertWidget(6,self.receipt_label)
        self.mode=QComboBox();self.mode.addItem('Pinned review','pinned');self.mode.addItem('Current global','current')
        self.mode.setAccessibleName('Review Packet export mode');self.filterbar.addWidget(self.mode)
        self.mode.currentIndexChanged.connect(self.receipt)
        self.state_filter=self.add_filter('Working Set state',['All','PENDING','QUEUED','AUDITING','READY','REVIEW','ERROR','ACCEPTED','REJECTED','DUPLICATE'],lambda _:self.filter_rows())
        self.state_filter.blockSignals(True)
        self.state_filter.setItemText(0,'Set state');self.state_filter.setItemData(0,'All')
        self.state_filter.blockSignals(False)
        self.health_filter=self.add_filter('Health',['All','Good','Review','Error','Unknown'],lambda _:self.filter_rows())
        self.health_filter.blockSignals(True);self.health_filter.setItemText(0,'Health');self.health_filter.setItemData(0,'All');self.health_filter.blockSignals(False)
        self.clear_button=button('Clear',self.clear_filters);self.filterbar.addWidget(self.clear_button)
        self.table=RecordTable(COLUMNS);self.table.setAccessibleName('Workflow exact Working Set memberships')
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.setStyleSheet('QTableView {border:1px solid #303C49;selection-background-color:#20466F;selection-color:#F4F5F7;}')
        self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch)
        self.set_content(self.table)
        self.table.selectionModel().selectionChanged.connect(self.selected)
        self.table.doubleClicked.connect(lambda _:window.safe(lambda:self.open_tool('Details')))
        self.search.setPlaceholderText('Search titles in this Working Set');self.search.textChanged.connect(self.filter_rows)
        contextual=QHBoxLayout();self.layout.addLayout(contextual)
        self.actions={}
        for name,cb in [('Retry Errors',window.retry_errors),('Force Re-Audit',lambda:window.force_reaudit_selected(self.selected_context())),
                        ('Reopen Selected',lambda:window.reopen_items(self.selected_context())),
                        ('Problems',lambda:self.open_tool('Problems')),('Curate',lambda:self.open_tool('Curate')),
                        ('Details',lambda:self.open_tool('Details'))]:
            b=button(name,lambda checked=False,callback=cb:window.safe(callback));self.actions[name]=b;contextual.addWidget(b)
        self.runtime_label=QLabel();self.runtime_label.setWordWrap(True);self.layout.addWidget(self.runtime_label)
        self.handoff=QLabel('Handoff: export a file → external review → guarded commands → Preview → Apply → automatic re-audit → export fresh → explicit acceptance.')
        self.handoff.setProperty('secondary',True);self.handoff.setWordWrap(True);self.layout.addWidget(self.handoff)
        # Reuse the widgets/actions above; reorganize them into the mockup's
        # table-left / health-and-actions-right hierarchy.
        self.left=QWidget();self.left_layout=QVBoxLayout(self.left);self.left_layout.setContentsMargins(0,0,0,0);self.left_layout.setSpacing(8)
        for widget in (cards,self.guide,self.states,self.empty,self.table):self.layout.removeWidget(widget)
        self.layout.removeItem(self.filterbar);self.filterbar.setParent(None)
        self.left_layout.addWidget(cards);self.left_layout.addWidget(self.guide);self.left_layout.addWidget(self.states)
        self.left_layout.addLayout(self.filterbar);self.left_layout.addWidget(self.empty);self.left_layout.addWidget(self.table,1)
        self.set_content(self.left)
        self.right=QWidget();self.right_layout=QVBoxLayout(self.right);self.right_layout.setContentsMargins(0,0,0,0);self.right_layout.setSpacing(8)
        self.right_layout.addWidget(self.inspector,1);self.splitter.addWidget(self.right)
        self.inspector.setStyleSheet('QScrollArea {border:1px solid #303C49;border-radius:6px;} QLabel[pageTitle="true"] {font-size:18px;} QGroupBox {font-size:11px;margin-top:10px;padding:2px;}')
        self.dock=QWidget();self.dock.setStyleSheet('QWidget#workflowActions {'+PANEL+'}');self.dock.setObjectName('workflowActions')
        self.dock_layout=QVBoxLayout(self.dock);self.dock_layout.setContentsMargins(10,10,10,10);self.dock_layout.setSpacing(6)
        self.action_title=QLabel('Next Actions');self.action_title.setStyleSheet('font-size:14px;font-weight:600;');self.dock_layout.addWidget(self.action_title)
        for widget in (production,self.receipt_label,self.runtime_label,self.handoff):self.layout.removeWidget(widget)
        self.filterbar.removeWidget(self.mode)
        self.dock_layout.addWidget(production);self.dock_layout.addWidget(self.mode);self.dock_layout.addWidget(self.receipt_label)
        self.layout.removeItem(contextual)
        while contextual.count():contextual.takeAt(0)
        contextual.setParent(None);contextual.deleteLater()
        self.secondary_widget=QWidget();self.secondary=QGridLayout(self.secondary_widget);self.secondary.setContentsMargins(0,0,0,0)
        self.dock_layout.addWidget(self.secondary_widget);self.dock_layout.addWidget(self.runtime_label);self.dock_layout.addWidget(self.handoff)
        self.right_layout.addWidget(self.dock)
        inspector_button=self.toolbar.itemAt(self.toolbar.count()-1).widget()
        inspector_button.clicked.disconnect()
        inspector_button.clicked.connect(self.toggle_inspector)
        self.adapt()

    @property
    def scope(self): return 'active'

    def batch_context(self): return capture(self.window.session,'active')

    def selected_context(self): return self.window.selection(self)

    def filter_rows(self):
        if not hasattr(self,'table'):return
        self.table.proxy.update(self.search.text(),{'item_status':self.state_filter.currentData() or self.state_filter.currentText(),
            'health_display':self.health_filter.currentData() or self.health_filter.currentText()})

    def clear_filters(self):
        self.search.clear();self.state_filter.setCurrentIndex(0);self.health_filter.setCurrentIndex(0)

    def refresh(self):
        session=self.window.session;db=self.window.db;uid=session.active_uuid
        key=(db.database_uuid,uid)
        old=self.table.current() if key==self.context_key else None
        self.context_key=key;ws=db.working_sets.get(uid);items=session.items('active')
        rows=session.catalog_rows('active');self.snapshots={};self.evaluations={}
        candidates={}
        if ws and ws['status'] in ('OPEN','REVIEW'):
            candidates=db.acceptance.bulk_preview(uid)['candidates']
        for row in rows:
            item=row['_item'];wid=row['_work_id'];iid=item['working_set_item_uuid']
            context,_=session.context(wid,'active',item) if wid else ({},None)
            evaluation=db.acceptance.evaluate(wid,iid) if wid else {}
            self.snapshots[iid]=context;self.evaluations[iid]=evaluation
            problems=context.get('problems') or []
            if not wid:
                observation=db.working_sets.latest_observation(iid)
                problems=intake_problems(observation)
            row['_problems']=problems
            row['health_display']=health_label(context.get('health') or {})
            row['next_action']=next_action(item,ws['status'],evaluation,problems)
        self._refreshing=True
        self.table.records.replace(rows);self.filter_rows()
        if old:self.table.select_record(lambda r:r['working_set_item_uuid']==old['working_set_item_uuid'])
        self._refreshing=False
        data=summary(items,candidates);self.summary=data
        for name,chip in self.summaries.items():
            value=data['counts'].get(name.upper(),0) if name in ('accepted','review','error') else data[name]
            chip.setText({'total':'Titles','accepted':'Accepted','eligible':'Eligible','review':'Review','error':'Error'}[name]+f' {value}')
        self.header.setText(f"{ws['name']} · {ws['status']} · {db.path.name}" if ws else f'No active Working Set · {db.path.name}')
        self.header.setToolTip(str(db.path))
        self.states.setText(' · '.join(f'{state} {data["counts"].get(state,0)}' for state in (
            'PENDING','QUEUED','AUDITING','READY','ACCEPTED','REJECTED','DUPLICATE'))+f' · Unlinked {data["unlinked"]}')
        self.empty.setText('New Batch or Select Working Set to begin.' if not ws else
                           'Paste titles to begin this batch.' if not rows else f'{len(rows)} exact memberships · final publication counts · pinned evidence')
        self.empty.setVisible(not rows)
        self.receipt();self.selected();self.runtime()

    def receipt(self):
        text,receipt=export_receipts.status(self.window.settings,self.window.db,self.window.session.active_uuid,self.mode.currentData())
        self.receipt_label.setText(text+(f" · {receipt['timestamp']} · locally remembered file" if receipt else ''))
        self.export_button.setText('Export Fresh Packet' if 'stale' in text else 'Export Review Packet')

    def export(self): return self.window.export_review_packet(self.batch_context(),self.mode.currentData())

    def selected(self):
        row=self.table.current()
        w=self.window
        if not getattr(self,'_refreshing',False) and hasattr(w,'drawer') and w.stack.currentWidget() is self and w.command.pending and (
                not row or w.command.current!=row['_work_id']):
            w.drawer.cancel()
        if not row:
            self.inspector.display('Select a title to inspect exact pinned evidence',{});self.update_actions();return
        item=row['_item'];iid=item['working_set_item_uuid'];c=self.snapshots.get(iid,{})
        if not row['_work_id']:
            observation=self.window.db.working_sets.latest_observation(iid)
            self.inspector.display(row['query'],{'Intake':{'Edition':row['edition'],'Language':row['language'],
                'Set state':row['item_status'],'Next action':row['next_action'],'Duplicate of':item.get('duplicate_of_item_uuid')}},raw=observation)
        else:
            self.inspector.display(c['title'],{'Selected title':{'Edition / language':c['edition']+' / '+c['language'],
                'Pinned audit':f"{c.get('audit_id')} · revision {c.get('audit_revision')}"},'Health':c['health'],
                'Problems':{'Categories':len(c['problems']),'Next actions':', '.join(sorted({p['next_action'] for p in c['problems']})),
                    'Acceptance':'Eligible' if self.evaluations[iid].get('eligible') else
                        '\n'.join(self.evaluations[iid].get('blockers',[])) or 'Not eligible'},
                **({'Supplementary identities':c['supplementary_identity']['summary']} if
                    ((c.get('supplementary_identity') or {}).get('summary') or {}).get('recognized') else {}),
                **({'Current supplementary review':{r['assertion_uuid']:r['effective_state'] for r in
                    c['supplementary_current_review']['reviewed_state']['decisions']}} if
                    ((c.get('supplementary_current_review') or {}).get('reviewed_state') or {}).get('decisions') else {})},raw=c)
        body=self.inspector.widget()
        body.layout().setContentsMargins(8,6,8,6);body.layout().setSpacing(4)
        for group in body.findChildren(QGroupBox):
            group.layout().setContentsMargins(8,4,8,4);group.layout().setVerticalSpacing(2)
        self.update_actions()

    def commands(self):
        selection=self.selected_context();rows=resolve(self.window.session,selection)
        if len(rows)!=1 or not rows[0]['_work_id']:raise ValueError('Choose one linked exact title for commands.')
        item=rows[0]['_item'];self.window.db.working_sets.editable_item(item['working_set_item_uuid'])
        self.window.open_curate(rows[0]['_work_id'],selection.scope)
        self.window.navigate('Workflow');self.window.drawer.set_expanded(True)

    def open_tool(self,name):
        selection=self.selected_context();rows=resolve(self.window.session,selection)
        if len(rows)!=1:raise ValueError('Select one exact title.')
        row=rows[0];wid=row['_work_id'];item=row['_item']
        if name=='Problems':
            self.window.problems.focus_item_uuid=item['working_set_item_uuid']
            self.window.problems.focus_context=(self.window.db.database_uuid,selection.set_uuid)
            self.window.problems.set_scope('active');self.window.problems.search.clear()
            for box in self.window.problems.filters.values():box.setCurrentIndex(0)
            self.window.problems.refresh();self.window.navigate('Problems')
        elif not wid:raise ValueError('Unlinked intake has no catalog publication yet.')
        elif name=='Details':self.window.open_details(wid,'active',item)
        else:self.window.open_curate(wid,'active')

    def runtime(self):
        w=self.window
        if not hasattr(w,'audit'):return
        self.runtime_label.setText(w.audit.stage.text() if w.busy else
            'Re-Audit queued after current run' if w.deferred or w.deferred_run_ids else
            w.page_feedback.get('Workflow','Idle · Apply starts or queues its required re-audit automatically.'))
        self.runtime_label.setVisible(w.busy or bool(w.deferred or w.deferred_run_ids or w.page_feedback.get('Workflow')))
        states={i['working_set_item_uuid']:i for i in w.session.items('active')}
        counts=summary(list(states.values()),{})['counts']
        self.states.setText(' · '.join(f'{state} {counts.get(state,0)}' for state in (
            'PENDING','QUEUED','AUDITING','READY','ACCEPTED','REJECTED','DUPLICATE'))+f' · Unlinked {sum(not i["work_id"] for i in states.values())}')
        changed=False
        for row in self.table.records.records:
            item=states.get(row['working_set_item_uuid'],row['_item'])
            action=next_action(item,(w.db.working_sets.get(w.session.active_uuid) or {}).get('status'),
                self.evaluations.get(item['working_set_item_uuid']),row.get('_problems',()),
                running=w.busy and item['working_set_item_uuid']==w.current_key)
            if row['next_action']!=action or row['item_status']!=item['processing_status']:
                row['next_action']=action;row['item_status']=item['processing_status'];changed=True
        if changed:
            self.table.records.dataChanged.emit(self.table.records.index(0,0),self.table.records.index(len(self.table.records.records)-1,len(COLUMNS)-1))
        self.update_actions()

    def update_actions(self):
        w=self.window;ws=w.db.working_sets.get(w.session.active_uuid);editable=bool(ws and ws['status'] in ('OPEN','REVIEW'))
        idle=not w.busy;rows=self.table.selected();one=rows[0] if len(rows)==1 else None
        self.new_button.setEnabled(idle);self.select_button.setEnabled(idle)
        self.intake_button.setEnabled(idle and bool(ws and ws['status']=='OPEN'))
        self.run_button.setEnabled(idle and editable);self.run_button.setText('Auditing…' if w.busy else 'Run Working Set')
        self.export_button.setEnabled(bool(ws) and idle)
        self.accept_button.setText(f'Accept Eligible Titles ({getattr(self,"summary",{}).get("eligible",0)})')
        self.accept_button.setEnabled(idle and editable and bool(getattr(self,'summary',{}).get('eligible')))
        terminal=all(r['_item']['processing_status'] in ('ACCEPTED','REJECTED','DUPLICATE') for r in self.table.records.records)
        self.complete_button.setEnabled(idle and editable and bool(self.table.records.records) and terminal)
        self.commands_button.setEnabled(idle and editable and bool(one and one['_work_id'] and one['item_status'] not in ('ACCEPTED','REJECTED','DUPLICATE','AUDITING','QUEUED','ERROR','PENDING')))
        for name in ('Curate','Details'):self.actions[name].setEnabled(bool(one and one['_work_id']))
        self.actions['Curate'].setEnabled(idle and self.commands_button.isEnabled())
        self.actions['Problems'].setEnabled(bool(one))
        self.actions['Retry Errors'].setEnabled(idle and editable and any(r['item_status']=='ERROR' for r in self.table.records.records))
        self.actions['Reopen Selected'].setEnabled(idle and editable and bool(rows) and all(r['item_status'] in ('ACCEPTED','REJECTED') for r in rows))
        try:w.force_selected_item(self.selected_context());force=True
        except ValueError:force=False
        self.actions['Force Re-Audit'].setEnabled(force)
        try:plan=w.force_all_plan();can_force_all=bool(plan['items'])
        except ValueError:can_force_all=False
        self.force_all_action.setEnabled(can_force_all)
        self.cancel_all_action.setEnabled(w.busy and bool(w.worker) and not w.worker.cancel_requested.is_set())
        self.results_action.setEnabled(bool(w.last_force_all))

    def adapt(self):
        compact=hasattr(self.window,'drawer') and not self.window.drawer.body.isHidden()
        self.layout.setSpacing(4 if compact else 6)
        narrow=self.width()<1120
        self.cards.parentWidget().setVisible(not compact)
        self.header.setVisible(not compact);self.guide.setVisible(not compact and not narrow);self.states.setVisible(not compact and not narrow)
        self.runtime_label.setVisible(self.window.busy or (not compact and not narrow and bool(
            self.window.deferred or self.window.deferred_run_ids or self.window.page_feedback.get('Workflow'))))
        self.receipt_label.setVisible(not compact)
        self.mode.setVisible(not compact)
        self.action_title.setVisible(not compact and not narrow)
        self.dock_layout.setContentsMargins(6,4,6,4) if compact else self.dock_layout.setContentsMargins(10,10,10,10)
        columns=3 if self.width()<850 else 5
        for index,chip in enumerate(self.summaries.values()):self.cards.addWidget(chip,index//columns,index%columns)
        for index,b in enumerate(self.production_buttons):
            self.production.addWidget(b,0 if narrow else index,index if narrow else 0);b.setMinimumHeight(32 if narrow else 42)
        for index,b in enumerate(self.actions.values()):self.secondary.addWidget(b,0 if narrow else index//2,index if narrow else index%2)
        self.handoff.setVisible(not compact and not narrow and self.height()>=850)
        if getattr(self,'narrow',None)!=narrow:
            self.narrow=narrow;self.right.setVisible(not narrow)
            if narrow:self.left_layout.insertWidget(3,self.dock)
            else:self.right_layout.addWidget(self.dock)
            self.splitter.setSizes([max(700,self.width()-370),360])

    def toggle_inspector(self):
        if self.narrow:
            visible=self.right.isHidden()
            self.right.setVisible(visible);self.inspector.setVisible(visible)
            if visible:self.splitter.setSizes([max(300,self.width()-330),320])
        else:self.inspector.setVisible(self.inspector.isHidden())

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'production_buttons'):self.adapt()
