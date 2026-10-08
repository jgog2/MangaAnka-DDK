"""Stable session preferences outside the catalog; no lifecycle decisions."""
import hashlib
import os
from pathlib import Path

from qt_app.session import Session


def database_key(path):
    return hashlib.sha256(os.path.normcase(str(Path(path).resolve())).encode('utf-8')).hexdigest()


def restore_working_set(session, settings):
    key='session/databases/'+database_key(session.db.path)+'/'
    if settings.value(key+'database_uuid','') != session.db.database_uuid:
        return
    session.restore_working_set(settings.value(key+'working_set_uuid',''))


def remember_session(session, settings):
    key='session/databases/'+database_key(session.db.path)+'/'
    settings.setValue(key+'database_uuid',session.db.database_uuid)
    settings.setValue(key+'working_set_uuid',session.active_uuid or '')
    settings.setValue('session/last_database',str(session.db.path.resolve()))
    settings.sync()


def restore_session(settings):
    """Use the normal validated open path, never implicit creation or fallback."""
    path=settings.value('session/last_database','')
    if not path:
        return None,''
    session=None
    try:
        session=Session(Path(path),create=False)
        restore_working_set(session,settings)
        return session,''
    except Exception as exc:
        if session:session.close()
        return None,'Could not reopen the previous database: '+str(exc)+'\nChoose a database below.'
