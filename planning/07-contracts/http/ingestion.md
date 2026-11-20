# Ingestion HTTP contract

Status: DRAFT · Service: [ingestion](../../05-services/ingestion/README.md) · Requirements: [ING](../../02-requirements/ing-ingestion.md) · Conventions: [README](README.md)

One pipeline: mirror sync, request, scrape, curate and validate, duplicate review, EPUB build, publish to catalog automatically when every gate passes (D-49). The API container only validates, records and enqueues; the worker container runs the jobs from the PostgreSQL queue. **No handler runs pipeline work** (REQ-ING-005): when the queue is unavailable the route answers 503 `queue_unavailable`. Acquisition is GET-only (D-03); there is no route that submits to the source site. Every route needs `operate` (session completed TOTP where required) and records the actor; there are no anonymous or capability-by-UUID routes and no manual EPUB upload (D-42). Catalog approval is **not** here: it needs `manage_catalog` in [catalog](catalog.md).

Request status (execution) and outcome (domain) are separate fields; the value lists below are indicative and fixed in the ingestion service contract: status `queued`, `running`, `awaiting_credential` (scrape blocked by a missing or expired source cookie; returns to `queued` when the credential is valid again; `retry` and `cancel` allowed), `needs_review`, `done`, `failed`, `cancelled`; outcome `built`, `needs_review`, `duplicate`, `failed`, `published` (catalog accepted the gate-passing build; confirmed by `book.published`). The earlier `submitted` outcome is retired by D-49.

## Public API (`/api/ingestion`) - 34 routes

### Console, credential

| Method | Path | Scope | Purpose | Errors |
|---|---|---|---|---|
| GET | `/console/summary` | operate | versioned snapshot: counts by status, queue depth and age, review backlog, credential status, automation state, `snapshot_version` | |
| GET | `/console/events` | operate | Server-Sent Events: `request.changed`, `job.progress`, `sync.changed`, `credential.changed`, `automation.changed`, `snapshot`, `reset`; `id` is the outbox id (`Last-Event-ID` resume); 15 s heartbeat; per-user filtering; closed on session revocation; display state follows server-confirmed state only | `unauthenticated` |
| GET | `/credential` | operate | source-site cookie status only: `valid`, `expiring`, `expired`, `missing`, with `expires_at` and `checked_at`; the cookie itself is a read-only secret file and is never returned or stored in the database | |
| POST | `/credential/check` | operate | enqueue a probe (one GET) that refreshes the status; 202 | `queue_unavailable` |

### Source mirror

| Method | Path | Scope | Purpose | Errors |
|---|---|---|---|---|
| GET | `/mirror/entries` | operate | source-site listing (source-owned fields) with filters `incomplete`, `state`, `q`; paged | |
| GET | `/mirror/entries/{id}` | operate | one entry and its linked request, if any | `not_found` |
| POST | `/mirror/syncs` | operate | start a catalog sync (page budget, error budget); idempotent while one is running; mutually exclusive with automation runs; 202 `{sync_id}` | `conflict`, `queue_unavailable` |
| GET | `/mirror/syncs` | operate | recent syncs | |
| GET | `/mirror/syncs/{id}` | operate | state and progress | `not_found` |
| POST | `/mirror/syncs/{id}/cancel` | operate | cooperative cancel (flag checked per page) | `invalid_transition` |

A re-sync writes only source-owned fields; an empty or failed fetch resolves nothing.

### Requests

