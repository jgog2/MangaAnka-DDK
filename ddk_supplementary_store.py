"""Guarded supplementary decisions; numeric publication remains untouched.

Assertions and events are append-only. Current pointers and the undo stack are
the only mutable decision state. Every write uses the existing DB writer lock.
"""
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import uuid
from urllib.parse import urlsplit

from ddk_catalog import compatible, dumps, stamp
from ddk_supplementary import (Scope, SHA, identity_from_observation,
    publication_supplements, project_supplements, binding_from_assertion,
    membership_from_assertion)


def fingerprint(row):
    """Exact reader/content manifest; never use its number as an identity proof."""
    keys=('id','chapter','url','_source_id','language','edition','page_urls','page_files',
          '_scanlation_id','_canonical_main','_canonical_numeric_special')
    return hashlib.sha256(dumps({k:row.get(k) for k in keys}).encode('utf-8')).hexdigest()


def acquisitions(publication):
    identity=publication.get('catalog_identity') or {}
    labels=(publication.get('normalization') or {}).get('labels') or ()
    result=[]
    for index,original in enumerate(publication.get('projection') or ()):
        row=deepcopy(original)
        row['_source_id']=row.get('_source_id') or row.get('source_id') or row.get('_acquisition_provider') or ''
        # Missing per-row scope inherits the exact audited acquisition context;
        # explicit contrary scope is retained and rejected, never overwritten.
        row.setdefault('language',identity.get('language'))
        row.setdefault('edition',identity.get('edition'))
        label=labels[index] if index<len(labels) else None
        row['_canonical_main']=bool(row.get('_canonical_main') or label=='main')
        row['_canonical_numeric_special']=bool(row.get('_canonical_numeric_special') or label=='recognized_special')
        result.append(row)
    return result


def http_url(value):
    try:
        parsed=urlsplit(str(value))
        return parsed.scheme in ('http','https') and bool(parsed.hostname) and not parsed.username and not parsed.password
    except ValueError:return False


def reviewed(value):
    if not isinstance(value,dict):raise ValueError('Reviewed decision must be an object.')
    if not all(isinstance(value.get(k),str) and value[k].strip() for k in ('reviewer','note')):
        raise ValueError('Explicit reviewer and decision note are required.')


def equivalence(value, identity, row):
    reviewed(value)
    proof=value.get('equivalence') or {}
    if (proof.get('method') not in ('complete_content_review','publisher_identifier') or
            proof.get('complete') is not True or not http_url(proof.get('source_url')) or
            not SHA.fullmatch(str(proof.get('payload_sha256') or '')) or
            not str(proof.get('note') or '').strip()):
        raise ValueError('Exact binding requires independent complete-content or publisher-identifier evidence; titles/OCR/counts alone are insufficient.')
    try:date=datetime.fromisoformat(proof.get('captured_at',''))
    except (TypeError,ValueError):raise ValueError('Equivalence evidence needs a zoned capture timestamp.') from None
    if date.tzinfo is None or date>datetime.now(timezone.utc):raise ValueError('Invalid equivalence capture time.')
    if proof.get('method')=='publisher_identifier' and (
            not identity.publisher_content_id or proof.get('publisher_content_id')!=identity.publisher_content_id):
        raise ValueError('Publisher identifier proof must match the current official story content identifier.')
    if value.get('acquisition_sha256')!=fingerprint(row):raise ValueError('Stale acquisition content/identity fingerprint.')
    if identity.scope.language!=row.get('language') or identity.scope.edition!=row.get('edition'):
        raise ValueError('Acquisition language/edition is incompatible; translation equivalence is not authorized.')


