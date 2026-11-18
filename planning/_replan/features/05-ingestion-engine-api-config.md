# 05 - Legacy ingestion: Central Job Engine, API, Celery, signals, commands, config

Status: DRAFT (research evidence; read-only record)

Source root: `archive/app/backend/` (`apps/ingestion/{engine,tasks.py,signals.py,views,serializers,models,management,urls.py,admin.py,apps.py}` and `config/`). Read-only, every line read. Services/pipeline (`apps/ingestion/services`, `pipeline`) were out of scope; where behaviour lives there it is named only as "service X (not read)". `CanManageProcessing`, `user_has_scope`, `SubmissionRateThrottle`, `TimeStampedModel`, `ReviewState` live in `apps/common` (not read).

## 1. Coverage

| File (under apps/ingestion unless noted) | Lines | Fully read |
|---|---|---|
| engine/__init__.py | 1 | yes |
| engine/__main__.py | 42 | yes |
| engine/api.py | 106 | yes |
| engine/constants.py | 46 | yes |
| engine/dispatch.py | 34 | yes |
| engine/engine.py | 303 | yes |
| engine/job_queue.py | 102 | yes |
| engine/recovery.py | 108 | yes |
| engine/redis_client.py | 25 | yes |
| engine/stale_detector.py | 51 | yes |
| engine/worker_registry.py | 117 | yes |
| tasks.py | 173 | yes |
| signals.py | 264 | yes |
| urls.py | 100 | yes |
| admin.py | 21 | yes |
| apps.py | 11 | yes |
| views/__init__.py | 82 | yes |
| views/activity.py | 15 | yes |
| views/catalog_entries.py | 276 | yes |
| views/curation.py | 196 | yes |
| views/duplicates.py | 164 | yes |
| views/filters.py | 164 | yes |
| views/guards.py | 50 | yes |
| views/incomplete_checks.py | 168 | yes |
| views/job_actions.py | 134 | yes |
| views/jobs.py | 162 | yes |
| views/querysets.py | 217 | yes |
| views/submissions.py | 294 | yes |
| serializers/__init__.py | 29 | yes |
| serializers/catalog.py | 121 | yes |
| serializers/common.py | 59 | yes |
| serializers/reviews.py | 48 | yes |
| serializers/submissions.py | 169 | yes |
| models/__init__.py | 40 | yes |
| models/catalog.py | 110 | yes |
| models/choices.py | 100 | yes |
| models/processing.py | 50 | yes |
| models/submissions.py | 75 | yes |
| management/__init__.py, management/commands/__init__.py | 1+1 (blank) | yes |
| management/commands/curate_source_site_books.py | 509 | yes |
| management/commands/process_legacy_batch.py | 44 | yes |
| management/commands/run_engine.py | 60 | yes |
| config/__init__.py | 3 | yes |
| config/asgi.py | 16 | yes |
| config/celery.py | 51 | yes |
| config/settings.py | 300 | yes |
| config/urls.py | 17 | yes |
| config/wsgi.py | 16 | yes |

Total 47 files / 5247 lines, all read. `.env` files not opened.

## 2. HTTP endpoints

Mount: `config/urls.py:11` `api/ingestion/` -> `apps/ingestion/urls.py`. Global DRF default: `SessionAuthentication` only, default permission `AllowAny` (settings.py:198-203) - every view sets its own. JSON renderer only (except the SSE view). No DRF pagination class; each list view applies its own `limit`. Statuses presented to clients map DB `cancelled` -> `"stopped"` (serializers/common.py:9) and the filter accepts `stopped` -> `cancelled` (views/filters.py:21).

Permission legend: Auth = `IsAuthenticated`; Manage = `CanManageProcessing` (apps.common.permissions, not read; I did not open its rule); `can_manage_processing_records(user)` (service, not read) decides who sees all submissions/jobs; others see only their own (`submitter=user`).

Total: 36 URL paths, 40 method operations.

### Submissions (views/submissions.py)

| # | Method + path | Permission | Request | Response | Side effects |
|---|---|---|---|---|---|
| 1 | GET `submissions/` (:46-76) | Auth | query: origin (`catalog` = curation+automation, or a value), status, review_state, resolution_status, input_type, q (icontains on original_input, resolved_url, with slug/url-encoded variants), linked_book_slug, created_after/created_before (datetime or date), limit (default 80, max 200) | list of SubmissionSerializer (id, input_type, origin, original_input, resolved_url, resolution_status/confidence, status, review_state, error_message, linked_book_slug, linked_book{id,title,slug,authors,series}, linked_book_deleted, served_from_database, canonical_submission_id, uses_existing_request, candidates (top 3), latest_job, created_at, updated_at) ordered by status priority then -updated_at | none |
| 2 | POST `submissions/` (:78-88) | AllowAny + `SubmissionRateThrottle` (scope `submission`, default 40/hour) | `input_type` (url/title/csv; required unless entries), `content` (text, lines or CSV with url/title/query/first-column), `entries` (list of strings; "http*" -> url else title), `auto_process` (default true) | 201, list of SubmissionSerializer | `create_submission_records(submitter=user or None, parsed_entries, auto_process, origin=USER)` (service, not read): creates BookSubmission rows (+ presumably resolution + queues jobs). Anonymous allowed (public submissions flagged `raw_payload.submitted_publicly`). |
| 3 | POST `submissions/status/` (:91-110) | AllowAny | `ids`: 1-200 UUIDs | list of visible SubmissionSerializer (missing/invisible silently dropped) | none. Visible if manager, owner, or public submission. |
| 4 | GET `submissions/<uuid>/` (:113-132) | AllowAny (DELETE needs Auth) | - | SubmissionSerializer; 403 if not manager/owner/public | none |
| 5 | DELETE `submissions/<uuid>/` | Auth | - | 204; 403 if not visible; 400 `{detail}` when service raises ValueError (active) | `delete_submission_record` (soft or hard delete, service) |
| 6 | POST `submissions/<uuid>/confirm-candidate/` (:135-176) | AllowAny (access by `get_accessible_submission`) | `candidate_id` (required) | SubmissionSerializer; 400 missing id; 403 candidate not of this submission; 409 if automation lock | marks chosen MatchCandidate selected (others unselected); target submission (canonical or itself) gets resolved_url, resolution_status=RESOLVED, confidence, status=QUEUED, error cleared; `sync_deduplicated_submissions`; if a Book already exists for that source URL -> `fulfill_submission_with_existing_book` (no job), else `queue_submission` (creates job + dispatch) |
| 7 | POST `submissions/<uuid>/action-links/` (:179-212) | AllowAny (access check) | - | `{book{title,slug}, launch_url (FRONTEND_BASE_URL/reader?manifest=...), manifest_url, epub_download_url, html_preview_url, expires_at}`; 400 not ready/no session; 410 book deleted | `ensure_preview_session(user|None, book, submission, allow_guest=is_public)` creates/reuses a PreviewAccessSession (token). EPUB/HTML URLs only if READY generated assets exist |
| 8 | POST `submissions/bulk-delete/` (:215-252) | Auth | `ids` (<=200 UUIDs) | `{deleted_count, soft_deleted_count, hard_deleted_count, skipped_active, skipped_missing}` | `delete_submission_record` per unique canonical target |
| 9 | POST `submissions/bulk-retry/` (:255-267) | Auth | `ids` | 202 service payload + `skipped_missing`; 409 if automation lock | `retry_submission_records(submissions, user)` |
| 10 | POST `submissions/<uuid>/retry/` (:270-282) | Auth | - | 202 ProcessingJobSerializer; 400 `{detail}`; 409 lock | `retry_submission_record` creates and dispatches a job. Non-visible id -> `.get()` DoesNotExist -> 500 (bug) |

