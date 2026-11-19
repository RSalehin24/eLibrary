# ingestion — state machines

Status: DRAFT

Formal model: [JobLifecycle.tla](../../03-correctness/formal-models/tla/JobLifecycle.tla) (to be updated to leases with fencing epoch) and Outbox.tla. Every transition below is one SQL statement or transaction with a compare-and-set on the current state (`UPDATE ... WHERE id=$1 AND state=$expected RETURNING`), and writes an outbox event in the same transaction.

## Request

```
                    ┌──────────── credential PUT ─────────────┐
                    ▼                                         │
 (create) ─► queued ─► running ─► needs_review ─(resolve)─► queued
                │         │  │          │
                │         │  ├─ auth_required ─► awaiting_credential
                │         │  ├─ permanent/exhausted ─► failed ─(retry)─► queued
                │         │  └─ build ok + catalog intake ok ─► in_catalog_review
                │         └─ duplicate review pending ─► needs_review (kind duplicate)
                └─ cancel ─► cancelled ─(retry)─► queued
 in_catalog_review ─ book.published ─► published
 in_catalog_review ─ version rejected (book.version_changed) ─► needs_review (CatalogRejected)
 needs_review(duplicate) ─ confirm_duplicate ─► rejected_duplicate
 published / rejected_duplicate ─ new-edition ─► (child request) queued
```

| State | Meaning | Active (counts toward unique per source URL) |
|---|---|---|
| `queued` | has a runnable or waiting job | yes |
| `running` | a job holds a lease | yes |
| `needs_review` | waiting for a human (validation review or duplicate review) | yes |
| `awaiting_credential` | scrape blocked by missing/expired source credential | yes |
| `in_catalog_review` | candidate sent to catalog as `in_review`, waiting for approval | yes |
| `published` | catalog emitted `book.published` for this version | no |
| `failed`, `cancelled`, `rejected_duplicate` | terminal (retry allowed from failed/cancelled) | no |

Rules:
- Outcome is never inferred from job success: a job `succeeded` only means the step ran; request state carries the outcome (fixes legacy T-03).
- A request becomes `published` only after the event `book.published` for its `version_id` is consumed; a failed build can never reach catalog (publish job requires `build_artifacts.state='built'`).
- Allowed actions per state (table-driven, 409 otherwise): `retry` in {failed, awaiting_credential, cancelled}; `cancel` in {queued, running, needs_review, awaiting_credential}; `force-generate` in {needs_review (validation kinds), failed (curation issues)}; `new-edition` in {published, rejected_duplicate, needs_review(duplicate)}; `resolve duplicate` in {needs_review(duplicate)}; delete in terminal states.
- `cancel` on `in_catalog_review` is refused (409): the operator rejects the version in catalog instead.
- Display state of a mirror entry is the state of its latest request (a query, not a stored column).

## Pipeline steps inside a request (each step is one job; the next job is inserted in the same transaction as the previous job's success)

```
scrape ─► curate ─► duplicate_check ─► build ─► publish ─► (wait for catalog approval)
```

| Step | Idempotency | Failure behavior |
|---|---|---|
| scrape | per-page cache files keyed by URL; cursor = next page index | page errors by class; unreachable leaf recorded; retry resumes from cursor; completeness gate before success (INV-ING-006) |
| curate | pure of (scrape manifest, ruleset); doc written to `docs/` then row (UNIQUE `(request_id, version_no)`) | `needs_review` with review items; `invalid` = permanent |
| duplicate_check | classifier is pure; `duplicate_reviews` unique pending per request | `exact_duplicate`/`needs_review` → `needs_review`; `new_*` with complete evidence continues |
| build | `build_hash` unique; same inputs give identical bytes | audit failure = permanent, review item `BuildFailed` |
| publish | catalog `Idempotency-Key = build_hash`; calls `PUT /internal/books/by-source/{key}` then `POST .../versions` | catalog 5xx/timeout retryable; 4xx permanent; success sets `in_catalog_review` |

## Job (lease model)

