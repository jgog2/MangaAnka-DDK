from qt_app.pages.base import Page
from qt_app.widgets.common import RecordTable


class HistoryPage(Page):
    def __init__(self,window):
        super().__init__(window,'History')
        self.category=self.add_filter('Event type',['All','Audit','Curation','Acceptance','Working Set','Maintenance'],lambda _:self.filter_rows(),caption=True)
        self.add_action('Copy Event',self.copy)
        self.add_action('Preview Revert',self.revert)
        self.table=RecordTable([('time','UTC Time',200,False),('title','Title / Context',220,False),('category','Type',100,False),('event','Event',420,False)])
        self.set_content(self.table);self.search.textChanged.connect(self.filter_rows)
        self.table.selectionModel().selectionChanged.connect(self.selected)
        self.table.sortByColumn(0,__import__('PySide6.QtCore',fromlist=['Qt']).Qt.DescendingOrder)

    def refresh(self):
        self.update_scopes();rows=self.window.session.history(self.scope);self.table.records.replace(rows)
        self.filter_rows();self.empty.setText('No events in this scope.' if not rows else f'{len(rows)} events · UTC · journals and audits preserved')

    def filter_rows(self):self.table.proxy.update(self.search.text(),{'category':self.category.currentText()})

    def selected(self):
        r=self.table.current()
        if not r:self.inspector.display('Select a history event',{});return
        d=r['_data'];details={k:v for k,v in d.items() if not k.endswith('_json') and k not in ('publication_json','health_json')}
        groups={'Event':{'Time':r['time'],'Type':r['category'],'Action':r['event']},'Context':details}
        if d.get('changes_json'):
            import json
            changes=json.loads(d['changes_json'])
            groups['Before / after']={f"{v['entity']} {v['key']} · {v['field']}":f"{v['before']['value'] if v.get('before') else '(automatic)'} → {v['after']['value'] if v.get('after') else '(reset)'}" for v in changes}
        self.inspector.display(r['title'],groups,raw=d)

    def copy(self):
        r=self.table.current()
        if r:self.window.copy_text(__import__('json').dumps(r['_data'],ensure_ascii=False,indent=2))

    def revert(self):
        r=self.table.current()
        if not r or r['category']!='Curation':raise ValueError('Only curated changes can be reverted; audit and workflow history is read-only.')
        self.window.open_curate(r['_data']['work_id'],self.scope)
        self.window.command.preview_reverse(change_id=r['_data']['change_id']);self.window.drawer.set_expanded(True)
        self.window.drawer.output.show_data(self.window.command.preview_text());self.window.drawer.apply_button.setEnabled(True)
