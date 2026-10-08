# Workflow Next Action repair

This pass repairs read-only action presentation after the reported BATCH 004 production run. DDK remains 0.3.0, schema 7, Grammar 3. No live catalog is opened by development or validation.

## Root cause and evidence

Workflow's unlinked intake path loaded the latest persisted observation, then called `problem_policy()` on each raw hole code. That policy classifies provider fractional/split candidates as CODE / CODE_REVIEW_REQUIRED for normal audit problems. Problems already treated unlinked REVIEW observations as IDENTITY / RESEARCH_REQUIRED because there was no trusted linked work or publication audit. Workflow therefore manufactured code-review actions from raw candidate codes, then its existing code-over-research priority selected “Code review.”

Disposable schema-7 observations with the exact reported Dr. STONE, Sakamoto Days, and The Promised Neverland code sets reproduced this mismatch before repair: Problems showed research for every row while Workflow showed code review. The names occur only in test fixtures, never in runtime rules.

There was also a linked projection defect: `catalog_context()`, Qt Problems, and the initial review-packet issue projection recomputed class/action from the code instead of preserving saved `audit_holes.problem_class` and `audit_holes.next_action`. A disposable linked fractional candidate saved as IDENTITY / RESEARCH_REQUIRED reproduced that defect too. The acceptance evaluator already honored these fields correctly.

The supplied `problems.csv` contains the linked My Hero Academia, Haikyu!! and Blue Lock controls, including actual CODE_REVIEW_REQUIRED and research/acquisition actions. It does not contain the three reported intake targets. No target's live database record was inspected, and the fixtures are deterministic reproductions, not reconstructed live audit data.

## Authority and precedence

Linked problem projections now use the persisted `audit_holes.next_action` and `problem_class`, matching the existing evaluator. The existing `problem_policy()` remains the fallback for legacy null/empty fields. It was not modified. Disposition handling, evidence-backed command suggestions, packet freshness handling and audit persistence are retained.

Both Qt pages now share the existing unresolved-intake presentation: use explicit saved observation hole `next_action`/`problem_class` when available; otherwise retain the established IDENTITY / RESEARCH_REQUIRED intake review presentation. A raw fractional/split code does not replace this authority. No lifecycle state, backend classifier, or second review policy is introduced.

The existing presentation precedence for unresolved action sets is unchanged:

1. BLOCKED_IDENTITY → Identity review
2. CODE_REVIEW_REQUIRED → Code review
3. RESEARCH_REQUIRED → Research required
4. CURATION_READY → Open Curate
5. AUTO_RESOLVABLE → Run audit
6. ACQUISITION_ONLY → Acquisition only
7. UNKNOWN → Inspect evidence

Runtime AUDITING/QUEUED, protected sets, terminal reopen, errors/duplicates, and stale/pending re-audit instructions retain precedence. A current eligible title is presented as “Accept eligible title” using the existing evaluator, including REVIEW memberships with only advisory findings; accepted/current remains “In Catalog.” The evaluator and actual acceptance guards were not changed.

## Exact files

Product files changed:

- `C:\MangaAnka DDK\ddk_review.py`: shared read-only saved-field projection; initial packet issue projection uses it.
- `C:\MangaAnka DDK\ddk_exports.py`: pinned catalog context preserves saved class/action.
- `C:\MangaAnka DDK\qt_app\workflow_presentation.py`: shared unresolved-intake projection, requested acquisition label, evaluator eligibility presentation.
- `C:\MangaAnka DDK\qt_app\pages\workflow.py`: removes raw-code reclassification of intake observations.
- `C:\MangaAnka DDK\qt_app\pages\problems.py`: uses saved linked fields and the same intake projection.

Validation files changed/added:

- `C:\MangaAnka DDK\tests\test_workflow.py`: existing acquisition-label expectation updated.
- `C:\MangaAnka DDK\tests\test_workflow_actions.py`: added 20 focused tests.
- `C:\MangaAnka DDK\tests\smoke_packaged_workflow.py`: includes the new tests and verifies both serializer modules in the EXE, totaling 23 embedded source comparisons.
- `C:\MangaAnka DDK\tests\prepare_next_action_native.py`: added guarded, task-local disposable native fixtures and isolated settings.
- `C:\MangaAnka DDK\DDK_WORKFLOW_NEXT_ACTION_VALIDATION.md`: this report.

The generated EXE and task-local logs/baseline/native fixtures under `build\next-action-*` are validation artifacts. No plugin file, launcher, spec, build hook, font, version, schema or grammar file changed.

## Regression coverage

The 20 new tests cover research/code alone; research with acquisition; code with research in both orders; acquisition only; identity/unknown/code class with authoritative research; artifact counts/codes without actions; evaluator eligibility with no findings or acquisition advisory; runtime override; identity blocking priority; three reported intake code sets; explicit saved observation actions; saved linked research across Workflow/Problems/context/JSON-packet/CSV; code controls; pinned actions versus a newer global audit with existing freshness priority; legacy null fallback; and ignored problem exclusion. Projection reads are verified not to change the disposable catalog bytes.

Existing Workflow tests retain accepted/current, queued/auditing, protected/reopen, exact targeting, scope/pin/race guards, receipts, command workflows and partial acceptance coverage.

Source validation passed:

