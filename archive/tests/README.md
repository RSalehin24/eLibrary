# Test Suite

The root `tests/` folder keeps all automated coverage organized by execution layer:

- `tests/backend/`: Django, ingestion, access, and catalog tests executed with `pytest`
- `tests/pytest.ini`: shared pytest configuration for backend runs inside and outside Docker
- `tests/frontend/unit/`: frontend unit coverage executed with `node --test`
- `tests/frontend/e2e/`: Playwright browser stories executed against the real Dockerized local application
- `tests/frontend/playwright.config.js`: shared Playwright config and live auth/bootstrap setup

All repo-facing helpers under `tests/scripts/` support `-h` or `--help` for usage details. Use `--` before passthrough flags when you want to forward options such as `-k` or `--workers` to the underlying test runner.

## Coverage Map

### Backend Coverage

| Feature Area | Coverage Layer | Main Location |
| --- | --- | --- |
| Authentication and session behavior | `pytest` | `tests/backend/auth/` |
| Access grants, reader access, and permission logic | `pytest` | `tests/backend/access/` |
| Catalog metadata and manual-book workflows | `pytest` | `tests/backend/catalog_management/` |
| Ingestion pipeline, curation, queue logic, processing activity summaries, and processing-state regressions | `pytest` | `tests/backend/ingestion/` |
| Shared/common behavior and legacy pipeline compatibility | `pytest` | `tests/backend/test_common.py`, `tests/backend/test_legacy_pipeline.py` |

### Frontend Unit Coverage

| Feature Area | Coverage Layer | Main Location |
| --- | --- | --- |
| Processing activity payload normalization and polling rules | `node --test` | `tests/frontend/unit/activityTracker.test.js` |
| Request text formatting and job-filter helpers | `node --test` | `tests/frontend/unit/requestHelpers.test.js` |

### Live Browser Coverage

| User Story | Coverage Layer | Main Location |
| --- | --- | --- |
| Sign in and search the live catalog | Playwright against Dockerized app | `tests/frontend/e2e/auth-pages.spec.js` |
| Public login and reset request flows | Playwright against Dockerized app | `tests/frontend/e2e/auth-public-login-and-reset-request.spec.js` |
| Reset and password validation flows | Playwright against Dockerized app | `tests/frontend/e2e/auth-public-reset-and-password-validation.spec.js` |
| Forced TOTP setup gate redirect | Playwright against Dockerized app | `tests/frontend/e2e/auth-public-forced-totp-setup.spec.js` |
| Create password from invite link with TOTP guidance | Playwright against Dockerized app | `tests/frontend/e2e/auth-public-create-password-totp.spec.js` |
| Expired create-password link handling | Playwright against Dockerized app | `tests/frontend/e2e/auth-public-expired-create-password.spec.js` |
| Edit managed user without losing filters | Playwright against Dockerized app | `tests/frontend/e2e/access-page.spec.js` |
| Create scoped book access rule | Playwright against Dockerized app | `tests/frontend/e2e/access-page.spec.js` |
| Mocked invitations and setup mail resend | Playwright with mocked API routes | `tests/frontend/e2e/access-page-mocked-invitations.spec.js` |
| Mocked validation and pagination | Playwright with mocked API routes | `tests/frontend/e2e/access-page-mocked-validation-and-pagination.spec.js` |
| Mocked permissions | Playwright with mocked API routes | `tests/frontend/e2e/access-page-mocked-permissions.spec.js` |
| Remove bookmark while saving metadata edits | Playwright against Dockerized app | `tests/frontend/e2e/book-detail-page.spec.js` |
| EPUB actions with HTML preview locked | Playwright against Dockerized app | `tests/frontend/e2e/book-detail-page.spec.js` |
| Category/series/writer-filtered library results | Playwright against Dockerized app | `tests/frontend/e2e/catalog-pages.spec.js` |
| Search seeded owned books | Playwright against Dockerized app | `tests/frontend/e2e/catalog-pages.spec.js` |
| Catalog book table mocked flows | Playwright with mocked API routes | `tests/frontend/e2e/catalog-book-tables-mocked.spec.js` |
| Reuse source URL and launch reader/download | Playwright against Dockerized app | `tests/frontend/e2e/create-books.spec.js` |
| Create manual book and find it again | Playwright against Dockerized app | `tests/frontend/e2e/manual-books.spec.js` |
| Search live processing requests | Playwright against Dockerized app | `tests/frontend/e2e/processing-pages-create-card-refreshes.spec.js` |
| Processing header spinner idle/active state | Playwright against Dockerized app | `tests/frontend/e2e/processing-pages-create-card-refreshes.spec.js` |
| Catalog state matrix | Playwright against Dockerized app | `tests/frontend/e2e/processing-pages-catalog-state-matrix.spec.js` |
| Catalog loading and skeletons | Playwright against Dockerized app | `tests/frontend/e2e/processing-pages-catalog-loading-and-skeletons.spec.js` |
| Catalog sync and record selection | Playwright against Dockerized app | `tests/frontend/e2e/processing-pages-catalog-sync-and-record-selection.spec.js` |
| Catalog automation flow | Playwright against Dockerized app | `tests/frontend/e2e/processing-pages-catalog-automation-flow.spec.js` |
| Live catalog runtime | Playwright against Dockerized app | `tests/frontend/e2e/processing-pages-live-catalog-runtime.spec.js` |
| Live incomplete runtime | Playwright against Dockerized app | `tests/frontend/e2e/processing-pages-live-incomplete-runtime.spec.js` |
| Live duplicate resolution | Playwright against Dockerized app | `tests/frontend/e2e/processing-pages-live-duplicate-resolution.spec.js` |
| Live created lifecycle | Playwright against Dockerized app | `tests/frontend/e2e/processing-pages-live-created-lifecycle.spec.js` |
| On-hold and incomplete actions | Playwright against Dockerized app | `tests/frontend/e2e/processing-pages-on-hold-and-incomplete-actions.spec.js` |
| Create and on-hold actions | Playwright against Dockerized app | `tests/frontend/e2e/processing-pages-create-and-on-hold-actions.spec.js` |
| Notifications and isolation | Playwright against Dockerized app | `tests/frontend/e2e/processing-pages-notifications-and-isolation.spec.js` |
| Create card state | Playwright against Dockerized app | `tests/frontend/e2e/processing-pages-create-card-state.spec.js` |
| Responsive layout: navigation and library | Playwright against Dockerized app | `tests/frontend/e2e/responsive-layout-navigation-and-library.spec.js` |
| Responsive layout: property and access | Playwright against Dockerized app | `tests/frontend/e2e/responsive-layout-property-and-access.spec.js` |
| Responsive layout: reader | Playwright against Dockerized app | `tests/frontend/e2e/responsive-layout-reader.spec.js` |
| Responsive layout: manual and profile | Playwright against Dockerized app | `tests/frontend/e2e/responsive-layout-manual-and-profile.spec.js` |
| Responsive layout: processing | Playwright against Dockerized app | `tests/frontend/e2e/responsive-layout-processing.spec.js` |
| Page loaders mocked | Playwright with mocked API routes | `tests/frontend/e2e/page-loaders-mocked.spec.js` |
| Profile page mocked | Playwright with mocked API routes | `tests/frontend/e2e/profile-page-mocked.spec.js` |
| Home filter | Playwright against Dockerized app | `tests/frontend/e2e/home-filter.spec.js` |
| Library page live | Playwright against Dockerized app | `tests/frontend/e2e/library-page-live.spec.js` |

