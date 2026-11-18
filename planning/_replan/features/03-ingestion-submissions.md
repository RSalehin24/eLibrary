# Legacy ingestion/services: submissions (read-only analysis)

Status: DRAFT (research evidence; read-only record)

Root: archive/app/backend/apps/ingestion/services. Paths below are relative to it. "sm/" = submission_modules/, "ss/" = submissions_support/.

## 1. Coverage

| file | lines | fully read |
|---|---|---|
| __init__.py | 1 (empty) | yes |
| submissions.py | 18 | yes |
| submission_modules/job_lifecycle.py | 264 | yes |
| submission_modules/retry_and_deduplication.py | 250 | yes |
| submission_modules/resolution_and_queueing.py | 246 | yes |
| submission_modules/book_persistence.py | 179 | yes |
| submission_modules/processing_job_runner.py | 293 | yes |
| submissions_support/__init__.py | 1 (comment) | yes |
| submissions_support/assets.py | 141 | yes |
| submissions_support/detection.py | 334 | yes |
| submissions_support/persistence.py | 166 | yes |
| submissions_support/preview.py | 39 | yes |
| submissions_support/sync.py | 98 | yes |

13/13 fully read.

Architecture note: `submissions.py` is a facade that `exec()`s the five sm/ files in order (job_lifecycle, retry_and_deduplication, resolution_and_queueing, book_persistence, processing_job_runner) into one shared global namespace. sm/ files have no imports except job_lifecycle (which holds all imports, constants, and cross-module names). ss/ files are pure functions that receive collaborators as injected `*_fn` / `*_callback` args; sm/book_persistence and sm/retry_and_deduplication are thin wrappers that inject them.

Vocabulary: Submission = BookSubmission (user request: URL or title). Job = ProcessingJob. Canonical/dependent submission = dedup tree (`canonical_submission` FK, `deduplicated_submissions` reverse).

## 2. Feature / action inventory

### Submission creation
- [S1] Create submissions from parsed entries — `create_submission_records(submitter, parsed_entries, auto_process=True, origin=USER)`; entry = {kind: "url"|"title", value} — one BookSubmission per entry; input_type=kind; normalized_input=normalize_text(value); initial status PENDING_RESOLUTION if title else QUEUED; raw_payload={"submitted_publicly": submitter is None} (anonymous/public submissions allowed) — state: BookSubmission row — side effects: AuditLog verb `submission.created` payload {input_type} actor=submitter — failure: ValueError in URL branch only (see S2) — sm/book_persistence.py:3-25
- [S2] URL entry flow — kind=="url": (1) `validate_source_url(value)` -> resolved_url; (2) `find_reusable_submission(resolved_url)`; if hit -> `sync_submission_from_canonical`, append, continue; (3) `capture_source_page_metadata` (network fetch; result stored in raw_payload.source_page_metadata); (4) `find_existing_book_by_source_url`; if hit -> `fulfill_submission_with_existing_book(source="source_url", confidence=1.0)`; (5) else resolution_status=RESOLVED, resolution_confidence=1.0, status=QUEUED, save — failure: ValueError from validate_source_url (or anything raising ValueError in the try) -> resolution_status=INVALID, status=NEEDS_REVIEW, review_state=NEEDS_REVIEW, error_message=str(exc) — sm/book_persistence.py:27-63
- [S3] Title entry flow — (1) `find_reusable_submission(normalized_input)`; hit -> sync from canonical; (2) `resolve_submission(submission)` (title resolver, see S9); (3) if resolved_url: reusable check by resolved_url, then `find_existing_book_by_source_url` -> fulfill with source="resolved_source_url" carrying resolution_status/confidence — sm/book_persistence.py:64-95
- [S4] Auto-queue — after branches, if `auto_process and resolved_url and status==QUEUED` -> `queue_submission(submission, actor=submitter)` then refresh_from_db — sm/book_persistence.py:97-99
- [S5] Legacy config import — `legacy_config_entries_as_submission_inputs()` -> `[{kind:"url", value:url, label:name}]` from `load_legacy_config_entries()` — sm/processing_job_runner.py:292-293
- [S6] Reprocess request — `queue_reprocess_book(book, actor, origin=USER)`: if any active job (QUEUED/PROCESSING) on book returns (job, False). Else builds new BookSubmission (input_type URL, resolved_url = normalize_source_url(primary source url of book), resolution RESOLVED conf 1.0, status QUEUED, review_state=book.review_state, linked_book=book, raw_payload {submitted_publicly False, reprocess_book_id}); submitter=actor only if `actor.is_authenticated`; ProcessingJob(job_type=REPROCESS, book=book, payload {resolved_url, actor_id, reprocess_book_id, previous_book_state=book.state}); book.state=PROCESSING; dispatch. Returns (job, True) — sm/resolution_and_queueing.py:207-246. No AuditLog write. Empty primary URL possible (primary_source_url_for_book returns "").

