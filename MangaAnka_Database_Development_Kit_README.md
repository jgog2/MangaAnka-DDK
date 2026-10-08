# MangaAnkā Qt DDK — v0.3.0, schema v7

The primary Qt Widgets frontend provides Catalog, Audit, Problems, Curate, History, and Details. Tk remains available as the Legacy / Recovery frontend through its original entry point and Launch_MangaAnka_DDK_Legacy_Tk.bat. Both frontends use the same validated backend and shared command compiler; no schema, search, provider, publication, command grammar, or plugin version change accompanies this frontend.

## Running the primary Qt DDK

Double-click `Launch_MangaAnka_DDK.bat`. It starts `dist\MangaAnka-Database-Development-Kit.exe` when present, otherwise the local Qt source launcher. The executable needs no Python installation, but still needs the current local plugin worktree at `C:\MangaNana-Dev\MangaNana-calibre` (or an explicit `MANGAANKA_PLUGIN_PATH`). With no arguments it asks for a database; it never silently opens the production catalog.

For source development, use the workspace-local environment (no global pip install):

```powershell
cd 'C:\MangaAnka DDK'
python -m venv .venv-qt
.\.venv-qt\Scripts\python.exe -m pip install -r requirements-qt.txt
.\.venv-qt\Scripts\python.exe mangaanka_qt.py
```

The environment is already installed in this development workspace. `Launch_MangaAnka_DDK_Qt.bat` also launches it without installing dependencies. With no database argument, the launcher asks to open or create a catalog. For a new disposable catalog, use a **new, nonexistent** path:

```powershell
.\.venv-qt\Scripts\python.exe mangaanka_qt.py --database '.\qt-scratch.db' --create --role SCRATCH
```

On later launches omit `--create`. The user may explicitly select a production catalog. Automated validation must use disposable catalogs or separately prepared copies, never the named live catalog. Both frontends share the existing OS writer lock; close one before opening the same database in the other. Database validation and existing supported migrations are unchanged. `--ui-settings path.ini` optionally isolates UI layout settings for development; it never selects a database.

Catalog defaults to eight columns; Columns enables advanced fields. Each page has its own visible scope. Set evidence stays pinned; Curate clearly edits the latest shared state. Inspectors collapse and resize. Problems opens exact affected chapters in the shared Publication Map. The bottom command drawer provides authoritative Help, multiline atomic Preview/Apply, Cancel, Undo/Redo, Ctrl+Enter, and in-session Up/Down history. Ctrl+F focuses the current search; Escape collapses the drawer; Enter opens selected Catalog/Problems rows safely. QSettings stores layout only.

**Catalog → More → Force Re-Audit Selected** deliberately queues one exact stable item in the active, unprotected Working Set for a fresh audit computation. Confirming preserves prior audits, pins until success, curation, and evidence. Success advances only that membership's pin; existing acceptance can become STALE and must be reconfirmed explicitly. The forced summary counts new audit IDs, not new catalog works. Normal Run Working Set and the Grammar 3 `audit` command are unchanged. This action does not purge caches or require fresh network retrieval. See [DDK_FORCE_REAUDIT_VALIDATION.md](DDK_FORCE_REAUDIT_VALIDATION.md) for guards, validation, and the manual checklist.

Validation uses temporary databases and deterministic provider mocks. See [DDK_QT_FRONTEND_VALIDATION.md](<C:/MangaAnka DDK/DDK_QT_FRONTEND_VALIDATION.md>) for the complete source inventory, feature mapping, results, limitations, screenshots, and manual checklist. See [DDK_QT_PROMOTION_VALIDATION.md](<C:/MangaAnka DDK/DDK_QT_PROMOTION_VALIDATION.md>) for the Qt promotion/build results. The earlier report is a historical source-only baseline.

## Building Qt / legacy fallback

