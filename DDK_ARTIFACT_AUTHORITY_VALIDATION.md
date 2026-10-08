# Provider-artifact classification authority — validation report

Date: 2026-10-05. DDK remains v0.3.0, schema 7, Grammar 3.

This repair makes provider-pattern classification consume exact current publication identities from the shared manifest. It does not implement a provider-split shadow policy or solve wider publication-reference coverage gaps. Automated work uses offline fixtures and disposable databases only.

## Findings and exact call path

The inspected path is:

`ddk_publication.resolve_publication()` -> `ReferenceMetadataService.lookup()` -> `PublicationManifestBuilder.apply_provider_inventory()` / `apply_mangadex_structure()` / `apply_wikipedia()` -> `build()` -> acquisition projection and existing duplicate reconciliation -> `normalize_acquisition()` -> effective counts -> `publication_holes()` -> existing review/health and persisted code-review candidate grouping.

The numbering-pattern passes were already downstream of initial classification. A row successfully labeled main or recognized special was already excluded from the pattern passes. The defect was an incomplete and unsafe identity boundary before those passes:

- The shared manifest exported typed special records but did not export a corresponding set of current exact main publication identities independent of volume membership.
- Normalization treated a manifest chapter's reference-sourced volume as sufficient identity evidence. Ordinary legacy reference gap filling can retain volume fields even when evidence is stale or unsuitable for independently establishing a current fractional identity. That shortcut bypassed the stricter trusted-record eligibility check.
- DDK orchestration passed independently trusted Wikipedia main identities as bare keys. That side channel could handle eligible volume-free rows in the complete DDK path, but it discarded record-level type/provenance and was not available to a manifest-only normalization caller. Conflicting main/special records could also be flattened into the main-key set.
- When exact volume-free identity was absent from the normalization input, rows remained provisional/unclassified and fell into `.1/.2` or generic fractional candidate grouping.

Before editing product code, the 20-test disposable regression module exposed 11 failures and two missing-field errors. It reproduced loss of volume-free identity through the manifest-only path, acceptance of stale/incompatible reference volume fields, bare-key promotion, contradictory taxonomy promotion, and missing per-acquisition provenance. A fully eligible Wikipedia positive fixture already passed before repair; this report does not claim that the original pattern loops overrode a row already successfully recognized as main.

No supported VIZ reference adapter was found in the inspected runtime path. The supplied official-chapter observation motivates the synthetic regression; this task adds no VIZ scraper and makes no claim to have acquired today's live SPY x FAMILY identities.

## Exact changed and added files

Changes are compared with a task-local baseline taken after the reference-integrity repair. Pre-existing plugin worktree modifications are not attributed to this task.

| File | Change and reason |
| --- | --- |
| `C:\MangaNana-Dev\MangaNana-calibre\publication_specials.py` | Changed. Add `canonical_publication_records()` beside the existing shared taxonomy. Reuse trusted Wikipedia records, current eligible MangaDex mappings, and existing recognized-special resolution; retain exact identity/provenance without requiring volume membership. |
| `C:\MangaNana-Dev\MangaNana-calibre\publication_manifest.py` | Changed. Import that helper and add current `publication_records` to runtime JSON. Existing reference-integrity reconciliation, projection, freshness and special logic remain unchanged. |
| `C:\MangaAnka DDK\ddk_chapter_normalization.py` | Changed. Consume manifest identities before candidate grouping, prevent fractional promotion from bare keys/legacy volume fields, preserve per-acquisition explanation/provenance, and keep unresolved acquisitions reviewable. |
| `C:\MangaNana-Dev\MangaNana-calibre\tests\test_publication_identity.py` | Added. 17 shared-core identity/eligibility tests. |
| `C:\MangaAnka DDK\tests\test_artifact_authority.py` | Added. 23 deterministic classification, provenance, residual-candidate and history tests. |
| `C:\MangaAnka DDK\tests\fixtures\artifact_authority_pattern.json` | Added. Synthetic official-fraction-shaped positive fixture plus unsupported 100.1/100.2 residue. |
| `C:\MangaAnka DDK\tests\smoke_packaged_artifact_authority.py` | Added. External offline checks of embedded DDK modules, current live shared core and regression fixtures. |
| `C:\MangaAnka DDK\DDK_ARTIFACT_AUTHORITY_VALIDATION.md` | Added. This report. |
| `C:\MangaAnka DDK\dist\MangaAnka-Database-Development-Kit.exe` | Rebuilt primary Qt EXE from current source using the unchanged spec. |

