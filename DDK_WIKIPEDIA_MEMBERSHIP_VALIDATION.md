# Wikipedia chapter-membership extraction repair

Date: 2026-10-06. Local DDK and shared-plugin worktrees were inspected before editing. The only product-source change in this task is `wikipedia_reference.py`; DDK product source is unchanged.

## Root cause and exact path

`ReferenceMetadataService.lookup()` resolves Wikipedia identity correctly, then calls `WikipediaPublicationAdapter.resolve_publication()`. For a validated Graphic novel list page, `_segment_from_page()` obtains records from `_parse_graphic_lists()` and `_parse_uncollected_chapters()` and attaches source provenance. The reference service serializes these through `_wikipedia_result()` for the existing manifest, canonical publication identity, acquisition normalization, projection and publication-state layers.

The balanced template reader and `ChapterList` field reader already retain the affected source text. The loss occurred afterward: `_parse_graphic_lists()` accepted Numbered list templates, ordered lists, `*31. Title`, and `*Chapter 31: Title`, but not `*Mission: 31–37`. The dedicated uncollected-section parser had the same missing form. Volume metadata was independently parsed, explaining why volumes were present while chapters were empty.

The public MediaWiki parse response was inspected, rather than deriving syntax from rendered HTML. Captured page ID: **70835375**; revision ID: **1375646933**. Its volume 6 `ChapterList` contains `*Mission: 31–37` and `*Short Mission: 4`. Volume 17 contains `*Mission: 119–127` and a comma/range Short Mission list. The dedicated section is headed `Chapters not yet in ''tankōbon'' format` and contains `*Mission: 128–140.1` plus `*Short Mission: 19`. Volume 18 has an empty chapter field and a November 4, 2026 release date, which is future relative to this validation date. [Public source page](https://en.wikipedia.org/wiki/List_of_Spy_%C3%97_Family_chapters)

The public snapshot is separate from the protected catalog and historical live audits. No production audit was opened or rerun.

## Exact files changed or added

| File | Change |
| --- | --- |
| `C:\MangaNana-Dev\MangaNana-calibre\wikipedia_reference.py` | Modified: bounded explicit labeled membership parsing; typed uncollected identity comparison; ambiguous duplicate same-work subsection rejection; internal parser version 7. |
| `C:\MangaNana-Dev\MangaNana-calibre\tests\test_wikipedia_membership.py` | Added: 21 deterministic parser, namespace, provenance, conflict, scope, decimal, range-bound and cache regressions. |
| `C:\MangaNana-Dev\MangaNana-calibre\tests\fixtures\wikipedia_labeled_membership.wiki` | Added: generic 17-volume main/supplementary layout, empty future volume 18 and exact integer uncollected tail. |
| `C:\MangaAnka DDK\tests\test_wikipedia_membership_audit.py` | Added: seven real-adapter/reference-service/manifest/DDK integration checks. |
| `C:\MangaAnka DDK\tests\smoke_packaged_artifact_authority.py` | Modified: optional `--wikipedia-membership` checks in the external archive-based offline runner. Default checks remain intact. |
| `C:\MangaAnka DDK\DDK_WIKIPEDIA_MEMBERSHIP_VALIDATION.md` | Added: this report. |

Generated inspection and validation evidence under `C:\MangaAnka DDK\build`:

- `wikipedia-membership-public-inspection.json`: captured public MediaWiki response.
- `wikipedia-membership-baseline\wikipedia_reference.py`: pre-edit parser copy.
- `wikipedia-membership-baseline\protected-hashes.json`: 93 protected product-source hashes.
- `wikipedia-membership-baseline\wikipedia_reference.py.diff`: exact task-local parser diff, excluding pre-existing repairs.
- `validate_wikipedia_membership.py`: static/hash checks and offline public-snapshot before/after replay.
- `wikipedia-membership-public-replay.json`: structured replay results.
- `wikipedia-membership-core-tests.log`, `wikipedia-membership-full-tests.log`, `wikipedia-membership-packaged-tests.log`, `wikipedia-membership-static.log`: validation output.

## Membership semantics

New syntax is recognized only in existing Graphic novel list `ChapterList*` fields or existing explicitly uncollected sections. Supported main labels are Chapter, Episode, Round and Mission; supported supplementary labels are Short Mission and Extra Mission. Arbitrary numbered prose and unsupported labels do not become main chapters. No title, provider, count or volume boundary is hardcoded into runtime logic.

Integer ranges reuse `publication_manifest._explicit_chapter_range()` and its existing maximum span of 200. Whole comma lists are bounded to 201 expanded records and parsed atomically: a malformed, reversed, oversized or partially unknown expression cannot promote its valid prefix. Equivalent duplicate evidence remains equivalent. Incompatible overlapping volume assignments reach existing manifest ambiguity/conflict handling.

Explicit individual decimal identifiers use the existing string/Decimal normalization helper; no float arithmetic is introduced. Mixed integer/decimal ranges such as `128–140.1` are retained as nonnumeric evidence with their original expression and source provenance. They are not expanded into guessed main units or decimal intermediates. Uncollected unresolved expressions use `kind=uncollected_range` and an empty volume.

Safely parsed supplementary records use source-local labels such as `Short Mission 4`, `kind=special`, explicit volume membership when present, source page/revision and record identity. Label case is preserved. They do not become main chapter 4 or a fabricated provider fraction. Existing canonical-special machinery does not assign numeric acquisition aliases to these nonnumeric labels; raw reference evidence remains available for inspection. Unsupported supplementary ranges remain labeled supplementary range evidence.

Exact integer uncollected rows use `kind=uncollected` with no volume. The existing freshness layer alone decides whether these are UNCOMPILED. No future-volume assignment, release-boundary relaxation or gap filling was added. An empty future or listed volume row neither supplies chapter membership nor becomes a released volume through table presence.

Uncollected override comparison now uses the existing `_chapter_identity()` rather than a set of numeric normalizations. This avoids treating every nonnumeric supplementary label or unresolved expression as the same `None` identity, which otherwise could drop unrelated collected supplementary evidence. Exact duplicate main/supplementary identities can still be superseded by explicit uncollected evidence. Multiple same-work subsection candidates now yield no scoped records instead of selecting the first arbitrarily.

## Before and after

Before implementation, the new 16-case initial parser regression reproduced the bug: nine failures and three errors, chiefly because expected chapter records were absent. Four negative cases already passed.

The same captured public source was replayed offline through the saved parser version 6 and repaired version 7:

| Public-snapshot extraction | Before | After |
| --- | --- | --- |
| Status | `supported_empty` | `valid_with_data` |
| Raw volume metadata rows | 18 | 18 |
| Explicit compiled main records | 0 | 127 |
| Labeled supplementary records | 0 | 21 |
| Safely expanded main uncollected records | 0 | 0 |
| Mixed tail evidence | Dropped | `128–140.1`, `uncollected_range`, no volume |

These are parser results, not final live-audit counts. Eighteen raw volume metadata rows do not mean eighteen released/final volumes. The actual mixed decimal tail remains conservative; no synthetic integer tail is substituted for it.

The generic deterministic fixture instead explicitly lists integer uncollected range 128–134. Through the real reference service and DDK pipeline it produces **134 canonical main units, 127 mapped main, seven UNCOMPILED, zero unmapped, 17 final volumes**. Supplementary evidence remains separate. The fixture with mixed tail `128–140.1` instead retains seven acquired tail chapters as unmapped and marks none UNCOMPILED, demonstrating that source uncertainty is not hidden.

## Cache behavior

Only the internal Wikipedia parser version changes: **6 → 7**. Product version remains v0.3.0. Pattern IDs and cache contracts remain `graphic-novel-list-explicit-chapter-list-v1`, `segmented-publication-collection-v1`, `wikipedia-structure-v3-collection` and `wikipedia-segment-v1`.

The existing version-aware outer/segment cache machinery invalidates old incompatible entries and reparses through the normal lookup path. Tests seed both old empty and old nonempty outer entries, confirm refresh after invalidation, then confirm a current-version cache hit with identical serialized evidence. An old version-6 segment cannot hide repaired memberships; current-version segment reuse preserves provenance.

`supported_empty` was already ineligible for trusted cache reuse. The bump also addresses old partially parsed nonempty results, not just empty results. No TTL change, global purge, forced-network policy or schema migration was introduced. Historical audit JSON is not rewritten.

## Validation

| Check | Result |
| --- | --- |
| New shared membership tests | 21 passed, included in focused suite. |
| Focused shared-core suite | 336 passed in 4.943 seconds. |
| New DDK integration tests | Seven passed, included in full and packaged checks. |
| Full DDK suite | 383 passed in 111.296 seconds on final source. |
| Packaged offline checks | 38 passed in 3.377 seconds. |
| Static/compile checks | Five Python files passed AST parsing/in-memory compilation and no newly introduced trailing whitespace. |
| Protected product-source hashes | 93 checked; only `wikipedia_reference.py` changed. |
| Scoped plugin diff check | Passed; only Git's line-ending advisory was emitted. |

Focused shared modules: `test_wikipedia_membership`, `test_wikipedia_identity`, `test_reference_metadata_prototype`, `test_publication_identity`, `test_reference_integrity`, `test_mangadex_structure_reference`, `test_publication_manifest`, `test_patch1c_publication`, `test_mangadex_special_metadata`, `test_publication_specials`, `test_publication_freshness`, `test_reference_integration`, `test_wikipedia_collection`, `test_unified_volume`, `test_reference_language_order`.

Checks use `C:\MangaAnka DDK\.venv-qt\Scripts\python.exe`, with the plugin root in `PYTHONPATH` for shared tests:

```text
-m unittest <the 15 focused modules above> -q
-m unittest discover -s tests -p test_*.py -q
tests\smoke_packaged_artifact_authority.py dist\MangaAnka-Database-Development-Kit.exe --wikipedia-identity --wikipedia-membership
build\validate_wikipedia_membership.py
```

The new integration tests exercise actual labeled parsing rather than injecting prebuilt Wikipedia chapter rows. They prove integer-tail freshness, exact fractional identity priority over provider syntax, no invented Short Mission aliases, MangaDex agreement/disagreement, provider-explicit precedence, internal-gap review, and preserved stale/failed/quarantined reference behavior. Existing reviewed/verified curation and acceptance/history controls remain in the full/focused suites.

The captured MangaPill Dandadan control remains **246 main, two recognized acquired specials, 248 logical units, two unresolved provider artifacts (`26.5`, `193.1`), 219 mapped main/221 total mapped, 27 UNCOMPILED, zero unmapped main, 25 final released volumes**. The nine missing recognized specials remain acquisition-only. Health remains identity PASS, publication PASS, normalization REVIEW, acquisition PARTIAL. The captured Atsu alternative-group control also passes unchanged.

The World Is Mine control remains **163 logical chapters, 14 final derived volumes, 163 mapped, zero unmapped and no holes**. Existing reference-integrity tests retain conflict quarantine and safe provider/curation precedence; the new labeled-membership conflict is not hidden by derivation. Existing artifact-authority tests continue to distinguish explicit trusted fractional main identities from unsupported provider residue.

## Packaging, safety and remaining limits

No rebuild was necessary or performed. The current EXE is `C:\MangaAnka DDK\dist\MangaAnka-Database-Development-Kit.exe`; primary launcher remains `C:\MangaAnka DDK\Launch_MangaAnka_DDK.bat`. Its live shared-core loader uses the current plugin worktree. The packaged runner verifies seven embedded DDK module code objects against current source, absence of frozen shared-core submodules/database payload, then runs the offline checks using embedded DDK modules and live shared core.

Tested EXE SHA-256: `275a1d8edc811d31b160ae71d72f03512e67ace13b00b2d0bb8dd87333f2864f`.

The production catalog `C:\Users\Jerry\Documents\MangaAnka-Database-Development-Kit\mangaanka_catalog.db` was **never opened or mutated**. Catalog/cache tests use disposable paths. No live audit, curation, acceptance or pin was changed automatically.

DDK v0.3.0, schema 7, Grammar 3, Wikipedia identity policy, MangaDex aggregation/cache, BookWalker release policy, canonical specials, provider/artifact authority, verified curation, acceptance, Working Sets/Force Re-Audit, immutable history, SQLite transaction repair, search/ranking, Atsu grouping, Qt/Tk launchers, packaging spec/fonts, artwork/download/output remain unchanged. No commit, push, tag, release, product version bump, reset, clean or broad reformat was performed.

The full plugin suite was not run. No native EXE GUI/bootloader smoke, physical DPI/window check or Calibre-library operation was performed in this parser-only task. Packaged validation is archive-based offline validation. New layouts/labels outside the bounded parser contract remain unsupported. Mixed decimal ranges and unproven supplementary acquisition aliases remain unresolved. A fresh live audit may still expose provider residue, missing acquisitions, conflicts or uncompiled uncertainty; this repair does not target a forced PASS or promise a final live chapter count.

## Short user-operated SPY x FAMILY retest

1. Close and restart DDK through the primary launcher so it reloads shared source. Select the intended catalog yourself.
2. Select the exact SPY x FAMILY working-set item; run **More → Force Re-Audit Selected** once.
3. In the new audit, verify the compatible chapter-list identity remains selected, Wikipedia parser version is 7, status is no longer empty merely because of labeled ranges, and main membership provenance is present across early/middle/late volumes. Inspect `31–37 → volume 6` when that evidence still exists.
4. Check final mapped/unmapped/UNCOMPILED counts and release evidence. Future/listed volume 18 must not receive a guessed tail; Short Mission labels must not become main numbering or invented provider decimals. Any unresolved `128–140.1` evidence and provider questions should remain visible.
5. Confirm the new immutable audit/pin advances normally on success and the old Audit 37 revision 2/history remains available. Do not curate missing chapters merely to mask extraction uncertainty.
