# X5 - End-to-end trace of one book (parent read the code itself)

Status: DRAFT (in progress; stages are appended as they are traced)

Method: the parent followed one book from the operator's click to the reader, reading the code directly. Root: `archive/app/backend/apps`. Every statement cites file:line or says NOT TRACED.

Path traced: operator selects a catalog record -> request -> job engine -> worker -> scrape -> build -> persist -> catalog -> reader.

## Stage 1 - Operator creates a request (HTTP)

1. `POST /api/processing/records/create-requests/` with `{ids:[...]}`; permission `CanManageProcessing` (`processing/view_modules/sync_action_and_automation_views.py:63-79`).
2. `create_requests_for_record_ids` loops the records sorted by name; skips any record where `record_is_selectable` is false (`processing/service_modules/automation_commands.py:34-42`).
3. `record_is_selectable` (`processing/service_modules/request_queue_runtime.py:19-39`): the URL must pass `can_process_record_url`; a confirmed DUPLICATE request is selectable only if its original request is FAILED/DELETED; a record that has a `linked_book` and no requests is NOT selectable; otherwise selectable unless an existing request blocks it.
4. `create_request_for_record` (`automation_commands.py:2-31`): creates `BookCreationRequest(id=next_request_id(request_id_for_record(record)), book_record, state=INITIAL, origin)`, calls `sync_record_state(record)`, publishes UI-domain version updates, then `queue_processing_request`.
5. `queue_processing_request` (`request_queue_runtime.py:~83-95`): if the URL is not a source-site book URL the request fails at once; if `should_enqueue_processing_work()` (true unless inline mode/tests) it calls `enqueue_request_processing`; **if that returns false it runs `kickoff_request_processing` inline inside the HTTP request**; in inline mode it also runs inline.

Observation O1: a request id is not a UUID (built from the record id, e.g. test-record-1 style). The engine knows this and skips DB bookkeeping for non-UUID ids (`ingestion/engine/engine.py:~254-265, 270-285`).

## Stage 2 - Request is queued to the job engine

1. `enqueue_request_processing` (`request_queue_runtime.py:42-72`): moves INITIAL->QUEUED with a guarded transition; returns false if already dispatch-pending; calls `dispatch_job(job_id=request.id, job_type="pipeline", handler="pipeline")`; on exception logs a warning and returns false (-> the inline fallback above); on success stores `PROCESSING_DISPATCH_REQUESTED_AT_KEY` in `progress`.
2. `dispatch_job` (`ingestion/engine/dispatch.py:14-35`): opens a Redis connection per call; `HSET engine:job:handlers <id> <handler>`, `RPUSH engine:queue:pending <id>`, `PUBLISH CH_JOB_REQUEST {...}`. No database write; the Redis queue is the only record that the job was handed over.
3. Engine (`ingestion/engine/engine.py`, a separate process, single-threaded): on a job-request message it stores the handler and calls `_dispatch_pending_jobs` (`engine.py:~195-199`).
4. `_dispatch_pending_jobs` (`engine.py:~214-250`): peeks the head of the pending list with `LINDEX`; if no idle worker has the capability matching the handler it stops (a head-of-line block: one job needing an unavailable capability blocks every job behind it); otherwise `LPOP`, `assign_job`, publishes `CH_JOB_ASSIGNED {job_id, worker_hostname, handler}`. The peek/find/pop steps are not one atomic operation, which is safe only because the engine is a single process.
5. `_update_db_job_assignment` updates `ProcessingJob.worker_hostname` only when the id is a UUID (`engine.py:~257-268`); for a pipeline request it does nothing.

## Stage 3 - A Celery worker process runs the job

