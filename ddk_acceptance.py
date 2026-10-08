"""One policy for exact catalog acceptance, eligibility and membership readiness."""
from contextlib import nullcontext
import hashlib
import json

from ddk_catalog import compatible
from ddk_review import problem_policy, issue_signature
from ddk_working_sets import stamp


def unpack(value):
    return json.loads(value or '{}')


class Acceptance:
    def __init__(self, db):
        self.db = db

    def evaluate(self, work_id, item_uuid=None, audit_id=None, con=None):
        if con is None:
            with self.db.con() as c:
                return self.evaluate(work_id, item_uuid, audit_id, c)
        blockers = []; warnings = []
        work = con.execute('SELECT * FROM works WHERE id=?', (work_id,)).fetchone()
        item = None
        latest = con.execute('SELECT * FROM search_audits WHERE work_id=? ORDER BY id DESC LIMIT 1', (work_id,)).fetchone()
        if item_uuid:
            item = self.db.working_sets.item(item_uuid, con=con)
            if not item or item['removed_at'] or not work or item['linked_work_uuid'] != work['work_uuid']:
                blockers.append('Working Set item does not own this exact catalog work.')
            else:
                try: self.db.working_sets.guard(item_uuid=item_uuid, con=con)
                except ValueError as exc: blockers.append(str(exc))
                if item['processing_status'] in ('PENDING','ERROR', 'QUEUED', 'AUDITING', 'REJECTED', 'DUPLICATE'):
                    blockers.append('Item must finish review/auditing before acceptance.')
            audit_id = item['pinned_audit_id'] if item else None
        audit = con.execute('SELECT * FROM search_audits WHERE id=? AND work_id=?',
                            (audit_id, work_id)).fetchone() if audit_id else (None if item_uuid else latest)
        current_pin = bool(audit and latest and audit['id'] == latest['id'])
        if not work: blockers.append('Catalog work is missing.')
        if not audit: blockers.append('No valid audited publication snapshot.')
        if audit and not current_pin: blockers.append('Pinned audit is superseded by a newer global audit.')
        state = self.db.catalog.state(work_id, con)
        pub = unpack(audit['publication_json']) if audit else {}
        identity = pub.get('catalog_identity') or {}
        dispositions = []; triaged_acquisition=False
        needs_reaudit=bool(not audit or not current_pin)
        if audit and work:
            if not identity.get('trusted') or not identity.get('canonical_work_id') or not (pub.get('context') or {}).get('shareable'):
                blockers.append('Identity/publication context is not trusted and shareable.')
            for field in ('edition', 'language'):
                expected = item['requested_' + field] if item else work[field]
                if identity.get(field) != expected or work[field] != expected:
                    blockers.append(f'Exact {field} identity does not match the requested catalog row.')
            if work['canonical_work_id'] != identity.get('canonical_work_id'):
                blockers.append('Trusted canonical claim differs from the catalog work.')
            if pub.get('edition') != work['edition']:
                blockers.append('Resolved publication edition differs from the catalog edition.')
            if item and (item['pinned_audit_revision'] != audit['audit_revision'] or
                         item['requested_workflow'] != audit['workflow']):
                blockers.append('Pinned revision/workflow does not match the item snapshot.')
            if pub.get('curation_revision', (pub.get('curated_database') or {}).get('revision', 0)) != state['revision']:
                blockers.append('Audit is stale after curation; a fresh audit is required.')
                needs_reaudit=True
            if state['identity'] and not compatible(state['identity'], identity)[0]:
                blockers.append('Curated identity is incompatible with this audit.')
            patch = pub.get('curated_database') or {}
            relation = self.db.catalog.audit_guard(work_id, con=con)
            used_dependencies=pub.get('catalog_dependencies')
            if pub.get('supplementary_revision',0)!=relation.get('supplementary_revision',0):
                blockers.append('Supplementary review changed; a fresh audit is required.')
                needs_reaudit=True
            if used_dependencies and any(used_dependencies.get(key)!=relation.get(key)
                                         for key in ('revision','curated_identity','sources')):
                blockers.append('Effective curation/structure dependencies changed; audit again.')
                needs_reaudit=True
            if patch.get('structure_shared'):
                if (not relation['sources'] or patch.get('revision') != relation['sources'][0]['revision'] or
                        relation['sources'][0]['canonical_work_id'] != work['canonical_work_id']):
                    blockers.append('Shared structure evidence changed; audit again.')
                    needs_reaudit=True
            elif relation['sources']:
                blockers.append('Shared structure relationship was not resolved in this audit.')
                needs_reaudit=True
            if pub.get('status') != 'complete' or not (pub.get('final_volumes') or 0) or not (
                    (pub.get('logical_chapters') or 0) > 0 or (pub.get('volume_only_units') or 0) > 0):
                blockers.append('Publication is empty, incomplete, or has no usable volume structure.')
            if pub.get('unmapped_chapters') or pub.get('unmapped'):
                blockers.append('Canonical publication chapters remain unmapped.')
            from ddk_publication_states import verified_uncompiled_identifiers
            safe_uncompiled = verified_uncompiled_identifiers(pub)
            if pub.get('uncompiled_chapters',0) != len(safe_uncompiled):
                blockers.append('Uncompiled publication evidence is incomplete or inconsistent.')
            if pub.get('logical_chapters',0)>0 and (pub.get('mapped_chapters',0) +
                    len(safe_uncompiled)) != pub.get('logical_chapters'):
                blockers.append('Logical publication coverage is not completely mapped.')
            if pub.get('conflicting_chapters'):
                blockers.append('Publication structure has unresolved conflicts.')
            if audit['final_state'] == 'ERROR' or audit['run_status'] == 'Failed':
                blockers.append('Audit contains a fatal execution/publication failure.')
            validation = self.db.catalog.validate(work_id, state, audit=audit, con=con)
            blockers.extend(validation['errors'])
            if validation['unmapped'] or validation['conflicts']:
                blockers.append('Effective catalog curation has unmapped/conflicting publication rows.')
            for hole in con.execute('SELECT * FROM audit_holes WHERE audit_id=?', (audit['id'],)):
                disposition = con.execute('''SELECT * FROM problem_dispositions WHERE problem_row_id=?
                    ORDER BY id DESC LIMIT 1''', (hole['id'],)).fetchone()
                if disposition: dispositions.append(disposition['id'])
                triaged = bool(disposition and hole['code'] == 'UNCLASSIFIED_ACQUISITION' and
                    disposition['status'] == 'IGNORED_WITH_REASON' and
                    disposition['verification'] in ('REVIEWED', 'VERIFIED') and disposition['reason'].strip() and
                    disposition['signature'] == issue_signature(hole, pub))
                if triaged:
                    triaged_acquisition=True
                    continue
                cls, action, _, _ = problem_policy(hole['code'], unpack(hole['details_json']))
                cls = hole['problem_class'] or cls
                action = hole['next_action'] or action
                if cls in ('IDENTITY', 'DATA', 'RESEARCH', 'UNKNOWN', 'CODE') or action in (
                        'RESEARCH_REQUIRED', 'CODE_REVIEW_REQUIRED', 'BLOCKED_IDENTITY'):
                    blockers.append(f'{hole["code"]}: {hole["message"]}')
                elif hole['severity'] == 'error' and hole['code'] in ('SOURCE_FAILURE', 'AUDIT_ERROR', 'NO_USABLE_PROVIDER'):
                    blockers.append(f'{hole["code"]}: {hole["message"]}')
                else: warnings.append(f'{hole["code"]}: {hole["message"]}')
            raw_unclassified=bool(pub.get('unclassified_acquisition') or any(label in ('unclassified','provisional')
                for label in (pub.get('normalization') or {}).get('labels') or ()))
            if raw_unclassified and not triaged_acquisition:
                blockers.append('Unclassified acquisition requires a valid human disposition.')
            health = unpack(audit['health_json'])
            if health.get('normalization') == 'REVIEW': warnings.append('Normalization remains REVIEW; unresolved problems determine eligibility.')
            if health.get('acquisition') == 'PARTIAL': warnings.append('Acquisition is PARTIAL; publication eligibility is evaluated separately.')
        fingerprint = hashlib.sha256(json.dumps({
            'work_uuid': work['work_uuid'] if work else None, 'audit_id': audit['id'] if audit else None,
            'audit_revision': audit['audit_revision'] if audit else None, 'curation_revision': state['revision'],
            'identity': identity, 'catalog_guard': self.db.catalog.audit_guard(work_id, con=con),
            'dispositions': dispositions}, sort_keys=True, default=str).encode()).hexdigest()
        return {'eligible': not blockers, 'blockers': list(dict.fromkeys(blockers)),
                'warnings': list(dict.fromkeys(warnings)), 'audit_id': audit['id'] if audit else None,
                'audit_revision': audit['audit_revision'] if audit else None,
                'curation_revision': state['revision'], 'work_uuid': work['work_uuid'] if work else None,
                'working_set_item_uuid': item_uuid, 'pin_current': current_pin,
                'fingerprint': fingerprint,'needs_reaudit':needs_reaudit}

    def state(self, work_id, con=None):
        if con is None:
            with self.db.con() as c: return self.state(work_id, c)
        work = con.execute('SELECT * FROM works WHERE id=?', (work_id,)).fetchone()
        if not work: return 'NONE'
        accepted = con.execute('SELECT * FROM catalog_acceptances WHERE work_uuid=? ORDER BY id DESC LIMIT 1',
                               (work['work_uuid'],)).fetchone()
        if not accepted:
            return 'LEGACY_REVIEW_REQUIRED' if work['lifecycle_status'] == 'ACCEPTED' else 'NONE'
        if accepted['decision'] == 'REVOKE': return 'REVOKED'
        evaluated = self.evaluate(work_id, con=con)
        return 'CURRENT' if (evaluated['eligible'] and evaluated['audit_id'] == accepted['audit_id'] and
            evaluated['audit_revision'] == accepted['audit_revision'] and
            evaluated['curation_revision'] == accepted['curation_revision'] and
            evaluated['fingerprint'] == accepted['state_fingerprint']) else 'STALE'

    def recalculate(self, work_id=None, con=None):
        with self.db.lock, (self.db.con() if con is None else nullcontext(con)) as c:
            sql = '''SELECT i.working_set_item_uuid,w.id work_id FROM working_set_items i
                JOIN working_sets s ON s.working_set_uuid=i.working_set_uuid
                JOIN works w ON w.work_uuid=i.linked_work_uuid
                WHERE i.removed_at IS NULL AND s.status IN ('OPEN','REVIEW')
                AND i.processing_status IN ('AUDITED','READY','REVIEW')'''
            rows = c.execute(sql + (''' AND (w.id=? OR w.work_uuid IN
                (SELECT target_work_uuid FROM edition_structure_relationships WHERE source_work_uuid=
                (SELECT work_uuid FROM works WHERE id=?)))''' if work_id is not None else ''),
                             (work_id,work_id) if work_id is not None else ()).fetchall()
            for row in rows:
                result = self.evaluate(row['work_id'], row['working_set_item_uuid'], con=c)
                c.execute('UPDATE working_set_items SET processing_status=? WHERE working_set_item_uuid=?',
                          ('READY' if result['eligible'] else 'REVIEW', row['working_set_item_uuid']))

    def _record(self, c, work_id, result, item=None):
        work = c.execute('SELECT * FROM works WHERE id=?', (work_id,)).fetchone()
        prior = c.execute('SELECT * FROM catalog_acceptances WHERE work_uuid=? ORDER BY id DESC LIMIT 1',
                          (work['work_uuid'],)).fetchone()
        # A second membership can approve the identical globally approved state.
        same = bool(prior and prior['decision'] == 'ACCEPT' and prior['state_fingerprint'] == result['fingerprint'])
        if not same:
            c.execute('''INSERT INTO catalog_acceptances(work_uuid,decision,audit_id,audit_revision,
                curation_revision,state_fingerprint,accepted_at,working_set_uuid,working_set_item_uuid)
                VALUES(?,?,?,?,?,?,?,?,?)''', (work['work_uuid'], 'ACCEPT', result['audit_id'], result['audit_revision'],
                result['curation_revision'], result['fingerprint'], stamp(),
                item['working_set_uuid'] if item else None, item['working_set_item_uuid'] if item else None))
        c.execute("UPDATE works SET lifecycle_status='ACCEPTED',updated_at=? WHERE work_uuid=?", (stamp(), work['work_uuid']))
        if item:
            c.execute("UPDATE working_set_items SET processing_status='ACCEPTED',updated_at=? WHERE working_set_item_uuid=?",
                      (stamp(), item['working_set_item_uuid']))
        self.db.working_sets.event(c, 'ACCEPT_MEMBERSHIP' if same and item else 'REACCEPT' if prior else 'ACCEPT',
                                  dict(result, working_set_uuid=item['working_set_uuid'] if item else None))

    def accept(self, item_uuids=(), work_ids=(), expected=None, bulk=False):
        targets = [('item', i) for i in dict.fromkeys(item_uuids)] + [('work', int(i)) for i in dict.fromkeys(work_ids)]
        if not targets: raise ValueError('Select exact catalog works or Working Set items.')
        with self.db.lock:
            self.db.catalog._backup()
            with self.db.con() as c:
                c.execute('BEGIN IMMEDIATE')
                safe = []; skipped = []
                for kind, key in targets:
                    item = self.db.working_sets.guard(item_uuid=key, con=c) if kind == 'item' else None
                    work_id = item['work_id'] if item else key
                    result = self.evaluate(work_id, key if item else None, con=c)
                    if expected is not None and expected.get(str(key)) != result['fingerprint']:
                        result['eligible'] = False; result['blockers'].append('Acceptance preview is stale.')
                    if not result['eligible']:
                        if not bulk: raise ValueError('\n'.join(result['blockers']))
                        if item and item['processing_status'] == 'READY':
                            c.execute("UPDATE working_set_items SET processing_status='REVIEW' WHERE working_set_item_uuid=?", (key,))
                        skipped.append(result); continue
                    safe.append((work_id, result, item))
                for work_id, result, item in safe: self._record(c, work_id, result, item)
                if bulk: self.db.working_sets.event(c, 'ACCEPT_ALL_SAFE', {'accepted': len(safe), 'skipped': len(skipped),
                    'working_set_uuids':sorted({self.db.working_sets.item(i,con=c)['working_set_uuid'] for i in item_uuids})})
                if c.execute('PRAGMA foreign_key_check').fetchone(): raise ValueError('Acceptance failed foreign-key validation.')
                return {'accepted': [r[1] for r in safe], 'skipped': skipped}

    def bulk_preview(self, set_uuid):
        self.db.working_sets.guard(set_uuid=set_uuid)
        candidates = {}; stale = 0
        items = self.db.working_sets.items(set_uuid)
        for item in items:
            if item['processing_status'] != 'READY': continue
            result = self.evaluate(item['work_id'], item['working_set_item_uuid'])
            if result['eligible']: candidates[item['working_set_item_uuid']] = result['fingerprint']
            else: stale += 1
        return {'candidates': candidates, 'ready_items':[i['working_set_item_uuid'] for i in items if i['processing_status']=='READY'], 'stale': stale,
                'review': sum(i['processing_status'] == 'REVIEW' for i in items),
                'error': sum(i['processing_status'] == 'ERROR' for i in items)}

    def revoke(self, work_id, reason):
        if not str(reason or '').strip(): raise ValueError('Explain the acceptance revocation.')
        with self.db.lock:
            self.db.catalog._backup()
            with self.db.con() as c:
                c.execute('BEGIN IMMEDIATE')
                result = self.evaluate(work_id, con=c)
                if not result['work_uuid']: raise ValueError('Catalog work no longer exists.')
                c.execute('''INSERT INTO catalog_acceptances(work_uuid,decision,audit_id,audit_revision,
                    curation_revision,state_fingerprint,accepted_at,reason) VALUES(?,?,?,?,?,?,?,?)''',
                    (result['work_uuid'], 'REVOKE', result['audit_id'], result['audit_revision'],
                     result['curation_revision'], result['fingerprint'], stamp(), reason.strip()))
                c.execute("UPDATE works SET lifecycle_status='STAGED',updated_at=? WHERE work_uuid=?", (stamp(), result['work_uuid']))
                self.db.working_sets.event(c, 'REVOKE_ACCEPTANCE', dict(result, reason=reason.strip()))
