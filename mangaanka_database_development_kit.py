#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
import queue
import sqlite3
import threading
import time
import uuid
import webbrowser
from concurrent.futures import CancelledError, ThreadPoolExecutor, as_completed
from contextlib import contextmanager, nullcontext, closing
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ddk_publication import resolve_publication, publication_holes, evaluate_structure_coverage
from ddk_chapter_normalization import publication_classification_counts
from ddk_catalog import Catalog, SCHEMA as CURATED_SCHEMA
from ddk_catalog_maintenance import CatalogMaintenance, format_delete_preview
from ddk_schema import migrate_v7, migrate_v8, SCHEMA_VERSION
from ddk_acceptance import Acceptance
from ddk_editor import CatalogEditor
from ddk_workspace import validate_database, saved_path, remember_path
from ddk_working_sets import WorkingSets, IntakeIdentityReview, AuditSuperseded, DuplicateIntake, SCHEMA as WORKING_SCHEMA
from ddk_writer_lock import WriterLock
from ddk_exports import (catalog_summary,review_context,working_set_csv,
                         working_set_title_list,working_set_packet,working_set_rows,
                         working_set_review_context)
from ddk_review import review_packet, packet_markdown, detailed_csv, write_packet, issue_from_row, health, problem_policy
from mangaanka_search_core.canonical_identity import edition_identity

from mangaanka_search_core.source_registry import SourceRegistry
from mangaanka_search_core.source_coordinator import SourceCoordinator
from mangaanka_search_core.mangadex_source import MangaDexSource
from mangaanka_search_core.mangapill_source import MangaPillSource
from mangaanka_search_core.weebcentral_source import WeebCentralSource
from mangaanka_search_core.mangak_source import MangaKSource
from mangaanka_search_core.atsu_source import AtsuSource
from mangaanka_search_core.enrichment_sources import DEFAULT_ENRICHMENT_REGISTRY
from mangaanka_search_core.enrichment_matching import (enrich_content_results,
    effective_search_rows, trusted_alias_for_query)
from mangaanka_search_core.search_ranking import MatchTier, rank_canonical_results
from mangaanka_search_core.search_resolution import resolve_search_group
from mangaanka_search_core.canonical_identity import normalize_identity_text
from mangaanka_search_core.version_info import SEMANTIC_VERSION as SEARCH_CORE_VERSION, CODENAME as SEARCH_CORE_CODENAME

APP = 'MangaAnkā Database Development Kit'
VERSION = '0.3.0'
SEARCH_LIMIT = 12
RESOLUTION_LIMIT = 6

# Higher contrast than the previous DDK theme. Readonly/selected controls are
# explicitly mapped so Windows does not render white text on a white field.
BG = '#111214'
PANEL = '#191B1F'
PANEL2 = '#25282E'
PANEL3 = '#30343B'
TEXT = '#F7F7F7'
MUTED = '#B9BEC7'
ACCENT = '#FF6740'
ACCENT_DARK = '#B9472B'
BORDER = '#4B505A'
GOOD = '#72D28B'
WARN = '#F0C56A'
BAD = '#EF7D7D'


def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def uniq(values):
    out = []
    seen = set()
    for value in values:
        value = str(value or '').strip()
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            out.append(value)
    return out


