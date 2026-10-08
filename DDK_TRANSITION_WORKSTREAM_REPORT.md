# MangaAnkā DDK transition report

Task-local results, October 6, 2026. DDK remains **0.3.0**, SQLite schema **7**, Grammar **3**, Wikipedia parser **7**. Earlier repairs and unrelated worktree changes were treated as the baseline.

## A — SPY mixed uncollected tail

**No safe generic expansion was established. No production parser or freshness change was made.** The source preserves `Mission: 128–140.1` as opaque uncollected-range evidence. It does not independently enumerate 128 through 140 or explain the identity of 140.1.

The captured chapter-list source is page 70835375, revision 1375646933. Inspection of the [Graphic novel list documentation](https://en.wikipedia.org/wiki/Template:Graphic_novel_list/doc), page 15541726, revision 1336835261, found a formatted ChapterList field, rather than a canonical chapter-number expansion contract. The [chapter-list page](https://en.wikipedia.org/wiki/List_of_Spy_%C3%97_Family_chapters) supplies surrounding explicit compiled memberships, but not an independent integer enumeration of this tail. Public inspection evidence is saved under `build`, separately from catalog data.

| Question | Finding |
| --- | --- |
| Does the expression explicitly mean every integer followed by 140.1? | That is a plausible human interpretation, but the source/template does not establish it as a generic machine identity rule. |
| Are mixed endpoints semantically ambiguous? | Yes for canonical enumeration: decimal tokens may identify specials, splits or source-local numbering. A mathematical interval alone does not establish publication membership. |
| Does surrounding structure independently prove the integer members? | It establishes collected memberships through 127 and an uncollected section containing the raw expression; it does not list the tail members individually. |
| Can available provider chapters prove the intersection? | They prove acquisition availability, not structural authority. Using them to manufacture uncollected membership would cross the acquisition/structure boundary. |
| Can the integer subset be accepted while ignoring the decimal endpoint? | Not from the current evidence alone. It would still assume that the range enumerates a contiguous main-chapter namespace. |
| Can existing helpers implement this without floats? | Existing helpers already support bounded integer ranges and exact individual decimal identifiers. Technical implementability is not proof of the mixed expression's meaning. |
| Is an expansion safe across titles? | Not demonstrated. No title-specific or terminal-decimal production exception was added. |

Before and after this task, the mixed expression remains opaque, does not assign future Volume 18, and cannot make the acquired tail UNCOMPILED. Parser/cache version and source provenance remain unchanged. The supplied **Audit 38 revision 4** packet has 172 acquisition records, 148 logical units, **135 recognized canonical main chapters plus 13 provisional unmapped integers**, 135 mapped, 0 uncompiled, 13 unmapped and 17 final volumes. Its health is PASS / REVIEW / REVIEW / PARTIAL. Calling all 148 already-established canonical main identities would overstate the evidence.

Expected next live result, assuming unchanged source/provider evidence: those 13 tail integers remain unmapped; no forced PASS or promised count change. A future explicit individual source list, or independent trusted publication/serialization evidence establishing numbering, edition and tail membership, could support the existing freshness machinery. This task did not curate around uncertainty.

Files added for investigation only:

- Shared core: `C:\MangaNana-Dev\MangaNana-calibre\tests\test_mixed_uncollected_contract.py` — **5 tests**.
- DDK: `C:\MangaAnka DDK\tests\test_mixed_tail_investigation.py` — **3 tests**.

Controls cover integer expansion, mixed .1/.5 endpoints, reversed/malformed ranges, decimal starts, arbitrary decimals, nonnumeric identifiers, range bounds, collected/uncollected contexts, future-volume presence, released-boundary context, acquisition intersection, missing acquisition, internal gaps and immutable provenance. Numeric parsing was inspected for exact identifiers/bounded integer arithmetic; no floating-point expansion was introduced. The integration controls deliberately retain unmapped results when the source is opaque.

## B — Fractional residue forensics

**All 24 residue rows remain D: unresolved research on the supplied evidence.** B: exact data/curation is possible only after an independently demonstrated relationship. None is proven E: artifact or C: harmless acquisition noise; none proves A: a generic runtime capability defect. These research categories do not replace current application problem classes or make candidates nonblocking.

Evidence examined: `C:\Users\Jerry\Downloads\Spy x Spy packet.txt`, 1,785,111 bytes, SHA-256 `418cfd38982a16c5a34005a7d75a9609bd56dc33221d434f8b1bd0c705fe33ba`. It contains **Audit 38 revision 4**, selected MangaPill, with exact chapter URLs. It is an exported record, not an opened production database. No prior revision was reconstructed from memory.

All 24 descriptive provider titles are blank. Twenty-two have parent-derived fractional volume assignments; 139.2 and 140.5 are unmapped. This derivation is useful context but is not independent identity evidence. Four rows are currently split candidates: 58.1, 58.2, 67.1 and 67.2. The other twenty remain fractional candidates; the spelling of 62.2/62.3 alone does not establish a split.

The actual Wikipedia snapshot places Short Missions 7/8 in Volume 10, with none in Volume 9, and Short Missions 9/10 in Volume 12, with none in Volume 11. This is the source evidence used below, even where a synthetic fixture differs. Record order and proximity cannot safely choose among these supplementary identities.

| Identifier | Exact provider record ID | Effective volume / source | Classification | Supplementary candidates | Supporting evidence | Evidence against | Confidence / disposition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 23.6 | [4143-10023600](https://mangapill.com/chapters/4143-10023600/spy-x-family-chapter-23.6) | 4 / parent derivation | provider_fractional_candidate | Short Mission 1, Short Mission 2 | Order between 23 and 24; same-volume context only | Blank title; no exact MangaDex match or publication alias; parent-derived volume is not identity evidence | Insufficient to identify content; D: research; B only after exact evidence |
| 37.5 | [4143-10037500](https://mangapill.com/chapters/4143-10037500/spy-x-family-chapter-37.5) | 6 / parent derivation | provider_fractional_candidate | Short Mission 4 | Order between 37 and 38; same-volume context only | Blank title; no exact MangaDex match or publication alias; parent-derived volume is not identity evidence | Insufficient to identify content; D: research; B only after exact evidence |
| 44.5 | [4143-10044500](https://mangapill.com/chapters/4143-10044500/spy-x-family-chapter-44.5) | 7 / parent derivation | provider_fractional_candidate | Short Mission 5 | Order between 44 and 45; same-volume context only | Blank title; no exact MangaDex match or publication alias; parent-derived volume is not identity evidence | Insufficient to identify content; D: research; B only after exact evidence |
| 51.5 | [4143-10051500](https://mangapill.com/chapters/4143-10051500/spy-x-family-chapter-51.5) | 8 / parent derivation | provider_fractional_candidate | Short Mission 6 | Order between 51 and 52; same-volume context only | Blank title; no exact MangaDex match or publication alias; parent-derived volume is not identity evidence | Insufficient to identify content; D: research; B only after exact evidence |
| 53.5 | [4143-10053500](https://mangapill.com/chapters/4143-10053500/spy-x-family-chapter-53.5) | 8 / parent derivation | provider_fractional_candidate | Short Mission 6 | Order between 53 and 54; same-volume context only | Blank title; no exact MangaDex match or publication alias; parent-derived volume is not identity evidence | Insufficient to identify content; D: research; B only after exact evidence |
| 58.1 | [4143-10058100](https://mangapill.com/chapters/4143-10058100/spy-x-family-chapter-58.1) | 9 / parent derivation | provider_split_candidate | None in this volume | Order between 58 and 59; same-volume context only | Blank title; no exact MangaDex match or publication alias; parent-derived volume is not identity evidence | Insufficient to identify content; D: research; B only after exact evidence |
| 58.2 | [4143-10058200](https://mangapill.com/chapters/4143-10058200/spy-x-family-chapter-58.2) | 9 / parent derivation | provider_split_candidate | None in this volume | Order between 58 and 59; same-volume context only | Blank title; no exact MangaDex match or publication alias; parent-derived volume is not identity evidence | Insufficient to identify content; D: research; B only after exact evidence |
| 58.5 | [4143-10058500](https://mangapill.com/chapters/4143-10058500/spy-x-family-chapter-58.5) | 9 / parent derivation | provider_fractional_candidate | None in this volume | Order between 58 and 59; same-volume context only | Blank title; no exact MangaDex match or publication alias; parent-derived volume is not identity evidence | Insufficient to identify content; D: research; B only after exact evidence |
| 62.2 | [4143-10062200](https://mangapill.com/chapters/4143-10062200/spy-x-family-chapter-62.2) | 10 / parent derivation | provider_fractional_candidate | Short Mission 7, Short Mission 8 | Order between 62 and 63; same-volume context only | Blank title; no exact MangaDex match or publication alias; parent-derived volume is not identity evidence | Insufficient to identify content; D: research; B only after exact evidence |
| 62.3 | [4143-10062300](https://mangapill.com/chapters/4143-10062300/spy-x-family-chapter-62.3) | 10 / parent derivation | provider_fractional_candidate | Short Mission 7, Short Mission 8 | Order between 62 and 63; same-volume context only | Blank title; no exact MangaDex match or publication alias; parent-derived volume is not identity evidence | Insufficient to identify content; D: research; B only after exact evidence |
| 62.5 | [4143-10062500](https://mangapill.com/chapters/4143-10062500/spy-x-family-chapter-62.5) | 10 / parent derivation | provider_fractional_candidate | Short Mission 7, Short Mission 8 | Order between 62 and 63; same-volume context only | Blank title; no exact MangaDex match or publication alias; parent-derived volume is not identity evidence | Insufficient to identify content; D: research; B only after exact evidence |
| 66.5 | [4143-10066500](https://mangapill.com/chapters/4143-10066500/spy-x-family-chapter-66.5) | 10 / parent derivation | provider_fractional_candidate | Short Mission 7, Short Mission 8 | Order between 66 and 67; same-volume context only | Blank title; no exact MangaDex match or publication alias; parent-derived volume is not identity evidence | Insufficient to identify content; D: research; B only after exact evidence |
| 67.1 | [4143-10067100](https://mangapill.com/chapters/4143-10067100/spy-x-family-chapter-67.1) | 11 / parent derivation | provider_split_candidate | None in this volume | Order between 67 and 68; same-volume context only | Blank title; no exact MangaDex match or publication alias; parent-derived volume is not identity evidence | Insufficient to identify content; D: research; B only after exact evidence |
| 67.2 | [4143-10067200](https://mangapill.com/chapters/4143-10067200/spy-x-family-chapter-67.2) | 11 / parent derivation | provider_split_candidate | None in this volume | Order between 67 and 68; same-volume context only | Blank title; no exact MangaDex match or publication alias; parent-derived volume is not identity evidence | Insufficient to identify content; D: research; B only after exact evidence |
| 68.1 | [4143-10068100](https://mangapill.com/chapters/4143-10068100/spy-x-family-chapter-68.1) | 11 / parent derivation | provider_fractional_candidate | None in this volume | Order between 68 and 69; same-volume context only | Blank title; no exact MangaDex match or publication alias; parent-derived volume is not identity evidence | Insufficient to identify content; D: research; B only after exact evidence |
| 84.5 | [4143-10084500](https://mangapill.com/chapters/4143-10084500/spy-x-family-chapter-84.5) | 12 / parent derivation | provider_fractional_candidate | Short Mission 9, Short Mission 10 | Order between 84 and 85; same-volume context only | Blank title; no exact MangaDex match or publication alias; parent-derived volume is not identity evidence | Insufficient to identify content; D: research; B only after exact evidence |
| 90.5 | [4143-10090500](https://mangapill.com/chapters/4143-10090500/spy-x-family-chapter-90.5) | 13 / parent derivation | provider_fractional_candidate | Short Mission 11 | Order between 90 and 91; same-volume context only | Blank title; no exact MangaDex match or publication alias; parent-derived volume is not identity evidence | Insufficient to identify content; D: research; B only after exact evidence |
| 92.5 | [4143-10092500](https://mangapill.com/chapters/4143-10092500/spy-x-family-chapter-92.5) | 13 / parent derivation | provider_fractional_candidate | Short Mission 11 | Order between 92 and 93; same-volume context only | Blank title; no exact MangaDex match or publication alias; parent-derived volume is not identity evidence | Insufficient to identify content; D: research; B only after exact evidence |
| 99.5 | [4143-10099500](https://mangapill.com/chapters/4143-10099500/spy-x-family-chapter-99.5) | 14 / parent derivation | provider_fractional_candidate | Short Mission 12, Short Mission 13 | Order between 99 and 100; same-volume context only | Blank title; no exact MangaDex match or publication alias; parent-derived volume is not identity evidence | Insufficient to identify content; D: research; B only after exact evidence |
| 105.5 | [4143-10105500](https://mangapill.com/chapters/4143-10105500/spy-x-family-chapter-105.5) | 15 / parent derivation | provider_fractional_candidate | Short Mission 14 | Order between 105 and 106; same-volume context only | Blank title; no exact MangaDex match or publication alias; parent-derived volume is not identity evidence | Insufficient to identify content; D: research; B only after exact evidence |
| 108.5 | [4143-10108500](https://mangapill.com/chapters/4143-10108500/spy-x-family-chapter-108.5) | 15 / parent derivation | provider_fractional_candidate | Short Mission 14 | Order between 108 and 109; same-volume context only | Blank title; no exact MangaDex match or publication alias; parent-derived volume is not identity evidence | Insufficient to identify content; D: research; B only after exact evidence |
| 127.2 | [4143-10127200](https://mangapill.com/chapters/4143-10127200/spy-x-family-chapter-127.2) | 17 / parent derivation | provider_fractional_candidate | Short Mission 15, Short Mission 17, Short Mission 18 | Order between 127 and 128; same-volume context only | Blank title; no exact MangaDex match or publication alias; parent-derived volume is not identity evidence | Insufficient to identify content; D: research; B only after exact evidence |
| 139.2 | [4143-10139200](https://mangapill.com/chapters/4143-10139200/spy-x-family-chapter-139.2) | None / unmapped | provider_fractional_candidate | Short Mission 19 | Uncollected source-local supplementary context only | Blank title; no exact MangaDex match or publication alias; parent-derived volume is not identity evidence | Insufficient to identify content; D: research; B only after exact evidence |
| 140.5 | [4143-10140500](https://mangapill.com/chapters/4143-10140500/spy-x-family-chapter-140.5) | None / unmapped | provider_fractional_candidate | Short Mission 19 | Uncollected source-local supplementary context only | Blank title; no exact MangaDex match or publication alias; parent-derived volume is not identity evidence | Insufficient to identify content; D: research; B only after exact evidence |


Every supporting entry in that table is **context only**. The URLs identify provider records precisely; they do not establish their contents. “Candidates” means supplementary records in the same effective volume, not proposed aliases. Shared volume, nearest main chapter and chronological position cannot prove equality.

Additional evidence and limits:

- The exact MangaDex keys in this snapshot are 5.5, 8.5, 11.5, 15.5, 15.6, 17.5, 18.5, 23.5, 24.5, 27.5, 30.5, 112.1, 112.2, 114.5, 116.5, 118.5, 120.5, 123.1, 123.2 and 123.5. None equals a residue key. Different decimal spellings are not evidence of cross-source aliases.
- MangaDex typed special metadata reports complete, but its `special_records` list is empty here. There is no typed content relationship to use for these 24 rows.
- The 12 explicit reference keys missing from acquisition are 114.5, 118.5, 120.5, 123.1, 123.5, 15.5, 15.6, 18.5, 24.5, 27.5, 5.5 and 8.5. They remain acquisition-only findings, separate from the mixed-tail blocker.
- Other-provider inventories are summary records, not stable chapter/title/order snapshots. The packet cannot prove equivalence with another provider's content, chronology or numbering. Atsu grouping evidence for a different acquisition must not be invented for selected MangaPill.
- No applicable curated field/alias supplied an exact relationship. No reader content inspection or publisher TOC tying a particular provider URL to a named supplementary story is present.

Useful next evidence: an official TOC or story header tied to the exact provider record, corroborated cross-numbering evidence, work/edition/language identity, explicit volume membership and dated source provenance. Capture full other-provider chapter rows or typed MangaDex content metadata if those are to be compared. A pair of fractions could represent parts of one story, separate stories or another artifact; this packet cannot distinguish them.

If an exact relationship is later established, use the **existing Grammar 3** path in the exact work/edition/language context: freshly exported `guard database_uuid … audit … revision … database …`, exact `select chapter …`, justified `set type special selected`, `set volume … selected` only with explicit membership proof, `set title … selected`, `add evidence source … url … selected`, and `set verification reviewed selected` or verified when warranted. Preview the entire guarded batch, inspect changes, then explicitly Apply and re-audit. These are command forms, **not a ready-to-apply mapping for any current residue row**. Multiple provider parts may require stronger evidence before deciding which identity operation is appropriate. Never rewrite a stale guard or use renumbering merely to resemble Wikipedia.

No provider-shadow policy, special alias invention, nonblocking reclassification, provider runtime change or production curation was implemented.

## C — Startup/session restoration

**Implemented through the existing authoritative open path.** Previously an ordinary Qt launch opened the chooser every time. Now it reopens the last successfully opened database, restores a safe per-database Working Set selection and lands on **Catalog**. Arbitrary last-page restoration is not used. A future separately authorized Workflow page should become the predictable landing page.

Product files changed:

| File | Change |
| --- | --- |
| `C:\MangaAnka DDK\qt_app\app.py` | Creates existing QSettings before startup resolution; explicit `--database` takes precedence; ordinary launch attempts restoration; failure returns to the existing picker with a concise nonblocking explanation. |
| `C:\MangaAnka DDK\qt_app\session.py` | Validated runtime Working Set selection and explicit activation separation; successful open resets previous selection context. |
| `C:\MangaAnka DDK\qt_app\main_window.py` | Remembers successful open/switch/selection/save; restores per-database selection; starts on Catalog; preferences-write failure is nonblocking. |
| `C:\MangaAnka DDK\qt_app\preferences.py` — added | Stable path/DB UUID/Working Set UUID preferences and restoration helpers. |

Existing startup architecture remains QApplication → Session → normal validation/WriterLock/DB open → MainWindow. QSettings remains outside the manga catalog: normal `MangaAnka` / `DDK-Qt` preferences, or an explicitly supplied `--ui-settings` INI for tests. Only stable paths and UUIDs are saved. A normalized resolved-path hash keys each database's selection; its database UUID prevents applying a stale selection if another database replaces the file at the same path.

Restoration validates without implicit creation, then acquires the existing writer lock and performs the existing schema/open checks. Missing, inaccessible, unrelated, corrupted, incompatible or locked databases return to normal selection. No substitute database is chosen and no remembered missing file is created. Failed switches preserve the already-open successful session/preferences. Explicit `--database` keeps its existing error behavior and overrides remembered startup.

Database A → A3 and B → B7 are independent. Restored selection is runtime UI context, not a rewritten `database_meta` active-set decision. A deleted/malformed selection falls back to the existing backend active set if valid, otherwise empty. COMPLETE/ARCHIVED sets may be displayed without reopening them; existing mutation guards still apply. Human selection continues through normal `WorkingSets.set_active`. No connection or QObject is persisted.

Restoration adds no automatic audit, acceptance or curation. Ordinary validated open retains its **pre-existing** migration and interrupted-AUDITING recovery behavior; this feature does not disable those safety mechanisms. Byte-for-byte unchanged normal v7 disposable catalogs verify that session selection itself adds no catalog writes.

Tests/artifacts added or adjusted:

- `C:\MangaAnka DDK\tests\test_qt_session_restore.py` — **21** focused tests, including actual app startup paths with isolated settings, Unicode/spaces, A/B, protected/deleted sets, DB UUID replacement, locked DB, invalid files, malformed settings and settings-write failure.
- `C:\MangaAnka DDK\tests\test_qt_frontend.py` — one existing QSettings contract assertion updated to allow only stable per-database Working Set UUID preferences. It still rejects acceptance preference state; no other frontend behavior was changed.
- `C:\MangaAnka DDK\tests\smoke_packaged_transition.py` — frozen-code comparisons and disposable/offline packaged regressions.
- Task-scoped inspection/preparation/static scripts, logs, source baselines and disposable native smoke catalogs under `C:\MangaAnka DDK\build`; final report is this file.

Validation results:

| Check | Result |
| --- | --- |
| Final full DDK suite | **407 passed**, 230.193 seconds. |
| Focused shared-core protected suite | **341 passed**, 6.233 seconds; no full plugin suite run. |
| Session restoration | **21 passed**, 5.172 seconds in focused execution. |
| Mixed-tail investigation | **5 shared-core + 3 DDK passed**. |
| Qt sizes/scales | **9 passed**: 1120×720, 1440×900, 1920×1080 at 1.0, 1.25, 1.5; existing six pages. |
| Source/hash checks | Syntax/compile checks passed for all 9 changed/added Python source/test files; 117 protected product sources checked; only three existing Qt product modules changed, one new preferences module. |
| Final packaging and native startup | Rebuilt successfully with PyInstaller 6.20.0 / Python 3.10.6. **89 frozen-module tests passed**, 29.658 seconds; twelve embedded modules compare equal to final compiled source, no database payload, live shared-core loading retained. Native startup restored the disposable Unicode/spaces path and A3; second-writer startup showed the nonblocking chooser explanation without bypassing its lock. Normal GUI Close released the lock; reopening restored the same A3 and Catalog without a picker. A separate missing-path settings file showed the concise chooser explanation; Cancel exited normally, and no replacement file/lock sidecar was created. Both disposable catalogs remained byte-for-byte unchanged. |

The first full run had 405 tests and one failure in the old “no Working Set preference key” assertion, which contradicted the requested stable-ID restoration feature. That assertion was narrowed as described above; the final 407-test suite passed. This was not a catalog/schema failure.

The first sandboxed PyInstaller attempt failed its existing Tk guard because installed Tcl could not initialize. The existing EXE was not replaced by that failed attempt. The final retry used installed-runtime access and a separate build work directory; no spec/hook change or worktree cleanup was required.

Primary launcher: `C:\MangaAnka DDK\Launch_MangaAnka_DDK.bat`. Legacy fallback: `C:\MangaAnka DDK\Launch_MangaAnka_DDK_Legacy_Tk.bat`, unchanged. Final EXE: `C:\MangaAnka DDK\dist\MangaAnka-Database-Development-Kit.exe`. Size: 52,513,260 bytes; SHA-256 `42dd74bcfb9a3f6e00af91624d5bfeec36522c6e50edb2f85ed02b48a891b6ed`.

Spec, build helpers, Tcl/Tk inclusion, Poppler ICU filtering, font assets and launchers are unchanged in this task. Geist is not newly bundled; installed-font/fallback selection remains unchanged. The shared-core loader continues to use the current configured local plugin worktree, rather than shipping a divergent core snapshot.

Task-generated inspection/validation scripts are `build\inspect_wikipedia_template_contract.py`, `build\inspect_transition_packet.py`, `build\write_fractional_forensics.py`, `build\validate_transition_sources.py`, `build\prepare_transition_session_smoke.py`, `build\finish_transition_report.py` and `build\finalize_transition_native.py`. Their JSON/Markdown evidence, baselines, test/build logs, PyInstaller intermediate files and the two TEST catalogs in `build\transition-session-smoke` are validation artifacts. They are not packaged catalog data or a production configuration. The native tests always passed an explicit isolated `--ui-settings` file.

## D — Workflow UI architecture (design only)

**No Workflow page, navigation entry, backend state model or new lifecycle was implemented.** The mockup establishes useful information hierarchy; its sample counts, status labels and stage highlighting are not authoritative product state.

### Existing architecture and selection boundary

`qt_app/main_window.py` orchestrates six pages in a QStackedWidget: Catalog, Audit, Problems, Curate, History and Details. Pages reuse scope selectors, RecordTable/proxy filtering, InspectorPage splitters and the shared CommandDrawer. Session adapts authoritative backend services; AuditWorker performs long work off the GUI thread. Existing WriterLock and per-operation transaction ownership remain unchanged.

The eventual Workflow should be a seventh presentation/orchestration page using these services. Several MainWindow methods currently read **Catalog.table selection or Catalog.scope directly**: `selected_entries`, `force_selected_item` and `export_set`. Connecting a new Workflow button to those methods unchanged could act on a stale Catalog selection. First introduce a small stable-UUID scope/selection adapter in the shared orchestration layer. Do not duplicate acceptance, audit persistence, normalization, grammar or policy code inside the new page.

### Current actions and proposed placement

All paths below are in `C:\MangaAnka DDK`.

| Desired action | Existing action → authoritative backend | Reusable | Current location → proposed Workflow location | Risk/constraint |
| --- | --- | --- | --- | --- |
| New Working Set / next batch | `MainWindow.new_set` → `WorkingSets.create`; explicit activation | Yes | Working Set menu → batch header/New Batch | No new batch-size rule. Creation and running remain explicit operations. |
| Paste titles | `MainWindow.intake` → `WorkingSets.guard(membership=True)` / `add_requests` | Yes | Catalog/Audit intake → primary batch action | Existing standard/en/volume defaults, duplicate result counts and terminal-set guards. |
| Select Working Set | `activate_set` → `Session.activate_working_set` → `WorkingSets.set_active` | Yes | Header selector → same header | Busy guard; cancel stale command preview on context change. |
| Run Working Set | `run_working_set` → recovery / `run_candidates` → `start_audit` / `AuditWorker` | Yes | Catalog/Audit → primary run action | Exact membership IDs; normal current-code audit; retain per-item failures and pins. |
| Retry Errors | `retry_errors` → `WorkingSets.retry_errors` / worker | Yes | Catalog More/Audit → error action | Retry only eligible exact error memberships, no global purge. |
| Show error | `AuditWorker.failed` / `audit_failed`; item observations and refresh | Yes | Audit/Details → selected inspector and progress | A failed attempt is not a new current audit. |
| Export Review Packet | `export_set('packet', mode='pinned')` → `ddk_exports.working_set_packet` | Yes, scope adapter needed | Catalog More → primary handoff action | Pin/current mode must be explicit; current JSON body is saved with `.md` suffix. Prefer `.json` in future UI without inventing another format. |
| Other exports | Working Set titles/CSV/context, catalog CSV, Problems review packet/details CSV, curated patch exports | Yes | Specialist pages → secondary export menu | Label scope and pinned/current meaning; do not silently substitute one export. |
| Paste commands | Shared CommandDrawer + `CommandController.open/execute` | Yes, exact-work context needed | Bottom drawer/Curate → prominent handoff action | A guarded mutation batch targets one exact work/edition/language. A batch-level command box must make that context explicit. |
| Parse / guard | `ddk_commands.parse_batch`; existing CommandLogic/compile path; Catalog preview/apply validation | Yes | Command controller → same controller | No second parser, stale-guard rewriting or error suppression. |
| Preview Changes | Drawer preview → CommandController → compile/preview | Yes | Shared drawer → same drawer | Guarded edit batches preview without writing. Generic console actions retain their current distinct semantics. |
| Apply | CommandController.apply → `Catalog.apply` → refresh/post_curation | Yes | Drawer Apply → same explicit Apply | Recheck fingerprint/revisions; no automatic apply. |
| Re-Audit after changes | `post_curation` → QUEUED; immediate worker when idle or deferred set while busy | Yes | Existing orchestration → progress/next action | **Current Apply already schedules/runs re-audit.** Show queued/running; do not schedule a duplicate or pretend it always waits for manual Run. |
| Force Re-Audit Selected | `force_reaudit_selected` / candidate validation / human confirmation / `queue_force_audit` / worker force flag | Yes, selection adapter needed | Catalog More → secondary exact-title action | Preserve exact item UUID, old history, pin-on-success and transaction repair. |
| Accept Selected | `accept_selected` → `Acceptance.evaluate` / expected fingerprint / explicit confirm / accept | Yes, selection adapter needed | Catalog → selected-title action | Never infer eligibility from PASS or READY alone. |
| Accept Safe Titles | `accept_all_safe` → `bulk_preview` / guarded bulk accept | Yes | Catalog/Audit → batch acceptance action | Label **eligible candidates** count; READY count may include ineligible/stale candidates. Others remain unresolved. |
| Complete Working Set | `set_status('COMPLETE')` → `WorkingSets.set_status` | Yes | Working Set menu → completion action | Existing terminal-item and human approval requirements. |
| Archive / reopen | `set_status('ARCHIVED')`, `reopen_set`, `reopen_items` → WorkingSets | Yes | Working Set menu/Catalog More → secondary actions | Protected sets/items require explicit reopening; preserve decisions/history. |
| Switch database | `switch_database` → `Session.open` / normal validation / writer lock | Yes | Header database menu → same header | Busy guard; clear previews, deferred work and prior selection; restore only compatible per-DB context. |
| Inspect title | `Session.context` / `open_details` / `open_curate` | Yes | Catalog/Problems → selected-title inspector and links | Exact scope/item/pinned audit; never select another edition by display title alone. |

Command-controller nuance: the generic existing console also has commands such as `audit` whose execution starts validated work. A Workflow “Preview Changes” flow should expose guarded mutation batches with their existing preview semantics, rather than claim every generic console command is inert. Changing console behavior requires separate authorization.

### Authoritative state inventory

| Display | Existing authority | Presentation rule |
| --- | --- | --- |
| Total / accepted / ready / review / error / duplicate counts | `WorkingSets.items` processing_status and membership records | Also expose PENDING, QUEUED, AUDITING and REJECTED; mockup's five cards omit real states. Count memberships consistently. |
| Four health dimensions | Persisted audit health via `catalog_context` / Session.context | Show identity/publication/normalization/acquisition distinctly; retain exact labels. Aggregate Health is a presentation helper, not acceptance policy. |
| Catalog / Working Set / acceptance state | Catalog record, membership status and Acceptance evaluation | Distinct concepts; one conflated STATUS enum would be misleading. |
| Pin / revision / curation / acceptance | Exact membership pin, audit revision, catalog curation revision, existing acceptance fingerprint/state | Show pinned-vs-current and stale state explicitly. |
| Problems / affected identifiers | Existing problems, evidence/disposition helpers and `ddk_review` | Category count and affected-record count are different. Do not invent severity totals from mockup. |
| Chapters / mapped / unmapped / uncompiled / specials / volumes | Persisted publication/normalization result | Preserve canonical-main versus logical count and UNCOMPILED distinction; raw inventory stays diagnostic. |
| Provider | Persisted selected source and inventory provenance | No independent provider ranking in the UI. |
| Acceptance eligibility | `Acceptance.evaluate` or bulk_preview candidate fingerprints/blockers/warnings/needs_reaudit | Read-only evaluator; human acceptance remains explicit. |
| Next action | Existing problem class/next_action, pin state, needs_reaudit, membership/protection, runtime queued/busy state | Ordered presentation of existing decisions, not a second lifecycle model. |

Recommended Next Action precedence: show running/queued first; show protected-set/item reopen requirements before editing; ERROR → Retry; PENDING/QUEUED or evaluator needs_reaudit → normal run when allowed; unresolved REVIEW → existing problem_next_action (curation, research, code review, acquisition-only, blocked identity); eligible snapshot → explicit Accept; accepted/current → In Catalog. An accepted stale terminal item may require **Reopen Selected** before normal candidate selection can re-audit it. Duplicate/unlinked memberships need their existing intake explanation. Do not convert every acquisition PARTIAL or every REVIEW into one universal blocker; use existing evaluator policy.

### Mockup feasibility

Codes: A existing state/action; B small presentation helper; C genuine missing capability; D unsafe assumption to revise.

| Region | Class | Recommendation |
| --- | --- | --- |
| Workflow navigation entry | B | Future seventh page only after authorization. |
| Active Working Set header | A | Reuse global context selector/name/status. |
| Batch summary counts | A/B | Existing membership counts; add queued/pending/duplicates and evaluator eligibility as appropriate. |
| Workflow stage strip | D/B | Guidance/checklist only. External review completion and persisted stage advancement are not known. |
| Search/filter row | A/B | Reuse proxy/filter patterns; any aggregate health filter must remain presentation only. |
| Working Set table | A | Existing rows and exact item IDs, including unlinked/error rows. |
| Aggregate Health | B | Derive display from four persisted dimensions without replacing them. |
| Chapters / Volumes | A | Use final publication counts and explicit special/uncompiled semantics. |
| Status | D | Split or label membership, catalog and acceptance concepts. |
| Next Action | B | Ordered helper over existing evaluator/problem/runtime state. |
| Selected-title inspector | A | Scope/pin-aware context, exact identity and Details/Curate links. |
| Four health rows | A | Existing stored health and diagnostic links. |
| Problem summary | A/B | Existing categories; severity breakdown only if backed by current severity data. |
| Export Review Packet | A/B | Existing JSON packet, explicit scope/pin mode and `.json` file affordance. |
| Paste Fix Commands | A | Open shared drawer with exact-work context. |
| Re-Audit | A/D | Reuse runner and expose current automatic/deferred rerun behavior. |
| Export Fresh Packet | D/B | Export action exists; persisted freshness requires an actual export receipt. |
| Accept Safe Titles | A | Existing bulk evaluator and human confirmation; eligible count rather than READY total. |
| Review Handoff card | B | Explain the human cycle without asserting external review happened. |
| Command entry | A | Shared CommandDrawer, not a new parser/editor policy. |
| Preview | A | Existing guarded mutation preview. |
| Apply | A | Existing explicit guarded apply; show its rerun consequence. |
| Completion / next batch | A/B | Existing guarded completion plus create/intake; no fixed batch size. |

### Packet strategy and genuine gaps

Keep `mangaanka-ddk-working-set-review-v1` as the primary handoff. It already carries DB UUID, set, membership, pinned/current mode, audit records, holes and observations with publication evidence. The richer existing `ddk_review.review_packet` exposes exact guard/database revision, current curation, automatic/effective mapping, dispositions and re-audit differences with consistency checks. A future narrow extension should add these existing diagnostics/evaluator output to Working Set entries, including unlinked intake failures, rather than invent a second competing review format.

JSON should be the obvious production save format; current `.md` suffix for a JSON body is a presentation mismatch. Guard and snapshot fields must name the exact reviewed work/edition/language and audit revision. Current-vs-pinned export must remain explicit and must not advance pins.

Actual capability gaps: serialized other-provider inventories omit full stable chapter/title/order rows needed for certain forensic comparisons; the application has no persisted export receipt and cannot know external review completion. Multi-work atomic guarded mutation would also be a genuine additional capability if requested later, not something an aggregate command box can assume. None of these gaps was implemented here.

### Export freshness

`save_text` writes the selected file and shows feedback; clipboard copies are ephemeral. There is no persistent export event/receipt. Therefore a startup banner saying “packet stale” would currently fabricate knowledge of a prior export. The existing database revision string alone is also insufficient for every membership/pin/status change.

A future local per-database/per-set QSettings receipt could be saved **only after successful export**, containing timestamp/path/mode and a content/scope fingerprint. Derive that fingerprint from sorted exact membership IDs, audit pin/revisions, curation revisions, relevant evidence/dispositions, acceptance/current dependencies and export mode. Compare on demand; no receipt means **unknown**, not stale or fresh. Label its scope as a locally remembered export, not evidence that another person reviewed it. Reliable cross-machine export history would need a separately authorized backend registry/schema capability. No receipt or freshness flag was added in this task.

### Recommended page/navigation and geometry

Future landing page: Workflow, consistently. Keep all six specialist pages reachable. Workflow should show batch actions, a selectable membership table, selected-title health/problems/next-action inspector, and the shared collapsible command drawer. Default New Batch intake uses standard/en/volume and presents duplicate/count results; Create & Run coordinates existing explicit create/intake/run actions. Batches of 5–25+ require no new hard limit.

At 1920×1080 with 125% scaling, usable logical screen size is roughly 1536×864, before taskbar/window decorations. Bound the initial window to actual availableScreen rather than enlarging it to fit the mockup. Collapse the right inspector on narrower widths, wrap summary cards, stack actions, fold advanced filters and abbreviate the optional guide. Core actions must not require horizontal scrolling; optional diagnostic columns may retain visible horizontal scrollbars. Keep readable dark controls, selected-row/combobox contrast and explicit vertical scrollbars. Reuse existing theme/icon/font helpers. The command drawer should be expandable without permanently consuming the table's useful height.

Likely future files: `qt_app/pages/workflow.py`; optionally a pure `qt_app/workflow_presentation.py`; narrow shared orchestration/selection changes in `qt_app/main_window.py`; reuse/refine common page/table/drawer helpers. Extend `ddk_exports.py` only for a proven existing-packet diagnostic omission. Do not add a parallel workflow enum, acceptance evaluator, publication resolver or grammar.

Future test plan: exact UUID/scope targeting despite stale Catalog selection; unlinked/duplicate/error memberships; pin and failure preservation; eligible partial acceptance; stale approval/reopen rules; protected sets; stale guard rejection and preview-no-write; Apply auto/deferred rerun without duplication; packet pinned/current identity; successful export receipt and unknown-receipt cases; completion guards; per-database startup; all nine scale/window combinations, keyboard reachability, narrow inspector/filters/drawer behavior and Tk coexistence. Integration smokes should follow the complete human cycle against disposable catalogs with deterministic audit fixtures.

## Production safety and manual checks

- The protected production catalog was **never opened or mutated**. The supplied packet was read as a file only. Disposable DBs and isolated QSettings were used throughout automated validation.
- No automatic acceptance, live curation, new schema/Grammar/parser version, title-specific production hack or provider-shadow policy.
- No shared/plugin production source, search/ranking/provider, canonical-special, freshness, artifact-authority, transaction, acceptance or history behavior changed in this task. Only one shared-core test file was added.
- No Workflow UI was implemented. No commit, push, tag, release, version bump, reset, clean or package rename.

Short manual checklist (human-operated):

1. Launch the primary launcher, explicitly choose your intended catalog once if needed, select the intended Working Set, close normally, then relaunch. Confirm the same exact path/set and Catalog landing.
2. Switch between two **disposable** catalogs and verify independent set selection. If a remembered disposable file is moved, confirm startup explains failure and offers the chooser without recreating it.
3. View a COMPLETE/ARCHIVED set and confirm it was not reopened automatically. Any live acceptance or re-audit remains your explicit action.
4. If you re-audit SPY, compare the fresh packet rather than expecting this task to remove the mixed-tail/residue reviews. No uncertain mapping was promoted.

Known limits: current mixed range and fractional identities remain unresolved; external review/export freshness is not tracked; shared-core worktree remains a runtime dependency; restoration retains normal migration/interrupted-run recovery; no live network corpus rerun or production database inspection was performed. Native session checks exercised the actual Windows EXE; protected regressions used its embedded Python modules with deterministic disposable fixtures, rather than live provider/network audits. Scale factors were simulated through Qt; physical monitor DPI switching was not performed. Legacy Tk code/launcher were preserved but a separate native Tk smoke was not rerun for this Qt-only feature. A sandbox-only initial smoke process was terminated when it was not exposed on the interactive desktop; subsequent native sessions closed normally. Brief desktop-input interference interrupted the first close attempt; fresh observations and the observed Close button completed the check. Final tests left no DDK smoke window running.
