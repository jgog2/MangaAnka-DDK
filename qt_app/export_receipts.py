"""Local file-export receipts; no packet contents or catalog writes."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


def fingerprint(db, set_uuid, mode='pinned'):
    if mode not in ('pinned','current'): raise ValueError('Choose pinned or current export mode.')
    ws = db.working_sets.get(set_uuid)
    if not ws: raise ValueError('Working Set no longer exists.')
    with db.con() as con:
        con.execute('BEGIN')  # One consistent, short read snapshot; no write lock.
        ws = dict(con.execute('SELECT * FROM working_sets WHERE working_set_uuid=?', (set_uuid,)).fetchone())
        items = [dict(r) for r in con.execute('''SELECT i.*,w.id work_id FROM working_set_items i
            LEFT JOIN works w ON w.work_uuid=i.linked_work_uuid
            WHERE i.working_set_uuid=? ORDER BY i.working_set_item_uuid''', (set_uuid,))]
        evidence = []
        for item in items:
            wid = item['work_id']
            observations = [dict(r) for r in con.execute('SELECT * FROM working_set_observations WHERE working_set_item_uuid=? ORDER BY id', (item['working_set_item_uuid'],))]
            if not wid:
                evidence.append(dict(item=item['working_set_item_uuid'], observations=observations))
                continue
            work = dict(con.execute('SELECT * FROM works WHERE id=?', (wid,)).fetchone())
            state = db.catalog.state(wid, con)
            guard = db.catalog.audit_guard(wid, con=con)
            latest = con.execute('SELECT id,audit_revision,health_json FROM search_audits WHERE work_id=? ORDER BY id DESC LIMIT 1', (wid,)).fetchone()
            pin = con.execute('SELECT id,audit_revision,health_json FROM search_audits WHERE id=?', (item['pinned_audit_id'],)).fetchone()
            dispositions = [dict(r) for r in con.execute('SELECT * FROM problem_dispositions WHERE work_id=? ORDER BY id', (wid,))]
            acceptance = [dict(r) for r in con.execute('SELECT * FROM catalog_acceptances WHERE work_uuid=? ORDER BY id', (work['work_uuid'],))]
            evidence.append(dict(work=work, state=state, guard=guard, latest=dict(latest) if latest else None,
                pin=dict(pin) if pin else None, dispositions=dispositions, acceptance=acceptance, observations=observations))
        payload = dict(version=1, database_uuid=db.database_uuid, working_set=ws, mode=mode,
                       items=items, evidence=evidence)
        return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode('utf-8')).hexdigest()


def key(db, set_uuid, mode):
    return f'workflow/exports/{db.database_uuid}/{set_uuid}/{mode}'


def remember(settings, db, set_uuid, mode, digest, path):
    receipt = dict(version=1, fingerprint=digest, path=str(Path(path).resolve()),
                   timestamp=datetime.now(timezone.utc).isoformat())
    settings.setValue(key(db,set_uuid,mode), json.dumps(receipt, ensure_ascii=False)); settings.sync()
    return receipt


def status(settings, db, set_uuid, mode='pinned'):
    if not set_uuid or not db.working_sets.get(set_uuid): return 'Unknown · no Working Set', None
    try: receipt = json.loads(settings.value(key(db,set_uuid,mode), '') or 'null')
    except (ValueError,TypeError): receipt = None
    if not isinstance(receipt,dict) or receipt.get('version') != 1 or not all(
            isinstance(receipt.get(k),str) and receipt[k] for k in ('fingerprint','timestamp','path')):
        return 'Unknown · no local file export receipt', None
    current = receipt.get('fingerprint') == fingerprint(db,set_uuid,mode)
    return ('Review packet current' if current else 'Review packet stale · export fresh'), receipt
