# DDK curated editor — implementation and validation

Date: 2026-10-02. Development source pass; existing EXE remains unchanged.

## 1. DDK files changed

Updated:
- `mangaanka_database_development_kit.py`: catalog initialization, five-tab navigation, selected-title publication integration, Problems navigation, count provenance, stale-audit state, diagnostics, protection against deleting curated history.
- `ddk_publication.py`: exact catalog lookup before external reference lookup; effective curation overlay and curated-identity/count findings.
- `tests/ui_smoke.py`: five-tab overflow and native selection/command/history workflow checks using disposable SQLite.
- `MangaAnka_Database_Development_Kit_README.md`: editor usage and operating boundaries.

Added:
- `ddk_catalog.py`: exact identity bindings, SQLite curated fields, previews, backups, validation, change journal, undo/redo and patch export.
- `ddk_curated_resolution.py`: immutable reference overlay around existing plugin projection and volume-plan functions.
- `ddk_commands.py`: deterministic bounded grammar and exact title/record scopes.
- `ddk_editor.py`: chapter/volume editor, title forms, console, previews, History and health summary.
- `tests/test_catalog.py`, `tests/test_commands.py`: focused regression tests.
- `DDK_COMMANDS.md`, this report.

No build scripts/specs were changed during this pass. Test bytecode was generated only in the DDK workspace. Existing test corpus and plugin fixtures were retained.

## 2. Plugin files changed

None. All implementation is in the DDK. The plugin's current pure modules remain the source of publication behavior. No commit, push, tag, release, reset, worktree clean, full plugin test suite, or EXE/release build was performed.

The unchanged Calibre plugin does not independently consume this catalog yet. The DDK adapter currently implements the curated authority; the export contract provides a future integration boundary. No plugin change was required for this pass.

## 3. Schema and migration

Four additive, idempotent tables:

- `curated_catalog`: work_id, exact identity JSON, monotonically increasing revision.
- `curated_fields`: work/entity/record/field primary key, value JSON, verification state, provenance note.
- `curated_changes`: timestamp, work, operation, complete per-field before/after states, identity before/after, revision, active/reverted/superseded status.
- `curated_events`: append-only apply/undo/redo events for journal transactions.

Audit/source snapshots are never overwritten. New `publication_json` payloads retain an `automatic` result and the effective result, plus catalog identity/status/revision, applied fields and attributed count evidence. Effective values are derived rather than copied over raw rows.

Existing databases initialize these tables without rewriting existing works, audits, holes, custom tables, or source snapshots. Audits lacking the new identity evidence show RERUN REQUIRED. Existing manual data in unrelated legacy tables is retained, never assumed trusted or silently promoted.

All development migration/edit tests used disposable databases. The actual user catalog was not opened or migrated during development.

## 4. Final precedence and identity safety

The catalog is queried before `ReferenceMetadataService.lookup`. Approved exact-compatible fields take precedence in the final DDK projection:

curated DB → provider explicit metadata → MangaDex structure → Wikipedia structure → existing safe derivation → unresolved.

The original automatic pipeline still runs to retain independent current evidence; curation does not suppress external requests. Both results remain inspectable. The adapter reuses plugin immutable dataclasses, `build_publication_projection`, `build_unified_volume_plan`, and the existing manifest builder's membership rebuild helper. No independent chapter-boundary algorithm is added.

Identity must match canonical work, edition, language, and publication context exactly, with no shared trusted-ID contradiction. Multiple compatible catalog records are ambiguous and not applied. Explicit incompatible local bindings are surfaced as CURATED_IDENTITY_CONFLICT. Unknown/untrusted identities cannot be curated until a trusted audit is available.

The authority boundary conservatively separates provider-native omnibus/deluxe/bunkobon/kanzenban markers where the core's color classifier has no print-format class. It ignores alternate titles for this check and does not change plugin search ranking. Unrecognized or conflicting edition evidence is not inferred compatible.

Acquisition IDs, URLs, page lists, provider choice, and fallback transport remain unchanged. Raw reference contradictions remain in the automatic snapshot even when a curated mapping resolves the effective conflict.

## 5. Database editor

Database has a title list, chapter/volume views, filters, bulk fields, an individual row form, title identity form, command console, preview output, and Apply/Cancel.

The chapter table displays automatic, curated, and effective volume values, effective title/type, mapping source and status. Double-click one row to edit chapter number, title, type, volume, or source note. Chapter-number changes are single-record, checked for collisions, and marked high-impact. Bulk edits change only explicitly entered fields. Forms require field checkboxes.

