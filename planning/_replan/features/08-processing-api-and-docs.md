# 08 - Processing: API surface, models, docs (legacy `archive/app/backend/apps/processing`)

Status: DRAFT (research evidence; read-only record)

Scope: everything in `processing/` except `service_modules/` and `migrations/` (those are another reader's). Read-only. Four small greps into service_modules/common (constants, `CanManageProcessing`, `allow_processing_remote_page_payloads`, root urls) were used only to resolve names; flagged "(grep)".

URL prefix: `config/urls.py:12` mounts `api/processing/` (grep). All paths below are relative to `/api/processing/`.

## 1. Coverage table

| file | lines | fully read |
|---|---|---|
| processing/__init__.py | 1 | yes |
| processing/admin.py | 115 | yes |
| processing/apps.py | 8 | yes |
| processing/models.py | 240 | yes |
| processing/services.py | 39 | yes |
| processing/source.py | 205 | yes |
| processing/tasks.py | 57 | yes |
| processing/views.py | 15 | yes |
| processing/view_modules/read_stream_and_sync_start_views.py | 260 | yes |
| processing/view_modules/sync_action_and_automation_views.py | 153 | yes |
| processing/serializers.py | 251 | yes |
| processing/urls.py | 39 | yes |
| processing/management/__init__.py, commands/__init__.py | 0 | yes (empty) |
| processing/management/commands/backfill_multi_page_toc.py | 150 | yes |
| docs/processing-pages-reference.md | 576 | yes |
| docs/processing-use-cases.md | 116 | yes |
| docs/processing-user-stories.md | 54 | yes |
| docs/processing-pages-implementation-audit.md | 433 | yes |
| docs/processing_pages.txt | 766 | yes |
| docs/processing-live-test-matrix.md | 60 | yes |

Code total 1533 lines (13 files), docs 2005 lines (6 files). 19/19 non-empty files read in full.

## 2. HTTP endpoints (17 route entries, 16 distinct view classes/behaviours)

All views: DRF `APIView`, `permission_classes=[CanManageProcessing]` (= scope `PermissionScope.PROCESSING_MANAGE`, common/permissions.py:135 (grep)). Every response goes through `processing_response()` (read_stream...views.py:95) which adds `Cache-Control: no-store, no-cache, must-revalidate, max-age=0` and `Pragma: no-cache` (except the stream, which sets its own plus `X-Accel-Buffering: no`). Mutations are wrapped in `collect_processing_ui_version_updates()` and return the standard mutation payload `{"ok": true, "versions": {<cardKey>: int,...}}` (only keys in `PROCESSING_CARD_KEYS` kept, :109-120) plus `extra`. `versions` = new UI-domain version numbers touched by that call, so the client knows which cards to refetch.

Files: R = view_modules/read_stream_and_sync_start_views.py, S = view_modules/sync_action_and_automation_views.py (S has no imports of its own; it relies on the exec-into-shared-globals facade in views.py, so it cannot be imported standalone).

| # | Method | Path | Params | Response | Side effects | file:line |
|---|---|---|---|---|---|---|
| 1 | GET | `state/` | `includeLists` (bool, default true; 1/true/yes/on, 0/false/no/off; else default) | `processing_state_payload(include_lists)` (shape in service_modules; serializer `ProcessingStateSerializer` = records, requests, sync, automation exists but the view does not use it) | none | R:133-143 |
| 2 | GET | `card/` | `card` required, else 400 `{"card":["This query parameter is required."]}`; unknown card -> KeyError -> 400 "Unsupported processing card: X" | `processing_card_payload(card)` (overview/aggregate payload) | none | R:146-159 |
| 3 | GET | `table/` | `card` required; `q` (default ""), `category`, `status`, `offset` (int >=0, default 0), `limit` (int, default 60, min 1, max 600), `includeFacets` (bool default true). Unknown card -> 400 "Unsupported processing table" | `processing_table_payload(...)` | none | R:207-240 |
| 4 | GET | `stream/` | `page` (default `catalog`; must be a key of `PROCESSING_PAGE_DOMAINS` = catalog, create, on-hold, incomplete (grep); else 400 "Unsupported processing page") | Server-Sent Events (`text/event-stream`, custom `EventStreamRenderer`). Sends `event: connected\ndata: {}`; then polls DB domain versions every 1 s; on change `event: versions\ndata: {"eventId": <ms epoch>, "versions": {domain: version,...}}`; sends `: keepalive` comment after 15 s idle | none (read); holds one worker thread per connection forever (infinite generator, sync `time.sleep`) | R:162-204 |
| 5 | POST | `sync/start/` | body `{remotePages?: list[list[dict]]}`; `remotePages` only honoured if `allow_processing_remote_page_payloads()` (setting `PROCESSING_ALLOW_REMOTE_PAGE_PAYLOADS` or pytest loaded or `PYTEST_CURRENT_TEST` env) (grep), otherwise ignored | mutation payload | `run_manual_catalog_sync(remote_pages or None)`: starts manual catalog sync (Celery) | R:243-260 |
| 6 | POST | `sync/pause/` | none; scope = `active_sync_scope()` | mutation payload | `pause_sync(scope)` | S:3-18 (route urls.py:27) |
| 7 | POST | `sync/resume/` | optional body `runMode` in {manual, catalog_automation, incomplete_automation}; default = `sync_run_mode(get_sync_state(scope))`; invalid -> 400 `{"runMode":[...]}`. Note: `request.data.get` only if `request.data` is a dict | mutation payload | `resume_sync(scope, run_mode=...)` | S:21-42 (urls.py:28) |
| 8 | POST | `sync/stop/` | none; scope = `active_sync_scope()` | mutation payload | `stop_sync(scope)` | S:45-60 (urls.py:29) |
| 9 | POST | `sync/<slug:scope>/pause/` | scope in {catalog, incomplete} else 400 `{"scope":[...]}` | same as 6 | same | urls.py:30 |
| 10 | POST | `sync/<scope>/resume/` | as 7 | same | same | urls.py:31 |
| 11 | POST | `sync/<scope>/stop/` | as 8 | same | same | urls.py:32 |
| 12 | POST | `records/create-requests/` | body `{ids: non-empty list[str]}` (BulkIdsSerializer; empty list -> 400) | mutation payload + `createdCount` | `create_requests_for_record_ids(ids, actor=request.user)` creates BookCreationRequest rows for BookRecord ids | S:63-79 |
| 13 | POST | `requests/action/` | body `{ids: non-empty list[str], action: delete\|pause\|resume\|retry\|force_generate\|new\|new_edition\|confirm_duplicate\|create_again\|recreate, deleteBook: bool default false}`. `ValueError` from service -> 400 `{"detail": msg}` | mutation payload + `changedCount` | `apply_request_action(ids, action, delete_book=, actor=)`: state transitions on requests (see section 3 rules); `deleteBook` can delete the linked catalog Book | S:82-103 |
| 14 | POST | `automation/catalog/` | body `{enabled?: bool, interval?: str non-blank, time?: HH:MM[:SS]}` all optional | mutation payload | `update_automation_settings(CATALOG, data)` (upserts ProcessingAutomationSettings, sets `saved`) | S:106-123 |
| 15 | POST | `automation/catalog/run/` | none | mutation payload | `run_catalog_automation()` | S:130-140 |
| 16 | POST | `automation/incomplete/` | same body as 14 | mutation payload | `update_automation_settings(INCOMPLETE, data)` | S:106-127 |
| 17 | POST | `automation/incomplete/run/` | none | mutation payload | `run_incomplete_automation()` | S:143-153 |

Notes:
- There is NO endpoint to read automation settings, list runs, delete a catalog row, create a book from a catalog row, review a title-match, or delete run history; those appear in the reference docs only for the older (pre-refactor) model. Reads of automation are via `state/` / `card/`.
- Only GET and POST are used; no PUT/PATCH/DELETE. All deletions are `requests/action` with `action=delete`.
- `ProcessingStateSerializer`, `BookCreationRequestSerializer`, `BookRecordSerializer`, `ProcessingSyncStateSerializer`, `ProcessingAutomationSettingsSerializer` are imported/used by the services layer (serializers.py imports `latest_request_for_record`, `record_is_selectable`, `sync_run_mode` from services - circular-ish: services -> serializers -> services, works only because of lazy exec/facade).
- Serialization shapes (camelCase), serializers.py:
  - BookRecord: id, name, url, displayUrl (unquoted), displayPath (unquoted path, or netloc), category, writer, translator, composer, publisher, createdAt, updatedAt, bookCreationState, linkedBookId, linkedBookSlug (null if linked book soft-deleted), wasIncomplete, resolvedFromIncomplete, willResolveToCategory, isDuplicate, duplicateOfRecordId, selectable (= `record_is_selectable`), latestRequestId (per-row query `latest_request_for_record`, N+1).
  - BookCreationRequest: id, bookRecordId, state, createdAt, updatedAt, progress (see rule below), errorMessage, isResumed, isConfirmedNotDuplicate, duplicateOfRequestId, duplicateOfRecordId, duplicateConfirmed, linkedBookId, linkedBookSlug (falls back to the record's linked book), pipelineOutcome, hasMultiPageToc, sourceTocPageCount, fetchedTocPageCount.
    - `progress` is exposed only when state==paused (full JSON) or state==failed with `progress.curatedValidation` (then only `{curatedValidation, curatedStatus}`); otherwise null.
  - SyncState: status, progress, fetchedCount, skippedCount, updatedCount, appendedCount, message, remotePages, pageIndex, runMode (derived), phase (= progress.phase or "sync").
  - AutomationSettings: kind, enabled, interval, time, saved, lastRunAt, statusMessage.

### Data model (models.py)
- `BookRecord`: id str PK (uuid4 str, max 120), name, url (unique, 1000), category, writer/translator/composer/publisher (blank ok), `book_creation_state` (not_created, initial, queued, processing, created, paused, failed, duplicate, deleted; indexed; default not_created), `linked_book` FK catalog.Book SET_NULL, was_incomplete, resolved_from_incomplete, will_resolve_to_category, is_duplicate, `duplicate_of_record` self FK SET_NULL, `source_catalog_entry` FK ingestion.SourceCatalogEntry SET_NULL. Ordering name,id. Timestamps via TimeStampedModel.
- `BookCreationRequest`: id str PK, `book_record` FK CASCADE, `state` (initial, queued, processing, created, paused, failed, duplicate, deleted; indexed), `origin` (user | curation | automation; default "curation"; indexed), progress JSON null, error_message, is_resumed, is_confirmed_not_duplicate, force_generate, duplicate_of_request (self FK), duplicate_of_record (FK BookRecord), duplicate_confirmed, has_multi_page_toc (indexed), source_toc_page_count (default 1), fetched_toc_page_count (default 1), `linked_book` FK catalog.Book, `submission` OneToOne ingestion.BookSubmission (SET_NULL), `pipeline_outcome` (char 32, default "created"). Ordering -updated_at,-created_at,id.
- `ProcessingSyncState`: singleton by `singleton_key` (unique, default "default"; keys used in code: "catalog", "incomplete"), status (idle, syncing, pausing, paused), progress JSON, remote_pages JSON list, page_index, fetched/skipped/updated/appended counts, message (default "Ready to sync."), task_id, queue_name, last_error.
- `ProcessingAutomationSettings`: kind (catalog | incomplete, unique), enabled (default False), interval (default "daily"), time (default 02:00), saved, last_run_at, status_message.
- `ProcessingUiDomainVersion` (domain unique, version bigint) - per-card monotonically increasing counters; the SSE stream polls this table.
- `ProcessingUiProjection` (key unique, payload JSON) - cached projections.
- Admin (admin.py) registers all 6 models with list_display/filters/search; raw_id_fields on FKs.

### Celery tasks (tasks.py)
- `run_processing_sync_task(singleton_key="catalog")` bound; calls `run_processing_sync_until_blocked(singleton_key, task_id)` -> returns `sync_state_task_payload`.
- `kickoff_book_creation_request_task(request_id)` bound, `acks_late=True`, `reject_on_worker_lost=True`; `kickoff_request_processing(request_id)`; if request row missing returns `{request_id, state: "deleted", submission_id: "", missing: true}`; else `{request_id, state, submission_id}`.
- `run_due_processing_automations_task()` -> `run_due_processing_automations()` (beat-driven scheduler).
- `run_processing_maintenance_task()` -> `run_processing_maintenance()` (stale recovery etc.).
- `run_processing_runtime_tick_task()` -> `run_processing_runtime_tick()` (pipeline advance).
- No explicit beat schedule in these files (beat config is elsewhere).
- Module alias `run_processing_sync = run_processing_sync_until_blocked` (tasks.py:14), used by the task (tests probably patch it).

### source.py (scrape/curate adapter)
Thin adapter over ingestion pipeline:
- `capture_source_page_metadata(url)`: fetch metadata, upsert SourceCatalogEntry; swallows ALL exceptions -> returns None.
- Limit builders reading Django settings: `processing_scrape_limits` (PROCESSING_SCRAPER_MAX_NODES=48, MAX_DEPTH=3, MAX_LESSON_PAGES=2, MAX_CONTENT_CHARS=12000, DISABLE_RECURSIVE=False), `high_fidelity_scrape_limits` (scraper defaults, recursion on), `processing_curate_limits` (PROCESSING_CURATE_MAX_NODES=None/unlimited, MAX_DEPTH=6, MAX_LESSON_PAGES=20, MAX_CONTENT_CHARS=60000, recursion on; bad int -> None).
- `scrape_book`, `scrape_book_high_fidelity`, `curate_book(url, high_fidelity, content_limits, page_cache)` (-> `curate_book_document`), `generate_exports` (html_book + epub), `detect_metadata_duplicate`, `find_exact_existing_book`, `sync_metadata_relations` (replace_book_relations: contributors, series, categories), `persist_scraped_book`, `persist_curated_book` (uses `submission.resolved_url`), `sync_assets` (requires generated asset types HTML and EPUB).
- Both a legacy "scrape" path and a newer "curate" path exist side by side.

## 3. Pages / cards / tables / buckets (from docs; current four-page model, validated 2026-05-27)

Routes: `/catalog`, `/create`, `/on-hold`, `/incomplete` + standalone `/multipage-toc` and `/reprocessing` (described only as one-liners: "multi-page TOC processing for complex TOCs", "book reprocessing queue"; no columns/actions documented). Old routes redirect: `/processing-catalog-books`,`/processing-automation` -> `/catalog`; `/processing-my-requests` -> `/create`; `/processing-failed-requests`,`/processing-duplicate-requests` -> `/on-hold`; `/processing-incomplete-check` -> `/incomplete`. Card keys per page (backend, grep): catalog = {catalog-overview, catalog-sync, catalog-automation, catalog-records}; create = {create-overview, create-requests, create-queue, create-processing, create-created}; on-hold = {on-hold-overview, on-hold-paused, on-hold-failed, on-hold-duplicate, on-hold-deleted}; incomplete = {incomplete-overview, incomplete-automation, incomplete-records, incomplete-completed (= "Updated")}.

Request state machine: initial -> queued -> processing -> created. Holding: paused (resumable). Terminal: created, failed, duplicate, deleted. Active: initial, queued, processing. BookRecord.bookCreationState mirrors the active request state, plus `not_created`.

Shared UI rules (processing_pages.txt Part 2): checkbox column only on cards with at least one action (Incomplete card has none); during an action all checkboxes/buttons in THAT card disabled, other cards stay interactive; per-card loader, per-card server-side search (name, writer, translator, publisher; case-insensitive), per-card filters (category, request status), per-card record count (full match count, not rendered rows); card with <60 matches hydrates fully in first response, >=60 uses incremental scroll loading (table default limit 60, max 600).

### /catalog
- **Catalog Overview**: summary-only; stat counts update after sync / request creation. No actions.
- **Catalog Sync (manual)**: Start Sync / Pause (-> "Pausing..." until in-flight page finishes and checkpoint saved) / Resume / Stop. Runtime states idle -> syncing -> pausing -> paused/idle. Owner = `manual`.
- **Automation (catalog)**: enable toggle; Time, Frequency, Mode, Pages (reference doc) ; `Save automation`; run button (disabled while manual owns runtime). Backend only accepts enabled/interval/time (no Mode or Pages fields in `AutomationUpdateSerializer`; mismatch, see 7).
- **Catalog Books** (card `catalog-records`): columns book, categories, curation status, local book, updated, action. Controls: search, status filter, sort, page size, pagination First/Prev/Next/Last, sync/stop sync. Bulk: Create selected, Delete selected. Row actions: `Open` (local book exists AND catalog status `ready`); `Create` (status in new, failed, stopped, unfinished, deleted, requeued); label becomes `Resume` when status `stopped`; `Delete` (always). Non-creatable rows read-only. Record not selectable (checkbox disabled) when linked to an active request, i.e. request state not in {failed, deleted} (processing_pages.txt; backend `record_is_selectable`). Duplicate-flagged record is locked until the original request is failed/deleted. Create-in-progress tracked client-side by `catalogCreationTracker` until terminal state.
- Catalog run history card family (columns run summary, status, mode, updated, action; row Stop only when run is queued/processing, Delete always; bulk Stop/Delete) is documented on /catalog and /incomplete in the audit but is NOT in the card key list, i.e. likely stale (see 7).

### /create
- **Create Overview**: live counts for Requests, Queue, Processing, Created.
- **Requests** (state initial): bulk Delete selected. No row actions (bulk delete only; the processing_pages spec says select + Delete).
- **Queue** (state queued): bulk Delete selected.
- **Processing** (state processing): bulk Pause selected, Delete selected. Job-family columns documented: request, status, step (ingestion=Create, resolution=Match, reprocess=Regenerate), updated, action. Legacy job row actions (older model): Open (target book exists), Recreate (target book deleted), Start (queued, no task id), Stop (active), Resume (stopped), Retry (failed), Delete (not active). Bulk Resume/Stop/Delete in legacy doc; current page doc says only Pause + Delete. Pause waits for the current long step to finish before saving progress (checkpoint, savedAt, savedData).
- **Created** (state created): row `Open` when `linkedBookSlug` set; bulk Delete selected, which also deletes the linked Book (`deleteBook`).
- Request cell: primary label + secondary URL/host line.

### /on-hold
- **On Hold Overview**: counts Paused, Failed, Duplicate, Deleted.
- **Paused**: row actions Resume, Delete; bulk Resume selected, Delete selected. Rows show saved progress (checkpoint, savedAt). Resume sets `isResumed`, state -> initial, request reappears in Create/Requests; pipeline uses checkpoint; corrupt checkpoint falls back to full restart with a warning. Delete clears saved progress, state -> deleted.
- **Failed**: columns request, updated, inline error reason (`errorMessage`). NO per-row buttons; bulk Retry selected (state -> initial) and Delete selected. Failure causes: retry-loop threshold, source fetch failing after retries, exception, Celery timeout, detected loop.
- **Duplicate**: columns request, duplicate review status, action. Row + bulk actions: `New` (set `isConfirmedNotDuplicate`, state -> initial, never re-flagged), `New Edition` (treat as new edition of existing book), `Duplicate` (confirm: sets duplicateOfRequestId/duplicateOfRecordId, record flagged duplicate, locked in catalog until original terminal), `Delete`. If the matched existing book is already deleted, `New` and `New Edition` remain available.
- **Deleted**: row/bulk `Create Again` only (state -> initial). Receives all deleted requests regardless of origin page.
- Action names map to backend `action` enum: delete, pause, resume, retry, force_generate, new, new_edition, confirm_duplicate, create_again, recreate. Doc "Duplicate" = `confirm_duplicate`. `force_generate` and `retry` vs `recreate` semantics: `recreate` used on Incomplete/Updated (and legacy "Recreate when previous linked book deleted"); `force_generate` has no UI mention anywhere in docs.

### /incomplete
- **Incomplete Overview**: counts of Incomplete and Updated (resolved).
- **Automation (incomplete)**: enable toggle, Time, Frequency, Save automation / run control. Fetches live source category `অসম্পূর্ণ বই` only and reconciles local catalog.
- **Incomplete** (card `incomplete-records`): read-only; no checkbox column; search + filters. Columns (legacy): book, local categories, source categories, synthetic status (ready = removed from unfinished, unfinished, needs_review = missing from catalog snapshot). Legacy had Reload and Reprocess actions; current model: no actions.
- **Updated** (`incomplete-completed`): records that disappeared from the incomplete category after a successful run (`resolved_from_incomplete`). Bulk Recreate selected (request -> initial, appears in Create/Requests), Delete selected (request -> deleted, appears in On Hold/Deleted). Legacy "Removed from Unfinished" was read-only with range filter.

### Bulk-actions summary (audit, current)
Requests, Queue: Delete. Processing: Pause, Delete. Created: Delete(+book). Paused: Resume, Delete. Failed: Retry, Delete. Duplicate: New, New Edition, Duplicate, Delete. Deleted: Create Again. Updated: Recreate, Delete. Catalog Books: Create, Delete.

### Notifications and sounds (processing_pages.txt Part 3, spec; whether implemented unknown)
Notify when: any action finishes; requests fail (batched, 2-minute quiet window, timer resets on each new failure/duplicate); duplicates detected; automated sync completes (not on manual pause); auto-requests created after automated sync; pipeline finishes all requests. Sound distinct for success/failure/info, soft, with a mute toggle.

### Invalidation / push model (user stories, use cases)
Backend pushes only version numbers (SSE) per card domain; frontend refetches only the named cards; flush at page reconciliation, pause, resume, failure, completion, post-sync request creation. Overviews refetch only when their own aggregates change. Bucket transitions invalidate only source card, destination card, and affected overviews (e.g. initial->queued: create-requests, create-queue, create-overview; processing->paused: create-processing, on-hold-paused, create-overview, on-hold-overview).

## 4. Use cases and user stories

### Use cases (processing-use-cases.md, all against real dev app)
- UC-01 Manual catalog sync start: runtime idle; click Start Sync; catalog runtime owner `manual`, manual card `syncing`, automation run disabled; each fully reconciled source page invalidates catalog-records, catalog-overview, catalog-sync; mounted records card refetches; overview refetches only if aggregates changed.
- UC-02 Manual pause/resume: Pause -> runtime `pausing`; current page finishes; checkpoint stored in DB and mirrored in Redis; owner stays manual; card shows Resume; resume restarts at page 1, reconciles saved rows up to checkpoint, then continues with new pages.
- UC-03 Catalog automation run button: runtime idle and settings saved; owner `catalog_automation`; manual button disabled; same sync behaviour; after completion initial requests created ONLY for records with no prior request history; invalidates catalog-overview, create-requests, create-overview.
- UC-04 Scheduler run: automation enabled and due by wall-clock; same as UC-03; if manual owns the runtime the scheduled run waits until idle.
- UC-05 Incomplete automation: runtime idle; button or scheduler; owner `incomplete_automation`; fetch only `অসম্পূর্ণ বই`; each page invalidates incomplete-records, incomplete-overview, incomplete-automation; final resolved/removed diff invalidates incomplete-records, Updated, incomplete-overview.
- UC-06 Create bucket movement: initial->queued, queued->processing, processing->created with the exact invalidations listed in section 3.
- UC-07 On-hold movement: processing->paused, processing->failed, duplicate decisions, delete actions invalidate only the source/destination cards and both overviews.
- UC-08 Card-local search/filter/count/empty state: refetch preserves q, category, status; count = full matched size; non-matching new rows leave card unchanged; empty state replaced when matching rows arrive.
- UC-09 Created -> Deleted -> Create Again: delete moves row to on-hold-deleted; Create Again removes it from Deleted and the same request re-enters live flow.
- UC-10 Duplicate -> New: row leaves Duplicate card; request re-enters pipeline; Duplicate card search/filter/count stay server-backed throughout.

### User stories (processing-user-stories.md)
Runtime units: catalog runtime shared by Manual Sync and Catalog Automation; incomplete runtime owned by Incomplete Automation.
Catalog (7): (1) manual + automation control the same runtime, never parallel, no conflicting updates; (2) button/automation/scheduler starts share pause, resume, checkpoint, reconcile, completion behaviour; (3) records card hydrates during run; (4) overview hydrates during run; (5) Manual disabled while Automation owns runtime and vice versa; (6) pause finishes current page, persists durably, resume starts from page 1 and reconciles to checkpoint; (7) Catalog Automation creates initial requests only for records never requested before.
Incomplete (5): (1) same runtime behaviour whether button or scheduler; (2) records card hydrates; (3) overview hydrates; (4) records vanishing from the incomplete category after a successful run move to Updated; (5) Updated card lets operator recreate/delete only those resolved/removed records.
Request state pages (4): Create page cards each own one bucket (Requests, Queue, Processing, Created); On Hold each own one (Paused, Failed, Duplicate, Deleted); transitions invalidate only source, destination, affected overviews; card-local loaders and disabled controls.
Search/filter/count (6): server-side on full dataset; counts are full matched size; <60 rows fully hydrated on first response; >=60 keeps incremental scroll loading; empty card auto-fills on matching transition; stays empty for non-matching rows.
Overview (3): backend-owned aggregates independent of loaded rows; refetch only when own aggregates change; no refetch for non-aggregate row changes.
Minimal push (3): push only invalidation events + tiny metadata; frontend refetches only named cards; flush at meaningful checkpoints (page reconcile, pause, resume, failure, completion, post-sync creation) not per row.

### Live test matrix (processing-live-test-matrix.md)
Deterministic scenarios (15): catalog manual start, manual pause/resume, automation button, scheduler start, post-sync request creation (only records without request history), catalog search/filter/count, empty-card hydration, create-pipeline movement, on-hold movements, created->deleted->create again, duplicate->new, incomplete run start, incomplete scheduler, incomplete search/filter/count (incomplete-records, Updated), overview aggregate-only refresh. Best-effort (observe only): source outage, rate limit/transient failures, worker crash/restart, incomplete-category row omission. Plus the 300-book EPUB structure regression harness (`tests/scripts/regression_curate_300.sh`, options `--limit N`, `--retry-failed`; state in `/app/storage/regression-300/state.json`, resumable; exit 0 only if every URL verdict ok) asserting per book: spine order `cover -> title -> info? -> dedication? -> front_section_* -> toc -> (lesson_+ | main_content) -> back_section_* -> nav`; EPUB-3 `nav.xhtml` comprehensive (all readable pages, never links to itself); printed `toc.xhtml` content-scoped (content chapters + back sections); no blank content/front/back page. Acceptance: no Playwright route mocking, no synthetic `remotePages`, no seeded synthetic rows; real data only through the real app flow.

### processing_pages.txt (original rebuild prompt; spec richer than the final implementation)
TDD prompt (Playwright first, React/Vite/TS, Django/Celery/Postgres). Contains Part 0 schema checks, Part 1 models (BookRecord, BookCreationRequest, RequestProgress{savedAt, checkpoint, savedData}), Part 2 global UI rules, Part 3 notifications/sounds, Part 4 per-page test lists (Catalog sections A-D incl. retry/backoff, 429 retry-after, malformed record skip, duplicate start blocked with warning; Create cards A-D; On Hold A-D; Incomplete A-B), Part 5 13 cross-cutting scenarios, Part 6 edge-case catalogue (sync, pipeline, UI, notification), Part 7 constraints (data-testid naming `[page]-[section]-[element]`; atomic state transitions; idempotent tasks; DB locking/optimistic concurrency; stale-request recovery; loop detection -> failed; no timeouts for 15-20+ min items; authenticated endpoints). Key requirement rules extracted:
- Auto-create `initial` request after automated sync for records whose state is `not_created` OR whose last request is `failed` or `deleted`; never for created/paused/queued/processing/duplicate. (Contradicts UC-03/user story 7 "only never-requested records"; see 7.)
- Auto-create blocked/selectable rule: record with active request (not failed/deleted) not selectable.
- Resume of paused request restarts via checkpoint; corrupted -> full restart + warning.
- Delete of `created` request deletes the Book; delete of paused clears saved progress.
- Worker crash recovery for stale `processing`.

## 5. Known gaps / audit findings (processing-pages-implementation-audit.md, 2026-05-27)
Clear bugs:
1. Catalog sync stop is optimistic in the UI but not safely cancellable: frontend sets stopped state immediately; backend `cancel_source_catalog_refresh` (ingestion/services/curation.py) revokes the Celery task and sets idle at once, but `TitleResolver.refresh_catalog` (ingestion/services/resolution.py) has no cooperative cancellation checks in its page loop, so fetching/upserting can continue in the background (reported: start, stop, still syncing).
2. Selection checkboxes (row and select-all) are generally NOT locked during pending single/bulk actions across submission, job, duplicate, failed, run-history tables (bulk and row buttons are); violates the "selection and actions disabled until action finishes" rule.
3. Incomplete-page `Updated` Recreate lock only held around the API call, not until the resulting request reaches terminal state (created/paused/failed/duplicate); no equivalent to `catalogCreationTracker`.
4. On Hold rows do not show/filter by originating pipeline stage; stored `origin` (user/curation/automation) is not surfaced as a filter.
Needs structural change/product direction: store richer originating stage on request for on-hold filtering; add recreate-tracker for Incomplete/Updated; wire selection-lock flag into every card checkbox/select-all.
Coverage gaps: no tests for true backend cancellation after stop; checkbox lock during actions on every card family; incomplete recreate tracking; on-hold origin filtering. Covered: helpers, catalog tracked-create loading/disable, basic pause/resume/delete on queue cards, mocked catalog sync start/stop UI, automation settings save/persist.
Fixes already applied (pages-reference): catalog browse queries made lightweight/paginated (overview via separate summary path); heavy book fields deferred; dev frontend avoids duplicate requests/background polling when idle; dev Celery worker run in `solo` mode (prefork SIGKILL crashes); six-page dropdown consolidated into four routes. Verification stats cited: backend `10 passed`, frontend unit `9 passed`, live Playwright `8 passed`, mocked sweep `14 passed`.

## 6. Management commands
Only `backfill_multi_page_toc` (`python manage.py backfill_multi_page_toc [--dry-run] [--batch-size N=200]`):
- Scope: BookCreationRequest rows with `has_multi_page_toc=False` and `linked_book` not null (ordered by id).
- For each, loads latest `CuratedBookDocument` (by `created_at` desc, per book) and reads `source_snapshot.manifest.source_structure`: if `has_paginated_toc` is None -> skip "old doc"; false -> skip single page; true -> set `has_multi_page_toc=True`, `source_toc_page_count = max(int(source_total_pages),1)`, `fetched_toc_page_count = max(toc_pages_with_content, fetched_total_pages)`. No doc -> skip.
- Uses `bulk_update` in a transaction per batch; dry-run prints `WOULD UPDATE`. Prints counts: updated, skipped no doc, skipped old doc, skipped 1 page. Writes carriage-return progress.
- Docstring says it targets rows predating migration 0006.

## 7. Mismatches between docs and code
1. Automation fields: reference doc lists `Mode` and `Pages` settings on catalog automation, but `AutomationUpdateSerializer` and `ProcessingAutomationSettings` only have enabled, interval, time. Mode/Pages not supported by this API/model.
2. Auto-request creation rule: UC-03 / user story 7 / live matrix: only records with NO prior request history; processing_pages.txt: also records whose last request is failed or deleted. Code rule lives in service_modules (not read by me); treat the three docs as in conflict.
3. Run History card (Stop for queued/processing, Delete) is documented on /catalog and /incomplete in the audit, but the current card keys and endpoint set contain no run-history card or run endpoint; likely leftover from the pre-refactor model. Also audit "Submission list / Processing job card / Catalog Books Create/Delete/Resume/Open" row actions have no corresponding endpoints here (no catalog-row delete/create endpoints; creation goes through `records/create-requests/`; catalog delete would be `requests/action delete`?). Doc says Catalog Books has "bulk Delete selected" and row Delete "delete the catalog row", but `requests/action` takes request ids, not catalog entry ids.
4. Processing card doc: reference says Processing bulk = Pause+Delete (current) while audit's "Processing Job Card Family" lists Resume/Stop/Delete and job-type labels (ingestion/resolution/reprocess) from the old submission/job model that this app does not expose (no job type field on BookCreationRequest).
5. `Requests`/`Queue` card: reference says "bulk Delete selected" only; spec says select + Delete; consistent. But old shared-card section still lists `Stop selected`, `Review`, `Start`, `Add Again to Queue` - none exist in the `action` enum (enum has pause, resume, create_again). Review Match dialog documented but no endpoint.
6. Duplicate action naming: docs `Duplicate` = code `confirm_duplicate`; docs say `New Edition` -> code `new_edition` (consistent). `force_generate` and `recreate` actions exist in code, `force_generate` appears nowhere in docs; `recreate` appears in docs (Updated card) only for incomplete resolution.
7. Page count/titles: docs describe "four pages" plus `/multipage-toc` and `/reprocessing`; the backend stream only knows four pages (catalog, create, on-hold, incomplete) and has no API for the two extra pages (multi-page TOC data only appears as three fields on the request + the backfill command; `/reprocessing` has no endpoint here).
8. Reference doc's "Validation" section header appears twice; the first marks the remainder obsolete (old six-page model) while the live test numbers after it (8 live, 14 mocked passes) describe old scenarios (my-requests, failed/duplicate pages).
9. Spec said "All new code must be JavaScript with strict mode and no implicit any" while the Stack line says TypeScript; spec language inconsistency.
10. Spec (processing_pages.txt) BookRecord shows only id,name,url,category,writer,translator,composer,createdAt,updatedAt,bookCreationState; code adds publisher, linkedBook, wasIncomplete, resolvedFromIncomplete, willResolveToCategory, isDuplicate, duplicateOfRecordId, source_catalog_entry; request adds origin, force_generate, multi-page TOC fields, submission, pipeline_outcome, duplicateConfirmed.
11. Spec `RequestProgress{savedAt, checkpoint, savedData}` only exposed on paused; code also exposes failed-state `curatedValidation/curatedStatus` (extension).
12. Spec: duplicate "Select + Duplicate" must set duplicateOfRequestId/RecordId; both exist on model and serializer. Consistent.
13. Doc says pause "checkpoint mirrored in Redis"; no Redis fields in these models (lives in service_modules).
14. Notifications + sound (2-minute batching window, mute toggle) are in the spec; no backend code for them in the assigned files (frontend concern); whether implemented is not verifiable from here.
15. Docs say backend "validated" behaviors (429 retry-after, exponential backoff, loop detection, stale recovery) - implementation is in service_modules, not verified here.

## 8. Bugs, dead code, surprises
1. **Facade-by-`exec`**: `services.py` and `views.py` build their namespace by `exec(compile(read_text()))` of 26 + 2 module files into one shared globals dict. Consequences: module files are not importable/lintable alone (e.g. `sync_action_and_automation_views.py` begins with no imports and uses `APIView` from the previous file), strict ordering dependency, no real encapsulation, hidden name collisions, tracebacks reference file paths but tooling/IDE/coverage can break. Must not be replicated in the rebuild.
2. **Circular dependency**: `serializers.py` imports from `.services`; services presumably import serializers (state payloads).
3. **`ProcessingSyncStopView`/Pause/Resume default scope** uses `active_sync_scope()`; unspecified when both runtimes idle. Scope-less routes (`sync/pause/`) vs scoped routes are redundant duplicates (6 URL entries, 3 views).
4. **SSE stream implementation**: infinite sync generator with `time.sleep(1)` polling the DB per connection (N clients = N blocked workers + N polls/sec); no auth refresh, no `Last-Event-ID` handling; `eventId` is `int(time.time()*1000)` not a durable cursor so reconnect cannot replay missed versions (client must refetch everything on `connected`); `GeneratorExit` handled but no max duration.
5. **`allow_processing_remote_page_payloads`** returns true whenever `"pytest" in sys.modules` or `PYTEST_CURRENT_TEST` is set (grep): test-mode backdoor in production code that lets a caller inject fake remote catalog pages into `sync/start/`; gated otherwise by setting. Docs also forbid synthetic `remotePages` in live tests. Security smell: anyone with `processing.manage` could inject arbitrary catalog data if the setting is on.
6. **`capture_source_page_metadata`** swallows every exception silently and returns None.
7. **N+1 queries** in `BookRecordSerializer`: `latest_request_for_record` per row, `linked_book` per row (unless service uses select_related), `BookCreationRequestSerializer.get_linkedBookSlug` hits book_record and its linked_book.
8. **`BookRecord.url` unique** but `BookCreationRequest.submission` OneToOne: one submission per request; re-creating a request for the same record creates a new request row (history preserved, fine) but `latest_request_for_record` must define "latest".
9. **Dual state storage**: `BookRecord.book_creation_state` denormalises the active request state (with `not_created`, which requests lack) - sync hazard; `BookCreationRequestState` and `BookCreationState` are two enums that differ only by `not_created`; `pipeline_outcome` defaults to `"created"` (a state value, default misleading for new/initial requests).
10. **`origin` on request** defaults to `"curation"` while docs/spec call the catalog-created ones user/automation; origin is never exposed in the serializer (confirms audit finding 4).
11. **Dead/unused imports in view module**: `BookCreationRequest`, `BookRecord`, `BookCreationRequestSerializer`, `BookRecordSerializer`, `ProcessingSyncStatus` imported in R but unused. `ProcessingStateSerializer` is defined but `ProcessingStateView` returns a raw dict payload.
12. **Dead code**: `source.py` scrape path (`scrape_book`, `scrape_book_high_fidelity`, `persist_scraped_book`, `generate_exports`, `sync_assets`) coexists with the curate path; `processing_scrape_limits` constants (48 nodes, 2 lesson pages, 12000 chars) are tiny vs curate limits (unlimited, 20, 60000) - the old truncating path suggests partial books if still used. `ProcessingUiProjection` model has no references in assigned files.
13. **`run_processing_sync` alias** in tasks.py only exists for patching.
14. **`ProcessingSyncState.message`** `CharField(500)`: long error text must be truncated by services.
15. **backfill command bug (offset paging over a shrinking filter)**: `requests_qs` filters `has_multi_page_toc=False`; each batch bulk-updates rows to True so they drop out of the queryset, but `offset` still advances by `batch_size` and `total` is computed once - rows are skipped (roughly every other batch lost when many rows update). Also `bulk_update(..., fields=[..., "updated_at"])` does not auto-refresh `updated_at` (auto_now only applies on save), so updated_at is written with its stale in-memory value; the `.only(...)` deferred-field queryset plus `select_related("linked_book")` with `only` that omits `linked_book` relation fields can raise "Field X cannot be both deferred and traversed" in Django (select_related with `only` not including the FK; `linked_book_id` is listed but the related-object traversal conflicts). It also computes `pages_with_content` fallback default 0 and `max(...)` for fetched count (intended). Also dead `select_related`.
16. **Command imports `CuratedBookDocument` from `curated_persistence`** (a pipeline module, not a model module): cross-app coupling.
17. **Mutation payload `versions`** filters on `PROCESSING_CARD_KEYS` but SSE emits domains from `PROCESSING_PAGE_DOMAINS`; unknown domains silently dropped from mutation responses.
18. **No pagination metadata documented** for `table/` beyond offset/limit (response shape in service_modules).
19. **No rate limiting/idempotency** on bulk endpoints; `ids` list unbounded (spec requires 200+ bulk to work); `apply_request_action` raising ValueError is the only validation path (400 `detail`); unknown ids behaviour unknown.
20. **Permissions**: a single scope `processing.manage` gates everything including GET, SSE and bulk deletes of books (`deleteBook`); no per-action or per-user scoping (docs once said "My Requests scoped to current user" in the old model; current code has no per-user filter; `actor=request.user` only recorded).
21. Heading typo "Deplicate" existed in old UI, corrected per audit.
22. `kickoff_book_creation_request_task` returns `state: DELETED` for missing request rows: deleted-vs-missing conflated (flagged with `missing: true`).
23. Admin exposes ProcessingSyncState etc. with no read-only protection beyond timestamps.

## 9. Unread items and why
- None of the assigned files were left unread. Not read (out of assignment): `processing/service_modules/*` (26 modules holding all business rules: state-transition validity per action, `record_is_selectable`, `latest_request_for_record`, pipeline, sync runner, automation, table/card payload shapes), `processing/migrations/*`. Consequently the exact rules for "which `apply_request_action` actions are valid in which state" are taken from the docs only, NOT confirmed against code; the response shapes of `state/`, `card/`, `table/` are unknown beyond the names. `allow_processing_remote_page_payloads`, `PROCESSING_PAGE_DOMAINS`, `PROCESSING_CARD_KEYS`, `CanManageProcessing` and root URL include were checked by grep only (partial).
- `__pycache__` ignored. `.env`/secrets not opened.
