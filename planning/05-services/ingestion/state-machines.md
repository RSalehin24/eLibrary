# ingestion - state machines

Status: DRAFT

Formal models: [JobLifecycle.tla](../../03-correctness/formal-models/tla/JobLifecycle.tla) (leases, fencing, cancel) and [Outbox.tla](../../03-correctness/formal-models/tla/Outbox.tla); both to be checked against the tables below (TST-ING-005). Every transition is one SQL statement or transaction with a compare-and-set on the current state (`UPDATE ... WHERE id=$1 AND state=$expected RETURNING`) that also writes its `audit_log` row and its console `events` row. An illegal transition returns 409 `invalid_transition` with `details.allowed`.

## 1. Request (status and outcome are separate) - REQ-ING-001, REQ-ING-008

`status` is execution; `outcome` is the domain result ([domain model](domain-model.md) section 2). `step` (scrape, curate, duplicate_check, build, publish) is display only.

| Status | Meaning | Active (counts toward one per source URL) |
|---|---|---|
| `queued` | has a runnable or waiting job | yes |
| `running` | a job holds a lease | yes |
| `awaiting_credential` | scrape blocked by a missing or expired source cookie | yes |
| `needs_review` | a human must act (review item, duplicate review, failed-gate hold, catalog refusal of the publish call) | yes |
| `done` | the pipeline reached its domain result; see `outcome` | no (final) |
| `failed` | permanent failure or attempts exhausted (retry allowed) | no |
| `cancelled` | cancelled or discarded (retry allowed unless discarded) | no |

| From (status / outcome) | Event | Guard | To (status / outcome) |
|---|---|---|---|
| (create) | `POST /requests`, `/requests/from-mirror`, automation batch | no active request for `url_key` (409 otherwise); host allow-list; the `scrape` job inserted in the same transaction | `queued` / - |
| `queued` | job claimed | lease granted | `running` / - |
| `running` | retryable error, attempt < max | typed class only | `queued` / - (job `run_after` backoff) |
| `running` | step succeeded, next step exists | next job inserted in the same transaction | `queued` / - |
| `running` | `auth_required` | | `awaiting_credential` / - |
| `awaiting_credential` | credential valid again (file changed and probe passed, or check passes) | same transaction requeues the job | `queued` / - |
| `running` | validation gives review items (`needs_review`), or duplicate classification is not clear | review item or pending duplicate review written first | `needs_review` / `needs_review` |
| `running` | permanent error or attempts exhausted | | `failed` / `failed` |
| `running` | build gate passed (artifact `built`) | audit report all green | `running` / `built` (publish job queued in the same transaction) |
| `running` | publish succeeded (catalog 200/201: the version is already published, artifact `sent`) | every gate passed (INV-ING-036); `version_id` stored | `done` / `published` (no human step, D-49) |
| `done` / `published` | `book.published` consumed for `version_id` | idempotent confirmation; artifact `accepted` | `done` / `published` |
| `running` | catalog 4xx on the publish call (`catalog_rejected`) | review item `CatalogRejected` written first | `needs_review` / `needs_review` |
| `needs_review` | review item resolved | action valid for the kind; stored as override | `queued` / - |
| `needs_review` | duplicate review `confirm_duplicate` | | `done` / `duplicate` |
| `needs_review` | duplicate review `create_new` or `create_as_new_edition` | not allowed for `exact_duplicate` | `queued` / - (resumes at build with the decision as input) |
| `needs_review` | duplicate review `discard` | | `cancelled` / - |
| `queued`, `running`, `needs_review`, `awaiting_credential` | `cancel` | not `done` | `cancelled` / - (running: when the cancel flag is honored) |
| `failed`, `cancelled`, `awaiting_credential` | `retry` | at most one active job per request; not a discarded request | `queued` / - (resumes from the stored cursor and scrape cache) |
| `needs_review`, `failed`, `done` (`built`, `duplicate`, `published`) | `reprocess` | scrape cache present, else re-scrape; new curated version | `queued` / - (a published version stays visible until the new one is published) |
| `failed`, `cancelled`, `needs_review`, `done` (`duplicate`) | `discard` | never deletes catalog data; a book the request did not create is never touched | `cancelled` / - (terminal, local files released) |

Rules:
- The outcome is never inferred from job success.
- A request reaches `published` only after the publish job's catalog call succeeded; the `book.published` event for its `version_id` only confirms it. A build with any failed or missing gate result never reaches catalog (the publish job requires artifact state `built`, which means every gate passed; INV-ING-036). There is no waiting-for-approval state (D-49).
- `cancel` on `done` is refused: the book is already published (use unpublish in catalog, `manage_catalog`).
- Bulk actions apply each item in its own transaction, are bounded (see the HTTP contract), idempotent, and return per-item results; an invalid item is reported, never skipped silently.
- Forced generation (`needs_review` with validation kinds, or `failed` with curation issues) is a parameter of `retry` that marks the curated document `forced`; it cannot bypass the audit gate, unfetched leaves without `empty_at_source` evidence, or a pending duplicate review.

## 2. Pipeline steps (each step is one job; the next job is inserted in the same transaction as the previous job's success)

