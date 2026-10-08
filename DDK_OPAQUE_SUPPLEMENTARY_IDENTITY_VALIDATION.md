# MangaAnkā DDK: opaque supplementary identity validation

Completed against the current local DDK/shared-plugin worktrees. Version remains 0.3.0, schema remains 7 and command grammar remains 3. No production database was opened, read, copied or modified. No automatic acceptance, commit, push, tag, release, version bump, reset or worktree clean was performed.

## Delivered scope

A typed, separately projected supplementary identity/evidence model is implemented and packaged. It coexists with existing numeric canonical specials without putting opaque strings into Decimal chapter sets. Official publication identity, exact acquisition recognition and collection membership are independently validated and exported. Existing main counts, numeric special counts, health, CODE findings, curation, release evaluation and acceptance policy remain intact.

This is an operational read-only evidence layer, not an automatic binding of the seven captured research subjects. A separately authorized guarded binding mutation workflow is still required. Phase 3 expressly prohibited silently extending Grammar 3 or schema 7; that portion stops at a concrete proposal. No set type/source-note workaround or hidden chapter-volume assertion was introduced.

## Inspected call graph and architecture

SearchAuditor.audit_many → normal search/enrichment/canonical ranking/provider qualification → resolve_publication → ReferenceMetadataService → PublicationManifestBuilder → Atsu group acquisition → build_publication_projection → reconcile_duplicates → normalize_acquisition/effective_counts → shared publication-state evaluation → apply_curated → immutable audit/problem persistence and normal pin advancement.

The new collect_supplements call adds supplementary_identity immediately before the existing curation snapshot is copied. Both automatic/effective snapshots therefore retain the same independent evidence. It does not rerun structural resolution or invent a parallel search, source selection, chapter ordering or volume resolver. Numeric publication_specials.match_special and inventory_coverage remain unchanged and are still used by the real pipeline.

Types are Scope, Provenance, SupplementaryIdentity, AcquisitionBinding and CollectionMembership in ddk_supplementary.py. The versioned payload is publication_json.supplementary_identity, contract opaque-supplementary-v1. This is publication evidence in an existing publication JSON field, not unrelated-field overloading. No migration/backfill occurs. Architecture detail is in build/opaque-supplementary-identity/ARCHITECTURE.md.

## Identity and authority contracts

Identity is SHA-256 over exact canonical work, edition, publication language, publisher, immutable publisher book identifier, and publisher content ID where supplied (otherwise the exact official story heading). The opaque ID uses the supplement: namespace. TOC page numbers, provider decimals, numeric proximity, page counts and artwork never seed the ID. Capture time and payload hash remain provenance, not identity seeds. Repeated captures retain observations; conflicting same-heading locators are quarantined. Different publications/headings never merge by similarity.

Initial supported publisher authority is Shueisha official book TOCs, with exact official URL-to-ISBN/JDCN validation, compatible work/edition scope, original publication language, title/label, capture time, explicit evidence type, payload SHA-256 and locator. The bounded existing official metadata adapter is reused. Its guidebook discovery now runs independently of the main-series completion branch; an open series can have supplementary books. A strict special-one-shot TOC heading is also recognized generically. Publisher chapter-count and maximum-availability completion safeguards are unchanged.

Exact binding is a separate read-only reviewed_exact contract. It requires VERIFIED review, explicit reviewer/note, independently supplied current database UUID/audit ID/audit revision/database revision, exact provider/reader ID/original label/URL, exact edition/language, publication hash and acquisition evidence hash. Rejected proofs and raw acquisitions remain inspectable. Same-label different readers, duplicate reader matches, stale guards, insufficient proof, conflicting targets, contrary main identity and existing numeric-special authority fail closed. Multiple exact compatible readers count once per supplementary identity. A reader claiming different identities is quarantined on both sides.

No product command supplies an opaque review context, and publisher/captured research payloads cannot authorize their own VERIFIED flag. Stored evidence is revalidated when read; stale/self-declared binding claims do not become verified acquisitions. Actual current providers have no independently established publisher-to-reader identifier bridge in the supplied evidence. OCR/title-page samples alone are not promoted into complete-content equivalence. There are **zero newly verified production/captured provider bindings**.

