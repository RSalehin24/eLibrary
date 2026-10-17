# Bengali library web workspace

Next.js owns rendering and interactive workspaces. Django owns authentication,
permissions, validation, transactions, and all database writes. The existing
`app/frontend` application remains available during the transition.

## Development

Run the API on port 8000, then run `npm run dev` from this directory. The web
workspace listens on `http://127.0.0.1:3000`. `/api/` is proxied to Django so
browser sessions and CSRF protection use one origin.

| Setting | Purpose |
| --- | --- |
| `API_INTERNAL_URL` | Django origin reachable by Next.js; defaults to localhost port 8000 |
| `PUBLIC_SITE_URL` | Canonical site origin; HTTPS is mandatory in production |
| `PUBLIC_CONTACT_EMAIL` | Optional public support address |
| `GOOGLE_SITE_VERIFICATION` | Optional Search Console HTML verification token |
| `BING_SITE_VERIFICATION` | Optional Bing HTML verification token |

Set Django's `FRONTEND_BASE_URL` to the browser's origin. Keep credentials and
environment files outside version control. Public server requests do not
forward browser cookies; private server requests forward the session and use
`no-store`. API responses also prohibit private caching.

## Checks and production artifact

```sh
npm run lint
npm test
npm run typecheck
PUBLIC_SITE_URL=https://library.example.test npm run build
PUBLIC_SITE_URL=https://library.example.test npm run start
```

Stop the development server before production builds or route type generation.
Development and production generated route definitions use different output
directories. Type checking regenerates production route definitions and checks
application and dependency types with `skipLibCheck: false`.

The build's `postbuild` step packages fingerprinted static assets and any public
assets alongside Next.js's standalone server. `start` uses that server. No CDN
or cloud provider is required. A complete production Compose deployment,
protected file serving, and operating procedures remain scheduled work.

Generate the API contract from the repository root, then regenerate TypeScript:

```sh
PYTHONPATH=app/backend .venv/bin/python app/backend/manage.py spectacular --urlconf config.schema_urls --format openapi-json --file docs/api/openapi.json --validate --fail-on-warn
```

From `app/web`, run `npm run generate:api`. Do not edit generated contracts.

## Browser verification

`tests/web` uses synthetic records in the isolated reference database
on port 55432. Its fixture generator rejects production databases and writes
random credentials to a new, mode-0600 file outside the repository. It does not
reset existing application data. Generate a fresh fixture for each full browser
run because editorial tests intentionally save and publish their own records.

Use the approved Playwright 1.64.0 runner from this workspace:

```sh
FOUNDATION_FIXTURE_PATH=/private/tmp/library-preview.json app/web/node_modules/.bin/playwright test --config tests/web/playwright.config.mjs --project=chromium
```

Run this from the repository root with both servers available. For a production
artifact whose canonical origin differs from the local browser URL, also set
`FOUNDATION_CANONICAL_ORIGIN` to the build's `PUBLIC_SITE_URL`.

Restart the development reference API between complete runs to reset its
disposable LocMem login quota; production throttles stay enabled. Never seed
synthetic fixtures into the separate `bangla_library_preview` user preview.
Set `FOUNDATION_WEB_URL` and `FOUNDATION_API_URL` when using the reference ports.
See `docs/architecture/verification-tooling.md` for approved browser bundles and
the pinned Linux Firefox simulator. Current reader/admin simulator results are
recorded in `docs/implementation-handoff.md`; physical device installation,
external Kindle arrival and independent-machine performance remain unverified.

For the complete UI suite, configure Django's SMTP backend with a loopback host
and synthetic sender (see `docs/implementation-handoff.md`). Kindle requests
require mail readiness even when the worker is stopped and no mail is sent.

## Catalog administration

