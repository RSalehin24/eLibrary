# Implementation handoff — 16 October 2026

## Latest checkpoint — administration and book creation

The user's latest direction is **one configured website for automated book
creation, plus manual uploads**. Provider names belong in configuration, not
runtime application code. The existing historical migration remains untouched.
Do not reintroduce other provider choices or remove manual entry/upload.

Implemented in this continuation:

- Login initially contains email/password only. The existing authenticated
  `otp_required` response reveals and focuses the security code. Invalid
  credentials do not reveal it; editing credentials clears the challenge;
  invalid codes and temporary failures preserve it. Existing six/eight-digit
  code support and backend checks remain in place.
- Native SVG branding, version-two PWA icons, fresh hashed installation
  previews, and responsive home/login/profile/header styling. Immutable old
  icon and preview files remain available. Account touch controls remain 44px.
- Administrator profiles now expose **পরিচালনায় যান**. Management has direct
  source-import/manual-entry/job shortcuts, visible source workflow steps, and
  current-section navigation. Existing permissions still enforce every entry.
- Automated processing accepts only `SOURCE_SITE_HOST` and its `www` alias.
  An unrelated fallback hostname invalidates configuration. The local preview
  now reads the actual source configuration from the existing ignored local
  environment file, rather than the test placeholder.
- Manual digital records expose EPUB upload in their editor. The new multipart
  versioned endpoint checks archive/manifest safety, a 24 MiB limit, scoped
  metadata access, current revision and unfinished source work. It preserves
  previous files, records an audit, clears review, and grants no ownership.
  The Next proxy permits 32 MiB requests, matching the production proxy ceiling.
  Existing persisted preparation jobs prepare uploaded resources for reading.
- Parallel setup exposed catalog identifier allocation races. Model saves and
  the existing code generators now share a transaction-scoped PostgreSQL lock.
  Four deterministic concurrency cases cover books/authors/categories/series;
  existing codes and their format remain unchanged.
- Local RabbitMQ startup exposed development-only transient queue declarations
  and a legacy Redis factory using an AMQP broker URL. Control queues are now
  durable and event queues exclusive in every environment. Redis state uses a
  Redis configuration independently of the task broker, retaining legacy Redis
  broker support. No deprecated broker feature was enabled.

Current verification:

- **32 Chromium, 32 WebKit, 32 Linux Firefox, 13 Android, 13 iPhone** focused
  journeys passed, including actual enabled TOTP login, invalid challenges,
  administrator/reader navigation, uploads and responsive layouts. Artifacts:
  `ui-{chromium,webkit,android,ios}-final.log` and `ui-firefox-rerun.log` in
  `test-artifacts/foundation/`. Firefox uses the already approved matching image.
- **293 catalog/source/security cases** passed with thread and pytest warnings
  treated as errors (`ui-backend-accepted.log`). The complete non-live audit
  passed **1,289**, with 13 live-network cases excluded
  (`ui-full-backend-final.log` / `.xml`). Its one existing Django URL-field
  deprecation warning remains; no check was weakened.
- **21 web helper tests**, web lint/type checking, final production standalone
  build (`ui-build-accepted.log`), mypy on **201 source files**, affected Python
  lint, migration consistency, file/architecture policies and whitespace pass.
- An actual **11 MiB EPUB** passed the local Next proxy, then completed its
  persisted RabbitMQ preparation job through the local processing worker.
  Reader readiness is recorded in `ui-upload-worker-accepted.json`.
- The user's original administrator credentials still sign in without an OTP
  field and open management/source/manual-entry controls. Accounts were not
  reset or enrolled in two-factor authentication. Final reviewed screenshots
  include `admin-controls-final.png`, `source-controls-final.png` and
  `profile-final-phone.png`.

The local preview is at `http://localhost:3000/`, with administration at
`/manage/`, source import at `/manage/sources/`, and manual entry at
`/manage/books/new/`. Preview RabbitMQ is the separate
`elibrary-preview-broker` Docker project, bound to localhost 5673/15673 with the
approved pinned image. Private runtime configuration/bootstrap and logs are
under ignored `test-artifacts/foundation/ui-*`; never dump their credentials.
API/worker/dispatcher use `ui-runtime.py`, which reads source settings from
`local/env/.env` and broker/Redis settings from private `ui-runtime.json`.
Delivery workers and schedulers remain stopped; no external email was sent.
At handoff, Next3000 is PID 37616, Django8000 PID 39372, processing worker
PID 41094, and dispatcher PID 41095. Inspect listeners/processes before any
restart. The worker answered its RabbitMQ control ping and API readiness returned
HTTP 200. Final runtime logs are `ui-{processing-worker,dispatcher}-final.log`.

