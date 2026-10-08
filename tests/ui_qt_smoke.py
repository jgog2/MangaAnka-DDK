"""Disposable Qt geometry/scaling smoke and optional review screenshots."""
import argparse
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QSettings,Qt
from PySide6.QtWidgets import QApplication
from qt_app.session import Session
from qt_app.main_window import MainWindow
from qt_app.theme import apply_theme
from test_pre_catalog_hardening import fixture,ODD
from test_working_sets import publication


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--screenshots',type=Path);parser.add_argument('--expected-scale',type=float);args=parser.parse_args()
    app=QApplication([]);apply_theme(app)
    with tempfile.TemporaryDirectory() as folder:
        session=Session(Path(folder)/'qt-smoke.db',create=True,role='TEST')
        try:
            db=session.db;db.add_titles(['MF Ghost','Monster'],'standard','en')
            pub=fixture(unmapped=True,odd=ODD)
            db.save_audit(1,dict(query='MF Ghost',match_title='MF Ghost',selected_source_name='MangaK',publication=pub,
                inventories=[dict(source_name='MangaK',chapter_count=279,native_volumes=0,standalone_chapters=279,usable=True,summary='Qualified standalone chapters')]),
                [dict(code='UNCLASSIFIED_ACQUISITION',severity='warning',message='Four provider-only records need grounded research.',details=dict(chapters=list(ODD)))])
            db.catalog.apply(db.catalog.preview(1,[dict(entity='chapter',key='275',field='volume',value='23',verification='VERIFIED'),
                dict(entity='chapter',key='275',field='title',value='Delving Into the Future',verification='VERIFIED')]))
            pub=fixture(unmapped=False,odd=ODD);pub['curation_revision']=db.catalog.state(1)['revision'];pub['curated_database']=db.catalog.state(1)
            pub['automatic']=fixture(unmapped=True,odd=ODD)
            pub['projection'][274]['title']='Delving Into the Future'
            db.save_audit(1,dict(query='MF Ghost',match_title='MF Ghost',selected_source_name='MangaK',publication=pub),
                [dict(code='UNCLASSIFIED_ACQUISITION',severity='warning',message='Four provider-only records require research.',details=dict(chapters=list(ODD)))])
            db.save_audit(2,dict(query='Monster',match_title='Monster',selected_source_name='MangaPill',publication=publication(canonical='fixture:monster')),[])
            uid=db.working_sets.create('Catalog Batch 003');db.working_sets.set_active(uid);db.working_sets.add_requests(uid,['MF Ghost','Monster'])
            for item,wid in zip(db.working_sets.items(uid),(1,2)):db.working_sets.pin(item['working_set_item_uuid'],wid,db.latest_audit(wid)['id'])
            window=MainWindow(session,QSettings(str(Path(folder)/'ui.ini'),QSettings.IniFormat));window.safe=lambda cb:cb();window.show();app.processEvents()
            if args.expected_scale:assert abs(window.devicePixelRatioF()-args.expected_scale)<.02,(window.devicePixelRatioF(),args.expected_scale)
            for width,height in ((1120,720),(1440,900),(1920,1080)):
                window.resize(width,height);app.processEvents()
                for name in window.pages:
                    window.navigate(name);app.processEvents();assert window.width()==width
                    page=window.pages[name];assert page.toolbar.geometry().right()<=page.width()
                window.navigate('Workflow');window.workflow.table.selectRow(0);app.processEvents()
                page=window.workflow
                for b in [page.new_button,page.intake_button,page.run_button,page.batch_actions_button,*page.production_buttons]:
                    assert b.geometry().width()>0 and b.isVisibleTo(page)
                    mapped=b.mapTo(page,b.rect().topLeft())
                    assert mapped.x()>=0 and mapped.x()+b.width()<=page.width(),(width,height,b.text(),mapped,b.size(),page.size())
                assert page.table.horizontalScrollBar().maximum()==0,(width,height,page.table.horizontalScrollBar().maximum())
                assert page.table.viewport().height()>=110,(width,height,page.table.viewport().height())
                if width>=1440:
                    from PySide6.QtWidgets import QLabel
                    acquisition=next(label for label in page.inspector.findChildren(QLabel) if label.text()=='Acquisition')
                    bottom=acquisition.mapTo(page.inspector.viewport(),acquisition.rect().bottomLeft()).y()
                    assert bottom<page.inspector.viewport().height(),(width,height,'four health rows must fit',bottom,page.inspector.viewport().height())
                window.drawer.set_expanded(True);app.processEvents()
                assert window.width()==width and window.height()==height
                assert page.table.viewport().height()>=70,(width,height,'expanded',page.table.viewport().height())
                for b in page.production_buttons:
                    position=b.mapTo(page,b.rect().topLeft())
                    assert position.y()+b.height()<=page.height(),(width,height,b.text(),'expanded')
                window.drawer.set_expanded(False);app.processEvents()
                if args.screenshots:
                    args.screenshots.mkdir(parents=True,exist_ok=True)
                    assert window.grab().save(str(args.screenshots/f'workflow-{width}x{height}.png'))
                if args.screenshots and width>=1440:
                    args.screenshots.mkdir(parents=True,exist_ok=True)
                    window.catalog.table.selectRow(0);window.problems.table.selectRow(0)
                    window.open_curate(1,'active',['275']);window.open_details(1,'active');window.details.tabs.setCurrentIndex(0)
                    for name in ('Catalog','Problems','Curate','Details'):
                        window.navigate(name);app.processEvents();assert window.grab().save(str(args.screenshots/f'{name.lower()}-{width}x{height}.png'))
            with db.con() as con:assert con.execute('PRAGMA user_version').fetchone()[0]==8
            print(f'Qt smoke passed: seven pages, reachable Workflow actions, no core table horizontal scrolling; three logical sizes, scale {window.devicePixelRatioF():g}; disposable schema-v8 catalog')
            window.close();app.processEvents()
        finally:session.close()


if __name__=='__main__':main()
