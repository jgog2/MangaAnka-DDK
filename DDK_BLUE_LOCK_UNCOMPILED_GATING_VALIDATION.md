# Blue Lock UNCOMPILED gating investigation

This pass uses the current local worktrees and the supplied export's Blue Lock **Audit 46 revision 2**. The production catalog was never opened. The scoped export copy and its SHA-256 provenance are in `build/blue-lock-gating`.

## Finding and safety purpose

The former shared gate in `publication_freshness.py` was:

```python
no_conflicts = not (release.get('conflicts') or publication.get('conflicting_chapters') or
    manifest.get('ambiguous_chapter_keys') or md.get('ambiguous_chapters'))
```

It is one condition among explicit compatible uncollected evidence, unique main identities, contiguous integer sequence, consecutive trailing suffix, nondecreasing collected volume order, no tail membership claims, positive consecutive released-volume evidence, and complete projection of trusted released membership.

Its safety role is to prevent an unresolved membership/identity contradiction from masquerading as a safely established publication boundary. The earlier publication-freshness report documents the absence-of-conflicting-claims requirement. Local documentation does not establish why a global rather than evidence-scoped MangaDex check was originally chosen; no historical author intent is inferred here.

The raw MangaDex portion is over-broad. The manifest already rejects internally contradictory MangaDex assignments and can independently fill the same chapter from trusted Wikipedia. Such rejected claims are not two trustworthy references disagreeing. An independently resolved older chapter need not invalidate a complete, ordered released prefix and a separately explicit uncollected suffix. Conversely, an early chapter number alone does not prove irrelevance: its rejected volume claims or conflicting release IDs can still affect the boundary or identity.

## Narrow rule

Only the raw MangaDex ambiguity part is scoped. Release conflicts, unresolved effective reference conflicts, and manifest ambiguity remain blockers. Existing suffix, ordering, membership, freshness, identity, edition, language, acquisition completeness, and release checks are unchanged.

An ambiguity can be excluded from the main-tail proof only when:

- Existing MangaDex integrity-contract diagnostics establish a volume-only contradiction. Missing/unknown diagnostics and conflicting release identifiers remain blocking.
- Current trusted Wikipedia evidence independently supplies a single collected main membership, and the unique projected main row uses that exact Wikipedia membership.
- The resolved membership and **every rejected MangaDex volume alternative** belong to released volumes strictly before the final released volume. Consequently neither the final volume nor its immediate tail predecessor can be bypassed.
- Alternatively, independent trusted Wikipedia taxonomy proves a separate special identity outside the canonical main sequence, with released membership and no main/provisional projection collision. Fractional syntax is not special authority.

The original MangaDex ambiguity list and rejected evidence remain intact. No MangaDex mapping is reinstated. New runtime `uncompiled_evidence.ambiguity_scope` diagnostics list independently resolved and blocking keys; they are ordinary JSON evidence, not a schema addition.

A related adapter leak was reproduced: the DDK added raw MangaDex ambiguity to its effective conflict set even after the manifest marked that reference `incompatible`. Both consumers now honor that existing rejection before using its raw ambiguity, mappings or volume count for tail proof. Work/edition matching policy itself is unchanged, including the existing approved standard/color structural family; the incompatible-edition control uses omnibus.

## Call path

`aggregate_mappings()` retains accepted mappings separately from ambiguity and integrity diagnostics. `ReferenceMetadataService` supplies the reference bundle. `PublicationManifestBuilder.apply_mangadex_structure()` validates work/structural edition/contract and quarantines ambiguous keys; Wikipedia can independently fill them. `_reference_memberships()` reconciles eligible explicit source claims; genuine disagreements remain unresolved, and `build()` clears their effective membership and records ambiguity/conflicts. `build_publication_projection()` preserves that fail-closed result.

