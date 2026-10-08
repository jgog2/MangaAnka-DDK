# MangaAnkā project handoff for a new ChatGPT chat

Prepared October 7, 2026, America/Chicago. This is project context, not authorization to start another repair, repeat completed implementation, or operate production. Read it, then wait for the user's next specific task.

This handoff supersedes the October 5 handoff's statements about the latest task, current EXE, missing publisher completion authority, and next production check. Older reports remain useful evidence of their own passes. Their old counts, hashes, pending tasks, and source descriptions must not override current files or newer evidence.

## 1. Two programs, one shared behavioral source

**MangaAnkā Database Development Kit (DDK)**

- Workspace: `C:\MangaAnka DDK`
- Current product version: v0.3.0.
- Standalone development/audit, review, curation, working-set and catalog tool.
- Primary frontend: Qt Widgets / PySide6. Legacy Tk remains a recovery frontend.
- SQLite schema: **7**. Command grammar: **3**.

**MangaAnkā Calibre plugin / shared core**

- Worktree: `C:\MangaNana-Dev\MangaNana-calibre`
- Local files are the behavioral source of truth for search, canonical identity, provider resolution and shared publication/reference machinery.
- Legacy module/package names may still use MangaNana. Do not rename or change versions during a targeted repair.
- The worktree contains substantial earlier development changes. Preserve them; a whole-worktree diff is not the latest task's change list.

The DDK audits the CURRENT plugin implementation. It must not maintain a divergent replacement for search ranking, edition classification, canonical grouping, MangaDex structure, publication manifests, reference integration or chapter-volume projection.

The live-core adapter is `C:\MangaAnka DDK\mangaanka_search_core\__init__.py`. It resolves `MANGAANKA_PLUGIN_PATH`, defaulting to the plugin worktree above, and imports live shared modules without executing Calibre's plugin entry point. Existing snapshot-looking files under the package are not necessarily the active implementation. Inspect the loader before drawing conclusions. The packaged EXE still requires the local shared-plugin source; it is not a portable copy of the entire plugin.

## 2. Standing safety and development constraints

LOCAL WORKTREES ARE THE SOURCE OF TRUTH. Inspect the actual code and call graph before editing. Do not reconstruct current behavior from GitHub, guess from filenames, or redo completed work.

- Prefer narrow DDK changes. Shared-plugin edits require a concrete defect and a documented narrow justification or explicit user authorization.
- No title-specific runtime hacks, broad fuzzy identity matching, invented chapters, or guessed volume assignments.
- No commit, push, tag, release, version bump, reset/clean, or broad reformatting.
- Preserve unrelated changes, historical audits, selected pins, curation, assertion evidence, failed intake observations and acceptance provenance.
- Use deterministic offline/fake-network tests and disposable schema-v7 databases.
- Do not run the whole plugin repository test suite for a targeted DDK task. Use focused shared-core tests; use the full DDK suite when warranted by a repair.
- Provider/network/reference work belongs off the GUI thread. Do not hold a SQLite write transaction across that work.
- Preserve readable dark controls, selected-row/combobox contrast, visible functioning horizontal/vertical scrollbars, and scrollable Details.
- Do not suppress or reclassify CODE findings merely to make a title pass. A successful forensic repair can legitimately leave REVIEW.
- Distinguish captured replay, source tests, frozen-module tests, offscreen EXE startup, interactive packaged UI tests and live production checks. Never claim one proves another.

**Protected live catalog — do not open or mutate automatically:**

`C:\Users\Jerry\Documents\MangaAnka-Database-Development-Kit\mangaanka_catalog.db`

The latest pass did not open this database, even read-only. The user operates production manually. Do not run a migration, audit, acceptance, curation, deletion, cache purge, or ad hoc SQL against it.

The user has supplied a separate review export for inspection:

`C:\Users\Jerry\Documents\MangaAnka-Database-Development-Kit\export.json`

This filename is reused and may now contain different data. Check the actual work, audit, revision and packet context. A previously captured export is not proof of current live state.

## 3. Product purpose and architectural contracts

The DDK feeds popular titles through MangaAnkā's actual resolution pipeline and audits its **final logical publication**, not raw provider inventories. Hundreds of standalone chapters with zero native provider volumes are normal if references derive the final volumes correctly.

Keep these responsibilities separate:

| System | Authority |
|---|---|
| Acquisition | Provider reader IDs, page/chapter payloads, availability and transport |
| Structure | Publication identities, volumes and chapter membership |
| Artwork | Trusted compatible covers for established volumes |

