# Six-title Review Packet regression pass — 2026-10-02

This pass uses the first real six-title Review Packet as reduced, offline regression evidence. The fixture is `tests/fixtures/review_packet_regressions.json`; it records diagnostic shapes and observed counts, not hard-coded title rules. The user's live catalog and existing packet were read only. No provider crawl or EXE build was run during source development.

## Root cause and rule

The plugin's `build_publication_projection` marks every repeated numeric acquisition key ambiguous. For two equivalent provider records at chapter 125, this suppressed an otherwise unambiguous Wikipedia chapter-to-volume mapping. The DDK also counted raw multiplicity as `REFERENCE_CONFLICT`. The DDK-only `ddk_duplicate_projection.py` adapter now reconciles equivalent duplicate rows against the existing manifest after the plugin projection. It preserves every acquisition row and all source/reference payloads. An unambiguous explicit provider membership keeps precedence; otherwise a trusted MangaDex or Wikipedia mapping can fill both computed projection entries. Contradictory explicit provider memberships for the same key still fail closed as one structural conflict. Duplicate count remains visible as provenance.

Provider integer ranges such as `8-16` are now classified as `PROVIDER_RANGE_BUNDLE` when canonical evidence has not established them as chapters. Same-provider `.1/.2` pairs are `PROVIDER_SPLIT_CANDIDATE`; other repeated fractional numbering is `PROVIDER_FRACTIONAL_CANDIDATE`. These are conservative unresolved acquisition diagnostics, never automatic canonical chapter promotions. A group is reported once per provider and pattern family, with all member IDs retained in the packet JSON and Details. Remaining unknown acquisition rows stay `UNCLASSIFIED_ACQUISITION`. No title-specific mappings or provider rules were added.

The Problems and Review Packet suggestions now direct identity mismatches to identity resolution, range/split patterns to code review, acquisition gaps to acquisition checks, and real structural conflicts to reference research. Automatic code-review candidates can arise from one work with repeated records; grouped candidates across works retain all member IDs. Wrong-edition/no-canonical audits are excluded from those automatic candidates. `affected_rows` resolves normalized numeric keys while preserving the exact original provider identifier.

## Expected six-title re-audit checks

After a future EXE rebuild, rerun exactly **Attack on Titan, Chainsaw Man, Jujutsu Kaisen, Demon Slayer: Kimetsu no Yaiba, Berserk, and The World Is Mine** against the current provider/reference services. Export a fresh paired JSON/Markdown Review Packet. Inspect the Audit and Problems columns, select each work in Details, and verify:

| Work | Focus |
| --- | --- |
| Attack on Titan | Equivalent duplicate acquisition rows retain the trusted volume mapping; only genuine structural contradictions remain `REFERENCE_CONFLICT`. |
| Chainsaw Man | Publication mapping remains separate from provider range/split candidates; inspect all grouped members in JSON/Details. |
| Jujutsu Kaisen | Fractional extra records remain unresolved until independently confirmed; do not infer canonical chapters from numbering alone. |
| Demon Slayer: Kimetsu no Yaiba | Publication may pass while acquisition coverage remains partial. |
| Berserk | Wrong fan-color edition blocks publication curation and recommends identity resolution. |
| The World Is Mine | 163 canonical chapters / 14 reference volumes remains a PASS control if live evidence is unchanged. |

Live totals may differ from the original packet because providers and references can change. Compare evidence and classification, not fixed counts. The deterministic fixtures establish the rules without assuming those totals remain current.

## Validation and limits

Fourteen packet regression tests pass, including provider precedence, conflicting explicit memberships, provenance, grouping, health separation, and the World control. The full DDK suite and disposable-database Tk smoke are run separately. The UI smoke covers scrollbars, contrast, Problems candidate notice, and all artifact members in Details. No schema migration is needed: artifact evidence is stored in existing JSON fields on new audits. Legacy audits need a re-audit to gain the new classifications. The unchanged Calibre plugin still treats duplicate keys as ambiguous in its own projection; the DDK adapter is an audit-only correction pending a separate, explicitly reviewed plugin change. Candidate range/split/fractional groups are prompts for investigation, not proof of provider bugs or safe publication curation.