### Reuse / dedup of submissions (request level)
- [D1] Reusable submission lookup — `find_reusable_submission(normalized_input="", resolved_url="", exclude_submission_id)`: candidates = canonical_submission IS NULL, status in REUSABLE_SUBMISSION_STATUSES (PENDING_RESOLUTION, QUEUED, PROCESSING, READY), linked_book and duplicate_of_book either null or not soft-deleted; exclude self. Match order: resolved_url first (newest by created_at), then normalized_input (newest). Not scoped by submitter — any user's submission is reused — sm/retry_and_deduplication.py:3-28
- [D2] Sync dependent from canonical — copies resolved_url, resolution_status, resolution_confidence, status, review_state, linked_book, duplicate_of_book, error_message; sets canonical_submission FK; raw_payload gets deduplicated=True, canonical_submission_id, plus shared keys (served_from_database, existing_book_source, linked_book_slug, source_page_metadata, normalized_url, scraped_preview) if present on canonical. If dependent is READY with linked_book and submitter -> ensure_preview_session. No-op if same pk. Takes root of canonical first — ss/sync.py:24-84, wrapper sm/retry_and_deduplication.py:234-242, keys const sm/job_lifecycle.py:110-117
- [D3] Fan-out sync — `sync_deduplicated_submissions(submission)`: root, then sync every dependent (select_related submitter, linked_book). Called after nearly every status change on a root — ss/sync.py:87-98
- [D4] Root resolution — `root_submission(s)` = s.canonical_submission or s (single level, no chain walk) — ss/sync.py:6-7

### Resolution
- [R1] Title resolution — `resolve_submission(submission, force_refresh=False)`: `TitleResolver().resolve(original_input, refresh_catalog=force_refresh)`; writes TitleResolutionAttempt(query, normalized_query, status, confidence, resolved_url, raw_results) and one MatchCandidate per candidate (rank from 1, title, author, url, confidence, metadata). Result status "exact_match" -> resolved_url, resolution_status EXACT_MATCH, confidence, status QUEUED; "ambiguous" -> AMBIGUOUS, confidence, status NEEDS_REVIEW, review_state NEEDS_REVIEW; anything else -> UNRESOLVED, status NEEDS_REVIEW, review_state NEEDS_REVIEW, error_message "No confident catalog match was found." (confidence not updated). Then sync dependents — sm/resolution_and_queueing.py:85-127. No threshold is in this file (thresholds live in TitleResolver, other agent).
- [R2] Local resolution attempt record — `create_local_resolution_attempt(submission, book, confidence=1.0)` writes TitleResolutionAttempt source "local_database". Never called in the assigned files (dead; see section 5) — resolution_and_queueing.py:31-44
- [R3] Fulfill from existing book — `fulfill_submission_with_existing_book(submission, book, source, confidence=1.0, resolution_status=RESOLVED, resolved_url="")`: resolved_url defaults to primary source URL of book; sets linked_book, resolution fields, status READY, review_state=book.review_state, clears error_message, raw_payload served_from_database=True, existing_book_source=source, linked_book_slug; syncs dependents; `ensure_preview_session(submitter, book, submission)`; AuditLog `submission.fulfilled_from_database` payload {book_id, source}. Sources used: source_url, resolved_source_url, processing_source_url, processing_title_match — sm/resolution_and_queueing.py:47-82
- [R4] Source page metadata capture — `capture_source_page_metadata(url)`: `fetch_source_page_metadata`, any exception swallowed -> None; on success `upsert_source_catalog_entry(metadata)` side effect; returns metadata (uses `["raw_data"]`) — sm/retry_and_deduplication.py:147-154