Title form supports canonical title/work ID, edition, language/publication context, exact aliases, arbitrary source=value external IDs (AniList, Kitsu, MangaDex, etc.), expected counts, publication status and note. Identity rebinding is explicit, single-title, and may quarantine curation until a compatible search result exists.

Volume view lists chapter membership explicitly, including decimals, with curated title/IDs/provenance/verification. Volume membership is proposed by selecting chapter rows or issuing a range command. No simple-range assumption is used to invent membership.

Filters: All, Unmapped, Missing acquisition, Conflicts, Modified, Curated, Automatic only, Volume N. Problem navigation opens the relevant filter and selects affected identities when supplied. No per-chapter top-level issue explosion is introduced.

## 6. Multi-selection

The chapter Treeview uses native extended-selection behavior: click, Shift-click range, Ctrl-click toggle. Ctrl+A selects visible/filtered rows. The smoke test exercised actual Tk mouse events to select eleven contiguous rows, toggle another row on/off, and select all filtered rows. No custom range-selection mechanism replaces the native bindings.

## 7. Command grammar

`DDK_COMMANDS.md` and the in-app Command Help document all requested initial selection, edit, navigation and database commands, plus `reset volume selected`.

Examples:

```
select chapters 222-232
set volume 24 selected
set volume 24 chapters 222-232
clear volume selected
reset volume selected
set type bonus selected
set title "Exact title" chapter 222
set source-note "Verified against official TOC" selected
on "Exact title" set volume 24 chapters 222-232
validate
save
audit
undo
redo
```

Ranges include only existing numeric identities between existing endpoints, including decimal chapters. Explicit title scope must match exactly one title/edition/language record; ambiguous or unknown titles fail closed. Commands are case-sensitive, parse through shlex plus a bounded grammar, and never interpret natural language or execute code/SQL. Up/Down recalls in-session command history.

## 8. Preview / Apply

Every edit and undo/redo produces a concrete preview; Enter never applies it. Preview includes affected records, fields and effective before/after values. Apply commits one transaction; Cancel discards it. Edit previews capture audit ID and catalog revision, rejecting stale proposals after refresh or another edit. Undo/redo also checks revision and journal state atomically.

`clear volume` creates an explicit null reference override, blocking the old mapping. `reset volume` removes the override and restores the automatic value. Apply saves immediately. Save validates already committed edits and refuses to silently apply a pending preview.

## 9. Undo/redo, History and backups

Manual and console edits share the same persistent per-title transaction journal. Undo restores prior curated values and verification/note states; redo restores the reverted change. A new edit after undo supersedes the redo branch. History View shows before/after entries, and Preview Revert requires later active changes for that title to be reverted first. Network harvesting is never undone.

First curated mutation in a session creates an SQLite backup with the backup API in `workspace/backups`. Retention keeps the newest 20 matching generated backup files, not arbitrary database files. There is no per-cell backup. Titles with curated history are protected from queue deletion.

## 10. Validation

Local validation runs after Apply/Undo/Redo and through Validate/Save. Invalid numeric edits, invalid types, ID contradictions and curated renumbering collisions are rejected. Existing duplicate identities, nonnumeric chapter identities needing a special type, incompatible bindings, orphan overrides, missing acquisition, remaining unmapped rows and unresolved conflicts are surfaced.

Ambiguous duplicate acquisition identities are not mass-curated by a guessed chapter key. Missing acquisition is shown separately and cannot be fixed by inventing page-bearing rows. Existing source anomalies remain visible rather than being erased.

Reviewed/verified expected chapter/volume counts are compared with the effective result using aggregated disagreement findings. Unverified drafts do not affect final resolution. All curated states survive refresh, including VERIFIED overrides that later agree with automatic evidence.

## 11. Re-audit

Re-run Audit and the `audit` command validate and submit the open title through the real search/publication path on the existing worker thread. Prior audits remain append-only. Local edits never silently convert a historical result to PASS; affected titles show RERUN REQUIRED until evaluated again.

## 12. Curated export

Export Patch writes `exports/curated-patches/<title>-<edition>-<language>-<work_id>.json`.

The stable envelope is `format: mangaanka-curated-patch`, `version: 1`, exact identity, revision and curated field records. Fields include entity/key/name/value, REVIEWED or VERIFIED state, and provenance note. Raw evidence, automatic snapshots, acquisition URLs/pages and UNVERIFIED drafts are excluded. SQLite remains authoritative. Export validates first; no import or automatic distribution is implemented.

