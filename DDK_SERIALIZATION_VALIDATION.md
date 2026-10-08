# Targeted serialization and fractional-special repair

DDK v0.3.0, schema v7; current local search core 0.14.0-dev. Validation completed 2026-10-04. Automated work used deterministic fixtures and disposable catalogs. The production catalog and Audit 16 were never opened or modified. No commit, push, tag, release, or version bump was performed.

## 1. Root causes

The existing final projection treated every included chapter without an effective volume as unmapped. Neither effective counts nor central acceptance distinguished a known current serial chapter from a failed volume assignment. Qt grouped both under Unmapped.

Fractional normalization did not retain explicit independent special/extra identity before provider-pattern classification. Unsupported decimals could become provider fractional candidates, while independently supported extras were not represented as a distinct recognized class. Missing explicitly referenced acquisition records shared CHAPTER_COUNT_DISAGREEMENT even when they were typed specials and the publication structure was complete.

## 2. Exact source inventory

Modified:

- `ddk_chapter_normalization.py`: independent special recognition and fractional fail-closed rules; effective counts.
- `ddk_publication.py`: validated reference records, derived states, counts, coverage, concise findings.
- `ddk_curated_resolution.py`: preserve automatic informational state while respecting reviewed overrides.
- `ddk_catalog.py`: effective row states and validation counts.
- `ddk_acceptance.py`: revalidate uncompiled evidence in the existing central evaluator.
- `ddk_review.py`: acquisition-only classification, health, packet diagnostics.
- `ddk_exports.py`: context, summary, and CSV count diagnostics.
- `qt_app/models/publication.py`: distinct uncompiled and provider-only groups.
- `qt_app/pages/catalog.py`: mapped/uncompiled display and inspector; default Title width 185 and Chapters width 195 keep the eight-column layout within its existing viewport.
- `qt_app/pages/details.py`: serialization identifiers and special provenance.
- `qt_app/session.py`: stored-publication count display.
- `MangaAnka_Database_Development_Kit_README.md`: current repair documentation.

Added:

- `ddk_publication_states.py`: shared evidence validation and derived state summary.
- `tests/test_publication_states.py`: 23 deterministic publication/acceptance/normalization regression tests.
- `tests/test_qt_publication_states.py`: five Qt model/presentation tests.
- `tests/prepare_publication_state_smoke.py`: reproducible disposable packaged fixture.
- `DDK_SERIALIZATION_VALIDATION.md`: this report.

Generated: rebuilt `dist/MangaAnka-Database-Development-Kit.exe` and normal PyInstaller build artifacts. No plugin/search-core source, provider implementation, search ranking, command compiler, schema definition, launcher, spec, or hook was edited in this repair.

## 3. Schema and database safety

Schema remains v7. No migration, new table, or live database update is needed. Derived publication data is stored in existing audit JSON. Existing audits, pins, curation, dispositions, and approval history remain historical until a human explicitly reruns an audit. The smoke database is under the Windows temporary directory, with a separate temporary QSettings INI.

## 4. UNCOMPILED representation

Projection rows carry `_publication_state = UNCOMPILED` without a volume assignment. Publication JSON records `uncompiled_identifiers`, `uncompiled_chapters`, and `uncompiled_evidence`, alongside mapped, unmapped, and conflict identifiers. UNCOMPILED contributes to logical/canonical inventory but contributes to neither mapped nor unresolved counts. No future volume is created.

## 5. Exact evidence requirements

Automatic classification currently uses explicit uncollected records already supplied by the real Wikipedia reference service. It requires trusted canonical ID, a shareable context, compatible edition/language, a confident exact normalized canonical-title or trusted-alias match, the current cache contract, and validated complete/current reference data. Failed, stale, quarantined, conflicting, or unsupported collection segments reject the evidence. Each supporting chapter has an exact numeric identifier, explicit/validated confidence, Wikipedia source, source page, and stable source record ID.

All included unmapped candidates must be independently supported canonical main chapters explicitly identified as uncollected. They must form an integer contiguous suffix after the last compiled chapter, with no earlier internal gap, duplicate canonical key, or conflicting chapter assignment. Compiled chapters must follow an ordered volume sequence. The validated released volumes must be consecutive from volume 1 and exactly match the mapped released-volume set. Every trusted compiled reference pair must reach the projection with the same volume. MangaDex, manifest, provider assignments, and reported released-volume totals must not contradict that boundary or claim additional unresolved released volumes.

This is intentionally stricter than merely seeing a trailing gap. MangaDex aggregate absence, popularity, an ongoing label, or a large chapter total cannot establish uncompiled status.

## 6. Protection of real holes

Internal gaps, incomplete latest-release evidence, lost trusted volume assignments, conflicting mappings, identity/edition/language mismatches, stale reference data, and unsupported fractionals retain review findings. The entire candidate set must satisfy the suffix proof; a mixed or uncertain set stays unmapped. Tests include a trusted chapter 22 volume claim whose projection is deliberately broken; it remains a mapping failure.

