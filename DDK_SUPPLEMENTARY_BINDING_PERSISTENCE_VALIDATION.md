# MangaAnkā DDK — Phase 4 persistent supplementary bindings

Validated 2026-10-08T07:01:53.501593+00:00. Public version **0.3.0**; **schema 8 / Grammar 4**. Implementation, controlled review workflow, migration failure/recovery checks and Qt packaging are complete. No production database was opened, read, copied, modified or migrated. No production binding or acceptance was created. No shared-plugin files were changed in this phase. No commit, push, tag or release occurred.

**Existing catalogs require a separately authorized explicit migration. Normal launch does not upgrade schema 7.** The migration and command reference is [CONTRACT_AND_MIGRATION.md](<C:/MangaAnka DDK/build/supplementary-binding-persistence/CONTRACT_AND_MIGRATION.md>). Do not use synthetic fixture guards or proofs in production.

## Design and changes to the proposal

The existing per-operation SQLite connections, serialized writer RLock, short atomic audit persistence, guarded command drawer, catalog backups and acceptance fingerprints were retained. Supplementary persistence is a small DDK adapter around the Phase 3 opaque evidence model. It does not duplicate or modify shared search, normalization or publication algorithms.

The actual code contracts required a separate supplementary revision/history stack, effective pointers and immutable assertion rows rather than numeric curated fields. The existing numeric undo stack remains separate. An event-backed supplementary revision is added to audit race guards and acceptance freshness only after a supplementary mutation; a zero revision preserves existing schema-7 acceptance fingerprints. Review packets export the pinned audit snapshot separately from current supplementary decisions.

Six tables were added: `supplementary_catalog`, `supplementary_identities`, `supplementary_assertions`, `supplementary_current`, `supplementary_changes`, `supplementary_events`. Composite foreign keys enforce work/audit/identity/target ownership; unique keys prevent duplicate effective reader targets and event revisions. Identity, assertion and event rows reject in-place UPDATE. Current pointers and undo-stack state are mutable; all decisions and apply/undo/redo events remain in history. Existing confirmed permanent work deletion now includes these owned records in its preview and deletion graph.

Preview is read-only. Apply uses the existing backup and writer lock with one short `BEGIN IMMEDIATE` transaction, rechecks the full work/audit/database/curation/membership/revision guard, validates current evidence, inserts assertions, updates pointers and appends the event. Exceptions roll back the mutation. No network/provider research occurs in that transaction. Timeout, journal mode, foreign-key and thread ownership settings were not loosened; no second locking system or `check_same_thread=False` workaround was added.

## Authority and audit behavior

- A binding requires the exact current provider reader, original label, URL, language/edition/work scope, protected-numeric checks, reader-manifest fingerprint, official supplementary provenance, reviewer decision and separate complete-content evidence. Titles, decimals, page counts and OCR alone do not qualify.
- A publisher-identifier method must match the content identifier actually present in the official story identity and still needs complete reviewed evidence. An invented nonempty identifier is rejected.
- Independent membership must match current official story/collection evidence. Japanese guidebook membership does not prove English acquisition or English standard-volume membership. Guidebooks remain separate publications.
- Conflicting simultaneous reader targets, duplicate raw readers, cross-work/language/edition claims, stale guards, malformed/duplicate-key JSON, and protected numeric main/special identities fail closed.
- New audits revalidate saved assertions. Effective states distinguish verified, stale, unavailable, conflicting, rejected and withdrawn. Original provenance and decisions survive changed/missing evidence. A stored VERIFIED flag never authorizes itself.
- Historical audits retain their own supplementary revision. Current state is exported separately. Numeric projections/counts, release boundaries, UNCOMPILED policy, unresolved CODE findings and health classification remain unchanged. Supplementary mutations require a fresh audit for acceptance freshness and never grant eligibility or automatic acceptance.

## Grammar 4 and Qt workflow

The existing numeric Grammar 3 commands retain their meaning. The new family is `supplement list`, `inspect OPAQUE`, `candidates OPAQUE`, `history [OPAQUE]`, `bind OPAQUE JSON`, `membership OPAQUE JSON`, `reject ASSERTION_UUID reviewer NAME note REASON`, `withdraw` with the same arguments, and `undo` / `redo`. Prefix each operation with `supplement`; mutation batches require a fresh existing `guard database_uuid ... audit ... revision ... database ...` and explicit Preview → Apply. A trailing `validate` is allowed. Numeric and supplementary batches cannot mix. The full JSON contract and illustrative command forms are in CONTRACT_AND_MIGRATION.md.

