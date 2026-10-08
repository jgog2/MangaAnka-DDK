# Generic unresolved intake identity — Black Clover forensic case

Completed October 7, 2026 using the current local worktrees, the supplied export, and read-only public metadata captures. No production database was opened or modified.

## Answer

Black Clover did not fail title search or acquisition/publication resolution. It failed the separate **trusted canonical entity-linking boundary**. The search adapter was discarding MangaDex's explicit AniList/Kitsu/MAL links, so existing enrichment had to compare a serial and a one-shot with the same title, creator and nearby publication years. Both services can supply multiple plausible candidates; the resolver correctly refuses to invent an identity when no unique anchor survives.

The generic defect is lost evidence at the MangaDex adapter boundary. The repair retains supported explicit numeric IDs and reuses the existing direct-ID reconciliation policy. No new title, popularity, chapter-count, fuzzy-match, edition, acceptance or fallback policy was introduced.

## What the supplied packet establishes

The Black Clover entry is an unresolved intake observation, **not a persisted audit**:

- Working-set item: `e47a99e5-8b1a-43ec-9d5c-9ae18c4c207f`.
- Working set: `1b2fdd82-2bfe-4574-afab-ea4d377e4569`.
- Observation: **12**, captured `2026-10-06T18:46:03.190320+00:00`.
- No linked work, audit ID or pinned revision; item state REVIEW.
- Match: **EXACT_PRIMARY**, five providers; native provider group confidence high.
- Selected acquisition: MangaPill `524`.
- 394 logical/acquisition records, 393 mapped records, one unmapped record, 38 derived volumes.
- Canonical context: empty work ID, confidence `ambiguous`, `shareable=False`.
- Catalog identity: empty canonical ID, `trusted=False`, standard/en.
- MangaDex structural/artwork references: `unavailable_identity`.
- Existing research remains: chapter 393 unmapped; acquisition records 0 and 393 unclassified. Native-volume count zero is not an identity defect.

The source hashes recorded in the observation match the inspected pre-repair `mangadex_source.py`, `enrichment_matching.py`, `canonical_identity.py`, and `reference_integration.py`. Thus the relevant local implementation matches the captured implementation.

The packet's compact provider rows omit native years, external IDs, conflict-candidate IDs and the original enrichment candidates. It proves the ambiguous state and downstream refusal, but cannot prove the precise historical four-candidate payload. The current-payload reproduction below is explicitly distinguished from those missing historical bytes.

Export SHA-256: `fcbd8afd1c0c0be9b0ca78c305595ddc70d013c902ef642371d90be360874b1d`. Only the Black Clover entry was copied to `build/black-clover-identity/export-entries.json`.

## Reproduced conflict and lost evidence

The current public enrichment snapshot contains:

| Service / ID | Work | Format | Start year | Reported chapters / volumes |
|---|---|---|---:|---|
| AniList 86123 | Black Clover serial | MANGA | 2015 | 392 / 38 |
| AniList 114652 | Black Clover pilot | ONE_SHOT | 2014 | 1 / unknown |
| Kitsu 27527 | Black Clover serial | manga | 2015 | 392 / 38 |
| Kitsu 53659 | Black Clover pilot | oneshot | 2014 | 1 / unknown |

AniList supplies Yuuki Tabata for both works. Native MangaDex main-card metadata supplies Tabata Yuuki and year 2015. Existing creator normalization considers these compatible; the one-year difference also falls inside the existing era tolerance. Consequently all four candidates can qualify as HIGH individual matches. This is not enough to prove that the serial and pilot are the same work.

`_resolved_family_candidates()` already rejects one-shot/serial contradictions. Its non-direct path starts from services having exactly one eligible candidate. Here each service has two, so there is no unique initial anchor and the family becomes ambiguous. Existing tests covered one duplicated service plus one unambiguous service; this case exposes duplicates in both.

