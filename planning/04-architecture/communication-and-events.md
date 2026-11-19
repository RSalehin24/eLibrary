# Communication and events

Status: DRAFT (six services, internal HTTP, pull-based outbox; D-31, D-37)

## Styles

| Use | Style | Why |
|---|---|---|
| Browser to services | HTTPS to Caddy, then `web` (pages) or `gateway` (`/api/*`); gateway checks the session with identity | One authentication point; Caddy only does TLS |
| Authorization checks between services | Synchronous `identity /internal/check`, fail closed, cache at most 5 s keyed by grant version | Needs current grants |
| Reading ticket verification | Synchronous `identity /internal/tickets/verify` on every redemption (D-37) | Immediate revocation, no local verification |
| Bytes (EPUB, covers, reading copy) | Streamed over internal HTTP by the owning service after a check | Files are never served by Caddy, the gateway or shared volumes |
| State propagation | Pull-based outbox events ([ADR-0022](adr/0022-pull-based-outbox-events.md)) | No broker, replayable, simple |
| Long-running work | `jobs` table in ingestion ([ADR-0021](adr/0021-postgres-job-queue-no-redis.md)) | No work inside HTTP requests |

## Allowed synchronous calls (everything else is forbidden and CI-checked)

| Caller | Callee | Purpose | Failure behavior |
|---|---|---|---|
| web (SSR) and browser | gateway `/api/*` | all data | per gateway rules |
| gateway | identity `POST /internal/authorize` | verify session and CSRF, return user id, scopes and grant version | 401 or 403 from identity; unreachable gives 503; never allow on error |
| catalog, reader, ingestion, notify | identity `POST /internal/check` | scope or grant decision for a user and book | fail closed |
| reader | identity `POST /internal/tickets`, `POST /internal/tickets/verify` | mint and redeem reading tickets | fail closed; 503 |
| reader | catalog `GET /internal/books/{id}/versions/{vid}/epub` | stream the EPUB of a published version | retry with back-off; copy stays absent |
| ingestion | catalog `POST /internal/books/{id}/versions`, `POST /internal/books/match` | publish a gate-passing build (no approval, D-49); duplicate matching | idempotent; retry |
| notify | identity `GET /internal/users/{id}`, `GET /internal/email-requests/{id}`; catalog EPUB stream; catalog `POST /internal/kindle-requests/{id}/status` | address, link by reference, attachment, status report back | retry |
| any service | any service | calls carry an internal service token verified by the callee | 401 `service_token_invalid` |

Services trust identity headers only from the gateway with a valid service token; see [service authentication](cross-cutting/service-auth.md).

## Events (no broker)

Each producer keeps an `events` outbox table written in the same transaction as the change and exposes `GET /internal/events?after=<cursor>`. Consumers pull with a stored cursor, are idempotent, and tolerate duplicates and restarts. Full catalog with payloads and idempotency keys: [events](../07-contracts/events/README.md).

| Event | Producer | Consumers |
|---|---|---|
| `book.published`, `book.unpublished`, `book.version_changed` | catalog | reader, ingestion |
| `user.disabled`, `grant.changed` | identity | reader, catalog (cache invalidation) |
| `email.requested` | identity | notify |
| `kindle.requested` | catalog | notify |
| `build.finished` | ingestion | ingestion console (internal) |
| `user.deleted` (proposed, **OPEN O-1**) | identity | reader, catalog |

### Envelope

```json
{ "cursor": 1234, "id": "uuid7", "type": "book.published", "v": 1,
  "at": "RFC3339 UTC", "subject_id": "...", "request_id": "...", "payload": { } }
```

`cursor` is monotonic per producer; `id` is stable across redelivery. Payloads carry ids plus the minimum data needed (no documents, no addresses, no links). Schema changes are additive within a `v`; a breaking change publishes `v + 1` alongside the old one for one release.

### Delivery rules

- The consumer applies the effect and advances its cursor in one transaction; duplicates are harmless (idempotent effects).
- Ordering is by cursor within one producer; no ordering is assumed across producers.
- A consumer that loses its cursor resynchronizes from the owner's listing endpoint.
- Pruning waits until all known consumers have passed a cursor ([limits](cross-cutting/limits.md)).
- Models: [Outbox](../03-correctness/formal-models/tla/Outbox.tla) (to be adapted to pull), [JobLifecycle](../03-correctness/formal-models/tla/JobLifecycle.tla), [ReadOnce](../03-correctness/formal-models/tla/ReadOnce.tla).

## Publish flow (ingestion to reader)

1. Ingestion builds an EPUB (`build.finished`); only if every gate passed (validation, structure audit, epubcheck, duplicate rule) it calls catalog `POST /internal/books/{id}/versions` with the artifacts (idempotent by build identity). A failed gate never calls catalog (D-49).
2. Catalog stores the version as `published` in the same transaction (no approval step) and emits `book.published`.
3. Reader sees `book.published`, fetches the EPUB from catalog, parses and sanitizes it, and stores the reading copy keyed by `(book_id, version)`.
4. A failed build or a failed reader copy never leaves a visible book: visibility is catalog `published`; opening additionally requires a Ready reading copy and otherwise returns `copy_unavailable`.

## Open flow (reader)

`POST /api/reader/books/{slug}/open` (gateway checks the session) -> reader asks identity to decide and mint a ticket -> browser calls `GET /api/reader/tickets/{ticket_id}/book` with `X-Reader-Ticket` -> reader asks identity to verify and redeem (read-once consumed here) -> whole-book package. Progress and annotation calls need the session and the ticket.

## Contract versions

Each service serves `GET /internal/contract` with its contract crate version and supported event versions. The startup handshake (INV-PLT-003) refuses to serve when a required peer is incompatible.
