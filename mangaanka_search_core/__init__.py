"""Load pure core modules from the development worktree, never a stale snapshot.

Do not execute the plugin __init__: it imports Calibre. The finder also gives
live source precedence over modules collected by a frozen executable.
"""
import importlib.abc
import importlib.machinery
import os
from pathlib import Path
import sys

PLUGIN_ROOT = Path(os.environ.get('MANGAANKA_PLUGIN_PATH',
                                 r'C:\MangaNana-Dev\MangaNana-calibre')).resolve()
if not (PLUGIN_ROOT / 'publication_manifest.py').is_file():
    raise ImportError(f'MangaAnkā worktree unavailable: {PLUGIN_ROOT}. '
                      'Set MANGAANKA_PLUGIN_PATH to the current plugin worktree.')
__path__ = [str(PLUGIN_ROOT)]


class _ReadOnlySourceLoader(importlib.machinery.SourceFileLoader):
    def set_data(self, path, data, **kwargs):
        pass  # Auditing must not write bytecode into the plugin worktree.


class _LiveCoreFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(__name__ + '.'):
            spec = importlib.machinery.PathFinder.find_spec(fullname, __path__)
            if spec is None:
                raise ModuleNotFoundError(f'Current MangaAnkā core module missing: {fullname}')
            if spec.origin and spec.origin.endswith('.py'):
                spec.loader = _ReadOnlySourceLoader(fullname, spec.origin)
            return spec
        return None


sys.meta_path.insert(0, _LiveCoreFinder())
