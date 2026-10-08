# MangaAnkā DDK pre-production lifecycle repair

Completed source validation on 2026-10-03 (America/Chicago). Visible DDK version remains **0.3.0**; database schema is **7**. No EXE rebuild, commit, push, tag, or release was performed.

The production/test catalog at `C:\Users\Jerry\Documents\MangaAnka-Database-Development-Kit\mangaanka_catalog.db` was not opened, instantiated, migrated, copied, or written. Every database used for validation was disposable. The MangaAnkā Calibre plugin and `mangaanka_search_core` were not edited. No provider/network audit or plugin-wide test suite was run.

## 1. Root causes

READY and acceptance used different policies. Acceptance allowed unresolved UNCLASSIFIED_ACQUISITION, accepted by work ID, and changed other linked memberships. Lifecycle ACCEPTED lacked approval provenance and remained trusted after newer evidence. Some set views substituted latest global audits for pins. Title uniqueness prevented unrelated same-title works; alias requests could create redundant memberships. Protection, reopening, recovery, and post-curation scheduling lacked one consistent workflow.

## 2. Exact files changed

Application source:

- `mangaanka_database_development_kit.py`
- `ddk_acceptance.py` — new
- `ddk_schema.py` — new
- `ddk_working_sets.py`
- `ddk_catalog.py`
- `ddk_publication.py`
- `ddk_review.py`
- `ddk_exports.py`
- `ddk_editor.py`
- `ddk_catalog_maintenance.py`
- `ddk_workspace.py`

Tests:

- `tests/test_lifecycle_v7.py` — new, 33 regressions
- `tests/test_catalog_maintenance.py`
- `tests/test_database_safety.py`
- `tests/test_pre_catalog_hardening.py`
- `tests/test_review.py`
- `tests/test_working_set_audit_recovery.py`
- `tests/test_working_sets.py`
- `tests/ui_lifecycle_v7_smoke.py` — new
- `tests/ui_working_set_smoke.py`
- `tests/ui_smoke.py`

Documentation: `MangaAnka_Database_Development_Kit_README.md` and this report. Existing fixture identities were corrected where formerly distinct works claimed the same canonical ID. Obsolete permissive acceptance, terminal-set, and schema-v6 expectations were updated.

## 3. Schema v7 requirement

Schema 7 was necessary for durable approval provenance, removal of title uniqueness, canonical uniqueness, and a duplicate membership pointer. Application and plugin release versions were not changed.

## 4. Migration behavior

Existing v6 databases receive a SQLite backup at `backups/<stem>_before_schema_v7_<timestamp>.db` before mutation. Migration detects duplicate nonempty canonical ID/edition/language claims first and aborts with each conflicting ID and UUID. It rebuilds `works` under `BEGIN IMMEDIATE`, copying every original column and ID/UUID unchanged, restores explicit indexes, adds v7 objects, and validates foreign keys and full integrity before commit. A failure rolls back the table rebuild and all child/schema changes; the pre-migration backup remains available. Fresh empty databases need no pre-v7 backup. Older supported schemas still take their existing migration path before v7.

Migration regressions preserve database/work/conceptual/set/item UUIDs, audit IDs and revisions, curation, evidence, dispositions, edition relationships, removed intake rows, pins, and history. Both `PRAGMA foreign_key_check` and `PRAGMA integrity_check` pass. A deliberately injected mid-migration failure and a duplicate canonical claim both fail safely.

## 5. Tables, indexes and columns

- New `catalog_acceptances`: work UUID, ACCEPT/REVOKE decision, audit ID/revision, curation revision, effective-state fingerprint, UTC timestamp, originating set/item UUIDs, and reason.
- New acceptance-history index on `(work_uuid,id DESC)`.
- Removed table-level `UNIQUE(input_title,edition,language)`.
- New partial unique index on nonempty `(canonical_work_id,edition,language)`.
- New `working_set_items.duplicate_of_item_uuid` self-reference and index.
- New sets and audits record schema version 7; historical environment metadata is preserved.

Approval history has work/audit foreign keys. Deleting a catalog work explicitly previews/counts/removes its approval history; surviving intake requests are detached rather than deleted. Set/item provenance references use SET NULL if those referenced records are deleted.

## 6. Central eligibility

`Acceptance.evaluate()` returns eligibility, human-readable blockers/warnings, exact audit and curation revisions, work/item UUIDs, pin currency, dependency freshness and a fingerprint. It drives pin READY/REVIEW classification, selected/bulk acceptance, reconciliation, linked recalculation, and CURRENT approval validity.

Acceptance requires a trusted shareable canonical identity, exact edition/language, current consistent audit/pin, complete nonempty publication with final volumes and fully mapped logical chapters, compatible and valid curation, and unchanged applicable structure dependencies. Identity, data, research, unknown and unresolved code-review problems block. Canonical unmapped/conflicting rows and fatal execution failures block. Raw unclassified acquisition blocks even if an issue row is accidentally absent. A matching, reviewed/verified, grounded human disposition can resolve UNCLASSIFIED_ACQUISITION. Normalization REVIEW and acquisition PARTIAL alone produce warnings and need not block.

