# Force Re-Audit All — implementation and validation

Date: October 7, 2026. DDK v0.3.0, schema 7, Grammar 3. Local worktrees were inspected before editing. Production SQLite was not opened or mutated; all automated database work used disposable fixtures. No shared-plugin file, version, schema, grammar, provider, search, normalization, publication, curation or acceptance policy was changed. No commit, push, tag or release.

## Existing path and implementation decision

The selected action resolves an exact scoped membership, calls `force_audit_candidate`, requires confirmation, commits `queue_force_audit`, and dispatches `AuditWorker` → `SearchAuditor.audit_many` → `audit_one`. The normal auditor marks AUDITING in a short transaction before resolution, invokes the actual search/provider/reference/publication/normalization machinery, then calls `persist_item_audit` to append the audit/problems and advance the exact pin atomically. Failure observations and superseded-curation retries use existing helpers. Connections are operation-scoped and created in the thread using them; no connection or write transaction is retained across provider work.

Batch forcing wraps this same single-item lifecycle. It does not add an alternate resolver, direct audit-insert shortcut, thread termination, database lock system or force-network/cache-purge policy.

## Workflow actions

Workflow → **Actions → Force Re-Audit All** uses the currently active Working Set, independent of visible filters or row selection. The existing selected action remains available.

The confirmation names the set and eligible title count, explicitly counts ACCEPTED items, warns about new immutable audits and STALE approvals, and defaults to Cancel. No item is queued before confirmation. The exact membership snapshot is revalidated after confirmation; changes require fresh confirmation. A new title added after execution begins is not silently added to the confirmed batch.

The batch includes REVIEW, READY, ACCEPTED, REJECTED, ERROR, PENDING, QUEUED and AUDITED memberships. Removed entries are excluded; DUPLICATE, AUDITING, invalid requested contexts and empty queries are ineligible/skipped. COMPLETE/ARCHIVED sets retain their existing protection and require explicit Reopen for Review first. No automatic reopen is performed.

The batch queues one exact `working_set_item_uuid` immediately before its turn. Each title uses its own requested language/edition/workflow through the normal auditor. Ordinary per-title provider or persistence failures retain the previous pin and do not prevent later titles from running. Existing curation dependency checks and bounded superseded retries remain active.

Busy/confirmation guards prevent overlapping GUI audit launches, including Run Working Set, Retry Errors and the console's existing audit path. Pending deferred re-audits block batch launch. The process-scoped WriterLock remains unchanged and prevents a second writable instance from opening the same catalog.

## Acceptance and preservation

No automatic ACCEPT/REVOKE decision is created. Existing `catalog_acceptances` history, curation fields/evidence/history and old immutable audit snapshots survive. `works.lifecycle_status=ACCEPTED` stays ACCEPTED. A new audit normally makes the earlier approval **STALE**, using the existing acceptance evaluator; its Working Set processing status becomes READY, REVIEW or ERROR from the current result. STALE is an existing approval status, not a new lifecycle state.

New REVIEW/CODE/acquisition findings are not suppressed. Current problems/health and existing review actions remain visible. Newly eligible titles are not automatically accepted, and accepted catalog works are not changed back to STAGED.

Only the targeted item's pin advances. Other sets' pins remain unchanged. Existing global eligibility recalculation may change another membership's computed READY/REVIEW state when the same work acquires a newer audit; this pre-existing policy was preserved rather than bypassed.

## Progress, summary and cancellation

The current title, batch position, provider operation/progress and aggregate successful/failed/skipped counts are presented in the existing runtime surfaces. Exact UUID context is attached when events are emitted, avoiding dependence on title-string matching or relay timing.

The final summary contains one result per confirmed eligible item plus initially skipped active items: title, item UUID, SUCCESS/FAILED/SKIPPED/CANCELLED/NOT_RUN, reason where applicable, and new audit ID/revision on persistence. Successful results also include current Working Set and approval states. Successful audit execution can legitimately result in REVIEW; SUCCESS is not health PASS or acceptance.

Workflow → **Actions → View Last Force Re-Audit Results** opens the scrollable/copyable summary. Audit Details also receives the final summary. The last batch summary is session-local; immutable audits and failure observations retain their normal database persistence. Switching databases clears the session summary.

Workflow → **Actions → Cancel Run** uses existing cooperative cancellation. A current request may need to finish before cancellation is observed. Completed audits/pins remain. A safely cancelled current title preserves its old pin and becomes QUEUED through the existing auditor; subsequent NOT_RUN titles are never queued and remain unchanged by batch dispatch. No unsafe QThread termination or all-batch transaction exists.

## Console

Grammar 3 currently parses only the standalone `audit` verb. `audit all` is invalid; accepting it would extend the grammar and make its work-vs-set scope differ from existing console behavior. This pass therefore implements the requested **UI action only** and leaves Grammar 3 and mutation guards unchanged.

## Exact files changed/added

Product edits:

- `C:\MangaAnka DDK\ddk_working_sets.py` — read-only exact batch plan and opt-in pending eligibility through existing force helpers. Default single-selected eligibility is unchanged.
- `C:\MangaAnka DDK\qt_app\workers.py` — sequential per-item force wrapper, emitted exact UUID context, results/progress and cooperative cancellation.
- `C:\MangaAnka DDK\qt_app\main_window.py` — confirmation/snapshot validation, background dispatch, duplicate guards and result presentation.
- `C:\MangaAnka DDK\qt_app\pages\workflow.py` — Actions menu, force-all/cancel/results actions and enablement.

Tests/report:

- NEW `C:\MangaAnka DDK\tests\test_force_all.py` — 16 disposable lifecycle tests.
- NEW `C:\MangaAnka DDK\tests\test_qt_force_all.py` — 8 Qt action/worker tests.
- EDIT `C:\MangaAnka DDK\tests\ui_qt_smoke.py` — new Actions button reachability included in all scale/window smokes.
- NEW `C:\MangaAnka DDK\tests\smoke_packaged_force_all.py` — frozen-source verification and offline packaged-code regressions.
- NEW this report; task logs/screenshots under `C:\MangaAnka DDK\build\force-all\`.

Shared/plugin files changed: **none**. Writer-lock implementation, SQLite timeout/journal settings, schema v7, Grammar 3, launcher/spec/fonts and the legacy Tk frontend are unchanged.

## Validation

- Focused force-audit/transaction suites: **67 passed**, 51.776 seconds, including 24 new batch tests and existing Force Re-Audit Selected/transaction controls.
- Static compilation passed for all eight changed/added Python files.
- Nine window/scale combinations passed: 1120×720, 1440×900, 1920×1080 at 100%, 125%, 150%. Seven pages and expanded command drawer checked; new Actions button reachability included. Offscreen rendered screenshots were generated; the 1120×720 Workflow image was visually inspected for layout/selection/scrollbars.
- Full DDK suite: **698 passed**, 374.078 seconds, including the existing publication/publisher/canonical-special and acceptance/curation lifecycle controls. The suite contains 111 Qt tests (103 existing + 8 new).
- Rebuilt-package offline regressions: **121 passed**, 52.039 seconds. This includes all new batch tests, existing selected/transaction Qt controls, canonical-special Dandadan controls and publisher/membership tests. Twelve embedded modules match current source, including the four edited runtime modules and the prior publisher/normalization implementation. Shared core remains external.
- Actual rebuilt EXE offscreen startup passed using an explicit new disposable TEST database and isolated settings; process stayed alive, schema was 7 and integrity check returned `ok`. Only the verified fixture process tree was stopped. This is not a claim of an interactive native packaged batch audit or a live production run.

Tests cover mixed accepted/unaccepted states; new audits and exact pin advancement; immutable old history; accepted-current to accepted-stale lifecycle; new review findings without revocation; curation/evidence survival; failure continuation/retry; atomic pin-failure rollback; between-title and current-provider cancellation; removed/ineligible items; snapshot changes; filtered rows; duplicate and deferred operation guards; existing writer lock; provider work off the GUI thread; GUI reads and independent short writes without held provider-stage transactions; superseded-curation retry; sequential batches; and unchanged Grammar 3.

## Build and manual check

Primary launcher: `C:\MangaAnka DDK\Launch_MangaAnka_DDK.bat`.

EXE target: `C:\MangaAnka DDK\dist\MangaAnka-Database-Development-Kit.exe`.

The primary Qt EXE was rebuilt successfully using the unchanged existing spec. Size: **52,547,978 bytes**. SHA-256: **`0a6a3b6bad586f375c8892f51530bcdfc0b5131d5ad6ec713c2f6e9e3cb33931`**. This supersedes the earlier Black Clover build identity; its publisher repair is still included and verified.

Legacy Tk launcher remains `C:\MangaAnka DDK\Launch_MangaAnka_DDK_Legacy_Tk.bat`; Tk source/launcher were not modified. The new batch action is Qt Workflow only. No standalone Tk interactive smoke was repeated for this feature.

Exact artifact/source/report hashes are recorded in `C:\MangaAnka DDK\build\force-all\evidence-manifest.json`. Test/build logs, nine-scale screenshot captures and disposable startup results are in that folder. PyInstaller intermediates and disposable startup DB/settings are excluded from the manifest.

Suggested user-operated check:

1. Restart the DDK; select the intended Working Set. If protected, explicitly reopen it first.
2. Workflow → Actions → Force Re-Audit All. Confirm the set/count and ACCEPTED warning; Cancel first to check no changes.
3. Launch again, confirm, and watch current title/operation/counts. Existing accepted catalog entries must retain acceptance history; new approvals should be STALE until separately reviewed/accepted.
4. Open View Last Force Re-Audit Results; verify distinct new audit IDs/revisions and exact pins. Inspect any REVIEW/CODE findings normally.
5. In a disposable set, cancel during a run: completed pins remain, the safely cancelled current item is retryable, and later items stay unprocessed. Export a fresh packet before any guarded curation.

No automated live-catalog test or production acceptance was performed.