Membership is separately typed as standard_volume, separate_publication, standalone or related_work. It must identify the same exact official story/collection evidence. Standard membership requires explicit numbered-volume provenance; a guidebook cannot become a standard volume. A related-work relationship requires a distinct canonical target ID. Membership does not prove acquisition, and acquisition does not prove membership. Japanese publication evidence does not certify English acquisition or English standard-edition membership. Applicability is explicit; Dr. STONE volume-27 observations remain Japanese-scope membership, not English numeric mappings.

## Workflow, UI and exports

Details → References includes a supplementary summary and complete raw evidence. Details → Publication and Curate → Publication Map append a separate Supplementary / separate identities group with readable story titles. Selecting a node shows acquisition, membership and scope applicability before detailed provenance. Opaque IDs remain in tooltips/raw evidence. Nodes never enter Catalog.rows or the chapter command selection; Curate clearly marks them read-only under Grammar 3. The table mode remains the existing numeric chapter editor.

Problems and Workflow Inspector expose independent supplementary summaries and full context. Existing problems are not suppressed or reclassified. Catalog context and JSON/Markdown review packets carry the versioned identities, original observations, rejected proof diagnostics, memberships and provenance. Existing persisted disposition-adjusted health remains the authoritative health field; export does not recompute a more favorable state.

No new page, layout redesign, font assets or dependency was added. Existing dark controls, readable selected text and explicit vertical/horizontal scrolling remain. Nine scale/window geometry checks and supplementary-specific Qt tests passed. Offscreen screenshots were inspected; native interactive EXE visual certification is not claimed.

## BATCH 004 before/after evidence

The controlled replay loaded original source from originals/ddk_publication.py, used identical captured acquisition/reference/curation inputs, then added scope-annotated official supplementary observations to the new model only. Across all ten, eight count fields, full numeric projection, health and problem lists remained equal. It persisted ten immutable audits in a new path-guarded schema-v7 TEST catalog, with integrity ok and zero acceptances. Export/read-back equality passed. Dr. STONE 206 → 24 and Sakamoto 232 → 26 remain effective.

| Title | Main | Logical | Mapped | Uncompiled | Unmapped | Volumes | Captured opaque identities | Verified acquired |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| My Hero Academia | 431 | 433 | 432 | 0 | 1 | 42 | 1 | 0 |
| Haikyu!! | 402 | 402 | 402 | 0 | 0 | 45 | 0 | 0 |
| Black Clover | 392 | 392 | 392 | 0 | 0 | 38 | 2 | 0 |
| Blue Lock | 364 | 364 | 354 | 10 | 0 | 40 | 0 | 0 |
| Sakamoto Days | 277 | 277 | 255 | 0 | 22 | 28 | 0 | 0 |
| Kaiju No. 8 | 129 | 129 | 129 | 0 | 0 | 16 | 0 | 0 |
| Dr. STONE | 232 | 232 | 232 | 0 | 0 | 26 | 4 | 0 |
| The Promised Neverland | 182 | 182 | 182 | 0 | 0 | 20 | 0 | 0 |
| Vinland Saga | 220 | 220 | 220 | 0 | 0 | 29 | 0 | 0 |
| Golden Kamuy | 314 | 314 | 314 | 0 | 0 | 31 | 0 | 0 |

Captured replay lacks complete raw peer inventories. Haikyu 402, Kaiju 129 and Vinland 220 occur in both controlled versions; absent peer corroboration was not fabricated. The fresh network audits below preserve the historical 408/130/223 counts.