`/manage/entities/` directly lists contributors, with category, series and curated
collection tabs, related-book links, role filters, remote selection and explicit
collection ordering. Global metadata managers create entities; scoped editors
edit their exact granted contributor/category. Book editors link to
`/manage/books/<slug>/relationships/` for contributor roles, categories, ordered
series, and edition grouping. Those associations require global metadata access
because they also determine scoped permissions. See
`docs/architecture/catalog-entities.md` for transactions, validation, and tests.
Public author/category/series directories link to their books. My Books opens a
combined personal list with visible Add/Remove controls on book pages. Manual
review is not required; source books publish automatically after source, export
and reader checks. `/manage/unfinished/` tracks the source website's unfinished
category separately from application processing failures.

## Protected reader

The reader uses account-bound UUID sessions and prepared, sandboxed EPUB
chapters. Book permissions and expiry are checked by Django for each request.
Existing EPUBs need preparation outside reader requests; see
`docs/architecture/reader-access.md` for the operator command and limits.
The reader includes scroll/single/spread views, fullscreen/focus, text/font/theme
settings, nested EPUB 3/NCX contents, chapter/full-book search,
keyboard/swipe/pinch/tap navigation, progress with visible save failures,
bookmarks, highlights/quotes, and private notes with revision conflicts. Supported
original text CFIs and package-relative locations retain their target checks;
older prepared books offer an explicit reader-file update while remaining
readable. Book details show account-specific progress and notes;
book/source/editor surfaces share reading, HTML and permitted Kindle actions.
Real protected cover assets have a title/author fallback. See
`docs/operations/feature-parity.md` for the original-app comparison and remaining
validation limits. `/profile/` includes names, password/session changes, Kindle
addresses, and authenticator setup/login. See `docs/architecture/account-settings.md`.
`/kindle/` adds selected-recipient requests, private history, per-address outcomes,
and revision-checked cancellation. The delivery worker and a loopback SMTP server
verify acceptance/uncertainty handling; live RabbitMQ/device arrival remain work.
See `docs/architecture/kindle-delivery.md`. Profile-image upload/removal is available.
Password-link confirmation/setup uses
`/create-password/` and `/reset-password/confirm/` with CSRF, nonce consumption,
TOTP policy, and draft/update guards. See `docs/architecture/password-links.md`.
`/reset-password/` and `/manage/users-access/invite/` queue reset/invitation
mail outside serving requests. Private mail history, status, controls, and resend
are available in Users & Access. See `docs/architecture/account-mail.md`.

`/manage/jobs/` adds status filters, bounded pagination, execution details, and
revision-checked pause/cancel/resume. Authorized processors can request EPUB
preparation from book management. The persisted worker, confirmed dispatcher,
and recovery logic are covered by local PostgreSQL tests; live RabbitMQ testing
awaits image approval. See `docs/architecture/background-jobs.md` for commands,
connection budgets, and the remaining source/delivery workflows.

`/manage/users-access/` adds private account search, revision-checked account
settings, and global/book/category/writer grants. Reference searches are bounded,
obsolete reads are cancelled, and grant creation preserves ownership. Protected
accounts and uncertain writes retain explicit backend controls. See
`docs/architecture/users-access.md`. Queued invitation creation/resend and
anonymous reset requests now use the persisted delivery workflow; live broker
verification and bulk outcomes remain part of the accepted administration work.

`/manage/` shows counts for authorized books/sources/accounts, eligible queue age,
active work, and recent failure links. It polls work status independently of
static catalog counts. See `docs/architecture/management-overview.md`.

`/manage/sources/` adds SQL-filtered discovery-record inspection and exact catalog
linkage, with separate metadata permissions and EPUB preparation for linked books.
It excludes raw source payloads and book bodies from paginated reads. See
`docs/architecture/source-workspace.md` for the remaining discovery/processing,
bulk resolution, and automation work.

## Installation and offline launch

Production `postbuild` generates the root service worker and generic offline
notice alongside the standalone artifact. It caches fingerprinted static files
only. Root manifest/icons and installation controls are included. Updates wait
for user acceptance, unsaved work, and progress saving. See
`docs/architecture/pwa.md` for the cache boundary and outstanding physical-device
installation checks. Run `npm test` with Node 22.18 or newer; the coordinator
tests use Node's built-in TypeScript type stripping.
