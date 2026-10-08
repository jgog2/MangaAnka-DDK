"""Run Workflow contracts with the final EXE's actual embedded application code."""
from pathlib import Path
import sys
import unittest
from PyInstaller.archive.readers import CArchiveReader
from smoke_packaged_transition import main as protected_main


def main():
    if protected_main():return 1
    exe=Path(sys.argv[1]).resolve()
    pyz=CArchiveReader(str(exe)).open_embedded_archive('PYZ.pyz')
    names=('qt_app.orchestration','qt_app.workflow_presentation','qt_app.export_receipts',
        'qt_app.pages.workflow','qt_app.widgets.workflow','qt_app.icons','qt_app.pages.curate',
        'qt_app.pages.problems','qt_app.widgets.command_drawer','ddk_exports','ddk_review')
    for name in names:
        embedded=pyz.extract(name)
        source=Path(__file__).resolve().parents[1]/(name.replace('.','/')+'.py')
        assert compile(source.read_text(encoding='utf-8-sig'),embedded.co_filename,'exec',dont_inherit=True)==embedded,name
    from test_workflow import Workflow,WorkflowPresentation
    from test_workflow_actions import ActionPages,ActionPresentation
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(case) for case in (Workflow,WorkflowPresentation,ActionPages,ActionPresentation))
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    print('Verified 23 embedded modules match final source, including saved problem actions.')
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())
