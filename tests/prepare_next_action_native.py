"""Native smoke fixtures only; never reads remembered production settings."""
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QSettings
from qt_app.session import Session
from qt_app.preferences import remember_session
from test_working_set_audit_recovery import publication


def main():
    root=Path(__file__).resolve().parents[1]/'build/next-action-native'
    root.mkdir(parents=True,exist_ok=True)
    path=root/'Next Action disposable.db'
    if path.exists():raise RuntimeError('Existing disposable fixture retained; choose a fresh directory.')
    session=Session(path,create=True,role='TEST');db=session.db
    try:
        uid=db.working_sets.create('Next Action disposable');session.activate_working_set(uid)
        research={'Dr. STONE':['REFERENCE_CONFLICT','UNMAPPED_CHAPTERS','PROVIDER_FRACTIONAL_CANDIDATE','UNCLASSIFIED_ACQUISITION'],
            'Sakamoto Days':['UNMAPPED_CHAPTERS','PROVIDER_FRACTIONAL_CANDIDATE','PROVIDER_SPLIT_CANDIDATE','UNCLASSIFIED_ACQUISITION'],
            'The Promised Neverland':['UNMAPPED_CHAPTERS','PROVIDER_FRACTIONAL_CANDIDATE','UNCLASSIFIED_ACQUISITION']}
        db.working_sets.add_requests(uid,list(research)+['Code control','Acquisition control','Eligible control'])
        items=db.working_sets.items(uid)
        for item in items[:3]:
            holes=[dict(code=code,severity='warning',message='Disposable research observation',details=dict(chapters=['26.5']))
                   for code in research[item['original_query']]]
            db.working_sets.observe_unresolved(item['working_set_item_uuid'],dict(query=item['original_query']),holes)
        db.add_titles(['Code control','Acquisition control','Eligible control'],'standard','en')
        for wid,item in enumerate(items[3:],1):
            holes=[] if wid==3 else [dict(code='PROVIDER_FRACTIONAL_CANDIDATE' if wid==1 else 'ACQUISITION_COVERAGE_GAP',
                severity='warning',message='Disposable linked control')]
            pub=publication('Monster')
            pub['catalog_identity']['canonical_work_id']=f'fixture:control-{wid}'
            pub['catalog_identity']['external_ids']={'fixture':f'control-{wid}'}
            aid=db.save_audit(wid,dict(query=item['original_query'],publication=pub),holes)
            db.working_sets.pin(item['working_set_item_uuid'],wid,aid)
        settings=QSettings(str(root/'ui.ini'),QSettings.IniFormat);remember_session(session,settings)
    finally:session.close()
    manifest=dict(path=str(path),set_uuid=uid,sha256_before=hashlib.sha256(path.read_bytes()).hexdigest())
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest))


if __name__=='__main__':main()
