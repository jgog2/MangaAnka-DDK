"""Prepare only task-local disposable catalogs/settings for native EXE checks."""
import hashlib
import json
from pathlib import Path
import sys
from PySide6.QtCore import QSettings
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from qt_app.session import Session
from qt_app.preferences import remember_session
from test_working_set_audit_recovery import publication


def main():
    root=Path(__file__).resolve().parents[1]/'build/workflow-native'
    root.mkdir(parents=True,exist_ok=True)
    path=root/'Workflow 漫画 disposable.db'
    if path.exists():raise RuntimeError('Keep previous fixtures intact; select a new task-local fixture directory.')
    session=Session(path,create=True,role='TEST');db=session.db
    try:
        db.add_titles(['Monster','Fire Force'],'standard','en')
        uid=db.working_sets.create('Workflow Batch 003');db.working_sets.set_active(uid)
        db.working_sets.add_requests(uid,['Monster','Fire Force','Monster'])
        for item,wid,title in zip(db.working_sets.items(uid)[:2],(1,2),('Monster','Fire Force')):
            pub=publication(title)
            holes=[] if wid==1 else [dict(code='UNMAPPED_CHAPTERS',severity='warning',message='Disposable review fixture',details=dict(chapters=['1']))]
            aid=db.save_audit(wid,dict(query=title,match_title=title,selected_source_name='Fixture',publication=pub),holes)
            db.working_sets.pin(item['working_set_item_uuid'],wid,aid)
        db.working_sets.create('Unselected Batch')
        session.restore_working_set(uid)
        settings=QSettings(str(root/'ui.ini'),QSettings.IniFormat);remember_session(session,settings)
    finally:session.close()
    missing=QSettings(str(root/'missing.ini'),QSettings.IniFormat)
    missing.setValue('session/last_database',str(root/'must-not-create.db'));missing.sync()
    manifest=dict(path=str(path),set_uuid=uid,sha256_before=hashlib.sha256(path.read_bytes()).hexdigest())
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest))


if __name__=='__main__':main()