### Jobs (views/jobs.py, views/job_actions.py)

| # | Method + path | Permission | Request | Response | Side effects |
|---|---|---|---|---|---|
| 11 | GET `jobs/` (jobs.py:38-62) | Auth | query: origin, status (comma list), submission_status, job_type, q (submission input, last_error, book title), created_after/before, limit (80/200) | list ProcessingJobSerializer (id, submission_id, job_type, status, task_id, queue_name, retry_count, cancel_requested, submission_origin/input/status/resolution_status, target_book_slug/title/deleted, last_error, timestamps). Ordered processing, queued, failed, cancelled, succeeded, then activity | none |
| 12 | GET `jobs/reprocess/summary/` (:98-110) | Manage | - | `{queued, active, done, failed, stopped}` counts of REPROCESS jobs | none |
| 13 | GET `jobs/stream/` (:113-152) | Manage | - | SSE `text/event-stream`: `event: connected`, then `event: job-update` with the raw Engine event JSON, `: keepalive` every 5 s idle | Opens its own Redis pub/sub on `CH_JOB_ASSIGNED`, `CH_JOB_COMPLETED`, `CH_JOB_REASSIGNED`; loops forever until client disconnect (headers: no-store, `X-Accel-Buffering: no`) |
| 14 | POST `jobs/recover/` (:85-95) | Manage | `origin`, `limit` (body or query; default 50, clamped 1-100) | 202 `{recovered_jobs}`; 400 bad limit | `recover_stale_processing_jobs(origin, limit)` (service) |
| 15 | POST `jobs/bulk-stop/` (job_actions.py:50-72) | Auth | `ids` | `{stopped_count, skipped_complete, skipped_missing}` | `cancel_processing_job` per visible job |
| 16 | POST `jobs/bulk-resume/` (:75-101) | Auth | `ids` | 202 `{resumed_count, skipped_invalid, skipped_missing}`; 409 lock | `resume_processing_job` each |
| 17 | POST `jobs/bulk-delete/` (:104-125) | Auth | `ids` | `{deleted_count, skipped_active, skipped_missing}` | deletes non-active jobs (cascades logs) |
| 18 | DELETE `jobs/<uuid>/` (jobs.py:65-73) | Auth (visible jobs only) | - | 204; 400 if queued/processing. No GET on this path | deletes job |
| 19 | GET `jobs/<uuid>/logs/` (:76-82) | Auth (visible) | - | last... first 200 ProcessingLogSerializer (id, level, message, details, created_at) ascending | none |
| 20 | POST `jobs/<uuid>/resume/` (job_actions.py:33-47) | Auth; `can_manage_job` = staff or scope `processing.manage` or job's submitter | - | 202 job; 400 ValueError; 403; 409 lock | `resume_processing_job` |
| 21 | POST `jobs/<uuid>/stop/` (:23-30) | same as 20 | - | job | `cancel_processing_job` |

### Source catalog (views/catalog_entries.py, curation.py, incomplete_checks.py) - all Manage