1. Each Celery worker process starts a listener thread subscribed to `CH_JOB_ASSIGNED` via Redis pub/sub (`ingestion/signals.py:122-182`). It ignores messages whose `worker_hostname` is not its own.
2. For handler `"pipeline"` it calls `apps.processing.services.kickoff_request_processing(job_id)` directly in that thread (`signals.py:~146-149`); for `"process_submission"` it calls `process_submission_job`. Any other handler only logs a warning, **and still publishes `succeeded`** (the publish sits after the if/elif chain, `signals.py:~151-157`).
3. After the call returns, the thread publishes `CH_WORKER_DONE` with status `succeeded` even if the request ended in state FAILED, because `kickoff_request_processing` returns the request instead of raising (`processing/service_modules/request_processing_pipeline.py:449-466`). Status `failed` is published only if an exception escapes.
4. Pub/sub is fire-and-forget: if the assigned worker is not subscribed at that moment, the assignment is lost; recovery relies on `stale_detector.py` / `recovery.py` (NOT TRACED here).
5. Separately, Celery's own `task_prerun`/`task_postrun` signals publish heartbeat/done events for ANY task whose first positional argument is truthy (`signals.py:229-264`). The processing tasks pass the request id first (`processing/tasks.py: kickoff_book_creation_request_task(self, request_id)`), so a request run through the Celery task path produces a second "done" event for the same id (see X4: X1-065).
6. Two ways to run the same request therefore exist: the engine assignment above, and the Celery task `kickoff_book_creation_request_task` (`processing/tasks.py:25-41`). Which one is used in production depends on settings (`should_enqueue_processing_work`, inline flags). NOT TRACED: which one actually fires in the deployed configuration.

(Stages 4+ are appended below as they are traced.)

## Stage 4 - The request pipeline (`kickoff_request_processing` -> `_run_processing_request`)

All in `processing/service_modules/request_processing_pipeline.py` (read in full, lines 1-466).

1. `kickoff_request_processing` (449-466): INITIAL->QUEUED->PROCESSING with guarded transitions (`_transition_request_state`, 413-448: `select_for_update`, no-op if the state moved). If the state is PROCESSING it runs `_run_processing_request`.
2. `_run_processing_request` (369-410): loop of `MAX_PROCESSING_REQUEST_ATTEMPTS` calls to `_process_request_once`. **Retry policy is decided by error text:** any `ValueError` whose message contains "source site" stops retrying; a `ValueError` starting with "Incomplete scrape:" sleeps 60 s (inside the worker thread) and retries; every other exception retries immediately. After the loop the request is FAILED with `str(last_error)`.
3. `_process_request_once` (176-320), step by step:
   1. Stop if the request is terminal or PAUSED.
   2. `capture_source_page_metadata(url)` (`processing/source.py:41`): fetches the source page metadata, upserts a `SourceCatalogEntry`, updates the record's fields. Failures are swallowed (`return None`).
   3. Re-load the request; if DELETED return; if PAUSED save checkpoint `PROCESSING_SOURCE_METADATA_CHECKPOINT` and return. **Pause/stop is cooperative: it is noticed only at these re-load points** (after metadata, after the scrape, before persisting), not during the multi-minute scrape.
   4. Unless `is_confirmed_not_duplicate`: `find_existing_book_by_source_url`; if it exists and is not this request's own book, try `_claim_unlinked_source_book` (adopt the book if no other record/request links it), else mark the request DUPLICATE.
   5. Resume: `_saved_curated_result_for_resume` / `_saved_scraped_data_for_resume` use the stored `progress` checkpoint only when `is_resumed` and the checkpoint equals `PROCESSING_SCRAPED_CONTENT_CHECKPOINT`.
   6. Scrape: if `processing.source.scrape_book` has been monkey-patched (module name check `legacy_scrape_overridden`, a test seam in production code) it uses the legacy payload route; otherwise `curate_book(url, page_cache=DiskPageCache(...))` runs while a daemon thread touches `updated_at` every `PROCESSING_SCRAPE_HEARTBEAT_INTERVAL` seconds so the maintenance task does not mark the running scrape stale (lines 1-24, 226-240).
   7. Normalise the projection (fallback title/author/type from the catalog record if the scrape found none).
   8. `_apply_multi_page_toc_signal` (127-173): stores `has_multi_page_toc`, `source_toc_page_count`, `fetched_toc_page_count`; raises if the TOC is incomplete (error text deliberately contains "source site" to stop retries) or content is incomplete (text starts "Incomplete scrape:" so retries continue).
   9. Re-check PAUSED -> save checkpoint with the full `scrapedData` and `curatedResult` inside the request's JSON `progress`. **A whole scraped book is stored as JSON in a database column for resume.**
   10. Duplicate check on scraped data: exact title match (`find_exact_existing_book`), then metadata similarity (`detect_metadata_duplicate`, which uses `texts_are_similar`); DUPLICATE if found and it is not the request's own book.
   11. If curated status is INVALID and no title: raise "Curated document requires review...".
   12. `_persist_processing_book(...)` writes the Book (Stage 6), then: if the curated status is not VALIDATED and not `force_generate` the request becomes **FAILED with the message "Curated document requires review before asset generation." while keeping `linked_book` set** (`_mark_request_review_required`, 345-366). "Needs review" is represented as FAILED, not as a distinct state. Otherwise `_finalize_processing_request` (Stage 7).

