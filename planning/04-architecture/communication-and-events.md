# Communication and events

Status: DRAFT

## Styles

| Use | Style | Why |
|---|---|---|
| User-facing reads/writes | Synchronous HTTP/JSON via gateway | Simple, cacheable |
| Authorization checks | Synchronous `decide`, fail-closed, cache ≤ 5 s | Needs current grants |
| Byte access (chapters, EPUB) | Signed capability, verified offline | No runtime dependency on access |
| State propagation | Asynchronous events via transactional outbox | Loose coupling, replay, rebuildable projections |
| Multi-service workflows (publish) | Orchestrated saga in ingestion with idempotency keys | Explicit steps and compensation |

## Allowed synchronous calls (everything else is forbidden and CI-checked, Q6)

| Caller | Callee | Purpose | Failure behavior |
|---|---|---|---|
| gateway | identity | resolve session → subject assertion | anonymous only |
| gateway | any | route | 502 typed error |
| catalog, library, ingestion | access | `decide` | fail closed |
| access | identity | subject facts (active, mfa) | use last projection; if stale > 5 min deny |
| ingestion | catalog | upsert draft book, resolve agents, duplicate query, publish | retry with idempotency key |
| ingestion | content | put canonical document, request build | retry; build is idempotent by doc hash |
| library | content | section index for re-anchoring | retry later |
| notify | content | fetch EPUB for Kindle with service capability | retry/backoff |

## Event envelope (all events)

```json
{ "id": "uuid7", "type": "BookPublished", "version": 1, "occurred_at": "RFC3339 UTC",
  "producer": "catalog", "subject_id": "…", "causation_id": "…", "correlation_id": "request id",
  "payload": { … } }
```

Rules: `id` unique and stable across redelivery; consumers dedupe on `(consumer, id)`;
events are facts in the past tense; payloads reference IDs plus the minimum data needed
(no full documents); schema changes are additive within a `version`, breaking changes
publish `version + 1` alongside the old for one release.

## Delivery

Producer writes the state change and an `outbox` row in one transaction. A relay claims
rows with `FOR UPDATE SKIP LOCKED`, delivers to subscribers' inbox endpoints (HTTP POST,
authenticated, idempotent), and marks sent on 2xx. Consumers write the effect and the
`(consumer, event id)` dedupe row in one transaction ([Outbox model](../03-correctness/formal-models/tla/Outbox.tla)).
Ordering is per aggregate (`subject_id`) only; consumers must tolerate reordering across aggregates.

## Publish saga (ingestion orchestrates)

1. `catalog.upsert_draft(book_key, metadata, credits)` → `book_id` (idempotent by `book_key` = source URL hash).
2. `content.put_document(book_id, doc_hash, document)` → `build_id`; content builds deterministically → `ArtifactSetSealed`.
3. `catalog.publish(book_id, artifact_set_id, expected_revision)`; catalog emits `BookPublished`.
4. `content.activate(book_id, artifact_set_id)` (pointer swap) — also driven by `BookPublished`.
5. Compensation: if any step fails permanently, book stays Draft; job goes to Review with the failing step; nothing half-visible because visibility = (catalog Published ∧ content active).

Each step has an idempotency key `(job_id, step, epoch)`; the saga's persisted step cursor is part of the
[job state machine](../05-services/ingestion/state-machines.md).

## Contract versions

Each service publishes `GET /internal/contract` → `{service, contract_crate_version, supported_event_versions}`.
Startup handshake (INV-PLT-001) refuses to serve when a required peer's contract is incompatible.
