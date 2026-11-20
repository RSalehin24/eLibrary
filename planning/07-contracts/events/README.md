# Event catalog

Status: DRAFT (pull-based outbox, no broker; [ADR-0022](../../04-architecture/adr/0022-pull-based-outbox-events.md); six-service design, D-31)

## Mechanism

- A producer inserts an `events` row in the same transaction as the change (`cursor` bigserial).
- `GET /internal/events?after=<cursor>&limit=<n>` (service token; default and maximum batch in [limits](../../04-architecture/cross-cutting/limits.md)) returns `{ "events": [Envelope], "next": cursor }`, ascending, at-least-once, ordered only within one producer. Details: [HTTP conventions](../http/README.md).
- A consumer stores its own cursor (`event_cursors`), applies each event idempotently, and advances the cursor in the same transaction as the effect. It tolerates duplicates, restarts and gaps in time. A consumer that lost its cursor resynchronizes from the owner's listing endpoint; events are a trigger, not the only source of truth.
- Retention (30 days) and pruning wait for known consumer cursors; alert on consumer lag above 5 minutes.
- Payloads carry ids and the minimum data; never secrets, addresses, links, document text or book text.
- Cached decisions are keyed by `grant_version`, so a missed `grant.changed` is repaired by identity's `GET /internal/users/{id}/grant-version`.

## Envelope

```json
{ "cursor": 1042, "id": "<uuid7, stable across redelivery>", "type": "book.published", "v": 1,
  "at": "2026-11-19T08:30:00.000Z", "subject_id": "<uuid of the book or user>",
  "request_id": "<originating request id>", "payload": { } }
```

`v` is the schema version of the payload (additive changes keep it). Consumers ignore unknown fields and unknown event types. A breaking change publishes `v + 1` alongside the old one for one release.

## Events

| Event | v | Producer | Consumers | Payload | Idempotency key at the consumer | Meaning |
|---|---|---|---|---|---|---|
| `book.published` | 1 | catalog | reader, ingestion | `book_id, slug, version_id, version_no, epub_sha256` | reader: `(book_id, version_id)` (copy build is a no-op when a Ready copy exists); ingestion: `request_id` found by `version_id` or `book_id` (set `published` once) | a version became visible; reader builds the reading copy; ingestion confirms the request `published` (already set from the publish response; idempotent) |
| `book.unpublished` | 1 | catalog | reader, ingestion | `book_id, version_id?, reason` (`archived`, `deleted`) | `(book_id, event id)`; setting a state twice is a no-op | book hidden; reader stops serving the copy and tickets for it fail verification; ingestion records it |
| `book.version_changed` | 1 | catalog | reader, ingestion | `book_id, version_id, change` (`replaced` only: `submitted`, `approved` and `rejected` were retired by D-49) | `(version_id, change)` | a newer version replaced the previous published one; `replaced` makes the reader re-anchor annotations after the new copy is Ready |
| `kindle.requested` | 1 | catalog | notify | `request_id, user_id, book_id, version_id, address_index` | `request_id` (claim-before-send row) | send a book to a Kindle address (address read from identity at send time) |
| `user.disabled` | 1 | identity | reader, catalog | `user_id, grant_version` | `(user_id, grant_version)` | account suspended or disabled (suspend and disable both emit it); reader invalidates tickets, catalog drops cached decisions |
| `grant.changed` | 1 | identity | reader, catalog | `user_id, grant_version, scope?, book_id?` | `(user_id, grant_version)`; keep the highest | invalidate decision caches and issued tickets |
| `email.requested` | 1 | identity | notify | `request_id, kind` (`invite`, `password_reset`, `password_changed`), `user_id, language` | `(request_id, kind)` | send a mail; address and link are fetched by reference from identity, never in the event |
| `build.finished` | 1 | ingestion | ingestion console | `request_id, artifact_id, outcome` | internal; feeds SSE only | not a cross-service contract |

`notify` and `reader` emit no events; the gateway neither emits nor consumes any. The ingestion console stream (`request.changed`, `job.progress`, `sync.changed`, `credential.changed`, `automation.changed`) is SSE for display and is specified in the [ingestion API](../http/ingestion.md).

### Proposed (not decided)

| Event | Producer | Consumers | Payload | Status |
|---|---|---|---|---|
| `user.deleted` | identity | reader, catalog | `user_id` | **OPEN (O-1)**: account deletion must make reader (progress, annotations) and catalog (shelf, saved filters) erase user-owned data. Until decided, reader declares `POST /internal/users/{id}/erase` ([reader](../http/reader.md)) |

Rule: a new event or consumer needs a row here and, when it changes state in the consumer, an idempotency key definition (usually the event `id`, `version_id` or `grant_version`).

Reading tickets are not events: they expire by time and are rejected when identity's verification sees a changed grant version, a disabled user or an unpublished book.
