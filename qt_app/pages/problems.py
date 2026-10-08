import json
from PySide6.QtWidgets import QHBoxLayout
from ddk_review import CLASSES,persisted_problem_policy, review_packet, packet_markdown, detailed_csv
from qt_app.workflow_presentation import intake_problems
from qt_app.pages.base import Page
from qt_app.widgets.common import RecordTable, StatusChip, menu_button, pretty


class ProblemsPage(Page):
    def __init__(self, window):
        super().__init__(window, 'Problems');self.focus_item_uuid=None;self.focus_context=None
        summary=QHBoxLayout();self.summaries={}
        for kind in ('RESEARCH','DATA','CODE','UNKNOWN','ERROR'):
            chip=StatusChip(kind+'  0');self.summaries[kind]=chip;summary.addWidget(chip)
        summary.addStretch();self.layout.insertLayout(1,summary)
        for text, cb in [('Record Disposition', lambda:window.disposition(False)), ('Reopen Problem',lambda:window.disposition(True)),
                         ('Open in Curate',self.open_curate), ('Copy Diagnostic',self.copy), ('Export',self.export)]: self.add_action(text,cb)
        more=menu_button('More',[
            ('Show All Titles in Scope',self.clear_title_focus),
            ('Export Detailed CSV',lambda:window.safe(self.export_csv)),
            ('Code Review Candidates',lambda:window.show_text('Code Review Candidates',pretty(window.db.code_review_candidates()))),
            ('View Diagnostic',lambda:window.show_text('Review Diagnostic',packet_markdown(self.packet())))])
        self.toolbar.insertWidget(self.toolbar.count()-2,more)
        self.filters = {}
        for key,choices in [('class',['All',*CLASSES,'ERROR']),
                            ('action',['All']),('disposition',['All','OPEN','IGNORED'])]:
            self.filters[key] = self.add_filter(key,choices,lambda _:self.filter_rows(),caption=True)
        self.table = RecordTable([('title','Title',200,False),('code','Problem',250,False),('class','Class',110,True),
                                 ('action','Next Action',190,False),('affected','Affected',70,False),('disposition','Disposition',100,True)])
        self.set_content(self.table); self.search.textChanged.connect(self.filter_rows)
        self.table.selectionModel().selectionChanged.connect(self.selected)
        self.table.doubleClicked.connect(lambda _:window.safe(self.open_curate))

    def clear_title_focus(self):
        self.focus_item_uuid=None;self.focus_context=None;self.refresh()

    def filter_rows(self): self.table.proxy.update(self.search.text(),{k:b.currentText() for k,b in self.filters.items()})

    def refresh(self):
        self.update_scopes(); db=self.window.db; pins=self.window.session.audit_map(self.scope)
        allowed={w['id'] for w in self.window.session.works(self.scope)}; rows=[]
        for h in db.holes(include_ignored=True,audit_ids=list(pins.values()) if pins is not None else None):
            if h['work_id'] not in allowed: continue
            h=dict(h); d=json.loads(h['details_json'] or '{}'); cls,action,_,_=persisted_problem_policy(h,d)
            disposition=db.problem_disposition(h['id'])
            rows.append(dict(title=db.work(h['work_id'])['input_title'],code=h['code'],class_=cls,
                             action=action,affected=h.get('affected_count') or len(d.get('chapters') or d.get('records') or []),
                             disposition='IGNORED' if disposition and disposition['status']=='IGNORED_WITH_REASON' else 'OPEN',_hole=h,_details=d,**{'class':cls}))
        # Unlinked intake failures have observations rather than invented audits.
        observed=[]
        for failure in db.working_sets.audit_errors(self.window.session.set_uuid(self.scope)) if self.scope!='accepted' and (self.scope=='all' or self.window.session.set_uuid(self.scope)) else []:
            item=failure['item'];obs=failure['observation'];h=failure['hole']
            observed.append(dict(title=item['original_query'],code=h['code'],action='RETRY_REQUIRED',affected=1,disposition='OPEN',_hole=None,_item=item,_details=h,_observation=obs,**{'class':'ERROR'}))
        for item in self.window.session.items(self.scope):
            if item['work_id'] or item['processing_status']!='REVIEW':continue
            obs=db.working_sets.latest_observation(item['working_set_item_uuid'])
            if not obs:continue
            for h in intake_problems(obs):
                rows.append(dict(title=item['original_query'],code=h['code'],action=h['next_action'],affected=1,
                                 disposition='OPEN',_hole=None,_item=item,_details=h,_observation=obs,**{'class':h['class']}))
        rows+=observed
        focus=self.window.db.working_sets.item(self.focus_item_uuid) if self.focus_item_uuid else None
        key=(db.database_uuid,self.window.session.set_uuid(self.scope))
        if self.focus_context!=key:self.focus_item_uuid=None;focus=None
        if focus:
            rows=[r for r in rows if (r.get('_hole') or {}).get('work_id')==focus['work_id'] and focus['work_id'] is not None
                  or (r.get('_item') or {}).get('working_set_item_uuid')==self.focus_item_uuid]
        for kind,chip in self.summaries.items():chip.setText(f'{kind}  {sum(r["class"]==kind and r["disposition"]=="OPEN" for r in rows)}')
        self.table.records.replace(rows)
        box=self.filters['action']; old=box.currentText();box.blockSignals(True);box.clear();box.addItems(['All']+sorted({r['action'] for r in rows}));box.setCurrentText(old if box.findText(old)>=0 else 'All');box.blockSignals(False)
        self.filter_rows(); self.empty.setText(('Exact selected item · ' if focus else '')+('No unresolved problems in this scope.' if not rows else f'{len(rows)} problem categories · exact affected records in inspector'))
        self.window.sidebar_buttons['Problems'].setText(f'Problems  {sum(r["disposition"]=="OPEN" for r in rows)}')

    def selected(self):
        r=self.table.current()
        if not r:self.inspector.display('Select a problem',{});return
        h=r['_hole']; d=r['_details']; context={}
        if h: context,_=self.window.session.context(h['work_id'],self.scope)
        self.inspector.display(r['title'],{'Problem':{'Code':r['code'],'Class':r['class'],'Why':h['message'] if h else d.get('message'),
            'Affected records':d.get('chapters') or d.get('records') or r['affected'],'Next action':r['action'],'Disposition':r['disposition']},
            'Publication':{k:context.get(k) for k in ('canonical_main_chapters','acquired_specials','logical_publication_units','mapped_main_chapters','mapped','unmapped','volumes')},
            'Evidence':{'References':context.get('reference_states'),'Conflicts':context.get('conflicts'),
                'Supplementary identities':(context.get('supplementary_identity') or {}).get('summary'),
                'Current supplementary review':{r['assertion_uuid']:r['effective_state'] for r in
                    ((context.get('supplementary_current_review') or {}).get('reviewed_state') or {}).get('decisions',[])}}},
            [('View Evidence',lambda:self.window.safe(lambda:self.window.open_details(h['work_id'],self.scope))) ] if h else (),raw=dict(problem=d,hole=h,context=context))

    def open_curate(self):
        r=self.table.current()
        if not r or not r['_hole']:raise ValueError('Select a linked problem; unresolved intake has no publication yet.')
        h=r['_hole']; d=r['_details']; context,_=self.window.session.context(h['work_id'],self.scope)
        keys=d.get('chapters') or context['canonical_unmapped_identifiers'] or context['conflicts'] or context['unclassified_acquisition_identifiers']
        self.window.open_curate(h['work_id'],self.scope,keys)

    def packet(self):
        pins=self.window.session.audit_map(self.scope)
        selected=[r['_hole']['id'] for r in self.table.selected() if r['_hole']]
        return review_packet(self.window.db,problem_ids=selected or None,
            work_ids=[w['id'] for w in self.window.session.works(self.scope)],include_ignored=True,audit_by_work=pins)

    def diagnostic(self):
        text=packet_markdown(self.packet())
        for r in self.table.selected() or self.table.records.records:
            if r.get('_observation'):text+='\n\n## Latest intake failure · '+r['title']+'\n\n```json\n'+pretty(r['_observation'])+'\n```\n'
        return text
    def copy(self):self.window.copy_text(self.diagnostic())
    def export(self): self.window.save_text('Review packet',self.diagnostic(),'md')

    def export_csv(self):
        from PySide6.QtWidgets import QFileDialog
        path,_=QFileDialog.getSaveFileName(self,'Detailed Problems CSV',str(self.window.db.path.parent/'problems.csv'),'CSV (*.csv)')
        if path:detailed_csv(self.packet(),path);self.window.feedback('Exported '+path,'Problems')
