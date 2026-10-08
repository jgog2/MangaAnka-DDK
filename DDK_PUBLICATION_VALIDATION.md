# DDK publication integration validation — 2026-10-02

## Files changed in DDK

- `mangaanka_database_development_kit.py`: publication handoff, aggregated findings, additive migration, final metrics/CSV/Details, explicit SQLite connection closure, injectable workspace for isolated UI tests.
- `mangaanka_search_core/__init__.py`: read-only live-source loader; refuses missing worktree/modules instead of using the old snapshot.
- `ddk_publication.py`: thin orchestration adapter around current plugin functions and final-result classification.
- `ddk_build.py`: discovers the pure core's dependencies without importing Calibre.
- `hooks/pre_safe_import_module/hook-mangaanka_search_core.py`: makes live modules visible to PyInstaller analysis.
- `MangaAnka-Database-Development-Kit.spec`: collects those dependencies and uses absolute source paths.
- `Build_MangaAnka_DDK_EXE.bat`, `Update_MangaAnka_DDK_EXE.bat`: use the maintained spec instead of deleting/recreating it; removed build-directory deletion.
- `tests/test_publication_audit.py`: 18 deterministic tests.
- `tests/ui_smoke.py`: real Tk smoke against disposable databases.
- `tests/analysis_smoke.spec`: dependency-analysis-only validation; creates no EXE.
- `MangaAnka_Database_Development_Kit_README.md`, this report: operating requirements and validation.

Generated diagnostics are under `build/publication-analysis*`. Python checks also generated DDK-local bytecode. Existing `dist` executable was not changed.

## Plugin changes

No plugin source, configuration, release/version files, or tests were edited. Its existing uncommitted changes were preserved. No commit, push, tag, release, reset, clean, or full plugin test suite was run.

The initial normal Python import may have generated Python bytecode; the final loader suppresses bytecode writes into the plugin worktree. No Calibre library was opened.

## Exact reuse boundary

The existing provider search/enrichment/grouping/ranking/source-resolution orchestration remains in the DDK, now importing the current local modules instead of copied snapshot modules.

Post-selection calls match the relevant path in plugin `main.py`: `_start_reference_lookup` / `ReferenceLookupWorker.run`, `_on_reference_lookup_ready`, `_project_inventory_through_publication_manifest`, and `_refresh_unified_volume_plan`. The adapter calls:

- `canonical_family_publication_context`, `canonical_reference_alias`, and `trusted_alias_for_query`.
- `ReferenceMetadataService.lookup`, with current MangaDex structural/artwork resolvers, Wikipedia publication resolver, BOOKWALKER, MADB enabled as in current defaults, and existing Google Books availability rules.
- `PublicationManifestBuilder` provider, MADB, MangaDex structure, Wikipedia, reference artwork, and enrichment applications.
- `build_publication_projection` for authoritative memberships and safe derivation.
- `build_unified_volume_plan` for acquired native/derived volumes.
- The resolved executable Chapter-mode `fallback_plan.items`, guarded by the same primary/language checks and preserving acquisition provenance.

Provider → MangaDex → Wikipedia precedence is unchanged. Structure and artwork remain separate. No plugin UI entry point is imported.

## Before / after

Before: raw provider chapter counts, zero-native-volume warnings, raw-provider count disagreements, and reported-volume-versus-native-volume gaps.

After: final projected acquisition chapter units, actual final volume groups, mapped/unmapped counts, exact unresolved evidence, and aggregated final findings. Provider inventories remain visible.

The real saved MangaDex aggregate fixture for The World Is Mine, passed through the real resolver/service/manifest/projection/volume planner with offline request adapters, produced:

| Metric | Result |
| --- | ---: |
| Logical chapters | 163 |
| Native volumes | 0 |
| Derived/final volumes | 14 |
| Mapped | 163/163 |
| Unmapped | 0 |
| Holes | 0 |
| State | PASS |

This is fixture validation, not a claim about a fresh live provider audit.

## Findings changes

Removed from new audits: `REFERENCE_STRUCTURE_NEEDED`, `PARTIAL_VOLUME_MAPPING`, `PROVIDER_INVENTORY_DISAGREEMENT`, `REPORTED_CHAPTER_GAP`, `REPORTED_VOLUME_GAP`, both `REPORTED_*_TOTAL_CONFLICT` categories, and `SOURCE_ACCESS_WARNING`. These raw/advisory facts remain in Details.

Renamed/consolidated: `NO_PROVIDER_RESULTS` / `NO_RELEVANT_MATCH` → `NO_CANONICAL_RESULT`; `NO_USABLE_INVENTORY` → `NO_USABLE_PROVIDER`; selected partial inventory → `SOURCE_FAILURE`.

