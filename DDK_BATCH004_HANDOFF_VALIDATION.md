# BATCH 004 publication and guarded review handoff

Authoritative input: the user-supplied fresh Working Set packet, copied to
`C:\MangaAnka DDK\build\batch004-handoff\fresh-export.json`.
SHA-256: `4fea07bfaceacbb8f4ea173aecbff40ff5f9af4d6153c52f142138be0389439d`.
Its database UUID is `ef8a838e-ae2a-4fe2-bb48-45ae83e2e233`, BATCH 004 UUID
`1b2fdd82-2bfe-4574-afab-ea4d377e4569`, and export mode is explicitly `pinned`.
The packet was read; its source production database was never opened.
Publication replays retain the fresh audits' 2026-10-07 cutoff.

# Sakamoto Days

Baseline: **Audit 52 revision 2**, work 27,
`anilist:125828|kitsu:58159`, standard/en, selected MangaK.
Item UUID `d794db04-e5f4-40a5-a98f-5d11c07fd635`.
277 logical / 254 mapped / 23 unmapped / 0 uncompiled / 28 projected volumes.
Health: identity PASS, publication REVIEW, normalization REVIEW, acquisition PASS.

## Chapter 232: CURATION / DATA

| Source | Chapter | Volume | Title | Source identity | Evidence type | Compatibility | Trust status | Conclusion |
|---|---:|---:|---|---|---|---|---|---|
| Shueisha official TOC | 232 | 26 | Worry Wins / 心配が勝つ | ISBN 978-4-08-884867-9 | Explicit published TOC | Standard Sakamoto Days | Publisher primary evidence | Supports 26 |
| Shueisha official TOC | 218–226 | 25 | — | ISBN 978-4-08-884810-5 | Explicit full volume TOC | Same work and edition | Publisher primary evidence | 232 is not in 25 |
| Wikipedia | 232 | 26 | Worry Wins | page 78225153, revision 1378514757 | Explicit membership | Validated compatible chapter list | Trusted reference, still fallible | Agrees with publisher |
| MangaDex | 232 | 25 | — | 9d9b04ad-9a83-49f4-8ae4-a9a3780fe9c0 | Explicit aggregate metadata | Validated standard work | Passes generic integrity; claim factually wrong | Preserve automatic conflict pending reviewed correction |