| Fresh final-code audit | Main | Logical | Mapped | Uncompiled | Unmapped | Volumes | State |
|---|---:|---:|---:|---:|---:|---:|---|
| The Promised Neverland | 182 | 182 | 182 | 0 | 0 | 20 | READY |
| My Hero Academia | 431 | 433 | 432 | 0 | 1 | 42 | REVIEW |
| Haikyu!! | 408 | 408 | 408 | 0 | 0 | 45 | REVIEW |
| Dr. STONE | 232 | 232 | 232 | 0 | 0 | 26 | REVIEW |
| Sakamoto Days | 277 | 277 | 255 | 0 | 22 | 28 | REVIEW |
| Black Clover | 392 | 392 | 392 | 0 | 0 | 38 | REVIEW |
| Blue Lock | 364 | 364 | 354 | 10 | 0 | 40 | READY |
| Kaiju No. 8 | 130 | 130 | 130 | 0 | 0 | 16 | READY |
| Golden Kamuy | 314 | 314 | 314 | 0 | 0 | 31 | READY |
| Vinland Saga | 223 | 223 | 223 | 0 | 0 | 29 | READY |

Final-code fresh audits ran all ten actual current search/provider/reference/normalization/persistence paths in live-final-disposable, producing twelve immutable audits including both normal curated re-audits. All seven baseline count fields, whole-audit health, exact canonical identity, selected source, state and problem categories match the Phase 2 baseline. Every SQLite connection was restricted to the disposable directory. Integrity/schema/zero-acceptance checks passed. The initial sandbox-only attempts failed on blocked sockets; those failures are retained and are not counted as successful network validation. An earlier network run during implementation also matched all ten; the final-code run is the release evidence.

## Verified and unresolved subject matrix

- **Dr. STONE:** four official volume-27 story observations are represented in the controlled fixture: TERRAFORMING; 1D: FUTURE MESSAGE; 2D: FUTURE ROAD MAP; 3D: FUTURE SCIENCE. Original Japanese publication scope, exact JDCN, title, hash and TOC locators are retained. They are separate from Atsu 232.5–232.8. All four exact acquisitions remain unbound and all fractional CODE findings remain. No numeric ID, English-volume mapping or complete volume-27 structure was invented. Automatic standard-volume TOC discovery is not implemented by the existing guidebook-only adapter; these four are research fixtures, not shipped title tables.
- **My Hero Academia:** the official Ultra Age short-story heading is represented as a separate publisher book/story identity in the captured fixture. MangaPill 432 is not bound automatically. Pilot/My Hero, Team-Up Missions/What Is a Hero?, Endeavor’s Mission, Connect to the Day and A Piece of Cake remain research observations unless their own compatible authoritative identity and exact binding are supplied. The model can represent standalone/related-work relationships without inserting them into the main series, but no VIZ ingestion adapter or title-specific table was added. Preserve 431 main and Phase 2 creator equivalence. Current Shueisha search lists Ultra Age as a distinct series; the strict existing exact work selector does not infer parentage from a prefix. The generic eight-title reference cap can also hide late native-script aliases; no shared alias/search policy was broadened here.
- **Black Clover:** two publisher guidebook/pilot headings are represented. Both raw MangaPill 0 and 393 remain unclassified/unbound; neither is assigned to standard volume 1/38. Completed main boundary remains 392. Fresh automatic guidebook observation ingestion succeeds for the two exact-family guidebooks.
- **Haikyu!!:** mixed mislabeled main openings, bonuses and duplicate candidates remain unresolved. Existing 86 fractional CODE and 16 split CODE findings plus zero research are retained. No decimal-to-special rule or duplicate collapse.
- **Sakamoto Days:** provider 300/307 still lack complete exact equivalence proofs; 101 fractional CODE, 30 split CODE, zero/300/307 research and 22 unmapped tail chapters remain. The protected curated-tail authority boundary is unchanged. Preserve 232 → 26.
- **Controls:** Blue Lock retains ten UNCOMPILED main and two acquisition-only missing specials. The Promised Neverland retains acquisition-only missing extras. Kaiju, Vinland and Golden Kamuy retain their clean fresh results. Dandadan captured controls retain 246 main, two acquired numeric specials, 248 logical, 219 mapped main/221 total mapped, 27 uncompiled, zero unmapped main, 25 released volumes, unresolved 26.5/193.1 and nine acquisition-only missing specials; health PASS/PASS/REVIEW/PARTIAL.

