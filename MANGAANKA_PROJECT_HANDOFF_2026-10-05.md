# MangaAnkā project context and development handoff

Prepared: October 5, 2026. Environment: Windows, PowerShell, America/Chicago.

This file is intended to be uploaded to a new ChatGPT conversation. It summarizes the current MangaAnkā / MangaAnkā Database Development Kit project, completed development, architectural contracts, validation evidence, known limitations, and the last unresolved manual checks. It is context, not an instruction to repeat completed implementation or start an unrequested repair.

The current local files are authoritative. Historical reports describe their own development passes; their old version/build/test statements must not override newer source or newer evidence. This is a consolidated handoff, not a verbatim transcript. Unavailable original exports and the contents of unseen historical attachments have not been reconstructed.

## 1. Immediate orientation

There are TWO separate programs:

| Program | Local worktree | Current identity |
|---|---|---|
| MangaAnkā Database Development Kit (DDK) | C:\MangaAnka DDK | Standalone audit, review, curation, and catalog tool; v0.3.0; SQLite schema 7; command Grammar 3 |
| MangaAnkā Calibre plugin / shared core | C:\MangaNana-Dev\MangaNana-calibre | Current source version 0.14.0-dev, codename Judgement; legacy Python/package/display names still include MangaNana |

The DDK's primary frontend is now Qt Widgets / PySide6. Tk remains the Legacy / Recovery frontend. The original four-tab Tk interface is historical; do not recreate it as the current primary application.

The plugin's currently inspected Git branch is feature/judgement-ui-overhaul. It has substantial existing modified and untracked development work. Those changes belong to earlier work and must be preserved. A whole-worktree diff is not the change list for the latest DDK repair. The DDK's reports indicate it is not itself a Git checkout.

The latest development repair is COMPLETE in source: Force Re-Audit Selected's SQLite self-lock. The latest local report records full tests, packaging, and two native disposable Force Re-Audits passing. A new context-only inspection also confirmed that the EXE currently on disk embeds matching code for 13 important current source modules. There is a build-hash discrepancy between the on-disk EXE and the latest historical validation report; see section 14. Do not silently erase that distinction.

No post-repair live Dandadan retest has been supplied in the visible conversation. Do not assume the user's production catalog has been successfully reaudited.

## 2. What the DDK is for

The DDK is a development/audit harness around the CURRENT MangaAnkā implementation. Its purpose is to feed popular manga titles through real search and resolution, inspect the final logical publication, isolate concrete failures, and preserve evidence for reliable patches and catalog curation.

It must not independently reinvent:

- Search ranking or source selection.
- Canonical work identity or edition classification.
- MangaDex structural references or Wikipedia structure.
- Publication manifests or chapter-to-volume projection.
- Shared publication freshness / released-volume / special taxonomy policy.

The useful output is concise: a correct title can PASS; another can have WRONG_EDITION_MATCH, a grouped UNMAPPED_CHAPTERS finding, or incomplete reference structure. It should not produce hundreds of repetitive per-chapter issue rows.

The original defect was auditing raw provider inventory too early. A provider supplying hundreds of standalone chapters and ZERO native volumes is normal. The reference layer may derive every volume successfully. Native provider volume count is not final logical volume count and is not inherently a hole.

Raw provider data remains important diagnostic evidence in Details. It must not replace the final publication model as the audit's subject.

## 3. Standing constraints and working style

LOCAL WORKTREES ARE THE SOURCE OF TRUTH.

Inspect actual files and the real call graph before editing. Do not reconstruct current behavior from GitHub, assume old reports describe current code exactly, replace working code on speculation, or redo completed work.

Default development scope is narrow and evidence driven:

- Prefer DDK adaptations over large Calibre-plugin refactors.
- Change shared plugin code only for a concrete identified defect or explicitly authorized shared correction. Document the defect and scope first.
- Preserve unrelated modified/untracked files and existing user data.
- No title-specific runtime hacks for Berserk, Dandadan, the regression corpus, or any other title.
- No broad fuzzy identity matching or invented chapter/volume boundaries.
- No commit, push, tag, release, version bump, worktree reset/clean, or broad reformatting unless the user explicitly changes those instructions.
- Do not run the entire MangaAnkā plugin test suite during these targeted passes. Use relevant focused plugin tests; run the full DDK suite when appropriate to an implementation repair.
- Use deterministic offline/fake-network fixtures and disposable schema-v7 catalogs for automated development.
- Preserve dark controls, readable light text, selected-row and readonly-combobox contrast, visible functioning scrollbars, and scrollable long Details. No unrelated UI redesign.
- Long provider/reference/output work belongs off the GUI thread.
- Report the actual checks performed. Do not describe a skipped test, missing dependency, cancelled confirmation, source-only smoke, or frozen-module test as a native end-to-end success.

The last SQLite task explicitly prohibited changes to canonical specials, Dandadan normalization, publication freshness, released-volume logic, UNCOMPILED, provider ranking, Atsu groups, health derivation, acceptance/curation semantics, schema v7, and Grammar 3. Its implementation respected that scope. These are established contracts to preserve unless a later request specifically authorizes changing one.

## 4. Production data safety

Protected live catalog:

    C:\Users\Jerry\Documents\MangaAnka-Database-Development-Kit\mangaanka_catalog.db

DO NOT OPEN OR MUTATE THIS DATABASE DURING AUTOMATED DEVELOPMENT OR VALIDATION. Use disposable databases only. Do not delete the user's failed intake records. Do not automatically run a live migration, force audit, acceptance, curation, maintenance deletion, or cache purge.

The user explicitly chooses and operates the live database for manual checks. The Qt normal launcher asks for a database rather than silently opening production. UI settings are layout settings, not authority to select or alter a catalog.

Historical nuance: some October 2 systemic/packet reports describe earlier immutable/read-only catalog inspection. That is history, not current authorization. Later tasks, including the latest repair and this handoff, did not open the production catalog.

Last user-reported live Dandadan state:

| Field | Reported value |
|---|---|
| Work ID | 10 |
| Working-set item UUID | 465c6205-b25e-4a01-b0ab-057d184fae68 |
| Pin | Audit 20, revision 5 |
| Failure | Force Re-Audit Selected failed twice with database is locked |
| Latest failed intake ID | 8 |
| Partial audit | No partial Audit 21 existed |
| Preservation | Old audit, pin, and history remained intact; failure record persisted |

Those values are user-reported starting context, not a fresh inspection of the live file. They may change through subsequent user actions.

User-provided export path:

    C:\Users\Jerry\Documents\MangaAnka-Database-Development-Kit\export.md

It is not guaranteed to contain a particular audit or both conflicting historical health exports. Audit 20's exact serialized record was unavailable during the canonical-special repair. Two conflicting Audit 19 revision 4 outputs were pasted elsewhere and were not available as two known local files. Never recreate either original export from memory.

Calibre development safety paths, from plugin AGENTS.md:

    C:\MangaNana-Dev\Test-Library
    C:\MangaNana-Dev\Test-Downloads
    C:\MangaNana-Dev\Test-Data

Never substitute the user's normal Calibre library. Read the current AGENTS.md before plugin work. The existing Choose Manga → Download Settings / customization → Review/finalization flow and cancellation/import behavior must survive.

## 5. Core architecture and real reuse boundary

Three distinct systems must stay distinct:

| System | Responsibility |
|---|---|
| ACQUISITION | Provider pages, reader IDs, chapter records, native packages, transport/fallback |
| STRUCTURE | Which volumes exist and explicit/safely derived chapter membership |
| ARTWORK | Trusted edition-compatible cover for an established volume |

A bibliographic volume or cover cannot fabricate chapter membership or an acquisition URL. A source-number alias cannot replace the real reader ID. Artwork must not create new structural volumes.

Automatic structural precedence remains:

1. Selected-provider explicit volume membership.
2. Unambiguous MangaDex explicit chapter → volume metadata.
3. Validated Wikipedia explicit chapter → volume metadata.
4. Existing safe derivation rules where their evidence requirements hold.
5. Unmapped.