## 7. Acceptance provenance

Explicit human approval records the exact safe state, not just lifecycle ACCEPTED. The write rechecks all targets inside one transaction before approval history, lifecycle, selected membership and journal events commit together. A second membership approving the identical global state does not duplicate the global acceptance snapshot; its own membership decision is journalled.

## 8. Stale acceptance

The latest approval must still match the latest audit, audit revision, current curation revision and state fingerprint, and pass the evaluator. A newer clean audit still makes the prior approval STALE. No automatic reapproval occurs. Accepted Master Catalog filters to CURRENT; All Catalog shows lifecycle and acceptance state separately.

## 9. Legacy ACCEPTED rows

Lifecycle is preserved during migration. Without v7 approval provenance the derived state is LEGACY_REVIEW_REQUIRED. No audit is guessed and no work is silently downgraded. Reevaluate Acceptance explicitly confirms a safe current snapshot or offers a reasoned revocation to STAGED.

## 10. Exact Working Set acceptance

Set acceptance uses exact item UUIDs and their pins. Accepting A leaves B's decision and pin unchanged even when both refer to the same work. Global acceptance is a separate explicit work-ID operation. A superseded item pin blocks acceptance.

## 11. Set reopening

COMPLETE and ARCHIVED remain protected until Status → Reopen for Review explicitly changes the set to REVIEW. UUIDs, links, pins, item statuses, observations and approval history remain unchanged; reopening performs no audit. REVIEW can return to OPEN for membership edits. COMPLETE requires a nonempty set with only ACCEPTED, REJECTED or DUPLICATE nonremoved items. Archive can park unfinished work. Complete/archive are human decisions.

## 12. Item reopening

Intake → Reopen Selected for Review changes only selected accepted/rejected items in an active editable set to QUEUED. Their previous decisions remain journalled and their old pins remain until a new audit successfully persists. DUPLICATE is terminal and is not independently reaudited.

## 13. Mutation protection

Shared backend guards verify active database ownership, exact membership/work ownership, set state and terminal-item state. Protected sets reject intake changes, item status changes, audits, observations, pins, acceptance, rejection, retries, batch execution and set-driven curation. REVIEW blocks membership edits but permits workflow. Reading/export/reopen remain available. Explicit global curation and global reaudit are allowed without changing archived membership pins.

## 14. Run Working Set

The run is sequential at title level. It audits pending/queued/interrupted items and stale pins, and completes legacy AUDITED workflow items. It skips accepted/rejected/duplicate items, current READY items and REVIEW cases requiring human action. ERROR is not silently retried. A newly added unpinned item receives a fresh audit despite any existing global work audit. No age-based provider scheduling or title parallelism was added.

The run summary includes full set status counts, reused/new work counts and zero duplicate canonical work creations, with Run/Accept All Safe/Open Review Items/Retry Errors actions in the existing UI. The set is left OPEN/REVIEW until the user changes it.

## 15. Accept All Safe

Preview targets current READY items and reports safe/review/error/stale counts. Commit re-evaluates under the transaction and verifies the preview fingerprint. Changed/unsafe candidates remain unaccepted and stale READY candidates become REVIEW. Safe approvals commit together; injected write failures roll back every approval/lifecycle/item/event write.

## 16. Retry Errors

Retry Errors explicitly queues ERROR items in an editable active set and starts their run. Normal Run does not infer transient failures from exception text or retry errors indefinitely. Interrupted AUDITING items are recovered once to QUEUED at app startup/activation of a database and before a new run; old pins survive and protected sets are untouched.

## 17. Post-curation automation

Apply, Undo, Redo and reviewed structure sharing through the active set preserve committed curation and queue a fresh audit of only that membership. Busy runs defer affected memberships; already refreshed memberships do not need another deferred run. Successful persistence advances that pin and reevaluates readiness. A failed run retains curation and the previous pin and exposes ERROR/REVIEW. Evidence-only changes conservatively use the same audit path. Explicit global curation does not automatically advance any set's pin.

## 18. Curation/audit races

The publication adapter invokes a narrow identity callback before effective catalog lookup and reference computation. The audit captures the target's curation revision/identity and applicable structure relationships, source revisions and source audit IDs. Persistence rechecks those dependencies transactionally and never stamps an old computation with a newly read revision. Changed results are discarded and queued; one immediate retry is permitted, then continuing changes leave the item QUEUED. Unrelated title changes do not invalidate the audit. Used dependencies are retained in publication diagnostics for later freshness checks.

## 19. Disposition recalculation

Ignore/Reopen retains the existing append-only disposition and issue-signature mechanism. It recalculates relevant active audited/ready/review memberships without a network audit. Reopening the issue makes them REVIEW again when blocked. Accepted/rejected decisions remain historical and are not silently reopened. Protected membership states/pins are not changed.

## 20. Same-title works

Distinct exact canonical identities can coexist with the same displayed title, edition and language and retain different work UUIDs. The canonical unique index and exact reuse path prevent duplicate trusted canonical rows. No fuzzy/title-based merge was added.

