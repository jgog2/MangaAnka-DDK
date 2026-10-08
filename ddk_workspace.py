"""Validate DDK databases before activation and retain the active database path."""
import json
import sqlite3
from contextlib import closing
from pathlib import Path


CONFIG = 'active_database.json'
REQUIRED = {'works', 'search_audits', 'audit_holes'}


def validate_database(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError(f'Database does not exist: {path}')
    try:
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as con:
            tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not REQUIRED <= tables:
                raise ValueError('This is not a MangaAnkā DDK database (required tables are missing).')
            version = con.execute('PRAGMA user_version').fetchone()[0]
            if version > 8:
                raise ValueError(f'Database schema v{version} is newer than this DDK supports.')
            if con.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                raise ValueError('Database integrity check failed.')
    except sqlite3.DatabaseError as exc:
        raise ValueError(f'Cannot open a valid SQLite database: {exc}') from exc
    return path


def saved_path(workspace):
    config = Path(workspace) / CONFIG
    if not config.exists():
        return None
    try:
        return Path(json.loads(config.read_text(encoding='utf-8'))['active_database']).resolve()
    except (OSError, ValueError, KeyError, TypeError):
        return None


def remember_path(workspace, path):
    config = Path(workspace) / CONFIG
    temporary = config.with_suffix('.tmp')
    temporary.write_text(json.dumps({'active_database': str(Path(path).resolve())}, indent=2), encoding='utf-8')
    temporary.replace(config)