### Job lifecycle
- [J1] Queue — `queue_submission(submission, actor)`: use root; if an active job (QUEUED/PROCESSING) exists return it; else create ProcessingJob(job_type INGESTION, status QUEUED, payload {resolved_url, actor_id}); submission.status=QUEUED; sync dependents; `dispatch_processing_job(job)` — sm/resolution_and_queueing.py:130-150
- [J2] Dispatch — `dispatch_processing_job(job, force=False, attempt_offset=None)`: refresh; return if CANCELLED or cancel_requested; if not force and status QUEUED and task_id set -> return (already dispatched). attempt_offset = max(job.retry_count, attempt_offset). Assigns task_id=uuid4 string and queue_name="engine"; calls `apps.ingestion.engine.dispatch.dispatch_job(job_id, job_type, handler="process_submission", attempt_offset)`. On ANY exception: task_id="", queue_name="inline-fallback", last_error="Engine dispatch failed: ...", warning log, then runs `process_submission_job` inline in-process looping attempts from job.retry_count up to MAX_PROCESSING_JOB_ATTEMPTS(3), swallowing exceptions except the last, re-raising last_error if all fail — sm/resolution_and_queueing.py:153-204
- [J3] Process job (main pipeline) — `process_submission_job(job_id, retry_count=0, task_id="")`. Steps:
  1. Load job (+submission, submitter, book). Return unchanged if SUCCEEDED or CANCELLED; if cancel_requested -> finalize_cancelled_job.
  2. job.status=PROCESSING, retry_count, task_id (keeps old if empty), started_at=now; submission.status=PROCESSING; sync dependents; job log info "Started processing submission."
  3. Cancel checks (via `cancel_requested_for_job`, which refreshes status/cancel_requested from DB) are inserted at 5 points: start of try, after reprocess-state flip, before duplicate-by-URL check done, after scrape/curation (before title dup), and (see below) before persistence is NOT checked. Each -> finalize_cancelled_job.
  4. If no resolved_url and input_type=="title": resolve_submission(force_refresh=True); if still no resolved_url: job marked SUCCEEDED (finished_at) with warning log "Submission requires review before processing can continue." (submission stays NEEDS_REVIEW from resolver) and return.
  5. normalized_url = normalize_source_url(resolved_url). If REPROCESS: target book id = payload.reprocess_book_id or job.book_id or submission.linked_book_id; Book must exist and deleted_at is null else ValueError "The target book for regeneration is unavailable."; set book.state=PROCESSING if not already.
  6. capture_source_page_metadata(normalized_url) -> raw_payload.source_page_metadata.
  7. Exact source URL dedup (skipped if reprocess or submission.raw_payload.skip_duplicate_checks): see X1.
  8. Scrape+curate: see X2.
  9. Exact normalized-title dedup (skipped likewise): X3.
  10. Metadata similarity dedup (skipped likewise): X4.
  11. Invalid curated doc with no title: X5.
  12. Persist book: `persist_curated_book` (P2). If not legacy path and curated status != VALIDATED: X6 (needs review, no assets).
  13. Export + assets: `export_payload_from_book`, `generate_exports(curated_document_with_projection(document, export_payload))`, `sync_assets` (A1), job log, `complete_processed_submission` (P3, source "reprocess" or "scrape"), job.book=book, job SUCCEEDED, finished_at, final log "Submission finished successfully." with {book_id, job_type}.
  — sm/processing_job_runner.py:3-246
- [J4] Failure/retry in runner — any Exception: log exception; next_retry_count=retry_count+1; if next_retry_count < 3 -> `requeue_processing_job(..., preserve_dispatch_state=bool(task_id or job.task_id))` and RE-RAISE (so the engine/celery retries); else terminal failure: submission FAILED with error_message=str(exc), sync dependents; if reprocess_book -> restore book.state from payload.previous_book_state (if set); job FAILED, task_id/queue_name cleared, last_error, finished_at; error job log {error}; re-raise — sm/processing_job_runner.py:247-289. So max 3 attempts total (retry_count 0,1,2).
- [J5] Cancel — `cancel_processing_job(job, message="Stopped by user.")`: reload; if SUCCEEDED/FAILED/CANCELLED return unchanged; set cancel_requested=True; if QUEUED/PROCESSING: `revoke_processing_task(task_id, terminate = (status==PROCESSING))` then `finalize_cancelled_job`; else (not reachable given statuses) log "Stop requested." — sm/job_lifecycle.py:193-204
- [J6] Finalize cancelled — submission.status=CANCELLED, error_message=message; sync dependents; for REPROCESS jobs restore book.state=payload.previous_book_state when the book resolves and previous state exists; job CANCELLED, cancel_requested False, last_error=message, finished_at; warning log — sm/job_lifecycle.py:170-190
- [J7] Resume — `resume_processing_job(job)`: only QUEUED or CANCELLED allowed else ValueError "Only queued or stopped jobs can be resumed." CANCELLED -> reset to QUEUED (clear cancel_requested, task_id, queue_name, last_error, started_at, finished_at; NOT retry_count); a CANCELLED submission is set back to QUEUED with error cleared and dependents synced. If job.cancel_requested still true -> ValueError "This job has a pending stop request." Then `dispatch_processing_job(force=True)` — sm/job_lifecycle.py:207-239. Note: the book state is NOT re-set to PROCESSING for reprocess resume (done in runner step 5).
- [J8] Revoke task — `revoke_processing_task(task_id, terminate=False)`: celery `current_app.control.revoke`, exceptions swallowed with warning — sm/job_lifecycle.py:154-160
- [J9] Cancel-check helper — `cancel_requested_for_job(job)` refreshes (status, cancel_requested, updated_at) and returns status==CANCELLED or cancel_requested — sm/book_persistence.py:177-179
- [J10] Job log — `record_job_log(job, level, message, details)` writes ProcessingLog; levels used: info, warning, error — sm/job_lifecycle.py:145-151
- [J11] Requeue — `requeue_processing_job(job, retry_count, message, preserve_dispatch_state)`: submission QUEUED, error cleared, synced; job QUEUED, retry_count set, cancel_requested False, last_error=message, started_at/finished_at None; task_id/queue_name cleared unless preserve; warning log {auto_requeued, retry_count, preserve_dispatch_state} — sm/retry_and_deduplication.py:40-84
- [J12] Fail job — `fail_processing_job(job, message)`: submission FAILED + error + sync; job FAILED, cancel_requested False, task_id/queue_name cleared, last_error, finished_at; error log {auto_failed: True} — sm/retry_and_deduplication.py:12-37. Does not restore reprocess book state (see bugs).

