# Publication-reference integrity repair — validation report

Date: 2026-10-05. DDK remains v0.3.0, schema 7, Grammar 3.

The repair is implemented in the current local worktrees. The primary Qt EXE has been rebuilt. All validation used offline evidence and disposable databases. The production catalog was never opened or mutated.

## Root cause and scope

The existing MangaDex aggregate parser already excluded a chapter with multiple explicit volume assignments inside one aggregate. It did not preserve detailed rejection evidence or validate conflicting reuse of a stable release identifier. A malformed aggregate was handled like a transport failure, which could restore an older mapping through the last-known-good cache path.

The manifest then applied source precedence without separately reconciling independently eligible explicit MangaDex and Wikipedia claims. A valid MangaDex chapter-to-volume mapping could win even when validated Wikipedia explicitly assigned the same chapter to another volume. That contradiction was not represented as an unresolved publication conflict. Projection could also derive fractional membership from the disputed parent. Existing DDK health and acceptance could only react to conflicts actually represented upstream.

Before implementation, disposable in-memory evidence confirmed that MangaDex chapter 10 -> volume 1 plus Wikipedia chapter 10 -> volume 2 retained the MangaDex membership without ambiguity. Internal MangaDex disagreement was already recognized. New regressions failed against the original implementation before the repair.

The correction separates source integrity from cross-source reconciliation. It does not establish that Wikipedia is universally correct, or that a plausible uncorroborated MangaDex mapping is wrong.

## Exact files changed or added

These changes are relative to the task's local baseline, rather than the plugin worktree's large pre-existing Git diff.

| Location | File | Change and reason |
| --- | --- | --- |
| Plugin | `C:\MangaNana-Dev\MangaNana-calibre\mangadex_structure_reference.py` | Changed. Validate aggregate representation and stable release identifiers; preserve ambiguity/rejection evidence; prevent corrupt refreshes or legacy unvalidated cache entries from concealing integrity failures. |
| Plugin | `C:\MangaNana-Dev\MangaNana-calibre\publication_manifest.py` | Changed. Reconcile independently eligible explicit reference claims, retain both claims, preserve provider/curation authority, and prevent projection or parent derivation from filling an unresolved conflict. |
| Plugin | `C:\MangaNana-Dev\MangaNana-calibre\tests\test_reference_integrity.py` | Added. 31 deterministic shared-core tests. |
| Plugin | `C:\MangaNana-Dev\MangaNana-calibre\tests\test_mangadex_structure_reference.py` | Updated existing test. Malformed aggregate now expects `invalid_structure` and integrity diagnostics, rather than a transient transport failure. This test file already existed locally. |
| DDK | `C:\MangaAnka DDK\ddk_publication.py` | Changed. Expose manifest reference-conflict claims in publication JSON and the existing aggregate `REFERENCE_CONFLICT` finding. |
| DDK | `C:\MangaAnka DDK\ddk_curated_resolution.py` | Changed. Carry effective conflict diagnostics from the curated manifest; retain the automatic result separately. |
| DDK | `C:\MangaAnka DDK\tests\test_reference_integrity.py` | Added. Five tests for the generic disagreement pattern, provider authority, curation, immutable history/acceptance, and the clean World Is Mine control. |
| DDK | `C:\MangaAnka DDK\tests\fixtures\reference_integrity_pattern.json` | Added. Explicitly synthetic, count-shaped evidence fixture; no title-specific production behavior. |
| DDK | `C:\MangaAnka DDK\tests\smoke_packaged_reference_integrity.py` | Added. External offline verification of embedded DDK modules and seven packaged regression checks. No product smoke mode or catalog loader added. |
| DDK | `C:\MangaAnka DDK\DDK_REFERENCE_INTEGRITY_VALIDATION.md` | Added. This report. |
| DDK | `C:\MangaAnka DDK\dist\MangaAnka-Database-Development-Kit.exe` | Rebuilt from current source and the unchanged spec. |

Generated validation evidence is under `C:\MangaAnka DDK\build`: `reference-integrity-baseline`, `reference-integrity-validation.json`, `reference-integrity-plugin-tests.log`, `reference-integrity-full-tests.log`, `reference-integrity-packaged-tests.log`, `reference-integrity-build.log`, and the `reference-integrity-pyinstaller` build directory.

The baseline directory contains original copies, four task-scoped unified product diffs, and hashes of 92 top-level Python product sources across both worktrees. Exactly the four product files listed above changed in that hash comparison. The remaining protected sources were identical. No Qt source, launcher, spec, font, database, writer-lock, acceptance, search, provider-ranking, or command parser file was edited. No commit, push, tag, release, version bump, reset, or clean was performed.

