# BATCH 004 publication/reference investigation

Validated 2026-10-07. One generic parser repair; neither target is forced green.

## Authoritative snapshot and evidence basis

The user confirmed that the requested `export(6).json` is locally named
`C:\Users\Jerry\Documents\MangaAnka-Database-Development-Kit\export.json`.
Its SHA-256 is `77944e1d80f425f9586de589fce3728efe6b0eae9a0eb48d462bb4af550b98b2`.
It contains Sakamoto Days Audit 50/1, Dr. STONE Audit 51/1 and The Promised
Neverland Audit 49/1, with publication as-of 2026-10-07. Schema is 7.

Only that named export was read from the protected catalog directory. No
production SQLite database was opened, even read-only.

Public API refreshes confirmed that both Wikipedia revisions are still current:
Sakamoto page 78225153, revision 1378514757; Dr. STONE page 58423826,
revision 1372940792. Raw wikitext and responses are retained in
`C:\MangaAnka DDK\build\batch004-publication`.

Fresh-export publication replays use its selected raw acquisition records,
references, frozen trusted identity and as-of date. Compact search cards omit
trusted identity fields, so those fields are restored from that same audit's
context, without reopening identity. Peer raw inventories were not serialized;
previously captured peer rows are reused only on exact provider/ref/count
matches. This limitation is explicit, not a claim of byte-exact historical I/O.
Separate complete normal audits use captured I/O and disposable schema-7 DBs.

## Dr. STONE

Baseline: `anilist:98416|kitsu:38860`, standard/en, Atsu, 236 raw acquisition
records, 232 logical, 231 mapped, 1 unmapped, 0 uncompiled, 26 final volumes.
Health: identity PASS, publication REVIEW, normalization REVIEW, acquisition PARTIAL.

### Chapter 206 evidence

| Source | Claimed chapter | Volume | Source identity | Internal integrity | Compatibility | Eligible for reconciliation? | Reason |
|---|---|---|---|---|---|---|---|
| Wikipedia | 206, “Universe of Zeroes and Ones” | 23 | page 58423826 / revision 1372940792 | Invalid at key 206: duplicate conflicting membership | Exact standard work | No automatic winning assignment for this key | Same page also assigns 206 to 24 |
| Wikipedia | 206, “Dawn of the Computer” | 24 | same exact page/revision | Same key-level ambiguity | Exact standard work | No automatic winning assignment for this key | Correct against publisher, but parser cannot choose from its own contradictory claims |
| MangaDex | No 206 claim | — | cfc3d743-bd89-48e2-991f-63e680cc4edf | Valid aggregate; 207 mappings / 23 volumes | Exact standard work | No assignment available | No MangaDex-versus-Wikipedia conflict at 206 |
| Selected Atsu inventory | 206 | none | main-serial raSQb acquisition | No explicit native volume | Exact standard work | Acquisition only | Does not break structural tie |
| Shueisha digital TOC | Z=206, computer chapter | 24 | ISBN 978-4-08-882877-0 / digital product 08X10000000018964600 | Explicit publisher membership | Exact standard volume | Suitable human curation evidence | Not an existing automatic structural adapter |
| Shueisha digital TOC | Z=205, zeroes/ones chapter | 23 | ISBN 978-4-08-882820-6 / digital product 08X10000000017856300 | Explicit publisher membership | Exact standard volume | Suitable corroboration | Establishes Wikipedia's erroneous label |

