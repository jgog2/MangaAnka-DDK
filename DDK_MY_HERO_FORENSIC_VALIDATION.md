# My Hero Academia: Audit 39 revision 1 forensic investigation

Investigation date: 2026-10-06. Outcome: **one independently proven generic Wikipedia extraction defect repaired; four CODE candidates remain**. This is not a title-pass correction.

## Evidence boundary

The user confirmed `C:\Users\Jerry\Documents\MangaAnka-Database-Development-Kit\export.json` as the packet. SHA256: `eb0e7a93f81da85b72f9a3abafd786192c9e06543b92a759871fc70d411483cd`. Batch 004 UUID `1b2fdd82-2bfe-4574-afab-ea4d377e4569`; item UUID `2b2cb912-1cb7-4eb0-a3d1-7070e6234074`; work 19, Audit 39 revision 1, standard/en/volume, STAGED/REVIEW. Canonical work `anilist:85486|kitsu:26004`.

The packet, actual local implementations, the exact cited public Wikipedia revision, and representative public reader pages were inspected. The protected production catalog was **never opened or mutated**. No audit, acceptance, pin, curation or disposition was written to it. Public page inspection is research evidence, not a new machine-trusted canonical binding.

Baseline: MangaPill 437 raw acquisition records, 433 logical units, 431 mapped, 2 unmapped, 42 final volumes, no native provider volumes. Normalization: 430 main, 3 provisional, 4 fractional candidates. The logical count includes provisional rows; it does **not** prove 433 canonical main chapters. Health: identity PASS / publication REVIEW / normalization REVIEW / acquisition PASS.

## Exact affected records

All seven records are from MangaPill title 601. Stable acquisition ID is the full reader URL below; there is no separate persisted UUID. Saved provider titles are empty; the reader H1 supplies a numeric chapter label, not an independently established story identity. Order indices below are zero-based in the saved 437-row projection. Every native volume is absent; effective volumes are derived projection values.