| Method | Path | Scope | Purpose | Errors |
|---|---|---|---|---|
| GET | `/requests` | operate | list with `status`, `outcome`, `q`; paged | |
| POST | `/requests` | operate | create from a source URL or title `{source_url?, title?}` (`Idempotency-Key`); enqueues the scrape job | `duplicate_book`, `validation_failed`, `queue_unavailable` |
| POST | `/requests/from-mirror` | operate | `{entry_ids[]}` (bounded); per-item results; idempotent (no extra requests) | `limit_exceeded` |
| GET | `/requests/{id}` | operate | status, outcome, attempts, typed last error, links to build and catalog book | `not_found` |
| POST | `/requests/{id}/actions/{action}` | operate | `action` in `retry`, `cancel`, `reprocess`, `discard`; `retry` takes an optional `force_generate` boolean (D-93, default false) that regenerates the build instead of reusing the stored cursor and scrape cache; allowed-source-state table, invalid transitions are 409; deleting a book applies only to a book the request created | `invalid_transition`, `not_found` |
| POST | `/requests/bulk-actions` | operate | `{action, request_ids[]}` bounded, idempotent, per-item results | `limit_exceeded` |
| GET | `/requests/{id}/document` | operate | curated document summary: sections, entities with evidence and confidence, dropped-block reasons (never the full scraped text) | `not_found` |
| GET | `/requests/{id}/review` | operate | items below the confidence threshold or with locked chapters or layout drift | |
| POST | `/requests/{id}/review/resolve` | operate | per-item decisions (accept, override value, drop); nothing guessed is published | `validation_failed`, `invalid_transition` |
| GET | `/requests/{id}/builds` | operate | build candidates: builder version, ruleset version, gate results (XML, structure, epubcheck run in the worker, nav/NCX/TOC) | |
| GET | `/requests/{id}/diff` | operate | structured diff (sections, entities, text) of a reprocess against the published build | `not_found` |
| GET | `/requests/{id}/log` | operate | bounded event log with job correlation id | |

### Duplicate review

| Method | Path | Scope | Purpose | Errors |
|---|---|---|---|---|
| GET | `/duplicate-reviews` | operate | open reviews (exact normalized title key plus author, category, edition; near-matches listed, never merged) | |
| GET | `/duplicate-reviews/{id}` | operate | candidate against matched catalog books | `not_found` |
| POST | `/duplicate-reviews/{id}/resolve` | operate | `{action: create_new | create_as_new_edition | confirm_duplicate | discard}`; an exact duplicate is refused for `create_new` | `duplicate_book`, `invalid_transition` |

### Jobs

| Method | Path | Scope | Purpose | Errors |
|---|---|---|---|---|
| GET | `/jobs` | operate | list with `state` (`queued`, `running`, `succeeded`, `failed`, `cancelled`) | |
| GET | `/jobs/{id}` | operate | state, lease, attempt counter, error class (`retryable`, `rate_limited`, `auth_required`, `permanent`) and code | `not_found` |
| POST | `/jobs/{id}/cancel` | operate | sets the cancel flag (checked before every page and between stages) | `invalid_transition` |
| POST | `/jobs/{id}/retry` | operate | new attempt for a failed job; optional `force_generate` boolean as for the request `retry` action (D-93); at most one active job per request | `invalid_transition`, `conflict` |
| GET | `/jobs/{id}/attempts` | operate | attempts and logs, bounded | `not_found` |

### Automation, rulesets, audit

| Method | Path | Scope | Purpose | Errors |
|---|---|---|---|---|
| GET | `/automation` | operate | schedule, `next_due`, last run, limits (default 3 attempts per request, 50 requests per run, 0.5 s page delay) | |
| PUT | `/automation` | operate | interval, time and explicit time zone validated; `If-Match`; duplicate and needs_review outcomes are never retried automatically | `validation_failed`, `stale_revision` |
| GET | `/rulesets` | operate | versioned rulesets and promotion state (read only) | |
| GET | `/audit` | operate | append-only audit of operator actions with actor | |

## Internal API (`/internal`, service token) - 1 route

| Method | Path | Caller | Purpose |
|---|---|---|---|
| GET | `/internal/events` | reserved | outbox pull; `build.finished` is internal and feeds the SSE stream, not a cross-service contract |

Also on the internal port: `GET /internal/health`, `GET /internal/ready`, `GET /internal/contract`. The worker container serves only the internal port.

Calls out: identity `POST /internal/check` (`operate`) per request; catalog `POST /internal/books/{id}/versions` to publish a gate-passing build, `POST /internal/books/match` for duplicate matching, `GET /internal/books` for resync; consumes catalog events `book.published`, `book.unpublished`, `book.version_changed` (`replaced`). A 4xx from catalog's publish call becomes `catalog_rejected` (a hold in the review queue).
