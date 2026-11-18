Status: DRAFT

# D2 - Ingestion: submissions, resolution, normalization, curation, job engine (legacy analysis for rebuild)

Sources (source report IDs used in citations): R03 = features/03-ingestion-submissions.md (ids S*, D*, R*, J*, T*, Y*, DEL*, X*, P*, A*, V*); R04 = features/04-ingestion-resolution-normalization-curation.md (ids RES*, META*, FM*, SEG*, NORM*, CAT*, RUN*, ACT*); R05 = features/05-ingestion-engine-api-config.md (endpoint numbers #1-#40, sections Engine/Celery/Signals/Commands/Settings); R14g = features/14g-notes-engine.md (EN1-EN18). Code paths are relative to `archive/app/backend/`. Verification marks: VERIFIED = I checked the code line; UNVERIFIED = taken from reports only.

## 1 Purpose and scope

The ingestion bounded context turns an operator/reader "request" (a source-site book URL or a free-text Bengali title) into a finished book: resolve the title to a URL, de-duplicate against existing books and earlier requests, scrape and curate the source page into structured content (metadata, contributors, front matter, dedication, chapters/TOC), persist the Book, generate HTML + EPUB (+ optional cover) assets, and make a reader preview available. Around that core sit: a source catalog (a crawled index of the one source website), scheduled/manual "curation runs" that bulk-create or reprocess books from the catalog, duplicate review, an activity feed, and a central job engine (Redis pub/sub on top of Celery) that dispatches jobs to workers.

In scope for this report: submissions and their dedup tree; processing jobs and logs; title resolution and match scoring; scraped-metadata normalization (contributor roles, labels, front matter, dedication, chapter inference); catalog refresh and curation runs and automation schedule; duplicate review; ingestion HTTP API (40 operations / 36 paths under `/api/ingestion/`); job engine, Celery tasks, signals, management commands, settings. Out of scope (other analyses): the scraper pipeline body (`pipeline/*`: curate_book_document, generate_exports, persist_curated_book_with_hooks), catalog/Book model and `apps.processing` (BookCreationRequest, refresh_catalog_parallel), access/preview-session model, common permissions/throttles.

Product context: private invite-only Bengali ebook library; one operator imports from one source site; the source site's Bengali text (and a WordPress theme with FacetWP archive + "Fixed TOC Plus" plugin) shapes many heuristics.

## 2 Features and behaviours

Stable IDs D2-Fn. "Src" cites report IDs.

### 2.1 Submission intake
- D2-F1 Create submissions from a batch of entries (kind url|title); one BookSubmission per entry; input normalized; initial status PENDING_RESOLUTION (title) or QUEUED (url); anonymous (submitter null) allowed and flagged `raw_payload.submitted_publicly`; audit `submission.created`. Src S1, R05 #2.
- D2-F2 URL entry flow: validate host/path (allow-list), reuse an existing equivalent request, capture source page metadata, link to an already-imported Book by source URL (instantly READY), else mark RESOLVED(1.0)/QUEUED. Invalid URL -> resolution INVALID, status NEEDS_REVIEW with error message. Src S2, RES-19.
- D2-F3 Title entry flow: reuse equal-title request; run title resolver; if a resolved URL maps to an existing Book, fulfil from it without a job. Src S3.
- D2-F4 Auto-queue: after intake, `auto_process` + resolved URL + QUEUED -> create ProcessingJob and dispatch. Src S4, J1.
- D2-F5 Input formats at the API: `input_type` url/title/csv, free `content` (lines or CSV with url/title/query/first column), or `entries` list (http* -> url else title); 40/hour throttle on create. Src R05 #2.
- D2-F6 Legacy config import (old scraper config list of URLs) as submission inputs via a management command. Src S5, R05 section 6.
- D2-F7 Confirm candidate: for ambiguous title matches the user picks one of the top-3 MatchCandidates; the submission resolves to it and queues (or fulfils from an existing Book). Src R05 #6.

### 2.2 Request-level reuse (dedup tree)
- D2-F8 Reusable-request lookup (by resolved URL first, then by normalized input) over canonical submissions in status PENDING_RESOLUTION/QUEUED/PROCESSING/READY, not scoped by submitter. Src D1.
- D2-F9 Dependent submissions mirror the canonical one (copy of resolved_url, statuses, linked/duplicate book, error, shared payload keys); fan-out sync after nearly every state change; all mutations act on the root. Src D2-D4.

### 2.3 Title resolution
- D2-F10 Resolve title -> URL: score all SourceCatalogEntry rows (tiers 1.0 / 0.88 / 0.78 / Jaccard*0.75), keep top 3, optionally refresh catalog (letter bucket), enrich top 3 from live pages, decide exact_match (top == 1.0 and unique), ambiguous (any candidates) or unresolved. Writes TitleResolutionAttempt + MatchCandidate rows. Src R1, RES-01..06, RES-02..04.
- D2-F11 Catalog crawl: page through the archive listing (`/books/` with `_a_z`, `_paged`), parse title + author from "Title - Author" display text, upsert SourceCatalogEntry, loop guard on repeated page signature. Src RES-07..09, RES-11.
- D2-F12 Book page metadata fetch: title, author line, series, category, canonical URL from page; upsert catalog entry (merge raw_data). Src RES-12..14, R4.
- D2-F13 Source URL normalization/allow-list: only configured source host (+www twin, + fallback hosts), path must start `/books/`, forced https, query/fragment dropped. Src RES-19.
- D2-F14 Resilient fetch: host fallback list, then DNS fallback (system, raw UDP to configured resolvers, DNS-over-HTTPS) and direct-IP HTTPS with hostname-verified certificate. Src RES-15..17.

### 2.4 Processing pipeline (job)
- D2-F15 Main job pipeline (see 7.2): resolve if needed -> normalize URL -> capture metadata -> exact-URL dedup -> scrape+curate -> exact-title dedup -> metadata-similarity dedup -> persist book -> generate HTML/EPUB -> sync assets -> complete submission. Src J3.
- D2-F16 Reprocess (regenerate) an existing book: new URL submission + REPROCESS job, book.state=PROCESSING, previous state saved for restore, high-fidelity scrape limits, dedup checks skipped. Src S6, X2.
- D2-F17 Fulfil from existing book: sets READY, links book, creates reader preview session, audit `submission.fulfilled_from_database`. Src R3.
- D2-F18 Curated-document quality outcomes: invalid with no title -> persist document only, NEEDS_REVIEW; non-validated with title -> persist book, NEEDS_REVIEW, no assets. Src X5, X6.
- D2-F19 Asset sync: HTML, EPUB required; cover optional; checksum, size, content type; staging folder cleanup; missing required -> book NEEDS_REVIEW + error + retry. Src A1-A3.
- D2-F20 Reader preview: ensure an unexpired PreviewAccessSession for (user, book); action-links endpoint returns launch URL, manifest, EPUB download and HTML preview URLs. Src V1, R05 #7.

### 2.5 Duplicate detection and review
- D2-F21 Three automatic book-level detectors: exact source URL (CONFIRMED), exact normalized title + overlapping authors/categories (CONFIRMED), metadata similarity via fuzzy title + same attribute rules (PENDING review, submission -> DUPLICATE). Src X1, X3, X4.
- D2-F22 Duplicate review queue for managers: list, resolve (confirm existing / dismiss / aliases same_book, new_book). Src R05 #39, #40.

### 2.6 Job control
- D2-F23 Cancel (cooperative flag + task revoke, finalize), resume (QUEUED/CANCELLED only), requeue on failure up to 3 attempts, fail, bulk stop/resume/delete, delete of non-active job. Src J5-J7, J11, J12, R05 #15-#21.
- D2-F24 Stale recovery: QUEUED jobs never dispatched and PROCESSING jobs older than 20 min are re-dispatched or failed after 3 attempts; runs every minute (beat) and by operator button. Src T1, R05 #14.
- D2-F25 Manual retry of a request (single/bulk), delete request (soft then hard; bulk). Src Y1, Y2, DEL1, DEL2, R05 #8-#10.
- D2-F26 Per-job log stream (ProcessingLog, 200 lines) and live SSE feed of engine events for managers. Src R05 #13, #19.
- D2-F27 Activity snapshot for polling UI: which scopes (submissions, jobs, source_jobs, automation_jobs, runs, catalog_refresh) have active work, scoped to caller. Src ACT-01.

### 2.7 Normalization and curation of scraped content
- D2-F28 Contributor/role extraction: role keyword vocabulary (translator, editor(+compiler folded), cover artist, illustrator, publisher; authors = unlabelled), label+value parsing, name validity heuristics, multi-value splitting (",;|\n", "ও/and/&"), publisher trimming. Src META-01..16.
- D2-F29 Front-matter detection: label/value lines scored (threshold 5), plausibility and title-prefix rules; front-section headings (foreword, preface...), dedication headings, body-section markers; TOC removal incl. Fixed TOC Plus containers. Src FM-01..15.
- D2-F30 Content segmentation: split leading/trailing front sections, extract dedication + book-info, infer chapters (heading scoring / numeric markers), sub-chapter synthesis, residual classification, de-duplication of fragments/sections. Src SEG-01..12.
- D2-F31 Scraped book normalization: output `{title, contributors, series, categories, raw_strings}`, ordered book-info HTML re-emit with canonical key order. Src NORM-01..06.
- D2-F32 Curation quality gate: reject books with no readable body (structure no_public_body, no body section text, < 200 chars) and quarantine. Src RUN-16 (not wired in runtime; used by CLI curate command per R05 section 6).

### 2.8 Catalog sync, curation runs, automation
- D2-F33 Catalog refresh job (singleton state): begin/stop, task ownership guards, status IDLE/QUEUED/PROCESSING/SUCCEEDED/FAILED. Src CAT-01..06, R05 #26-#27.
- D2-F34 Curation run: iterate whole catalog in chunks of 500, per entry compute curation status and (a) create submission for missing/failed/stopped/deleted-local, (b) queue reprocess for unfinished/failed/stopped (or all in mode ALL), (c) skip; summary counters; cancel cooperative. Src RUN-01..04, RUN-06.
- D2-F35 Entry curation status (derived): deleted > processing > stopped > failed > new > unfinished > ready; summary counters, snapshot serialization. Src RUN-07..12.
- D2-F36 Automation settings (singleton) and scheduler tick every minute: enabled, daily_run_time, frequency (8 values), mode, refresh_max_pages; due-time arithmetic; busy/not_due/already_ran/disabled reasons. Src RUN-13, RUN-14, R05 #36-#37.
- D2-F37 Manual "create books" for selected catalog entries and for "incomplete" books (category contains unfinished/অসম্পূর্ণ) with comparison to the source category. Src R05 #25, #28, #29.
- D2-F38 Catalog entry management: list (3 code paths), sort/filter/page, delete/bulk-delete. Src R05 #22-#24.
- D2-F39 CLI batch curation tool `curate_source_site_books` with resumable batches, verification gates, report; `process_legacy_batch`; `run_engine`. Src R05 section 6.

### 2.9 Job engine
- D2-F40 Capability-routed FIFO dispatch to idle workers via Redis (queue list, active hash, worker hashes, pub/sub), heartbeats, stale detection and requeue, startup DB recovery, DB status write-back. Src R05 section 3, R14g EN1-EN18.

## 3 Actions by actor

| Actor | Actions |
|---|---|
| Anonymous visitor | create submission (rate-limited 40/h per throttle scope), view submission detail by UUID if public, poll status of up to 200 UUIDs, confirm a candidate, request action-links (reader preview token) for a public submission. Src R05 #2,#3,#4,#6,#7 (VERIFIED AllowAny: apps/ingestion/views/submissions.py:48,92,114,119,136,180). |
| Authenticated user (invited reader) | list own submissions/jobs (managers see all), delete own request (single/bulk), retry (single/bulk), stop/resume own jobs, bulk-delete own non-active jobs, view job logs, activity snapshot. Src R05 #1,#5,#8,#9,#10,#11,#15-#21,#38. |
| Manager (`CanManageProcessing` = staff or scope processing.manage) | everything above across all users; reprocess summary; SSE stream; recover stale jobs; catalog entries CRUD/list; create-books; catalog refresh/stop; incomplete-check; curation runs create/stop/delete/bulk; automation settings get/patch; duplicate review list/resolve. Src R05 #12-#14, #22-#40. |
| Scheduler (Celery beat) | run_catalog_automation_schedule (1 min), recover_stale_processing_jobs (1 min), heartbeat (5 s). Src R05 section 4. |
| System/worker | process job, catalog refresh task, curation run task, engine assign/complete. |
| Operator (CLI) | run_engine, process_legacy_batch, curate_source_site_books. |

## 4 Business rules and invariants

### 4.1 Request-level duplicate detection (reuse)
- BR1 A new request attaches to an existing canonical request when `canonical_submission IS NULL`, status in {PENDING_RESOLUTION, QUEUED, PROCESSING, READY}, linked/duplicate book not soft-deleted; match by resolved URL (newest) then by normalized input (newest). Not scoped by submitter or anonymity. Dependents copy state; one level only; every mutation targets the root. (D1-D4)
- BR2 Retry/delete/cancel act on the root; permission on retry is evaluated on the passed (possibly dependent) submission.
- BR3 Only one active (QUEUED/PROCESSING) job per submission and per book (reprocess): `queue_submission` and `queue_reprocess_book` return the existing job. No locking (check-then-create).

### 4.2 Book-level duplicate detection (in job, skipped when job is REPROCESS or `raw_payload.skip_duplicate_checks`)
1. Exact normalized source URL -> existing Book: submission READY from DB, DuplicateReview(exact_source_url, CONFIRMED), job SUCCEEDED, no scrape (X1).
2. Exact normalized title (same source site, not deleted, newest first): requires incoming authors AND categories non-empty; candidate must have both; category sets intersect; if incoming has series it must intersect; if incoming has translators they must intersect; authors intersect (X3). -> fulfil, DuplicateReview(exact_normalized_title, CONFIRMED).
3. Metadata similarity (X4): scan ALL non-deleted books (no source filter), `texts_are_similar(title)` then same attribute rules; hit -> submission DUPLICATE + NEEDS_REVIEW, DuplicateReview(normalized_metadata, PENDING), job still SUCCEEDED. Threshold of `texts_are_similar` lives in pipeline/scraper_support/text (UNVERIFIED value).
4. Unused variants: classify_incoming_book (NEW_WORK/EXACT_DUPLICATE/NEW_EDITION/NEEDS_REVIEW with edition/publisher awareness) and find_existing_matching_book. The edition-aware variant is the only one that models "same title, different edition/translator"; the live detectors cannot (they treat translator mismatch as non-duplicate only when both present).
- Duplicate-review resolution: confirm -> fulfil from existing book (source `duplicate_review_confirmed`, confidence >= 0.95), review CONFIRMED; dismiss -> clear links/flags, re-queue (or NEEDS_REVIEW if nothing to process), review DISMISSED. Statuses: pending/confirmed/dismissed/merged (merged never produced in read code).

### 4.3 Title resolution
- Normalization of query: `normalize_text` (pipeline/scraper_support/text, not read).
- Score tiers (RES-02): 1.0 exact title or "title author" equality; 0.88 `texts_are_similar`; 0.78 substring either way; else Jaccard of whitespace tokens * 0.75 (3 dp).
- Decision (RES-01): exact_match iff top == 1.0 and second < 1.0 (or absent); any candidates else -> ambiguous (no URL); none -> unresolved. A single 0.78/0.88 candidate is never auto-resolved: always human confirmation (D2-F7).
- Candidate cap 3; bucket = first alnum/Bengali char of query; refresh crawl if no candidates or forced; enrich top-3 from live pages, rescoring on fetched title/author.
- Display title split: separator `\s+[–—-]\s+`, rightmost split whose tail "looks like a contributor phrase" (<=140 chars, <=1 sentence mark, no digits, no non-contributor suffix words like খণ্ড/পর্ব/উপন্যাস/edition/vol/part/series, and equals the exact author list or has role labels).
- Resolved URL canonical form: `https://<SOURCE_SITE_HOST>/books/<slug>/`.

### 4.4 Normalization rules (full tables to port as data + tests; R04 section 4 holds verbatim lists)
- Roles: TRANSLATOR, COMPILER(->EDITOR), EDITOR, COVER_ARTIST, ILLUSTRATOR, PUBLISHER; authors are the unlabelled default; match is token-boundary on `normalize_catalog_text`. Labels sorted longest-first; compound aliases (অনুবাদ ও সম্পাদনা etc.).
- Label matching rejects glued matches, "মূল" with whitespace separator (avoids "মূল্য"), mid-string labels without explicit separator.
- Name validity: reject digits (non-publisher), months/dates, addresses, honorific fragments (মো, md), role-label words, verb-suffixed tokens (ছেন, েছে...), prose markers, >8 words, >80 chars, dotted tokens that are not initials. Publisher rules: org keyword (প্রকাশনী, publishers, library, limited) required for >4 words; address trimmed at stop patterns/numbers; solo-English disallow list.
- Front matter: line accepted if score >= 5 (no prefix +8, title-prefix +6, break +5, strong +4...), values <=180 chars, text <=320.
- Dedication: headings উৎসর্গ / অনুবাদকের উৎসর্গ / লেখকের উৎসর্গ / dedication; block continues until body marker, numeric marker, label line, >600 chars, or >8 sentence marks. Default heading "উৎসর্গ" ("Dedication" if English).
- Chapters: heading candidate scoring (+3 chapter keyword, +3 numeric prefix, +2 ordinal word, +1 heading tag, +1 <=8 words); thresholds strong >=4 / usable >=3 / loose >=2; numeric-marker fallback needs >=4 blocks, markers starting at 1 or 2, near-sequential; sub-chapter synthesis from h2/h3/h4 (needs >=2 headings, each section >=20 chars, preamble >=80 chars kept as parent intro).
- Dedupe: signature = normalize_catalog_text(clean_display_text(text)), min length 8; navigation sections (TOC title + >=3 anchors, >=75% external `/books/` links) dropped.
- Digits: chapter titles converted to Bengali digits; numeric markers accept both scripts.
- Canonical book-info key order: title, original_title, author, translator, editor, compiler, illustrator, cover_artist, publisher, type, series, category, first_published, publisher_address, edition, language, page_count, isbn, price.
- Series/categories split on `[,;|\n]`, de-duped by normalized form.

### 4.5 Review states and statuses
- Submission status: draft, pending_resolution, queued, processing, needs_review, ready, failed, cancelled, duplicate, deleted. Resolution status: unresolved, resolved, exact_match, ambiguous, rejected, invalid. Review state (shared enum): PENDING, NEEDS_REVIEW (others exist, e.g. REJECTED used by quarantine). Book.state: READY, PROCESSING, NEEDS_REVIEW, ARCHIVED. Job: queued, processing, succeeded, failed, cancelled (API presents cancelled as "stopped"). Job types: resolution (declared), ingestion, reprocess. Origin: user, curation, automation.
- Invariant: JobStatus.SUCCEEDED means "the job ran"; the real outcome is on the submission (READY/DUPLICATE/NEEDS_REVIEW). A title that cannot be resolved still yields a SUCCEEDED job.
- Invariant: max 3 attempts per job (MAX_PROCESSING_JOB_ATTEMPTS = 3), retry_count 0..2.
- Invariant: required generated assets for a "ready" book are HTML and EPUB (cover optional).
- Invariant: Book is never READY with only a partial pipeline; incomplete books are reprocess candidates (status `unfinished`).
- Invariant (intent): reprocess must restore book.state on cancel/final failure (not honoured by stale-fail path, see 8).
- Permission rules: visibility = manager OR submitter OR (submitter null AND submitted_publicly); job control `can_manage_job` = staff or scope processing.manage or job submitter; bulk endpoints use visibility instead (divergent).
- Source-URL rules: host allow-list; path starts `/books/`; https only; query/fragment dropped (collapses URL variants).
- Automation locks (409): scheduled run active blocks manual curation operations; refresh in progress blocks create-books (only that endpoint).

## 5 Data handled/owned

All UUID PK with created_at/updated_at (R05 section 8).
- **SourceCatalogEntry**: source_url (unique, <=1000, trailing slash), title, author_line, normalized_title, normalized_display (indexed), raw_data JSON {metadata_source archive_page|book_page, title, display_title, full_title, author_line, meta_author_line, title_author_line, series, category}, last_seen_at (auto_now), created_at. Lifecycle: created by crawl or single-page upsert; raw_data overwritten by crawl, merged by upsert; deleted manually; never expired.
- **BookSubmission**: submitter (null=anonymous), input_type url/title/csv, origin, original_input, normalized_input, resolved_url, resolution_status, resolution_confidence, status, review_state, linked_book, duplicate_of_book, canonical_submission (self FK), raw_payload JSON (flags: submitted_publicly, deduplicated, canonical_submission_id, served_from_database, existing_book_source, linked_book_slug, source_page_metadata, normalized_url, scraped_preview, curated_document_id, curated_validation, skip_duplicate_checks, reprocess_book_id, processing_source), error_message. Side effect: `save()` get_or_creates a `UserBook` (puts book into submitter's library) when submitter and linked_book are set.
- **TitleResolutionAttempt** (query, normalized_query, status, confidence, resolved_url, raw_results, error; also source "local_database" by dead code) and **MatchCandidate** (rank from 1, title, author, url, confidence, metadata, is_selected).
- **ProcessingJob**: submission, book, job_type, status, task_id, queue_name ("engine"|"inline-fallback"|"celery"), worker_hostname, retry_count, cancel_requested, payload {resolved_url, actor_id, reprocess_book_id, previous_book_state}, last_error, started_at, finished_at. **ProcessingLog**: job, level info/warning/error, message, details JSON (cascade delete).
- **DuplicateReview**: submission, existing_book, detected_by (exact_source_url, exact_normalized_title, normalized_metadata), status, notes, raw_evidence.
- **CatalogAutomationSettings** singleton (enabled False, daily_run_time 02:00, frequency, mode pending/all, refresh_max_pages 80, updated_by). **SourceCatalogRefreshState** singleton. **CatalogCurationRun** (trigger manual/scheduled, mode, status, refresh_catalog, refresh_max_pages (0 = unlimited), requested_by, task_id, queue_name, retry_count, cancel_requested, summary JSON {catalog_entries, refreshed_entries, queued_creates, queued_updates, skipped_ready, skipped_processing, skipped_deleted(never set), errors<=20, status_counts}, last_error, started/finished).
- **GeneratedAsset** (book, asset_type HTML/EPUB/COVER, status READY/FAILED, size, content_type, sha256, storage_path, source_job) and **PreviewAccessSession** (user|null, book, source_submission, token, expires_at) are owned by catalog/access but written here. **MetadataVersion** (legacy persist only), **BookSource** (normalized_source_url -> book), **CuratedBookDocument** (second ingestion model).
- Redis (engine): `engine:worker:{host}` hash, `engine:queue:pending` list, `engine:active` hash, `engine:job:handlers` hash (see 7.4). No TTLs.
- Files: staging output folder per job (html/epub/cover) outside MEDIA_ROOT; synced into storage; per-URL disk page cache for CLI curation (md5 key jsonl); source_site_auth.json cookie state.
- Audit: AuditLog verbs submission.created, submission.fulfilled_from_database, submission.processed only. Everything else only in ProcessingLog.
- Retention: no TTL/cleanup for submissions, attempts, logs, jobs, catalog entries, engine keys.

## 6 Interfaces

Mount `/api/ingestion/`. Global DRF default is SessionAuthentication + AllowAny (VERIFIED settings only sets default; each view sets its own). JSON; SSE for #13. No pagination; per-view `limit`. Status "cancelled" shown as "stopped" (filter translates back). Full table from R05 section 2; condensed (auth: A=anonymous allowed, U=authenticated, M=manager):

| # | Op | Auth | Request -> Response / effect |
|---|---|---|---|
| 1 | GET submissions/ | U | filters origin(catalog=curation+automation), status, review_state, resolution_status, input_type, q (3 variants raw/hyphen/url-encoded), linked_book_slug, created_after/before, limit 80/200 -> list SubmissionSerializer (incl. candidates top 3, latest_job, linked_book summary) ordered by status priority |
| 2 | POST submissions/ | A + throttle 40/h | input_type/content/entries/auto_process -> 201 list; creates submissions (+jobs) |
| 3 | POST submissions/status/ | A | ids (1-200) -> visible submissions |
| 4 | GET submissions/{id}/ | A (403 if not manager/owner/public) | detail |
| 5 | DELETE submissions/{id}/ | U | soft/hard delete; 400 if processing |
| 6 | POST submissions/{id}/confirm-candidate/ | A (access check) | candidate_id -> resolves + queues or fulfils; 400/403/409 |
| 7 | POST submissions/{id}/action-links/ | A (access check) | -> book, launch_url (FRONTEND_BASE_URL/reader?manifest=...), manifest_url, epub_download_url, html_preview_url, expires_at; creates/reuses preview session (guest allowed for public); 400/410 |
| 8 | POST submissions/bulk-delete/ | U | ids<=200 -> counts |
| 9 | POST submissions/bulk-retry/ | U | ids -> 202 counts (409 lock) |
| 10 | POST submissions/{id}/retry/ | U | -> 202 job; non-visible id -> 500 |
| 11 | GET jobs/ | U | filters origin/status(csv)/submission_status/job_type/q/dates, limit 80/200 -> ProcessingJobSerializer list |
| 12 | GET jobs/reprocess/summary/ | M | {queued, active, done, failed, stopped} |
| 13 | GET jobs/stream/ | M | SSE `connected`, `job-update` (raw engine event), keepalive 5 s; own Redis subscription per client (assigned/completed/reassigned) |
| 14 | POST jobs/recover/ | M | origin, limit 1-100 default 50 -> 202 {recovered_jobs} |
| 15 | POST jobs/bulk-stop/ | U | ids -> counts |
| 16 | POST jobs/bulk-resume/ | U | ids -> 202 counts (409 lock) |
| 17 | POST jobs/bulk-delete/ | U | ids -> counts |
| 18 | DELETE jobs/{id}/ | U | 204; 400 if active |
| 19 | GET jobs/{id}/logs/ | U | first 200 logs ascending |
| 20 | POST jobs/{id}/resume/ | U + can_manage_job | 202 |
| 21 | POST jobs/{id}/stop/ | U + can_manage_job | job |
| 22 | GET catalog/entries/ | M | q, status, include_summary, include_sync_state, view=overview, sort (6 options), limit 180/400, page -> entries + pagination + summary + sync_state; three internal code paths |
| 23 | DELETE catalog/entries/{id}/ | M | 204 |
| 24 | POST catalog/entries/bulk-delete/ | M | counts |
| 25 | POST catalog/entries/create-books/ | M | ids -> 202 counts + errors<=20 (409 locks) |
| 26 | POST catalog/refresh/ | M | max_pages (default 3, unbounded) -> 202 refresh state |
| 27 | POST catalog/refresh/stop/ | M | state |
| 28 | GET catalog/incomplete-check/ | M | q, status removed/still/missing -> summary + entries (unpaged) |
| 29 | POST catalog/incomplete-check/create-books/ | M | book ids -> 202 reprocess counts |
| 30 | GET catalog/curation-runs/ | M | trigger,status,mode,q,limit 12/50 |
| 31 | POST catalog/curation-runs/ | M | mode, refresh_catalog, refresh_max_pages 1-80 -> 202 run |
| 32 | DELETE catalog/curation-runs/{id}/ | M | 204; 400 if active |
| 33 | POST catalog/curation-runs/{id}/stop/ | M | run |
| 34 | POST catalog/curation-runs/bulk-stop/ | M | counts |
| 35 | POST catalog/curation-runs/bulk-delete/ | M | counts |
| 36 | GET catalog/automation/ | M | {settings (with next_run_at), latest_run} |
| 37 | PATCH catalog/automation/ | M | partial update, no range validation |
| 38 | GET activity/ | U | {can_manage_processing, has_visible_activity, active_scopes[]} |
| 39 | GET duplicate-reviews/ | M | origin, status default pending, q, limit 40/200 |
| 40 | POST duplicate-reviews/{id}/resolve/ | M | decision same_book/new_book/confirm_existing/dismiss, notes; 410 if book deleted; 409 lock |

Outbound interfaces: HTTP scraping of the source site (timeout 30 s, Chrome UA, optional cookie auth state via SOURCE_SITE_EMAIL/PASSWORD), DNS UDP/DoH; Redis pub/sub; Celery broker; object/file storage; email not used here.

Channels (JSON, `timestamp` ISO): worker:register {hostname, capabilities[process_submission, pipeline, catalog_sync, curation, automation], pool_size 1, concurrency 1}; worker:heartbeat {hostname}; worker:deregister; worker:done {hostname, job_id, status succeeded|failed, error_message, handler}; job:request {job_id, job_type, handler, args}; job:assigned {job_id, worker_hostname, handler}; job:reassigned {job_id, from_worker, to_worker}; job:completed {job_id, status, error_message}; worker:stale {hostname}.

Management commands: `run_engine [--heartbeat-timeout 15] [--check-interval 2]`; `process_legacy_batch [--url ...] [--sync]`; `curate_source_site_books` (flags: --source-url, --discover, --max-pages, --offset, --limit, --batch-size 50, --all-remaining, --resume-after, --skip-existing, --continue-on-error, --strict-verification, --require-validated, --require-catalog-match, --dry-run, --generate-assets, --force-generate-assets, --require-assets, --perfect, --report-path, --last-chapter-title).

Settings/env that matter for this context: SOURCE_SITE_HOST, SOURCE_SITE_FALLBACK_HOSTS, SOURCE_SITE_DNS_RESOLVERS, SOURCE_SITE_EMAIL/PASSWORD, SOURCE_SITE_AUTH_STATE_PATH, CELERY_BROKER_URL/RESULT_BACKEND, REDIS_URL, CELERY_TASK_ALWAYS_EAGER (default True outside production), CELERY_PROCESSING_CONCURRENCY 5, THROTTLE_SUBMISSION 40/hour, FRONTEND_BASE_URL, RUNTIME_STORAGE_DIR/MEDIA_ROOT, TIME_ZONE Asia/Dhaka. Full list R05 section 7.

## 7 States and processes

### 7.1 State machines
- Submission: create -> PENDING_RESOLUTION (title) / QUEUED (url) / NEEDS_REVIEW (invalid URL) / READY (existing book). PENDING_RESOLUTION -> QUEUED (exact) | NEEDS_REVIEW (ambiguous/unresolved). QUEUED -> PROCESSING (job start) | CANCELLED | DELETED | READY (fulfil). PROCESSING -> READY | DUPLICATE | NEEDS_REVIEW | QUEUED (auto requeue) | FAILED (3rd failure or stale exhausted) | CANCELLED. NEEDS_REVIEW/FAILED/DUPLICATE/READY -> QUEUED (retry). CANCELLED -> QUEUED (resume). any -> DELETED (never while PROCESSING job) -> hard delete. Dependents copy the root.
- Job: QUEUED -> PROCESSING -> SUCCEEDED | FAILED | CANCELLED | QUEUED(retry); CANCELLED -> QUEUED (resume); SUCCEEDED/FAILED terminal (FAILED has no resume; use request-level retry which makes a new job). cancel_requested set on cancel, cleared on finalize/requeue/resume.
- Book.state during reprocess: any -> PROCESSING (previous saved) -> READY (success) | previous (cancel/final failure) | NEEDS_REVIEW (missing assets).
- Refresh state: IDLE -> QUEUED -> PROCESSING -> SUCCEEDED | FAILED; stop -> IDLE with stop message in last_error.
- Curation run: QUEUED -> PROCESSING -> SUCCEEDED | FAILED | CANCELLED (queued cancel immediate; processing cooperative per entry).
- Worker: idle <-> processing; any -> stale (no heartbeat 15 s) -> idle (heartbeat); offline (recovery).
- DuplicateReview: PENDING -> CONFIRMED | DISMISSED.

### 7.2 Job pipeline (process_submission_job, services/submission_modules/processing_job_runner.py)
1. Load; no-op if SUCCEEDED/CANCELLED; honour cancel_requested.
2. job PROCESSING (retry_count, task_id, started_at), submission PROCESSING, sync dependents, log.
3. Title input without URL: re-resolve (force catalog refresh); still unresolved -> job SUCCEEDED, submission stays NEEDS_REVIEW.
4. normalize URL; for REPROCESS verify target book alive and flip to PROCESSING.
5. capture source page metadata (errors swallowed).
6. exact-URL dedup; 7. scrape+curate (curate_book_document, high-fidelity limits for reprocess; ValueError if no content); 8. exact-title dedup; 9. metadata dedup; 10. invalid-doc/no-title branch; 11. persist curated book; 12. non-validated -> NEEDS_REVIEW without assets; 13. export (generate_exports HTML+EPUB), sync assets, complete submission (READY, confidence 1.0, preview session if submitter, audit submission.processed), job SUCCEEDED.
- Cancel checks at 4 points only (before dedup, after curation...), none around persistence/asset sync; no DB transaction around the pipeline.
- Failure: next_retry = retry_count+1; < 3 -> requeue (QUEUED, retry_count, message "Processing failed on attempt N of 3 and will retry automatically.") and re-raise so the engine/Celery retries; else submission FAILED, reprocess book state restored, job FAILED, logs.

### 7.3 Dispatch, retries, stale recovery
- `dispatch_processing_job`: skip if CANCELLED/cancel_requested or already dispatched (QUEUED with task_id); assign task_id, queue_name "engine", call `engine.dispatch.dispatch_job(handler=process_submission)`. Any exception -> queue_name "inline-fallback" and process synchronously in the caller (up to 3 attempts) (VERIFIED resolution_and_queueing.py:178-184; exec facade VERIFIED submissions.py:16).
- Parallel path: Celery task `process_submission_task` (bind, backoff+jitter, max_retries 2). Two dispatch paths exist for the same job.
- Stale recovery (every minute): QUEUED + empty task_id (never dispatched) first, then PROCESSING with started_at (or updated_at) older than 20 min; PROCESSING -> revoke(terminate=True); retry+1 >= 3 -> fail with stale message; else requeue and force dispatch. Beat task covers origins USER, CURATION, and AUTOMATION only if automation enabled; limit 100 total.
- Catalog tasks: refresh (autoretry max 2), curation run (autoretry max 2), automation scheduler (every minute), all with "celery" queue and inline-fallback (runs whole job in web request) on broker failure; EAGER mode just logs.

### 7.4 Central job engine (R05 section 3, R14g)
- Processes: Engine (JobEngine with event-loop thread + stale-check thread), Django publisher (`dispatch_job`: HSET handler, RPUSH queue, PUBLISH job:request - works with engine down), Celery prefork children (register on process init, listener thread executes assigned jobs, heartbeat thread every 5 s), Celery beat.
- Assignment: strict FIFO from list head; find first idle worker whose capabilities include the job's handler (routing by handler, not job_type); if none, stop (head-of-line blocking). Assign: HSET active, worker processing, publish job:assigned, write ProcessingJob.worker_hostname. Concurrency 1 per worker.
- Completion: worker publishes done -> engine unassigns, HDEL handler, worker idle, publish job:completed, write ProcessingJob status/finished_at/last_error, dispatch next. Idempotent on double done (R14g EN6, EN8).
- Stale: heartbeat gap > 15 s (check every 2 s) -> stale, requeue its active jobs at back, publish reassigned. Heartbeat from stale worker -> idle. Deregister requeues current job. Startup recovery: workers offline/stale and active jobs of missing workers requeued; DB rows (BookCreationRequest QUEUED/PROCESSING, ProcessingJob queued/processing) not present in Redis re-enqueued (handlers pipeline / process_submission) (R14g EN17, EN18).
- Contract worth preserving (R14g): states idle/processing/stale/offline; capability routing; FIFO; requeue on worker death; DB recovery on start; idempotent completion; enqueue works while engine is down.
- Celery config: worker_max_tasks_per_child 50, max_memory_per_child 400000 KB, prefetch 1, acks_late; beat entries listed in R05 section 4.
- Engine testing: real Redis + Postgres, sleep-based, no mocks (R14g).

### 7.5 Failure modes (summary; details in 8)
Lost pub/sub message -> job stuck "processing" until stale/recovery; duplicate execution via engine + Celery or revived stale worker; broker/engine down -> inline processing in web request; worker killed mid-write (terminate revoke) -> partial book/assets; cancel ignored during persistence; source site unreachable -> DNS fallback chain then job retry; content unusable -> NEEDS_REVIEW not FAILED.

## 8 Issues

Sev: H/M/L. Ver: V = verified in code, U = unverified (report only).

| # | Issue | Sev | Ver |
|---|---|---|---|
| I1 | DNS-over-HTTPS call uses `verify=False` against 1.1.1.1 (resolution_support_network.py:130); poisoned answers feed direct-IP fetches (cert still verified by hostname) | M | V |
| I2 | Unsafe defaults: insecure SECRET_KEY fallback (settings.py:74), DEBUG on unless APP_ENV=production, EAGER default true outside production (settings.py:250), DRF default AllowAny, demo-user password committed as default (settings.py:108; value deliberately not copied), real admin email default | H | V |
| I3 | Anonymous endpoints (create/detail/status/confirm-candidate/action-links) protected only by UUID secrecy + 40/h throttle; action-links issues reader preview tokens/ downloads to anyone with the UUID; guests can see others' public submissions | H | V (AllowAny lines) |
| I4 | Two parallel dispatch mechanisms (engine pub/sub and Celery task) can run the same job; engine recovery re-queues jobs waiting in Celery broker; task_postrun publishes `done` for any Celery task with a first arg, marking engine workers idle and overwriting ProcessingJob.status (including user-cancelled jobs; Celery RETRY mapped to failed) | H | U |
| I5 | Engine race: two threads call dispatch; find_idle/assign not atomic; no leader lock so two engines double-dispatch; comment "single-threaded" is false | H | U |
| I6 | Pub/sub is fire-and-forget: lost assigned/done/register leaves job stuck forever (heartbeats keep worker "alive"); no ack/lease | H | U |
| I7 | Dispatch fallback runs the entire job synchronously in the request thread on ANY dispatch exception, which may have already enqueued the task -> double processing; runner only short-circuits SUCCEEDED/CANCELLED, not PROCESSING | H | V (fallback) / U (double) |
| I8 | Head-of-line blocking: one job with no capable worker blocks queue; stale/deregister requeue to back (order lost); stale workers never expire (no TTL), re-evaluated every 2 s forever; scan cost grows | M | U |
| I9 | `api.reassign_job` publishes `job:reassigned` which no worker listens to; `api.py` unreferenced; `get_engine_status` hard-codes running True; dead constants, duplicated helpers | L | U |
| I10 | exec()-composed facades (submissions.py:16 VERIFIED; curation, normalization, catalog_entries) hide dependencies, defeat static analysis | M | V |
| I11 | Test seam `legacy_scrape_overridden` changes production control flow (skips validity branches) | M | U |
| I12 | Job SUCCEEDED for unresolved title / duplicate / needs-review: job status is not outcome | M | U |
| I13 | Metadata-duplicate scan is O(N books) in Python with no source filter; near-duplicate rules written 4 times with different semantics (empty authors allowed in two, forbidden in two) | M | U |
| I14 | Global request reuse across users (D1): a user's request can attach to someone else's, sync overwrites dependents' review state/error; retry permission uses dependent's submitter on shared root | M | U |
| I15 | `fail_processing_job` (stale-exhausted) does not restore reprocess book.state -> book stuck PROCESSING (code has no book reference in the function body, VERIFIED by grep of lines 12-40: no book handling) | M | V |
| I16 | Cancel is cooperative with 4 check points; revoke(terminate=True) can kill worker mid-write; no transaction around persist/asset sync; old stored asset file deleted before new one saved | M | U |
| I17 | `sync_assets`: ValueError after setting book NEEDS_REVIEW triggers retries; final failure then restores previous_book_state overriding NEEDS_REVIEW; FAILED asset rows for missing optional cover; .png cover typed octet-stream | L | U |
| I18 | Stale recovery race: QUEUED jobs with empty task_id may be redispatched while queue_submission is between create and dispatch | M | U |
| I19 | Retry view: `.get(pk)` -> 500 for missing/non-visible (submissions.py:274 VERIFIED); malformed candidate_id -> 500; `can_manage_job` vs `can_manage_processing_records` divergence; bulk endpoints use visibility rules | M | V / U |
| I20 | Bulk retry: PermissionDenied not caught, aborts whole batch; URL intake catches only ValueError so later entries lost on DB/network error | L | U |
| I21 | `capture_source_page_metadata` swallows all errors silently and has DB side effect; enrich candidates swallows exceptions | L | U |
| I22 | Title resolver: empty catalog title scores 0.78 via `"" in query`; single close match (0.78/0.88) never auto-resolves; refresh crawl unbounded and synchronous in request path; up to 3 live fetches in-request | M | U |
| I23 | Substring semantics reject legitimate names (vol/part/row/road match inside names such as Volkov, Parthasarathi, Crowley); possible Unicode-form duplicates in constant lists (য়) mean silent match failures unless Bengali is NFC-normalized at one entry point | M | U |
| I24 | `format_book_info_html_ordered` mutates module-level label dicts (cross-request leakage) and discards unparsed lines; danda-split writes unescaped HTML into book_info (HTML injection of scraped text) | M | U |
| I25 | Audit coverage thin (3 verbs); no actor on cancel/delete/retry/reprocess/duplicate-resolve/stale recovery | M | V (R03 lists all writes) |
| I26 | Settings `refresh_max_pages` stored but `refresh_catalog_parallel()` called without it; curation run has no stale-task guard; inline fallback runs hours-long run in web request | M | U |
| I27 | Automation scheduler: check-then-create race; settings edit re-arms today_slot and can fire a second run same day; next date computed from last run creation date (drift); manual runs not locked against each other | M | U |
| I28 | Failed classification treats `duplicate` and `needs_review` as failed -> scheduled runs retry duplicates every 6 h | M | U |
| I29 | SSE: one worker + one Redis connection per manager, broadcasts all events with no filtering | L | U |
| I30 | List views: catalog entries slow path in memory; incomplete-check loads all books; no pagination class; N+1 risk | L | U |
| I31 | BookSubmission.save() side-effect creates UserBook and extra SELECT per save; legacy persist revives soft-deleted book by title only (no author check) | M | U |
| I32 | Hard delete of a soft-deleted request has unknown cascade; two-step delete semantic is implicit | L | U |
| I33 | Two ingestion models (ProcessingJob/submission path and CuratedBookDocument CLI path); duplicated automation/recovery across ingestion and processing apps; ingestion imports processing models (circular coupling) | M | U |
| I34 | Dead code: create_local_resolution_attempt, classify_incoming_book, find_existing_matching_book, persist_scraped_book legacy path, `_generate_residual_heading`, `skipped_deleted`, "requeued" overview status, unused quality gate in runtime, MIDSTRING_ROLE_LABELS always empty, `build_retry_payload` ignored args | L | U |
| I35 | Engine and Celery share Redis DB 0; engine key literal strings repeated; handlers hash leaked for cancelled/deleted queued jobs | L | U |

## 9 Keep / change / drop for a rebuild

KEEP (behavioural contract)
- Submission vs processing-job split with an explicit outcome field on the request (not just job success). Reason: UI needs ready/needs-review/duplicate/failed independent of job mechanics.
- Request-level reuse concept (attach identical requests to one canonical work), but scope it (same user or explicit "attach", never silently cross-user) and keep a single-level tree. Reason: avoids duplicate scrapes.
- Title -> candidate list -> human confirm for anything not an exact match; top-3 candidates with scores; candidate selection record. Reason: safety with fuzzy Bengali titles.
- Source catalog index + live-page enrichment; URL allow-list and normalization rules; the display-title "Title - Author" split rules.
- Three-stage duplicate detection ordering (exact URL, exact title+authors, fuzzy metadata with human review) plus the unused edition-aware classifier as a basis for NEW_EDITION. Reason: correctness of library.
- Normalization data tables (roles, labels, name-rejection lists, front-section/dedication/body patterns, chapter regexes, thresholds) as versioned data + golden tests; port verbatim lists from R04 section 4 and metadata.py:103-483. Reason: this is hard-won domain knowledge for Bengali sources.
- Quality gate (no readable body), required assets HTML+EPUB, status "unfinished" derivation, reprocess flow with state restore.
- Job semantics: max 3 attempts, cancel/resume, stale detection (20 min), restore reprocess state on every terminal path, per-job log lines.
- Curation run + automation schedule concept (frequency set, daily time, mode pending/all, 6 h failure cooldown) and catalog refresh as a singleton job.
- Engine contract (R14g): capability routing, FIFO, idle/processing/stale/offline, requeue on worker death, DB recovery, idempotent completion.
- Activity snapshot (cheap polling), job logs, duplicate review queue, bulk operations with skipped-counts responses.

CHANGE
- Replace Celery + Redis pub/sub hybrid with one durable queue (e.g. Postgres-backed or broker with acks/leases, visibility timeout, idempotent job keys). Single dispatch path; no inline fallback in request handlers; no fire-and-forget assignment. Reason: I4-I8.
- Replace exec() facades with real modules and explicit dependencies; drop test-seam control flow. Reason: I10, I11.
- Make pipeline stages explicit, idempotent, transactional where possible, with cancel checks between all stages and atomic asset swap (write new then replace). Reason: I16-I17.
- Job result vs outcome: separate "executed" from "outcome"; add explicit statuses for duplicate and needs-review.
- Authorization: default deny; anonymous intake only if product requires (invite-only suggests no); opaque signed tokens for preview/downloads instead of UUID secrecy; unify visibility and manage rules; return 404 not 500; audit every state-changing action with actor. Reason: I2, I3, I19, I25.
- Duplicate detection: one implementation, indexed (normalized title, trigram/author tables), edition-aware, source-scoped. Reason: I13.
- Normalize Bengali (NFC + nukta composition) at a single entry point before any matching; replace substring checks with token-boundary checks where names collide (vol, part, road). Reason: I23.
- Escape all scraped text inserted into HTML; make label tables immutable. Reason: I24.
- Apply refresh_max_pages; add stale-task guard to runs; make scheduler lock-protected and slot-based (store next_due), skip `duplicate`/`needs_review` from auto-retry. Reason: I26-I28.
- Pagination on all list endpoints; SSE replaced by one shared fan-out (or WebSocket/long poll) with per-user filtering.
- Configuration: required secrets with no defaults, no demo password in code, explicit environment profile.
- DNS/DoH/direct-IP fallback: drop or make opt-in; if kept, no verify=False.
- Lifecycle: add TTL/cleanup for logs, attempts, stale engine entries, expired preview sessions.

DROP
- Engine management API (`api.py`), `ENGINE_STATE`, beat-based pseudo-worker heartbeat, duplicate heartbeat paths, dead constants, `reassign_job`.
- Legacy persist path (`persist_scraped_book`, MetadataVersion writes), legacy config import / process_legacy_batch, create_local_resolution_attempt, `_generate_residual_heading`, skipped_deleted, "requeued" status.
- Hard-delete cascade by second DELETE call (use explicit purge with retention policy).
- Two parallel ingestion models: unify submission/job path and curated-document batch path.
- SubmissionRateThrottle design tied to anonymous creation (replace with per-user quotas).

## 10 Open questions

1. Should anonymous/public submissions and guest preview tokens exist in the rebuild, given the app is invite-only? (Legacy allows them; reason unknown.)
2. Is the "inline fallback when the queue is down" behaviour ever wanted, or should intake return 503/queued state?
3. What are the exact thresholds and algorithm of `texts_are_similar` and `normalize_text` (pipeline/scraper_support/text.py), and the scraping limits (DEFAULT_SCRAPE_LIMITS)? Needed to reproduce 0.88 tier and duplicate fuzziness (UNVERIFIED, not read).
4. What does `refresh_catalog_parallel` (apps.processing) do and does it honour max_pages? What is BookCreationRequest/"pipeline" handler (second job type in engine) and is it a separate book-creation flow to merge?
5. Who may submit requests in the rebuild (any reader, operator only)? Is request reuse across users acceptable?
6. Reader-facing outcome of NEEDS_REVIEW and DUPLICATE: who resolves, and does a reader see these states?
7. Should DuplicateReview support merge (status exists, never produced) and NEW_EDITION grouping (BookGroup)?
8. Is category-based "unfinished" tagging (keywords unfinished/অসম্পূর্ণ) an authoring convention on the source site that must be preserved?
9. Retention policy for submissions/logs/attempts and for generated assets of deleted books?
10. Does the source site require login (SOURCE_SITE_EMAIL/PASSWORD, auth-state file) for full content, and how are those credentials to be held?
11. Expected scale (catalog size, books/day, workers) to choose queue tech; legacy assumptions: 5 workers, 1 job each, 20 min stale window.
12. Is scheduled automation needed at all, or only manual runs? (Defaults to disabled in legacy.)
13. Behaviour of `PermissionDenied`/`CanManageProcessing` and scope names (processing.manage) - defined in apps.common, not read here.