In the DDK's effective curated result, reviewed/verified exact-compatible curated fields overlay that automatic model. The automatic model and original contradictions remain preserved independently. This is an explicit authority layer, not a change to provider acquisition.

The DDK's real pipeline is broadly:

    Input query / edition / language / workflow
      → current MangaDex, MangaPill, WeebCentral, MangaK, Atsu search
      → AniList / Kitsu enrichment and trusted alias retry where applicable
      → effective_search_rows / canonical identity grouping / relevance ranking
      → provider inventory qualification / current source resolution
      → trusted canonical publication context
      → reference service and publication manifest
      → MangaDex structure / validated Wikipedia / applicable existing references
      → acquisition/publication projection and unified-volume planning
      → DDK normalization, equivalent-duplicate reconciliation, effective curation
      → shared freshness/release/special diagnostics and final logical inventory
      → aggregate problems / health / immutable audit persistence / exact set pin

This is an architectural outline. Use the current functions for exact order and conditional paths.

The publication adapter follows the relevant plugin main.py path: ReferenceLookupWorker / reference lookup, reference-ready handling, publication-manifest projection, and unified-volume-plan refresh. It calls shared functions including:

- canonical_family_publication_context, canonical_reference_alias, trusted_alias_for_query.
- ReferenceMetadataService.lookup with current structure/artwork/publication adapters and existing optional-source availability rules.
- PublicationManifestBuilder's provider, MADB, MangaDex, Wikipedia, reference artwork, and enrichment applications.
- build_publication_projection and build_unified_volume_plan.
- Guarded Chapter-mode fallback_plan.items preserving original acquisition provenance.
- Current publication_freshness and publication_specials helpers rather than a divergent second implementation.

Reference services can include MangaDex, Wikipedia, BOOK☆WALKER, MADB, and existing Google Books rules. Their individual responsibilities differ. Enrichment counts and bibliographic totals are diagnostics, not proof of chapter membership.

Live-core import adapter:

    C:\MangaAnka DDK\mangaanka_search_core\__init__.py

It resolves MANGAANKA_PLUGIN_PATH, defaulting to the plugin path above; points package imports at that worktree; does not execute the Calibre-importing plugin __init__; gives live source precedence; refuses missing worktree/modules; and suppresses bytecode writes into the plugin worktree. Old snapshot files still present under mangaanka_search_core must not be mistaken for the active source. The EXE packages the loader and dependencies but excludes frozen mangaanka_search_core submodules.

Restart after shared source changes; rebuild when packaged DDK source or required dependencies change. The standalone EXE requires the current local plugin worktree even though it does not require an installed Python runtime.

Known parity boundary: ddk_duplicate_projection.py is a DDK-specific reconciliation adapter for equivalent repeated acquisition keys. The historical packet report says the base plugin still marked those keys ambiguous. Do not assume this adapter was promoted to the plugin; inspect current shared code before any separate parity correction.

## 6. Current source map

Paths in this table are relative to C:\MangaAnka DDK.

| File / directory | Role |
|---|---|
| mangaanka_qt.py | Primary source entry point |
| mangaanka_database_development_kit.py | DB, SearchAuditor, shared backend and original Tk App entry point |
| mangaanka_search_core\__init__.py | Read-only live shared-core loader |
| ddk_publication.py | Narrow shared publication orchestration and final-result diagnostics |
| ddk_chapter_normalization.py | Canonical main / special / duplicate / artifact classifications with retained provenance |
| ddk_duplicate_projection.py | Equivalent-duplicate projection reconciliation without deleting source rows |
| ddk_publication_states.py | Compatibility imports from shared publication freshness/state evaluator |
| ddk_catalog.py | Exact curated identity/fields, effective rows, validation, journal, previews, undo/redo, export |
| ddk_curated_resolution.py | Scoped reviewed curation overlay around shared manifests/projection |
| ddk_working_sets.py | Exact intake memberships, queue/run/recovery, immutable audit persistence and pinning |
| ddk_acceptance.py | Central human-approval eligibility, provenance, CURRENT/STALE lifecycle evaluation |
| ddk_schema.py | Schema-v7 migration and constraints |
| ddk_workspace.py | Database validation/activation and saved active path |
| ddk_review.py | Problem policy, four health dimensions, Review Packets, Grammar version |
| ddk_exports.py | Read-only sharing contexts/CSV/packet count and persisted-health presentation |
| ddk_commands.py / ddk_command_controller.py | Deterministic bounded grammar, guarded Preview/Apply |
| ddk_editor.py | Legacy editor/forms/console |
| ddk_catalog_maintenance.py | Guarded permanent work deletion with impact preview and backup |
| ddk_writer_lock.py | Existing OS writable-instance lock |
| ddk_build.py | Live-core dependency analysis, intentional Qt assets, Windows ICU filtering |
| qt_app\app.py / session.py | Startup, session ownership, DB switching, UI settings |
| qt_app\main_window.py / workers.py | Actions, async audit dispatch, progress/cancellation/refresh |
| qt_app\pages\ | Catalog, Audit, Problems, Curate, History, Details |
| qt_app\widgets\publication_map.py | Shared chapter/volume map including uncompiled and provider-only groups |
| qt_app\widgets\command_drawer.py | Shared command console UI |
| qt_app\theme.py / icons.py | Dark theme, font fallbacks, original SVG resources |
| tests\ | Disposable deterministic backend/Qt/Tk/packaged regression fixtures and smokes |

Important shared files under C:\MangaNana-Dev\MangaNana-calibre include canonical_identity.py, enrichment_matching.py, search_ranking.py, search_resolution.py, inventory_comparison.py, source_coordinator.py, provider source adapters, reference_integration.py, reference_metadata.py, publication_manifest.py, mangadex_structure_reference.py, mangadex_artwork_reference.py, wikipedia_reference.py, bookwalker_reference.py, publication_freshness.py, publication_specials.py, atsu_acquisition.py, unified_volume.py, and main.py.

The plugin also has processing/output work: image_processing.py, processing_presets.py, page_framing.py, output_series_metadata.py, finalization_covers.py, book_export.py, import_workers.py, import_workflow.py, window_geometry.py, and shared Qt theme/widgets. Do not alter those to fix a DDK database problem.

## 7. Completed development history — do not redo

These are implemented passes, not a new task list. Older reports may say their EXE was not rebuilt; later packaging supersedes that statement for current source.

### Final publication integration

The DDK stopped classifying provider inventory as if it were final structure and began invoking the current reference/manifest/projection/unified-plan stages. Audit metrics include final logical chapters, final volumes, mapped/unmapped units, edition, source, aggregate holes, final state, and run status. Provider inventories remain inspectable.

Raw warnings removed/demoted include zero native volumes, provider-only reported gaps/disagreements, optional source-access warnings, and conflicting enrichment totals used as unsupported expectations. Important final categories include NO_CANONICAL_RESULT, NO_USABLE_PROVIDER, WRONG_EDITION_MATCH, UNMAPPED_CHAPTERS, REFERENCE_CONFLICT, SOURCE_FAILURE, CHAPTER_COUNT_DISAGREEMENT, MISSING_REFERENCE_STRUCTURE, and AUDIT_ERROR where applicable. Use actual code terminology; the user's original illustrative list was not a requirement to implement every suggested enum.

Legacy audits lacking new evidence show RERUN REQUIRED / unknown metrics rather than fabricated zeros or PASS. A rerun appends a new audit instead of changing the old snapshot.

### Discovery and normalization

The adapter now runs effective_search_rows after enrichment. A formerly missed high-confidence canonical discovery step prevented MangaDex references for The World Is Mine; the discovery path and fail-closed path gained tests. A later live audit in a temporary database reported 163 canonical chapters, 14 final volumes, 163 mapped, no holes.

Main chapter identity is supported by compatible chapter-level structure, validated peer evidence, or safe provider-explicit membership. Equivalent releases count once for canonical coverage while all acquisition records survive. Unsupported rows remain provisional/unclassified or conservative artifact candidates. Reported counts do not select individual chapters.