### Stale recovery
- [T1] `recover_stale_processing_jobs(origin="", limit=50, stale_after=20 min)`: only jobs with cancel_requested=False; optional filter by submission.origin. Picks (a) QUEUED jobs with empty/null task_id (never dispatched / lost), oldest first up to limit; (b) with remaining limit, PROCESSING jobs with started_at < now-20min, or started_at null and updated_at < now-20min. For each: if PROCESSING -> revoke task with terminate=True; next_retry = retry_count+1; if >= 3 -> `fail_processing_job(STALE_PROCESSING_FAILURE_MESSAGE)` (not counted in recovered); else `requeue_processing_job(STALE_PROCESSING_RETRY_MESSAGE)`. Then `dispatch_processing_job(force=True)`; recovered++. Returns count of redispatched jobs — sm/retry_and_deduplication.py:87-144

### Manual retry
- [Y1] `retry_submission_record(submission, actor)`: target=root. Permission: allowed if actor.is_staff or `can_manage_processing_records(actor)` (is_staff or scope PROCESSING_MANAGE) or `submission.submitter_id == actor.id` (checked on the passed submission, not root); else PermissionDenied "You cannot retry this submission." Requires resolved_url unless input_type=="title" else ValueError "This submission does not have a resolved URL yet." Cleans: nulls linked_book if soft-deleted; nulls duplicate_of_book if missing/soft-deleted; clears error_message; strips raw_payload keys requeued, requeued_at, requeue_requested_by, requeue_reason plus RETRY_PAYLOAD_RESET_KEYS (served_from_database, existing_book_source, linked_book_slug); review_state -> PENDING; status -> QUEUED unless already QUEUED/PROCESSING; sync dependents; then `queue_submission` (returns existing active job if any) — sm/retry_and_deduplication.py:157-203. build_retry_payload accepts actor/previous_status/previous_error_message but ignores them (ss/sync.py:10-21).
- [Y2] Bulk retry — `retry_submission_records(submissions, actor)`: dedupes by `canonical_submission_id or id`; ValueError -> skipped_invalid; returns {queued_count, skipped_invalid, skipped_duplicate_targets}. PermissionDenied is NOT caught (propagates and aborts batch) — sm/retry_and_deduplication.py:206-231

### Deletion
- [DEL1] Soft delete — `soft_delete_submission_record(submission, message="Deleted by user.")`: root; active jobs (QUEUED/PROCESSING); if any PROCESSING -> ValueError "Stop processing before deleting this request."; else cancel every QUEUED job (cancel_processing_job with message, which sets submission CANCELLED then below overwrites to DELETED); status=DELETED; error_message cleared; sync dependents — sm/job_lifecycle.py:242-264
- [DEL2] Delete dispatcher — `delete_submission_record(submission)`: root; if already DELETED -> `.delete()` hard delete (returns "hard_deleted"); else soft delete ("soft_deleted"). Two-step delete (soft then hard). Cascade behavior of hard delete depends on model FKs (not visible here) — sm/retry_and_deduplication.py:3-9

