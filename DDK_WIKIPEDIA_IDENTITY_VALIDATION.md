# Wikipedia structural-page identity repair

Date: 2026-10-05. Local worktrees are authoritative. DDK remains v0.3.0, SQLite schema 7, Grammar 3.

## Outcome and root cause

A unique exact compatible `List of <work> chapters` search result now represents the same work as its corresponding main-series article. Its original Wikipedia page title, ID and URL are preserved. It can resolve directly as the structural root and supply eligible exact publication records to the existing DDK classification pipeline.

Previously, `WikipediaPublicationAdapter.match_publication()` counted exact title/alias rows individually. Supplying both the series title and its chapter-list title as aliases could create two exact results and fail identity matching. Without a list alias, the matcher selected the main article instead of recognizing the list's work identity. The general comparison helper kept the typographic cross `×` distinct from a spaced `x`, so title matching and related-page traversal could disagree across otherwise compatible title spellings.

There was also a downstream boundary: `trusted_wikipedia_records()` compared the selected page title directly to canonical work titles, allowing the existing manga suffix but not the exact chapter-list wrapper. Merely selecting a chapter-list page upstream would therefore leave its records ineligible downstream.

These problems were reproduced with offline synthetic evidence before product edits. The initial 14-test module had nine failing assertions. No live Wikipedia, SPY x FAMILY audit, export or production database was used.

## Exact files changed or added

| File | Reason |
| --- | --- |
| `C:\MangaNana-Dev\MangaNana-calibre\wikipedia_identity.py` | Added Wikipedia-specific comparison helpers for typography and exact chapter-list/work roles. Global canonical normalization remains unchanged. |
| `C:\MangaNana-Dev\MangaNana-calibre\wikipedia_reference.py` | Changed matching, same-work structural-page comparison, subsection scope and exact-list fallback selection. Reject incompatible list redirects. Preserve original source/display strings. |
| `C:\MangaNana-Dev\MangaNana-calibre\publication_freshness.py` | Changed only imports and the Wikipedia trusted-record title-comparison helper. All freshness, release, UNCOMPILED and other eligibility rules remain unchanged. |
| `C:\MangaNana-Dev\MangaNana-calibre\tests\test_wikipedia_identity.py` | Added 21 offline identity, typography, ambiguity, edition, redirect and reference-service tests. |
| `C:\MangaAnka DDK\tests\test_wikipedia_page_identity.py` | Added one end-to-end real-adapter -> reference service -> manifest -> DDK fractional-classification test. |
| `C:\MangaAnka DDK\tests\smoke_packaged_artifact_authority.py` | Added an optional `--wikipedia-identity` check to the external packaged-test runner; its default 30-test behavior remains. |
| `C:\MangaAnka DDK\DDK_WIKIPEDIA_IDENTITY_VALIDATION.md` | Added this report. |

Generated evidence is under `C:\MangaAnka DDK\build`: `wikipedia-identity-baseline`, `validate_wikipedia_identity.py`, `wikipedia-identity-core-tests.log`, `wikipedia-identity-full-tests.log` and `wikipedia-identity-packaged-tests.log`.

The task-local baseline records 92 pre-existing top-level Python product-source hashes. Only `wikipedia_reference.py` and `publication_freshness.py` changed among those files. `wikipedia_identity.py` is the sole new product module. Two exact baseline diffs distinguish these edits from pre-existing plugin worktree changes. No DDK product source changed.

## Resolution policy

- Typography comparison remains Unicode/case/punctuation/whitespace aware. The added bounded equivalence maps a literal `×` between words to a spaced `x`. It does not remove arbitrary symbols, accents or word gaps, or introduce fuzzy matching.
- Only the exact anchored `List of <work> chapters` role is unwrapped for work comparison. Edition descriptors, subtitles and year qualifiers are retained. A spinoff prefix is not an exact work identity.
- A compatible unique chapter-list result takes precedence over the corresponding series article. Repeated results with the same page ID do not create another identity candidate.
- Different exact work/alias identities or two distinct eligible chapter-list page IDs remain ambiguous. Typography equivalence alone cannot select between two different pages.
- Existing edition compatibility guards apply to selected exact rows and structural fallback candidates. Incompatible omnibus/color pages cannot be promoted through a list alias. Distinct plausible edition titles remain ambiguous.
- A corresponding `(manga)` article alone does not defeat the chapter-list page. When a bare homonym article and a manga-disambiguated article also compete, existing creator corroboration remains required unless the supplied exact identity explicitly selects the manga-disambiguated title.
- The existing secondary structural search can prefer one exact compatible list over same-work segment pages. Multiple exact list variants remain unresolved. Unsupported layouts still require existing explicit structure parsing; page-name syntax alone never invents chapters or volumes.
- An exact list match that redirects to another work or incompatible edition yields `ambiguous_identity` and no chapter/volume rows.
- Downstream trusted-record eligibility uses the same Wikipedia work-title comparison. Work identity, edition, language, cache contract, confidence, stale/failed refresh checks, collection quarantine, provenance and validation requirements remain intact.