Curated-created publication records can exist without acquisition; that absence is diagnosed separately and never generates pages/URLs.

### Curated editing, commands, review, and count cleanup

Automatic, curated, and effective values are distinct. UNVERIFIED changes are drafts; REVIEWED/VERIFIED exact-compatible fields affect effective resolution. Preview/Apply is atomic, stale guarded, persistent, and undoable per work. History, provenance, source notes, and zero-to-many assertion evidence survive reruns.

Review Packets have stable IDs, audit revision, database UUID/revision guard, schema/grammar metadata, four health dimensions, source and publication evidence, existing curation, and re-audit diffs. Markdown/JSON and detailed issue CSV retain exact affected identifiers. Clean PASS works can be compactly listed instead of exporting every chapter.

Equivalent duplicate provider rows can retain an unambiguous trusted membership; contradictory explicit memberships still conflict. Range bundles, split candidates, fractional candidates, and genuinely unclassified records are separate. Top-level findings group patterns/categories and keep member detail in evidence. CODE_REVIEW_REQUIRED means investigation destination, not proof of a software defect.

An evidence-grounded Ignore with Reason disposition is available only for eligible acquisition problems on trusted edition-safe identity, with REVIEWED/VERIFIED state and an append-only journal. It does not dismiss identity or publication failures. Exact signatures can carry dispositions across reruns; Show ignored and Reopen preserve reversals.

### Systemic canonical identity correction

An approved shared enrichment correction prevents collecting multiple HIGH external identities into one compound canonical work merely because provider aliases overlap. Alias-only textual matches are demoted; explicit standard/colored contradictions reject; at most one selected identity per external service is allowed. A direct external ID or unique independently corroborated cross-service match can resolve conflicts. Title overlap alone is insufficient. Ambiguous families get no trusted canonical ID or inherited creator/volume facts.

The DDK now records the actually inspected selected provider result title/reference, rather than reporting the first search result from that provider. A final selected-row edition guard uses that row's own title, badge, color flag, and explicit edition. An alias containing colored does not classify the primary standard edition as colored.

Historical Berserk result: a plain standard request selected Berserk (Fan Colored), MangaK, four chapters. This is a regression/edition-identity case, not permission for a Berserk string special case. General identity/ranking/guard tests exist; a fresh live standard Berserk success has not been established by this handoff.

### Catalog lifecycle, Working Sets, schema v7, and maintenance

Persistent edition/language work UUIDs, conceptual-work grouping, exact intake UUIDs, pinned audit revisions, curation/evidence, acceptance history, guarded set states, duplicate intake handling, race protection, and scoped exports were implemented. See section 8 for current semantics.

Permanent Catalog Work deletion is a distinct guarded maintenance feature, not normal Remove Selected from Working Set. It previews exact impact and work UUID, warns for accepted/curated works, requires typed DELETE, makes a fresh backup, and deletes owned rows atomically. Affected intake/observations remain and become REVIEW with work/pin links cleared; siblings/unrelated works remain. Recovery is backup restoration, not normal Undo. Never invoke it automatically for cleanup.

### Qt migration and promotion

Qt is primary; legacy Tk remains. Six pages, independent visible scope selectors, collapsible inspectors, Publication Map, command drawer, async audit worker, explicit database chooser, QSettings layout persistence, and existing writer-lock behavior were exercised.

Minor polish already finished: context-specific feedback, quieter secondary toolbar actions, Review/Retry actions, clearer problem/history filters, scope placement, compact scrollable Details tabs, empty-state inspector styling, and explicit selection clearing when switching to an empty Catalog set. Preserve these.

Packaging fixes already finished: shared backend's required Tk runtime is retained; incompatible Poppler ICU DLLs are filtered; Qt platform resources are collected; live-core snapshots are excluded. Geist Sans/Mono are supported but no font files are bundled. Installed Geist → Segoe UI Variable/Segoe UI → installed monospace/Qt/system fallbacks remain.

### Serialized / UNCOMPILED publication repair

An independently proven currently serialized tail can be UNCOMPILED rather than an unexplained unmapped hole. It stays a logical/main chapter without a guessed future volume. Internal gaps, lost known mappings, uncertain release boundaries, unsupported fractions, wrong identities, stale/failed references, and conflicts remain reviewable.

Publication Map has a neutral Uncompiled / Serialized chapters group; provider-only artifacts are separate. Central acceptance revalidates evidence rather than trusting stored counts/markers. Missing typed specials are acquisition-only; acquisition PARTIAL can coexist with publication PASS.

### Force Re-Audit Selected

The Qt Catalog More action queues one exact stable selected membership and calls the existing normal worker/auditor. It bypasses candidate reuse selection only. It preserves old immutable audits, curation/evidence, acceptance history, and old pins until success. It does not purge caches, force network requests, or introduce another search pipeline. See section 8.

### Shared publication freshness / release repair

The DDK-only publication-state policy was moved into shared publication_freshness.py, with the DDK compatibility module importing it. The plugin gets real trusted publication context through its existing manifest path. Wikipedia/BOOK☆WALKER provide optional positive release evidence; planned/listed/future volumes do not count as released or invent memberships. Bibliography and chapter structure remain separate.

Reviewed fields anchor only their exact scope; safe new live structure outside that scope can extend the effective model. Freshness diagnostics are CURRENT, EXTENSION_AVAILABLE, SOURCE_CHANGED, or CONFLICT_REVIEW, with fingerprints/provenance. They are not new acceptance/lifecycle states.

Sparse corrections do not imply complete coverage through their maximum chapter/volume. A tested explicit runtime complete_publication_snapshot contract can support extension, but schema v7 / Grammar 3 have NO persistent complete-coverage declaration feature. Never silently attach that contract to existing records.

Existing TTLs remain: inventories 3 hours; query snapshots 24 hours; metrics/provider mappings 7 days; external identity/reference structure/reference catalog 30 days. Normal outer refresh now clears adapter-local temporary caches to avoid reusing old bytes indefinitely. Wikipedia parser version became 6. Ordinary caching may still delay discovery until expiry/invalidation.

Important unfinished integration: the plugin has NO implemented loader consuming the DDK SQLite catalog automatically. Shared runtime patch/curation protection is not a catalog distribution/import system. Curated patch export is a future boundary, not proof that Calibre already consumes produced catalog data.

### Atsu multi-group and health consistency repair

Atsu's captured Dandadan feed contained Alpha 248 and Delta 233 acquisitions, 481 raw total. The stateless Recommended policy uses the first compatible API scanlator (captured Alpha), retaining alternate groups and actual reader IDs as evidence. Alternates do not expand canonical coverage by default. Group selection precedes volume filtering. Guarded fallback can recover real alternates only with independent compatible evidence. Unknown/incomplete/conflicting cases stay conservative. Cache inventory contract: atsu-groups-v1.

Delta-only 19.5, 89.1, 92.5 explain All-versus-Recommended differences; group membership does not prove their content invalid or special. The three can be retained noncanonical alternatives under the validated primary-backbone guards. No hidden/deleted status was observed or invented.

The health bug was recomputing whole-audit health from a selected subset of problem rows. For the same audit, an acquisition-only selection could show normalization PASS; a fraction-only selection could show acquisition PASS. Deterministic fixtures reproduced it without the original two serialized exports. Presentation now reads persisted whole-audit, disposition-adjusted search_audits.health_json. Filtering affects problem detail, not the health tuple. health_basis is persisted_disposition_adjusted_audit.

### Canonical fractional-special repair

Shared publication_specials.py retains explicit trusted type/title evidence in manifests/projections and separates main chapters, acquired recognized specials, and unresolved provider artifacts. Bounded MangaDex fractional metadata supplements aggregate mappings; taxonomy requires scoped compatible evidence and conservative category headings. Incidental extra/bonus words do not establish type.

Explicit alternate numbering requires exact source, acquisition record ID, and original identifier in trusted special aliases. No decimal-neighbor inference or Dandadan-specific alias was added. Actual download IDs and _acquisition_chapter survive canonical labeling. A special without explicit safe membership does not inherit its integer parent's volume.