## 13. Diagnostics and UI

Tabs: Audit, Problems, Database, History, Details. Existing Titles internals remain hidden for compatibility; Summary Export is available from Audit.

Details adds curated identity/status/revision, exact unmapped/conflicting numbers, and reported totals with the actual enrichment `provenance` and provider/canonical record association. It does not invent Part 1/current-work explanations. Raw reference bundles retain parser/contract/source states and structural rows. Older unattributed totals explicitly require a rerun.

All major tables retain vertical/horizontal scrollbars and light selected text on dark backgrounds. Database chapter and volume tables, History, console output, Help, previews and long Details use scrollable controls. The health summary shows title/audit counts, curated title/manual-field counts, and last-audit unmapped totals. It is a simple summary, not a redesigned dashboard.

## 14. Tests and exact results

- `python -m unittest discover -s tests -v`: **40 tests passed**. Includes 18 existing publication/migration controls plus new curation, parser, scopes, transactions, identity, export and history tests.
- `python -m py_compile ddk_catalog.py ddk_commands.py ddk_editor.py ddk_curated_resolution.py ddk_publication.py mangaanka_database_development_kit.py tests/test_catalog.py tests/test_commands.py tests/ui_smoke.py`: passed. The final membership-rebuild change also passed syntax compilation and all 40 focused tests.
- `python tests/ui_smoke.py`: passed outside the sandbox, which is required for Tcl/Tk initialization in this environment. Temporary workspace only. Audit/Problems/Database/History/Details overflow scrolling, native Shift/Ctrl selection, filtered select-all, preview-without-mutation, Apply, undo/redo, stale-audit indication, readonly-combobox colors and selected-row colors passed. Volume-view scrollbars and two-axis Details scrolling passed. This is real-widget verification, not screenshot-based visual review.

The World Is Mine fixture remains **163 logical chapters / 14 derived volumes / 163 mapped / 0 unmapped / 0 holes / PASS**. An incomplete generic 11-chapter fixture becomes PASS after a reviewed bulk mapping and fresh resolution. A conflicting lower Wikipedia reference is resolved by curation while its original contradictory rows remain intact. Provider volume precedence is overridden only in the reference layer; acquisition remains unchanged.

No full plugin suite, live 25-title network corpus, build, release or versioning operation was run.

## 15. Remaining limitations

- The unchanged Calibre plugin does not yet independently read this database/export. The DDK adapter implements the new authority without modifying plugin source.
- Curation begins from a trusted resolved work. It does not force failed/ambiguous searches to identify a work, or change acquisition selection based on manual aliases. Identity edits can deliberately quarantine existing overrides instead of forcing an unsafe match.
- The command/editor set operates on existing projected chapter records and chapter-backed volume groups. It does not create acquisitions, deduplicate source records, create arbitrary reference-only chapters, or provide unrestricted bulk identity editing.
- Native provider markers can conservatively separate known print formats; unmarked format differences still require trustworthy metadata. The DDK does not add broad fuzzy edition matching.
- The automatic service still performs fresh network reference lookup, even where a curated field is already present, to preserve an independent automatic baseline. Provider/artwork failures outside structural relevance remain diagnostic.
- Effective row edits are visible immediately; derived downstream structure and new audit findings are finalized on Re-run Audit. Historical Problems and health totals remain audit snapshots until rerun.
- Live Attack on Titan, Chainsaw Man, Demon Slayer and Jujutsu Kaisen results were not independently rerun or patched. No title-specific facts were hardcoded.
- Existing EXE and its packaging/runtime behavior were not rebuilt or tested in this pass. The local plugin worktree remains required.

## 16. Short manual sequence

Use the Python source now, or perform these checks in an EXE only after a separately authorized rebuild:

1. Open the existing title list, rerun a title marked RERUN REQUIRED, then double-click an unmapped/conflict Problem to open its Database rows.
2. Select a known correct range with click/Shift-click. Enter a verified volume and source note, Preview, and confirm nothing changes before Apply. Apply, inspect History, preview Undo/Redo and apply them.
3. Paste an equivalent scoped command from Command Help. Validate, Re-run Audit, inspect automatic versus curated evidence, and Export Patch. Scroll all five tabs and confirm selection remains readable.

No EXE was built or replaced by this work.