| # | Method + path | Request | Response | Side effects |
|---|---|---|---|---|
| 22 | GET `catalog/entries/` (catalog_entries.py:67-187) | q (title/author icontains), status (computed per-entry curation_status incl. `deleted`), include_summary (default true), include_sync_state (default true), view=`overview`, sort (created_desc/asc, activity_desc/asc, title_asc/desc, default status priority), limit (180, max 400), page | `{entries[], pagination{page,limit,total_count,page_count,has_previous,has_next}, summary?, sync_state?}`; entry snapshot: id,title,author_line,categories,source_url,created_at,last_seen_at,curation_status,local_book_slug/title/state,latest_submission_status,latest_job_status,latest_job_error,activity_at,updated_at. Three code paths: overview (only entries with statuses failed/requeued, no paging), fast DB-paged path (no summary, status in {"" ,deleted}, fast sort), slow path (compute all snapshots in memory, filter, sort, slice) | none |
| 23 | DELETE `catalog/entries/<uuid>/` | - | 204 | hard-deletes the SourceCatalogEntry |
| 24 | POST `catalog/entries/bulk-delete/` | ids | `{deleted_count, skipped_missing}` | deletes entries |
| 25 | POST `catalog/entries/create-books/` (:216-268) | ids | 202 `{queued_creates, queued_updates, skipped_ready, skipped_processing, skipped_deleted (never incremented), skipped_missing, errors[<=20]}`; 409 if automation lock or refresh in progress | per entry: no local book or deleted -> `create_submission_records(submitter=user, url, auto_process, origin=CURATION)`; status unfinished/failed/stopped -> `queue_reprocess_book(book, origin=CURATION)`; processing -> skip |
| 26 | POST `catalog/refresh/` (curation.py:165-177) | `max_pages` (body or query, default 3, no upper bound here) | 202 SourceCatalogRefreshState (status, max_pages, task_id, queue_name, retry_count, refreshed_entries, last_error, requested_by_email, timestamps); 400 NaN; 409 lock | `begin_source_catalog_refresh` (service) sets singleton state and enqueues `refresh_source_catalog_task` |
| 27 | POST `catalog/refresh/stop/` (:180-184) | - | state | `cancel_source_catalog_refresh` |
| 28 | GET `catalog/incomplete-check/` (incomplete_checks.py:16-133) | q, status in removed/still/missing | `{summary{total_incomplete_books, removed_from_unfinished, still_in_unfinished, missing_in_catalog, queued, processing, failed, stopped}, entries[{book_id, book_title, book_slug, author_line, local_categories, source_url, source_categories, catalog_entry_id, removed_from_unfinished, latest_job_status, latest_job_error, updated_at}]}` | none. Finds non-deleted Books whose category names contain keywords `unfinished`, `অসম্পূর্ণ বই`, `অসম্পূর্ণ`; compares with the source catalog entry's `raw_data.category/book_type`. Summary computed before q/status filters. Loads all matching books unpaged |
| 29 | POST `catalog/incomplete-check/create-books/` (:136-165) | ids (book ids) | 202 `{queued_updates, skipped_processing, skipped_missing, errors}`; 409 lock | `queue_reprocess_book(..., origin=CURATION)` |
| 30 | GET `catalog/curation-runs/` (curation.py:31-54) | trigger, status, mode, q (requester email / last_error), limit (12, max 50) | list CatalogCurationRunSerializer | none |
| 31 | POST `catalog/curation-runs/` (:56-68) | `mode` (pending/all), `refresh_catalog` (true), `refresh_max_pages` (1-80, default 80) | 202 run; 409 lock | `create_catalog_curation_run` (service; creates run + enqueues `process_catalog_curation_run_task`) |
| 32 | DELETE `catalog/curation-runs/<uuid>/` (:78-86) | - | 204; 400 if queued/processing | deletes run |
| 33 | POST `catalog/curation-runs/<uuid>/stop/` (:71-75) | - | run | `cancel_catalog_curation_run` |
| 34 | POST `catalog/curation-runs/bulk-stop/` (:89-111) | ids | `{stopped_count, skipped_complete, skipped_missing}` | cancels |
| 35 | POST `catalog/curation-runs/bulk-delete/` (:114-135) | ids | `{deleted_count, skipped_active, skipped_missing}` | deletes |
| 36 | GET `catalog/automation/` (:138-149) | - | `{settings{enabled, daily_run_time, frequency, mode, refresh_max_pages, next_run_at}, latest_run}` (latest SCHEDULED run) | `get_catalog_automation_settings()` get-or-creates the singleton |
| 37 | PATCH `catalog/automation/` (:151-162) | partial of enabled, daily_run_time, frequency (daily/weekly/biweekly/monthly/bimonthly/quarterly/four_monthly/half_yearly), mode, refresh_max_pages (no max validation) | same as GET | saves with `updated_by=user` |

### Activity and duplicates

| # | Method + path | Permission | Request | Response | Side effects |
|---|---|---|---|---|---|
| 38 | GET `activity/` (views/activity.py) | Auth | - | `get_processing_activity_snapshot(user)` (service, not read) | none |
| 39 | GET `duplicate-reviews/` (duplicates.py:29-89) | Manage | origin, status (default `pending`), q (submission input, existing book title, notes), limit (40/200) | list DuplicateReviewSerializer (id, detected_by, status, notes, raw_evidence, submission{...}, existing_book{id,title,slug,authors,series}, existing_book_deleted, created_at) | none |
| 40 | POST `duplicate-reviews/<uuid>/resolve/` (:92-161) | Manage | `decision` in same_book / new_book / confirm_existing / dismiss (`same_book`==confirm_existing, `new_book`==dismiss), `notes` | review; 410 if existing book deleted on confirm; 409 lock | confirm: `fulfill_submission_with_existing_book(..., source="duplicate_review_confirmed", confidence=max(res_conf,0.95))`, sets `duplicate_of_book`, review CONFIRMED. dismiss: clears deleted/duplicate links, error_message and payload flags (`served_from_database`, `existing_book_source`, `linked_book_slug`), then if resolved_url or title input -> review_state PENDING + `queue_submission` (recreate) else status NEEDS_REVIEW; review DISMISSED |

Locks (views/guards.py): 409 "Automation is currently syncing the catalog..." when any SCHEDULED CatalogCurationRun is active; 409 "Catalog sync is currently running" when SourceCatalogRefreshState status is queued/processing (guards only used on endpoint 25; endpoint 26 only checks the automation lock).

Notable access rules (views/querysets.py): `get_accessible_submission` = manager OR submitter OR (`submitter is None` and `raw_payload.submitted_publicly`) else 403. Guests can therefore see, confirm candidates for, and get reader links for public submissions by UUID only.

## 3. Central Job Engine

### Purpose and shape
`engine/__init__.py` docstring: "replaces Celery dispatch with push-based event-driven architecture". In reality it is a hybrid: Celery still hosts the worker processes, but each Celery prefork child registers itself with the Engine and runs engine-assigned jobs from a background thread. Celery tasks (`process_submission_task`) still exist. Only Redis is used for engine state (plus Postgres rows for `ProcessingJob` / `BookCreationRequest`).