Shared inventory comparisons and primary tie-breakers prefer supported main coverage, then independently recognized specials where applicable. Extra unsupported raw rows do not purchase coverage. Explicit native volume-local numbering restarts are preserved. Missing typed specials are one MISSING_SPECIAL_ACQUISITION category.

MangaDex metadata is bounded to at most one chapter metadata request for at most 100 fractional release IDs from the same work's aggregate; total resolver bound is three title searches + aggregate + optional metadata. Metadata failure leaves usable structure intact. Old untyped caches refresh through the mangadex-specials-v1 marker.

### SQLite Force Re-Audit self-lock repair

The source repair and latest reported full/package validation are complete. Its proven root cause and exact changes are in section 12. It did not alter the preceding canonical-special, freshness, provider, health, or acceptance policies.

## 8. Catalog, Working Set, acceptance, and curation contracts

The identifiers mean different things:

- work_uuid: one exact edition/language catalog work and acquisition/lifecycle target.
- conceptual_work_uuid: reviewed grouping of underlying work concepts; not permission to merge editions, providers, or publication structure.
- working_set_item_uuid: exact intake membership, its original query, status, and pinned evidence.
- audit ID/revision: newly persisted audit snapshot; an older audit is not relabeled as a fresh result.
- curation revision: version of scoped human assertions/evidence used by a computation.

Schema-v7 canonical uniqueness is nonempty canonical ID + edition + language; displayed title is not unique. Distinct same-title identities may coexist. Trusted aliases resolving to the same work within one set produce a primary membership plus terminal DUPLICATE with retained intake provenance, not another publication audit/pin. The same global work can appear in different sets.

Set states: OPEN allows membership edits and workflow; REVIEW freezes membership additions/removals but permits review workflow; COMPLETE and ARCHIVED protect mutations/pins until explicit Reopen for Review. COMPLETE requires a nonempty set whose nonremoved items are ACCEPTED, REJECTED, or DUPLICATE. Reopening preserves IDs, pins, history, and decisions; no automatic audit occurs merely from reopening.

Run Working Set is sequential at title level. It handles pending/queued/interrupted items and stale pins, and completes applicable legacy workflow states. It skips terminal decisions, current READY items, and human REVIEW cases. ERROR requires explicit Retry Errors. Interrupted AUDITING becomes QUEUED once on recovery with its old pin preserved; protected sets are not rewritten.

Force Re-Audit Selected requires exactly one stable membership in the visible active unprotected Working Set. It is not a global work-ID action. Allowed stable states include REVIEW, READY, ACCEPTED, REJECTED, ERROR. PENDING/QUEUED/AUDITING/DUPLICATE, removed/missing items, multiple/no selections, inactive or protected sets reject. Duplicate confirmation/queue/busy starts are guarded. A successful force reports New 1 / Reused 0 meaning a new AUDIT, not a new catalog work.

Success atomically persists audit/problems/evidence and advances that exact membership's pin. Another membership's pin stays fixed. Failure leaves the previous pin, records an observation/error, and permits retry. Cancellation/requeue and curation-race guards remain. Do not delete/re-intake to force a fresh result.

Set Catalog/Problems/Details and default set exports use PINNED evidence. All Catalog uses latest global evidence. A newer audit elsewhere can supersede a set's pin without replacing it. Missing pins do not substitute global evidence. Curate explicitly edits latest SHARED catalog state; it is not editing an immutable historical pin.

Apply/Undo/Redo and reviewed structure sharing through the active set queue an audit only for the affected membership. Busy work defers affected audits. Committed curation survives failed audits. Explicit global curation does not advance archived/other set pins.

Audit computations capture exact curation/identity and used structure-source dependencies before reference computation. Persistence rechecks them; changes discard/requeue stale results rather than stamping them with a newer revision. One immediate retry is permitted; continuing change leaves QUEUED. Unrelated work changes do not invalidate the target.

Acceptance is EXPLICIT HUMAN APPROVAL. PASS, READY, clean mapping, or Force Re-Audit never auto-accepts.

Accept Selected targets exact item UUIDs in a set or exact work IDs in a global view. Accept All Safe previews READY candidates, then reevaluates transactionally against a fingerprint. Identity/publication safety, current exact audit/curation, real structure, edition/language compatibility, no fatal failures, no canonical unmapped/conflicts, no curated validation errors, and no unresolved blocking findings are required. Raw unclassified acquisition cannot bypass the evaluator merely because a problem row is missing. Valid grounded dispositions can resolve eligible blockers. Normalization REVIEW and acquisition PARTIAL alone can be warnings; unresolved CODE/UNKNOWN/RESEARCH/DATA/IDENTITY problems still block as applicable.

Acceptance provenance pins exact audit/revision, curation revision, and state fingerprint. New audits or effective curation make prior approval STALE even when the new audit is clean. Accepted Master Catalog includes only CURRENT approvals. Legacy ACCEPTED lifecycle rows without v7 provenance remain LEGACY_REVIEW_REQUIRED until explicit reevaluation. No automatic reconstruction or reapproval.

Curation is granular and edition/work/language/context guarded. Reviewed values override only their scope; UNVERIFIED is draft. Conflicting live overlap remains visible and does not erase a reviewed value. Evidence records are zero-to-many per assertion with source, URL when available, access date, note, verification, and assertion revision. Preview/Apply, Undo/Redo, and History Revert preserve journaling. Missing acquisition cannot be repaired by inventing page-bearing records.

## 9. Health, counts, holes, and provenance

Four separate health dimensions:

| Dimension | Question |
|---|---|
| Identity | Is this the trusted intended work/edition? |
| Publication | Is the current released structure and supported serialized tail sound? |
| Normalization | Are provider records classified/reconciled safely? |
| Acquisition | Can the selected/fallback source supply the expected supported units? |

Publication PASS can coexist with acquisition PARTIAL and normalization REVIEW. Overall PASS is stricter. Read the selected audit's persisted complete health; never derive health from currently selected problems or silently combine different audit/pin/disposition revisions.

Counts must distinguish raw acquisition rows, supported canonical MAIN chapters, acquired recognized specials, included logical units, duplicates, classified provider artifacts, truly unclassified records, mapped main, mapped total, supported uncompiled main, unmapped main, and released final volumes. Legacy context field canonical_chapters keeps its logical-count meaning for compatibility; explicit canonical_main_chapters/mapped_main_chapters remove ambiguity. Do not rename old semantics implicitly or backfill unknown historic values.

Provider artifact classifications include range bundles, split/fractional candidates, unresolved group candidates, and unclassified acquisition. They are not automatically canonical main chapters or special acquisitions. Report one category with affected count and retain original numeric labels, provider IDs, group/member lists, source rows, and confidence in Details/JSON.

An uncompiled tail is informational only when its proof holds. It does not count as mapped, does not count as unexplained unmapped, and does not create future volumes. A missing recognized special is an acquisition problem, not automatically a structural/main gap.

Derived structure, source status, manifest work/edition identity, reference evidence, aliases/enrichment, provider qualification, exact ambiguous/conflicting rows, selected-result provenance, and concise final explanations remain visible to developers.

## 10. Dandadan captured-data regression — current authoritative fixture

These are CAPTURED/OFFLINE expectations, not title-specific production constants or promised current live counts. Earlier reports used 248 main before two mapped supplements gained correct taxonomy. The final canonical-special fixture supersedes those old main-count descriptions.

| Metric | Captured MangaPill case |
|---|---:|
| Raw selected acquisition records | 250 |
| Canonical main chapters | 246 |
| Acquired recognized specials | 2 |
| Included logical publication units | 248 |
| Unresolved provider artifacts | 2 |
| Mapped main chapters | 219 |
| Total mapped units | 221 |
| Uncompiled main chapters | 27 |
| Unmapped main chapters | 0 |
| Released final volumes | 25 |

Health: identity PASS / publication PASS / normalization REVIEW / acquisition PARTIAL.

