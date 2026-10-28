# Verification and continuation queue

These are recorded results, not tests rerun on 28 October. Infrastructure was
unavailable during handover preparation. Read the source/build freshness notes
before interpreting any result as current acceptance.

## Executed evidence

All artifact names below are relative to ignored `test-artifacts/foundation/`.
Transfer them privately if you need the original evidence on the new machine.

| Check | Actual result / artifact |
| --- | --- |
| Full non-live Python/backend/tooling/plan/performance gate | **1,974 passed; 13 live cases deselected**, warnings as errors; `implementation-backend-final.log` |
| Latest linked-entity focused backend gate | **47 passed**, including seven new cases; `implementation-linked-entities-backend.log` |
| Isolated browser-runner tools | **3 passed**, including pinned-container/private-mount regression |
| Website units | **149 passed**; `implementation-web-unit.log`; predates the final guidance/unit-assertion edit |
| Website lint | Passed; `implementation-web-lint.log`; predates the final contributor-selector/guidance edits |
| Website production build and strict types | Passed for preceding build; `implementation-web-build.log`; latest capability/selector changes need rebuild |
| Python types | **293 configured files passed**, including clean non-incremental run; `implementation-mypy-clean.log` |
| OpenAPI/client | Latest `can_edit` schema generation and client generation succeeded; repeat identity after that generation not yet checked |
| Fresh DB and migration drift | Passed before the latest non-schema capability change; `implementation-reference-migrations.log`, `implementation-migration-check.log` |
| Plans | 347 exact mappings; 25 acyclic tasks; 54 starting route obligations; 139 links; 18 evidence paths; 18 closed planning findings; 28 fingerprints; 30 validator tests previously passed |
| Chromium layout | **1,340 combinations, all eight families passed** after reader-header/Kindle fixes; `implementation-browser-06/` and full-run layout records |
| Full Chromium workflows | **51/59 specs passed; 249 journeys passed, 8 failed**; `implementation-chromium-full/summary.json` and per-spec `browser.log` |
| Firefox smoke | **4 login journeys passed** in approved pinned container; `implementation-firefox-smoke/` |
| Other profiles | Full current WebKit/Android/iOS/Firefox suites not executed for this revision |

Focused counts overlap broad runs; do not add them into a unique pass total.
The full Chromium run selected 59 specs before the new linked-entity spec was
added; current source contains 60 specs. Layout combinations are separate from
journey counts and are not evidence that every adverse state has been inspected.

Mypy without the backend Python path produced 50 dependency/import-context errors.
The documented environment (`PYTHONPATH=app/backend`) passed, also with
`--no-incremental`. Preserve the failed log, use the correct import environment,
and investigate any new failure rather than adding ignores or narrowing scope.

## Eight failures from the latest complete Chromium run

Every failure has its original screenshot/context/log under
`implementation-chromium-full/<spec-name-without-.mjs>/`. Do not discard them.

| Specification | Observed failure | Current status / next action |
| --- | --- | --- |
| `account.spec.mjs` | Password-change test requested hardcoded port 3000; connection refused | Test now creates the second context with configured `baseURL`; **not rerun** |
| `jobs.spec.mjs` | Expected retired upload-success text | Test now expects EPUB+HTML ready copy; **not rerun**; retain preparation/conflict assertions |
| `password-links.spec.mjs` | Required invitation confirmation showed uncertain outcome instead of TOTP setup link | Unresolved. Capture confirmation HTTP status/body safely and server logs; accumulated password-link quota is a hypothesis, not verified cause |
| `pwa.spec.mjs` | Unsaved editorial-update test waited for a field on a non-admin editor's denied book page | Test still uses scoped `editor`; update to an authorized administrator and verify current field label; retain real worker/update/draft/other-tab checks |
| `reader-bookmark-precision.spec.mjs` | Exact bookmark restoration test timed out | Unresolved; identify the blocked step and confirm passage restoration after size/viewport change; do not increase timeout as a substitute for diagnosis |
| `reader-language.spec.mjs` | Generated-source chapter paragraph width 262px; expected >320px in a 390px viewport | Unresolved reader style/injected-wrapper regression; preserve the width assertion and no-overflow check |
| `workspace-views.spec.mjs` | Admin login remained on `/login/` | Unresolved; inspect response/status and quotas with fresh reference API; do not disable login security |
| `workspaces.spec.mjs` | Deep-link login remained on login page | Unresolved; same investigation, plus safe encoded return-path handling |

Earlier `entity-directory` and account-menu failures were obsolete removed-feature
expectations; tests were updated to use `/contributors/` and assert no physical-book
menu. Their later full-run checks passed. Source primary-action count now matches
the four required actions. Responsive and overview assertions were updated and
passed later in the full run.

## Changes that still need new evidence

- Rebuild/restart latest source before testing `ManagedEntity.can_edit` and the
  bilingual read-only linked-entity page. Run the new linked-entity browser spec.
- Rerun relationship/homonym tests and layout after selected contributor labels
  and accessible action names gained catalog codes. Check saved/reloaded labels.