The [main MangaDex record](https://api.mangadex.org/manga/e7eabe96-aa17-476f-b431-2497d5e9d060) explicitly supplies:

```text
al  = 86123
kt  = 27527
mal = 86337
```

These identify the serial directly. The other MangaDex ID in the packet, `74bada5e-5cf6-4ef5-8cd8-7d1b5fe6eef9`, is the fan-colored card; it is not the pilot. Its explicit edition remains distinct.

Before repair, both `MangaDexSource.search()` and `get_manga()` normalized titles, creators and years but omitted `attributes.links`. The downstream matcher already supports `external_ids.anilist_id`, `kitsu_id` and `mal_id`; it simply never received this evidence.

An instructive control: replaying only the compact exported cards can falsely appear to resolve successfully, because those cards have lost the year that promotes the Kitsu pilot to HIGH. The forensic replay therefore restores native MangaDex metadata by running the actual adapter on captured responses. It does not treat the compact export as complete historical input.

The fresh snapshots were read through existing adapters, with a 15-second timeout only in the investigation wrapper. Production timeouts, enrichment limits and cache policy are unchanged. Captured raw responses and normalized candidates are retained under `build/black-clover-identity`.

## Why publication could resolve while catalog linking could not

`SearchAuditor.audit_one()` runs provider search, external enrichment, relevance/group ranking and inventory qualification. `resolve_publication()` then freezes canonical family context and calls `identity_for()`. Ambiguous confidence/empty canonical ID yields an untrusted catalog identity.

The reference service can nevertheless resolve an exact compatible Wikipedia chapter-list page from provider-local title evidence and construct a local publication projection. A successful chapter layout is not an AniList/Kitsu entity-ID proof. The system intentionally does not promote chapter counts or volume coverage into canonical identity authority.

At persistence, `WorkingSets.persist_item_audit()` calls `resolve_work()` and creates a candidate only for a trusted compatible work/edition/language identity. With `trusted=False`, it returns no target. The runner stores `observe_unresolved()` instead. This preserves useful research without inventing a catalog work or half-created audit. It is expected fail-closed persistence behavior, not a SQLite failure.

## Narrow repair

Only product file changed:

`C:\MangaNana-Dev\MangaNana-calibre\mangadex_source.py`

A small `_linked_external_ids()` helper retains the supported explicit MangaDex link keys as existing matcher fields. Only positive ASCII numeric IDs are accepted. URLs, slugs, zero/negative values, booleans, unsupported services and malformed link containers do not become IDs. Both search and metadata normalization expose the same field.

The existing resolver now sees unique directly anchored serial candidates in both services and confirms their compatibility. Conflicting direct links, multiple directly linked same-title works, native creator contradictions and edition separation remain fail-closed. Raw provider records remain distinct. The identity donor need not be the selected acquisition provider.

No edits to DDK product code, canonical matching/reconciliation rules, ranking, provider choice, publication/reference logic, normalization/artifact authority, acceptance, curation, writer transactions, schema, command grammar, Qt/Tk UI, launchers, build spec or version files. No database migration, global cache purge, catalog merge or automatic relink. Schema remains **7**, grammar **3**. No commit, push, tag or release.

DDK additions:

- `tests/test_intake_identity_links.py`: 14 generic deterministic tests, including a disposable schema-v7 unresolved-observation → trusted audit/link/pin lifecycle.
- This report.
- Baseline copy, current API captures, scoped export, task diff, replay/verification scripts and logs under `build/black-clover-identity`.

## Reproduction result

The replay combines historical compact cards/acquisition IDs with current captured native MangaDex and AniList/Kitsu metadata. It runs actual pre-repair and repaired adapters, existing enrichment, canonical context and publication evaluation. Network is forbidden during replay. Historical peer chapter lists are not invented; only retained inventory summaries are supplied.

| Result | Pre-repair adapter | Repaired adapter |
|---|---|---|
| Canonical ID | empty | `anilist:86123\|kitsu:27527` |
| Trusted catalog identity | false | true |
| Identity health | REVIEW | PASS |
| Mapped / unmapped / volumes | 393 / 1 / 38 | 393 / 1 / 38 |
| Unclassified records | 0 and 393 | 0 and 393 |
| Publication / normalization / acquisition health | REVIEW / REVIEW / PASS | REVIEW / REVIEW / PASS |

Captured references and every acquisition ID/effective volume assignment are identical between the two evaluations. Missing structure and acquisition classifications are not suppressed to make the title pass. A real fresh audit can now request identity-dependent references; the replay deliberately holds those unavailable historical references fixed rather than fabricating a new MangaDex structure response.

In the disposable lifecycle test, the untrusted result creates no work/audit and retains an unresolved observation. The trusted result creates one work and one audit, pins only the exact item, leaves another item untouched, preserves the unresolved observation, and leaves acceptance NONE. No production observation or pin was modified.

## Validation and delivery

- 14/14 new focused identity/link/intake tests pass. Before repair, the positive link-preservation, identity and persistence regressions failed.
- 116/116 focused shared enrichment, adapter, canonical identity, ranking, source policy and registry tests pass.
- 147/147 focused DDK identity/intake, working-set/recovery/lifecycle, provider boundary, artifact, reference integrity, canonical-special and UNCOMPILED controls pass.
- 52/52 offline packaged-module tests pass, followed by the Black Clover replay using frozen DDK modules and the repaired live adapter.
- Changed source and investigation scripts compile. Scoped Git diff check passes; task-local diff isolates this change from pre-existing dirty worktree work.

Full DDK suite: **569/569 PASS**, completed in 350.675 seconds. The full plugin repository suite was not run.

An EXE rebuild is **not required**: DDK product code is unchanged, and the existing executable loads shared plugin modules from the local worktree. Packaged verification confirms the repaired `mangadex_source.py` is loaded from `C:\MangaNana-Dev\MangaNana-calibre`, no shared-core snapshots/database are bundled, and relevant frozen DDK code matches current source.

EXE remains `C:\MangaAnka DDK\dist\MangaAnka-Database-Development-Kit.exe`, SHA-256 `f129016d350319980450e907d904daf69e88c04688c75a97a4fbecc48bc69b07`. No interactive GUI/live-provider audit or fresh DPI smoke is claimed.

## Manual check and remaining limits

1. Restart DDK through `Launch_MangaAnka_DDK.bat` so the repaired shared module is imported.
2. Manually open the intended catalog, activate BATCH 004 and select the existing Black Clover unresolved item.
3. Use **Force Re-Audit** for that exact item. Normal Run Working Set does not automatically retry a stable, unlinked REVIEW observation; Retry Errors targets ERROR items.
4. With the captured direct links and enrichment responses available, expect canonical identity `anilist:86123|kitsu:27527`, a newly linked work/audit and a pin. The old unresolved observation remains historical evidence. Continue reviewing any publication/normalization issues normally; do not expect automatic acceptance or a forced PASS.

If MangaDex/external enrichment is unavailable, direct links are absent or contradictory, or genuinely different same-title works retain multiple anchors, the item can still remain unresolved. This repair preserves decisive evidence; it does not authorize guessing when that evidence is missing. Existing conflicting catalog identities are not merged or silently relinked. Fresh upstream contents can change publication results.
