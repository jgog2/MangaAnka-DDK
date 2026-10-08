"""Transactional catalog schema upgrades; existing catalogs require opt-in to v8."""
from datetime import datetime, timezone
import json
import re
import sqlite3

SCHEMA_VERSION = 8
ACCEPTANCE_SCHEMA = '''
CREATE TABLE IF NOT EXISTS catalog_acceptances(
 id INTEGER PRIMARY KEY,
 work_uuid TEXT NOT NULL REFERENCES works(work_uuid) ON DELETE CASCADE,
 decision TEXT NOT NULL CHECK(decision IN ('ACCEPT','REVOKE')),
 audit_id INTEGER REFERENCES search_audits(id) ON DELETE CASCADE,
 audit_revision INTEGER,
 curation_revision INTEGER NOT NULL,
 state_fingerprint TEXT NOT NULL,
 accepted_at TEXT NOT NULL,
 working_set_uuid TEXT REFERENCES working_sets(working_set_uuid) ON DELETE SET NULL,
 working_set_item_uuid TEXT REFERENCES working_set_items(working_set_item_uuid) ON DELETE SET NULL,
 reason TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS catalog_acceptances_work_idx ON catalog_acceptances(work_uuid,id DESC);
CREATE UNIQUE INDEX IF NOT EXISTS works_canonical_unique_idx
 ON works(canonical_work_id,edition,language)
 WHERE canonical_work_id IS NOT NULL AND canonical_work_id<>'';
CREATE INDEX IF NOT EXISTS working_set_duplicate_idx ON working_set_items(duplicate_of_item_uuid);
'''


