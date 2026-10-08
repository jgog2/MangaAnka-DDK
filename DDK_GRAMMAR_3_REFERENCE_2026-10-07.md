# MangaAnkā DDK command reference — Grammar 3

Checked against the current local parser/controller/catalog on October 7, 2026. Grammar version is 3 (`ddk_review.py`). This is the **in-application command console**, not PowerShell, CMD, SQL, Python or a natural-language interface. No product code or grammar was changed to create this reference.

## General syntax

- Commands/keywords are case-sensitive. Quote titles, notes and other multiword strings with double quotes.
- One command per line. Blank lines are ignored. `|` in older help means alternatives, not a literal command separator. Do not paste Markdown fences, comments or placeholder values into the console.
- Commands normally target the open work. Prefix an individual command with `on "Exact title"` to resolve an exact stored title. It must identify exactly one title/edition/language record; there is no fuzzy title selection.
- An edit batch previews one atomic transaction. Review the changes, then click **Apply**. A batch creates one History entry. Cancel discards the proposal.
- Selection and edit lines can share a batch. `validate` may appear last. Run inspection, save, audit, undo and redo separately from mutation batches. Multi-work batches are not supported.
- Apply saves immediately. `save` validates saved data. `audit` invokes the existing audit action; **Force Re-Audit Selected** is a separate UI action, not a new console verb.

## Revision guard

Use the exact `review_guard.command` from a fresh packet as the first line of packet-derived mutations:

```text
guard database_uuid <UUID> audit <AUDIT_ID> revision <AUDIT_REVISION> database <DATABASE_REVISION>
```

Angle-bracket values are placeholders, not executable commands. The database revision token has the shape `a<number>-e<number>-d<number>-w<number>`. The guard needs a mutation after it and is checked during Preview and again during Apply. New audits, curation, relevant disposition/queue changes can stale it, including a mutation on another work. Export fresh; do not reuse a disposable guard or fabricate a production token.

## Selection and scopes

```text
select chapter 222
select chapters 222-232
select chapters 1,3,5,10.5,12-16
select volume 24
select selected
select all
select unmapped
select conflicts
select modified
select missing-title
select automatic
select curated
clear selection
```

Numbers are non-negative decimals. Chapter lists use commas without spaces. Ranges are ascending, include existing decimal-numbered rows between their endpoints, and require existing endpoints. Selection never creates chapters. `modified` and `curated` select rows with curated fields; `automatic` selects rows without curated fields.

For chapter-field edits and evidence, the permitted target scopes are:

```text
selected
chapter 222
chapters 222-232
chapters 1,3,10.5
```

Select a volume or filtered group first, then edit `selected`; `set volume 24 all` is not an edit scope.

## Chapter-field edits

```text
set volume 24
set volume 24 selected
set volume 24 chapter 222
set volume 24 chapters 222-232
clear volume selected
reset volume selected
set title "Exact chapter title" chapter 222
clear title selected
reset title selected
set type special selected
reset type selected
set source-note "Verified against official TOC" selected
clear source-note selected
reset source-note selected
```

`set`, `clear` and `reset` chapter-field edits default to the current selection if scope is omitted. Explicit chapter/list/range scopes are supported as above. `clear` stores an explicit empty value; `reset` removes the override and restores the automatic value.

Supported type values:

```text
chapter
bonus
extra
omake
special
prologue
epilogue
```

Type cannot be cleared. There is **no `set type uncompiled`**, provider-artifact classification command, completion-boundary command or automatic supplementary-binding command. `special` curation does not itself prove acquisition identity or invent an alias.

## Verification

```text
set verification unverified selected
set verification reviewed selected
set verification verified selected
set work verification unverified
set work verification reviewed
set work verification verified
```

The chapter verification command uses `selected`; to target a chapter, select it first. It changes existing curated fields or chapter fields staged earlier in the same batch. Work verification operates on existing curated work fields; set/apply a work field before verifying it if none exists.

UNVERIFIED values are drafts. REVIEWED/VERIFIED exact-compatible values affect effective resolution. Verification is not acceptance and does not override identity/consistency validation.

## Evidence

```text
add evidence source "Publisher" url "https://example.org/toc" selected
add evidence source "Publisher" note "Official volume contents" chapter 222
add evidence source "Publisher" url "https://example.org/toc" note "Contents entry" accessed "2026-10-07" chapters 222-232
```

