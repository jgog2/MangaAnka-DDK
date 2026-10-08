"""Offline frozen-module verification; does not launch GUI or open live DB."""
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
    parser=argparse.ArgumentParser();parser.add_argument('exe',type=Path)
    parser.add_argument('--wikipedia-identity',action='store_true')
    parser.add_argument('--working-set-guards',action='store_true')
    parser.add_argument('--publisher-membership',action='store_true')
    parser.add_argument('--wikipedia-membership',action='store_true');args=parser.parse_args()
    archive=CArchiveReader(str(args.exe.resolve()))
    pyz=archive.open_embedded_archive('PYZ.pyz')
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
    for name in ('ddk_chapter_normalization','ddk_publication','ddk_curated_resolution','ddk_publisher_reference',
                 'mangaanka_database_development_kit','ddk_catalog','ddk_acceptance','qt_app.workers',
                 'ddk_review','ddk_exports','ddk_working_sets'):
        code=pyz.extract(name)
        source=Path(__file__).resolve().parents[1]/(name.replace('.','/')+'.py')
        assert compile(source.read_text(encoding='utf-8-sig'),code.co_filename,'exec',dont_inherit=True)==code,name
    assert not any(n.startswith('mangaanka_search_core.') for n in pyz.toc)
    assert not any(n.casefold().endswith(('.db','.sqlite','.sqlite3')) for n in archive.toc)
    from test_artifact_authority import ArtifactAuthority
    from test_reference_integrity import ReferenceIntegrityAudit
    from test_canonical_specials import CapturedDandadanSpecials
    suite=unittest.TestSuite()
    for case in (ArtifactAuthority,ReferenceIntegrityAudit,CapturedDandadanSpecials):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(case))
    if args.wikipedia_identity:
        from test_wikipedia_page_identity import WikipediaPageIdentity
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(WikipediaPageIdentity))
    if args.wikipedia_membership:
        from test_wikipedia_membership_audit import WikipediaMembershipAudit
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(WikipediaMembershipAudit))
    if args.working_set_guards:
        from test_working_set_review_guards import WorkingSetReviewGuards
        from test_uncompiled_future_totals import FutureTotals
        for case in (WorkingSetReviewGuards,FutureTotals):
            suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(case))
    if args.publisher_membership:
        from test_logical_membership_authority import LogicalMembershipAuthority
        from test_publisher_reference import PublisherProtocol,PublisherMembership,PublisherSupplements
        for case in (LogicalMembershipAuthority,PublisherProtocol,PublisherMembership,PublisherSupplements):
            suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(case))
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    assert {'ddk_chapter_normalization','ddk_publication','ddk_curated_resolution'} <= loaded
    if args.working_set_guards:
        assert {'ddk_review','ddk_exports','ddk_working_sets'} <= loaded
    if args.publisher_membership:
        assert 'ddk_publisher_reference' in loaded
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())
