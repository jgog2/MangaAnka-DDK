# MangaAnkā Qt promotion and packaging validation

Date: 2026-10-04  
Application: MangaAnkā Database Development Kit v0.3.0  
Database schema: v7

This report records the completed Qt promotion pass. The Qt Widgets frontend is now the primary DDK interface. The existing Tk application remains available as a clearly labeled legacy/recovery frontend. No commit, push, tag, release, live-catalog access, schema migration, backend rewrite, search-core change, provider change, or plugin change was made.

## 1. Exact files changed

The authored existing files changed in this pass are:

- `MangaAnka-Database-Development-Kit.spec`
- `Build_MangaAnka_DDK_EXE.bat`
- `Update_MangaAnka_DDK_EXE.bat`
- `ddk_build.py`
- `requirements-qt.txt`
- `mangaanka_qt.py`
- `MangaAnka_Database_Development_Kit_README.md`
- `qt_app/__init__.py`
- `qt_app/app.py`
- `qt_app/main_window.py`
- `qt_app/session.py`
- `qt_app/theme.py`
- `qt_app/pages/base.py`
- `qt_app/pages/catalog.py`
- `qt_app/pages/details.py`
- `qt_app/pages/history.py`
- `qt_app/pages/problems.py`
- `qt_app/widgets/common.py`
- `tests/test_qt_frontend.py`

## 2. Exact files added

- `Launch_MangaAnka_DDK.bat`
- `Launch_MangaAnka_DDK_Legacy_Tk.bat`
- `MangaAnka-DDK-Legacy-Tk.spec`
- `requirements-build.txt`
- `tests/test_qt_promotion.py`
- `tests/prepare_packaged_qt_smoke.py`
- `DDK_QT_PROMOTION_VALIDATION.md` (this report)

Generated validation artifacts include the primary EXE, `qt-build.log`, and the promotion review screenshots under `qt-review/promotion/`. Test databases were temporary disposable files and are not runtime resources.

## 3. Primary Qt launcher

`Launch_MangaAnka_DDK.bat` changes to the DDK directory, starts `dist\\MangaAnka-Database-Development-Kit.exe` when it exists, and falls back to `Launch_MangaAnka_DDK_Qt.bat` for source development. Arguments are passed through unchanged, including `--database`, `--create`, `--role`, and `--ui-settings`. The EXE is launched asynchronously so the batch window does not remain as console clutter.

The standard batch was also invoked against the disposable `created-by-exe.db`; it spawned the final EXE successfully. The earlier packaged UI session directly opened that same final artifact, created a fresh disposable database, and verified its empty Catalog state, schema-v7 initialization, settings persistence, and writer lock. A resumed desktop reattach was not possible after the escalation reviewer reported the account usage limit, so no additional UI assertion was made from the hidden non-escalated launcher process.

## 4. Legacy Tk launcher

`Launch_MangaAnka_DDK_Legacy_Tk.bat` is explicitly labeled Legacy / Recovery, uses the local Python environment when available, and falls back to `py mangaanka_database_development_kit.py`. The Tk source entry point and behavior remain intact. A separate legacy spec is provided for optional packaging; a second legacy EXE was not required for this pass.

## 5. PyInstaller and build changes

The primary spec uses `mangaanka_qt.py`, one-file/windowed packaging, the existing live-plugin-path architecture, and PySide6 hooks for only the Qt modules used by the application. It includes the Windows platform plugins and required Qt runtime libraries, excludes unrelated Qt bindings and unused QML/Quick/WebEngine/Python-extension payloads, keeps the Tk runtime required by shared backend imports, and filters frozen `mangaanka_search_core.*` submodules so the read-only local loader remains authoritative.

The build scripts use only `.venv-qt\\Scripts\\python.exe`, fail with setup instructions when the local build environment is missing, and never install globally. The Windows runtime dependency helper removes incompatible Poppler ICU DLL entries so the Qt-supplied/system ICU is not shadowed. The final frozen archive contains Qt Widgets, the Qt Windows platform plugin, Tk support, and the current Qt application modules; it contains no ICU DLL collision and no test database or screenshot payload.

## 6. Final EXE

Path: `C:\MangaAnka DDK\dist\MangaAnka-Database-Development-Kit.exe`  
Size: 48,668,878 bytes  
SHA-256: `B748B81A972D1A7D3415182C3E06127D3AB7BDE9B1A90C6B970C0AA6DBEF8900`

Archive inspection confirmed `qt_app.main_window`, `qt_app.pages.catalog`, `qt_app.theme`, the namespace `mangaanka_search_core` loader, `tkinter`, and `PySide6/plugins/platforms/qwindows.dll` are present in the final artifact.

## 7. Resources and fonts

The SVG icon set and theme are Python resources and are included by module analysis. The asset path `qt_app/assets/fonts` is supported in source and frozen execution. No Geist Sans or Geist Mono files were present locally, so no fonts were downloaded or distributed. The runtime fallback remains installed Geist if available, then Segoe UI Variable/Segoe UI, then an installed monospace font or Qt/system fallback. No font licensing issue was introduced.

## 8. Minor UX fixes

- Status feedback is page-contextual. Curate/command guidance stays on Curate; Audit and Catalog run feedback stays on those pages; unrelated navigation clears stale guidance while generic errors still use the warning dialog/global path.
- Sidebar buttons retain the same six pages, icons, counts, and click targets but use flatter inactive rows, a restrained hover/active treatment, and a narrow accent edge.
- Catalog keeps `Run Working Set` as the sole primary action. `Accept All Safe`, `Accept Selected`, `Open Review Items`, and `Retry Errors` remain visible as quieter actions. Rare actions remain behind `More` or `Intake`.
- The empty Catalog inspector is centered, low-emphasis, and width-stable. Catalog refresh now explicitly clears stale selection after model resets, including switching to an empty Working Set.
- Problems filters visibly identify Class, Action, and Disposition; History identifies Event Type. Existing filter values and backend semantics remain unchanged.
- Scope selectors remain visible beside the page heading and remain independently controlled per page.
- Details keeps all nine sections, uses compact tabs with a clearer active treatment and scroll buttons, and retains its long-content scrolling.
- The command drawer remains available and its grammar, Preview/Apply/Cancel, Undo/Redo, history, shortcuts, selection integration, and transaction behavior are unchanged.

