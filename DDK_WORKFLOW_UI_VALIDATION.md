# Workflow UI implementation and validation

Task-local report, October 6, 2026. The current local worktrees were the baseline. This pass adds the production Workflow frontend and brings its layout closer to the supplied dashboard mockup.

## Interface and action architecture

Workflow is the seventh page and the normal landing page after a successful database open or remembered-session restoration. Navigation is Workflow, Catalog, Audit, Problems, Curate, History, Details. The existing chooser and validated session restoration remain in use. Startup geometry is bounded to the actual available screen; saved maximized state remains supported.

The page has an active-set/database header, existing New Batch/Paste Titles/Run Working Set actions, five summary cards, a numbered six-step guide, search/state/health filters with Clear, a dense six-column membership table, a scrollable selected-title inspector, and a stacked action panel. Export and Paste Fix Commands use blue emphasis. The guide explains the human loop; it does not claim that external review happened or persist fictional stages.

The summary cards show total exact memberships, persisted ACCEPTED membership count, actual acceptance-eligible candidate count, persisted REVIEW count, and persisted ERROR count. Additional PENDING/QUEUED/AUDITING/READY/REJECTED/DUPLICATE/unlinked counts remain discoverable. Eligibility is `Acceptance.bulk_preview()['candidates']`, never an alias for READY. Table health is a display aggregation of persisted health dimensions; it does not authorize acceptance. Chapters/volumes retain the existing final-publication display, including uncompiled units.

Next Action precedence is running/AUDITING; QUEUED; protected Working Set; REJECTED or accepted item requiring re-audit/reopen; ERROR; duplicate; PENDING or evaluator requiring re-audit; existing REVIEW problem policy; eligible nonaccepted item; accepted/current; unlinked/inspect evidence. REVIEW problem priority is blocked identity, code review, research, curation, auto-resolvable, acquisition-only, unknown. These are presentation labels over existing decisions, not a second lifecycle policy.

`qt_app/orchestration.py` captures immutable, ephemeral action arguments: database UUID/path, scope, set UUID, and exact item UUID/work UUID/edition/language/pin/revision. It resolves them again against the authoritative Session before execution and after human confirmation where applicable. Changed DB, set, membership, identity or pin is rejected. Catalog remains the default source for its own actions; Workflow explicitly supplies its selection. No persistent alternate selection model, policy engine, parser, writer or queue was added.

Selected-title inspection uses exact pinned context. It shows edition/language, pinned audit/revision, four stored health dimensions, meaningful problem categories/next actions and evaluator blockers. Complete context/provenance is selectable under Technical details. Unlinked items show their intake observations. Details, Curate and Problems target the selected exact membership; Problems has an explicit Show All Titles in Scope escape from the title filter.

## Export, commands and acceptance

Workflow saves the existing `mangaanka-ddk-working-set-review-v1` packet as JSON. Pinned review is the default; Current global is explicit. Export never advances a pin. The database/scope is captured before the file dialog, and before/after content fingerprints reject a packet assembled across changing evidence.

Local QSettings receipts are keyed by database UUID, set UUID and pinned/current mode. They contain only version, SHA-256 fingerprint, local output path and UTC timestamp. A short consistent read snapshot fingerprints set/membership state, linked work identity, pin and latest audit revisions/health, curation state/evidence, guard dependencies, dispositions, acceptance records and intake observations. No catalog schema, packet content, acceptance decision or external-review completion is stored in preferences. No receipt or malformed/deleted context is Unknown. A changed snapshot is stale. Only a successful file save records a receipt; cancellation, failure and clipboard copy do not. Freshness describes the locally remembered exported snapshot, not the continued existence or review of the external file.

Paste Fix Commands opens the existing Curate/controller for the exact selected work, then returns to Workflow with the shared CommandDrawer expanded. Its context preserves exact title/edition/language/item UUID/pinned audit and curation revision. Guarded edits still require Preview followed by explicit Apply. Preview does not write. Stale guards remain rejected. Ordinary console commands retain their existing semantics. Selection changes cancel incompatible pending previews; refresh alone preserves a still-valid preview.

Apply uses the existing automatic/deferred re-audit. Workflow observes that worker, persisted membership state and existing deferred queue; it never creates a second queue or duplicate rerun. Accept Eligible Titles uses the existing bulk preview and explicit human confirmation. Unresolved/ineligible items remain unresolved. Accepted stale items retain existing reopen/re-audit rules. Completion uses the existing guard requiring terminal memberships. Intake defaults remain standard/en/volume with exact duplicate/count results, and New Batch uses existing creation/activation.

## Responsive layout and keyboard

At narrower widths the inspector collapses and action buttons move above the table. Inspector remains available through its toggle. Cards can wrap; optional guide/extra state summary fold at small widths. Expanding CommandDrawer compacts the surrounding presentation rather than expanding the window. Specialist inspectors and long technical content retain visible vertical scrollbars; wide diagnostic surfaces keep horizontal scrollbars. The core Workflow table and primary actions require no horizontal scrolling in the tested sizes. Selected rows and read-only controls remain readable.

