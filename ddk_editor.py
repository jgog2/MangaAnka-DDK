"""Tk catalog editor; all writes flow through previewed Catalog transactions."""
import json
import re
import uuid
import tkinter as tk
from tkinter import ttk, messagebox

from ddk_command_controller import CommandLogic
from ddk_catalog import TYPES, VERIFICATIONS, numeric
from ddk_commands import HELP, parse, parse_batch, matches, scoped_rows, title_scope
from ddk_chapter_normalization import publication_classification_counts
from mangaanka_search_core.cross_source_fallback import normalize_chapter_number


class CatalogEditor(CommandLogic):
    def command_selection(self):
        return self.tree.selection()

    def __init__(self, app, frame, history_frame):
        self.app=app;self.store=app.db.catalog;self.current=None;self.pending=None
        self.scope_label=tk.StringVar(value='Curation edits shared catalog data; audit pins belong to Working Set items.')
        ttk.Label(frame,textvariable=self.scope_label,wraplength=1000).pack(fill='x',pady=4)
        self.command_history=[];self.history_index=0;self.rows=[]
        split=ttk.Panedwindow(frame,orient='horizontal');split.pack(fill='both',expand=True)
        left=ttk.Frame(split);right=ttk.Frame(split);split.add(left,weight=1);split.add(right,weight=5)
        ttk.Label(left,text='Catalog titles').pack(anchor='w')
        f,self.titles=app.tree_widget(left,('title',),('Title',),(240,))
        f.pack(fill='both',expand=True)
        self.titles.bind('<<TreeviewSelect>>',self.title_selected)
        self.health=tk.StringVar();ttk.Label(left,textvariable=self.health,wraplength=220).pack(fill='x',pady=6)
        actions=ttk.Frame(right);actions.pack(fill='x')
        for label,command in [('Title / Identity',self.edit_identity),('Re-audit',self.reaudit)]:
            ttk.Button(actions,text=label,command=lambda fn=command:self.safe(fn)).pack(side='left',padx=2)
        more=ttk.Menubutton(actions,text='More ▾');more.pack(side='left',padx=3)
        more_menu=tk.Menu(more,tearoff=False)
        more_menu.add_command(label='Validate',command=lambda:self.safe(self.validate))
        more_menu.add_command(label='Export Patch',command=lambda:self.safe(self.export))
        more_menu.add_command(label='Selected Evidence...',command=lambda:self.safe(self.edit_evidence))
        more_menu.add_command(label='Share Structure from Edition...',
                              command=lambda:self.safe(self.share_structure))
        more.configure(menu=more_menu)
        controls=ttk.Frame(right);controls.pack(fill='x',pady=4)
        self.filter=tk.StringVar(value='All')
        combo=ttk.Combobox(controls,textvariable=self.filter,state='readonly',width=18,
                         values=('All','Unmapped','Missing','Conflicts','Modified','Curated','Automatic only','Volume N'))
        combo.pack(side='left');combo.bind('<<ComboboxSelected>>',lambda e:self.refresh_rows())
        self.volume_filter=tk.StringVar();ttk.Entry(controls,textvariable=self.volume_filter,width=7).pack(side='left')
        ttk.Button(controls,text='Filter',command=self.refresh_rows).pack(side='left')
        self.selected_label=tk.StringVar(value='Selected: 0 rows')
        ttk.Label(controls,textvariable=self.selected_label).pack(side='left',padx=8)
        self.views=ttk.Notebook(right);self.views.pack(fill='both',expand=True)
        chapters=ttk.Frame(self.views);volumes=ttk.Frame(self.views)
        self.views.add(chapters,text='Chapters');self.views.add(volumes,text='Volumes')
        cols=('chapter','title','volume','type','auto','curated','effective','source','status','source_note','verification')
        f,self.tree=app.tree_widget(chapters,cols,('Chapter','Title','Volume','Type','Automatic Volume','Curated Volume','Effective Volume','Source','Status','Source Note','Verification'),
                                    (95,240,85,85,125,125,125,150,300,260,125),'extended')
        self.tree.tag_configure('pending',background='#274C5A',foreground='#FFFFFF')
        f.pack(fill='both',expand=True)
        self.tree.bind('<<TreeviewSelect>>',self.selection_changed)
        self.tree.bind('<Control-a>',self.select_all);self.tree.bind('<Control-A>',self.select_all)
        self.tree.bind('<Double-1>',lambda e:self.safe(self.edit_row))
        f,self.volumes=app.tree_widget(volumes,('volume','title','chapters','ids','source','status'),
                                     ('Volume','Title','Chapter identities','IDs','Provenance','Status'),(90,220,400,180,180,150))
        f.pack(fill='both',expand=True)
        vb=ttk.Frame(volumes);vb.pack(fill='x')
        ttk.Button(vb,text='Edit volume metadata',command=lambda:self.safe(self.edit_volume)).pack(side='left')
        ttk.Label(vb,text='Assign membership by selecting chapter rows or using an exact chapter range command.').pack(side='left',padx=8)
        bulk=ttk.LabelFrame(right,text='Bulk edit — only entered fields change',padding=4);bulk.pack(fill='x',pady=4)
        self.bulk={}
        for index,(field,label) in enumerate((('volume','Volume'),('type','Type'),('title','Title'),('source_note','Source note'))):
            ttk.Label(bulk,text=label).grid(row=0,column=index*2,sticky='w')
            var=tk.StringVar();self.bulk[field]=var
            if field=='type': widget=ttk.Combobox(bulk,textvariable=var,values=('',*TYPES),state='readonly',width=10)
            else: widget=ttk.Entry(bulk,textvariable=var,width=9 if field=='volume' else 16)
            widget.grid(row=0,column=index*2+1,sticky='ew',padx=3)
            bulk.columnconfigure(index*2+1,weight=1)
        self.verification=tk.StringVar(value='REVIEWED')
        ttk.Combobox(bulk,textvariable=self.verification,values=VERIFICATIONS,state='readonly',width=13).grid(row=1,column=0,columnspan=2,pady=4)
        ttk.Button(bulk,text='Preview Changes',command=lambda:self.safe(self.bulk_preview)).grid(row=1,column=2,columnspan=2)
        bulk_more=ttk.Menubutton(bulk,text='More ▾');bulk_more.grid(row=1,column=4,columnspan=2)
        bulk_menu=tk.Menu(bulk_more,tearoff=False)
        bulk_menu.add_command(label='Clear Curated Volume',command=lambda:self.safe(lambda:self.bulk_preview(clear=True)))
        bulk_menu.add_command(label='Reset Selected Overrides',command=lambda:self.safe(lambda:self.bulk_preview(reset=True)))
        bulk_menu.add_command(label='Set Verification',command=lambda:self.safe(self.verify_selected))
        bulk_more.configure(menu=bulk_menu)
        self.advanced_button=ttk.Button(right,text='▶ Advanced Commands',command=self.toggle_advanced)
        self.advanced_button.pack(anchor='w',pady=(3,0))
        console=ttk.Frame(right);self.console=console
        self.command=tk.StringVar()  # Compatibility for programmatic single-command control.
        input_frame,self.entry=app.text_widget(console,height=4,wrap='none')
        input_frame.pack(side='left',fill='both',expand=True)
        self.entry.bind('<Control-Return>',lambda e:(self.safe(self.execute),'break')[1])
        self.entry.bind('<KeyRelease>',lambda e:self.cancel() if not
                        (e.keysym=='Return' and e.state & 4) else None)
        self.entry.bind('<<Paste>>',lambda e:self.cancel())
        ttk.Button(console,text='Preview Command',command=lambda:self.safe(self.execute)).pack(side='left')
        ttk.Button(console,text='Command Help',command=lambda:self.display_window('Command Help',HELP)).pack(side='left')
        f,self.output=app.text_widget(right,height=5,wrap='none');f.pack(fill='both',pady=4)
        self.output.configure(state='disabled')
        buttons=ttk.Frame(right);buttons.pack(fill='x')
        self.apply_button=ttk.Button(buttons,text='Apply Changes',state='disabled',command=lambda:self.safe(self.apply))
        self.apply_button.pack(side='left')
        ttk.Button(buttons,text='Cancel Preview',command=self.cancel).pack(side='left',padx=5)
        ttk.Button(buttons,text='Undo',command=lambda:self.safe(lambda:self.preview_reverse(False))).pack(side='left')
        ttk.Button(buttons,text='Redo',command=lambda:self.safe(lambda:self.preview_reverse(True))).pack(side='left')
        self._programmatic_command_reset=False
        self.preview_selection=set()
        for var in (*self.bulk.values(),self.verification,self.filter,self.volume_filter):
            var.trace_add('write',lambda *_:self.cancel())
        self.command.trace_add('write',lambda *_:None if self._programmatic_command_reset else self.cancel())
        self.build_history(history_frame)

    def selection_changed(self,event=None):
        self.selected_label.set(f'Selected: {len(self.tree.selection())} rows')
        if self.pending and set(self.tree.selection())!=self.preview_selection:self.cancel()

    def toggle_advanced(self):
        if self.console.winfo_manager():
            self.console.pack_forget();self.advanced_button.configure(text='▶ Advanced Commands')
        else:
            self.console.pack(fill='x',after=self.advanced_button)
            self.advanced_button.configure(text='▼ Advanced Commands')

    def rebind(self,store):
        self.cancel();self.store=store;self.current=None;self.rows=[]
        self.tree.delete(*self.tree.get_children());self.volumes.delete(*self.volumes.get_children())
        self.output.configure(state='normal');self.output.delete('1.0','end');self.output.configure(state='disabled')
        self.refresh()

    def safe(self, callback):
        try: return callback()
        except (ValueError, OSError) as exc:
            self.log('ERROR: '+str(exc));messagebox.showerror('Catalog',str(exc),parent=self.app)

    def log(self,text):
        self.output.configure(state='normal');self.output.insert('end',str(text)+'\n');self.output.see('end');self.output.configure(state='disabled')

    def select_all(self,event=None):
        self.tree.selection_set(self.tree.get_children());return 'break'

    def title_selected(self,event=None):
        selection=self.titles.selection()
        if selection and int(selection[0])!=self.current: self.open(int(selection[0]))

    def open(self,work_id,filter_name='All',keys=None):
        self.current=work_id;self.cancel();self.filter.set(filter_name)
        self.app.nb.select(self.app.database_tab)
        if self.titles.exists(str(work_id)): self.titles.selection_set(str(work_id))
        self.refresh_rows()
        if keys is not None:
            selected_keys={normalize_chapter_number(key) or str(key) for key in keys}
            chosen=[r['iid'] for r in self.rows if r['key'] in selected_keys and self.tree.exists(r['iid'])]
            self.tree.selection_set(chosen)
        elif filter_name!='All': self.select_all()

    def refresh(self):
        if self.pending and (self.current is None or
                self.store.snapshot(self.current)[1]!=self.pending.get('audit_id') or
                self.store.state(self.current)['revision']!=self.pending.get('revision')):
            self.cancel()
        self.titles.delete(*self.titles.get_children())
        allowed=self.app.scoped_work_ids()
        works=self.app.db.works(allowed,audit_by_work=self.app.scope_audits())
        for row in works: self.titles.insert('','end',iid=str(row['id']),values=(row['input_title'],))
        if self.current and self.titles.exists(str(self.current)): self.titles.selection_set(str(self.current))
        states=[self.app.audit_state(r) for r in works]
        with self.app.db.con() as c:
            count=c.execute('SELECT count(DISTINCT work_id),count(*) FROM curated_fields').fetchone()
        classifications=[publication_classification_counts(json.loads(row['publication_json'] or '{}'))
                         for row in works if row['audit_id']]
        artifacts=sum(row['classified_provider_artifacts'] for row in classifications)
        unclassified=sum(row['unclassified_records'] for row in classifications)
        self.health.set(f'Titles: {len(works)}\nPass: {states.count("PASS")}  Review: {states.count("REVIEW")}  Error: {states.count("ERROR")}\nCurated titles: {count[0]}\nManual fields: {count[1]}\nProvider artifacts: {artifacts}\nUnclassified: {unclassified}\nUnmapped: {sum(r["unmapped_chapters"] or 0 for r in works)}')
        if self.current: self.refresh_rows()
        self.refresh_history()

    def refresh_rows(self):
        keep=set(self.tree.selection());self.tree.delete(*self.tree.get_children())
        self.volumes.delete(*self.volumes.get_children())
        if self.current is None: return
        self.rows=self.store.rows(self.current)
        filters={'All':['all'],'Unmapped':['unmapped'],'Missing':['missing'],'Conflicts':['conflicts'],
                 'Modified':['modified'],'Curated':['curated'],'Automatic only':['automatic'],
                 'Volume N':['volume',self.volume_filter.get() or '-1']}
        scope=filters[self.filter.get()]
        for row in self.rows:
            if not matches(row,scope): continue
            effective=row['effective'];curated=row['curated'].get('volume')
            value=curated['value'] if curated else '—'
            source='curated_database' if curated and curated['verification']!='UNVERIFIED' and 'INCOMPATIBLE' not in row['status'] else row['source']
            verifications=sorted({entry['verification'] for entry in row['curated'].values()})
            self.tree.insert('','end',iid=row['iid'],values=(effective['chapter'],effective.get('title') or '',effective.get('volume') if effective.get('volume') is not None else '∅',
                effective.get('type'),row['automatic'].get('volume'), '∅' if value is None else value,effective.get('volume'),source,row['status'],
                effective.get('source_note') or '',', '.join(verifications) or 'AUTOMATIC'))
        self.tree.selection_set([key for key in keep if self.tree.exists(key)])
        groups={}
        for row in self.rows:
            volume=row['effective'].get('volume')
            if volume is not None: groups.setdefault(str(volume),[]).append(row['effective']['chapter'])
        state=self.store.state(self.current)
        for field in state['fields']:
            if field['entity']=='volume' and field['field']=='exists' and field['value']:
                groups.setdefault(field['record_key'],[])
        for volume,chapters in groups.items():
            fields={r['field']:r for r in state['fields'] if r['entity']=='volume' and r['record_key']==volume}
            self.volumes.insert('','end',iid=volume,values=(volume,fields.get('title',{}).get('value',''),', '.join(chapters),
                fields.get('external_ids',{}).get('value',''),fields.get('source_note',{}).get('value',''),
                ', '.join(sorted({r['verification'] for r in fields.values()})) or 'AUTOMATIC'))
        if not self.rows: self.log('RERUN REQUIRED: no chapter projection is stored for this title.')
        if self.pending:self.paint_pending_grid()

    def paint_pending_grid(self):
        if not self.pending:return
        by_key={r['key']:r['iid'] for r in self.rows if self.tree.exists(r['iid'])}
        first=None
        for op in self.pending['changes']:
            key=(op['after'] or op['before'])['record_key'] if op['entity']=='evidence' else op['key']
            iid=by_key.get(str(key))
            if iid is None:continue
            values=list(self.tree.item(iid,'values'))
            field=op['field'];after=op['after']
            marker='  ⟦PENDING⟧'
            if op['entity']=='evidence':
                values[8]=' '.join((values[8],
                    'PENDING EVIDENCE' if after else 'PENDING EVIDENCE REMOVAL')).strip()
            elif field=='volume':
                proposed=after['value'] if after else next((r['automatic'].get('volume') for r in self.rows if r['iid']==iid),None)
                shown='∅' if proposed is None else str(proposed)
                values[5]=shown+marker if after else '—'+marker
                values[6]=shown+marker
                values[2]=shown+marker
            elif field=='title':values[1]=str(after['value'] if after else '')+marker
            elif field=='type':values[3]=str(after['value'] if after else '')+marker
            elif field=='source_note':values[9]=str(after['value'] if after else '')+marker
            if op['entity']!='evidence' and after and (not op['before'] or
                    op['before']['verification']!=after['verification']):
                values[10]=after['verification']+marker
            if 'PENDING' not in values[8]:values[8]=' '.join((values[8],'PENDING')).strip()
            self.tree.item(iid,values=values,tags=('pending',))
            if first is None:first=iid
        if first:self.tree.see(first)

    def selected(self):
        values=set(self.tree.selection());return [r for r in self.rows if r['iid'] in values]

    def bulk_preview(self,clear=False,reset=False):
        rows=self.selected()
        if not rows: raise ValueError('Select chapter rows first.')
        values={k:v.get() for k,v in self.bulk.items() if v.get()!=''}
        if clear or reset: values={'volume':None}
        if not values: raise ValueError('Enter at least one field.')
        changes=[dict(entity='chapter',key=r['key'],field=k,value=v,reset=reset) for r in rows for k,v in values.items()]
        self.preview(changes,'Bulk edit')

    def verify_selected(self):
        changes=[{'entity':'chapter','key':r['key'],'field':field,'value':entry['value']}
                 for r in self.selected() for field,entry in r['curated'].items()]
        if not changes: raise ValueError('Select rows with existing curated overrides.')
        self.preview(changes,'Set verification')

    def preview(self,changes,operation,guard=None):
        item_uuid=self.app.curation_item_uuid(self.current)
        self.pending=self.store.preview(self.current,changes,operation,self.verification.get(),self.bulk['source_note'].get(),guard)
        self.pending['working_set_item_uuid']=item_uuid
        self.preview_selection=set(self.tree.selection())
        self.render_preview()

    def edit_evidence(self):
        rows=self.selected()
        if not rows:raise ValueError('Select curated chapter rows before adding evidence.')
        if not all('volume' in r['curated'] for r in rows):
            raise ValueError('Selected rows need curated volume assertions before adding evidence.')
        dialog=tk.Toplevel(self.app);dialog.title('Curated Evidence');dialog.transient(self.app)
        dialog.configure(bg=self.app.cget('bg'))
        body=ttk.Frame(dialog,padding=14);body.pack(fill='both',expand=True)
        fields={}
        for label,key in (('Source name','source_name'),('Source URL (optional)','source_url'),
                          ('Evidence note (optional)','note'),
                          ('Accessed date (YYYY-MM-DD; blank means Apply date)','accessed_at')):
            ttk.Label(body,text=label).pack(anchor='w',pady=(6,0))
            value=tk.StringVar();ttk.Entry(body,textvariable=value,width=70).pack(fill='x')
            fields[key]=value
        def submit():
            evidence={k:v.get().strip() for k,v in fields.items()}
            changes=[dict(entity='evidence',key=str(uuid.uuid4()),field='add',
                          target_key=r['key'],target_field='volume',**evidence) for r in rows]
            self.safe(lambda:self.preview(changes,'Add curated evidence'))
            if self.pending:dialog.destroy()
        ttk.Button(body,text='Preview Evidence Change',command=submit).pack(anchor='e',pady=10)

    def share_structure(self):
        if self.current is None:raise ValueError('Open the target edition first.')
        target=self.app.db.work(self.current)
        candidates=[r for r in self.app.db.works() if r['id']!=self.current and
                    r['canonical_work_id'] and r['canonical_work_id']==target['canonical_work_id'] and
                    r['language']==target['language'] and r['edition']!=target['edition']]
        if not candidates:raise ValueError('No exact canonical sibling edition is available.')
        dialog=tk.Toplevel(self.app);dialog.title('Reviewed Structure Compatibility')
        dialog.configure(bg=self.app.cget('bg'));dialog.transient(self.app)
        body=ttk.Frame(dialog,padding=14);body.pack(fill='both',expand=True)
        ttk.Label(body,text=f'Target: {target["input_title"]} / {target["edition"]}').pack(anchor='w')
        choices={f'{r["input_title"]} / {r["edition"]} [{r["id"]}]':r['id'] for r in candidates}
        selected=tk.StringVar(value=next(iter(choices)))
        ttk.Label(body,text='Structure source edition').pack(anchor='w',pady=(8,2))
        ttk.Combobox(body,textvariable=selected,values=tuple(choices),state='readonly',width=55).pack(fill='x')
        ttk.Label(body,text='Evidence note explaining identical chapter-to-volume structure').pack(anchor='w',pady=(8,2))
        note=tk.StringVar();ttk.Entry(body,textvariable=note,width=70).pack(fill='x')
        verification=tk.StringVar(value='REVIEWED')
        ttk.Combobox(body,textvariable=verification,values=('REVIEWED','VERIFIED'),state='readonly').pack(anchor='w',pady=8)
        def submit():
            try:
                item_uuid=self.app.curation_item_uuid(self.current)
                self.app.db.working_sets.relate_structure(choices[selected.get()],self.current,
                                                           note.get(),verification.get(),item_uuid=item_uuid)
            except ValueError as exc:messagebox.showerror('Structure Compatibility',str(exc),parent=dialog)
            else:
                dialog.destroy();self.app.refresh_all()
                self.app.post_curation(item_uuid)
                self.log('Reviewed structure relationship saved; active membership queued for audit.')
        ttk.Button(body,text='Save Relationship',command=submit).pack(anchor='e')

    def render_preview(self):
        value=self.pending
        item_uuid=self.app.curation_item_uuid(value['work_id'])
        if value.get('working_set_item_uuid',item_uuid)!=item_uuid:
            raise ValueError('Curation scope changed; preview again.')
        value['working_set_item_uuid']=item_uuid
        records={(r['entity'],r['key']) for r in value['changes'] if r['entity']!='evidence'}
        evidence=[r for r in value['changes'] if r['entity']=='evidence']
        added=sum(r['after'] is not None for r in evidence)
        removed=len(evidence)-added
        transitions=[r for r in value['changes'] if r['entity']!='evidence' and r['after'] and
                     (not r['before'] or r['before']['verification']!=r['after']['verification'])]
        lines=[f'PRE-APPLY VALIDATION: {len(records)} records / '
               f'{len(value["changes"])-len(evidence)} value fields / '
               f'{len(transitions)} verification changes / {added} evidence additions / '
               f'{removed} evidence removals. Apply to commit.']
        if value.get('guard'): lines.append('Review packet revision guard verified; it will be checked again at Apply.')
        if value.get('high_impact'): lines.append('HIGH-IMPACT identity/number edit. Rebinding may quarantine existing overrides until an exact compatible audit.')
        if value.get('identity_before')!=value.get('identity_after'):
            lines.append('Identity before: '+json.dumps(value.get('identity_before'),ensure_ascii=False))
            lines.append('Identity after: '+json.dumps(value.get('identity_after'),ensure_ascii=False))
        for r in value['changes']:
            if r['entity']=='evidence':
                item=r['after'] or r['before']
                lines.append(f'EVIDENCE {"ADDED" if r["after"] else "REMOVED"} '
                             f'chapter {item["record_key"]} {item["field"]}: '
                             f'{item["source_name"]}  {item["source_url"] or "(no URL)"}')
                continue
            before=r.get('effective_before',r['before']['value'] if r['before'] else '(automatic)')
            after=r.get('effective_after',r['after']['value'] if r['after'] else '(automatic)')
            lines.append(f'{r["entity"]} {r["key"]}  {r["field"]}: {before!r} → {after!r}')
            if r['after'] and (not r['before'] or r['before']['verification']!=r['after']['verification']):
                lines.append(f'{r["entity"]} {r["key"]}  verification: '
                             f'{r["before"]["verification"] if r["before"] else "AUTOMATIC"} → '
                             f'{r["after"]["verification"]}')
        lines.extend(value.get('validation',{}).get('warnings',[]))
        self.log('\n'.join(lines));self.apply_button.configure(state='normal')
        self.paint_pending_grid()

    def cancel(self):
        had_pending=bool(self.pending)
        self.pending=None
        self.apply_button.configure(state='disabled')
        if had_pending and self.current is not None:self.refresh_rows()

    def apply(self):
        if not self.pending: raise ValueError('Preview changes first.')
        value=self.pending
        item_uuid=self.app.curation_item_uuid(value['work_id'])
        if value.get('working_set_item_uuid',item_uuid)!=item_uuid:
            raise ValueError('Curation scope changed; preview again.')
        value['working_set_item_uuid']=item_uuid
        if value.get('database_uuid')!=self.app.db.database_uuid:
            raise ValueError('Preview belongs to another database; preview again.')
        if value.get('reverse'):
            if self.store.state(value['work_id'])['revision']!=value['revision']: raise ValueError('Stale undo/redo preview.')
            result=self.store.reverse(value['work_id'],value['redo'],value['change_id'],value['revision'],value['audit_id'],item_uuid=item_uuid)
        else: result=self.store.apply(value)
        self.cancel();self.app.refresh_all()
        self.app.post_curation(item_uuid)
        for var in self.bulk.values(): var.set('')
        self.log('POST-APPLY VALIDATION: saved fields and identity verified. '+self.validation_text(result)+
                 ('\nFresh audit queued for the active membership.' if item_uuid else '\nRe-run Audit to publish a new global audit result.'))

    def preview_reverse(self,redo=False,change_id=None):
        if self.current is None: raise ValueError('Open a title first.')
        history=[r for r in self.store.history(self.current) if r['state']==('reverted' if redo else 'active')]
        if not history: raise ValueError('Nothing to redo.' if redo else 'Nothing to undo.')
        row=history[-1] if redo else history[0]
        if change_id and row['id']!=change_id: raise ValueError('Revert newer active changes for this title first.')
        changes=json.loads(row['changes_json'])
        if not redo: changes=[dict(r,before=r['after'],after=r['before'],
                                  effective_before=r.get('effective_after'),effective_after=r.get('effective_before')) for r in changes]
        self.pending={'database_uuid':self.app.db.database_uuid,'reverse':True,'redo':redo,
                      'work_id':self.current,'change_id':row['id'],
                      'revision':self.store.state(self.current)['revision'],
                      'audit_id':self.store.snapshot(self.current)[1],'changes':changes}
        self.render_preview()



    def _clear_command_input(self):
        self._programmatic_command_reset=True
        try:
            self.command.set('');self.entry.delete('1.0','end')
        finally:self._programmatic_command_reset=False

    def execute(self):
        text=self.entry.get('1.0','end-1c').strip() or self.command.get()
        self.cancel()
        commands=parse_batch(text)
        guard=commands.pop(0) if commands[0]['action']=='guard' else None
        if not commands:raise ValueError('Guard needs an edit command.')
        work_id=None;current=self.current
        for command in commands:
            resolved=title_scope(self.app.db,current,command['title'])
            if work_id is not None and resolved!=work_id:
                raise ValueError('A batch must target one exact work, edition, and language.')
            work_id=resolved;current=resolved
        if work_id!=self.current:self.open(work_id)
        if guard and not any(c['action'] in ('edit','evidence','record','renumber','verify','verify_work','work_edit','alias','id_edit','volume_edit') for c in commands):
            raise ValueError('A revision guard needs a mutation.')
        if len(commands)>1:
            changes,selected=self.compile_batch(commands)
            if changes:
                self.tree.selection_set([iid for iid in selected if self.tree.exists(iid)])
                self.preview(changes,f'Batch: {len(commands)} commands',guard)
            elif commands[-1]['action']=='validate':self.validate()
            else:self.tree.selection_set([iid for iid in selected if self.tree.exists(iid)])
            self.log('> '+text)
            self.command_history.append(text);self.history_index=len(self.command_history)
            self._clear_command_input()
            return
        command=commands[0];action=command['action']
        if action in ('select','show'):
            rows=scoped_rows(self.rows,command['target'],self.tree.selection())
            if action=='show':
                filters={'unmapped':'Unmapped','conflicts':'Conflicts','modified':'Modified','automatic':'Automatic only','curated':'Curated','volume':'Volume N'}
                self.filter.set(filters.get(command['target'][0],'All'))
                if command['target'][0]=='volume': self.volume_filter.set(command['target'][1])
                self.refresh_rows()
            self.tree.selection_set([r['iid'] for r in rows if self.tree.exists(r['iid'])])
            if self.tree.selection():self.tree.see(self.tree.selection()[0])
            self.log(f'{len(self.tree.selection())} visible rows selected.')
        elif action=='inspect':self.inspect(command)
        elif action in ('edit','evidence','record','renumber','verify','verify_work','work_edit','alias','id_edit','volume_edit'):
            self.preview(self.command_changes(command),text,guard)
        elif action in ('undo','redo'):self.preview_reverse(action=='redo')
        else:{'validate':self.validate,'save':self.save,'audit':self.reaudit}[action]()
        self.log('> '+text)
        self.command_history.append(text);self.history_index=len(self.command_history)
        self._clear_command_input()

    def command_cycle(self,direction):
        self.history_index=max(0,min(len(self.command_history),self.history_index+direction))
        value=self.command_history[self.history_index] if self.history_index<len(self.command_history) else ''
        self.command.set(value);self.entry.delete('1.0','end');self.entry.insert('1.0',value)
        return 'break'




    def validate(self):
        if self.current is None: raise ValueError('Open a title first.')
        value=self.store.validate(self.current);self.log(self.validation_text(value));return value

    def save(self):
        if self.pending: raise ValueError('A preview is pending. Apply or Cancel it first.')
        validation=self.validate()
        if not validation['valid']: raise ValueError('Validation errors must be resolved before continuing.')
        self.log('All applied edits are already saved transactionally.')

    def reaudit(self):
        self.save()
        item_uuid=self.app.curation_item_uuid(self.current)
        self.app.start_audit([item_uuid] if item_uuid else [self.current],global_context=item_uuid is None)
        self.app.nb.select(self.app.tabs[0])

    def export(self):
        self.save();path=self.store.export(self.current);self.log('Exported '+str(path))

    def form(self,title,fields,callback):
        win=tk.Toplevel(self.app);win.title(title);win.geometry('670x620');win.configure(bg=self.app.cget('bg'))
        canvas=tk.Canvas(win,bg=self.app.cget('bg'),highlightthickness=0)
        bar=ttk.Scrollbar(win,orient='vertical',command=canvas.yview);canvas.configure(yscrollcommand=bar.set)
        bar.pack(side='right',fill='y');canvas.pack(fill='both',expand=True)
        body=ttk.Frame(canvas,padding=12);window=canvas.create_window((0,0),window=body,anchor='nw')
        body.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(window,width=e.width))
        ttk.Label(body,text='Check only fields to change. Identity/number changes are high-impact.',wraplength=580).grid(row=0,column=0,columnspan=3,sticky='w',pady=8)
        entries={}
        for index,(field,value) in enumerate(fields.items(),1):
            enabled=tk.BooleanVar();var=tk.StringVar(value=value if value is not None else '')
            ttk.Checkbutton(body,text=field,variable=enabled).grid(row=index,column=0,sticky='w',pady=5)
            ttk.Entry(body,textvariable=var,width=48).grid(row=index,column=1,sticky='ew',pady=5)
            entries[field]=(enabled,var)
        body.columnconfigure(1,weight=1)
        def propose():
            values={key:var.get() for key,(enabled,var) in entries.items() if enabled.get()}
            if not values: raise ValueError('Check fields to edit.')
            callback(values);win.destroy()
        ttk.Button(body,text='Preview Changes',command=lambda:self.safe(propose)).grid(row=len(fields)+1,column=1,pady=10)

    def edit_row(self):
        rows=self.selected()
        if len(rows)!=1: raise ValueError('Select exactly one row to edit chapter number/title/type/volume.')
        row=rows[0]
        self.form('Edit chapter',row['effective'],lambda values:self.preview([
            {'entity':'chapter','key':row['key'],'field':k,'value':None if k=='volume' and not v else v}
            for k,v in values.items()],'Edit chapter'))

    def edit_identity(self):
        if self.current is None: raise ValueError('Open a title first.')
        auto,_=self.store.snapshot(self.current);state=self.store.state(self.current)
        identity=state['identity'] or auto.get('catalog_identity') or {}
        work=self.app.db.work(self.current)
        values={'canonical_title':work['canonical_title'] or work['input_title'],
                'canonical_work_id':identity.get('canonical_work_id',''), 'edition':identity.get('edition',work['edition']),
                'language':identity.get('language',work['language']),'publication_context':identity.get('publication_context',''),
                'aliases':'','external_ids':'','expected_chapters':'','expected_volumes':'','publication_status':'','source_note':''}
        for r in state['fields']:
            if r['entity']=='work': values[r['field']]=r['value']
        if not values['external_ids']: values['external_ids']=identity.get('external_ids',{})
        values['external_ids']='; '.join(f'{k}={v}' for k,v in values['external_ids'].items()) if isinstance(values['external_ids'],dict) else values['external_ids']
        if isinstance(values['aliases'],list): values['aliases']='; '.join(values['aliases'])
        self.form('HIGH-IMPACT title identity — aliases separated by ; / IDs source=value',values,self.identity_preview)


    def identity_preview(self,values):
        if 'aliases' in values: values['aliases']=[v.strip() for v in values['aliases'].split(';') if v.strip()]
        if 'external_ids' in values: values['external_ids']=self.ids(values['external_ids'])
        self.preview([{'entity':'work','key':'work','field':k,'value':v} for k,v in values.items()],'Edit title identity')

    def edit_volume(self):
        selection=self.volumes.selection()
        if not selection: raise ValueError('Select a volume first.')
        key=selection[0]
        values={'title':'','external_ids':'','source_note':''}
        for r in self.store.state(self.current)['fields']:
            if r['entity']=='volume' and r['record_key']==key: values[r['field']]=r['value']
        if isinstance(values['external_ids'],dict): values['external_ids']='; '.join(f'{k}={v}' for k,v in values['external_ids'].items())
        def propose(changes):
            if 'external_ids' in changes: changes['external_ids']=self.ids(changes['external_ids'])
            self.preview([{'entity':'volume','key':key,'field':k,'value':v} for k,v in changes.items()],'Edit volume metadata')
        self.form('Volume '+key,values,propose)

    def build_history(self,frame):
        controls=ttk.Frame(frame);controls.pack(fill='x')
        ttk.Label(controls,text='History scope').pack(side='left')
        self.history_scope=tk.StringVar(value='Active Working Set' if self.app.active_set_uuid else 'All Catalog')
        self.history_scope_box=ttk.Combobox(controls,textvariable=self.history_scope,state='readonly',width=26)
        self.history_scope_box.pack(side='left',padx=5)
        self.history_scope_box.bind('<<ComboboxSelected>>',lambda e:self.refresh_history())
        ttk.Button(controls,text='View',command=lambda:self.safe(self.view_history)).pack(side='left')
        ttk.Button(controls,text='Preview Revert',command=lambda:self.safe(self.revert_history)).pack(side='left',padx=5)
        f,self.history=self.app.tree_widget(frame,('date','database','title','action','fields','before','after'),
            ('UTC timestamp','Database','Title','Action','Fields affected','Before','After'),
            (220,260,240,180,220,250,250))
        f.pack(fill='both',expand=True,pady=5)
        self.history.bind('<Double-1>',lambda e:self.safe(self.view_history))
        self.history.bind('<<TreeviewSelect>>',lambda e:self.cancel() if self.pending else None)

    def refresh_history(self):
        self.history.delete(*self.history.get_children())
        self.history_data={}
        choices=('Active Working Set','Accepted Master Catalog','All Catalog',
                 *getattr(self.app,'catalog_named_sets',{}))
        self.history_scope_box.configure(values=choices)
        if self.history_scope.get() not in choices:
            self.history_scope.set('Active Working Set' if self.app.active_set_uuid else 'All Catalog')
        scope=self.history_scope.get()
        if scope=='All Catalog':allowed=None
        elif scope=='Accepted Master Catalog':
            allowed={r['id'] for r in self.app.db.works(accepted_only=True)}
        else:
            set_uuid=(self.app.active_set_uuid if scope=='Active Working Set' else
                      self.app.catalog_named_sets.get(scope))
            allowed={r['work_id'] for r in self.app.db.working_sets.items(set_uuid) if r['work_id']}
        database=f'{self.app.db.path.name} [{self.app.db.database_uuid}]'
        with self.app.db.con() as c:
            audits=[dict(r) for r in c.execute('''SELECT a.id,a.work_id,a.created_at,a.audit_revision,
                a.final_state,a.logical_chapters,a.final_volumes,w.input_title FROM search_audits a
                JOIN works w ON w.id=a.work_id''')]
            edits=[dict(r) for r in c.execute('''SELECT e.id,e.timestamp,e.action,h.id change_id,
                h.operation,h.changes_json,h.state,h.work_id,w.input_title FROM curated_events e
                JOIN curated_changes h ON h.id=e.change_id JOIN works w ON w.id=h.work_id''')]
            events=[dict(r) for r in c.execute('SELECT * FROM database_events')]
        entries=[]
        for a in audits:
            if allowed is not None and a['work_id'] not in allowed:continue
            iid=f'a:{a["id"]}'
            entries.append((a['created_at'],iid,(a['created_at'],database,a['input_title'],'AUDIT',
                f'Revision {a["audit_revision"]}', 'Previous automatic audit',
                f"{a['final_state'] or '—'} · {a['logical_chapters']} chapters / {a['final_volumes']} volumes"),a))
        for e in edits:
            if allowed is not None and e['work_id'] not in allowed:continue
            iid=f'c:{e["id"]}';changes=json.loads(e['changes_json'])
            affected=', '.join(sorted({f"{r['entity']} {r['key']} {r['field']}" for r in changes}))
            action={'apply':'CURATION','undo':'UNDO','redo':'REDO'}.get(e['action'],e['action'].upper())
            before='; '.join(f"{r['field']}={r['before']['value'] if r['before'] else '(automatic)'}" for r in changes[:4])
            after='; '.join(f"{r['field']}={r['after']['value'] if r['after'] else '(automatic)'}" for r in changes[:4])
            if e['action']=='undo':before,after=after,before
            entries.append((e['timestamp'],iid,(e['timestamp'],database,e['input_title'],action,affected,before,after),e))
        for e in events:
            if allowed is not None:
                details=json.loads(e['details_json'] or '{}')
                work_uuids={self.app.db.work(wid)['work_uuid'] for wid in allowed}
                set_scope=(self.app.active_set_uuid if scope=='Active Working Set' else self.app.catalog_named_sets.get(scope))
                if (details.get('work_uuid') not in work_uuids and
                    not (set_scope and (details.get('working_set_uuid')==set_scope or set_scope in (details.get('working_set_uuids') or [])))):continue
            iid=f'e:{e["id"]}'
            entries.append((e['timestamp'],iid,(e['timestamp'],database,'—',e['origin'],e['description'],'—',
                                              e['details_json']),e))
        for _,iid,values,data in sorted(entries,reverse=True):
            self.history.insert('','end',iid=iid,values=values)
            self.history_data[iid]=data

    def history_row(self):
        selection=self.history.selection()
        if not selection: raise ValueError('Select a history entry.')
        if not selection[0].startswith('c:'):
            raise ValueError('Audit/import/migration history is read-only; select a curated change to revert.')
        change_id=self.history_data[selection[0]]['change_id']
        return next(r for r in self.store.history() if r['id']==change_id)

    def view_history(self):
        selected=self.history.selection()
        if not selected:raise ValueError('Select a history entry.')
        if not selected[0].startswith('c:'):
            row=self.history_data[selected[0]]
            if selected[0].startswith('a:'):
                with self.app.db.con() as c:
                    row={'audit':dict(c.execute('SELECT * FROM search_audits WHERE id=?',(row['id'],)).fetchone()),
                         'problems':[dict(r) for r in c.execute('SELECT * FROM audit_holes WHERE audit_id=?',(row['id'],))]}
            self.display_window('Database history',json.dumps(row,ensure_ascii=False,indent=2,default=str))
            return
        row=self.history_row()
        lines=[row['timestamp'],row['input_title'],row['operation'],row['state']]
        for c in json.loads(row['changes_json']):
            lines.append(f'{c["entity"]} {c["key"]}: {c["field"]}  {c["before"]} → {c["after"]}')
        self.display_window('Curated transaction','\n'.join(lines))

    def revert_history(self):
        row=self.history_row();self.open(row['work_id']);self.preview_reverse(False,row['id'])

    def display_window(self,title,text):
        win=tk.Toplevel(self.app);win.title(title);win.geometry('900x600')
        frame,widget=self.app.text_widget(win,wrap='none');frame.pack(fill='both',expand=True)
        widget.insert('1.0',text);widget.configure(state='disabled')
