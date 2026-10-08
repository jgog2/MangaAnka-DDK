# MangaAnkā DDK normalization and console validation — 2026-10-02

The DDK now runs the local plugin's `effective_search_rows` between enrichment
and ranking. The previous live The World Is Mine audit skipped that pass, so
its selected rows had a canonical ID but no high-confidence identity. The
plugin's MangaDex structure resolver correctly returned
`unavailable_identity` without a request. The older positive fixture supplied
high confidence and a MangaDex title ID directly, so it tested projection but
did not reproduce live discovery. Both the fail-closed and discovery paths now
have deterministic tests. A fresh live temporary-database audit returned
163 raw records, 163 canonical chapters, 14 final volumes, 163 mapped, and no
holes.

## Implementation and counts

`ddk_chapter_normalization.py` uses the plugin's numeric chapter parser and
exact chapter-identity matcher. A row is canonical main when compatible
chapter-level structural evidence, two independent complete provider
inventories, or provider-explicit membership without contrary peer quorum
supports it. An explicit provider special type remains a special. Equivalent
releases of the same exact chapter are counted once. Unsupported rows remain
unclassified; when there is only one provider and no structural evidence,
numeric chapters are provisional and still block PASS. Reported totals never
select individual chapters. Raw acquisition and reference payloads are
preserved alongside classification and effective projection.

`raw_acquisition_records` counts selected/fallback acquisition rows.
`canonical_main_chapters` counts established main chapters.
`recognized_specials` counts explicit special records.
`duplicate_records` and `unclassified_records` are separate diagnostics.
`logical_chapters` counts normalized main, special, and provisional chapters,
plus reviewed curated-created publication chapters. `mapped_chapters` and
`unmapped_chapters` refer to that effective publication set. Final volumes
are distinct effective mappings, including approved curated publication
volumes, rather than native provider groups. Provisional rows remain visible
in logical totals but have a blocking unclassified finding.

Curated chapter and volume existence markers reuse `curated_fields`; no new
table or column was needed. Reviewed/verified curated-created chapters enter
the effective manifest without creating acquisition URLs or pages. Missing
acquisition gets one `ACQUISITION_COVERAGE_GAP` finding. Raw snapshots and the
automatic manifest remain unchanged.

`WRONG_EDITION_MATCH` suppresses dependent mapping findings, while an
independent source failure remains visible. `REFERENCE_CONFLICT` owns its
affected unmapped keys. Fully absent volume structure with reported volume
evidence is aggregated as `MISSING_REFERENCE_STRUCTURE`; unexplained provider
rows are one `UNCLASSIFIED_ACQUISITION` finding with affected keys. Existing
explicit reference gaps remain `CHAPTER_COUNT_DISAGREEMENT`. Details and
Problems show identity gates, attributed AniList/Kitsu totals, raw and
effective counts, reference status, and chapter-level before/after evidence.

## Command surface

The multiline console parses every line before preview, rejects mixed-work
batches, validates all changes together, and commits as one existing
`curated_changes` transaction. One undo/redo reverses/reapplies the group.
It adds mixed chapter sets; verification; generic reset; curated chapter and
volume creation/removal; renumber; work identity, alias, external-ID and
expected-total edits; and effective/provenance/explain inspection. Identity
and existence edits are marked high impact. An audit or revision change
invalidates both edit and undo/redo previews. Exact scope and raw evidence
immutability remain enforced. The full grammar is in `DDK_COMMANDS.md`.

## Focused live checks (disposable databases)

| Query | Raw | Canonical main | Unclassified | Mapped | Final volumes | Findings |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| The World Is Mine | 163 | 163 | 0 | 163 | 14 | none |
| Jujutsu Kaisen | 277 | 272 | 5 | 272 | 30 | UNCLASSIFIED_ACQUISITION |
| Chainsaw Man | 390 | 232 | 158 | 232 | 24 | UNCLASSIFIED_ACQUISITION; CHAPTER_COUNT_DISAGREEMENT (13 explicitly referenced fractional chapters absent) |
| Demon Slayer: Kimetsu no Yaiba | 205 | 205 | 0 | 205 | 23 | CHAPTER_COUNT_DISAGREEMENT |
| Berserk | 4 | — | — | — | — | WRONG_EDITION_MATCH only; selected fan-colored edition |

These are current responses from focused runs, not fixed expectations in code.
The existing 25-title corpus was not fully rerun.

## Verification

- `python -m unittest discover -s tests -p 'test_*.py' -q`: **51 passed**.
- `python -m py_compile` on changed Python modules and focused tests: passed.
- `python -u tests/ui_smoke.py`: passed with disposable SQLite and real Tk;
  Audit, Problems, Database, History and Details scrollbars, selected row and
  combobox contrast, multiline batch, previews, undo/redo and diagnostics
  were exercised. The Tcl runtime required execution outside the sandbox.
- A read-only SQLite backup of the existing working database was initialized
  in a temporary directory. Works, audits, holes, curated tables, and History
  counts were preserved; `integrity_check=ok`, no foreign-key errors.
- The working database was never opened for writing. No plugin file, commit,
  release, build script, or EXE was changed.

## Limits and manual check

MangaDex discovery can still fail closed when current identities or reference
results are ambiguous or unavailable. Provisional or unclassified rows need
chapter-level evidence or reviewed curation before PASS. The current plugin
does not yet consume the DDK's curated catalog directly. A title without a
trusted identity cannot be curated under the existing exact-binding rule.

After rebuilding the EXE yourself, open the existing workspace, rerun The
World Is Mine, Jujutsu Kaisen, Chainsaw Man and Berserk, and compare the
Problems/Details counts with the focused results above. Paste two nonoverlap
volume commands into the Database console, inspect one combined preview,
Apply, Undo, and Redo. Scroll each tab and inspect selected-row contrast.