Native Qt keyboard/focus behavior is preserved: table selection and Enter open exact Details, the existing Ctrl+Enter preview shortcut remains, and controls have accessible names/tooltips. The shared drawer remains collapsible. Screen-scale simulation does not establish behavior on every physical monitor configuration.

## Exact source/test files for this pass

Added:

- `C:\MangaAnka DDK\qt_app\orchestration.py`
- `C:\MangaAnka DDK\qt_app\workflow_presentation.py`
- `C:\MangaAnka DDK\qt_app\export_receipts.py`
- `C:\MangaAnka DDK\qt_app\pages\workflow.py`
- `C:\MangaAnka DDK\qt_app\widgets\workflow.py`
- `C:\MangaAnka DDK\tests\test_workflow.py`
- `C:\MangaAnka DDK\tests\smoke_packaged_workflow.py`
- `C:\MangaAnka DDK\tests\prepare_workflow_native.py`
- `C:\MangaAnka DDK\DDK_WORKFLOW_UI_VALIDATION.md`

Changed:

- `C:\MangaAnka DDK\qt_app\main_window.py`
- `C:\MangaAnka DDK\qt_app\icons.py`
- `C:\MangaAnka DDK\qt_app\pages\curate.py`
- `C:\MangaAnka DDK\qt_app\pages\problems.py`
- `C:\MangaAnka DDK\qt_app\widgets\command_drawer.py`
- `C:\MangaAnka DDK\tests\test_qt_frontend.py`
- `C:\MangaAnka DDK\tests\test_qt_session_restore.py`
- `C:\MangaAnka DDK\tests\test_qt_promotion.py`
- `C:\MangaAnka DDK\tests\ui_qt_smoke.py`

Task-local baselines/logs/build intermediates/disposable catalogs are under `C:\MangaAnka DDK\build\workflow*`. Rendered UI evidence is under `C:\MangaAnka DDK\qt-review\workflow`. The final primary EXE is replaced after passing source checks. No launcher, PyInstaller spec/hook, backend or shared-plugin product file was changed.

## Validation

| Check | Result |
| --- | --- |
| New focused Workflow contracts | **67 passed**, 45.838 seconds. |
| Focused session restoration | **21 passed**, 4.316 seconds. |
| Focused promotion/layout compatibility | **13 passed**, 5.685 seconds. |
| Final full DDK suite | **474 passed**, 318.129 seconds, including all Qt/frontend/Force/lifecycle/canonical-special regressions. |
| Protected shared-core suite | **328 passed**: 316 across fifteen targeted modules plus 12 unified-volume tests. No full plugin suite run. |
| Qt window/scale smokes | **9 passed**: 1120×720, 1440×900, 1920×1080 at 1.0, 1.25 and 1.5. All seven pages, useful collapsed/expanded table space, reachable actions and no core-table horizontal scrolling. |
| Static checks | Compile checks passed; 117 existing baseline hashes checked with only the five authorized existing Qt source changes. |
| Frozen-module and native checks | **156 passed**: 89 protected packaged tests (38.627s) and 67 Workflow tests (54.008s). All **21 embedded modules** match final compiled source; no database payload; shared core remains live. Native checks below passed. |

Logs: `build/workflow-tests-final.log`, `workflow-session-tests.log`, `workflow-promotion-tests.log`, `workflow-full-ddk.log`, `workflow-protected-core.log`, `workflow-protected-volume.log`, and `workflow-smoke-final-{1,1.25,1.5}.log`.

The 67 new Workflow tests include exact targeting despite stale Catalog selection, database/set/pin switches, unlinked/duplicate/error/protected memberships, eligibility versus READY, receipt cancellation/failure/restart/mode/scope and audit/curation/evidence/disposition/acceptance/membership changes, guarded Preview-no-write/stale rejection, refresh/selection behavior, automatic/deferred rerun without duplication, partial human acceptance, completion/new batch, inspector/filter/keyboard/scrollbar checks.

The deterministic full operator-cycle test performs New Batch, actual intake dialog with an exact duplicate, real existing audit orchestration, pinned JSON export, exact guarded fix Preview/Apply, automatic re-audit, stale receipt/fresh export, explicit acceptance of only eligible titles, unresolved REVIEW retention, explicit terminal resolution/completion, then a new empty batch. No network or production database is used. The packaged runner repeats this cycle using the EXE's embedded Qt/DDK modules; the shared core remains the live runtime dependency.

Existing frontend assertions were adjusted for seven pages/Workflow landing, explicit specialist-page selection and the additional legitimate summary evaluator refresh. Safety assertions were retained. The first full suite had 474 tests and one old promotion assertion requiring a local scope dropdown on every page; Workflow intentionally uses the visible global Working Set selector. That assertion was updated only for Workflow, and the 13 focused promotion tests passed. A receipt evidence test initially attached evidence without first curating its target chapter-volume assertion; the fixture was corrected to meet existing backend requirements. Narrow geometry initially left insufficient table height; the compact layout was repaired and all nine smokes rerun successfully. The first native EXE check exposed larger inspector spacing than the offscreen renders: only two health rows fit at 900px. Inspector form spacing was compacted and idle text folded. The full 474-test suite and all nine smokes were rerun, with an explicit fourth-health-row geometry check added for wide windows.