The targeted serialization repair distinguishes explicitly supported **UNCOMPILED** serial chapters from unexplained unmapped chapters. It never assigns future volumes. Exact, independently supported fractional specials are retained separately from canonical main chapters; unsupported decimals still require review. Missing trusted specials use an acquisition-only diagnostic. Schema v7, command grammar, human acceptance, and the legacy launcher are unchanged. See [DDK_SERIALIZATION_VALIDATION.md](DDK_SERIALIZATION_VALIDATION.md) for evidence requirements, fixture counts, final EXE validation, and the manual re-test checklist. Existing audits retain their historical results until explicitly rerun.

Install the local build dependencies with `.\.venv-qt\Scripts\python.exe -m pip install -r requirements-build.txt`, then run `Build_MangaAnka_DDK_EXE.bat` or `Update_MangaAnka_DDK_EXE.bat`. Both build the primary Qt EXE. They never install globally. The spec analyzes dependencies of the current local plugin but omits frozen plugin submodules; the existing read-only live loader remains authoritative.

`Launch_MangaAnka_DDK_Legacy_Tk.bat` starts the unchanged Tk entry point with local Python, falling back to `py`. For an optional legacy build: `.\.venv-qt\Scripts\python.exe -m PyInstaller --noconfirm MangaAnka-DDK-Legacy-Tk.spec`. This writes a separately named legacy EXE.

The theme prefers installed/bundled Geist Sans and Geist Mono, then Segoe UI Variable/Segoe UI and an installed monospace font, then Qt/system fonts. No Geist files are currently bundled. Properly licensed local font files and their license can later be placed in `qt_app/assets/fonts`; the loader/spec already support that path. Original SVG icons and theme tokens are Python resources, included by module analysis; Qt platform plugins come from PyInstaller's PySide6 hooks. Test catalogs, review screenshots, virtual environments and backups are excluded.

---

# Pre-production workflow repair — schema v7, DDK v0.3.0

Create a Working Set, add/import titles, then **Run Working Set**. The run handles pending/queued/interrupted items and stale pins sequentially. Current READY items and human REVIEW cases are skipped; **Retry Errors** deliberately retries ERROR items. Search/provider/reference behavior is unchanged.

**Accept Selected** approves exact item UUIDs in a set, or exact work IDs from a global view. **Accept All Safe** previews and rechecks READY items transactionally. Unresolved UNKNOWN, RESEARCH, DATA, IDENTITY and CODE findings block acceptance, including raw UNCLASSIFIED_ACQUISITION. A valid grounded Ignore with Reason disposition can resolve that blocker. Normalization REVIEW and acquisition PARTIAL alone need not block.

Acceptance records the exact audit and curation revision. Catalog shows lifecycle and acceptance state separately. Accepted Master Catalog includes only CURRENT approvals. New audits or effective curation make prior approvals STALE until a human reconfirms them. Legacy ACCEPTED rows retain their lifecycle and show LEGACY_REVIEW_REQUIRED. **More → Reevaluate Acceptance** inspects, reconfirms, or explicitly revokes an approval.

COMPLETE requires a nonempty set with only ACCEPTED/REJECTED/DUPLICATE items. COMPLETE and ARCHIVED protect mutations; **Status → Reopen for Review** preserves every item and pin. **Intake → Reopen Selected for Review** queues only the selected accepted/rejected items, retaining their prior pins until a successful new audit. REVIEW freezes membership changes; choose OPEN to add/remove intake again.

Set Catalog, Problems, Details and default exports use pinned audit evidence and show the latest global audit separately. All Catalog uses latest global evidence. Curate explicitly edits the latest shared catalog state. Apply/Undo/Redo through an active set automatically audit only its affected membership; failures retain curation and the old pin. Busy runs defer affected-item audits. Protected or inactive named sets must be activated/reopened, or the user can select All Catalog for explicit global curation.

Schema v7 backs up existing v6 databases before a transactional works-table rebuild, removes title uniqueness, adds acceptance history and a duplicate membership pointer, and enforces nonempty canonical ID + edition + language uniqueness. Conflicting canonical claims abort with exact IDs/UUIDs. Identity, child rows, history and pins survive the upgrade; foreign-key and integrity checks gate commit. Same-title distinct identities can coexist. Two aliases resolving to one identity within a set retain intake provenance but produce one primary membership and a terminal DUPLICATE, with no second publication audit/pin.