**Verified provider bindings added: none.** Seven captured official publication observations are represented; all acquisition associations remain unresolved. Synthetic reviewed-binding positive/negative cases validate the generic contract only and are not production corrections.

## Persistence, compatibility and deferred authorization

Schema 7 is unchanged: no SQLite DDL, migration, table, pragma, writer lock or transaction-lifetime edit. Audit JSON is append-only through the existing save path. Existing audits, pins, acceptance provenance, curation evidence and revision semantics survive unchanged. Old audits without the extension render empty supplementary evidence; old raw observations missing scope/capture authority remain readable diagnostics and do not gain trust through guessed backfill.

Grammar 3 is unchanged. No new binding command, type alias or reused chapter field exists. A reviewed exact-binding mutation requires an explicit new grammar/target contract and persistent journal; the complete additive schema-8/grammar-4 proposal is build/opaque-supplementary-identity/PERSISTENCE_PROPOSAL.md. It covers tables, foreign keys, migration/rollback/idempotence, independent membership assertions, full revision guards, stale proof, undo/redo, dependencies and acceptance lifecycle. This proposal is not executed. No routine approval is needed for the delivered non-mutating functionality; enabling those mutations needs separate authorization under Phase 3’s restriction.

## Exact runtime files changed

- C:\MangaAnka DDK\ddk_exports.py
- C:\MangaAnka DDK\ddk_publication.py
- C:\MangaAnka DDK\ddk_publisher_reference.py
- C:\MangaAnka DDK\ddk_review.py
- C:\MangaAnka DDK\qt_app\models\publication.py
- C:\MangaAnka DDK\qt_app\pages\curate.py
- C:\MangaAnka DDK\qt_app\pages\details.py
- C:\MangaAnka DDK\qt_app\pages\problems.py
- C:\MangaAnka DDK\qt_app\pages\workflow.py
- C:\MangaAnka DDK\qt_app\widgets\publication_map.py

Added source/tests/fixture/report:

- C:\MangaAnka DDK\ddk_supplementary.py
- C:\MangaAnka DDK\tests\test_opaque_supplementary.py
- C:\MangaAnka DDK\tests\test_supplementary_integration.py
- C:\MangaAnka DDK\tests\test_qt_supplementary.py
- C:\MangaAnka DDK\tests\smoke_packaged_supplementary.py
- C:\MangaAnka DDK\tests\fixtures\opaque_supplementary\observations.json
- C:\MangaAnka DDK\tests\fixtures\opaque_supplementary\README.md
- C:\MangaAnka DDK\DDK_OPAQUE_SUPPLEMENTARY_IDENTITY_VALIDATION.md

Rebuilt C:\MangaAnka DDK\dist\MangaAnka-Database-Development-Kit.exe. Investigation scripts, design/proposal, originals/diff, official captures, logs, screenshots, two successful network audit catalogs and controlled replay catalogs are under build/opaque-supplementary-identity. The evidence manifest hashes the final files. DDK is not a Git repository; local originals/diffs establish the source delta. Shared-plugin files changed: **none**. Plugin status before/after is unchanged. No normalization, source adapter/ranking, health derivation, release/UNCOMPILED policy, acceptance, schema, command parser, Qt theme/font, launcher, spec or version file was edited.

## Tests and package validation

