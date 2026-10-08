"""Ephemeral action arguments, resolved against the one authoritative Session."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Target:
    item_uuid: str | None
    work_uuid: str | None
    edition: str
    language: str
    pin: int | None
    revision: int | None


@dataclass(frozen=True)
class Selection:
    database_uuid: str
    path: str
    scope: str
    set_uuid: str | None
    targets: tuple


def capture(session, scope, rows=()):
    targets = []
    for row in rows:
        item = row.get('_item')
        work = session.db.work(row['_work_id']) if row.get('_work_id') else None
        targets.append(Target(item['working_set_item_uuid'] if item else None,
            work['work_uuid'] if work else None, item['requested_edition'] if item else work['edition'],
            item['requested_language'] if item else work['language'],
            item['pinned_audit_id'] if item else None, item['pinned_audit_revision'] if item else None))
    return Selection(session.db.database_uuid, str(session.db.path), scope, session.set_uuid(scope), tuple(targets))


def resolve(session, selection):
    if selection.database_uuid != session.db.database_uuid or selection.path != str(session.db.path):
        raise ValueError('Selection belongs to another database; select again.')
    if session.set_uuid(selection.scope) != selection.set_uuid:
        raise ValueError('Working Set context changed; select again.')
    if selection.set_uuid and not session.db.working_sets.get(selection.set_uuid):
        raise ValueError('Working Set no longer exists.')
    rows = []
    current_rows = session.catalog_rows(selection.scope) if selection.targets else []
    for target in selection.targets:
        item = session.db.working_sets.item(target.item_uuid) if target.item_uuid else None
        if target.item_uuid:
            if not item or item['removed_at'] or item['working_set_uuid'] != selection.set_uuid:
                raise ValueError('Exact Working Set membership changed; select again.')
            if (item['requested_edition'], item['requested_language'], item['pinned_audit_id'], item['pinned_audit_revision']) != (
                    target.edition, target.language, target.pin, target.revision):
                raise ValueError('Selected identity/pin changed; refresh and select again.')
            work = session.db.work(item['work_id']) if item['work_id'] else None
        else:
            work = next((w for w in session.db.works() if w['work_uuid'] == target.work_uuid), None)
        if (work['work_uuid'] if work else None) != target.work_uuid:
            raise ValueError('Selected exact work changed; select again.')
        if work and (work['edition'], work['language']) != (target.edition, target.language):
            raise ValueError('Selected edition/language changed; select again.')
        row = next((r for r in current_rows if
            (r.get('_item') or {}).get('working_set_item_uuid') == target.item_uuid and
            r.get('_work_id') == (work['id'] if work else None)), None)
        if row is None:raise ValueError('Selection is no longer present in this scope.')
        rows.append(row)
    return rows
