import json
from PySide6.QtWidgets import QComboBox, QTabWidget
from qt_app.pages.base import Page
from qt_app.widgets.common import Inspector, RawData, RecordTable
from qt_app.widgets.publication_map import PublicationMap
from ddk_supplementary import publication_supplements, inspector_summary


class DetailsPage(Page):
    sections=('Overview','Identity','Publication','Acquisition','References','Curation','Acceptance','Working Sets','Raw Data')
    def __init__(self,window):
        super().__init__(window,'Details');self.work_id=None;self.item=None
        self.title_box=QComboBox();self.title_box.setMinimumWidth(220);self.filterbar.insertWidget(0,self.title_box)
        self.title_box.currentIndexChanged.connect(self.title_changed)
        self.tabs=QTabWidget();self.panes={}
        self.tabs.tabBar().setUsesScrollButtons(True);self.tabs.tabBar().setExpanding(False)
        for section in self.sections:
            pane=PublicationMap() if section=='Publication' else RawData() if section=='Raw Data' else RecordTable([
                ('provider','Provider',170,False),('usable','Usable',65,True),('chapters','Chapters',80,False),('native_volumes','Native Volumes',105,False),
                ('standalone','Standalone',90,False),('qualification','Qualification',300,False)]) if section=='Acquisition' else Inspector()
            self.panes[section]=pane;self.tabs.addTab(pane,section)
        self.set_content(self.tabs);self.inspector.hide()
        self.panes['Publication'].chapter_selected.connect(self.chapter_selected)
        self.panes['Acquisition'].selectionModel().selectionChanged.connect(self.provider_selected)
        self.search.setPlaceholderText('Search raw data (Enter)');self.search.returnPressed.connect(self.search_raw)
        self.add_action('Copy JSON',lambda:window.copy_text(self.panes['Raw Data'].toPlainText()))
        self.add_action('Open in Curate',lambda:window.open_curate(self.work_id,self.scope))

    def title_changed(self):
        value=self.title_box.currentData()
        if value:self.open(value['wid'],value.get('item'))

    def refresh(self):
        self.update_scopes();self.title_box.blockSignals(True);self.title_box.clear()
        for row in self.window.session.catalog_rows(self.scope):
            if row['_work_id']:self.title_box.addItem(row['query']+' · '+row['edition'],{'wid':row['_work_id'],'item':row['_item']})
        idx=next((i for i in range(self.title_box.count()) if self.title_box.itemData(i)['wid']==self.work_id and
            (not self.item or (self.title_box.itemData(i).get('item') or {}).get('working_set_item_uuid')==self.item.get('working_set_item_uuid'))),0)
        self.title_box.setCurrentIndex(idx);self.title_box.blockSignals(False)
        value=self.title_box.currentData()
        if value:self.open(value['wid'],value.get('item'))
        else:
            self.work_id=None;self.item=None;self.empty.setText('No linked publication in this scope. Choose another scope or run intake.')
            for section,pane in self.panes.items():
                if isinstance(pane,Inspector):pane.display('No selected title',{})
                elif isinstance(pane,RawData):pane.clear()
                elif isinstance(pane,PublicationMap):pane.replace([])
                else:pane.records.replace([])

    def open(self,wid,item=None):
        self.work_id=wid;self.item=item;db=self.window.db;c,item=self.window.session.context(wid,self.scope,item);self.item=item
        audit=db.audit(c['audit_id'],wid) if c['audit_id'] else None
        pub=json.loads(audit['publication_json'] or '{}') if audit else {};work=dict(db.work(wid))
        self.empty.setText(f"{c['title']} · Pinned / snapshot {c['audit_id'] or 'none'} · Latest global {c['latest_global_audit_id'] or 'none'} · {c['pin_state']}")
        self.panes['Overview'].display(c['title'],{'Health':c['health'],'Publication':{k:c[k] for k in ('canonical_main_chapters','acquired_specials','logical_publication_units','mapped_main_chapters','mapped','uncompiled','unmapped','volumes')},
            'Serialization / specials':{'Uncompiled identifiers':', '.join(c['uncompiled_identifiers']),
                'Recognized specials':'\n'.join(f"{r['key']} · {r['kind']} · {r['source_page']}" for r in c['recognized_specials']),
                'Missing special acquisition':', '.join(c['missing_special_acquisition'])},
            'Acquisition':{k:c[k] for k in ('selected_provider','provider_artifacts','unclassified')},'Approval':{'Catalog':c['catalog_status'],'State':c['acceptance_state'],'Pin':c['pin_state']}})
        self.panes['Identity'].display('Canonical identity',{'Identity':pub.get('catalog_identity') or {},'Search':{k:work.get(k) for k in ('input_title','canonical_title','edition','language','canonical_work_id','anilist_id','mal_id','mangadex_id')},
            'Aliases / enrichment':{'Aliases':c['aliases'],'External IDs':c['external_ids']}},raw=dict(work=work,audit=dict(audit) if audit else None))
        rows=db.catalog.rows(wid,audit=audit) if audit else []
        self.panes['Publication'].replace(rows,(pub.get('manifest') or {}).get('volumes') or [],c['supplementary_identity'])
        record=json.loads(audit['record_json'] or '{}') if audit and 'record_json' in audit.keys() else {}
        inventories=record.get('inventories') or []
        # Retain every original field in the provider inspector / raw data.
        providers=[]
        for inv in inventories:
            providers.append(dict(provider=inv.get('source_name') or inv.get('provider') or inv.get('source_id'),usable=inv.get('usable'),
                chapters=inv.get('chapters') or inv.get('chapter_count'),native_volumes=inv.get('volumes') or inv.get('volume_count',0),
                standalone=inv.get('standalone_chapters'),qualification=inv.get('qualification') or inv.get('reason'),_inventory=inv))
        if not providers and audit:
            for field in ('inventories_json','provider_inventory_json'):
                if field in audit.keys():
                    for inv in json.loads(audit[field] or '[]'):
                        providers.append(dict(provider=inv.get('source_name') or inv.get('source_id'),_inventory=inv,
                            usable=inv.get('usable'),chapters=inv.get('chapter_count'),native_volumes=inv.get('native_volumes'),
                            standalone=inv.get('standalone_chapters'),qualification=inv.get('error') or inv.get('summary')))
        self.panes['Acquisition'].records.replace(providers)
        self.panes['References'].display('Structure / references',{'States':c['reference_states'],
            'Coverage':c['structural_coverage'],'Catalog freshness':c['catalog_freshness'],
            'Release boundary':c['release_boundary'], 'Supplementary identities':c['supplementary_identity'].get('summary',{})},raw={'references':pub.get('references'),
            'supplementary_identity':c['supplementary_identity'],
            'supplementary_current_review':c['supplementary_current_review'],
            'manifest':pub.get('manifest'),'provenance':c['reported_totals'],
            'uncompiled_evidence':c['uncompiled_evidence'],'source_fingerprints':c['source_fingerprints']})
        self.panes['Curation'].display('Snapshot curation',{'Snapshot':{'Revision':c['curation_revision'],'Fields':c['curated_fields'],'Verification':c['curated_verifications']},
            'Evidence':{str(i+1):str(v) for i,v in enumerate(c['curated_evidence'])}},raw=pub.get('curated_database') if item else db.catalog.state(wid))
        evaluation=db.acceptance.evaluate(wid,item['working_set_item_uuid'] if item and item['processing_status']!='DUPLICATE' else None)
        self.panes['Acceptance'].display('Acceptance',{'State':{'Catalog':c['catalog_status'],'Approval':c['acceptance_state'],'Eligible':evaluation['eligible'],'Blockers':'\n'.join(evaluation['blockers']),'Warnings':'\n'.join(evaluation['warnings'])}},raw=evaluation)
        with db.con() as con:members=[dict(r) for r in con.execute('SELECT * FROM working_set_items WHERE linked_work_uuid=?',(work['work_uuid'],))]
        self.panes['Working Sets'].display('Memberships',{'Context':{'Snapshot set':c['working_set_uuid'],'Item':c['working_set_item_uuid'],'Duplicate of':c['duplicate_of_item_uuid']},
            'Memberships':{m['working_set_item_uuid']:f"{m['working_set_uuid']} · {m['processing_status']} · pin {m['pinned_audit_id']}" for m in members}},raw=members)
        raw=dict(work=work,audit=dict(audit) if audit else None,publication=pub,context=c,memberships=members)
        raw['latest_intake_observations']=[dict(item_uuid=m['working_set_item_uuid'],observation=db.working_sets.latest_observation(m['working_set_item_uuid'])) for m in members]
        self.panes['Raw Data'].show_data(raw)

    def chapter_selected(self,row):
        if row.get('supplementary'):
            self.inspector.show();self.inspector.display(row['effective']['title'],
                {'Independent states':{k:row['evidence'][k] for k in ('acquisition_state','membership_state','applicability')},
                 'Supplementary authority':row['evidence']['identity']},
                actions=[('Open Supplementary Review',lambda:self.review_supplement(row['key']))],raw=row['evidence'])
            return
        self.inspector.show();self.inspector.display(row['key']+' · '+(row['effective'].get('title') or 'Untitled'),
            {'Automatic':row['automatic'],'Curated':{k:f"{v['value']} · {v['verification']}" for k,v in row['curated'].items()},'Effective':row['effective'],'Provenance':{'Source':row['source'],'State':row['status']}},raw=row)

    def provider_selected(self):
        r=self.panes['Acquisition'].current()
        if r:
            groups=((self.window.session.context(self.work_id,self.scope,self.item)[0].get('provider_group_acquisition') or {})
                    if (r.get('_inventory') or {}).get('source_id')=='atsu' else {})
            alternatives=groups.get('alternatives') or []
            self.inspector.show();self.inspector.display(r.get('provider') or 'Provider inventory',{
                'Inventory':{k:v for k,v in r.get('_inventory',{}).items() if not isinstance(v,(dict,list))},
                'Scanlation groups':{'Primary group':groups.get('primary_group'),
                    'Selection basis':groups.get('recommendation_basis'),'Raw records':groups.get('raw_count'),
                    'Retained alternatives':len(alternatives),
                    'Recovered fallback records':sum(bool(a.get('recovered')) for a in alternatives),
                    'Alternates requiring review':sum(bool(a.get('requires_review')) for a in alternatives)}},
                raw={'inventory':r.get('_inventory'),'groups':groups})

    def review_supplement(self,opaque_id):
        self.window.open_curate(self.work_id,self.scope)
        self.window.curate.review_supplement(opaque_id)

    def search_raw(self):
        self.tabs.setCurrentWidget(self.panes['Raw Data'])
        if not self.panes['Raw Data'].find(self.search.text()):
            self.panes['Raw Data'].moveCursor(__import__('PySide6.QtGui',fromlist=['QTextCursor']).QTextCursor.Start)
            self.panes['Raw Data'].find(self.search.text())