A cover, bibliographic count, source number, or acquisition URL does not independently prove chapter membership.

The established automatic structural precedence is selected-provider explicit membership, unambiguous MangaDex explicit membership, validated Wikipedia explicit membership, applicable safe derivation, then unmapped. Reviewed/verified exact-compatible curation overlays effective results while preserving automatic data and contradictions.

The pipeline includes current multi-provider search; AniList/Kitsu enrichment and trusted alias retry; canonical/edition selection; ranking and inventory qualification; source resolution; reference lookup and manifest building; acquisition/publication projection; normalization and duplicate reconciliation; effective curation and freshness/release evaluation; grouped problems and four health dimensions; immutable audit persistence and exact working-set pin advancement.

The newest addition is optional, validated publisher evidence during publication resolution. See section 7. It supplements existing references; it does not replace the shared structural pipeline.

Edition identity must remain distinct: standard, official colored, fan-colored, omnibus/deluxe and incompatible structures cannot be casually merged. Aliases mentioning colored must not contaminate a standard edition. Fail closed when different works/editions remain genuinely plausible.

## 4. Current UI and workflow

The primary application now includes **Workflow**, Catalog, Audit, Problems, Curate, History, Details and Publication Map surfaces. Workflow was implemented and visually moved toward the supplied dark dashboard mockup. The old four-tab Tk layout is historical, not the current primary UI.

The production handoff loop is:

1. Intake into the exact Working Set.
2. Run the current audit pipeline.
3. Export a pinned Working Set Review Packet.
4. Investigate findings and prepare evidence-backed fixes.
5. Preview/Apply exact guarded commands where appropriate, or repair generic software defects.
6. Force Re-Audit the exact selected item after software changes.
7. Export fresh again and check actual results.
8. Explicit human acceptance only when eligible and justified.

Audit success, READY, health PASS and acceptance are different concepts. Do not accept a title just to change its status.

**Force Re-Audit Selected** targets the exact `working_set_item_uuid`, bypasses candidate reuse/selection only, runs the normal current-code pipeline, appends a new immutable audit and advances the selected pin only after successful atomic persistence. Old history/curation survive; failure preserves the old pin and remains retryable. Its earlier SQLite self-lock was already repaired. Do not reopen that task without new evidence.

Grammar 3 commands are deterministic, bounded, and guarded by database UUID, audit ID/revision and a database-wide revision token. Preview and Apply must reject stale guards. Mutating one work can stale another work's exported guard. **Never reuse an old production or disposable guard.** Export fresh rather than weakening checks. There is no new completion command, special-binding editor, or schema migration from the latest pass.

## 5. Current source/navigation map

Paths below are relative to `C:\MangaAnka DDK` unless otherwise specified.

| File | Role |
|---|---|
| `mangaanka_qt.py` | Primary source launcher |
| `mangaanka_database_development_kit.py` | Shared backend, DB/SearchAuditor and legacy Tk entry point |
| `mangaanka_search_core\__init__.py` | Live plugin-core adapter |
| `ddk_publication.py` | Shared publication orchestration and final-result diagnostics |
| `ddk_publisher_reference.py` | NEW official publisher ingestion and validated membership contract |
| `ddk_chapter_normalization.py` | Main/special/provisional/artifact normalization and effective counts |
| `ddk_duplicate_projection.py` | Equivalent acquisition-key reconciliation |
| `ddk_curated_resolution.py` / `ddk_catalog.py` | Reviewed curation and effective result |
| `ddk_working_sets.py` / `ddk_writer_lock.py` | Queue, exact membership/pins, transactions and writer protection |
| `ddk_acceptance.py` / `ddk_schema.py` | Acceptance lifecycle and schema v7 |
| `ddk_review.py` / `ddk_exports.py` | Problems, health, packets and guard metadata |
| `ddk_commands.py` / `ddk_command_controller.py` | Grammar 3 Preview/Apply |
| `qt_app\pages\workflow.py` / `qt_app\workflow_presentation.py` | Workflow page and presentation |
| `qt_app\workers.py` / `qt_app\main_window.py` | Background operations and UI actions |
| `ddk_build.py` / `MangaAnka-Database-Development-Kit.spec` | Packaging and live-core dependency handling |

Shared plugin modules include `publication_manifest.py`, `reference_integration.py`, `reference_metadata.py`, `mangadex_structure_reference.py`, `wikipedia_reference.py`, canonical/search/source modules, `publication_freshness.py` and `publication_specials.py`. Inspect actual calls and applicable `AGENTS.md`; filenames alone do not establish behavior.