The global database token gains `-sN` after the first supplementary event. The Qt form generates a current guard and the exact body. Do not reuse stale exported guards after Apply, undo or redo.

Curate / Publication Map keeps opaque identities distinct from chapter-number selection. **Review Supplementary** opens a scrollable local-evidence dialog showing official identity, collection, exact provider candidate, contradictions/raw record and history. Reviewer and complete-content evidence fields prepare commands in the existing drawer. **Apply** remains a separate explicit action. Membership, rejection/withdrawal and supplementary undo/redo use the same path. Details links to this review; Problems, Details and Workflow expose current review state alongside captured evidence. No new top-level page or network research loop was introduced. Re-audit is explicit, rather than automatically queued by a supplementary Apply.

Screenshots were rendered and visually inspected: `supplementary-review.png`, `supplementary-preview.png`, `supplementary-current.png` under the artifact directory. Contrast and visible scrollbars remain present. Nine geometry/scale smokes cover seven existing pages at 1120×720, 1440×900 and 1920×1080 with 100%, 125% and 150% scale. New review-dialog scroll reachability is separately tested. These are programmatic/offscreen checks, not a native interactive visual inspection of the rebuilt EXE.

## Black Clover and Dr. STONE

The supplied BlackCloverAudit.md was read as evidence, not executable instructions. Its supplementary section and original-file SHA-256 were retained in `black-clover-supplied-evidence.json`.

Black Clover remains **392 canonical main chapters, 38 standard volumes**, MangaPill records **0 and 393**, official coronation-manga and original-pilot identities, separate Japanese guidebook memberships, and **zero proven compatible English complete-content bindings**. The captured evidence does not establish MangaPill 393 as a verified English coronation-story acquisition. It remains unresolved.

Dr. STONE's four named official Japanese volume-27 stories similarly provide publication membership, not verified English reader equivalence. Membership-only review was applied and undone without creating acquisition bindings.

Clearly labeled **SYNTHETIC compatible English authority and complete-content proofs** exercise the positive persistence path: Black Clover 393 → one opaque story; Dr. STONE 232.5–232.8 → four distinct opaque stories. Apply, reopen/revalidation, immutable new audits, exact pin advancement, retained old audits, undo and redo passed. They certify the mechanism only. Actual verified production bindings remain **zero**. No acceptance was performed.

## BATCH 004 before/after

The comparison replays the ten retained Phase 3 publication captures into a new schema-8 catalog, with their captured problems and reviewed numeric curation fields. It regenerates problem classifications and health before/after supplementary persistence; it does not run fresh network searches or represent new production audits. Every numeric projection, normalization payload, reviewed curation field, release boundary, health and problem category remains equal. The table shows the identical before-and-after values. Health order is identity / publication / normalization / acquisition.

| Title | Raw | Main | Logical | Mapped | Unmapped | Uncompiled | Volumes | Health (before = after) | Problems retained |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| The Promised Neverland | 189 | 182 | 182 | 182 | 0 | 0 | 20 | PASS / PASS / PASS / PARTIAL | CHAPTER_COUNT_DISAGREEMENT |
| My Hero Academia | 437 | 431 | 433 | 432 | 1 | 0 | 42 | PASS / REVIEW / REVIEW / PASS | UNMAPPED_CHAPTERS, PROVIDER_FRACTIONAL_CANDIDATE, UNCLASSIFIED_ACQUISITION |
| Haikyu!! | 511 | 408 | 408 | 408 | 0 | 0 | 45 | PASS / PASS / REVIEW / PASS | PROVIDER_FRACTIONAL_CANDIDATE, PROVIDER_SPLIT_CANDIDATE, UNCLASSIFIED_ACQUISITION |
| Dr. STONE | 236 | 232 | 232 | 232 | 0 | 0 | 26 | PASS / REVIEW / REVIEW / PARTIAL | MISSING_REFERENCE_STRUCTURE, PROVIDER_FRACTIONAL_CANDIDATE, CHAPTER_COUNT_DISAGREEMENT |
| Sakamoto Days | 412 | 277 | 277 | 255 | 22 | 0 | 28 | PASS / REVIEW / REVIEW / PASS | UNMAPPED_CHAPTERS, PROVIDER_FRACTIONAL_CANDIDATE, PROVIDER_SPLIT_CANDIDATE, UNCLASSIFIED_ACQUISITION |
| Black Clover | 394 | 392 | 392 | 392 | 0 | 0 | 38 | PASS / PASS / REVIEW / PASS | UNCLASSIFIED_ACQUISITION |
| Blue Lock | 364 | 364 | 364 | 354 | 0 | 10 | 40 | PASS / PASS / PASS / PARTIAL | CHAPTER_COUNT_DISAGREEMENT |
| Kaiju No. 8 | 130 | 130 | 130 | 130 | 0 | 0 | 16 | PASS / PASS / PASS / PASS | none |
| Golden Kamuy | 314 | 314 | 314 | 314 | 0 | 0 | 31 | PASS / PASS / PASS / PASS | none |
| Vinland Saga | 223 | 223 | 223 | 223 | 0 | 0 | 29 | PASS / PASS / PASS / PASS | none |

