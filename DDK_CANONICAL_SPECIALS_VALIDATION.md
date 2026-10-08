Validated canonical-special repair from the current local worktrees, 2026-10-04. No live catalog was opened or changed; no commit, push, tag, release, or version bump was made. Counts below describe deterministic captured-data fixtures, not a new live Audit 20. The available export contained no matching Audit 20 / Work 10 entry, so it was not used to reconstruct that audit.

1. **Why 32.5 and 40.5 became main.** DDK normalization accepted exact explicit MangaDex chapter-volume mappings as canonical chapter evidence. MangaDex aggregate mappings did not carry chapter titles or special types. Provider-seeded manifest chapters defaulted to `chapter`; special recognition used validated Wikipedia special rows. Consequently, mapped fractions entered the main count despite their supplementary content. This was a taxonomy gap, not a numbering or volume-placement failure.

2. **Why 26.5 and 193.1 remained candidates.** They had acquisition identifiers but no compatible exact trusted chapter or special evidence in the inspected path. They therefore became `provider_fractional_candidate`. Neither decimal proximity nor a provider's row count proves identity or bonus status. Those safeguards remain.

3. **Research for every identifier.** The table uses captured public MangaDex aggregate and bounded chapter metadata for the verified work ID, plus the current public MangaPill chapter list. MangaDex category titles are from Portuguese-language releases, with explicit collected-volume membership. They support structural taxonomy, not page-for-page equivalence with every English release. Mixed supplementary bundles are deliberately typed `special`; they are not all claimed to be single omake chapters.