The original Wikipedia page title, source page/record identifiers, URL, chapter labels and acquisition records are not rewritten. No series name or chapter number is hardcoded into runtime logic.

## Validation

| Check | Result |
| --- | --- |
| New shared Wikipedia identity module | 21 tests passed within focused suite. |
| Focused shared-core suite | 315 tests passed in 3.759 seconds. |
| New DDK end-to-end check | One test passed, also included in full and packaged checks. |
| Full DDK suite | 376 tests passed in 88.699 seconds. |
| Packaged offline checks | 31 tests passed in 1.957 seconds. |
| Static checks | AST parsing, in-memory compilation and no newly introduced trailing whitespace passed for six source/test Python files. Scoped plugin `git diff --check` passed. Existing unrelated whitespace was preserved. |

Focused modules: `test_wikipedia_identity`, `test_reference_metadata_prototype`, `test_publication_identity`, `test_reference_integrity`, `test_mangadex_structure_reference`, `test_publication_manifest`, `test_patch1c_publication`, `test_mangadex_special_metadata`, `test_publication_specials`, `test_publication_freshness`, `test_reference_integration`, `test_wikipedia_collection`, `test_unified_volume`, and `test_reference_language_order`.

Commands used `C:\MangaAnka DDK\.venv-qt\Scripts\python.exe`, with `PYTHONPATH=C:\MangaNana-Dev\MangaNana-calibre` for focused plugin checks:

```text
-m unittest <the 14 focused shared modules above> -q
-m unittest discover -s tests -p test_*.py -q
tests\smoke_packaged_artifact_authority.py dist\MangaAnka-Database-Development-Kit.exe --wikipedia-identity
build\validate_wikipedia_identity.py
```

The end-to-end fixture uses the actual Wikipedia adapter and reference service. Search returns both a main-series article and its exact chapter-list alias. The list becomes the selected source; explicit fractional chapters classify as supported main units, stay out of artifact groups and retain their acquisition IDs and source-page provenance. Only one search request is needed in that fixture.

Negative tests cover different work aliases, distinct page IDs despite equivalent typography, spinoffs, incompatible editions, competing plausible edition titles, namespace lookalikes, unresolved homonyms and redirects to another work/edition. Positive tests cover list-only lookup, main/list collision, typographic crosses with and without spaces, Unicode spaces, repeated same-page search results, compatible manga article roles, subsection scoping and existing main-only behavior.

All prior classification-authority, reference-integrity, Dandadan canonical-special, World Is Mine, acceptance/history, working-set, Qt and transaction-repair DDK regressions pass. The packaged checks include the prior 30 artifact-authority/reference-integrity/captured-Dandadan cases plus the new adapter-to-classification case.

## Packaging and preserved contracts

The current primary EXE at `C:\MangaAnka DDK\dist\MangaAnka-Database-Development-Kit.exe` passed archive-based offline validation with this live shared-core repair. Seven embedded DDK module code objects match current DDK source, and no frozen shared-core submodules or database payload are present.

No EXE rebuild was required or performed in this task: bundled DDK product source is unchanged, and the existing `mangaanka_search_core` loader reads the current plugin worktree, including the new helper module. The tested current EXE SHA-256 is `847d9971be1169d665788695c57bc4e6fa8e1f3939e73d4747aade7d29bd3946`.

Primary launcher, legacy Tk fallback, PyInstaller spec, Qt UI/fonts, database schema, Grammar 3, version, acceptance/curation policy, Working Set and Force Re-Audit lifecycle, locking, search/provider ranking, Atsu grouping, acquisition authority, artwork/output, canonical-special taxonomy and reference-conflict policy were not changed. Publication freshness changed only its Wikipedia title-comparison dependency; release/UNCOMPILED rules remain untouched.

No cache-contract version, TTL, schema migration, global cache purge or forced-network policy was introduced. Existing valid reference caches can still be used normally. Previously failed/ambiguous matching is reevaluated through the ordinary lookup path; the repair does not rewrite historical audit JSON.

No commit, push, tag, release, version bump, reset, clean or broad reformat was performed. The entire plugin suite was not run; validation was focused on the affected shared path and its protected controls.

## Limits and short manual retest

There was no live Wikipedia/provider audit, production-catalog access, native EXE GUI/bootloader smoke, physical DPI check or Calibre-library operation. Packaged checks verify archive code and offline behavior, not interactive GUI launch. The current live SPY x FAMILY page content/coverage has not been verified, and this repair does not guarantee that every missing structural chapter is solved.

Restart the DDK to reload shared source. Select the intended catalog and exact working-set item yourself, then run the normal re-audit workflow. Inspect the new audit's Wikipedia match and source-page provenance: a unique compatible exact chapter-list page should resolve without the corresponding series article causing artificial ambiguity. Genuine work/edition conflicts should remain unresolved. Check that fractional identities are supported only when current eligible reference records recognize them, and that old audits/history remain intact.

The production catalog `C:\Users\Jerry\Documents\MangaAnka-Database-Development-Kit\mangaanka_catalog.db` was never opened or mutated during automated development or validation.