def json_text(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def safe_json(value):
    try:
        return json.loads(value or '{}')
    except Exception:
        return {}


def reported_totals(rows):
    chapters = set()
    volumes = set()
    for row in rows or ():
        for ctx in row.get('volume_context') or ():
            if not isinstance(ctx, dict):
                continue
            c = ctx.get('reported_total_chapters')
            v = ctx.get('reported_total_volumes')
            try:
                if c is not None and int(c) > 0:
                    chapters.add(int(c))
            except Exception:
                pass
            try:
                if v is not None and int(v) > 0:
                    volumes.add(int(v))
            except Exception:
                pass
    return sorted(chapters), sorted(volumes)


def audit_is_fresh(row):
    if not row['audit_id']:
        return False
    publication = safe_json(row['publication_json'])
    if not publication.get('catalog_identity'):
        return False
    if row['catalog_revision'] != publication.get('curation_revision', publication.get('curated_database', {}).get('revision', 0)):
        return False
    patch=publication.get('curated_database') or {}
    if row['structure_source_revision'] is not None:
        if (not patch.get('structure_shared') or patch.get('revision')!=row['structure_source_revision'] or
            row['structure_source_claim']!=row['canonical_work_id'] or
            (publication.get('catalog_identity') or {}).get('canonical_work_id')!=row['canonical_work_id']):
            return False
    elif patch.get('structure_shared'):
        return False
    return True


def audit_status(row):
    if not row['audit_id']:
        return 'NOT AUDITED'
    if not audit_is_fresh(row):
        return 'RERUN REQUIRED' if row['final_state'] != 'ERROR' else 'ERROR'
    if row['final_state']=='REVIEW' and row['hole_count']==0:
        return 'PASS' if all(v=='PASS' for v in safe_json(row['health_json']).values()) else 'REVIEW'
    return row['final_state'] or 'RERUN REQUIRED'


SCHEMA = '''
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS conceptual_works(
    conceptual_work_uuid TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS works(
    id INTEGER PRIMARY KEY,
    input_title TEXT,
    canonical_title TEXT,
    edition TEXT,
    language TEXT,
    identity_status TEXT DEFAULT 'queued',
    publication_status TEXT,
    media_format TEXT,
    anilist_id TEXT,
    mal_id TEXT,
    mangadex_id TEXT,
    work_uuid TEXT,
    conceptual_work_uuid TEXT REFERENCES conceptual_works(conceptual_work_uuid),
    canonical_work_id TEXT,
    lifecycle_status TEXT NOT NULL DEFAULT 'STAGED',
    expected_chapters INTEGER,
    expected_volumes INTEGER,
    approval_status TEXT DEFAULT 'draft',
    created_at TEXT,
    updated_at TEXT,
    last_harvested_at TEXT,
    UNIQUE(input_title,edition,language)
);
CREATE TABLE IF NOT EXISTS search_audits(
    id INTEGER PRIMARY KEY,
    work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    workflow TEXT NOT NULL,
    match_title TEXT,
    match_tier TEXT,
    group_confidence TEXT,
    group_reason TEXT,
    provider_count INTEGER DEFAULT 0,
    selected_source TEXT,
    selected_source_name TEXT,
    selected_chapters INTEGER DEFAULT 0,
    selected_native_volumes INTEGER DEFAULT 0,
    selected_standalone INTEGER DEFAULT 0,
    reported_chapters TEXT,
    reported_volumes TEXT,
    language_fallback INTEGER DEFAULT 0,
    resolution_error TEXT,
    provider_states_json TEXT,
    provider_rows_json TEXT,
    inventories_json TEXT,
    enrichment_errors_json TEXT,
    alias_retry TEXT,
    ddk_version TEXT,
    search_core_version TEXT,
    schema_version INTEGER,
    requested_edition TEXT,
    requested_language TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS search_audits_work_idx ON search_audits(work_id,id DESC);
CREATE TABLE IF NOT EXISTS audit_holes(
    id INTEGER PRIMARY KEY,
    audit_id INTEGER NOT NULL REFERENCES search_audits(id) ON DELETE CASCADE,
    work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    details_json TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS audit_holes_work_idx ON audit_holes(work_id,audit_id);
CREATE TABLE IF NOT EXISTS problem_dispositions(
    id INTEGER PRIMARY KEY,
    problem_row_id INTEGER NOT NULL REFERENCES audit_holes(id) ON DELETE CASCADE,
    work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    audit_id INTEGER NOT NULL REFERENCES search_audits(id) ON DELETE CASCADE,
    signature TEXT NOT NULL,
    status TEXT NOT NULL,
    problem_class TEXT,
    reason TEXT NOT NULL,
    verification TEXT NOT NULL,
    pattern TEXT,
    provider TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS problem_dispositions_row_idx ON problem_dispositions(problem_row_id,id DESC);
CREATE TABLE IF NOT EXISTS database_meta(
    singleton INTEGER PRIMARY KEY CHECK(singleton=1),
    database_uuid TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('PRODUCTION','TEST','SCRATCH')),
    created_at TEXT NOT NULL,
    active_working_set_uuid TEXT
);
CREATE TABLE IF NOT EXISTS database_events(
    id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL,
    origin TEXT NOT NULL,
    description TEXT NOT NULL,
    details_json TEXT NOT NULL DEFAULT '{}'
);
'''


class DB:
    def __init__(self, path: Path, role='PRODUCTION', create_new=False, migrate_schema8=False):
        self.path = Path(path).resolve()
        if role not in ('PRODUCTION','TEST','SCRATCH'):
            raise ValueError('Choose PRODUCTION, TEST, or SCRATCH.')
        if create_new:
            if not self.path.exists() or self.path.stat().st_size:
                raise ValueError('New database reservation is missing or contains data.')
        elif self.path.exists():
            validate_database(self.path)
            if self.path.stat().st_size:
                with closing(sqlite3.connect(self.path.as_uri()+'?mode=ro',uri=True)) as existing:
                    version=existing.execute('PRAGMA user_version').fetchone()[0]
                if version<8 and not migrate_schema8:
                    raise ValueError('Existing catalog requires explicit schema-8 migration. Normal opening never upgrades it. '
                                     'Review the migration/recovery checklist, then use --database PATH --migrate-schema8.')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self._artifact_groups_cache = {}
        existing_before_init=self.path.is_file() and self.path.stat().st_size>0
        self.init(role)
        migrate_v7(self,backup=existing_before_init)
        migrate_v8(self,backup=existing_before_init)
        self.catalog = Catalog(self)
        from ddk_supplementary_store import SupplementaryStore
        self.supplementary = SupplementaryStore(self)
        self.working_sets = WorkingSets(self)
        self.acceptance = Acceptance(self)
        self.maintenance = CatalogMaintenance(self)

    @contextmanager
    def con(self):
        c = sqlite3.connect(self.path, timeout=30)
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA foreign_keys=ON')
        try:
            with c:
                yield c
        finally:
            c.close()

    def init(self, role='PRODUCTION'):
        with self.con() as c:
            existing=c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='search_audits'").fetchone()
            old_version=c.execute('PRAGMA user_version').fetchone()[0]
            if old_version>8:raise ValueError('Database schema is newer than this DDK supports.')
            if old_version in (6,7,8):
                if not c.execute('SELECT database_uuid FROM database_meta WHERE singleton=1').fetchone():
                    raise ValueError('Database metadata is missing; cannot activate this database.')
                tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if not {'curated_catalog','curated_fields','curated_changes','curated_events','database_events',
                        'working_sets','working_set_items','edition_structure_relationships',
                        'conceptual_works','curated_evidence'} <= tables:
                    raise ValueError('Current-schema database is missing catalog or history tables.')
                return
            if existing and old_version<6:
                folder=self.path.parent/'backups';folder.mkdir(exist_ok=True)
                backup=folder/(self.path.stem+'_before_schema_v6_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.db')
                target=sqlite3.connect(backup)
                try: c.backup(target)
                finally: target.close()
            c.execute('BEGIN IMMEDIATE')
            statement=''
            for line in (SCHEMA+CURATED_SCHEMA).splitlines(keepends=True):
                statement+=line
                if sqlite3.complete_statement(statement):
                    if not statement.strip().startswith('PRAGMA foreign_keys'):
                        c.execute(statement)
                    statement=''
            # Additive migration: retain every legacy audit and hole unchanged.
            columns = {r['name'] for r in c.execute('PRAGMA table_info(search_audits)')}
            for name, kind in {
                'publication_json': 'TEXT', 'selected_edition': 'TEXT',
                'logical_chapters': 'INTEGER', 'final_volumes': 'INTEGER',
                'mapped_chapters': 'INTEGER', 'unmapped_chapters': 'INTEGER',
                'final_state': 'TEXT', 'run_status': 'TEXT',
                'audit_revision': 'INTEGER', 'health_json': 'TEXT',
                'ddk_version':'TEXT','search_core_version':'TEXT','schema_version':'INTEGER',
                'requested_edition':'TEXT','requested_language':'TEXT',
            }.items():
                if name not in columns:
                    c.execute(f'ALTER TABLE search_audits ADD COLUMN {name} {kind}')
            hole_columns = {r['name'] for r in c.execute('PRAGMA table_info(audit_holes)')}
            for name, kind in {'problem_class':'TEXT','next_action':'TEXT',
                               'problem_role':'TEXT','evidence_sufficient':'INTEGER'}.items():
                if name not in hole_columns:
                    c.execute(f'ALTER TABLE audit_holes ADD COLUMN {name} {kind}')
            curated_columns={r['name'] for r in c.execute('PRAGMA table_info(curated_fields)')}
            for name in ('source_name','source_url','accessed_at'):
                if name not in curated_columns:
                    c.execute(f"ALTER TABLE curated_fields ADD COLUMN {name} TEXT NOT NULL DEFAULT ''")
            if old_version<6:
                for evidence in c.execute('''SELECT work_id,entity,record_key,field,source_name,source_url,
                    accessed_at,note,verification FROM curated_fields WHERE source_name<>'' ''').fetchall():
                    revision=c.execute('SELECT revision FROM curated_catalog WHERE work_id=?',
                                       (evidence['work_id'],)).fetchone()
                    c.execute('''INSERT INTO curated_evidence VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',
                              (str(uuid.uuid4()),evidence['work_id'],evidence['entity'],evidence['record_key'],
                               evidence['field'],revision['revision'] if revision else 0,
                               evidence['source_name'],evidence['source_url'],evidence['accessed_at'],
                               evidence['note'],evidence['verification'],now()))
            work_columns={r['name'] for r in c.execute('PRAGMA table_info(works)')}
            for name,kind in {'work_uuid':'TEXT','canonical_work_id':'TEXT',
                              'conceptual_work_uuid':'TEXT REFERENCES conceptual_works(conceptual_work_uuid)',
                              'lifecycle_status':"TEXT NOT NULL DEFAULT 'STAGED'"}.items():
                if name not in work_columns:c.execute(f'ALTER TABLE works ADD COLUMN {name} {kind}')
            for row in c.execute('SELECT id FROM works WHERE work_uuid IS NULL OR work_uuid=""').fetchall():
                c.execute('UPDATE works SET work_uuid=? WHERE id=?',(str(uuid.uuid4()),row['id']))
            for row in c.execute('SELECT id,work_uuid FROM works WHERE conceptual_work_uuid IS NULL').fetchall():
                c.execute('INSERT OR IGNORE INTO conceptual_works VALUES(?,?)',(row['work_uuid'],now()))
                c.execute('UPDATE works SET conceptual_work_uuid=? WHERE id=?',(row['work_uuid'],row['id']))
            if 'active_working_set_uuid' not in {r['name'] for r in c.execute('PRAGMA table_info(database_meta)')}:
                c.execute('ALTER TABLE database_meta ADD COLUMN active_working_set_uuid TEXT')
            c.execute('INSERT OR IGNORE INTO database_meta(singleton,database_uuid,role,created_at) VALUES(1,?,?,?)',
                      (str(uuid.uuid4()),role,now()))
            for row in c.execute('''SELECT w.id,a.publication_json FROM works w JOIN search_audits a ON
                a.id=(SELECT max(id) FROM search_audits WHERE work_id=w.id)
                WHERE w.canonical_work_id IS NULL''').fetchall():
                identity=(safe_json(row['publication_json']).get('catalog_identity') or {})
                if identity.get('trusted') and identity.get('canonical_work_id'):
                    c.execute('UPDATE works SET canonical_work_id=? WHERE id=?',
                              (identity['canonical_work_id'],row['id']))
            statement=''
            for line in WORKING_SCHEMA.splitlines(keepends=True):
                statement+=line
                if sqlite3.complete_statement(statement):
                    c.execute(statement);statement=''
            relationship_columns={r['name'] for r in c.execute('PRAGMA table_info(edition_structure_relationships)')}
            for name in ('source_context','target_context'):
                if name not in relationship_columns:
                    c.execute(f"ALTER TABLE edition_structure_relationships ADD COLUMN {name} TEXT NOT NULL DEFAULT ''")
            if old_version<6:
                for relation in c.execute('SELECT source_work_uuid,target_work_uuid FROM edition_structure_relationships').fetchall():
                    contexts=[]
                    for work_uuid in (relation['source_work_uuid'],relation['target_work_uuid']):
                        audit=c.execute('''SELECT a.publication_json FROM works w JOIN search_audits a
                            ON a.work_id=w.id WHERE w.work_uuid=? ORDER BY a.id DESC LIMIT 1''',
                            (work_uuid,)).fetchone()
                        identity=(safe_json(audit['publication_json']).get('catalog_identity') or {}) if audit else {}
                        contexts.append(identity.get('publication_context') or '')
                    c.execute('''UPDATE edition_structure_relationships SET source_context=?,target_context=?
                        WHERE source_work_uuid=? AND target_work_uuid=?''',
                        (*contexts,relation['source_work_uuid'],relation['target_work_uuid']))
            c.execute('''UPDATE works SET conceptual_work_uuid=(SELECT source.conceptual_work_uuid
                FROM edition_structure_relationships r JOIN works source ON source.work_uuid=r.source_work_uuid
                WHERE r.target_work_uuid=works.work_uuid LIMIT 1)
                WHERE work_uuid IN (SELECT target_work_uuid FROM edition_structure_relationships)''')
            if existing and old_version<6:
                c.execute('INSERT INTO database_events(timestamp,origin,description,details_json) VALUES(?,?,?,?)',
                          (now(),'MIGRATION',f'Schema v{old_version} to v6',json_text({'backup':str(backup)})))
            c.execute('PRAGMA user_version=6')
            if c.execute('PRAGMA foreign_key_check').fetchone() or c.execute('PRAGMA quick_check').fetchone()[0]!='ok':
                raise ValueError('Database migration failed integrity validation; original backup retained.')

    @property
    def database_uuid(self):
        with self.con() as c:
            return c.execute('SELECT database_uuid FROM database_meta WHERE singleton=1').fetchone()[0]

    @property
    def role(self):
        with self.con() as c:
            return c.execute('SELECT role FROM database_meta WHERE singleton=1').fetchone()[0]

    def add_titles(self, titles, edition, language):
        t = now()
        count = 0
        added=[]
        titles=[str(title or '').strip() for title in titles]
        with self.lock:
            with self.con() as c:
                existing={(r['input_title'],r['edition'],r['language']) for r in c.execute(
                    'SELECT input_title,edition,language FROM works')}
            if existing and any(title and (title,edition,language) not in existing for title in titles):
                self.catalog._backup()
            with self.con() as c:
                for title in titles:
                    if not title or (title,edition,language) in existing:
                        continue
                    work_uuid=str(uuid.uuid4())
                    inserted=c.execute(
                        '''INSERT OR IGNORE INTO works(input_title,edition,language,work_uuid,
                           lifecycle_status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)''',
                        (title, edition, language, work_uuid,'STAGED',t,t),
                    ).rowcount
                    count+=inserted
                    if inserted:
                        c.execute('INSERT INTO conceptual_works VALUES(?,?)',(work_uuid,t))
                        c.execute('UPDATE works SET conceptual_work_uuid=? WHERE work_uuid=?',(work_uuid,work_uuid))
                        added.append(title)
                        existing.add((title,edition,language))
                if added:
                    c.execute('INSERT INTO database_events(timestamp,origin,description,details_json) VALUES(?,?,?,?)',
                              (t,'IMPORT',f'Added {len(added)} title(s)',json_text({'titles':added,'edition':edition,'language':language})))
        return count

    def works(self,work_ids=None,accepted_only=False,con=None,audit_by_work=None):
        ids=list(dict.fromkeys(work_ids)) if work_ids is not None else None
        if ids is not None and not ids:return []
        clauses=[];args=[]
        if ids is not None:
            clauses.append('w.id IN ('+','.join('?' for _ in ids)+')');args.extend(ids)
        where='WHERE '+' AND '.join(clauses) if clauses else ''
        audit_join='(SELECT a2.id FROM search_audits a2 WHERE a2.work_id=w.id ORDER BY a2.id DESC LIMIT 1)'
        if audit_by_work is not None:
            audit_join=('CASE w.id '+''.join(f'WHEN {int(wid)} THEN {int(aid) if aid else "NULL"} ' for wid,aid in audit_by_work.items())+'ELSE NULL END') if audit_by_work else 'NULL'
        with (self.con() if con is None else nullcontext(con)) as c:
            rows=c.execute(f'''
                SELECT w.*,
                       a.id audit_id,a.match_title,a.match_tier,a.group_confidence,
                       a.provider_count,a.selected_source,a.selected_source_name,
                       a.selected_chapters,a.selected_native_volumes,a.selected_standalone,
                       a.reported_chapters,a.reported_volumes,a.resolution_error,
                       a.publication_json,a.selected_edition,a.logical_chapters,a.final_volumes,
                       COALESCE((SELECT revision FROM curated_catalog cc WHERE cc.work_id=w.id),0) catalog_revision,
                       (SELECT cc.revision FROM edition_structure_relationships r
                        JOIN works source ON source.work_uuid=r.source_work_uuid
                        JOIN curated_catalog cc ON cc.work_id=source.id
                        WHERE r.target_work_uuid=w.work_uuid LIMIT 1) structure_source_revision,
                       (SELECT source.canonical_work_id FROM edition_structure_relationships r
                        JOIN works source ON source.work_uuid=r.source_work_uuid
                        WHERE r.target_work_uuid=w.work_uuid LIMIT 1) structure_source_claim,
                       a.mapped_chapters,a.unmapped_chapters,a.final_state,a.run_status,a.health_json,
                       a.audit_revision,
                       a.created_at audit_created_at,
                       (SELECT COUNT(*) FROM audit_holes h WHERE h.audit_id=a.id AND NOT EXISTS
                         (SELECT 1 FROM problem_dispositions d WHERE d.problem_row_id=h.id
                          AND d.id=(SELECT max(d2.id) FROM problem_dispositions d2 WHERE d2.problem_row_id=h.id)
                          AND d.status='IGNORED_WITH_REASON')) hole_count,
                       (SELECT COUNT(*) FROM audit_holes h WHERE h.audit_id=a.id AND h.severity='error') error_count
                FROM works w
                LEFT JOIN search_audits a ON a.id={audit_join} AND a.work_id=w.id
                {where}
                ORDER BY lower(COALESCE(a.match_title,w.canonical_title,w.input_title))
            ''',args).fetchall()
            result=[]
            for row in rows:
                item=dict(row)
                item['acceptance_state']=self.acceptance.state(row['id'],con=c) if hasattr(self,'acceptance') else 'NONE'
                if not accepted_only or item['acceptance_state']=='CURRENT':result.append(item)
            return result

    def work(self, work_id, con=None):
        with (self.con() if con is None else nullcontext(con)) as c:
            return c.execute('SELECT * FROM works WHERE id=?', (work_id,)).fetchone()

    def latest_audit(self, work_id, con=None):
        with (self.con() if con is None else nullcontext(con)) as c:
            return c.execute(
                'SELECT * FROM search_audits WHERE work_id=? ORDER BY id DESC LIMIT 1',
                (work_id,),
            ).fetchone()

    def audit(self, audit_id, work_id):
        with self.con() as c:
            return c.execute('SELECT * FROM search_audits WHERE id=? AND work_id=?',
                             (audit_id,work_id)).fetchone()

    def holes(self, filter_code='All', include_ignored=False, audit_ids=None):
        with self.con() as c:
            sql = '''
                SELECT h.*,COALESCE(a.match_title,w.canonical_title,w.input_title) title,a.created_at audit_created_at
                FROM audit_holes h
                JOIN search_audits a ON a.id=h.audit_id
                JOIN works w ON w.id=h.work_id
                WHERE 1=1
            '''
            args = []
            if audit_ids is None:
                sql+=' AND a.id=(SELECT max(id) FROM search_audits WHERE work_id=w.id)'
            else:
                ids=list(audit_ids)
                if not ids:return []
                sql+=' AND a.id IN ('+','.join('?' for _ in ids)+')';args.extend(ids)
            if filter_code and filter_code != 'All':
                sql += ' AND h.code=?'
                args.append(filter_code)
            if not include_ignored:
                sql += ''' AND NOT EXISTS (SELECT 1 FROM problem_dispositions d
                    WHERE d.problem_row_id=h.id AND d.id=(SELECT max(d2.id) FROM problem_dispositions d2
                    WHERE d2.problem_row_id=h.id) AND d.status='IGNORED_WITH_REASON')'''
            sql += " ORDER BY CASE h.severity WHEN 'error' THEN 0 WHEN 'warning' THEN 1 ELSE 2 END, lower(title),h.code"
            return c.execute(sql, args).fetchall()

    def hole_codes(self):
        with self.con() as c:
            rows = c.execute('SELECT DISTINCT code FROM audit_holes ORDER BY code').fetchall()
        return [r['code'] for r in rows]

    def problem_disposition(self, problem_row_id):
        with self.con() as c:
            return c.execute('SELECT * FROM problem_dispositions WHERE problem_row_id=? ORDER BY id DESC LIMIT 1',
                             (problem_row_id,)).fetchone()

    @staticmethod
    def _refresh_audit_health(c, audit_id, publication, requested_edition):
        from ddk_review import health
        issues=[]
        for hole in c.execute('SELECT id,code,severity FROM audit_holes WHERE audit_id=?',(audit_id,)):
            disposition=c.execute('SELECT status FROM problem_dispositions WHERE problem_row_id=? ORDER BY id DESC LIMIT 1',
                                  (hole['id'],)).fetchone()
            issues.append({'problem_type':hole['code'],'severity':hole['severity'],
                           'disposition':disposition['status'] if disposition else None})
        dimensions=health(publication,issues,requested_edition)
        unresolved=[i for i in issues if i['disposition']!='IGNORED_WITH_REASON']
        prior=c.execute('SELECT final_state FROM search_audits WHERE id=?',(audit_id,)).fetchone()['final_state']
        state='ERROR' if prior=='ERROR' else ('PASS' if not unresolved and
                 all(v=='PASS' for v in dimensions.values()) else 'REVIEW')
        c.execute('UPDATE search_audits SET health_json=?,final_state=? WHERE id=?',
                  (json_text(dimensions),state,audit_id))

    def dispose_problem(self, problem_row_id, reason, verification='REVIEWED', pattern=None, item_uuid=None):
        from ddk_review import issue_signature
        reason=str(reason or '').strip()
        if not reason: raise ValueError('A specific reason is required.')
        if verification not in ('REVIEWED','VERIFIED'): raise ValueError('Choose REVIEWED or VERIFIED.')
        with self.lock, self.con() as c:
            c.execute('BEGIN IMMEDIATE')
            hole=c.execute('SELECT * FROM audit_holes WHERE id=?',(problem_row_id,)).fetchone()
            if not hole: raise ValueError('Problem no longer exists.')
            if item_uuid:self.working_sets.editable_item(item_uuid,hole['work_id'],con=c)
            latest=c.execute('SELECT * FROM search_audits WHERE work_id=? ORDER BY id DESC LIMIT 1',
                             (hole['work_id'],)).fetchone()
            if latest['id']!=hole['audit_id']: raise ValueError('Re-audit changed this problem; review the latest result.')
            publication=safe_json(latest['publication_json'])
            identity=publication.get('catalog_identity') or {}
            if (hole['code']!='UNCLASSIFIED_ACQUISITION' or not identity.get('trusted') or
                any(r['code'] in ('WRONG_EDITION_MATCH','NO_CANONICAL_RESULT','CURATED_IDENTITY_CONFLICT')
                    for r in c.execute('SELECT code FROM audit_holes WHERE audit_id=?',(latest['id'],)))):
                raise ValueError('Only unclassified acquisition on a trusted, edition-safe identity may be ignored.')
            labels=(publication.get('normalization') or {}).get('labels') or ()
            providers={row.get('_acquisition_provider') for row,label in zip(publication.get('projection') or (),labels)
                       if label in ('unclassified','provisional') and row.get('_acquisition_provider')}
            provider=next(iter(providers)) if len(providers)==1 else None
            c.execute('''INSERT INTO problem_dispositions(problem_row_id,work_id,audit_id,signature,status,
                         problem_class,reason,verification,pattern,provider,created_at)
                         VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
                      (problem_row_id,hole['work_id'],latest['id'],issue_signature(hole,publication),
                       'IGNORED_WITH_REASON','ACQUISITION',reason,verification,
                       str(pattern).strip() if pattern else None,provider,now()))
            work=c.execute('SELECT edition FROM works WHERE id=?',(hole['work_id'],)).fetchone()
            self._refresh_audit_health(c,latest['id'],publication,work['edition'] or 'standard')
            self.acceptance.recalculate(hole['work_id'],con=c)

    def reopen_problem(self, problem_row_id, reason, verification='REVIEWED', item_uuid=None):
        reason=str(reason or '').strip()
        if not reason: raise ValueError('A reason for reopening is required.')
        if verification not in ('REVIEWED','VERIFIED'): raise ValueError('Choose REVIEWED or VERIFIED.')
        with self.lock, self.con() as c:
            c.execute('BEGIN IMMEDIATE')
            hole=c.execute('SELECT * FROM audit_holes WHERE id=?',(problem_row_id,)).fetchone()
            if not hole: raise ValueError('Problem no longer exists.')
            if item_uuid:self.working_sets.editable_item(item_uuid,hole['work_id'],con=c)
            latest=c.execute('SELECT * FROM search_audits WHERE work_id=? ORDER BY id DESC LIMIT 1',
                             (hole['work_id'],)).fetchone()
            disposition=c.execute('SELECT * FROM problem_dispositions WHERE problem_row_id=? ORDER BY id DESC LIMIT 1',
                                  (problem_row_id,)).fetchone()
            if latest['id']!=hole['audit_id'] or not disposition or disposition['status']!='IGNORED_WITH_REASON':
                raise ValueError('Only a currently ignored problem on the latest audit can be reopened.')
            c.execute('''INSERT INTO problem_dispositions(problem_row_id,work_id,audit_id,signature,status,
                         problem_class,reason,verification,pattern,provider,created_at)
                         VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
                      (problem_row_id,hole['work_id'],latest['id'],disposition['signature'],
                       'REOPENED',hole['problem_class'],reason,verification,None,disposition['provider'],now()))
            work=c.execute('SELECT edition FROM works WHERE id=?',(hole['work_id'],)).fetchone()
            self._refresh_audit_health(c,latest['id'],safe_json(latest['publication_json']),work['edition'] or 'standard')
            self.acceptance.recalculate(hole['work_id'],con=c)

    def code_review_candidates(self):
        with self.lock, self.con() as c:
            candidates={}
            audits=c.execute('''SELECT a.id,a.work_id FROM search_audits a JOIN works w ON w.id=a.work_id
                WHERE a.id=(SELECT max(id) FROM search_audits WHERE work_id=a.work_id)''').fetchall()
            for audit in audits:
                cached=self._artifact_groups_cache.get(audit['work_id'])
                if not cached or cached[0]!=audit['id']:
                    blocked=bool(c.execute('''SELECT 1 FROM audit_holes WHERE audit_id=? AND code IN
                        ('WRONG_EDITION_MATCH','NO_CANONICAL_RESULT','CURATED_IDENTITY_CONFLICT') LIMIT 1''',
                        (audit['id'],)).fetchone())
                    publication=c.execute('SELECT publication_json FROM search_audits WHERE id=?',(audit['id'],)).fetchone()
                    groups=(safe_json(publication['publication_json']).get('normalization') or {}).get('artifact_groups') or []
                    cached=(audit['id'],blocked,groups)
                    self._artifact_groups_cache[audit['work_id']]=cached
                if cached[1]: continue
                for group in cached[2]:
                    provider=group.get('provider');classification=group.get('classification')
                    family=group.get('pattern_family')
                    if not provider or not classification or not family: continue
                    key=(provider,classification,family)
                    candidate=candidates.setdefault(key,{'provider':provider,'classification':classification,
                        'pattern_family':family,'pattern':family,'records':0,'work_ids':set(),'audit_ids':set(),
                        'all_identifiers':[],'members':[],'reason':group.get('reason') or '',
                        'confidence':group.get('confidence') or 'candidate',
                        'problem_class':'CODE',
                        'next_action':'CODE_REVIEW_REQUIRED',
                        'origin':'automatic_normalization'})
                    candidate['records']+=int(group.get('count') or 0)
                    candidate['work_ids'].add(audit['work_id']);candidate['audit_ids'].add(audit['id'])
                    members=group.get('member_records') or ({'identifier':x} for x in group.get('identifiers') or ())
                    for member in members:
                        candidate['all_identifiers'].append(member['identifier'])
                        candidate['members'].append(dict(member,work_id=audit['work_id'],audit_id=audit['id']))
            result=[]
            for candidate in candidates.values():
                if candidate['records']<2: continue
                candidate['works']=len(candidate.pop('work_ids'))
                candidate['audits']=len(candidate.pop('audit_ids'))
                candidate['representative_identifiers']=candidate['all_identifiers'][:8]
                result.append(candidate)
            manual=c.execute('''SELECT d.provider,d.pattern,count(DISTINCT d.work_id) titles
                FROM problem_dispositions d WHERE pattern IS NOT NULL AND pattern!=''
                AND provider IS NOT NULL AND provider!='' AND status='IGNORED_WITH_REASON'
                AND d.id=(SELECT max(d2.id) FROM problem_dispositions d2 WHERE d2.problem_row_id=d.problem_row_id)
                GROUP BY provider,pattern HAVING count(DISTINCT work_id)>=2
                ORDER BY titles DESC,provider,pattern''').fetchall()
            result.extend(dict(r,works=r['titles'],classification='reviewed_provider_pattern',
                               pattern_family=r['pattern'],problem_class='CODE',
                               next_action='CODE_REVIEW_REQUIRED',origin='reviewed_disposition') for r in manual)
            return sorted(result,key=lambda r:(r['provider'],r['pattern_family'],r.get('classification','')))

    def audit_diff(self, work_id):
        with self.con() as c:
            audits=c.execute('SELECT * FROM search_audits WHERE work_id=? ORDER BY id DESC LIMIT 2',(work_id,)).fetchall()
            if len(audits)<2: return None
            unresolved_sql='''SELECT h.code FROM audit_holes h WHERE h.audit_id=? AND NOT EXISTS
                (SELECT 1 FROM problem_dispositions d WHERE d.problem_row_id=h.id AND
                 d.id=(SELECT max(d2.id) FROM problem_dispositions d2 WHERE d2.problem_row_id=h.id)
                 AND d.status='IGNORED_WITH_REASON')'''
            def codes(a): return {r['code'] for r in c.execute(unresolved_sql,(a['id'],))}
            after,before=audits
            def count(a): return len(c.execute(unresolved_sql,(a['id'],)).fetchall())
            def conflicts(a): return len(safe_json(a['publication_json']).get('conflicting_chapters') or ())
            before_health=safe_json(before['health_json'])
            after_health=safe_json(after['health_json'])
            return {'before_audit_id':before['id'],'after_audit_id':after['id'],
                    'problem_count':{'before':count(before),'after':count(after)},
                    'reference_conflicts':{'before':conflicts(before),'after':conflicts(after)},
                    'resolved_problem_types':sorted(codes(before)-codes(after)),
                    'new_problem_types':sorted(codes(after)-codes(before)),
                    'remaining_problem_types':sorted(codes(after)&codes(before)),
                    'health':{k:{'before':before_health.get(k),'after':after_health.get(k)}
                              for k in ('identity','publication','normalization','acquisition')},
                    'counts':{k:{'before':before[k],'after':after[k]}
                              for k in ('logical_chapters','final_volumes','mapped_chapters','unmapped_chapters')}}

    def save_audit(self, work_id, record, holes, con=None):
        from ddk_review import problem_policy, health, issue_signature
        with self.lock, (self.con() if con is None else nullcontext(con)) as c:
            if con is None:c.execute('BEGIN IMMEDIATE')
            if record.get('catalog_guard') and record['catalog_guard']!=self.catalog.audit_guard(work_id,con=c):
                raise AuditSuperseded('Effective catalog dependencies changed during audit; rerun required.')
            previous=c.execute('SELECT id FROM search_audits WHERE work_id=? ORDER BY id DESC LIMIT 1',(work_id,)).fetchone()
            previous_revision=c.execute('SELECT count(*) FROM search_audits WHERE work_id=?',(work_id,)).fetchone()[0]
            cur = c.execute('''
                INSERT INTO search_audits(
                    work_id,query,workflow,match_title,match_tier,group_confidence,group_reason,
                    provider_count,selected_source,selected_source_name,selected_chapters,
                    selected_native_volumes,selected_standalone,reported_chapters,reported_volumes,
                    language_fallback,resolution_error,provider_states_json,provider_rows_json,
                    inventories_json,enrichment_errors_json,alias_retry,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ''', (
                work_id, record.get('query',''), record.get('workflow','volume'),
                record.get('match_title'), record.get('match_tier'), record.get('group_confidence'),
                record.get('group_reason'), int(record.get('provider_count') or 0),
                record.get('selected_source'), record.get('selected_source_name'),
                int(record.get('selected_chapters') or 0), int(record.get('selected_native_volumes') or 0),
                int(record.get('selected_standalone') or 0), json_text(record.get('reported_chapters') or []),
                json_text(record.get('reported_volumes') or []), int(bool(record.get('language_fallback'))),
                record.get('resolution_error') or '', json_text(record.get('provider_states') or []),
                json_text(record.get('provider_rows') or []), json_text(record.get('inventories') or []),
                json_text(record.get('enrichment_errors') or {}), record.get('alias_retry') or '', now(),
            ))
            audit_id = cur.lastrowid
            work=c.execute('SELECT edition,language FROM works WHERE id=?',(work_id,)).fetchone()
            c.execute('''UPDATE search_audits SET ddk_version=?,search_core_version=?,schema_version=?,
                requested_edition=?,requested_language=? WHERE id=?''',
                (record.get('ddk_version') or VERSION,record.get('search_core_version') or SEARCH_CORE_VERSION,
                 SCHEMA_VERSION,record.get('requested_edition') or work['edition'],
                 record.get('requested_language') or work['language'],audit_id))
            publication = deepcopy(record.get('publication') or {})
            publication['supplementary_revision']=self.supplementary.revision(work_id,c)
            publication['supplementary_identity']=self.supplementary.resolve(publication,work_id,con=c)
            final_state = ('ERROR' if any(h['code'] in ('SOURCE_FAILURE','AUDIT_ERROR') and h['severity'] == 'error' for h in holes)
                           else 'REVIEW' if holes else 'PASS')
            c.execute('''UPDATE search_audits SET publication_json=?,selected_edition=?,
                         logical_chapters=?,final_volumes=?,mapped_chapters=?,unmapped_chapters=?,
                         final_state=?,run_status=?,audit_revision=?,health_json=? WHERE id=?''', (
                json_text(publication), publication.get('edition'),
                publication.get('logical_chapters'), publication.get('final_volumes'),
                publication.get('mapped_chapters'), publication.get('unmapped_chapters'),
                final_state, 'Failed' if final_state == 'ERROR' else 'Audited', previous_revision+1,
                json_text(health(publication,[{'problem_type':h['code']} for h in holes],record.get('requested_edition','standard'))), audit_id,
            ))
            for hole in holes:
                cls,action,role,sufficient=problem_policy(hole['code'],hole.get('details'))
                hcur=c.execute('''
                    INSERT INTO audit_holes(audit_id,work_id,code,severity,message,details_json,created_at,
                                            problem_class,next_action,problem_role,evidence_sufficient)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)
                ''', (
                    audit_id, work_id, hole['code'], hole['severity'], hole['message'],
                    json_text(hole.get('details') or {}), now(),cls,action,role,int(sufficient),
                ))
                if previous and hole['code']=='UNCLASSIFIED_ACQUISITION':
                    current=c.execute('SELECT * FROM audit_holes WHERE id=?',(hcur.lastrowid,)).fetchone()
                    signature=issue_signature(current,publication)
                    prior=c.execute('''SELECT d.* FROM problem_dispositions d JOIN audit_holes h ON h.id=d.problem_row_id
                        WHERE h.audit_id=? AND d.signature=? AND d.status='IGNORED_WITH_REASON'
                        ORDER BY d.id DESC LIMIT 1''',(previous['id'],signature)).fetchone()
                    if prior:
                        c.execute('''INSERT INTO problem_dispositions(problem_row_id,work_id,audit_id,signature,status,
                                     problem_class,reason,verification,pattern,provider,created_at)
                                     VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
                                  (hcur.lastrowid,work_id,audit_id,signature,prior['status'],prior['problem_class'],
                                   prior['reason'],prior['verification'],prior['pattern'],prior['provider'],now()))
            canonical = record.get('match_title') or None
            identity=(publication.get('catalog_identity') or {})
            claim=identity.get('canonical_work_id') if identity.get('trusted') else None
            identity_status = 'resolved' if canonical and not any(h['code'] in ('NO_CANONICAL_RESULT','NO_USABLE_PROVIDER','WRONG_EDITION_MATCH') for h in holes) else 'review'
            c.execute('''UPDATE works SET canonical_title=COALESCE(?,canonical_title),identity_status=?,
                         canonical_work_id=COALESCE(?,canonical_work_id),last_harvested_at=?,updated_at=? WHERE id=?''',
                      (canonical, identity_status, claim, now(), now(), work_id))
            work=c.execute('SELECT edition FROM works WHERE id=?',(work_id,)).fetchone()
            self._refresh_audit_health(c,audit_id,publication,work['edition'] or 'standard')
            self.acceptance.recalculate(work_id,con=c)
        return audit_id

    def audit_csv(self, path):
        rows = self.holes()
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(['Title','Severity','Hole','Detail','Audit Date'])
            for r in rows:
                w.writerow([r['title'],r['severity'],r['code'],r['message'],r['audit_created_at']])
        return len(rows)

    def audit_summary_csv(self, path):
        rows = self.works()
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(['Query','Matched Title','Edition','Providers','Selected Source','Logical Chapters',
                        'Final Volumes','Mapped','Unmapped','Classified Provider Artifacts',
                        'Provider Artifact Breakdown','Unclassified Records',
                        'Holes','Audit State','Run Status','Audited'])
            for r in rows:
                classified=publication_classification_counts(safe_json(r['publication_json']))
                w.writerow([
                    r['input_title'],r['match_title'] or '',r['selected_edition'] or '',r['provider_count'] or 0,
                    r['selected_source_name'] or r['selected_source'] or '',r['logical_chapters'],
                    r['final_volumes'],f"{r['mapped_chapters']}/{r['logical_chapters']}" if r['mapped_chapters'] is not None else '',
                    r['unmapped_chapters'],classified['classified_provider_artifacts'],
                    json_text(classified['provider_artifact_breakdown']),classified['unclassified_records'],
                    r['hole_count'] or 0,audit_status(r),
                    r['run_status'] or '',r['audit_created_at'] or '',
                ])
        return len(rows)


class SearchAuditor:
    def __init__(self, db: DB, events: queue.Queue):
        self.db = db
        self.events = events
        self.stop_event = threading.Event()
        self.sources = (
            MangaDexSource(), MangaPillSource(), WeebCentralSource(), MangaKSource(), AtsuSource()
        )
        self.registry = SourceRegistry(self.sources)

    def emit(self, kind, **payload):
        self.events.put((kind, payload))

    def stop(self):
        self.stop_event.set()

    def _parallel_provider_search(self, query, language, only_source_ids=None, alias=False):
        coordinator = SourceCoordinator(
            self.registry,
            tuple(s for s in self.sources if only_source_ids is None or s.source_id in only_source_ids),
        )
        results = []
        with ThreadPoolExecutor(max_workers=max(1, len(coordinator.sources)), thread_name_prefix='ddk-search') as pool:
            futures = {}
            for source in coordinator.sources:
                coordinator.mark_running(source.source_id)
                futures[pool.submit(
                    source.search, query, 0, SEARCH_LIMIT, False, language, {}
                )] = source
            for future in as_completed(futures):
                source = futures[future]
                if self.stop_event.is_set():
                    break
                try:
                    page = future.result()
                    normalized = coordinator.complete(source.source_id, page)
                    results.extend(normalized.get('rows') or ())
                except Exception as exc:
                    coordinator.fail(source.source_id, exc)
        snap = coordinator.snapshot()
        return results, snap

    @staticmethod
    def _compact_provider_rows(rows):
        out = []
        for row in rows or ():
            out.append({
                'source_id': row.get('source_id'),
                'source_name': row.get('source_name'),
                'id': row.get('id'),
                'url': row.get('url'),
                'title': row.get('_provider_native_title') or row.get('title'),
                'author': row.get('author') or '',
                'canonical_title': row.get('canonical_title') or '',
                'canonical_work_id': row.get('canonical_work_id') or '',
                'edition': row.get('edition') or row.get('_edition') or '',
                'canonical_aliases': row.get('canonical_aliases') or [],
                'alternate_titles': row.get('alternate_titles') or [],
                'identity_confidence': row.get('_canonical_identity_confidence') or '',
            })
        return out[:80]

    @staticmethod
    def _inventory_rows(resolution):
        out = []
        for inv in getattr(resolution, 'inventories', ()) or ():
            out.append({
                'source_id': inv.source_id,
                'source_name': inv.source_name,
                'chapter_count': inv.chapter_count,
                'native_volumes': inv.native_volumes,
                'native_volume_metadata': inv.native_volume_metadata,
                'standalone_chapters': inv.standalone_chapters,
                'complete': bool(inv.complete),
                'usable': bool(inv.usable),
                'error': inv.error,
                'summary': inv.summary,
                'result_title':inv.result.get('_provider_native_title') or inv.result.get('title') or '',
                'result_ref':inv.result.get('url') or inv.result.get('id') or '',
            })
        return out

    def audit_one(self, work_id, workflow='volume', item_uuid=None):
        item=self.db.working_sets.item(item_uuid) if item_uuid else None
        work = dict(self.db.work(work_id)) if work_id else ({'input_title':item['original_query'],
            'edition':item['requested_edition'],'language':item['requested_language']} if item else None)
        if not work:
            return
        query = item['original_query'] if item else work['input_title']
        captured_guard=self.db.catalog.audit_guard(work_id)
        def identity_ready(identity):
            nonlocal captured_guard
            target=work_id
            if item:
                try:target=self.db.working_sets.resolve_work(item,identity)
                except ValueError as exc:raise IntakeIdentityReview(str(exc)) from exc
                if self.db.working_sets.mark_duplicate_if_known(item_uuid,identity):raise DuplicateIntake()
            captured_guard=self.db.catalog.audit_guard(target)
            return target
        language = work['language'] or 'en'
        self.emit('status', work_id=work_id, text='Searching MangaAnkā providers', progress=12)

        provider_rows, provider_snapshot = self._parallel_provider_search(query, language)
        if self.stop_event.is_set():
            raise CancelledError()

        self.emit('status', work_id=work_id, text='Running AniList / Kitsu enrichment', progress=30)
        external_candidates = ()
        enrichment_errors = {}
        try:
            external_candidates, enrichment_errors = DEFAULT_ENRICHMENT_REGISTRY.search(query, timeout=5.0)
        except Exception as exc:
            enrichment_errors = {'enrichment': str(exc)}

        alias_retry = ''
        alias = trusted_alias_for_query(query, external_candidates)
        if not alias:
            normalized = normalize_identity_text(query)
            if ' ' not in normalized and len(normalized) >= 8:
                alias = normalized[:4]
        if alias and normalize_identity_text(alias) != normalize_identity_text(query):
            present = {r.get('source_id') for r in provider_rows}
            missing = {s.source_id for s in self.sources if s.source_id not in present}
            if missing:
                self.emit('status', work_id=work_id, text=f'Alias retry: {alias}', progress=42)
                retry_rows, retry_snapshot = self._parallel_provider_search(alias, language, missing, alias=True)
                existing = {(r.get('source_id'), r.get('id'), r.get('url')) for r in provider_rows}
                provider_rows.extend(
                    r for r in retry_rows
                    if (r.get('source_id'), r.get('id'), r.get('url')) not in existing
                )
                # Merge terminal state view without overwriting successful first-pass states.
                state_map = {p['source_id']: dict(p) for p in provider_snapshot.get('providers') or ()}
                for p in retry_snapshot.get('providers') or ():
                    if state_map.get(p['source_id'], {}).get('status') != 'complete':
                        state_map[p['source_id']] = dict(p)
                provider_snapshot = dict(provider_snapshot)
                provider_snapshot['providers'] = tuple(state_map.get(s.source_id, {'source_id':s.source_id,'display_name':s.display_name,'status':'pending','error':''}) for s in self.sources)
                alias_retry = alias

        self.emit('status', work_id=work_id, text='Applying current search enrichment + ranking', progress=55)
        overlays = {}
        if external_candidates:
            try:
                for row in enrich_content_results(provider_rows, external_candidates):
                    key=(str(row.get('source_id') or ''),str(row.get('id') or row.get('url') or ''))
                    if all(key): overlays[key]=dict(row)
            except Exception as exc:
                enrichment_errors['overlay'] = str(exc)
        effective_rows = list(effective_search_rows(provider_rows, overlays))

        ranked = list(rank_canonical_results(query, effective_rows, False))[:RESOLUTION_LIMIT]
        holes = []
        selected_ranked = None
        selected_resolution = None
        all_resolution_summaries = []

        if not provider_rows:
            holes.append({'code':'NO_CANONICAL_RESULT','severity':'error','message':'Current MangaAnkā search returned no content-provider results.'})
        if provider_rows and not ranked:
            holes.append({'code':'NO_CANONICAL_RESULT','severity':'error','message':'Providers returned rows, but current MangaAnkā relevance gating accepted no canonical match.'})

        self.emit('status', work_id=work_id, text='Qualifying provider inventories', progress=68)
        metadata_cache = {}
        inventory_cache = {}
        budget = [16]
        usable_candidates = []
        for ranked_row in ranked:
            if self.stop_event.is_set():
                raise CancelledError()
            try:
                resolution = resolve_search_group(
                    self.registry, ranked_row.group.results, language, workflow,
                    metadata_cache, inventory_cache, None, False, inspection_budget=budget,
                )
            except Exception as exc:
                resolution = None
                all_resolution_summaries.append({'title':ranked_row.group.display_title,'error':str(exc)})
                continue
            all_resolution_summaries.append({
                'title': ranked_row.group.display_title,
                'usable': bool(resolution.usable),
                'error': resolution.error,
                'language': resolution.language,
                'language_fallback': bool(resolution.language_fallback),
                'inventories': self._inventory_rows(resolution),
            })
            if resolution.usable:
                key = tuple(ranked_row.sort_key)
                key = key[:4] + (1 if resolution.language_fallback else 0,) + key[4:]
                usable_candidates.append((key, ranked_row, resolution))

        if usable_candidates:
            _, selected_ranked, selected_resolution = sorted(usable_candidates, key=lambda x:x[0])[0]
        elif ranked:
            selected_ranked = ranked[0]
            try:
                selected_resolution = resolve_search_group(
                    self.registry, selected_ranked.group.results, language, workflow,
                    metadata_cache, inventory_cache, None, False, inspection_budget=budget,
                )
            except Exception:
                selected_resolution = None

        match_title = selected_ranked.group.display_title if selected_ranked else ''
        match_tier = selected_ranked.match.tier.name if selected_ranked else ''
        group_confidence = selected_ranked.group.confidence if selected_ranked else ''
        group_reason = selected_ranked.group.reason if selected_ranked else ''

        if selected_ranked and int(selected_ranked.match.tier) < int(MatchTier.ALL_TOKENS):
            holes.append({
                'code':'WEAK_SEARCH_MATCH','severity':'error',
                'message':f'Best current-search match is only {selected_ranked.match.tier.name}: {match_title}.',
            })

        inventories = self._inventory_rows(selected_resolution) if selected_resolution else []
        primary = getattr(selected_resolution, 'primary', None) if selected_resolution else None
        if ranked and not (selected_resolution and selected_resolution.usable):
            reason = (selected_resolution.error if selected_resolution else '') or 'No provider inventory qualified.'
            holes.append({'code':'NO_USABLE_PROVIDER','severity':'error','message':reason})
        if not primary:
            failed = [p for p in provider_snapshot.get('providers') or () if p.get('status') == 'failed']
            if failed:
                holes.append({'code':'SOURCE_FAILURE','severity':'error',
                              'message':'Provider requests failed and no usable acquisition was resolved.',
                              'details':{'providers':failed}})

        selected_chapters = int(getattr(primary, 'chapter_count', 0) or 0)
        selected_volumes = int(getattr(primary, 'native_volumes', 0) or 0)
        selected_standalone = int(getattr(primary, 'standalone_chapters', 0) or 0)
        group_rows = list(selected_ranked.group.results) if selected_ranked else []
        chapter_totals, volume_totals = reported_totals(group_rows)
        provenance = []
        seen_provenance = {}
        for row in group_rows:
            for context in row.get('volume_context') or ():
                if isinstance(context, dict):
                    key=(context.get('provenance'),context.get('reported_total_chapters'),
                         context.get('reported_total_volumes'),context.get('retrieved_at'))
                    if key not in seen_provenance:
                        count_source=dict(context, provider_records=[],canonical_work_id=row.get('canonical_work_id'))
                        seen_provenance[key]=count_source;provenance.append(count_source)
                    source=row.get('source_id')
                    if source and source not in seen_provenance[key]['provider_records']:
                        seen_provenance[key]['provider_records'].append(source)
        publication = {}
        if primary and selected_resolution.usable:
            self.emit('status', work_id=work_id, text='Resolving publication references and final volumes', progress=82)
            try:
                publication = resolve_publication(selected_resolution, effective_rows, external_candidates,
                                                  metadata_cache, self.stop_event.is_set, catalog=self.db.catalog, catalog_work_id=work_id,
                                                  on_identity=identity_ready)
            except CancelledError:
                raise
            except DuplicateIntake:
                self.emit('status',work_id=item_uuid,text='Duplicate canonical intake retained',progress=100)
                return
            except IntakeIdentityReview:
                raise
            except Exception as exc:
                edition = edition_identity(primary.result)
                publication = {'status': 'failed', 'error': str(exc),
                               'edition': 'standard' if edition == 'original' else edition}
            publication['reported_count_provenance'] = provenance
            if publication.get('status')=='complete':
                publication['structural_coverage']=evaluate_structure_coverage(publication,provenance)
            if publication.get('automatic') is not None:
                publication['automatic']['reported_count_provenance'] = provenance
            holes.extend(publication_holes(publication, primary, work['edition'] or 'standard'))
        if self.stop_event.is_set():
            raise CancelledError()

        publication['curation_revision'] = captured_guard['revision']
        publication['catalog_dependencies'] = captured_guard
        publication['reported_count_provenance'] = provenance
        if publication.get('automatic') is not None:
            publication['automatic']['reported_count_provenance'] = provenance
        record = {
            'query': query,
            'requested_edition': work['edition'],
            'requested_language': language,
            'publication': publication,
            'catalog_guard':captured_guard,
            'workflow': workflow,
            'match_title': match_title,
            'match_tier': match_tier,
            'group_confidence': group_confidence,
            'group_reason': group_reason,
            'provider_count': len({r.get('source_id') for r in group_rows if r.get('source_id')}),
            'selected_source': getattr(primary, 'source_id', '') if primary else '',
            'selected_source_name': getattr(primary, 'source_name', '') if primary else '',
            'selected_chapters': selected_chapters,
            'selected_native_volumes': selected_volumes,
            'selected_standalone': selected_standalone,
            'reported_chapters': chapter_totals,
            'reported_volumes': volume_totals,
            'language_fallback': bool(getattr(selected_resolution, 'language_fallback', False)) if selected_resolution else False,
            'resolution_error': getattr(selected_resolution, 'error', '') if selected_resolution else '',
            'provider_states': list(provider_snapshot.get('providers') or ()),
            'provider_rows': self._compact_provider_rows(effective_rows),
            'inventories': inventories,
            'enrichment_errors': enrichment_errors,
            'alias_retry': alias_retry,
            'resolution_candidates': all_resolution_summaries,
        }
        if item:
            identity=publication.get('catalog_identity') or {}
            try:
                outcome=self.db.working_sets.persist_item_audit(item_uuid,identity,record,holes)
                if outcome is None:
                    self.db.working_sets.observe_unresolved(item_uuid,record,holes)
                    self.emit('status', work_id=item_uuid, text='Identity unresolved; intake retained for review',progress=100)
                    return
                self.emit('status', work_id=item_uuid, text='Audited',progress=100)
            except IntakeIdentityReview as exc:
                self.db.working_sets.observe_unresolved(item_uuid,record,[*holes,
                    {'code':'INTAKE_IDENTITY_REVIEW','severity':'warning','message':str(exc)}])
                self.emit('status',work_id=item_uuid,text=str(exc),progress=100)
        else:
            self.db.save_audit(work_id, record, holes)
            self.emit('status', work_id=work_id, text='Audited', progress=100)

    def audit_many(self, work_ids, workflow):
        self.stop_event.clear()
        pending=list(dict.fromkeys(work_ids)); retries={}; processed=[]
        before={r['work_uuid'] for r in self.db.works()}
        while pending and not self.stop_event.is_set():
            work_id=pending.pop(0)
            item=self.db.working_sets.item(work_id) if isinstance(work_id,str) else None
            work=self.db.work(work_id) if not item else None
            self.emit('batch',text=f'{len(processed)+1}/{len(processed)+len(pending)+1}  {item["original_query"] if item else work["input_title"] if work else work_id}')
            try:
                if item:
                    self.db.working_sets.guard(item_uuid=work_id)
                    if item['processing_status'] in ('ACCEPTED','REJECTED','DUPLICATE'):continue
                    self.db.working_sets.set_item_status(work_id,'AUDITING')
                    self.audit_one(item['work_id'],item['requested_workflow'],item_uuid=work_id)
                else:self.audit_one(work_id,workflow)
            except CancelledError:
                if item:self.db.working_sets.set_item_status(work_id,'QUEUED')
                break
            except AuditSuperseded as exc:
                if item:
                    self.db.working_sets.set_item_status(work_id,'QUEUED')
                    retries[work_id]=retries.get(work_id,0)+1
                    if retries[work_id]==1:pending.append(work_id)
                self.emit('status',work_id=work_id,text=str(exc),progress=0)
            except Exception as exc:
                record={'query':item['original_query'] if item else work['input_title'] if work else str(work_id),
                        'workflow':item['requested_workflow'] if item else workflow,
                        'resolution_error':str(exc),'provider_states':[], 'provider_rows':[],
                        'inventories':[], 'enrichment_errors':{}}
                review=isinstance(exc,IntakeIdentityReview)
                errors=[{'code':'INTAKE_IDENTITY_REVIEW' if review else 'AUDIT_ERROR',
                         'severity':'warning' if review else 'error','message':str(exc)}]
                if item:
                    try:self.db.working_sets.observe_unresolved(work_id,record,errors,status='REVIEW' if review else 'ERROR')
                    except ValueError:self.emit('status',text=str(exc),progress=0)
                elif work:self.db.save_audit(work_id,record,errors)
            processed.append(work_id)
            self.emit('refresh')
        attempted=[self.db.working_sets.item(uid) for uid in dict.fromkeys(processed) if isinstance(uid,str)]
        requested_items=[self.db.working_sets.item(uid) for uid in dict.fromkeys(work_ids) if isinstance(uid,str)]
        sets={i['working_set_uuid'] for i in requested_items if i}
        final=[i for uid in sets for i in self.db.working_sets.items(uid)]
        counts={state:sum(i and i['processing_status']==state for i in final) for state in
                ('PENDING','QUEUED','AUDITING','READY','REVIEW','ERROR','ACCEPTED','REJECTED','DUPLICATE')}
        reused=sum(bool(i and i['linked_work_uuid'] in before) for i in attempted if i and i['processing_status']!='DUPLICATE')
        created={i['linked_work_uuid'] for i in attempted if i and i['linked_work_uuid'] and i['linked_work_uuid'] not in before}
        summary=f'Run ended: {len(final)} set items · Ready {counts["READY"]} · Review {counts["REVIEW"]} · Error {counts["ERROR"]} · Accepted {counts["ACCEPTED"]} · Rejected {counts["REJECTED"]} · Duplicate {counts["DUPLICATE"]} · Pending {counts["PENDING"]} · Queued {counts["QUEUED"]} · Reused {reused} · New {len(created)} · Duplicate works created 0. Accept All Safe / Open Review Items / Retry Errors.'
        self.emit('done',text=summary,counts=counts,reused=reused,new=len(created))


class App(tk.Tk):
    def __init__(self, workspace=None):
        super().__init__()
        self.title(f'{APP}  v{VERSION}')
        self.geometry('1550x930')
        self.minsize(1120, 720)
        self.configure(bg=BG)

        self.ws = Path(workspace) if workspace else Path.home() / 'Documents' / 'MangaAnka-Database-Development-Kit'
        self.ws.mkdir(parents=True, exist_ok=True)
        active=saved_path(self.ws) or self.ws / 'mangaanka_catalog.db'
        try:self.writer_lock=WriterLock(active)
        except Exception:
            super().destroy();raise
        try:self.db = DB(active)
        except Exception:
            self.writer_lock.close();super().destroy();raise
        self.db.working_sets.recover_interrupted()
        self.active_set_uuid=self.db.working_sets.active_uuid()
        self.queue_ids=[r['working_set_item_uuid'] for r in self.db.working_sets.items(self.active_set_uuid)
                        if r['processing_status'] in ('QUEUED','AUDITING','ERROR')]
        self.events = queue.Queue()
        self.auditor = SearchAuditor(self.db, self.events)
        self.worker = None
        self._active_work_id = None
        self._active_hole = None

        self.style_ui()
        self.build()
        self.refresh_all()
        self.after(100, self.poll)
        self.protocol('WM_DELETE_WINDOW', self.close)

    def style_ui(self):
        s = ttk.Style(self)
        try:
            s.theme_use('clam')
        except Exception:
            pass
        self.option_add('*Font', ('Segoe UI', 10))
        self.option_add('*TCombobox*Listbox.background', PANEL2)
        self.option_add('*TCombobox*Listbox.foreground', TEXT)
        self.option_add('*TCombobox*Listbox.selectBackground', ACCENT_DARK)
        self.option_add('*TCombobox*Listbox.selectForeground', '#FFFFFF')

        s.configure('.', background=BG, foreground=TEXT)
        s.configure('TFrame', background=BG)
        s.configure('TLabel', background=BG, foreground=TEXT)
        s.configure('TCheckbutton',background=BG,foreground=TEXT)
        s.map('TCheckbutton',background=[('active',BG)],foreground=[('active',TEXT)])
        s.configure('Muted.TLabel', background=BG, foreground=MUTED)
        s.configure('Title.TLabel', background=BG, foreground=TEXT, font=('Segoe UI Semibold', 18))
        s.configure('TButton', background=PANEL2, foreground=TEXT, bordercolor=BORDER, padding=(10,6))
        s.map('TButton', background=[('active',PANEL3)], foreground=[('disabled','#777C85')])
        s.configure('Accent.TButton', background=ACCENT, foreground='#FFFFFF', padding=(12,7))
        s.map('Accent.TButton', background=[('active','#FF7B5A')], foreground=[('disabled','#B0B0B0')])
        s.configure('TNotebook', background=BG, borderwidth=0)
        s.configure('TNotebook.Tab', background=PANEL, foreground=MUTED, padding=(18,9))
        s.map('TNotebook.Tab', background=[('selected',PANEL3)], foreground=[('selected','#FFFFFF')])
        s.configure('Treeview', background=PANEL, fieldbackground=PANEL, foreground=TEXT, rowheight=28, bordercolor=BORDER)
        s.configure('Treeview.Heading', background=PANEL3, foreground='#FFFFFF', relief='flat')
        s.map('Treeview', background=[('selected',ACCENT_DARK)], foreground=[('selected','#FFFFFF')])
        s.map('Treeview.Heading', background=[('active','#3B4048')])
        s.configure('TEntry', fieldbackground=PANEL2, foreground=TEXT, insertcolor=TEXT, bordercolor=BORDER)
        s.configure('TCombobox', fieldbackground=PANEL2, background=PANEL2, foreground=TEXT, arrowcolor=TEXT, bordercolor=BORDER)
        s.map('TCombobox',
              fieldbackground=[('readonly',PANEL2),('disabled','#202226')],
              background=[('readonly',PANEL2)],
              foreground=[('readonly','#FFFFFF'),('disabled','#858A93')],
              selectbackground=[('readonly',PANEL2)],
              selectforeground=[('readonly','#FFFFFF')])
        s.configure('TProgressbar', troughcolor=PANEL2, background=ACCENT)
        s.configure('TLabelframe', background=BG, foreground=TEXT, bordercolor=BORDER)
        s.configure('TLabelframe.Label', background=BG, foreground=TEXT)
        s.configure('Vertical.TScrollbar', background=PANEL3, troughcolor=PANEL, arrowcolor=TEXT)
        s.configure('Horizontal.TScrollbar', background=PANEL3, troughcolor=PANEL, arrowcolor=TEXT)

    def text_widget(self, parent, height=8, wrap='word'):
        frame = ttk.Frame(parent)
        text = tk.Text(frame, height=height, wrap=wrap, bg=PANEL, fg=TEXT,
                       insertbackground=TEXT, selectbackground=ACCENT_DARK,
                       selectforeground='#FFFFFF', relief='flat', padx=8, pady=8)
        vs = ttk.Scrollbar(frame, orient='vertical', command=text.yview)
        text.configure(yscrollcommand=vs.set)
        text.grid(row=0,column=0,sticky='nsew')
        vs.grid(row=0,column=1,sticky='ns')
        if wrap == 'none':
            hs = ttk.Scrollbar(frame, orient='horizontal', command=text.xview)
            text.configure(xscrollcommand=hs.set)
            hs.grid(row=1,column=0,sticky='ew')
        frame.rowconfigure(0,weight=1); frame.columnconfigure(0,weight=1)
        return frame, text

    def tree_widget(self, parent, columns, headings, widths, selectmode='browse', anchors=None):
        frame = ttk.Frame(parent)
        tree = ttk.Treeview(frame, columns=columns, show='headings', selectmode=selectmode)
        anchors = anchors or {}
        for c, label, width in zip(columns, headings, widths):
            tree.heading(c, text=label)
            tree.column(c, width=width, minwidth=55, anchor=anchors.get(c,'center'), stretch=(c == columns[-1] or c == columns[0]))
        vs = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        hs = ttk.Scrollbar(frame, orient='horizontal', command=tree.xview)
        tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        tree.grid(row=0,column=0,sticky='nsew')
        vs.grid(row=0,column=1,sticky='ns')
        hs.grid(row=1,column=0,sticky='ew')
        frame.rowconfigure(0,weight=1); frame.columnconfigure(0,weight=1)
        return frame, tree

    def build(self):
        header = ttk.Frame(self, padding=(18,14))
        header.pack(fill='x')
        ttk.Label(header, text=APP, style='Title.TLabel').pack(side='left')
        ttk.Label(header, text=f'v{VERSION}  •  current MangaAnkā search audit', style='Muted.TLabel').pack(side='left', padx=(12,0))
        ttk.Label(header, text=f'Search core: v{SEARCH_CORE_VERSION} {SEARCH_CORE_CODENAME}', style='Muted.TLabel').pack(side='right', padx=(0,12))
        database=ttk.Frame(self);database.pack(fill='x',padx=18,pady=(0,8))
        self.database_label=tk.StringVar()
        ttk.Label(database,textvariable=self.database_label,style='Muted.TLabel',
                  wraplength=700,justify='left').pack(side='left',fill='x',expand=True)
        ttk.Button(database,text='Open Folder',command=self.open_ws).pack(side='right')
        ttk.Button(database,text='New Database',command=self.new_database).pack(side='right',padx=5)
        ttk.Button(database,text='Switch Database',command=self.choose_database).pack(side='right',padx=5)
        working=ttk.Frame(self);working.pack(fill='x',padx=18,pady=(0,8))
        self.working_set_label=tk.StringVar(value='ACTIVE WORKING SET  None')
        ttk.Label(working,textvariable=self.working_set_label,style='Muted.TLabel',
                  wraplength=800,justify='left').pack(side='left',fill='x',expand=True)
        ttk.Button(working,text='New Working Set',command=self.new_working_set).pack(side='right')
        ttk.Button(working,text='Switch Working Set',command=self.switch_working_set).pack(side='right',padx=5)
        self.set_more=ttk.Menubutton(working,text='Status: NONE',state='disabled')
        self.set_more.pack(side='right',padx=5)
        set_menu=tk.Menu(self.set_more,tearoff=False)
        self.set_menu=set_menu
        for label,status in (('Open','OPEN'),('Review','REVIEW'),('Complete','COMPLETE'),('Archive','ARCHIVED')):
            set_menu.add_command(label=label,command=lambda state=status:self.change_working_set_status(state))
        set_menu.add_command(label='Reopen for Review',command=self.reopen_working_set)
        self.set_more.configure(menu=set_menu)

        self.shared_scope=tk.StringVar(value='Scope: Active Working Set')
        ttk.Label(self,textvariable=self.shared_scope,style='Muted.TLabel').pack(fill='x',padx=18,pady=(0,5))
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill='both', expand=True, padx=14, pady=(0,14))
        self.tabs = []
        for name in ('Audit','Titles','Problems','Details'):
            f = ttk.Frame(self.nb, padding=12)
            self.tabs.append(f)
        self.database_tab = ttk.Frame(self.nb, padding=12)
        self.catalog_tab = ttk.Frame(self.nb, padding=12)
        self.history_tab = ttk.Frame(self.nb, padding=12)
        for frame, label in ((self.tabs[0],'Audit'),(self.tabs[2],'Problems'),
                             (self.catalog_tab,'Catalog'),(self.database_tab,'Curate'),
                             (self.history_tab,'History'),(self.tabs[3],'Details')):
            self.nb.add(frame,text=label)
        self.build_audit()
        self.build_titles()
        self.build_holes()
        self.build_catalog()
        self.build_details()
        self.editor = CatalogEditor(self, self.database_tab, self.history_tab)

    def build_audit(self):
        f = self.tabs[0]
        top = ttk.Frame(f)
        top.pack(fill='x')
        input_box = ttk.LabelFrame(top, text='Popular titles to audit', padding=10)
        input_box.pack(side='left', fill='both', expand=True)
        settings = ttk.LabelFrame(top, text='Audit settings', padding=10)
        settings.pack(side='left', fill='y', padx=(10,0))
        ttk.Label(input_box, text='Paste one manga title per line. The audit runs the current MangaAnkā search providers, enrichment, ranking, references, and final publication projection.').pack(anchor='w')
        text_frame, self.input = self.text_widget(input_box, height=8, wrap='none')
        text_frame.pack(fill='both', expand=True, pady=(6,8))
        b = ttk.Frame(input_box); b.pack(fill='x')
        ttk.Button(b,text='Paste',command=self.paste_titles).pack(side='left')
        ttk.Button(b, text='Import TXT / CSV', command=self.import_titles).pack(side='left')
        ttk.Button(b,text='Clear',command=lambda:self.input.delete('1.0','end')).pack(side='left')
        ttk.Button(b,text='Run Working Set',command=self.run_working_set).pack(side='left',padx=5)
        ttk.Button(b, text='Add to Queue', style='Accent.TButton', command=self.add_titles).pack(side='right')

        self.language = tk.StringVar(value='en')
        self.workflow = tk.StringVar(value='volume')
        self.edition = tk.StringVar(value='standard')
        ttk.Label(settings, text='Language').grid(row=0,column=0,sticky='w',pady=(0,4))
        ttk.Combobox(settings, textvariable=self.language, values=('en','ja'), state='readonly', width=18).grid(row=1,column=0,sticky='ew')
        ttk.Label(settings, text='Requested edition').grid(row=2,column=0,sticky='w',pady=(8,4))
        ttk.Combobox(settings, textvariable=self.edition,
                     values=('standard','official_color','fan_color','omnibus','deluxe','bunkobon','kanzenban'),
                     state='readonly', width=18).grid(row=3,column=0,sticky='ew')
        ttk.Label(settings, text='Workflow').grid(row=4,column=0,sticky='w',pady=(8,4))
        ttk.Combobox(settings, textvariable=self.workflow, values=('volume','chapter'), state='readonly', width=18).grid(row=5,column=0,sticky='ew')

        box = ttk.LabelFrame(f, text='Search audit queue', padding=8)
        box.pack(fill='both', expand=True, pady=(10,0))
        cols = ('query','match','edition','providers','source','chapters','volumes','mapped','unmapped','artifacts','unclassified','holes','state','status')
        heads = ('Query','Matched Title','Edition','Providers','Selected Source','Logical Chapters','Final Volumes','Mapped','Unmapped','Provider Artifacts','Unclassified','Holes','Audit State','Run Status')
        widths = (240,260,120,80,140,125,110,100,90,120,100,70,125,125)
        frame, self.audit_tree = self.tree_widget(box, cols, heads, widths, 'extended', {'query':'w','match':'w','source':'w','state':'w','status':'w'})
        frame.pack(fill='both', expand=True)
        self.audit_tree.bind('<Double-1>', lambda e:self.open_details_from(self.audit_tree))

        foot = ttk.Frame(f); foot.pack(fill='x', pady=(10,0))
        self.progress = ttk.Progressbar(foot, maximum=100, length=250); self.progress.pack(side='left')
        self.batch = tk.StringVar(value='Ready')
        ttk.Label(f, textvariable=self.batch, style='Muted.TLabel',wraplength=1000).pack(fill='x',pady=(4,0))
        ttk.Button(foot, text='Remove Selected', command=self.remove_selected).pack(side='right')
        ttk.Button(foot, text='Clear Queue', command=self.clear_queue).pack(side='right',padx=5)
        self.stop_button=ttk.Button(foot, text='Stop', command=self.auditor.stop,state='disabled')
        self.stop_button.pack(side='right', padx=6)
        self.start_button = ttk.Button(foot, text='Start Audit', style='Accent.TButton', command=self.start_audit)
        self.start_button.pack(side='right')
        export=ttk.Menubutton(foot,text='Export ▾');export.pack(side='right',padx=5)
        menu=tk.Menu(export,tearoff=False);menu.add_command(label='Summary CSV',command=self.export_summary)
        export.configure(menu=menu)

    def build_titles(self):
        f = self.tabs[1]
        top = ttk.Frame(f); top.pack(fill='x')
        ttk.Label(top, text='Audited Titles', style='Title.TLabel').pack(side='left')
        ttk.Button(top, text='Export Summary CSV', command=self.export_summary).pack(side='right')
        cols = ('query','match','edition','providers','source','chapters','volumes','mapped','unmapped','artifacts','unclassified','holes','state','audited')
        heads = ('Query','Matched Title','Edition','Providers','Selected Source','Logical Chapters','Final Volumes','Mapped','Unmapped','Provider Artifacts','Unclassified','Holes','Audit State','Last Audited')
        widths = (230,250,120,75,140,125,110,100,90,120,100,70,125,165)
        frame, self.title_tree = self.tree_widget(f, cols, heads, widths, 'browse', {'query':'w','match':'w','source':'w','audited':'w'})
        frame.pack(fill='both', expand=True, pady=(10,0))
        self.title_tree.bind('<Double-1>', lambda e:self.open_details_from(self.title_tree))
        actions = ttk.Frame(f); actions.pack(fill='x', pady=(8,0))
        ttk.Button(actions, text='Open Details', command=lambda:self.open_details_from(self.title_tree)).pack(side='left')
        ttk.Button(actions, text='Audit Again', command=self.audit_again).pack(side='left', padx=6)

    def build_holes(self):
        f = self.tabs[2]
        top = ttk.Frame(f); top.pack(fill='x')
        ttk.Label(top, text='Publication Problems', style='Title.TLabel').pack(side='left')
        self.hole_filter = tk.StringVar(value='All')
        self.problem_view=tk.StringVar(value='Active Working Set' if self.active_set_uuid else 'All Catalog')
        self.problem_scope=ttk.Combobox(top,textvariable=self.problem_view,state='readonly',width=23,
                                         values=('Active Working Set','All Catalog','Accepted Master Catalog'))
        self.problem_scope.pack(side='right',padx=5)
        self.problem_scope.bind('<<ComboboxSelected>>',lambda e:self.refresh_holes())
        ttk.Label(top, text='Filter').pack(side='right', padx=(12,6))
        self.hole_combo = ttk.Combobox(top, textvariable=self.hole_filter, values=('All',), state='readonly', width=30)
        self.hole_combo.pack(side='right')
        self.hole_combo.bind('<<ComboboxSelected>>', lambda e:self.refresh_holes())
        self.show_ignored=tk.BooleanVar(value=False)
        ttk.Checkbutton(top,text='Show ignored',variable=self.show_ignored,
                        command=self.toggle_ignored).pack(side='right',padx=7)
        actions=ttk.Frame(f);actions.pack(fill='x',pady=(8,0))
        self.review_scope=tk.StringVar(value='All unresolved')
        ttk.Label(actions,text='Review scope').pack(side='left')
        ttk.Combobox(actions,textvariable=self.review_scope,state='readonly',width=19,
                     values=('All unresolved','Selected problems','Selected titles')).pack(side='left',padx=5)
        ttk.Label(actions,text='Class').pack(side='left',padx=(12,4))
        self.problem_class_filter=tk.StringVar(value='All')
        class_box=ttk.Combobox(actions,textvariable=self.problem_class_filter,state='readonly',width=14,
                               values=('All','DATA','CODE','ACQUISITION','RESEARCH','IDENTITY','UNKNOWN'))
        class_box.pack(side='left');class_box.bind('<<ComboboxSelected>>',lambda e:self.refresh_holes())
        ttk.Button(actions,text='Open in Curate',command=self.open_hole_details).pack(side='right',padx=4)
        ttk.Button(actions,text='Ignore',command=self.ignore_problem).pack(side='right',padx=4)
        copy=ttk.Menubutton(actions,text='Copy Diagnostic ▾');copy.pack(side='right',padx=4)
        copy_menu=tk.Menu(copy,tearoff=False)
        copy_menu.add_command(label='Selected Problem',command=lambda:self.copy_diagnostics(True))
        copy_menu.add_command(label='Selected Title',command=self.copy_selected_title_diagnostic)
        copy_menu.add_command(label='All Problems',command=lambda:self.copy_diagnostics(False))
        copy.configure(menu=copy_menu)
        export=ttk.Menubutton(actions,text='Export ▾');export.pack(side='right',padx=4)
        export_menu=tk.Menu(export,tearoff=False)
        export_menu.add_command(label='Review Packet',command=self.export_review_packet)
        export_menu.add_command(label='Detailed Issues CSV',command=self.export_detailed_problems)
        export_menu.add_command(label='Summary CSV',command=self.export_holes)
        export.configure(menu=export_menu)
        self.pattern_notice=tk.StringVar()
        ttk.Label(f,textvariable=self.pattern_notice,style='Muted.TLabel').pack(fill='x',pady=(5,0))
        cols = ('title','severity','code','class','next','confidence','affected','disposition','message','audited')
        heads = ('Title','Severity','Problem','Class','Next Action','Confidence','Affected','Disposition','Why It Was Flagged','Audit Date')
        widths = (240,80,205,100,150,95,80,135,600,160)
        frame, self.hole_tree = self.tree_widget(f, cols, heads, widths, 'extended', {'title':'w','code':'w','message':'w','audited':'w'})
        frame.pack(fill='both', expand=True, pady=(10,0))
        self.hole_tree.bind('<Double-1>', lambda e:self.open_hole_details())
        self.hole_tree.bind('<<TreeviewSelect>>', lambda e:self.problem_selected())
        pf,self.problem_text=self.text_widget(f,height=10,wrap='none')
        pf.pack(fill='both',expand=False,pady=(8,0))
        self.problem_text.configure(state='disabled')
        bottom=ttk.Frame(f);bottom.pack(fill='x',pady=(8,0))
        self.reopen_button=ttk.Button(bottom,text='Reopen Ignored Problem',command=self.reopen_ignored_problem)

    def toggle_ignored(self):
        if self.show_ignored.get():self.reopen_button.pack(side='right',padx=5)
        else:self.reopen_button.pack_forget()
        self.refresh_holes()

    def build_catalog(self):
        f=self.catalog_tab
        top=ttk.Frame(f);top.pack(fill='x')
        ttk.Label(top,text='Active Database Catalog',style='Title.TLabel').pack(side='left')
        self.catalog_view=tk.StringVar(value='Active Working Set' if self.active_set_uuid else 'All Catalog')
        self.catalog_scope=ttk.Combobox(top,textvariable=self.catalog_view,state='readonly',width=27)
        self.catalog_scope.pack(side='left',padx=10)
        self.catalog_scope.bind('<<ComboboxSelected>>',lambda e:self.refresh_all())
        ttk.Button(top,text='Export CSV',command=self.export_catalog).pack(side='right')
        ttk.Button(top,text='Refresh',command=self.refresh_catalog).pack(side='right',padx=5)
        actions=ttk.Frame(f);actions.pack(fill='x',pady=(5,0))
        self.copy_selected_menu=ttk.Menubutton(actions,text='Copy Selected ▾');self.copy_selected_menu.pack(side='left',padx=5)
        menu=tk.Menu(self.copy_selected_menu,tearoff=False)
        for label,kind in (('Summary','summary'),('Review Context','review'),('Full Details','full'),
                           ('CSV Row','csv'),('Diagnostic','diagnostic')):
            menu.add_command(label=label,command=lambda k=kind:self.copy_catalog_selected(k))
        self.copy_selected_menu.configure(menu=menu)
        ttk.Button(actions,text='Accept Selected',command=self.preview_accept_selected).pack(side='left',padx=5)
        set_actions=ttk.Menubutton(actions,text='Intake ▾');set_actions.pack(side='left',padx=4)
        intake_menu=tk.Menu(set_actions,tearoff=False)
        intake_menu.add_command(label='Remove Selected from Working Set',command=self.remove_selected_from_set)
        intake_menu.add_command(label='Reject Selected Intake',command=self.reject_selected_intake)
        intake_menu.add_command(label='Reopen Selected for Review',command=self.reopen_selected_items)
        set_actions.configure(menu=intake_menu)
        copy_set=ttk.Menubutton(actions,text='Copy Working Set ▾');copy_set.pack(side='left',padx=4)
        copy_menu=tk.Menu(copy_set,tearoff=False)
        for label,kind in (('Summary','summary'),('CSV (Pinned)','csv'),('Title List','titles'),
                           ('Review Context (Pinned)','review')):
            copy_menu.add_command(label=label,command=lambda k=kind:self.copy_working_set(k))
        copy_set.configure(menu=copy_menu)
        export_set=ttk.Menubutton(actions,text='Export Working Set ▾');export_set.pack(side='left',padx=4)
        export_menu=tk.Menu(export_set,tearoff=False)
        for label,kind in (('CSV (Pinned)','csv'),('CSV (Current)','current_csv'),
                           ('Review Packet (Pinned)','review'),('Detailed Issues CSV (Current)','issues'),
                           ('Title List','titles')):
            export_menu.add_command(label=label,command=lambda k=kind:self.export_working_set(k))
        export_set.configure(menu=export_menu)
        more=ttk.Menubutton(actions,text='More ▾');more.pack(side='left',padx=4)
        more_menu=tk.Menu(more,tearoff=False)
        maintenance_menu=tk.Menu(more_menu,tearoff=False)
        maintenance_menu.add_command(label='Delete Catalog Work...',command=self.preview_delete_catalog_work)
        more_menu.add_command(label='Reevaluate Acceptance...',command=self.reevaluate_acceptance)
        more_menu.add_cascade(label='Catalog Maintenance',menu=maintenance_menu)
        more.configure(menu=more_menu)
        self.catalog_more_menu=more_menu
        self.catalog_maintenance_menu=maintenance_menu
        workflow_bar=ttk.Frame(f);workflow_bar.pack(fill='x',pady=5)
        for label,fn in (('Run Working Set',self.run_working_set),('Accept All Safe',self.accept_all_safe),('Open Review Items',self.open_review_items),('Retry Errors',self.retry_errors)):
            ttk.Button(workflow_bar,text=label,command=fn).pack(side='left',padx=4)
        cols=('title','work_uuid','catalog_status','item_status','edition','language','identity','identity_health','publication_health',
              'normalization_health','acquisition_health','provider','chapters','volumes','mapped',
              'unmapped','artifacts','unclassified','curated','curation_revision','audit','audit_revision','freshness','pinned_audit','acceptance_state','latest_global_audit')
        heads=('Title','Work UUID','Catalog Status','Item Status','Edition','Language','Canonical Identity','Identity Health','Publication Health',
               'Normalization Health','Acquisition Health','Selected Provider','Canonical Chapters',
               'Volumes','Mapped','Unmapped','Provider Artifacts','Unclassified','Curated Fields',
               'Curation Revision','Snapshot Audit Date','Audit Revision','Audit Freshness','Pinned Audit','Acceptance State','Latest Global Audit')
        widths=(245,270,115,105,115,85,220,120,125,135,125,135,125,85,95,95,125,110,110,120,175,105,120,110,180,130)
        frame,self.catalog_tree=self.tree_widget(f,cols,heads,widths,'extended',{'title':'w','identity':'w','provider':'w'})
        frame.pack(fill='both',expand=True,pady=(8,4))
        self.catalog_tree.bind('<<TreeviewSelect>>',lambda e:self.catalog_selected())
        self.catalog_tree.bind('<Double-1>',lambda e:self.open_catalog_curate())
        detail_frame,self.catalog_text=self.text_widget(f,height=11,wrap='none')
        detail_frame.pack(fill='both',expand=False,pady=(4,0))
        self.catalog_text.configure(state='disabled')

    def catalog_scope_sets(self):
        values=['Active Working Set','Accepted Master Catalog','All Catalog']
        self.catalog_named_sets={}
        for row in self.db.working_sets.list():
            label=f'Set: {row["name"]} · {row["working_set_uuid"][:8]}'
            values.append(label);self.catalog_named_sets[label]=row['working_set_uuid']
        self.catalog_scope.configure(values=values)
        if self.catalog_view.get() not in values:self.catalog_view.set(
            'Active Working Set' if self.active_set_uuid else 'All Catalog')

    def scoped_items(self):
        view=self.catalog_view.get()
        set_uuid=self.active_set_uuid if view=='Active Working Set' else self.catalog_named_sets.get(view)
        return self.db.working_sets.items(set_uuid) if set_uuid else []

    def scope_audits(self,view=None):
        view=view or self.catalog_view.get()
        if view in ('All Catalog','Accepted Master Catalog'):return None
        uid=self.active_set_uuid if view=='Active Working Set' else self.catalog_named_sets.get(view)
        return {i['work_id']:i['pinned_audit_id'] for i in self.db.working_sets.items(uid)
                if i['work_id'] and i['processing_status']!='DUPLICATE'}

    def scoped_audit(self,work_id):
        pins=self.scope_audits()
        return self.db.audit(pins.get(work_id),work_id) if pins is not None else self.db.latest_audit(work_id)

    def scoped_work_ids(self):
        view=self.catalog_view.get()
        if view=='Accepted Master Catalog':return {r['id'] for r in self.db.works(accepted_only=True)}
        if view=='All Catalog':
            with self.db.con() as c:return {r[0] for r in c.execute('SELECT id FROM works')}
        return {r['work_id'] for r in self.scoped_items() if r['work_id']}

    def refresh_catalog(self):
        self.catalog_scope_sets()
        keep=self.catalog_tree.selection()
        self.catalog_tree.delete(*self.catalog_tree.get_children())
        with self.db.con() as c:
            curated={r['work_id']:r['n'] for r in c.execute(
                'SELECT work_id,count(*) n FROM curated_fields GROUP BY work_id')}
        view=self.catalog_view.get()
        items=self.scoped_items() if view not in ('Accepted Master Catalog','All Catalog') else []
        item_work_ids={item['work_id'] for item in items if item['work_id']}
        all_works={r['id']:r for r in self.db.works(
            item_work_ids if view not in ('Accepted Master Catalog','All Catalog') else None,
            accepted_only=view=='Accepted Master Catalog',audit_by_work=self.scope_audits())}
        entries=[(f'i:{item["working_set_item_uuid"]}',all_works.get(item['work_id']),item)
                 for item in items] if view not in ('Accepted Master Catalog','All Catalog') else [
                 (str(row['id']),row,None) for row in all_works.values()
                 if view=='All Catalog' or row['lifecycle_status']=='ACCEPTED']
        for iid,row,item in entries:
            if item and row and row['audit_id']!=item['pinned_audit_id']:
                row=self.db.works([row['id']],audit_by_work={row['id']:item['pinned_audit_id']})[0]
            if not row:
                self.catalog_tree.insert('','end',iid=iid,values=(item['original_query'],'—','STAGED',
                    item['processing_status'],item['requested_edition'],item['requested_language'],
                    'Unresolved','—','—','—','—','—','—','—','—','—','—','—',0,0,'—','—','NOT AUDITED','—','NONE','—'))
                continue
            pub=safe_json(row['publication_json'])
            identity=pub.get('catalog_identity') or {}
            h=safe_json(row['health_json'])
            counts=publication_classification_counts(pub) if row['audit_id'] else {}
            mapped=f"{row['mapped_chapters']}/{row['logical_chapters']}" if row['mapped_chapters'] is not None else '—'
            self.catalog_tree.insert('','end',iid=iid,values=(
                item['original_query'] if item else row['input_title'],row['work_uuid'],row['lifecycle_status'],
                item['processing_status'] if item else '—',row['edition'],row['language'],identity.get('canonical_work_id') or '—',
                h.get('identity','—'),h.get('publication','—'),h.get('normalization','—'),
                h.get('acquisition','—'),row['selected_source_name'] or row['selected_source'] or '—',
                row['logical_chapters'] if row['logical_chapters'] is not None else '—',
                row['final_volumes'] if row['final_volumes'] is not None else '—',mapped,
                row['unmapped_chapters'] if row['unmapped_chapters'] is not None else '—',
                counts.get('classified_provider_artifacts','—'),counts.get('unclassified_records','—'),
                len((pub.get('curated_database') or {}).get('fields') or []) if item else curated.get(row['id'],0),pub.get('curation_revision',0) if item else row['catalog_revision'],row['audit_created_at'] or '—',
                row['audit_revision'] if row['audit_id'] else '—',
                ('UNPINNED' if not item['pinned_audit_id'] else 'SUPERSEDED' if self.db.latest_audit(row['id'])['id']!=item['pinned_audit_id'] else self.audit_state(row)) if item else self.audit_state(row),item['pinned_audit_id'] if item else '—',
                row['acceptance_state'],self.db.latest_audit(row['id'])['id'] if self.db.latest_audit(row['id']) else '—'))
        if keep and self.catalog_tree.exists(keep[0]):
            self.catalog_tree.selection_set(keep[0])
        self.catalog_selected()

    def catalog_selected(self):
        selected=self.catalog_tree.selection()
        self.catalog_text.configure(state='normal');self.catalog_text.delete('1.0','end')
        if selected:
            iid=selected[0]
            item=self.db.working_sets.item(iid[2:]) if iid.startswith('i:') else None
            wid=item['work_id'] if item else int(iid)
            if not wid:
                self.catalog_text.insert('1.0',json.dumps({'working_set_item':item,
                    'message':'Intake query is not linked to a canonical catalog work.',
                    'latest_search_observation':self.db.working_sets.latest_observation(item['working_set_item_uuid'])},
                    ensure_ascii=False,indent=2))
                self.catalog_text.configure(state='disabled');return
            work=self.db.work(wid);audit=self.db.audit(item['pinned_audit_id'],wid) if item else self.db.latest_audit(wid)
            pub=safe_json(audit['publication_json']) if audit else {}
            rows=self.db.catalog.rows(wid,audit=audit) if audit else []
            details={'work':dict(work),'working_set_item':item,'database_uuid':self.db.database_uuid,
                     'aliases':(pub.get('context') or {}).get('trusted_aliases') or [],
                     'creator':(pub.get('context') or {}).get('creator'),
                     'trusted_external_ids':(pub.get('catalog_identity') or {}).get('external_ids') or {},
                     'selected_acquisition':pub.get('selected_acquisition_ref'),
                     'provider_inventories':safe_json(audit['inventories_json']) if audit else [],
                     'reference_states':pub.get('references') or {},
                     'structural_coverage':pub.get('structural_coverage') or {},
                     'snapshot_problems':[dict(r) for r in self.db.holes(audit_ids=[audit['id']] if audit else []) if r['work_id']==wid],
                     'acceptance_state':self.db.acceptance.state(wid),
                     'latest_global_audit_id':self.db.latest_audit(wid)['id'] if self.db.latest_audit(wid) else None,
                     'scope':'Pinned Working Set snapshot; curation edits shared catalog data' if item else 'Global catalog',
                     'curation_snapshot':pub.get('curated_database') or {},
                     'current_curation_revision':self.db.catalog.state(wid)['revision'],
                     'chapters':[{'key':r['key'],'automatic':r['automatic'],
                                  'curated':r['curated'],'effective':r['effective']} for r in rows]}
            self.catalog_text.insert('1.0',json.dumps(details,ensure_ascii=False,indent=2,default=str))
        self.catalog_text.configure(state='disabled')

    def open_catalog_curate(self):
        selected=self.catalog_tree.selection()
        if not selected:return
        iid=selected[0];item=self.db.working_sets.item(iid[2:]) if iid.startswith('i:') else None
        wid=item['work_id'] if item else int(iid)
        if wid:self.editor.open(wid)

    def selected_catalog_entry(self):
        selected=self.catalog_tree.selection()
        if len(selected)!=1:raise ValueError('Select exactly one Catalog row.')
        iid=selected[0];item=self.db.working_sets.item(iid[2:]) if iid.startswith('i:') else None
        wid=item['work_id'] if item else int(iid)
        if not wid:raise ValueError('This intake item has no linked canonical work yet.')
        return wid,item

    def selected_catalog_work_uuid(self):
        work_id,_=self.selected_catalog_entry()
        work=self.db.work(work_id)
        if not work or not work['work_uuid']:
            raise ValueError('Selected catalog work no longer exists; refresh and select again.')
        return work['work_uuid']

    def preview_delete_catalog_work(self):
        try:
            if self.worker and self.worker.is_alive():
                raise ValueError('Wait for the current audit to finish before deleting a catalog work.')
            work_uuid=self.selected_catalog_work_uuid()
            preview=self.db.maintenance.preview(work_uuid)
        except (ValueError,OSError,sqlite3.DatabaseError) as exc:
            messagebox.showerror(APP,str(exc),parent=self)
            return None
        opened_db=self.db
        dialog=tk.Toplevel(self)
        dialog.title('Delete Catalog Work — impact preview')
        dialog.geometry('760x690')
        dialog.minsize(630,500)
        dialog.configure(bg=BG)
        dialog.transient(self)
        body=ttk.Frame(dialog,padding=14);body.pack(fill='both',expand=True)
        ttk.Label(body,text='Permanent catalog deletion',style='Title.TLabel').pack(anchor='w')
        if preview['strong_warning']:
            ttk.Label(body,text='ACCEPTED OR CURATED WORK — review every dependency before deletion.',
                      foreground=BAD).pack(anchor='w',pady=(4,0))
        frame,impact=self.text_widget(body,height=24,wrap='word')
        frame.pack(fill='both',expand=True,pady=(8,8))
        impact.insert('1.0',format_delete_preview(preview))
        impact.configure(state='disabled')
        dialog.impact_text=impact
        ttk.Label(body,text='Type DELETE to enable permanent deletion. A fresh backup is created first.').pack(anchor='w')
        confirmation=tk.StringVar()
        entry=ttk.Entry(body,textvariable=confirmation,width=20)
        entry.pack(anchor='w',pady=(5,10))
        buttons=ttk.Frame(body);buttons.pack(fill='x')
        ttk.Button(buttons,text='Cancel',command=dialog.destroy).pack(side='right',padx=(8,0))
        delete_button=ttk.Button(buttons,text='Permanently Delete Work',state='disabled')
        delete_button.pack(side='right')
        dialog.confirmation_var=confirmation
        dialog.delete_button=delete_button
        confirmation.trace_add('write',lambda *_:delete_button.configure(
            state='normal' if confirmation.get()=='DELETE' else 'disabled'))

        def finish():
            try:
                if self.worker and self.worker.is_alive():
                    raise ValueError('An audit started after preview; stop it and preview again.')
                if self.db is not opened_db or self.selected_catalog_work_uuid()!=work_uuid:
                    raise ValueError('Database or selected work changed after preview; preview again.')
                result=self.db.maintenance.delete(preview,confirmation.get())
            except (ValueError,OSError,sqlite3.DatabaseError) as exc:
                dialog.destroy()
                messagebox.showerror(APP,str(exc),parent=self)
                return
            dialog.destroy()
            detached=set(result['detached_item_uuids'])
            self.queue_ids=[key for key in self.queue_ids if key!=result['work_id'] and key not in detached]
            self._active_work_id=None;self._active_hole=None
            self.detail_header.set('Select a title');self.detail_summary.set('')
            self.set_detail_text('')
            self.inventory_tree.delete(*self.inventory_tree.get_children())
            self.problem_text.configure(state='normal');self.problem_text.delete('1.0','end')
            self.problem_text.configure(state='disabled')
            self.editor.pending=None;self.editor.current=None
            self.editor.rebind(self.db.catalog)
            self.refresh_all()
            self.batch.set(f'Deleted catalog work {work_uuid}. Backup: {result["backup"]}')

        delete_button.configure(command=finish)
        dialog.grab_set()
        entry.focus_set()
        return dialog

    def clipboard_text(self,value):
        self.clipboard_clear();self.clipboard_append(value);self.update()

    def copy_catalog_selected(self,kind):
        try:
            wid,item=self.selected_catalog_entry()
            if kind=='summary':value=catalog_summary(self.db,wid,item)
            elif kind=='review':value=review_context(self.db,wid,item)
            elif kind=='full':value=self.catalog_text.get('1.0','end-1c')
            elif kind=='csv':
                from io import StringIO
                buffer=StringIO(newline='');writer=csv.writer(buffer)
                cols=self.catalog_tree['columns']
                writer.writerow([self.catalog_tree.heading(c)['text'] for c in cols])
                writer.writerow(self.catalog_tree.item(self.catalog_tree.selection()[0],'values'))
                value=buffer.getvalue()
            else:
                packet=review_packet(self.db,work_ids={wid},include_ignored=True,audit_by_work={wid:item['pinned_audit_id']} if item else None)
                value=packet_markdown(packet) if packet['works'] else catalog_summary(self.db,wid,item)
            self.clipboard_text(value)
            self.batch.set(f'Copied one selected {kind} to clipboard.')
        except (ValueError,OSError) as exc:messagebox.showerror(APP,str(exc))

    def preview_accept_selected(self):
        items=[];works=[];expected={};descriptions=[]
        try:
            for iid in self.catalog_tree.selection():
                item=self.db.working_sets.item(iid[2:]) if iid.startswith('i:') else None
                wid=item['work_id'] if item else int(iid)
                result=self.db.acceptance.evaluate(wid,item['working_set_item_uuid'] if item else None)
                if not result['eligible']:raise ValueError('\n'.join(result['blockers']))
                key=item['working_set_item_uuid'] if item else wid
                (items if item else works).append(key);expected[str(key)]=result['fingerprint']
                descriptions.append(f'{self.db.work(wid)["input_title"]}: audit {result["audit_id"]}, curation {result["curation_revision"]}')
            if not items and not works:raise ValueError('Select exact linked items or catalog works.')
            preview=f'Accept {len(descriptions)} exact snapshots?\n\n'+'\n'.join(descriptions[:30])
            if len(descriptions)>30:preview+=f'\n... and {len(descriptions)-30} more selected snapshots.'
            if messagebox.askyesno('Accept Selected',preview,parent=self):
                self.db.acceptance.accept(items,works,expected);self.refresh_all()
        except ValueError as exc:messagebox.showerror(APP,str(exc))

    def accept_all_safe(self):
        try:
            preview=self.db.acceptance.bulk_preview(self.active_set_uuid)
            text=f'{len(preview["candidates"])} safe items will be accepted.\n{preview["review"]} remain REVIEW.\n{preview["error"]} remain ERROR.\n{preview["stale"]} stale READY items will return to REVIEW.'
            if preview['ready_items'] and messagebox.askyesno('Accept All Safe',text,parent=self):
                self.db.acceptance.accept(preview['ready_items'],expected=preview['candidates'],bulk=True)
                self.refresh_all()
        except ValueError as exc:messagebox.showerror(APP,str(exc))

    def run_working_set(self):
        if self.worker and self.worker.is_alive():return
        try:
            self.db.working_sets.recover_interrupted()
            ids=self.db.working_sets.run_candidates(self.active_set_uuid)
            if ids:self.start_audit(ids)
            else:self.batch.set('No pending or stale items. Accept All Safe / Open Review Items / Retry Errors.')
        except ValueError as exc:messagebox.showerror(APP,str(exc))

    def retry_errors(self):
        try:self.start_audit(self.db.working_sets.retry_errors(self.active_set_uuid))
        except ValueError as exc:messagebox.showerror(APP,str(exc))

    def reopen_selected_items(self):
        try:
            ids=[iid[2:] for iid in self.catalog_tree.selection() if iid.startswith('i:')]
            if not ids:raise ValueError('Select accepted/rejected Working Set items.')
            self.db.working_sets.reopen_items(ids);self.refresh_all()
        except ValueError as exc:messagebox.showerror(APP,str(exc))

    def reopen_working_set(self):
        try:self.db.working_sets.reopen(self.active_set_uuid);self.refresh_all()
        except ValueError as exc:messagebox.showerror(APP,str(exc))

    def open_review_items(self):
        self.catalog_view.set('Active Working Set');self.refresh_all();self.nb.select(self.catalog_tab)
        ids=['i:'+i['working_set_item_uuid'] for i in self.scoped_items() if i['processing_status']=='REVIEW']
        self.catalog_tree.selection_set(ids)
        if ids:self.catalog_tree.see(ids[0])

    def reevaluate_acceptance(self):
        try:
            wid,_=self.selected_catalog_entry()
            result=self.db.acceptance.evaluate(wid)
            with self.db.con() as c:
                previous=[dict(r) for r in c.execute('SELECT * FROM catalog_acceptances WHERE work_uuid=? ORDER BY id DESC',(result['work_uuid'],))]
                memberships=[dict(r) for r in c.execute('SELECT working_set_uuid,working_set_item_uuid,processing_status,pinned_audit_id FROM working_set_items WHERE linked_work_uuid=?',(result['work_uuid'],))]
            win=tk.Toplevel(self);win.title('Reevaluate Acceptance');win.configure(bg=BG);win.geometry('850x620')
            frame,text=self.text_widget(win,wrap='none');frame.pack(fill='both',expand=True,padx=12,pady=12)
            text.insert('1.0',json.dumps({'scope':'Global catalog acceptance; membership decisions and pins remain unchanged.',
                'work':dict(self.db.work(wid)),'acceptance_state':self.db.acceptance.state(wid),'current':result,
                'acceptance_history':previous,'memberships':memberships},indent=2));text.configure(state='disabled')
            bar=ttk.Frame(win);bar.pack(fill='x',padx=12,pady=8)
            def approve():
                try:self.db.acceptance.accept(work_ids=[wid],expected={str(wid):result['fingerprint']});win.destroy();self.refresh_all()
                except ValueError as exc:messagebox.showerror(APP,str(exc),parent=win)
            def revoke():
                from tkinter import simpledialog
                reason=simpledialog.askstring(APP,'Reason for revocation (returns catalog work to STAGED)',parent=win)
                if reason:
                    try:self.db.acceptance.revoke(wid,reason);win.destroy();self.refresh_all()
                    except ValueError as exc:messagebox.showerror(APP,str(exc),parent=win)
            ttk.Button(bar,text='Confirm Safe Snapshot',command=approve,state='normal' if result['eligible'] else 'disabled').pack(side='left')
            ttk.Button(bar,text='Revoke Acceptance',command=revoke).pack(side='left',padx=8)
        except ValueError as exc:messagebox.showerror(APP,str(exc))

    def problem_item_uuid(self,work_id):
        view=self.problem_view.get()
        if view in ('All Catalog','Accepted Master Catalog'):return None
        uid=self.active_set_uuid if view=='Active Working Set' else self.catalog_named_sets.get(view)
        items=[i for i in self.db.working_sets.items(uid) if i['work_id']==work_id and i['processing_status']!='DUPLICATE']
        if len(items)!=1:raise ValueError('Select one exact problem membership.')
        self.db.working_sets.editable_item(items[0]['working_set_item_uuid'],work_id)
        return items[0]['working_set_item_uuid']

    def curation_item_uuid(self,work_id):
        view=self.catalog_view.get()
        if view in ('All Catalog','Accepted Master Catalog'):return None
        matches=[i for i in self.scoped_items() if i['work_id']==work_id and i['processing_status']!='DUPLICATE']
        if len(matches)!=1:raise ValueError('Select one exact Working Set membership before editing shared catalog data.')
        item=matches[0];self.db.working_sets.guard(item_uuid=item['working_set_item_uuid'])
        if item['working_set_uuid']!=self.active_set_uuid:
            raise ValueError('Activate this Working Set before editing its membership, or choose All Catalog for global curation.')
        if item['processing_status'] in ('ACCEPTED','REJECTED'):raise ValueError('Reopen this item for review before curation.')
        return item['working_set_item_uuid']

    def post_curation(self,item_uuid):
        if not item_uuid:return
        self.db.working_sets.guard(item_uuid=item_uuid)
        self.db.working_sets.set_item_status(item_uuid,'QUEUED')
        if self.worker and self.worker.is_alive():
            self.deferred_curation_items=getattr(self,'deferred_curation_items',set())|{item_uuid}
            self.batch.set('Curation saved; fresh audit queued after this run.')
        else:self.start_audit([item_uuid])

    def remove_selected_from_set(self):
        item_ids=[iid[2:] for iid in self.catalog_tree.selection() if iid.startswith('i:')]
        if not item_ids:
            messagebox.showerror(APP,'Select Working Set intake rows.');return
        if not messagebox.askyesno(APP,f'Remove {len(item_ids)} intake item(s) from this view? Catalog works, audits, and curation remain.'):
            return
        for item_uuid in item_ids:self.db.working_sets.remove_item(item_uuid)
        self.queue_ids=[key for key in self.queue_ids if key not in item_ids]
        self.refresh_all()

    def reject_selected_intake(self):
        item_ids=[iid[2:] for iid in self.catalog_tree.selection() if iid.startswith('i:')]
        if not item_ids:
            messagebox.showerror(APP,'Select Working Set intake rows.');return
        if not messagebox.askyesno(APP,f'Mark {len(item_ids)} intake item(s) REJECTED? Evidence remains available.'):
            return
        for item_uuid in item_ids:self.db.working_sets.set_item_status(item_uuid,'REJECTED')
        self.queue_ids=[key for key in self.queue_ids if key not in item_ids]
        self.refresh_all()

    def active_set_for_export(self):
        if not self.active_set_uuid or not self.db.working_sets.get(self.active_set_uuid):
            raise ValueError('Select an active Working Set first.')
        return self.active_set_uuid

    def copy_working_set(self,kind):
        try:
            set_uuid=self.active_set_for_export()
            if kind=='csv':value=working_set_csv(self.db,set_uuid)
            elif kind=='titles':value=working_set_title_list(self.db,set_uuid)
            elif kind=='review':value=working_set_review_context(self.db,set_uuid)
            else:
                ws=self.db.working_sets.get(set_uuid);items=self.db.working_sets.items(set_uuid)
                counts={status:sum(i['processing_status']==status for i in items) for status in
                        ('PENDING','QUEUED','AUDITING','REVIEW','READY','ACCEPTED','REJECTED')}
                value=(f'{ws["name"]} [{ws["status"]}]\nDatabase UUID: {self.db.database_uuid}\n'
                       f'Working Set UUID: {set_uuid}\nItems: {len(items)}\n'+
                       '\n'.join(f'{k}: {v}' for k,v in counts.items())+'\n\n'+
                       '\n'.join(f'{i["original_query"]} · {i["requested_edition"]} / '
                                 f'{i["requested_language"]} · {i["processing_status"]}' for i in items))
            self.clipboard_text(value)
        except (ValueError,OSError) as exc:messagebox.showerror(APP,str(exc))

    def export_working_set(self,kind):
        try:
            set_uuid=self.active_set_for_export()
            extension='.csv' if kind in ('csv','current_csv','issues') else '.txt' if kind=='titles' else '.json'
            path=filedialog.asksaveasfilename(defaultextension=extension,
                initialfile=f'working_set_{set_uuid[:8]}_{kind}{extension}')
            if not path:return
            if kind=='csv':value=working_set_csv(self.db,set_uuid,'pinned')
            elif kind=='current_csv':value=working_set_csv(self.db,set_uuid,'current')
            elif kind=='titles':value=working_set_title_list(self.db,set_uuid)
            elif kind=='review':value=json.dumps(working_set_packet(self.db,set_uuid,'pinned'),ensure_ascii=False,indent=2)
            else:
                ids={r['work_id'] for r in self.db.working_sets.items(set_uuid) if r['work_id']}
                packet=review_packet(self.db,work_ids=ids)
                import tempfile
                with tempfile.TemporaryDirectory() as folder:
                    temp=Path(folder)/'issues.csv';detailed_csv(packet,temp)
                    value=temp.read_text(encoding='utf-8-sig')
            Path(path).write_text(value,encoding='utf-8-sig' if extension=='.csv' else 'utf-8')
        except (ValueError,OSError) as exc:messagebox.showerror(APP,str(exc))

    def export_catalog(self):
        path=filedialog.asksaveasfilename(defaultextension='.csv',initialfile='mangaanka_catalog.csv',
                                          filetypes=[('CSV','*.csv')])
        if not path:return
        with open(path,'w',newline='',encoding='utf-8-sig') as file:
            writer=csv.writer(file)
            writer.writerow([self.catalog_tree.heading(c)['text'] for c in self.catalog_tree['columns']])
            for iid in self.catalog_tree.get_children():writer.writerow(self.catalog_tree.item(iid,'values'))

    def build_details(self):
        f = self.tabs[3]
        split = ttk.Panedwindow(f, orient='horizontal')
        split.pack(fill='both', expand=True)
        left = ttk.Frame(split); right = ttk.Frame(split, padding=(12,0,0,0))
        split.add(left, weight=1); split.add(right, weight=4)
        ttk.Label(left, text='Titles', style='Title.TLabel').pack(anchor='w')
        lf, self.detail_titles = self.tree_widget(left, ('title',), ('Title',), (280,), 'browse', {'title':'w'})
        lf.pack(fill='both', expand=True, pady=(8,0))
        self.detail_titles.bind('<<TreeviewSelect>>', lambda e:self.detail_selected())

        self.detail_header = tk.StringVar(value='Select a title')
        self.detail_summary = tk.StringVar(value='')
        ttk.Label(right, textvariable=self.detail_header, style='Title.TLabel').pack(anchor='w')
        ttk.Label(right, textvariable=self.detail_summary, style='Muted.TLabel', wraplength=1000).pack(anchor='w', pady=(2,8))

        ttk.Label(right, text='Provider inventories').pack(anchor='w')
        cols = ('provider','usable','complete','chapters','volumes','standalone','summary')
        heads = ('Provider','Usable','Complete','Chapters','Native Vols','Standalone','Summary')
        widths = (130,70,75,85,85,85,500)
        pf, self.inventory_tree = self.tree_widget(right, cols, heads, widths, 'browse', {'provider':'w','summary':'w'})
        self.inventory_tree.configure(height=4)
        pf.pack(fill='x', expand=False, pady=(4,8))

        ttk.Label(right, text='Latest audit evidence / diagnostics').pack(anchor='w')
        tf, self.detail_text = self.text_widget(right, height=13, wrap='none')
        tf.pack(fill='both', expand=True, pady=(4,0))
        self.detail_text.configure(state='disabled')

    def open_ws(self):
        if os.name == 'nt':
            os.startfile(self.db.path.parent)
        else:
            webbrowser.open(self.db.path.parent.as_uri())

    def update_database_label(self):
        with self.db.con() as c:
            schema=c.execute('PRAGMA user_version').fetchone()[0]
            works=c.execute('SELECT count(*) FROM works').fetchone()[0]
            audits=c.execute('SELECT count(*) FROM search_audits').fetchone()[0]
            curated=c.execute('SELECT count(*) FROM curated_catalog').fetchone()[0]
        self.database_label.set(f'ACTIVE DATABASE  [{self.db.role}]  {self.db.path.name}  ·  Schema v{schema}  '
                                f'·  {works} works / {audits} audits / {curated} curated\n'
                                f'{self.db.path}  ·  UUID {self.db.database_uuid}')

    def update_working_set_label(self):
        active=self.db.working_sets.get(self.active_set_uuid)
        if not active:
            self.set_more.configure(text='Status: NONE',state='disabled')
            for index in range(5):self.set_menu.entryconfigure(index,state='disabled')
            self.working_set_label.set('ACTIVE WORKING SET  None · Create one to stage a research batch.')
            return
        self.set_more.configure(text=f'Status: {active["status"]} ▾',state='normal')
        allowed=({'ARCHIVED'} if active['status']=='COMPLETE' else set()
                 if active['status']=='ARCHIVED' else {'OPEN','REVIEW','COMPLETE','ARCHIVED'})
        for index,status in enumerate(('OPEN','REVIEW','COMPLETE','ARCHIVED')):
            self.set_menu.entryconfigure(index,state='normal' if status in allowed else 'disabled')
        self.set_menu.entryconfigure(4,state='normal' if active['status'] in ('COMPLETE','ARCHIVED') else 'disabled')
        items=self.db.working_sets.items(self.active_set_uuid)
        counts={key:sum(r['processing_status']==key for r in items) for key in
                ('PENDING','QUEUED','AUDITING','AUDITED','REVIEW','READY','ACCEPTED','REJECTED','ERROR')}
        work_ids={i['work_id'] for i in items if i['work_id']}
        works={r['id']:r for r in self.db.works(work_ids,audit_by_work={i['work_id']:i['pinned_audit_id'] for i in items if i['work_id'] and i['processing_status']!='DUPLICATE'})}
        states={key:0 for key in ('PASS','REVIEW','ERROR')}
        for item in items:
            state='ERROR' if item['processing_status']=='ERROR' else (
                self.audit_state(works[item['work_id']]) if item['work_id'] in works else None)
            if state in states:states[state]+=1
        with self.db.con() as c:
            curated=c.execute('SELECT count(DISTINCT work_id) FROM curated_fields WHERE work_id IN ('+
                ','.join('?' for _ in work_ids)+')',tuple(work_ids)).fetchone()[0] if work_ids else 0
        problem_counts={'RESEARCH_REQUIRED':0,'CODE_REVIEW_REQUIRED':0,'ACQUISITION_ONLY':0}
        for row in self.db.holes(audit_ids=[i['pinned_audit_id'] for i in items if i['pinned_audit_id']]):
            if row['work_id'] in work_ids:
                _,action,_,_=problem_policy(row['code'],safe_json(row['details_json']))
                if action in problem_counts:problem_counts[action]+=1
        self.working_set_label.set(f'ACTIVE WORKING SET  {active["name"]} [{active["status"]}]  '
            f'· {len(items)} items · Pending {counts["PENDING"]} · Queued {counts["QUEUED"]} '
            f'· Auditing {counts["AUDITING"]} · Review {counts["REVIEW"]} · Ready {counts["READY"]} '
            f'· Accepted {counts["ACCEPTED"]} · Duplicate {sum(i["processing_status"]=="DUPLICATE" for i in items)} · Error {counts["ERROR"]}\n'
            f'PASS {states["PASS"]} · REVIEW {states["REVIEW"]} · ERROR {states["ERROR"]} · Curated {curated} '
            f'· Research {problem_counts["RESEARCH_REQUIRED"]} · Code {problem_counts["CODE_REVIEW_REQUIRED"]} '
            f'· Acquisition {problem_counts["ACQUISITION_ONLY"]}')

    def activate_working_set(self,set_uuid):
        if self.worker and self.worker.is_alive():raise ValueError('Wait for the audit before switching Working Sets.')
        self.db.working_sets.set_active(set_uuid)
        self.active_set_uuid=set_uuid
        self.catalog_view.set('Active Working Set')
        self.problem_view.set('Active Working Set')
        self.editor.history_scope.set('Active Working Set')
        self.queue_ids=[r['working_set_item_uuid'] for r in self.db.working_sets.items(set_uuid)
                        if r['processing_status'] in ('QUEUED','AUDITING','ERROR')]
        self.refresh_all()

    def new_working_set(self):
        from tkinter import simpledialog
        name=simpledialog.askstring(APP,'New Working Set name',parent=self)
        if name is None:return
        try:
            set_uuid=self.db.working_sets.create(name,language=self.language.get(),workflow=self.workflow.get())
            self.activate_working_set(set_uuid)
        except ValueError as exc:messagebox.showerror(APP,str(exc))

    def change_working_set_status(self,status):
        if not self.active_set_uuid:
            messagebox.showerror(APP,'Select an active Working Set.');return
        if self.worker and self.worker.is_alive():
            messagebox.showerror(APP,'Wait for the audit before changing Working Set status.');return
        try:
            self.db.working_sets.set_status(self.active_set_uuid,status)
            if status in ('COMPLETE','ARCHIVED'):
                self.queue_ids=[key for key in self.queue_ids if not isinstance(key,str)]
            self.refresh_all()
        except ValueError as exc:messagebox.showerror(APP,str(exc))

    def switch_working_set(self):
        choices=self.db.working_sets.list()
        if not choices:
            messagebox.showinfo(APP,'No Working Sets in this database yet.');return
        dialog=tk.Toplevel(self);dialog.title('Switch Working Set');dialog.configure(bg=BG)
        dialog.transient(self);dialog.grab_set()
        body=ttk.Frame(dialog,padding=16);body.pack(fill='both',expand=True)
        ttk.Label(body,text='Select a Working Set in the active database').pack(anchor='w')
        names={f'{r["name"]} [{r["status"]}] · {r["working_set_uuid"][:8]}':r['working_set_uuid'] for r in choices}
        chosen=tk.StringVar(value=next(iter(names)))
        ttk.Combobox(body,textvariable=chosen,values=tuple(names),state='readonly',width=58).pack(fill='x',pady=10)
        def activate():
            try:self.activate_working_set(names[chosen.get()])
            except ValueError as exc:messagebox.showerror(APP,str(exc),parent=dialog)
            else:dialog.destroy()
        ttk.Button(body,text='Open Working Set',command=activate).pack(anchor='e')
        self.wait_window(dialog)

    def switch_database(self,path):
        if self.worker and self.worker.is_alive():
            raise ValueError('Stop the audit and wait for it to finish before switching databases.')
        path=validate_database(path)
        if path==self.db.path:return
        next_lock=WriterLock(path)
        try:
            replacement=DB(path)
            replacement.works()  # Check expected columns and latest-audit query before activation.
            with replacement.con() as c:
                if c.execute('PRAGMA foreign_key_check').fetchone():
                    raise ValueError('Database has broken foreign-key references; current database remains active.')
        except Exception:
            next_lock.close();raise
        old_lock=self.writer_lock
        self.writer_lock=next_lock
        self.db=replacement
        self.auditor=SearchAuditor(self.db,self.events)
        self.db.working_sets.recover_interrupted()
        self.active_set_uuid=self.db.working_sets.active_uuid()
        self.catalog_view.set('Active Working Set' if self.active_set_uuid else 'All Catalog')
        self.problem_view.set('Active Working Set' if self.active_set_uuid else 'All Catalog')
        self.editor.history_scope.set('Active Working Set' if self.active_set_uuid else 'All Catalog')
        self.queue_ids=[r['working_set_item_uuid'] for r in self.db.working_sets.items(self.active_set_uuid)
                        if r['processing_status'] in ('QUEUED','AUDITING','ERROR')]
        self._active_work_id=None;self._active_hole=None
        self.editor.rebind(self.db.catalog)
        self.detail_summary.set('');self.detail_header.set('Select a title');self.set_detail_text('')
        self.inventory_tree.delete(*self.inventory_tree.get_children())
        remember_path(self.ws,path)
        self.refresh_all()
        old_lock.close()

    def choose_database(self):
        path=filedialog.askopenfilename(title='Switch MangaAnkā DDK database',
                                        filetypes=[('SQLite database','*.db'),('All files','*.*')])
        if path:
            try:self.switch_database(path)
            except (ValueError,OSError,sqlite3.DatabaseError) as exc:messagebox.showerror(APP,str(exc))

    def create_database(self,path,role):
        path=Path(path).resolve()
        if self.worker and self.worker.is_alive():
            raise ValueError('Stop the audit before creating another database.')
        if role not in ('PRODUCTION','TEST','SCRATCH'):
            raise ValueError('Choose PRODUCTION, TEST, or SCRATCH.')
        try:
            with path.open('xb'):pass
        except FileExistsError as exc:
            raise ValueError(f'Refusing to overwrite an existing file: {path}') from exc
        created=DB(path,role,create_new=True)
        self.switch_database(created.path)
        return created

    def new_database(self):
        path=filedialog.asksaveasfilename(title='New MangaAnkā DDK database',defaultextension='.db',
                                          filetypes=[('SQLite database','*.db')])
        if not path:return
        dialog=tk.Toplevel(self);dialog.title('New Database');dialog.configure(bg=BG)
        dialog.resizable(False,False);dialog.transient(self);dialog.grab_set()
        body=ttk.Frame(dialog,padding=16);body.pack(fill='both',expand=True)
        ttk.Label(body,text=f'Create {Path(path).name}').pack(anchor='w')
        ttk.Label(body,text=str(Path(path).resolve()),style='Muted.TLabel',wraplength=480).pack(anchor='w',pady=(2,12))
        ttk.Label(body,text='Database role').pack(anchor='w')
        role=tk.StringVar(value='TEST')
        ttk.Combobox(body,textvariable=role,values=('PRODUCTION','TEST','SCRATCH'),
                     state='readonly',width=20).pack(anchor='w',pady=(3,12))
        buttons=ttk.Frame(body);buttons.pack(fill='x')
        ttk.Button(buttons,text='Cancel',command=dialog.destroy).pack(side='right')
        def create():
            try:self.create_database(path,role.get())
            except (ValueError,OSError,sqlite3.DatabaseError) as exc:
                messagebox.showerror(APP,str(exc),parent=dialog)
            else:dialog.destroy()
        ttk.Button(buttons,text='Create Database',style='Accent.TButton',command=create).pack(side='right',padx=6)
        self.wait_window(dialog)

    def import_titles(self):
        path = filedialog.askopenfilename(filetypes=[('Text / CSV','*.txt *.csv'),('All files','*.*')])
        if not path:
            return
        text = Path(path).read_text(encoding='utf-8-sig', errors='replace')
        if path.lower().endswith('.csv'):
            text = '\n'.join(row[0].strip() for row in csv.reader(text.splitlines()) if row and row[0].strip())
        self.input.delete('1.0','end'); self.input.insert('1.0',text)

    def paste_titles(self):
        try:incoming=self.clipboard_get()
        except tk.TclError:return
        existing=self.input.get('1.0','end').splitlines()
        titles=list(dict.fromkeys(line.strip() for line in [*existing,*incoming.splitlines()] if line.strip()))
        self.input.delete('1.0','end');self.input.insert('1.0','\n'.join(titles))

    def add_titles(self):
        titles = [line.strip() for line in self.input.get('1.0','end').splitlines() if line.strip()]
        if not titles:return
        if not self.active_set_uuid:
            self.active_set_uuid=self.db.working_sets.create('Intake',language=self.language.get(),
                                                              workflow=self.workflow.get())
            self.db.working_sets.set_active(self.active_set_uuid)
            self.catalog_view.set('Active Working Set');self.problem_view.set('Active Working Set')
        try:
            report=self.db.working_sets.add_requests(self.active_set_uuid,titles,self.edition.get(),
                                                     self.language.get(),self.workflow.get())
        except ValueError as exc:
            messagebox.showerror(APP,str(exc));return
        wanted={(value.casefold(),self.edition.get(),self.language.get(),self.workflow.get()) for value in titles}
        for item in self.db.working_sets.items(self.active_set_uuid):
            context=(item['original_query'].casefold(),item['requested_edition'],
                     item['requested_language'],item['requested_workflow'])
            if context in wanted and item['processing_status'] in ('PENDING','QUEUED','ERROR'):
                self.db.working_sets.set_item_status(item['working_set_item_uuid'],'QUEUED')
                if item['working_set_item_uuid'] not in self.queue_ids:
                    self.queue_ids.append(item['working_set_item_uuid'])
        self.input.delete('1.0','end')
        self.batch.set(f'{report["input_lines"]} lines · {report["unique_requests"]} unique · '
                       f'{report["new_items"]} new · {report["restored_items"]} restored · '
                       f'{report["already_in_set"]} already in set.')
        self.refresh_all()

    @staticmethod
    def selected_ids(tree):
        out=[]
        for iid in tree.selection():
            try: out.append(int(iid[2:] if iid.startswith('w:') else iid))
            except Exception: pass
        return out

    def start_audit(self, ids=None, global_context=False):
        if self.worker and self.worker.is_alive():
            return
        ids = list(ids) if ids is not None else (self.selected_queue_ids() or list(self.queue_ids))
        if not ids:
            return
        active=self.db.working_sets.get(self.active_set_uuid)
        if not global_context and active and active['status'] in ('OPEN','REVIEW'):
            by_work={}
            for item in self.db.working_sets.items(self.active_set_uuid):
                if item['work_id'] and item['processing_status']!='DUPLICATE':by_work.setdefault(item['work_id'],[]).append(item['working_set_item_uuid'])
            ids=[by_work[wid][0] if isinstance(wid,int) and len(by_work.get(wid,()))==1 else wid
                 for wid in ids]
        if any(isinstance(wid,str) for wid in ids):
            if not active or active['status'] not in ('OPEN','REVIEW'):
                messagebox.showerror(APP,'Complete or archived Working Sets cannot pin new audits.');return
            items=[self.db.working_sets.item(wid) for wid in ids if isinstance(wid,str)]
            if any(not item or item['removed_at'] or item['working_set_uuid']!=self.active_set_uuid
                   for item in items):
                messagebox.showerror(APP,'Audit only active Working Set intake items.');return
            if any(item['processing_status'] in ('ACCEPTED','REJECTED','DUPLICATE') for item in items):
                messagebox.showerror(APP,'Reopen accepted/rejected items for review before auditing. Duplicate intake cannot be audited.');return
            for item in items:
                if item['processing_status'] not in ('QUEUED','AUDITING'):
                    self.db.working_sets.set_item_status(item['working_set_item_uuid'],'QUEUED')
        for wid in ids:
            if (self.db.working_sets.item(wid) if isinstance(wid,str) else self.db.work(wid)) and wid not in self.queue_ids:
                self.queue_ids.append(wid)
        self.refresh_audit()
        self.start_button.configure(state='disabled')
        self.stop_button.configure(state='normal')
        self.worker = threading.Thread(target=self.auditor.audit_many, args=(ids,self.workflow.get()), daemon=True)
        self.worker.start()

    def remove_selected(self):
        ids = self.selected_queue_ids()
        if self.worker and self.worker.is_alive():return
        for item_uuid in ids:
            if isinstance(item_uuid,str) and self.db.working_sets.item(item_uuid)['processing_status']!='ERROR':
                self.db.working_sets.set_item_status(item_uuid,'PENDING')
        self.queue_ids=[wid for wid in self.queue_ids if wid not in ids]
        self.refresh_audit()

    def clear_queue(self):
        if self.worker and self.worker.is_alive():return
        for item_uuid in self.queue_ids:
            if isinstance(item_uuid,str) and self.db.working_sets.item(item_uuid)['processing_status']!='ERROR':
                self.db.working_sets.set_item_status(item_uuid,'PENDING')
        self.queue_ids.clear();self.refresh_audit()

    def selected_queue_ids(self):
        result=[]
        for iid in self.audit_tree.selection():
            if iid.startswith('i:'):result.append(iid[2:])
            elif iid.startswith('w:'):result.append(int(iid[2:]))
        return result

    def poll(self):
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == 'status':
                    self.progress['value'] = payload.get('progress',0)
                    self.batch.set(payload.get('text',''))
                elif kind == 'batch':
                    self.batch.set(payload.get('text',''))
                elif kind == 'refresh':
                    self.refresh_all()
                elif kind == 'done':
                    self.start_button.configure(state='normal')
                    self.stop_button.configure(state='disabled')
                    self.progress['value'] = 0
                    self.batch.set(payload.get('text','Audit complete.'))
                    self.refresh_all()
                    deferred=getattr(self,'deferred_curation_items',set());self.deferred_curation_items=set()
                    if deferred:
                        candidates=set(self.db.working_sets.run_candidates(self.active_set_uuid))
                        if deferred & candidates:self.after(150,lambda keys=list(deferred & candidates):self.start_audit(keys))
        except queue.Empty:
            pass
        self.after(100, self.poll)

    def audit_state(self, row):
        return audit_status(row)

    def final_values(self, row):
        def value(key):
            return row[key] if row[key] is not None else '—'
        mapped = (f"{row['mapped_chapters']}/{row['logical_chapters']}"
                  if row['mapped_chapters'] is not None else '—')
        classified=publication_classification_counts(safe_json(row['publication_json'])) if row['audit_id'] else None
        return (row['input_title'], row['match_title'] or '', row['selected_edition'] or '—',
                row['provider_count'] or 0, row['selected_source_name'] or row['selected_source'] or '',
                value('logical_chapters'), value('final_volumes'), mapped, value('unmapped_chapters'),
                classified['classified_provider_artifacts'] if classified else '—',
                classified['unclassified_records'] if classified else '—',
                row['hole_count'] or 0, self.audit_state(row))

    def refresh_all(self):
        self.update_database_label()
        self.update_working_set_label()
        self.shared_scope.set(f'Catalog / Titles / Curate / Details scope: {self.catalog_view.get()} · Problems: {self.problem_view.get()} · History: {self.editor.history_scope.get()} · Curation edits shared catalog data.')
        self.editor.scope_label.set(f'Curation scope: {self.catalog_view.get()} · Grid edits the latest shared catalog state; only the active membership advances its audit pin.')
        self.refresh_audit()
        self.refresh_titles()
        self.refresh_catalog()
        self.refresh_holes()
        self.refresh_detail_titles()
        if hasattr(self, 'editor'):
            self.editor.refresh()

    def refresh_audit(self):
        keep = set(self.audit_tree.selection())
        self.audit_tree.delete(*self.audit_tree.get_children())
        works={r['id']:r for r in self.db.works()}
        for key in list(self.queue_ids):
            if isinstance(key,str):
                item=self.db.working_sets.item(key)
                if not item or item['processing_status'] not in ('QUEUED','AUDITING','ERROR'):
                    self.queue_ids.remove(key);continue
                work=self.db.works([item['work_id']],audit_by_work={item['work_id']:item['pinned_audit_id']})[0] if item['work_id'] else None
                values=(item['original_query'],*(self.final_values(work)[1:] if work else
                    ('',item['requested_edition'],0,'','—','—','—','—','—','—',0,'NOT AUDITED')),
                    item['processing_status'])
                self.audit_tree.insert('','end',iid='i:'+key,values=values)
            else:
                work=works.get(key)
                if work:self.audit_tree.insert('','end',iid='w:'+str(key),values=(
                    *self.final_values(work),work['run_status'] or ('Legacy' if work['audit_id'] else 'Waiting')))
        for iid in keep:
            if self.audit_tree.exists(iid): self.audit_tree.selection_add(iid)

    def refresh_titles(self):
        self.title_tree.delete(*self.title_tree.get_children())
        for r in self.db.works(self.scoped_work_ids(),audit_by_work=self.scope_audits()):
            self.title_tree.insert('', 'end', iid=str(r['id']), values=(
                *self.final_values(r), r['audit_created_at'] or '',
            ))

    def refresh_holes(self):
        choices=('Active Working Set','All Catalog','Accepted Master Catalog',*getattr(self,'catalog_named_sets',{}))
        self.problem_scope.configure(values=choices)
        if self.problem_view.get() not in choices:self.problem_view.set(
            'Active Working Set' if self.active_set_uuid else 'All Catalog')
        candidates=self.db.code_review_candidates()
        self.pattern_notice.set('CODE_REVIEW_REQUIRED: '+', '.join(
            f"{c['provider'] or 'unknown provider'} / {c['pattern_family']} "
            f"({c.get('records','?')} records, {c.get('works',c.get('titles',0))} works)" for c in candidates[:3])+
            (f' +{len(candidates)-3} more in Review Packet' if len(candidates)>3 else '')
            if candidates else 'No repeated provider normalization patterns recorded.')
        intake_errors=self.scoped_intake_errors()
        values = ('All', *sorted(set(self.db.hole_codes()) |
                                  ({'AUDIT_ERROR'} if intake_errors else set())))
        self.hole_combo.configure(values=values)
        if self.hole_filter.get() not in values:
            self.hole_filter.set('All')
        self.hole_tree.delete(*self.hole_tree.get_children())
        view=self.problem_view.get()
        if view=='All Catalog':allowed=None
        elif view=='Accepted Master Catalog':allowed={r['id'] for r in self.db.works(accepted_only=True)}
        else:
            set_uuid=self.active_set_uuid if view=='Active Working Set' else self.catalog_named_sets.get(view)
            allowed={i['work_id'] for i in self.db.working_sets.items(set_uuid) if i['work_id']}
        pins=self.scope_audits(self.problem_view.get())
        for r in self.db.holes(self.hole_filter.get(),include_ignored=self.show_ignored.get(),audit_ids=list(pins.values()) if pins is not None else None):
            if allowed is not None and r['work_id'] not in allowed:continue
            details=safe_json(r['details_json'])
            disposition=self.db.problem_disposition(r['id'])
            problem_class,next_action,_,_=problem_policy(r['code'],details)
            if self.problem_class_filter.get() not in ('All',problem_class):continue
            self.hole_tree.insert('', 'end', iid=str(r['id']), values=(
                r['title'], r['severity'].upper(), r['code'], problem_class,
                next_action,details.get('confidence') or '',
                details.get('affected') or len(details.get('chapters') or ()),
                disposition['status'] if disposition else '',r['message'], r['audit_created_at'],
            ))
        if self.hole_filter.get() in ('All','AUDIT_ERROR'):
            problem_class,next_action,_,_=problem_policy('AUDIT_ERROR')
            if self.problem_class_filter.get() in ('All',problem_class):
                for failure in intake_errors:
                    item=failure['item'];hole=failure['hole']
                    self.hole_tree.insert('','end',iid='i:'+item['working_set_item_uuid'],values=(
                        item['original_query'],'ERROR','AUDIT_ERROR',problem_class,next_action,'',0,'',
                        hole['message'],failure['observation']['created_at']))

    def scoped_problems(self,include_ignored=False):
        pins=self.scope_audits(self.problem_view.get())
        return self.db.holes('All',include_ignored=include_ignored,
                             audit_ids=list(pins.values()) if pins is not None else None)

    def scoped_intake_errors(self):
        view=self.problem_view.get()
        if view=='Accepted Master Catalog':return []
        if view=='All Catalog':return self.db.working_sets.audit_errors()
        set_uuid=self.active_set_uuid if view=='Active Working Set' else self.catalog_named_sets.get(view)
        return self.db.working_sets.audit_errors(set_uuid) if set_uuid else []

    def refresh_detail_titles(self):
        keep = self.detail_titles.selection()
        self.detail_titles.delete(*self.detail_titles.get_children())
        allowed=self.scoped_work_ids()
        for r in self.db.works(audit_by_work=self.scope_audits()):
            if r['id'] not in allowed:continue
            self.detail_titles.insert('', 'end', iid=str(r['id']), values=(r['match_title'] or r['input_title'],))
        for iid in keep:
            if self.detail_titles.exists(iid): self.detail_titles.selection_set(iid)

    def open_details_from(self, tree):
        ids = self.selected_ids(tree)
        if tree is self.audit_tree and not ids:
            selected=tree.selection()
            item=self.db.working_sets.item(selected[0][2:]) if selected and selected[0].startswith('i:') else None
            ids=[item['work_id']] if item and item['work_id'] else []
        if not ids:
            return
        wid = ids[0]
        self.nb.select(self.tabs[3])
        if self.detail_titles.exists(str(wid)):
            self.detail_titles.selection_set(str(wid)); self.detail_titles.see(str(wid))
        self.load_details(wid)

    def open_hole_details(self):
        sel = self.hole_tree.selection()
        if not sel:
            return
        if sel[0].startswith('i:'):
            item_uuid=sel[0][2:]
            failure=next((r for r in self.db.working_sets.audit_errors()
                          if r['item']['working_set_item_uuid']==item_uuid),None)
            if failure:
                set_uuid=failure['item']['working_set_uuid']
                scope=next((label for label,uid in self.catalog_named_sets.items() if uid==set_uuid),None)
                self.catalog_view.set('Active Working Set' if set_uuid==self.active_set_uuid else scope or 'All Catalog')
                self.refresh_catalog()
                if self.catalog_tree.exists(sel[0]):
                    self.catalog_tree.selection_set(sel[0]);self.catalog_selected()
                self.nb.select(self.catalog_tab)
            return
        hole_id = int(sel[0])
        row = next((r for r in self.scoped_problems(include_ignored=self.show_ignored.get()) if r['id'] == hole_id), None)
        if row:
            filters={'UNMAPPED_CHAPTERS':'Unmapped','REFERENCE_CONFLICT':'Conflicts',
                     'CHAPTER_COUNT_DISAGREEMENT':'Missing','MISSING_REFERENCE_STRUCTURE':'Unmapped'}
            details=safe_json(row['details_json'])
            keys=details.get('chapters') or None
            self.editor.open(row['work_id'],filters.get(row['code'],'All'),keys)
            self.editor.log(row['code']+': '+row['message'])

    def problem_selected(self):
        selected=self.hole_tree.selection()
        self.problem_text.configure(state='normal');self.problem_text.delete('1.0','end')
        if selected:
            if selected[0].startswith('i:'):
                failure=next((r for r in self.db.working_sets.audit_errors()
                              if r['item']['working_set_item_uuid']==selected[0][2:]),None)
                if failure:
                    item=failure['item'];working_set=failure['working_set']
                    self.problem_text.insert('1.0',json.dumps({
                        'kind':'working_set_intake_audit_error',
                        'working_set':working_set['name'],
                        'working_set_uuid':working_set['working_set_uuid'],
                        'working_set_item_uuid':item['working_set_item_uuid'],
                        'query':item['original_query'],'edition':item['requested_edition'],
                        'language':item['requested_language'],'audit_id':None,
                        'error':failure['hole']['message']},ensure_ascii=False,indent=2))
            else:
                row=next((r for r in self.scoped_problems(include_ignored=self.show_ignored.get()) if str(r['id'])==selected[0]),None)
                if row:
                    packet=review_packet(self.db,problem_ids={row['id']},include_ignored=True,audit_by_work=self.scope_audits(self.problem_view.get()))
                    self.problem_text.insert('1.0',packet_markdown(packet))
        self.problem_text.configure(state='disabled')

    def selected_review_packet(self, selected_only=False):
        scope='Selected problems' if selected_only else self.review_scope.get()
        if scope=='Selected problems':
            if any(i.startswith('i:') for i in self.hole_tree.selection()):
                raise ValueError('Intake audit failures have no audit row; use Working Set Review Context for their diagnostics.')
            ids={int(i) for i in self.hole_tree.selection()}
            if not ids: raise ValueError('Select one or more problem rows first.')
            return review_packet(self.db,problem_ids=ids,include_ignored=self.show_ignored.get(),audit_by_work=self.scope_audits(self.problem_view.get()))
        if scope=='Selected titles':
            ids=set(self.selected_ids(self.audit_tree))
            ids.update(item['work_id'] for item in
                (self.db.working_sets.item(key) for key in self.selected_queue_ids() if isinstance(key,str))
                if item and item['work_id'])
            if not ids: raise ValueError('Select title rows in Audit first.')
            return review_packet(self.db,work_ids=ids,include_ignored=self.show_ignored.get(),audit_by_work=self.scope_audits(self.problem_view.get()))
        if self.problem_view.get()=='All Catalog':return review_packet(self.db)
        view=self.problem_view.get()
        if view=='Accepted Master Catalog':ids={r['id'] for r in self.db.works(accepted_only=True)}
        else:
            set_uuid=self.active_set_uuid if view=='Active Working Set' else self.catalog_named_sets.get(view)
            ids={r['work_id'] for r in self.db.working_sets.items(set_uuid) if r['work_id']}
        return review_packet(self.db,work_ids=ids,include_ignored=self.show_ignored.get(),audit_by_work=self.scope_audits(self.problem_view.get()))

    def export_detailed_problems(self):
        try:
            packet=self.selected_review_packet()
            path=filedialog.asksaveasfilename(defaultextension='.csv',initialfile='mangaanka_problems_detailed.csv',filetypes=[('CSV','*.csv')])
            if path: messagebox.showinfo(APP,f'Exported {detailed_csv(packet,path)} diagnostic row(s).')
        except (ValueError,OSError) as exc: messagebox.showerror(APP,str(exc))

    def export_review_packet(self):
        try:
            packet=self.selected_review_packet()
            path=filedialog.asksaveasfilename(defaultextension='.md',initialfile='mangaanka_review_packet.md',filetypes=[('Markdown','*.md')])
            if path:
                md,js=write_packet(packet,path)
                messagebox.showinfo(APP,f'Exported review packet:\n{md}\n{js}')
        except (ValueError,OSError) as exc: messagebox.showerror(APP,str(exc))

    def copy_diagnostics(self,selected_only=False):
        try:
            packet=self.selected_review_packet(True) if selected_only else self.selected_review_packet()
            self.clipboard_clear();self.clipboard_append(packet_markdown(packet));self.update()
            self.batch.set(f'Copied {len(packet["works"])} title diagnostics to clipboard.')
        except (ValueError,OSError) as exc: messagebox.showerror(APP,str(exc))

    def copy_selected_title_diagnostic(self):
        selection=self.hole_tree.selection()
        if not selection:
            messagebox.showerror(APP,'Select a problem title first.');return
        if selection[0].startswith('i:'):
            self.problem_selected()
            self.clipboard_clear();self.clipboard_append(self.problem_text.get('1.0','end-1c'));self.update()
            return
        row=next((r for r in self.scoped_problems(include_ignored=True) if str(r['id'])==selection[0]),None)
        if not row:return
        packet=review_packet(self.db,work_ids={row['work_id']},include_ignored=True)
        self.clipboard_clear();self.clipboard_append(packet_markdown(packet));self.update()

    def ignore_problem(self):
        selected=self.hole_tree.selection()
        if len(selected)!=1:
            messagebox.showerror(APP,'Select exactly one problem.');return
        row=next((r for r in self.scoped_problems(include_ignored=self.show_ignored.get()) if str(r['id'])==selected[0]),None)
        if not row: return
        if row['code']!='UNCLASSIFIED_ACQUISITION':
            messagebox.showerror(APP,'Only unclassified acquisition can be ignored with a reason.');return
        win=tk.Toplevel(self);win.title('Ignore with Reason');win.configure(bg=BG);win.geometry('610x260')
        box=ttk.Frame(win,padding=14);box.pack(fill='both',expand=True)
        ttk.Label(box,text=f"{row['title']} — {row['code']}").pack(anchor='w')
        ttk.Label(box,text='Reason grounded in the source and chapter evidence').pack(anchor='w',pady=(10,0))
        reason=tk.StringVar();ttk.Entry(box,textvariable=reason,width=78).pack(fill='x')
        ttk.Label(box,text='Repeat provider pattern (optional; same pattern on 2+ titles creates a code-review candidate)').pack(anchor='w',pady=(8,0))
        pattern=tk.StringVar();ttk.Entry(box,textvariable=pattern,width=78).pack(fill='x')
        verification=tk.StringVar(value='REVIEWED')
        ttk.Combobox(box,textvariable=verification,state='readonly',values=('REVIEWED','VERIFIED'),width=15).pack(anchor='w',pady=7)
        def submit():
            try:
                self.db.dispose_problem(row['id'],reason.get(),verification.get(),pattern.get(),item_uuid=self.problem_item_uuid(row['work_id']))
                win.destroy();self.refresh_all()
            except ValueError as exc: messagebox.showerror(APP,str(exc),parent=win)
        ttk.Button(box,text='Record disposition',command=submit).pack(anchor='e')

    def reopen_ignored_problem(self):
        selected=self.hole_tree.selection()
        if len(selected)!=1:
            messagebox.showerror(APP,'Select exactly one ignored problem.');return
        row=next((r for r in self.scoped_problems(include_ignored=True) if str(r['id'])==selected[0]),None)
        if not row or not (self.db.problem_disposition(row['id']) and
                          self.db.problem_disposition(row['id'])['status']=='IGNORED_WITH_REASON'):
            messagebox.showerror(APP,'Select a currently ignored problem.');return
        win=tk.Toplevel(self);win.title('Reopen Problem');win.configure(bg=BG);win.geometry('590x185')
        box=ttk.Frame(win,padding=14);box.pack(fill='both',expand=True)
        ttk.Label(box,text=f"Reopen {row['title']} — {row['code']}").pack(anchor='w')
        ttk.Label(box,text='Reason').pack(anchor='w',pady=(9,0))
        reason=tk.StringVar();ttk.Entry(box,textvariable=reason,width=75).pack(fill='x')
        def submit():
            try:
                self.db.reopen_problem(row['id'],reason.get(),item_uuid=self.problem_item_uuid(row['work_id']))
                win.destroy();self.refresh_all()
            except ValueError as exc: messagebox.showerror(APP,str(exc),parent=win)
        ttk.Button(box,text='Reopen',command=submit).pack(anchor='e',pady=8)

    def audit_again(self):
        ids = self.selected_ids(self.title_tree)
        if ids:
            try:
                items=[self.curation_item_uuid(wid) for wid in ids]
                self.nb.select(self.tabs[0]); self.start_audit(items if all(items) else ids,global_context=not any(items))
            except ValueError as exc:messagebox.showerror(APP,str(exc))

    def detail_selected(self):
        ids = self.selected_ids(self.detail_titles)
        if ids:
            self.load_details(ids[0])

    def load_details(self, work_id):
        work = self.db.work(work_id)
        audit = self.scoped_audit(work_id)
        self._active_work_id = work_id
        self.inventory_tree.delete(*self.inventory_tree.get_children())
        self.detail_header.set((audit['match_title'] if audit and audit['match_title'] else work['input_title']) if work else 'Unknown')
        if not audit:
            self.detail_summary.set('Not audited yet.')
            self.set_detail_text('')
            return
        self.detail_summary.set(
            f"Query: {audit['query']}   Match: {audit['match_tier'] or '—'}   "
            f"Providers in canonical group: {audit['provider_count']}   "
            f"Selected: {audit['selected_source_name'] or audit['selected_source'] or '—'}   "
            f"Workflow: {audit['workflow']}   Alias retry: {audit['alias_retry'] or 'none'}"
        )
        inventories = safe_json(audit['inventories_json'])
        for index, inv in enumerate(inventories):
            self.inventory_tree.insert('', 'end', iid=f'i{index}', values=(
                inv.get('source_name') or inv.get('source_id'), 'Yes' if inv.get('usable') else 'No',
                'Yes' if inv.get('complete') else 'No', inv.get('chapter_count',0),
                inv.get('native_volumes',0), inv.get('standalone_chapters',0), inv.get('summary') or inv.get('error') or '',
            ))
        holes = self.db.holes('All',audit_ids=[audit['id']])
        states = safe_json(audit['provider_states_json'])
        enrichment = safe_json(audit['enrichment_errors_json'])
        lines = [
            'PINNED WORKING SET AUDIT' if self.scope_audits() is not None else 'LATEST GLOBAL AUDIT',
            f"Snapshot audit: {audit['id']} · Latest global: {self.db.latest_audit(work_id)['id']} · Acceptance: {self.db.acceptance.state(work_id)}",
            'Curation edits shared catalog data; this Working Set owns its audit pin.',
            f"Matched title: {audit['match_title'] or '—'}",
            f"Match tier: {audit['match_tier'] or '—'}",
            f"Canonical grouping: {audit['group_confidence'] or '—'} / {audit['group_reason'] or '—'}",
            f"Reported chapter totals: {audit['reported_chapters'] or '[]'}",
            f"Reported volume totals: {audit['reported_volumes'] or '[]'}",
            f"Resolution error: {audit['resolution_error'] or 'none'}",
            '', 'HOLES',
        ]
        if holes:
            lines.extend(f"[{h['severity'].upper()}] {h['code']}: {h['message']}" for h in holes)
        else:
            lines.append('No holes flagged.')
        lines.extend(['', 'PROVIDER SEARCH STATES'])
        for p in states if isinstance(states,list) else []:
            lines.append(f"{p.get('display_name') or p.get('source_id')}: {p.get('status')} {p.get('error') or ''}".rstrip())
        lines.extend(['', 'OPTIONAL ENRICHMENT ERRORS'])
        if enrichment:
            for k,v in enrichment.items(): lines.append(f'{k}: {v}')
        else:
            lines.append('none')
        publication = safe_json(audit['publication_json'])
        health_state=safe_json(audit['health_json']) or health(publication,[],work['edition'])
        state = self.db.catalog.state(work_id)
        normalization=publication.get('normalization') or {}
        classified=publication_classification_counts(publication)
        publication_view=dict(publication,**classified)
        if isinstance(publication.get('automatic'),dict):
            automatic=publication['automatic']
            publication_view['automatic']=dict(automatic,**publication_classification_counts(automatic))
        context=publication.get('context') or {}
        reference=publication.get('references') or {}
        headline=['REVIEW DIAGNOSTIC — '+work['input_title'],
                  f"Search: {audit['query']} → {audit['match_title'] or 'none'} ({audit['match_tier'] or 'unknown'})",
                  f"Work: {context.get('canonical_title') or 'unverified'} / {context.get('canonical_work_id') or 'none'}",
                  f"Identity: {context.get('identity_confidence') or 'unverified'}; {context.get('shareability_reason') or 'shareable'}",
                  f"Edition: requested {work['edition']} / selected {publication.get('edition') or 'unknown'}; language {work['language']}",
                  f"Acquisition: {audit['selected_source_name'] or audit['selected_source'] or 'none'}; raw records {publication.get('raw_acquisition_records','—')}",
                  f"Selected acquisition: {publication.get('selected_acquisition_title') or 'not recorded'}; edition {publication.get('acquisition_edition') or 'not recorded'}",
                  f"Canonical main: {publication.get('canonical_main_chapters','—')}; specials: {publication.get('recognized_specials','—')}; duplicates: {publication.get('duplicate_records','—')}; provider artifacts: {classified['classified_provider_artifacts']}; unclassified: {classified['unclassified_records']}",
                  f"Provider artifact breakdown: {json.dumps(classified['provider_artifact_breakdown'],ensure_ascii=False,sort_keys=True)}",
                  f"Effective publication: {publication.get('logical_chapters','—')} chapters; {publication.get('final_volumes','—')} volumes; mapped {publication.get('mapped_chapters','—')}; unmapped {publication.get('unmapped_chapters','—')}",
                  f"MangaDex: {(reference.get('mangadex_structure') or {}).get('status','not run')}; Wikipedia: {(reference.get('wikipedia') or {}).get('status','not run')}",
                  f"Structural coverage: {json.dumps(publication.get('structural_coverage') or {},ensure_ascii=False,sort_keys=True)}",
                  f"Normalization: {normalization.get('status','legacy audit; rerun required')}",
                  f"Health: identity {health_state['identity']} / publication {health_state['publication']} / normalization {health_state['normalization']} / acquisition {health_state['acquisition']}",
                  'PROBLEMS']
        for hole in holes:
            details=safe_json(hole['details_json'])
            headline.append(f"{hole['code']}: {hole['message']}")
            if details.get('chapters'):
                headline.append('Affected chapters: '+', '.join(map(str,details['chapters'][:80])))
        if not holes: headline.append('none')
        lines[:0]=headline+['','DETAILED EVIDENCE']
        lines.extend(['', 'CURATED DATABASE',
                      f"Catalog revision: {state['revision']}; audited revision: {publication.get('curation_revision', 0)}",
                      f"Lookup: {publication.get('curated_database', {}).get('status', 'not recorded; rerun required')}",
                      f"Identity: {state['identity']}",
                      f"Manual fields: {len(state['fields'])}",
                      '', 'REPORTED COUNTS WITH SOURCE PROVENANCE'])
        lines.extend(['','PROVIDER ARTIFACT GROUPS'])
        artifact_groups=normalization.get('artifact_groups') or []
        if not artifact_groups: lines.append('none')
        for group in artifact_groups:
            lines.append(f"{group.get('provider')} / {group.get('classification')} / {group.get('pattern_family')}: "
                         f"{group.get('count')} records; {group.get('confidence')} confidence")
            lines.append(str(group.get('reason') or ''))
            for member in group.get('member_records') or []:
                lines.append('  '+json.dumps(member,ensure_ascii=False,sort_keys=True))
        diff=self.db.audit_diff(work_id)
        lines.extend(['','RE-AUDIT DIFF',json.dumps(diff,ensure_ascii=False,indent=2) if diff else 'No preceding audit.'])
        for count in publication.get('reported_count_provenance') or []:
            lines.append(json.dumps(count,ensure_ascii=False))
        if not publication.get('reported_count_provenance'):
            lines.append('No attributed count evidence in this audit; rerun required for legacy totals.')
        lines.extend(['', 'EXACT MAPPING DIAGNOSTICS',
                      'Unmapped: '+', '.join(str(r.get('chapter') or r.get('id')) for r in publication.get('unmapped') or []),
                      'Conflicts: '+', '.join(publication.get('conflicting_chapters') or [])])
        lines.extend(['', 'FINAL AUDIT',
                      f"State: {self.audit_state(next(r for r in self.db.works([work_id],audit_by_work=self.scope_audits()) if r['id'] == work_id))}",
                      f"Edition: {audit['selected_edition'] or 'unknown'}",
                      f"Logical chapters: {audit['logical_chapters']}",
                      f"Final volumes: {audit['final_volumes']}",
                      f"Mapped: {audit['mapped_chapters']}/{audit['logical_chapters']}",
                      f"Unmapped: {audit['unmapped_chapters']}",
                      f"Native / derived volumes: {publication.get('native_volumes', '—')} / {publication.get('derived_volumes', '—')}",
                      f"Manifest work: {publication.get('manifest', {}).get('work', {}).get('canonical_identity', '—')}",
                      f"Manifest edition: {publication.get('manifest', {}).get('edition', {}).get('identity', '—')}",
                      f"MangaDex structure: {publication.get('references', {}).get('mangadex_structure', {}).get('status', 'not run')}",
                      f"Wikipedia structure: {publication.get('references', {}).get('wikipedia', {}).get('status', 'not run')}",
                      f"Conflicting chapters: {publication.get('conflicting_chapters', [])}",
                      '', 'REFERENCE / PUBLICATION (including per-chapter provenance)',
                      json.dumps(publication_view, ensure_ascii=False, indent=2),
                      '', 'SEARCH RECORDS',
                      json.dumps(safe_json(audit['provider_rows_json']), ensure_ascii=False, indent=2)])
        self.set_detail_text('\n'.join(lines))

    def set_detail_text(self, value):
        self.detail_text.configure(state='normal')
        self.detail_text.delete('1.0','end')
        self.detail_text.insert('1.0',value)
        self.detail_text.configure(state='disabled')

    def export_holes(self):
        path = filedialog.asksaveasfilename(defaultextension='.csv', initialfile='mangaanka_search_holes.csv', filetypes=[('CSV','*.csv')])
        if path:
            n = self.db.audit_csv(path); messagebox.showinfo(APP, f'Exported {n} detected hole(s).')

    def export_summary(self):
        path = filedialog.asksaveasfilename(defaultextension='.csv', initialfile='mangaanka_search_audit_summary.csv', filetypes=[('CSV','*.csv')])
        if path:
            n = self.db.audit_summary_csv(path); messagebox.showinfo(APP, f'Exported {n} title audit row(s).')

    def close(self):
        self.auditor.stop()
        self.destroy()

    def destroy(self):
        if hasattr(self,'writer_lock'):self.writer_lock.close()
        super().destroy()


if __name__ == '__main__':
    App().mainloop()