| Check | Result |
| --- | --- |
| New focused action regressions | **20 passed**, 9.886s (`build/next-action-focused-final.log`). |
| Workflow, action, review/serialization, Working Set/recovery, v7 acceptance lifecycle, Qt frontend regressions | **191 passed**, 124.041s (`build/next-action-regressions-final.log`). |
| Full DDK suite on final source | **494 passed**, 372.866s (`build/next-action-full-ddk-final.log`). |
| Window/scale smokes | **9 passed**: 1120×720, 1440×900, 1920×1080 at 1.0, 1.25 and 1.5, all seven pages (`build/next-action-scale-*-final.log`). |
| Static checks | `py_compile` passed for all five product files and four edited/added validation scripts. |
| Protected source hashes | 249 checked; exactly the five listed product files changed (`build/next-action-source-check.json`). |

The earlier full run passed 493 tests before adding the evaluator/advisory case. The final full suite above includes that case and the final eligibility presentation. Before-fix fixtures failed on the three reported intake labels and the saved linked research label. A pinned-versus-newer-audit fixture initially expected research despite the evaluator's existing `needs_reaudit` result; its assertion was corrected to retain “Run Working Set” while verifying that the pinned research actions remain loaded.

## Build and packaged validation

Final EXE: `C:\MangaAnka DDK\dist\MangaAnka-Database-Development-Kit.exe`.

Size: **52,533,046 bytes**. SHA-256: `c245795515893ae2984f598187d05893c2f5697dc6f1de36f680e20b4f106be6`.

Rebuilt after the final 494-test source suite, using Python 3.10.6 / PyInstaller 6.20.0 and the unchanged spec. Build completed successfully (`build/next-action-pyinstaller.log`). The existing Tcl/Tk packaging guard, live shared-core dependency, exclusions and DLL filtering are retained. No database is embedded.

Primary launcher remains `C:\MangaAnka DDK\Launch_MangaAnka_DDK.bat`; legacy fallback remains `C:\MangaAnka DDK\Launch_MangaAnka_DDK_Legacy_Tk.bat`. Neither was edited. Fonts and visual layout remain unchanged.

**176 packaged tests passed** against actual embedded application modules: 89 protected checks (29.149s) plus 87 Workflow/action checks (63.263s). All **23 embedded module comparisons passed**, including all five changed product modules and both serializers (`build/next-action-packaged.log`). This verifies that the EXE contains the final fixes, not an older build.

## Native Windows smoke

Using the Computer Use skill against the rebuilt EXE and only `build/next-action-native/Next Action disposable.db` with isolated `ui.ini`:

- TEST catalog and the exact disposable Working Set restored; six memberships, two eligible, four REVIEW, zero errors.
- Workflow displayed **Research required** for all three observed-pattern intake fixtures. Each selection's inspector agreed.
- Exact-item Problems navigation displayed four Dr. STONE rows, four Sakamoto Days rows and three The Promised Neverland rows, all **IDENTITY / RESEARCH_REQUIRED**, including fractional/split candidates.
- Linked code control retained **Code review**. Both the clean eligible control and eligible acquisition-advisory control retained **Accept eligible title**.
- Selection remained readable and scrollbars remained visible. No native audit, curation, acceptance or catalog mutation was performed.
- Test window closed normally; no DDK smoke process/window remained. Read-only checks confirmed schema **7**, SQLite integrity **ok**, three works, three audits, six memberships and three observations.
- Catalog SHA-256 before/after was identical: `78d3fa5a1c00a6386e7436e1a43cd950abd9e169e8d00bc4100bbeb2625ab66e`.

Results are recorded in `build/next-action-native/results.json`. Initial sandboxed launches did not expose a Computer Use target; only the task-owned smoke processes were stopped, and the successful visible native check ran outside the sandbox. No user instance was terminated. A read-only post-smoke count probe initially used the wrong observation-table name; it was corrected to the existing `working_set_observations` table. Neither harness issue required a product change.

## Safety and limits

The protected `C:\Users\Jerry\Documents\MangaAnka-Database-Development-Kit\mangaanka_catalog.db` was never opened or mutated. Only the user-named CSV was read. Every test/native catalog and settings file is disposable. No failed live intake record or audit pin was modified.

A task-local hash baseline covers 249 existing DDK/plugin Python, launcher and spec files. Exactly the five product files above changed. Publication/reference/provider/search/canonical identity/normalization/health derivation, database transactions, acceptance/curation policy, schema 7 and Grammar 3 are unchanged. No database migration or repair is performed. No commit, push, tag, release, reset, clean or version bump.

The exact live target records remain uninspected; their reported intake presentation is reproduced deterministically. This change corrects presentation and serialization authority, not the underlying unresolved research/publication findings. Native validation uses synthetic observations and linked controls; no provider network audit is needed.

## Manual production check

1. Launch the rebuilt EXE normally and confirm the intended catalog and BATCH 004.
2. Use Options → Refresh; inspect Dr. STONE, Sakamoto Days and The Promised Neverland. Where their authoritative actions remain research-only, Next Action should read “Research required.” A re-audit is not needed just to refresh this presentation.
3. Compare their Problems rows; check Haikyu!!/My Hero Academia still show code review when CODE_REVIEW_REQUIRED is present, Blue Lock remains research with acquisition advisory, and eligible titles still show “Accept eligible title.”
4. Do not accept or change pins merely to test labels. Any normal re-audit/acceptance remains an explicit operator action.