Generated evidence is under `C:\MangaAnka DDK\build`: `artifact-authority-baseline`, `validate_artifact_authority.py`, `artifact-authority-validation.json`, and task-specific test/build logs. The baseline includes 92 protected top-level product-source hashes and three exact unified product diffs. Exactly three product files changed in that comparison.

`ddk_publication.py`, `ddk_review.py`, `ddk_duplicate_projection.py`, `ddk_curated_resolution.py`, MangaDex parsing/cache integrity, reference service adapters, and the other protected product sources were not edited. No UI, spec, launcher, schema, grammar, acceptance, Working Set, writer-lock, search/ranking, Atsu, artwork, download/output, or page-processing change was made. No commit, push, tag, release, version bump, reset or clean was performed.

## Classification before and after

Before: acquisition grouping -> equivalence check -> special lookup / reference volume or bare main key / existing provider corroboration -> residual numbering candidates.

After: shared current exact compatible main/special identity -> existing acquisition equivalence/duplicate checks -> supported main or recognized special classification with provenance -> existing independent provider corroboration where applicable -> residual numbering candidates -> unresolved records remain reviewable.

The shared helper:

- Reuses `trusted_wikipedia_records()` for work/title, edition, language, contract, collection, refresh and provenance eligibility. A trusted exact chapter/uncollected identity may exist without a known volume.
- Uses current valid unambiguous MangaDex explicit mappings in the matching work and compatible structural edition family. Its established shared-numbering policy remains language-independent; that basis is explicitly recorded. Wikipedia language-specific evidence must match the requested language.
- Rejects stale/failed refreshes, incompatible contexts, internally conflicting memberships and conflicting main/special taxonomy as promotion evidence. A compatible independent source can still provide eligible fallback evidence.
- Reuses `canonical_special_records()` rather than introducing a second special taxonomy. An untyped MangaDex volume mapping does not override a recognized Wikipedia special.
- Does not expand a range bundle into a new canonical acquisition identity, derive neighboring identifiers, use chronology/page counts, or infer revised-copy semantics.

Normalization no longer uses a reference volume field or a bare caller-provided key alone to promote a fractional row. Integer legacy behavior and existing independent-provider corroboration are preserved. Recognized main/special rows cannot enter residual artifact groups. If acquisition copies disagree, they remain unclassified/reviewable; a known publication key prevents a misleading syntax diagnosis without declaring the acquisitions equivalent.

Supported identity does not resolve a chapter-to-volume conflict. Both main identity claims can survive while the earlier reference-integrity repair keeps volume membership unresolved and reports `REFERENCE_CONFLICT`.

There is no `provider_split_shadow` rule. Unsupported pairs and unknown fractions retain current blocking/review behavior. Health and CODE-problem policy were not changed.

## Provenance and immutability

`manifest.runtime_publication.publication_records` retains exact eligible source records. `normalization.publication_identity_rows` aligns with acquisition rows and records:

- original provider identifier, acquisition record ID and URL when supplied;
- acquisition provider and normalized canonical identifier;
- main or recognized-special classification, including duplicate indication;
- trusted source record/page, confidence and available claimed volume evidence;
- explicit reason why exact trusted publication identity suppresses provider-pattern classification.

These fields persist in the existing publication JSON; no schema migration is needed. Raw acquisitions, source bundles and source snapshots are not rewritten. Existing projection IDs/URLs survive. Equivalent repeated acquisitions contribute one logical supported unit while retaining both acquisition records and provenance. Conflicting acquisition copies retain their existing safety checks.