### Processes
1. **Engine process** (`python -m apps.ingestion.engine` or `manage.py run_engine [--heartbeat-timeout 15] [--check-interval 2]`): one `JobEngine` with two daemon threads (`engine-event-loop`: pub/sub `get_message(timeout=0.2)`, calls per-channel handler; `engine-stale-check`: sleep `check_interval`, `check_stale_workers`, then `_dispatch_pending_jobs` if any stale). Main thread blocks in `signal.pause()` (POSIX only). SIGINT/SIGTERM -> `engine.stop()`.
2. **Django web/API process**: `dispatch_job()` (publisher) and read helpers in `engine/api.py`; the SSE view subscribes to job events.
3. **Celery worker child processes** (`signals.py`): each child on `worker_process_init` registers as a worker named `celery-{host}-{pid}@worker`, starts two daemon threads (assignment listener on `CH_JOB_ASSIGNED`; heartbeat every 5 s). It executes the assigned job in the listener thread, then publishes `CH_WORKER_DONE`.
4. **Celery beat**: `send_worker_heartbeat_task` every 5 s (hostname `celery-beat-{host}-{pid}@beat`).

### Redis keys
- `engine:worker:{hostname}` HASH: hostname, capabilities (JSON list), pool_size, concurrency, status (idle/processing/stale/offline), current_job, registered_at, last_heartbeat (ISO UTC). No TTL.
- `engine:queue:pending` LIST of job ids (RPUSH to enqueue, LPUSH to requeue front, LINDEX 0 peek, LPOP to take).
- `engine:active` HASH job_id -> worker hostname.
- `engine:job:handlers` HASH job_id -> handler name (literal string used in code, not a constant). Never expires; removed only on done.
- `engine:state` / `ENGINE_STATE_KEY`: defined, unused.
- Constants: HEARTBEAT_TIMEOUT 15 s, CHECK_INTERVAL 2.0 s, ENGINE_POLL_INTERVAL 0.01 (unused), socket timeouts 5 s, default URL `redis://redis:6379/0`; `REDIS_URL` env, else `CELERY_BROKER_URL`.

### Pub/sub channels (all JSON payloads, `timestamp` ISO)
| Channel | Publisher | Subscriber | Payload |
|---|---|---|---|
| `engine:channel:worker:register` | celery child (`worker_process_init`) | engine | hostname, capabilities [`process_submission`,`pipeline`,`catalog_sync`,`curation`,`automation`], pool_size 1, concurrency 1 |
| `engine:channel:worker:heartbeat` | child heartbeat thread (5 s), Celery `heartbeat_sent` signal, beat task, `task_prerun` | engine | hostname (+ job_id/status on prerun, ignored by the engine) |
| `engine:channel:worker:deregister` | child shutdown | engine | hostname |
| `engine:channel:worker:done` | listener thread after job; `task_postrun` for any task with a first arg | engine | hostname, job_id, status (`succeeded`/`failed`), error_message, handler |
| `engine:channel:job:request` | `dispatch_job` | engine | job_id, job_type, handler, args, timestamp |
| `engine:channel:job:assigned` | engine | celery children + SSE | job_id, worker_hostname, handler |
| `engine:channel:job:reassigned` | engine (stale, recovery, `api.reassign_job`) | SSE | job_id, from_worker, (to_worker) |
| `engine:channel:job:completed` | engine on done | SSE | job_id, status, error_message |
| `engine:channel:worker:stale` | engine | nobody | hostname |
`ALL_CHANNELS` constant lists only 5 of 9, unused.

### Dispatch flow
1. Django creates a `ProcessingJob` (or `BookCreationRequest` in apps.processing) then `dispatch_job(job_id, job_type="reprocess", handler="process_submission")` (engine/dispatch.py): HSET handler, RPUSH `engine:queue:pending`, PUBLISH `job:request` (callers of dispatch_job live in services/processing, not read).
2. Engine `_handle_job_request` re-HSETs the handler and calls `_dispatch_pending_jobs()`.
3. `_dispatch_pending_jobs`: loop: LINDEX 0; look up handler (default `process_submission`); `find_idle_worker(required_capability=handler)` (SCANs all `engine:worker:*` keys, reads each hash; first idle one whose capabilities include the handler); if none, stop (strict FIFO head-of-line blocking: a job with no capable worker blocks all behind it); else LPOP, check same id (else LPUSH back), `assign_job` (HSET active, worker.current_job, status=processing), publish `job:assigned`, update `ProcessingJob.worker_hostname` (skipped if id is not a UUID, which is how a BookCreationRequest is distinguished).
4. The one celery child whose hostname equals `worker_hostname` runs the handler: `process_submission` -> `services.submissions.process_submission_job(job_id, retry_count=0, task_id="engine")`; `pipeline` -> `apps.processing.services.kickoff_request_processing(job_id)`; any other -> warning only, but still reports `succeeded`. Then publishes `worker:done`.
5. Engine `_handle_worker_done`: unassign, HDEL handler, worker -> idle/current_job "", publish `job:completed`, update `ProcessingJob.status` (+ `finished_at`, `last_error` if any), then dispatch pending.
6. Dispatch is also triggered by worker register, done, job request, and any stale detection. Not triggered by a plain heartbeat or a worker becoming idle through a stale->idle revival.

### Worker registry (`worker_registry.py`)
register (overwrites hash, status idle), deregister (if worker had a current job: RPUSH it to the back of pending, HDEL active, DEL hash), `update_heartbeat` (no-op returning False for unknown hostnames; flips `stale` back to `idle`), `set_worker_status`, `get_worker`, `get_all_workers` (SCAN count 100, then one HGETALL per key), `find_idle_worker`, `get_worker_count`.

### Stale detection (`stale_detector.py`)
Every `check_interval` (2 s): for each worker not `offline` and with a last_heartbeat: elapsed > timeout (15 s) -> status `stale`, publish `worker:stale`, for each active job of that worker: unassign, RPUSH to the back of the queue, publish `job:reassigned`. Unparseable timestamp -> elapsed 0 (never stale).