## 6. Recent production history and controls to preserve

Several completed passes investigated reference integrity, provider-artifact authority, Wikipedia structural-page identity and chapter extraction, Haikyu MangaK fractions/splits and provider selection, MHA parser/residue findings, Blue Lock UNCOMPILED gating, unlinked intake identities, and BATCH 004 publication tails. These are historical completed repairs, not a new task list. Use relevant reports/current source for exact scope.

The user manually applied publisher-backed reviewed corrections in the recent workflow:

- Sakamoto Days chapter **232 → volume 26**.
- Dr. STONE chapter **206 → volume 24**.

The conversation explicitly confirmed the shared token advanced after Sakamoto. Treat the reviewed mappings as regression requirements, but obtain a fresh packet before claiming their current persisted production state. Old guard values in chat are obsolete and intentionally omitted here.

Required controls include Sakamoto's uncollected 256–277 behavior; Blue Lock scoped UNCOMPILED; MHA chapter 118 parser and unresolved supplementary rows; Haikyu CODE findings; SPY x FAMILY parsing; Chainsaw fail-closed reference conflicts; World Is Mine 163 mapped / 14 volumes; and explicit acceptance/curation race protection.

The captured Dandadan canonical-special regression remains:

- 246 main + 2 acquired recognized specials = 248 logical units.
- 219 mapped main / 221 mapped total; 27 uncompiled main; zero unmapped main; 25 released volumes.
- Provider fractions 26.5 and 193.1 unresolved; nine missing recognized specials acquisition-only.
- Health identity PASS / publication PASS / normalization REVIEW / acquisition PARTIAL.

These are captured fixture expectations, not fixed future live counts or evidence that every source behaves identically.

## 7. Latest completed task: Black Clover and publisher evidence

The user asked why Black Clover had **392 canonical main but 394 logical chapters**, and required investigation of exact MangaPill rows **0 and 393**, rather than forcing the title green. After a broad counting experiment failed existing controls and was withdrawn, the user explicitly authorized: **“Expand to publisher evidence ingestion.”** That expansion is implemented, tested and packaged.

### Captured baseline

- BATCH 004 UUID: `1b2fdd82-2bfe-4574-afab-ea4d377e4569`.
- Black Clover work 25; work UUID `f8440008-e392-4f19-932c-dc76121d00cc`.
- Item UUID: `e47a99e5-8b1a-43ec-9d5c-9ae18c4c207f`.
- Audit **48 revision 1**; canonical `anilist:86123|kitsu:27527`; MangaPill; standard/en.
- Captured export SHA-256: `90172654f1f2e731a9dc3408fa1d1b5a21b4750453f0dbc05e698a624d0baf87`.

These identify the investigated snapshot, not a newly inspected production pin.

### Exact root cause

The normalizer had **392 main + two provisional** rows, not 394 main labels. Existing effective logical coverage includes provisional rows. With only one other complete usable provider, the existing two-peer exclusion did not apply. The shared generic pre-chapter-one projection also placed provider row 0 in volume 1. Thus 394 logical candidates contributed 393 mapped / one unmapped despite two unresolved acquisition identities.

There was no publisher-backed completion authority to distinguish this completed series from ongoing works, stale references or interior gaps. A blanket rule excluding provisional rows whenever any main identity existed broke three existing controls and was fully removed. **Do not restore that rule.**

### Forensic findings

**MangaPill 393:**

`https://mangapill.com/chapters/524-10393000/black-clover-chapter-393`

Fourteen image files; first image identifies the 29th Wizard King's coronation and prints book page 303; ending explicitly calls it a special. Shueisha's Complete Grimoire TOC independently identifies the coronation manga at page 303, followed by an author message at 318. It is a **legitimate supplementary guidebook special**, not established serialized main 393 or volume-38 extra. Sampled opening/ending hashes differ from neighboring 392; no complete all-page duplicate comparison or provider upload-date proof was claimed.

Official guidebook: <https://www.shueisha.co.jp/books/items/contents.html?jdcn=08X10000000073529800>, ISBN 978-4-08-885227-0, released August 4, 2026.

**MangaPill 0:**

`https://mangapill.com/chapters/524-10000000/black-clover-chapter-0`

Fifty image files including a scanlation credit; separate story/title/ending, 49-page announcement, Asta/Yuno and the pilot's Japanese title typography. Strongly consistent with the original pilot/one-shot, but no authoritative page-by-page binding was obtained. Keep **UNRESOLVED ACQUISITION**, likely separate pilot/one-shot. Number 0 is not identity or volume-1 proof.