The live database, plugin, search core and EXE were not changed during this pass. The EXE must eventually be rebuilt before these source features can be tested there. See [DDK_LIFECYCLE_V7_VALIDATION.md](DDK_LIFECYCLE_V7_VALIDATION.md) for the complete validation report.

---

# Permanent catalog work maintenance — 2026-10-03

Catalog → More → Catalog Maintenance → **Delete Catalog Work...** is a guarded maintenance action for exactly one selected edition/language work. It shows a read-only, database-computed impact preview, including the exact `work_uuid`, owned audit/curation/history/problem counts, affected Working Set memberships, structure relationships, and conceptual siblings. ACCEPTED or curated works show an extra warning. Typing `DELETE` enables the final action. Cancel and preview make no database changes.

After confirmation, the DDK makes a fresh SQLite backup in `backups/`, then deletes the selected work and owned rows in one validated transaction. Affected Working Set intake items and observations remain; their work and audit pins are cleared and the items become REVIEW. Other editions and unrelated works remain. The final edition also removes its now-unused `conceptual_works` parent. A small `DELETE_WORK` database event remains visible in History under **All Catalog**. Permanent deletion is outside normal per-title Undo/Redo; recovery requires restoring the backup. Normal **Remove Selected from Working Set** is still non-destructive.

---

# Final pre-catalog hardening source pass — 2026-10-03

Schema v6 adds `conceptual_works` and `works.conceptual_work_uuid`. The immutable `work_uuid` identifies one edition/language catalog row, including its acquisition target and lifecycle. It does **not** identify every edition of an underlying manga. `conceptual_work_uuid` can group rows without merging their publication contexts or providers. New rows begin with their own conceptual UUID; an explicit reviewed structure relationship can link two edition rows to the same conceptual work. Cross-language and broader conceptual grouping remain future explicit catalog work, not a fuzzy title match.

Curate previews show staged chapter values in the grid with `⟦PENDING⟧` markers and a highlighted row. Curated/Effective Volume, Title, Type, Source Note, and Verification show their staged values; Automatic Volume remains committed. Verification transitions and evidence additions appear in the preview log. Cancel, changed selection/command/edit fields, work or database switch, and stale audit/revision clear the preview. Apply writes one transaction and refreshes committed values.

Publication validation counts canonical logical chapters separately from unclassified acquisition records. Review Context exports `canonical_unmapped_identifiers` and `unclassified_acquisition_identifiers` separately. Provider-only records remain visible for normalization work and do not inflate canonical unmapped counts.

`Status: <STATE>` shows the active Working Set state, or disabled `Status: NONE`. OPEN and REVIEW sets may advance an item's pinned audit during an audit in that active set. COMPLETE and ARCHIVED protect pins and mutations; either can explicitly reopen to REVIEW. Historical exports use those pins; current exports intentionally use the latest audit.

**Accept Selected** is explicit and per edition/language row. It requires a fresh audit, trusted matching canonical/edition/language identity, shareable context, a complete nonempty publication with at least one volume, identity and publication health PASS, no fatal audit state, no unresolved IDENTITY/DATA/RESEARCH issue, no untriaged UNKNOWN issue, compatible curated identity, and no curated validation errors, canonical unmapped chapters, or conflicts. Raw `UNCLASSIFIED_ACQUISITION` blocks until valid human disposition. Normalization REVIEW and acquisition PARTIAL alone do not block; unresolved code-review findings do. PASS never auto-accepts. Existing code/research findings still need separate review where appropriate.

`curated_evidence` stores zero-to-many provenance records per granular curated assertion (entity/key/field), with assertion revision, source name, optional URL, access date, note, verification, and creation time. `add evidence source "Publisher" url "https://…" selected` and exact chapter targets work in the multiline command batch. Multiple evidence records preview and commit atomically; undo/redo includes them. Curation and evidence survive re-audits even when automatic data later agrees or disagrees. Legacy inline source fields remain for compatibility and migrate into separate evidence rows once. Structure-sharing relationships keep exact source and target publication contexts; lookup fails closed when either changes.

