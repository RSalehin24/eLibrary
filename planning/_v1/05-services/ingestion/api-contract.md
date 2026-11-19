# ingestion — API contract

Status: DRAFT · Source of truth: `contracts-ingestion`

Prefix `/api/ingestion` via caddy. Every route requires scope `operate` (declared in code; undeclared route fails startup) and a signed-in session; user id comes from caddy's verified `X-User-Id`. Mutations are audited. Creating POSTs accept `Idempotency-Key`. Lists use keyset `after`/`limit` (<= 100). Role demo has no `operate`.

## Requests

| Method and path | Request | Response |
|---|---|---|
| `POST /requests` | `{mirror_entry_id}` or `{source_url}` (host allow-list enforced, canonicalized); optional `intent`, `edition_label` | `201 request`; `409 active_request_exists` returns the active request id |
| `POST /requests/resolve-title` | `{query}` | up to 3 candidates from the local mirror `[{mirror_entry_id, title, author, score, evidence}]`; local data only, no live crawl; exact key first, then token-set; never substring |
| `POST /requests/upload` | multipart EPUB, size-bounded, streamed | `201 request` (`source_kind=epub_upload`); goes through the same curate/validate/duplicate/build path (REQ-ING-013) |
| `GET /requests?state&origin&phase&q&after` | | list with state, phase, progress `{done,total}`, error code |
| `GET /requests/{id}` | | detail: attempts, jobs, issues, duplicate review, build audit, catalog version state |
| `POST /requests/{id}/retry` | | requeues from the failed step reusing the scrape cache; allowed from `failed`, `awaiting_credential`, `cancelled` |
| `POST /requests/{id}/cancel` | | sets cancel flag and cancels queued jobs; allowed from `queued`, `running`, `needs_review`, `awaiting_credential` |
| `POST /requests/{id}/force-generate` | `{reason, acknowledged_issue_codes[]}` | allowed from `needs_review` (validation kinds only) or `failed` with curation issues; marks the curated document `forced`, continues to duplicate check and build; cannot bypass the audit gate, completeness of unfetched leaves without `empty_at_source` evidence, or a pending duplicate review; the catalog version carries `forced=true` |
| `POST /requests/{id}/new-edition` | `{edition_label?, publisher?, translator?, work_book_id?}` | allowed from `published`, `rejected_duplicate`, or `needs_review` with a duplicate review: creates a child request (`parent_request_id`, `intent=new_edition`) |
| `DELETE /requests/{id}` | | soft delete of a terminal request (history stays in audit) |
| `POST /requests/bulk` | `{action: retry\|cancel\|import, ids[] <= 200}` | `200 {results:[{id, ok, code?}]}`; each item in its own transaction; invalid transitions are reported per item, never silently skipped |

## Duplicate reviews and review items

| Method and path | Purpose |
|---|---|
| `GET /duplicate-reviews?state&after`, `GET /duplicate-reviews/{id}` | candidates with evidence side by side |
| `POST /duplicate-reviews/{id}/resolve` | `{decision: new_work\|new_edition\|new_translation\|refresh_existing\|confirm_duplicate, target_book_id?, edition_label?, note?}`; `confirm_duplicate` ends the request as `rejected_duplicate`; others resume the pipeline at build; `409` if not pending |
| `GET /review-items?kind&state&after`, `GET /review-items/{id}` | validation reviews with highlighted evidence |
| `POST /review-items/{id}/resolve` | `{action, payload}` validated per kind; may requeue the request |

## Mirror and sync

| Method and path | Purpose |
|---|---|
| `GET /mirror?status&q&incomplete&after` | mirror entries with derived status from latest request |
| `POST /mirror/import` | `{entry_ids[] <= 200}` creates requests (skips those with an active request, reports per item) |
| `POST /sync/{catalog\|incomplete}/start` | creates a run (manual trigger); `409 sync_active` if one exists; may pass `resume_run_id` |
| `POST /sync/runs/{id}/cancel` | sets cancel flag (honored per page) |
| `GET /sync/runs?kind&after`, `GET /sync/runs/{id}` | phase, counters, errors |

## Automation and credential

| Method and path | Purpose |
|---|---|
| `GET /automation`, `PUT /automation/{kind}` | settings; `If-Match: revision`; validated enums, time and timezone; `412 stale_revision` |
| `POST /automation/{kind}/run-now` | same code path as the scheduler, trigger `manual` |
| `GET /credential` | status only: `{state, expires_at, set_at, last_checked_at, last_failure_code}`; never the secret |
| `PUT /credential` | `{cookie, expires_at?}` replaces the credential; requests in `awaiting_credential` are requeued in the same transaction; audited |
| `POST /credential/check` | enqueues a `check_credential` job (GET of an authenticated-only page) |
| `DELETE /credential` | state `absent` |

## Jobs

| Method and path | Purpose |
|---|---|
| `GET /jobs?state&kind&request_id&after`, `GET /jobs/{id}`, `GET /jobs/{id}/log?after` | read-only observation; there is no endpoint to claim, assign or reassign jobs |

## Live updates

| Method and path | Purpose |
|---|---|
| `GET /snapshot` | `{version: <last event id>, counters, active_requests[], active_sync_runs[], credential, automation}` |
| `GET /events` | SSE (`text/event-stream`), `id:` = event id, honors `Last-Event-ID`; events `request.changed`, `job.progress` (throttled to 1/s per job), `sync.changed`, `credential.changed`, `automation.changed`; keep-alive comment every 15 s. If the requested id is older than retention, the server sends `event: reset` and the client reloads `/snapshot`. Delivery is a display aid; `GET` endpoints are the record. |

Fan-out: the API container holds one `LISTEN ingestion_events` connection and one in-process broadcast; per-client queue is bounded (slow client is dropped and reconnects with `Last-Event-ID`).

## Internal

| Method and path | Caller | Purpose |
|---|---|---|
| `GET /internal/events?after` | none required (console only), reserved | outbox page |
| `GET /internal/health` | compose | liveness; readiness includes database and worker heartbeat age |

## Error model

Same envelope as catalog: `{"error":{"code","message","request_id","details"}}`.

| HTTP | `code` | When |
|---|---|---|
| 400 | `invalid_request`, `url_not_allowed`, `invalid_epub` | validation, host not on allow-list |
| 401 / 403 | `unauthenticated` / `forbidden` | session or `operate` missing |
| 404 | `not_found` | |
| 409 | `invalid_transition`, `active_request_exists`, `sync_active`, `duplicate_review_pending`, `credential_required` | `details.allowed` lists legal actions |
| 412 | `stale_revision` | |
| 413 | `too_large` | upload cap |
| 429 | `rate_limited` | operator mutation limits (bulk size, per-minute) |
| 503 | `dependency_unavailable` | catalog or database unreachable on a synchronous check |

Error codes stored on jobs/requests (shown in the console): `network`, `timeout`, `http_5xx`, `rate_limited`, `auth_required`, `locked_source`, `source_changed`, `incomplete_source`, `invalid_document`, `audit_failed`, `catalog_unavailable`, `catalog_rejected`, `lease_expired`, `cancelled`.
