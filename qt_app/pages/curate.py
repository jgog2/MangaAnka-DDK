from PySide6.QtWidgets import QComboBox, QStackedWidget, QLabel, QPushButton, QMenu
from qt_app.pages.base import Page
from qt_app.widgets.publication_map import PublicationMap
from qt_app.widgets.common import RecordTable, pretty
from ddk_supplementary import publication_supplements


class CuratePage(Page):
    def __init__(self,window):
        super().__init__(window,'Curate');self.work_id=None;self.rows=[]
        self.title_box=QComboBox();self.title_box.setMinimumWidth(180);self.filterbar.insertWidget(0,self.title_box)
        self.title_box.currentIndexChanged.connect(self.title_changed)
        self.mode=QComboBox();self.mode.addItems(['Publication Map','Table']);self.filterbar.addWidget(self.mode)
        self.add_action('Edit Chapter',lambda:window.edit_chapter())
        self.add_action('Evidence',lambda:window.edit_evidence())
        self.add_action('Verify',lambda:window.verify_chapters())
        more=QPushButton('More');menu=QMenu(more);more.setMenu(menu)
        for text,cb in [('Edit Work Identity',window.edit_identity),('Edit Volume',window.edit_volume),
                        ('Share Reviewed Structure',window.share_structure),('Validate',lambda:window.drawer_command('validate')),
                        ('Save / Validate',lambda:window.drawer_command('save')),('Re-audit',lambda:window.drawer_command('audit')),
                        ('Export Curated Patch',window.export_patch),('Undo',lambda:window.drawer.reverse(False)),('Redo',lambda:window.drawer.reverse(True))]:
            menu.addAction(text,lambda checked=False,action=cb:window.safe(action))
        self.toolbar.insertWidget(self.toolbar.count()-2,more)
        self.notice=QLabel('Edits affect the latest shared catalog. Set evidence elsewhere stays pinned.');self.notice.setWordWrap(True);self.notice.setProperty('secondary',True)
        self.layout.insertWidget(2,self.notice)
        self.content=QStackedWidget();self.map=PublicationMap();self.content.addWidget(self.map)
        self.table=RecordTable([('key','Chapter',90,False),('title','Title',250,False),('auto_volume','Automatic',90,False),
            ('curated_volume','Curated',90,False),('volume','Effective',90,False),('verification','Verification',110,True),('status','State',230,True)])
        self.content.addWidget(self.table);self.mode.currentIndexChanged.connect(self.content.setCurrentIndex);self.set_content(self.content)
        self.map.chapter_selected.connect(self.chapter_selected);self.table.selectionModel().selectionChanged.connect(self.table_selected)
        self.search.textChanged.connect(self.filter_rows)

    def title_changed(self):
        wid=self.title_box.currentData()
        if wid:self.open(wid)

    def refresh(self):
        self.update_scopes();self.title_box.blockSignals(True);self.title_box.clear()
        for w in self.window.session.works(self.scope):self.title_box.addItem(f"{w['input_title']} · {w['edition']} / {w['language']}",w['id'])
        i=self.title_box.findData(self.work_id)
        self.title_box.setCurrentIndex(i if i>=0 else 0);self.title_box.blockSignals(False)
        self.work_id=self.title_box.currentData()
        if self.work_id:self.open(self.work_id,preserve=True)
        else:
            self.rows=[];self.map.replace([]);self.table.records.replace([]);self.window.command.current=None;self.empty.setText('Choose a linked title in this scope to inspect or curate publication.');self.inspector.display('Choose a title',{})

    def open(self,wid,preserve=False):
        selection=self.window.command.selection.copy() if preserve and self.window.command.current==wid else set()
        command=self.window.command;pending=command.pending
        retain=bool(preserve and command.current==wid and command.scope==self.scope and pending and
            pending.get('audit_id')==self.window.db.catalog.snapshot(wid)[1] and
            pending.get('revision')==self.window.db.catalog.state(wid)['revision'])
        if pending and pending.get('supplementary'):
            try:
                retain=bool(preserve and command.current==wid and command.scope==self.scope and
                    pending.get('context')==self.window.db.supplementary.guard(wid,pending.get('working_set_item_uuid')))
            except ValueError:retain=False
        self.work_id=wid;self.window.command.open(wid,self.scope);self.window.command.selection=selection
        if hasattr(self.window,'drawer'):
            work=self.window.db.work(wid)
            context,item=self.window.session.context(wid,self.scope)
            self.window.drawer.set_target(f"{work['input_title']} · {work['edition']} / {work['language']} · "
                f"item {item['working_set_item_uuid'] if item else 'global catalog'} · "
                f"pinned audit {context['audit_id']} revision {context['audit_revision']} · edits use latest shared catalog")
        if retain:self.window.command.pending=pending
        if hasattr(self.window,'drawer'):
            self.window.drawer.apply_button.setEnabled(retain)
            if pending and not retain:self.window.drawer.output.show_data('Preview cancelled: title, scope, audit or curation revision changed. Preview again.')
        self.rows=self.window.db.catalog.rows(wid)
        auto,_=self.window.db.catalog.snapshot(wid)
        state=self.window.db.catalog.state(wid)
        volume_keys=[r['record_key'] for r in state['fields'] if r['entity']=='volume' and r['field']=='exists']
        volumes=list(auto.get('manifest',{}).get('volumes') or [])+volume_keys
        self.map.replace(self.rows,volumes,self.window.db.supplementary.for_audit(wid,current=True))
        self.table.records.replace([dict(key=r['key'],title=r['effective'].get('title') or 'Untitled',
            auto_volume=r['automatic'].get('volume'),curated_volume=r['curated'].get('volume',{}).get('value'),
            volume=r['effective'].get('volume'),verification='/'.join(sorted({f['verification'] for f in r['curated'].values()})),
            status=r['status'],_row=r) for r in self.rows])
        self.title_box.blockSignals(True);self.title_box.setCurrentIndex(self.title_box.findData(wid));self.title_box.blockSignals(False)
        self.empty.setText(f'{len(self.rows)} records · latest shared catalog · exact chapter selection drives the command drawer')
        self.filter_rows();self.select_iids(selection)

    def filter_rows(self):
        self.table.proxy.update(self.search.text())
        text=self.search.text().casefold();model=self.map.publication
        for gi,g in enumerate(model.root.children):
            parent=model.index(gi,0);visible=False
            for ri,node in enumerate(g.children):
                match=not text or text in ' '.join(str(v) for v in node.values).casefold()
                self.map.setRowHidden(ri,parent,not match);visible=visible or match
            self.map.setRowHidden(gi,model.index(-1,0),not visible and bool(text))

    def select_iids(self,iids):
        keys=[r['key'] for r in self.rows if r['iid'] in iids]
        if keys:self.map.focus_keys(keys)

    def chapter_selected(self,row):
        self.window.command.selection={r['iid'] for r in self.map.selected_rows() if not r.get('supplementary')}
        if row.get('supplementary'):
            self.window.command.selection=set()
            self.inspector.display(row['effective']['title'],
                {'Supplementary evidence':{'Acquisition':row['evidence']['acquisition_state'],
                    'Membership':row['evidence']['membership_state'],
                    'Commands':'Grammar 4 supplementary review; numeric Grammar 3 selection stays separate.'},
                 'Supplementary identity':row['evidence']['identity']},
                actions=[('Review Supplementary',lambda:self.review_supplement(row['key']))],raw=row['evidence'])
            return
        state=self.window.db.catalog.state(self.work_id)
        evidence=[r for r in state['evidence'] if r.get('record_key')==row['key']]
        self.inspector.display(f"{row['effective'].get('chapter') or row['key']} · {row['effective'].get('title') or 'Untitled'}",
            {'Automatic':row['automatic'],'Curated':{k:f"{v['value']} · {v['verification']}" for k,v in row['curated'].items()},
             'Effective':row['effective'],'Provenance':{'Source':row['source'],'State':row['status'],'Ambiguous':row['ambiguous'],'Missing acquisition':row['missing']},
             'Evidence':{str(i+1):f"{e['source_name']} · {e['source_url']} · {e['verification']} · {e['note']}" for i,e in enumerate(evidence)}},raw=dict(row=row,evidence=evidence))

    def table_selected(self):
        selected=self.table.selected()
        self.window.command.selection={r['_row']['iid'] for r in selected}
        if selected:
            row=selected[0]['_row'];self.chapter_selected(row)
            self.window.command.selection={r['_row']['iid'] for r in selected}

    def review_supplement(self,opaque_id):
        from qt_app.widgets.supplementary_review import SupplementaryReview
        self.window.safe(lambda:SupplementaryReview(self.window,self.work_id,self.scope,opaque_id).exec())
