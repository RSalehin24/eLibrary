# Event catalog

Status: DRAFT (rewritten: pull-based outbox, no broker; [ADR-0022](../../04-architecture/adr/0022-pull-based-outbox-events.md))

## Mechanism

- A producer inserts an `events` row in the same transaction as the change (`id` bigserial is the cursor).
- `GET /internal/events?after=<cursor>&limit=<n>` (service token) returns `{ "events": [Envelope], "next": cursor }`, ascending, at-least-once, ordered only within one producer. Details: [HTTP conventions](../http/README.md).
- A consumer stores its own cursor (`event_cursors`), applies each event idempotently, and advances the cursor in the same transaction as the effect. It tolerates duplicates, restarts and gaps in time. A consumer that lost its cursor resynchronizes from the owner's listing endpoint; events are a trigger, not the only source of truth.
- Retention is set in [limits](../../04-architecture/cross-cutting/limits.md) and pruning waits for known consumer cursors; alert on consumer lag.
- Payloads carry ids and the minimum data; never secrets, addresses, links or text of books.

## Envelope

```json
{ "id": 1042, "type": "book.published", "v": 1, "at": "2026-11-19T08:30:00.000Z",
  "subject_id": "<uuid of the book or user>", "payload": { } }
```

`v` is the schema version of the payload (additive changes keep it). Consumers ignore unknown fields and unknown event types.

## Events

| Event | v | Producer | Consumers | Payload | Meaning |
|---|---|---|---|---|---|
| `book.published` | 1 | catalog | reader, ingestion | `book_id, slug, version_id, version_no, epub_sha256` | a version became visible; reader builds the reading copy; ingestion marks the request `published` |
| `book.unpublished` | 1 | catalog | reader, ingestion | `book_id, version_id?` | book hidden (archive, delete); reader invalidates tickets and copy access |
| `book.version_changed` | 1 | catalog | reader, ingestion | `book_id, version_id, change` (`submitted`, `approved`, `rejected`, `replaced`) | version state or replacement; a `rejected` change reaches ingestion as `CatalogRejected` |
| `kindle.requested` | 1 | catalog | notify | `request_id, user_id, book_id, version, address_index` | send a book to a Kindle address (address read from identity at send time) |
| `user.disabled` | 1 | identity | reader, catalog | `user_id` | revoke tickets and sessions' derived state; erase after the grace period |
| `grant.changed` | 1 | identity | reader, catalog | `user_id, scope?, book_id?` | invalidate decision caches and issued tickets |
| `email.requested` | 1 | identity | notify | `event_id, kind, user_id, language` | invite, password reset or similar; the link is fetched by reference, never in the event |
| `build.finished` | 1 | ingestion | ingestion (console) | `request_id, artifact_id, outcome` | internal; feeds SSE, not a cross-service contract |

`notify` emits nothing; the reader exposes no events. The ingestion console stream (`request.changed`, `job.progress`, `sync.changed`, `credential.changed`, `automation.changed`) is SSE for display only and is specified in the [ingestion API](../../05-services/ingestion/api-contract.md).

Rule: a new event or consumer needs a row here and, when it changes state in the consumer, an idempotency key definition (usually the event `id` or `version_id`).

Reading tickets are not events: they expire by time or are rejected when the reader sees `grant.changed` or `user.disabled`.