## Stage 5 - How the scrape works (`ingestion/pipeline/book_manifest.py`, key parts read)

Source site type: a WordPress/LearnDash course site (the code uses LearnDash AJAX TOC paging, lesson/topic pages, WP REST fallback).

1. Entry `curate_book` (`processing/source.py:118`) -> `curate_book_document` (`ingestion/pipeline/curated_pipeline.py:218`) -> `fetch_source_pages` -> `build_manifest_source_pages` (`book_manifest.py:2186-2257`).
2. Limits: curate path uses `processing_curate_limits` (`source.py:~65-85`): `max_nodes` unlimited by default, depth 6, 20 lesson pages, 60,000 chars per item; the older scrape path uses 48 nodes, depth 3, 2 pages, 12,000 chars (`source.py:~46-62`). Both are configured through settings, not data.
3. Authentication: `SourceFetchContext.__init__` calls `login_source_session(session)` (`book_manifest.py:155-161`; `scraper_support/network.py:137-...`). It loads the `wordpress_logged_in_*` cookie from a state file at `SOURCE_SITE_AUTH_STATE_PATH`, generated once by a local script that reads the cookie out of a developer's logged-in browser, because the source site's bot protection blocks automated logins; the file lives in shared storage mounted into every container. `SOURCE_SITE_EMAIL`/`PASSWORD` settings exist in config but this function does not use them. This resolves X1 conflict #3: the real mechanism is the **manually harvested cookie file**; an expired cookie makes paginated TOCs come back incomplete (and then the request fails with the "sign in required" message).
4. Fetching (`book_manifest.py:155-240`): one `requests` session, **strictly sequential**, 0.5 s sleep after each successful page, 60 s timeout, up to 4 attempts per URL with 2 s x attempt backoff on 429/500/502/503/504 and network errors, host fallback via `get_with_host_fallback`; failed pages are recorded with status and error in `pages`.
5. Landing page -> title/author, taxonomy terms (authors, series, category), cover (downloaded into a per-book output folder created by `scraper.create_output_folder(title)`), main content, then `collect_learndash_toc` (paged AJAX), then `collect_content_items` (1465-1526) which walks every TOC node: items found in the on-disk `DiskPageCache` are reused (resume), others fetched by `fetch_content_item`; reachable-but-empty pages become placeholders that stay in the TOC and spine; failures set `has_content=False` and are skipped.
6. `normalize_body_sections` (front matter promotion, title-page duplicate removal, inline-TOC dropping, 1947-2124), `classify_manifest_structure` (1561), `projection_from_manifest_parts` (2125), `build_manifest_from_projection` (2156). The result is a `manifest` plus a `raw_scrape_payload` (the "projection") and, via `build_curated_document` (`curated_pipeline.py:92`), a curated document with a validation status.
7. Timing consequence: a 900-topic book needs at least 900 x (fetch time + 0.5 s) sequentially, so tens of minutes in one worker thread; the 20-minute stale rule is survivable only because the heartbeat thread keeps `updated_at` fresh.
8. Known defect on this path (already VERIFIED in X4/D1): `_submit_mark_complete` (`book_manifest.py:1230`, called from the fetch path ~1416-1453) POSTs the source site's "mark complete" form for lessons, changing the logged-in account's progress on the source site.

(Stages 6+ appended below as traced: persist, build assets, finalize, catalog, reader.)

## Stage 6 - Persisting the book (`_persist_processing_book`, `persist_curated_book_with_hooks`)

Read: `processing/service_modules/request_processing_persistence.py:1-303`, `ingestion/pipeline/curated_persistence.py:170-411`, `ingestion/services/submissions_support/assets.py:1-135`.

