# BATCH 004 remaining unlinked titles — consolidated investigation

All three titles safely link in captured-input, disposable-database audits after three generic shared-core repairs. **Linking does not mean acceptance:** Dr. STONE and Sakamoto Days remain REVIEW; The Promised Neverland becomes READY with acquisition PARTIAL under the unchanged evaluator. No production database was opened.

## Evidence boundary and exact pipeline

Authoritative input: the named `export.json`, SHA-256 `46e02e9937fb3e911a764030b3dcb4e280ac41b57f614c45b3dbb57a7790508e`, containing ten BATCH 004 entries. Working Set UUID: `1b2fdd82-2bfe-4574-afab-ea4d377e4569`. Only the three target entries were copied into `build/batch004-unlinked/packet.json`.

`baseline.json` in that directory preserves each exact item, request key, observation, problem and affected identifier, all retained aliases/creators/provider cards, inventories and rejected/unusable resolution summaries. The exported observations do **not** serialize individual external enrichment candidates, native years/links, or individual identity-match rejection reasons. Stored problem_class/next_action are also absent from these unresolved-observation holes; `baseline.json` labels current-policy classifications separately instead of presenting them as historical stored fields. Workflow REVIEW / Research required is the supplied user observation.

The observations were created October 6 before the Black Clover link-retention repair. Fresh public metadata, provider inventories and reference outputs were captured October 7. These captures reproduce the resolver boundaries; they are not represented as byte-exact historical network responses. Public requests never downloaded manga page images.

Actual code path inspected and exercised:

1. `SearchAuditor.audit_one()` obtains provider cards and AniList/Kitsu candidates.
2. `enrich_content_results()` matches candidates, gathers primary-title work families, and invokes `_resolved_family_candidates()`.
3. `effective_search_rows()` applies overlays, existing `group_canonical_results()`, canonical work facts and existing trusted-family propagation.
4. `rank_canonical_results()` and `resolve_search_group()` qualify native provider inventories and select acquisition using the existing policy.
5. `resolve_publication()` freezes `canonical_family_publication_context()`, creates `identity_for()`, looks up references and applies provider → MangaDex → Wikipedia structure through the existing manifest/projection machinery. Existing normalization, duplicate handling, publication states, freshness and artifact authority run normally.
6. `WorkingSets.persist_item_audit()` only creates/links a work when identity is trusted and edition/language match. It atomically saves the new audit/problems and advances that item's pin. Otherwise `observe_unresolved()` preserves the research without a half-created audit.
7. The existing acceptance evaluator determines READY versus REVIEW; the replay never calls accept.

The offline audits replace external I/O with captures, not ranking, qualification, publication logic or persistence. Real source reference parsing and real metadata enrichment run. Inventories outside the captured target families are explicitly unavailable in the replay rather than invented; no claim is made to replay every unrelated search hit's network inventory. Known primary target inventories are captured completely. SQLite connection guards restrict every connection to the temporary test directory. Separate fresh temporary databases are used for source and packaged checks.

# Dr. STONE

## Exact baseline

| Field | Exported value |
|---|---|
| Item UUID | `1f15d2f0-2756-46c5-aba1-84c0d08327a0` |
| Request key | `dr. stone` + U+001F + `standard` + U+001F + `en` + U+001F + `volume` |
| Requested edition / language / workflow | standard / en / volume |
| Processing / linked work / pin | REVIEW / null / null |
| Unresolved observation | 14, `2026-10-06T18:47:50.516852+00:00` |
| Search match | Dr. STONE Reboot: Byakuya group; EXACT_PRIMARY; high group confidence |
| Selected acquisition | MangaPill `1059`, `https://mangapill.com/manga/1059/dr-stone` |
| Providers / raw selected records | 4 / 237 |
| Logical / canonical main / mapped / unmapped / uncompiled / volumes | 232 / 230 / 230 / 2 / 0 / 26 |
| Catalog/context claim | `anilist:112673|kitsu:55534`, ambiguous, untrusted, unshareable |
| Reported totals | 9 chapters / 1 volume — the spin-off's totals, not proof of serial identity |
| Enrichment errors | empty |