### Duplicate detection (book level)
- [X1] Exact source URL — `find_existing_book_by_source_url(normalized_url)` (catalog service, other agent). Hit: fulfill_submission_with_existing_book(source="processing_source_url", confidence 1.0); `DuplicateReview.get_or_create(submission, existing_book, defaults {detected_by "exact_source_url", status CONFIRMED, raw_evidence {resolved_url}})`; log "Submission matched an existing book by exact source URL."; job.book=dup, SUCCEEDED — processing_job_runner.py:57-80
- [X2] Scrape/curate — `legacy_scrape_overridden` = scrape_book or scrape_book_high_fidelity not defined in `apps.ingestion.services.legacy_adapter` (i.e. monkeypatched, test hook). If overridden: raw=(high-fidelity scrape if reprocess else scrape_book)(submission.resolved_url) then `curate_scraped_book_data(normalized_url, raw)`. Else `curate_book_document(normalized_url, content_limits=high_fidelity_scrape_limits() if reprocess else None)`. scraped_data=curated_result["projection"]; non-dict -> ValueError "Source curation returned no content for {url}. Verify the source URL is valid and publicly reachable." Log info with title/status/structure_type — processing_job_runner.py:84-113
- [X3] Exact normalized-title — `find_exact_existing_book(scraped)`: normalized title (normalize_catalog_text) must be non-empty; candidates Book with source_site==get_source_site_domain(), normalized_title equal, deleted_at null, newest first. Requires incoming authors AND categories non-empty (else None). A candidate matches when: existing has authors and categories; category sets intersect; if incoming series non-empty it must intersect existing series; if incoming translators non-empty they must intersect existing translators; and author sets intersect. First match returned. Hit -> fulfill (source "processing_title_match"), DuplicateReview get_or_create (detected_by "exact_normalized_title", CONFIRMED, evidence {book_title, resolved_url}), job.book=dup, job SUCCEEDED — detection.py:83-129, runner 116-142
- [X4] Metadata similarity — `detect_metadata_duplicate(scraped)`: requires title; iterates ALL non-deleted books (no source_site filter, no title index; full table scan with prefetch); `texts_are_similar(target_title, book.title)` (legacy_adapter, threshold not here); then same attribute rules as X3 but additionally requires both author sets and both category sets non-empty, category intersection, series intersection if incoming has series, translator intersection if incoming has translators, author intersection. First hit returned. Hit: submission.duplicate_of_book=book, status DUPLICATE, review_state NEEDS_REVIEW, raw_payload.scraped_preview {book_title, author}; sync dependents; DuplicateReview.create (detected_by "normalized_metadata", status PENDING, raw_evidence=scraped_preview); warning log; job.book=dup, job SUCCEEDED (job success though submission is DUPLICATE) — detection.py:42-80, runner 144-170
- [X5] Invalid curated doc, no title — if not legacy path and curated status == INVALID and no book_title: `persist_curated_document(curated_result, job)`; submission NEEDS_REVIEW, review_state NEEDS_REVIEW, error_message "Curated document requires review before a book can be created.", raw_payload curated_document_id + curated_validation; sync; job SUCCEEDED; warning log — runner 172-192
- [X6] Non-validated curated doc with title — after `persist_curated_book`: submission.linked_book=book, NEEDS_REVIEW, error "Curated document requires review before asset generation.", raw_payload normalized_url/linked_book_slug/curated_document_id/curated_validation; job.book=book, job SUCCEEDED; no assets generated — runner 200-222
- [X7] Classification (unused) — `classify_incoming_book(scraped, normalize_fn)` returns {verdict, matched_book, suggested_group, reason}: NEW_WORK (no title; no title match; authors differ), EXACT_DUPLICATE (all fields overlap or empty), NEW_EDITION (translator/publisher/edition differ on both non-empty sides; suggested_group=book.group or BookGroup by normalized_canonical_title), NEEDS_REVIEW (author info on only one side, evaluated after loop). Publisher from raw_strings.manual_publisher / publisher / manual_publisher; edition from scraped.edition / raw_strings.edition. Constants CLASSIFY_EXACT_DUPLICATE="exact_duplicate", NEW_EDITION="new_edition", NEW_WORK="new_work", NEEDS_REVIEW="needs_review" — detection.py:194-334. Not referenced by any assigned file.
- [X8] `find_existing_matching_book(title, normalized)` (unused here): same normalized title+source_site, authors required on incoming; skip candidate if different authors or if existing has none; skip if both translators present and disjoint — detection.py:132-191.

### Persistence of scraped books
- [P1] `persist_scraped_book(submission, job, scraped, target_book=None)` (legacy, non-curated; only reachable via facade, runner now calls persist_curated_book): normalize via normalize_scraped_book; clean dedication HTML; raw_scraped_metadata = normalized raw_strings + source_url. Existing = target_book or soft-deleted book matching title (`find_deleted_book_by_title`) -> revived: deleted_at=None, state READY, review_state PENDING, overwrite raw_scraped_metadata, raw_scrape_payload, main_content_html, book_info_html, dedication_html, toc, content_items, cover_source_url. Else Book.create (inside atomic); on IntegrityError (slug/unique source collision) falls back to `find_existing_book_by_source_url(normalized url)` and overwrites it (else re-raise). Then `replace_book_relations` (contributors, series, categories), `BookSource.update_or_create(normalized_source_url -> {book, source_url, source_title, raw_metadata})`, `MetadataVersion.create(snapshot=scraped, source="scrape")` — ss/persistence.py:56-133
- [P2] `persist_curated_book(submission, job, curated_result, target_book)` -> delegates to `curated_pipeline` hook `persist_curated_book_with_hooks(curated_result, source_url=submission.resolved_url, job, target_book, find_deleted_book_by_title_fn, find_existing_book_by_source_url_fn, replace_book_relations_fn)`; returns (book, curated_document). Body is in apps/ingestion/pipeline (not mine) — sm/book_persistence.py:165-174
- [P3] Complete submission — `complete_processed_submission`: linked_book=book, duplicate_of_book=None, resolved_url=normalized_url, resolution RESOLVED, confidence=max(current, 1.0) (always 1.0 effectively), status READY, review_state=book.review_state, error cleared, raw_payload normalized_url/linked_book_slug/processing_source/served_from_database False; sync dependents; preview session only if submitter_id; AuditLog `submission.processed` {book_id, source: "scrape"|"reprocess"} — ss/persistence.py:8-44
- [P4] Export payload — `export_payload_from_book(book, scraped)`: author names from book contributors (role AUTHOR) else scraped author; series names from book else scraped; book_type = category names else scraped book_type; cover = scraped.cover or book.cover_source_url; main_content/book_info/dedication from book; front_sections/back_sections from book.raw_scrape_payload or scraped; toc/content_items from book; output_folder from scraped (KeyError if absent) — ss/persistence.py:136-166

