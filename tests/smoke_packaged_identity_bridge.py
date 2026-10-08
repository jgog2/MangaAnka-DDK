"""Verify frozen scoped creator authority and retained workflow protections."""
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
    exe=args.exe.resolve();pyz=CArchiveReader(str(exe)).open_embedded_archive('PYZ.pyz')
    class FrozenApp(importlib.abc.MetaPathFinder,importlib.abc.Loader):
        def find_spec(self,fullname,path=None,target=None):
            if fullname in pyz.toc and (fullname.startswith(('ddk_','qt_app')) or fullname=='mangaanka_database_development_kit'):
                return importlib.util.spec_from_loader(fullname,self,is_package=pyz.toc[fullname][0]==1)
        def create_module(self,spec):return None
        def exec_module(self,module):
            module.__file__=str(exe.parent/(module.__name__.replace('.','/')+'.py'))
            exec(pyz.extract(module.__name__),module.__dict__)
    sys.meta_path.insert(0,FrozenApp())
    names=('ddk_publisher_reference','ddk_publication','ddk_chapter_normalization','ddk_review',
        'ddk_catalog','ddk_acceptance','ddk_commands','ddk_working_sets','qt_app.workers',
        'qt_app.main_window','qt_app.pages.workflow','mangaanka_database_development_kit')
    for name in names:
        embedded=pyz.extract(name);source=Path(__file__).resolve().parents[1]/(name.replace('.','/')+'.py')
        assert compile(source.read_text(encoding='utf-8-sig'),embedded.co_filename,'exec',dont_inherit=True)==embedded,name
    assert not any(name.startswith('mangaanka_search_core.') for name in pyz.toc)
    suite=unittest.TestSuite()
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    for name in ('test_publisher_creator_equivalence','test_publisher_completion_authority','test_publisher_reference','test_logical_membership_authority',
                 'test_canonical_specials','test_force_all','test_qt_force_all','test_force_reaudit',
                 'test_qt_force_reaudit','test_force_transactions','test_qt_force_transactions'):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromName(name))
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    print('Twelve frozen modules match source; shared core external; disposable offline tests only.')
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())