Each new audit records its own DDK version, search-core version, schema version, requested edition, requested language, and workflow. The v5→v6 migration creates a pre-migration backup, runs transactionally, preserves existing work UUIDs, audits, curation, and history, and does not open the production catalog during development. Existing EXE is unchanged; rebuild it before a live MF Ghost acceptance test. Direct scripts that bypass the app writer lock remain outside that lock's protection.

---

# Working Sets and catalog lifecycle source pass — 2026-10-03

Schema v5 added immutable `work_uuid`, conservative `STAGED` catalog lifecycle state, persistent Working Sets and intake items, pinned audit revisions, explicit reviewed edition-structure relationships, and source metadata on curated fields. Pasted titles stay as intake requests until the real search identity path links or creates a work. PASS does not accept a work; schema v7 defines the current acceptance and workflow rules above. Existing v4 data was backed up and migrated transactionally. The real production database was not opened for this development pass.

The Catalog can show the active Working Set, accepted Master Catalog, all works, or a named set. Problems, Curate, Details, and History follow scoped views. Copy Selected offers a compact summary, review context, CSV row, and full details. Working Set CSV and review exports distinguish pinned historical audits from requested current state. The app uses an operating-system writer lock to block a second writable DDK instance. The plugin and EXE remain unchanged; run from source or rebuild the EXE when ready.

The command console accepts `set volume 24` for selected rows and mixes exact-title selection, edits, and a final `validate` in one atomic preview. Invalid lines block the entire batch. See [DDK_COMMANDS.md](DDK_COMMANDS.md) for the current grammar and guard format.

---

# Review workflow development pass — 2026-10-02

The Problems tab now exports its original summary CSV, a one-row-per-affected-record detailed CSV, and a paired Markdown/JSON Review Packet. Choose all unresolved problems, selected problem rows, or selected titles from the Audit table. Copy Selected and Copy All place the same Markdown diagnostics on the clipboard. The bottom Problems pane shows the selected problem packet, including source titles, provider IDs, automatic/curated/effective fields, reference evidence, classification, next action, and any strictly supported command suggestion.

Review Packets include stable numeric audit/problem IDs, an audit revision, a database revision token, schema and grammar versions, health dimensions, provider and publication evidence, existing curation, and a before/after re-audit diff. Paste the packet's `guard audit … revision … database …` line before commands derived from it. Preview and Apply both reject a stale guard. Suggested commands require trusted exact two-source agreement and still need Preview and Apply.

Unclassified acquisition can be marked **Ignored with Reason** only for a trusted, edition-safe identity. This requires a reason and REVIEWED or VERIFIED state; the append-only disposition journal retains the audit/problem ID and timestamp. Exact issue signatures carry such a disposition across re-audits. Use **Show ignored** and **Reopen Ignored Problem** to reverse a mistaken decision, with another recorded reason. Repeated user-entered provider patterns on two or more works appear as CODE_REVIEW_REQUIRED candidates. Publication and identity problems cannot be ignored this way.

The additive schema-v3 migration backs up an existing catalog before altering it. Tests use disposable databases; the user's catalog is never opened during development. The EXE has not been rebuilt, and no plugin source was changed. See `DDK_REVIEW_VALIDATION.md` for checks and remaining limits.

---

# Curated editor development pass — 2026-10-02

The source now exposes **Audit / Problems / Database / History / Details**.
Run `python mangaanka_database_development_kit.py` to use these changes. The existing EXE has not been rebuilt or replaced.

The Database tab separates automatic, curated, and effective values. Select chapter rows with normal click, Shift-click, Ctrl-click, or Ctrl+A. Enter only fields you intend to change, preview, then Apply. Double-click one chapter for individual editing. Dedicated title-identity and volume-metadata forms use explicit field checkboxes and previews.

REVIEWED and VERIFIED overrides are effective only for exact compatible canonical work, edition, language, publication context and trusted IDs. UNVERIFIED edits are drafts. The curated store is read before external reference lookup; the automatic pipeline still runs to retain independent evidence. Curated values take priority in the final DDK reference projection. Pages/providers are unchanged.