The shared evaluator runs in manifest runtime construction and again on the DDK's normalized acquisition projection. The latter has canonical main/special labels and effective conflicts. `effective_counts()`, publication holes, health, review exports and UI consume those states. Central acceptance still calls `verified_uncompiled_identifiers()` to recompute the evidence; acceptance and curation implementations are unchanged. No other consumer of the evaluator's former `no_conflicts` boolean was found.

## Deterministic matrix

Numbers are UNCOMPILED main chapters in a synthetic ten-chapter tail. Both policies were run through the real manifest/projection, with network forbidden. The baseline evaluator is loaded from the task-local pre-edit copy rather than reimplemented.

| Case | Former | Scoped | Result |
|---|---:|---:|---|
| 1. Early ambiguity without independent membership | 0 | 0 | Distance alone is insufficient |
| 2. Immediate predecessor ambiguity | 0 | 0 | Boundary remains blocked |
| 3. Ambiguity inside tail | 0 | 0 | Tail remains unresolved |
| 4. Ambiguity in final released volume | 0 | 0 | Final membership remains protected |
| 5. Independently typed, separate special | 0 | 10 | Special does not contaminate main continuity |
| 6. Other work/incompatible edition | 0 | 10 | Existing manifest rejection is honored |
| 7. Clean explicit uncollected tail | 10 | 10 | Existing behavior preserved |
| 8. No explicit uncollected evidence | 0 | 0 | No inference from missing volume |
| 9. Empty future listed volume | 10 | 10 | Tail stays uncompiled; future volume not assigned |
| 10. Gapped tail | 0 | 0 | Continuity fails |
| 11. Explicit membership claim on tail | 0 | 0 | No uncompiled classification over a mapping claim |
| 12. Earlier quarantined volume-only ambiguity plus complete independent Wikipedia boundary | 0 | 10 | Safe historical ambiguity excluded |

Additional controls keep an early ambiguity blocking if its alternatives reach the final/future volume; reject stale/partial Wikipedia, absent/unknown diagnostics and release-ID conflicts; and preserve actual cross-reference disagreement as unmapped `REFERENCE_CONFLICT`.

## Captured Blue Lock result

The replay reconstructs the selected Atsu acquisition rows from retained provider fields and reuses captured references unchanged. Other providers are represented only by their captured inventory summaries; historical peer chapter lists are not invented. No selection/search rerun, network, catalog write or audit mutation occurs.

| Measure | Former evaluator | Scoped evaluator |
|---|---:|---:|
| Logical/main | 364 | 364 |
| Mapped | 354 | 354 |
| Unexplained unmapped | 10 | 0 |
| UNCOMPILED | 0 | 10 |
| Final volumes | 40 | 40 |
| Reference conflicts | 0 | 0 |

The scoped keys are 300/301: independent Wikipedia volume 34; rejected MangaDex alternatives 33/34 and 34/35, all before released volume 40. Explicit uncollected 355–364 now establish the suffix. References, normalization, acquisition IDs and all effective volume assignments are structure-equivalent across the two replays. Missing acquisition parts 288.1/288.2 remain unchanged.

Health becomes **identity PASS / publication PASS / normalization PASS / acquisition PARTIAL**. Neither missing part is silently aliased to the selected full chapter. No CODE finding is suppressed, and no future volume is assigned. This is a replay result; the stored production audit remains unchanged until a manual re-audit.

## Files and preservation

Product changes:

- `C:\MangaNana-Dev\MangaNana-calibre\publication_freshness.py`: bounded ambiguity proof and existing incompatible-source rejection.
- `C:\MangaAnka DDK\ddk_publication.py`: honor the manifest's incompatible MangaDex source state when collecting effective conflicts.
- `C:\MangaAnka DDK\dist\MangaAnka-Database-Development-Kit.exe`: regenerated executable.

Added:

- `C:\MangaAnka DDK\tests\test_uncompiled_ambiguity_scope.py`: 18 deterministic regression tests.
- This validation report.
- Task-local evidence, baseline copies, diff, replay/matrix/package-verification scripts and logs under `C:\MangaAnka DDK\build\blue-lock-gating`.