class SupplementaryStore:
    def __init__(self,db):self.db=db

    def revision(self,work_id,con=None):
        if con is None:
            with self.db.con() as c:return self.revision(work_id,c)
        row=con.execute('SELECT revision FROM supplementary_catalog WHERE work_id=?',(work_id,)).fetchone()
        return row[0] if row else 0

    def state(self,work_id,con=None,revision=None):
        if con is None:
            with self.db.con() as c:return self.state(work_id,c,revision)
        current=self.revision(work_id,con)
        if revision is None:
            pointers=[dict(r) for r in con.execute('SELECT * FROM supplementary_current WHERE work_id=? ORDER BY kind,target_key',(work_id,))]
        else:
            if not isinstance(revision,int) or not 0<=revision<=current:raise ValueError('Unknown supplementary revision.')
            effective={}
            for event in con.execute('''SELECT e.action,h.changes_json FROM supplementary_events e
                JOIN supplementary_changes h ON h.id=e.change_id WHERE e.work_id=? AND e.revision<=? ORDER BY e.revision''',(work_id,revision)):
                side='before' if event['action']=='undo' else 'after'
                for op in json.loads(event['changes_json']):
                    key=(op['kind'],op['target_key'])
                    if op[side] is None:effective.pop(key,None)
                    else:effective[key]=dict(work_id=work_id,kind=op['kind'],target_key=op['target_key'],assertion_uuid=op[side])
            pointers=list(effective.values())
        decisions=[]
        for pointer in pointers:
            row=dict(con.execute('SELECT * FROM supplementary_assertions WHERE assertion_uuid=? AND work_id=?',
                                 (pointer['assertion_uuid'],work_id)).fetchone())
            row['payload']=json.loads(row.pop('payload_json'));decisions.append(row)
        return dict(revision=current if revision is None else revision,pointers=pointers,decisions=decisions)

    def guard(self,work_id,item_uuid=None,con=None):
        if con is None:
            with self.db.con() as c:
                c.execute('BEGIN')
                return self.guard(work_id,item_uuid,c)
        from ddk_review import database_revision, audit_revision
        work=self.db.work(work_id,con=con);audit=self.db.latest_audit(work_id,con=con)
        if not work or not audit:raise ValueError('Open an audited canonical work first.')
        pub=json.loads(audit['publication_json'] or '{}');identity=pub.get('catalog_identity') or {}
        if (not identity.get('trusted') or identity.get('canonical_work_id')!=work['canonical_work_id'] or
                identity.get('edition')!=work['edition'] or identity.get('language')!=work['language']):
            raise ValueError('Exact trusted work/edition/language identity is required.')
        if pub.get('curation_revision',(pub.get('curated_database') or {}).get('revision',0))!=self.db.catalog.state(work_id,con)['revision']:
            raise ValueError('Stale numeric curation snapshot; re-audit before supplementary review.')
        item=None
        if item_uuid:
            item=self.db.working_sets.editable_item(item_uuid,work_id,con=con)
            if item['pinned_audit_id']!=audit['id'] or item['pinned_audit_revision']!=audit_revision(self.db,audit,con):
                raise ValueError('Selected Working Set pin is stale; re-audit or advance it first.')
        return dict(database_uuid=con.execute('SELECT database_uuid FROM database_meta WHERE singleton=1').fetchone()[0],
            work_id=work_id,work_uuid=work['work_uuid'],identity=identity,
            audit_id=audit['id'],audit_revision=audit_revision(self.db,audit,con),
            database_revision=database_revision(self.db,con),supplementary_revision=self.revision(work_id,con),
            curation_revision=self.db.catalog.state(work_id,con)['revision'],
            working_set_item_uuid=item_uuid,membership=dict(item) if item else None)

    def history(self,work_id,opaque_id=None,con=None):
        if con is None:
            with self.db.con() as c:return self.history(work_id,opaque_id,c)
        rows=[]
        for row in con.execute('''SELECT e.*,h.operation,h.state,h.changes_json FROM supplementary_events e
            JOIN supplementary_changes h ON h.id=e.change_id WHERE e.work_id=? ORDER BY e.revision''',(work_id,)):
            value=dict(row);ops=json.loads(value['changes_json'])
            if opaque_id and not any(op.get('opaque_id')==opaque_id for op in ops):continue
            value['changes']=ops;rows.append(value)
        return rows

    def _publication(self,work_id,con=None):
        audit=self.db.latest_audit(work_id,con=con)
        if not audit:raise ValueError('No audited publication.')
        return json.loads(audit['publication_json'] or '{}')

    @staticmethod
    def _saved_identity(con,work_id,opaque_id):
        row=con.execute('SELECT identity_json FROM supplementary_identities WHERE work_id=? AND opaque_id=?',(work_id,opaque_id)).fetchone()
        if not row:raise ValueError('Saved supplementary identity is missing.')
        raw=json.loads(row[0])
        ident=identity_from_observation({**raw,**raw['provenance']},Scope(**raw['scope']))
        if ident.opaque_id!=opaque_id:raise ValueError('Saved supplementary identity hash mismatch.')
        return ident

    def candidates(self,work_id,opaque_id):
        pub=self._publication(work_id)
        try:self._identity(pub,opaque_id)
        except ValueError:
            # Inspection/recovery may use historical identity evidence; positive
            # binding validation still requires current official evidence.
            with self.db.con() as c:self._saved_identity(c,work_id,opaque_id)
        return [dict(provider=r['_source_id'],record_id=str(r.get('id') or ''),original_label=str(r.get('chapter','')),
            url=r.get('url'),language=r.get('language'),edition=r.get('edition'),acquisition_sha256=fingerprint(r),
            contrary_numeric_identity=bool(r['_canonical_main'] or r['_canonical_numeric_special']),raw=r)
            for r in acquisitions(pub)]

    @staticmethod
    def _identity(publication,opaque_id):
        projection=publication_supplements(publication)
        matches=[r for r in projection['identities'] if r['identity']['opaque_id']==opaque_id]
        if len(matches)!=1 or matches[0]['acquisition_state']=='conflict':raise ValueError('Supplementary identity is absent or ambiguous in current official evidence.')
        raw=matches[0]['identity']
        return identity_from_observation({**raw,**raw['provenance']},Scope(**raw['scope']))

    def _validate(self,publication,kind,payload,identity,context):
        reviewed(payload)
        if kind=='binding':
            rows=acquisitions(publication)
            scope=Scope(context['identity']['canonical_work_id'],context['identity']['edition'],context['identity']['language'])
            binding=binding_from_assertion(payload,identity,rows,scope,{k:context[k] for k in ('database_uuid','audit_id','audit_revision','database_revision')})
            equivalence(payload,identity,binding.acquisition)
            return 'reader:'+dumps([binding.provider,binding.record_id])
        if kind!='membership':raise ValueError('Unknown supplementary assertion kind.')
        if payload.get('verification')!='VERIFIED':raise ValueError('Membership requires explicit VERIFIED review.')
        membership_from_assertion(payload,identity)
        return 'collection:'+identity.opaque_id

    def preview(self,work_id,operations,guard,item_uuid=None,operation='Supplementary review'):
        with self.db.con() as c:
            c.execute('BEGIN')
            context=self.guard(work_id,item_uuid,c)
            if not guard or any(guard.get(k)!=context[k] for k in ('database_uuid','audit_id','audit_revision','database_revision')):
                raise ValueError('Stale or missing supplementary review guard; export fresh context.')
            pub=self._publication(work_id,c);state=self.state(work_id,c)
            current={(r['kind'],r['target_key']):r for r in state['decisions']}
            changes=[];assertions=[];identities={}
            for op in operations:
                action=op['action']
                if action in ('bind','membership'):
                    ident=self._identity(pub,op['opaque_id']);kind='binding' if action=='bind' else 'membership'
                    payload=deepcopy(op['payload'])
                    target=self._validate(pub,kind,payload,ident,context)
                    prior=current.get((kind,target))
                    if prior and prior['decision']=='VERIFIED':
                        if prior['opaque_id']!=ident.opaque_id:raise ValueError('Conflicting simultaneous reader binding; withdraw it explicitly first.')
                        if prior['payload']==payload:raise ValueError('No changes to apply.')
                    decision='VERIFIED';identities[ident.opaque_id]=asdict(ident)
                elif action in ('reject','withdraw'):
                    prior=next((r for r in state['decisions'] if r['assertion_uuid']==op['assertion_uuid']),None)
                    if not prior:raise ValueError('Only an exact current assertion can be rejected/withdrawn.')
                    payload=deepcopy(prior['payload']);reviewed(op)
                    payload.update(reviewer=op['reviewer'],note=op['note'])
                    kind=prior['kind'];target=prior['target_key'];ident=self._saved_identity(c,work_id,prior['opaque_id'])
                    decision='REJECTED' if action=='reject' else 'WITHDRAWN'
                else:raise ValueError('Unknown supplementary operation.')
                if any(r['kind']==kind and r['target_key']==target for r in changes):raise ValueError('Duplicate/contradictory supplementary target in one batch.')
                aid=str(uuid.uuid4())
                assertions.append(dict(assertion_uuid=aid,opaque_id=ident.opaque_id,kind=kind,target_key=target,decision=decision,payload=payload))
                changes.append(dict(kind=kind,target_key=target,opaque_id=ident.opaque_id,
                    before=prior['assertion_uuid'] if prior else None,after=aid))
            if not changes:raise ValueError('No supplementary mutations.')
            return dict(supplementary=True,database_uuid=context['database_uuid'],work_id=work_id,
                working_set_item_uuid=item_uuid,audit_id=context['audit_id'],revision=context['supplementary_revision'],
                context=context,changes=changes,assertions=assertions,identities=identities,operation=operation)

    def preview_reverse(self,work_id,redo=False,item_uuid=None,guard=None):
        with self.db.con() as c:
            c.execute('BEGIN');context=self.guard(work_id,item_uuid,c)
            if guard and any(guard.get(k)!=context[k] for k in ('database_uuid','audit_id','audit_revision','database_revision')):
                raise ValueError('Stale supplementary undo/redo guard.')
            row=c.execute('SELECT * FROM supplementary_changes WHERE work_id=? AND state=? ORDER BY id '+
                ('ASC' if redo else 'DESC')+' LIMIT 1',(work_id,'reverted' if redo else 'active')).fetchone()
            if not row:raise ValueError('Nothing to redo.' if redo else 'Nothing to undo.')
            return dict(supplementary=True,reverse=True,redo=redo,change_id=row['id'],work_id=work_id,
                database_uuid=context['database_uuid'],working_set_item_uuid=item_uuid,audit_id=context['audit_id'],
                revision=context['supplementary_revision'],context=context,changes=json.loads(row['changes_json']),operation='redo' if redo else 'undo')

    def _check_reverse(self,c,preview,context):
        row=c.execute('SELECT * FROM supplementary_changes WHERE id=? AND work_id=?',(preview['change_id'],preview['work_id'])).fetchone()
        redo=preview['redo'];expected='reverted' if redo else 'active'
        first=c.execute('SELECT id FROM supplementary_changes WHERE work_id=? AND state=? ORDER BY id '+
            ('ASC' if redo else 'DESC')+' LIMIT 1',(preview['work_id'],expected)).fetchone()
        if not row or row['state']!=expected or not first or first[0]!=row['id']:raise ValueError('Stale supplementary undo/redo stack.')
        if json.loads(row['changes_json'])!=preview['changes']:raise ValueError('History preview was modified.')
        # Redo can restore a positive decision only while its authority is current.
        if redo:
            pub=self._publication(preview['work_id'],c)
            for op in preview['changes']:
                assertion=c.execute('SELECT * FROM supplementary_assertions WHERE assertion_uuid=?',(op['after'],)).fetchone()
                if assertion['decision']=='VERIFIED':
                    payload=json.loads(assertion['payload_json']);ident=self._identity(pub,assertion['opaque_id'])
                    self._revalidate(pub,assertion['kind'],payload,ident,context)
        return row

    @staticmethod
    def _pointer(c,work_id,op,side):
        c.execute('DELETE FROM supplementary_current WHERE work_id=? AND kind=? AND target_key=?',(work_id,op['kind'],op['target_key']))
        if op[side]:c.execute('INSERT INTO supplementary_current VALUES(?,?,?,?)',(work_id,op['kind'],op['target_key'],op[side]))

    def apply(self,preview):
        # Rebuild previews under the current read snapshot; reject tampered plans.
        wid=preview['work_id']
        with self.db.lock:
            self.db.catalog._backup()
            with self.db.con() as c:
                c.execute('BEGIN IMMEDIATE');context=self.guard(wid,preview.get('working_set_item_uuid'),c)
                if context!=preview['context']:raise ValueError('Stale supplementary preview: database, membership, audit or revision changed.')
                revision=context['supplementary_revision']+1;now=stamp()
                if preview.get('reverse'):
                    change=self._check_reverse(c,preview,context)
                    expected,side=('before','after') if preview['redo'] else ('after','before')
                    for op in preview['changes']:
                        current=c.execute('SELECT assertion_uuid FROM supplementary_current WHERE work_id=? AND kind=? AND target_key=?',(wid,op['kind'],op['target_key'])).fetchone()
                        if (current[0] if current else None)!=op[expected]:raise ValueError('Supplementary journal/current-state conflict.')
                    for op in preview['changes']:self._pointer(c,wid,op,side)
                    c.execute('UPDATE supplementary_changes SET state=? WHERE id=?',('active' if preview['redo'] else 'reverted',change['id']))
                    change_id=change['id'];action='redo' if preview['redo'] else 'undo'
                else:
                    pub=self._publication(wid,c)
                    if len(preview['changes'])!=len(preview['assertions']):raise ValueError('Invalid supplementary preview plan.')
                    for op,assertion in zip(preview['changes'],preview['assertions']):
                        prior=c.execute('SELECT assertion_uuid FROM supplementary_current WHERE work_id=? AND kind=? AND target_key=?',(wid,op['kind'],op['target_key'])).fetchone()
                        if (prior[0] if prior else None)!=op['before']:raise ValueError('Stale supplementary target.')
                        ident=(self._identity(pub,assertion['opaque_id']) if assertion['decision']=='VERIFIED' else
                               self._saved_identity(c,wid,assertion['opaque_id']))
                        if (op['after']!=assertion['assertion_uuid'] or op['kind']!=assertion['kind'] or
                                op['target_key']!=assertion['target_key'] or op['opaque_id']!=ident.opaque_id):raise ValueError('Invalid supplementary target plan.')
                        if assertion['decision']=='VERIFIED':
                            target=self._validate(pub,assertion['kind'],assertion['payload'],ident,context)
                            if target!=op['target_key']:raise ValueError('Invalid supplementary target key.')
                            if prior:
                                old=c.execute('SELECT opaque_id,decision FROM supplementary_assertions WHERE assertion_uuid=?',(prior[0],)).fetchone()
                                if old['decision']=='VERIFIED' and old['opaque_id']!=ident.opaque_id:raise ValueError('Conflicting reader binding.')
                        elif assertion['decision'] in ('REJECTED','WITHDRAWN'):
                            reviewed(assertion['payload'])
                            if not prior:raise ValueError('Cannot reject/withdraw an absent decision.')
                            old=c.execute('SELECT * FROM supplementary_assertions WHERE assertion_uuid=?',(prior[0],)).fetchone()
                            if old['opaque_id']!=ident.opaque_id or old['kind']!=assertion['kind']:raise ValueError('Decision target mismatch.')
                        else:raise ValueError('Unknown decision state.')
                        c.execute('INSERT OR IGNORE INTO supplementary_identities VALUES(?,?,?,?,?)',(wid,ident.opaque_id,dumps(asdict(ident)),context['audit_id'],now))
                        c.execute('INSERT INTO supplementary_assertions VALUES(?,?,?,?,?,?,?,?,?)',
                            (assertion['assertion_uuid'],wid,ident.opaque_id,assertion['kind'],assertion['target_key'],assertion['decision'],dumps(assertion['payload']),context['audit_id'],now))
                    for op in preview['changes']:self._pointer(c,wid,op,'after')
                    c.execute("UPDATE supplementary_changes SET state='superseded' WHERE work_id=? AND state='reverted'",(wid,))
                    change_id=c.execute('INSERT INTO supplementary_changes(work_id,operation,changes_json,guard_json,state,created_at) VALUES(?,?,?,?,?,?)',
                        (wid,preview['operation'],dumps(preview['changes']),dumps(context),'active',now)).lastrowid
                    action='apply'
                c.execute('INSERT INTO supplementary_catalog VALUES(?,?) ON CONFLICT(work_id) DO UPDATE SET revision=excluded.revision',(wid,revision))
                c.execute('INSERT INTO supplementary_events(work_id,change_id,action,revision,guard_json,created_at) VALUES(?,?,?,?,?,?)',(wid,change_id,action,revision,dumps(context),now))
                if c.execute('PRAGMA foreign_key_check').fetchone():raise ValueError('Supplementary integrity failure; transaction rolled back.')
        self.db.acceptance.recalculate(wid)
        return dict(valid=True,errors=[],warnings=['Supplementary decision saved; re-audit required. Numeric projection unchanged.'],
                    supplementary_revision=revision,changes=len(preview['changes']))

    def _revalidate(self,pub,kind,payload,ident,context):
        value=deepcopy(payload)
        if kind=='binding':
            if value.get('publication_sha256')!=ident.provenance.payload_sha256:
                raise ValueError('Stale publisher payload fingerprint; review current evidence again.')
            value['review_guard']={k:context[k] for k in ('database_uuid','audit_id','audit_revision','database_revision')}
            value['captured_at']=ident.provenance.captured_at
        elif (value.get('provenance') or {}).get('payload_sha256')==ident.provenance.payload_sha256:
            value['provenance']=asdict(ident.provenance)
        self._validate(pub,kind,value,ident,context)
        return value

    def resolve(self,publication,work_id,con=None,revision=None):
        if con is None:
            with self.db.con() as c:
                c.execute('BEGIN')
                return self.resolve(publication,work_id,c,revision)
        base=publication_supplements(publication);state=self.state(work_id,con,revision)
        catalog=publication.get('catalog_identity') or {}
        if not catalog.get('trusted') or not all(catalog.get(k) for k in ('canonical_work_id','edition','language')):
            base['reviewed_state']=dict(revision=state['revision'],decisions=[dict(r,effective_state='conflicting',
                reason='Current canonical identity is not trusted.') for r in state['decisions']])
            base['reviewed_binding_persistence']='schema_8_grammar_4'
            return base
        scope=Scope(catalog['canonical_work_id'],catalog['edition'],catalog['language'])
        identities=[];memberships=[];bindings=[];decisions=[]
        context=dict(identity=catalog,database_uuid=con.execute('SELECT database_uuid FROM database_meta WHERE singleton=1').fetchone()[0],
            audit_id=0,audit_revision=0,database_revision='revalidation')
        for row in base['identities']:
            for raw in row['observations']:
                identities.append(identity_from_observation({**raw,**raw['provenance']},Scope(**raw['scope'])))
            memberships.extend(row['memberships'])
        present={ident.opaque_id for ident in identities}
        for saved in state['decisions']:
            if saved['opaque_id'] not in present:
                identities.append(self._saved_identity(con,work_id,saved['opaque_id']))
                present.add(saved['opaque_id'])
        for saved in state['decisions']:
            decision=deepcopy(saved);decision['effective_state']=saved['decision'].lower()
            if saved['decision']=='VERIFIED':
                try:
                    saved_scope=saved['payload'].get('scope') or {}
                    if saved_scope.get('work')!=scope.work or saved_scope.get('edition')!=scope.edition:
                        raise ValueError('Current work or edition contradicts saved decision scope.')
                    ident=self._identity(publication,saved['opaque_id'])
                    payload=self._revalidate(publication,saved['kind'],saved['payload'],ident,context)
                    if saved['kind']=='binding':bindings.append(payload)
                    else:
                        memberships=[r for r in memberships if r['supplement_id']!=ident.opaque_id]
                        memberships.append(payload)
                    decision['effective_state']='verified'
                except (ValueError,TypeError,KeyError) as exc:
                    text=str(exc)
                    decision['effective_state']=('unavailable' if 'absent' in text else 'stale' if 'Stale' in text or 'fingerprint' in text else 'conflicting')
                    decision['reason']=text
            decisions.append(decision)
        result=project_supplements(identities,acquisitions(publication),bindings,memberships,scope,
            {k:context[k] for k in ('database_uuid','audit_id','audit_revision','database_revision')})
        result['diagnostics'].extend(base['diagnostics'])
        for row in result['identities']:
            relevant=[r for r in decisions if r['opaque_id']==row['identity']['opaque_id']]
            row['reviewed_decisions']=relevant
            for kind,field in (('binding','acquisition_state'),('membership','membership_state')):
                active=[r for r in relevant if r['kind']==kind]
                states={r['effective_state'] for r in active}
                if 'verified' not in states and states:
                    row[field]=next((s for s in ('conflicting','stale','unavailable','rejected','withdrawn') if s in states),row[field])
        result['reviewed_binding_persistence']='schema_8_grammar_4'
        result['reviewed_state']=dict(revision=state['revision'],decisions=decisions)
        result['summary']['verified_acquired']=sum(r['acquisition_state']=='verified' for r in result['identities'])
        result['summary']['unresolved_acquisition']=sum(r['acquisition_state']!='verified' for r in result['identities'])
        result['summary']['standard_volume_memberships']=sum(r['membership_state']=='standard_volume' and r['applicability']=='compatible' for r in result['identities'])
        result['summary']['separate_publication_memberships']=sum(r['membership_state'] in ('separate_publication','standalone','related_work') for r in result['identities'])
        result['summary']['unresolved_membership']=sum(r['membership_state'] in ('unresolved','conflict','conflicting','stale','unavailable','rejected','withdrawn') for r in result['identities'])
        return result

    def for_audit(self,work_id,audit=None,current=False):
        audit=audit if audit is not None else self.db.latest_audit(work_id)
        if not audit:return {}
        publication=json.loads(audit['publication_json'] or '{}')
        return self.resolve(publication,work_id,revision=None if current else publication.get('supplementary_revision',0))
