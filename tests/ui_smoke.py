"""Run real Tk widgets on a disposable database; never open the user workspace."""
from pathlib import Path
import sys
import tempfile
import tkinter as tk
from tkinter import ttk

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mangaanka_database_development_kit as ddk


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


with tempfile.TemporaryDirectory() as tmp:
    app = ddk.App(workspace=tmp)
    try:
        app.geometry('1120x720')
        labels=[app.nb.tab(tab,'text') for tab in app.nb.tabs()]
        assert labels==['Audit','Problems','Catalog','Curate','History','Details'],labels
        assert str(app.db.path) in app.database_label.get() and '[PRODUCTION]' in app.database_label.get()
        assert not app.editor.console.winfo_manager(), 'Advanced Commands should start collapsed'
        buttons={w.cget('text'):w for w in descendants(app) if isinstance(w,(ttk.Button,ttk.Menubutton))}
        for expected in ('Switch Database','New Database','Open Folder','Paste','Clear',
                         'Open in Curate','Copy Diagnostic ▾','Export ▾'):
            assert expected in buttons,expected
        app.clipboard_clear();app.clipboard_append('Alpha\n\nBeta\nAlpha\nGamma')
        buttons['Paste'].invoke()
        assert app.input.get('1.0','end').strip()=='Alpha\nBeta\nGamma'
        buttons['Clear'].invoke()
        assert not app.input.get('1.0','end').strip()
        titles = (Path(__file__).resolve().parents[1] / 'MangaAnka_DDK_Test_Titles.txt').read_text(encoding='utf-8-sig').splitlines()
        app.db.add_titles(titles + [f'Scroll test {n}' for n in range(80)], 'standard', 'en')
        app.queue_ids=[r['id'] for r in app.db.works()]
        for work in app.db.works():
            app.db.save_audit(work['id'], {'query':work['input_title'], 'match_title':work['input_title'],
                'publication': {'status':'complete','edition':'standard','logical_chapters':163,
                                'final_volumes':0,'mapped_chapters':0,'unmapped_chapters':163,
                                'catalog_identity':{'canonical_work_id':f'fixture:{work["id"]}',
                                    'edition':'standard','language':'en','publication_context':'',
                                    'external_ids':{'fixture':str(work['id'])},'trusted':True},
                                'projection':[{'chapter':str(n),'id':str(n),'_acquisition_provider':'fixture',
                                               'title':'','volume':None} for n in range(222,385)]},
                'inventories':[{'source_name':'Test provider','usable':True,'chapter_count':163,
                                'native_volumes':0,'standalone_chapters':163,'summary':'Qualified'}]},
                [{'code':'SMOKE_ONLY','severity':'warning','message':'Wide diagnostic ' * 30}])
        app.refresh_all()
        app.load_details(1)
        style = ttk.Style(app)
        assert style.lookup('Treeview', 'foreground', ('selected',)).lower() == '#ffffff'
        assert style.lookup('Treeview', 'background', ('selected',)) == ddk.ACCENT_DARK
        assert style.lookup('TCombobox', 'foreground', ('readonly',)).lower() == '#ffffff'
        assert style.lookup('TCombobox', 'selectbackground', ('readonly',)) == ddk.PANEL2
        editor=app.editor
        editor.open(1)
        app.update()
        tree=editor.tree
        editor.entry.insert('1.0','select chapter 275\nset volume 23 selected\n'
                            'set source-note "Verified source" selected\n'
                            'set verification verified selected\nvalidate')
        editor.execute();app.update()
        assert editor.pending and len(editor.pending['changes'])==2
        row=editor.tree.item('53')
        assert str(row['values'][0])=='275' and row['tags']==['pending'],row
        values=row['values']
        assert values[4]=='None' or values[4]=='',values
        assert all('23' in str(values[index]) and 'PENDING' in str(values[index])
                   for index in (2,5,6)),values
        assert 'Verified source' in values[9] and 'PENDING' in values[9]
        assert 'VERIFIED' in values[10] and 'PENDING' in values[10]
        assert 'verification changes' in editor.output.get('1.0','end')
        assert not app.db.catalog.state(1)['fields'], 'Atomic preview wrote before Apply'
        assert {r['key'] for r in editor.pending['changes']}=={'275'}
        editor.apply();app.update()
        assert not editor.tree.item('53','tags') and 'PENDING' not in str(editor.tree.item('53','values')),editor.tree.item('53')
        assert len(app.db.catalog.history(1))==1
        assert len(app.db.catalog.state(1)['fields'])==2
        editor.preview_reverse();editor.apply();app.update()
        assert not app.db.catalog.state(1)['fields']
        for field,command,column,expected in (
                ('title','set title "Preview Title" chapter 275',1,'Preview Title'),
                ('type','set type special chapter 275',3,'special'),
                ('source_note','set source-note "Preview Note" chapter 275',9,'Preview Note')):
            editor.command.set(command);editor.execute();app.update()
            staged=editor.tree.item('53','values')
            assert expected in staged[column] and 'PENDING' in staged[column],(field,staged)
            assert all('PENDING' not in str(staged[n]) for n in ({1,3,9}-{column})),(field,staged)
            editor.cancel();app.update()
            assert not editor.tree.item('53','tags') and 'PENDING' not in str(editor.tree.item('53','values'))
        editor.command.set('set volume 23 chapters 275-330');editor.execute();app.update()
        assert len(editor.pending['changes'])==56
        assert sum('pending' in editor.tree.item(iid,'tags') for iid in editor.tree.get_children())==56
        editor.command.set('set volume 24 chapters 275-330');app.update()
        assert editor.pending is None and str(editor.apply_button['state'])=='disabled'
        assert not any('pending' in editor.tree.item(iid,'tags') for iid in editor.tree.get_children())
        editor.command.set('')
        editor.command.set('set volume 23 chapter 275');editor.execute();app.update()
        editor.tree.selection_set('0');app.update()
        assert editor.pending is None and not editor.tree.item('53','tags')
        editor.command.set('')
        editor.entry.insert('1.0','select chapter 275\nset volume 23 selected\n'
                            'add evidence source "Publisher" url "https://example.org/one" selected\n'
                            'add evidence source "Independent TOC" note "Volume 23" selected')
        editor.execute();app.update()
        assert len(editor.pending['changes'])==3
        assert editor.output.get('1.0','end').count('EVIDENCE ADDED chapter 275')==2
        assert not app.db.catalog.evidence(1)
        editor.cancel();app.update()
        assert not app.db.catalog.evidence(1) and not editor.tree.item('53','tags')
        for script in ('select chapter 275\nset volume 23 selected',
                       'on "Chainsaw Man" select chapter 275\non "Chainsaw Man" set volume 23 selected',
                       'on "Chainsaw Man" select chapter 275\nset volume 23 selected'):
            editor.entry.insert('1.0',script);editor.execute();app.update()
            assert editor.pending and len(editor.pending['changes'])==1,script
            editor.cancel()
        editor.command.set('set volume 23');editor.execute()
        assert editor.pending and len(editor.pending['changes'])==1
        editor.cancel()
        for script in ('select chapter 275\nset volume 23 selected\nunsupported nonsense',
                       'on "Unknown Title" select chapter 275\nset volume 23 selected',
                       'select chapter 275\nset volume 23 selected\nset volume 24 selected'):
            editor.entry.insert('1.0',script)
            try:editor.execute()
            except ValueError:pass
            else:raise AssertionError('Invalid atomic batch succeeded: '+script)
            assert editor.pending is None and not app.db.catalog.state(1)['fields']
            editor.entry.delete('1.0','end')
        editor.tree.selection_remove(*editor.tree.selection())
        editor.command.set('set volume 23 selected')
        try:editor.execute()
        except ValueError:pass
        else:raise AssertionError('Selected-required edit succeeded without selection')
        editor.command.set('')
        print('MF Ghost-style scoped mutations and atomic command failure semantics OK')
        tree.unbind('<Double-1>')  # Synthetic rapid clicks must not open a modal edit form.
        def click(iid, state=0):
            tree.see(iid);app.update()
            x,y,w,h=tree.bbox(iid)
            tree.event_generate('<ButtonPress-1>',x=x+12,y=y+h//2,state=state)
            tree.event_generate('<ButtonRelease-1>',x=x+12,y=y+h//2,state=state)
            app.update()
        click('0');click('10',1)
        assert len(tree.selection())==11, ('Shift range',tree.selection())
        click('12',4)
        assert len(tree.selection())==12, ('Ctrl toggle',tree.selection())
        click('12',4)
        assert len(tree.selection())==11
        editor.command.set('set volume 24 chapters 222-232');editor.execute()
        assert not app.db.catalog.state(1)['fields'], 'Command mutated before Apply'
        assert len(editor.pending['changes'])==11
        editor.bulk['title'].set('Edited after preview')
        assert editor.pending is None and str(editor.apply_button['state'])=='disabled'
        editor.bulk['title'].set('')
        editor.command.set('set volume 24 chapters 222-232');editor.execute()
        assert str(editor.apply_button['state'])=='normal'
        editor.apply()
        assert len(app.db.catalog.state(1)['fields'])==11
        assert app.audit_state(next(r for r in app.db.works() if r['id']==1))=='RERUN REQUIRED'
        editor.command.set('undo');editor.execute()
        assert len(app.db.catalog.state(1)['fields'])==11, 'Undo mutated before Apply'
        editor.apply();assert not app.db.catalog.state(1)['fields']
        editor.command.set('redo');editor.execute();editor.apply()
        assert len(app.db.catalog.state(1)['fields'])==11
        editor.command.set('select volume 24');editor.execute();assert len(tree.selection())==11
        editor.entry.insert('1.0','set volume 25 chapters 222-226\nset volume 26 chapters 227-232')
        editor.execute()
        assert len(editor.pending['changes'])==11
        assert editor.pending['operation']=='Batch: 2 commands'
        editor.apply()
        assert len(app.db.catalog.history(1))>=2
        editor.preview_reverse();editor.apply()
        assert all(r['effective']['volume']=='24' for r in editor.rows if r['key'] in {str(n) for n in range(222,233)})
        editor.preview_reverse(True);editor.apply()
        assert next(r for r in editor.rows if r['key']=='222')['effective']['volume']=='25'
        editor.preview_reverse();editor.apply()
        for command in ('set verification verified selected','set work edition standard',
                        'set work language en','set work canonical-title "Exact Fixture"',
                        'add alias "Exact Alias"','set id anilist 12345',
                        'set expected chapters 207','add chapter 500','add volume 50',
                        'set volume-title 24 "Exact Volume"','renumber chapter 222 to 500'):
            editor.command.set(command);editor.execute()
            assert editor.pending and editor.pending['changes'],command
            editor.cancel()
        for command in ('show aliases','show ids','show expected','show effective chapter 222',
                        'show provenance volume 24','explain chapter 222','explain work'):
            editor.command.set(command);editor.execute()
            assert editor.pending is None,command
        for command in ('add chapter 500','renumber chapter 500 to 501',
                        'remove curated chapter 501','add volume 50',
                        'set volume-title 50 "Exact Volume"','remove curated volume 50',
                        'add alias "Exact Alias"','remove alias "Exact Alias"',
                        'set id anilist 12345','reset id anilist',
                        'set expected chapters 207','reset expected chapters'):
            editor.command.set(command);editor.execute();editor.apply()
        assert not any(r['key'] in ('500','501') for r in editor.rows)
        assert not any(r['entity']=='volume' and r['record_key']=='50' for r in app.db.catalog.state(1)['fields'])
        editor.filter.set('Unmapped');editor.refresh_rows();editor.select_all()
        assert len(tree.selection())==152
        editor.filter.set('All');editor.refresh_rows()
        for n in range(35):
            app.db.catalog.apply(app.db.catalog.preview(1,[{'entity':'chapter','key':'222','field':'source_note','value':f'Note {n}'}]))
        app.refresh_all()
        print('Native Shift/Ctrl selection, filtered Ctrl+A, command preview/apply, persistent undo/redo and stale audit state OK')
        surfaces=((app.tabs[0],'Audit'),(app.tabs[2],'Problems'),(app.catalog_tab,'Catalog'),(app.database_tab,'Curate'),
                  (app.history_tab,'History'),(app.tabs[3],'Details'))
        for surface, name in surfaces:
            app.nb.select(surface)
            app.update()
            bars = [w for w in descendants(surface) if isinstance(w, ttk.Scrollbar) and w.winfo_ismapped()]
            assert bars and all(b.winfo_ismapped() for b in bars), name
            for widget in descendants(surface):
                if isinstance(widget, ttk.Treeview) and widget.winfo_ismapped():
                    if len(widget.get_children()) > 30:
                        widget.yview_moveto(1)
                        app.update()
                        assert widget.yview()[0] > 0, name
                    widget.xview_moveto(1)
                    app.update()
                    if widget not in (app.detail_titles,editor.titles):
                        assert widget.xview()[0] > 0, name
                    if widget.get_children(): widget.selection_set(widget.get_children()[0])
            print(name + ': visible scrollbars, scroll commands and row selection OK')
        app.nb.select(app.database_tab);editor.views.select(1);app.update()
        bars=[w for w in editor.volumes.master.winfo_children() if isinstance(w,ttk.Scrollbar)]
        assert len(bars)==2 and all(b.winfo_ismapped() for b in bars)
        app.nb.select(app.tabs[3]);app.update()
        app.set_detail_text(('wide ' * 100 + '\n') * 200)
        app.detail_text.yview_moveto(1)
        app.detail_text.xview_moveto(1)
        app.update()
        assert app.detail_text.yview()[0] > 0 and app.detail_text.xview()[0] > 0, (app.detail_text.yview(),app.detail_text.xview(),app.detail_text.winfo_height(),app.detail_text.get('1.0','1.end')[:50])
        app.nb.select(app.tabs[2]);app.update();app.hole_tree.selection_set(app.hole_tree.get_children()[0]);app.problem_selected()
        problem_buttons=[w for w in descendants(app.tabs[2]) if isinstance(w,ttk.Button) and w.winfo_ismapped()]
        assert all(w.winfo_rootx()+w.winfo_width()<=app.winfo_rootx()+app.winfo_width() for w in problem_buttons)
        assert 'Review Packet' in app.problem_text.get('1.0','end')
        assert 'Suggested command' in app.problem_text.get('1.0','end')
        app.open_hole_details()
        assert app.nb.tab(app.nb.select(),'text')=='Curate'
        app.nb.select(app.tabs[2]);app.update()
        app.copy_diagnostics(True)
        assert 'Review Packet' in app.clipboard_get()
        editor.entry.insert('1.0',('set volume 1 chapters 222-223\n')*20)
        editor.entry.yview_moveto(1);editor.entry.xview_moveto(1);app.update()
        assert editor.entry.yview()[0]>0
        assert app.audit_tree.heading('volumes')['text'] == 'Final Volumes'
        assert app.title_tree.heading('mapped')['text'] == 'Mapped'
        artifact_group={'provider':'mangak','classification':'provider_range_bundle',
                        'pattern_family':'integer_range_bundle','count':2,
                        'identifiers':['8-16','80-88'],
                        'representative_identifiers':['8-16','80-88'],
                        'confidence':'syntax','reason':'Provider bundle identifier.',
                        'member_records':[{'identifier':'8-16','record_id':'range-a'},
                                          {'identifier':'80-88','record_id':'range-b'}]}
        app.db.save_audit(1,{'query':'Fixture','match_title':'Fixture','selected_source':'mangak',
            'publication':{'status':'complete','edition':'standard','logical_chapters':1,
                'mapped_chapters':1,'unmapped_chapters':0,'final_volumes':1,
                'unclassified_records':2,
                'normalization':{'status':'established','counts':{'main':1,'provider_range_bundle':2},
                                 'artifact_groups':[artifact_group]},
                'catalog_identity':{'trusted':True,'language':'en'},
                'context':{'shareable':True},'raw_acquisition_records':3}},
            [{'code':'PROVIDER_RANGE_BUNDLE','severity':'warning','message':'2 range bundles',
              'details':{'affected':2,'chapters':['8-16','80-88'],'confidence':'syntax'}}])
        app.refresh_all();app.update();app.load_details(1)
        detail=app.detail_text.get('1.0','end')
        assert 'PROVIDER ARTIFACT GROUPS' in detail and 'range-a' in detail and 'range-b' in detail, detail[:1000]
        assert 'provider artifacts: 2; unclassified: 0' in detail
        assert '"unclassified_records": 0' in detail
        assert 'integer_range_bundle' in app.pattern_notice.get()
        assert any(app.hole_tree.item(iid,'values')[2:6]==
                   ('PROVIDER_RANGE_BUNDLE','CODE','CODE_REVIEW_REQUIRED','syntax')
                   for iid in app.hole_tree.get_children())
        assert app.audit_tree.set('w:1','artifacts')=='2'
        assert app.audit_tree.set('w:1','unclassified')=='0'
        assert 'Provider artifacts: 2' in app.editor.health.get()
        assert app.catalog_tree.exists('1')
        old_path=app.db.path;old_uuid=app.db.database_uuid;old_count=len(app.db.works())
        app.audit_tree.selection_set('w:1');app.remove_selected()
        assert not app.audit_tree.exists('w:1') and len(app.db.works())==old_count
        app.clear_queue();assert not app.audit_tree.get_children() and len(app.db.works())==old_count
        fresh=Path(tmp)/'new-test.db'
        app.create_database(fresh,'TEST')
        assert app.db.path==fresh.resolve() and app.db.role=='TEST'
        assert '[TEST]' in app.database_label.get() and str(fresh.resolve()) in app.database_label.get()
        assert not app.catalog_tree.get_children() and not app.editor.titles.get_children()
        app.db.add_titles(['Only New DB'],'standard','en');app.refresh_all()
        assert len(app.catalog_tree.get_children())==1
        invalid=Path(tmp)/'invalid.db';invalid.write_text('not SQLite',encoding='utf-8')
        try:app.switch_database(invalid)
        except ValueError:pass
        else:raise AssertionError('Invalid database was activated')
        assert app.db.path==fresh.resolve()
        app.switch_database(old_path)
        assert app.db.database_uuid==old_uuid and len(app.db.works())==old_count
        assert len(app.catalog_tree.get_children())==old_count
        assert str(old_path) in app.database_label.get()
        app.catalog_tree.selection_set('1');app.catalog_selected()
        assert '"work"' in app.catalog_text.get('1.0','end')
        database_bytes=app.db.path.read_bytes()
        app.refresh_catalog();app.catalog_tree.selection_set('1');app.catalog_selected()
        assert app.db.path.read_bytes()==database_bytes, 'Catalog viewing wrote to SQLite'
        assert not app.editor.console.winfo_manager()
        app.geometry('1550x930');app.update()
        assert app.winfo_width()>=1500 and app.winfo_height()>=900
        print('Details long text scrolls on both axes; dark selection styles preserved.')
    finally:
        app.destroy()
    reopened=ddk.App(workspace=tmp)
    try:
        assert reopened.db.path==old_path and reopened.db.database_uuid==old_uuid
        assert len(reopened.catalog_tree.get_children())==old_count
        assert not reopened.audit_tree.get_children(), 'Queue should be transient across launches'
    finally:
        reopened.destroy()
