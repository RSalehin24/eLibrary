# Bengali library implementation: foundation

The accepted product plan is the implementation target. This document records
the repository discovery, the first delivery boundary, and the dependency
proposal. It does not replace the functional, device, SEO, or capacity criteria.

## Repository discovery

- Backend: Django 5.2 LTS, Django REST Framework, PostgreSQL, Celery, Redis.
- Frontend: React 18, JavaScript, Vite, React Router; no Next.js or TypeScript.
- Existing domains: accounts, catalog, access/reading, ingestion, processing.
- Retained features include invitations, TOTP, scoped permissions, ownership,
  editions, physical records, Kindle, bookmarks, highlights, notes, and progress.
- Existing tests use pytest, Node's test runner, and Playwright. The architecture
  and 300-line file policies run through `tests/scripts/verify.sh`.
- Docker's configured Colima socket was unavailable during discovery. Python
  3.12 and Node 22 are available; backend packages are not installed locally.

## Dependency proposal — approved

Versions were checked against the publishers' registries on 2026-10-11. These
are proposed direct pins; package-manager generated lockfiles must capture
transitive dependencies after approval. Dependency installation and manifest
changes were authorized by the user's subsequent “OK”.

The new Next.js application will live in `app/web/` while the existing frontend
continues to run. Replace the serving frontend only after the retained journeys
pass against the new application. No repository cleanup is part of this step.

| npm package | Exact version | Use |
| --- | --- | --- |
| next | 16.4.0 | Server rendering and application routes |
| react, react-dom | 19.3.0 each | New application's UI runtime |
| @tanstack/react-query | 5.104.1 | Remote state and mutations |
| typescript | 5.9.3 | Static frontend contracts |
| @types/react, @types/react-dom | 19.3.0 each | React types |
| @types/node | 22.19.15 | Types for the selected Node 22 runtime |
| eslint | 9.39.4 | Frontend linting |
| eslint-config-next | 16.4.0 | Framework lint rules |
| openapi-typescript | 7.13.0 | Types generated from OpenAPI |

TypeScript 5.9.3 meets openapi-typescript's declared `^5.x` peer range. The
selected Next.js version declares Node >=20.9 and React 19 compatibility. The
ESLint version meets eslint-config-next's >=9 peer range. Installation and
build checks must verify the resolved dependency graph.

| Python package | Exact version | Change / use |
| --- | --- | --- |
| Django | 5.2.18 | Patch the existing 5.2.12 LTS pin |
| drf-spectacular | 0.30.0 | OpenAPI schema generation and validation |
| ruff | 0.17.0 | Python lint and format checks |
| mypy | 2.4.0 | Python type checks |
| django-stubs | 6.1.2 | Django types; publisher lists partial 5.2 support |
| djangorestframework-stubs | 3.18.1 | REST framework types |

Install existing backend requirements in an isolated local environment for
verification; retain Python 3.12 and PostgreSQL. Keep existing tests intact.
Ruff/mypy checks begin with the new foundation modules and expand as domains
are ported; do not suppress errors to satisfy checks. Stubs must be tested
against the retained Django/DRF runtime before accepting the foundation.

