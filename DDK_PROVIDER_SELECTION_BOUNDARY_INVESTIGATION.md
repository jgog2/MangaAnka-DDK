# Provider-selection evidence boundary

Date: 2026-10-06. DDK 0.3.0; schema 7; command Grammar 3 unchanged.

## Decision: outcome D, with the current behavior preserved

The current pre-publication selector cannot distinguish a provider-only integer identifier from an independently established canonical chapter with the same identifier. This is a general unverified-integer coverage limitation, not a zero-specific defect. No existing quality signal at this boundary safely supplies the missing chapter identity.

No runtime selection rule was changed. Therefore the reported Haikyu!! acquisition still selects MangaK with the same inventories. This does **not** certify that its extra chapter zero is legitimate. It documents the limitation rather than replacing it with an unproven exclusion, consensus, or deduplication policy. The requested stronger selection guarantee is not achieved by this investigation alone.

Twenty-two deterministic tests now document the evidence boundary, including thirteen generic fixture cases, preservation controls, and counterexamples to tempting shortcuts. These are **characterization tests**, not an endorsement of the unresolved coverage bonus or a new desired ranking policy.

## 1. Exact ranking path

DDK entry point: `C:\MangaAnka DDK\mangaanka_database_development_kit.py`, `SearchAuditor.audit_one()`.

1. Current provider search, enrichment, and `rank_canonical_results()` produce relevant canonical groups.
2. `canonical_identity.group_canonical_results()` joins compatible work/media identities, rejects different editions, and keeps separate results from the same provider in separate groups. Thus the alternate MangaK `/haikyuu` result is not automatically substituted into the `/haikyu` provider slot.
3. For each candidate group, shared `search_resolution.resolve_search_group()` selects a reported language and calls `inspect_source_inventory()`, using the existing metadata/inventory caches and bounded inspection budget.
4. `inventory_comparison.compare_inventories()` filters the expected edition and usability, preserves the native-volume preference in volume mode, prefers complete inventories, then compares `publication_specials.inventory_coverage()`.
5. A clear main-coverage advantage requires at least five units and a 1.25 ratio. Materially comparable providers remain ambiguous. For 403 versus 402, comparison returns ambiguity with no selected winner.
6. `resolve_search_group()` nevertheless chooses an acquisition primary through `decision.selected or _choose_primary(inventories, workflow)`.
7. `_choose_primary()` orders by native-volume availability in volume mode, completeness, descending main score, descending recognized-special score, descending native-volume count, then `source_id`.
8. Only after selection does DDK `ddk_publication.resolve_publication()` construct the selected acquisition/context, invoke `ReferenceMetadataService.lookup()`, build the publication manifest/projection, and call `normalize_acquisition()`.

The real plugin uses the same shared resolver in `main.py`'s `SearchResolutionWorker`. Its reference lookup is dispatched later for the selected provider/load generation. This is not a DDK-only ranking algorithm. DDK imports the live local shared modules through `mangaanka_search_core/__init__.py`; no fallback snapshot was edited.

Canonical **work/edition** identity may be known before selection. Exact canonical **chapter** identities and their current reference evidence are not supplied to the selector.

## 2–3. Exact metric and chapter-zero contribution

`publication_specials.inventory_coverage()` adds a numeric record to its `main` score when the normalized number is integral, it is not explicitly typed as a special, and no supplied recognized-special identity matches it. It counts unique keys, with explicit native-volume numbering accounting for restarted chapter numbers. There is no canonical-chapter proof requirement in this branch.

Consequently `0`, `21`, and `999` are all eligible integer identifiers. Zero is not treated specially in this ranking function. Its category here is a **generic acquisition main-unit estimate**, not verified canonical main coverage, a special, or pre-chapter-one structure. The field name `main` and the docstring's word “confirmed” must not be read as a reference-backed guarantee.

Captured Haikyu-style scores:

| Inventory | Raw | Main score | Recognized specials | Unresolved |
|---|---:|---:|---:|---:|
| Selected MangaK `/haikyu` | 511 | 403 | 0 | 108 |
| Each captured competing source | 408 | 402 | 0 | 6 |

MangaK has the integers 0–402. The other inventories' recorded main score is 402. The one-key difference is sufficient in `_choose_primary()`, even though it is insufficient for a clear comparison winner. Unknown fractions do not buy this advantage.