```
 queued ─claim (SKIP LOCKED, epoch+1, lease)─► running ─success─► succeeded
   ▲                                              │  ├─ Retryable & attempt<max ─► queued (run_after = backoff)
   │          lease expired (reaper)              │  ├─ Retryable & attempt=max / Permanent ─► failed
   └──── attempt<max (error lease_expired) ◄──────┘  └─ cancel flag seen ─► cancelled
 queued ─cancel─► cancelled
```

- Lease 120 s, heartbeat every 30 s by the executor; `lease_epoch` fences every write.
- Reaper (every 30 s in the worker, itself idempotent): `running` with `lease_expires_at < now` → `queued` (attempt < max) or `failed` (`lease_expired`, permanent). It is the only transition driven by time (INV-ING-010: lease expiry only moves Running to Queued/Failed).
- Cancel: API sets `cancel_requested` and, for `queued` jobs, cancels at once. A running executor reads the flag before every page and between steps, writes its cursor, and finishes as `cancelled`. Cancelling cannot interrupt a single in-flight HTTP request (bounded by request timeout).
- Idempotent re-run: any step may execute twice; outputs are keyed so a second run is a no-op or overwrites with identical bytes.
- Concurrency: bounded by worker slots (default 2 for scrape, 1 per host politeness semaphore), delay between GETs with jitter; limits come from settings, not from sleeping inside claims.

## Sync run (phases)

```
 fetching ─► reconciling ─► creating_requests ─► done
    │             │                │
    ├─cancel──────┴────────────────┴─► cancelled
    └─ error budget exhausted / listing_ok=false ─► failed (no reconcile, no request creation)
```

| Phase | Work | Guards |
|---|---|---|
| `fetching` | listing page by page: persist `page_cursor` and `last_page_signature` after every page, heartbeat, upsert mirror rows by `url_key` in a page-sized transaction; a repeated page signature stops with `SourceDrift` review | error budget (consecutive errors, default open); page cap; cancel checked per page; page errors are never swallowed (a failed page counts and the run fails at budget; no silent holes) |
| `reconciling` | for catalog kind: mark entries not seen as `missing_since` (never delete); for incomplete kind: resolve flags only for entries the live list proves complete | runs only if `listing_ok` (>= 1 parsable entry, run completed all pages, count >= 50% of previous run unless operator confirms); an empty or short listing can never mass-resolve (legacy F3) |
| `creating_requests` | automation runs only (manual runs end at `done` with `creating_requests` skipped): create requests for eligible entries in batches with `create_cursor` | eligibility below; bounded by `max_requests_per_run` and `max_open_requests` (back-pressure) |
| `done` | write `last_success_at`, clear `active_run_id` | |

Transitions are compare-and-set on `phase`, so a duplicate worker cannot advance twice. An interrupted run (lease lost) resumes from the persisted cursor (live mode also checkpoints per page; no restart from page 1). A single active run per kind is enforced by the partial unique index.

Eligibility for automatic request creation: entry not `missing`, `incomplete_flag` false (or incomplete kind and now complete), no request ever created for its `url_key` in states other than `failed` older than the cooldown, ordered by source order (`first_seen_at`, then listing position), `mode=pending` selects never-requested only; `mode=all` also last-failed (never `rejected_duplicate`, `cancelled` by an operator, or `needs_review`).

## Automation sequence (fixes the legacy idle-run defect)

Legacy defect (X6c F1, F5): the live automated run handed off to request creation and then bounced through `idle` (a dead guard undid the hand-off), creating requests only by 1-minute scheduler re-entry; `last_run_at` was written only on success, so a failure or stop was retried every minute.

Exact sequence in the new design (the scheduler is the `scheduler_tick` job, one instance, every 60 s, claimed like any job):