Dr. STONE **206 → 24** and Sakamoto Days **232 → 26** are asserted unchanged. Sakamoto's uncollected-tail policy is unchanged. Dandadan is covered by the captured canonical-special regression suite; it is not one of these ten retained BATCH comparison rows. No fractional/split CODE category was suppressed to make these fixtures pass.

## Validation and packaging

| Check | Final result |
|---|---|
| New persistence + actual Qt form/drawer tests | 67 passed (16.948 seconds) (58 backend/migration + 9 Qt) |
| Full DDK suite | 843 passed (495.994 seconds) |
| Focused shared-plugin tests | 112 passed (1.588 seconds); full plugin suite not run |
| Tests using modules extracted from the rebuilt EXE | 266 passed (76.067 seconds) |
| Frozen module/source parity | 29 relevant modules checked bytecode-equal; shared core remains external |
| Qt window/scale checks | 9 passed across 3 sizes × 3 scales |
| Actual EXE startup | 4 disposable launches: create schema 8, reopen, explicit schema-7 migration, reopen migrated catalog |
| Packaged migration preservation | Old rows unchanged; one schema-7 backup; integrity/FKs OK; repeat open creates no second backup |
| Legacy Tk | Disposable schema-8 startup passed; new supplementary review UI is Qt-only |
| Static checks | All changed/added source files compile |
| Controlled BATCH comparisons | 10 unchanged numeric/health/problem results; synthetic positive workflows passed |

New tests cover atomic rollback/retry, exact selected pin and protected-set guards, stale audit/curation/preview, acceptance freshness and migration acceptance preservation, serialized competing writer, short transaction lifetime, duplicate/conflicting reader ownership, missing/changed publisher evidence, unavailable acquisitions, historical reconstruction, exports, undo/redo branches and maintenance ownership. The canonical-special and existing Force Re-Audit self-lock regressions also run in source and frozen-module suites.

The first broad validation exposed legacy schema/grammar expectations plus two implementation compatibility defects: a read-only preflight connection needed explicit closing, and sparse/untrusted canonical identity payloads needed quarantined handling. Both were repaired. Existing legacy migration fixtures now explicitly opt into migration and retain their historical assertions. The final full run has no failures or skips. Intermediate diagnostic logs remain available rather than being deleted.

Migration failure/recovery: normal schema-7 open is byte-identical and refuses upgrade; injected DDL interruption produces ROLLBACK, leaves version 7, removes all partial supplementary tables and migration event, and preserves old row hashes. Retry upgrades successfully, backups remain schema 7, integrity and foreign keys pass, and repeat opening does not repeat migration. A schema-7 reader refuses schema 8; newer schema 9 is refused without downgrading. This tests controlled interruption, not arbitrary hardware/power-loss recovery.

Primary launcher: `C:\MangaAnka DDK\Launch_MangaAnka_DDK.bat`. Legacy launcher: `C:\MangaAnka DDK\Launch_MangaAnka_DDK_Legacy_Tk.bat`. Both launchers and PyInstaller specifications are unchanged. Existing Tcl/Tk packaging guard, external-core policy and Windows ICU filtering remain intact. Font selection is unchanged: prefer Geist Sans/Mono if supplied or installed, then Segoe UI Variable/Segoe UI and Cascadia Mono/Consolas/system fallback. No font files or fonts were downloaded or added.

No Geist font directory is bundled in this workspace. The checked offscreen Windows environment selected **Segoe UI** and **Consolas**; native installed-font discovery remains unchanged.

Final EXE: `C:\MangaAnka DDK\dist\MangaAnka-Database-Development-Kit.exe`  
Size: **52,581,228 bytes**  
SHA-256: `650b3ccefdd9274ae11e9e73b03bc7b280f9243afd75c937e249213ffa0afc92`