Problems: REFERENCE_CONFLICT (`206`); UNMAPPED_CHAPTERS (`202`); PROVIDER_FRACTIONAL_CANDIDATE (`232.5`, `232.8`); UNCLASSIFIED_ACQUISITION (`202`, `206`). The two top-level unmapped records include the separately reported conflict. Current policy assigns CODE_REVIEW_REQUIRED to fractional candidates and RESEARCH_REQUIRED to the remaining root findings.

## Root cause and evidence

Fresh MangaDex serial `cfc3d743-bd89-48e2-991f-63e680cc4edf` explicitly co-links AniList `98416`, Kitsu `38860`, MAL `103897`. AniList reports 236/27, Kitsu 232/26. Both share normalized core title `dr stone`, year 2017 and compatible manga format. Kitsu supplies no creator names. Existing `_cross_service_agrees()` therefore returns false: one shared normalized title, missing creator intersection, and unequal totals. Even after link retention, `_resolved_family_candidates()` rejected the two direct anchors because it did not use their co-occurrence on one native card as cross-service evidence.

Without trusted serial IDs, ordinary alias grouping allowed the Byakuya card's broad `Dr. Stone` alias to contaminate display/work facts. The ambiguous confidence still correctly blocked persistence. After the anchors resolve, **existing** canonical grouping rejects different trusted IDs, so the serial, Byakuya and 4D Science stay separate without a grouping-policy change.

The second repair also matters: the MangaDex card credits only Inagaki while canonical creators include Inagaki and Boichi. A provider's known creator subset is an omission, not evidence that the other canonical creator is wrong. Previously the publication context could exclude that card and lose the precise MangaDex structural identity hint.

