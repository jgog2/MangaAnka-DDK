# Haikyu!! MangaK provider-artifact investigation

Investigation date: 2026-10-06. Local worktrees were inspected as the behavioral source of truth. No production catalog was opened. Input was the user-supplied `C:\Users\Jerry\Documents\MangaAnka-Database-Development-Kit\export.json`.

## Conclusion

The findings expose unreliable identifiers and mixed content in MangaK's `/haikyu` listing. They are not evidence that 102 canonical chapters need volume corrections, nor proof of 16 genuinely split chapters. The inspected software preserves the provider's labels and correctly withholds canonical identity from unresolved records.

No safe generic runtime repair was established. In particular, merging paired decimals, dropping decimals, treating them all as specials, using MangaK's internal upload index as a chapter number, or clearing CODE after choosing a different provider would conceal real identity risks. No runtime or policy change was made, and no CODE finding was suppressed or reclassified.

This investigation does **not** identify every one of the 102 records conclusively. It establishes several distinct content types and disproves a single benign explanation for the whole set. Individual unresolved identities remain unresolved.

## Captured audit

Haikyu!!, work 20, Audit 40 revision 1, working set Batch 004; item `0d76561f-114f-4165-9d4c-38bf99a4d2ed`.

| Property | Captured value |
|---|---:|
| Selected source | MangaK, `/haikyu`, title ID `08AG9bBD` |
| Raw acquisition records | 511 |
| Normalized main records | 408 |
| Fractional candidates | 86 |
| Split candidates | 16 |
| Unclassified acquisitions | 1: chapter `0` |
| Logical / mapped / unmapped | 408 / 408 / 0 |
| Final volumes | 45 |
| Exact trusted Wikipedia publication identities | 402 |
| Recognized reference specials | 0 |
| MangaDex structural status | `no_structure` |

The two CODE problem rows aggregate 102 affected records. Chapter zero has a separate `UNCLASSIFIED_ACQUISITION` finding. Captured health is identity PASS, publication PASS, normalization REVIEW, acquisition PASS. Complete volume mapping does not certify the contents of every acquisition.

The 16 split-candidate identifiers are `1.1`, `1.2`, `2.1`, `2.2`, `3.1`, `3.2`, `4.1`, `4.2`, `5.1`, `5.2`, `125.1`, `125.2`, `199.1`, `199.2`, `331.1`, `331.2`.

Six additional fractional keys currently classify as main through two independent provider inventories: `125.5`, `153.5`, `207.5`, `402.1`, `402.2`, `402.3`. That describes existing software evidence, not a research determination that these are canonical main chapters or recognized specials. The supplied export does not contain the full peer chapter inventories; the regression explicitly models those peer keys synthetically.

## What the reader content shows

Public MangaK inventory metadata and 31 selected reader metadata records were captured using the current shared adapter. Opening pages were examined for selected records. The following are direct observations, with uncertainty preserved:

| MangaK label | Observed opening content | Implication |
|---|---|---|
| [1.1](https://mangak.io/haikyu/chapter-1-1) | Bonus-story opening | A decimal can identify extra material; its canonical special identity is not established by the label. |
| [1.2](https://mangak.io/haikyu/chapter-1-2) | Printed chapter 213 | Not the second half of chapter 1. The integer 213 upload opens with a colored version of the same scene. |
| [2.1](https://mangak.io/haikyu/chapter-2-1) | Printed chapter 41 | Not the first half of chapter 2. The integer 41 upload opens with a colored version of the same chapter illustration. |
| [2.2](https://mangak.io/haikyu/chapter-2-2) | Printed chapter 49 | Provider label and visible main-chapter identity disagree. |
| [2.3](https://mangak.io/haikyu/chapter-2-3) | Printed chapter 58 | Same kind of numbering mismatch. |
| [2.9](https://mangak.io/haikyu/chapter-2-9) | Printed chapter 180 | Same kind of numbering mismatch. |
| [6.1](https://mangak.io/haikyu/chapter-6-1) | Printed chapter 244 | Same kind of numbering mismatch. |
| 16.1 / 16.5 | Matching bonus-story opening and second sampled page | Duplicate-looking uploads; full content equivalence not established. |
| 125.1 / 125.2 | Matching crossover opening and second sampled page | Evidence against interpreting them as two split halves; full equivalence not established. |
| 199.1 / 199.2; 331.1 / 331.2 | Matching bonus openings and second sampled pages | Same caution about duplicates versus split chapters. |
| 125.3 / 125.6 | Similar bonus opening, different dimensions/layout | Insufficient evidence to collapse the uploads. |
| [402.5](https://mangak.io/haikyu/chapter-402-5) | Explicit special-one-shot title page | Real extra material is present, but provider numbering alone cannot establish trusted canonical identity. |
| [0](https://mangak.io/haikyu/chapter-0) | Illustrated opening unlike the main-series chapter openings, apparently fan-work material | Do not treat integer zero as independently verified main-chapter content. Exact work identity was not established. |

First-two-page comparisons for the duplicate-looking pairs are visually close but not byte-identical; full image URL sequences also differ. This is research evidence, not authorization for a perceptual-hash deduplication rule. Printed numbers establish a mismatch, not complete page-for-page equivalence with integer uploads. The listing contains both black-and-white and colored sampled pages; its title metadata is insufficient to certify a uniform edition.

The export also lists a second MangaK result, `Haikyuu!!` at `/haikyuu`, ID `G8nV4l8e`. A focused public metadata check found 448 records, including named specials and a notice. Its inventory was not substituted or treated as verified clean. This is a distinct provider listing, not a spelling correction to the selected reader URL.

## Code trace and why the warnings occur

1. `mangaanka_search_core/__init__.py` loads the shared local plugin implementation. This investigation used `C:\MangaNana-Dev\MangaNana-calibre\mangak_source.py`, rather than assuming the DDK's fallback snapshot was active.
2. `MangaKSource.get_chapters()` parses the display name. The API and reader metadata themselves name the sampled records `Chapter 1.2`, `Chapter 2.1`, etc. Their API `number` values are internal upload indexes, not corrective chapter identities. There is no demonstrated decimal-parsing error.
3. `ddk_publication.resolve_publication()` builds the shared publication manifest and projection, then invokes `normalize_acquisition()` with reference and provider evidence.
4. `ddk_chapter_normalization.normalize_acquisition()` considers exact trusted publication identities, recognized specials, and independent provider corroboration before residual syntax. Unresolved unique `.1/.2` pairs become split **candidates**. Remaining decimals become fractional candidates. These are provisional pattern diagnoses, not asserted content semantics.
5. `ddk_review.problem_policy()` intentionally retains CODE / CODE_REVIEW_REQUIRED for these artifact categories. Normalization excludes unresolved artifacts from final logical counts. A derived parent volume does not establish a decimal's canonical identity.

### Why MangaK was selected

The current shared `publication_specials.inventory_coverage()` does **not** reward unknown fractions as main coverage. It reports MangaK main 403, unresolved 108, raw 511. The other captured sources report main 402, unresolved 6, raw 408. MangaK's extra integer key is `0`.

Under the current comparison and `_choose_primary()` ordering, that one integer-key advantage selects MangaK among otherwise comparable complete standalone inventories. A deterministic characterization confirms that removing all decimals still preserves the advantage; removing zero removes it. Therefore “511 beat 408 because of fractional inflation” would be an incorrect diagnosis.

This exposes a limitation: acquisition ranking counts integer identifiers before later DDK canonical confirmation and does not inspect page content. It cannot know that zero's content is suspect from these blank chapter titles. This investigation does not establish a safe universal zero-chapter exclusion rule or a new ranking policy. Changing ranking solely to evade these CODE findings would not resolve the unreliable identifiers.

## Changes and validation

Added:

- `tests/test_haikyu_provider_residue.py`: six deterministic, network-blocked regressions.
- `tests/fixtures/haikyu_provider_residue.json`: captured acquisition/reference identifiers, projection volumes, expected residual identifiers/counts, four public adapter metadata samples, and explicit provenance describing synthetic peer corroboration.
- This report.

Investigation-only captures, scripts, downloaded samples, test logs, and SHA-256 evidence manifest are under `build/haikyu-investigation/`. Scans are not embedded in this report or checked into the regression fixture. These investigation artifacts are not runtime inputs.

Validation:

- Six new tests pass: full captured numbering pattern and CODE categories; effective-count exclusion despite parent-volume projection; fraction-safe inventory coverage; integer-zero source-selection characterization; no selected-source/one-peer self-corroboration; faithful adapter display labels instead of internal upload indexes.
- 62 DDK focused tests pass: new tests plus existing artifact-authority, canonical-special, and publication-state modules. Includes the captured Dandadan canonical-special regression.
- 12 shared MangaK adapter tests pass.
- Total: 74 passing tests. Python compile check of the new test passes. JSON fixture parses successfully.
- Full DDK/plugin suites and GUI smokes were not run: no runtime/UI implementation changed. Shared worktree status was inspected; existing unrelated changes were left intact.

No DDK runtime, plugin source, ranking, normalization, health policy, schema v7, Grammar 3, curation, acceptance, or live audit was modified. The existing EXE was not rebuilt. No commit, push, tag, release, or version change was performed.

## Remaining work and safe interpretation

Leave Audit 40's CODE findings intact. Establishing exact equivalence or canonical identity for the remaining records needs stronger per-record evidence: trusted explicit identities/aliases, complete-content comparison where relevant, or corrected provider metadata. Neither opening-page similarity nor a familiar decimal pattern is sufficient authority.

The metadata-only audit cannot automatically detect incorrect page contents or a mixed edition behind a correctly shaped integer identifier. The 408 logical count describes current evidence resolution, not a complete manual content certification. No title-specific renumbering, duplicate suppression, special promotion, or provider substitution is recommended from this investigation alone.