| Raw label / stable ID | Saved neighboring order | Effective volume / projection state | Normalization | Persisted problem policy |
|---|---|---|---|---|
| [0](https://mangapill.com/chapters/601-10000000/boku-no-hero-academia-chapter-0) | index 0: 0, 1, 2 | 1 / derived_pre_chapter_one | provisional | hole 82 UNKNOWN / RESEARCH_REQUIRED |
| [118](https://mangapill.com/chapters/601-10118000/boku-no-hero-academia-chapter-118) | index 118: 116, 117, 118, 119, 120 | none / unmapped | provisional | hole 80 RESEARCH / RESEARCH_REQUIRED; hole 82 UNKNOWN / RESEARCH_REQUIRED |
| [192.5](https://mangapill.com/chapters/601-10192500/boku-no-hero-academia-chapter-192.5) | index 193: 191, 192, 192.5, 193, 194 | 21 / derived_fractional | provider_fractional_candidate | hole 81 CODE / CODE_REVIEW_REQUIRED |
| [321.5](https://mangapill.com/chapters/601-10321500/boku-no-hero-academia-chapter-321.5) | index 323: 320, 321, 321.5, 322, 323 | 33 / derived_fractional | provider_fractional_candidate | hole 81 CODE / CODE_REVIEW_REQUIRED |
| [430.5](https://mangapill.com/chapters/601-10430500/boku-no-hero-academia-chapter-430.5) | index 433: 429, 430, 430.5, 430.6, 431 | 42 / derived_fractional | provider_fractional_candidate | hole 81 CODE / CODE_REVIEW_REQUIRED |
| [430.6](https://mangapill.com/chapters/601-10430600/boku-no-hero-academia-chapter-430.6) | index 434: 430, 430.5, 430.6, 431, 432 | 42 / derived_fractional | provider_fractional_candidate | hole 81 CODE / CODE_REVIEW_REQUIRED |
| [432](https://mangapill.com/chapters/601-10432000/boku-no-hero-academia-chapter-432) | index 436: 430.6, 431, 432 | none / unmapped | provisional | hole 80 RESEARCH / RESEARCH_REQUIRED; hole 82 UNKNOWN / RESEARCH_REQUIRED |

Exact sets: fractional candidates `{192.5,321.5,430.5,430.6}`; unmapped `{118,432}`; unclassified `{0,118,432}`. Fractions are disjoint from both other sets. The unmapped set is a subset of unclassified. Three problem categories cover seven unique rows, not nine independent failures.

## What the records contain

The first two reader images were inspected for each affected record, along with metadata and surrounding acquisition order. These observations distinguish story identities; they do not establish whole-file equivalence or automatically authorize classification changes.

| Label | Observed content and independent evidence | Exact standard-publication identity in the captured references? | Investigation classification |
|---|---|---|---|
| 192.5 | Supplementary story credited to Yoko Akiyama with Horikoshi's original concept; Japanese title matches the [official Jump+ one-shot listing](https://shonenjumpplus.com/episode/4856001361260520733) under Team-Up Missions. | No. Provider decimal and inherited volume 21 do not identify a standard main chapter. | **B/E**: conservative unresolved identity; richer publication/acquisition binding needed. |
| 321.5 | Opening identifies *Endeavor's Mission*, with Akiyama/Horikoshi credits. [VIZ identifies it as a film-prelude special spin-off](https://www.viz.com/shonenjump/chapters/my-hero-academia-special-spin-off-endeavors-mission). | No standard chapter 321.5 binding. No justified main-series volume 33 assignment for this story. | **B/E**. |
| 430.5 | Opening identifies *Connect to the Day*, with Akiyama/Horikoshi credits. [VIZ's Team-Up Missions volume 8 listing](https://www.viz.com/manga-books/manga/my-hero-academia-team-up-missions-volume-8-0/product/8887) explicitly includes that film-prequel story. | No standard chapter 430.5 binding. Its spin-off collection is distinct from standard volume 42. | **B/E**. |
| 430.6 | Opening identifies *A Piece of Cake*, a Horikoshi special one-shot with TOHO translation credits; distinct title/authorship from 430.5. Primary publisher catalog confirmation of its exact collection was not obtained in this pass. | No standard chapter 430.6 binding. Do not infer a duplicate, split, or main-series volume from proximity. | **B/E**, exact collection research remains. |
| 0 | Opening identifies the earlier *My Hero* one-shot/prototype. The scanned introduction describes its earlier publication and inclusion with Oumagadoki Zoo. That collection claim was not independently verified against a primary publisher catalog in this pass. | No. The safe existing pre-chapter-one projection gives volume 1, but this is derived structure, not proof that the prototype belongs to standard volume 1. | **B/E**, with possible **C** only after an explicit reviewed identity/data model. |
| 118 | Printed main-story number/title matches the exact Wikipedia revision's explicit volume-13 entry. | **Yes**, once the parser stops discarding that positional entry. | **A**: generic extraction defect, repaired. |
| 432 | Opening marks a special one-shot and shows older Eri visiting the school, rather than a printed main chapter 432. [Shueisha's Ultra Age fanbook listing](https://www.shueisha.co.jp/books/items/contents.html?jdcn=08X10000000062024400) describes its short new manga; the [official adaptation announcement](https://heroaca.com/news/27409/) identifies the fanbook story involving older Eri. Matching this provider upload to that special is a research inference, not an existing trusted alias binding. | No. No trusted explicit uncompiled-main record or volume membership exists for 432. Do not assign volume 42 or invent a later volume. | **B/E**; potential **C** requires separately reviewed special identity and acquisition alias evidence. |

The four fractions contain supplementary material, including material from another publication series. No evidence established that they are canonical main decimals, split pieces, duplicate uploads, or alternate editions of their adjacent main chapters. Nor is there a safe generic rule to discard official supplementary stories as acquisition-only noise (**D**). Decimal syntax alone cannot supply that rule. None was added.

## Reference and provider evidence

MangaDex structure is valid/current, title ID `4f3bcae4-2d96-4c9d-932c-90181d9c873e`, with only explicit mappings `1 -> 1` and `431 -> 42`; special records are empty, special metadata reports `no_ids`. It supplies no identity proof for the seven affected rows.

Wikipedia's matched main-series page is 44555475. The actual structure is `List of My Hero Academia chapters`, page **49144012**, revision **1372952288**, parser version 7, collection cache contract `wikipedia-structure-v3-collection`. [Exact cited revision](https://en.wikipedia.org/w/index.php?title=List_of_My_Hero_Academia_chapters&oldid=1372952288). It explicitly lists volume 13 chapters 109–118, volume 14 starting at 119, and volume 42 through 431. It does not bind 0, 432, or the four fractions to main chapters or recognized specials. Total chapter/volume enrichment is not record-level identity evidence.

Audit 39 saved 430 Wikipedia chapter rows. Its manifest runtime publication evidence has 432 records because chapter 1 and 431 also have MangaDex evidence; that is not 432 distinct trusted chapter identities. After repair, the exact Wikipedia source yields 431 chapter rows and restores 118's volume 13 membership with page/revision/record provenance.

Captured qualification: MangaPill 437 complete/usable; Atsu 431 complete/usable; WeebCentral 0 unusable; MangaDex acquisition 0 unusable with `Enter a valid MangaDex title URL.` The MangaDex acquisition error is separate from its usable structural reference and was not changed. Only one other complete acquisition provider exists, insufficient for the existing two-independent-provider identity rule.

A separate current public Atsu inventory capture has 431 rows: 118 and 431 exist, but none of 0, 432 or the four fractions do. This is contemporary corroboration, **not** a reconstruction of unsaved historical peer rows. Provider selection remains unchanged: it precedes final publication identity and counts unverified positive integers as previously characterized. No post-selection rerank or provider-specific exception was introduced.

## Exact software cause and narrow repair

`_numbered_list_rows()` formerly treated any `=` anywhere in a positional argument as a top-level named parameter. The exact volume-13 source's final nested `nihongo` transliteration contains `Iminonai Tat=-p[akai`. Its English title and explicit parent volume are intact, but the parser discarded the entire positional entry. The same bug earlier in a list could also renumber following chapters.

The defect was documented and reproduced **before** editing: three new regressions failed and the real-top-level-parameter control passed. The repair recognizes assignments only outside nested templates. Existing real named parameters, `start`, identity checks, volume precedence, provenance, special authority and fail-closed behavior remain unchanged. No title/number check, source-text correction, adjacent-volume inference, or missing-chapter count inference was added.

The four CODE candidates have a different cause: `normalize_acquisition()` finds repeated unresolved fractional numbering after exact publication/special proof is considered. `_artifact_groups()` records that pattern with candidate confidence. Existing `problem_policy()` deliberately maps that category to CODE/CODE_REVIEW_REQUIRED; persisted policy governs Workflow. A human can identify supplementary stories from opening pages, while the current machine input contains empty titles and no trusted publication/acquisition bindings. That is **B/E**, not a proven generic defect in fractional or special authority. No suppression, disposition, special promotion, policy rewrite or curation command was applied.

## Before/after and expected manual re-audit

An offline replay used the captured selected acquisition records and reference bundle, with all network calls forbidden. Derived projection volumes were removed before reconstructing provider inventory. The packet preserves only the peer count, not original peer chapter rows; the replay keeps that count without fabricating identities. It exactly reproduces the relevant baseline. Only Wikipedia chapters/volumes were then replaced with the actual adapter's parse of the exact saved revision.

| Measure | Captured/baseline replay | Repaired replay |
|---|---:|---:|
| Raw MangaPill records | 437 | 437 |
| Logical units | 433 | 433 |
| Trusted normalized main | 430 | 431 |
| Mapped logical units | 431 | 432 |
| Unmapped | 2: 118, 432 | 1: 432 |
| Final volumes | 42 | 42 |
| Unclassified/provisional | 3: 0, 118, 432 | 2: 0, 432 |
| Fractional candidates | 4 | same 4 |

With unchanged public inventories/references, expect **432/433**, 42 volumes, identity PASS / publication REVIEW / normalization REVIEW / acquisition PASS. Workflow remains **Code review** because CODE_REVIEW_REQUIRED remains. The three category rows remain, with reduced unmapped/unclassified affected counts. Audit 39 itself stays immutable; a manual successful re-audit creates a new audit and advances only the selected pin. Future public data changes can change counts.

DDK constructs `ReferenceMetadataService(None)` for this resolution, so a new run parses current reference data rather than requiring a global cache purge. Parser version/cache contracts and plugin freshness policy were not changed; other plugin callers with their own existing caches retain their ordinary freshness lifecycle.

## Changed files and packaging

Product change: `C:\MangaNana-Dev\MangaNana-calibre\wikipedia_reference.py` (only the nested-assignment repair).

DDK additions: `C:\MangaAnka DDK\tests\test_my_hero_forensics.py` (four deterministic regressions); this report. Research evidence/scripts/logs are under `C:\MangaAnka DDK\build\my-hero-investigation\`, including packet provenance, source baselines/hashes, exact revision, representative reader metadata/images, before/after parser results, offline replay and packaged-module validation. Images are local research evidence and are not embedded in this report or shipped in the EXE.

No DDK product module, Qt UI, launcher or spec changed. Schema **7**, Grammar **3**, DDK **0.3.0**, acceptance/history/curation semantics and provider selection are unchanged. Twelve inspected protected product/EXE hashes match the task baseline; only the shared Wikipedia source hash differs. The existing dirty plugin worktree was preserved; these are task-relative changes, not attribution of all pre-existing Git changes.

**No EXE rebuild is required.** The current packaged loader gives the current shared worktree source priority, and no shared submodule snapshot is packaged. Frozen DDK publication/normalization modules were checked against current source, then exercised with the current shared parser, including the captured replay and all four new regressions. This is frozen-module offline validation, not a new interactive GUI or live provider audit.

Final existing EXE: `C:\MangaAnka DDK\dist\MangaAnka-Database-Development-Kit.exe`; SHA256 `c245795515893ae2984f598187d05893c2f5697dc6f1de36f680e20b4f106be6`. Primary launcher and legacy Tk fallback are untouched. Restart an already-running DDK before retesting so Python reloads shared source.

## Validation

- New parser regressions: before repair **3 failures / 1 pass**; after repair **4/4 pass**. Includes the exact nested-transliteration defect, protection against renumbering following entries, real outer named parameters and deep nesting.
- Full DDK discovery: **526/526 pass**, 315.288 seconds. Includes the four new tests, artifact authority, canonical specials, reference integrity, Wikipedia membership/page identity, SPY x FAMILY controls, World Is Mine, Haikyu residue and provider-selection boundary, Workflow/persisted action, Qt, acceptance/curation/history and transaction regressions. All catalogs used by tests are disposable.
- Focused shared Wikipedia discovery only: **83/83 pass**, covering collection, identity and membership. The entire plugin suite was not run.
- Existing-EXE frozen-module controls: **38/38 pass**, including artifact authority, reference integrity, captured Dandadan, Wikipedia identity and membership. A further **4/4 new parser tests** and the captured before/after replay pass with frozen DDK modules and the current live shared parser. Tests verify no bundled catalog or stale shared-module snapshot. Counts here overlap the full suite and are not presented as unique tests.
- Captured Dandadan remains 246 main + 2 acquired recognized specials = 248 logical; 219 mapped main / 221 total mapped; 27 uncompiled main; 0 unmapped; 25 volumes; unresolved 26.5 and 193.1; nine missing recognized specials acquisition-only. Health remains PASS/PASS/REVIEW/PARTIAL for that captured MangaPill fixture.
- Haikyu's six residue tests and 22 provider-selection-boundary tests pass unchanged. Its 86 fractional and 16 split candidates retain CODE/CODE_REVIEW_REQUIRED; provider selection was not altered. Ordinary integers, independently supported decimals/omake, split candidates, duplicate-looking rows, conflicting identities and edition incompatibility controls pass.
- Shared-file syntax compilation and changed-test compile checks pass. Task-relative diff contains only the nested-assignment product repair. Captured evidence JSON parses successfully; source/EXE hash comparison passes for all twelve other inspected files.
- No interactive GUI/DPI/window smoke or new live audit was run: no UI or packaged DDK product source changed. Frozen-module checks establish the packaging decision without launching the normal launcher or accessing production preferences/catalogs.

## Remaining limits and manual check

Representative openings establish distinct supplementary content, not exhaustive whole-file deduplication. Exact collection identity for 430.6 and the prototype's collection claim were not independently catalog-verified. No runtime OCR, scan-content inference or new identity bridge was introduced. Resolving supplementary stories safely needs explicit compatible publication identities and provider alias bindings; a separate policy/data task may follow this evidence, but this pass does not authorize curation around CODE.

Manual check: close/reopen DDK; open the live catalog yourself; select Batch 004's My Hero Academia item; Force Re-Audit Selected; verify the new audit maps 118 to volume 13, leaves 432 unresolved, retains all four fractional CODE candidates and Code review, and preserves Audit 39 in history. Export a fresh packet if data differs. Do not accept merely because one parser hole was fixed.

Nothing was committed, pushed, tagged, released or version-bumped.