## Reconciliation policy

Ordinary precedence remains selected provider explicit membership -> unambiguous MangaDex explicit metadata -> validated Wikipedia metadata -> existing safe derivation -> unmapped.

Fallback applies when another reference has no independently eligible membership claim. An unresolved conflict applies when independently eligible explicit claims for the same publication context disagree and no authorized provider or reviewed/verified curation resolves the membership. Source rank alone does not break that tie.

Eligibility is checked before comparing claims:

- MangaDex must have valid structure, the existing structure contract, matching canonical work and compatible structural edition family, an explicit normalized numeric mapping, and no per-chapter ambiguity. Last-known-good/failed-refresh evidence is not an independently current challenger.
- Wikipedia challenger eligibility reuses `trusted_wikipedia_records`: trusted/shareable work context, matching identity and language, compatible edition, confident title/alias match, supported contract and successful collection status, explicit validated record provenance, and no quarantine, stale collection, or failed refresh. Explicit bounded ranges are expanded using the existing range helper. Existing future/preorder content filtering remains in force.
- Internally conflicting Wikipedia claims do not become a single eligible challenger. Untrusted, incompatible, stale, partial, or incomplete evidence cannot veto a current eligible MangaDex claim.

This is an eligibility gate for independent reconciliation, not a rewrite of every historical Wikipedia gap-fill path. Existing ordinary gap-fill behavior remains. Aliases, edition classification, and canonical matching were not changed.

When eligible explicit claims disagree:

1. Preserve both claims and their provenance in manifest runtime data.
2. Preserve explicit provider membership or REVIEWED/VERIFIED curated membership as the effective authority, with `resolved_by` diagnostics.
3. Otherwise clear only the disputed effective chapter membership; mark it ambiguous and unresolved.
4. Keep unrelated chapter mappings and acquisition identities intact.
5. Expose one aggregate `REFERENCE_CONFLICT` category with affected chapters and claims in Details.
6. Let existing publication-health and acceptance rules consume that state. Their policy was not edited.

A builder refresh replaces that source's previous stored claims and recomputes conflicts. Repeated builds do not mutate source snapshots. Partial refreshes preserve remaining eligible claims; a legacy stored conflict without claims stays fail-closed until sufficient reevaluation occurs. Curation can resolve the effective result while the automatic contradiction remains available for inspection.

## MangaDex integrity and cache behavior

`aggregate_mappings()` keeps its existing two-result API by default. Optional diagnostics supply a third result. Equivalent duplicate normalized chapter labels remain supported. Sparse mappings, missing native volume labels, zero/decimal identifiers, nonmonotonic assignments, and plausible uncorroborated mappings are not rejected by new statistical heuristics.

Malformed aggregate/record/container representations and malformed supplied release identifiers produce retained integrity diagnostics. Where the source supplies stable UUID release identifiers, incompatible reuse across chapter or explicit volume claims quarantines the affected chapter keys; unrelated valid mappings survive. Equivalent duplicate releases and missing identifiers remain supported.

The existing structure cache contract remains `mangadex-structure-v1`. A new validation marker, `mangadex-aggregate-integrity-v1`, distinguishes entries processed by the hardened parser. Legacy entries without that marker cannot be reused as validated hits or last-known-good fallback. Validation refresh is scoped to the existing identity/edition cache key; there is no global cache purge or TTL change.

A demonstrably malformed aggregate refresh is `invalid_structure`, not a transport failure. It stores the quarantined result under that same cache key, preventing a later transport failure from resurrecting the formerly accepted mapping. All-ambiguous refreshes also replace prior accepted structure. Genuine transport failures retain existing last-known-good behavior for appropriately validated prior entries.

Consistent but factually wrong MangaDex metadata cannot be disproved by this parser alone. An independently eligible contradictory reference or authorized evidence is still necessary. The repair deliberately does not invent volume-order or chapter-count plausibility rules.

## Deterministic policy matrix