### Asset syncing
- [A1] `sync_assets(book, job, scraped)`: for each of HTML (output_folder/book.html), EPUB (`safe_epub_filename(f"{title}.epub")` in output folder, else first *.epub sorted, else None), COVER (resolve_generated_cover_path): get_or_create GeneratedAsset(book, asset_type). Missing file -> status FAILED. Present -> status READY, size, content_type from suffix (.epub application/epub+zip; .jpg/.jpeg image/jpeg; .webp image/webp; .html text/html; else application/octet-stream — note .png falls to octet-stream), sha256 checksum (8192 chunks), source_job=job; deletes previous stored file (`asset.file.delete(save=False)`), saves new file into storage, storage_path=file.name, legacy_path cleared. Then `cleanup_staged_asset_files(output_folder, synced_paths)`. Required types HTML and EPUB (labels "HTML","EPUB"); if either missing: book.state=NEEDS_REVIEW, book.review_state=NEEDS_REVIEW and ValueError "Missing generated assets: HTML, EPUB." (triggers job retry path J4). Cover is optional — ss/assets.py:103-141, consts sm/job_lifecycle.py:122-126
- [A2] Cover resolution — requested cover path (absolute or relative to output folder); else any file with same stem; else first `book_cover.*` then `book_image.*` — ss/assets.py:33-51
- [A3] Staging cleanup — skipped if folder missing or inside MEDIA_ROOT; otherwise unlink synced files that are within folder, then try rmdir (ignore OSError so leftover files stay) — ss/assets.py:81-100. Only synced files removed; FAILED/unsynced leftovers remain.

### Preview access
- [V1] `ensure_preview_session(user, book, submission=None, allow_guest=False)`: no user and not allow_guest -> None. Looks for unexpired (`expires_at__gt now`) PreviewAccessSession for book + user (or user null + source_submission when guest); newest returned; else creates (user, book, source_submission). `expires_at` default is model-defined — ss/preview.py:13-39
- [V2] `can_manage_processing_records(user)` = is_staff or scope PROCESSING_MANAGE — ss/preview.py:7-10

### Audit log writes (all)
- `submission.created` {input_type} (sm/book_persistence.py:19)
- `submission.fulfilled_from_database` {book_id, source} (resolution_and_queueing.py:75)
- `submission.processed` {book_id, source} (ss/persistence.py:38)
No audit entries for retry, cancel, resume, delete, reprocess, duplicate review, stale recovery, failure (those use ProcessingLog instead).

### ProcessingLog writes
Started processing; Curated source content; exact URL/title match; metadata duplicate warning; curated needs review x2; "Generated HTML and EPUB exports..."; "Submission finished successfully."; failure; stop requested/cancel message; requeue; auto-fail; dispatch fallback; "Submission requires review before processing can continue."

## 3. State machines

### SubmissionStatus (values seen: PENDING_RESOLUTION, QUEUED, PROCESSING, READY, NEEDS_REVIEW, DUPLICATE, FAILED, CANCELLED, DELETED)
- create: -> PENDING_RESOLUTION (title) / QUEUED (url)
- PENDING_RESOLUTION -> QUEUED (exact_match) | NEEDS_REVIEW (ambiguous/unresolved)
- URL create: -> NEEDS_REVIEW (invalid URL, resolution INVALID) | READY (reuse/existing book) | QUEUED
- QUEUED -> PROCESSING (job start) | CANCELLED (cancel/finalize) | DELETED (soft delete) | READY (fulfill from existing book on dedupe)
- PROCESSING -> READY (complete_processed_submission or existing-book hit) | DUPLICATE (metadata dup) | NEEDS_REVIEW (curation review / unresolved title) | QUEUED (auto requeue) | FAILED (3rd failure or stale-fail) | CANCELLED
- NEEDS_REVIEW/FAILED/DUPLICATE/READY -> QUEUED (retry; READY too since retry forces QUEUED unless QUEUED/PROCESSING)
- CANCELLED -> QUEUED (resume)
- any -> DELETED (soft delete, never while a PROCESSING job exists) ; DELETED -> row hard-deleted
- Dependents mirror canonical status via sync (copy).
- Re-resolution in runner may set NEEDS_REVIEW for title submissions (then job SUCCEEDED).

### ResolutionStatus (seen): RESOLVED, EXACT_MATCH, AMBIGUOUS, UNRESOLVED, INVALID. Transitions only at creation/resolution/fulfil/complete (-> RESOLVED).