Syntax: `add evidence source "NAME"` followed by optional `url "URL"`, `note "NOTE"`, `accessed "YYYY-MM-DD"` attributes, then an explicit chapter/chapters/selected scope. Attributes can be reordered, each at most once. A named source is required. Access date defaults to Apply date.

Evidence attaches to the chapter's curated **volume assertion**, which must exist or be staged in the same batch. Multiple evidence lines retain separate sources. Evidence stores provenance, not copied source-page text. Book pages, guidebook labels and provider numbering are not automatically interpreted as chapter identity.

## Curated records and renumbering

```text
add chapter 206
add chapters 206-207
remove curated chapter 206
remove curated chapters 206-207
renumber chapter 10.5 to 10.6
add volume 24
remove curated volume 24
set volume-title 24 "Exact volume title"
set volume-source-note 24 "Official TOC"
```

Single chapter/volume identifiers may be decimals. Plural creation/removal requires an integer range; ascending endpoints and `end - start <= 500`. Removal is restricted to curated-created records. Creation does not overwrite existing source/reference records or fabricate downloadable pages/URLs. Renumbering requires an unambiguous existing source identity and an unused target identity; original provider/reference snapshots remain preserved.

## Work identity, aliases, external IDs and expectations

```text
set work canonical-title "Exact title"
set work canonical-work-id "Exact canonical identifier"
set work publication-context "Exact publication context"
set work edition standard
set work language en
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
```

Edition values: `standard`, `official_color`, `fan_color`, `omnibus`, `deluxe`, `bunkobon`, `kanzenban`. Language must be an exact supported-form code: two or three lowercase letters, optionally a hyphenated alphanumeric suffix.

ID source names are normalized to lowercase and must start with a letter, followed by letters/digits/underscore/hyphen. AniList/Kitsu IDs must be numeric; MangaDex IDs must be UUIDs. Other exact source names are parsed but still subject to catalog validation. `clear id` removes that ID from the curated value; `reset id` restores its automatic value where present. Alias removal targets curated aliases.

Expected counts are non-negative integers and do not create chapter identities, prove completion or assign membership. Work identity edits are high impact and remain subject to exact compatibility/conflict checks.

## Inspection and separate actions

```text
show chapter 222
show chapters 222-232
show volume 24
show selected
show all
show unmapped
show conflicts
show modified
show missing-title
show automatic
show curated
show aliases
show ids
show expected
show effective chapter 222
show effective volume 24
show effective work
show provenance chapter 222
show provenance volume 24
show provenance work
explain chapter 222
explain volume 24
explain work
validate
save
audit
undo
redo
```

Undo/redo are per-work and previewed; Apply commits the proposal. History Revert is also a previewed UI operation. Inspection scopes must be exact and unambiguous.

## Explicit title prefix

```text
on "Exact stored title" select chapter 222
on "Exact stored title" set volume 24 selected
```

This is exact stored-title resolution, not a title search. If multiple editions/languages match, open the intended work rather than guessing.

## Illustrative correction body

This is a syntax example, not evidence that a real chapter belongs to this volume. Prepend a fresh real guard for packet-derived curation; do not substitute an old guard from chat.

```text
select chapter 222
set volume 24 selected
set source-note "Verified against publisher volume contents" selected
set verification reviewed selected
add evidence source "Publisher" url "https://example.org/official-volume" note "Chapter listed in volume contents" selected
validate
```

Preview, inspect the exact proposed changes, then Apply. Export fresh after a mutation before constructing another packet-derived correction.

## Local sources

- `C:\MangaAnka DDK\ddk_commands.py` — parser, scopes and exact-title resolution.
- `C:\MangaAnka DDK\ddk_command_controller.py` — compilation, verification, evidence and record rules.
- `C:\MangaAnka DDK\ddk_catalog.py` — accepted types/verification values and persistence validation.
- `C:\MangaAnka DDK\ddk_review.py` — Grammar 3 declaration and packet guard generation.
- `C:\MangaAnka DDK\DDK_COMMANDS.md` — existing shorter application documentation.

Parser acceptance alone does not guarantee a command is valid for a specific work/current selection. Preview and catalog validation remain authoritative. Never use this reference as permission for automatic production mutation.
