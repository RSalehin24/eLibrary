# Service ownership and integration contract

**Target contract.** Existing implementation is in `app/web` and `app/backend`; `app/reader` and `app/engine` are planned directories. F02 verifies this contract before application coding; R01 and E01 implement the new boundaries.

## Ownership

| Service | Owns | Does not own |
| --- | --- | --- |
| Website | Accounts, Django sessions, grants, catalog/publication records, personal library, annotations/progress, Kindle/account mail, admin UI, root installation manifest/worker | Source snapshots, engine stage checkpoints, reader UI runtime |
| Reader | Library/local reading UI, EPUB navigation/typography/search, command registry, public offline shell | Account database, authorization decisions, source processing, publication |
| Engine | Configured-source discovery/collection, snapshots/blocks, inference, canonical documents, generated builds, creation jobs/schedules and their checkpoints | Website ORM tables, personal activity, outbound Kindle/account mail |

The website may keep an engine status projection and publication receipts. Its projection cannot act as an engine job queue. Engine account/book references are opaque IDs plus current authority/catalog revisions; there are no cross-database foreign keys or ORM joins. Manual EPUB intake stays with the website's preparation workflow; source intelligence stays in the engine.

The website also owns source→book identity reservations and administrator metadata/cover override context. [Publication lifecycle](publication-context-and-lifecycle.md) defines reservation, first creation, override transfer and file leases; [scheduling and status](scheduling-and-status.md) defines complete Run Now workflows and the monotonic status projection used for correct combined job pagination. These are required contract seams, not optional later refinements.

## Browser route ownership

| Public path | Owner | Rule |
| --- | --- | --- |
| `/reader/`, `/reader/[identifier]/`, `/local-reader/` | Reader | Proxy complete documents, deep links, and reloads to the reader; no website header in the canvas. |
| `/reader-assets/` | Reader | Distinct immutable asset namespace. No root `/_next/` collision. |
| `/api/v1/` | Website API | Same-origin sessions and CSRF; do not send calls through a reader-owned account implementation. |
| `/sw.js`, `/manifest.webmanifest`, root installation assets | Website | One root service worker and one install identity. Reader publishes its public shell/assets to that worker's release manifest. |
| Remaining retained page routes | Website | Defined by the website route matrix. |
| `/internal/v1/engine/`, `/internal/v1/website/` | Private service APIs | Not exposed by the public proxy. |

Navigate across website/reader boundaries using full document navigation. Back/forward, opening a new tab, direct links, language/theme, and a validated same-origin return destination must work. Reject external or protocol-relative return URLs. Reader identifiers identify account-bound sessions; they are never bearer credentials.

Keep the current reader available until the extracted build and proxy pass R01 checks; switch ownership for all three page routes in one proxy release. Remove the superseded website reader route implementation after the switch passes. No obsolete development redirects are required.

## Authentication, privacy, and authority

- Website session cookies stay HttpOnly, secure in production, and same-origin. Reuse current session/CSRF/TOTP flows. Never put passwords, service assertions, or bearer tokens into a URL or local storage.
- Every protected chapter, media range, progress, annotation, download, and Kindle request checks current account/resource authorization. Account mismatch is indistinguishable from an unknown private object (`404`); a known object with revoked current authority returns the existing documented denial.
- Account logout/switch clears private query state and pending work, broadcasts invalidation, and causes reader tabs to stop protected requests. A stale callback cannot write under a different account.
- Keep read-once launch serialization and active-session rules. A renderer reconnect or proxy retry is not a new opening. Failed preparation must not consume an opening.
- Session, private HTML, resources, mutations, and engine payloads use private/no-store responses. Offline cache contains only the public reader shell and public fingerprinted assets.
- Private transport uses the scoped short-lived assertions and replay rules in [private engine v1](private-engine-v1.md). Recheck authority at job admission, claim/resume, protected stage boundaries, and website publication. Fail closed while current authority cannot be established.

## Build and operational boundaries

Reuse the approved React/TypeScript/Next.js toolchain for the planned reader workspace and Django/Python/Celery tooling for the planned engine. Do not introduce another UI framework, broker, inference service provider, or dependency as a shortcut. Use the package manager for workspace manifests/lockfiles; any new package approval remains required.

Each product service has its own build artifact, configuration validation, tests, start command, and release identity. The engine has separate API/worker/scheduler processes; inference is private and never serves website/reader requests. Infrastructure may share a PostgreSQL server and broker, with separate databases/roles, storage roots, and named queues. Engine tests need a separate Redis server, not merely another Redis database.

**Target health routes:** `GET /health/live/` reports process liveness, `GET /health/ready/` reports readiness and version without credentials. The proxy dispatches these on internal service origins. Website readiness checks its DB, reader readiness checks its build/shell manifest, engine API readiness checks its DB and required transport configuration. Worker/scheduler heartbeats are separate statuses. Inference unavailability makes dependent jobs wait; public browsing must continue.

Release manifests identify website, reader, engine, schema, preparation policy, and private-contract versions. Accept only private contract v1 and exact supported document/preparation schema versions initially. A mismatched version returns a typed conflict and never partially applies data. Services can restart/redeploy independently within this declared compatibility envelope; incompatible versions require a coordinated, quiesced development release.

## Boundary acceptance scenarios

R01 proves independent build/start, direct reader reload, distinct asset URLs, full navigation both directions, shared session/logout, account isolation, CSRF, read-once behavior, and no accidental router prefetch across services. Engine failure must not break website/reader builds or reading already prepared content.

E01 proves engine DB credentials cannot access website tables, website cannot write engine files, website and engine can restart independently, and every source/job/schedule caller uses the contract. Static import checks reject engine imports of website ORM modules. Private routes are unreachable at the public edge. Faults and duplicate handoffs follow the private contract, not an in-memory callback.