The legacy engine integration tests use real Redis. Pause preview processing
while running that suite, or use a separate Redis server. Logical databases do
not isolate [Redis Pub/Sub channels](https://redis.io/docs/latest/develop/pubsub/#database--scoping).
A preview worker heartbeat contaminated the first full run's worker-capacity
assertion and an optional logical-database isolation probe; the clean full rerun
passed with preview processing paused. Never run two pytest processes against
the same automatically managed test database.
The capacity assertion also passed individually with preview processing paused
(`ui-engine-paused-preview.log`); the preview worker/dispatcher were restarted
afterward and remain running.

See `architecture/account-navigation.md`, `architecture/catalog-records.md` and
`architecture/source-processing.md`. Earlier simulator acceptance remains
historical evidence; physical resources and live source acceptance are outside
the user's simulator-only verification scope. No commits/pushes/deployment or
destructive cleanup were performed.

## Previous checkpoint — simulator acceptance

This section supersedes the historical checkpoints below. Continue the user's
full implementation/fix request without repeating already completed work.
No commit, push, production deployment, external email/account action, purchase,
destructive cleanup, or volume reset is authorized. No subagents were used.

Implemented since the entity checkpoint:

- Saved/recent/granted library feeds, revision-checked private paper-reading logs,
  public cross-edition browsing, and private normalized profile images. Generated
  and applied `catalog.0026_personal_reading`; API contracts/types regenerated.
  See `architecture/personal-reading.md`.
- Bengali title/contributor query intent and reviewed Romanized aliases; home
  Organization and collection ItemList JSON-LD match visible content.
- Every remaining application `exec(compile(...))` source loader was replaced
  with normal Python modules. Compatibility exports remain; tests patch actual
  consumers/definitions without removing assertions. Natural processing/seed
  boundaries keep all file-policy targets within 300 lines. See
  `architecture/legacy-imports.md`.
- CSRF rejection retry is limited to one explicit `403 csrf_failed` response,
  which Django rejects before a handler runs. Other/uncertain failures are not
  replayed. Sign-in/out share the mutation helper. A new browser regression
  verifies identical retry payloads.
- Cross-tab session response races, 320px paper forms, WebKit sandboxed reader
  observation, reading-position capture/resize, and dialog focus were fixed.
  Authored reader scripts remain disabled. Safari installation help was added.
- Real worker SIGKILL/lease recovery and duplicate-publication checks passed.
  Isolated HTTPS startup now waits for proxy readiness with a deadline; two
  deterministic regression tests cover startup and timeout.
- Capacity harness fixture/response diagnostics are sanitized; sessions, duration,
  chapter paths and expiry are validated. Public reads explicitly clear reader
  cookies, and reports filter metric fields. Fourteen dependency-free regressions
  cover these paths, both documented summary shapes, and unknown-format failure.
- The guarded k6 runner completed HTTPS simulations at 1, 5, and 20 virtual
  users. Ubuntu/Debian package-install simulations passed after selecting each
  distribution's own repository/key URL and validating OS metadata before apt.
  Accepted-install/standalone/reinstall journeys and browser lab timings were
  added. See `operations/simulator-acceptance.md` for the complete current scope.

Verification already passed:

- Complete non-live backend/tools audit: **1,247 passed**, 13 live source-network
  cases excluded, thread-exception warnings treated as errors. Artifact:
  `test-artifacts/foundation/full-backend-final.log` / `.xml`.
- The latest separate tools run passed **7**, including the two subsequently
  added HTTPS startup cases (`tools-final.log`).
- Capacity harness checks passed **14** with simulated runtime modules
  (`capacity-unit-final.log`), plus syntax and lint. API readiness and the local
  web home both returned HTTP 200 after restarting the development API.
- Latest simulator continuation: **19 tools tests**, **18 performance helper
  tests**, **12 focused installation browser checks**, **33 mail/search cases**,
  and **12 browser timing observations** passed. Three actual k6 HTTPS runs
  and both Linux installer simulations passed. The fresh web helper run passed
  **21**; TypeScript, ESLint and affected source/shell/policy checks also pass.
  Mypy was rerun successfully on all 199 configured source files. Fresh npm
  audits still report zero production and five development-only findings;
  the latest available Next lint patch also retains the unpatched chain.
  Artifacts and measurement limits are in `operations/simulator-acceptance.md`.
- Final clean matrix: **108 Chromium**, **108 WebKit**, **108 Firefox**;
  Android Pixel 7 and iPhone 13 profiles each passed **30** journeys. All use
  the final reader/Safari build and fresh per-project fixtures. Artifacts are
  `matrix-accepted-{chromium,webkit,firefox,android,ios}.log` and
  `matrix-accepted-results.json` under `test-artifacts/foundation/`.
- Progress failures now remain visible while new positions queue, with automatic
  saves paused until explicit recovery. Three focused Firefox repetitions and
  two unit regressions also passed. The catalog creation/status test checks its
  independent status page in a second tab, preserving rendered-content,
  mobile-width, and creator-only permission assertions without waiting for a
  streamed editor response to close.
- **21 web helper tests**, **154 retained frontend unit tests**, both production
  builds, strict TypeScript, ESLint, mypy on **199 configured source files**,
  affected Python lint/format, validated semantically unchanged OpenAPI,
  migration consistency, file-size/architecture policies, and diff whitespace.
- Production npm audit: **0** findings. Development audit: **5 high** findings
  in the lint chain remain unresolved, with no unsafe forced dependency change.
- Synthetic disposable PostgreSQL profile: 10,000 books, twenty samples per
  intent, four SQL queries/request, median 15.65–22.61 ms and p95 24.59–46.10 ms.
  EXPLAIN/BUFFERS JSON is in `test-artifacts/performance/discovery-profile.json`.
  This is not concurrent HTTPS capacity or production corpus relevance.
- Rebuilt Docker API/frontend/proxy passed current HTTPS/public/protected-byte,
  real RabbitMQ preparation, broker/cache failure, broker/API/frontend replacement,
  active preparation SIGKILL/normal lease recovery, one ready publication,
  duplicate replay, and separate-project backup/restore/progress/paused-job
  recovery. Logs: `deployment-platform-current.log`,
  `deployment-recovery-current.log`, `deployment-restore-current.log`,
  `deployment-help-confirm.log`, and the final reader build check
  `deployment-final-verified.log`. See `operations/local-platform-verification.md`.

Approvals persist: Playwright 1.64.0 and matching bundles; temporary ESLint
9.39.4 exception with all lint rules retained; development `types-reportlab` and
`types-qrcode`; approved base images; and Docker installation simulation.
The user's subsequent “do them?” authorizes the documented Grafana k6 2.3.0
image and local acceptance simulations. The user then explicitly required
**simulators only** because physical/staging resources are unavailable. The
pinned image is installed. Actual k6 HTTPS runs at 1, 5, and 20 virtual users
passed with zero failed checks; the 20-user run measured 55.19 requests/second,
public p95 154.17 ms and protected-reading p95 42.50 ms. It used a 47-record
fixture catalog and a shared 2-CPU VM; no production-capacity claim is implied.
Fourteen JS harness regressions, four browser-metric regressions, and twelve new
Python runner/installer checks pass. Ubuntu/Debian package-install simulations
passed with Docker 29.9.1 and Compose 5.6.0; only systemd startup was simulated. See
`operations/capacity-verification.md` for commands, scope, and the image pin.

Running infrastructure:

- Foundation PostgreSQL 55432 / Redis 56379 retain their original volumes.
- Development Django8000 PID 39372 and standalone Next3000 PID 37616 are running.
  Inspect with `lsof` before restarting. Next uses `ui-build-accepted.log`.
  Private logs remain
  under ignored `test-artifacts/foundation/`; never dump credentials/session URLs.
- Production test project `elibrary-platform-test-kjzj4dcz` and restore projects
  are stopped, with volumes retained. Private config/fixture remains in
  `test-artifacts/deployment/isolated-yxc_0c_9/`. No external SMTP was configured.
- Linux Firefox uses the approved matching Playwright Noble image and
  `tests/web/container-browser.mjs`. Do not run it beside a full Docker stack on
  this 2-CPU/2-GiB VM. Mount the repo read-only, test-artifacts read/write.
- A full browser run consumes its fixture. Restart Django to reset disposable
  LocMem login quotas and seed a NEW private fixture immediately before each
  full run. Never seed another fixture while a full run is active: Overview
  assertions depend on that fixture being the newest failure set. Preserve
  existing database/media files; no resets. Include SMTP readiness settings
  from the historical infrastructure section; keep delivery workers stopped.

The requested implementation and simulator verification are complete locally,
including the final Docker reader build, measured HTTPS load, and Linux package
installation. The isolated application and restore stacks are stopped with all
volumes retained. Five development-only lint dependency findings remain
unresolved because the publisher has no patched release; no check was weakened.

Physical installations, external mailbox/Kindle acceptance, production editorial
judgment, field Web Vitals, and separate-machine capacity are outside the user's
current simulator-only scope. Do not claim those real-world criteria passed.
The simulator report records the evidence and limits without marking the original
physical acceptance criteria complete.

## Historical checkpoints

Continuation checkpoint after entity and book relationship administration.
Continue the accepted Bengali library plan; **the full plan is not complete**.
Read root `AGENTS.md`, preserve all existing tracked/untracked edits, and do not
restart implementation or repeat completed discovery.

## Scope and authorization

Implement the accepted six-phase Next.js/Django/PostgreSQL/Celery/RabbitMQ/Redis
plan, with Bengali public discovery, reader and admin workspaces, responsive PWA,
SEO, portable deployment, and measured capacity. The user wants implementation
continued until complete. No commits, pushes, destructive cleanup, production
deployment, external emails/account actions, or purchases are authorized.
No subagents are authorized. New dependencies still require explicit approval.

Approved dependencies are installed in `.venv`, `app/web/node_modules`, and the
retained frontend. The user explicitly approved isolated local downloads/builds
and tests of Python 3.12.15, Node 22.23.3, Nginx 1.30.6, and RabbitMQ 4.3.6 images.
Their digests are pinned in `deploy/compose/platform.yml` and Dockerfiles.
Current Playwright/browser upgrades and an ESLint support exception remain
unapproved; see `docs/architecture/verification-tooling.md`.

## Completed and verified checkpoint

Core delivered work includes public Bengali SSR discovery/search/entity pages,
reviewed editorial metadata, SEO/sitemaps/slug history, scoped permissions,
transaction-safe read-once launches, prepared protected EPUB resources, reader
progress/appearance/bookmarks/highlights/notes, profile/password/TOTP/session
invalidation, Kindle requests, invitations/reset links, access administration,
source inspection/discovery/processing, explicit bulk outcomes, persisted jobs,
source automations, admin overview, responsive layouts, and PWA offline/update
handling. Detailed architecture documentation is in `docs/architecture/`.

This session additionally completed:

- Shared source request pacing, protected Nginx byte delivery, production settings,
  shared Redis quotas, health checks, and production exclusion of legacy routes
  and legacy engine signal listeners.
- Container images, fresh migrations and static publication, configurable HTTPS
  origin/ports, graceful scheduler/dispatcher termination, Docker DNS refresh in
  Nginx, stable RabbitMQ hostname, compatible durable control/exclusive event queues.
- Actual isolated HTTPS integration, live confirmed dispatch/preparation, duplicate
  delivery, broker/cache outages, broker/API/frontend replacement, stale-attempt
  recovery, and a separate-project database/media/runtime backup/restore drill.
- Digital/paper-book record creation, immutable UUID request replay/status,
  revision-checked edition/language/publisher/decimal price/binding/compilation
  fields, no ownership assignment, current-actor editorial authority checks,
  and a fix preserving editorial save confirmation on server refresh.

Earlier verification **before the entity/relationship continuation below**:

- 701 selected PostgreSQL tests passed (77 files), including 26 new catalog cases.
- All 93 Chromium browser journeys passed with a fresh fixture and restarted
  disposable development API. Existing Playwright 1.53/Chromium 138 was used.
- 18 Node tests; mypy on 181 source files; strict TypeScript; ESLint; local and
  Docker Next.js production builds; OpenAPI validation; migration consistency;
  Ruff on affected modules; architecture policy; `git diff --check` passed.
- Full legacy suite is not passing: earlier 243 passes/40 failures need audit;
  three failures reproduced on unchanged HEAD. File-size policy still reports
  18 pre-existing violations; no exemptions or checks were weakened.

See `docs/operations/local-platform-verification.md`,
`docs/operations/platform-deployment.md`, and
`docs/architecture/catalog-records.md` for tested behavior and limitations.

## Completed continuation — entity and relationship administration

The previously unfinished backend now has tested responsive Bengali management
screens at `/manage/entities/`, kind-specific lists, creation, and UUID detail
pages. Kinds: contributors, categories, series, collections. Creation requires
global metadata authority; contributor/category grants manage only the exact
granted entity. Entity metadata reuses the book editor's text/SEO fields.

Creation replay now verifies the audit target UUID. Normalized-name checks and
kind locks cover both creation and renames, including collections. Creation and
updates take kind locks before entity row locks, including legacy UUID collisions.
Lists fetch only displayed fields. Collection detail includes ordered book IDs
and labels in two queries, with no deferred reverse-FK queries. Invalid selection rolls back
all metadata/order/audit changes. Review, publication, withdrawal, and slug
history are covered. Collections accept up to 100 unique selected books.

`/manage/books/<slug>/relationships/` and its versioned API manage contributor
roles, categories, ordered series, and explicit edition grouping. Global metadata
authority is required because these relationships also determine scoped access.
Changes snapshot the old relationships and reset review. Creating a group changes
and snapshots both editions; moving/detaching affects only the edited book.
Commands serialize before taking book locks, including reciprocal edition links.
Public cross-edition browsing is still outstanding.

Remote selectors use bounded, debounced, cancelled searches; selections survive
search changes. Entity creation invalidates cached reference results. Forms keep
drafts on validation/conflict, retain uncertain creation UUIDs, block uncertain
repeated writes, and participate in the PWA update guard. API types regenerated;
mypy coverage expanded to 189 files. No dependency added.

The full browser run also exposed old Overview ordering: PostgreSQL sorted null
completion times ahead of newer failures. It now orders by completion time with
update-time fallback, with a regression test. New relationship browser tests use
their own entities so they cannot change the existing scoped editor fixture.

Verification at this continuation:

- 706 foundation PostgreSQL tests passed in 75 files, including 62 new cases
  for entities, relationships, grouping, and Overview failure ordering.
- All 101 Chromium journeys passed with a fresh fixture and restarted local API,
  including eight new entity/relationship journeys and cached-reference refresh.
- 18 Node tests; mypy on 189 source files; strict TypeScript; ESLint; Next.js
  production build; OpenAPI validation; migration consistency; affected Ruff and
  formatting; architecture policy; `git diff --check` passed.
- 320-pixel/200%-text entity and relationship screenshots were inspected.
- Current Docker application images were not rebuilt for this continuation;
  the isolated deployment results above apply to the earlier checkpoint.
- Full legacy-suite failures and the same 18 file-size violations remain open.

See `docs/architecture/catalog-entities.md` for contracts, authority, grouping,
and regression coverage. Tests are in `test_managed_entities.py`,
`test_managed_collections.py`, `test_entity_authority.py`,
`test_entity_concurrency.py`, `test_book_relationships.py`, and the Overview suite.
Browser additions are `entities.spec.mjs` and `book-relationships.spec.mjs`.

## Running/local infrastructure

Existing foundation project: `local/compose/docker-compose.yml` plus
`local/compose/platform-test.yml`, project `elibrary-foundation`.
PostgreSQL localhost 55432 (`bangla_library`), Redis 56379. Never reset its volumes.

Backend test prefix:

```sh
PYTHONPATH=app/backend DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55432/bangla_library CELERY_BROKER_URL=redis://127.0.0.1:56379/0
```

Production test project `elibrary-platform-test-kjzj4dcz` has its private env and
fixture in ignored `test-artifacts/deployment/isolated-yxc_0c_9/`. Never print the
env contents/expanded Compose configuration or private fixture values. It binds
18080/18443; test origin `https://library.example.test:18443`.
Production test services stopped successfully (session 40546, exit 0).
Restore projects are stopped and volumes retained. No data was deleted.
The Colima VM has only 2 CPUs/2 GiB RAM/no swap. Run one full test stack at a time.

Local Django port 8000 runs current code with `--noreload` (PID 39942). Next
standalone port 3000 runs the verified entity/relationship build (PID 37136).
Private server logs are in ignored `test-artifacts/foundation/` files. A separate
local protected-proxy test also has
Django 8001 and rootless Nginx 8082; inspect processes before restarting.
Stop servers with output filtered to exit metadata: Django buffers can contain
reader-session URLs. Do not print credentials or reader tokens.

For every complete browser run, restart development Django to reset its disposable
LocMem login quota and generate a **fresh** fixture with `tests/web/seed_preview.py`.
Include `SOURCE_SITE_HOST=source.example.test` when seeding/running Django.
The UI suite also needs local SMTP readiness settings: use
`EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST=127.0.0.1`,
`EMAIL_PORT=1025`, `EMAIL_USE_TLS=false`, and synthetic
`ACCOUNT_INVITE_FROM_EMAIL=library@example.test` / `DEFAULT_FROM_EMAIL=library@example.test`.
Keep workers stopped for this UI-only run; requests queue work without sending mail.
Omitting SMTP configuration disables Kindle requests and fails those journeys.
The seed guard rejects production/non-55432 databases; do not weaken it.
Set `FOUNDATION_FIXTURE_PATH` to a new private file and
`FOUNDATION_CANONICAL_ORIGIN=https://library.example.test` for browser tests.
Full fixtures are consumed by the tests; never reuse one for another full run.

## Remaining accepted work

Public cross-edition browsing; saved/recent/granted library views; remaining
physical-book reader workflows; profile images;
legacy source-exec facade removal and failing legacy/policy checks; Bengali search
corpus/query intent/editorial launch content/SEO and performance acceptance;
supported Firefox/WebKit tooling, actual Android/iOS installation and PWA checks;
fresh Ubuntu/Debian host verification; active-worker interruption scenarios;
actual external/device delivery; and isolated k6 capacity tests with documented
separate load-generation hardware. No capacity or actual-device acceptance is
established. Do not mark the full plan complete or invent a completion percentage.

## Active continuation — personal reading and verification (16 October)

The user subsequently requested full implementation and issue fixing, then
repeatedly asked to continue. Continue working; this is an active checkpoint.
Do not stop at the previous entity increment.

New implementation: saved/recent/granted library feeds, private paper reading
logs, published cross-edition links/full list, and private normalized profile
images. `catalog.0026_personal_reading` was generated/applied. Contracts/types
were regenerated. See `architecture/personal-reading.md` and new tests in
`tests/backend/catalog_management/test_personal_library_views.py`,
`test_physical_reading.py`, `test_public_editions.py`,
`tests/backend/auth/test_profile_images.py`, and
`tests/web/e2e/personal-library.spec.mjs`.

The user explicitly approved Playwright 1.64.0/browser bundles, the temporary
ESLint 9.39.4 exception with all rules retained, and `types-reportlab` /
`types-qrcode` development stubs. These are installed and pinned. The user also
requested Docker installation simulation for unavailable external/device test
resources. Actual physical-device installation and external mail delivery must
not be represented as simulated proof. A pending async approval request for the
pinned Grafana k6 2.3.0 image has not been answered at this checkpoint.

Retained audit: a complete non-live run passed **1,234 tests** (13 live cases
explicitly deselected) in `full-backend-audit-4.log`. It exposed Redis observer
shutdown warnings; the fixture now stops and joins before closing. All **84
engine tests pass with thread-exception warnings treated as errors**. The old
source scraper, normalization, and submission loaders use explicit imports;
retry/failure/regeneration helpers were separated without removing assertions.
All **180 ingestion tests passed** after the last extraction. Full suite needs
rerunning after final changes. Mypy passes all **199 configured source files**,
with no error suppression. Ruff, architecture and 300-line size policies pass.
All **154 retained frontend unit tests** passed. Keep all pre-existing edits.

Search now combines title and contributor terms and reviewed Romanized aliases;
31 corpus/discovery/pagination cases passed. Ten of these are new synthetic
corpus cases. Home Organization and collection ItemList structured data were
added with browser assertions, not yet in a passing full matrix.

Browser findings and current work:
- Playwright's Firefox fails on macOS 27 before launching (upstream issue 42768).
  The matching Ubuntu Noble image was downloaded with the user's Docker/bundle
  authorization: `mcr.microsoft.com/playwright:v1.64.0-noble` digest
  `sha256:06a9939e57531807f8d5fd76ce44b53165ffb7d7501d87ab10e285c20b1e971f`.
  `tests/web/container-browser.mjs` forwards container loopback 3000/8000 to host
  services, preserving trusted host/origin headers. Mount repo read-only and
  ignored test-artifacts read/write; `/private/tmp` is not shared with Colima.
- General browser tests block service workers so injected network failures are
  intercepted consistently; PWA and reader specs explicitly allow workers and
  exercise the actual worker. Status assertions now identify their expected
  message instead of assuming the entire page has only one status region.
- Account switching had a real in-flight session race. Focus now cancels the old
  session read before refetching; server-rendered private layouts use an account
  snapshot guard. All three focused account-isolation tests passed, including
  the new first-response timing regression.
- Chromium full run passed 105/106 before the latest fixes. Password-link reset
  passed independently with a fresh fixture, but the full run needs confirming.
- Latest WebKit full run: **104/107 passed**. Remaining failures were reset mock
  timing, immediate update saving zero progress, and resize position. Fixes now
  in source: wait for the actual write, synchronous capture before flush,
  parent-realm position/selection observation for script-disabled WebKit frames,
  resize sampling guard, and explicit dialog opener focus restoration. Reader
  scripts stay disabled. Need rebuild and rerun focused/full checks.
- The latest Linux Firefox full run passed 90/106 before shared status/timing,
  container port-8000 forwarding, and reader-CSP assertion fixes. Run again with
  a fresh fixture; do not reuse consumed password/session/source fixtures.

Current build `reader-flush-build.log` is running. Previous standalone PID 65801
was stopped for it. Restart from `app/web` with HTTPS PUBLIC_SITE_URL and
HOSTNAME=127.0.0.1 PORT=3000 when complete. Current Django8000 is PID 65781 with
SMTP readiness configuration from above. Restart it for each full browser run
(to reset disposable LocMem login quotas). Workers remain stopped for UI tests.
Private fixture `/private/tmp/elibrary-webkit-final-20261016-h.json` is consumed.
Fresh, unused fixture `test-artifacts/foundation/firefox-final-fixture.json` was
created but not yet run. Protect fixture contents. Use separate browser output
paths per run, since Playwright clears its output directory.

A real worker SIGKILL integration scenario is implemented but unverified:
`tests/deployment/interruption_fixture.py` creates 100 substantial EPUB chapters;
`verify_active_worker_interruption` waits for actual preparation, kills/restarts
only the isolated test worker, waits for normal lease recovery, and verifies
one prepared publication and duplicate suppression. `compose_client.py` copies
this new script; `job_probe.py` exposes the guarded fixture action and stage.
Run after rebuilding isolated API/frontend images. The production test project
is still stopped with all volumes retained. Existing isolated directory remains
`test-artifacts/deployment/isolated-yxc_0c_9/`; never print its environment.

Still required: finalize all browser checks and fresh Docker simulator build/
recovery checks; measured search plans and local capacity harness/results;
update architecture/operations docs to match actual evidence. Full product and
external/device/capacity acceptance remains incomplete. No commit or push.

Latest checkpoint correction: the three focused WebKit failures are now fixed
and passed together (`webkit-last-fixes.log`). Before flushing progress, the hook
captures the actual chapter position; observation skips resize geometry changes,
and closing the reader dialog explicitly restores opener focus. The last build
`reader-flush-build.log` passed and standalone is running again (inspect port
3000 for PID). Linux Firefox full rerun `firefox-final-b.log` is now running via
Docker with the previously-unused `firefox-final-fixture.json` and separate
`firefox-final-browser` output. Do not change/rebuild the standalone while it runs.
The next unused Chromium fixture is `/private/tmp/elibrary-chromium-final-20261016-i.json`.

`tests/performance/test_discovery_profile.py` is running a guarded pytest test DB
profile with 10,000 synthetic books, 20 samples for each of three intents, and
EXPLAIN ANALYZE/BUFFERS JSON. Report target is ignored
`test-artifacts/performance/discovery-profile.json`. Its first attempt failed
because the catalog-code length was guessed; corrected to the existing
`catalog_code_from_int` generator and now rerunning. Do not cite results until
this run passes. It leaves no persistent corpus in the development database.