No edits to Wikipedia parsing/scoping, MangaDex aggregation/quarantine, reference reconciliation, provider selection/ranking, artifact authority, acceptance, curation, schema, commands, Qt/Tk UI, launchers, packaging spec or version files. Schema remains **7**, command grammar **3**. No database migration, cache purge, title-specific rule, commit, push, tag or release.

## Validation and delivery

- Final 18-test boundary regression: PASS. Running those final expectations against the preserved former evaluator reproduces five expected baseline failures; the repaired evaluator passes all eighteen. The twelve-case before/after matrix is saved as `build/blue-lock-gating/synthetic-matrix.json`.
- Focused DDK publication/freshness/states/integrity/Wikipedia/normalization/provider controls: **165/165 PASS**.
- Focused shared-core freshness/integrity/integration/manifest/identity/specials/Wikipedia controls: **231/231 PASS**. The full plugin repository suite was not run.
- Full DDK suite: **555/555 PASS**, 317.904 seconds. This includes existing Qt, acceptance, curation, workflow, command and schema regressions.
- Captured Blue Lock Audit 46/2 before/after replay: PASS. Captured My Hero Academia parser replay: unchanged, PASS.
- Preserved controls include SPY-shaped Wikipedia membership, The World Is Mine 163 chapters/14 volumes, captured Dandadan canonical specials, Haikyu provider residue and provider-selection boundary. Dandadan retains 246 main plus two acquired specials, 248 logical, 219 mapped main/221 total mapped, 27 uncompiled main, zero unmapped main, 25 volumes, fractions 26.5/193.1 unresolved, and missing recognized specials acquisition-only.
- Changed Python sources compile; task-local diff whitespace check and scoped Git diff check pass. Existing unrelated dirty worktree changes were preserved.
- A rebuild **was required** for the small packaged DDK conflict-collection fix. The unchanged primary Qt spec rebuilt `C:\MangaAnka DDK\dist\MangaAnka-Database-Development-Kit.exe`. The initial restricted build failed its existing Tcl/Tk guard before replacing the old EXE; rebuilding with installed-runtime access and a separate task-local work directory succeeded. No guard, spec, dependency or launcher was changed.
- Final EXE size: **52,532,661 bytes**. SHA-256: `f129016d350319980450e907d904daf69e88c04688c75a97a4fbecc48bc69b07`.
- Primary launcher remains `C:\MangaAnka DDK\Launch_MangaAnka_DDK.bat`; legacy fallback remains `C:\MangaAnka DDK\Launch_MangaAnka_DDK_Legacy_Tk.bat`.

- Offline packaged verification: **71/71 PASS** (38 existing artifact/integrity/captured-Dandadan/Wikipedia tests plus 33 boundary/section-scoping/My-Hero tests), followed by successful captured Blue Lock and My Hero replays using the frozen application modules.
- The archive verifier confirms relevant embedded DDK code matches current source, no shared-core submodule snapshots or database files are bundled, and the evaluator resolves from the current local plugin `publication_freshness.py`.

No interactive production EXE launch, live provider re-audit or fresh DPI/window smoke is claimed. Qt/Tk UI code is unchanged; the live catalog is reserved for the user's manual check.

## Manual re-audit

1. Start the primary launcher and manually open the intended production catalog.
2. Select the exact Blue Lock working-set item, then run **More → Force Re-Audit Selected** once.
3. Inspect the new audit and publication evidence. With the same source facts, expect 364 main, 354 mapped, 10 UNCOMPILED, zero unexplained unmapped, 40 volumes, and no reference conflicts. Acquisition remains PARTIAL for 288.1/288.2.
4. Confirm the previous Audit 46 revision 2 remains in history. Acceptance remains a separate explicit action.

New upstream facts can change counts; the replay establishes behavior for the supplied packet, not a promise about future source contents. Unknown ambiguity, final-volume uncertainty, stale references, unresolved reference conflict, missing released membership and missing explicit tail proof deliberately remain fail-closed.