Later, raw projection can assign zero to volume one through `derived_pre_chapter_one`. DDK normalization still leaves the captured zero unclassified because it lacks independent identity confirmation. A derived volume is not canonical identity authority. This later result does not feed back into search selection.

The prior Haikyu fixture contains captured identifiers/counts but synthetic peer rows for the six corroborated fractional keys; the investigation does not misrepresent them as recovered full peer captures. Its primary-selection characterization and all 102 exact residual identifiers still pass unchanged.

## 4–5. What else can affect this score

| Record/evidence | Current ranking treatment |
|---|---|
| Provider-only integer, including zero, negative integers, or an unrelated positive integer | Can count as main before later normalization rejects it. |
| Unknown fractional identifier or split-looking decimal pair | Unresolved; no main bonus. No pair-merging rule exists here. |
| Range bundle such as `1-3` | Unresolved; no main bonus. |
| Repeated exact numeric key in the same volume namespace | Unique-unit counting avoids an extra main bonus. This is not page-content deduplication. |
| Duplicate-looking content under a different integer identifier | Can count as main; page resemblance is not an input and cannot justify invented deduplication. |
| Explicit provider special type without independent recognized-special evidence | Excluded from main; currently unresolved in this coverage metric. |
| Supplied exact recognized-special identity | Separate `specials` score, after main coverage; not main inflation. |
| Count-only legacy inventory without chapter records | Falls back to `chapter_count`; no per-record identity distinction is possible. |
| Explicitly different work/edition in title metadata | Canonical grouping separates it; comparison additionally filters expected edition. |
| Hidden noncanonical/colored contents behind compatible metadata | Not detectable by this metadata-only selector. |

`_choose_primary()` itself assumes its callers supply a compatible canonical group; its eligibility helper checks usability, not a new expected-edition argument. This investigation preserves that call contract and verifies edition separation at grouping and comparison. It does not claim arbitrary mixed-edition inputs are safe at every private helper.

The limitation affects any title with unmatched integer identifiers, not only Haikyu!! or MangaK. Synthetic `999` reproduces the same advantage and later unclassified result. This proves generic applicability, not additional live-title failures; no production corpus was rerun.

## 6. Circular dependency and candidate rules

There is no cycle in the current execution graph: acquisition selection precedes publication resolution.

Making the existing selector call the **full** `resolve_publication()` to decide its own primary would introduce a cycle: that function consumes `resolution.primary`, its metadata, acquisition rows, manifest provider precedence, and projection. A DDK-only rerank afterward would also stop auditing the same selection as the real plugin and could change the provider's higher-priority explicit structure.

This is not an inherent impossibility for a future architecture. `ReferenceMetadataService.lookup()` accepts optional acquisition data, and independent work-scoped reference identity can in principle be resolved separately. A deliberate shared preselection identity phase could avoid a cycle. It would need to define current/scoped main and special evidence, incomplete or unavailable reference behavior, stale/conflicting evidence, native-volume namespaces, and reuse without divergent selection in DDK and Calibre. It is **not** an identity signal already available to the present selector, or a one-line count adjustment.

Existing signals were examined:

- Usable/complete inventory flags establish adapter acquisition availability, not chapter canonicality.
- Native membership is an existing higher-priority provider structure signal; it does not establish independent canonical identity for every standalone row.
- Work IDs, aliases, reported totals, acquisition fitness, and edition tags establish different facts from exact chapter identity.
- `special_records` is an existing optional coverage/comparison hook. `resolve_search_group()` currently calls both comparison and primary selection without reference specials; there is no corresponding live main-identity input at this boundary.
- Peer identities are available, but agreement cannot establish that an unmatched legitimate chapter is invalid; providers may share omissions or metadata errors. Turning peer absence into a canonical exclusion would introduce a new authority policy.

Rejected shortcuts:

| Shortcut | Counterexample / consequence |
|---|---|
| Ignore every chapter zero | Loses a genuine independently canonical chapter zero. |
| Require peer agreement for any extra integer | Removes credit from a genuine chapter available only on one provider. |
| Ignore all small count differences after ambiguous comparison | Also discards a small independently verified completeness advantage; it does not identify the misleading record. |
| Penalize a provider by artifact count or choose a different source to remove CODE | Evades the diagnosis rather than resolving chapter identities; useful extras and genuine coverage may coexist with unresolved records. |
| Deduplicate by decimal syntax, page count, or opening resemblance | Unsupported content identity inference; would violate artifact authority. |

