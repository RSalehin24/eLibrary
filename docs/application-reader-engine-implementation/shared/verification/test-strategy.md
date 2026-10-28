# Verification commands, scenarios, and evidence

This document defines implementation verification; [plan review](plan-review.md) records this documentation change's actual checks. Application tests and semantic/visual acceptance have not run merely because commands are listed here.

The [follow-up gap audit](gap-audit.md) adds lower-level requirement coverage, exact source/context/schedule/status contracts and persistent negative validator tests. Its checks are a prerequisite for the read-only F01/F02 entry work; they do not replace that pre-code baseline or the later application gates.

The latest [whole-package requirement verification](requirement-verification.md) also checks exact source wording/line and target-section references, all prose/ordered/service/milestone/route-area clauses, and fingerprints for the entire reviewed package. The current results supersede earlier mapping/test counts; runtime and visual acceptance remain separate.

## Existing commands and prerequisites

Use repository-provided commands and installed approved tooling. Before execution identify isolated DB/broker/Redis/storage and avoid active preview workers. Do not print environment files or credentials. The current full Docker verifier builds/tests `app/frontend`, so run current website checks separately. New reader/engine work must add and document their real independent commands before their gates close; do not pretend those commands already exist.

From `app/web` (documented in its README/package manifest):

```sh
npm run lint
npm test
npm run typecheck
PUBLIC_SITE_URL=https://library.example.test npm run build
```

Stop a conflicting development server before production build/type generation. Start the completed immutable production artifact using the documented `npm run start` with matching configuration before browser acceptance. Do not build new service-worker output while PWA tests run.

From the repository root, after the correct Python environment/settings/isolated services are available:

```sh
PYTHONPATH=app/backend .venv/bin/python app/backend/manage.py spectacular --urlconf config.schema_urls --format openapi-json --file docs/api/openapi.json --validate --fail-on-warn
PYTHONPATH=app/backend .venv/bin/python app/backend/manage.py check
PYTHONPATH=app/backend .venv/bin/python app/backend/manage.py makemigrations --check --dry-run
.venv/bin/python -m mypy --config-file mypy.ini
python3 tests/scripts/check-file-size-policy.py
python3 tests/scripts/check-architecture-policy.py
git diff --check
```

Schema generation is a mutation: run it as part of the relevant implementation change, then from `app/web` run `npm run generate:api`. Check that a second generation produces no diff. Never hand-edit `docs/api/openapi.json` or generated TypeScript. Run the same pipeline for the implemented private engine contract/schema after its tooling exists. Apply migrations on empty PostgreSQL and check active tables/constraints separately; `makemigrations --check` alone does not prove initialization.

Python lint/format uses installed Ruff from `app/backend/requirements-dev.txt`; run `.venv/bin/python -m ruff check` and `.venv/bin/python -m ruff format --check` with the changed Python paths. Run mypy's configured scope and ensure new/replaced service modules are included without weakening existing checks. Command modules/tools are verified against the installed runtime before use; unsupported flags are not invented to clear a failure.

Existing Docker backend test entrypoint is `tests/scripts/test-backend.sh`; it starts the local stack, so use only the explicitly identified test environment. Its `--` convention is described in `tests/README.md`. For isolated local verification use the configured environment's pytest runner and `tests/pytest.ini`, serializing processes that share a test database. Run changed domain tests first, then all non-live backend/tooling coverage before a milestone. Explicit live-source cases run separately with paced transport and current source evidence; excluding live cases must remain visible in the result.

Current browser command from the repository root, with a fresh private fixture and both servers available:

```sh
FOUNDATION_FIXTURE_PATH=/private/tmp/library-preview.json app/web/node_modules/.bin/playwright test --config tests/web/playwright.config.mjs --project=chromium
```

The path is an example private fixture, not a file created by these plans. Use `tests/web/run_isolated.py` and current guarded seed helpers as documented in `app/web/README.md`; fixture credentials stay outside the repository with restrictive permissions. Set `FOUNDATION_WEB_URL`, `FOUNDATION_API_URL`, and the documented canonical origin when required. Other real project names are `firefox`, `webkit`, `android`, and `ios`. Use the approved pinned Linux Firefox simulator when host launch is unavailable; do not skip Firefox silently.