### Runtime Data Strategy

- Live browser tests use the real local Docker stack started by `local/scripts/dev.sh up`.
- Deterministic browser data is reset by `tests/scripts/seed-e2e-data.sh`.
- Seeded records are intentionally prefixed with `E2E ` or use the `@e2e.local` domain so they are easy to identify and clean between runs.
- The full repo verifier is `tests/scripts/verify.sh` or `tests/scripts/test-all.sh`, which runs backend pytest in Docker, frontend unit tests, the frontend production build, and the live Playwright suite against the local stack.

## Script Guide

`tests/scripts/seed-e2e-data.sh`

- Starts the local Docker stack if needed.
- Waits for the backend to become reachable.
- Seeds deterministic browser and access-management data inside the backend container.

`tests/scripts/test-backend.sh`

- Starts the local Docker stack if needed.
- Waits for the backend to become reachable.
- Runs backend `pytest` inside the backend container.
- Accepts optional pytest paths or flags.

`tests/scripts/test-frontend-unit.sh`

- Runs the frontend unit tests locally from `app/frontend`.
- Does not start Docker services because these tests do not need the live stack.
- Accepts optional Node test runner flags.

`tests/scripts/test-e2e.sh`

- Starts the local Docker stack if needed.
- Waits for both frontend and backend to become reachable.
- Reseeds deterministic live E2E data through `tests/scripts/seed-e2e-data.sh`.
- Runs the Playwright browser suite against the live application.
- Accepts optional Playwright spec paths or flags.

`tests/scripts/verify.sh`

- Starts or refreshes the local Docker stack.
- Waits for frontend and backend readiness.
- Reseeds deterministic live E2E data.
- Runs backend tests, frontend unit tests, the frontend production build, and the live Playwright suite.
- Accepts `--repeat N` to execute the full verification flow multiple times.

`tests/scripts/test-all.sh`

- Convenience wrapper around `tests/scripts/verify.sh`.
- Accepts the same arguments as `verify.sh`.

## Common Runs

For full-stack verification, run:

```bash
tests/scripts/verify.sh
```

This flow uses the live local Docker stack, not mocked services or SQLite.

Run the suites separately when you want narrower feedback:

```bash
tests/scripts/seed-e2e-data.sh
tests/scripts/test-backend.sh
tests/scripts/test-frontend-unit.sh
tests/scripts/test-e2e.sh
```

Run the same full verifier through the convenience wrapper:

```bash
tests/scripts/test-all.sh
```

For additional confidence on stateful flows, repeat the verifier:

```bash
tests/scripts/verify.sh --repeat 3
```
