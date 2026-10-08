"""Prepare a disposable offline catalog for the actual EXE's UI smoke.

This script is never bundled. It prints explicit database/settings paths;
there is no production-catalog default and no provider request.
"""
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qt_app.session import Session
from test_working_sets import publication


def main():
    root=Path(tempfile.mkdtemp(prefix='mangaanka-qt-packaged-'))
    path=root/'packaged-smoke.db'
    session=Session(path,create=True,role='TEST')
    try:
        db=session.db;db.add_titles(['Monster'],'standard','en')
        wid=db.works()[0]['id']
        audit=db.save_audit(wid,dict(query='Monster',match_title='Monster',selected_source_name='Offline fixture',
            publication=publication(canonical='fixture:packaged'),inventories=[dict(source_name='Offline fixture',usable=True,
                chapter_count=1,native_volumes=0,standalone_chapters=1,summary='Offline structural fixture')]),[])
        uid=db.working_sets.create('Packaged Offline Set');db.working_sets.set_active(uid)
        db.working_sets.add_requests(uid,['Monster'])
        item=db.working_sets.items(uid)[0]['working_set_item_uuid'];db.working_sets.pin(item,wid,audit)
    finally:session.close()
    print(path);print(root/'ui.ini')


if __name__=='__main__':main()