Acquired independently recognized supplementary records: 32.5 in volume 4; 40.5 in volume 5. They are supplementary rather than main serial chapters, and retain their real acquisition IDs.

Unresolved MangaPill provider fractions: 26.5 and 193.1. Neither has accepted exact independent identity/volume proof. They remain reviewable artifacts, never decimal-neighbor aliases.

Nine reference-known missing specials: 5.5, 14.5, 23.5, 49.5, 58.5, 67.5, 76.5, 85.5, 201.5. One MISSING_SPECIAL_ACQUISITION / ACQUISITION_ONLY finding affects them. Do not invent their acquisition URLs or make them publication failures.

Eleven typed MangaDex supplementary records have explicit volume evidence: the two acquired ones plus those nine absent ones. Category/title evidence is scoped structural taxonomy (including Portuguese releases), not proof of page-for-page equivalence with every English acquisition. Official supplementary listings did not establish alternate-number links for 26.5/193.1.

Captured Atsu case:

- Raw groups 481 = Alpha 248 + Delta 233.
- Selected Alpha 248 = 246 main + 2 acquired specials.
- Retained Delta alternatives 233 = 230 parallel identifiers + 19.5, 89.1, 92.5.
- Same 219 mapped main, 221 total mapped, 27 uncompiled, 0 unmapped main, 25 released volumes.
- Typed resolved group fixture has zero unresolved primary artifacts.
- Health: PASS / PASS / PASS / PARTIAL. Acquisition remains partial for missing specials.

The latest repaired native disposable audits selected Atsu, so normalization PASS rather than the captured MangaPill REVIEW was expected existing provider behavior, not a changed health rule.

Fixture locations under C:\MangaAnka DDK\tests\fixtures:

- canonical_specials\mangadex-aggregate.json
- canonical_specials\mangadex-fractional-0.json
- canonical_specials\mangapill-chapters.json
- canonical_specials\research.json
- dandadan_audit18_review.json
- publication_freshness_evidence\wikipedia_audit18_revision.json
- publication_freshness_evidence\atsu_dandadan_allchapters.json
- atsu_group_page.json

Audit 18 release evidence was evaluated using its cited Wikipedia revision 1374992070 as of October 4, 2026. Volume 25 had positive release evidence; 26–27 had unknown original release dates in that captured revision. Listed without release proof is not the same as demonstrably dated future. The shared release evaluator is time/context/evidence driven; no fixed Dandadan boundary is hardcoded.

## 11. Regression corpus and clean control

The original 25-title corpus:

1. Chainsaw Man
2. Jujutsu Kaisen
3. Demon Slayer: Kimetsu no Yaiba
4. Attack on Titan
5. Death Note
6. One-Punch Man
7. Dandadan
8. My Hero Academia
9. JoJo's Bizarre Adventure Part 7: Steel Ball Run
10. JoJo's Bizarre Adventure Part 8: JoJolion
11. Fullmetal Alchemist
12. Tokyo Ghoul
13. Hunter x Hunter
14. Berserk
15. Monster
16. 20th Century Boys
17. Vinland Saga
18. Spy x Family
19. Blue Lock
20. Kaiju No. 8
21. Frieren: Beyond Journey's End
22. The Promised Neverland
23. Mob Psycho 100
24. Black Clover
25. Sakamoto Days

The World Is Mine is the additional 26-title clean structural control: 163 standalone acquisitions, zero native volumes, 163 explicit mappings, 14 derived/final volumes, 0 unmapped, 0 holes, PASS in validated evidence. Both deterministic pipeline tests and an earlier temporary-database live check support it. Do not turn these figures into runtime rules.

The October 2 historical 26-title packet had 1 PASS / 25 REVIEW before later corrections. It is not a current corpus score. Reduced fixtures include corpus_systemic_regressions.json and review_packet_regressions.json. Current live providers/counts may differ. No latest whole-corpus live rerun is claimed.

MF Ghost, Fire Force, and Monster are important unrelated-state regression controls. A verified MF Ghost chapter 275 → volume 23 fixture tests preservation of curation/evidence, but that is not a universal mapping template for other manga. The latest SQLite task explicitly verified that forcing Dandadan leaves these unrelated memberships/pins unchanged.

## 12. Latest SQLite self-lock repair — exact proven cause

Original live symptom: one freshly launched instance, Force Re-Audit Selected, database is locked; failure observation persisted; no new audit/pin. The user's hypothesis was a long write transaction across audit work. Inspection showed that hypothesis was NOT the actual cause.

The original lifecycle already committed the queue and AUDITING claim before provider/reference work. The defect was inside the final SHORT atomic persistence transaction:

    Writer connection: BEGIN IMMEDIATE
      → insert audit and problems
      → UPDATE large publication JSON
      → SQLite cache spill in DELETE journal upgrades writer to EXCLUSIVE
      → pin readiness / acceptance validation
      → Catalog lookup opens a DIFFERENT reader connection
      → reader SELECT waits on its own workflow's EXCLUSIVE writer
      → OperationalError: database is locked

Exact failing statement was a READ:

~~~sql
SELECT * FROM curated_catalog cc
WHERE EXISTS (SELECT 1 FROM curated_fields cf WHERE cf.work_id=cc.work_id)
~~~

Call chain:

    Catalog More action
      → MainWindow.force_reaudit_selected / start_audit
      → AuditWorker.run
      → SearchAuditor.audit_many / audit_one
      → WorkingSets.persist_item_audit
      → pin
      → Acceptance.evaluate
      → Catalog.validate / rows / lookup
      → new reader connection / SELECT

Deterministic original-source trace: writer 9 and reader 10, same thread 32672. Original-source Qt trace: writer 30 and reader 32, same AuditWorker thread 14856. These are DISPOSABLE TRACE IDs, not live-database connection IDs.

Large publication data made the defect reproducible; small old fixtures did not spill the cache. Native disposable reproduction produced the same lock failure. A generic 4,000,000-byte inert provenance fixture reproduced it deterministically. A rolled-back disposable pager control proved that separate reads succeeded before the large write but failed after spill; disabling spill on a test-only control connection removed that conflict. Production spill settings were not changed.

One application instance can self-lock because the OS writable-instance lock and reentrant backend RLock do not turn distinct SQLite connections into the same transaction.

Failure sequence explains preservation:

    nested reader fails / closes
      → persistence writer ROLLBACK / closes
      → separate failure transaction
      → insert working_set_observations + membership ERROR
      → COMMIT / closes

The lock had been released before failure persistence. Empty provider arrays in the generic failure record were constructed by the failure handler even for persistence-stage errors; they did not prove resolution never happened.

The fix reuses the owning transaction's connection for all synchronous nested validation/catalog reads. EXACTLY FOUR product files changed in this pass:

| DDK file | Narrow change |
|---|---|
| ddk_acceptance.py | Pass existing evaluation connection to catalog validation; eligibility policy unchanged |
| ddk_catalog.py | Optional connection through lookup/snapshot/rows/validate and post-write curation validation |
| ddk_working_sets.py | Optional connection for structure_source and related work reads |
| mangaanka_database_development_kit.py | Optional existing connection for work/latest_audit reads |

Added tests: tests\test_force_transactions.py (20), tests\test_qt_force_transactions.py (2), and external tests\smoke_packaged_force_transactions.py (30 packaged checks). Added DDK_FORCE_TRANSACTION_VALIDATION.md and rebuilt primary EXE. Generated traces/baselines/logs are under build\force-transaction-evidence; disposable native catalog/settings under build\force-transaction-packaged-disposable.

No plugin files, Qt product code, schema, grammar, policies, launchers/spec/hooks, fonts, or writer-lock implementation changed in this repair. Hash protection covered 138 product/plugin Python sources; only the four intended product files changed.

Transaction boundaries after repair remain:

