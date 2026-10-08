# MangaAnkā DDK — autonomous BATCH 004 investigation and repair

Date: 2026-10-07 America/Chicago (network captures extend into 2026-10-08 UTC).

One generic software defect was demonstrated and repaired: publisher chapter availability was incorrectly treated as final-chapter identity. It caused false completion conflicts in The Promised Neverland, Haikyu!!, and Dr. STONE. All ten exact requests completed fresh disposable audits. Their baseline counts and canonical identities were preserved; only those three false REFERENCE_CONFLICT categories disappeared. Legitimate CODE, REVIEW and PARTIAL findings remain.

No production database was opened, copied or mutated. No production pins, curation, acceptance or history were changed. No shared-plugin source was changed. Schema 7, Grammar 3 and v0.3.0 are unchanged. No commit, push, tag, release, version bump, reset or clean was performed.

## Verified historical baseline

Input: the supplied pinned export.json, SHA-256 `e604724638ea843e3ea1b816327b735dd0c721ff19046fd5fba1ac53efcc80cf`.
Database UUID `ef8a838e-ae2a-4fe2-bb48-45ae83e2e233`, token `a66-e4-d1-w28`; Working Set UUID `1b2fdd82-2bfe-4574-afab-ea4d377e4569`, Batch 004 OPEN.
The extractor verified all ten query/edition/language/workflow requests, exact item UUIDs, audit IDs/revisions, pin/guard equality, database UUID/token and Working Set UUID. All requests are standard/en/volume. This is historical exported evidence, not a read of the production database.

Health order throughout: identity / publication / normalization / acquisition. READY is a Working Set processing state, not an acceptance.

| Title | Pin | State | Source | Raw | Main | Logical | Mapped | Unmapped | Uncompiled | Volumes | Health |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| My Hero Academia | 57 r3 | REVIEW | MangaPill | 437 | 431 | 433 | 432 | 1 | 0 | 42 | PASS/REVIEW/REVIEW/PASS |
| Haikyu!! | 58 r2 | REVIEW | MangaK | 511 | 408 | 408 | 408 | 0 | 0 | 45 | PASS/REVIEW/REVIEW/PASS |
| Black Clover | 59 r3 | REVIEW | MangaPill | 394 | 392 | 392 | 392 | 0 | 0 | 38 | PASS/PASS/REVIEW/PASS |
| Blue Lock | 60 r4 | READY | Atsu | 364 | 364 | 364 | 354 | 0 | 10 | 40 | PASS/PASS/PASS/PARTIAL |
| Sakamoto Days | 61 r5 | REVIEW | MangaK | 412 | 277 | 277 | 255 | 22 | 0 | 28 | PASS/REVIEW/REVIEW/PASS |
| Kaiju No. 8 | 62 r2 | READY | Atsu | 130 | 130 | 130 | 130 | 0 | 0 | 16 | PASS/PASS/PASS/PASS |
| Dr. STONE | 63 r3 | REVIEW | Atsu | 236 | 232 | 232 | 232 | 0 | 0 | 26 | PASS/REVIEW/REVIEW/PARTIAL |
| The Promised Neverland | 64 r2 | REVIEW | Atsu | 189 | 182 | 182 | 182 | 0 | 0 | 20 | PASS/REVIEW/PASS/PARTIAL |
| Vinland Saga | 65 r2 | READY | Atsu | 223 | 223 | 223 | 223 | 0 | 0 | 29 | PASS/PASS/PASS/PASS |
| Golden Kamuy | 66 r2 | READY | Atsu | 314 | 314 | 314 | 314 | 0 | 0 | 31 | PASS/PASS/PASS/PASS |

Exact problem details and identifiers are preserved in `build/batch004-autonomous-20261007/BASELINE.md` and `baseline-summary.json`; the unmodified packet is `baseline-packet.json`.

## Root cause and narrow repair

`PublisherReferenceAdapter.lookup()` previously set `final_chapter = chapters[-1]` whenever release schedule was COMPLETED (8). The MANGA Plus lists describe available chapters, including first/last free previews. A completed series can expose only four early chapters. `membership_evidence()` then treated all independently established chapters above 4 as contradictory completion evidence. This was a positive-authority bug, not a conflict-policy or health-rendering bug.

Current unmodified public protobuf responses prove the defect:

| Publisher work | Public ID | Schedule | Exposed numbered records | Explicit terminal identity |
|---|---:|---|---|---|
| The Promised Neverland | 100026 | COMPLETED (8) | 1–4 | None |
| Haikyu!! | 100014 | COMPLETED (8) | 1–4 | None |
| Dr. STONE | 100010 | COMPLETED (8) | 1–4 | None |
| Black Clover | 100003 | COMPLETED (8) | 1–4, 392 | Explicit Final Page 392, publisher record 1027803 |

Responses were captured at 01:04 UTC from the public [MANGA Plus title detail API](https://jumpg-webapi.tokyo-cdn.com/api/title_detailV4?title_id=100026&clang=eng). Raw response fixtures and hashes are retained. The previously captured official web client decoder independently identifies firstChapterList, lastChapterList and available chapter lists; none supplies a terminal-chapter guarantee.

The adapter now requires exactly one explicitly terminal-labeled publisher chapter (Final Chapter, Final Page or Final Episode, with an optional punctuated subtitle). Highest number, list position and COMPLETED status alone cannot select a terminal identity. The consumer independently revalidates that label and uniqueness, so a previously captured bogus chapter-4 final cannot regain authority. Ambiguous terminal labels remain open. Existing work/edition/language/creator, provenance, freshness, timestamp, established identity and contiguous positive-backbone checks still apply. A genuinely newer independently established main identity still raises REFERENCE_CONFLICT. No identities are invented and no numeric ceiling is inferred from availability.

The initial ten-test synthetic suite reproduced ten failure reports, including subtests, before the edit. Both the adapter error and stored-evidence consumer error are captured in `completion-before.log`. Twelve new tests now cover free previews, explicit final records, misleading story titles, competing final labels, old poisoned observations, unmarked maxima, true newer-main contradiction, future final records and four actual publisher responses.

## Fresh disposable before/after results

Real current provider search, enrichment, canonical ranking, inventory qualification, reference resolution, normalization, publication evaluation and persistence ran through `SearchAuditor.audit_many()` in a new TEST schema-v7 catalog. These were not reconstructed historical responses. Network audits ran from 01:06 to 01:13 UTC. SQLite connections were guarded to the exact disposable directory, including read-only validation URIs. Integrity check is ok and catalog_acceptances remains empty.

Dr. STONE chapter 206 → volume 24 and Sakamoto Days chapter 232 → volume 26 were replayed from the packet into the disposable catalog only, after verifying exact canonical identity. The normal Preview/Apply and Force Re-Audit paths created new disposable provenance/history; they are not production mutations. Their uncurated snapshots are separately preserved from immutable disposable audits.

| Title | Historical pin | Disposable audit | Health before → after | State before → after | Removed category |
|---|---|---:|---|---|---|
| My Hero Academia | 57 r3 | 2 | PASS/REVIEW/REVIEW/PASS → PASS/REVIEW/REVIEW/PASS | REVIEW → REVIEW | None |
| Haikyu!! | 58 r2 | 3 | PASS/REVIEW/REVIEW/PASS → PASS/PASS/REVIEW/PASS | REVIEW → REVIEW | REFERENCE_CONFLICT |
| Black Clover | 59 r3 | 8 | PASS/PASS/REVIEW/PASS → PASS/PASS/REVIEW/PASS | REVIEW → REVIEW | None |
| Blue Lock | 60 r4 | 9 | PASS/PASS/PASS/PARTIAL → PASS/PASS/PASS/PARTIAL | READY → READY | None |
| Sakamoto Days | 61 r5 | 7 | PASS/REVIEW/REVIEW/PASS → PASS/REVIEW/REVIEW/PASS | REVIEW → REVIEW | None |
| Kaiju No. 8 | 62 r2 | 10 | PASS/PASS/PASS/PASS → PASS/PASS/PASS/PASS | READY → READY | None |
| Dr. STONE | 63 r3 | 5 | PASS/REVIEW/REVIEW/PARTIAL → PASS/REVIEW/REVIEW/PARTIAL | REVIEW → REVIEW | REFERENCE_CONFLICT |
| The Promised Neverland | 64 r2 | 1 | PASS/REVIEW/PASS/PARTIAL → PASS/PASS/PASS/PARTIAL | REVIEW → READY | REFERENCE_CONFLICT |
| Vinland Saga | 65 r2 | 12 | PASS/PASS/PASS/PASS → PASS/PASS/PASS/PASS | READY → READY | None |
| Golden Kamuy | 66 r2 | 11 | PASS/PASS/PASS/PASS → PASS/PASS/PASS/PASS | READY → READY | None |

For every title, **all seven count fields in the baseline table equal the fresh post-repair result**. `summarize.py` asserts those equalities, exact canonical work identity, no newly added categories, and only the three expected removed conflicts. Detailed fresh holes, identities and counts are in `live-results.json`; exact comparisons are in `comparisons.json`. Successful auditing does not mean every title passes or is acceptable.

## Findings and next actions

### The Promised Neverland

The false chapter-4 completion conflict is fixed. The remaining acquisition-only CHAPTER_COUNT_DISAGREEMENT covers 181.6, 182–185, 21.5, 3.5, 38.5 and 4.5. The software still reports 182 logical/main units from its current evidence; this is not a manual certification of 182 serialized main chapters. The [official volume 20 contents](https://www.shueisha.co.jp/books/items/contents.html?jdcn=08882375880872315501) explicitly end with the final story, and [Jump+ chapter 181](https://shonenjumpplus.com/episode/13933686331721589440) identifies it. Neither binds the provider extras automatically. Next action: obtain exact supplementary acquisition identities before changing taxonomy or counts. Publication PASS, acquisition PARTIAL is retained.

### My Hero Academia

All 431 currently established main chapters remain. Provider 432 is still one unmapped provisional logical unit; 0 and 432 remain unclassified acquisitions. Fractions 192.5, 321.5, 430.5 and 430.6 retain CODE / CODE_REVIEW_REQUIRED. Fresh complete reader manifests have 49, 15, 17, 17, 8 and 6 pages respectively for 0, 192.5, 321.5, 430.5, 430.6 and 432. Page counts do not prove identity, equivalence or membership.

Prior direct opening-page observations distinguish supplemental/spin-off content rather than split main chapters. They are retained as historical research in `DDK_MY_HERO_FORENSIC_VALIDATION.md`, not re-described as newly inspected images. The [official volume 42 contents](https://www.shueisha.co.jp/books/items/contents.html?jdcn=08X10000000055591900) explicitly include No.431 More. The [Ultra Age fanbook](https://www.shueisha.co.jp/books/items/contents.html?jdcn=08X10000000062024400) lists a separately commissioned short story; its TOC page position is not canonical chapter 432. The present metadata contract has no verified per-acquisition bridge for these supplemental works. Next action: a trusted identity/evidence bridge, not guessed numeric assignment or blanket special classification.

Publisher lookup remains unmatched because the English MANGA Plus creator is Kohei Horikoshi while trusted creator evidence says Kouhei Horikoshi. The adapter intentionally does not collapse arbitrary short/long-vowel names. Exact title alone cannot authorize publisher authority; no broad romanization/fuzzy matching was added.

### Haikyu!!

The false publisher completion conflict is fixed. All 86 fractional CODE candidates, 16 split CODE candidates and unclassified zero remain. Fresh reader manifests were captured for eight samples; 125.1 and 125.2 each have 32 pages but different URL-manifest hashes, which does not establish equality or inequality of their actual images. The historical investigation already proved mixed contents: bonuses, ordinary main chapters under wrong decimals, duplicate-looking material, and suspect zero. It disproves a universal split or special rule. See `DDK_HAIKYU_PROVIDER_INVESTIGATION.md` and its existing six regression controls.

Source-selection characterization remains intact: MangaK wins by one additional integer key (zero), not by rewarding unknown fractions. Six peer-corroborated decimals account for 408 normalized main units versus 402 Wikipedia integer identities; that is existing software evidence, not new authoritative taxonomy. Next action: per-record identity/corrected provider metadata. No provider swap, decimal collapse, ranking adjustment or CODE suppression was justified.

### Dr. STONE

The false publisher completion conflict is fixed. Reviewed 206 → 24 remains effective. The remaining MISSING_REFERENCE_STRUCTURE concerns released volume 27 versus 26 resolved numeric volumes. Fractions 232.5–232.8 remain CODE, and missing 4.5/18.5 remain acquisition-only disagreement. Fresh reader manifests contain 51/42/45/46 pages for those four tail fractions.

The [official volume 27 TOC](https://www.s-manga.net/items/contents.html?jdcn=08X10000000040243800) explicitly lists Terraforming and three named 4D Science installments. This supports real supplementary contents, but does not identify any Atsu reader record by numeric fraction. No guessed 232.5 → Terraforming or volume 27 assignment was made. Next action: a verified acquisition-to-publication identity bridge; keep distinct canonical supplementary works separated.

### Sakamoto Days

Reviewed 232 → 26 remains effective and its raw MangaDex 25 versus Wikipedia 26 provenance is preserved as resolved by curation. Twenty-two explicit uncollected tail records 256–277 remain UNMAPPED rather than being silently promoted to UNCOMPILED. The shared evaluator derives automatic tail safety before the DDK curated overlay, requiring complete compatible released structure. The underlying 232 discrepancy still fails that automatic structure check; this is the previously documented conservative boundary, not a newly proven parser or membership error. Changing whether effective curation may discharge that gate is a separate architectural/policy decision and was not made.

The [official volume 26](https://www.s-manga.net/items/contents.html?jdcn=08X10000000069979000) supports 232 in volume 26; [volume 28](https://www.shueisha.co.jp/books/items/contents.html?jdcn=08X10000000073438300) ends at 255 and was released August 4. The [publisher November schedule](https://www.shueisha.co.jp/books/newcomics/index.html?digital=1&genre=inherit&month=next), checked October 7, lists volume 29 for November 4. No future volume was counted as released. The 101 fractional CODE candidates, 30 split CODE candidates and unclassified 0/300/307 remain. Fresh reader manifests for 300 and 307 do contain pages, but their blank metadata cannot establish canonical identities. Next action: retain conservative tail state and resolve supplemental acquisition identity separately.

### Black Clover

The explicitly identified Final Page 392 still supports the existing closed positive main model. Main/logical/mapped remain 392/392/392 with 38 volumes. Unclassified 0 and 393 remain visible and keep normalization REVIEW. Existing publisher guidebook/pilot observations are unbound supplementary publications; no alias, numbering or TOC-position guess was added.

### Blue Lock

All 364 logical/main units remain, with 354 mapped and 10 explicitly evidenced UNCOMPILED units across 40 resolved volumes. The two missing recognized acquisition identities 288.1/288.2 remain acquisition-only CHAPTER_COUNT_DISAGREEMENT. No new defect was found; existing tail gating and special authority controls pass. Next action: acquire the missing recognized units, not manufacture volume assignments.

### Kaiju No. 8, Golden Kamuy and Vinland Saga

All three fresh audits remain four-axis PASS with no persisted holes: 130/130/16, 314/314/31 and 223/223/29 logical/mapped/volume counts respectively. No runtime change or correction is needed. This certifies the current metadata audit result, not manual inspection of every page.

## Captured offline replay versus fresh network evidence

A separate network- and SQLite-blocked replay used exact selected acquisition rows, captured reference bundles and captured curation for all ten. It compared the original consumer implementation saved before editing with the repaired implementation on identical inputs. All seven count fields stayed identical in that controlled before/after replay; the false conflicts disappeared.

The packet does not include complete raw peer inventories. The replay did not invent them. Consequently its absolute peer-corroboration counts are lower than the full production/fresh audits for Haikyu (402 versus 408), Kaiju (129 versus 130) and Vinland (220 versus 223). These are missing-input limitations present before and after the repair, not regressions. Fresh live audits supply the valid baseline comparisons and restore those original counts. Exact replay inputs/results are preserved in `replay.py`, `replay-results.json` and `replay-*-publication.json`.

## Files changed or added

- EDIT `C:\MangaAnka DDK\ddk_publisher_reference.py` — unique explicit terminal identity, independently checked at the consumer boundary.
- NEW `C:\MangaAnka DDK\tests\test_publisher_completion_authority.py` — twelve deterministic regressions.
- NEW `C:\MangaAnka DDK\tests\smoke_packaged_publisher_completion.py` — frozen source verification and offline packaged-code regressions.
- NEW `C:\MangaAnka DDK\tests\fixtures\publisher_completion\100003.bin`, `100010.bin`, `100014.bin`, `100026.bin` — unmodified public publisher responses.
- NEW `C:\MangaAnka DDK\tests\fixtures\publisher_completion\README.md` — capture provenance.
- NEW `C:\MangaAnka DDK\DDK_BATCH004_AUTONOMOUS_VALIDATION.md` — this report.
- REBUILT `C:\MangaAnka DDK\dist\MangaAnka-Database-Development-Kit.exe`.
- Investigation-only scripts, originals, captures, baselines, disposable DB/settings and logs: `C:\MangaAnka DDK\build\batch004-autonomous-20261007\`; artifact hashes in `evidence-manifest.json`.

Plugin source changes: none. PyInstaller/spec/launcher/font changes: none. The existing spec still excludes packaged shared-core snapshots and loads the authoritative local plugin. Tk fallback is intact. No migrations; SQLite timeout/journal/writer-lock architecture, schema 7, Grammar 3, acceptance/curation semantics, structural authority hierarchy, ranking, providers and canonical-special logic are unchanged.

## Validation

- New/focused publisher suites: 44 passed in 0.881 seconds.
- Full DDK initial run: 708 passed in 389.681 seconds. This run collected ten new tests; two actual-response fixture tests were added afterward.
- Full DDK final run (including all twelve new tests): 710 passed in 358.572 seconds.
- Focused shared-core publication manifest, specials, freshness, reference integration and MangaK adapter: 112 passed in 1.486 seconds.
- Packaged-code offline suite: 133 passed in 39.636 seconds.
- Python compile checks passed for the changed runtime file and both new Python test/smoke files.
- Fresh disposable live audits: 10/10 linked and persisted; reviewed correction replay and normal re-audit for both applicable works; integrity ok, schema 7, no acceptances.
- Captured Dandadan canonical-special regression is included in source and packaged suites; its expected 246 main, 248 logical, 221 total mapped, 27 uncompiled, zero unmapped main, 25 released volumes, 26.5/193.1 residuals and PASS/PASS/REVIEW/PARTIAL health are unchanged.
- Existing Qt tests run within the full DDK suite and selected packaged suites. No Qt source changed. The prior nine window/scale smokes were not repeated; no new interactive GUI or DPI certification is claimed.
- Actual rebuilt EXE startup passed: the process stayed alive, created schema 7, and integrity check returned ok, using an explicit new disposable TEST DB and isolated settings. Results: `packaged-startup-results.json`. Frozen code tests are not an interactive EXE workflow test. Offscreen startup is not interactive GUI validation.
- No full plugin repository suite was run. Shared worktree status is unchanged. Existing DDK root source/spec hashes confirm only the publisher runtime file changed; unrelated modifications were preserved.

## Build and manual check

Primary launcher: `C:\MangaAnka DDK\Launch_MangaAnka_DDK.bat`.
Legacy Tk launcher: `C:\MangaAnka DDK\Launch_MangaAnka_DDK_Legacy_Tk.bat`.
Final EXE: `C:\MangaAnka DDK\dist\MangaAnka-Database-Development-Kit.exe`.
EXE size: 52,547,774 bytes. SHA-256: `a9019855600fba600689006dc878b69facc44db37319e371ea3c45c30f3607c3`.

1. Restart via the primary launcher and select Batch 004.
2. Manually Force Re-Audit the three affected titles (or use the existing confirmed batch action). Export a fresh pinned packet.
3. Confirm no chapter-4 publisher conflict remains. Haikyu CODE findings and Dr. STONE volume-27/fraction findings must remain visible; The Promised Neverland acquisition PARTIAL may remain.
4. Confirm Black Clover still has 392 mapped main units and REVIEW for 0/393, and the two existing reviewed chapter-volume corrections remain effective.
5. Review remaining evidence normally before any separate acceptance. Do not reuse the historical packet guards after catalog mutations.

## Stop condition and limitations

One investigation/repair cycle was completed. The reproducible in-scope software defect is repaired. Other remaining findings require unavailable per-record identity evidence or a separate decision about the protected automatic-versus-curated tail gate. No repeated policy edits were made to increase PASS counts.

Explicit English terminal-label support is deliberately bounded; completed works without a unique supported terminal label remain open. Official book TOCs are retained as investigation evidence, not a new automatic numeric bridge. Metadata-only audits cannot detect wrong pages or mixed editions behind correctly shaped chapter keys. Some exact publisher creator aliases remain unmatched conservatively. Live network results are time-specific; captured replay does not reconstruct absent peer inventories. Native interactive packaged GUI and legacy Tk launches were not repeated in this pass.