Retained frontend/parity checks remain available through its package scripts and `tests/scripts/test-frontend-unit.sh`. The full `tests/scripts/verify.sh` can stop workers and reseed its Docker environment; never run it against a preview/acceptance environment assuming it is a read-only check.

## Coverage assignment

| Gate | Required checks |
| --- | --- |
| F01/F02 | Issue/feature/route/state inventory; task/contract/permission/failure mapping; plan consistency and baseline renders |
| W01–W03 | Fresh schema, removed fields/endpoints/grants, generated API, direct permissions, automatic source/import preparation, atomic files and metadata races |
| W04–W08 | Shared units plus every retained website route/state/language/width; realistic user/admin flows and visual acceptance |
| R01 | Independent build/start/proxy/assets/health, session/CSRF/logout/read-once/account isolation and deep links |
| R02/R03 | Actual commands/focus/gestures/fullscreen, reflow anchors, search/Notes exact targets, latest progress/conflicts/annotations |
| R04/R05 | Malicious archives/scripts/network/media, rich feature parity, local network silence, cache/update/privacy, all simulator profiles and visual acceptance |
| E01 | Service/DB/storage/queue isolation, private auth/version/replay/idempotency, outbox/inbox/receipts and independent start |
| E02/E03 | Reconciled entire catalog, frozen reference split, real model outputs/accuracy/resources/runtime projection |
| E04–E08 | Source fixtures/reference cases, ordered spine/HTML/evidence verification, artifacts/atomic activation, updates and injected lifecycle faults |
| REL01/REL02 | Empty initialization, complete integrated canaries, all applicable checks, reconciled evidence and user acceptance |

Regression tests must demonstrate an observed original failure and the corrected result. Use deterministic fixed source/EPUB/media fixtures, injected clocks/latency/faults and controlled transport. Production semantics cannot be proven by tests that mirror the same implementation. Real broker/DB/Redis/inference evidence is required at the specified gates. Separate Redis server instances are mandatory for engine Pub/Sub isolation, even when database numbers differ.

## Browser/state coverage

- Bengali and English, widths 320/390/820/1366/1920px, relevant portrait/landscape and 200% text. Use five supported simulator profiles; record any configuration-limited subset explicitly and add required routes to the selection rather than silently excluding them.
- Expand each route into applicable state packs from the website matrix and the full reader plan. Include dialogs/menus, not-found/error/offline boundaries, long text/credits, missing cover, delayed hydration, partial data, failed reads/writes, unknown outcome, conflict, expired permission and duplicate submission.
- Check keyboard/tab/real shortcut events, touch/gesture, focus containment/restoration, screen-reader names, contrast, reduced motion, no overflow/clipping/overlap, stable account actions, control heights/targets, card alignment and result/canvas geometry.
- Inspect rendered screenshots manually and finish task flows. Keep failing and accepted evidence; do not automatically replace reference screenshots or lower thresholds to accept a regression.
- Test production worker/cache behavior through the real offline proxy. General request-injection specs block service workers; PWA/local-reader specs explicitly allow them. Do not interpret a generic offline document as a successful chapter/API load.

## Evidence and stopping rules

Each record contains task/requirement/issue ID, code/build identifiers, timestamp/timezone, exact command, environment/schema/fixture/source/model versions, role/language/viewport/browser, expected/actual behavior, exit status, artifact/screenshot location and limitation. Screenshots, logs and credentials follow existing ignored artifact/private-fixture conventions; no secrets or private notes enter tracked docs.

Task status and source issue status follow the root plan. A failed/newly found case reopens the relevant gate. Report unique cases separately from repeated or overlapping runs. An external delivery or physical-device claim requires external/physical evidence; loopback mail and browser emulation do not establish it. Missing infrastructure/approval for a dependency is a concrete unverified prerequisite, not a passing test or reason to weaken acceptance.

For this documentation-only change, run plan link/path/requirement/route/task consistency checks, existing repository policies and whitespace checks. Application build/lint/type/backend/browser/model tests are intentionally not evidence of planning correctness and need not run until implementation changes them. Report that distinction explicitly.