## 21. Alias duplicate intake

After trusted identity resolution, another primary membership with the same exact work inside that set produces DUPLICATE with the original query, primary pointer and a small observation/event. It stops before reference/publication computation, creates no second work/audit/pin/approval, and permits COMPLETE. The same work in different sets remains valid.

## 22. Pinned versus current views

Set Catalog health/counts, queued audit diagnostics, Problems, Details, selected review packets/context and default set exports use the pinned audit. Missing pins do not substitute global evidence. Snapshot chapter rows/curation use stored evidence; current global audit and pin state are separately exposed. Global views use latest audits. Working Set CSV/context include item/work UUIDs, status/lifecycle/acceptance state, pin ID/revision, latest global ID, pin state, audited curation revision and duplicate pointer. Reconciliation explicitly shows global current state and linked memberships. Curate clearly labels that it edits the latest shared catalog state.

## 23. Focused test results

All passed:

- 33 new lifecycle-v7 regressions, including the 275/275-mapped MF Ghost-style fixture with four unclassified records, two-set acceptance, migration preservation/rollback/conflict, alias short-circuit, cancellation, recovery, curation race and source-dependency freshness.
- 10 Working Set regressions.
- 6 audit/recovery regressions.
- 18 catalog-maintenance regressions.
- 9 pre-catalog hardening regressions.

Acceptance failure injection covers validation, after evaluation/before first write, approval-history insert, catalog lifecycle update, membership update and a later selected work; safe retry succeeds.

## 24. Complete suite

`python -m unittest discover -s tests -q`: **179 tests passed** (final run, 22.004 seconds). The MangaAnkā repository suite was not run.

## 25. UI smoke results

All five offline disposable Tk scripts passed:

- `tests/ui_smoke.py`: visible functioning scrollbars, both-axis Details scrolling, dark selection/read-only control styles, native selection, command preview/apply and undo/redo.
- `tests/ui_working_set_smoke.py`: intake/switching/scopes/copy/acceptance and toolbar bounds at 1120 and 1920 widths.
- `tests/ui_working_set_audit_smoke.py`: batch linking/pinning, visible intake failures and retry.
- `tests/ui_catalog_maintenance_smoke.py`: preview/cancel/typed deletion and preserved sibling/intake data.
- `tests/ui_lifecycle_v7_smoke.py`: run, bulk approval, reopening, completion gate, blocked reason, automatic curation/undo/redo audits, retained curation on failure, deferred busy-run curation, explicit global reaudit with archived pins unchanged, superseded/current indicators, reconciliation and scoped history.

Tk required access outside the filesystem sandbox to its installed runtime. The smoke databases remained temporary. Details provider inventory initially displays four rows so the long diagnostics pane remains usable at 1120×720; both provider scrollbars remain available. No dark theme redesign was made.

## 26. Static validation

AST parsing and bytecode compilation pass for all 34 DDK/test Python files. Edited application modules and new test files pass trailing-whitespace/conflict-marker scanning. A Git diff check is unavailable because this DDK directory has no `.git`; no Git command changed either workspace.

## 27. Remaining limitations

- The EXE still contains its prior packaged source; this pass did not rebuild it.
- Live provider/network behavior was intentionally not exercised. Existing provider/search/publication algorithms were reused unchanged.
- No real catalog migration was attempted. Canonical conflicts in a real v6 file deliberately abort and require human resolution rather than automatic merging.
- Legacy approval provenance cannot be reconstructed; it requires explicit human reevaluation.
- Curate edits the latest shared catalog, while set evidence panes stay pinned. Global curation requires a later explicit global audit or set run before fresh approval.
- Evidence-only edits conservatively trigger a network audit when performed through the active set.
- If dependencies keep changing across the immediate race retry, the item remains QUEUED for a later Run.
- Direct scripts bypassing the app's OS writer lock remain outside its process-level writer protection; backend SQLite transactions/ownership/revision guards still apply.
- No time-based data-recency scheduling, title parallelism, automatic completion/archive, provider changes or general repair wizard was added.

## Short manual checklist after an eventual EXE rebuild

1. Open the existing test catalog, confirm the pre-v7 backup and unchanged UUIDs/pins/curation. Legacy ACCEPTED works should show LEGACY_REVIEW_REQUIRED and stay out of current Accepted Master Catalog until explicitly confirmed.
2. In Batch 002, use Reevaluate Acceptance on MF Ghost. Unresolved acquisition rows must block. Record an evidence-grounded disposition, verify READY, then Accept Selected/All Safe and check CURRENT. Do not invent a disposition merely to make it pass.
3. Reopen archived Batch 001 to REVIEW. Pins must remain fixed. Reopen just one terminal item and run it; only that item's successful audit should advance its pin. Apply a real curation correction and check its automatic reaudit.
4. Put the same work in two sets, approve only one membership, and create a newer audit in the other. The older set must retain its pin and show SUPERSEDED; current global approval must be STALE until explicitly reconfirmed. Check Details/table scrolling and readable selections at the minimum window size.