A new audit recomputes identity from current evidence. Gaining eligible evidence promotes the new audit; losing eligibility returns its fractional records to conservative classification. The disposable history test saves three distinct immutable audits and compares the entire original serialized audit row after later saves. The original row remains identical. The shared refresh test also confirms that the prior manifest remains unchanged when current eligible identities disappear.

## Regression results

The synthetic SPY x FAMILY-style fixture includes 58, 58.1, 58.2, 58.3, 59, 67, 67.1, 67.2, 68, 100, 100.1 and 100.2. Eligible exact publication evidence recognizes the five fractions 58.1, 58.2, 58.3, 67.1 and 67.2.

- All five supported fractions classify as main, retain acquisition provenance, and are absent from split/fraction candidate groups.
- Unsupported 100.1 and 100.2 remain `provider_split_candidate`. The residual group contains exactly those two identifiers, and persisted code-review grouping contains exactly two candidate records.
- An isolated eligible fraction beats generic fractional syntax. An isolated unknown decimal remains `provider_fractional_candidate`.
- Base chapter existence does not suppress independently recognized fractions.
- Fractional omake records classify as recognized specials, retain existing taxonomy and membership behavior, and create no syntax-only candidate warning.
- Incompatible work/edition/language, stale/failed/quarantined evidence and contradictory main/special taxonomy do not rescue unsupported fractions.
- Component integer identities do not promote `1-3`: it remains `provider_range_bundle`. V2 identifiers retain conservative unclassified behavior. Range-bundle and revised-copy policies were not broadened.
- Supported repeated equivalent acquisitions count once. Non-equivalent copies remain unclassified and reviewable.

The completed Chainsaw-pattern reference-integrity regression remains 232 canonical main chapters, 230 mapped main, two unmapped main, direct conflicts at 203/232, and one aggregate `REFERENCE_CONFLICT`; dependent 203.1/203.2 memberships remain unresolved. Health remains PASS / REVIEW / REVIEW / PARTIAL. A new fractional-main disagreement test also proves that supported identity leaves disputed volume membership unresolved.

Captured Dandadan regressions remain unchanged. The MangaPill fixture retains 246 main chapters, two recognized acquired specials, 248 logical units, two unresolved provider artifacts (26.5 and 193.1), 219 mapped main / 221 total mapped, 27 uncompiled main, zero unmapped main, and 25 released volumes. Health remains PASS / PASS / REVIEW / PARTIAL. The captured Atsu case retains its existing PASS / PASS / PASS / PARTIAL health. No new shadow policy was applied.

World Is Mine remains the clean structural control: 163 logical chapters, 14 derived volumes, 163 mapped, zero unmapped, and no holes.

## Validation and packaging

| Check | Result |
| --- | --- |
| New shared identity tests | 17 tests passed within the focused suite. |
| Focused shared-core suite | 251 tests passed in 3.408 seconds. |
| New DDK classification-authority tests | 23 tests passed in both full-suite and packaged runs. |
| Full DDK suite | 375 tests passed in 91.532 seconds on final source. |
| Static/source-diff checks | AST parsing, in-memory compilation and trailing-whitespace checks passed for six source/test Python files. Protected-source comparison found exactly three product changes. Scoped plugin diff check passed. |
| EXE rebuild | Passed; unchanged PyInstaller spec and primary Qt entry point. |
| Packaged offline checks | 30 tests passed in 1.757 seconds. |

Focused shared modules: `test_publication_identity`, `test_reference_integrity`, `test_mangadex_structure_reference`, `test_publication_manifest`, `test_patch1c_publication`, `test_mangadex_special_metadata`, `test_publication_specials`, `test_publication_freshness`, `test_reference_integration`, `test_wikipedia_collection`, `test_unified_volume`, and `test_reference_language_order`.

