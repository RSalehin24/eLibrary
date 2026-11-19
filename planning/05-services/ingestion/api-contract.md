# ingestion - API behaviour

Status: DRAFT · Route list and error codes are owned by the [HTTP contract](../../07-contracts/http/ingestion.md); this page states the service behaviour behind it and must not add routes. A difference is a bug in this page.

## Rules

1. **Handlers only validate, record and enqueue** (REQ-ING-005). When the queue or database is unavailable a route answers 503 `queue_unavailable` (or returns a queued result); there is no inline fallback and no environment check in production code.
2. Every route declares its scope in code (`operate`); an undeclared route fails startup (REQ-ING-009). The actor comes from the gateway's verified headers, is recorded in `audit_log`, and no route authorizes by possession of an id. Reuse of a request by another user is never implicit.
3. Creating POSTs accept `Idempotency-Key`; replays return the first result.
4. Lists are keyset-paged with `after` and `limit` (bounded); bulk routes are bounded and return per-item results.
5. A route never submits anything to the source site (D-03) and none accepts an uploaded book (D-42, REQ-ING-031).
6. Invalid state transitions are 409 `invalid_transition` with `details.allowed`; stale `If-Match` is `stale_revision`.

## Route groups and behaviour

| Group | Behaviour beyond the contract |
|---|---|
| Console summary | `GET /console/summary` returns counts by status and outcome, queue depth and oldest queued age, review backlog, credential status, automation state and `snapshot_version` (the last outbox event id at read time, read in the same transaction) |
| Credential | `GET /credential` returns state (`valid`, `expiring`, `expired`, `missing`), `expires_at`, `checked_at`; the cookie is never returned. `POST /credential/check` enqueues one probe GET and answers 202. There is no route to set or delete the secret: the file is the interface |
| Mirror | `GET /mirror/entries` filters (`incomplete`, `state`, `q`); `state` is derived from the latest request. `POST /mirror/syncs` starts a run (page and error budget), idempotent while one runs, 409 when an automation run is active; cancel sets the cooperative flag |
| Requests | `POST /requests` accepts `source_url` (host allow-list, canonicalized) or `title` (resolved against the local mirror by `exact_key`, never a live crawl; more than one match answers `validation_failed` listing candidates); `from-mirror` creates requests for a bounded list of entries and skips those with an active request, reporting per item. Actions `retry`, `cancel`, `reprocess`, `discard` follow the table in [state machines](state-machines.md) section 1; `bulk-actions` is the same table per item |
| Document, review, builds, diff, log | read-only views: the document summary shows sections, entities with evidence and confidence, and dropped-block reasons, never the full scraped text; `review/resolve` stores per-item decisions as overrides; `diff` compares a reprocess with the published build (sections, entities, text) |
| Duplicate review | `resolve` takes `create_new`, `create_as_new_edition` (`edition_label`), `confirm_duplicate`, `discard`; `create_new` on an exact duplicate is `duplicate_book`; a second resolve returns 409 with the stored decision |
| Jobs | read, cancel (sets the flag; queued jobs cancel at once), retry (one active job per request, else `conflict`), attempts and log (bounded). No route claims, assigns or reassigns jobs |
| Automation | `PUT /automation` validates interval, time and explicit time zone with `If-Match: revision`; the view shows `next_due`, last run, cooldown and the limits (3 attempts, 50 requests, 0.5 s delay) |
| Rulesets, audit | rulesets are read-only; `GET /audit` lists append-only audit rows with actor |

## Live updates (REQ-ING-032)

- `GET /console/events` is `text/event-stream`. Each event has `id` = outbox id and the types `request.changed`, `job.progress` (throttled to 1 per second per job), `sync.changed`, `credential.changed`, `automation.changed`, plus `snapshot` and `reset`. `build.finished` stays internal.
- The API container holds one `LISTEN ingestion_events` connection and one in-process broadcast. After `NOTIFY` it reads new outbox rows by id, so a missed notification is repaired by the next one and by the 15 s heartbeat poll.
- **Reconnect**: the client sends `Last-Event-ID`; the server replays later events in id order. If the id is older than retention (7 days) or unknown, the server sends `reset`; the client reloads `GET /console/summary` (versioned snapshot) and continues from its `snapshot_version`. The client backs off with jitter on reconnect.
- Per-user filtering: the stream only carries data the caller may see; the stream closes when the session is revoked (identity check on connect and periodically).
- Per-client queues are bounded: a slow client is dropped and reconnects. Display state follows server-confirmed state only; GET endpoints are the record.
- Stream limits (provisional, open point C-6): 20 streams in total, 3 per user.

## Internal

`GET /internal/events` (outbox pull, reserved; `build.finished` is not a cross-service contract), `GET /internal/health`, `/internal/ready` (database reachable, worker heartbeat age), `/internal/contract`. The worker container serves only the internal port.

## Calls out

Identity `POST /internal/check` (`operate`) per request; catalog `POST /internal/books/{id}/versions` (idempotent), `POST /internal/books/match`, `GET /internal/books` (resync), `GET /internal/events`. Every call carries the internal service token and a bounded timeout; failures map to typed errors (`catalog_unavailable` retryable, 4xx `catalog_rejected` permanent).

## Error codes stored on jobs and requests (console display)

`network`, `timeout`, `http_5xx`, `rate_limited`, `auth_required`, `locked_source`, `source_changed`, `incomplete_source`, `invalid_document`, `audit_failed`, `catalog_unavailable`, `catalog_rejected`, `lease_expired`, `cancelled`. Each maps to one error class ([domain model](domain-model.md) section 3).
