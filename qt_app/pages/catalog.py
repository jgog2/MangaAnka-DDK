from PySide6.QtWidgets import QHBoxLayout, QPushButton, QMenu
from qt_app.pages.base import Page
from qt_app.widgets.common import RecordTable, StatusChip

DEFAULT = [('query','Title',185,False), ('item_status','Item',82,True), ('catalog_status','Catalog',85,True),
           ('publication_health','Publication',88,True), ('chapter_display','Chapters',195,False),
           ('volumes','Volumes',75,False), ('acceptance_state','Acceptance',90,True), ('selected_provider','Provider',105,False)]
ADVANCED = [('canonical_identity','Canonical Identity'), ('identity_health','Identity Health'),
            ('normalization_health','Normalization Health'), ('acquisition_health','Acquisition Health'),
            ('provider_artifacts','Provider Artifacts'), ('unclassified','Unclassified'), ('curated_fields','Curated Fields'),
            ('curation_revision','Curation Revision'), ('audit_id','Snapshot Audit'), ('audit_created_at','Snapshot Audit Date'), ('audit_revision','Audit Revision'),
            ('audit_freshness','Audit Freshness'), ('pinned_audit_id','Pinned Audit'), ('latest_global_audit_id','Latest Global Audit'),
            ('pin_state','Pin State'), ('work_uuid','Work UUID'), ('working_set_item_uuid','Working Set Item UUID')]


