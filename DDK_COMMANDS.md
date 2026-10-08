# DDK deterministic console

```text
Commands apply to the open title. Edits PREVIEW; click Apply to commit.
guard database_uuid 123e4567-e89b-12d3-a456-426614174000 audit 42 revision 3 database a42-e7-d0-w25
select chapter 222 | select chapters 222-232 | select volume 24
select unmapped | conflicts | modified | missing-title | all
clear selection
set volume 24 | set volume 24 selected | set volume 24 chapters 222-232
clear volume selected | clear volume chapters 222-232
reset volume selected  (remove override and restore automatic value)
set type chapter|bonus|extra|omake|special selected
set title "Exact title here" chapter 222
set source-note "Verified against official TOC" selected
set verification verified selected
add evidence source "Publisher" url "https://example.org/toc" selected
add evidence source "Second TOC" note "Volume 23 contents" chapter 275
show chapter 222 | show volume 24 | show unmapped | show conflicts
show modified | show automatic | show curated
validate | save | audit | undo | redo
on "Exact title" select chapter 222 | on "Exact title" set volume 24 selected

Ranges include existing numeric rows between both endpoints, including decimals.
Endpoints must exist; a range never creates chapters. No fuzzy title matching.
Explicit titles must identify exactly one edition/language row; otherwise open it first.
clear volume stores an explicit empty mapping. reset volume removes the override.
UNVERIFIED changes are drafts. REVIEWED / VERIFIED changes affect resolution.
Undo/redo are per-title and previewed. Apply saves immediately; save validates saved data.
Chapter numbers and title identity can be edited through explicit high-impact commands or their dedicated panels.
```

Commands are case-sensitive. Quote titles and notes with double quotes. An explicit title must resolve to exactly one stored title/edition/language. The console does not execute SQL, Python, shell commands, or natural-language instructions.

The console accepts multiple lines. Click **Preview Command** (or Ctrl+Enter) to preview one atomic transaction. Selection lines can precede edits in the same batch, and `validate` can be the last line. Apply commits the whole batch in one History entry; undo and redo operate on that whole entry. Show, explain, audit, save, and undo run separately from mutation batches. `set volume 24` uses the current selected rows.

Pending chapter edits are visible in the grid with `⟦PENDING⟧` markers; Automatic Volume stays unchanged. The preview log counts verification transitions and evidence records. Cancel restores committed cells without writing. Evidence attaches to an existing curated chapter-volume assertion or a volume assertion staged in the same batch. Add multiple sources with multiple lines; each is retained separately. `url` is optional when a named source has no URL, and `accessed "YYYY-MM-DD"` is optional (Apply date by default). Evidence stores provenance only, not source-page text.

Review Packets include a `guard database_uuid … audit … revision … database …` line for each title. Put that exact line first when pasting packet-derived edit commands. The DDK checks it during Preview and again inside the Apply transaction. A new audit, curated change, problem disposition, or title queue change makes an old guard stale. Export a fresh packet after such a change. The guard does not bypass normal Preview, identity, range, or catalog validation.

Additional exact commands:

```text
select chapters 1,3,5,10.5,12-16
set verification reviewed selected
set work verification verified
reset type selected
reset title chapter 10
reset source-note selected
add chapter 206
add chapters 206-207
remove curated chapter 206
remove curated chapters 206-207
renumber chapter 10.5 to 10.6
add volume 24
remove curated volume 24
set volume-title 24 "Exact title"
set volume-source-note 24 "Official TOC"
set work edition standard
set work language en
set work canonical-title "Exact title"
add alias "Exact alias"
remove alias "Exact alias"
set id anilist 12345
set id kitsu 67890
set id mangadex "00000000-0000-0000-0000-000000000000"
clear id mangadex
reset id mangadex
set expected chapters 207
set expected volumes 23
reset expected chapters
reset expected volumes
show aliases
show ids
show expected
show effective chapter 222
show provenance volume 24
explain chapter 222
explain volume 24
explain work
```

Creation and removal are restricted to curated records; they never change provider or reference snapshots. A created chapter is publication evidence even when no provider can acquire it. Range selection still requires existing endpoints. `reset` removes the override; `clear` stores an explicit empty value where supported.

Edits, undo, redo, and History Revert display a preview and require Apply. Cancel discards the proposal. A stale audit/revision invalidates an edit preview. Up/Down recalls in-session commands. Apply commits atomically and performs local validation; Re-run Audit performs fresh network resolution.

For example, open Chainsaw Man and paste:

```text
set volume 24 chapters 222-232
```

Review all proposed rows, then Apply. This is an example of command syntax, not a verified title-specific mapping.