### Recovery (`recovery.py`, run once in `JobEngine.start`)
1. Workers whose status is offline/stale: set offline, unassign + requeue their active jobs.
2. Active jobs whose worker hash no longer exists: unassign + requeue.
3. DB reconciliation (inside try/except): `BookCreationRequest` in QUEUED/PROCESSING and `ProcessingJob` in queued/processing that are neither in the pending list nor in `engine:active` are re-queued (DB PROCESSING reverted to QUEUED first); handlers set to `pipeline` and `process_submission` respectively. Returns counts. After recovery the engine calls `_dispatch_pending_jobs`.

### Management API (`engine/api.py`)
`list_workers(status)`, `get_worker_detail`, `get_job_status` (only knows active jobs), `get_queue_depth`, `reassign_job`, `get_engine_status` (always `running: True`). Each opens and closes its own Redis client. No view or command in my scope calls these (dead from the HTTP surface).

### Relation to Celery
- Celery still: broker/result backend (same Redis URL, default db 0, so engine keys share the Celery DB), beat schedule, `process_submission_task` with retry/backoff (max attempts `MAX_PROCESSING_JOB_ATTEMPTS`), catalog tasks, `recover_stale_processing_jobs_task`.
- Engine replaces: dispatch of ProcessingJobs/BookCreationRequests to a free worker, and worker liveness tracking.
- Celery signals bridge into the engine (section 5). Both paths can run the same job (see bugs).
- `CELERY_TASK_ALWAYS_EAGER` default True outside production: in dev tasks run in the web process and the engine/worker path is not exercised.

## 4. Celery tasks and beat schedule

Celery app `bangla_library` (config/celery.py), config namespace `CELERY_*`, autodiscover. Worker settings: `worker_max_tasks_per_child=50`, `worker_max_memory_per_child=400000` KB, `worker_prefetch_multiplier=1`, `task_acks_late=True`.

Tasks (apps/ingestion/tasks.py):
| Task | Retry policy | What it does |
|---|---|---|
| `process_submission_task(job_id, attempt_offset=0)` | bind, retry_backoff+jitter, max_retries = MAX_PROCESSING_JOB_ATTEMPTS-1; manual `self.retry` unless attempts exhausted | `process_submission_job(job_id, retry_count, task_id)`; returns `{job_id, submission_id, book_id, status}` |
| `process_catalog_curation_run_task(run_id)` | autoretry any Exception, backoff, max 2 | `process_catalog_curation_run` |
| `refresh_source_catalog_task()` | autoretry, backoff, max 2 | `process_source_catalog_refresh`; returns state dict |
| `run_catalog_automation_schedule_task()` | none | `run_due_catalog_automation()`; swallows "schema not ready" DB errors (tables `ingestion_catalogautomationsettings`/`ingestion_catalogcurationrun`) and returns `{ran: False, reason: schema_not_ready}` |
| `recover_stale_processing_jobs_task()` | none | recovers up to 100 stale jobs total across origins USER then CURATION, then AUTOMATION only if automation settings `enabled` (schema-not-ready guard); returns `{recovered_jobs}` |
| `send_worker_heartbeat_task()` | none | publishes a heartbeat for pseudo-worker `celery-beat-...@beat` (see bugs) |

Beat schedule (config/celery.py:26-50):
| Entry | Task | Interval |
|---|---|---|
| run-catalog-automation-scheduler | apps.ingestion.tasks.run_catalog_automation_schedule_task | crontab() = every minute |
| run-processing-runtime-tick | apps.processing.tasks.run_processing_runtime_tick_task | 60 s |
| run-processing-automation-scheduler | apps.processing.tasks.run_due_processing_automations_task | every minute |
| run-processing-maintenance-scheduler | apps.processing.tasks.run_processing_maintenance_task | every minute |
| recover-stale-processing-jobs | apps.ingestion.tasks.recover_stale_processing_jobs_task | every minute |
| send-worker-heartbeat | apps.ingestion.tasks.send_worker_heartbeat_task | 5 s |
Processing tasks are in another app (not read).

## 5. Signals (signals.py, connected in `IngestionConfig.ready`)

| Signal | Handler | Effect |
|---|---|---|
| `worker_process_init` | on_worker_process_init | publish `worker:register`; start listener + heartbeat threads |
| `worker_process_shutdown` | on_worker_process_shutdown | stop threads (join 3 s / 6 s), publish `worker:deregister`, close Redis |
| `heartbeat_sent` (Celery worker-level heartbeat) | on_heartbeat_sent | publish `worker:heartbeat` for this child hostname |
| `task_prerun` | on_task_prerun | if `args[0]` exists: publish heartbeat with job_id and status "processing" (engine ignores the extras; docstring claims "claim job") |
| `task_postrun` | on_task_postrun | if `args[0]` exists: publish `worker:done` with status `succeeded` if state == SUCCESS else `failed` (error text from retval when FAILURE) |
No Django model signals (post_save etc.) exist in this scope. The module name `signals.py` is Celery signals only.

## 6. Management commands

- `run_engine [--heartbeat-timeout 15] [--check-interval 2]`: builds Redis client + JobEngine, starts it, installs SIGINT/SIGTERM handlers calling `engine.stop()`, blocks on `signal.pause()`.
- `process_legacy_batch [--url URL ...] [--sync]`: if no `--url`, uses `legacy_config_entries_as_submission_inputs()` (old scraper config). Creates submissions with `auto_process=False`; skips unresolved; `--sync` creates a `ProcessingJob(INGESTION)` and runs `process_submission_job` inline, else `queue_submission` and prints the job id.
- `curate_source_site_books` (509 lines): resumable batch curation of catalog entries into "curated documents".
  - Options: `--source-url` (repeatable), `--discover` (runs `TitleResolver().refresh_catalog`, `--max-pages` 0 = unlimited), `--offset`, `--limit`, `--batch-size 50`, `--all-remaining`, `--resume-after URL`, `--skip-existing`, `--continue-on-error`, `--strict-verification`, `--require-validated`, `--require-catalog-match`, `--dry-run`, `--generate-assets`, `--force-generate-assets`, `--require-assets`, `--perfect` (implies strict + validated + catalog match + assets, forbids skip-existing), `--report-path` (JSON), `--last-chapter-title`.
  - URL selection: explicit URLs, else SourceCatalogEntry ordered by source_url, filtered by `--resume-after`, sliced.
  - Per URL: optional skip if a CuratedBookDocument exists; DiskPageCache (md5 of URL, `curate_cmd_<hash>.jsonl` in the scrape cache root); `curate_book_document(url, content_limits, page_cache)`; `verify_curated_result` (recompute validation, title/structure present, content_items or main_content non-empty, body sections with text, no duplicate content paths, persisted-vs-projection equality of title, content, TOC, content_items, content summary counts, curated section/entity/evidence counts); `catalog_mismatch_errors` against the SourceCatalogEntry (title exact-normalised, author/series/category fuzzy contains). Gates: require-validated, require-catalog-match, strict verification raise CommandError.
  - Persist (unless dry-run): invalid with no title -> persist document only; else `persist_curated_book` (optionally in `transaction.atomic()` when strict or require-assets), post-persist verification, optional asset generation (`generate_exports` + `sync_assets`; only for validated, or review_required with force; failure marks book NEEDS_REVIEW), then `book_quality_gate`: fail -> book ARCHIVED + review REJECTED ("quarantined"). Summary counters and per-URL results written to the report after every URL; DEBUG query logging disabled and DB connections/GC cleaned each iteration.

