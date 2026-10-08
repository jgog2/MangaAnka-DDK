# Black Clover BATCH 004: publication membership and publisher evidence

Date: 2026-10-07. This pass used the current local DDK and shared-plugin worktrees. No production database was opened or mutated. No production curation, acceptance, version bump, commit, push, tag, or release was performed.

## Root cause

The captured packet pins Black Clover work 25 to Audit 48 revision 1, canonical work `anilist:86123|kitsu:27527`, MangaPill, standard/en. The packet SHA-256 is `90172654f1f2e731a9dc3408fa1d1b5a21b4750453f0dbc05e698a624d0baf87`.

The actual path is `resolve_publication()` → shared reference service/manifest → shared acquisition projection → `normalize_acquisition()` → `effective_counts()`/shared state summary → DDK holes/health.

1. Existing trusted references establish main identities 1–392. Neither provider row 0 nor 393 has independent chapter-level identity in that audit.
2. The normalizer labels both rows **provisional**, rather than main. Only one other usable complete provider inventory exists, so its existing two-peer exclusion rule does not apply.
3. `effective_counts()` deliberately includes provisional rows in logical coverage. Consequently 392 canonical main identities become 394 logical candidates. This was fallback acquisition coverage leaking across a missing completed-publication authority boundary, not direct promotion to the normalizer's `main` label.
4. The shared projection's generic `0 <= chapter < 1` derivation assigns row 0 to volume 1 when volume 1 exists. Projection is not identity proof, but this provisional row also contributes to mapped coverage: 393 mapped, one unmapped.
5. The pipeline previously contained no publisher-backed completion contract. Wikipedia parse completion and a last listed number are insufficient substitutes.

A first experimental rule excluding every provisional row once any main identity existed was rejected: it broke three existing Days/Wikipedia membership controls, including an unresolved SPY-style tail and an interior gap. That rule was completely withdrawn. The user then explicitly authorized expansion to generic publisher evidence ingestion.

## Authoritative publication evidence