Four new tables preserve curation separately from append-only audit snapshots: `curated_catalog`, `curated_fields`, `curated_changes`, `curated_events`. All applied edits are immediately saved. Undo/redo and History Revert are per title, previewed and persistent. Reverting older changes requires reverting newer active changes for that title first.

The first curation, intake import, or major lifecycle change in each app session creates a SQLite backup in `backups/`; this pass does not delete older generated backups. Automatic refresh never deletes manual fields, including when it later agrees with them. Titles with curated history are protected from queue deletion.

The Console's **Command Help** and `DDK_COMMANDS.md` document the supported deterministic grammar. Export Patch writes reviewed/verified fields only, with exact identity and provenance, to `exports/curated-patches/`. JSON is an export, not an editing interface.

Old audits without a catalog identity, and audits predating an edit, show RERUN REQUIRED. Re-run Audit uses the selected title and creates a new audit; local validation never relabels a historical audit as PASS.

See `DDK_CURATION_VALIDATION.md` for exact changes, tests, and boundaries. The unchanged Calibre plugin does not yet independently read this catalog; the new precedence currently runs in the DDK adapter. No plugin source or EXE was changed during this pass.

---

# MangaAnkā Database Development Kit v0.3.0 — publication audit development pass

The DDK now audits MangaAnkā's final publication projection, using the **local plugin worktree** as the behavioral source of truth.

## Legacy Tk source running

Run `Launch_MangaAnka_DDK_Legacy_Tk.bat` for the legacy/recovery interface.
The standard launch/build/update flow now targets Qt; see the primary Running section above.

The live plugin path defaults to `C:\MangaNana-Dev\MangaNana-calibre`. Override it with the `MANGAANKA_PLUGIN_PATH` environment variable when necessary. Restart the DDK after changing plugin code. A missing worktree fails closed; the DDK never silently falls back to its historical search snapshot. The old copied modules remain on disk but are not used at runtime. The plugin's Calibre entry point is not imported.

This is a standalone process, but it now requires the local plugin source, including when run as an EXE. Rebuild after plugin changes introduce new Python dependencies. Each successful audit stores the source path and SHA-256 hashes of loaded core modules.

## Pipeline

1. Current provider search, enrichment, trusted alias retry, canonical grouping and ranking.
2. Current provider inventory qualification and source resolution.
3. Trusted `canonical_family_publication_context`, with the plugin's provider-local evidence fallback.
4. `ReferenceMetadataService`: MangaDex structure, Wikipedia publication resolution, and applicable reference/catalog evidence. MADB and MangaDex artwork are enabled as in the current plugin defaults. Google Books follows its existing verified-credential availability checks.
5. `PublicationManifestBuilder`: provider membership → MangaDex structure → Wikipedia, plus existing reference enrichment.
6. `build_publication_projection`: exact mappings and the plugin's safe fractional/pre-chapter-one derivations.
7. `build_unified_volume_plan`: actual acquired native and derived volume groups. Executable Chapter-mode fallback plans retain acquisition-source provenance.
8. Aggregated DDK findings against the final result.

No acquisition pages are downloaded. Provider covers are not audited; artwork evidence does not establish volume membership. The standalone run uses fresh reference lookups, without reading or modifying the plugin's search/reference cache or Calibre library.

## Output

Audit and Titles show Query, Matched Title, Edition, Providers, Selected Source, Logical Chapters, Final Volumes, Mapped, Unmapped, Holes, and Audit State. Audit also shows Run Status. Titles retains Last Audited. Summary CSV exports final metrics.

Logical chapters count chapter acquisition units presented by the plugin projection, including Chapter-mode fallback units. Native volume-only units are recorded separately, not counted as chapters. Duplicate/ambiguous chapter identities are left to the plugin's fail-closed projection. Final volume count includes only groups backed by acquisition, not every volume mentioned by a reference.