- Rerun units/lint/types/build after the final intake translation and component edits.
- Repeat schema/client generation and compare bytes after the latest schema change.
- Run remaining negative permissions, failures, keyboard/touch and bilingual visual
  checks for W08. A shared component pass does not close every route/state.

## Ordered restart work

1. Verify the transfer, read AGENTS.md and reverify planning fingerprints.
2. Start only isolated reference infrastructure and initialize an empty reference
   schema. Preserve user preview and original evidence.
3. Rebuild/restart latest API and immutable website with matching runtime origins.
4. Run focused specs for linked entities, relationships, account/jobs, password
   links, PWA, bookmark precision, reader language and workspace login. Use new
   artifact directories/fixtures. Diagnose true failures before the broad rerun.
5. Run the full Chromium suite, then full applicable Firefox/WebKit/Android/iOS
   suites sequentially. All five projects now select all specs. Record unique
   cases, failures, simulator limitations and evidence per role/language/viewport.
6. Run the current non-live backend/tools gate serially against its own DB, plus
   website checks, schema/migration/type/lint/policy gates. Keep broker/Redis test
   ownership separate; do not clear resources used by browser acceptance.
7. Inspect actual renders and complete realistic workflows. Update the issue/state
   register with new findings. Preserve failures alongside corrected evidence.
8. Present concrete website review evidence and record user visual/UX acceptance.
   Only then continue R01–R05, followed by engine E01–E08 and release tasks.

## Commands after loading the reference environment

From repository root; serialize suites that share databases, Redis or queues:

```sh
PYTHONPATH=app/backend .venv/bin/python -m pytest -c tests/pytest.ini --reuse-db -m 'not live' -W error -q --tb=short
PYTHONPATH=app/backend .venv/bin/python -m pytest -c tests/pytest.ini tests/tools/test_isolated_browser_runner.py -W error -q
PYTHONPATH=app/backend .venv/bin/python -m mypy --config-file mypy.ini --no-incremental
PYTHONPATH=app/backend .venv/bin/python app/backend/manage.py check
PYTHONPATH=app/backend .venv/bin/python app/backend/manage.py makemigrations --check --dry-run
.venv/bin/python docs/application-reader-engine-implementation/shared/verification/verify_plans.py
python3 tests/scripts/check-file-size-policy.py
python3 tests/scripts/check-architecture-policy.py
git diff --check
```

Run changed non-generated Python through Ruff check and format check, using
installed `.venv/bin/python -m ruff`. Include new files; do not hand-format generated
migrations. Use `app/web` scripts for website units, lint, types and production build.

Schema generation is an intentional generated-file mutation:

```sh
PYTHONPATH=app/backend .venv/bin/python app/backend/manage.py spectacular --urlconf config.schema_urls --format openapi-json --file docs/api/openapi.json --validate --fail-on-warn
```

Then `npm run generate:api` from `app/web`; compare hashes before/after a second
generation. Do not edit schema/client by hand or indiscriminately replace reviewed
plan fingerprints. The plan validator allows exactly the two W01 page removals;
missing retained or extra undeclared pages remain errors.

Full Chromium, new unused artifact directory:

```sh
.venv/bin/python tests/web/run_isolated.py --project chromium --artifacts test-artifacts/foundation/new-machine-chromium
```

Repeat sequentially with the other four project names and new artifact directories.
If a spec's global action affects a later run, identify/reset only the disposable
reference state with recorded ownership. Never weaken the fixture safety guard.

## Known limits and later work

Independent reader proxy/build/session integration, revisioned progress/command
registry, extracted local/offline shell and R05 acceptance remain future work.
Independent engine transport/data/storage, frozen full corpus, real local inference,
200/100 reference split, ordered-spine verifier, update fencing and final integrated
release remain future work. Existing export occurrence checks do not prove spine
order; ENG-03 is explicitly open for the engine milestone.

No live-source accuracy, physical-device behavior, actual external Kindle arrival,
new-machine capacity or production deployment has been established by this revision.
Previously recorded five development-only lint-chain audit highs and the compatible
ESLint exception are historical limitations; recheck rather than assume resolved.
Current transfer documentation does not certify dependency security on 28 October.

The in-app browser bootstrap previously failed with `missing field sandboxPolicy`.
Maintained Playwright specs and local screenshot inspection were used; no ad hoc
browser driver was introduced. A receiving agent should follow its available
browser skill and tools before choosing a fallback.

No current result establishes “no gaps will ever arise.” Close requirements with
specific evidence and keep unverified acceptance criteria visible.

## Handover documentation checks — 28 October

The five handover files' relative links resolve. Planning verification passed
again with 347 mappings, 25 acyclic tasks, 54 route obligations, **140 links**,
18 evidence paths, 18 closed planning findings and 28 unchanged fingerprints.
All 30 validator tests passed again. Original Markdown/PDF checksums match the
recorded values. File-size,
architecture and whitespace checks pass. These are documentation/source checks;
no application suite or new-machine startup was rerun for the handover.