Sources: [Next.js registry](https://registry.npmjs.org/next/16.4.0),
[React Query registry](https://registry.npmjs.org/@tanstack%2freact-query/5.104.1),
[OpenAPI types registry](https://registry.npmjs.org/openapi-typescript/7.13.0),
[Django supported versions](https://www.djangoproject.com/download/),
[drf-spectacular](https://pypi.org/project/drf-spectacular/0.30.0/),
[Django stubs compatibility](https://pypi.org/project/django-stubs/6.1.2/).

Starting the existing local Docker/Colima runtime, downloading required images,
and installing these packages is approved. RabbitMQ and k6 image pins
will be presented before their installation in the reliability/capacity phases.
This proposal excludes production deployment, purchases, external accounts,
commits, pushes, destructive cleanup, and data resets.

## Foundation API and permission boundary

Introduce `/api/v1/` additively. Existing `/api/` contracts remain operational
during the transition. Django continues to authenticate same-origin sessions,
enforce CSRF, and decide authorization.

| Workspace/action | Backend requirement |
| --- | --- |
| Public metadata | Published, approved, undeleted catalog records only |
| Personal library, notes, profile | Authenticated account; own records only |
| Read/download/Kindle | Existing action-specific scope or ownership rules |
| Source and job management | Global processing management or full control |
| Access management | Global access management or full control |
| Metadata management | Existing global or matching scoped metadata grant |
| Maintenance `/admin/` | Django staff access and the account's enabled/required TOTP policy |

Workspace visibility is derived from active, unexpired backend grants. A
book-scoped metadata grant enables editing that book, not global processing or
user management. Reader accounts receive no management sections. Staff and
superusers retain the existing administrative permission behavior.

Reader feeds return `entries`, `next_cursor`, and `has_more`; administration
returns `entries` plus `pagination.page`, `pagination.limit`, and
`pagination.total_count`. Reader limits default to 24, administration to 50,
and both cap at 100. Cursors use a signed position and bind it to the normalized
search, filters, and ordering. Public serializers whitelist metadata and never
return book HTML, raw source payloads, protected asset paths, or reader tokens.

## Delivery tracking

The approved packages are installed. Local verification uses the isolated
`elibrary-foundation` Compose project, PostgreSQL on port 55432 and Redis on
56379. Existing application volumes and accounts were not migrated or reset.

Working increments include anonymous discovery, reviewed editorial metadata,
author/category/series/curated-collection pages, bounded sitemaps, personal
ownership feeds, scoped book editing, revision conflicts, review, publication,
withdrawal, protected reader sessions, edition-bound annotations, personal notes,
the PWA installation/offline/update implementation, reader profile/security,
cross-tab account isolation, persisted EPUB/job administration, asynchronous
Kindle requests, account/scoped-permission administration, and password-link
confirmation/setup, bounded source inspection with linked-book preparation,
queued invitation/reset mail, the permission-scoped administration Overview,
  source-to-book processing, duplicate/incomplete decisions, draft/export recovery,
  explicit bulk source outcomes, bounded source discovery, and security-session invalidation.
The generated OpenAPI contract and
frontend types cover the new `/api/v1/` routes. See
[public discovery](public-discovery-seo.md), [reader access](reader-access.md),
[account settings](account-settings.md), [background jobs](background-jobs.md),
[Kindle delivery](kindle-delivery.md), [users/access](users-access.md),
[password links](password-links.md), [account mail](account-mail.md),
[Overview](management-overview.md), [source inspection](source-workspace.md),
[source processing](source-processing.md), [source discovery](source-discovery.md),
[source automations](source-automations.md), and [PWA behavior](pwa.md)
for behavior, verification commands, and remaining work.

Checks updated on 2026-10-16:

- The complete non-live backend/tools audit passed **1,247 tests**, including
  retained processing/ingestion/engine cases. Thirteen live source-network cases
  were excluded. Thread-exception warnings were treated as errors.
- Mypy passed **199 configured source files**. Strict TypeScript, ESLint, the
  Next.js production build, **21 web helper tests**, OpenAPI validation,
  migration consistency, affected Python lint/format checks, architecture policy,
  file-size policy, and `git diff --check` passed. No exemption was expanded.
- All **108 Chromium**, **108 WebKit**, and **108 Firefox** journeys passed.
  Android and iPhone browser profiles each passed **30 journeys**. Safari
  installation help passed in all five profiles. The complete matrix is
  recorded in the [handoff](../implementation-handoff.md).
- The retained frontend passed all **154 unit tests** and its production build.
- Updated production images passed isolated HTTPS, real RabbitMQ preparation,
  broker/cache interruptions, replacement of broker/API/frontend containers,
  active preparation-worker SIGKILL and lease recovery, duplicate suppression,
  and a separate-project database/media/runtime restore drill. See the
  [verification report](../operations/local-platform-verification.md).
- Saved/recent/granted personal library feeds, physical reading logs, cross-edition
  browsing, and private profile images are implemented. See
  [personal reading](personal-reading.md). Retained source-execution loaders were
  replaced with [regular Python modules](legacy-imports.md).
- Synthetic Bengali search intents and reviewed aliases are covered by regression
  tests. A disposable 10,000-book profile retained four SQL queries and measured
  median requests below 23 ms. See [capacity scope](../operations/capacity-verification.md).

The user approved Playwright 1.64.0 and matching bundles, the temporary ESLint
9.39.4 support exception with every rule retained, development type stubs, and
Docker installation simulation. The production npm audit reports no findings;
five development-only lint-chain findings remain unresolved. See
[verification tooling](verification-tooling.md).

The user subsequently authorized the documented remaining checks and explicitly
required simulators only. Actual pinned k6 HTTPS runs passed at 1, 5, and 20
virtual users; Ubuntu and Debian Docker-package installations passed with
systemd startup simulated. Accepted-install/relaunch/reinstall checks passed
in desktop/Android/iPhone profiles, and loopback mail/search checks and browser
lab timing completed. See [simulator acceptance](../operations/simulator-acceptance.md).
Physical installation, external delivery, production editorial judgment, field
Web Vitals, and separate-machine capacity are outside that simulator scope.
No production deployment or commit was performed. The five development-only
lint dependency findings remain unresolved without a publisher patch.