Details retains raw provider inventories and adds final metrics, reference statuses, manifest identity, reference evidence, projected chapter provenance, exact unmapped/conflicting chapter rows, aliases, and source hashes. All existing dark styles and visible table/text scrollbars are preserved.

## Findings

- `NO_CANONICAL_RESULT`: no accepted current-search result.
- `WEAK_SEARCH_MATCH`: retained conservative search warning.
- `NO_USABLE_PROVIDER`: no acquisition inventory qualified.
- `WRONG_EDITION_MATCH`: plugin edition identity differs from the requested stored edition.
- `UNMAPPED_CHAPTERS`: one finding with the total still unmapped after references.
- `REFERENCE_CONFLICT`: unresolved acquisition keys with ambiguous reference or duplicate identity evidence.
- `CHAPTER_COUNT_DISAGREEMENT`: explicit trusted manifest chapter keys absent from acquisition, not a comparison of raw provider row totals.
- `SOURCE_FAILURE`: selected acquisition is partial, an essential stage failed, or structural requests failed while mapping remains incomplete.
- `AUDIT_ERROR`: unexpected harness failure.

Zero native volumes is never itself a finding. Raw cross-provider differences, optional provider failures after successful acquisition, AniList/Kitsu totals, and lower-priority reference conflicts resolved by higher-priority evidence remain diagnostic. No independent fuzzy matching, edition parser, or chapter-boundary derivation is added.

PASS means no findings for this resolved audit. REVIEW means concrete findings need inspection. ERROR means an essential request/stage failed. PASS is not a guarantee of full worldwide publication completeness where references are unavailable.

## Existing database

The default workspace remains `Documents\MangaAnka-Database-Development-Kit` with `mangaanka_catalog.db`.

Startup performs an idempotent additive migration of `search_audits`: nullable `publication_json`, `selected_edition`, `logical_chapters`, `final_volumes`, `mapped_chapters`, `unmapped_chapters`, `final_state`, and `run_status`. No historical audits, titles, holes, or legacy tables are deleted or rewritten. Historical audits show RERUN REQUIRED with blank final metrics. Their old findings remain available until a new latest audit supersedes them.

Development tests use disposable databases. The user's existing database has not been opened or migrated by these tests.

## Focused validation

- `python -m unittest discover -s tests -v`
- `python tests\ui_smoke.py` (requires a desktop/Tcl-capable process; uses a temporary workspace)
- `python -m PyInstaller --noconfirm --workpath build\publication-analysis-tk --distpath build\publication-analysis-output tests\analysis_smoke.spec` (dependency analysis only; does not build an EXE)

The saved plugin MangaDex fixture for The World Is Mine gives 163 logical chapters, 14 derived volumes, 163 mapped, 0 unmapped, PASS. These numbers are assertions in tests, never title-specific production behavior.

See DDK_PUBLICATION_VALIDATION.md for the change inventory, limitations, and manual checks.
# Current audit count semantics

The audit keeps the selected provider's raw acquisition rows intact. A separate
normalization view uses MangaAnkā's exact numeric chapter and chapter-identity
helpers, compatible explicit reference mappings, provider-native membership,
and independent provider inventories to classify main chapters, explicit
specials, duplicate releases, and unclassified records. Reported bibliography
totals are shown with their AniList/Kitsu provenance; they do not identify
individual chapters or manufacture mappings. A provisional chapter can remain
in the displayed logical count while blocking PASS until supported by evidence.

The earlier The World Is Mine live audit skipped the plugin's
`effective_search_rows` canonical-facts pass, leaving its reference identity
untrusted. The DDK now runs that pass. The positive fixture still supplies an
exact MangaDex title ID; a separate offline discovery test proves the full
trusted lookup path. A fresh live result still depends on current MangaDex
discovery and may fail closed if identity or reference evidence is ambiguous.

Curated chapter and volume records are stored in existing `curated_fields`
rows with explicit existence markers. They are publication assertions, never
downloadable provider acquisitions. See [DDK_COMMANDS.md](DDK_COMMANDS.md)
for multiline atomic commands and diagnostic inspection.
