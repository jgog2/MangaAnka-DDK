"""Validated database entry point with optional remembered-session restoration."""
import argparse
from pathlib import Path
import sys
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QDialog, QVBoxLayout, QLabel
from qt_app.theme import apply_theme
from qt_app.session import Session
from qt_app.main_window import MainWindow
from qt_app.widgets.common import button
from qt_app.preferences import restore_session


def main(argv=None):
    parser=argparse.ArgumentParser(description='MangaAnkā DDK Qt frontend')
    parser.add_argument('--database',type=Path,help='Explicit DDK database path (use a disposable catalog during development)')
    parser.add_argument('--create',action='store_true',help='Create a new empty database; never overwrites an existing file')
    parser.add_argument('--migrate-schema8',action='store_true',help='Explicitly migrate the named existing catalog, with backup; never applied to remembered catalogs')
    parser.add_argument('--role',choices=('TEST','SCRATCH','PRODUCTION'),default='SCRATCH')
    parser.add_argument('--ui-settings',type=Path,help='Optional separate INI file for layout/session preferences (useful for disposable smoke tests)')
    args=parser.parse_args(argv)
    if args.migrate_schema8 and (not args.database or args.create):
        parser.error('--migrate-schema8 requires one explicit existing --database path, without --create')
    app=QApplication(sys.argv[:1]);apply_theme(app)
    settings=QSettings(str(args.ui_settings.resolve()),QSettings.IniFormat) if args.ui_settings else QSettings('MangaAnka','DDK-Qt')
    session=None
    try:
        if args.database:session=Session(args.database,create=args.create,role=args.role,migrate_schema8=args.migrate_schema8)
        else:
            session,restore_note=restore_session(settings)
        if not args.database and session is None:
            welcome=QDialog();welcome.setWindowTitle('MangaAnkā DDK · Choose Database');welcome.resize(530,220);layout=QVBoxLayout(welcome)
            note=QLabel((restore_note+'\n\n' if restore_note else '')+'Choose a DDK database, or create a new scratch catalog. Only one frontend can write a database at a time.');note.setWordWrap(True);layout.addWidget(note)
            def choose(create):
                nonlocal session
                chooser=QFileDialog.getSaveFileName if create else QFileDialog.getOpenFileName
                path,_=chooser(welcome,'New Database' if create else 'Open Database',str(Path.cwd()),'SQLite databases (*.db *.sqlite)')
                if path:
                    try:session=Session(path,create=create,role=args.role);welcome.accept()
                    except Exception as exc:QMessageBox.warning(welcome,'Cannot open database',str(exc))
            layout.addWidget(button('Open Database…',lambda:choose(False)));layout.addWidget(button('New Scratch Database…',lambda:choose(True)))
            layout.addWidget(button('Cancel',welcome.reject))
            welcome.exec()
        if not session:return 0
        window=MainWindow(session,settings=settings);window.show();return app.exec()
    except Exception as exc:
        if session:session.close()
        QMessageBox.critical(None,'MangaAnkā DDK',str(exc));return 1


if __name__=='__main__':raise SystemExit(main())
