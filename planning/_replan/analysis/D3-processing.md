Status: DRAFT

# D3 - Processing (operator-side catalog sync, request creation, build pipeline, curation UI backend)

Sources: reports 06 (service_modules a..q, with s/u extras), 07 (service_modules r..z), 08 (API, models, docs), 14h (contract tests), 14i (catalog phase tests), 14j (catalog sync tests). Legacy code root: `archive/app/backend/apps/processing`. Citations "file:line" are relative to `service_modules/` unless stated. Source-report IDs: 06 uses F01-F129, 07 uses RA-/SY-/UI-/ST-/MS-, 08 uses endpoint numbers #1-#17 and section numbers, 14h uses PR1-PR10, 14i uses PA1-PA15, 14j uses PB1-PB7. Verification marks: VERIFIED = I re-read the code in this pass; UNVERIFIED = taken from the reports only.

## 1. Purpose and scope

The legacy `processing` app is the operator's control room for turning a single external source website (a Bengali ebook site, host in `SOURCE_SITE_HOST`) into local books. It does five jobs:

1. Mirror the source site's catalog (and its separate "incomplete books" archive category) into local `BookRecord` rows, either by live scraping or from a local snapshot (`SourceCatalogEntry`, owned by the ingestion app).
2. Turn catalog records into `BookCreationRequest` rows (one per attempt to build a book), either by operator selection or automatically after a catalog sync ("catalog automation").
3. Run each request through a scrape -> curate -> duplicate-check -> persist -> export (HTML + EPUB) pipeline, with pause/resume checkpoints, retries, stale-request recovery and review gating.
4. Give the operator a set of pages (/catalog, /create, /on-hold, /incomplete, plus /multipage-toc and /reprocessing) driven by 20 "cards", with server-side search/filter/pagination and a version-number based push/invalidation channel (SSE) so the UI refetches only what changed.
5. Schedule recurring automation (catalog and incomplete) with enable/interval/time settings.

In scope for the rebuild: everything above. Out of scope for this analysis (other analyses): the ingestion/scraper/curation engine itself (`apps.ingestion.*`, `curate_book`, `generate_exports`, `persist_curated_book`), the catalog Book model, reader features, identity/permissions model. The processing code calls into those, so the boundary matters (section 8, overlap).