1. `_persist_processing_book` (persistence.py:~199-250): picks `target_book` = the request's linked book if not soft-deleted; calls `persist_curated_book`; if the curated status is not VALIDATED and the request is not force-generated it **returns the Book without generating any file**; otherwise it builds the export payload, calls `generate_exports` (writes the HTML and EPUB files into a per-book output folder on disk: `processing/source.py: generate_exports -> html_book.create_html_book, epub_book.create_epub`) and then `sync_assets`.
2. `persist_curated_book_with_hooks` (curated_persistence.py:264-411):
   - Builds lifecycle state: VALIDATED -> `READY` + review `PENDING`; anything else -> `NEEDS_REVIEW` + `NEEDS_REVIEW`.
   - Matches an existing book: `target_book`, else `find_deleted_book_by_title`, else `find_existing_matching_book`. **It then overwrites that book's fields, sets `deleted_at = None` (revives a soft-deleted book) and resets `review_state` to PENDING.** (`apply_fields`, ~297-318.) This confirms the "title-match revival" claim (X1-029) and means regenerating an approved book silently removes its approval.
   - Stores **the entire scraped content on the Book row** as JSON/text columns: `main_content_html`, `book_info_html`, `dedication_html`, `toc`, `content_items`, `raw_scrape_payload` (slimmed), `raw_scraped_metadata`.
   - New book is created inside `transaction.atomic()`; on `IntegrityError` it re-looks-up an existing book by source URL or title (race tolerance).
   - Then separately (no surrounding transaction): `replace_book_relations` (contributors, series, categories), `BookSource.update_or_create`, `persist_curated_document`, a second `book.save`, optional `BookGroup` link from a hint in `job.submission.raw_payload` ("new_edition" flow), and `MetadataVersion.create(snapshot=curated_document.document)`.
3. `persist_curated_document` (curated_persistence.py:170-252): allocates a document version with up to 5 retries on `IntegrityError`; only the `CuratedBookDocument.create` is inside `transaction.atomic()`. The `CuratedEntity`, `CuratedSection` and `CuratedEvidence` rows (potentially thousands per book) are created one `.create()` call at a time **outside** any transaction. A crash midway leaves a document with partial children.
4. Net effect: the same book content lives in at least four places: Book JSON columns, `CuratedBookDocument.document` + `CuratedSection.html` rows, a `MetadataVersion.snapshot`, and the generated EPUB/HTML files. Which one is authoritative is not defined anywhere in the code.
5. `sync_assets` (assets.py:103-135): for each expected asset type (EPUB, HTML, COVER): `GeneratedAsset.get_or_create(book, asset_type)`; if the file is missing the asset is marked FAILED and skipped; otherwise it records size, content type and SHA-256, deletes the previous file, and saves the file into storage under `generated/<book.slug>/<file name>` (`catalog/models/utils.py:18-19`). The EPUB file name is the book title plus `.epub` (`assets.py:54-62`, `safe_epub_filename`), so **the public path of a book's file is predictable from its slug and title**, both visible in the catalog. Combined with the unauthenticated `/media/` alias (X4: X1-011), a book can be fetched without a login unless the deployment blocks it elsewhere. If a required asset is missing the book is set `NEEDS_REVIEW` and a `ValueError` is raised. The staging files in the output folder are deleted afterwards (`cleanup_staged_asset_files`).
6. Failure windows: files are written to disk before the DB rows that describe them, and old files are deleted before new ones are saved (`asset.file.delete` then `asset.file.save`); a failure between those two steps loses the previous EPUB.

## Stage 7 - Finalising the request (`_finalize_processing_request`, persistence.py:~253-303)

1. Re-load the request. If it was DELETED during the run: **the book is soft-deleted if not already** (`book.soft_delete()`), even when the book existed before this run (it can be a previously created book that was being regenerated). This confirms X1-033.
2. If PAUSED during the run: save checkpoint `PROCESSING_SCRAPED_CONTENT_CHECKPOINT` with `scrapedData` and `linkedBookId`; the build already happened.
3. Otherwise: state CREATED, `linked_book = book`, clear error/progress/force flag; update the catalog record's `linked_book`, clear its duplicate flags; `sync_record_state(record)`; publish UI-domain version updates; delete the disk scrape cache (failure ignored).

## Stage 8 - Result visible to readers (catalog side)