## 7. Exact fractional-special recognition

Validated reference records explicitly typed special, extra, bonus, omake, prologue, or epilogue can establish `recognized_special` for the exact provider identifier. Work, edition, language, source provenance, and publication context must pass the same independent evidence guard. Conflicting special types/volume claims reject recognition. Recognized records keep their exact identifiers and types and remain visible in acquisition/publication diagnostics. They are excluded from canonical main chapter counts.

## 8. Unsupported fractionals

No decimal equivalence or integer-base matching was added. Reference 92.1 does not establish provider 92.5. Provider titles, provider special labels, or provider native-volume membership alone cannot independently establish a fractional special. Unsupported 19.5 and 92.5 remain `provider_fractional_candidate` with CODE_REVIEW_REQUIRED. A single unexplained decimal is also reviewable; the existing repeated provider-pattern handling remains available.

## 9. Missing special acquisition

New narrow finding `MISSING_SPECIAL_ACQUISITION` groups exact trusted special records absent from the selected acquisition. It is ACQUISITION_ONLY and can leave acquisition PARTIAL while publication remains PASS. These keys are removed from the generic missing-main CHAPTER_COUNT_DISAGREEMENT category. Ordinary missing main records retain their existing classification. No fake volume-correction command is suggested.

## 10. Health, acceptance, and curation

Coverage evaluates the currently compiled logical inventory separately from safely uncompiled chapters. The existing central acceptance evaluator requires mapped plus independently revalidated uncompiled counts to equal logical inventory; stored markers/counts alone cannot bypass it. All existing identity, conflict, curation, unknown, research, code-review, freshness, and lifecycle checks still apply. A clean safe suffix can be READY but is never auto-accepted.

Compatible reviewed/verified curated chapter, type, or volume values retain precedence. A curated volume assignment removes the effective uncompiled marker while preserving the automatic evidence. Explicit clearing is not silently undone by automatic reclassification. Command grammar and clear/reset/verification/evidence semantics are unchanged; no `set type uncompiled` command was added.

## 11. Review packets and exports

Packets expose mapped, uncompiled, unmapped, and conflict identifiers; recognized reference specials; unsupported provider candidates; missing acquisition specials; and their provenance. A selected clean title can include informational uncompiled evidence without creating an actionable problem. Normal all-unresolved packet behavior is preserved. Summary/context/CSV exports include uncompiled diagnostics.

## 12. Publication Map

The reusable map displays `Uncompiled / Serialized chapters` as a neutral informational group with exact identifiers and chapter titles. Released volumes remain separate. Provider-only/acquisition artifacts remain separate from canonical uncompiled rows. No guessed future volume appears. Existing scrolling and selection styling are preserved.

## 13. Catalog and Details counts

Catalog replaces an unexplained mapped/total ratio with `mapped · uncompiled` when a suffix exists. Inspectors and Details expose mapped, uncompiled, unmapped, volume totals, exact uncompiled identifiers, and recognized/missing specials. Raw Data retains the full canonical-main and logical count breakdown and provenance.

Counts must distinguish main chapters from acquired specials: the historical context field `canonical_chapters` continues to represent included logical inventory. Publication JSON additionally exposes `canonical_main_chapters`/main counts and `mapped_main_chapters`. Consequently, a recognized mapped extra increases the UI's total mapped/logical count by one without increasing the main chapter total. No count is represented as all volume-mapped when some chapters are uncompiled.

## 14. Dandadan-shaped offline result

The count-shaped fixture has 248 independently supported main chapters, 221 mapped main chapters, 27 uncompiled main chapters (exactly 220–246), zero true unmapped chapters, and 25 released volumes. One exact reference-supported extra, 89.1, is recognized and mapped. Unsupported 19.5 and 92.5 remain reviewable; reference 92.1 does not convert 92.5. Missing extras 14.5 and 92.1 produce acquisition-only diagnostics.

With the acquired recognized special included, logical inventory is 249, mapped inventory is 222, and uncompiled inventory is 27. Publication health is PASS, acquisition is PARTIAL, and overall review remains necessary for the unsupported fractional candidates. This deliberately does not force PASS or READY.

To reproduce the observed totals without pretending to copy live chapter metadata, the fixture uses main identifiers 0–219 plus independently explicit main record 219.5, followed by 220–246. These artificial fixture numbers are not production rules. No production code contains a Dandadan title condition or hardcoded suffix.

## 15. Focused tests

23 new offline backend tests passed, including fixtures A–I, release completeness, stale/failed references, exact title/edition/language compatibility, unsupported fractional records, forged uncompiled counts, central acceptance, acquisition-only missing specials, and preserved curated overrides. Five new Qt tests passed. The existing compact Catalog/eight-column viewport regression also passed after the width correction.

## 16. Full DDK suite and static checks