No safe automatic rule using only the current inputs satisfies both “unverified zero must not decide” and “verified zero/unique legitimate extra must retain credit.” The tests demonstrate identical ranking inputs with different post-selection canonical outcomes. This is the reason for outcome D, not a global declaration that chapter zero is invalid.

## 7–9. Changes and before/after synthetic results

Added exactly three durable DDK files:

- `tests/test_provider_selection_boundary.py`
- `tests/fixtures/provider_selection_boundary.json`
- `DDK_PROVIDER_SELECTION_BOUNDARY_INVESTIGATION.md`

No existing DDK or shared-plugin runtime source changed. Build-only diagnostics are in `build/provider-selection-investigation/`: source/EXE hashes before and after, `ranking-matrix.json`, and new/DDK/shared test logs.

Generic fixtures use A=`zeta`, B=`alpha`, equal base coverage 1–20. Existing tie-breaking favors B. Each fixture is also repeated under two unrelated synthetic titles. Reference facts in the fixture are explicitly applied only after selection; they are not smuggled into the selector.

| Synthetic case | Before | After this investigation |
|---|---|---|
| A alone has unverified zero | A, main score 21 versus 20 | Same; documented limitation |
| Zero independently canonical | A; ranking input identical to preceding case | Same; later identity is main rather than unclassified |
| A has only unresolved decimals | B | Same |
| A has verified additional main 21 | A | Same |
| A has explicitly typed special-only extra | B without supplied trusted-special evidence | Same; optional trusted-special hook separately credits A's special |
| Duplicate-looking extra under new integer 21 | A | Same; no invented content deduplication |
| Repeated exact numeric key 20 | B | Same |
| Range bundle | B | Same |
| A edition-incompatible | B in compatible group/comparison | Same |
| Equal coverage | B, independently of input order | Same |
| A partial, B complete | B | Same |
| A genuinely much more complete, 40 versus 20 | A | Same |
| A alone has unverified positive integer 999 | A | Same; same general evidence gap |

Expected Haikyu outcome with the supplied inventories remains **MangaK**. The architecture result is D; it is not conclusion A that MangaK's zero has a legitimate coverage basis. No new audit, pin, acceptance, or history was created.

## 10. Validation

- **22 new deterministic tests pass**: thirteen fixture cases and nine boundary/preservation tests, including the actual shared resolver with fake adapters, no-network guard, exact distinction between preselection and post-selection identities, special hook, native structure, edition grouping, deterministic ties, and the peer/tie-break counterexamples.
- **146 DDK focused tests pass**: new boundary tests 22; Haikyu residue 6; artifact authority 23; canonical specials 10; publication states 23; publication audit 24; reference integrity 5; v7 lifecycle 33.
- **220 shared-core focused tests pass**: inventory comparison 14; search resolution 17; canonical grouping 18; search ranking 19; search barrier 4; publication specials 10; publication identity 17; publication manifest 27; cross-source fallback 21; Wikipedia identity 21; Wikipedia membership 21; reference integrity 31.
- **366 total passing tests**. Includes SPY x FAMILY captured membership/short-mission parsing; captured Dandadan canonical specials; World Is Mine 163 chapters/14 derived volumes; clean acceptance, curation/history lifecycle; and provider precedence/projection controls.
- New test Python compile check passes; fixture and ranking-matrix JSON parse successfully.
- Fourteen inspected runtime/core/EXE file hashes are unchanged across the work. Existing shared-worktree Git diff was inspected and left intact.
- No full plugin suite, full DDK suite, GUI, Calibre, DPI smoke, or packaged audit was run. No runtime/UI change required those checks. These are offline controls, not new live provider audits.

## 11–13. Preservation and packaging

The prior six Haikyu regression tests remain unchanged and pass: all **86 fractional + 16 split candidates**, their exact identifiers, and CODE/CODE_REVIEW_REQUIRED policy remain intact. No provider-shadow policy, special promotion, renumbering, suppression, edition relabeling, or title-specific runtime condition was added.

The protected production `mangaanka_catalog.db` was not opened or mutated. Existing test modules use disposable databases. No acceptance or history data was altered. No source provider requests or new page downloads were required for this pass.

No EXE rebuild is required: runtime sources and `dist\MangaAnka-Database-Development-Kit.exe` are unchanged. The primary and legacy launchers are unchanged. No schema, Grammar, version, reference freshness, or release changes were made. Nothing was committed, pushed, tagged, or released.