```
scrape ─► curate ─► duplicate_check ─► build ─► publish (automatic, gates passed) ─► done / published
```

| Step | Idempotency | Failure behaviour |
|---|---|---|
| scrape | per-page cache files keyed by URL; cursor = next page index; cancel flag read before each page | errors by class; unreachable leaf recorded; retry resumes from the cursor; completeness gate before success |
| curate | pure of (scrape manifest, ruleset, overrides); document written to `docs/` then row (`UNIQUE(request_id, version_no)`) | `needs_review` with review items; `invalid` is permanent |
| duplicate_check | pure over catalog data from `POST /internal/books/match`; one pending review per request | exact or unclear: `needs_review`; clear `new_*` with complete evidence continues |
| build | `build_hash` unique; identical inputs give identical bytes | audit failure: permanent, artifact `audit_failed`, review item `BuildFailed`; nothing sent |
| publish | catalog `Idempotency-Key = build_hash` | catalog 5xx/timeout `retryable`; 4xx `permanent` (`catalog_rejected`); see section 7 |

## 3. Job (lease model) - REQ-ING-004, REQ-ING-006, REQ-ING-007

| From | Event | Guard | To |
|---|---|---|---|
| `queued` | claim (`SKIP LOCKED`) | `run_after <= now()`; no other active job for the request; `lease_epoch + 1`, `attempt + 1` | `running` |
| `running` | success | write carries `lease_epoch`; next job inserted in the same transaction | `succeeded` |
| `running` | retryable or rate-limited error | `attempt < max_attempts` | `queued` (`run_after` = backoff or `retry_after`) |
| `running` | retryable error | `attempt = max_attempts` | `failed` |
| `running` | permanent or `auth_required` error | | `failed` |
| `running` | cancel flag seen (before a page, or between steps) | cursor written first | `cancelled` |
| `running` | lease expired (reaper) | `lease_expires_at < now()`; the only time-driven transition | `queued` (attempt < max) or `failed` (`lease_expired`, permanent) |
| `queued` | cancel | | `cancelled` |
| `failed`, `cancelled` | operator retry | no active job for the request | new job row (attempt counter restarts under a new idempotency key) |

- Lease 120 s (provisional); the heartbeat is made by the working thread between pages and at step boundaries, so a hung thread loses its lease. Lease expiry moves only `running` to `queued`/`failed`. A zombie executor's late write matches zero rows (fencing) and it stops.
- Completion is idempotent: a second `succeeded` write for the same epoch is a no-op; any step may execute twice with identical output.
- Cancel cannot interrupt one in-flight HTTP request (bounded by its timeout); it is honored before every page fetch.
- Concurrency: worker slots from settings, one in-flight request per source host, the polite delay between GETs; priority manual > reprocess > sync > scheduled recheck.

## 4. Source-mirror sync (two phases with a checkpoint) - REQ-ING-002, REQ-ING-003, REQ-ING-007

Phase 1 collects, phase 2 reconciles; nothing is resolved or marked missing until phase 1 completed and was verified.

| Phase | Work | Guards |
|---|---|---|
| `fetching` | listing page by page: after every page persist `page_cursor` and `last_page_signature`, heartbeat, upsert `mirror_entries` by `url_key` (source-owned columns only) in a page-sized transaction | page budget and error budget (consecutive errors); a repeated page signature stops with a `SourceDrift` review item; cancel read per page; a failed page counts and is never swallowed; an interrupted run resumes from the checkpoint, never from page 1 |
| `reconciling` | catalog kind: set `missing_since` on entries not seen in this run; incomplete kind: clear the incomplete flag only for entries the live list proves complete | only when `listing_ok` (all pages done, at least one parsable entry, count at least 50% of the previous run unless the operator confirms); an empty, short or failed listing resolves nothing (REQ-ING-002) |
| `creating_requests` | automation runs only: create requests for eligible entries in batches with `create_cursor` | `max_requests_per_run`, `max_open_requests` back-pressure; see section 5 |
| `done` / `failed` / `cancelled` | terminal | compare-and-set on `phase`: a duplicate worker cannot advance twice; one active run per kind by unique index |

Eligibility for automatic request creation: entry not missing; `incomplete_flag` false (or the incomplete kind and now complete); no request for its `url_key` in states other than `failed` older than the cooldown; source order; mode `pending` selects never-requested entries only, `all` also last-failed ones (never `duplicate`, operator-`cancelled` or `needs_review`).

## 5. Automation runs - REQ-ING-033

The legacy run bounced through `idle` and re-entered every minute (X6c). New sequence (`scheduler_tick` is one job claimed like any other, every 60 s):