Final complete DDK suite: **266 tests passed in 50.669 seconds**. Earlier intermediate validation exposed a one-pixel compact Catalog overflow after widening Chapters; it was corrected before this final passing run. No failing test was skipped to obtain the result.

AST/bytecode compilation checked 68 source/test files. Import, conflict-marker/trailing-whitespace checks and local dependency checks passed; `pip check` reported no broken requirements. No entire MangaAnkā plugin repository suite was run.

## 17. Qt window/scale smoke

All nine source window/scale cases passed: 1120×720, 1440×900, and 1920×1080 at Qt scale factors 1, 1.25, and 1.5. Catalog, Audit, Problems, Curate, History, and Details were exercised. New model tests verify distinct map groups, exact titles/identifiers, neutral color, visible scrollbars, readable breakdowns, supported-special diagnostics, and preserved actionable unsupported fractional findings. These are configured Qt scale tests, not certification on every physical monitor/DPI combination.

## 18–19. Final packaged build and smoke

Rebuilt successfully with the existing PyInstaller 6.20.0 spec after the final passing suite. The primary launcher remains `Launch_MangaAnka_DDK.bat`, the source Qt entry point remains `mangaanka_qt.py`, and the legacy launcher remains `Launch_MangaAnka_DDK_Legacy_Tk.bat`. Spec/hooks/dependency files were unchanged. Geist remains optional and unbundled, with the existing Segoe/system fallbacks unchanged.

Final EXE: `C:\MangaAnka DDK\dist\MangaAnka-Database-Development-Kit.exe`

Size: **52,511,621 bytes**. SHA-256: `a7f0c9b5543560d1114345d22a9c347593bdda3edf71bf9d79413934cb13ecb6`.

The embedded PYZ code objects for all 12 changed runtime modules match compilation of the final local source (normalizing only filenames). Archive checks also confirmed no frozen plugin submodules, SQLite fixtures, or ICU binaries. The existing local plugin loader remains authoritative.

Actual packaged Windows UI smoke used only `serialization.db` in `mangaanka-serialization-smoke-e0y4w58i` under the Windows temporary directory and its isolated `ui.ini`:

- Catalog: eight default columns fit; selected row is readable; `222 mapped · 27 uncompiled`, 25 volumes, publication PASS, overall REVIEW. Inspector shows unmapped zero and acquisition PARTIAL.
- Details: exact 220–246 identifiers, recognized-reference specials, and missing-special acquisition keys visible; scrollable content and tabs function.
- Publication Map: compiled entries, recognized 89.1, missing reference specials, neutral UNCOMPILED group and exact titled rows, and separate 19.5/92.5 provider-only records verified. Scroll and keyboard navigation reached the end and returned to the boundary.
- Problems: exactly two categories, MISSING_SPECIAL_ACQUISITION/ACQUISITION_ONLY and PROVIDER_FRACTIONAL_CANDIDATE/CODE_REVIEW_REQUIRED. No UNMAPPED_CHAPTERS for the safe suffix. Selected fractional diagnostic lists only 19.5 and 92.5.
- Clean normal close and reopen against the same explicit disposable database verified, with no writer-lock residue.
- After normal close, disposable SQLite integrity check returned `ok`, foreign-key check returned no violations, and isolated QSettings were saved.

No live provider/reference run or production database action was performed. The packaged smoke validates persisted deterministic model output; offline adapter tests exercise the actual derivation path.

## 20. Remaining limits

Actual Dandadan data may remain REVIEW if the existing references do not explicitly establish the safe current release boundary and uncollected suffix. A trailing absence alone is insufficient. Similarly, a decimal reference row typed ordinary chapter cannot establish a special merely from its number. The repair adds no web scraping or provider requests.

Old audits are not retroactively rewritten. Existing user QSettings can preserve previous column widths; resize/reset layout if the new count text is clipped. Main versus logical counts differ when acquired recognized specials exist, as explained above. The local plugin worktree remains required at runtime. The legacy Tk launcher is preserved; no fresh interactive Tk workflow certification was requested or performed in this repair.

## 21. Manual Dandadan re-test

1. Close other DDK writers and back up the live catalog. Launch the rebuilt primary EXE and explicitly select the intended live database.
2. Rerun Dandadan manually; retain Audit 16 as historical evidence. Check exact work, standard edition, and language before assessing the new audit.
3. In Details/Publication, inspect canonical-main versus logical counts, released volumes, mapped/uncompiled/unmapped identifiers, and the actual uncompiled evidence. Confirm no future volumes were invented.
4. Inspect 19.5, 89.1, and 92.5 individually. Recognition requires exact independent special evidence; unsupported or mismatched identifiers should still require review. Missing typed specials should show acquisition-only diagnostics.
5. Check Problems and central Acceptance. A safe tail alone should not block, but every other real blocker still applies. Accept only through the existing explicit human action after reviewing the evidence.