## 7. Settings and environment variables (config/settings.py)

Helpers: `env`, `env_bool` (1/true/yes/on), `env_int`, `env_list` (comma). Env names with defaults:

| Env var | Default | Meaning |
|---|---|---|
| APP_ENV | development | "production" flips DEBUG and eager defaults |
| DJANGO_DEBUG | APP_ENV != production | debug |
| DJANGO_SECRET_KEY | `development-only-insecure-secret-key` | secret (insecure default, no failure in production) |
| PUBLIC_BASE_URL | http://localhost | base |
| FRONTEND_BASE_URL | PUBLIC_BASE_URL | used in reader launch URLs, CORS/CSRF origin |
| FRONTEND_PORT | "" | unused in this scope |
| PUBLIC_API_ORIGIN | PUBLIC_BASE_URL | API origin; added to allowed hosts/CORS/CSRF |
| DJANGO_ALLOWED_HOSTS | localhost,127.0.0.1,backend,nginx (+hosts from the two URLs) | |
| DJANGO_CSRF_TRUSTED_ORIGINS | "" (+ the two origins; in DEBUG localhost/127.0.0.1 ports 5173-5181) | |
| DJANGO_CORS_ALLOWED_ORIGINS | "" (same additions) | |
| DJANGO_CORS_ALLOW_CREDENTIALS | true | |
| PASSWORD_CREATE_FRONTEND_PATH | /create-password | invite link path |
| PASSWORD_RESET_FRONTEND_PATH | /reset-password/confirm | reset link path |
| PASSWORD_RESET_TIMEOUT | 21600 s (6 h) | |
| SUPER_ADMIN_EMAIL / SUPER_ADMIN_PASSWORD | library@rsalehin24.me / "" | seeded admin |
| DEMO_USER_EMAIL / DEMO_USER_PASSWORD | demo_user.library@rsalehin24.me / a hard-coded real-looking password in the source default | demo account (secret in code) |
| SOURCE_SITE_EMAIL / SOURCE_SITE_PASSWORD | "" | credentials for the scraped source site |
| SOURCE_SITE_HOST / SOURCE_SITE_FALLBACK_HOSTS | "" | source site hosts |
| SOURCE_SITE_AUTH_STATE_PATH | RUNTIME_STORAGE_DIR/source_site_auth.json | cookie state file |
| DEFAULT_FROM_EMAIL | RSalehin24 Library <library@rsalehin24.me> | |
| OTP_TOTP_ISSUER | RSalehin24 Library | TOTP issuer |
| CATALOG_EXPORT_FONT_PATH | "" | font for catalog export PDF |
| DATABASE_URL | postgresql://postgres:postgres@postgres:5432/bangla_library | only postgres schemes supported |
| DB_CONN_MAX_AGE | 60 | (+ CONN_HEALTH_CHECKS True) |
| TIME_ZONE | Asia/Dhaka | USE_TZ true |
| THROTTLE_LOGIN / REGISTER / PASSWORD_RESET / SUBMISSION | 10/hour, 5/hour, 5/hour, 40/hour | DRF throttle rates |
| RUNTIME_STORAGE_DIR | backend/storage | base for static and media |
| STATIC_ROOT / MEDIA_ROOT | RUNTIME_STORAGE_DIR/staticfiles, /media | |
| SESSION_COOKIE_SAMESITE / CSRF_COOKIE_SAMESITE | Lax | |
| SESSION_COOKIE_SECURE / CSRF_COOKIE_SECURE | true when any public URL is https | |
| DJANGO_USE_X_FORWARDED_HOST | true | |
| DJANGO_SECURE_PROXY_SSL_HEADER | true | trust X-Forwarded-Proto |
| CELERY_BROKER_URL | redis://redis:6379/0 | also fallback for REDIS_URL |
| CELERY_RESULT_BACKEND | CELERY_BROKER_URL | |
| PROCESSING_CHECKPOINT_REDIS_URL | CELERY_BROKER_URL | checkpoint store (apps.processing) |
| CELERY_TASK_ALWAYS_EAGER | APP_ENV != production | run tasks inline |
| PROCESSING_USE_LIVE_SYNC | true | processing flag (apps.processing) |
| PROCESSING_INLINE_PIPELINE_ADVANCE | false | processing flag |
| CELERY_PROCESSING_CONCURRENCY | 5 | worker concurrency (consumed outside settings) |
| REDIS_URL | (engine only) | overrides broker URL for the engine |
| BREVO_API_KEY | "" | enables Anymail Brevo backend |
| EMAIL_BACKEND | brevo if key else console | |
| EMAIL_HOST / PORT / HOST_USER / HOST_PASSWORD / USE_TLS / USE_SSL / TIMEOUT | "" / 587 / "" / "" / true / false / 20 | SMTP |
| BREVO_SENDER_EMAIL | "" | |
| ACCOUNT_INVITE_FROM_EMAIL | BREVO_SENDER_EMAIL or DEFAULT_FROM_EMAIL | |
| LOG_LEVEL | INFO | root logger |