Official pilot notice: <https://www.shonenjump.com/j/notice/2018/05/02/20180502_bc001.html>. Official 16.5 guidebook TOC: <https://www.s-manga.net/items/contents.html?jdcn=08881551880416315501>, pilot at book page 156, ISBN 978-4-08-881551-0.

**Completion:** official MANGA Plus page showed Completed and #392, “Final Page: Beyond Not Giving Up,” April 30, 2026. Its API returned explicit COMPLETED enum **8**, final publisher chapter ID **1027803**. The API exposed only five chapter identities (1,2,3,4,392); no complete publisher list was invented.

<https://mangaplus.shueisha.co.jp/titles/100003>

Shueisha volume 38 was released August 4, 2026, ISBN 978-4-08-885136-5; its TOC includes the final installment and no linked next volume was observed. That observation does not rule out future editions.

<https://www.s-manga.net/items/contents.html?jdcn=08X10000000073438800>

### Implemented generic authority policy

`ddk_publisher_reference.py` ingests bounded official MANGA Plus public catalog/detail metadata using a small stdlib protobuf reader and anonymous web-client session header. No login, user credentials, third-party SDK, chapter downloads or new dependency. Matching requires exact compatible trusted title/alias and creator, standard edition and English. Explicit macron spelling equivalence is bounded; unrelated fuzzy matching remains prohibited.

Closure requires explicit COMPLETED enum 8, a published stable final chapter identity, freshness within 24 hours, compatible work/edition/language/provenance, final-identity corroboration by the trusted publication model, and an already explicit contiguous integer backbone through that final identity. This validates existing positive records; it does not generate chapters from a count/range. DISABLED enum 0 is deliberately not completion proof even if the website displays similar wording.

Only under validated `publisher_membership.status=closed` do unsupported provisional rows outside that main set become unclassified acquisition evidence rather than inflate logical coverage. Independently supported zeroes, specials, fractions, provider corroboration and newer main identities retain their existing paths. Independent newer main evidence disables closure and creates existing `REFERENCE_CONFLICT`; it is not discarded. Ongoing, stale, partial, ambiguous, incompatible or unavailable evidence retains conservative fallback behavior.

Shueisha official typed book search/TOCs also ingest at most two compatible guidebooks. Supplementary observations have book/ISBN/page/source identities and remain **unbound** to acquisition records. Book page 303 and guidebook label 16.5 are not canonical chapter/standard-volume assignments. No OCR, numeric alias, automatic special binding or production curation was added.

Evidence is serialized under `references.publisher_publication`; validated membership under `publisher_membership`; provenance contributes to the publication fingerprint. Supplementary lookup failure does not invalidate independent main completion proof.

### Exact changed/added files in the latest pass