Added: `WRONG_EDITION_MATCH`, `UNMAPPED_CHAPTERS`, `REFERENCE_CONFLICT`, and evidence-based `CHAPTER_COUNT_DISAGREEMENT`. Retained `WEAK_SEARCH_MATCH` and unexpected `AUDIT_ERROR`.

One UNMAPPED_CHAPTERS finding contains the affected count; exact rows are stored in publication evidence. Lower-priority ambiguities that are resolved by higher-priority evidence do not become conflicts. Optional reference/provider failures do not create holes when acquisition/structure is complete.

## Database migration

Eight nullable columns are added to `search_audits`: `publication_json`, `selected_edition`, `logical_chapters`, `final_volumes`, `mapped_chapters`, `unmapped_chapters`, `final_state`, `run_status`.

Migration is additive and idempotent. No existing tables/rows are deleted or overwritten. Old audits show RERUN REQUIRED and unknown final metrics, not misleading zeroes or PASS. Existing legacy holes remain historical records; a rerun supplies a new latest audit.

Tests verified old title/audit/hole/custom-table retention, repeat initialization, SQLite integrity and foreign keys. Development did not open or migrate the user's actual database.

## Tests executed

- `python -m unittest discover -s tests -v`: **18 passed**. Real core import origin; 163/14 reference fixture; precedence; Wikipedia gap filling; safe fractional/pre-chapter-one derivation; aggregate unmapped findings; duplicate ambiguity; higher-priority native resolution; generic edition mismatch; alias isolation; standard-versus-fan ranking; exact missing referenced acquisition; native volume-only units; cancellation; Chapter fallback provenance; structural failure relevance; successful/error audit persistence and CSV; backward-compatible migration.
- `python tests/ui_smoke.py`: **passed** on real Tk at 1120×720 with the existing corpus list plus overflow rows in a disposable database. Audit, Titles, Holes, Details scrollbar visibility and scroll commands passed; selected Treeview and readonly combobox colors passed; long Details text scrolled horizontally and vertically. This is programmatic widget validation, not visual screenshot inspection.
- `python -m py_compile mangaanka_database_development_kit.py ddk_publication.py ddk_build.py mangaanka_search_core/__init__.py tests/test_publication_audit.py tests/ui_smoke.py`: **passed**.
- PyInstaller analysis-only spec: **passed**, including reference modules and Tcl/Tk detection. The sandbox initially prevented Tcl initialization; the UI and final analysis checks passed outside the sandbox. No EXE was built. Optional fallback absolute-import/Calibre and platform-only module warnings are expected; the required package-qualified core modules are present.

## Remaining limitations

- Live 25-title or large-corpus network audits were not run. Current Berserk search responses and current per-title counts remain unverified. Offline tests confirm generic standard ranking and wrong-edition reporting, with no title-specific production rules.
- The DDK follows the plugin's existing edition classifier. It does not add independent omnibus/deluxe detection or promise to detect edition distinctions the plugin itself cannot recognize. Effective edition identity and raw classifier evidence are stored together.
- The local plugin worktree is now a runtime dependency for source and rebuilt EXE. Missing source fails closed. Restart after source changes; rebuild after dependency changes. Frozen runtime execution was not tested because the EXE was not rebuilt.
- Fresh reference lookup runs without the user's plugin cache or custom Calibre preferences. Optional reference availability can differ from a previously warmed/customized Calibre session. Native provider covers and page/artwork correctness are outside this audit.
- The DDK retains its existing automatic source-choice policy; it does not simulate an interactive Calibre user choosing a different equivalent provider.
- Logical chapter counts reflect the plugin's projected acquisition units; the DDK does not independently deduplicate, invent chapter boundaries, or equate reported bibliography totals with acquisition counts.
- PASS means no demonstrated failure in available final evidence, not proof that an unavailable reference has no additional publications.

## Small manual EXE checklist

1. Rebuild using `Update_MangaAnka_DDK_EXE.bat`, launch, and confirm the old 25-title list/history is present. Old audits should say RERUN REQUIRED.
2. Audit The World Is Mine and Berserk. Inspect final reference status, derived volumes, mapped/unmapped counts, and selected edition. A selected fan-colored edition for a standard request must show WRONG_EDITION_MATCH; do not expect fixed live counts.
3. Scroll Audit, Titles, Holes, and long Details horizontally/vertically; select rows and combobox values. Then rerun the full existing corpus and export Summary CSV.