Authoritative publisher credits: story by Riichiro Inagaki, art by Boichi ([VIZ](https://www.viz.com/dr-stone)). Captured distinct related identities: Byakuya AniList `112673` / Kitsu `55534`; 4D Science AniList `170755` / Kitsu `70240` / MangaDex `869ad120-7341-4ea9-a980-f3545bc0503c`; Terraforming one-shot AniList `152129` / Kitsu `64798`. Novel candidates remain separate. None is merged into the serial entity because it shares creators or franchise aliases.

## Post-repair disposable audit and remaining blockers

Canonical identity: `anilist:98416|kitsu:38860`, standard/en, trusted. The unchanged selector now sees the actual Atsu serial `raSQb`, with 236 records, rather than the nine-record Byakuya card as its Atsu peer. Atsu wins the existing main-coverage ranking; provider-selection code is unchanged. MangaPill's 237 raw records include duplicates/fractions and do not prove greater main coverage.

Result: 236 raw, 232 logical/main, 231 mapped, 1 unmapped, 0 uncompiled, 26 final volumes. Health: **identity PASS / publication REVIEW / normalization REVIEW / acquisition PARTIAL**. Membership REVIEW, acceptance ineligible.

Remaining findings: REFERENCE_CONFLICT (`206`), MISSING_REFERENCE_STRUCTURE (known released volume structure incomplete), four fractional CODE candidates (`232.5`, `232.6`, `232.7`, `232.8`), and acquisition-only CHAPTER_COUNT_DISAGREEMENT for absent explicitly referenced `4.5`, `18.5`. The current MangaDex aggregate maps 207 chapters / 23 volumes; Wikipedia supplies additional structure. Released volume 27 is known without sufficient chapter membership. No guessed mappings or UNCOMPILED classification were added.

# Sakamoto Days

## Exact baseline

| Field | Exported value |
|---|---|
| Item UUID | `d794db04-e5f4-40a5-a98f-5d11c07fd635` |
| Request key | `sakamoto days` + U+001F + `standard` + U+001F + `en` + U+001F + `volume` |
| Requested edition / language / workflow | standard / en / volume |
| Processing / linked work / pin | REVIEW / null / null |
| Unresolved observation | 13, `2026-10-06T18:47:01.706641+00:00` |
| Search match | Sakamoto Days; EXACT_PRIMARY; high group confidence |
| Providers / selected acquisition | 5 / MangaK `MDo5eX8v`, `https://mangak.io/sakamoto-days` |
| Raw / logical / canonical main / mapped / unmapped / uncompiled / volumes | 412 / 237 / 237 / 0 / 237 / 0 / 0 |
| Identity | empty canonical ID, ambiguous, untrusted, unshareable |
| Reported chapter/volume totals / enrichment errors | empty / empty / empty |

Problems: UNMAPPED_CHAPTERS (237); PROVIDER_FRACTIONAL_CANDIDATE (101); PROVIDER_SPLIT_CANDIDATE (30); UNCLASSIFIED_ACQUISITION (43). Exact identifiers are retained in baseline.json. Current policy: RESEARCH_REQUIRED, CODE_REVIEW_REQUIRED, CODE_REVIEW_REQUIRED, RESEARCH_REQUIRED respectively.

## Root cause and evidence

MangaDex serial `9d9b04ad-9a83-49f4-8ae4-a9a3780fe9c0` explicitly co-links AniList `125828`, Kitsu `58159`, MAL `131334`. Both catalogs identify the 2020 serial. AniList has Yuuto Suzuki but no completed chapter/volume totals; Kitsu has no creator and reports 29 volumes with no chapter total. Only one normalized core title is shared. The same direct-anchor corroboration defect as Dr. STONE rejects an otherwise explicit joint link. Missing metadata was incorrectly treated as insufficient even in the presence of this decisive bridge.

The full qualification path exposed a **second independent Sakamoto blocker**: `MangaKSource.get_manga()` flattened an explicit pending-credit entity into the creator display. Captured raw author entities are Suzuki Yuuto (`id/slug=suzuki-yuuto`) and Updating (`id/slug=updating`, URL `/authors/updating`). Result: `Suzuki Yuuto, Updating`. The latter is provider placeholder metadata, not a contrary creator. Search cards have blank MangaK author, so this only appears when qualification loads title metadata. The adapter now excludes exactly this verified entity shape. Similar creator names and unconfirmed `Updating` strings remain untouched.

[VIZ](https://www.viz.com/sakamoto-days) credits Yuto Suzuki. The existing name comparison recognizes the captured Yuuto spelling consistently; no new transliteration/fuzzy-name rule was added. Current metadata search did not return a separate same-title pilot candidate; that absence is not a claim that no pilot exists. Synthetic serial/pilot ambiguity controls remain mandatory. Novels Assassin's Blues (AniList `185734`) and Assassin's Method (`162695`, Kitsu `67204`) remain separate. The official colored MangaDex card `c3a410f3-6c1c-454c-93eb-8b995fd4cf56`, year 2024, has no explicit catalog links and stays a separate acquisition edition. Sakamoto Holidays and unrelated Sakamoto titles are not treated as serial aliases.

## Post-repair disposable audit and remaining blockers

Canonical identity: `anilist:125828|kitsu:58159`, trusted standard/en. Selected MangaK remains unchanged; raw 412, logical/main 254, mapped 32, unmapped 222, uncompiled 0, final volumes 6. Health: **identity PASS / publication REVIEW / normalization REVIEW / acquisition PASS**. Membership REVIEW, acceptance ineligible.

Current MangaDex structure is valid but sparse: 32 explicit mappings across 6 volumes. Wikipedia resolves the exact chapter-list identity but its chapter membership extraction returns `supported_empty`. Bibliography knows 28 released volumes and a future 29th at the replay as-of date; those totals are not membership proof. The sparse map cannot certify a safe uncompiled tail.

The 101 fractional and 30 split CODE candidates remain **exactly as before**. Unclassified records reduce from 43 to 26 because newly reachable explicit reference evidence establishes some integer chapter identities. No provider-artifact classification policy was changed. Remaining action: structural-page/extraction research and existing CODE review, including the previously characterized provider-selection evidence boundary. It is not appropriate to select a cleaner provider merely to hide these findings.

# The Promised Neverland

## Exact baseline

| Field | Exported value |
|---|---|
| Item UUID | `aecd00ae-e1b1-45bb-8134-760bb9e1d28e` |
| Request key | `the promised neverland` + U+001F + `standard` + U+001F + `en` + U+001F + `volume` |
| Requested edition / language / workflow | standard / en / volume |
| Processing / linked work / pin | REVIEW / null / null |
| Unresolved observation | 15, `2026-10-06T18:48:08.852183+00:00` |
| Search match | The Promised Neverland; EXACT_PRIMARY; high group confidence |
| Providers / selected acquisition | 4 / Atsu `tTK7p`, `https://atsu.moe/manga/tTK7p` |
| Raw selected / logical / canonical main / mapped / unmapped / uncompiled / volumes | 182 / 181 / 180 / 180 / 1 / 0 / 20 |
| Provider canonical identity | `anilist:87423|kitsu:38047`, high confidence |
| Publication context | same ID, but ambiguous confidence / unknown edition profile / unshareable |
| Native selected creator | `Kaiu Shirai, Posuka Demizu, DEMIZU Posuka, SHIRAI Kaiu` |
| Reported totals / enrichment errors | 181 chapters, 20 volumes / empty |

Problems: UNMAPPED_CHAPTERS (`7`); PROVIDER_FRACTIONAL_CANDIDATE (`181.5`); UNCLASSIFIED_ACQUISITION (`7`). Current policy assigns RESEARCH_REQUIRED / CODE_REVIEW_REQUIRED / RESEARCH_REQUIRED. MangaDex references were `unavailable_identity`; Wikipedia already supplied local structure.

## Root cause and evidence

This was **not search ambiguity or an edition mismatch**. Enrichment correctly recognized Kaiu Shirai and Posuka Demizu and attached the correct canonical IDs. The publication-context check passed the native comma-separated creator display as one creator into `creator_relationship()`, which compared it with individual canonical creators. It rejected an equivalent duplicated/reordered list. Its early return constructed an ambiguous context without the known edition, causing the misleading outward reason `ambiguous edition`.

The repair compares explicitly delimited native components against already trusted creator identities, deduplicating equivalence by comparison rather than inventing aliases. Known subsets are allowed; unknown extra components, unrelated creators and actual trusted creator conflicts remain rejected. The general MADB creator policy and edition classifier are unchanged.

Current MangaDex `46e9cae5-4407-4576-9b9e-4c517ae9298e` links AniList `87423`, Kitsu `38047`, MAL `100128`. [VIZ](https://www.viz.com/the-promised-neverland) independently credits story by Kaiu Shirai and art by Posuka Demizu. Distinct special one-shots, novels and Beyond The Promised Neverland (AniList `138817`, MAL `140090`) retain separate catalog entities; [the publisher's separate collection listing](https://www.viz.com/manga-books/manga/kaiu-shirai-x-posuka-demizu-beyond-the-promised-neverland/product/7267/digital) corroborates that distinction.

## Post-repair disposable audit and remaining blockers

Canonical identity unchanged, now trusted/shareable standard/en. Selected Atsu unchanged. Current primary inventory has 182 records; the existing Atsu group resolver also evaluates seven captured alternate records, producing a 189-record raw pool. Effective logical/main count is 182, mapped 182, unmapped 0, uncompiled 0, volumes 20. Raw pool size is not unique publication count.

Health: **identity PASS / publication PASS / normalization PASS / acquisition PARTIAL**. Membership READY and acceptance eligible under the existing evaluator, with **no acceptance performed**. Current MangaDex evidence resolves chapter 7 and explicitly establishes membership for 181.5; it is no longer an unsupported provider-only fractional claim. The software did not suppress that CODE finding: the existing authority rules received new independent reference evidence after identity became reachable.

Remaining acquisition-only CHAPTER_COUNT_DISAGREEMENT: nine explicit reference keys absent from selected acquisition (`3.5`, `4.5`, `21.5`, `38.5`, `181.6`, `182`, `183`, `184`, `185`). The existing evaluator warns about acquisition PARTIAL separately from complete mapped publication. MADB returns ambiguous; Google Books has no API key. Neither is used to invent structure or grant acceptance.

# Shared root causes

1. **Joint explicit catalog links were retained but not used as a bridge.** Affects Dr. STONE and Sakamoto Days. The repair only recognizes two compatible external candidates explicitly co-linked on the same native card, with exact shared core-title evidence and no creator/format/era/count-ratio or explicit cross-ID contradiction. It does not change ordinary cross-service title matching or infer a bridge from separate providers.
2. **Creator display strings were mistaken for creator entities.** Direct blocker for The Promised Neverland; also excluded incomplete native creator credits and precise MangaDex hints for multi-creator works such as Dr. STONE. Only already-known component identities are recognized.
3. **MangaK pending-credit entity became a real creator.** Additional full-pipeline blocker for Sakamoto Days. Normalized at its source, leaving genuine creator contradictions active.

The Black Clover repair is preserved unchanged. No title-specific IDs, runtime title tables, first-hit selection, count-as-identity proof or curation bypass was introduced.

# Product changes

Shared product files changed in this pass:

- `C:\MangaNana-Dev\MangaNana-calibre\enrichment_matching.py`: `_anchored_candidates_agree()` adds same-card co-link corroboration to direct-anchor reconciliation, with contradiction gates. Ordinary `_cross_service_agrees()` remains unchanged.
- `C:\MangaNana-Dev\MangaNana-calibre\reference_integration.py`: `_native_creator_relationship()` recognizes all native comma/slash components only when each already matches a trusted creator; otherwise delegates to the existing relationship policy.
- `C:\MangaNana-Dev\MangaNana-calibre\mangak_source.py`: `_author_names()` excludes the exact `Updating` pending-credit entity only when its explicit ID/slug is also `updating`.

DDK additions: `tests/test_intake_identity_witnesses.py` (21 deterministic synthetic tests), this report, and scoped forensic captures/replays/logs under `build/batch004-unlinked`. `task.diff` compares against task-start copies, isolating these edits from pre-existing worktree changes. No DDK embedded product modules changed.

No rebuild required: the existing EXE dynamically imports these three shared modules from the intended local plugin worktree. Packaged checks verify frozen DDK modules match source, no shared-core snapshots or databases are bundled, and repaired modules resolve to the actual plugin path. Restart DDK to reload them. EXE: `C:\MangaAnka DDK\dist\MangaAnka-Database-Development-Kit.exe`, SHA-256 `f129016d350319980450e907d904daf69e88c04688c75a97a4fbecc48bc69b07` (unchanged). Primary and legacy Tk launchers are untouched.

# Before / After

Results below are **captured-input disposable results**, not a production mutation or a promise that fresh upstream counts cannot change.

| Title | Before | After | Linked? | Publication result | Remaining action |
|---|---|---|---|---|---|
| Dr. STONE | Observation 14, ambiguous; spin-off facts on serial cards | Correct serial ID; REVIEW | Yes | 232 logical, 231 mapped, 1 unmapped, 0 uncompiled, 26 volumes | Research 206/volume-27 structure; review four fractional CODE candidates; acquisition warning |
| Sakamoto Days | Observation 13, ambiguous; 237 unmapped | Correct serial ID; REVIEW | Yes | 254 logical, 32 mapped, 222 unmapped, 0 uncompiled, 6 volumes | Sparse reference extraction research; 101 fractional + 30 split CODE findings remain |
| The Promised Neverland | Observation 15, correct ID but rejected creator context | Trusted context; READY, acquisition PARTIAL | Yes | 182 logical, 182 mapped, 0 unmapped, 0 uncompiled, 20 volumes | Inspect acquisition-only nine-key warning; manually evaluate acceptance |

# Validation

- **21/21 new synthetic tests pass.** Replaying the task-start code produces five identity/creator failures in the original 18-test subset; the subsequent MangaK placeholder regressions produce two additional failures before that repair. Controls cover missing/malformed IDs, shared-card versus separate-card evidence, conflicting IDs, same-title distinct works, serial/pilot, creator contradictions, incomplete/duplicate/reordered credits, aliases, spin-off grouping, colored editions and legitimate names resembling placeholders.
- **214/214 focused shared-core tests pass** (enrichment/matching, canonical identity/grouping, ranking, adapters/metadata, source policy/registry, MangaDex characterization/structure, MADB, reference integration and MangaK).
- **204/204 focused DDK tests pass**, including new identity tests, Black Clover links, working-set persistence/recovery, schema-v7 lifecycle/acceptance, provider-selection boundary, Haikyu residue, MHA parser forensics, reference/artifact integrity, canonical specials, scoped UNCOMPILED, Wikipedia identity/membership and World Is Mine.
- **590/590 full DDK tests pass**, completed in 339.241 seconds, including all three product repairs and 21 new tests. The full plugin repository suite was not run.
- **73/73 packaged-module tests pass**, plus the Black Clover identity/publication replay and all three complete disposable audits through frozen DDK modules with repaired live shared code.
- Compilation of changed product source, test and investigation scripts passes; scoped Git diff check passes (Git emits the existing LF/CRLF warning).
- Source and packaged disposable audits each create exactly three linked works/audits, pin their exact items, preserve earlier unresolved observations, leave an unrelated sentinel unchanged, remain schema 7 and create no acceptance rows. All connections are guarded to disposable paths; unexpected network access is forbidden during replay.

Logs, full problem identifiers, reference captures and publication projections are under `C:\MangaAnka DDK\build\batch004-unlinked`. `offline-audit-results.json` records actual eligibility results and blockers, not a hand-written eligibility guess. Reference acquisition provenance was refreshed for Dr. STONE after its correct serial became the selected provider. The replay uses the captured observation as-of date `2026-10-06` with freshly captured public inputs; fresh manual audit dates may differ.

# Safety and limits

- Protected production DB never opened or mutated. Existing observations, failed intakes, audits, pins and acceptance records were not edited.
- DDK 0.3.0, schema 7 and Grammar 3 unchanged. No schema migration.
- Acceptance, curation, writer locking/transactions, health derivation, normalization/artifact authority, publication precedence, freshness, released-volume logic, UNCOMPILED and provider-selection policy unchanged.
- Black Clover remains resolved in its captured replay; edition/pilot safeguards pass. Blue Lock scoped ambiguity/cross-work controls pass; Haikyu provider residue and MHA chapter 118/fractional controls pass; SPY x FAMILY Wikipedia/supplementary authority, Dandadan canonical specials and World Is Mine clean control pass. No unrelated live records were re-audited.
- No runtime title constants or automatic acceptance. No commit/push/tag/release/reset/clean/version bump. Existing uncommitted work preserved.
- No Qt/DDK UI code changed, so no new GUI/DPI smoke or EXE build was necessary or claimed. Packaged-module verification is not an interactive GUI smoke.
- Missing/contradictory co-links, multiple same-service anchors, genuinely different same-title works, incompatible editions or unknown native creator components still fail closed. Existing catalog identities are not merged or relinked automatically.
- The current Sakamoto Wikipedia `supported_empty` result, Dr. STONE structure conflict/volume gap, provider reference parsing failures, and general provider-selection limitation remain visible. This pass does not silently fix or suppress downstream findings unrelated to identity.

# Manual retest

1. Close/restart DDK through `C:\MangaAnka DDK\Launch_MangaAnka_DDK.bat` to load the shared source fixes.
2. Manually open the intended production catalog and activate BATCH 004. No re-import/new intake is needed.
3. Force Re-Audit **each existing item**: Dr. STONE (`1f15d2f0-2756-46c5-aba1-84c0d08327a0`), Sakamoto Days (`d794db04-e5f4-40a5-a98f-5d11c07fd635`), The Promised Neverland (`aecd00ae-e1b1-45bb-8134-760bb9e1d28e`). Run Working Set skips stable unlinked REVIEW observations; Retry Errors is not the correct action here.
4. Confirm each acquires the canonical ID shown above and a new immutable linked audit/pin. Retain the old observations in history. If upstream evidence is now absent or contradictory, retain REVIEW and export the new packet rather than forcing a link.
5. Inspect downstream problems. Expect Dr. STONE/Sakamoto Days to need review. The Promised Neverland may be READY with acquisition PARTIAL; inspect its fresh acceptance preview and decide manually. Do not auto-accept based solely on this report.
6. Leave Golden Kamuy, Kaiju No. 8, Vinland Saga, Blue Lock, Black Clover, Haikyu!! and My Hero Academia untouched unless separately requested. Export a fresh BATCH 004 packet after these three re-audits.
