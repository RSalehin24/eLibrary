# New architecture brief (single source of truth for the plan rewrite)

Status: ACTIVE

Basis: owner decisions D-33..D-44 (monthly backup, metadata-only public pages, no demo, no catalog codes, SSR web, ticket check via identity, host-command admin recovery, broad audit, separate preview/read scopes, no manual upload, saved filters, profile images), D-26 (minimalist, light/dark), D-31 (6 services: gateway, identity, catalog, reader, ingestion, notify; supersedes D-27's "no gateway"), D-28 (reader renders and serves the whole book given the EPUB), D-29 (small scale: under 5,000 books, under 50 users), owner requirements R-01..R-13, and the analysis in `analysis/` (X1 issues, X2 capabilities, X3 permissions, X5/X6 traces). Writers MUST follow this brief and not re-derive it. Where a doc says something different, change the doc.

## 1. Containers (10)

`caddy` (HTTPS and certificate auto-renewal only) - `web` (Angular SSR on Node, D-39) - `gateway` (Rust: routing, session check against identity, rate limits, CSRF) - `identity` - `catalog` - `reader` - `ingestion-api` - `ingestion-worker` (same image as ingestion-api, different command) - `notify` - `postgres` (one container, one database and role per service, D-24). No Redis, no Celery, no message broker. Six Rust services: gateway, identity, catalog, reader, ingestion (API + worker containers), notify.

Routing: `/` -> web; `/api/identity/*`, `/api/catalog/*`, `/api/reader/*`, `/api/ingestion/*` -> the service. Caddy forwards everything to `web` or `gateway`; `gateway` calls `identity /internal/authorize` for every `/api/*` request except the public routes below; identity returns the verified user id and scopes as headers; services trust only those headers from the gateway and verify an internal service token on service-to-service calls.

Public routes (no session): identity sign-in, invite acceptance, password reset request/confirm, catalog public browse/search/detail of metadata only (D-34); preview text and reading need sign-in.

## 2. Services and what each owns

| Service | Owns (data) | Responsibilities |
|---|---|---|
| identity | users, credentials (Argon2), sessions (opaque server-side, cookie), TOTP, invites, password reset, roles, grants, profile images (D-44), audit log (D-40) | Authentication, authorization decisions (`/internal/authorize`, `/internal/check`), user and grant administration. Only place that decides who may do what. |
| catalog | books, book versions, metadata (title, contributors, series, categories), publication state, metadata version history, source links, asset registry and files (EPUB, cover) on its own volume, shelves ("My Books"), full-text search index (PostgreSQL FTS) | Browse/search/detail, publication workflow (a version is born `published` and later `archived`, D-56; automatic publish through ingestion's call, D-49; manual edit, unpublish and soft delete under `manage_catalog`), downloads, issuing Kindle-send requests, publishing events. |
| reader | reading copies (parsed and sanitized books) on its own volume, reading sessions, progress, bookmarks, highlights, notes | The EPUB reader service (D-28): when a book is published it fetches the EPUB from catalog, parses it once, stores a sanitized whole-book rendering; serves the whole book to the browser against a short-lived reading ticket; stores per-user reading state. |
| ingestion | source mirror (catalog listing of the source site, incomplete tracking), intake requests, jobs, scrape cache, curated documents, duplicate reviews, source-site credential (cookie) and its status, automation settings | One pipeline: mirror sync -> request -> scrape -> curate/validate -> duplicate review -> build EPUB -> publish to catalog. Operator console API and live events. API container plus worker container; the job queue lives in PostgreSQL. |
| notify | outbox of mails, templates, delivery log | Sends invites, password resets and Kindle deliveries over SMTP with retries, from events only (no direct send routes, D-53); isolates mail failures. |

No service reads another service's tables or volume. Data moves by internal HTTP (streaming for files) and by events.

## 3. Events (no broker)

Each producer keeps an `events` outbox table written in the same transaction as the change, and exposes `GET /internal/events?after=<cursor>`. Consumers pull with a stored cursor, are idempotent, and tolerate duplicates and restarts. Events: `book.published`, `book.unpublished`, `book.version_changed` (catalog -> reader, ingestion); `user.disabled`, `grant.changed` (identity -> reader, catalog caches); `email.requested`, `kindle.requested` (identity/catalog -> notify); `build.finished` (ingestion internal).

## 4. Permission model (summary; detail in `analysis/X3-roles-actions.md` section 4)

Deny by default. Roles: `reader`, `operator`, `admin` (no demo, D-35). Scopes: `browse`, `preview`, `read`, `read_once`, `download`, `kindle`, `operate` (ingestion console), `manage_catalog`, `manage_users`. Grants are explicit rows (user, scope, optional book, optional expiry, granted_by). No wildcard roles (`is_staff` and `admin:full_control` do not exist). "My Books" is a shelf only; it never grants access. Demo is a real restricted account: read-only curated set, no mutations, no download or Kindle. Every `/api/*` route declares its required scope in code; a route without a declaration is rejected at startup (fail closed).

## 5. Reader (D-28 applied)

1. On `book.published` the reader fetches the EPUB from catalog, parses it once (OPF, spine, TOC, XHTML, images, fonts), sanitizes every XHTML document with an allow-list, rewrites resource links, and stores the result as a reading copy keyed by `(book_id, version)`.
2. Opening a book: `POST /api/reader/books/{slug}/open` checks the `read` scope (and `read_once` rule) with identity, then asks identity to mint a reading ticket (identity is the only minter) and returns it: bound to user + book + version, valid 15 minutes, in a header or body, never in a URL; the reader verifies every ticket by asking identity (D-37).
3. `GET /api/reader/tickets/{ticket_id}/book` (the secret ticket value travels in the `X-Reader-Ticket` header; only the non-secret id is in the path) serves the whole rendered book in one response (a single package of manifest, TOC, chapters and resources); the browser renders it with a small purpose-built renderer (reading modes, typography, themes). The EPUB file itself is not served to the reader.
4. Read-once is consumed when a ticket is successfully redeemed for the book, not at open time, and not when a file is missing.
5. Honest limit: serving the whole book means a reader can copy it. Controls are entitlements, short tickets, rate limits and an audit log of opens, not DRM. Records must say so.
6. Progress, bookmarks (create and delete), highlights and notes require the signed-in session in addition to the ticket and belong to the user.
7. Not in the legacy reader and worth adding only if cheap: in-book search over the reading copy.

## 6. Ingestion (one pipeline)

- Single request model (replaces `BookSubmission` + `BookCreationRequest`, `SourceCatalogEntry` + `BookRecord`, `ProcessingJob` + engine state). Source mirror fields and local workflow state are stored separately so a re-sync never overwrites workflow state.
- Job queue: a `jobs` table claimed with `FOR UPDATE SKIP LOCKED`, lease with heartbeat, visibility timeout, attempt counter, typed errors (`retryable` or `permanent`), idempotent steps, cooperative cancel flag checked per page. No work runs inside an HTTP request. No Redis.
- Scrape: GET only, never submits any source-site form (D-03); one explicit, rotatable source credential with a visible status ("cookie expires/expired") on the console; scrape cache stored as files, not in a row; bounded concurrency and polite delay.
- Curate: Bengali-correct normalization (the legacy word lists lost their vowel signs), title match = exact normalized key plus author plus category plus edition; no substring matching; duplicate review is an explicit state.
- Build: EPUB writer with HTML escaping on and content sanitized, images packaged, fonts embedded, complete OPF metadata, XML well-formedness and structure audit as a gate; build output is never visible until every gate passed and it is published automatically (D-49).
- Publish: ingestion calls `catalog` `POST /internal/books/{id}/versions` with the artifacts; it is called only for a build that passed every gate (curated validation, structure audit, epubcheck in the worker, exact-key duplicate rule; if epubcheck cannot run the gate fails closed, D-57); catalog creates the published version the version in the same transaction, with no manual approval (D-49). Anything that fails a gate stays in ingestion's review queue (duplicate review, `needs_review`, `failed`). A failed build never leaves a visible book.
- Console live updates: Server-Sent Events from an outbox/LISTEN-NOTIFY, with versioned snapshot on reconnect.

## 7. Legacy defects -> design rules

| Legacy defect (X1/X5/X6) | Rule in the new design |
|---|---|
| Self-granted ownership bypasses all gates; wildcard roles; AllowAny default | Deny by default, scope declared per route, ownership never grants access |
| Draft, rejected and failed books visible; reader launch ignores state | Only `published` versions are visible; entitlement check includes publication state |
| Reader token in URL, token-only content routes, no revocation | Header/body ticket, 15 min, bound to user and book version, revocable by grant version |
| `/media/` served without auth | Files are never served by Caddy or the gateway directly; only services stream them after a check |
| Job engine over Redis pub/sub: lost messages, double runs, success reported for failures | Postgres queue with leases and typed outcomes |
| Pipeline runs inside the HTTP request on dispatch failure | No inline execution anywhere |
| Retry decided by error text; cooperative pause only between big steps | Typed errors; cancel flag per page |
| Whole scraped book stored in a request row; four copies of content | One authoritative curated document; derived artifacts regenerable |
| Mark-complete form submitted to source site | Acquisition is GET-only |
| Autoescape off; chapter HTML unsanitized; images and fonts missing from EPUB | Escaping on, sanitize, package images and fonts |
| Substring title matching; vowel-stripped Bengali lists | Exact normalized key plus author, category, edition |
| Dark mode broken for OS preference; hard-coded colours; ten breakpoints | M3 tokens, `prefers-color-scheme` plus toggle, four window classes |
| No backups, no limits, secrets printed on deploy, deploy does down then up | Backups with restore drill, resource limits, secrets via files, rolling restart per service |
| Two parallel book pipelines, duplicated mirror/job/request concepts | One pipeline in `ingestion` |

## 8. Frontend (Angular Material M3)

Screens merge to: Sign-in/auth card shell; Library (browse, search, filters, My Books, Kindle); Book detail (tabs: overview, metadata, files); Reader; Import workspace (operator: catalog sync, requests, review, jobs); Users and access (admin); Settings (theme, profile, TOTP). Four window classes (compact, medium, expanded, large). Minimalist, light and dark both first-class, follows OS preference with a persisted toggle, WCAG AA.

## 9. Sizing (D-29)

One host. One PostgreSQL. PostgreSQL full-text search with Bengali normalization. No cache layer. Per-container memory limits and a restart policy in Compose. Monthly full backup of every database and the file volumes, copied off the host, plus a restore drill (D-33; up to 30 days of data can be lost).

## 10. Defaults chosen by the assistant (owner delegated: "decide and proceed"; owner may override any of these)

| Topic | Default |
|---|---|
| Source credential | Cookie kept in a read-only secret file mounted into the ingestion containers (rotatable without a rebuild); only its status and expiry live in the database. No crypto crate. |
| Embedded Bengali font | Noto Serif Bengali (SIL OFL licence allows embedding), regular and bold |
| User-Agent when scraping | Honest, with a contact address; the operator cookie flow handles bot protection; no evasion |
| Retention | Raw scraped pages 30 days; files of the previous published version kept until the next one is published |
| Exports | Streamed CSV only (no XLSX or PDF, they would need new dependencies) |
| Shelf mutations | Allowed with `browse` and a signed-in session |
| Catalog publishing | Automatic when every gate passed (D-49, no approval); edit, unpublish and delete need `manage_catalog` (not `operate`); `operate` runs the import pipeline |
| Scrape defaults | 3 attempts per request, 0.5 s delay between pages, 50 requests per automation run |
| Duplicate matching | Exact normalized key plus author, category and edition; no fuzzy threshold; near-matches are listed for a human to decide, never auto-merged |
| EPUB navigation | Generate both the nav document and NCX (Kindle compatibility) |
| Kindle delivery status | notify reports it back; shown on the book's Files tab |
| New reader default access | `browse`, `preview`, `read` on published books, and `kindle`; `download` and `read_once` only by explicit grant |
| Audit retention | 1 year |
| Erasure / export | Admin deletes an account on request; each of identity, reader and catalog exports the user's own data as JSON and Settings bundles them (D-55) |
