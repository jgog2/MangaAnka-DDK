# Force Re-Audit Selected workflow validation

DDK v0.3.0, schema v7, Grammar 3. Current local worktree inspected and used as the source of truth. All automated databases/settings were disposable. The live catalog and Audit 16 were never opened or modified. No commit, push, tag, release, or version bump.

## 1. Actual cause of the observed reuse behavior

`Catalog → Run Working Set → WorkingSets.run_candidates()` includes pending/queued items and stale READY/REVIEW items. The central evaluator's freshness check concerns pinned audit identity, workflow, curation, and structure dependencies; an implementation change without a version/fingerprint change does not itself make a current snapshot stale. Thus a current REVIEW/READY item may be omitted by a normal set run. Terminal ACCEPTED/REJECTED items are also deliberately skipped.

There is a second distinction: the existing `SearchAuditor.audit_many()` summary's **Reused/New** fields count existing/new catalog work identities, not existing/new audit rows. `Reused 1 / New 0` does not prove that an audit was reused. A linked nonterminal item passed to the existing Grammar 3 `audit` command already reaches a fresh `audit_one()` computation. Inspection found no audit-row reuse inside that pipeline. These normal semantics were left unchanged.

## 2. Exact changed files

Modified:

- `ddk_working_sets.py`: authoritative exact-item eligibility check and transactional explicit queue/reopen operation.
- `qt_app/pages/catalog.py`: More-menu action, selection/busy eligibility, menu refresh.
- `qt_app/main_window.py`: selected-item guard, confirmation, existing async start integration.
- `qt_app/workers.py`: forced-run reporting based on changed pinned audit IDs.
- `MangaAnka_Database_Development_Kit_README.md`: usage and safety documentation.

Added:

- `tests/test_force_reaudit.py`: 13 deterministic backend workflow tests.
- `tests/test_qt_force_reaudit.py`: eight deterministic Qt tests.
- `tests/smoke_packaged_force_reaudit.py`: offline execution smoke using application modules extracted directly from the final EXE's embedded PYZ; never bundled.
- `DDK_FORCE_REAUDIT_VALIDATION.md`: this report.

Generated: primary EXE and normal PyInstaller build artifacts. No changes to `mangaanka_database_development_kit.py`, schema, acceptance evaluator, publication/normalization/search/provider implementation, command parser/controller, local plugin/search core, build spec/hooks, launchers, or legacy Tk frontend.

## 3–5. Action, existing capability, and bypass

Exact label: **Force Re-Audit Selected**, under **Catalog → More**, with no primary-toolbar addition. There was no existing force/reuse flag. The existing async worker already computes fresh immutable audits for explicitly queued items. The new action bypasses only normal candidate selection, explicitly reopens/queues one stable membership, and calls the existing `start_audit`/`AuditWorker`/`SearchAuditor.audit_many`/`audit_one` path.

`force_reaudit` on Qt start/worker orchestration is opt-in and controls guarded queueing and accurate audit-ID reporting; it does not introduce another provider/search/publication path. Normal starts retain their existing behavior and summary.

## 6. Exact item scope and race guards

Exactly one selected row must have a `working_set_item_uuid` in the visible Working Set scope. All Catalog, Accepted Master Catalog, no selection, and multiple selections reject the action. The backend re-reads the exact membership and active database/Working Set at queue time.

Allowed stable states: REVIEW, READY, ACCEPTED, REJECTED, ERROR. PENDING, QUEUED, AUDITING, DUPLICATE, removed/missing memberships, inactive sets, and COMPLETE/ARCHIVED sets reject it. Reopen a protected Working Set through its existing action first.

The queue operation takes the existing database lock and `BEGIN IMMEDIATE`; a second queue attempt sees QUEUED and is rejected. A pending confirmation and a busy worker both disable/reject duplicate starts. Existing session writer locking, per-item identity/curation guards, superseded-audit retry, and persistence transactions remain authoritative. No global work-ID fallback is used.

## 7–8. History and pins

The normal `persist_item_audit()` transaction calls append-only `save_audit()` and then advances the selected item's pin. Audit ID/revision increase; previous audit JSON/results remain queryable and unchanged. No audit, title, or membership deletion/re-intake occurs.

Only the selected membership's pin advances. Other sets retain their old pin and revision. Existing global acceptance/freshness evaluation can regard those retained snapshots as superseded; that existing behavior is not disabled or replaced.

## 9. Failure and cancellation

Provider/audit execution failure records the normal ERROR observation while preserving the previous valid audit pin. Identity incompatibility retains the normal REVIEW observation. A persistence/pin failure rolls back the new audit transaction. Normal cancellation keeps the old successful pin and returns unfinished items to QUEUED where supported by the existing auditor. A forced failure summary reports New 0 / Reused 0; it does not claim that the preserved old pin is a fresh result.

## 10–12. Curation, acceptance, and caches

No curated fields, chapter/volume mappings, verification, evidence, source notes, aliases, IDs, or history are cleared. New automatic evidence passes through the existing curation boundary. A verified MF Ghost chapter 275 → volume 23 fixture retains its fields, evidence, history, and effective mapping after forcing.

No special acceptance policy or direct acceptance-state mutation was added. An ACCEPTED membership is explicitly queued for review; its existing acceptance record remains. On a successful newer audit, the existing central v7 evaluator derives STALE for the previously accepted snapshot. The resulting item becomes READY/REVIEW/ERROR through the normal pin evaluator. No automatic reacceptance occurs.

The action does not clear provider/reference caches or require fresh network retrieval. The normal pipeline retains control of cached evidence and retrieval. This feature creates a fresh audit computation, not a mandatory network refresh.