- NEW `C:\MangaAnka DDK\ddk_publisher_reference.py`.
- EDIT `C:\MangaAnka DDK\ddk_publication.py`.
- EDIT `C:\MangaAnka DDK\ddk_chapter_normalization.py`.
- NEW `C:\MangaAnka DDK\tests\test_logical_membership_authority.py` — 12 tests.
- NEW `C:\MangaAnka DDK\tests\test_publisher_reference.py` — 32 tests.
- EDIT `C:\MangaAnka DDK\tests\smoke_packaged_artifact_authority.py`.
- NEW `C:\MangaAnka DDK\DDK_BLACK_CLOVER_PUBLICATION_MEMBERSHIP_VALIDATION.md`.
- Investigation captures/scripts/logs/manifest under `C:\MangaAnka DDK\build\black-clover-membership\`.
- Rebuilt primary EXE, identified below.

**Shared/plugin files changed: none.** No latest-pass changes to Qt, spec, launcher, fonts, search/provider ranking, Atsu semantics, shared structural precedence, canonical specials, freshness/released/UNCOMPILED evaluator, health derivation, curation/acceptance semantics, schema 7 or Grammar 3.

### Controlled before/after replay

This replay uses the captured selected acquisition rows/reference bundle plus separately captured official publisher observations. Peer raw chapter identities were absent from the export; their saved summaries were retained and no peer rows invented. It is not a fresh live audit.

| Metric | Before | After |
|---|---:|---:|
| Raw acquisition records | 394 | 394 |
| Canonical main | 392 | 392 |
| Logical chapters | 394 | 392 |
| Mapped logical | 393 | 392 |
| Unmapped logical | 1 | 0 |
| Uncompiled | 0 | 0 |
| Final volumes | 38 | 38 |
| Identity | PASS | PASS |
| Publication | REVIEW | PASS |
| Normalization | REVIEW | REVIEW |
| Acquisition | PASS | PASS |
| Overall | REVIEW | REVIEW |
| Problem categories | 2 | 1 |

`UNCLASSIFIED_ACQUISITION` remains for 0 and 393. `UNMAPPED_CHAPTERS` for unsupported logical 393 drops out. All 394 acquisition records/projection rows survive. The old raw row-0 derivation remains inspectable but is excluded from logical mapped coverage. No CODE finding was suppressed. **Do not describe the result as fully PASS or accepted.**

## 8. Completed validation and exact current build

Latest implementation pass results, not tests rerun for this handoff:

- Baseline: 630 existing DDK tests passed.
- New publisher/membership tests: **44 passed**.
- Existing focused DDK controls: **265 passed**, 16.249 seconds.
- Focused shared-core controls: **261 passed**, 2.184 seconds; no full plugin suite.
- Final full DDK: **674 passed**, 333.036 seconds, including **103 Qt tests**.
- Compile checks: six changed/new Python files passed.
- Frozen/package offline suites: **157 passed** (108 in 59.552 seconds + 49 in 0.791 seconds), including new tests and the exact captured Black Clover replay.
- Frozen runtime bytecode matches current source for the new adapter and checked publication/normalization/backend/catalog/curation/acceptance/Qt worker/export guard modules. No frozen shared-core snapshots or database payloads were bundled.
- Actual packaged EXE launched offscreen using explicit disposable `--database`, `--create`, `--role TEST` and isolated `--ui-settings`. Process stayed alive; new schema-v7 DB creation and read-only integrity check passed. Only the verified test process tree was stopped.
- No interactive packaged UI audit, new nine-scale visual smoke, full live corpus rerun or live Black Clover mutation was performed in this backend-only pass.

**Primary launcher:** `C:\MangaAnka DDK\Launch_MangaAnka_DDK.bat`

**Primary source:** `C:\MangaAnka DDK\mangaanka_qt.py`

**Legacy Tk launcher:** `C:\MangaAnka DDK\Launch_MangaAnka_DDK_Legacy_Tk.bat` (unchanged).

**Final EXE:** `C:\MangaAnka DDK\dist\MangaAnka-Database-Development-Kit.exe`

- Size: **52,543,473 bytes**.
- SHA-256: **`9ccc78c7dcddfd7603410b73165920ffa68a040974efb25b2662e8bef608b64e`**.
- Built successfully using existing `MangaAnka-Database-Development-Kit.spec` and `.venv-qt` PyInstaller.
- No new runtime dependency. Prior Tcl/Tk and incompatible Poppler ICU packaging protections remain in place.
- Geist remains unbundled; installed Geist/system fallbacks remain the existing policy. No font or UI change in this pass.

This build supersedes older EXE hashes/discrepancies described by the October 5 handoff. Future edits/rebuilds require fresh artifact verification; do not transfer test provenance to a different binary solely because its filename matches.

Full latest report:
`C:\MangaAnka DDK\DDK_BLACK_CLOVER_PUBLICATION_MEMBERSHIP_VALIDATION.md`

Evidence manifest (40 investigation artifacts plus source/report/EXE hashes):
`C:\MangaAnka DDK\build\black-clover-membership\evidence-manifest.json`

Useful captured outputs: `publisher-current.json`, `black-clover-entry.json`, `provider-payloads.json`, `replay-results.json`, `after-publication.json`, `final-full-ddk-tests.log`, `packaged-tests.log`, `packaged-startup-results.json` and `build.log` in that same folder. Captured publisher evidence expires for runtime closure; use current lookup for a new audit, not a timestamp-adjusted fixture.

## 9. Next action — user-operated production check only

No fresh production Black Clover result has been supplied after this build. The next useful step is:

1. Save work and restart DDK using the normal primary launcher.
2. The user selects the live catalog and exact Black Clover item in BATCH 004.
3. Run **More → Force Re-Audit Selected** and wait for success/new immutable audit/pin.
4. Export a fresh pinned Working Set Review Packet.
5. Check actual publisher lookup status `current` and membership `closed`; compare counts and retained acquisition rows against the controlled replay if current evidence still matches.
6. Keep REVIEW while acquisition bindings remain unresolved. Do not assign 393 to volume 38 or 0 to volume 1 from numbering alone. No guarded curation batch was justified, and no automatic acceptance is authorized.

If the new audit differs, inspect the fresh exact pin and publisher/reference/provenance/status first. Optional publisher failure can legitimately preserve the old provisional counts. Do not assume a new software regression or fabricate completion proof just to match the replay.

## 10. Remaining limitations / possible future work

- Current closure support is narrow: exact compatible English/standard MANGA Plus works with complete explicit integer backbones in existing trusted references. Other publishers/languages, noncontiguous numbering, missing evidence, ambiguous creators and stale/unavailable endpoints remain conservative.
- Supplementary publication identities are ingested but not automatically bound to provider acquisitions. Reliable generic binding is separate future work, not permission to guess aliases.
- The EXE consumes local plugin core; missing/incompatible local source must fail closed.
- The plugin does not automatically consume the DDK production SQLite catalog or curated patch export. Distribution/runtime catalog integration is separate work.
- A successful captured control is not proof of current live source availability, unchanged counts, or current human acceptance.
- Scope any future CODE repair to evidence. Preserve unresolved research findings where identity is not yet proven.

## 11. Relevant report index

All paths below start with `C:\MangaAnka DDK\`. Read the newest relevant report and actual source before using older history.

- `DDK_BLACK_CLOVER_PUBLICATION_MEMBERSHIP_VALIDATION.md` — latest completed pass.
- `DDK_BATCH004_HANDOFF_VALIDATION.md`, `DDK_BATCH004_PUBLICATION_VALIDATION.md` — prior BATCH 004 handoff/publication work.
- `DDK_BLACK_CLOVER_INTAKE_IDENTITY_VALIDATION.md`, `DDK_BATCH004_UNLINKED_IDENTITY_VALIDATION.md` — intake identity work.
- `DDK_MY_HERO_FORENSIC_VALIDATION.md` — MHA findings.
- `DDK_BLUE_LOCK_RESEARCH_VALIDATION.md`, `DDK_BLUE_LOCK_UNCOMPILED_GATING_VALIDATION.md` — Blue Lock boundaries.
- `DDK_REFERENCE_INTEGRITY_VALIDATION.md` — trust and reference conflicts.
- `DDK_ARTIFACT_AUTHORITY_VALIDATION.md` — provider artifact authority.
- `DDK_WIKIPEDIA_IDENTITY_VALIDATION.md`, `DDK_WIKIPEDIA_MEMBERSHIP_VALIDATION.md` — page identity/extraction.
- `DDK_WORKFLOW_UI_VALIDATION.md`, `DDK_WORKFLOW_NEXT_ACTION_VALIDATION.md` — Workflow implementation/actions.
- `DDK_FORCE_TRANSACTION_VALIDATION.md`, `DDK_FORCE_REAUDIT_VALIDATION.md` — transaction and force lifecycle.
- `DDK_CANONICAL_SPECIALS_VALIDATION.md`, `DDK_ATSU_HEALTH_VALIDATION.md`, `DDK_PUBLICATION_FRESHNESS_VALIDATION.md` — protected normalization/state contracts.
- `DDK_LIFECYCLE_V7_VALIDATION.md`, `DDK_CURATION_VALIDATION.md`, `DDK_REVIEW_VALIDATION.md`, `DDK_COMMANDS.md` — schema, acceptance and command authority.
- `DDK_QT_PROMOTION_VALIDATION.md` — historical launcher/resources/font/packaging qualification; latest binary identity is section 8 above.

A ChatGPT chat without local tools cannot read a Windows file merely because its path is listed. Ask the user to attach the relevant report, fresh export or scoped source files. Never claim to have inspected unavailable local code. Do not reconstruct missing original packets from memory.

## 12. Suggested first message for the new chat

> Read this handoff as context and wait for my next task. Local MangaAnkā/DDK worktrees are authoritative. The Black Clover publisher-ingestion repair is already implemented, tested and packaged. Do not rebuild or redo it unless new evidence requires that. Do not open my live SQLite catalog automatically, reuse stale guards, change schema 7/Grammar 3, suppress CODE findings to force PASS, or commit/push/tag/release/bump versions. Distinguish captured replay, fresh live results and historical reports. If you cannot access local paths, ask for the specific files you need. The pending check is my manual Black Clover Force Re-Audit and fresh packet; supplementary provider bindings remain unresolved.

Handoff preparation created only this document. It did not change product source, rebuild, run audits/tests, open databases, or perform production actions.