The full DDK suite includes existing Qt, normalization, reference-integrity, canonical-special, freshness, curation/acceptance, working-set and transaction-repair regressions. Every database used by tests is disposable; network calls are fake/offline and new tests guard against unexpected urllib requests.

Validation commands used `C:\MangaAnka DDK\.venv-qt\Scripts\python.exe`:

```text
-m unittest <the 12 focused shared modules above> -q
-m unittest discover -s tests -p test_*.py -q
build\validate_artifact_authority.py
-m PyInstaller --noconfirm --workpath build\artifact-authority-pyinstaller MangaAnka-Database-Development-Kit.spec
tests\smoke_packaged_artifact_authority.py dist\MangaAnka-Database-Development-Kit.exe
```

Shared-core checks used `PYTHONPATH=C:\MangaNana-Dev\MangaNana-calibre` and the plugin working directory. The build ran with approved access to the installed Tcl/Tk runtime required by the unchanged spec. No packaging guard was bypassed.

The packaged runner compares seven embedded module code objects to compiled current source: `ddk_chapter_normalization`, `ddk_publication`, `ddk_curated_resolution`, `mangaanka_database_development_kit`, `ddk_catalog`, `ddk_acceptance`, and `qt_app.workers`. All match. It runs the 23 authority tests, five reference-integrity audit tests and two captured Dandadan tests using embedded DDK code and the current live shared core. Archive checks confirm no frozen shared-core submodules and no SQLite database payload. This verifies packaged code and offline behavior, not native GUI launch.

Final EXE: `C:\MangaAnka DDK\dist\MangaAnka-Database-Development-Kit.exe`.

- Size: 52,512,956 bytes.
- SHA-256: `1bdfd733a9a8afe188b6e7834663c727c5d85bc6e32158ee2a032029a0730ca8`.

Primary launcher remains `C:\MangaAnka DDK\Launch_MangaAnka_DDK.bat`; legacy Tk fallback remains intact. No launcher/spec/font/UI source changed.

## Deliberately skipped checks and remaining limitations

- No production database, live title audit, live export, or full corpus/network audit was opened or run. No claim is made that current live SPY x FAMILY reference coverage is sufficient to recognize these fractions.
- No official-publisher scraping adapter or hardcoded chapter list was introduced. Unsupported residue remains for later investigation.
- The entire plugin repository suite was not run; focused tests cover changed shared modules and protected publication controls.
- No native EXE GUI/bootloader, physical DPI/window, Calibre-library import, page-processing or download smoke was run. Qt/UI/output source did not change. Packaged archive-based tests are not interactive GUI tests.
- Historical audits are not retroactively rewritten. Restart the DDK and create a new audit to use current classification.
- Reference-sourced numeric identity remains evidence-dependent. This task cannot fact-check a consistently incorrect reference without independent evidence, or establish undocumented revised-copy/shadow semantics.

Schema 7, Grammar 3, DDK v0.3.0, acceptance/curation policy, Working Set/Force Re-Audit lifecycle, SQLite transaction handling, provider acquisition authority/ranking, Atsu grouping, canonical-special taxonomy, freshness/UNCOMPILED, reference-conflict policy, artwork and output behavior remain unchanged.

The production catalog `C:\Users\Jerry\Documents\MangaAnka-Database-Development-Kit\mangaanka_catalog.db` was never opened or mutated during automated work.

## Small user-operated retest

1. Close the DDK normally and launch the primary launcher. Explicitly select the intended catalog and working-set item.
2. Re-audit SPY x FAMILY using the existing workflow. Confirm the new audit preserves history and advances the selected pin only on success.
3. Inspect exact reference evidence and `publication_identity_rows`. Fractions with eligible exact evidence must be main/recognized special and absent from candidate groups; fractions lacking that evidence must remain reviewable. Do not assume the five synthetic identities are currently supplied by a runtime adapter.
4. Confirm unrelated publication mapping problems and reference conflicts remain visible. This repair should not clear the wider unmapped-chapter problem or silently create nonblocking shadows.
