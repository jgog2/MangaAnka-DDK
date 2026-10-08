"""Execute frozen app modules from the final EXE with a disposable offline audit.

No smoke mode is added to the product, and no test code is bundled. A finder
loads DDK/Qt application modules from the embedded PYZ, while deterministic
provider/reference fixtures are injected through the existing auditor factory.
"""
import argparse
import importlib.abc
import importlib.util
import os
from pathlib import Path
import sys
import unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PyInstaller.archive.readers import CArchiveReader


def main():
    parser=argparse.ArgumentParser();parser.add_argument('exe',type=Path);args=parser.parse_args()
    archive=CArchiveReader(str(args.exe.resolve()));pyz=archive.open_embedded_archive('PYZ.pyz')
    loaded=[]
    class FrozenApp(importlib.abc.MetaPathFinder,importlib.abc.Loader):
        def find_spec(self,fullname,path=None,target=None):
            if fullname in pyz.toc and (fullname.startswith(('ddk_','qt_app')) or fullname=='mangaanka_database_development_kit'):
                return importlib.util.spec_from_loader(fullname,self,is_package=pyz.toc[fullname][0]==1)
        def create_module(self,spec):return None
        def exec_module(self,module):
            module.__file__=str(args.exe.resolve().parent/(module.__name__.replace('.','/')+'.py'))
            exec(pyz.extract(module.__name__),module.__dict__);loaded.append(module.__name__)
    sys.meta_path.insert(0,FrozenApp())
    from test_qt_force_reaudit import QtForceReaudit
    suite=unittest.TestSuite(QtForceReaudit(name) for name in (
        'test_confirmation_actual_dialog_includes_title_and_cancel_is_default',
        'test_force_uses_worker_progress_new_summary_and_refreshes_pin',
        'test_failed_worker_reports_zero_new_and_keeps_old_pin',
        'test_normal_run_and_audit_command_unchanged'))
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    required={'ddk_working_sets','qt_app.workers','qt_app.main_window','qt_app.pages.catalog'}
    assert required<=set(loaded),(required-set(loaded))
    print('Verified frozen application modules:',', '.join(sorted(required)))
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())