### JobStatus: QUEUED, PROCESSING, SUCCEEDED, FAILED, CANCELLED
- QUEUED -> PROCESSING (runner) | CANCELLED (cancel) | QUEUED (redispatch)
- PROCESSING -> SUCCEEDED (also for duplicates/needs-review outcomes) | QUEUED (retry, retry_count<3) | FAILED (retries exhausted, stale fail) | CANCELLED
- CANCELLED -> QUEUED (resume). SUCCEEDED/FAILED terminal (no resume of FAILED; retry is via submission-level new job).
- cancel_requested flag: set True on cancel; reset False on finalize/requeue/resume.

### Book.state (LifecycleState): READY, PROCESSING, NEEDS_REVIEW (and previous state restoration)
- reprocess queue: any -> PROCESSING (previous saved in job payload); success -> READY (via curated persistence, other agent); cancel/final failure -> previous_book_state; missing assets -> NEEDS_REVIEW; stale auto-fail does NOT restore.
- persist_scraped_book revives soft-deleted: deleted_at=None, state READY, review_state PENDING.

### ReviewState: PENDING, NEEDS_REVIEW (others in model). Retry sets PENDING; fulfil/complete copy book.review_state.

### DuplicateReviewStatus: CONFIRMED (exact), PENDING (metadata). Transition away from PENDING not in these files.

### GeneratedAssetStatus: FAILED (missing), READY.

## 4. Config / constants
- MAX_PROCESSING_JOB_ATTEMPTS = 3
- STALE_PROCESSING_JOB_AFTER = 20 minutes; recover limit default 50
- ACTIVE_JOB_STATUSES = (QUEUED, PROCESSING)
- REUSABLE_SUBMISSION_STATUSES = (PENDING_RESOLUTION, QUEUED, PROCESSING, READY)
- SUBMISSION_PAYLOAD_KEYS_TO_SHARE = served_from_database, existing_book_source, linked_book_slug, source_page_metadata, normalized_url, scraped_preview
- RETRY_PAYLOAD_RESET_KEYS = served_from_database, existing_book_source, linked_book_slug
- JOB_CANCEL_MESSAGE "Stopped by user."; REQUEST_DELETE_MESSAGE "Deleted by user."
- Messages: STALE_PROCESSING_RETRY_MESSAGE, STALE_PROCESSING_FAILURE_MESSAGE, PROCESSING_RETRY_MESSAGE_TEMPLATE "Processing failed on attempt {attempt} of {max_attempts} and will retry automatically."
- REQUIRED_GENERATED_ASSET_TYPES = (HTML, EPUB); GENERATED_ASSET_LABELS
- queue_name values: "engine", "inline-fallback"; handler name "process_submission"
- raw_payload flags: skip_duplicate_checks, submitted_publicly, reprocess_book_id, deduplicated, canonical_submission_id, curated_document_id, curated_validation, processing_source
- detected_by values: exact_source_url, exact_normalized_title, normalized_metadata
- File checksum chunk 8192; content-type map in A1; fallback cover stems book_cover, book_image
- Classification constants (X7)
- Settings used: MEDIA_ROOT (ss/assets.py); `settings` imported in job_lifecycle but unused.