1. Short GUI queue/event transaction commits/closes before worker dispatch.
2. Short worker AUDITING claim transaction commits/closes before search.
3. Long provider/enrichment/reference/normalization/publication work with no retained catalog write transaction or backend mutation lock.
4. Short atomic success transaction writes immutable audit/problems/work metadata, performs nested reads on SAME connection, advances exact pin/readiness, commits together; failure rolls back all.
5. Separate short failure observation/ERROR transaction AFTER rollback and closure.
6. GUI/event-relay refresh uses each thread's own short read connections.

DB.con opens one connection per operation on the calling thread; normal context exit commits, exceptional exit rolls back, finally closes. Connections retain SQLite thread checking and are passed only through synchronous helpers on their owner thread. GUI, worker, and relay use their own connections. Provider threads do not receive catalog transaction connections. No shared long-lived connection or check_same_thread=False workaround.

Existing locking: OS writer lock for the writable app session; threading.RLock around short backend mutations. Nested write helpers use the supplied transaction. No new second locking system and no unnecessary app-wide serialization.

SQLite settings unchanged: journal_mode DELETE, timeout 30 seconds, busy_timeout 30000 ms, foreign_keys ON, isolation_level empty string, cache_size -2000, cache_spill 483 in disposable verification. Claim/persistence/failure helpers keep BEGIN IMMEDIATE. No WAL/timeout/cache-size production change.

Tests cover seven failure points: before providers, during providers, after resolution/before persistence, audit persistence, problem persistence, immediately before pin advancement, and after audit insert/before membership update. Each preserves old audit/pin, rolls back partial data, persists failure, exits AUDITING, releases locks, and permits retry. Recovery, exact targeting, GUI reads during provider work, serialized second writer, Run Working Set, Retry Errors, acceptance staleness, and curation dependency races are covered.

## 13. Latest reported validation and native evidence

Source: C:\MangaAnka DDK\DDK_FORCE_TRANSACTION_VALIDATION.md and build\force-transaction-evidence\final-validation.json. These results belong to the completed October 4 repair; they were not rerun just to create this handoff.

| Validation | Reported result |
|---|---|
| Focused transaction tests | 20 passed |
| New Qt transaction worker tests | 2 passed; focused combined 22 in 11.544 seconds |
| Full DDK suite | 347 passed in 86.087 seconds |
| Qt tests included in full suite | 82 |
| Final source window/scale smokes | All 9 passed |
| Packaged embedded-code tests | 30 passed in 16.548 seconds |
| Native packaged Force Re-Audit | Two sequential successful audits on disposable TEST catalog |
| Legacy Tk widget smoke | Passed with installed Tcl runtime access |
| Static/source checks | AST/compile and focused diff inspection passed |
| Entire plugin suite | Not run |
| Production database | Not opened or mutated |

Nine Qt cases = 1120×720, 1440×900, 1920×1080 at factors 1.0, 1.25, 1.5, exercising six pages and Publication Map. These are configured Qt/window checks, not physical multi-monitor certification.

Native packaged disposable sequence:

- Separate TEST database: build\force-transaction-packaged-disposable\catalog.db, isolated ui.ini.
- Disposable Dandadan UUID: 5d65eb33-62e7-41b9-9e8c-487ec7e12467 (NOT the live UUID).
- Before repair, native force failed; pin 1 stayed; failure observation remained.
- MF Ghost, Fire Force, Monster seeded with pins 2/3/4.
- Repaired first force created Audit 5, revision 2; immediately repeated force created Audit 6, revision 3.
- Both showed New 1 / Reused 0 and READY; target pin 1 → 5 → 6.
- Publication JSON sizes 2,264,148 and 2,264,146 UTF-8 bytes, enough to exercise large-record persistence.
- No new lock failure or observation; old disposable failure remained.
- Audits 1–5 remained unchanged after second success by serialized row hashes.
- Unrelated complete membership rows remained READY, pins 2/3/4, revision 1.
- Normal GUI close released the lock.

Evidence files include native-before.json, native-unrelated-before.json, native-after-first.json, native-after-second.json; large-before/after traces; Qt before/sequential-after traces; connection CSVs; source diffs/hashes; and final-validation.json under build\force-transaction-evidence. SQL traces keep templates rather than bound publication payloads.

Earlier counts are historical milestones, not totals to add together: Qt promotion full suite 238; serialization 266; Force feature 287; freshness 300; Atsu/health 312; canonical specials 325; latest SQLite pass 347. Latest focused shared-plugin canonical-special pass: 500 passed across selected modules, not the entire plugin suite. Prior freshness/Atsu focused counts belong to their own reports.

## 14. Build, launchers, fonts, and artifact discrepancy

Primary launcher:

    C:\MangaAnka DDK\Launch_MangaAnka_DDK.bat

It starts the EXE when present and falls back to the Qt source launcher. Arguments are passed through unchanged. Source Qt launcher:

    C:\MangaAnka DDK\Launch_MangaAnka_DDK_Qt.bat
    C:\MangaAnka DDK\mangaanka_qt.py

Primary EXE:

    C:\MangaAnka DDK\dist\MangaAnka-Database-Development-Kit.exe

Legacy / Recovery:

    C:\MangaAnka DDK\Launch_MangaAnka_DDK_Legacy_Tk.bat
    C:\MangaAnka DDK\mangaanka_database_development_kit.py

Optional separate legacy spec: MangaAnka-DDK-Legacy-Tk.spec. A separate legacy EXE was not required for primary Qt promotion.

Local environment: .venv-qt\Scripts\python.exe. requirements-qt.txt pins PySide6 6.10.2; requirements-build.txt includes that file and PyInstaller 6.20.0. Prior reports used Python 3.10.6. Build scripts use this local environment, never global pip, and preserve the maintained primary spec:

    Build_MangaAnka_DDK_EXE.bat
    Update_MangaAnka_DDK_EXE.bat
    MangaAnka-Database-Development-Kit.spec

The primary spec is one-file/windowed, entry mangaanka_qt.py. It analyzes live-core dependencies but removes frozen core submodules. It retains tkinter/Tcl needed by backend imports; collects used PySide6 modules/platform DLLs; excludes unrelated Qt bindings/QML/Quick/WebEngine/Test payloads; includes intentional local font assets if supplied; excludes test DBs/screenshots/venvs/backups from intentional resources. ddk_build.qt_runtime_binaries filters incompatible Windows ICU DLL entries, avoiding a Poppler ICU collision. Shared core stays external.

Fonts: no Geist Sans/Mono files are bundled. Installed Geist is preferred, then Segoe UI Variable/Segoe UI and installed monospace/Qt/system fallbacks (previous environment reports Cascadia Mono). Original SVG icons/theme tokens are Python resources. Do not download/distribute fonts without their proper license. Existing supported asset directory is qt_app\assets\fonts.

BUILD IDENTITY RECONCILIATION REQUIRED BEFORE ATTRIBUTING NATIVE TESTS TO THE CURRENT EXACT BINARY:

| Artifact evidence | Size | SHA-256 |
|---|---:|---|
| Latest repair report's validated build | 52,511,522 bytes | d30479357fe68b29f2c8f32ad0d87e555e2801ab070cbe3c66039c18566b4c49 |
| EXE actually inspected for this handoff | 48,674,735 bytes | 77fb17d5bf1779227c022815a75568d6ad39bd101a19b554ae58d31226a8d95d |

The current EXE's filesystem timestamp displayed October 4, 2026 22:08:35 in this shell. The report timestamp was earlier. Timestamp/size alone cannot establish why packaging differs, and this handoff does not guess.

READ-ONLY archive inspection performed for this handoff compared embedded code objects against freshly compiled current source, without executing application modules or opening a database. All 13 checked modules MATCH:

- mangaanka_database_development_kit
- ddk_working_sets
- ddk_acceptance
- ddk_catalog
- ddk_publication
- ddk_chapter_normalization
- ddk_exports
- ddk_review
- qt_app.workers
- qt_app.main_window
- qt_app.pages.catalog
- qt_app.pages.details
- qt_app.pages.problems