| Identifier | Evidence / category title | Type | Collected volume | MangaPill acquisition |
|---|---|---|---|---|
| 5.5 | [Omake & Extras](https://mangadex.org/chapter/ad45c2bc-04f5-4bd8-95e4-b3fad20e68e0) | special | 1 | absent |
| 14.5 | [Omake & Extras](https://mangadex.org/chapter/1ce9735a-5bfc-441f-b45b-af979900687b) | special | 2 | absent |
| 23.5 | [Omake & Extras](https://mangadex.org/chapter/657962be-bfce-4f59-a866-3a55908d8ea1) | special | 3 | absent |
| 26.5 | [Provider label only; exact independent identity unproved](https://mangapill.com/chapters/5460-10026500/dandadan-chapter-26.5) | uncertain | unknown | present |
| 32.5 | [Omake & Extras](https://mangadex.org/chapter/6a65f364-707e-4e6f-8885-8874743e24a7) | special | 4 | present |
| 40.5 | [One-Shot, Omake & Extras](https://mangadex.org/chapter/341c01e6-16b5-40ab-a6c6-a5a7727f8a6f) | special | 5 | present |
| 49.5 | [Omake & Extras](https://mangadex.org/chapter/e0e15f54-8928-49a5-aaf1-afe44d0a0f6d) | special | 6 | absent |
| 58.5 | [Omake & Extras](https://mangadex.org/chapter/05e458fa-97f3-46ec-a9eb-8afcba98e630) | special | 7 | absent |
| 67.5 | [Omakes & Extras](https://mangadex.org/chapter/351d8e01-9f0b-408c-9483-7242c1f77fc1) | special | 8 | absent |
| 76.5 | [Omake & Extras](https://mangadex.org/chapter/796c95bd-97fd-409d-85f4-d282ada834d3) | special | 9 | absent |
| 85.5 | [Omake & Extras](https://mangadex.org/chapter/aac50662-8de1-4ac7-ad7b-4ee1c3190dbf) | special | 10 | absent |
| 193.1 | [Provider label only; exact independent identity unproved](https://mangapill.com/chapters/5460-10193100/dandadan-chapter-193.1) | uncertain | unknown | present |
| 201.5 | [Extra](https://mangadex.org/chapter/49f06382-dce5-43f0-a213-96858c6bc05f) | extra | 23 | absent |

The [official Obon extra listing](https://shonenjumpplus.com/episode/3269754496443148048) and [official WJ44 one-shot reprint listing](https://shonenjumpplus.com/episode/3269754496713647940) establish that supplementary works exist. Neither establishes an exact link to MangaPill 26.5 or 193.1. Fan-wiki volume/omake listings were investigated; conflicting extra-chapter volume descriptions and numerical placement were not used to invent aliases or override explicit structure. Captures and the per-record confidence/provenance matrix are in `C:\MangaAnka DDK\tests\fixtures\canonical_specials`.

4. **Proven reference units.** Eleven fractions have explicit MangaDex category/title and volume evidence: 5.5, 14.5, 23.5, 32.5, 40.5, 49.5, 58.5, 67.5, 76.5, 85.5, 201.5. The selected captured MangaPill inventory acquires two of them. References never fabricate an acquisition URL for the other nine.

5. **Main versus special.** None of those eleven typed reference records is classified as main serial content. Ten mixed omake/extra or one-shot/omake/extra records use existing `special`; 201.5 uses existing `extra`. Existing `bonus`, `extra`, `omake`, `special`, `prologue`, and `epilogue` vocabulary is reused. Explicit category headings are matched conservatively; incidental words in a story title do not establish taxonomy.

6. **Uncertain/provider-only units.** MangaPill 26.5 and 193.1 remain retained, reviewable provider fractions. Their titles in the captured provider list are blank. There is no exact independent identity/volume proof accepted for them. Normalization remains REVIEW for this selected inventory; PASS is not forced.

7. **Alternate numbering.** No safe alternate-number link was established for the thirteen researched identifiers. In particular, 26.5 is not merged with nearby decimals or 40.5, and 193.1 is not merged with 201.5. A known Volume 23 omake does not prove that a differently numbered provider acquisition contains that unit.

8. **Alias representation.** A narrowly scoped shared matcher can consume explicit `aliases` in trusted special-reference JSON: provider/source ID, exact acquisition record ID, and exact original identifier must all match. The manifest retains the evidence; projection preserves the actual download ID and `_acquisition_chapter` while selecting the proven canonical label. A synthetic 2.1 → 2.5 link passes; without the link or with a different acquisition ID it fails closed. No Dandadan alias is injected. Existing JSON storage is sufficient; there is no new persistent alias table, command, or alias editor. Source notes are not automatically interpreted as proof.

9. **Dandadan main count: 246.** This is measured from the captured, independently resolved acquisition/reference fixture. The previous 248 included the two mapped supplementary acquisitions. No title-specific count is present in runtime code.

10. **Acquired recognized-special count: 2.** 32.5 and 40.5. The eleven reference-known special records remain separately visible; they are not all counted as acquired specials.

11. **Provider artifact count: 2.** 26.5 and 193.1 remain `provider_fractional_candidate`, grouped into one meaningful CODE / CODE_REVIEW_REQUIRED problem category.

12. **Mapped main count: 219.** Total mapped publication units remain 221: 219 main plus the two acquired specials. Correcting taxonomy does not remove those real acquisitions or damage volume structure.

13. **Uncompiled main count: 27.** The captured fixture's existing fully supported main suffix remains uncompiled. The shared released-volume/freshness and UNCOMPILED implementation is unchanged.

14. **Unmapped main count: 0.** A proven special without collected-volume evidence stays unassigned; it does not inherit its integer parent's volume and is tracked separately as an unassigned special. Exact affected records remain in diagnostic JSON.

15. **Released final volumes: 25.** Existing release evidence and publication precedence are preserved. Publication health remains PASS. The captured MangaPill tuple is identity PASS / publication PASS / normalization REVIEW / acquisition PARTIAL. The typed Atsu fixture remains PASS / PASS / PASS / PARTIAL, retaining its established primary/alternate group semantics.

16. **Special membership.** Explicit volumes for all eleven reference specials are in the table: Volumes 1–10 for their corresponding supplements, and Volume 23 for 201.5. The two acquired specials remain in Volumes 4 and 5. Provider explicit membership still precedes MangaDex; unambiguous MangaDex precedes validated Wikipedia; existing safe derivation follows. A recognized special bypasses numerical parent/pre-chapter-one volume inference. Unknown membership is never filled from decimal placement alone.

17. **Ordering.** Existing Decimal-based `chapter_sort_key` remains authoritative: 26 < 26.1 < 26.5 < 27. A recognized special retains its proven numeric/source label, title where available, type provenance, and actual acquisition ID. Reading order and collected-volume membership remain independent. Publication Map uses its existing recognized-special badge and effective type inspector.

18. **Main versus logical units.** The captured selected inventory has 250 raw rows, 246 main chapters, 2 acquired specials, 248 logical publication units, and 2 reviewable artifacts. Logical units describe legitimate projected acquisitions, not the union of every missing reference record. Counts now appear separately in Catalog, Problems, and Details inspectors and sharing context. Legacy `canonical_chapters` sharing field retains its previous logical-count meaning for compatibility; the explicit new fields remove ambiguity. Unknown old-snapshot main counts display as unknown rather than being invented. No historical audit is rewritten.

19. **Provider coverage.** Shared inventory comparison and ambiguous-primary selection now use unique supported main units before independently recognized special coverage; unresolved decimals do not purchase coverage. Raw row count remains diagnostic. Explicit native-volume chapter numbering restarts are preserved, and repeated rows do not expand coverage. Completeness, workflow/native-volume preferences, eligibility, and existing final source ordering remain. Count-only legacy inventories retain their existing count fallback. The early search stage has no full reference bundle, so unknown fractions receive no main/special coverage advantage; later DDK diagnostics show reference-qualified main/special/unresolved coverage. With trusted supplied special evidence, equal-main inventories may prefer richer legitimate specials without claiming more main chapters.

20. **MangaPill selection.** The actual inspected `_choose_primary` used raw count as a tie-breaker after native-workflow/completeness criteria; `compare_inventories` also used raw counts for superiority and comparability. An otherwise equivalent 246-main source versus 246-main plus four unsupported fractions deterministically reproduced the raw advantage; the repair removes it. This does not establish that live Audit 20 selected MangaPill solely for 250 rows: its exact serialized audit was unavailable. The next live audit may select another eligible source.

21. **Missing acquisition specials.** The nine missing fractions form one `MISSING_SPECIAL_ACQUISITION` category, ACQUISITION / ACQUISITION_ONLY, affecting nine identifiers. They are removed from the generic missing-main/count disagreement for this typed fixture. Publication stays PASS; acquisition may stay PARTIAL. The unresolved provider fractions remain a separate category. Nothing is deleted or fabricated.

22. **Exact plugin files added/changed during this pass.** Earlier unrelated worktree changes were preserved.

| Absolute path | Change |
|---|---|
| `C:\MangaNana-Dev\MangaNana-calibre\publication_specials.py` | Added shared scoped taxonomy, exact source-record aliases, explicit category parsing, coverage metrics. |
| `C:\MangaNana-Dev\MangaNana-calibre\publication_manifest.py` | Retains type evidence/title in manifest and projection; supports existing special kinds in Wikipedia membership; bypasses inferred special membership. |
| `C:\MangaNana-Dev\MangaNana-calibre\mangadex_structure_reference.py` | Optional bounded fractional chapter-metadata supplement to existing aggregate resolution; typed cache marker; preserves structure on metadata failure. |
| `C:\MangaNana-Dev\MangaNana-calibre\inventory_comparison.py` | Compares confirmed main/special coverage instead of raw chapter rows. |
| `C:\MangaNana-Dev\MangaNana-calibre\search_resolution.py` | Removes unknown extra-row advantage from primary tie-breaking. |
| `C:\MangaNana-Dev\MangaNana-calibre\tools\build_plugin.py` | Includes the new shared module in the explicit plugin package list. No plugin release package built. |
| `C:\MangaNana-Dev\MangaNana-calibre\tests\test_publication_specials.py` | Ten offline projection, identity, taxonomy, order, coverage and named-special tests. |
| `C:\MangaNana-Dev\MangaNana-calibre\tests\test_mangadex_special_metadata.py` | Five offline metadata scope, failure, cancellation and cache tests. |

The resolver adds at most one `/chapter?ids[]=` metadata request for at most 100 fractional release IDs obtained from the same work's explicit aggregate. Its total bound is three title searches + one aggregate + one metadata request. No feeds, pages, images, or acquisition requests are added. Missing IDs, untyped headings, parent/number/volume mismatches, contradictory releases, stale taxonomy, wrong identity/edition, and conflicting explicit types fail closed. Old untyped structure caches refresh to obtain the metadata marker; structure remains usable if the optional metadata call fails.

23. **Exact DDK files added/changed during this pass.**

| Absolute path | Change |
|---|---|
| `C:\MangaAnka DDK\ddk_chapter_normalization.py` | Consumes shared trusted special evidence and exact labels; separates unassigned specials from unmapped main publication units. |
| `C:\MangaAnka DDK\ddk_publication.py` | Reuses shared manifest special evidence; derives acquired/missing special and coverage diagnostics after the existing publication path. |
| `C:\MangaAnka DDK\ddk_exports.py` | Adds explicit main/special/logical/mapped-main count fields to existing read-only sharing context. Persisted health fields are unchanged. |
| `C:\MangaAnka DDK\qt_app\pages\catalog.py` | Existing inspector displays separate counts. |
| `C:\MangaAnka DDK\qt_app\pages\details.py` | Existing overview displays separate counts. |
| `C:\MangaAnka DDK\qt_app\pages\problems.py` | Existing inspector displays separate counts. |
| `C:\MangaAnka DDK\tests\test_canonical_specials.py` | Ten synthetic/captured tests, including both MangaPill and protected Atsu regressions. |
| `C:\MangaAnka DDK\tests\test_qt_canonical_specials.py` | Three existing-model/inspector/disposable persistence tests. |
| `C:\MangaAnka DDK\tests\fixtures\canonical_specials\mangadex-aggregate.json` | Captured public aggregate fixture. |
| `C:\MangaAnka DDK\tests\fixtures\canonical_specials\mangadex-fractional-0.json` | Minimized captured chapter category/title/volume/parent metadata. |
| `C:\MangaAnka DDK\tests\fixtures\canonical_specials\mangapill-chapters.json` | Captured public 250-row acquisition inventory, without page fetching. |
| `C:\MangaAnka DDK\tests\fixtures\canonical_specials\research.json` | Thirteen-identifier research/provenance/uncertainty matrix. |
| `C:\MangaAnka DDK\tests\smoke_packaged_canonical_specials.py` | External embedded-module verification and disposable packaged regression runner; not bundled. |
| `C:\MangaAnka DDK\DDK_CANONICAL_SPECIALS_VALIDATION.md` | This report. |
| `C:\MangaAnka DDK\dist\MangaAnka-Database-Development-Kit.exe` | Final rebuilt primary Qt EXE. |

Generated baseline/evidence/diff files are under `build\canonical-special-baseline`, `build\canonical-special-evidence`, and `build\canonical-special-packaged-disposable`. Existing PyInstaller build outputs are updated normally. Spec, hooks, fonts/theme, launcher scripts, provider adapters, output writers, plugin main workflow, and completed curation/health/freshness/acceptance implementations were not changed. No generic title hacks were added.

24. **Schema remains v7.** No SQLite DDL, migration, table or live-database operation. Kind evidence, aliases, special records and diagnostics use existing manifest/reference/publication JSON. Additional dataclass fields have defaults. Existing database files and pinned audit snapshots remain intact. Sixteen protected sources match saved baseline hashes; this includes schema, commands, health evaluator, acceptance, working sets, curated resolution, Atsu adapters/resolver and freshness sources. The persisted health field expressions in `ddk_exports.py` also compare equal to baseline.

25. **Grammar 3 remains unchanged.** No new command. Existing chapter type commands, Series # overrides, Force Re-Audit semantics, acceptance lifecycle and curated anchor/extension behavior are preserved. The health source remains persisted whole-audit disposition-adjusted health; filtering exports does not recompute it.

26. **Focused plugin validation: 500 tests passed in 8.040 seconds.** Thirty selected modules cover taxonomy/normalization, coverage/ranking, chapter order/output/effective Series #, source adapters, identity/edition/enrichment, cache, publication manifests/freshness, MangaDex/Wikipedia/reference integration, unified volumes and artwork boundaries. The entire plugin suite was not run. The first expanded run exposed the native-volume numbering-restart coverage edge case; it was corrected and all relevant existing inventory tests pass. Three initially mistyped test-module names were corrected before the final run. No failed import is counted as a passing test.

27. **Full DDK validation: 325 tests passed in 84.943 seconds.** `python -m unittest discover -s tests -p 'test_*.py'` in `.venv-qt`. Existing Fire Force/MF Ghost/Monster and count-shaped Chainsaw Man/Attack on Titan fixtures, World Is Mine control and systemic identity cases are covered. Selected plugin fixtures cover relevant Frieren, JoJolion, Tokyo Ghoul-style enrichment and Berserk edition protections. These are offline fixtures, not live corpus reruns. Changed/new Python sources pass AST/compile checks; plugin `git diff --check` passes. Main-only control behavior remains intact.

28. **Qt and Tk validation.** Three new Qt regressions pass; the full DDK suite includes existing Qt tests. All nine final geometry/scale smokes pass: 1120×720, 1440×900, 1920×1080 at 1.0, 1.25 and 1.5. Existing dark selection contrast and explicit scrollbars are preserved. The legacy Tk disposable widget smoke passed, covering all six surfaces, long-details scrolling, selection and commands. Its first sandboxed launch could not initialize installed Tcl; the same smoke passed with runtime access. No Tk code was changed. Font selection remains the existing installed-font/fallback chain; no font assets were added.

29. **Packaged validation.** PyInstaller completed after the final source tests. **42 packaged tests passed in 14.161 seconds**, running frozen application modules with disposable fixtures. Nine embedded DDK/Qt modules compare equal to freshly compiled current source, including the final count-inspector changes. The new taxonomy module loads from the current local plugin worktree. Native Computer Use also verified the normal no-database chooser, then explicitly opened only `build\canonical-special-packaged-disposable\catalog.db` with isolated `ui.ini`. Catalog showed 221 mapped / 27 uncompiled / 25 volumes and persisted PASS / PASS / REVIEW / PARTIAL. Publication Map displayed acquired 32.5 as RECOGNIZED SPECIAL, effective type special, Volume 4, with readable selection. Problems showed exactly nine missing special acquisitions and two review candidates. The final rebuilt EXE reopened the disposable catalog and Details visibly confirmed **246 main / 2 acquired specials / 248 logical / 219 mapped main / 221 total mapped / 27 uncompiled / 0 unmapped / 25 volumes**. The window was closed normally; no native command, acceptance or re-audit was applied to any live title.

30. **Final executable and launchers.** `C:\MangaAnka DDK\dist\MangaAnka-Database-Development-Kit.exe`. 52,511,618 bytes; SHA-256 `9ee9a432d2c6080dd5961723e2db047b26905dd71dc0b029396c1ecf99c329bc`. Primary launcher remains `C:\MangaAnka DDK\Launch_MangaAnka_DDK.bat`, using the packaged Qt EXE; source Qt entry point remains `mangaanka_qt.py`. Legacy fallback remains `C:\MangaAnka DDK\Launch_MangaAnka_DDK_Legacy_Tk.bat` and `mangaanka_database_development_kit.py`. Spec remains unchanged and loads the current local shared plugin core externally, rather than shipping a divergent copy. The explicit plugin package list includes `publication_specials.py`; the DDK dependency collector discovers it automatically.

31. **Known limitations and downstream behavior.** 26.5/193.1 identity remains uncertain; nine specials remain absent from captured primary acquisitions. MangaDex category metadata describes supplementary release units/bundles and is not an official publisher contents guarantee or content comparison. Only strict category headings are automatic; ambiguous titles and batches over 100 IDs stay conservative. Pre-reference ranking cannot know every decimal's taxonomy, and count-only legacy inventories have only their reported count available. Historical snapshots need a new audit to reflect the repair. No live Audit 20, Calibre GUI/import or actual manga-page CBZ/PDF download was run. Downstream chapter/volume acquisition uses actual projected reader IDs; output filenames, ComicInfo.xml generation, CBZ/PDF writers and effective metadata/Series # rules were inspected and left intact. Internal projected rows carry type/title/volume/order/provenance; no new ComicInfo tag or forced bonus filename rename was introduced. Unknown special membership remains visible rather than guessed. The native OS file chooser's accessibility focus could not be reliably confirmed, so its dialog was canceled; the disposable native smoke used explicit database and isolated UI-settings arguments instead.

32. **Small manual Dandadan check.** Open the primary launcher and explicitly choose your live catalog yourself. Select Dandadan standard/en and run More → Force Re-Audit Selected. Confirm a new audit and working-set pin, then inspect main/special/logical counts and health. With equivalent captured MangaPill evidence expect 246 main / 2 acquired specials / 248 logical / 2 artifacts, 219 mapped main / 221 total mapped / 27 uncompiled / 0 unmapped main / 25 volumes; current provider choice and availability may differ. Search 32.5 and 40.5 in Publication Map: special badges/types, Volumes 4/5, reference provenance and unchanged download IDs. Keep 26.5/193.1 under review unless new exact evidence resolves them. Check the single nine-special ACQUISITION_ONLY diagnostic and export the same pinned snapshot from Working Set and Problems: audit identity and persisted four-part health should agree. Do not accept it merely to force READY.
