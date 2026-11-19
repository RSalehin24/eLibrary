# HTTP conventions

Status: DRAFT (rewritten for 5 services behind Caddy forward-auth, no gateway)

## Surfaces

| Surface | Prefix | Who calls | Auth |
|---|---|---|---|
| Public API | `/api/identity/*`, `/api/catalog/*`, `/api/reader/*`, `/api/ingestion/*`, `/api/notify/*` (admin) | browser through Caddy | session cookie checked by Caddy forward-auth; scope declared per route |
| Internal API | `/internal/*` | services, Caddy (`/internal/authorize` only) | internal service token; never routed by Caddy |

Caddy calls identity `GET /internal/authorize` for every `/api/*` request except the declared public routes, strips any client-supplied identity headers, and forwards `X-User-Id`, `X-User-Scopes`, `X-User-Demo`, `X-Request-Id` from identity's reply. Services accept those headers only from Caddy ([service authentication](../../04-architecture/cross-cutting/service-auth.md)).

## Rules

| Topic | Rule |
|---|---|
| Format | JSON (UTF-8), enums as `snake_case` strings, unknown request fields rejected |
| Ids | internal ids are UUIDv7 in lowercase hyphenated text ([ADR-0012](../../04-architecture/adr/0012-identifiers.md)); catalog `code` and `slug` are separate human-facing fields; event and outbox cursors are 64-bit integers serialized as JSON numbers (below 2^53) |
| Time | RFC 3339 UTC with `Z`, millisecond precision (`2026-11-19T08:30:00.000Z`); durations as integer seconds in fields named `*_seconds`; display zone is a UI matter ([text and time](../../04-architecture/cross-cutting/text-and-time.md)) |
| Scopes | every route declares exactly one required scope in code: `public`, `browse`, `preview`, `read`, `read_once`, `download`, `kindle`, `operate`, `manage_catalog`, `manage_users`, or `session` (any signed-in user, for own data). A route without a declaration stops the service at startup; the declaration is exported to OpenAPI (`x-required-scope`) and to identity's route-to-scope table |
| Reading ticket | issued by `reader` `POST /api/reader/books/{slug}/open`; signed, bound to user, book and version, 15 minutes; sent in the `X-Reader-Ticket` header (or returned in a JSON body), never in a URL or query string; routes that need it declare "scope + ticket" |
| Internal service token | header `Authorization: Service <token>` naming caller and callee, at most 60 s, checked against a static allow-list generated from the contract crates |
| Pagination | keyset: `?after=<opaque token>&limit=<n>`; response `{items, next}`; page size defaults and caps in [limits](../../04-architecture/cross-cutting/limits.md); no offsets for unbounded lists |
| Filtering | repeated params for OR within a facet; distinct params for AND across facets |
| Concurrency | `ETag`/`If-Match` carrying the aggregate `revision`; mismatch is `412` or `409 stale_revision` |
| Idempotency | `Idempotency-Key` header on non-idempotent POSTs (24 h window); internal publish uses `build_hash` |
| Errors | one envelope `{ "error": { "code", "message", "request_id", "details"? } }`; [error model](../../04-architecture/cross-cutting/errors.md); codes in the [catalog](../error-catalog.md) |
| CSRF | `X-CSRF-Token` header on cookie-authenticated mutations |
| Caching | public GETs of published data `Cache-Control: public, max-age=60` with `ETag`; everything else, downloads and the reader package `private, no-store`; files are never served by Caddy from disk |
| Languages | `Accept-Language` (`bn`, `en`); `Content-Language` echoes; messages are localized from catalogs keyed by error code |
| Limits | [limits](../../04-architecture/cross-cutting/limits.md) |
| Streaming | files with `Range` support from the owning service; SSE (`text/event-stream`, ingestion console) with a comment heartbeat every 15 s and `Last-Event-ID` resume, `event: reset` when the id is older than retention |
| Health and handshake | `GET /internal/health`, `GET /internal/contract` (contract version) on every service |
| Contract version | contract crate version in the `X-Contract-Version` response header |

## Public routes (no session)

identity sign-in, invite acceptance, password reset request and confirm, demo sign-in (a rate-limited POST); catalog public browse, search metadata and published preview text (D-12). Anonymous access exists only on these routes; a missing identity header anywhere else is a rejection.

## Outbox pull API (all producers: identity, catalog; ingestion reserves it)

`GET /internal/events?after=<cursor>&limit=<n>` with a service token. Response `{ "events": [ ... ], "next": <cursor> }`, ascending by cursor; an empty page returns the same cursor. Event shape and catalog: [events](../events/README.md).