Actors: the operator (a user holding scope `processing.manage`, the single permission gating every endpoint), the system (Celery workers, scheduler/beat, maintenance tick, the ingestion engine's job dispatcher).

Scale hints (UNVERIFIED, from docs): catalog of thousands of records; bulk actions of 200+ ids must work; a book can take 15-20+ minutes to scrape; a 300-book EPUB structure regression harness exists.

## 2. Features and behaviours

IDs D3-F# are stable for this analysis. "Src" gives the source-report IDs.

### 2.1 Catalog record sync (source catalog -> BookRecord)

- D3-F1 Upsert remote records into BookRecord. Input: list of payload dicts (`id, name|title, url, category, writer|author, translator, composer, publisher, updatedAt, bookCreationState, wasIncomplete, resolvedFromIncomplete, willResolveToCategory`; both camelCase and snake_case accepted). Empty `url` skipped silently. Match existing by `pk=id OR url=url`. Create reuses payload id as pk only when unused, IntegrityError race re-queried. Update saves only changed fields. `desired_state` = payload state if valid, else CREATED if a Book already exists for the normalized URL, else NOT_CREATED. Also sets `source_catalog_entry` and `linked_book`. Publishes UI domains once per page. Src: 06 F01, F02, F19(upsert counters); catalog_record_sync.py:11-110.
- D3-F2 Remote payload normalisation: category default "Uncategorized", name default "Untitled book", `id = id or url`, `wasIncomplete` computed from category keywords when absent. Src: 06 F02, F06 (pages must be list of lists of dicts, else `[]`).
- D3-F3 SourceCatalogEntry -> remote payload: category from raw_data (category | resolvedCategory | resolved_category | "Uncategorized"), adds `displayUrl`, `displayPath`, `wasIncomplete`. Does NOT carry `resolvedFromIncomplete` or `bookCreationState`. Src: 06 F03.
- D3-F4 Offline "remote pages" from the local SourceCatalogEntry table: ordered `title,id`, pages of 100, terminated by an empty page `[]` sentinel. Src: 06 F04; 14j PB7 (BookRecord id=str(entry.id), name=title, url=source_url, category=raw_data.category, writer=author_line, publisher=raw_data.publisher).
- D3-F5 Live catalog scrape `refresh_catalog_parallel`: N threads (`CELERY_PROCESSING_CONCURRENCY`, default 5) pull page numbers from a shared counter, fetch the archive listing (30 s timeout, params `page`, `q`), parse entries, for each unseen source_url fetch page metadata, upsert SourceCatalogEntry then BookRecord. Stops only on a page with zero entries. Returns `{appended_count, updated_count, total}`. Tests (14j PB4): empty page -> zeros; stops at first empty page; duplicate URLs across pages deduplicated; entry whose metadata fetch raises is skipped; page fetch raise is skipped but crawl continues. Src: 06 F07; 14j PB4.
- D3-F6 Live vs offline selection (`should_use_live_catalog_fetch`): needs `PROCESSING_USE_LIVE_SYNC`, not eager Celery, not under pytest, no explicit remote pages, run mode manual or catalog_automation, and a processing worker present. Src: 06 F08.
- D3-F7 Start sync: inputs `remote_pages`, `run_mode` (manual | catalog_automation | incomplete_automation), `sync_key` (catalog | incomplete), `trigger_source` (button | scheduler). New `session_id` uuid4, counters zeroed, message by mode, task id cleared; a PAUSED request-creation phase is preserved. Enqueue Celery task if workers available, else run inline if eager/inline mode, else leave for manual ticks. Src: 06 F09; 14j PB5 (records are not written at start; each advance processes one page).
- D3-F8 Dispatch sync task: uuid4 task id, queue "processing"; on any exception falls back to running inline in the caller (blocking). Src: 06 F10.
- D3-F9 Single manual step `advance_sync_once` / `run_processing_sync`: skipped if a Celery task owns the state (unless eager) or task id mismatch (ownership token pattern); routes by run mode and phase. Src: 06 F11; 07 SY-09, SY-12; VERIFIED sync_runner.py:104-119, 205-212.
- D3-F10 Run-until-blocked loop: loops until status leaves syncing/pausing; live catalog path is one `refresh_catalog_parallel()` call followed by a pause check, then request creation (automation) or finalize; any exception -> `fail_sync`. Src: 06 F12; 07 SY-10; VERIFIED sync_runner.py:122-202.
- D3-F11 Advance one catalog page (non-live): upsert page, counters, `page_index += 1`; re-read persisted status; `pausing` -> `paused` with checkpoint `page-N` and message "Sync progress saved. Catalog now has N book records."; empty page -> done. Src: 06 F13.
- D3-F12 Finalize catalog sync: sync phase completed, request_creation preserved if paused else not_started, status idle, message "Sync complete. Updated X, Skipped Y, Added Z."; task cleared. Src: 06 F14, 07 SY-06; VERIFIED sync_completion.py:27-114.
- D3-F13 Fail sync: status idle, progress None, `last_error`, message "<label> failed: <err>", mirrored into automation `status_message`. Src: 06 F16; 07 SY-05.
- D3-F14 Pause sync (cooperative): only from syncing -> `pausing`; real pause happens in the worker after the current page or batch (DB re-read `persisted_sync_status`). Phase-appropriate messages. Src: 06 F17; 07 SY-01; 14i PA7.
- D3-F15 Resume sync: incomplete mode always restarts from page 0 ("Restarting incomplete catalog sync from the beginning."); catalog: if automation and request creation can resume, resume phase 2; else if sync phase paused continue from saved `nextPageIndex`/`fetchedCount`; else restart from page 0. Src: 06 F18; 07 SY-02, section 3; 14i PA9, PA10, PA12; 14j PB1.
- D3-F16 Stop sync: from syncing/pausing/paused -> idle, progress None, message "<label> stopped."; counters kept; does not revoke the Celery task (task id cleared so worker is ignored); checkpoint discarded. Src: 06 F19; 07 SY-03, item 16.
- D3-F17 Sync ownership conflicts: an active sync blocks any run mode different from its own; a paused sync conflicts unless both modes belong to the catalog shared runtime {manual, catalog_automation}. Src: 06 F20; 07 ST-03; 14i PA9/PA10.
- D3-F18 Entry points: `run_manual_catalog_sync` (conflict -> unchanged state; paused sync phase -> resume; active -> no-op; else start), `run_catalog_automation` (conflict -> scheduler sets "Waiting for the catalog runtime to become idle."; resume phase 2 or paused sync; if sync completed and request creation not_started go straight to request creation; else start), `run_incomplete_automation`. Src: 06 F21, F22, F23; VERIFIED automation_commands.py:165-200.
- D3-F19 Sync serialisation for UI: `{status, progress, phase, fetchedCount, skippedCount, updatedCount, appendedCount, message, pageIndex, runMode, triggerSource, scope, workerManaged, remotePages?}`. Src: 06 F32; 07 ST-04.
- D3-F20 Redis checkpoint mirror: on every `save_sync_state`, progress JSON written to key `processing:sync-checkpoint:<catalog|incomplete>` (timeouts 0.5 s, deleted when progress empty, deleted on stop per test 14j PB6). Write-only in the code read (never read back). Src: 06 F29; 14j PB6.
- D3-F21 Worker availability probe and execution-mode switches (inline / enqueue / manual advance), cached 2 s; production code branches on pytest presence. Src: 06 F30, F31.

### 2.2 Two-phase catalog automation (sync, then request creation)

- D3-F22 Phase model: catalog scope has two phases `sync` and `request_creation`, each in {not_started, running, pausing, paused, completed}, each with owner (run mode), trigger source, checkpoint, savedAt, savedData. Overall status derived (any pausing -> pausing, any running -> syncing, any paused -> paused, else idle). Includes a legacy-progress migration/normalisation layer. Src: 06 F27; 14i; 14j PB2, PB3; 14i PA6 (repair when both phases claim running).
- D3-F23 Checkpoint token `"{sessionId}:{1 if live else 0}:{nextPageIndex}:{fetchedCount}"`; request-creation progress is anchored to the sync checkpoint (`baseCheckpointToken`) so it is only reused when it belongs to the same sync. Src: 06 F28; 14i.
- D3-F24 Begin request creation: marks sync phase completed, builds token, `requestCreation = {baseCheckpointToken, lastRecordId:"", processedCount:0, createdCount:0, unsupportedCount:0}`, status syncing, message "Creating book requests from the synced catalog records.". VERIFIED sync_completion.py:124-191.
- D3-F25 Advance request creation one batch (50 BookRecords ordered by id, keyset cursor `id > lastRecordId`): unsupported URL -> `unsupportedCount++`; record with no request at all and state NOT_CREATED -> create request (origin AUTOMATION). Checkpoint-token mismatch resets counters. Pause handled per batch. Src: 06 F25; 14i PA11.
- D3-F26 Complete catalog automation: status message "Created N request(s). Skipped M unsupported record(s)." plus `last_run_at`; run message "Automated catalog sync complete. Updated U, Skipped S, Added A.". Src: 06 F26.
- D3-F27 Phase interplay rules proven by tests: manual start does not interrupt running automation request creation; manual start while phase 2 paused keeps phase 2 paused with its old base token; automation resume from both-paused resumes phase 2 while manual resumes phase 1 (14j PB1); manual sync never creates requests (14i PA9); starting again after both completed restarts at page 0 with request_creation not_started (14i PA1, PA2 #9). Src: 14i PA1-PA12; 14j PB1.

### 2.3 Incomplete-books flow

- D3-F28 Definition of incomplete: category (casefolded) contains any of "incomplete", "unfinished", "অসম্পূর্ণ", "অসম্পূর্ণ বই", or `was_incomplete=True`. Src: 06 F40.
- D3-F29 Unresolved-incomplete queryset: `resolved_from_incomplete=False AND (was_incomplete OR category keywords)`. Src: 06 F41.
- D3-F30 Local incomplete pages: ids of unresolved incomplete records that already have a non-empty `will_resolve_to_category`, pages of 100 plus terminal `[]`; items are id strings, not dicts. VERIFIED automation_advancement.py:189-203.
- D3-F31 Live incomplete scrape: archive URL `https://<SOURCE_SITE_HOST>/genres/<percent-encoded "অসম্পূর্ণ-বই">/`, pages `/page/N/` (404 on page>1 = end); parses `.entry-title a[href]`, `article h2 a[href]`, `article h3 a[href]`; max 250 pages, page size 100; stops on empty page or when the first 5 URLs repeat; category fixed to "অসম্পূর্ণ বই", `wasIncomplete=True`, `resolvedFromIncomplete=False`. Src: 06 F44; 14i PA13, PA14.
- D3-F32 Live-vs-local choice for incomplete: live only if live sync enabled, not eager/pytest, workers available and every unresolved incomplete record URL is a supported source URL; on exception fall back to the local snapshot with a warning. Src: 06 F45.
- D3-F33 Live incomplete step: one archive page per step, dedupe against pages already stored, upsert, pause handling; empty or repeated page -> complete. Src: 06 F46.
- D3-F34 Non-live incomplete step handles three page shapes (empty page -> resolve stale and complete; page of id strings -> resolve those ids directly; page of dicts -> upsert). Src: 06 F49; 07 SY-11; VERIFIED sync_runner.py:3-30 (empty and id-page branches).
- D3-F35 Stale = unresolved incomplete record whose normalised URL is not in the freshly fetched incomplete list (it left the incomplete archive). All stale records get resolved at the end. VERIFIED incomplete_resolution.py:72-97.
- D3-F36 Resolve incomplete records: for each incomplete BookRecord set category = preferred resolution category (first non-empty non-incomplete of `will_resolve_to_category`, source catalog entry's resolved category, current category, else "Uncategorized"), `was_incomplete=True`, `resolved_from_incomplete=True`, `book_creation_state=CREATED`; latest request set to CREATED (error/progress cleared) or a new CREATED request (origin AUTOMATION) is made. No Book is created. Src: 06 F47, F43.
- D3-F37 Complete incomplete automation: status "Updated N book(s)." and `last_run_at`. Src: 06 F50.

### 2.4 Automation settings and scheduler

- D3-F38 Automation settings per kind (catalog, incomplete): `enabled` (default False), `interval` (default weekly), `time` (03:00), `saved`, `last_run_at`, `status_message`. Unsaved settings forced to defaults on read; legacy "Not configured." blanked. Src: 06 F60; 07 ST-05, ST-06. Note model default differs: interval "daily", time 02:00 in `models.py` (08 section 2 data model) versus 03:00/weekly in service constants - a mismatch (section 8).
- D3-F39 Update settings (`enabled`, `interval`, `time`): sets `saved=True`, `status_message="Saved."`, publishes automation domain. Interval is not validated in service; API only checks non-blank string. Src: 06 F61, F-26 issue; 08 endpoints #14, #16.
- D3-F40 Due check: disabled -> false; before today's local scheduled time -> false; never run -> true; daily = last run before today's scheduled time; weekly >= 7 days; biweekly >= 14; monthly = different (year, month); unknown behaves as weekly; uses project local timezone. Src: 06 F62.
- D3-F41 Scheduler tick `run_due_processing_automations`: catalog first then incomplete; returns `{catalog:{ran,status,runMode}, incomplete:{...}}`; `ran` true only if the resulting run mode matches. A scheduled run blocked by an owner conflict waits ("Waiting for the catalog runtime to become idle.") and retries on the next tick. Src: 06 F63; 08 Celery tasks.
- D3-F42 Automation run status line: `status_message` (+ `last_run_at`) written only for catalog_automation / incomplete_automation modes; manual runs ignored. Src: 06 F64; 07 sync_status_messages.

### 2.5 Request creation, queueing and the build pipeline

- D3-F43 Create request for record: id `request-<recordId>` with `-2`, `-3` suffix when taken; INITIAL with unsupported URL returns None; syncs record state; publishes domains; INITIAL is queued. Origin in {user, curation (default), automation}. Src: 06 F70; 07 RA-26.
- D3-F44 Create requests for record ids (operator selection): only records passing `record_is_selectable`. Src: 06 F71; 08 endpoint #12.
- D3-F45 Record selectability rule: URL must be supported; confirmed DUPLICATE request makes the record selectable only if its original is missing/FAILED/DELETED; a record with a linked book and no requests is not selectable; otherwise not selectable if any request exists in a state other than FAILED/DELETED. Src: 06 F72; 07 RA-25.
- D3-F46 Queue request: unsupported URL -> FAILED "Only source site book URLs are allowed"; if enqueue mode -> `enqueue_request_processing` falling back to synchronous kickoff; if inline -> kickoff; else leave INITIAL for the ticker. Src: 06 F73; 07 RA-18.
- D3-F47 Enqueue to the shared engine: INITIAL->QUEUED, no-op if a dispatch marker younger than 2 min exists; calls `dispatch_job(job_id=request.id, job_type="pipeline", handler="pipeline")` from `apps.ingestion.engine.dispatch`; on success writes `progress._dispatchRequestedAt`. Src: 06 F74; 07 RA-17, RA-19. This is a direct coupling to the ingestion app.
- D3-F48 Kickoff: INITIAL->QUEUED->PROCESSING with compare-and-swap under `select_for_update`, then runs the pipeline synchronously. Src: 06 F75, F87.
- D3-F49 Pipeline ticker `advance_pipeline_once`: recover stale PROCESSING; oldest QUEUED; oldest PROCESSING (inline/no workers only); oldest INITIAL -> QUEUED; if idle, repair self-linked duplicates. One request per state per tick. Src: 06 F76; 07 RA-06.
- D3-F50 Run request with retries: up to 3 attempts; error text containing "source site" aborts retries; error starting "Incomplete scrape:" sleeps 60 s before retrying (blocking); other errors retry immediately; deleted/paused requests exit; exhaustion -> FAILED with last error or the stale message. Src: 06 F77; 07 RA-11.
- D3-F51 Process one request (steps): reload; terminal/paused -> stop; normalise URL; capture source page metadata and overwrite the record's name/writer/category/translator/composer/publisher/source_catalog_entry; DELETED/PAUSED checkpoints (`source-metadata`); source-URL duplicate check (claim unlinked book or mark DUPLICATE) unless `is_confirmed_not_duplicate`; resume from `scraped-content` checkpoint only when `is_resumed`; otherwise scrape+curate (`curate_book(url, page_cache=DiskPageCache)` with heartbeat thread; legacy path `scrape_book` + `curate_scraped_book_data` if monkeypatched); fill missing projection fields from the record; multi-page TOC signal; pause checkpoint `scraped-content` with `{scrapedData, curatedResult}`; title-based duplicate check (`find_exact_existing_book`, optionally `detect_metadata_duplicate`); INVALID-with-no-title guard; persist; review gate or finalize. Src: 06 F78; 07 RA-07.
- D3-F52 Scrape heartbeat: daemon thread touches `updated_at` every 300 s so the 20-minute stale recovery does not requeue a live scrape. Src: 06 F79.
- D3-F53 Multi-page TOC signal: reads `source_structure` from the curated snapshot manifest; stores `has_multi_page_toc`, `source_toc_page_count`, `fetched_toc_page_count`; raises a non-retried "Sign-in required: the source table of contents spans multiple pages ... Update the source site auth cookie and regenerate this book." when TOC incomplete, and a retried "Incomplete scrape: only X of Y topic pages returned content. The source may be rate-limiting requests - please try regenerating." when content incomplete. Fails before persisting so existing content is not overwritten. Src: 06 F80; 07 RA-10.
- D3-F54 Persist book: target = request.linked_book if not soft-deleted; `persist_curated_book`; if curated status != VALIDATED and not force, return without exporting (review gate); with force on non-validated doc, strip source chrome blocks and disambiguate duplicate content paths; then `export_payload_from_book`, `generate_exports` (HTML + EPUB), `sync_assets`. Src: 06 F81, F90, F91; 07 RA-20.
- D3-F55 Review-required gate: non-validated document and not force -> request FAILED, `linked_book=book`, error "Curated document requires review before asset generation.", progress `{curatedValidation, curatedStatus}` (exposed to the UI on failed requests). Src: 06 F82; 07 RA-13; 08 serializer rule.
- D3-F56 Finalize: DELETED -> soft-delete the built book; PAUSED -> checkpoint `{scrapedData, linkedBookId}`; else CREATED, `linked_book=book`, error/progress cleared, `force_generate=False`, record linked and duplicate flags cleared, scrape cache deleted. Src: 06 F84; 07 RA-21.
- D3-F57 Mark duplicate: state DUPLICATE, `linked_book=existing`, `duplicate_of_request` = latest other request linked to that book else `duplicate_of_record`; record flagged. Src: 06 F85; 07 RA-22.
- D3-F58 Claim unlinked source book: if a Book exists for the URL and no other record/request references it, link instead of flagging duplicate. Src: 06 F86; 07 RA-09.
- D3-F59 Disk scrape cache `DiskPageCache`: append-only JSONL keyed by source_url at `<RUNTIME_STORAGE_DIR>/processing/scrape_cache/<id>.jsonl`; tolerant of corrupt lines; deleted on success only. Src: 06 F88; 07 RA-30.
- D3-F60 Stale PROCESSING recovery: `updated_at` older than 20 min -> QUEUED, `is_resumed=True`, requeued. Stale sync states (syncing/pausing older than 20 min) recovered: pausing -> paused, syncing stays syncing with task re-dispatched. Src: 06 F89, F111.
- D3-F61 Repair self-linked duplicates: DUPLICATE requests whose live linked book is the record's own book, with no duplicate_of links, become CREATED. Run from maintenance and when the ticker is idle. Src: 06 F109.
- D3-F62 Maintenance and runtime tick tasks: `run_processing_maintenance` returns `{recoveredCount, syncRecoveredCount, repairedCount}`; `run_processing_runtime_tick` advances each active sync once then the pipeline. Src: 06 F110, F112; 08 Celery tasks.
- D3-F63 Reset processing data: optional Celery revoke and queue purge; deletes all requests, resets every BookRecord to NOT_CREATED with links cleared, resets sync states, publishes all 20 card domains. No HTTP route exposes it in the endpoint list (a management/admin path). Src: 06 F113; 07 RA-27.

### 2.6 Operator request actions (`requests/action`)

- D3-F64 Actions: delete, pause, resume, retry, force_generate, new, new_edition, confirm_duplicate, create_again|recreate; applied per request in `created_at,id` order; unknown action silently skipped; no state guards at the service layer; `sync_records_for_requests` afterwards. Src: 06 section 2.5 header; 07 RA-01.
  - delete (F100): optional soft-delete of the linked Book; state DELETED; progress/error cleared.
  - pause (F101): PAUSED from any state; progress `{savedAt, checkpoint, savedData}`.
  - resume (F102): INITIAL, `is_resumed=True`, `force_generate=False`, error cleared, progress retained, requeue.
  - retry (F103): INITIAL, flags/error/progress cleared, record duplicate flags cleared, requeue.
  - force_generate (F104): INITIAL with `force_generate=True`.
  - new (F105, "not a duplicate"): INITIAL, `is_confirmed_not_duplicate=True`, clears duplicate links and `linked_book` on request and record.
  - new_edition (F106): find existing duplicate Book, lazily create `BookGroup(canonical_title)`, store `target_book_group_id` into `submission.raw_payload` if a submission exists, then `new`.
  - confirm_duplicate (F107): `duplicate_confirmed=True`, state DUPLICATE, link target; no requeue.
  - recreate/create_again (F108): INITIAL, clears progress/error/duplicate_confirmed, keeps `linked_book` and `is_confirmed_not_duplicate`.
  Src: 06 F100-F108; 07 RA-02..RA-05.

### 2.7 UI projection, domain versions and push

- D3-F65 Twenty cards (keys): catalog-overview, catalog-sync, catalog-automation, catalog-records, create-overview, create-requests, create-queue, create-processing, create-created, on-hold-overview, on-hold-paused, on-hold-failed, on-hold-duplicate, on-hold-deleted, incomplete-overview, incomplete-automation, incomplete-records, incomplete-completed, multipage-records, empty-chapters-records. Seven "shared" cards (overviews, syncs, automations) have cached projections; table cards are queried on demand. Src: 06 F123; 07 section 6; 08 section 3.
- D3-F66 Domain version mechanism: per-domain monotonically increasing integer in `ProcessingUiDomainVersion`; `publish_processing_ui_domains` registers `on_commit` that rebuilds dependent projections first, then bumps versions under `select_for_update` in stable lock order; `catalog-sync` also rebuilds `catalog-automation`; a ContextVar collector lets a mutating HTTP view return the new versions so the client can ignore its own echo. Src: 06 section 4; 07 UI-01..UI-09.
- D3-F67 Which events bump which domains (request change, record change, sync save, automation change, reset = all, never `empty-chapters-records`). Src: 06 section 4 item 6; 07 UI-03; 14i PA15 (tests: a regular request change includes create-requests and create-queue but not incomplete domains; hydration of records includes overview and records but not incomplete-completed).
- D3-F68 Table payload `processing_table_payload(card, q, category, status, offset, limit, includeFacets)`: offset >= 0, limit clamped [1, 600], default 60; returns `{rows, pagination{offset,limit,totalCount,returnedCount,hasMore,nextOffset}, hasMore, filters{categoryOptions,statusOptions}?, version, summary?}`; search `icontains` on name, url, category, writer, translator, publisher, status (and error_message for requests); facets from the unfiltered set. Src: 06 F122, F124; 08 endpoint #3.
- D3-F69 Row payload (27 fields incl. selectable, progressCheckpoint, progressSavedAt, errorMessage, isResumed, isConfirmedNotDuplicate, linkedBookId, linkedBookSlug, duplicate ids, multi-page TOC counts). Request "details" text priority: checkpoint (savedAt) > checkpoint > error > "Confirmed duplicate" > "Confirmed new" > "Resumed from saved progress". Src: 06 F120, F121; 07 RA-28, RA-29.
- D3-F70 Overview summaries (catalog, create, onHold, incomplete, notifications incl. latestFailedMessage); multipage/empty-chapters card summaries `{total, created, failed, processing}`. Src: 06 F125, F126.
- D3-F71 Full state payload (`state/`): summary, primary sync, both sync states, orchestration (`manualPipelineAdvance:false`), automation, cards, versions, and optionally ALL records and ALL requests unpaginated. Primary sync selection: incomplete if active/paused, else catalog if so, else whichever has activity, else higher version / later update. Src: 06 F127.
- D3-F72 Backfill command `backfill_multi_page_toc` (see section 3/8). Src: 08 section 6.

## 3. Actions by actor

### 3.1 Operator (scope `processing.manage`; every endpoint is gated by this single scope, including reads and SSE)

| Action | Entry | Effect | Features |
|---|---|---|---|
| Read full state / one card / one table page | GET state, card, table | Fetch payloads; search, filter by category/status, paginate (60 default, 600 max), facets | D3-F68..F71 |
| Subscribe to push | GET stream?page=catalog\|create\|on-hold\|incomplete | SSE of domain version changes | D3-F66 |
| Start manual catalog sync | POST sync/start | Manual run owns catalog runtime; no requests created | D3-F7, F18 |
| Pause / resume / stop sync | POST sync/pause, resume, stop (scope-less or `sync/<scope>/...`) | Cooperative pause, resume (mode optional), stop to idle | D3-F14..F16 |
| Run catalog automation now | POST automation/catalog/run | Sync then create requests for never-requested records | D3-F18, F24, F25 |
| Run incomplete automation now | POST automation/incomplete/run | Reconcile the incomplete archive; resolve vanished books | D3-F29..F37 |
| Save automation settings | POST automation/catalog/, automation/incomplete/ | enabled, interval, time; marks saved | D3-F38, F39 |
| Create requests for selected catalog records | POST records/create-requests | Bulk create INITIAL requests for selectable records, queued for processing | D3-F44 |
| Act on requests in bulk | POST requests/action | delete (optionally with the linked Book), pause, resume, retry, force_generate, new, new_edition, confirm_duplicate, create_again/recreate | D3-F64 |
| Per-page UI actions (docs) | UI buttons mapped to the above | Create/Delete (Catalog Books); Delete (Requests, Queue); Pause/Delete (Processing); Delete+book (Created); Resume/Delete (Paused); Retry/Delete (Failed); New/New Edition/Duplicate/Delete (Duplicate); Create Again (Deleted); Recreate/Delete (Updated). `force_generate` has no UI mention in docs. | 08 section 3 |
| Sign-in cookie refresh (implied) | Out of band | When a multi-page TOC is incomplete the error asks the operator to update the source-site auth cookie, then regenerate | D3-F53 |
| Manage via admin (Django admin) | admin.py | All 6 models registered; no read-only protection beyond timestamps | 08 |
| Backfill command | CLI `backfill_multi_page_toc [--dry-run] [--batch-size]` | One-off data repair for old requests | 08 section 6 |

### 3.2 System

| Actor | Action | Notes |
|---|---|---|
| Scheduler (Celery beat, config not in the read files) | `run_due_processing_automations_task` | Starts catalog then incomplete automation when due; waits if the runtime is owned by someone else |
| Celery worker | `run_processing_sync_task(singleton_key)` | Runs sync until blocked; guarded by task-id ownership |
| Celery worker / ingestion engine | `kickoff_book_creation_request_task(request_id)` (acks_late, reject_on_worker_lost); also the engine handler "pipeline" dispatched via `dispatch_job` | Returns `state: deleted, missing: true` for a missing row (conflates deleted with missing) |
| Maintenance task | `run_processing_maintenance_task` | Stale requests (20 min) and stale syncs, repair self-linked duplicates |
| Runtime tick | `run_processing_runtime_tick_task` | Advances syncs and pipeline one step (used when no workers / manual mode) |
| Heartbeat thread | touches `updated_at` every 300 s while scraping | Keeps recovery from requeuing live work |
| UI projection committer | `on_commit` hook | Rebuilds projections and bumps versions; no outbox |
| Redis mirror | writes sync checkpoints | Write-only |
| Test hooks in production | POST sync/start `remotePages`; POST sync/advance, pipeline/advance (14i harness) | `remotePages` honoured under pytest or `PROCESSING_ALLOW_REMOTE_PAGE_PAYLOADS`; advance endpoints appear in tests but are not in the 17 production routes read (UNVERIFIED whether they exist outside test settings) |

## 4. Business rules and invariants

Numbered for reference (BR-D3-n).

Catalog/sync
1. BR-1 One sync state row per scope (`catalog`, `incomplete`). At most one run mode owns a scope while active. A paused catalog sync may be taken over between manual and catalog_automation, but never by incomplete_automation (14i PA9, PA10; 06 F20).
2. BR-2 Catalog runtime and incomplete runtime are independent; the pause/stop buttons with no scope target incomplete first when both are active (07 ST-02).
3. BR-3 Pause is cooperative: status `pausing` is set immediately, the worker transitions to `paused` after the current page or batch and stores a checkpoint (`page-N` or `request-<lastRecordId>`). Live catalog fetch cannot pause mid-fetch (whole `refresh_catalog_parallel` must finish).
4. BR-4 Resume of catalog continues from the saved page; resume of incomplete restarts from page 0 (counts preserved).
5. BR-5 A manual sync never creates requests; only catalog_automation does, in phase 2. Phase 2 is anchored to the sync checkpoint token it started from (`baseCheckpointToken`); a different token resets phase-2 counters.
6. BR-6 Starting a sync while phase 2 is paused preserves the paused phase 2 (and its old base token); automation later resumes it (14i PA12).
7. BR-7 Auto-created requests are for records that have NO prior request AND `book_creation_state == NOT_CREATED` (code: F25). The docs disagree (section 8 issue I-D). Unsupported URLs are counted, not created.
8. BR-8 A record's category is "incomplete" if it contains an incomplete keyword or `was_incomplete`; "resolved" = vanished from the incomplete archive (not "book was built").
9. BR-9 Batch size 50 for request creation; page size 100 for offline pages; table page 60 default, 600 max; incomplete live max 250 pages.
10. BR-10 Records with empty URL are skipped during upsert. Record match is by id OR url (url is unique).
11. BR-11 Stale thresholds: request PROCESSING 20 min; sync SYNCING/PAUSING 20 min; dispatch marker 2 min; heartbeat 300 s.

Request/pipeline
12. BR-12 Request states: initial, queued, processing, created, failed, duplicate, deleted, paused. Terminal: created, failed, duplicate, deleted. Active: initial, queued, processing. BookRecord.book_creation_state mirrors the latest request state (latest by `-updated_at,-created_at,id`), else CREATED if it has a linked book, else NOT_CREATED. In the legacy DB this is enforced by Postgres triggers: updating a request's state propagates to the record, and a direct record update is overridden (14h PR6, VERIFIED only through test description).
13. BR-13 State transitions use compare-and-swap under a row lock (initial->queued->processing); entering processing clears the error and dispatch markers.
14. BR-14 Only source-site book URLs are processable; others fail with "Only source site book URLs are allowed".
15. BR-15 A record is selectable only when no non-FAILED/DELETED request exists, with the duplicate-original exception (F45). A record with a linked book and no requests is not selectable. A duplicate-flagged record is locked until its original request is failed or deleted.
16. BR-16 Duplicate detection: by source URL (claim unlinked book else DUPLICATE), then exact title (and optionally metadata, disabled by default via `PROCESSING_SKIP_METADATA_DUPLICATE_CHECK=True`). Skipped entirely when `is_confirmed_not_duplicate`. Duplicate operator decisions: `new` (process anyway; never re-flagged), `new_edition`, `confirm_duplicate` (keep as duplicate), `delete`.
17. BR-17 Retry policy: 3 attempts per run; non-retryable if message contains "source site"; 60 s delay for "Incomplete scrape:" only; failure message stored on the request.
18. BR-18 Review gate: a document is exported only if curated status is VALIDATED or `force_generate` is true; otherwise request FAILED with the book persisted but no exports. Force mode strips source "chrome" blocks and repairs duplicate content paths.
19. BR-19 Multi-page TOC: incomplete TOC (auth/sign-in problem) fails without retry; incomplete content (rate-limit) retries; neither overwrites existing content.
20. BR-20 Resume: saved scrape data is reused only if `is_resumed` and checkpoint is `scraped-content` (and effectively only if a curated result was saved). Corrupt checkpoint should fall back to full restart (spec; UNVERIFIED in code).
21. BR-21 Delete: optional soft-delete of the linked Book; a delete arriving mid-build soft-deletes the freshly built book at finalize. Pause/delete are noticed by a running worker only at checkpoints (after source metadata, after scrape, at finalize).
22. BR-22 Deleted-vs-created: deleting a created request with `deleteBook` deletes the Book; deleting a paused request clears saved progress (docs).
23. BR-23 Progress exposed to the client only when state is paused (full) or failed with `curatedValidation` (only `{curatedValidation, curatedStatus}`).
24. BR-24 Request ids are `request-<recordId>[-n]`; record ids are UUID strings (or the SourceCatalogEntry id in offline sync); both are string PKs.
25. BR-25 `resolve_incomplete_records` makes request and record CREATED without a Book (so "created" does not imply a book exists - `linkedBookId` can be null).

Automation
26. BR-26 Automation is off by default; weekly at 03:00 when unsaved; intervals daily/weekly/biweekly/monthly; unknown acts weekly; scheduled time is server-local; one run per due check, no catch-up. Catalog before incomplete in a tick.
27. BR-27 Scheduled run cannot pre-empt a manual run; it records "Waiting for the catalog runtime to become idle.".

UI/push
28. BR-28 Server pushes only version numbers; client refetches only the named cards; overview cards refetch only when their own aggregates change; bucket transitions invalidate source card, destination card and affected overviews only (docs, user stories). Projection is rebuilt before the version bump so a client never sees a new version with a stale projection.
29. BR-29 Search, filter and counts are server-side over the full dataset; count shows the full matched size; <60 matches hydrate in the first response; >=60 use incremental scrolling. During a card action, only that card's checkboxes/buttons are disabled.
30. BR-30 No-store cache headers on all responses.

## 5. Data handled / owned

### 5.1 Entities (legacy models, 08 section 2 data model)

BookRecord (catalog mirror of the source site; owned by processing)
- `id` string PK (uuid4 str or str(SourceCatalogEntry.id), max 120); `name`; `url` UNIQUE (<=1000); `category`; `writer`, `translator`, `composer`, `publisher` (blank ok); `book_creation_state` (not_created, initial, queued, processing, created, paused, failed, duplicate, deleted; indexed; default not_created); `linked_book` FK catalog.Book (SET_NULL); `was_incomplete`, `resolved_from_incomplete`, `will_resolve_to_category`; `is_duplicate`; `duplicate_of_record` self FK (SET_NULL); `source_catalog_entry` FK ingestion.SourceCatalogEntry (SET_NULL); created/updated timestamps. Ordering name,id.
- Lifecycle: created/updated by sync upserts; state recomputed after every request change; category/flags rewritten by incomplete resolution and by the start of each pipeline run (source metadata overwrite); wiped to NOT_CREATED by reset. Never deleted by processing.

BookCreationRequest (one attempt to build a book; owned by processing)
- `id` string PK; `book_record` FK (CASCADE); `state` (8 values, indexed); `origin` (user | curation | automation, default curation, indexed; never exposed in API); `progress` JSON null (`{savedAt, checkpoint, savedData}` for pauses; `{curatedValidation, curatedStatus}` for review failures; `_dispatchRequestedAt`, `_dispatchTaskId` markers); `error_message`; `is_resumed`; `is_confirmed_not_duplicate`; `force_generate`; `duplicate_of_request` self FK; `duplicate_of_record` FK; `duplicate_confirmed`; `has_multi_page_toc` (indexed), `source_toc_page_count` (default 1), `fetched_toc_page_count` (default 1); `linked_book` FK catalog.Book; `submission` OneToOne ingestion.BookSubmission (SET_NULL); `pipeline_outcome` char(32) default "created" (misleading default); timestamps. Ordering `-updated_at,-created_at,id`.
- Lifecycle: see section 7.1. Rows are deleted only by CASCADE (record deletion) and `reset_processing_data`; history is retained otherwise (a record may have many requests).

ProcessingSyncState (singleton per scope)
- `singleton_key` UNIQUE ("catalog", "incomplete"; model default "default"); `status` (idle, syncing, pausing, paused); `progress` JSON (phase model for catalog, flat for incomplete); `remote_pages` JSON list-of-lists (test/offline pages); `page_index`; `fetched_count`, `skipped_count`, `updated_count`, `appended_count`; `message` (<=500 chars, default "Ready to sync."); `task_id`, `queue_name`, `last_error`; timestamps.
- Catalog progress JSON (shape from tests 14i/14j): `phaseStatuses{sync,request_creation}` (compat view, maps pausing->running), `phaseStates{sync|request_creation:{status, owner, triggerSource, checkpoint, savedAt, savedData, baseSyncCheckpointToken}}`, `requestCreation{baseCheckpointToken,lastRecordId,processedCount,createdCount,unsupportedCount}`, `savedData{runMode,triggerSource,sessionId,checkpointToken,nextPageIndex,fetchedCount,liveFetch?}`. Three historical generations of the shape exist (legacy top-level `phase`, `savedData`, `requestCreation`), with ~450 lines of normalisation (14j PB2, PB3).

ProcessingAutomationSettings (kind catalog | incomplete, unique)
- `enabled`, `interval`, `time`, `saved`, `last_run_at`, `status_message`. Model defaults daily/02:00; service defaults weekly/03:00.

ProcessingUiDomainVersion (domain unique, version bigint, timestamps) and ProcessingUiProjection (key unique, payload JSON, timestamps; only 7 shared cards).

Read from other apps (not owned): SourceCatalogEntry (ingestion; source_url, title, author_line, normalized_title, normalized_display, raw_data{category, publisher, resolvedCategory,...}), BookSubmission (ingestion, legacy), Book/BookGroup (catalog), `CuratedBookDocument` (curated_persistence; read by the backfill command and by persistence).

### 5.2 Derived/ephemeral data
- Scrape cache JSONL files per request (runtime storage dir); Redis checkpoint keys `processing:sync-checkpoint:<scope>`; worker availability cache (2 s); domain-version collector (ContextVar).
- Message strings are user-visible copy (list in 07 MS-01) and should be preserved or replaced deliberately.

### 5.3 Settings/config that shape behaviour
`PROCESSING_USE_LIVE_SYNC` (False), `PROCESSING_ALLOW_REMOTE_PAGE_PAYLOADS` (False), `PROCESSING_INLINE_PIPELINE_ADVANCE` (False), `PROCESSING_SKIP_METADATA_DUPLICATE_CHECK` (True), `PROCESSING_CHECKPOINT_REDIS_URL` (falls back to `CELERY_BROKER_URL`), `CELERY_TASK_ALWAYS_EAGER`, `CELERY_PROCESSING_CONCURRENCY` (5), `RUNTIME_STORAGE_DIR`, `SOURCE_SITE_HOST`. Scrape limits: processing scrape (cheap) 48 nodes / depth 3 / 2 lesson pages / 12 000 chars; high fidelity 320 / 6 / 20 / 120 000; curate (current) unlimited nodes / depth 6 / 20 lesson pages / 60 000 chars (settings `PROCESSING_SCRAPER_MAX_*`, `PROCESSING_CURATE_MAX_*`; 14h PR8, PR9; 08 source.py). HTTP: 30 s timeout, `create_session_with_retries(retries=3, backoff_factor=1)`, host-fallback (tries host variants), UTF-8 forced decoding (14h PR10).

### 5.4 URL normalisation
`normalize_source_url("https://example.com/books/example-book")` -> `https://www.example.com/books/example-book/` (adds www, trailing slash) (14h PR7). Used as the dedupe key for records, books and incomplete lists.

## 6. Interfaces

Mounted at `/api/processing/` (config/urls.py:12, grep per report 08). All DRF APIView, permission `CanManageProcessing` (scope `processing.manage`), all responses `Cache-Control: no-store, no-cache, must-revalidate, max-age=0` + `Pragma: no-cache`. Anonymous or non-processing users get 403 (14h PR5). Mutations are wrapped in the version collector and return `{ "ok": true, "versions": { "<cardKey>": int, ... }, ...extra }` (only keys in the 20 card keys; unknown domains dropped). Source: 08 section 2.

| # | Method | Path | Request | Response | Behaviour |
|---|---|---|---|---|---|
| 1 | GET | `state/` | `includeLists` bool, default true (1/true/yes/on, 0/false/no/off) | full state payload (summary, sync, syncStates, orchestration, automation, cards, versions, optionally all records and requests) | Read only. `ProcessingStateSerializer` exists but unused |
| 2 | GET | `card/` | `card` required (400 `{"card":["This query parameter is required."]}`); unknown card 400 "Unsupported processing card: X" | shared card payload with `version` | Only the 7 shared cards |
| 3 | GET | `table/` | `card` required; `q`, `category`, `status`, `offset` (>=0), `limit` (1..600, default 60), `includeFacets` (default true); unknown -> 400 "Unsupported processing table" | `{rows, pagination, hasMore, filters?, version, summary?}` | Read only |
| 4 | GET | `stream/` | `page` in {catalog, create, on-hold, incomplete} (default catalog), else 400 "Unsupported processing page" | SSE `text/event-stream`: `event: connected data: {}`; then `event: versions data: {"eventId": <ms epoch>, "versions": {domain: n}}` on change; `: keepalive` after 15 s idle; `X-Accel-Buffering: no` | Polls DB every 1 s; infinite generator holding one worker thread per connection. VERIFIED keepalive 15 s and sleep poll at read_stream...views.py:168-195 |
| 5 | POST | `sync/start/` | `{remotePages?: list[list[dict]]}` honoured only if remote page payloads are allowed | mutation payload | `run_manual_catalog_sync` |
| 6 | POST | `sync/pause/` | none | mutation payload | `pause_sync(active_sync_scope())` |
| 7 | POST | `sync/resume/` | optional `runMode` in {manual, catalog_automation, incomplete_automation}; default from state; invalid 400 `{"runMode":[...]}` | mutation payload | `resume_sync` |
| 8 | POST | `sync/stop/` | none | mutation payload | `stop_sync` |
| 9 | POST | `sync/<scope>/pause/` | scope in {catalog, incomplete} else 400 | as 6 | scoped duplicate of 6 |
| 10 | POST | `sync/<scope>/resume/` | as 7 | as 7 | scoped duplicate |
| 11 | POST | `sync/<scope>/stop/` | as 8 | as 8 | scoped duplicate |
| 12 | POST | `records/create-requests/` | `{ids: non-empty list[str]}` | mutation payload + `createdCount` | `create_requests_for_record_ids(ids, actor=request.user)`; actor unused |
| 13 | POST | `requests/action/` | `{ids: non-empty list[str], action: delete\|pause\|resume\|retry\|force_generate\|new\|new_edition\|confirm_duplicate\|create_again\|recreate, deleteBook: bool=false}`; ValueError -> 400 `{"detail": msg}` | mutation payload + `changedCount` | per-action rules D3-F64; ids unbounded |
| 14 | POST | `automation/catalog/` | `{enabled?, interval? non-blank str, time? HH:MM[:SS]}` | mutation payload | upsert settings, saved=true |
| 15 | POST | `automation/catalog/run/` | none | mutation payload | `run_catalog_automation()` |
| 16 | POST | `automation/incomplete/` | as 14 | mutation payload | settings for incomplete |
| 17 | POST | `automation/incomplete/run/` | none | mutation payload | `run_incomplete_automation()` |

Notes: only GET and POST exist; all deletions go through `requests/action`. No endpoint to read automation settings (they ride in `state/`/`card/`), list runs, delete catalog rows, create a book directly, or review a title match. The two extra pages (`/multipage-toc`, `/reprocessing`) have no backend API in these files. Test-only routes seen in the harness: POST `sync/advance/`, `sync/<scope>/advance/`, `pipeline/advance/` -> `{advancedCount}` (14i; UNVERIFIED in production URLs).

### 6.1 Serializer shapes (camelCase)
- BookRecord: id, name, url, displayUrl (unquoted), displayPath, category, writer, translator, composer, publisher, createdAt, updatedAt, bookCreationState, linkedBookId, linkedBookSlug (null if book soft-deleted), wasIncomplete, resolvedFromIncomplete, willResolveToCategory, isDuplicate, duplicateOfRecordId, selectable, latestRequestId (N+1 per row).
- BookCreationRequest: id, bookRecordId, state, createdAt, updatedAt, progress (rule BR-23), errorMessage, isResumed, isConfirmedNotDuplicate, duplicateOfRequestId, duplicateOfRecordId, duplicateConfirmed, linkedBookId, linkedBookSlug (falls back to record's), pipelineOutcome, hasMultiPageToc, sourceTocPageCount, fetchedTocPageCount.
- SyncState: see D3-F19. AutomationSettings: kind, enabled, interval, time ("%H:%M"), saved, lastRunAt, statusMessage.

### 6.2 SSE detail
Stream polls `ProcessingUiDomainVersion` for the page's domain set (`PROCESSING_PAGE_DOMAINS`: catalog, create, on-hold, incomplete; multipage and empty-chapters groups exist in constants but not as stream pages). `eventId` is a wall-clock ms value, not a durable cursor: a reconnect cannot replay missed changes (client must refetch on `connected`). No `Last-Event-ID`, no max duration, no auth refresh.

### 6.3 Background task interfaces (Celery)
`run_processing_sync_task(singleton_key="catalog")`, `kickoff_book_creation_request_task(request_id)` (acks_late, reject_on_worker_lost), `run_due_processing_automations_task()`, `run_processing_maintenance_task()`, `run_processing_runtime_tick_task()`. 14h PR3 additionally requires ingestion tasks `run_catalog_automation_schedule_task` and `recover_stale_processing_jobs_task` to be discoverable (shows the tight coupling with the ingestion app).

### 6.4 Outbound interfaces
- To the source website: catalog archive listing (params `page`, `q`), per-book page metadata, incomplete genre archive (`/genres/<slug>/`, `/page/N/`), book content scrape (via ingestion `curate_book`). Authenticated scraping with a source-site cookie is implied by the "Sign-in required" error.
- To the ingestion engine: `dispatch_job(job_id, job_type="pipeline", handler="pipeline")`.
- To the catalog: `persist_curated_book`, `persist_scraped_book`, `sync_assets` (requires HTML and EPUB asset types), `generate_exports` (`html_book.create_html_book`, `epub_book.create_epub`), `find_exact_existing_book`, `find_existing_book_by_source_url`, `detect_metadata_duplicate`, `sync_metadata_relations` (contributors, series, categories), `BookGroup`.
- To Redis (checkpoint mirror) and Celery/Kombu (revoke, purge, inspect with 0.5 s timeout).

### 6.5 EPUB output contract asserted by the regression harness (live test matrix, 08)
Spine order `cover -> title -> info? -> dedication? -> front_section_* -> toc -> (lesson_+ | main_content) -> back_section_* -> nav`; EPUB-3 `nav.xhtml` comprehensive and never links to itself; printed `toc.xhtml` content-scoped; no blank content/front/back page. Harness: `tests/scripts/regression_curate_300.sh` (`--limit N`, `--retry-failed`, resumable state in `/app/storage/regression-300/state.json`, exit 0 only if every URL verdict ok). This belongs to the ingestion/export analysis but constrains the rebuild.

## 7. States and processes

### 7.1 BookCreationRequest state machine

States and moves (all via compare-and-swap in the pipeline; operator actions are unguarded):

| From | To | Trigger | Guard / note |
|---|---|---|---|
| (new) | initial | create request | supported URL |
| (new) | created | incomplete resolution when record had no request | no Book |
| initial | queued | enqueue, kickoff, ticker | CAS |
| queued | processing | kickoff, ticker (inline), worker | CAS; clears error and markers |
| processing | queued | stale recovery | `updated_at` < now-20 min; `is_resumed=True` |
| processing | created | finalize | not deleted/paused at the end |
| processing | failed | 3 failed attempts; immediate on "source site" ValueError; review gate | no-op for deleted/paused |
| any | failed | unsupported URL on queue | "Only source site book URLs are allowed" |
| processing/initial/queued | duplicate | duplicate detection | source URL (not claimable) or exact title; not if confirmed-not-duplicate |
| duplicate | created | repair self-linked duplicate | rare |
| any | paused | pause action | unguarded; worker notices at 2 checkpoints |
| paused | initial | resume action | unguarded (works from any state); `is_resumed=True` |
| any | initial | retry, force_generate, new, new_edition, recreate | flag resets differ per action |
| any | deleted | delete | optional book soft-delete |
| any (latest) | created | resolve incomplete | no Book |
| all | row removed | reset | |

Checkpoints: `source-metadata` (saved but never consumed) and `scraped-content` (`{scrapedData, curatedResult}` saved after scrape; `{scrapedData, linkedBookId}` saved at finalize if paused - inconsistent, see issues).

Normal path per request: INITIAL -> QUEUED (dispatch to engine) -> PROCESSING (worker) -> [metadata capture -> duplicate-by-URL -> scrape+curate (heartbeat, disk cache) -> TOC signal -> duplicate-by-title -> persist -> export] -> CREATED or FAILED(review) or DUPLICATE or PAUSED/DELETED mid-flight.

Failure modes of a request: source unreachable/blocked (retries, then FAILED with last error), rate limiting ("Incomplete scrape", 60 s sleeps, up to 3 tries), sign-in/TOC incomplete (immediate FAILED with actionable message), invalid curated doc with no title ("Curated document requires review before a book can be created."), curation returned no content ("Source curation returned no content for {url}. Verify the source URL is valid and publicly reachable."), review gate (FAILED with persisted book), stale (20 min), worker lost (acks_late + reject_on_worker_lost requeues), dispatch failure (falls back to running inline in the caller).

### 7.2 BookRecord.book_creation_state
Mirror of the latest request state; else CREATED if linked book; else NOT_CREATED. In the legacy DB also trigger-enforced (14h PR6). Catalog upsert also writes it directly before the recompute (churn, see issues).

### 7.3 Sync state machine (per scope)
idle -> syncing (start/resume); syncing -> pausing (pause); pausing -> paused (worker after page/batch, or stale recovery after 20 min "progress saved after interruption"); paused -> syncing (resume/take-over); syncing/pausing/paused -> idle (stop; finalize; fail). Stale syncing stays syncing, message "Recovering interrupted <label>.", task redispatched.

Catalog two-phase process (what tests prove; 14i PA2, PA3 matrices, 14j PB1):
- Phase 1 sync: fetch pages -> upsert records (counters: fetched/skipped/updated/appended). Completed -> checkpoint token produced.
- Phase 2 request_creation: scan BookRecords in id order in batches of 50 -> create requests for eligible. Completed -> automation message.
- Manual start: phase 1 only; if phase 2 is running (owned by automation) the manual start is a no-op reporting phase 2; if phase 2 is paused it stays paused; if phase 2 completed it is reset to not_started.
- Automation run: if sync is completed and phase 2 not started -> go straight to phase 2; if phase 2 paused -> resume phase 2; if sync paused -> resume phase 1; if both completed -> restart at page 0; else start.
- Matrix reading (summarised from the 10-row manual and 10-row automation matrices): pausing is a no-op for a second start; resume only from paused; completed+completed restarts.

#### 7.3.1 Request-creation phase reachability bug (claim checked)
Claim: after a LIVE catalog fetch in catalog_automation mode, sync_runner.py ~194-199 goes straight to finalize_catalog_sync after request creation starts. VERIFIED. sync_runner.py:194-199 reads: `if run_mode == CATALOG_AUTOMATION: state = begin_catalog_request_creation(state); if state.status not in SYNC_ACTIVE_STATUSES: return state;` then `return finalize_catalog_sync(state, run_mode=run_mode)`. `begin_catalog_request_creation` (sync_completion.py:180-190) sets `state.status = SYNCING` and saves, so the active-status check is false and execution falls through to `finalize_catalog_sync`. `finalize_catalog_sync` (sync_completion.py:88-114) builds `catalog_progress_after_completion(...)` with the default `request_creation_phase_status=NOT_STARTED` (sync_completion.py:31, 70-79: stays paused only if it was paused, else not_started) and persists with status IDLE and "Sync complete..." message. Result: in live mode, the request-creation phase begins and is immediately overwritten; no requests are created in the same run. Contrast: the non-live path (`advance_catalog_sync_once`, incomplete_resolution.py:171-176) returns `begin_catalog_request_creation(state)` directly and works. Mitigation in the code: a second `run_catalog_automation` sees sync phase completed + request_creation not_started and calls `begin_catalog_request_creation` directly (automation_commands.py:187-193, VERIFIED), so automation needs two clicks/ticks in production live mode. The tests exercise the non-live path (remotePages / SourceCatalogEntry snapshot), so the bug is untested. Severity High (silent functional gap in the primary automation path). For the rebuild: model phase transitions as explicit transitions with one test per path (live and snapshot).

### 7.4 Pause/resume/ownership summary
- Ownership token: `task_id` on the state row; workers ignore themselves if `task_id` changed (stop clears it, a new start sets a new one).
- Owner conflict: BR-1. Scheduler yields; manual button disabled in UI while automation owns the runtime and vice versa.
- Pause is checked at: after each page (catalog, non-live), after each incomplete page, after each request-creation batch; NOT inside a live parallel fetch.
- Resume semantics: catalog continues from saved page (note the docs say "resume starts at page 1 and reconciles saved rows up to the checkpoint", the code continues from `nextPageIndex`: contradiction, issue I-L).

### 7.5 Request creation
Selected IDs -> `record_is_selectable` filter -> `create_request_for_record` -> `queue_processing_request` (engine dispatch or inline). Automation creates origin=AUTOMATION requests in phase 2 and publishes `catalog-automation` and `create-overview`. Incomplete resolution creates CREATED requests without a build.

### 7.6 Incomplete tracking process
Run: fetch archive (live or local ids) -> upsert/refresh incomplete records -> compute stale (records no longer on archive) -> resolve stale (category replaced, flags set, request CREATED) -> counts + automation message. UI: Incomplete card (read-only list of unresolved), Updated card (`incomplete-completed`; bulk Recreate -> request INITIAL, bulk Delete -> request DELETED).

### 7.7 Retries and recovery
Per-request: 3 attempts, 60 s sleep for rate-limit signal, none otherwise; heartbeat; stale recovery 20 min; dispatch marker 2 min; inline fallback on dispatch failure; acks_late. Per-sync: stale recovery re-dispatches; failure -> idle with `last_error`; no automatic retry of a failed sync (next schedule or manual).

### 7.8 UI invalidation flow (summary)
Data change -> `publish_processing_ui_domains` (on_commit) -> rebuild shared projections -> bump versions -> SSE poller sees new versions -> sends `versions` event -> client refetches named cards -> table/card endpoints stamp `version`. Mutating HTTP responses include the versions they caused (ignore own echo). Loss window: crash between commit and hook loses the notification (no outbox).

## 8. Issues

Severity: H high, M medium, L low. Mark: V = VERIFIED in code this pass, U = UNVERIFIED (from reports only). IDs I-A.. for cross-reference.

### 8.1 Correctness bugs
- I-A (H, V) Live catalog automation never creates requests in the same run: `begin_catalog_request_creation` then immediate `finalize_catalog_sync` (sync_runner.py:194-199 with sync_completion.py:27-114, 180-190). Detail in 7.3.1. Second run recovers (automation_commands.py:187-193). Untested path (tests use snapshot pages).
- I-B (H, V) Empty incomplete candidate list resolves every incomplete record: `incomplete_automation_pages` only includes records that already have `will_resolve_to_category` (automation_advancement.py:189-203); if none, pages are `[[]]`; `advance_incomplete_sync_once` empty-page branch calls `stale_incomplete_record_ids` (sync_runner.py:11-16; incomplete_resolution.py:72-97) whose `incomplete_remote_urls` is empty, so all unresolved incomplete records are "stale" and resolved to "Uncategorized"/CREATED. Data-corrupting.
- I-C (H, V logic) "Resolved" means "left the incomplete archive", and `resolve_incomplete_records` marks request+record CREATED with no Book (incomplete_resolution.py:3-53). `created` therefore does not imply a readable book; the Updated card can show a "created" book that does not exist.
- I-D (H, U) Catalog re-sync overwrites `resolved_from_incomplete` (payload never carries it), `category`, `linked_book`, `book_creation_state` (catalog_record_sync.py:27-46,81-94); a later catalog sync un-resolves resolved incomplete books, and any record with a request counts as "updated" every sync. Also the three docs disagree on which records get auto-requests: code and UC-03/user story 7 = never-requested only (also requires NOT_CREATED), processing_pages.txt = also last request failed/deleted.
- I-E (H, U) `refresh_catalog_parallel` has no max page count, swallows all exceptions with `continue`, no logging, counters only at the end, no pause/cancel check; with the source down each worker loops forever (catalog_record_sync.py:240-264). Audit confirms "stop" does not cancel the background fetch (08 section 5 item 1).
- I-F (M, U) `new_edition` is functionally "new" plus an orphan BookGroup: depends on `request.submission` which the current pipeline never creates (persist_* called with None submission); `target_book_group_id` never written (request_action_dispatch.py:30-47).
- I-G (M, U) Paused-at-finalize checkpoint saves `{scrapedData, linkedBookId}` without `curatedResult`, so resume re-scrapes; `source-metadata` checkpoint is saved and never read (request_processing_persistence.py:248-257).
- I-H (M, U) `_finalize_processing_request` on DELETED soft-deletes `book` even when it was a pre-existing target book being rebuilt (request_processing_persistence.py:243-247).
- I-I (M, U) No state guards: pause a CREATED request, resume a DELETED one, delete anything; `apply_resume_action` keeps `duplicate_confirmed` and record duplicate flags. Pause/delete of a PROCESSING request does not interrupt the scrape (noticed only at 2 checkpoints), and an exception from `_apply_multi_page_toc_signal` for a PAUSED request is swallowed (fail no-ops for paused) (07 item 3).
- I-J (M, U) `apply_confirm_duplicate_action` publishes domains with before=after=DUPLICATE, so the previous state's card (e.g. FAILED) may not refresh (07 item 10).
- I-K (M, U) `next_request_id` check-then-create race gives duplicate ids -> IntegrityError; ids are derived strings (request_queue_runtime.py:3-9).
- I-L (M, U) Doc/code mismatch on resume: docs say resume restarts at page 1 and reconciles to the checkpoint; code (and test PA9) continues from the saved page. Docs say Redis mirrors the checkpoint on pause; the mirror is write-only.
- I-M (M, U) "Latest request" ordering by `updated_at` means heartbeats or any touch can reorder latest and flip the record's mirrored state (processing_state_queries.py:133-153; heartbeat request_processing_pipeline.py:14-17). Heartbeat keeps updating while the main thread is hung, so hung work is never recovered.
- I-N (M, U) Blocking `time.sleep(60)` (up to 120 s) inside workers/ticker; other errors retry with no backoff. `advance_pipeline_once` and `queue_processing_request` can run an entire scrape synchronously in the HTTP/ticker process on dispatch failure.
- I-O (M, U) Scrape cache is only deleted on success; FAILED/DELETED/DUPLICATE/abandoned requests leak JSONL files; retries reuse stale cached pages (keyed by request id/source_url, no freshness); the code comment assumes concurrency 1 but setting default is 5; no locking.
- I-P (M, U) `ProcessingAutomationSettings` model defaults daily/02:00 vs service defaults weekly/03:00; `interval` unvalidated (any string acts as weekly); malformed `time` ("25:99") raises ValueError -> 500 unless guarded (06 issue 26).
- I-Q (M, U) Backfill command bug: paging by offset over a filter that shrinks as rows update (skips rows); `bulk_update` of `updated_at` does not auto-refresh; `.only()` with `select_related("linked_book")` may raise deferred-and-traversed error; imports `CuratedBookDocument` from a pipeline module (cross-app coupling).
- I-R (L, U) Stale-recovery / `kickoff_book_creation_request_task` conflates missing and deleted (`state: deleted, missing: true`). `queue_processing_request` for an invalid URL on a PAUSED request may not publish.
- I-S (L, U) `capture_source_page_metadata` swallows every exception and returns None, hiding source failures; `pipeline_outcome` defaults to "created" for new requests; `INCOMPLETE_CATALOG_URL` computed at import (empty host gives `https:///genres/...`); dead second source-duplicate block; `_REVIEW_REQUIRED_ERROR_MSG` unused; odd count arithmetic in `_fix_duplicate_paths_in_document`.
- I-T (L) String-typed control flow: "source site" substring and "Incomplete scrape:" prefix decide retry (07 item 5). Replace with typed errors.

### 8.2 Security
- I-U (H, V) Test backdoor in production: `allow_processing_remote_page_payloads` is true whenever `PROCESSING_ALLOW_REMOTE_PAGE_PAYLOADS` is set OR `"pytest" in sys.modules` OR env `PYTEST_CURRENT_TEST` is set (checkpoint_and_runtime_adapters.py:231-236, VERIFIED). Lets a caller with `processing.manage` inject arbitrary catalog records via `sync/start/` `remotePages`. Similar pytest branches in worker/live-sync decisions (F08, F30, F31, F45).
- I-V (M, U) Single coarse permission `processing.manage` guards reads, SSE, bulk deletes and `deleteBook` (book deletion from catalog). No per-action scope, no audit trail: `actor` is accepted and ignored everywhere (create requests, request actions).
- I-W (M, U) Unbounded `ids` lists on bulk endpoints, no rate limiting, no idempotency keys; `apply_request_action` has no transaction (one failure aborts the loop after earlier items committed, and `sync_records_for_requests` is skipped).
- I-X (M, U) SSE: one blocked worker thread per connection, 1 s DB polling per connection, no auth refresh, no durable cursor/replay, no max duration (DoS and correctness).
- I-Y (L, U) The source-site auth cookie (needed for multi-page TOC) is a secret the system depends on; its storage and rotation are outside the read files. Treat it as a secret in the rebuild.

### 8.3 Design flaws and tech debt
- I-Z (H, U) Fragment-by-`exec` architecture: `services.py` and `views.py` `exec` 26+2 files into one shared namespace; fragments have no imports, are unlintable and not importable, with hidden name collisions and circular service<->serializer dependencies. Must not be replicated.
- I-AA (M, U) Dual-write denormalisation: `BookRecord.book_creation_state` mirrors the latest request, maintained both by code (`sync_record_state`) and by Postgres triggers (14h PR6), with two near-identical enums. Triggers and code paths can disagree (the test proves a direct record update is overridden).
- I-AB (M, U) UI invalidation: no outbox (crash between commit and hook loses notifications); `ensure_processing_ui_rows` recomputes all shared payloads including summary aggregations every publish (double work, 07 item 11); projection rebuild happens in `on_commit`; domain versions are plain integers without epoch (a DB restore breaks clients using `>`); `empty-chapters-records` is never published here; `versions` filtered by card keys while SSE uses page domains.
- I-AC (M, U) Read-path cost: `state/?includeLists=true` serialises all records and requests unpaginated; BookRecordSerializer N+1 (`latest_request_for_record` per row); `processing_table_payload` repeats a 16-field `.defer()` list four times; table builders exist twice (unused `PROCESSING_TABLE_BUILDERS` path); status search is `icontains` on many columns (no index strategy).
- I-AD (M, U) Three generations of progress JSON and ~450 lines of normalisation; duplicated pause/resume blocks in sync loops; four near-identical request-reset actions.
- I-AE (L) Test seams in production (`scrape_book.__module__ != "apps.processing.source"` hack that also bypasses heartbeat, cache and review gate; `run_processing_sync` alias; pytest sniffing).
- I-AF (L) Two scrape paths coexist: legacy `scrape_book` (tiny limits 48 nodes / 2 lesson pages / 12 000 chars, likely truncating) and `curate_book`; `scrape_book_high_fidelity` unused in processing.
- I-AG (L) Redis checkpoint mirror is write-only and a down Redis costs up to 0.5 s per `save_sync_state`.
- I-AH (L) Duplicated route pairs (scoped and scope-less pause/resume/stop); `ProcessingStateSerializer` unused; unused imports/constants.
- I-AI (L) Message strings embed English UI copy in the service layer; no i18n.
- I-AJ (M, U) UI-side gaps recorded by the audit (08 section 5): selection checkboxes not locked during actions on most cards, Incomplete Updated-recreate lock released before the request reaches terminal state, On Hold cannot filter by originating stage and `origin` is never exposed, no true backend cancellation of the catalog refresh after stop, optimistic stop shows "stopped" while fetching continues.
- I-AK (L, U) Docs are partly stale: obsolete run-history card family, Review Match dialog, "Stop selected/Start/Add Again to Queue" actions that no longer exist, Mode/Pages automation fields that the API lacks, "validated" test counts for the old six-page model. Spec language inconsistency (JavaScript vs TypeScript). Notification and sound requirements (2-minute failure batching, mute toggle) have no backend and unknown frontend status.

### 8.4 Overlap and duplication with the ingestion app
- I-AL (H) The processing app is a second orchestration layer sitting on top of the ingestion pipeline. Shared concepts: SourceCatalogEntry (owned by ingestion, written by processing's live fetch), `BookSubmission` (OneToOne on BookCreationRequest, effectively dead), the ingestion engine's job dispatcher (`dispatch_job(handler="pipeline")`), ingestion tasks (`run_catalog_automation_schedule_task`, `recover_stale_processing_jobs_task`, 14h PR3), `TitleResolver.refresh_catalog` (ingestion/services/resolution.py), `cancel_source_catalog_refresh` (ingestion/services/curation.py), duplicate detection (`find_exact_existing_book`, `detect_metadata_duplicate`), `curate_book`, `persist_*`, `generate_exports`, `sync_assets`. There are two catalog-sync implementations (ingestion's `TitleResolver` + automation schedule task, and processing's `refresh_catalog_parallel` + two-phase sync), two stale-recovery mechanisms (`mark_stale_processing_requests` vs `recover_stale_processing_jobs_task`), two job/retry notions (ingestion job families Create/Match/Regenerate in old docs vs request states), and two scrape-limit regimes.
- I-AM (M) Legacy "job family" concepts (ingestion/resolution/reprocess steps, run-history cards, Review Match) still appear in docs but the request model has no job type; the rebuild must pick one model and one orchestrator.
- I-AN (M) `/multipage-toc` and `/reprocessing` pages are documented as one-liners without API; their data (`has_multi_page_toc` etc.) exists, "reprocessing queue" semantics unknown.

## 9. Keep / change / drop for a rebuild

### 9.1 Keep (concepts and behaviours)
- K1 Catalog mirror as local read model (BookRecord) separate from built Books; URL (normalised) as natural key. Reason: operator needs a browsable, searchable view of everything on the source whether built or not.
- K2 Request-per-attempt with history and an explicit state machine (initial, queued, processing, created, failed, duplicate, deleted, paused); latest request determines record display state. Reason: auditability and retry.
- K3 Compare-and-swap state transitions and row-level idempotent workers; task-ownership token on sync state. Reason: correctness under concurrent workers.
- K4 Cooperative pause with durable checkpoints; resume from checkpoint; stale detection with heartbeat. Reason: scrapes take 15-20+ minutes and sources rate-limit.
- K5 Two-phase catalog automation with checkpoint-token anchoring and owner rules (manual vs automation share the catalog runtime; incomplete independent). Reason: encoded in 20+ behaviour tests (14i, 14j) and gives deterministic resume semantics.
- K6 Duplicate-review flow (auto-detect, operator chooses new / new edition / confirm duplicate / delete) and the selectability rule.
- K7 Review gate (do not publish an unvalidated document unless the operator forces) and typed failure reasons shown to the operator, including the actionable "sign-in required" TOC error.
- K8 Domain-version invalidation with per-card refetch and mutation responses returning produced versions; server-side search/filter/pagination/facets; backend-owned aggregates.
- K9 Scheduler with enabled/interval/time/last_run and "waits for runtime" behaviour; one run per due check.
- K10 Incomplete-books reconciliation concept (separate runtime, resolution when a book leaves the incomplete archive) - but with the safeguards below.
- K11 Bulk operator actions with partial-success reporting (`changedCount`, `createdCount`).
- K12 Resumable page cache for scraping (disk or object store) so retries do not refetch.
- K13 Message strings for operator feedback (as content to be revisited).
- K14 The EPUB structural contract and the 300-book regression harness as acceptance tests (owned by export analysis).

### 9.2 Change
- C1 Replace exec-fragment architecture with real modules/crates and explicit interfaces; split into: catalog-sync, request-lifecycle, build-pipeline orchestration, automation scheduler, and UI projection/notification service. Reason: I-Z.
- C2 Make phase transitions explicit (typed state machine, one transition function per edge, property tests per path including live and snapshot). Fix I-A by design. Replace three progress-JSON generations with one typed progress record plus a version field; no legacy migration code.
- C3 Redefine incomplete handling: "resolved" must mean a Book exists or an explicit operator decision; never auto-resolve on an empty candidate list; require a non-empty fetched list (and sanity thresholds, e.g. refuse to mass-resolve when the fetch returned 0 items or the fetch failed). Fix I-B, I-C. Keep `resolved_from_incomplete` persistent across catalog syncs (merge, do not overwrite) (I-D).
- C4 Single source of truth for record display state: compute from requests (view or query) instead of denormalised column plus triggers plus code, or keep one mechanism (a projection updated in the same transaction). Reason: I-AA.
- C5 Typed errors with retryability (Retryable, RateLimited{retry_after}, AuthRequired, Fatal) instead of substring matching; exponential backoff with jitter and no worker-blocking sleeps (re-queue with delay). Reason: I-N, I-T.
- C6 Operator action guards: explicit allowed-source-state table per action; reject invalid transitions with 409 and per-item results (not silent skip); run each item in its own transaction with a result list; add actor + audit trail (who did what). Reason: I-I, I-W, I-V.
- C7 Live catalog fetch: bounded pages, structured logging, error budget (stop and fail after N consecutive errors), cooperative cancel/pause between pages, streaming counters. Reason: I-E.
- C8 Delivery of invalidation: transactional outbox (or LISTEN/NOTIFY) feeding SSE/WebSocket; durable event ids with resume (`Last-Event-ID`); async server, not a thread per connection; versions with epoch. Compute shared summaries incrementally rather than twice per publish. Reason: I-X, I-AB.
- C9 Remove production test hooks: no pytest sniffing, no `remotePages` in the public API (use test-only fixtures or a gated internal admin tool). Reason: I-U.
- C10 Permissions: separate read vs mutate vs destructive (book delete) scopes, surfaced in the gateway; rate limits and max bulk size; idempotency keys for bulk calls.
- C11 Own one orchestrator: processing as thin operator facade (catalog mirror, requests, review) over an ingestion service that owns scraping, curation, build, export and job dispatch via a message/queue contract; delete duplicate catalog-refresh and stale-recovery implementations (I-AL).
- C12 Pagination/keyset on all lists; remove unpaginated `includeLists`; fix N+1 with batch loads or a read model. Expose `origin` and originating stage for on-hold filtering.
- C13 Fix the `new_edition` flow (explicit book-group assignment on the request, no hidden `submission` dependency) or drop it until needed.
- C14 Unify automation defaults and validate interval (enum) and time at the boundary; add timezone setting explicitly; consider catch-up policy.
- C15 Scrape cache cleanup (TTL and delete on terminal states); cache key includes request id + content freshness policy.
- C16 Make `created` mean "has a Book"; model "resolved-without-build" as a distinct state if still needed.
- C17 Secrets: source-site auth cookie in a secret store with an operator-facing refresh flow and health check.

### 9.3 Drop
- D1 Redis write-only checkpoint mirror (or make it the real checkpoint store; do not keep a mirror nobody reads).
- D2 Legacy scrape path (`scrape_book`, `scrape_book_high_fidelity`, `persist_scraped_book`, the monkeypatch module check) and the tiny scrape limits.
- D3 Legacy progress-shape migration code, `phaseStatuses` compat view (pausing->running) unless a client needs it.
- D4 Duplicated route variants (keep scoped `sync/<scope>/...` only), unused serializers, dead code listed in 06 item 22, `PROCESSING_TABLE_BUILDERS` duplicate query path.
- D5 `BookSubmission` linkage and `pipeline_outcome` (misleading default) unless a real use appears.
- D6 Obsolete UI concepts: run-history card family, Review Match dialog, job-family step labels; `source-metadata` checkpoint (never consumed) unless resume actually uses it.
- D7 Inline-fallback execution (running a scrape in the HTTP/ticker process), the manual "advance" test endpoints in production, `manualPipelineAdvance` flag.
- D8 DB-trigger based mirroring (if C4 adopts a single mechanism).

## 10. Open questions

1. Should live catalog automation create requests in the same run (intended) or intentionally in a second run? The legacy flow is clearly a bug (I-A) but docs (UC-03) say "after completion initial requests are created"; confirm intent and the exact eligibility rule: never-requested only (code, UC-03) versus also last-failed/deleted (processing_pages.txt).
2. What should "resolved incomplete" mean in the new system: book vanished from archive, a Book built, or operator-confirmed? What should happen to the request (CREATED without a Book) and to `will_resolve_to_category` (who populates it? not found in the read files)?
3. Who writes `empty_chapters_count` on Book (the `empty-chapters-records` card depends on it and is never published here)?
4. What do `/multipage-toc` and `/reprocessing` pages do; is there a reprocessing queue distinct from retry/force_generate/recreate? `force_generate` has no UI mention: keep as an operator escape hatch?
5. Notifications and sounds (spec Part 3): are they in scope for the rebuild, and where do they run (frontend only; backend events)?
6. Which orchestrator owns scraping jobs: keep a separate processing request model or fold requests into the ingestion job model (see I-AL)? How do the two apps share SourceCatalogEntry?
7. Is operator multi-user concurrency real (several operators) or single operator? Affects ownership, audit, permission granularity, and whether `actor` matters.
8. Scale numbers: expected catalog size, bulk selection size, concurrent scrapes, and acceptable rate against the source site (429 handling, `retry-after`); legacy spec asks for 200+ bulk actions and no timeout for 15-20+ minute items.
9. How is the source-site auth cookie obtained and rotated; should the system detect expiry proactively?
10. Are the Postgres triggers (14h PR6) part of the contract that other services rely on, or an implementation detail to drop?
11. Do test-only endpoints `sync/advance`, `pipeline/advance` exist in production routes (not in the 17 read, only in tests)? Where does the beat schedule live (not in the files read)?
12. Timezone and "monthly"/"weekly" semantics: is server-local time acceptable; should missed runs be caught up?
13. Is the catalog sync required to be pausable mid-fetch (true cancellation), given the audit found stop does not stop the fetch?
14. Retention: should requests, scrape caches and history be pruned; are deleted requests kept forever?
15. Resume semantics for catalog: continue from checkpoint (code/tests) versus restart from page 1 and reconcile (docs); which is wanted?

## Appendix: coverage and caveats
- Read in full: reports 06, 07, 08, 14h, 14i, 14j. Code re-read for verification: sync_runner.py lines 100-216, sync_completion.py lines 25-191, automation_commands.py lines 160-200, incomplete_resolution.py (stale detection, advance_catalog_sync_once, advance_catalog_processing_once), automation_advancement.py lines 189-203, checkpoint_and_runtime_adapters.py lines 231-236, view stream grep (keepalive 15 s, sleep poll), sync_runner.py lines 1-30 via grep output. Everything else is UNVERIFIED (taken from reports).
- Not examined by any of the source reports: `models.py` triggers/migrations, beat schedule, `services.py` ordering, frontend implementation, `will_resolve_to_category` writer, `incomplete_sync_remote_pages`, the PUT of `PROCESSING_PAGE_DOMAINS` constant values (taken via grep by report 08).