## 9. Behavior deliberately unchanged

The command grammar and controller transaction semantics are unchanged. The validated schema-v7 backend, lifecycle, acceptance rules, Working Sets, pinning, curation, publication resolution, search/audit/provider behavior, canonical identity, problem disposition, writer lock, `mangaanka_search_core`, and the real MangaAnkā Calibre plugin were not modified. No database migration was added. The existing user catalog was not opened, copied, migrated, or written.

## 10. Focused tests

`tests/test_qt_promotion.py`: 13 tests passed in 3.751 seconds after the final launcher adjustment. Coverage includes contextual feedback, database-switch clearing, sidebar state, action hierarchy, empty-inspector behavior, model-reset clearing, filter labels, scope placement, Details tabs, resources/fonts/icons, launchers/specs, and ICU filtering. The pre-existing 46 Qt tests remain present.

The supported invocation is `python -m unittest discover -s tests`; running the file as an imported package module is not supported because the test suite intentionally uses discovery-directory imports.

## 11. Full suite

The complete local suite passed: **238 tests**, comprising 179 existing backend/Tk tests, 46 existing Qt tests, and 13 promotion tests. No repository-wide MangaAnkā plugin suite was run, per scope.

## 12. Static and dependency checks

The final checks passed for AST parsing and bytecode compilation across 64 Python files, spec parsing, import smoke tests, changed-file conflict/trailing-whitespace scans, frozen archive inspection, and `pip check`. Qt resources, icons, the optional font path, platform plugins, and the local plugin-path loader were checked in source and frozen contexts.

## 13. Packaged EXE smoke

The actual packaged Qt EXE was exercised against only the disposable catalog prepared by `tests/prepare_packaged_qt_smoke.py`. It launched without a console, opened the fixture catalog, ran the ready offline Working Set without provider/network requests, navigated Catalog, Audit, Problems, Curate, History, and Details, inspected Publication Map, changed scopes, created a Working Set through Intake, expanded the command drawer, executed a real Preview/Apply curation command, verified the resulting title, closed and reopened, and confirmed QSettings persistence. The fresh `--create` path created a new schema-v7 disposable database and the empty Catalog state. SQLite integrity, writer-lock blocking, and lock release after close were verified. History and Details were reopened from the persisted UI settings.

The smoke deliberately did not inject fake success into the EXE and did not perform live provider/network auditing. Offline deterministic source tests cover the auditor and worker pipeline; packaged smoke covers the frozen UI and shared backend integration boundary.

## 14. Window and DPI validation

Source Qt smoke passed all nine combinations of 1120x720, 1440x900, and 1920x1080 at `QT_SCALE_FACTOR` 1.0, 1.25, and 1.5. Catalog, Curate, Problems, and Details review screenshots were inspected at 1440x900 and 1920x1080. Controls fit the minimum width, scopes remain visible, Details tabs retain scroll buttons, dark contrast is readable, and long surfaces retain visible scrollbars. The packaged EXE was visually checked on the current approximately 1440x900 desktop. Physical multi-monitor/per-monitor DPI combinations on other Windows machines remain manual follow-up.

## 15. Tk fallback validation

The existing offline Tk UI smoke and Working Set smoke passed against temporary databases, including selection/commands/undo-redo, long Details scrolling, dark scrollbars, intake/dedupe/scopes/copy/acceptance/switching, and minimum-width toolbar behavior. The legacy source entry point remains callable. The optional legacy EXE was not built because the task only required the primary Qt artifact.

## 16. Known limitations

- The packaged app still requires the current local MangaAnkā plugin worktree or an explicit `MANGAANKA_PLUGIN_PATH`; provider/search code is intentionally not frozen as a divergent copy.
- No Geist font files were available locally, so the documented fallback is active.
- No live catalog or live provider/network audit was run automatically.
- The resumed standard-launcher process check could not be reattached to the desktop after escalation usage was exhausted; the batch did spawn the final EXE, and direct final-EXE UI launch/reopen was already completed in the packaged smoke above.
- Cross-machine Windows behavior and physical 125%/150% per-monitor DPI still deserve a short manual check.

## 17. Production-style launch command

From `C:\MangaAnka DDK`, double-click `Launch_MangaAnka_DDK.bat`, or run:

```text
Launch_MangaAnka_DDK.bat --database "C:\path\to\catalog.db" --ui-settings "C:\path\to\ui.ini"
```

For source development, `Launch_MangaAnka_DDK_Qt.bat` remains available. For recovery, use `Launch_MangaAnka_DDK_Legacy_Tk.bat`.

## 18. Short manual live-database checklist

1. Close other DDK writers and make a backup according to the existing catalog policy. Launch the Qt DDK and explicitly choose the real catalog; it is never opened implicitly.
2. Select the intended Working Set, confirm the visible scope, and run one small controlled set. Watch Running/progress/current-item feedback and confirm the resulting Catalog and Publication Map.
3. Open one review item, verify Problems → Curate, use Preview before Apply, and confirm the expected acceptance/curation revision.
4. Close and reopen the Qt DDK, verify the selected database/settings and writer-lock behavior, then optionally launch the legacy Tk recovery interface only after the Qt writer is closed.