Frozen shared-core submodules found: ZERO. Therefore the currently inspected EXE contains the checked latest SQLite/publication/normalization/UI source changes. This comparison does NOT certify all runtime DLL/resource differences or transfer the report's native smoke provenance to a different hash. No rebuild or native test was done during the context-only task. Preserve both hashes; investigate build provenance or run an appropriately scoped disposable smoke if an exact-current-binary packaging certification is requested.

## 15. Grammar 3 — current editing workflow and examples

The console is deterministic and case-sensitive. It is not SQL, Python, shell, or free-form natural language. Quote exact titles/notes. Explicit titles must resolve to exactly one stored edition/language work. No fuzzy title match. Decimal ranges select existing numeric records with existing endpoints; they never invent chapters.

Preview the complete multiline mutation batch, review staged values, then Apply atomically. Cancel clears staging. Selection changes, input changes, work/database switches, and stale audit/curation invalidate previews. A batch becomes one History entry. Undo/Redo and History Revert are previewed and applied. Show/explain/audit/save/undo operations run separately from mutation batches as supported.

Packets supply an EXACT guard; copy the actual current values, never use these placeholders literally:

~~~text
guard database_uuid <actual-uuid> audit <actual-id> revision <actual-revision> database <actual-token>
~~~

Preview AND Apply check guards. A new audit, curation, disposition, or relevant queue change can stale an old packet. Export a fresh packet rather than weakening the guard.

Examples of supported syntax (illustrative, not evidence that a manga has this mapping):

~~~text
select chapter 222
select chapters 222-232
select chapters 1,3,5,10.5,12-16
select volume 24
select unmapped
clear selection
set volume 24 selected
set volume 24 chapters 222-232
clear volume selected
reset volume selected
set type special selected
reset type selected
set title "Exact title" chapter 222
set source-note "Verified against official TOC" selected
set verification reviewed selected
set verification verified selected
add evidence source "Publisher" url "https://example.org/toc" selected
add evidence source "Second TOC" note "Contents" chapter 275
add chapter 206
add chapters 206-207
remove curated chapter 206
renumber chapter 10.5 to 10.6
add volume 24
remove curated volume 24
set volume-title 24 "Exact title"
set volume-source-note 24 "Official TOC"
set work verification verified
set work edition standard
set work language en
set work canonical-title "Exact title"
add alias "Exact alias"
remove alias "Exact alias"
set id anilist 12345
set id kitsu 67890
set id mangadex "00000000-0000-0000-0000-000000000000"
clear id mangadex
reset id mangadex
set expected chapters 207
set expected volumes 23
reset expected chapters
reset expected volumes
show effective chapter 222
show provenance volume 24
explain chapter 222
explain volume 24
explain work
validate
save
audit
undo
redo
~~~

Read C:\MangaAnka DDK\DDK_COMMANDS.md and current parser for full supported targets/variants. clear stores an explicit empty value; reset removes an override. Creation/removal is limited to curated publication records, never provider/reference acquisition snapshots. Source notes are not automatically interpreted as alternate-number proof. No new special-alias editor or persistent complete-coverage command was added. There is no set type uncompiled command.

UNVERIFIED fields remain drafts; reviewed/verified fields affect resolution under exact safety guards. Additional evidence requires an existing relevant assertion or an assertion staged in the same batch. Evidence stores provenance, not copied source-page text.

## 16. Schema and migration history

Current schema is 7, from ddk_schema.SCHEMA_VERSION. DDK VERSION remains 0.3.0. Grammar version is 3 in ddk_review.py. No version/schema/grammar change was made in the last shared-special or SQLite repairs.

Historical evolution:

- Initial publication integration added nullable final-publication metrics / JSON to search_audits; old audits remained intact and required rerun.
- Curation added curated_catalog, curated_fields, curated_changes, curated_events.
- Review workflow added stable revision/disposition/review metadata with backup-backed migrations.
- v5 added stable work UUIDs, lifecycle, Working Sets/intake/pins, reviewed structure relationships.
- v6 added conceptual-work grouping and separate assertion evidence, preserved IDs/history.
- v7 removed displayed-title uniqueness, enforced trusted canonical ID + edition + language uniqueness, added acceptance provenance/history and duplicate membership pointer.

Existing-database migrations are backward compatible, backed up before mutation, transactional, and gated by foreign-key/integrity checks. Canonical conflicts abort with exact IDs/UUIDs; no automatic fuzzy merge. No live migration was run by the latest repairs. JSON-only publication/freshness/special diagnostics required no new DDL.

Historical approval provenance cannot be invented. Existing user catalogs, pinned snapshots, curation, evidence, history, custom data, and failed observations must survive changes.

## 17. Broader plugin context to preserve

The Calibre plugin has pre-existing Judgement/Empress/Emperor development outside the DDK. It is not a clean release checkout. Current package/version names can still say MangaNana; do not perform a naming/version cleanup as part of a targeted bug fix.

Earlier plugin passes separated acquisition, structure and artwork; added trusted bounded MangaDex reference/cover catalogs; preserved provider reader IDs and language/source policies; improved processing/framing and responsive Qt workflow; and synchronized effective output metadata through cover rendering, filenames, CBZ ComicInfo, PDF metadata, and Calibre import.

Source volume/acquisition identity stays separate from output Series #. A source volume 14 edited to effective Series # 21 must still acquire volume 14 while output stamp/filename/metadata/import use 21. Per-row title overrides are local; explicit bulk changes apply only to selected rows. Preview/cover/final output use effective state and newest-state-wins generation checks.

Existing processing order retains layout/framing/gutters, grayscale, gated inversion, image adjustments, depth/dithering. Dark Page Inversion requires Grayscale; grayscale OFF clears/disables inversion; saturation value survives disabled grayscale controls. Live preview reuses acquired samples for local processing changes and is debounced; no unnecessary acquisition.

Do not confuse plugin UI policy with DDK UI policy: one older plugin polish pass deliberately hid certain inner list scrollbar widgets while preserving scroll ranges. DDK requirements explicitly demand visible functioning scrollbars. Do not copy the plugin's visual rule into the DDK.

Real Calibre GUI/library/import and physical multi-monitor/input behavior have separate manual qualification requirements. Latest DDK lock validation does not claim these were tested. Current AGENTS.md and task-specific plugin reports govern any later plugin work.

## 18. Remaining limitations and decisions not yet made

1. Post-repair LIVE Dandadan validation is not reported. The automation did not inspect/mutate its Audit 20 revision 5 pin or failures.
2. The current on-disk EXE differs in hash/size from the latest report. Checked embedded source is current, but exact artifact native-test provenance needs reconciliation for a packaging certification.
3. Legitimate external SQLite contention can still time out. Large short atomic writes can briefly block separate readers in DELETE mode. The repaired bug was a reader contending with its OWN transaction, not all possible database locks.
4. An unrelated existing WINDOWED-EXE --help invocation raised argparse NoneType.write because console streams are absent. Normal GUI startup/audits passed in the recorded repair. This CLI issue was deliberately left outside the narrow repair.
5. The EXE depends on current local shared-plugin source. Missing source fails closed. It is not a self-contained portable bundle of search/provider implementations.
6. The plugin does not automatically consume the DDK SQLite catalog or exported curated patches. Catalog production/distribution/runtime-loader integration remains separate future work.
7. Persistent complete-publication coverage contracts are absent from schema v7/Grammar 3. Existing curation is sparse/identity-only unless explicit runtime evidence proves otherwise.
8. Provider/reference availability, corpus counts, recommended Atsu ordering, dates, and cache freshness may change. Exact source/evidence determines results; no fixed live count promises.
9. Dandadan 26.5/193.1 remain unresolved in the MangaPill fixture; nine specials lack acquisition. Do not force normalization PASS/acquisition PASS or invent aliases.
10. DDK equivalent-duplicate projection reconciliation is an adapter boundary, not proof of identical plugin UI behavior for every repeated-key case.
11. Legacy audits lack some current taxonomy/provenance. Unknown values need rerun, not synthetic backfill or history rewriting.
12. Geist is unbundled; physical per-monitor DPI, precision-trackpad/wheel behavior, cross-machine Windows runtime behavior, and actual Calibre output/import need appropriate manual checks.
13. Some optional artwork tests in earlier DDK-environment focused plugin runs could not import Pillow and were NOT counted as passing. Relevant structural/artwork precedence tests did pass; latest lock task did not add artwork coverage.
14. Direct scripts bypassing the application OS writer lock are outside its instance protection. SQLite ownership/transactions/revision checks still apply; do not introduce ad hoc scripts against production.