1. **Claim the slot**: in one transaction `SELECT ... FROM automation_settings WHERE enabled AND next_due_at <= now() AND active_run_id IS NULL AND (cooldown_until IS NULL OR cooldown_until <= now()) FOR UPDATE SKIP LOCKED`; insert `sync_runs(trigger='automation', phase='fetching')` (the unique active-run index rejects a conflict with a manual run: skip and log), set `active_run_id` and `last_started_at`, move `next_due_at` to the next slot after now from the injected clock and the configured interval, time and time zone (a slot missed during downtime runs once), insert the `sync` job. Because `next_due_at` moves at start, a failure never causes a retry loop.
2. **fetching, reconciling, creating_requests** in the same run row, no intermediate idle: batches of at most 50 requests with their `scrape` jobs in one transaction per batch; if open requests reach `max_open_requests` the job requeues itself after 60 s and the run stays in `creating_requests`.
3. **done**: `last_success_at`, `active_run_id = NULL`. **failed**: `last_failure_at`, `cooldown_until = now() + 6 h` (provisional), `active_run_id = NULL`; `next_due_at` stays at its already-advanced slot. **cancelled** by the operator: no cooldown.
4. Disabling while a run is active lets the run finish its current batch and stop creating requests.
5. Settings validation: interval enum, `time_of_day`, an explicit IANA time zone; `PUT /automation` uses `If-Match: revision`. Duplicate and `needs_review` outcomes are never retried automatically; an automation request uses the stored attempt limit (default 3) and a run is capped at 50 requests (defaults, D-30).

## 6. Duplicate review - REQ-ING-023

| From | Event | Guard | To |
|---|---|---|---|
| (classification) | `new_work` or `new_edition` with complete evidence | | none created; the request continues to build with the class recorded |
| (classification) | `exact_duplicate`, `needs_review`, or incomplete evidence | | `pending` (request `needs_review` / `needs_review`) |
| `pending` | resolve `create_new` | classification is not `exact_duplicate` (otherwise 409 `duplicate_book`) | `resolved(create_new)`; request resumes at build |
| `pending` | resolve `create_as_new_edition` | `edition_label` present | `resolved(create_as_new_edition)`; child intent `new_edition` |
| `pending` | resolve `confirm_duplicate` | | `resolved`; request `done` / `duplicate` |
| `pending` | resolve `discard` | | `resolved`; request `cancelled` |
| `resolved` | resolve again | | 409 with the stored decision |

The decision is stored as an input to the pure stages, so a reprocess reproduces it.

## 7. Publish saga to catalog - REQ-ING-029

| Step | Action | Compensation / replay |
|---|---|---|
| 1 | publish job requires artifact `built` and request not cancelled | refuses otherwise (a failed build never reaches catalog) |
| 2 | `POST /internal/books/{book_id}/versions` with metadata, EPUB, cover, preview, `Idempotency-Key = build_hash`, internal service token | a retry after a crash, timeout or lost response returns the same version: one version per build identity |
| 3 | on 200/201 in one transaction: artifact `sent`, `version_id` stored, request `done` / `published` | if the transaction fails after a successful call, the retry replays the idempotent call |
| 4 | catalog publishes the version in the same call, with no approval step (D-49) | nothing is visible to readers unless every gate passed |
| 5 | event `book.published` (matched by `version_id`): artifact `accepted` (confirmation) | duplicates ignored |
| 6 | catalog 4xx on step 2 (`catalog_rejected`): `needs_review` with `CatalogRejected` | operator may reprocess |

Catalog events are pulled with `GET /internal/events?after=<cursor>`; the cursor is stored with the applied effects in one transaction; unknown versions are ignored; `book.unpublished` annotates the request without changing status.

## 8. Source credential status - REQ-ING-011

The cookie lives in a read-only secret file; the operator rotates it by replacing the file (no PUT route). The database holds only the derived status.

```
 missing ─(file present, probe ok)─► valid ─(expires_at - 3 days)─► expiring ─(expires_at passed, or probe fails with 401/403/login page)─► expired
    ▲                                  ▲                                  │                                      │
    └────────── file removed ──────────┴──── file replaced + probe ok ────┴──────────────────────────────────────┘
```

- Evaluated on read, by the daily `check_credential` job, on `POST /credential/check`, and when the worker sees the file fingerprint change. A scrape that observes an authentication failure sets `expired` with `last_failure_code` even when `expires_at` is unknown or in the future.
- Entering `expired` or `missing` leaves in-flight requests whose job raised `auth_required` in `awaiting_credential`; the transition back to `valid` requeues them in the same transaction.
- Every status change emits `credential.changed`; the console shows state and `expires_at` on every ingestion screen.

## 9. Review item and artifacts

Review item: `open -> resolved | dismissed`; resolving needs an action valid for the kind and may requeue the request; the resolution is stored as an override input to the pure stages. Curated document: `ready | needs_review | invalid` (append-only versions). Build artifact: `built | audit_failed`; `built -> sent` on catalog 200/201; `sent -> accepted` on `book.published`.

## 10. Ruleset

`candidate -> (gold gate passes) -> promoted -> retired`; promotion requires the shadow-reprocess diff review ([rulesets](rulesets/README.md)).

## 11. Console stream - REQ-ING-032

Each outbox row has a monotonic `id`. A client holds a `snapshot_version`; after a reconnect with `Last-Event-ID` it receives every later event, or, if the id is older than retention, a `reset` event and must reload the snapshot (versioned by the last event id). State shown follows server-confirmed state only (no optimistic status). Detail in [API](api-contract.md).
