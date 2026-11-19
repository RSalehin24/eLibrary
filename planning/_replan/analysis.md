# Analysis of the archived application (first-hand reading)

Status: SUPERSEDED

> **SUPERSEDED (2026-11-19).** Written before the owner's decisions D-27 (5 services, no gateway), D-28 (reader renders and serves the whole book) and D-29 (small scale). The current architecture is [new-architecture.md](new-architecture.md); the analysis is in [analysis/](analysis/). Kept only as history of an earlier, shallower pass.


Read directly by the assistant (not delegated): models of `access`, `accounts`, `catalog`, `ingestion`, `processing`; `common/permissions.py`; `access/views/reader.py`; `processing/service_modules/request_processing_pipeline.py`; `ingestion/services/submission_modules/processing_job_runner.py`; `ingestion/pipeline/curated_pipeline.py`; `processing/source.py`; the v1.0 release note, processing use cases and authentication-flow docs. Paths are under `archive/app/backend/apps` unless noted. Everything below was read, not inferred, except where marked *unverified*.

## 1. What the product is

A **private, invite-only Bengali ebook library** fed from one external source website. An operator imports books from that site (scrape → structured EPUB/HTML); a few invited readers browse, read in the browser, annotate, and send books to their Kindle. Nothing is public: every catalog endpoint requires login (all 15 catalog views use `IsAuthenticated` or a scope permission), and the frontend wraps every route but login/reset in `ProtectedRoute`.

## 2. The operator console is the heart (and is built twice)

The console workflow: **mirror the source catalog → turn records into creation requests → run each request through the pipeline → handle exceptions** (paused, failed, duplicate, deleted), with two schedulers (catalog sync, incomplete re-check) sharing one runtime.

Verified duplication at the data level:

| Concept | In `ingestion` | In `processing` |
|---|---|---|
| Mirror of the source listing | `SourceCatalogEntry` (url, title, author_line, raw_data) | `BookRecord` (url, name, category, writer, translator, composer, publisher, state) with FK to `SourceCatalogEntry` |
| Sync state singleton | `SourceCatalogRefreshState` | `ProcessingSyncState` (page_index, counts, remote_pages) |
| Automation settings | `CatalogAutomationSettings` (daily…half-yearly, mode, max pages) | `ProcessingAutomationSettings` (kind catalog/incomplete, interval, time) |
| Unit of work | `BookSubmission` → `ProcessingJob` (10 + 5 states) | `BookCreationRequest` (8 states) |
| Entry to the pipeline | `process_submission_job` | `_process_request_once` |

Both entries call the same pipeline functions (`curate_book`, persist, build). The console UI uses only the `processing` path; the frontend never calls `/ingestion/submissions` (grep of `frontend/src` finds nothing), while that endpoint family still exists with several `AllowAny` views (*their runtime exposure unverified*). The `submission` path is effectively a superseded earlier design that was never removed; `BookRecord.book_creation_state`, `BookCreationRequest.state`, `BookSubmission.status`, `ProcessingJob.status` and `Book.state` all track "where is this book" in five places.

The pipeline itself: `processing/source.py` wires `curate_book` (scrape with a disk page cache and a heartbeat thread, build a manifest, extract entities/sections, classify structure, validate → VALIDATED / REVIEW_REQUIRED / INVALID), then persist and build EPUB/HTML. A request that is not VALIDATED goes to **Failed** with "requires review"; `force_generate` overrides. Duplicate checks run by exact source URL and by metadata similarity. Scrape limits differ per path (e.g. 48 nodes/depth 3 vs unlimited/depth 6).

## 3. Access model

- `PermissionGrant(user, scope, optional book|category|contributor, expiry, is_active)`; 12 scopes. Superuser or staff bypasses everything; `admin:full_control` satisfies any scope.
- **Owning a book bypasses grants.** `UserBook` ("My Books") makes `user_owns_book` true, which allows reading, download, Kindle and preview for that book, and ownership is also created automatically when a user's submission is linked to a book.
- `read:once` is enforced by one `BookOpeningRecord` per (user, book): the second launch is refused, but nothing limits what happens during the 2-hour session.
- Cover visibility equals reader-launch permission (`user_can_view_book_cover`), so covers are protected too.
- `common/permissions.py` imports `access` and `catalog`: authorization is not independent of the catalog (grant targets are catalog rows; category and contributor grants are resolved by querying catalog tables).

## 4. Reader (verified)

`POST /access/books/<slug>/reader-launch/` (login, scope checks, read-once record) creates a `PreviewAccessSession` with a 32-byte URL-safe token and a 2 h expiry, renewed on each launch. The token is the credential for `AllowAny` endpoints: manifest (which **inlines that user's reading session, bookmarks and highlights**), the full EPUB (inline `FileResponse`), any single EPUB entry, and the HTML. So anyone holding the token URL gets the whole book and the user's annotations until expiry; read-once and "no download" cannot be enforced against a determined reader.

## 5. Data placement

`Book` stores `main_content_html`, `book_info_html`, `dedication_html`, `toc`, `content_items` and raw scrape payloads as columns, alongside separate `CuratedBookDocument` / `CuratedSection` rows holding the same material as JSON/HTML with evidence and confidence, plus `GeneratedAsset` files. The catalog row is therefore heavy and the same book content exists in up to three forms. Book catalog codes, slug and normalized title are generated in `save()`.

## 6. Observations that matter for the service split

1. The weight of the system is the **source mirror + request workflow + per-book pipeline** (≈ 29k of ≈ 39k backend lines), not the library. These are two different concerns: *deciding what to import and tracking it* (long-lived, console-driven, stateful) versus *building one book* (CPU/IO-bound, deterministic given a snapshot). The legacy mixed them, then duplicated the first one.
2. Authentication and authorization are small (≈ 3.6k lines together) and tightly coupled to catalog grant targets.
3. The reading side is small (≈ 2k lines) but has the weakest security model.
4. The product is entirely private; "public search and preview" in the earlier plan (D-12) is **new**, not inherited.
5. Reading state (progress, bookmarks, highlights, notes), the shelf (`UserBook`) and Kindle sends are all per-user data keyed by book.

## 7. Not yet read (so not claimed)

Catalog search and filter code; export generation; manual-books flows; the EPUB builder internals; the frontend processing store and SSE mechanics; the Celery engine (`engine/`); notes API; the Kindle mail code; real data volumes (none in the repo).