1. The new Book is `READY` with review state `PENDING` (or `NEEDS_REVIEW`). Catalog list/detail views filter only on `deleted_at` (X4/D4 verified), so **the book is visible to every logged-in user the moment it is saved, before any review**.
2. Review is a separate flow (`MetadataReview`, duplicate reviews) that changes `review_state`; it does not gate visibility.

(Stages 9+ appended below: EPUB build internals, reader launch and delivery.)

## Stage 9 - Building the EPUB (`ingestion/pipeline/epub_book.py`, read lines 1-120 and 195-304; builder internals NOT read)

1. `create_epub(book_data)` converts a curated document to a legacy payload, creates an `EpubBuilder`, adds in order: cover (real image if found, else a generated dark HTML cover), title page, info page, optional dedication page, front-section pages, table-of-contents page (hierarchical if the curated document supplies a TOC, else flat from content items), optional single-flow main content, lesson pages, back sections, then `build_epub("<book title>.epub", toc_structure=toc)`.
2. Many structural repair heuristics sit in this function (virtual-chapter promotion, "mis-classification rescue" that promotes front sections to chapters when there are 0 or 1 content items and 3+ front sections). The builder is therefore also a second place that decides what the book's structure is, after the curation step.
3. Quality gate (lines ~268-282): the build raises `ValueError("Too many empty chapters ...")` when more than one third of chapters are empty-source placeholders. The 95% test is redundant (X4/D1 verified).
4. **Ordering defect (read from the code order in `_persist_processing_book`):** the Book row is written first (`persist_curated_book`), and the EPUB is built after. If the gate raises, the retry loop re-scrapes the whole book again (the message does not contain "source site"), and after the last attempt the request is FAILED, **but the Book stays saved as `READY` with no EPUB/HTML assets** and is visible in the catalog. A reader can open its detail page; the reader launch then fails with "EPUB asset is unavailable" (`access/views/reader.py: ReaderManifestView`).
5. Builder internals (`epub_properties/epub_builder.py`, page templates, fonts, `labels.py`; about 1,100 lines) were not read in this trace; their behaviour is known only from the digests (D1).

## Stage 10 - Reading (access service) - read: `access/views/reader.py` in full, `access/views/shared.py:225-262`, `access/urls.py:35-43`, vendored epub.js `determineType`, `startup-session-methods.js:120-200`, `book-initialization-methods.js:56-86`