The publisher's [volume 23 TOC](https://www.s-manga.net/items/contents.html?jdcn=08X10000000017856300)
lists 197–205 explicitly. Wikipedia skips label 202 and shifts the remaining
four volume-23 labels to 203–206. The
[volume 24 TOC](https://www.s-manga.net/items/contents.html?jdcn=08X10000000018964600)
explicitly places 206–214 in volume 24. This is a source-data error, not a
numbered-list parser error. Existing MangaDex memberships keep 202–205 in
volume 23; their Wikipedia titles should not be treated as newly verified.

`PublicationManifestBuilder.apply_wikipedia()` detects multiple volumes for
one key and puts 206 in `manifest.ambiguous_chapter_keys`. The acquisition
projection leaves it unresolved; DDK emits REFERENCE_CONFLICT.
`reference_conflicts` contains cross-source reconciliation conflicts, so it is
empty here. This is an existing split diagnostic representation, potentially
confusing to a reader, but safe: neither claim silently wins. A synthetic test
now explicitly preserves this behavior. No whole-page quarantine or
cross-source reconciliation change is warranted by this case.

Outcome: **CURATION/DATA**. A verified chapter-206 → volume-24 override is
factually justified. In a nonpersisting catalog-overlay simulation, mapping
becomes 232/232; the automatic conflict remains preserved in provenance.
No production correction was applied.

### Volume 27

Shueisha's [explicit digital TOC](https://www.s-manga.net/items/contents.html?jdcn=08X10000000040243800)
identifies four contents: Terraforming, then the three 4D Science parts
labelled 1D, 2D and 3D. This is an actual main-series numbered volume containing
later material, not Byakuya and not ordinary main chapters 233–236.
The [English volume](https://www.viz.com/manga-books/manga/dr-stone-volume-27/product/8342/paperback)
is also published. Japanese release was April 4, 2024.

The exact Wikipedia template exposes `One-shot: "Terraforming"` and a nested
`Bonus: 4D Science` list with 1D/2D/3D. The current numeric membership parser
does not produce canonical numeric acquisition identities for those rows.
The publisher TOC establishes publication contents, but neither source
establishes that Atsu's 232.5–232.8 are the corresponding uploads.

Thus 26 is the current resolved acquisition-volume count, not proof that the
publication has only 26 volumes. The publication view remains incomplete.
Outcome: **RESEARCH**, specifically acquisition-to-published-unit identity.
No guessed range, fabricated decimal identity or merging of separately
cataloged sequels was introduced. Named/nested supplementary-unit support
would need a general identity representation and explicit acquisition bridge.

### Atsu 232.5–232.8

| Provider identifier | Stable reader suffix | Pages | Reader title |
|---|---|---:|---|
| 232.5 | t9pBu4uK | 51 | Z= 232.5 |
| 232.6 | hK7h4qFH | 42 | Z= 232.6 |
| 232.7 | Bzzzt6Bx | 45 | Z= 232.7 |
| 232.8 | sVUfjGD5 | 46 | Z= 232.8 |

All four are real readable records in the same acquisition group. Length and
order are consistent with later substantial material, but do not prove exact
Terraforming/4D Science correspondence. Reader metadata provides no independent
published title. Images were not downloaded or visually compared.
Outcome: **RESEARCH; existing CODE findings retained**. None was declared a
split, duplicate, artifact or recognized special merely from its suffix.

4.5/18.5 remain **ACQUISITION_ONLY**. No normalization, provider-selection or
acceptance policy changed. Automatic post-fix counts and health are unchanged.

## Sakamoto Days

Baseline: `anilist:125828|kitsu:58159`, standard/en, MangaK, 412 raw records,
254 logical, 32 mapped, 222 unmapped, 0 uncompiled, 6 final volumes.
Health: PASS / REVIEW / REVIEW / PASS.

### Wikipedia parser forensics and repair

Exact page: `List of Sakamoto Days chapters`, page 78225153, revision 1378514757.
Relevant headings: main-work `Sakamoto Days`, child `Volumes`, child
`Chapters not yet in tankōbon format`; sibling `Sakamoto Holidays` is separate.
The existing exact-work section scoper correctly excludes that sibling.

The page uses already supported Graphic novel list templates, VolumeNumber,
ChapterList and ChapterListCol2 fields. Contents are explicitly numbered:
`*Days 1: ...`, with later rows using `*Days 232. ...`. Nested Nihongo title
templates are already supported. Parsing takes the normal single-page
`resolve_publication` → `_segment_from_page` → `_parse_graphic_lists` path.
The label recognizer accepted Chapter/Episode/Round but not Days. Volume rows
were read, chapter rows were missed, and status became supported_empty.

Outcome: **GENERIC CODE DEFECT, repaired**. Days is now an explicit supported
numbering label, both for numbered-title rows and bounded labelled membership
expressions. It also works in the existing explicit uncollected section.
No title check, arbitrary fuzzy label match or sequential membership inference
was added. Parser contract advances 7 → 8; old segment and outer structure
caches cannot conceal new memberships. Application/plugin versions stay fixed.

Automatic replay: 277 logical, 254 mapped, 23 unmapped, 0 uncompiled, 28 final
volumes, 3 unclassified records. Existing reference authority promotes 23
previously unclassified integers, without weakening normalization policy.
The 101 fractional and 30 split candidates remain CODE.

### Newly exposed reference conflict and uncollected tail

MangaDex explicitly assigns chapter 232 to volume 25. Wikipedia explicitly
assigns it to volume 26. Both pass existing identity/integrity checks, so the
reconciler fails closed. Shueisha's
[volume 25 TOC](https://www.s-manga.net/items/contents.html?jdcn=08X10000000067724700)
explicitly lists 218–226; its
[volume 26 TOC](https://www.s-manga.net/items/contents.html?jdcn=08X10000000069979000)
lists 227–235, including 232. Outcome: **CURATION/DATA**, with publisher-backed
232 → volume 26 correction justified; no automatic source-preference rule.

Wikipedia explicitly identifies 256–277 as uncollected. They are retained as
22 candidate records, not assigned to invented volumes. Current fail-closed
gates still prevent UNCOMPILED: unresolved 232 breaks a trailing-only unmapped
suffix and no-conflict checks; the complete-release check also fails, including
reported count 29 versus 28 released volumes. Volume 29 is dated November 4,
2026 in the inspected page and is future at the audit date. A data override
for 232 does not automatically relax these source-completeness checks.

The nonpersisting verified-correction simulation reaches 255 mapped / 22
unmapped / 0 uncompiled. This is a remaining boundary limitation to investigate
separately; freshness/UNCOMPILED policy was deliberately preserved.

### Provider samples

| Identifier(s) | Pages in inspected records | Evidence and disposition |
|---|---|---|
| 0 / 0.1 / 0.2 | 38 / 38 / 40 | Distinct IDs; 0.1/.2 are not demonstrated half-chapters |
| 0.3 / 0.9 | 46 / 46 | Substantial lengths, numeric-only titles |
| 1 / 1.1 / 1.9 | 52 / 38 / 38 | Original integer record and later inserted decimal records |
| 14.4 / 15 | 19 / 21 | End of long decimal run adjacent to titled normal chapter |
| 22 / 22.1 / 23 | 21 / 42 / 19 | Isolated 22.1 differs from the early dense pattern |
| 31 / 53 / 54 | 19 / 19 / 18 | Titled integer records now supported by explicit Wikipedia memberships |
| 300 / 307 | 38 / 19 | Outliers beyond the independently evidenced serial extent |

Stable reader URLs, native IDs, titles, ordinal positions, dates and page counts
are saved in provider-samples.json. Early decimal uploads were inserted in
May 2026; the inspected 22.1 was inserted in June 2026; established integers
have older dates. The reader's `number` field is its list position (for example
ordinary chapter 1 has number 11), not authoritative canonical chapter numbering.
None of the 22 samples shares an identical complete image-URL sequence; that
does not prove different content, since reuploads may use different URLs.

These observations reject a confident blanket split rule. They do not establish
the content identity of every suspicious upload. Outcomes: fractional/split
groups **RESEARCH, CODE retained**; integers 31–53 **RESOLVED AUTOMATICALLY**
through existing explicit-reference authority; 0/300/307 **RESEARCH**.
No disposition, suppression or forced-green command was generated for these.

## Shared findings and before/after

The generic defect is a missing explicit Wikipedia numbering label. Dr. STONE's
remaining blockers are data and supplementary-unit identity gaps, not that label
defect. Both cases demonstrate why source validity does not prove every claim
correct, and why publication structure must stay separate from acquisition.

Health columns below are identity/publication/normalization/acquisition.

| Title / state | Mapped | Unmapped | Uncompiled | Volumes | Health | Action |
|---|---:|---:|---:|---:|---|---|
| Dr. STONE before | 231 | 1 | 0 | 26 | PASS/REVIEW/REVIEW/PARTIAL | Review |
| Dr. STONE automatic after | 231 | 1 | 0 | 26 | PASS/REVIEW/REVIEW/PARTIAL | Data correction + unit research |
| Sakamoto before | 32 | 222 | 0 | 6 | PASS/REVIEW/REVIEW/PASS | Review |
| Sakamoto automatic after | 254 | 23 | 0 | 28 | PASS/REVIEW/REVIEW/PASS | Data correction + remaining research/CODE |
| The Promised Neverland control | 182 | 0 | 0 | 20 | PASS/PASS/PASS/PARTIAL | Acceptance-compatible; not accepted automatically |

## Exact changes

Product source:

- `C:\MangaNana-Dev\MangaNana-calibre\wikipedia_reference.py`: add Days to two explicit label patterns; internal parser/cache contract 8.

Tests:

- `C:\MangaAnka DDK\tests\test_wikipedia_days_membership.py`: new 14-test synthetic suite, including pipeline, ambiguity, sibling scope, nested titles, supplementary rejection, malformed ranges, decimals, multiple tables, future/empty volumes, explicit uncollected rows and parser-cache invalidation.
- `C:\MangaAnka DDK\tests\test_wikipedia_membership_audit.py`: expected parser contract 8.
- `C:\MangaNana-Dev\MangaNana-calibre\tests\test_wikipedia_membership.py`: two expected current-cache/version values changed to 8.

Report: this file. Investigation scripts added under
`C:\MangaAnka DDK\build\batch004-publication`: replay.py, fresh_replay.py,
provider_samples.py, refresh_wikipedia.py, verify_packaged.py. The same directory
contains scoped captures, copied input inventories, replay outputs and logs.
No DDK application module or Qt/Tk UI file changed.

## Validation

- Before repair: original 12-test new suite had 6 failures and 2 errors, all missed explicit Days memberships; 4 safety cases already passed.
- After repair: expanded new suite 14/14 passes.
- Focused DDK: 203/203 passes, 6.327 seconds.
- Focused shared core: 261/261 passes, 2.055 seconds. This is not the full plugin repository suite. Two stale contract expectations were updated; an initial harness also named two nonexistent modules before selecting the actual suites.
- Full DDK: 604/604 passes, 348.236 seconds.
- Complete normal captured audits: three separate immutable audits in a disposable schema-7 DB, exact items/pins, unrelated sentinel intact, zero acceptances. Both target identities remain linked; The Promised Neverland remains 182/182 and eligible.
- Fresh-export 50/51/49 publication replays pass with both network and SQLite access forbidden.
- Verified correction simulations preserve automatic conflict provenance and leave other blockers intact.
- Packaged executable: 87 tests pass against extracted frozen DDK modules and live shared core, plus three disposable complete audits, fresh export replays and Black Clover replay. Frozen embedded product bytecode equals current DDK source; there is no embedded shared-core snapshot or database.
- Blue Lock captured replay: 354 mapped, 10 uncompiled, 0 unmapped, 40 volumes; PASS/PASS/PASS/PARTIAL; 288.1/.2 remain acquisition warnings.
- MHA captured replay: 118 remains mapped to 13; 432 remains unresolved; four fractional CODE candidates unchanged.
- Haikyu, SPY, Dandadan and World Is Mine controls pass in focused/full suites. Dandadan's captured special/artifact separation remains intact; World remains 163 mapped / 14 volumes / zero holes.
- In-memory syntax compilation and scoped Git diff whitespace checks pass. No Qt code changed; new GUI/DPI smokes were unnecessary and are not claimed.

## Curation commands and limitations

The exact export is the working-set snapshot format, not a full Grammar 3
review packet. It has database UUID and audit revisions but no database revision
token (`a…-e…-d…-w…`). That token depends on global audit/event/disposition/work
state and cannot be inferred safely from these entries. The user was asked for
the two actual fresh packet guard lines. No guard was invented and no paste-ready
unguarded edit batch is provided.

Once actual guards are available, the justified scope is only Dr. STONE 206 →
24 and Sakamoto 232 → 26, with the publisher evidence above and explicit reviewed
verification. These are data corrections, not commands to suppress CODE or
accept a title. Preview must check current audit/database revisions. No commands
are justified yet for the supplementary uploads or unexplained provider records.

Provider metadata sampling did not inspect image content or establish every
upload's canonical identity. Automatic publisher-TOC acquisition is not an
existing adapter; no new publisher integration was invented for two titles.
Named supplementary membership and Sakamoto's remaining tail completeness
boundary remain follow-up work.

## Safety and manual retest

Production DB, its existing audits, pins, curation and acceptance were untouched.
Schema 7, Grammar 3, identity repair, reference integrity/fail-closed behavior,
ranking, provider semantics, released-volume/freshness logic and acceptance
semantics remain unchanged. No title constants/hacks, commits, pushes, tags,
releases, migrations or application version bumps.

No EXE rebuild is required: the existing package loads this shared module from
the local plugin worktree, and that path was verified in packaged checks.
Current EXE: `C:\MangaAnka DDK\dist\MangaAnka-Database-Development-Kit.exe`;
SHA-256 `1d62713b6dab77d63520398f2285c50643eb9dd85e126eec63b150a38074eed4`.

1. Close and restart DDK through `C:\MangaAnka DDK\Launch_MangaAnka_DDK.bat` to load parser 8.
2. Force Re-Audit **Sakamoto Days**. With unchanged upstream evidence, expect 277 logical / 254 mapped / 23 unmapped / 0 uncompiled / 28 volumes; retain CODE and new 232 conflict. Inspect parser version 8 and explicit uncollected provenance.
3. **Dr. STONE** need not be re-audited merely for this Days-label repair; its automatic result is unchanged. After any separately reviewed data correction, Force Re-Audit Dr. STONE and export a fresh packet. Do the same for Sakamoto after its correction.
4. Optionally re-audit **The Promised Neverland** as the small control: expect 182/182 and acquisition-only warnings, without automatic acceptance.

Live network evidence can change these captured expectations; inspect a fresh
packet before making additional decisions.
