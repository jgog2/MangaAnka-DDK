"""External-only deterministic fixture for the final repair EXE smoke."""
from pathlib import Path
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from qt_app.session import Session
from test_publication_states import fixture,resolved,stored


def main():
    root=Path(tempfile.mkdtemp(prefix='mangaanka-serialization-smoke-'))
    session=Session(root/'serialization.db',create=True,role='TEST')
    try:
        res,bundle=fixture(dandadan=True);pub=resolved(res,bundle)
        wid,audit=stored(session.db,pub,res.primary)
        uid=session.db.working_sets.create('Serialization regression')
        session.db.working_sets.set_active(uid);session.db.working_sets.add_requests(uid,['Serialized fixture'])
        item=session.db.working_sets.items(uid)[0]['working_set_item_uuid']
        session.db.working_sets.pin(item,wid,audit)
        print('canonical main:',pub['canonical_main_chapters'],'mapped main:',pub['mapped_main_chapters'],
              'uncompiled:',pub['uncompiled_chapters'],'unmapped:',pub['unmapped_chapters'])
    finally:session.close()
    print(root/'serialization.db');print(root/'ui.ini')


if __name__=='__main__':main()
