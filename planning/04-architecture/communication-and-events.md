# Communication and events

Status: DRAFT

## Styles

| Use | Style | Why |
|---|---|---|
| Browser to services | HTTP/JSON through Caddy, authenticated by forward-auth to identity | One authentication point, no gateway code |
| Authorization checks between services | Synchronous `identity /internal/check`, fail closed, cache at most 5 s | Needs current grants |
| Bytes (EPUB, covers, reading copy) | Streamed over internal HTTP by the owning service after a check | Files are never served by Caddy or shared volumes |
| State propagation | Pull-based outbox events ([ADR-0022](adr/0022-pull-based-outbox-events.md)) | No broker, replayable, simple |
| Long-running work | `jobs` table in ingestion ([ADR-0021](adr/0021-postgres-job-queue-no-redis.md)) | No work inside HTTP requests |

## Allowed synchronous calls (everything else is forbidden and CI-checked)

| Caller | Callee | Purpose | Failure behavior |
|---|---|---|---|
| Caddy | identity `/internal/authorize` | verify session, return user id and scopes as headers | request rejected (401/503), never anonymous fallthrough |
| catalog, reader, ingestion | identity `/internal/check` | scope or grant decision for a user and book | fail closed |
| reader | catalog | stream EPUB of a published version | retry with back-off; copy stays absent |
| ingestion | catalog `POST /internal/books/{id}/versions` | submit candidate version and artifacts | idempotent; retry |
| notify | catalog | stream EPUB for Kindle delivery | retry |
| any service | any service | calls carry an internal service token verified by the callee | 401 |

Services trust identity headers only from Caddy; see [service authentication](cross-cutting/service-auth.md).

## Events (no broker)

Each producer keeps an `events` outbox table written in the same transaction as the change and exposes `GET /internal/events?after=<cursor>`. Consumers pull with a stored cursor, are idempotent, and tolerate duplicates and restarts.

| Event | Producer | Consumers |
|---|---|---|
| `book.published`, `book.unpublished`, `book.version_changed` | catalog | reader, ingestion |
| `user.disabled`, `grant.changed` | identity | reader, catalog (cache invalidation) |
| `email.requested` | identity | notify |
| `kindle.requested` | catalog | notify |
| `build.finished` | ingestion | ingestion (internal) |

### Envelope

```json
{ "cursor": 1234, "id": "uuid7", "type": "book.published", "version": 1,
  "occurred_at": "RFC3339 UTC", "subject_id": "…", "request_id": "…", "payload": { … } }
```

`cursor` is monotonic per producer; `id` is stable across redelivery. Payloads carry ids plus the minimum data needed (no documents). Schema changes are additive within a `version`; a breaking change publishes `version + 1` alongside the old one for one release.

### Delivery rules

- The consumer applies the effect and advances its cursor in one transaction; duplicates are harmless (idempotent effects).
- Ordering is by cursor within one producer; no ordering is assumed across producers.
- A consumer that loses its cursor resynchronizes from the owner's listing endpoint.
- Pruning waits until all known consumers have passed a cursor ([limits](cross-cutting/limits.md)).
- Models: [Outbox](../03-correctness/formal-models/tla/Outbox.tla) (to be adapted to pull), [JobLifecycle](../03-correctness/formal-models/tla/JobLifecycle.tla), [ReadOnce](../03-correctness/formal-models/tla/ReadOnce.tla).

## Publish flow (ingestion to reader)

1. Ingestion builds an EPUB candidate (`build.finished`) and calls catalog `POST /internal/books/{id}/versions` with the artifacts (idempotent by book key and document hash).
2. Catalog stores the version as `in_review`; approval makes it `published` and emits `book.published`.
3. Reader sees `book.published`, fetches the EPUB from catalog, builds the reading copy keyed by `(book_id, version)`.
4. A failed build or a failed reader copy never leaves a visible book: visibility is catalog `published`; opening additionally requires an existing reading copy and returns a typed "not ready" error otherwise.

## Contract versions

Each service serves `GET /internal/contract` with its contract crate version and supported event versions. The startup handshake (INV-PLT-001) refuses to serve when a required peer is incompatible.