1. Launch: `POST /api/access/books/<slug>/reader-launch/` (`ReaderLaunchView`, `IsAuthenticated`). `get_object_or_404(Book, slug=slug)` with **no `deleted_at`, state or review check**. Non-superuser, non-owner users first pass the Read-Once check (`user_has_read_once_limit`) then `user_can_launch_reader`; an already active preview session also lets the user through. For Read-Once-only users a `BookOpeningRecord` is created at launch (not at content delivery). A `PreviewAccessSession` is created or reused, `launch_count` incremented, and `expires_at` reset to the default expiry (2 h per D6) on every launch.
2. The response carries `launch_url = FRONTEND_BASE_URL/reader?manifest=<manifest URL with the token>`; the token is therefore in a URL (browser history, logs, referrers).
3. Frontend: the React route mounts the vendored reader; `loadManifestLaunchIfPresent` fetches the manifest with `credentials: "include"`, then calls `initializeBook(manifest.epub_download_url, {initialLocation: reading_session.last_location})` which calls `window.ePub(url, {requestCredentials: true})`.
4. Manifest (`ReaderManifestView`, `AllowAny`, token only): looks up the EPUB (and HTML) asset, creates or fetches the `ReadingSession`, returns the book title/slug, the EPUB URL, HTML preview URL, session/bookmark/highlight URLs, and the user's saved bookmarks and highlights; `no-store` headers.
5. **Delivery mode (resolves D6's open question):** `epub_download_url` is `/api/access/reader/<token>/epub/` (no file extension). The vendored epub.js `determineType` (`public/epub-reader/static/js/vendor/epub-runtime/modules/rendering-engine.modules.js:5035-5050`) returns "directory" when the URL has no extension, so the reader treats it as an **unpacked EPUB and requests each file individually** (`container.xml`, the OPF, every XHTML chapter, image, font) through `reader/<token>/epub/<path>`. The server route `ReaderEpubDownloadView.get` with `asset_path` opens the stored EPUB as a ZIP for every such request (`read_asset_bytes` then `zipfile.ZipFile`, `access/views/reader.py:140-165`); for non-local storage that means loading the whole file into memory for each request. A 900-chapter book generates thousands of requests, each a token lookup plus a ZIP open.
6. The whole-file route (no `asset_path`) streams the EPUB with `as_attachment=False`, so the full book can also be downloaded by anyone holding the token, with no Download grant check. Read-only versus download protection is therefore not enforceable (confirms X1 conflict #6).
7. Progress/notes: the session, bookmark and highlight token routes require a logged-in user whose id matches the session's user (`access/views/shared.py:52-59`). A bookmark delete route exists on the server (`urls.py:41`), although the digests reported the reader UI as create-only.
8. Path handling: `normalize_epub_asset_path` rejects `..` segments and leading slashes (`reader.py:~143-148`); entries are read from the ZIP by name, so no filesystem traversal.

## Findings that change or add to the register

| # | Finding | Evidence | Effect on design |
|---|---|---|---|
| T-01 | Request id is also the engine job id; the engine special-cases non-UUID ids | `engine.py:~257-285`, `request_queue_runtime.py:57-62` | One job concept, two id formats; rebuild uses one job model |
| T-02 | Dispatch failure runs the whole pipeline inline inside the HTTP request | `request_queue_runtime.py:~83-90` (fallback after `enqueue_request_processing` returns false) | Operator HTTP call can block for minutes; the rebuild must never run jobs in request handlers |
| T-03 | Worker publishes `succeeded` even if the request ended FAILED, and for unknown handlers | `signals.py:~140-157`; `request_processing_pipeline.py:449-466` | The engine's completion signal carries no real outcome |
| T-04 | Retry policy decided by substring of the error message | `request_processing_pipeline.py:~385-405` | Use typed errors with retryable/permanent classes |
| T-05 | Pause/stop is cooperative, checked only between big steps | `request_processing_pipeline.py:~196-225, 297-312` | Cancel cannot interrupt a long scrape; use a cancel flag checked per page |
| T-06 | A whole scraped book is stored as JSON inside the request's `progress` column to resume after a pause | `request_processing_persistence.py:~86-92`, pipeline `~268-275` | Store scrape cache as files/blobs, not in a request row |
| T-07 | Book saved READY/PENDING before the EPUB is built; an empty-chapter gate failure leaves a visible book with no files | `request_processing_persistence.py:~199-250`, `epub_book.py:~268-282` | Publish only after assets exist; separate "draft" from "published" |
| T-08 | Regeneration revives a deleted book and resets review to PENDING | `curated_persistence.py:~297-318` | Explicit versions and review state per version |
| T-09 | Four copies of the book content (Book JSON, curated document rows, MetadataVersion snapshot, files) | `curated_persistence.py:170-411` | One authoritative store for source content; derived artifacts regenerated |
| T-10 | Entity/section/evidence rows are inserted one by one, outside a transaction | `curated_persistence.py:~214-250` | Bulk insert in one transaction, or store the document as one blob |
| T-11 | The reader loads the EPUB as a directory: one HTTP request and ZIP open per file | `rendering-engine.modules.js:5035-5050`, `reader.py:~140-165` | Decide the reader delivery model deliberately (feeds Q-R1) |
| T-12 | Source authentication is a manually harvested browser cookie in a shared file | `scraper_support/network.py:137-...` | Needs an explicit, rotatable credential flow and a visible "cookie expired" state |
| T-13 | Reader launch has no deleted/state/review check | `reader.py: ReaderLaunchView.post` | Entitlement check must include publication state |

## Not traced (still unknown after this pass)

- The inside of `EpubBuilder` and its page templates (about 1,100 lines).
- `normalize_scraped_book`, `find_existing_matching_book`, `detect_metadata_duplicate` and `texts_are_similar` (title matching and duplicate rules).
- `sync_record_state` and the UI "projection" tables/triggers that keep the console in sync.
- The catalog sync phases (the other pipeline) and the incomplete-books flow.
- The `process_submission_job` path (the older ingestion pipeline with submissions, used by user submissions) - only its dispatch was seen.
- Recovery after a lost pub/sub assignment (`engine/recovery.py`, `stale_detector.py`).
- Kindle sending and download views.