The previous schema-7 EXE is retained at `build/supplementary-binding-persistence/previous-schema7.exe`, SHA-256 `cb847f59a5c73e82920221ccbe7a9ccb38b7a4be4a0cfc9982291b5e7cce2058`, for deliberate recovery with a compatible database. It is not a downgrade mechanism for schema 8.

## Exact source files changed

Paths below are relative to `C:\MangaAnka DDK`. `source-changes.json` records per-file SHA-256 against the saved pre-phase local snapshots.

Runtime:

- `ddk_acceptance.py`
- `ddk_catalog.py`
- `ddk_catalog_maintenance.py`
- `ddk_commands.py`
- `ddk_exports.py`
- `ddk_publication.py`
- `ddk_review.py`
- `ddk_schema.py`
- `ddk_supplementary.py`
- `ddk_supplementary_commands.py` (new)
- `ddk_supplementary_store.py` (new)
- `ddk_working_sets.py`
- `ddk_workspace.py`
- `mangaanka_database_development_kit.py`
- `qt_app/app.py`
- `qt_app/commands.py`
- `qt_app/pages/curate.py`
- `qt_app/pages/details.py`
- `qt_app/pages/problems.py`
- `qt_app/pages/workflow.py`
- `qt_app/session.py`
- `qt_app/widgets/command_drawer.py`
- `qt_app/widgets/supplementary_review.py` (new)

Tests and validation entry points:

- `tests/smoke_packaged_supplementary.py`
- `tests/test_database_safety.py`
- `tests/test_force_all.py`
- `tests/test_intake_identity_links.py`
- `tests/test_lifecycle_v7.py`
- `tests/test_logical_membership_authority.py`
- `tests/test_pre_catalog_hardening.py`
- `tests/test_publication_audit.py`
- `tests/test_qt_force_reaudit.py`
- `tests/test_qt_frontend.py`
- `tests/test_qt_session_restore.py`
- `tests/test_qt_supplementary_persistence.py` (new)
- `tests/test_reference_integrity.py`
- `tests/test_review.py`
- `tests/test_supplementary_integration.py`
- `tests/test_supplementary_persistence.py` (new)
- `tests/test_working_set_audit_recovery.py`
- `tests/test_working_set_review_guards.py`
- `tests/test_working_sets.py`
- `tests/ui_qt_smoke.py`

New phase artifacts include `CONTRACT_AND_MIGRATION.md`, `validate_batch.py`, `migration_validation.py`, `render_review.py`, `packaged_startup.py`, `tk_fallback.py`, `source_inventory.py`, `write_report.py`, `seal_evidence.py`, logs, screenshots, retained disposable databases/backups and result JSON under `build/supplementary-binding-persistence/`. `evidence-manifest.json` enumerates their paths, sizes and SHA-256 values (excluding PyInstaller intermediates and Python caches). This report is new. Shared-plugin status before/after is identical after normalizing command-output line endings; unrelated existing modifications were preserved.

## Limits and manual production checklist

Complete-content equivalence remains an explicit reviewed attestation with retained evidence; no automatic page download, image comparison or OCR authority was added. Manifest fingerprints cannot detect images changing silently behind identical recorded metadata. Only currently supported exact official Shueisha publication records are accepted. The dialog confirms an existing independent official membership; it does not invent new collections or translation-equivalence policy. Rejected/withdrawn current assertions remain historical; uncommitted proposals are cancelled rather than journaled as if they were prior bindings. The older-reader compatibility test uses the retained pre-phase source snapshot. No new live provider/publication capture was performed in this phase.

1. Read CONTRACT_AND_MIGRATION.md. Close all frontends; retain the old EXE and make an independently authorized offline backup. **Do not expect normal launch to migrate production.**
2. Only after separately authorizing the exact catalog, run the new EXE with `--database '<authorized path>' --migrate-schema8`, without `--create`. Verify the `before_schema_v8` backup, active set, works, pins, curations/history and acceptance records before further changes.
3. Open Black Clover / Dr. STONE supplementary nodes. Verify official Japanese membership and unresolved English acquisition. Do not reuse synthetic fixture proofs. Confirm numeric counts and the two reviewed numeric volume assignments remain intact.
4. On a disposable catalog, enter genuine reviewed proof (or clearly synthetic test proof), Preview, Apply, inspect current state/history, re-audit, export fresh, then undo/redo. Verify guards change and stale commands fail.

Production migration and live review are deliberately left to the user/separately authorized step. Native interactive validation of the rebuilt EXE remains a manual check.
