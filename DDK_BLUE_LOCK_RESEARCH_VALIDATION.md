# Blue Lock — Batch 004 research and repair

Investigation date: 2026-10-06 (America/Chicago). Result: **one generic cross-work extraction defect repaired; 26 conflicts resolve automatically in the captured replay. Ten tail chapters and two acquisition-part identifiers remain under the existing conservative policy.** No curation commands or acceptance were applied.

## 1. Exact packet baseline

Evidence: the user-named `C:\Users\Jerry\Documents\MangaAnka-Database-Development-Kit\export.json`, SHA256 `6890257c1b0147357225e7fe2bac6669400836ca112341077f551f3358879ab6`. The JSON was read explicitly; the protected production database was **never opened or mutated**. Local code, rather than GitHub, was inspected.

| Field | Captured state |
|---|---|
| Database UUID | ef8a838e-ae2a-4fe2-bb48-45ae83e2e233 |
| Working set | Batch 004, UUID 1b2fdd82-2bfe-4574-afab-ea4d377e4569 |
| Exact item UUID | dae4afee-1ce4-4c3d-9eaa-088451d082e7 |
| Work UUID / local ID | 4ac3d4a5-a29e-44b7-b37e-039d9f4651bd / 21 |
| Pinned audit / revision | **41 / 1** |
| Canonical work | anilist:106130|kitsu:53928; Blue Lock; high-confidence/shareable |
| Request | standard / en / volume |
| Lifecycle / processing | STAGED / REVIEW; Research required |
| Selected provider | [Atsu](https://atsu.moe/manga/0OElQ) |
| Raw / logical / normalized main | 364 / 364 / 364 |
| Recognized specials / artifacts / unclassified | 0 / 0 / 0 |
| Mapped / total unmapped / uncompiled | **328 / 36 / 0** |
| Unmapped breakdown | 26 conflict rows + 10 tail rows |
| Final volumes | 39; all derived, zero native |
| Health | identity PASS / publication REVIEW / normalization PASS / acquisition PARTIAL |
| Curation | absent; automatic and effective relevant mappings agree |
| Version / schema / grammar | DDK 0.3.0 / schema 7 / Grammar 3 |

Persisted holes: 86 REFERENCE_CONFLICT (26 identifiers), RESEARCH/RESEARCH_REQUIRED; 87 UNMAPPED_CHAPTERS (10 identifiers), RESEARCH/RESEARCH_REQUIRED; 88 CHAPTER_COUNT_DISAGREEMENT (two identifiers in **one category**), ACQUISITION/ACQUISITION_ONLY. The total unmapped field is 36, not ten: the hole classifier separately reports conflicts.

MangaDex structure: valid/refreshed, `mangadex-structure-v1`, integrity `mangadex-aggregate-integrity-v1`, [title 4141c5dc-c525-4df5-afd7-cc7d192a832f](https://mangadex.org/title/4141c5dc-c525-4df5-afd7-cc7d192a832f). 47 accepted explicit mappings across eight volumes; two internally ambiguous keys, 300 and 301. No recognized special records. Of its 47 mappings, 45 match selected acquisition keys; the other two are 288.1 and 288.2.

Wikipedia: confident exact compatible list identity, valid_with_data/refreshed, parser 7, `wikipedia-structure-v3-collection`; page **73491688**, revision **1378857482**. [Exact revision](https://en.wikipedia.org/w/index.php?title=List_of_Blue_Lock_chapters&oldid=1378857482). Captured parse: **400 chapter records and 49 volume records**, contaminated by a separate spin-off section. Current source text itself clearly distinguishes the works.

Captured release boundary is original/Japanese volumes **1–40**, with 41 FUTURE (2026-11-17). This is not proof of forty released English collected volumes: [Kodansha USA volume 39](https://kodansha.us/series/blue-lock/volume-39/) lists digital release 2026-09-15; [English volume 40](https://kodansha.us/series/blue-lock/volume-40/) is scheduled for 2026-11-24. The adapter currently uses OriginalRelDate for its structural release boundary. That existing language/release policy was inspected and **not changed**. Acquisition language, original structural edition and localized print/digital availability must not be conflated.

## 2. All 26 reference-conflict identifiers

**None is MangaDex-versus-Wikipedia disagreement.** MangaDex supplies no explicit mapping for these 26 keys. The parser mixed two valid but **different works**, Blue Lock and Blue Lock: Episode Nagi. This is not a main-work standard/omnibus edition difference or a numbering conversion.

All claims below are Wikipedia `chapter` rows with explicit confidence, source page/revision above, parser pattern `graphic-novel-list-explicit-chapter-list-v1`. The source-record suffix column abbreviates the final two components of `73491688:1378857482:graphic-novel-list-explicit-chapter-list-v1:<template-index>:<row-index>`, in main/foreign order. Complete original record objects and selected acquisition IDs are retained in [affected-records.json](<C:/MangaAnka DDK/build/blue-lock-investigation/affected-records.json>).

The source's main-work membership is retained by scope, not chosen by source precedence. Every selected Atsu record is acquired and standalone; provider-native volume is absent. Current effective/automatic membership is absent because conflicting Wikipedia memberships fail closed.

| Chapter | MangaDex claim | Wikipedia main / Episode Nagi volume | Provider-native claim | Current effective | Repaired volume / remediation | Source-record suffixes |
|---|---|---|---|---|---|---|
| 10 | — | 2 / 3 | — | unmapped | 2 / CODE → automatic | 1:5 / 43:0 |
| 11 | — | 2 / 3 | — | unmapped | 2 / CODE → automatic | 1:6 / 43:1 |
| 12 | — | 2 / 3 | — | unmapped | 2 / CODE → automatic | 1:7 / 43:2 |
| 13 | — | 2 / 3 | — | unmapped | 2 / CODE → automatic | 1:8 / 43:3 |
| 15 | — | 3 / 4 | — | unmapped | 3 / CODE → automatic | 2:1 / 44:0 |
| 16 | — | 3 / 4 | — | unmapped | 3 / CODE → automatic | 2:2 / 44:1 |
| 17 | — | 3 / 4 | — | unmapped | 3 / CODE → automatic | 2:3 / 44:2 |
| 18 | — | 3 / 4 | — | unmapped | 3 / CODE → automatic | 2:4 / 44:3 |
| 19 | — | 3 / 4 | — | unmapped | 3 / CODE → automatic | 2:5 / 44:4 |
| 20 | — | 3 / 5 | — | unmapped | 3 / CODE → automatic | 2:6 / 45:0 |
| 21 | — | 3 / 5 | — | unmapped | 3 / CODE → automatic | 2:7 / 45:1 |
| 22 | — | 3 / 5 | — | unmapped | 3 / CODE → automatic | 2:8 / 45:2 |
| 23 | — | 4 / 5 | — | unmapped | 4 / CODE → automatic | 3:0 / 45:3 |
| 24 | — | 4 / 5 | — | unmapped | 4 / CODE → automatic | 3:1 / 45:4 |
| 25 | — | 4 / 6 | — | unmapped | 4 / CODE → automatic | 3:2 / 46:0 |
| 26 | — | 4 / 6 | — | unmapped | 4 / CODE → automatic | 3:3 / 46:1 |
| 27 | — | 4 / 6 | — | unmapped | 4 / CODE → automatic | 3:4 / 46:2 |
| 28 | — | 4 / 6 | — | unmapped | 4 / CODE → automatic | 3:5 / 46:3 |
| 29 | — | 4 / 7 | — | unmapped | 4 / CODE → automatic | 3:6 / 47:0 |
| 30 | — | 4 / 7 | — | unmapped | 4 / CODE → automatic | 3:7 / 47:1 |
| 31 | — | 4 / 7 | — | unmapped | 4 / CODE → automatic | 3:8 / 47:2 |
| 32 | — | 5 / 7 | — | unmapped | 5 / CODE → automatic | 4:0 / 47:3 |
| 33 | — | 5 / 8 | — | unmapped | 5 / CODE → automatic | 4:1 / 48:0 |
| 34 | — | 5 / 8 | — | unmapped | 5 / CODE → automatic | 4:2 / 48:1 |
| 35 | — | 5 / 8 | — | unmapped | 5 / CODE → automatic | 4:3 / 48:2 |
| 36 | — | 5 / 8 | — | unmapped | 5 / CODE → automatic | 4:4 / 48:3 |

Why chapter 14 and 1–9 are not conflict rows: the mixed works happen to claim the same numeric volumes for those keys, so conflict detection cannot identify their cross-work contamination. The correction excludes **all** foreign-work chapter/title/volume rows, not just the 26 disagreements. A clean numeric result alone is not a sufficient identity check.

Research categories for each of these 26: **D, parser/adaptor defect**. Final remediation: **CODE**, producing automatic resolution. Neither publisher's valid spin-off table is “bad data” in its proper context. The bad claim was created when software attributed that context to the wrong work. No per-title override is justified for this defect.

## 3. All ten other unmapped chapters

Every row is acquired from Atsu, typed as main by existing trusted publication identity, with no native volume. Every row has a Wikipedia **explicit `uncollected`** record on the same exact page/revision; source-record suffixes `uncollected:0` through `uncollected:9` correspond to the rows in order. No MangaDex collected-volume claim exists for any of these ten. No supplementary/special identity is asserted by the captured references.

| Chapter | Trusted reference title | MangaDex claim | Wikipedia claim | Selected acquisition | Effective state after narrow repair | Remediation |
|---|---|---|---|---|---|---|
| 355 | One to Infinity | — | explicit uncollected; no volume | [present](https://atsu.moe/read/0OElQ/b5vXe) | unmapped; UNCOMPILED gate blocked | RESEARCH |
| 356 | Rainbow Knight | — | explicit uncollected; no volume | [present](https://atsu.moe/read/0OElQ/QNb94) | unmapped; UNCOMPILED gate blocked | RESEARCH |
| 357 | Double-Wing | — | explicit uncollected; no volume | [present](https://atsu.moe/read/0OElQ/Hqt1C) | unmapped; UNCOMPILED gate blocked | RESEARCH |
| 358 | Breakthrough Shot | — | explicit uncollected; no volume | [present](https://atsu.moe/read/0OElQ/p4bAH) | unmapped; UNCOMPILED gate blocked | RESEARCH |
| 359 | Got It? | — | explicit uncollected; no volume | [present](https://atsu.moe/read/0OElQ/nF6bP) | unmapped; UNCOMPILED gate blocked | RESEARCH |
| 360 | Origin | — | explicit uncollected; no volume | [present](https://atsu.moe/read/0OElQ/G2dG3) | unmapped; UNCOMPILED gate blocked | RESEARCH |
| 361 | Self-Abnegation | — | explicit uncollected; no volume | [present](https://atsu.moe/read/0OElQ/Wnsvz) | unmapped; UNCOMPILED gate blocked | RESEARCH |
| 362 | Obsession | — | explicit uncollected; no volume | [present](https://atsu.moe/read/0OElQ/DZC1W) | unmapped; UNCOMPILED gate blocked | RESEARCH |
| 363 | Taboo Game | — | explicit uncollected; no volume | [present](https://atsu.moe/read/0OElQ/eq7JI) | unmapped; UNCOMPILED gate blocked | RESEARCH |
| 364 | One-Point Gamble (Part 1) | — | explicit uncollected; no volume | [present](https://atsu.moe/read/0OElQ/M9Qxl) | unmapped; UNCOMPILED gate blocked | RESEARCH |

These are **F, explicitly uncompiled main chapters in the cited original-edition reference**, not ten missing acquisitions. Official English serialization confirms the same ongoing main work: [356](https://kmanga.kodansha.com/title/10008/episode/367369), [364 Part 1](https://kmanga.kodansha.com/title/10008/episode/368828), and the publisher's chapter lists on [this page](https://kmanga.kodansha.com/title/10008/episode/318972) and [this page](https://kmanga.kodansha.com/title/10008/episode/318776) corroborate titles 358–363. The exact Wikipedia revision supplies the explicit uncollected membership for every row, including 355 and 357; primary TOCs independently proving every collected boundary were not obtained. No consecutive-number inference was used to assign a volume.

Why the software still reports UNMAPPED rather than UNCOMPILED: its existing `derive_publication_states()` deliberately requires global reference ambiguity to be absent. Initially the cross-work conflicts also break suffix, complete-release and explicit-uncollected checks. After section repair, the captured checks are:

```
contiguous=True
suffix=True
ordered=True
complete_release=True
explicit_uncollected=True
no_conflicts=False
```

The remaining false gate is `md.ambiguous_chapters=['300','301']`: MangaDex internally claims 300 in volumes 33/34 and 301 in 34/35. Those ambiguous mappings are already rejected; Wikipedia maps both to 34 and the actual projection resolves both. Nevertheless, the existing global ambiguity condition still blocks tail-state establishment. This is a conservative **research/policy boundary**, not evidence that the ten tail chapters have volumes. It was not weakened or silently reinterpreted. Thus operational remediation is exactly **RESEARCH** for each tail record, despite its explicit uncollected source evidence. No future volume was invented, and no curation command bypasses the gate.

The remaining MangaDex 300/301 contradictions require trustworthy upstream metadata correction or a separately reviewed policy/evidence decision. They are distinct from the 26 parser-created conflicts. Clearing the parser conflicts alone cannot legitimately turn the row green under current rules.

## 4. The two acquisition-only identifiers

| Reference key | Captured claim | Selected acquisition | Current public corroboration | Remediation |
|---|---|---|---|---|
| 288.1 | MangaDex volume 33; no special taxonomy | exact key absent; Atsu has main 288 in volume 33 | [MangaDex record 49cb0134-837e-4966-b3f1-a2ef7ca491fb](https://mangadex.org/chapter/49cb0134-837e-4966-b3f1-a2ef7ca491fb): pt-br, part 1 title | ACQUISITION ONLY |
| 288.2 | MangaDex volume 33; no special taxonomy | exact key absent; Atsu has main 288 in volume 33 | [MangaDex record 5af03de6-1ca1-4c15-8994-3a423fc5c7dd](https://mangadex.org/chapter/5af03de6-1ca1-4c15-8994-3a423fc5c7dd): pt-br, part 2 title | ACQUISITION ONLY |

Kodansha's official English serialization explicitly calls these [chapter 288 Part 1](https://kmanga.kodansha.com/title/10008/episode/356662) and [chapter 288 Part 2](https://kmanga.kodansha.com/title/10008/episode/357191). This is strong evidence for **C, numbering/part semantics**, rather than two extra main chapters or recognized specials. Wikipedia represents the collected story as a single chapter 288, “Death Game”, in volume 33. The [English standard volume 33 publisher page](https://kodansha.us/series/blue-lock/volume-33/) independently verifies the volume identity/ISBN and digital/print releases, but does not expose a complete TOC in the retrieved text.

A separate **current public** metadata capture found exactly these two MangaDex part records, both Portuguese, with 10 and 13 image pages respectively. This is not a historical replay of the aggregate's individual uploads; the captured packet contains mappings but no per-mapping chapter UUID provenance. The current UUIDs above must not be retroactively attributed to the earlier aggregate with certainty.

Atsu currently has only `288` ([stable acquisition](https://atsu.moe/read/0OElQ/O7dsahLN), 19 pages); MangaPill currently has only `288` ([stable acquisition](https://mangapill.com/chapters/580-10288000/blue-lock-chapter-288)). Neither current inventory contains 288.1 or 288.2. Captured WeebCentral has 364 main records, but the packet does not retain its full historical chapter list; no exact absence/presence claim is manufactured for that provider. MangaDex is the only independently verified provider of the two exact keys in this research, and those uploads are not English acquisition substitutes.

Chapter `288` existing does not prove complete content equivalence to both parts, and page counts across translations/credits do not prove it either. No complete cross-provider page-content equivalence test was performed. Therefore the residual ACQUISITION_ONLY diagnostic and acquisition **PARTIAL** are retained as a conservative unresolved coverage indication, **not** a verified assertion that two distinct canonical main stories are missing. Safe automatic resolution would need an explicit part-to-whole acquisition identity/coverage contract; a decimal-prefix rule or title-specific renumbering would be unsafe.

## 5. Code repair and root-cause grouping

Before editing, the defect was documented and new synthetic regressions failed: **9 failures, 1 error, 1 pass**. The error was the expected missing effective membership in the contaminated synthetic projection, not an unexplained environment error. The actual captured old parser was then replayed offline against the exact revision and reproduced all saved membership tuples: 400 chapter rows / 49 volume rows.

`WikipediaPublicationAdapter._main_series_section()` formerly recognized only an exact normalized work heading. The actual heading is `''Blue Lock'' volumes`; it did not match `blue lock`, so the helper returned the whole page. The sibling `''Blue Lock: Episode Nagi'' volumes` table entered the same manifest.

The product change recognizes **only an exact work key or that exact key plus the literal structural suffix ` volumes`**. The unique-match requirement and heading-level end boundary remain. It does not use title prefixes, fuzzy matching, work-specific names/numbers, arbitrary suffix stripping, source ranking or a fallback volume rule. Duplicate plausible target headings still produce no structure. Real MangaDex/Wikipedia disagreement still fails closed.

| Cause group | Finding | Outcome |
|---|---|---|
| Code | foreign-work section included in main extraction | generic scope repair; 26 conflicts resolve automatically |
| Bad source data | MangaDex 300/301 mutually contradictory memberships | mappings already quarantined; diagnostic preserved |
| Edition/work mismatch | Episode Nagi is a separate work, not an alternate Blue Lock volume edition | foreign section excluded by exact heading scope |
| Genuine ambiguity / policy | global MangaDex ambiguity blocks otherwise explicit trailing-uncollected evidence | ten operational RESEARCH records retained |
| Acquisition only / numbering semantics | Portuguese 288.1/288.2 parts versus selected integer 288 | both acquisition diagnostics retained; no fabricated equality |
| Curation | no independently justified title-specific override remains after the software repair | no command batch |

## 6. Offline replay and expected re-audit

The before/after replay reconstructs selected acquisition from stable IDs, raw `_atsu_provider_title` labels and page counts; it does **not** feed derived volumes or Wikipedia-inherited titles back as provider evidence. Compatible peer counts are captured, but peer chapter identities are not fabricated. The original reference bundle reproduces the relevant baseline exactly; only the Wikipedia parse of the exact same revision is replaced for the after case. A network guard rejects every accidental request. No catalog is opened.

| Measure | Saved / baseline replay | Repaired exact-revision replay |
|---|---:|---:|
| Raw / logical / main | 364 / 364 / 364 | same |
| Mapped | 328 | **354** |
| Total unmapped | 36 | **10** |
| Reference-conflict identifiers | 26 | **0** |
| Final volumes | 39 | **40** |
| UNCOMPILED established by current evaluator | 0 | **0** |
| Missing reference acquisition keys | 288.1, 288.2 | same |
| Health | PASS / REVIEW / PASS / PARTIAL | same |

Corrected parser output: **364 chapter records** (354 collected + ten explicit uncollected) and **41 listed volume records** (40 originally released + one future empty listing). The eight spin-off volumes and all 36 foreign chapter/title claims disappear. Final projected volumes count only resolved acquisitions, hence 40 rather than 41. Source page/revision and parser record provenance are retained.

Assuming unchanged provider/reference data, manually re-auditing should produce 354/364 mapped, 40 volumes, no REFERENCE_CONFLICT problem for 10–36, the same ten tail research identifiers and two acquisition-only part identifiers. Workflow stays **Research required**. A successful re-audit creates a new immutable audit and advances the exact selected set pin; Audit 41 is not rewritten. Live data changes can change these counts. Nothing was accepted automatically.

## 7. Grammar 3 decision

**No curation command batch is provided.** The 26 defects must be fixed in software, not overridden with 26 volume assignments. The ten tail records must not be assigned a future volume or curated around the global safety gate. The two part keys lack a verified part-to-whole acquisition binding, and neither renumbering nor adding phantom chapters proves content coverage.

No guard was invented. The supplied working-set JSON contains database UUID and exact audit/revision but does not contain the full serialized `guard ... database a...-e...-d...-w...` line; no missing guard is used as an excuse to generate approximate commands. If a future independently justified curation batch is prepared, it must use a newly exported exact guard after the new audit, not Audit 41's old state.

## 8. Files, validation and packaging

Product file changed: `C:\MangaNana-Dev\MangaNana-calibre\wikipedia_reference.py`, only the two-line exact heading candidate comparison. The My Hero nested-template-assignment repair remains intact.

DDK added: `C:\MangaAnka DDK\tests\test_wikipedia_work_section_scope.py` (11 regressions), and this report. Evidence/scripts/logs are under `C:\MangaAnka DDK\build\blue-lock-investigation\`: input provenance, affected-record objects, exact Wikipedia revision, product baseline and hashes, public inventory/metadata captures, failing/passing logs, real-adapter before/after replay, and packaged-module checks. These are research/test artifacts, not shipped provider data.

- New heading-scope regressions: **11/11 pass** after repair. Covers main/foreign work separation, same-volume title contamination, scoped uncollected tails, requested side-work scope, exact suffix, typography, duplicate ambiguity, real inter-reference conflict, provenance and real manifest integration.
- Focused shared suite: **231/231 pass** (Wikipedia identity/membership/collection; reference integrity/integration; publication manifest/identity/freshness/specials). No full plugin suite.
- Existing-EXE frozen-module controls: **38/38 pass**, plus **15/15** scope and My Hero parser controls. Captured Blue Lock and My Hero replays pass with frozen DDK modules and the live shared parser. No interactive EXE/live catalog audit was performed.
- Full DDK discovery: **537/537 pass**, 326.682 seconds, including the 11 new scope tests. This includes reference/artifact authority, Wikipedia membership/identity, publication states/freshness, captured Dandadan specials, SPY x FAMILY, World Is Mine, Haikyu residue/provider-selection boundary, My Hero parser regressions, Workflow/persisted action, Qt and acceptance/curation/history controls. Test databases are disposable. These counts overlap focused/frozen checks and are not presented as unique tests.
- Syntax compilation and evidence-JSON checks pass. Task-relative product diff is only the exact heading candidate comparison. All **ten other inspected product/EXE hashes** match the task baseline, including publication/normalization/Grammar/Workflow presentation, integrity/specials/provider selection and the EXE. Existing unrelated Git changes were inspected and preserved.
- The captured Dandadan fixture still asserts 246 main + 2 recognized specials = 248 logical, 219 mapped main / 221 total mapped, 27 uncompiled, zero unmapped and 25 volumes; unresolved 26.5 and 193.1 and nine missing recognized specials retain their prior roles. Haikyu's 86 fractional / 16 split candidates and its provider-selection boundary remain unchanged. The captured My Hero replay remains 432/433 mapped with all four fractional CODE candidates retained.

No DDK product module, UI, spec, launcher, database schema, Grammar or version was changed. No new GUI/DPI/window smoke is claimed: this is a shared pure-parser correction. The existing EXE dynamically loads the current shared worktree via the live source finder. Frozen DDK-module checks run the new scope controls, prior artifact/reference/special controls and captured Blue Lock **and My Hero** replays against that loader. No EXE rebuild is necessary; restart an already-running DDK to load the changed module.

Existing EXE: `C:\MangaAnka DDK\dist\MangaAnka-Database-Development-Kit.exe`, SHA256 `c245795515893ae2984f598187d05893c2f5697dc6f1de36f680e20b4f106be6`. Primary launcher and Tk fallback remain intact. DDK uses a new `ReferenceMetadataService(None)` for its reference resolution; no catalog cache purge is needed. Other plugin callers retain their ordinary cache freshness behavior.

## 9. Deliberately unresolved and evidence limitations

- Ten explicit uncollected chapters remain operational RESEARCH because the existing global ambiguity guard is unsatisfied. No future release/volume identity is inferred.
- Two numbered part keys remain ACQUISITION ONLY. No complete content-equivalence proof or new coverage relationship was introduced.
- MangaDex 300/301 metadata contradictions are preserved, even though the current projection has compatible Wikipedia volume-34 membership for both.
- Official English publisher pages verify distinct work/edition and release identities; retrieved product text does not provide complete TOCs for all 26 affected memberships. Exact membership/scope evidence is therefore explicitly attributed to the cited Wikipedia revision, not falsely claimed as primary TOC verification. Some Japanese product pages returned HTTP 403. Official English chapter lists corroborate serialization but do not assign tail volumes.
- Current provider requests are contemporary observations, not invented historical inventories. The named packet remains the baseline authority.

Protected production DB never opened or mutated; no title-specific runtime hack; REFERENCE_CONFLICT remains fail closed; no automatic acceptance; provider selection and precedence unchanged; Haikyu and MHA findings preserved; schema **7** and Grammar **3** unchanged. No commit, push, tag, release, reset, clean or version bump.

Manual retest: close/reopen DDK, open the live catalog yourself, select **Batch 004 → Blue Lock**, Force Re-Audit Selected, inspect the new audit for the expected 354/364 and 40-volume result, then export fresh. Verify Audit 41 remains in History and review the remaining tail/part diagnostics before considering acceptance.
