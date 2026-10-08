"""Frozen Qt/session checks with disposable catalogs and offline controls."""
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
    archive=CArchiveReader(str(args.exe.resolve()));pyz=archive.open_embedded_archive('PYZ.pyz');loaded=set()
    class FrozenApp(importlib.abc.MetaPathFinder,importlib.abc.Loader):
        def find_spec(self,name,path=None,target=None):
            if name in pyz.toc and (name.startswith(('ddk_','qt_app')) or name=='mangaanka_database_development_kit'):
                return importlib.util.spec_from_loader(name,self,is_package=pyz.toc[name][0]==1)
        def create_module(self,spec):return None
        def exec_module(self,module):
            module.__file__=str(args.exe.resolve().parent/(module.__name__.replace('.','/')+'.py'))
            exec(pyz.extract(module.__name__),module.__dict__);loaded.add(module.__name__)
    sys.meta_path.insert(0,FrozenApp())
    names=('qt_app.app','qt_app.session','qt_app.preferences','qt_app.main_window','qt_app.workers',
           'ddk_acceptance','ddk_catalog','ddk_working_sets','ddk_commands','ddk_chapter_normalization',
           'ddk_publication','mangaanka_database_development_kit')
    for name in names:
        embedded=pyz.extract(name);source=Path(__file__).resolve().parents[1]/(name.replace('.','/')+'.py')
        assert compile(source.read_text(encoding='utf-8-sig'),embedded.co_filename,'exec',dont_inherit=True)==embedded,name
    assert not any(n.startswith('mangaanka_search_core.') for n in pyz.toc)
    assert not any(n.casefold().endswith(('.db','.sqlite','.sqlite3')) for n in archive.toc)
    from test_qt_session_restore import SessionRestore
    from test_mixed_tail_investigation import MixedTailInvestigation
    from test_wikipedia_membership_audit import WikipediaMembershipAudit
    from test_reference_integrity import ReferenceIntegrityAudit
    from test_artifact_authority import ArtifactAuthority
    from test_canonical_specials import CapturedDandadanSpecials
    from test_force_transactions import ForceTransactions
    from test_qt_force_transactions import QtForceTransactions
    from test_qt_force_reaudit import QtForceReaudit
    from test_lifecycle_v7 import LifecycleV7
    suite=unittest.TestSuite()
    for case in (SessionRestore,MixedTailInvestigation,WikipediaMembershipAudit,ReferenceIntegrityAudit,
                 ArtifactAuthority,CapturedDandadanSpecials,ForceTransactions,QtForceTransactions):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(case))
    for name in ('test_confirmation_actual_dialog_includes_title_and_cancel_is_default',
                 'test_force_uses_worker_progress_new_summary_and_refreshes_pin',
                 'test_failed_worker_reports_zero_new_and_keeps_old_pin','test_normal_run_and_audit_command_unchanged'):
        suite.addTest(QtForceReaudit(name))
    for name in ('test_curation_during_real_orchestration_discards_old_result_and_requeues',
                 'test_new_clean_audit_stales_approval_until_human_reaccepts'):
        suite.addTest(LifecycleV7(name))
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    assert {'qt_app.app','qt_app.preferences','qt_app.session','qt_app.main_window'}<=loaded
    print('Verified',len(names),'embedded modules match final source; shared core remains live; no DB payload.')
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())
