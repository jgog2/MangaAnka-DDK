"""Collect dependencies of the live pure core for PyInstaller, without Calibre."""
import ast
import os
import sys
from pathlib import Path


def core_hidden_imports():
    root = Path(os.environ.get('MANGAANKA_PLUGIN_PATH', r'C:\MangaNana-Dev\MangaNana-calibre'))
    pending = ['source_registry', 'source_coordinator', 'mangadex_source', 'mangapill_source',
               'weebcentral_source', 'mangak_source', 'atsu_source', 'enrichment_sources',
               'enrichment_matching', 'search_ranking', 'search_resolution', 'canonical_identity',
               'version_info', 'reference_integration', 'publication_manifest', 'unified_volume',
               'mangadex_structure_reference', 'mangadex_artwork_reference']
    visited, dependencies = set(), set()
    while pending:
        name = pending.pop()
        if name in visited:
            continue
        visited.add(name)
        tree = ast.parse((root / (name + '.py')).read_text(encoding='utf-8-sig'))
        for node in ast.walk(tree):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else (
                [node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
            for imported in names:
                if (root / (imported + '.py')).is_file():
                    pending.append(imported)
                elif not imported.startswith(('calibre', 'qt', 'PyQt')):
                    dependencies.add(imported)
    return sorted(dependencies | {'mangaanka_search_core.' + n for n in visited})


def qt_assets(workspace):
    """Only intentional runtime font assets (and their licenses), if supplied.

    Theme tokens and original SVG icons live in imported Python modules.
    PyInstaller's PySide6 hooks collect the imported Widgets/Gui/Core/Svg
    modules and their platform plugins; never collect the whole Qt package.
    """
    fonts = Path(workspace) / 'qt_app' / 'assets' / 'fonts'
    return [(str(fonts), 'qt_app/assets/fonts')] if fonts.is_dir() else []


def qt_runtime_binaries(entries, platform=None):
    """Use Windows' ICU API, not an unrelated ICU found on the build PATH.

    Qt's Windows wheel imports unversioned ICU symbols. For example, Poppler's
    icuuc.dll exports suffixed symbols and cannot satisfy those imports. Let
    Windows resolve its own ICU DLLs; retain Qt/platform/MSVC binaries as-is.
    """
    if (platform or sys.platform) != 'win32':
        return list(entries)
    return [entry for entry in entries if not Path(entry[0]).name.lower().startswith('icu')]