## 13. Confirmation and progress

The dialog names the actual selected title and states that current audit logic creates a new audit, previous audits/curation/evidence are preserved, and existing acceptance may become stale. Buttons are **Force Re-Audit** and **Cancel**, with Cancel as default/Escape action.

The existing worker supplies immediate Running feedback, current-item/stage/progress UI, cancellation, activity, and final refresh. Forced reporting compares original pins with the final selected pins: a successful one-item run shows **New 1 / Reused 0** and the new audit ID. Selection/inspector refresh follows the new pin. There is no synchronous special audit path.

## 14. Focused source validation

- 21 new focused tests passed: 13 backend and eight Qt.
- Existing Working Set/recovery regressions: 16 passed.
- Existing v7 lifecycle/acceptance regressions: 33 passed.
- All Qt tests: 72 passed.

Coverage includes a reusable current REVIEW snapshot, immutable history, pin advancement, pipeline failure, transactional pin failure, verified curation/evidence preservation, ACCEPTED→STALE without a new acceptance record, READY results derived from new evidence, ERROR and REJECTED states, two sets sharing one work, missing/unstable/duplicate selection, duplicate queueing, inactive/protected sets, cancellation, normal Run Working Set, and unchanged Grammar 3 `audit` dispatch. Qt tests exercise the actual Cancel-default confirmation, async worker, progress, busy and nested-confirmation guards, success/failure summary, and refreshed pin/selection.

## 15. Complete suite and static checks

Final complete DDK suite: **287 tests passed in 76.500 seconds**. AST and bytecode compilation passed for 71 source/test files, including a final check after the full suite; changed-file conflict-marker and trailing-whitespace checks passed. No whole plugin repository suite was run.

## 16. Window/scale checks

All nine source cases passed: 1120×720, 1440×900, and 1920×1080 at Qt scale factors 1, 1.25, and 1.5. All six pages were exercised with disposable catalogs. No layout redesign, theme/font change, selection-contrast change, or scrollbar removal occurred. These are configured Qt scale checks, not certification of every physical monitor setup.

## 17–18. Final build and packaged validation

Rebuilt successfully after the final 287-test pass, using the existing validated PyInstaller 6.20.0 spec. No spec, hook, font, dependency, or launcher change was needed. All 15 checked runtime modules (the four affected by this repair plus the preceding serialization modules) have embedded code objects matching compilation of the final local source, normalizing only filenames. Archive checks exclude frozen plugin submodules, test fixtures, SQLite databases, and ICU binaries.

Final size: **52,513,820 bytes**.
SHA-256: `73159f2542d80df8f6bd03198fbecae7a73f3cccf94f2bce866041954bddb86d`.

**Frozen application execution:** four additional offline smoke tests passed in 2.000 seconds. The harness imports the actual embedded DDK/Qt application code directly from the final EXE, supplying deterministic provider/reference fixtures through the existing auditor factory. It verifies the actual confirmation dialog, asynchronous fresh audit and higher ID, selected pin refresh, New 1 / Reused 0, failure preserving the old pin with New 0, and unchanged normal command dispatch. Assertions ensure `ddk_working_sets`, `qt_app.main_window`, `qt_app.pages.catalog`, and `qt_app.workers` were loaded from the EXE, not local source. No product smoke flag or bundled test code was added.

**Native EXE window:** launched against an explicit temporary `packaged-smoke.db` and isolated INI only. Verified the exact More-menu label, disabled action with no row selection, enabled action on the exact READY membership, actual Monster title in the confirmation, preservation/staleness wording, readable dark controls, and the Force Re-Audit/Cancel buttons with Cancel initially focused. Cancel returned to the unchanged READY row without starting an audit; a read-only check after normal close confirmed one audit row and pin 1, SQLite integrity `ok`, and no foreign-key violations.

The native EXE confirmation was cancelled deliberately. Successful forced execution was verified with frozen application code and offline fixtures as described above; no live provider requests or production-catalog run were used for this smoke.

Primary EXE target: `C:\MangaAnka DDK\dist\MangaAnka-Database-Development-Kit.exe`.
Primary launcher: `Launch_MangaAnka_DDK.bat`. Legacy Tk fallback remains intact.

## 19. Known limits

Force Re-Audit is intentionally a Qt Catalog action for one active, unprotected Working Set membership. Global rows, multiple selections, duplicate memberships, and protected sets require choosing/activating/reopening the exact set first. A new audit may still return REVIEW or ERROR; this feature does not make uncertain publication/identity evidence pass.

The old normal Reused/New summary still describes catalog identities; the forced summary explicitly describes audit rows. No normal command behavior or Grammar 3 extension was introduced. Native packaged UI smoke and frozen-module offline execution are separate checks, so deterministic validation need not send real provider requests. Live Dandadan is left for the user.

## 20. Manual Dandadan checklist

1. Back up the live catalog and close other DDK writers. Launch the rebuilt primary Qt EXE and explicitly open the intended catalog.
2. Activate Dandadan's exact Working Set; reopen the set for review if protected. Select only the intended standard/en membership.
3. Catalog → More → **Force Re-Audit Selected**. Check the title in the confirmation, then choose **Force Re-Audit**.
4. Wait for completion. Check **New 1 / Reused 0**, a new audit ID greater than 16, and that the selected membership's pin points to it. Audit 16 must remain in history; other membership pins must remain unchanged.
5. Inspect the new publication/fractional evidence, curation/evidence, and acceptance state. Do not expect forced PASS or automatic acceptance. If it fails, verify the previous valid pin is still usable and inspect the reported error before retrying.