def migrate_v7(db, backup=True):
    with db.lock, db.con() as c:
        version = c.execute('PRAGMA user_version').fetchone()[0]
        if version in (7, 8):
            if not c.execute("SELECT 1 FROM sqlite_master WHERE name='catalog_acceptances'").fetchone():
                raise ValueError('Schema v7 acceptance provenance is missing.')
            return
        if version != 6:
            raise ValueError(f'Cannot migrate schema v{version} to v7.')
        conflicts = c.execute('''SELECT canonical_work_id,edition,language FROM works
            WHERE canonical_work_id IS NOT NULL AND canonical_work_id<>''
            GROUP BY canonical_work_id,edition,language HAVING count(*)>1''').fetchall()
        if conflicts:
            details = []
            for conflict in conflicts:
                rows = c.execute('''SELECT id,work_uuid FROM works WHERE canonical_work_id=?
                    AND edition=? AND language=?''', tuple(conflict)).fetchall()
                details.append(dict(identity=dict(conflict), works=[dict(row) for row in rows]))
            raise ValueError('Canonical duplicates block v7 migration; resolve these exact works first: '
                             + json.dumps(details, ensure_ascii=False))
        backup_path = None
        if backup:
            folder = db.path.parent / 'backups'; folder.mkdir(exist_ok=True)
            backup_path = folder / (db.path.stem + '_before_schema_v7_' +
                                   datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.db')
            target = sqlite3.connect(backup_path)
            try: c.backup(target)
            finally: target.close()
        # SQLite requires foreign keys disabled before rebuilding a referenced
        # table. Every original ID/UUID and child row is copied unchanged.
        c.execute('PRAGMA foreign_keys=OFF')
        c.execute('BEGIN IMMEDIATE')
        original = c.execute("SELECT sql FROM sqlite_master WHERE name='works'").fetchone()[0]
        indexes = [row[0] for row in c.execute("SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='works' AND sql IS NOT NULL")]
        rebuilt = re.sub(r',\s*UNIQUE\s*\(\s*input_title\s*,\s*edition\s*,\s*language\s*\)', '', original, flags=re.I)
        rebuilt = re.sub(r'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?["`\[]?works["`\]]?',
                         'CREATE TABLE works_v7', rebuilt, count=1, flags=re.I)
        c.execute(rebuilt)
        columns = ','.join('"' + row['name'] + '"' for row in c.execute('PRAGMA table_info(works)'))
        c.execute(f'INSERT INTO works_v7({columns}) SELECT {columns} FROM works')
        c.execute('DROP TABLE works')
        c.execute('ALTER TABLE works_v7 RENAME TO works')
        for sql in indexes: c.execute(sql)
        if 'duplicate_of_item_uuid' not in {r['name'] for r in c.execute('PRAGMA table_info(working_set_items)')}:
            c.execute('''ALTER TABLE working_set_items ADD COLUMN duplicate_of_item_uuid TEXT
                REFERENCES working_set_items(working_set_item_uuid) ON DELETE SET NULL''')
        for statement in ACCEPTANCE_SCHEMA.split(';'):
            if statement.strip(): c.execute(statement)
        if backup_path:
            c.execute('''INSERT INTO database_events(timestamp,origin,description,details_json)
                VALUES(?,?,?,?)''', (datetime.now(timezone.utc).isoformat(), 'MIGRATION', 'Schema v6 to v7',
                                    json.dumps({'backup': str(backup_path)})))
        c.execute('PRAGMA user_version=7')
        if c.execute('PRAGMA foreign_key_check').fetchone() or c.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Schema v7 integrity validation failed; migration rolled back.')
        # DB.con commits on successful exit and all subsequent connections turn
        # foreign keys on. Exceptions roll back the entire rebuild.


SUPPLEMENTARY_SCHEMA = '''
CREATE UNIQUE INDEX supplementary_audit_owner_idx ON search_audits(work_id,id);
CREATE TABLE supplementary_catalog(
 work_id INTEGER PRIMARY KEY REFERENCES works(id) ON DELETE CASCADE,
 revision INTEGER NOT NULL DEFAULT 0 CHECK(revision>=0));
CREATE TABLE supplementary_identities(
 work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
 opaque_id TEXT NOT NULL, identity_json TEXT NOT NULL,
 created_audit_id INTEGER NOT NULL, created_at TEXT NOT NULL,
 PRIMARY KEY(work_id,opaque_id),
 FOREIGN KEY(work_id,created_audit_id) REFERENCES search_audits(work_id,id));
CREATE TABLE supplementary_assertions(
 assertion_uuid TEXT PRIMARY KEY,
 work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
 opaque_id TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('binding','membership')),
 target_key TEXT NOT NULL, decision TEXT NOT NULL CHECK(decision IN ('VERIFIED','REJECTED','WITHDRAWN')),
 payload_json TEXT NOT NULL, created_audit_id INTEGER NOT NULL,
 created_at TEXT NOT NULL,
 UNIQUE(work_id,kind,target_key,assertion_uuid),
 FOREIGN KEY(work_id,created_audit_id) REFERENCES search_audits(work_id,id),
 FOREIGN KEY(work_id,opaque_id) REFERENCES supplementary_identities(work_id,opaque_id));
CREATE TABLE supplementary_current(
 work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
 kind TEXT NOT NULL CHECK(kind IN ('binding','membership')), target_key TEXT NOT NULL,
 assertion_uuid TEXT NOT NULL,
 PRIMARY KEY(work_id,kind,target_key),
 FOREIGN KEY(work_id,kind,target_key,assertion_uuid)
 REFERENCES supplementary_assertions(work_id,kind,target_key,assertion_uuid));
CREATE TABLE supplementary_changes(
 id INTEGER PRIMARY KEY AUTOINCREMENT, work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
 operation TEXT NOT NULL, changes_json TEXT NOT NULL, guard_json TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('active','reverted','superseded')), created_at TEXT NOT NULL,
 UNIQUE(work_id,id));
CREATE TABLE supplementary_events(
 id INTEGER PRIMARY KEY AUTOINCREMENT, work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
 change_id INTEGER NOT NULL,
 action TEXT NOT NULL CHECK(action IN ('apply','undo','redo')), revision INTEGER NOT NULL,
 guard_json TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(work_id,revision), FOREIGN KEY(work_id,change_id) REFERENCES supplementary_changes(work_id,id));
CREATE INDEX supplementary_assertions_work_idx ON supplementary_assertions(work_id,opaque_id);
CREATE TRIGGER supplementary_identities_immutable BEFORE UPDATE ON supplementary_identities
BEGIN SELECT RAISE(ABORT,'Supplementary identities are immutable'); END;
CREATE TRIGGER supplementary_assertions_immutable BEFORE UPDATE ON supplementary_assertions
BEGIN SELECT RAISE(ABORT,'Supplementary assertions are immutable'); END;
CREATE TRIGGER supplementary_events_immutable BEFORE UPDATE ON supplementary_events
BEGIN SELECT RAISE(ABORT,'Supplementary events are immutable'); END;
'''


def migrate_v8(db, backup=True):
    """Explicitly invoked additive migration; no guessed bindings or backfill."""
    with db.lock, db.con() as c:
        version=c.execute('PRAGMA user_version').fetchone()[0]
        required={'supplementary_catalog','supplementary_identities','supplementary_assertions',
                  'supplementary_current','supplementary_changes','supplementary_events'}
        tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if version==8:
            if not required<=tables: raise ValueError('Schema v8 supplementary provenance is incomplete.')
            return
        if version!=7: raise ValueError(f'Cannot migrate schema v{version} to v8.')
        if required & tables: raise ValueError('Unexpected supplementary tables in schema v7; migration refused.')
        if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or c.execute('PRAGMA foreign_key_check').fetchone():
            raise ValueError('Schema v7 integrity validation failed; migration refused.')
        backup_path=None
        if backup:
            folder=db.path.parent/'backups';folder.mkdir(exist_ok=True)
            backup_path=folder/(db.path.stem+'_before_schema_v8_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.db')
            target=sqlite3.connect(backup_path)
            try:c.backup(target)
            finally:target.close()
        c.execute('BEGIN IMMEDIATE')
        statement=''
        for line in SUPPLEMENTARY_SCHEMA.splitlines(keepends=True):
            statement+=line
            if sqlite3.complete_statement(statement):
                c.execute(statement);statement=''
        c.execute('''INSERT INTO database_events(timestamp,origin,description,details_json)
            VALUES(?,?,?,?)''',(datetime.now(timezone.utc).isoformat(),'MIGRATION','Schema v7 to v8',
                json.dumps({'backup':str(backup_path) if backup_path else None})))
        c.execute('PRAGMA user_version=8')
        if c.execute('PRAGMA foreign_key_check').fetchone() or c.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
            raise ValueError('Schema v8 integrity validation failed; migration rolled back.')
