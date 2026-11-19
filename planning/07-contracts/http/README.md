# HTTP conventions

Status: DRAFT (rewritten for six services: caddy, gateway, identity, catalog, reader, ingestion, notify; D-31, D-37, D-39)

## Surfaces

| Surface | Prefix | Who calls | Auth |
|---|---|---|---|
| Web pages | `/` | browser through Caddy to `web` (Angular SSR) | none for public pages; the web server calls `/api/*` for data |
| Public API | `/api/identity/*`, `/api/catalog/*`, `/api/reader/*`, `/api/ingestion/*` | browser and `web` SSR, through Caddy then gateway | session cookie checked by the gateway against identity; scope declared per route |
| Internal API | `/internal/*` | services only | internal service token; never routed by Caddy or the gateway |

Caddy terminates HTTPS and forwards `/` to `web` and `/api/*` to `gateway`; nothing else ([gateway](gateway.md)). `gateway` calls identity `POST /internal/authorize` for every `/api/*` request except the closed public allow-list, strips client-supplied identity headers, and forwards the identity reply as headers. Notify has no public surface.

| Header set by the gateway | Meaning |
|---|---|
| `X-User-Id` | verified user id (UUID), absent on public routes |
| `X-User-Scopes` | space-separated effective scopes at this moment; management scopes (`operate`, `manage_catalog`, `manage_users`) are present only when the session completed TOTP where the account requires it (REQ-IDN-025) |
| `X-Grant-Version` | the subject's grant version (cache key, revocation) |
| `X-Request-Id` | request id (generated when absent) |
| `Authorization: Service <token>` | internal service token the gateway presents to the upstream; services accept identity headers only with a valid token from the gateway |

## Rules

| Topic | Rule |
|---|---|
| Format | JSON (UTF-8), enums as `snake_case` strings, unknown request fields rejected |
| Ids | internal ids are UUIDv7 in lowercase hyphenated text ([ADR-0012](../../04-architecture/adr/0012-identifiers.md)); books are addressed by UUID and a unique `slug` (D-36: no catalog code); event and outbox cursors are 64-bit integers serialized as JSON numbers (below 2^53) |
| Time | RFC 3339 UTC with `Z`, millisecond precision (`2026-11-19T08:30:00.000Z`); durations as integer seconds in fields named `*_seconds`; display zone is a UI matter ([text and time](../../04-architecture/cross-cutting/text-and-time.md)) |
| Scopes | every route declares exactly one required scope in code: `public`, `browse`, `preview`, `read`, `read_once`, `download`, `kindle`, `operate`, `manage_catalog`, `manage_users`, or `session` (any signed-in user, own data only). A route without a declaration stops the service at startup; the declaration is exported to OpenAPI (`x-required-scope`). Grant- or book-dependent decisions are not taken from headers: the service asks identity `POST /internal/check` |
| 401 versus 403 | 401 `unauthenticated`: no valid session (missing, expired, revoked); the client sends the user to sign-in. 403: the session is valid but the action is denied (`forbidden` with `details.reason`, `mfa_required`, `csrf_invalid`); a 403 never ends the client session ([error catalog](../error-catalog.md)) |
| Reading ticket | issued through `reader` `POST /api/reader/books/{slug}/open`, minted and verified by identity (D-37); bound to user, book and version, 15 minutes; sent in the `X-Reader-Ticket` header (or returned in a JSON body), never in a URL or query string. Routes that need it declare "scope + ticket". The path segment `{ticket_id}` on reader routes is a non-secret handle, not the ticket |
| Internal service token | header `Authorization: Service <token>` naming caller and callee, at most 60 s, checked against a static allow-list generated from the contract crates |
| Pagination | keyset: `?after=<opaque token>&limit=<n>`; response `{items, next}`; page size defaults and caps in [limits](../../04-architecture/cross-cutting/limits.md) (100 rows provisional, O-7); no offsets for unbounded lists |
| Filtering | repeated params for OR within a facet; distinct params for AND across facets |
| Concurrency | `ETag`/`If-Match` carrying the aggregate `revision`; mismatch is `412 stale_revision` |
| Idempotency | `Idempotency-Key` header on non-idempotent POSTs (24 h window); internal publish uses the build identity; PUT and DELETE are idempotent by construction |
| Errors | one envelope `{ "error": { "code", "message", "request_id", "details"? } }`; [error model](../../04-architecture/cross-cutting/errors.md); codes in the [catalog](../error-catalog.md) |
| CSRF | `X-CSRF-Token` header plus matching `Origin` on cookie-authenticated mutations; the token comes with the session response ([identity](identity.md)); enforced by the gateway |
| Caching | public GETs of published metadata `Cache-Control: public, max-age=60` with `ETag`; everything else, downloads and the reader package `private, no-store`; files are never served by Caddy or the gateway from disk |
| Languages | `Accept-Language` (`bn`, `en`); `Content-Language` echoes; messages are localized from catalogs keyed by error code |
| Limits | [limits](../../04-architecture/cross-cutting/limits.md) |
| Streaming | files with `Range` support from the owning service; SSE (`text/event-stream`, ingestion console) with a comment heartbeat every 15 s and `Last-Event-ID` resume, `event: reset` when the id is older than retention |
| Health and handshake | `GET /internal/health` (liveness), `GET /internal/ready` (readiness), `GET /internal/contract` (contract version, supported event versions) on every service, on the internal port only |
| Contract version | contract crate version in the `X-Contract-Version` response header |
| Side effects | GET handlers never change state (REQ-CAT-032, REQ-RDR-025) |

## Public routes (no session)

A closed allow-list in the gateway (REQ-GWY-003), each also declared `public` by its service:

| Route | Service |
|---|---|
| `POST /api/identity/auth/sign-in`, `POST /api/identity/auth/totp/verify` (pending-session cookie), `POST /api/identity/invites/accept`, `POST /api/identity/password-reset/request`, `POST /api/identity/password-reset/confirm` | identity |
| `GET /api/catalog/books`, `GET /api/catalog/books/{slug}`, `GET /api/catalog/books/{slug}/cover`, `GET /api/catalog/browse/{facet}`, `GET /api/catalog/browse/{facet}/{id}` | catalog (metadata only, D-34) |

Preview text, reading, downloads and everything else need a session. A missing identity header anywhere else is a rejection.

## Outbox pull API (producers: identity, catalog; ingestion reserves it)

`GET /internal/events?after=<cursor>&limit=<n>` with a service token. Response `{ "events": [ ... ], "next": <cursor> }`, ascending by cursor; an empty page returns the same cursor. Event shape and catalog: [events](../events/README.md).

## Service pages

[gateway](gateway.md) · [identity](identity.md) · [catalog](catalog.md) · [reader](reader.md) · [ingestion](ingestion.md) · [notify](notify.md)

Route tables use the columns: method, path (relative to `/api/<service>` for public routes), required scope, purpose with request and response summary, errors beyond the common set.