| Evidence case | Validated behavior |
| --- | --- |
| MangaDex only | Accept uncontested eligible explicit memberships under existing precedence. |
| Wikipedia only | Use eligible explicit Wikipedia memberships. |
| Both agree | Retain claims; effective membership retains MangaDex precedence. |
| Both explicitly disagree | Only affected membership unresolved; claims retained; aggregate conflict represented. |
| Internally ambiguous MangaDex + valid Wikipedia | Fall back to Wikipedia for the affected membership. |
| Internally ambiguous MangaDex without fallback | Unresolved; fractional derivation cannot conceal ambiguity. |
| Explicit provider membership + reference disagreement | Provider membership survives, whether it agrees with MangaDex or Wikipedia. Automatic disagreement remains diagnostic. |
| REVIEWED/VERIFIED curation + disagreement | Curated membership resolves the effective result; automatic contradiction remains inspectable. |
| One dispute surrounded by clean mappings | Only disputed membership and dependent unsafe derivation change. |
| Disputed fractional/special chapter | Cannot be silently filled from parent membership; special and acquisition identity remain intact. |
| Previously clean mapping gains eligible contradiction | Refresh removes disputed effective membership and records conflict. Later resolving evidence can recover it. |
| Equivalent duplicate releases/normalized labels | Accepted; no invented disagreement. |
| Conflicting normalized labels/reused stable release ID | Affected keys quarantined with evidence; unrelated keys preserved. |
| Sparse plausible uncorroborated mappings | Accepted; no mandatory second-source corroboration. |
| Missing volume / zero / decimal / nonmonotonic labels | Existing supported representation behavior preserved. |
| Malformed aggregate | Invalid-structure diagnostics; unsafe cached structure not restored. |
| Ineligible Wikipedia challenger | Does not veto current eligible MangaDex. Identity, edition, language, contract, confidence, stale/future and internal-ambiguity cases covered. |
| Stale MangaDex + current eligible Wikipedia | Eligible fallback survives; stale evidence is not an independently current challenger. |
| Reordered application/repeated build/partial refresh | Deterministic reconciliation; stored claims survive or are replaced according to source refresh. |

## Synthetic Chainsaw Man evidence-pattern regression

The fixture represents the reported generic pattern; it is not copied from the actual Audit 23 or the production database. Production code contains no title or chapter-number special case.

The MD-only control selected 203 -> 20 and 232 -> 1, with artifacts 203.1 and 203.2 deriving volume 20. Adding independently eligible Wikipedia claims 203 -> 22 and 232 -> 24 changes only these four projection memberships:

| Identifier | Control | Reconciled result |
| --- | --- | --- |
| 203 | Volume 20 | Unresolved reference conflict |
| 203.1 | Derived volume 20 | Unresolved |
| 203.2 | Derived volume 20 | Unresolved |
| 232 | Volume 1 | Unresolved reference conflict |

The fixture retains 232 canonical main chapters: 230 mapped and 2 unmapped main chapters. Direct conflicting chapters are 203 and 232. It reports exactly one aggregate `REFERENCE_CONFLICT`. Health is identity PASS / publication REVIEW / normalization REVIEW / acquisition PARTIAL. All acquisition IDs and labels survive, and other memberships remain unchanged.

Provider-authority variants and REVIEWED/VERIFIED curation variants pass separately. Curation restores all 232 main mappings and publication PASS in the effective result, while preserving the original automatic conflict evidence. Fractional derivation and special handling cannot conceal the unresolved conflict.

The clean World Is Mine fixture remains 163 logical chapters, 14 derived volumes, 163 mapped, zero unmapped, and no holes.

## History, acceptance, and protected behavior

The disposable schema-7 history test persists a clean audit followed by a conflicting audit. Their audit IDs are distinct. The entire serialized original audit row remains identical. New conflict evidence is stored only in the new audit. Existing acceptance blocks unresolved mappings/conflicts; acceptance policy was not changed.

The full DDK suite also passes existing working-set, Force Re-Audit transaction/lifecycle, acceptance, curation, provider, and canonical-special regressions. No backend schema migration, command-grammar change, cache purge, acceptance bypass, curation-policy change, or history rewrite was introduced.

Captured Dandadan regressions pass, including the MangaPill case with 246 main chapters, two acquired recognized specials, 248 logical units, two unresolved provider artifacts (26.5 and 193.1), 219 mapped main / 221 total mapped, 27 uncompiled main, zero unmapped main, and 25 released volumes. Its captured health remains PASS / PASS / REVIEW / PARTIAL. The captured Atsu multi-group case also passes with its existing health PASS / PASS / PASS / PARTIAL.

Acquisition, publication structure, and artwork remain separate. Search identity, ranking, Atsu semantics, canonical specials, freshness/released-volume/UNCOMPILED rules, health derivation, output behavior, and the prior SQLite self-lock correction were not edited.

## Tests and build

| Validation | Result |
| --- | --- |
| New focused shared-core integrity module | 31 tests passed, included in focused suite. |
| Focused shared-core suite | 234 tests passed in 3.703 seconds. |
| New DDK integrity module | Five tests passed; included in full suite. |
| Full DDK suite | 352 tests passed in 85.916 seconds. |
| Packaged offline regression checks | Seven tests passed in 1.230 seconds. |
| Syntax/static checks | AST parsing, in-memory compilation and trailing-whitespace checks passed for eight changed source/test Python files. Scoped plugin `git diff --check` passed. |
| Primary Qt EXE rebuild | Passed using the unchanged PyInstaller spec. |