## Build and compatibility

Final EXE: `C:\MangaAnka DDK\dist\MangaAnka-Database-Development-Kit.exe`. Size: **52,531,423 bytes**. SHA-256: `e2c6150c3e90af052ff614f83f50df72e278aa5c6d9dc5e32f1d7db26561d0cd`.

Built successfully with Python 3.10.6 / PyInstaller 6.20.0 using the unchanged primary spec and `build/workflow-pyinstaller`. Installed Tcl/Tk access was used for the existing packaging guard. The EXE was rebuilt after the final native-spacing repair and the final full source tests; frozen-module comparisons then verified every latest Workflow fix. No running user instance was terminated. The task-owned smoke windows closed normally before replacement. Build log: `build/workflow-pyinstaller.log`; final embedded-code checks: `build/workflow-packaged-tests.log`.

Primary launcher: `C:\MangaAnka DDK\Launch_MangaAnka_DDK.bat`. Legacy Tk fallback: `C:\MangaAnka DDK\Launch_MangaAnka_DDK_Legacy_Tk.bat`, unchanged. Existing PyInstaller live-core exclusion, tkinter guard and DLL filtering are retained. No packaging/spec/version alteration was needed. Geist font assets are not present; the existing Segoe UI Variable/Segoe UI and Cascadia Mono/Consolas/system fallbacks remain. No fonts were downloaded.

## Native Windows checks

Using the Computer Use skill, the final Windows EXE passed:

- Normal primary-launcher startup with isolated `--ui-settings`, restoring the disposable Unicode/spaces catalog and exact Workflow Batch 003 without a chooser.
- Workflow landing, readable selected row, compact selected-title inspector with all four health rows visible at 1440×900, and reachable primary actions.
- Paste Fix Commands targeting the exact selected Fire Force fixture/item/pinned revision in the existing shared drawer. Drawer expansion/collapse kept the window size and useful table space; no native command Apply or acceptance was performed.
- A second instance on the same disposable database returned to the existing chooser with the writer-lock explanation. Cancel exited without bypassing it.
- Normal Close, then successful primary-launcher reopen of the same exact database/batch without a picker, demonstrating lock release.
- Missing remembered path returned to the chooser with its concise explanation; Cancel exited without creating a replacement DB or lock sidecar.
- Explicit creation of a fresh disposable TEST catalog opened empty Workflow, with zero cards and appropriately disabled set-scoped actions. Read-only verification confirmed schema 7, zero works and zero Working Sets.

The populated disposable catalog remained byte-for-byte unchanged. All final native smoke windows closed normally. `build/workflow-native-results.json` records observations and final file/hash checks. One Computer Use table-index action reported unavailable geometry; fresh screenshot-backed selection completed the check without changing application code or data. Automated work never used default production settings.

## Safety, deliberate mockup differences and limits

The protected production catalog was never opened or mutated. All development/validation catalogs and QSettings are disposable. Baseline hashes checked 117 existing protected files: only the five listed existing Qt modules changed; backend, schema/search/providers, publication/reference/canonical-special/freshness/normalization/artifact authority, writer transactions, acceptance/curation policy and shared-plugin source are unchanged. Schema remains 7, Grammar remains 3, DDK remains 0.3.0. No automatic acceptance, provider-shadow policy or title-specific production hack. No commit, push, tag, release, reset or clean.

The UI intentionally labels actual membership state and Eligible rather than making READY synonymous with acceptance. It keeps the Audit specialist page, explicit pin mode/receipt scope and exact technical diagnostics. The guide is guidance rather than fabricated persisted progress. Primary actions and layout follow the mockup, while a compact arrangement keeps small windows usable. No fictional health/severity/counts from the mockup are copied into the catalog. Provider/edition/reference decisions remain backend-owned.

Known limits: receipts are local to the settings file/machine and describe a successful past snapshot, not external-review completion; live provider/corpus audits were not performed; current publication/reference research issues are not repaired by a frontend change; shared-plugin worktree remains required at runtime. Native smoke exercises startup/window behavior; packaged deterministic tests exercise mutating operator workflows. Physical monitor DPI switching and a separate native legacy-Tk run were not repeated in this Qt-only pass.

Short human-operated checklist:

1. Launch normally, select the intended database/set once if needed, confirm Workflow and the exact database/set header, close and reopen.
2. In a small disposable batch, paste titles, inspect duplicate/count feedback, then Run Working Set. Verify summary counts and final-publication table data.
3. Select a REVIEW title, export pinned JSON, paste its exact guarded commands, Preview, inspect, then explicitly Apply. Confirm a single automatic/deferred re-audit and stale → fresh export receipt.
4. Explicitly accept only eligible titles; unresolved titles should remain REVIEW. Inspect exact Details/Problems/Curate links and protected-set guards.
5. Resize and expand/collapse CommandDrawer/Inspector. Confirm readable selection, useful table space and visible scrollbars; complete a set only when existing guards allow, then create the next batch.
