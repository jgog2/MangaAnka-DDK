# MangaAnkā DDK Qt frontend validation

Source implementation and offline validation completed 2026-10-04. DDK remains **v0.3.0**, schema **7**. Qt coexists with Tk. No EXE build, updater change, commit, push, tag, release, plugin edit or live-provider audit occurred.

The named live database at `C:\Users\Jerry\Documents\MangaAnka-Database-Development-Kit\mangaanka_catalog.db` was not opened, instantiated, migrated, copied or written. Every validation database and QSettings file was disposable. The development Qt session rejects that exact path before validation, locking or DB construction.

1. **Exact Python source added.** Root: `C:\MangaAnka DDK\mangaanka_qt.py`, `C:\MangaAnka DDK\ddk_command_controller.py`. Qt package files below are all under `C:\MangaAnka DDK\qt_app\`:

   ```text
   __init__.py
   app.py
   commands.py
   dialogs.py
   icons.py
   main_window.py
   session.py
   theme.py
   workers.py
   models/__init__.py
   models/publication.py
   models/table.py
   pages/__init__.py
   pages/audit.py
   pages/base.py
   pages/catalog.py
   pages/curate.py
   pages/details.py
   pages/history.py
   pages/problems.py
   widgets/__init__.py
   widgets/command_drawer.py
   widgets/common.py
   widgets/publication_map.py
   ```

   Tests added: `C:\MangaAnka DDK\tests\test_qt_frontend.py` and `C:\MangaAnka DDK\tests\ui_qt_smoke.py`. Other additions: `C:\MangaAnka DDK\requirements-qt.txt`, `C:\MangaAnka DDK\Launch_MangaAnka_DDK_Qt.bat`, this report, and eight screenshots in `C:\MangaAnka DDK\qt-review\`. The optional local dependency environment is `C:\MangaAnka DDK\.venv-qt\`.

2. **Existing files modified.** Only `C:\MangaAnka DDK\ddk_editor.py` and `C:\MangaAnka DDK\MangaAnka_Database_Development_Kit_README.md`. Existing backend tests, Tk launcher, build/update scripts and PyInstaller spec were not modified.

3. **Dependencies.** `requirements-qt.txt` pins PySide6 **6.10.2**. The local environment also installed its matching PySide6_Addons, PySide6_Essentials and shiboken6 **6.10.2** dependencies. `pip check` reports no broken requirements. No global Python environment was changed and no fonts or icon packages were downloaded. No silent installation occurs in either launcher.

4. **Qt entry point.** `mangaanka_qt.py` delegates to `qt_app.app.main()`. Without arguments, it shows a database chooser. `--database`, `--create` and `--role` provide explicit startup context. New Database refuses existing paths; existing files use the existing read-only validator and OS writer lock before DB activation. The current backend's supported migrations remain available for explicitly selected disposable/copied catalogs; no migration code was added.

5. **Shared extraction.** Six existing Tk methods moved into `CommandLogic`: `compile_batch`, `evidence_changes`, `command_changes`, `inspect`, `validation_text`, and `ids`. Their implementation is retained; the selection call now uses a host-supplied `command_selection()` seam. Tk's seam returns its original Treeview selection. Qt uses the same compiler/inspection methods. Qt adds presentation orchestration over existing Catalog preview/apply/reverse operations, with exact scope, database, audit and revision guards. A regression confirms both frontends reference the same shared methods.

6. **Backend unchanged.** `mangaanka_database_development_kit.py`, all existing database/lifecycle/acceptance/catalog/publication/review/export/maintenance/workspace/lock modules, `ddk_commands.py`, `mangaanka_search_core`, and `C:\MangaNana-Dev\MangaNana-calibre` were not edited. There is no new schema, acceptance policy, canonical identity rule, provider logic, publication algorithm or command grammar. Qt calls `DB`, `WorkingSets`, `Acceptance`, `Catalog`, review/export helpers, maintenance and the existing `SearchAuditor` pipeline.

7. **Window architecture.** QMainWindow with compact context controls, six-button sidebar, QStackedWidget pages, page-specific QSplitters/inspectors, persistent command drawer and status bar. Minimum logical size 1120×720; default 1440×900. No QML, HTML or third-party theme engine.

8. **Theme/fonts.** Central tokens use the requested soft dark surfaces, light text, muted metadata, restrained orange action/focus treatment and status tints. Table selection remains subdued. QFontDatabase chooses installed Geist Sans/Mono, then Windows Segoe UI Variable/Segoe UI and a Windows monospace font, then Qt system fallbacks. Later local assets can be placed in `qt_app/assets/fonts`. Windows Qt offscreen does not enumerate system fonts; when enumeration is empty, the theme loads installed Segoe UI/Consolas files directly, without copying/downloading fonts. Screenshots render readable text.

9. **Sidebar.** Catalog, Audit, Problems, Curate, History and Details stay visible, with selected-page treatment and Problems count. Icons are small original SVG paths rendered through Qt; no external assets. Options contains actual refresh/layout/folder/about actions.

10. **Context controls.** Database menu: switch, new, open folder, role/schema/work/audit counts and secondary Copy UUID. Working Set menu: switch/new/status/reopen. Impossible/protected transitions are disabled with explanations; COMPLETE is disabled until its existing terminal-item gate is satisfied. Busy runs prevent database/set context switches. Backend guards still recheck every mutation.

11. **Catalog.** Main working workspace has acceptance/readiness/review/error/duplicate summaries, title search, status/edition/language/provider filters, Run Working Set, Accept All Safe, selected approval, Intake and More. Item status, catalog lifecycle and acceptance remain separate. Global status filtering uses catalog lifecycle; set status filtering uses membership state. Copy, exports, reconciliation, reject/remove/reopen and guarded permanent deletion remain accessible.

12. **Advanced Columns.** Eight default columns: Title, Item, Catalog, Publication, mapped/total Chapters, Volumes, Acceptance, Provider. Columns exposes canonical/health/artifact/unclassified/curation/audit date/revision/freshness/pin/latest/UUID data. Default desktop rendering has no horizontal sprawl; advanced columns retain horizontal scrolling. QSettings stores visibility and header width/order.

13. **Inspectors.** Shared resizable/collapsible, scrollable shell presents headings and key/value groups, relevant actions and an intentional Technical Details expansion. Catalog shows identity, health, publication, acquisition, curation, snapshot/latest/pin state and approval; linked execution failures appear as a separate latest attempt. Catalog and Audit also reuse the Publication Map for compact volume summaries. Empty selections clear stale inspector context.

14. **Audit execution.** Run immediately changes to Running… and disables duplicate starts before any auditor/provider construction. Construction and the existing sequential audit loop run in QThread. A thread-safe queue relay emits queued Qt events for item/stage/progress/activity/summary. Widgets are only updated on the GUI thread. Current index/title/stage, result, audit ID and available duration are shown. Worker initialization and execution failures return to idle with readable messages and expandable technical data. Cancellation is cooperative; it retains prior successful pins. Deferred curation uses a window-owned timer, exact membership IDs and the backend run-candidate filter; close/database switch cancels pending UI timers.

15. **Problems.** Research/Data/Code/Unknown/Error summaries, class/action/disposition/title filters, grounded disposition/reopen, diagnostic copy/view, detailed CSV, review-packet export, Code Review Candidates, evidence access and exact Curate navigation. The existing policy classifies audit holes. The existing `WorkingSets.audit_errors()` separately supplies current intake execution failures, including linked failures with retained pins. Those observations are diagnostic records and cannot receive invented audit-hole dispositions.

16. **Publication Map.** One QAbstractItemModel/QTreeView component groups existing Catalog rows by effective volume. It preserves identifiers and backend row order, including fractions and semantic/provider identifiers. It shows title or muted Untitled, curated/verification/conflict/unmapped state, source and volume range/count summaries. Provider-only records have their own group and are labelled records, not canonical chapters. Group status MAPPED means all represented rows map; it does not invent a claim of reference completeness. Empty explicit volumes remain visible. The selected inspector retains exact automatic/curated/effective values and evidence.

17. **Curate.** Shared Publication Map and secondary QTableView, exact title/scope selector, chapter/work/volume editing, evidence, verification, reviewed structure sharing, validation/save/re-audit, curated patch export and previewed Undo/Redo. It explicitly edits latest shared catalog state. Protected/inactive/terminal membership curation is guarded. Apply/Undo/Redo through the active set queues only that membership; explicit global edits preserve all set pins. An unchanged preview survives unrelated refreshes; changed work/scope/audit/revision cancels it. Successful writes refresh the map. The 275-chapter/23-volume fixture shows chapter 275's title and VERIFIED curated volume mapping.

18. **History.** Scoped UTC event list/timeline with All/Audit/Curation/Acceptance/Working Set/Maintenance filters. Selection shows context, revisions and available before/after values, with raw event data intentionally expandable/copyable. Curation revert is previewed through the same reverse transaction; audit/workflow history is read-only.

19. **Details.** Overview, Identity, Publication, Acquisition, References, Curation, Acceptance, Working Sets and Raw Data tabs. Snapshot publication uses the same map. Provider inventory preserves native volumes/standalone chapters/qualification and full raw records. References retain manifest/reference/coverage/count provenance. Approval evaluation stays central. Raw data includes complete audit payload, publication, work, memberships and latest intake observations.

20. **Raw-data access.** Monospace selectable/copyable text with visible vertical and available horizontal scrolling. Raw Data is explicit; Technical Details is expandable. Details search finds raw text. Copy JSON and selected full diagnostics retain underlying diagnostic payloads without occupying the primary workspace.

21. **Command drawer.** Persistent collapsed entry bar; expandable multiline console, authoritative help, preview summary, Apply/Cancel, Undo/Redo, selected count, in-session history and readable/highlighted errors. Selection from map/table feeds the shared compiler. Any invalid batch leaves no pending write; all valid batch changes reach one Catalog transaction. No second curation engine exists.

22. **Grammar.** None changed. `ddk_commands.HELP`, parser, exact-title resolution, ranges, guards, clear/reset distinctions, verification levels, evidence/identity/ID/expected-total commands and inspection remain authoritative. No fuzzy interpretation or new `show publication` syntax. Optional autocomplete and line-number gutters were not implemented.

23. **Keyboard/accessibility.** Ctrl+F current search; Ctrl+Enter/Ctrl+Return command preview; Escape drawer collapse and normal Qt dialog/menu behavior; Up/Down command history; Enter safely opens Catalog Details or Problem Curate. No destructive shortcuts. Buttons, controls and maps have accessible names/tooltips, focus borders and textual statuses. Standard Qt Ctrl/Shift row selection and scrolling remain available.

24. **QSettings.** UI geometry/maximized state, last page, splitters/inspector visibility, table column widths/order, advanced visibility and drawer layout/expanded state only. Catalog, active set/workflow, pins, audit, curation and approval remain in the existing database. Tests use temporary INI files. Command history is in-session only.

25. **Tk → Qt feature locations.** Existing entry point remains Tk; no retirement occurred.

   | Existing function | Qt location |
   |---|---|
   | Switch/New Database/Open Folder/metadata | Top Database selector |
   | Switch/New Set/status/complete/archive/reopen | Top Working Set selector |
   | Paste/import title intake/context | Catalog → Intake; Load Title File |
   | Run/retry/progress/cancel | Catalog/Audit primary controls and Catalog More |
   | Exact selected/bulk approval | Catalog primary actions |
   | Global reconciliation/revocation | Catalog More → Re-evaluate Acceptance |
   | Reopen/reject/remove selected intake | Catalog More |
   | Selected title/UUID/summary/context/full diagnostic/CSV copy | Catalog More |
   | Set titles/context/CSV/pinned-current exports/review packet | Catalog More |
   | Catalog CSV/refresh | Catalog More; Options → Refresh |
   | Permanent maintenance preview/typed DELETE/fresh backup | Catalog More → Catalog Maintenance |
   | Problem disposition/reopen/evidence/diagnostic/export | Problems toolbar/inspector/More |
   | Detailed issue CSV and code-review candidates | Problems More |
   | Chapter/volume/work edits, evidence/verification | Curate toolbar/More and command drawer |
   | Aliases/IDs/expected totals/chapter-volume creation/reset | Existing command grammar; identity/volume forms where applicable |
   | Structure sharing/validation/save/global or item audit/patch | Curate More |
   | Persistent Undo/Redo and history revert | Command drawer; History Preview Revert |
   | Scoped events/before-after/raw history | History |
   | Search identity/provider/reference/publication/curation/approval diagnostics | Details sections and Raw Data |

26. **New focused tests.** **46 offline Qt tests pass**, covering all 30 requested categories plus real-auditor post-curation/Undo/Redo pin advancement with deterministic provider mocks, busy deferral, initialization failure, linked execution failures, stale preview cancellation, CSV/patch exports, disposition reopening and destructive backup/detachment. The tests import the exact existing backend fixtures, never the live catalog. If PySide6 is unavailable in another Python environment, this optional module explicitly skips; the local Qt environment runs every test.

27. **Complete suite.** Local environment command `.\.venv-qt\Scripts\python.exe -m unittest discover -s tests -q` passes **225 tests: all 179 existing tests plus 46 Qt tests**. No existing tests were rewritten, removed or skipped in that run. The plugin repository suite was not run.

28. **UI smokes.** Disposable Qt smoke passes all six pages at 1120×720, 1440×900 and 1920×1080, with scale factors **1.0, 1.25 and 1.5** checked against Qt's device-pixel ratio. All five existing offline Tk scripts pass: `ui_smoke.py`, `ui_working_set_smoke.py`, `ui_working_set_audit_smoke.py`, `ui_catalog_maintenance_smoke.py`, `ui_lifecycle_v7_smoke.py`. Tk smoke access to installed Tcl/Tk was approved; databases remained temporary. Eight readable Qt review screenshots were generated:

   | Page | 1440×900 | 1920×1080 |
   |---|---|---|
   | Catalog | [Preview](<C:/MangaAnka DDK/qt-review/catalog-1440x900.png>) | [Preview](<C:/MangaAnka DDK/qt-review/catalog-1920x1080.png>) |
   | Problems | [Preview](<C:/MangaAnka DDK/qt-review/problems-1440x900.png>) | [Preview](<C:/MangaAnka DDK/qt-review/problems-1920x1080.png>) |
   | Curate | [Preview](<C:/MangaAnka DDK/qt-review/curate-1440x900.png>) | [Preview](<C:/MangaAnka DDK/qt-review/curate-1920x1080.png>) |
   | Details | [Preview](<C:/MangaAnka DDK/qt-review/details-1440x900.png>) | [Preview](<C:/MangaAnka DDK/qt-review/details-1920x1080.png>) |

29. **Static checks.** AST parsing and bytecode compilation pass for **62 DDK/Qt/test Python files**. Qt/Tk import smoke passes for seven entry/adapter modules. All **29 edited/new Python source files** pass trailing-whitespace/conflict-marker scanning. `pip check` passes. DDK has no Git checkout, so a DDK `git diff --check` is unavailable; no Git state was reset or cleaned.

30. **Known limitations.** This is a source frontend; the existing EXE still contains Tk and its previous packaged source. The development launcher deliberately excludes the named live catalog. Live providers/corpus reruns and real catalog migrations were not exercised. Native on-screen Windows/DPI/accessibility verification remains a manual check; automated scaling uses Qt offscreen logical scaling. Cancellation waits for existing provider requests to finish. Historical audits do not have persisted duration, so those rows show —; new in-session activity has measured duration. Large-catalog page-query latency is not benchmarked; record models avoid per-cell widgets but read-only refresh queries still run on the GUI thread. Publication group MAPPED describes represented rows, not independent completeness validation. Command autocomplete/line-number gutters are optional follow-ups. No Qt EXE packaging is configured in this pass.

31. **Launch.** In PowerShell:

   ```powershell
   cd 'C:\MangaAnka DDK'
   .\.venv-qt\Scripts\python.exe mangaanka_qt.py
   ```

   Or run `Launch_MangaAnka_DDK_Qt.bat`. For initial scratch creation: `.\.venv-qt\Scripts\python.exe mangaanka_qt.py --database '.\qt-scratch.db' --create --role SCRATCH`; the path must not already exist. Do not pass `--create` on subsequent launches.

32. **Small manual checklist.** Use a disposable catalog or separately prepared copy, not the named live catalog. Create/switch a set and test visible scopes on all six pages. Inspect Catalog selection, Columns, splitters and saved layout at 1120/1440/1920 and native Windows 125%/150%. Open a problem in Curate and verify exact chapter/title/automatic-curated-effective/evidence. Preview one real correction, Cancel it, then Preview/Apply and check immediate audit feedback and the intended pin; test Undo/Redo. Check reconciliation, History raw events and Details provider/reference/raw panes. Open a permanent-delete preview and cancel it; if validating actual deletion, use only a disposable title and inspect the fresh backup/intake detachment. Finally launch Tk separately to confirm coexistence; the writer lock deliberately prevents both frontends writing the same file simultaneously.

Qt API references consulted: [Qt item models](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QAbstractItemModel.html) and [Qt threads](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html). Backend behavior was read from the local worktrees, not reconstructed from GitHub.