class CatalogPage(Page):
    def __init__(self, window):
        super().__init__(window, 'Catalog')
        self.run_button = self.add_action('Run Working Set', window.run_working_set, True)
        self.accept_all_button = self.add_action('Accept All Safe', window.accept_all_safe)
        self.add_action('Accept Selected', window.accept_selected)
        self.add_action('Intake', window.intake)
        self.add_action('Open Review Items', window.open_review)
        self.add_action('Retry Errors', window.retry_errors)
        more = QPushButton('More'); self.more_menu = QMenu(more); more.setMenu(self.more_menu)
        self.force_audit_action=self.more_menu.addAction('Force Re-Audit Selected',lambda:window.safe(window.force_reaudit_selected))
        self.force_audit_action.setEnabled(False)
        self.more_menu.aboutToShow.connect(self.update_force_action)
        entries = [('Reopen Selected for Review', window.reopen_items), ('Reject Selected Intake', window.reject_items),
                   ('Remove Selected Intake', window.remove_items), ('Copy Selected Summary', lambda: window.copy_selected('summary')),
                   ('Copy Selected CSV Rows',lambda:window.copy_selected('csv')),('Copy Selected Full Diagnostic',lambda:window.copy_selected('full')),
                   ('Copy Selected Title', lambda: window.copy_selected('title')), ('Copy Selected Work UUID', lambda: window.copy_selected('uuid')),
                   ('Copy Selected Review Context', lambda: window.copy_selected('context')), ('Copy Working Set Titles', lambda: window.export_set('titles', True)),
                   ('Copy Working Set Context', lambda: window.export_set('context', True)), ('Copy Working Set CSV', lambda: window.export_set('csv', True)),
                   ('Export Working Set (Pinned)', lambda: window.export_set('context')), ('Export Working Set (Current)', lambda: window.export_set('context', mode='current')),
                   ('Export Working Set CSV (Pinned)', lambda: window.export_set('csv')), ('Export Working Set CSV (Current)', lambda: window.export_set('csv', mode='current')),
                   ('Export Working Set Titles', lambda: window.export_set('titles')), ('Export Working Set Review Packet', lambda: window.export_set('packet')),
                   ('Export CSV', window.export_catalog), ('Refresh', window.refresh_all),
                   ('Re-evaluate Acceptance', window.reevaluate), ('Catalog Maintenance · Permanently Delete', window.delete_work)]
        for text, callback in entries: self.more_menu.addAction(text, lambda checked=False,cb=callback: window.safe(cb))
        self.toolbar.insertWidget(self.toolbar.count()-2, more)
        self.summaries = {}
        summary = QHBoxLayout()
        for state in ('ACCEPTED', 'READY', 'REVIEW', 'ERROR', 'DUPLICATE'):
            chip = StatusChip(state+'  0'); self.summaries[state] = chip; summary.addWidget(chip)
        summary.addStretch(); self.layout.insertLayout(1, summary)
        self.table = RecordTable(DEFAULT+[(k,l,170,'health' in k or k in ('pin_state',)) for k,l in ADVANCED])
        self.set_content(self.table)
        self.columns_button = QPushButton('Columns'); self.columns_menu = QMenu(self.columns_button)
        self.columns_button.setMenu(self.columns_menu); self.filterbar.addWidget(self.columns_button)
        self.column_actions = []
        for i, c in enumerate(self.table.records.columns):
            action = self.columns_menu.addAction(c[1]); action.setCheckable(True); action.setChecked(i < len(DEFAULT))
            self.table.setColumnHidden(i, i >= len(DEFAULT))
            action.toggled.connect(lambda enabled, n=i: self.table.setColumnHidden(n, not enabled)); self.column_actions.append(action)
        self.filters = {}
        for key, choices in [('item_status', ['All','PENDING','QUEUED','READY','REVIEW','ERROR','ACCEPTED','REJECTED','DUPLICATE']),
                             ('edition',['All','standard','official_color','fan_color','omnibus','deluxe','bunkobon','kanzenban']),
                             ('language',['All','en','ja']), ('selected_provider',['All'])]:
            self.filters[key] = self.add_filter(key, choices, lambda _: self.filter_rows())
            self.filters[key].setItemText(0,{'item_status':'Status','edition':'Edition','language':'Language','selected_provider':'Provider'}[key])
            self.filters[key].setItemData(0,'All')
        self.search.textChanged.connect(self.filter_rows)
        self.table.selectionModel().selectionChanged.connect(self.selected)
        self.table.doubleClicked.connect(lambda _: window.safe(self.open_details))

    def filter_rows(self):
        values={k:b.currentData() or b.currentText() for k,b in self.filters.items()}
        if self.scope in ('all','accepted'):values['catalog_status']=values.pop('item_status')
        self.table.proxy.update(self.search.text(),values)

    def refresh(self):
        self.update_scopes(); rows = self.window.session.catalog_rows(self.scope)
        status=self.filters['item_status'];old=status.currentText();status.blockSignals(True);status.clear()
        status.addItem('Catalog status' if self.scope in ('all','accepted') else 'Item status','All')
        status.addItems(['STAGED','ACCEPTED'] if self.scope in ('all','accepted') else ['PENDING','QUEUED','READY','REVIEW','ERROR','ACCEPTED','REJECTED','DUPLICATE'])
        if status.findText(old)>=0:status.setCurrentText(old)
        status.blockSignals(False)
        selected = self.table.current(); self.table.records.replace(rows)
        provider = self.filters['selected_provider']; old = provider.currentText()
        provider.blockSignals(True); provider.clear(); provider.addItems(['All']+sorted({r['selected_provider'] for r in rows if r.get('selected_provider')}))
        provider.setCurrentText(old if provider.findText(old) >= 0 else 'All'); provider.blockSignals(False)
        provider.setItemText(0,'Provider');provider.setItemData(0,'All')
        language = self.filters['language']; old = language.currentText(); language.blockSignals(True)
        language.clear(); language.addItems(['All']+sorted({r['language'] for r in rows if r.get('language')})); language.setCurrentText(old); language.blockSignals(False)
        language.setItemText(0,'Language');language.setItemData(0,'All')
        self.filter_rows()
        for state, chip in self.summaries.items(): chip.setText(f'{state}  {sum(r["item_status"] == state for r in rows)}')
        self.empty.setText('Add titles through Intake, or switch scope.' if not rows else f'{len(rows)} rows · {self.scope_box.currentText()} · set evidence stays pinned')
        if selected: self.table.select_record(lambda r: r.get('working_set_item_uuid') == selected.get('working_set_item_uuid') and r.get('_work_id') == selected.get('_work_id'))
        # Qt model resets need not emit selectionChanged. Clear stale context
        # when the previous row no longer exists in the new set/scope.
        self.selected()

    def selected(self):
        self.update_force_action()
        r = self.table.current()
        if not r:self.inspector.display('Select a catalog row',{});return
        if not r['_work_id']:
            observation = self.window.db.working_sets.latest_observation(r['_item']['working_set_item_uuid'])
            self.inspector.display(r['query'], {'Intake':{'Status':r['item_status'], 'Edition':r['edition'], 'Language':r['language'], 'Next action':'Run Working Set or inspect the intake failure'}}, raw=observation)
            return
        c, item = self.window.session.context(r['_work_id'], self.scope, r['_item'])
        groups={
            'Identity':{'Edition':c['edition'],'Language':c['language']}, 'Health':c['health'],
            'Publication':{k:c[k] for k in ('canonical_main_chapters','acquired_specials','logical_publication_units','mapped_main_chapters','mapped','uncompiled','unmapped','volumes')},
            'Acquisition':{k:c[k] for k in ('selected_provider','provider_artifacts','unclassified')},
            'Curation':{k:c[k] for k in ('curated_fields','curation_revision')},
            'Publication freshness':{'Catalog':(c['catalog_freshness'] or {}).get('state','Unknown'),
                'Coverage':(c['catalog_freshness'] or {}).get('coverage_kind','Unknown'),
                'Latest released':(c['release_boundary'] or {}).get('latest_released_volume'),
                'Future volumes':', '.join((c['release_boundary'] or {}).get('future_volumes') or []),
                'Listed without release proof':', '.join((c['release_boundary'] or {}).get('listed_unreleased_volumes') or [])},
            'Audit':{k:c[k] for k in ('audit_id','audit_revision','latest_global_audit_id','pin_state')},
            'Acceptance':{'Membership':r['item_status'],'Catalog':c['catalog_status'],'Approval':c['acceptance_state']}}
        observation=self.window.db.working_sets.latest_observation(item['working_set_item_uuid']) if item and item['processing_status'] in ('ERROR','REVIEW') else None
        if observation:groups['Latest intake attempt']={'Problems':'\n'.join(h['message'] for h in observation['holes']),'When':observation['created_at'],'Snapshot':'Previous pin retained'}
        self.inspector.display(c['title'],groups,
            [('Accept Selected',lambda:self.window.safe(self.window.accept_selected)), ('Re-evaluate',lambda:self.window.safe(self.window.reevaluate)),
             ('Open Details',lambda:self.window.safe(self.open_details)), ('Open in Curate',lambda:self.window.safe(lambda:self.window.open_curate(r['_work_id'],self.scope)))], raw=dict(context=c,latest_attempt=observation),
            publication_rows=self.window.db.catalog.rows(r['_work_id'],audit=self.window.db.audit(c['audit_id'],r['_work_id'])) if c['audit_id'] else [])

    def open_details(self):
        row = self.table.current()
        if not row or not row['_work_id']: raise ValueError('Select a linked catalog work.')
        self.window.open_details(row['_work_id'], self.scope, row['_item'])

    def update_force_action(self):
        try:
            self.window.force_selected_item()
            enabled=True
        except ValueError:
            enabled=False
        self.force_audit_action.setEnabled(enabled)
