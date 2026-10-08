"""External frozen-code/offline validation; no product smoke mode or live DB."""
import argparse
import importlib.abc
import importlib.util
import os
from pathlib import Path
import sys
import unittest
from PyInstaller.archive.readers import CArchiveReader

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('exe',type=Path);args=parser.parse_args()
    pyz=CArchiveReader(str(args.exe.resolve())).open_embedded_archive('PYZ.pyz')
    loaded=set()
    class FrozenApp(importlib.abc.MetaPathFinder,importlib.abc.Loader):
        def find_spec(self,name,path=None,target=None):
            if name in pyz.toc and (name.startswith(('ddk_','qt_app')) or name=='mangaanka_database_development_kit'):
                return importlib.util.spec_from_loader(name,self,is_package=pyz.toc[name][0]==1)
        def create_module(self,spec):return None
        def exec_module(self,module):
            module.__file__=str(args.exe.resolve().parent/(module.__name__.replace('.','/')+'.py'))
            exec(pyz.extract(module.__name__),module.__dict__);loaded.add(module.__name__)
    sys.meta_path.insert(0,FrozenApp())
    for name in ('ddk_publication','ddk_curated_resolution','mangaanka_database_development_kit',
                 'ddk_catalog','ddk_acceptance','qt_app.workers'):
        code=pyz.extract(name)
        source=Path(__file__).resolve().parents[1]/(name.replace('.','/')+'.py')
        assert compile(source.read_text(encoding='utf-8-sig'),code.co_filename,'exec',dont_inherit=True)==code,name
    assert not any(n.startswith('mangaanka_search_core.') for n in pyz.toc)
    from test_reference_integrity import ReferenceIntegrityAudit
    from test_canonical_specials import CapturedDandadanSpecials
    suite=unittest.TestSuite()
    for case in (ReferenceIntegrityAudit,CapturedDandadanSpecials):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(case))
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    assert {'ddk_publication','ddk_curated_resolution'} <= loaded
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())