Focused shared-core modules: `test_reference_integrity`, `test_mangadex_structure_reference`, `test_publication_manifest`, `test_patch1c_publication`, `test_mangadex_special_metadata`, `test_publication_specials`, `test_publication_freshness`, `test_reference_integration`, `test_wikipedia_collection`, `test_unified_volume`, and `test_reference_language_order`.

Commands used with `C:\MangaAnka DDK\.venv-qt\Scripts\python.exe`:

```text
-m unittest <the 11 focused shared-core modules above> -q
-m unittest discover -s tests -p test_*.py -q
tests\smoke_packaged_reference_integrity.py dist\MangaAnka-Database-Development-Kit.exe
-m PyInstaller --noconfirm --workpath build\reference-integrity-pyinstaller MangaAnka-Database-Development-Kit.spec
```

Shared-core tests used `PYTHONPATH=C:\MangaNana-Dev\MangaNana-calibre`. All test databases were disposable. Network was fake/offline; tests guard against accidental urllib requests.

The first sandboxed build could not collect installed Tcl/Tk; the spec correctly refused an incomplete artifact. The build was then rerun with approved access to the installed runtime and completed successfully. The spec was not weakened or edited.

Packaged validation reads the actual EXE archive and compares six embedded module code objects with current source: `ddk_publication`, `ddk_curated_resolution`, `mangaanka_database_development_kit`, `ddk_catalog`, `ddk_acceptance`, and `qt_app.workers`. All match. It then runs the five new DDK integrity tests plus the two captured Dandadan tests against embedded DDK code and the local shared core.

Archive checks confirm the Qt Windows platform plugin, Tk/Tcl fallback resources, no database payload, no colliding ICU DLL, and no frozen shared-core submodules. The DDK continues to load current shared implementation from the local plugin worktree. Launcher and legacy Tk fallback source remain unchanged.

Final EXE: `C:\MangaAnka DDK\dist\MangaAnka-Database-Development-Kit.exe`

- Size: 52,511,341 bytes.
- SHA-256: `11947599f299920cf9de0c8a0e36c7eb415af6960b5595453e748bce494aeddb`.
- Primary launcher remains `C:\MangaAnka DDK\Launch_MangaAnka_DDK.bat`.

## Checks deliberately not run and limitations

- The production catalog, actual Audit 23, and live exports were not opened. The actual title's current provider/reference evidence has not been confirmed by this pass.
- No live network/provider audit or full corpus audit was run. The synthetic fixture validates policy, not today's source data.
- The entire plugin repository suite was not run, as requested. The focused 234-test suite covers affected reference/publication behavior and clean controls.
- No native packaged GUI/bootloader interaction, physical DPI/window smoke, Calibre import, or output-download test was run in this pass. Qt product code did not change; existing Qt tests were included in the passing full DDK suite. Do not interpret the seven archive-based packaged checks as an interactive GUI smoke.
- Old historical audits remain unchanged and are not retroactively repaired. Restart the DDK and run a new audit to use the correction.
- Without independently eligible evidence, a consistent but incorrect source claim can still be accepted. This is an intentional evidence boundary, not a guessed plausibility check.
- Reference eligibility and source claims can change between live runs. A provider or reviewed/verified curation may legitimately resolve a contradiction, so synthetic counts are not unconditional live expectations.

## Manual live-catalog retest — user operated only

1. Close the DDK normally, then launch `C:\MangaAnka DDK\Launch_MangaAnka_DDK.bat`. Select your intended catalog and working set explicitly.
2. Select the exact standard-English Chainsaw Man working-set item and run More -> Force Re-Audit Selected. Confirm a new immutable audit ID is created and the selected pin advances only on success; the previous audit remains in History.
3. Inspect Details and Publication Map. If the same independently eligible claims remain and there is no provider/curation resolver, expect direct conflicts at 203 and 232, 230/232 mapped main chapters, one `REFERENCE_CONFLICT`, publication REVIEW, and no inherited volume on 203.1/203.2. If evidence differs, inspect the retained claims and authority rather than forcing these counts.
4. Compare Details/export health for that same audit revision. Confirm unaffected mappings and other working-set pins remain intact. Do not accept or curate solely to clear the warning; review the preserved evidence first.

No automated operation in this task accessed `C:\Users\Jerry\Documents\MangaAnka-Database-Development-Kit\mangaanka_catalog.db`.