Direct browser verification of [MANGA Plus's Black Clover page](https://mangaplus.shueisha.co.jp/titles/100003?pubDate=20260805) showed Completed and #392, dated April 30, 2026. The public official API separately returned explicit release-schedule enum **8 (COMPLETED)** and final chapter ID **1027803**. It exposed five numbered chapter records, not a complete 392-row list. No missing publisher chapter records were invented.

[Shueisha's volume 38 catalog](https://www.s-manga.net/items/contents.html?jdcn=08X10000000073438800) confirms August 4, 2026, ISBN `978-4-08-885136-5`, and the final main installment in its TOC. Its next-volume label has no linked next volume. This is an observed catalog state, not proof that no future edition could ever exist.

## Chapter 0

Stable acquisition ID:
`https://mangapill.com/chapters/524-10000000/black-clover-chapter-0`

The reader contains 50 image files. Inspected first/title, scanlation-credit, and final images show a separately presented story with a 49-page announcement, Asta/Yuno, and its own ending. Its Japanese title uses the middle dot seen in the publisher's pilot title. One image is a scanlation credit, so image-file count must not be mistaken for an official page count.

[Shonen Jump's official 2018 notice](https://www.shonenjump.com/j/notice/2018/05/02/20180502_bc001.html) identifies the original one-shot and its guidebook inclusion. [The official 16.5 guidebook TOC](https://www.s-manga.net/items/contents.html?jdcn=08881551880416315501) identifies that one-shot at book page 156, ISBN `978-4-08-881551-0`.

**Finding:** strong consistency with the separate original pilot/one-shot, but this inspection did not obtain an authoritative page-by-page scan match. Its exact acquisition-to-publication binding remains **UNRESOLVED ACQUISITION**, with a likely **SEPARATE PILOT / ONE-SHOT** identity for research. It is not established serialized main chapter 0. Neither its provider number nor the old volume-1 derivation proves that identity.

The new ingestion records the publisher's pilot TOC identity as an unbound supplementary publication. Existing `special` taxonomy can represent a proven supplementary binding; no title-specific alias or production correction was fabricated.

## Chapter 393

Stable acquisition ID:
`https://mangapill.com/chapters/524-10393000/black-clover-chapter-393`

The reader contains 14 image files. Its first image names the coronation of the 29th Wizard King and visibly prints book page **303**. Its final image explicitly identifies a special chapter and its ending. The neighboring 392 reader has 21 images and a different final-main title/opening/ending. The sampled images have different hashes; a complete all-page duplication comparison was not performed.

[Shueisha's Complete Grimoire guidebook TOC](https://www.shueisha.co.jp/books/items/contents.html?jdcn=08X10000000073529800) identifies Tabata's coronation manga at page **303**, followed by an author message at 318. It advertises 15 manga pages and was released August 4, 2026, ISBN `978-4-08-885227-0`. Fourteen image files are not necessarily fourteen printed pages; a spread can occupy one file. No exact upload date was established from the provider reader, and a CDN path is not publication-date proof.

**Finding:** **LEGITIMATE SPECIAL**, a supplementary guidebook publication, rather than authoritative serialized chapter 393, fabricated content, or an established volume-38 extra. Title, subject, page position, and explicit special ending support the guidebook identity. The software still preserves its acquisition binding as unresolved: it does not OCR downloaded pages or automatically create a numeric alias from this forensic finding.

## Generic repair

The final rule requires positive, compatible, current evidence:

- Exact trusted canonical title/alias plus creator match, standard edition, English; ambiguous candidates fail closed. The bounded macron spelling comparison is specific to explicitly written macrons, not general fuzzy creator matching.
- MANGA Plus's current public catalog and detail metadata, using the web client's anonymous session header. No user credentials, login, chapter downloads, or third-party reconstructions are used.
- An explicit COMPLETED enum, a stable published final chapter identity, and current compatible existing main publication records corroborating that final chapter.
- Every integer in the backbone through that final identity must already be explicitly present in the trusted record set. This validates an observed set; it does not manufacture identifiers from a range or use a reported chapter count. Noncontiguous or partial models remain conservative.
- Consumer-side work/edition/language/title/creator/provenance/freshness validation. Closure evidence older than 24 hours, failed, future-dated, incompatible, or structurally conflicting is not used.
- Unsupported provisional rows outside that closed main set become unclassified acquisition evidence. Independently established main chapters, independently established zeroes, recognized specials, fractions, and existing provider corroboration retain their normal paths.
- A newer independent main identity contradicting completion disables closure and creates an existing `REFERENCE_CONFLICT` finding. It is retained, not suppressed. Ongoing or stale-reference cases do not receive a closed-world ceiling.

Shueisha's typed book search and guidebook TOCs are ingested separately, bounded to two exact-family official guidebooks. Book/page IDs identify supplementary publications; page 303 and book label 16.5 are never converted into canonical chapter/standard-volume assignments. These unbound observations are stored under `references.publisher_publication.supplementary_publications` in the audit JSON. Publisher membership and provenance are also serialized and fingerprinted.

Failure to fetch or validate the optional publisher evidence preserves the old conservative provisional behavior and records the publisher lookup status/error. This feature does not declare a work complete from provider totals, Wikipedia's last row, or metadata status text alone.

### Files changed or added

Product:

- `ddk_publisher_reference.py` — new bounded official metadata adapter, supplementary observations, validated membership contract, provenance fingerprint.
- `ddk_publication.py` — collect publisher evidence in normal live audits; consume captured evidence in injected/offline services; expose membership/provenance and completion conflicts.
- `ddk_chapter_normalization.py` — use validated positive publisher identities and conditional closed main membership; retain unsupported acquisitions.

Tests/report:

- `tests/test_logical_membership_authority.py` — 12 synthetic lifecycle/membership scenarios.
- `tests/test_publisher_reference.py` — 32 protocol/identity/freshness/conflict/supplementary scenarios.
- `tests/smoke_packaged_artifact_authority.py` — verify the new frozen module and add publisher regressions to the packaged smoke.
- This report.

**Shared/plugin files changed: none.** Search, provider ranking, source adapters, Atsu groups, canonical-special implementation, reference structural precedence, release/UNCOMPILED evaluator, health derivation, curation commands, acceptance code, schema v7 and Grammar 3 were not modified. Existing worktree changes from earlier work were preserved.

Evidence and replay scripts/output are under `build/black-clover-membership/`; the evidence manifest lists their exact paths/hashes. These are investigation artifacts, not shipped source or corpus hacks. The DDK directory is not a Git repository; frozen-bytecode comparisons are used to verify the changed runtime files against the rebuilt package.

## Before / after

This is a controlled publication replay of Audit 48's selected acquisition records and reference bundle. Peer raw chapter identities were not serialized in the packet; their saved inventory summaries were retained and no missing peer records were invented. The after replay adds separately captured current official publisher observations. It is not a fresh production/network audit.

| Metric | Before | After replay |
|---|---:|---:|
| Raw acquisition records | 394 | 394 |
| Canonical main | 392 | 392 |
| Logical chapters | 394 | 392 |
| Mapped logical chapters | 393 | 392 |
| Unmapped logical chapters | 1 | 0 |
| Uncompiled | 0 | 0 |
| Final volumes | 38 | 38 |
| Identity health | PASS | PASS |
| Publication health | REVIEW | PASS |
| Normalization health | REVIEW | REVIEW |
| Acquisition health | PASS | PASS |
| Overall | REVIEW | REVIEW |
| Problem categories | 2 | 1 |

`UNMAPPED_CHAPTERS` for unsupported 393 is removed from logical publication coverage. `UNCLASSIFIED_ACQUISITION` remains, affecting **0 and 393**. No CODE finding is suppressed or reclassified. All acquisition IDs/URLs and all 394 projection rows remain present. Row 0's old raw projection derivation remains available for debugging, but it no longer appears in logical mapped identifiers or mapped counts. The shared plugin's derivation rule was not rewritten.

## Regression validation

- New publisher/membership tests: **44 passed** (12 + 32). They cover all seven requested synthetic scenarios, plus unavailable/partial/stale/future evidence, wrong identity/edition/language/creator, ambiguous catalogs, malformed protobuf, completion contradictions, independent peer extensions, book-page identity, persistence and no automatic acceptance.
- Existing focused DDK controls: **265 passed**, 16.249 seconds, after repair.
- Focused shared-core controls: **261 passed**, 2.184 seconds; no full plugin suite was run.
- Full DDK suite: **674 passed**, 333.036 seconds, including **103 Qt tests**. The pre-change baseline also passed all 630 existing tests.
- Static compilation: six changed/new Python files passed.
- Captured Black Clover replay: before counts reproduced exactly; after counts shown above; all acquisition IDs retained; only the unresolved acquisition category remains.
- Dandadan captured controls retain 246 main + 2 recognized specials = 248 logical; 219 mapped main / 221 mapped total; 27 uncompiled; zero unmapped main; 25 volumes; unresolved provider fractions 26.5 and 193.1 and nine acquisition-only missing specials; health PASS/PASS/REVIEW/PARTIAL.
- Sakamoto/Dr. STONE guarded corrections, Sakamoto tail behavior, Blue Lock scoped UNCOMPILED, MHA parser/residue, Haikyu CODE categories, SPY parser, Chainsaw reference conflicts, World Is Mine 163/163/14, and explicit acceptance/race/lifecycle controls are included in the passing existing suites.

### Packaging validation

The primary Qt EXE was rebuilt successfully with the existing PyInstaller spec. Final size: **52,543,473 bytes**. SHA-256: `9ccc78c7dcddfd7603410b73165920ffa68a040974efb25b2662e8bef608b64e`.

- Frozen runtime bytecode matches current source for the publisher adapter, normalization/publication integration and checked curation, backend, catalog, acceptance, Qt worker and export/guard modules. No shared-core snapshot or database payload was bundled.
- Packaged offline tests: **157 passed** (108 in 59.552 seconds; 49 in 0.791 seconds), including all 44 new publisher/membership tests and the captured Black Clover replay. The frozen replay reproduces the before/after counts and health above without network or database access.
- Actual EXE startup passed with explicit disposable `--database`, `--create`, `--role TEST` and isolated `--ui-settings`. Qt ran offscreen, the process stayed alive, a fresh schema-v7 database was created, and its read-only integrity check returned `ok`. Only the verified test process tree was stopped afterward.
- These are packaged-code and noninteractive startup checks, not an interactive visual or production audit. Logs and the exact disposable startup paths are in the evidence manifest.

Primary launcher: `C:\MangaAnka DDK\Launch_MangaAnka_DDK.bat`.
Legacy Tk fallback: `C:\MangaAnka DDK\Launch_MangaAnka_DDK_Legacy_Tk.bat` (unchanged).
Target EXE: `C:\MangaAnka DDK\dist\MangaAnka-Database-Development-Kit.exe`.

No PyInstaller/spec, Qt, font, or launcher source changes were needed. No new runtime dependency was added. No new interactive UI or nine-scale visual smoke is claimed for this backend-only change.

## Known limitations

Automatic closure is currently supported for exact compatible English/standard works in MANGA Plus, with a complete explicit integer backbone in the existing trusted publication model. Other publishers, languages, noncontiguous numbering, missing/partial references, ambiguous author names, unavailable endpoints and stale evidence remain conservative. Catalog/detail/TOC reads are bounded and run in the existing audit worker; optional lookup failure leaves prior review behavior intact.

Supplementary publisher identities are observable but deliberately **unbound** to acquisition records. There is no automatic image/OCR matching or number-based pilot/special alias. Exact machine-readable acquisition-to-supplement binding remains future work. An unavailable publisher lookup may leave Black Clover at the old provisional counts; inspect the exported publisher status rather than interpreting that as a new canonical main identity.

No full live 25-title corpus rerun or production mutation was performed. The new publisher behavior is conditional; captured controls without publisher closure evidence retain their existing behavior.

## Production action

After the repaired build is verified:

1. Close/restart the DDK using its normal primary launcher.
2. Select the exact Black Clover item in BATCH 004 and run **More → Force Re-Audit Selected**.
3. Export a fresh pinned Working Set Review Packet.
4. Check for 394 raw records, 392 canonical/logical main chapters, 392 mapped, zero logical unmapped/uncompiled, 38 volumes, and the two retained unclassified acquisition rows. Check `publisher_publication.status=current` and `publisher_membership.status=closed`.
5. Keep Black Clover in REVIEW while the supplementary acquisition bindings remain unresolved. Do not map 393 to volume 38 or 0 to volume 1 solely from their provider numbers. No guarded curation batch is supplied or justified by this change, and Black Clover must not be accepted automatically.

Every production step above is for the user to perform manually; none was performed during development.