1. **Due check and start in one transaction**: `SELECT ... FROM automation_settings WHERE enabled AND next_due_at <= now() AND active_run_id IS NULL AND (cooldown_until IS NULL OR cooldown_until <= now()) FOR UPDATE SKIP LOCKED`. For each row: insert `sync_runs(kind, trigger='automation', phase='fetching')` (the unique active-run index rejects a conflict with a manual run, in which case skip and log), set `active_run_id`, `last_started_at = now()`, set `next_due_at` to the next slot after now computed from the injected clock and the configured interval/time/timezone (a missed slot during downtime is run once; no backlog), and insert the `sync` job. Commit. Because `next_due_at` moves at start, a failure or stop can never cause a one-minute retry loop.
2. **Fetching** (job `sync`): page by page as in "Sync run"; heartbeat renews the lease during the crawl, so a long crawl is not mistaken for stale (legacy F2).
3. **Reconciling**: in the same job, one transaction applies the mirror reconciliation, guarded by `listing_ok`, and compare-and-sets `phase: fetching -> reconciling -> creating_requests` within the same transaction. There is no intermediate `idle`, no second scheduler pass and no second run row.
4. **Creating requests**: same run row, batches of at most 50: insert `requests` (`origin='automation'`, `state=queued`) and their `scrape` jobs in one transaction per batch, advance `create_cursor`. If open requests (`queued`+`running`+`needs_review`) reach `max_open_requests`, the job requeues itself with `run_after = now + 60 s` and the run stays in `creating_requests`; it continues until the cursor is exhausted or `max_requests_per_run` is reached.
5. **Done**: CAS `phase -> done`, `last_success_at = now()`, `active_run_id = NULL`. On `failed`: `last_failure_at = now()`, `cooldown_until = now() + 6 h`, `active_run_id = NULL`; `next_due_at` stays at its already-advanced slot.
6. **Stop/cancel**: sets `cancel_requested`; honored per page and per batch; phase `cancelled`, `active_run_id = NULL`, no cooldown (the operator stopped it), `next_due_at` unchanged so the next slot applies.
7. **Disabled while running**: the active run finishes its current batch and stops creating requests.

The incomplete-recheck automation follows the same sequence with kind `incomplete`; manual and automation runs of one kind exclude each other by the unique index; catalog and incomplete kinds run independently.

## Duplicate review

```
 (classification) ─► [none: new_work with complete evidence] ─► continue to build
        │
        └─► pending ─resolve─► resolved(decision)
                         │
                         ├─ new_work / new_edition / new_translation ─► request resumes (queued → build) with decision as input
                         ├─ refresh_existing ─► request resumes, catalog gets a new version of target_book_id
                         └─ confirm_duplicate ─► request rejected_duplicate
```

The decision is persisted as an input to the pure stages, so reprocessing reproduces it. `pending` requires an operator (`operate`) action; resolution is idempotent (a second resolve returns 409 with the stored decision).

## Source credential

```
 absent ─PUT─► valid ─(expires_at - 3 days)─► expiring ─(expires_at passed)─► expired
                 │  ▲                                │
                 │  └──── PUT (new cookie) ──────────┴─────────────────────────┐
                 ├─ job gets 401/403/login page (AuthRequired) ─► rejected ─PUT─┘ (back to valid)
                 └─ DELETE ─► absent
```

- `expiring` and `expired` are derived from `expires_at` on read and by the daily `check_credential` job; `rejected` is set by a scrape or check observing authentication failure (even when `expires_at` is unknown or in the future).
- Entering `expired` or `rejected` moves in-flight requests whose job raised `auth_required` to `awaiting_credential`; `PUT` of a new credential requeues them in the same transaction.
- The console shows the state and `expires_at` on every ingestion screen header; the secret is write-only.

## Catalog event consumption

`cursor n → GET catalog /internal/events?after=n → apply (idempotent by version_id) → store cursor`. `book.published` for a known `version_id` sets the request `published`; `book.version_changed` with `rejected` sets `needs_review (CatalogRejected)`; `book.unpublished` annotates the request (no state change). Unknown versions are ignored.

## Review item

`open → resolved | dismissed`; resolving requires an action valid for the kind; may requeue the request, with the resolution stored as an override input to the pure stages.

## Curated document / build artifact

`curated: ready | needs_review | invalid` (append-only versions). `build: built | audit_failed | sent | accepted`; `built → sent` when catalog intake returns 201/200; `sent → accepted` when `book.published` is consumed.

## Ruleset

`Candidate → (gold gate passes) → Promoted → Retired`; promotion requires a shadow reprocess diff review ([rulesets](rulesets/README.md)).