## 19. Next manual Dandadan check — USER OPERATED ONLY

After ensuring the intended current build is being launched:

1. Save work and close other DDK writers normally.
2. Launch C:\MangaAnka DDK\Launch_MangaAnka_DDK.bat and explicitly choose the live catalog yourself.
3. Activate the intended Working Set and select only Dandadan item UUID 465c6205-b25e-4a01-b0ab-057d184fae68. Confirm the expected starting pin (last reported Audit 20 revision 5). If the set is protected, use the existing explicit reopen action.
4. More → Force Re-Audit Selected → confirm Force Re-Audit. Wait for completion.
5. Verify New 1 / Reused 0, one distinct immutable audit, exact selected pin advancement, preserved old audit/history/curation/evidence, no database-lock error, and no stranded AUDITING state. Do not assume the next numeric ID must be 21 if other work was audited.
6. Force the same item once more. Verify a second distinct audit, final pin on it, both earlier audits preserved, and unchanged unrelated MF Ghost/Fire Force/Monster pins.
7. Inspect main/special/logical/mapped/uncompiled/unmapped/released counts and actual provenance. Compare against captured expectations only if current evidence matches. Atsu and MangaPill can have the established normalization-health difference.
8. Export fresh contexts for the same audit/revision/pin/disposition state; four health values should agree across whole/set/selected-problem views.
9. Leave the two old failed intake observations intact. Do not Accept simply to change readiness; acceptance is a separate evidence-based human decision.

## 20. Development commands and safe validation boundaries

Commands below are for an authorized future implementation task. They were not run again to manufacture new validation claims during this handoff. Use disposable data and explicit test paths. No production DB argument belongs in automated commands.

~~~powershell
Set-Location -LiteralPath 'C:\MangaAnka DDK'

# Full DDK suite after a relevant repair:
.\.venv-qt\Scripts\python.exe -m unittest discover -s tests -p 'test_*.py'

# Focused SQLite / Qt worker suites:
.\.venv-qt\Scripts\python.exe -m unittest discover -s tests -p 'test_force_transactions.py'
.\.venv-qt\Scripts\python.exe -m unittest discover -s tests -p 'test_qt_force_transactions.py'

# Source launch: chooser; no implicit production selection:
.\.venv-qt\Scripts\python.exe mangaanka_qt.py

# Create a NEW nonexistent disposable path only; replace the example path:
.\.venv-qt\Scripts\python.exe mangaanka_qt.py --database 'C:\MangaAnka DDK\build\new-disposable-example.db' --create --role SCRATCH --ui-settings 'C:\MangaAnka DDK\build\new-disposable-example.ini'

# Rebuild only when required; close running EXE normally first:
.\.venv-qt\Scripts\python.exe -m PyInstaller --noconfirm MangaAnka-Database-Development-Kit.spec

# External frozen-code test runner against disposable fixtures:
.\.venv-qt\Scripts\python.exe tests\smoke_packaged_force_transactions.py dist\MangaAnka-Database-Development-Kit.exe
~~~

For a shared source repair, inspect relevant plugin tests and use their correct runtime. Do not run the entire repository suite. Windows sandboxed Tk/PyInstaller may need access to installed Tcl runtime; a missing Tcl init.tcl under sandbox is not automatically an application defect. Native interaction and frozen-module tests are different evidence.

Read-only Git status used a command-local safe.directory exception when ownership differed; no global Git configuration was changed. Do not reset or clean the extensive worktree.

## 21. Local evidence index

All DDK files below are in C:\MangaAnka DDK. Read newest relevant reports first; earlier prose saying not rebuilt or older counts is historical.

| Report | Main purpose |
|---|---|
| DDK_FORCE_TRANSACTION_VALIDATION.md | LATEST SQLite root cause, exact four changes, 347 tests, native sequential audits, complete connection evidence |
| DDK_CANONICAL_SPECIALS_VALIDATION.md | Current Dandadan taxonomy/counts, trusted explicit aliases, coverage ranking, special gaps |
| DDK_ATSU_HEALTH_VALIDATION.md | Recommended/alternate groups, recovery/provenance, authoritative persisted health |
| DDK_PUBLICATION_FRESHNESS_VALIDATION.md | Shared freshness/release/UNCOMPILED, curation extension limits, no plugin catalog loader |
| DDK_FORCE_REAUDIT_VALIDATION.md | Exact selected membership action, queue guards, normal pipeline, immutable history/pins |
| DDK_SERIALIZATION_VALIDATION.md | Initial uncompiled/special distinction; synthetic counts partly superseded by captured taxonomy |
| DDK_QT_PROMOTION_VALIDATION.md | Primary Qt packaging, files changed, resources/fonts, UX, launchers, original smokes |
| DDK_QT_FRONTEND_VALIDATION.md | Frontend inventory and six-page/backend feature mapping |
| DDK_LIFECYCLE_V7_VALIDATION.md | Current migration, acceptance lifecycle, protected sets, races, pinned views |
| DDK_CURATION_VALIDATION.md | Curation identity authority, automatic/effective separation, undo/redo/export |
| DDK_REVIEW_VALIDATION.md | Review packets, guards, dispositions, health dimensions |
| DDK_COUNT_REPORTING_VALIDATION.md | Artifact versus unclassified count cleanup and compact clean packets |
| DDK_PACKET_REGRESSION_VALIDATION.md | Equivalent duplicates and grouped range/split/fractional diagnostics |
| DDK_26_TITLE_SYSTEMIC_REVIEW.md | Shared identity defect/correction and selected edition/coverage evidence |
| DDK_NORMALIZATION_VALIDATION.md | Discovery confidence fix and initial canonical normalization |
| DDK_PUBLICATION_VALIDATION.md | Original real manifest/reference/projection integration and World Is Mine control |
| DDK_COMMANDS.md | Current deterministic grammar help and exact semantics |
| MangaAnka_Database_Development_Kit_README.md | Current launch/build instructions plus historical development sections |

Plugin context reports under C:\MangaNana-Dev\MangaNana-calibre include AGENTS.md, PATCH1_VALIDATION_REPORT.md, PATCH1B_VALIDATION_REPORT.md, PATCH1C_VALIDATION_REPORT.md, PATCH1D_VALIDATION_REPORT.md, PATCH2_4_VALIDATION_REPORT.md, MADB_VALIDATION_REPORT.md, JUDGEMENT_STATE_SYNC_REPORT.md, and JUDGEMENT_UI_RESILIENCE_REPORT.md. Other source-specific reports exist; verify their scope before treating them as current architecture.

These paths are a navigation index, not files embedded in this handoff. A ChatGPT model without local tools cannot inspect Windows paths merely because they are listed. Ask the user for the relevant source/report or a scoped source archive when exact implementation is needed. Do not claim to have inspected files that were not supplied.

## 22. Suggested opening message for the new model

~~~text
Read the attached MangaAnkā project handoff before proposing changes. The DDK and Calibre plugin are separate programs; local worktrees are authoritative. The latest SQLite Force Re-Audit self-lock repair is already implemented. Do not redo completed work, access my live catalog automatically, change schema 7 / Grammar 3, or commit/push/tag/release/bump versions. Distinguish historical reports, captured fixtures, my live observations, and newly verified facts. Note the current EXE/report hash discrepancy and the source-match archive check. Wait for my next specific task; if you need exact code and cannot access local files, ask for the relevant files rather than guessing.
~~~

Handoff preparation changed only this new Markdown file. It did not edit product code, rebuild the EXE, run a database operation, repeat the test suite, or modify either project's existing implementation.