Sources: [official volume 26 TOC](https://www.s-manga.net/items/contents.html?jdcn=08X10000000069979000),
[official volume 25 TOC](https://www.s-manga.net/items/contents.html?jdcn=08X10000000067724700).
The publisher settles the factual membership. No general invalid-source pattern
was established: neither adapter should acquire a title-specific exception or an
unimplemented automatic publisher preference. A reviewed 232 → 26 overlay is
justified. Automatic conflicting evidence remains preserved beneath that overlay.

## Chapters 256–277: explicit uncollected candidates; REVIEW remains

The exact captured Wikipedia chapter list explicitly places all 22 serialized
main chapters under its uncollected heading. Volume 28 is dated 2026-08-04;
volume 29 is an empty future row dated 2026-11-04. The publisher's
[November release schedule](https://books.shueisha.co.jp/newcomics/index.html?genre=inherit&month=next)
also lists volume 29 for November 4, after this audit's cutoff. No explicit
chapter → volume 29 membership was established. Sequence alone was not used.
The schedule URL is date-relative; the observation is as of October 7, 2026.

Two distinct gates were identified:

1. **GENERIC CODE DEFECT, repaired:** a reported total including an explicitly
   known future volume incorrectly failed released-structure completeness.
   The evaluator now accounts for a total only if every numbered volume through
   it is explicitly released or future. Unknown totals, undated listings, gaps,
   newly released empty volumes and conflicts still block. It does not add a
   chapter mapping or promote a future volume to released.
2. **Legitimate remaining gate:** the unresolved 232 conflict is inside the
   released structure. The candidate set is therefore not a clean trailing
   suffix, and the complete released projection is still unproved. Global
   conflict/completeness gates and central acceptance's automatic-evidence
   recheck were deliberately preserved.

Terminal classification for the current tail: **RESEARCH / REVIEW**, with explicit
uncollected provenance; it is not yet automatically established UNCOMPILED.
A hypothetical reviewed 232 correction yields 255 mapped / 22 unmapped, still
0 uncompiled. This pass does not change the policy to authorize UNCOMPILED from
curation in place of the existing automatic proof. If the upstream 232 claim is
corrected and the rest stays complete, the generic future-total repair removes
that independent obstacle. The synthetic tests exercise that clean case.

## Provider residue: RESEARCH, CODE findings retained

The fresh normalization has 277 main, 101 fractional candidates, 30 split
candidates, 3 unclassified and 1 duplicate among 412 raw records. The previous
Days-label repair remains intact. Captured reader metadata from October 7 was
reused; no image content was downloaded or visually compared.

| Representative MangaK record | Stable ID | Pages | Finding |
|---|---|---:|---|
| 0 | jD6wepR2 | 38 | Numeric label only; unclassified remains |
| 0.1 | p29X1W6D | 38 | Not proved to be half a main chapter |
| 0.2 | 9YJ6KW5Y | 40 | Same limitation |
| 0.3 | QDwKAmxD | 46 | Full-length upload; identity unknown |
| 0.9 | MDoVWGGY | 46 | Same limitation |
| 1 / 1.1 / 1.9 | EDVdXXz8 / WYXGdV48 / G8nxoeZD | 52 / 38 / 38 | Heterogeneous neighboring uploads |
| 14.4 | oYOvXA58 | 19 | Normal-looking length does not identify a work |
| 22 / 22.1 / 23 | eDkj6NgY / DBEXX5eY / yDERB5q2 | 21 / 42 / 19 | 22.1 is not proved a split or special |
| 300 | KY5PAx58 | 38 | Unsupported integer; unclassified remains |
| 307 | M2zvxE42 | 19 | Unsupported integer; unclassified remains |

Exact reader URLs and complete metadata are retained in
`C:\MangaAnka DDK\build\batch004-publication\provider-samples.json`.
The provider's native `number` is an ordering ordinal (main chapter 1 has ordinal
11), not a second canonical chapter number. Early decimal runs were inserted
2026-05-26; 22.1 was inserted 2026-06-22. Neighboring established main uploads
have explicit Days titles, while the suspicious records mostly have numeric
labels. None of the sampled full image-URL sequences are identical, but different
URLs cannot establish different content. No safe rule classifies all 131 records
as splits, duplicates, specials or artifacts. All CODE findings remain active.

Automatic fresh replay after repair: **unchanged 277 / 254 / 23 / 0 / 28** and
PASS/REVIEW/REVIEW/PASS. Remaining blockers: 232 automatic conflict, the unresolved
tail proof, fractional/split CODE groups, and 0/300/307 research.

# Dr. STONE

Baseline: **Audit 51 revision 1**, work 28,
`anilist:98416|kitsu:38860`, standard/en, selected Atsu.
Item UUID `1f15d2f0-2756-46c5-aba1-84c0d08327a0`.
232 logical / 231 mapped / 1 unmapped / 0 uncompiled / 26 projected volumes.
Health: PASS/REVIEW/REVIEW/PARTIAL.

## Chapter 206: CURATION / DATA, internal Wikipedia ambiguity

| Source | Claim | Identity / evidence | Conclusion |
|---|---|---|---|
| Wikipedia volume 23 | 206, Universe of Zeroes and Ones | page 58423826, revision 1372940792; explicit bullet | Numbering error |
| Wikipedia volume 24 | 206, Dawn of the Computer | Same exact page/revision; explicit bullet | Correct 206 claim |
| MangaDex | No mapping for 206 | cfc3d743-bd89-48e2-991f-63e680cc4edf; valid aggregate | Not a MangaDex/Wikipedia 206 disagreement |
| Shueisha volume 23 | 197–205; Zeroes and Ones is 205 | ISBN 978-4-08-882820-6; explicit TOC | Confirms erroneous Wikipedia labeling |
| Shueisha volume 24 | 206–214; Computer is 206 | ISBN 978-4-08-882877-0; explicit TOC | Supports 206 → 24 |

Sources: [official volume 23 TOC](https://www.s-manga.net/items/contents.html?jdcn=08X10000000017856300),
[official volume 24 TOC](https://www.s-manga.net/items/contents.html?jdcn=08X10000000018964600).
Wikipedia omits the 202 label and shifts later labels in volume 23. The actual
parser preserves these supplied claims; it is not misparsing two correct labels.
The manifest quarantines 206 through `ambiguous_chapter_keys`; projection fails
closed. `reference_conflicts: []` is the cross-source reconciler's diagnostic,
so its emptiness does not mean there is no internal source ambiguity. The raw
Wikipedia rows and manifest ambiguity are already serialized in the audit.
No new diagnostic or reconciliation policy was required.

A reviewed 206 → 24 correction is justified. Simulation produces **232 mapped /
0 unmapped**, preserves automatic ambiguity provenance and leaves volume 27,
decimal CODE findings, and acquisition warnings unresolved.

## Volume 27: known supplementary compilation; identity bridge remains RESEARCH

[Shueisha's official volume 27 TOC](https://www.s-manga.net/items/contents.html?jdcn=08X10000000040243800)
(ISBN 978-4-08-884037-6, released 2024-04-04) lists Terraforming and the three
4D Science installments: Future Message, Future Road Map, Future Science.
[VIZ's official 4D Science listing](https://www.viz.com/shonenjump/chapters/dr-stone-4d-science)
independently identifies a three-chapter limited series and links the numbered
Dr. STONE volume 27. This is an official main-title supplementary compilation,
not ordinary serial main chapters 233–236 and not Reboot: Byakuya.

The Wikipedia input already contains named Terraforming and nested named bonus
entries. The present numeric membership contract cannot supply a trusted numeric
identity bridge from those names to four provider decimals. Bibliography knows
27 released volumes; the acquisition-backed numerical projection currently has
26. Volume 27 belongs in the publication bibliography, but cannot be fabricated
as four canonical main units or silently filled from upload order.

Separate catalog identities remain distinct: main AniList 98416/Kitsu 38860;
Byakuya 112673/55534; 4D Science 170755/70240; Terraforming 152129/64798.
The unresolved part is supplementary-unit membership/identity projection, not
proof that the volume or its contents do not exist. No broad named-unit model or
cross-work merge was introduced in this narrow repair.

## Atsu decimals: four independent RESEARCH outcomes, CODE retained

| Record | Stable chapter ID / reader | Pages | Provider title | Conclusion |
|---|---|---:|---|---|
| 232.5 | https://atsu.moe/read/raSQb/t9pBu4uK | 51 | Z= 232.5 | Content identity unproved |
| 232.6 | https://atsu.moe/read/raSQb/hK7h4qFH | 42 | Z= 232.6 | Content identity unproved |
| 232.7 | https://atsu.moe/read/raSQb/Bzzzt6Bx | 45 | Z= 232.7 | Content identity unproved |
| 232.8 | https://atsu.moe/read/raSQb/sVUfjGD5 | 46 | Z= 232.8 | Content identity unproved |

All are in the same captured Atsu group `cmgzkia1m00jpm191mwl2bsp1`.
Length/order makes later supplementary material plausible, but numeric titles
and page counts cannot establish which work or installment any upload contains.
No record was declared a legitimate special, split, artifact, or alias of a
separately cataloged work. Image content identity remains unverified.
`PROVIDER_FRACTIONAL_CANDIDATE` remains CODE. Missing 4.5/18.5 remain
**ACQUISITION ONLY**, with no curation commands.

Automatic fresh replay after repair: **unchanged 232 / 231 / 1 / 0 / 26** and
PASS/REVIEW/REVIEW/PARTIAL. No Dr. STONE runtime special case was added.

# Working Set Guard Export

Existing authority remains `ddk_review.database_revision`, `audit_revision`,
and the unchanged Grammar 3 Catalog Preview/Apply validator. The token is exactly
`a<max audit ID>-e<max curated event ID>-d<max disposition ID>-w<work count>`.
The old per-work exporter formatted this guard; the Working Set exporter merely
copied raw audits and holes, omitting that existing authority.

One shared `ddk_review.review_guard` now generates the canonical command for both
paths. Working Set entries add `review_guard` with database UUID, work ID/UUID,
audit ID/revision, exact existing database token, edition/language/publication
context, current and audited curation revisions, latest audit ID, current-audit
indicator, and `command`. Root fields add `database_revision` and
`command_grammar_version: 3`. Unlinked or auditless entries have a null guard.

Pins, audits, observations, curation metadata and token are read on one SQLite
connection in one deferred read snapshot. Optional connection arguments were
added to three Working Set read helpers. No write transaction, writer-lock
change, journal/timeout setting, schema migration, or catalog mutation is added.
A concurrent-writer WAL fixture proves the export cannot mix dependencies;
WAL is used only in that test, not configured by product code.

Pinned historical exports retain the exact historical audit guard. Preview
rejects them rather than silently substituting the latest audit. Current exports
remain explicitly `mode=current`. The guard's current-audit indicator describes
ID currency; it does not override curation freshness, identity, or acceptance
checks. A fresh guard after curation still requires the existing re-audit policy
for that same work. Preview and Apply continue to recheck stale dependencies.

Format remains `mangaanka-ddk-working-set-review-v1`; raw entry fields and the old
per-work packet's `guard` string remain compatible. Existing packet consumers
need not require the new field. This codebase has no import/mutation parser for
old Working Set packets; compatibility means additive read-only JSON, not
inventing a new packet import path. An old guardless packet cannot safely supply
a missing global token.

Grammar 3 guards are **work-scoped**, not new item-scoped tokens. Unique audit IDs
bind another work/edition/language out. Exact membership UUIDs remain in the
entry and Qt Preview/Apply retain their existing independent membership checks.
Two memberships deliberately pointing to the same work do not gain distinct
Grammar authority; duplicating guards would require changing the contract,
which this task forbids. No such stronger guarantee is claimed.

Example from the tested **disposable** export (not valid for production):

```json
{
  "database_uuid": "9a2ddeac-f86b-43e9-8191-89f86bd85f41",
  "work_id": 1,
  "work_uuid": "f3c366d4-8139-455e-bdf6-8333ca7c7133",
  "audit_id": 1,
  "audit_revision": 1,
  "database_revision": "a2-e0-d0-w2",
  "edition": "standard",
  "language": "en",
  "publication_context": "",
  "curation_revision": 0,
  "audit_curation_revision": 0,
  "latest_global_audit_id": 1,
  "audit_is_current": true,
  "command": "guard database_uuid 9a2ddeac-f86b-43e9-8191-89f86bd85f41 audit 1 revision 1 database a2-e0-d0-w2"
}
```

Complete disposable examples and actual export:

- `C:\MangaAnka DDK\build\batch004-handoff\disposable-guard-packet.json`
- `C:\MangaAnka DDK\build\batch004-handoff\disposable-0-commands.txt`
- `C:\MangaAnka DDK\build\batch004-handoff\disposable-1-commands.txt`
- `C:\MangaAnka DDK\build\batch004-handoff\guard-preview-results.json`

Both complete batches validate through the real Qt command controller and
Grammar 3 Catalog Preview. Disposable Apply preserves immutable audits and pins,
stores the reviewed mapping plus source-note/evidence, and accepts nothing.
Applying one batch invalidates the other's old global token; a newly exported
second guard validates. These exact test guards intentionally reject production.

# Curation

Only two corrections are factually justified: Sakamoto 232 → 26; Dr. STONE
206 → 24. The files above contain complete tested Grammar 3 batches, including
source-note, verification and publisher evidence. They are disposable examples,
not commands authorized against the production database.

The supplied fresh production packet predates this export repair and lacks the
global database token. Its exact live guard cannot be reconstructed from the
visible entries, and no production DB was opened to obtain it. Export a new
pinned packet from the rebuilt EXE. Use that exact entry's `review_guard.command`
as the first line, followed by the corresponding tested command body. Preview
before Apply. Re-export after an intervening curation/re-audit, since the token
is database-wide. No commands are justified for the CODE groups, supplementary
identity research, acquisition gaps, or uncertain provider artifacts.

# Validation

- Guard regression before implementation: original 15 tests failed on missing guard fields. Expanded **17/17** pass after repair (2.414 seconds).
- Future-total positive regression failed before repair; **9/9** boundary tests pass after repair (0.119 seconds), including a validated real cross-reference conflict fixture.
- Focused DDK: **265/265**, 15.266 seconds.
- Full DDK: **630/630**, 312.031 seconds, including **103 Qt tests**. No skipped Qt dependency environment was used.
- Focused shared core: **261/261**, 2.199 seconds; not the full plugin suite.
- Packaged modules: **113/113** (64 + 49; 5.151 + 0.204 seconds). Embedded guard/export/read-helper code and other checked product bytecode equal current source. Shared core is dynamically loaded from the current plugin path; no embedded core snapshot or SQLite database.
- Fresh pinned **52/2, 51/1, 49/1** publication replays pass with SQLite and network access forbidden. Exact selected raw inventory comes from the fresh packet; peer records reuse captured inventories only when provider/ref/count match. Wikipedia is reparsed from captured source requests; its exact identity is preserved.
- Three complete normal audits pass in a disposable schema-7 DB using captured search/enrichment/provider I/O and the current reference parser. These reuse the earlier captured intake scenario, separately from the fresh pinned replay; no missing live state is reconstructed. Exact pins advance, unrelated sentinel remains unchanged, immutable history persists, zero acceptances.
- Two full Qt-controller Grammar 3 command batches Preview successfully. Disposable Apply stores reviewed evidence and preserves audits/pins. Applying the first invalidates the old second token; re-exporting the second succeeds. Wrong UUID/audit/revision/token/work/edition/language and stale Apply are rejected.
- Blue Lock replay: 354 mapped / 10 uncompiled / 0 unmapped / 40 volumes, PASS/PASS/PASS/PARTIAL, acquisition-only missing 288.1/.2 unchanged. MHA: 118 → 13, 432 unresolved, four CODE candidates unchanged. Black Clover remains linked. Haikyu, SPY x FAMILY, Dandadan and World Is Mine controls pass in focused/full suites; World remains 163/163 in 14 volumes. Captured Dandadan retains 246 main + 2 acquired specials = 248 logical, 221 mapped, 27 uncompiled, 25 volumes, two unresolved fractions, PASS/PASS/REVIEW/PARTIAL.
- In-memory syntax compilation of all seven changed Python files passes. No new whitespace issue; the shared file's pre-existing trailing space on its cache constant was preserved. No Qt presentation source changed, so nine DPI/window smokes were not rerun.
- Packaged normal startup creates an explicit disposable TEST schema-7 database with zero works/audits/acceptances and remains responsive. Separate INI settings prevent production session restoration. This is a bounded startup check, not an interactive GUI inspection.
- Additional CLI-only limitation: `--help` produced an exception dialog. A temporary console diagnostic build captured a cp1252 UnicodeEncodeError while argparse emits the macron in MangaAnkā. No database opens on that path. This output-encoding issue was left outside the current repair; normal disposable startup and all packaged module tests pass. Test processes were path/argument-verified and cleaned up.

# Changes and packaging

DDK product source changed:

- `C:\MangaAnka DDK\ddk_review.py`: shared existing guard serialization; optional connection for legacy revision fallback; per-work exporter reuses helper.
- `C:\MangaAnka DDK\ddk_exports.py`: additive Working Set guards and one read snapshot.
- `C:\MangaAnka DDK\ddk_working_sets.py`: optional caller-owned connections for get/items/latest_observation reads.

DDK tests changed/added:

- `C:\MangaAnka DDK\tests\test_working_set_review_guards.py`: 17 new tests.
- `C:\MangaAnka DDK\tests\test_uncompiled_future_totals.py`: nine new boundary tests.
- `C:\MangaAnka DDK\tests\smoke_packaged_artifact_authority.py`: verify frozen guard/export modules and run new packaged regressions.

Shared core changed:

- `C:\MangaNana-Dev\MangaNana-calibre\publication_freshness.py`: explicitly account for known future volumes in reported bibliography totals; retain all other proof gates.

Report: `C:\MangaAnka DDK\DDK_BATCH004_HANDOFF_VALIDATION.md`.
Investigation/validation scripts and outputs are under
`C:\MangaAnka DDK\build\batch004-handoff`: validate.py, replay_handoff.py,
full_replay.py, verify_packaged.py; temporary MangaAnka-Diagnostic.spec; copied scoped captures, disposable packet and
commands, fresh/full replay JSON, and before/after/test/build logs.
No previous repair was redone. In particular, Days parser version 8 stays intact.
No Qt/Tk presentation source or PyInstaller spec changed.

Primary EXE: `C:\MangaAnka DDK\dist\MangaAnka-Database-Development-Kit.exe`.
Primary launcher: `C:\MangaAnka DDK\Launch_MangaAnka_DDK.bat`.
Legacy fallback: `C:\MangaAnka DDK\Launch_MangaAnka_DDK_Legacy_Tk.bat` (untouched).
EXE_- Guard regression before implementation: original 15 tests failed on missing guard fields. Expanded **17/17** pass after repair (2.414 seconds).
- Future-total positive regression failed before repair; **9/9** boundary tests pass after repair (0.119 seconds), including a validated real cross-reference conflict fixture.
- Focused DDK: **265/265**, 15.266 seconds.
- Full DDK: **630/630**, 312.031 seconds, including **103 Qt tests**. No skipped Qt dependency environment was used.
- Focused shared core: **261/261**, 2.199 seconds; not the full plugin suite.
- Packaged modules: **113/113** (64 + 49; 5.151 + 0.204 seconds). Embedded guard/export/read-helper code and other checked product bytecode equal current source. Shared core is dynamically loaded from the current plugin path; no embedded core snapshot or SQLite database.
- Fresh pinned **52/2, 51/1, 49/1** publication replays pass with SQLite and network access forbidden. Exact selected raw inventory comes from the fresh packet; peer records reuse captured inventories only when provider/ref/count match. Wikipedia is reparsed from captured source requests; its exact identity is preserved.
- Three complete normal audits pass in a disposable schema-7 DB using captured search/enrichment/provider I/O and the current reference parser. These reuse the earlier captured intake scenario, separately from the fresh pinned replay; no missing live state is reconstructed. Exact pins advance, unrelated sentinel remains unchanged, immutable history persists, zero acceptances.
- Two full Qt-controller Grammar 3 command batches Preview successfully. Disposable Apply stores reviewed evidence and preserves audits/pins. Applying the first invalidates the old second token; re-exporting the second succeeds. Wrong UUID/audit/revision/token/work/edition/language and stale Apply are rejected.
- Blue Lock replay: 354 mapped / 10 uncompiled / 0 unmapped / 40 volumes, PASS/PASS/PASS/PARTIAL, acquisition-only missing 288.1/.2 unchanged. MHA: 118 → 13, 432 unresolved, four CODE candidates unchanged. Black Clover remains linked. Haikyu, SPY x FAMILY, Dandadan and World Is Mine controls pass in focused/full suites; World remains 163/163 in 14 volumes. Captured Dandadan retains 246 main + 2 acquired specials = 248 logical, 221 mapped, 27 uncompiled, 25 volumes, two unresolved fractions, PASS/PASS/REVIEW/PARTIAL.
- In-memory syntax compilation of all seven changed Python files passes. No new whitespace issue; the shared file's pre-existing trailing space on its cache constant was preserved. No Qt presentation source changed, so nine DPI/window smokes were not rerun.
- Packaged normal startup creates an explicit disposable TEST schema-7 database with zero works/audits/acceptances and remains responsive. Separate INI settings prevent production session restoration. This is a bounded startup check, not an interactive GUI inspection.
- Additional CLI-only limitation: `--help` produced an exception dialog. A temporary console diagnostic build captured a cp1252 UnicodeEncodeError while argparse emits the macron in MangaAnkā. No database opens on that path. This output-encoding issue was left outside the current repair; normal disposable startup and all packaged module tests pass. Test processes were path/argument-verified and cleaned up.

# Manual retest

1. Restart with the primary launcher to load the rebuilt export code and current shared evaluator.
2. Force Re-Audit Sakamoto Days to refresh the generic future-total evaluator. With unchanged references expect 277 logical / 254 mapped / 23 unmapped / 0 uncompiled / 28 volumes and the existing conflict/CODE findings. Do not expect forced-green behavior.
3. Export a **fresh pinned** BATCH 004 packet. Check both linked entries have `review_guard.command`, exact pins, and Grammar 3 metadata. The previous guardless production packet must be replaced for curation handoff; no second richer per-work export is needed.
4. If approving the evidenced correction, Preview then Apply only Sakamoto 232 → 26 with its new exact guard and evidence. Force Re-Audit and export fresh. Expect the correction simulation's 255 mapped / 22 unresolved tail unless upstream evidence has changed.
5. Re-export before the Dr. STONE batch to obtain its current global token. Preview then Apply only 206 → 24, Force Re-Audit Dr. STONE, and export fresh. Expect 232 mapped main units but the volume 27/decimal findings to remain. Dr. STONE does not need re-audit merely for the future-total fix; it needs it after curation under the existing lifecycle.
6. Do not accept either title while its CODE/research blockers remain. The Promised Neverland remains acceptance-compatible; any existing human acceptance stays untouched.

# Safety and known limitations

Production DB untouched; no production acceptance, audit, pin, failed intake,
curation, or schema was changed. All mutation tests used disposable databases.
DDK version 0.3.0, schema 7 and Grammar 3 remain unchanged. Acceptance stays
explicit human approval. No provider/ranking/identity/normalization changes,
reference-conflict weakening, CODE suppression, title-specific runtime hacks,
commits, pushes, tags, releases, reset/clean or version bumps.

Unresolved limitations are explicit: provider content identity was not verified
from images; supplementary named units still lack a canonical numeric bridge;
Sakamoto's tail remains blocked by released-structure conflict proof; existing
work-scoped Grammar cannot become item-scoped without a contract change; the
production token must come from the user's new export; CLI --help has the separate ANSI output-encoding limitation described above. Live upstream evidence
may change after these captures. No new interactive desktop or DPI smoke is
claimed when no Qt presentation code changed.