- New focused model/persistence/Qt suite: **41 passed** in 2.337 seconds.
- Final full DDK suite: **776 passed** in 372.135 seconds.
- Publisher creator/completion/protocol controls: **69 passed** in 0.894 seconds.
- Focused shared manifest/specials/freshness/reference/MangaK controls: **112 passed** in 2.053 seconds. No full plugin repository suite.
- Frozen packaged suite: **199 passed** in 45.875 seconds. Nineteen embedded DDK/Qt modules compare exactly with current source code objects. No shared-core snapshot is bundled.
- Syntax compilation passed for every changed/new runtime and test/smoke Python file. Runtime unified diff inspected.
- All nine final geometry/scale smokes passed: 1120×720, 1440×900, 1920×1080 at 1, 1.25, 1.5; all seven pages and reachable Workflow actions. Offscreen supplementary screenshots inspected: readable story titles/states and visible scrolling. No native interactive/DPI certification claim.
- Ten controlled title replays persisted/exported/read back successfully; final fresh disposable audits passed all ten exact baseline comparisons, twelve audits, schema 7, integrity ok, zero acceptances.
- Actual rebuilt EXE startup passed with explicit disposable --database/--create/--role TEST/--ui-settings, process alive, schema 7 and integrity ok. Only its verified test process tree was stopped. This is not an interactive production binding or acceptance test.

Initial missing-feature tests failed because ddk_supplementary did not exist; positive/negative fixture and stored-membership checks were repaired during implementation. Earlier complete suites passed before the last safeguards; the final result above is from finished source. Initial blocked-socket audits remain separately labeled. No failed/incomplete run is counted as a passing release check.

## Package and launchers

Primary launcher: C:\MangaAnka DDK\Launch_MangaAnka_DDK.bat (unchanged).
Legacy Tk launcher: C:\MangaAnka DDK\Launch_MangaAnka_DDK_Legacy_Tk.bat (unchanged).
Legacy Tk source remains compatible and untouched; a native Tk GUI smoke was not repeated for this Qt/evidence pass.
PyInstaller spec/dependency/font configuration remains unchanged; static imports collect the new model automatically. Existing Geist/installed/fallback font selection is unchanged; no font asset was added.
The initial sandbox build could not access the installed Tcl/Tk runtime and stopped at the existing spec guard. Rebuilding with runtime access succeeded; the guard and packaging configuration were preserved.
Final EXE: C:\MangaAnka DDK\dist\MangaAnka-Database-Development-Kit.exe.
Size: 52,558,610 bytes. SHA-256: `cb847f59a5c73e82920221ccbe7a9ccb38b7a4be4a0cfc9982291b5e7cce2058`.

## Known limitations

This stage intentionally keeps numeric publication/health and opaque evidence projections independent. Recognized opaque stories do not close numeric gaps, discharge CODE findings, change released-volume counts or make a title acceptable. Persistent exact-binding commands and downstream Calibre opaque-consumer integration are not implemented. No complete scan equivalence, image matching or OCR pipeline was added. Live provider metadata can remain mislabeled behind correctly shaped reader identifiers.

Automatic publisher collection remains bounded to the existing exact-family guidebook search, two books, strict supported headings and existing trusted identity guards. Standard-volume supplementary ingestion, native alias discovery beyond the generic cap, publisher parent-work relationships, VIZ evidence adapters and translation/edition equivalence need explicit compatible sources. The four Dr. STONE and one MHA research fixtures are not secretly loaded as production overrides. Stable title fallback can change identity if an official heading changes; no unproven cross-publication equivalence is inferred.

## Manual production verification

1. Close/restart through the primary launcher, then choose your live catalog yourself. Nothing in this validation opened it.
2. Force Re-Audit Black Clover and export a fresh pinned packet. Confirm 392 main; raw 0/393 and REVIEW remain. Details → References/Publication should show the two separately identified Japanese guidebook/pilot observations when current publisher responses supply them, with unresolved acquisition bindings.
3. Select an opaque node in Curate Publication Map. Its story title, membership and applicability are visible. It is read-only; it must not select a numbered chapter or enable a fabricated Grammar 3 binding.
4. Re-audit/export MHA and Dr. STONE if desired: main remains 431/232, existing CODE and missing-structure findings remain, Dr. STONE 206 → 24 survives. Do not expect fixture-only observations to appear automatically without compatible runtime publisher discovery.
5. Confirm Sakamoto 232 → 26 and its unresolved tail/CODE remain, and Dandadan numeric-special counts remain unchanged when equivalent current evidence is available. Use fresh guards after mutations. Accept only through the existing guarded workflow when independently satisfied; no automatic acceptance or correction batch is provided.
