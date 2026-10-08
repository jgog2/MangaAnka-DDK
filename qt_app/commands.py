"""Qt command orchestration over the shared compiler and Catalog transactions."""
import json
from ddk_command_controller import CommandLogic
from ddk_commands import parse_batch, title_scope, scoped_rows


class CommandController(CommandLogic):
    def __init__(self, window):
        self.app = window; self.current = None; self.rows = []; self.pending = None
        self.selection = set(); self.scope = 'all'; self.messages = []

    @property
    def store(self): return self.app.db.catalog
    def command_selection(self): return tuple(self.selection)
    def log(self, text): self.messages.append(text)

    def open(self, wid, scope):
        self.current = wid; self.scope = scope; self.pending = None; self.selection = set()
        self.rows = self.store.rows(wid)

    def cancel(self): self.pending = None

    def preview(self, changes, operation, guard=None):
        item = self.app.session.mutation_item(self.current, self.scope)
        self.pending = self.store.preview(self.current, changes, operation, guard=guard)
        self.pending['working_set_item_uuid'] = item
        self.log(self.preview_text())

    def preview_text(self):
        if not self.pending: return 'No pending changes.'
        if self.pending.get('supplementary'):
            p=self.pending
            return ('Supplementary Preview — not yet saved\n'+p['operation']+'\n'+
                json.dumps(dict(changes=p['changes'],assertions=p.get('assertions',[]),guard=p['context']),ensure_ascii=False,indent=2)+
                '\nExplicit Apply records this decision. Numeric publication remains unchanged.')
        lines = ['Preview Changes — not yet saved']
        for r in self.pending['changes']:
            before = r.get('before'); after = r.get('after')
            lines.append(f"{r['entity']} {r['key']} · {r['field']}: {before.get('value') if before else '(automatic)'} → {after.get('value') if after else '(reset to automatic)'}")
            if after: lines.append('  '+after.get('verification', ''))
        return '\n'.join(lines)

    def preview_reverse(self, redo=False, change_id=None):
        if self.current is None: raise ValueError('Open a title first.')
        item = self.app.session.mutation_item(self.current, self.scope)
        history = [r for r in self.store.history(self.current) if r['state'] == ('reverted' if redo else 'active')]
        if not history: raise ValueError('Nothing to redo.' if redo else 'Nothing to undo.')
        row = history[-1] if redo else history[0]
        if change_id and row['id'] != change_id: raise ValueError('Revert newer active changes for this title first.')
        changes = json.loads(row['changes_json'])
        if not redo: changes = [dict(r, before=r['after'], after=r['before']) for r in changes]
        self.pending = dict(database_uuid=self.app.db.database_uuid, working_set_item_uuid=item,
                            reverse=True, redo=redo, work_id=self.current, change_id=row['id'],
                            revision=self.store.state(self.current)['revision'], audit_id=self.store.snapshot(self.current)[1], changes=changes)
        self.log(self.preview_text())

    def apply(self):
        if not self.pending: raise ValueError('Preview changes first.')
        p = self.pending
        item = self.app.session.mutation_item(p['work_id'], self.scope)
        if item != p['working_set_item_uuid']: raise ValueError('Curation scope changed; preview again.')
        if p['database_uuid'] != self.app.db.database_uuid: raise ValueError('Preview belongs to another database.')
        if p.get('supplementary'):
            result=self.app.db.supplementary.apply(p)
        elif p.get('reverse'):
            result = self.store.reverse(p['work_id'], p['redo'], p['change_id'], p['revision'], p['audit_id'], item_uuid=item)
        else: result = self.store.apply(p)
        self.pending = None; self.rows = self.store.rows(self.current)
        self.app.refresh_all()
        if not p.get('supplementary'):self.app.post_curation(item)
        self.log(self.validation_text(result))
        return result

    def execute(self, text):
        self.cancel(); self.messages = []
        commands = parse_batch(text)
        guard = commands.pop(0) if commands[0]['action'] == 'guard' else None
        if not commands: raise ValueError('Guard needs an edit command.')
        wid = None; current = self.current
        for command in commands:
            resolved = title_scope(self.app.db, current, command['title'])
            if wid is not None and resolved != wid: raise ValueError('A batch must target one exact work, edition, and language.')
            wid = resolved; current = resolved
        if wid != self.current:
            self.app.open_curate(wid, self.scope)
        if any(c['action']=='supplement' for c in commands):
            return self.execute_supplement(commands,guard)
        mutations = ('edit', 'evidence', 'record', 'renumber', 'verify', 'verify_work', 'work_edit', 'alias', 'id_edit', 'volume_edit')
        if guard and not any(c['action'] in mutations for c in commands): raise ValueError('A revision guard needs a mutation.')
        if len(commands) > 1:
            changes, selected = self.compile_batch(commands)
            self.selection = selected
            if changes: self.preview(changes, f'Batch: {len(commands)} commands', guard)
            elif commands[-1]['action'] == 'validate': self.log(self.validation_text(self.store.validate(self.current)))
        else:
            command = commands[0]; action = command['action']
            if action in ('select', 'show'):
                self.selection = {r['iid'] for r in scoped_rows(self.rows, command['target'], self.selection)}
                if action == 'show': self.log('\n'.join(f"{r['key']} · {r['effective']} · {r['status']}" for r in self.rows if r['iid'] in self.selection))
            elif action == 'inspect': self.inspect(command)
            elif action in mutations: self.preview(self.command_changes(command), text, guard)
            elif action in ('undo', 'redo'): self.preview_reverse(action == 'redo')
            elif action in ('validate', 'save'):
                result = self.store.validate(self.current)
                self.log(self.validation_text(result))
                if action == 'save' and not result['valid']: raise ValueError('Validation errors must be resolved before continuing.')
            elif action == 'audit':
                result = self.store.validate(self.current)
                if not result['valid']: raise ValueError(self.validation_text(result))
                item = self.app.session.mutation_item(self.current, self.scope)
                self.app.start_audit([item] if item else [self.current])
        self.app.curate.select_iids(self.selection)
        self.log(f'{len(self.selection)} chapter(s) selected.')
        return '\n'.join(self.messages)

    def execute_supplement(self,commands,guard):
        store=self.app.db.supplementary
        if commands[-1]['action']=='validate':commands=commands[:-1]
        if not commands or any(c['action']!='supplement' for c in commands):
            raise ValueError('Supplementary and numeric commands cannot share one batch.')
        reads=('list','inspect','candidates','history')
        if len(commands)==1 and commands[0]['operation'] in reads:
            if guard:raise ValueError('A guard needs a mutation.')
            cmd=commands[0];op=cmd['operation'];key=cmd.get('opaque_id')
            if op=='history':data=store.history(self.current,key)
            elif op=='candidates':data=store.candidates(self.current,key)
            else:
                data=store.for_audit(self.current,current=True)
                if op=='inspect':data=next((r for r in data.get('identities',[]) if r['identity']['opaque_id']==key),None)
                if data is None:raise ValueError('Unknown supplementary identity.')
            self.log(json.dumps(data,ensure_ascii=False,indent=2));return '\n'.join(self.messages)
        item=self.app.session.mutation_item(self.current,self.scope)
        if not guard:raise ValueError('Supplementary mutations require a current guard; use the review form or export fresh context.')
        if len(commands)==1 and commands[0]['operation'] in ('undo','redo'):
            self.pending=store.preview_reverse(self.current,commands[0]['operation']=='redo',item,guard)
        else:
            if any(c['operation'] not in ('bind','membership','reject','withdraw') for c in commands):
                raise ValueError('Only supplementary mutations may share one batch.')
            ops=[dict(c,action=c['operation']) for c in commands]
            self.pending=store.preview(self.current,ops,guard,item)
        self.log(self.preview_text());return '\n'.join(self.messages)
