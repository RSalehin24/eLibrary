# Current system inventory (branch `main`, commit 08fc99f)

Status: DRAFT · Source: code survey 2026-11-17 (not runtime-verified)

## Stack

Django 5.2 + DRF, Celery + Redis, PostgreSQL 16, React 18 + Vite, Docker Compose, Nginx + Certbot.

## Backend apps and size

| App | Responsibility | Approx. lines (non-migration) | Notes |
|---|---|---|---|
| accounts | User, login, password links, TOTP, managed users | 1.7k | invite-only; `kindle_emails` JSON on User |
| catalog | Book, Contributor, Series, Category, BookGroup, UserBook, UserBookKindleSend, exports | 3.9k | Book row stores `main_content_html`, `toc`, `content_items` JSON inline |
| ingestion | scraper, normalization, EPUB/HTML builders, submissions, jobs, curation, catalog sync | 20.7k | 2.3k-line `book_manifest.py`; 1.5k-line segment extraction |
| processing | UI-facing projection of ingestion state (BookRecord, BookCreationRequest, sync, UI projections) | 8.5k | duplicates ingestion state |
| access | PermissionGrant, preview sessions, reading sessions, bookmarks, highlights, opening records | 2.0k | CFI anchors |
| common | base models, permissions, audit log, saved filters, text utils | 2.3k | imports domain apps (inverted dependency) |

## Coupling (cross-app imports)

`ingestion→common` 30 · `processing→ingestion` 21 · `catalog→common` 21 ·
`ingestion→catalog` 20 · **`catalog→ingestion` 12** · `common→ingestion` 7 ·
`common→catalog` 6 · `access→catalog` 8 · others ≤ 4. Cycles: catalog↔ingestion,
ingestion↔processing, common↔(access, catalog, ingestion).

## Permission scopes (12)

`submit:create preview:html read:durable read:once download:file metadata:edit
physical_books:view processing:manage access:manage source_records:view
send:kindle admin:full_control`. Resolution = global, book, category, or author-contributor grant; staff/superuser bypass.

## HTTP surface

`/api/auth/*` (session, login, demo-login, profile, password-reset, users, 2fa) ·
`/api/catalog/*` (books, export, categories, series, writers/translators/compilers/editors/publishers, manual-books, details) ·
`/api/ingestion/*` (submissions, jobs, catalog entries, curation runs, duplicate reviews, activity) ·
`/api/processing/*` (state, card, table, stream, sync, automation) ·
`/api/access/*` (grants, references, downloads, send-to-kindle, reader launch, reader token endpoints, bookmarks, highlights, me/notes, me/reading-progress) · `/api/health`, `/api/csrf`, `/api/saved-filters`.

## Frontend

React SPA, ~72k lines of which ≈ 40k are a vendored third-party EPUB reader runtime
(`embedded-reader`, `public/epub-reader` v1.1). 21 pages, 9 feature folders, 3 CSS
bundles (largest: 1.8k-line `dark-mode.css`).

## Hygiene findings

- Ad-hoc scripts in backend root: `check_books1-5.py`, `check_gita.py`, `check_refs.py`, `diagnose_curation.py`.
- Hardcoded per-book guard (`last_chapter_title` for one title) in structure completeness.
- Three divergent duplicate-book matchers, each scanning books in Python.
- Search is `icontains` joins over four tables; no index support found.
- Dead letters: redirects for retired `/processing-*` routes.

## Test assets

≈ 480 backend `test_` functions, frontend unit tests, 42+ Playwright journeys,
`regression_curate_300` harness + `epub_structure_audit` (structure only).
**No gold corpus of expected outputs.**