## 5. Bugs, dead code, duplication, surprises
1. exec()-based facade: five files share one namespace; sm/ files are not importable alone (no imports) and rely on load order/names (e.g. runner uses `resolve_submission`, `sync_assets`). Static analysis/IDEs cannot resolve them. Rebuild: real modules.
2. Name collision: `sync_assets`, `sync_submission_from_canonical`, `sync_deduplicated_submissions`, `persist_scraped_book`, etc. exist as both underscored ss/ implementation and wrapper; wrappers only exist to inject dependencies (dependency-injection by function args), heavy ceremony.
3. Dead/unused in assigned files: `create_local_resolution_attempt`, `classify_incoming_book` (+CLASSIFY_*), `find_existing_matching_book`, `persist_scraped_book`/`_persist_scraped_book` (runner uses curated persistence; only legacy path), `legacy_config_entries_as_submission_inputs` (caller outside), many imports in job_lifecycle (settings, IntegrityError, transaction, BookCategory, BookContributor, BookSeries, Category, Contributor, Series, ContributorRole, normalize_catalog_text, DuplicateReview..., calculate_checksum, candidate_asset_paths, cleanup_staged_asset_files, content_type_for_suffix, path_is_within, resolve_generated_cover_path, load..., persist_curated_document used, `promote_leading_front_matter`, `curate_...`). `MetadataVersion` side effects only in the legacy persist path.
4. `build_retry_payload` ignores actor/previous_status/previous_error_message (params unused; probably intended to record requeue info — the stripped keys requeued/requeued_at/requeue_requested_by/requeue_reason suggest an earlier version wrote them).
5. `legacy_scrape_overridden` module-name sniff is a test seam that changes production control flow (whole branch: curation path validity checks skipped when overridden; X5/X6 conditioned on `not legacy_scrape_overridden`).
6. Title-submission job returns SUCCEEDED without work when resolution fails (runner 30-36); job success != ingestion success. Same for duplicates and needs-review: JobStatus.SUCCEEDED means "job ran", with real outcome in submission.status.
7. Metadata duplicate scan (X4) iterates every non-deleted book in Python and calls texts_are_similar per book, with no source_site filter, unlike X3: O(N) per ingestion; also inconsistent with X3's source_site scoping. Rebuild needs an indexed/trigram strategy.
8. Duplicate-check inconsistency: X3 requires incoming authors+categories, then skips candidates missing them; X4 repeats the same rules after a fuzzy title gate. Near-duplicate logic written twice (detection.py:58-78 vs 112-127); X7 and X8 are third and fourth variants with different semantics (X8/X7 allow empty authors on both sides, X3/X4 forbid).
9. Dedup tree is single-level (`root_submission` one hop) while `find_reusable_submission` requires `canonical_submission IS NULL`, so chains are avoided only by that filter; sync copies status verbatim, so a dependent can be mirrored as PROCESSING etc.; dependents are not deleted/cancelled independently (all mutations act on root). Retry permission check uses the passed submission's submitter, not root's: a dependent's submitter can retry the shared root.
10. Reuse is global across users (D1 has no submitter filter) and includes anonymous ones; a user's request can attach to someone else's, and sync overwrites dependents' review_state/error.
11. `soft_delete_submission_record` calls cancel for QUEUED jobs which first sets submission CANCELLED then DELETED; if the submission was already DELETED the early-return still updates nothing. Also does not touch dependents' independent state besides sync. `delete_submission_record` second call hard deletes (irreversible; cascades unknown).
12. `fail_processing_job` (stale-exhausted path) doesn't restore reprocess book state, unlike runner failure and cancel, leaving the Book stuck in PROCESSING.
13. Stale-recover counts: failed ones aren't included in `recovered`. QUEUED-without-task_id recovery redispatches jobs immediately even ones just created but not yet dispatched (race with queue_submission, which creates then dispatches in separate saves; task_id set only inside dispatch).
14. Dispatch fallback: if the engine is down, processing runs synchronously inside the HTTP/caller thread (up to 3 attempts), blocking requests; broad `except Exception` also catches errors *during* dispatch that may have already enqueued the task -> possible double processing (the runner short-circuits SUCCEEDED/CANCELLED but not PROCESSING).
15. Runner `except Exception` + `raise` after requeue: relies on engine retry and also on inline loop; both increment attempts independently (retry_count param vs job.retry_count). `requeue_processing_job` stores retry_count but runner passes retry_count from engine attempt; `attempt_offset` used to reconcile. Potential off-by-one divergence.
16. Cancel is cooperative with only 4 check points; no check between persist_curated_book / sync_assets / complete; terminate=True revoke may kill the worker mid-write (no transaction wraps persistence; partial book/asset state possible). Whole `process_submission_job` is not in a transaction.
17. `sync_assets`: raises ValueError after setting book NEEDS_REVIEW, which causes job retry up to 3 times; on final failure the submission is FAILED but book remains NEEDS_REVIEW (and for reprocess, state later restored to previous_book_state, overriding NEEDS_REVIEW). Asset FAILED rows are created even when only the optional cover is missing. `.png` covers get content_type octet-stream. Old stored file deleted before new saved (data loss if save fails).
18. `complete_processed_submission` max(resolution_confidence,1.0) always yields >=1.0; preview session only for submitters (anonymous submitters get none even though ensure_preview_session supports guests; fulfil path calls ensure_preview_session(submitter=None) -> returns None, so anonymous submissions never get a preview session).
19. `capture_source_page_metadata` swallows every exception silently (no log), also performs a DB upsert as a side effect in what looks like a read.
20. URL create flow catches only ValueError; `capture_source_page_metadata`/DB errors would abort the whole batch midway (earlier submissions created, later ones not).
21. `queue_reprocess_book` race: check-then-create without locking; no AuditLog; `primary_source_url_for_book` may return "" leading to blank resolved_url.
22. Audit coverage is thin (3 verbs); no actor on cancel/delete/retry; actor_id stored only in job payload.
23. `ensure_preview_session` for guest filters by source_submission only when provided; `get` race can create duplicates (no unique constraint seen).
24. Persist (legacy) Book revived by `find_deleted_book_by_title` purely by title: a different book with the same title as a deleted one gets overwritten (no author check).
25. Mixed-script note in assets comment: Bengali titles ("ভলিউম ৪/১") require safe EPUB filename; the source site is Bengali-language, so normalization (normalize_catalog_text) must be Unicode aware.
26. services/__init__.py is empty (1 blank line); ss/__init__.py is a comment.

## 6. Unread
Nothing in the assigned set was left unread. Not covered (belongs elsewhere, referenced only): legacy_adapter, resolution*, normalization*, curation*, pipeline/* (curated persistence body, curate_book_document, generate_exports, safe_epub_filename), engine/dispatch, models (status enums, expires_at default), catalog services (find_existing_book_by_source_url, find_deleted_book_by_title, replace_book_relations), TitleResolver thresholds, `texts_are_similar` threshold.
