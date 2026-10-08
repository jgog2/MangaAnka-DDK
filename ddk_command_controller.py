"""Shared existing command compilation/inspection, extracted from the Tk editor.

The host supplies store/current/rows, selection(), app.db and log().
No parser, validation or mutation policy lives in this presentation adapter.
"""
import json
import re
import uuid
from ddk_catalog import VERIFICATIONS, numeric
from ddk_commands import scoped_rows


class CommandLogic:
    def compile_batch(self,commands):
        """Resolve selection and edits in memory; one Catalog preview owns the write."""
        selected=set(self.command_selection())
        staged={}
        existing=self.store.state(self.current)
        fields={(r['entity'],r['record_key'],r['field']):r for r in existing['fields']}
        for index,command in enumerate(commands):
            action=command['action']
            if action=='validate':
                if index!=len(commands)-1:raise ValueError('Validate must be the last batch line.')
                continue
            if action=='select':
                selected={r['iid'] for r in scoped_rows(self.rows,command['target'],selected)}
                continue
            if action=='verify':
                if command['value'] not in VERIFICATIONS:raise ValueError('Invalid verification state.')
                rows=scoped_rows(self.rows,command['target'],selected)
                if not rows:raise ValueError('No matching selected rows for verification.')
                changed=False
                for row in rows:
                    key=row['key']
                    names={field for entity,k,field in staged if entity=='chapter' and k==key}
                    names.update(row['curated'])
                    for field in names:
                        ident=('chapter',key,field)
                        if ident not in staged:
                            item=fields.get(ident)
                            if item:staged[ident]={'entity':'chapter','key':key,'field':field,'value':item['value']}
                        if ident in staged:
                            staged[ident]['verification']=command['value'];changed=True
                if not changed:raise ValueError('No curated or staged fields in selected rows.')
                continue
            if action=='edit':
                rows=scoped_rows(self.rows,command['target'],selected)
                if not rows:raise ValueError('No matching rows for edit command.')
                changes=[{'entity':'chapter','key':r['key'],'field':command['field'],
                          'value':command['value'],'reset':command['reset']} for r in rows]
            elif action=='evidence':
                changes=self.evidence_changes(command,selected)
            elif action in ('record','renumber','verify_work','work_edit','alias','id_edit','volume_edit'):
                changes=self.command_changes(command)
            else:
                raise ValueError('Only selection, edit, and final validate commands may share one atomic batch.')
            for change in changes:
                ident=(change['entity'],str(change['key']),change['field'])
                if ident in staged:
                    if staged[ident]!=change:
                        raise ValueError(f'Contradictory edits to {ident[0]} {ident[1]} {ident[2]} in one batch.')
                    continue
                staged[ident]=change
        return list(staged.values()),selected


    def evidence_changes(self,command,selected):
        rows=scoped_rows(self.rows,command['target'],selected)
        if not rows:raise ValueError('No matching chapter rows for evidence.')
        return [{'entity':'evidence','key':str(uuid.uuid4()),'field':'add','target_key':r['key'],
                 'target_field':'volume','source_name':command['source_name'],
                 'source_url':command['source_url'],'note':command['note'],
                 'accessed_at':command['accessed_at']} for r in rows]


    def command_changes(self, command):
        action=command['action']; state=self.store.state(self.current)
        fields={(r['entity'],r['record_key'],r['field']):r for r in state['fields']}
        def entry(entity,key,field,value=None,reset=False,verification=None):
            row={'entity':entity,'key':key,'field':field,'value':value,'reset':reset}
            if verification: row['verification']=verification
            return row
        if action=='evidence':return self.evidence_changes(command,self.command_selection())
        if action=='edit':
            rows=scoped_rows(self.rows,command['target'],self.command_selection())
            if not rows: raise ValueError('No matching rows in this title.')
            return [entry('chapter',r['key'],command['field'],command['value'],command['reset']) for r in rows]
        if action=='verify':
            if command['value'] not in VERIFICATIONS: raise ValueError('Invalid verification state.')
            rows=scoped_rows(self.rows,command['target'],self.command_selection())
            changes=[entry('chapter',r['key'],field,item['value'],verification=command['value'])
                     for r in rows for field,item in r['curated'].items()]
            if not changes: raise ValueError('No existing curated fields in selection.')
            return changes
        if action=='verify_work':
            if command['value'] not in VERIFICATIONS: raise ValueError('Invalid verification state.')
            changes=[entry('work','work',r['field'],r['value'],verification=command['value'])
                     for r in state['fields'] if r['entity']=='work']
            if not changes: raise ValueError('Set a work field before changing work verification.')
            return changes
        if action=='work_edit':
            field=command['field']; value=command.get('value')
            if field=='edition' and value not in ('standard','official_color','fan_color','omnibus','deluxe','bunkobon','kanzenban'):
                raise ValueError('Use an exact supported edition value.')
            if field=='language' and not re.fullmatch(r'[a-z]{2,3}(?:-[A-Za-z0-9]+)?',value or ''):
                raise ValueError('Use an exact language code.')
            return [entry('work','work',field,value,command.get('reset',False))]
        if action=='alias':
            old=fields.get(('work','work','aliases'))
            values=list(old['value'] if old else [])
            if command['operation']=='add':
                if command['value'] in values: raise ValueError('Alias already curated.')
                values.append(command['value'])
            else:
                if command['value'] not in values: raise ValueError('Alias is not curated.')
                values.remove(command['value'])
            return [entry('work','work','aliases',values)]
        if action=='id_edit':
            source=command['source'].lower()
            if not re.fullmatch(r'[a-z][a-z0-9_-]*',source): raise ValueError('Invalid ID source name.')
            old=fields.get(('work','work','external_ids'))
            automatic,_=self.store.snapshot(self.current)
            default=dict((automatic.get('catalog_identity') or {}).get('external_ids') or {})
            values=dict(old['value'] if old else default)
            if command['operation']=='set':
                value=command['value']
                if source in ('anilist','kitsu') and not re.fullmatch(r'\d+',value): raise ValueError('AniList/Kitsu IDs must be numeric.')
                if source=='mangadex' and not re.fullmatch(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}',value):
                    raise ValueError('MangaDex ID must be a UUID.')
                values[source]=value
            elif command['operation']=='clear': values.pop(source,None)
            else:
                if source in default: values[source]=default[source]
                else: values.pop(source,None)
                if values==default: return [entry('work','work','external_ids',reset=True)]
            return [entry('work','work','external_ids',values)]
        if action=='volume_edit':
            return [entry('volume',numeric(command['key'],'volume'),command['field'],command['value'])]
        if action=='record':
            kind=command['kind'];operation=command['operation'];value=command['value']
            if kind in ('chapter','chapters'):
                if kind=='chapters':
                    pair=re.fullmatch(r'(\d+)-(\d+)',value)
                    if not pair: raise ValueError('Chapter creation/removal range must use integer endpoints.')
                    start,end=map(int,pair.groups())
                    if end<start or end-start>500: raise ValueError('Invalid or excessive chapter range.')
                    keys=[str(n) for n in range(start,end+1)]
                else: keys=[numeric(value,'chapter')]
                result=[]
                for key in keys:
                    if operation=='add': result.append(entry('chapter',key,'exists',True))
                    else:
                        if ('chapter',key,'exists') not in fields: raise ValueError(f'Chapter {key} was not curated-created.')
                        result.extend(entry('chapter',key,f,reset=True) for (e,k,f) in fields if e=='chapter' and k==key and f!='exists')
                        result.append(entry('chapter',key,'exists',reset=True))
                return result
            key=numeric(value,'volume')
            if operation=='add': return [entry('volume',key,'exists',True)]
            if ('volume',key,'exists') not in fields: raise ValueError(f'Volume {key} was not curated-created.')
            result=[entry('volume',key,f,reset=True) for (e,k,f) in fields if e=='volume' and k==key and f!='exists']
            return result+[entry('volume',key,'exists',reset=True)]
        if action=='renumber':
            old=numeric(command['old'],'chapter');new=numeric(command['new'],'chapter')
            if old==new: raise ValueError('Chapter number is unchanged.')
            if any(r['effective'].get('chapter')==new or r['key']==new for r in self.rows):
                raise ValueError('Target chapter identity already exists.')
            row=next((r for r in self.rows if r['effective'].get('chapter')==old),None)
            if not row or row['ambiguous']: raise ValueError('Source chapter identity is absent or ambiguous.')
            if ('chapter',old,'exists') in fields:
                moves=[entry('chapter',new,'exists',True)]
                moves.extend(entry('chapter',new,f,r['value'],verification=r['verification']) for (e,k,f),r in fields.items()
                             if e=='chapter' and k==old and f!='exists')
                moves.extend(entry('chapter',old,f,reset=True) for (e,k,f) in fields if e=='chapter' and k==old and f!='exists')
                return moves+[entry('chapter',old,'exists',reset=True)]
            return [entry('chapter',row['key'],'chapter',new)]
        raise ValueError('Unsupported edit action.')


    def inspect(self, command):
        auto,_=self.store.snapshot(self.current);state=self.store.state(self.current)
        view=command['view'];target=command['target']
        if view in ('aliases','ids','expected'):
            work={r['field']:r for r in state['fields'] if r['entity']=='work'}
            names={'aliases':['aliases'],'ids':['external_ids'],'expected':['expected_chapters','expected_volumes']}[view]
            self.log('\n'.join(f'{name}: {work.get(name,{}).get("value", "(automatic / none)")}' for name in names));return
        if target and target[0]=='work' or not target:
            latest=self.app.db.latest_audit(self.current)
            final=json.loads(latest['publication_json'] or '{}') if latest else {}
            self.log(json.dumps({'identity':state['identity'],'manifest_work':auto.get('manifest',{}).get('work'),
                'curated_work_fields':[r for r in state['fields'] if r['entity']=='work'],
                'effective_catalog':final.get('effective_catalog'),
                'reference_status':{k:v.get('status') for k,v in auto.get('references',{}).items() if isinstance(v,dict)},
                'count_provenance':auto.get('reported_count_provenance'),
                'findings':[r['code'] for r in self.app.db.holes('All') if r['work_id']==self.current]},
                ensure_ascii=False,indent=2));return
        if len(target)!=2 or target[0] not in ('chapter','volume'):
            raise ValueError('Inspect an exact chapter, volume, or work.')
        kind,key=target[0],numeric(target[1],target[0])
        if kind=='chapter':
            rows=[r for r in self.rows if r['key']==key or r['effective'].get('chapter')==key]
            if len(rows)!=1: raise ValueError('Chapter is absent or ambiguous.')
            r=rows[0]
            payload={'chapter':key,'automatic':r['automatic'],'curated':r['curated'],
                     'effective':r['effective'],'status':r['status'],'source':r['source'],
                     'manifest_evidence':next((m for m in auto.get('manifest',{}).get('chapters',()) if m.get('key')==r['key']),None),
                     'reference_status':{k:v.get('status') for k,v in auto.get('references',{}).items() if k in ('mangadex_structure','wikipedia')}}
        else:
            rows=[r for r in self.rows if str(r['effective'].get('volume'))==key]
            edits=[r for r in state['fields'] if r['entity']=='volume' and r['record_key']==key]
            payload={'volume':key,'chapters':[r['key'] for r in rows],
                     'automatic_manifest_volume':next((m for m in auto.get('manifest',{}).get('volumes',()) if m.get('key')==key),None),
                     'curated_fields':edits,'effective_volume':bool(rows or edits)}
        self.log(json.dumps(payload,ensure_ascii=False,indent=2))


    @staticmethod
    def validation_text(result):
        return ('VALID' if result['valid'] else 'INVALID')+'\n'+'\n'.join(result['errors']+result['warnings'])


    @staticmethod
    def ids(value):
        result={}
        for pair in value.split(';'):
            if not pair.strip(): continue
            key,sep,val=pair.strip().partition('=')
            if not sep or not key.strip() or not val.strip(): raise ValueError('IDs use source=value; source=value.')
            if key.strip() in result: raise ValueError('Duplicate external ID source.')
            result[key.strip()]=val.strip()
        return result