Other fixed settings: installed apps (admin, auth, contenttypes, sessions, messages, staticfiles, anymail, corsheaders, rest_framework, django_filters, django_otp + otp_totp, apps.common, accounts, catalog, ingestion, processing, access); middleware includes corsheaders, Security, Session, Common, CSRF, Auth, `django_otp.middleware.OTPMiddleware`, custom `RequireTotpSetupMiddleware`; `AUTH_USER_MODEL=accounts.User`; ModelBackend; four password validators; `X_FRAME_OPTIONS=DENY`; `SECURE_BROWSER_XSS_FILTER` (obsolete); DRF: SessionAuthentication, AllowAny default, DjangoFilterBackend, JSON renderer; templates dir `backend/templates`; static dir `backend/static`; logging to console. Root URLs (config/urls.py): `admin/`, `api/` (common), `api/auth/`, `api/catalog/`, `api/ingestion/`, `api/processing/`, `api/access/`; media served only if DEBUG. wsgi/asgi are stock.

## 8. Other features: models, admin

Models (ingestion app, all UUID PK + created/updated):
- `SourceCatalogEntry`: source_url (unique, 1000), title, author_line, normalized_title/normalized_display (indexed), raw_data JSON, last_seen_at (auto_now).
- `BookSubmission`: submitter (nullable), input_type (url/title/csv), origin (user/curation/automation), original_input, normalized_input, resolved_url, resolution_status (unresolved/resolved/exact_match/ambiguous/rejected/invalid), resolution_confidence, status (draft, pending_resolution, queued, processing, needs_review, ready, failed, cancelled, duplicate, deleted), review_state, linked_book, duplicate_of_book, canonical_submission (self FK, dedup), raw_payload, error_message. `save()` override: when submitter and linked_book are set/changed it get_or_creates a `catalog.UserBook` (adds the book to the submitter's library) and runs an extra SELECT per save.
- `TitleResolutionAttempt` (query, status, confidence, resolved_url, raw_results, error) and `MatchCandidate` (rank, candidate title/author/url, confidence, metadata, is_selected).
- `ProcessingJob`: submission, book, job_type (resolution/ingestion/reprocess), status (queued/processing/succeeded/failed/cancelled), task_id, queue_name, worker_hostname, retry_count, cancel_requested, payload, last_error, started/finished. `ProcessingLog`: job, level, message, details. `DuplicateReview`: submission, existing_book, detected_by (default exact_source_url), status (pending/confirmed/dismissed/merged), notes, raw_evidence.
- `CatalogAutomationSettings` singleton (enabled False, daily_run_time 02:00, frequency, mode pending/all, refresh_max_pages 80, updated_by). `SourceCatalogRefreshState` singleton (status idle/queued/processing/succeeded/failed, max_pages 80, task_id, queue_name, retry_count, refreshed_entries, last_error, requested_by, started/finished). `CatalogCurationRun` (trigger manual/scheduled, mode, status, refresh_catalog, refresh_max_pages, requested_by, task_id, queue_name, retry_count, cancel_requested, summary JSON, last_error, started/finished).
- Choice enums are in models/choices.py; `SubmissionOrigin` USER/CURATION/AUTOMATION.

Admin: default `ModelAdmin` for SourceCatalogEntry, BookSubmission, TitleResolutionAttempt, MatchCandidate, ProcessingJob, ProcessingLog, DuplicateReview. Not registered: CatalogAutomationSettings, CatalogCurationRun, SourceCatalogRefreshState.

Serializer/filter details worth keeping: text search tries three variants (raw, hyphenated, URL-encoded) because source URLs are slugs; Bengali keywords for "unfinished" category detection; list queries defer heavy Book columns (summary, raw_scraped_metadata, raw_scrape_payload, main_content_html, book_info_html, dedication_html, toc, content_items) - a sign the Book table stores whole book HTML/JSON in the row.

## 9. Bugs, dead code, duplication, surprises

Engine correctness
1. **Two threads dispatch concurrently**: `_dispatch_pending_jobs` is called from the event-loop thread and the stale-check thread. The code comment "engine is single-threaded" is false. `find_idle_worker` -> `assign_job` is not atomic; double-assignment or LPOP/requeue shuffle possible. No leader lock either, so two engine instances double-dispatch.
2. **Pub/sub is fire-and-forget**: a `job:assigned` message published while the target child is not yet subscribed, restarting, or Redis blips is lost; the job stays in `engine:active` and the worker `processing` until the worker goes stale (15 s without heartbeat) - but heartbeats continue, so the job can be stuck forever. Same for `done` lost. `register` lost -> worker never known (heartbeat for unknown host is a no-op).
3. **Done is published twice / for unrelated tasks**: `task_postrun` publishes `worker:done` for any Celery task whose first positional arg exists (including `run_id` of curation, `attempt_offset`-style args) and the listener thread also publishes done for engine jobs. Engine then marks that worker idle (even mid-engine-job), and overwrites `ProcessingJob.status` with `succeeded`/`failed` and `finished_at`. A Celery retry (state RETRY) maps to `failed` and writes `failed` into the DB while the retry is pending. `_update_db_job_status` also overwrites a user-cancelled job.
4. **Engine "succeeded" regardless of outcome for unknown handlers** (warning only). Capabilities list `catalog_sync`, `curation`, `automation` have no handler.
5. **Heartbeat beat task is useless**: it heartbeats a hostname that never registers, so `update_heartbeat` returns False. It only costs a Redis connection every 5 s. Also the real heartbeat is published 3 ways per child (thread, `heartbeat_sent`, plus prerun).
6. **Stale spam**: stale workers are never deleted or marked offline in the runtime loop; each 2 s cycle re-evaluates them (status stale, not offline), republishes `worker:stale` and re-calls dispatch. Dead workers accumulate in Redis forever (no TTL), and `find_idle_worker`/`get_all_workers` scan cost grows (SCAN + HGETALL per key on every dispatch).
7. **Revived stale worker duplicates work**: a heartbeat flips `stale` -> `idle` while its job was already reassigned elsewhere; the old child may still be running the job (duplicate execution).
8. **Recovery can duplicate Celery work**: DB reconciliation re-queues every ProcessingJob in `queued`/`processing` not in Redis, including ones legitimately waiting in the Celery broker (the `process_submission_task` path), so the same job can run via both mechanisms. The reconciliation also runs only at engine start, not periodically.
9. `deregister_worker` and stale requeue use RPUSH (back of queue) despite `requeue_job` existing to preserve order; `recover_state` also uses enqueue (back). Head-of-line blocking: one job requiring a missing capability blocks the whole queue.
10. `api.reassign_job` assigns in Redis and publishes `job:reassigned`, but workers listen for `job:assigned`, so the target never runs it; no capability or status check on the target. Whole `api.py` is unreferenced in this scope; `get_engine_status` hard-codes `running: True`.
11. Dead code: `JobEngine._try_assign_job`, `job_queue.dequeue_job/requeue_job/get_active_job_worker` (partly used by api), `ENGINE_STATE`, `ENGINE_STATE_KEY`, `ENGINE_POLL_INTERVAL`, `ALL_CHANNELS`, `WORKER_STATUS_CHOICES`, `CH_WORKER_STALE` (no subscriber), `last_heartbeat_str` unused in recovery, `now_iso` duplicated in 4 modules, `set_worker_status/set_worker_current_job` duplicated in `job_queue` and `worker_registry`, `from .constants import *` everywhere.
12. `engine:job:handlers` hash is leaked for jobs that are cancelled or deleted while queued (no cleanup), and the literal key string is repeated in 4 places.
13. Engine shares Redis DB 0 with Celery; `__main__` uses `signal.pause()` (not Windows-safe); `stop()` does not join the stale thread; `run_engine` option types int only.
14. `engine` imports `apps.processing.models` in recovery: ingestion depends on processing, while processing is presumably dependent on ingestion (circular coupling).
15. Jobs assigned to a worker run in the listener thread of a Celery prefork child while Celery itself may also hand that child a task: the engine's idea of "idle" is blind to Celery-delivered tasks. `max_tasks_per_child=50` recycles children frequently, causing register/deregister churn and requeue of in-flight jobs on shutdown.
16. Engine-run jobs get `retry_count=0, task_id="engine"` and no retry/backoff, unlike `process_submission_task`.

API
17. `SubmissionRetryView` uses `.get(pk=pk)` -> 500 on missing/not visible. `SubmissionConfirmCandidateView` with a malformed `candidate_id` raises a Django ValidationError -> 500.
18. `can_manage_job` (job_actions) differs from `can_manage_processing_records` used for visibility; bulk stop/resume use the visibility queryset instead of `can_manage_job`, so rules diverge between single and bulk endpoints.
19. Public/anonymous surface: POST submissions, GET detail, POST status, confirm-candidate, action-links (issues reader preview tokens) are all unauthenticated and protected only by UUID secrecy plus a 40/hour throttle on POST create.
20. `SourceCatalogRefreshView` has no upper bound on `max_pages` (curation serializer caps at 80); `CatalogAutomationSettingsUpdateSerializer` has no range validation; stop views never check state; `skipped_deleted` summary key never incremented; guards inconsistent (only create-books checks sync lock).
21. SSE stream holds one gunicorn worker and one Redis connection per client indefinitely, broadcasts all job events to every manager with no per-user filtering; `EventStreamRenderer` defined mid-file between imports.
22. `views/__init__.py` re-exports `create_catalog_curation_run`, `queue_submission`, `create_submission_records` and sibling modules call them via `ingestion_views.<name>` solely so tests can monkeypatch; circular-import smell.
23. Catalog entry list slow path computes every snapshot in memory then slices; incomplete-check loads all books; both unpaged scale poorly. Three divergent code paths in one view.
24. `jobs/<pk>/` has DELETE only (no GET); `ProcessingJobSerializer` N+1 risk avoided only by prefetch.
25. Status vocabulary leak: DB `cancelled` presented as `stopped` and filters translate back; `unfinished` etc. are computed statuses in services.

Config
26. Defaults are unsafe-by-default: insecure `SECRET_KEY` fallback, `DEBUG=True` unless `APP_ENV=production`, `CELERY_TASK_ALWAYS_EAGER=True` unless production, DRF default `AllowAny`, a demo-user password committed as a default, a real super-admin email default.
27. No HSTS/secure redirect settings, deprecated `SECURE_BROWSER_XSS_FILTER`, no caching, no DRF pagination, no health endpoint listed (maybe in `apps.common`).
28. Settings consumed outside scope: `PROCESSING_*`, `CELERY_PROCESSING_CONCURRENCY`, `SOURCE_SITE_*`, `OTP_TOTP_ISSUER`, `CATALOG_EXPORT_FONT_PATH`.
29. Two heartbeat/liveness concepts exist (Celery's own `heartbeat_sent` and the engine's); beat entries named "processing" tick/automation/maintenance overlap conceptually with ingestion's recover and automation tasks (duplication across the two apps).
30. `process_legacy_batch` and the `curate_source_site_books` command refer to "legacy" scraper config and "curated documents" (a second ingestion model - `CuratedBookDocument`) separate from the submission/job pipeline: two parallel ingestion paths (job-based vs curated document batch).
31. `curate_source_site_books` mutates `settings.DEBUG` globally; uses an md5-keyed disk cache; `continue` inside `try/finally` still writes report each iteration (O(n^2) writes of the growing JSON).

## 10. Unread files and reasons
None in the assigned scope. Not opened by design: `.env` files; `apps/ingestion/services/`, `pipeline/` (other agents); `apps/common/*` (permissions, throttles, middleware), `apps/processing/*` (tasks `run_processing_*`, `kickoff_request_processing`, `BookCreationRequest`), `apps/catalog`, `apps/access` models. Behaviour attributed to those is inferred from names only and is marked "(service, not read)" above.
