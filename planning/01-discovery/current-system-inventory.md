# Current system inventory (archived legacy app)

Status: DRAFT · Source: analysis digests [D1..D7](../_replan/analysis/D7-ops-schema.md) and [X1](../_replan/analysis/X1-issues-register.md), which read the code in `archive/` (read-only). Claims keep the digests' verified/unverified marks. Nothing here was re-run. Frontend line counts are from the earlier survey (2026-11-17).

## Product

A private, invite-only Bengali ebook library. One operator mirrors a single external source website, builds EPUB, HTML and cover assets through a scrape, curate, build pipeline, and publishes into a catalog. Invited readers browse, keep a shelf, read in a web reader (highlights, notes, bookmarks, progress), download and send to Kindle. A superadmin invites users and grants scoped rights ([X2](../_replan/analysis/X2-capability-map.md)).

## Stack and runtime (D7 section 2)

Django 5.2 with DRF, Celery and Redis, PostgreSQL 16, React 18 with Vite, Docker Compose. Containers: postgres, redis, backend-init (one-shot migrate and seed), backend (gunicorn), worker, processing-worker, engine (custom Redis job coordinator), beat, frontend (nginx). Edge: host-level nginx and certbot, outside Compose. No memory or CPU limits and no Redis `maxmemory`, though docs claimed them. Backups: none. Deploy: SSH scripts, builds on the host, full down then up. Host move: a 15-file, ~2k-line bash toolkit.

## Backend structure and size

| App | Responsibility | Approx. lines (non-migration) |
|---|---|---|
| accounts | User, login, password links, TOTP, managed users | 1.7k |
| catalog | Book, Contributor, Series, Category, UserBook, Kindle send, exports | 3.9k |
| ingestion | Scraper, normalization, EPUB/HTML builders, submissions, jobs, curation, catalog sync | 20.7k |
| processing | UI-facing projection of ingestion state (BookRecord, BookCreationRequest, sync, projections) | 8.5k |
| access | PermissionGrant, preview and reading sessions, bookmarks, highlights, opening records | 2.0k |
| common | Base models, permissions, audit log, saved filters, text utils | 2.3k |

Cycles: catalog and ingestion, ingestion and processing, common and the domain apps (imports in both directions; X1-105).

## Data model (D7 section 4)

43 models over 58 migrations (accounts 1, catalog 19, access 6, ingestion 11, processing 4, common 2, plus framework). Two parallel book pipelines (ingestion and processing) and a three-way record split of one book (BookRecord, curated document, Book). Lifecycle state stored in at least seven places. Postgres triggers keep `book_creation_state` in step; UI projection payloads and domain version counters are stored in the system of record. Full book HTML duplicated in Book, curated JSON, curated section rows and asset rows. Enums are free text with `choices`, no CHECK constraints.

## Permissions

12 scopes (`submit:create`, `preview:html`, `read:durable`, `read:once`, `download:file`, `metadata:edit`, `physical_books:view`, `processing:manage`, `access:manage`, `source_records:view`, `send:kindle`, `admin:full_control`), resolved by global, book, category or author grant; staff and superuser bypass; "ownership" via My Books ([X3](../_replan/analysis/X3-roles-actions.md)).

## HTTP surface

`/api/auth/*`, `/api/catalog/*`, `/api/ingestion/*`, `/api/processing/*` (state, card, table, stream, sync, automation), `/api/access/*` (grants, downloads, Kindle, reader launch and token routes, bookmarks, highlights, notes, progress), `/api/health`, `/api/csrf`, `/api/saved-filters`. Two SSE streams with different wire formats (D5 section 7).

## Frontend

React SPA, 72,496 lines in `src/` of which 35,032 are an embedded EPUB reader runtime; a further 32,899 lines of a vendored third-party reader in `public/epub-reader` (byte-for-byte duplicate code, D6 section 5.1). 20 pages, 10 feature folders, 64 CSS files (1.8k-line `dark-mode.css`). Three separate client-side permission models, no route guards (X1-008, X1-014).

## Scripts and tests (D7 sections 6 and 8)

Throwaway debuggers left in the repo root (`check_books*.py`, `check_gita.py`, `check_refs.py`, `diagnose_curation.py`). About 480 backend test functions, frontend unit tests, 42+ Playwright journeys (need the full live stack, one worker), a 300-URL regression harness and an EPUB structure audit. No gold corpus of expected outputs. Plain console logs, no metrics or tracing; `/api/csrf/` doubled as health check.

## Key defects (X1 ids)

| Area | Defect | X1 id |
|---|---|---|
| Security | Any user can add a book to My Books and become "owner", bypassing every gate | X1-001 |
| Security | Insecure defaults (secret key, DEBUG, AllowAny, committed demo password, printed admin password) | X1-002, X1-013 |
| Security | Reader token in URL, sole credential for content routes, 2 h, not revoked | X1-003 |
| Security | Scraped HTML stored and served unsanitised; autoescape off | X1-004 |
| Security | Anonymous submission endpoints guarded only by UUID secrecy | X1-006 |
| Security | Demo login by GET, credential-less shared account | X1-007 |
| Security | `is_staff` and `admin:full_control` wildcards | X1-008 |
| Security | Draft, rejected and failed books listed to every user; deleted books still readable | X1-009, X1-010 |
| Security | `/media/` served unauthenticated by nginx | X1-011 |
| Source | Scraper POSTs "mark complete" to the source site | X1-012 |
| Data | Whole book stored in several rows; non-atomic persistence; destructive re-scrape | X1-027, X1-028, X1-035 |
| Data | Dual-written state, triggers overriding writes, stored UI projections | X1-030 |
| Sync | Empty incomplete list resolves every record; re-sync overwrites workflow state | X1-024, X1-026 |
| Correctness | Job status is not outcome; success reported for failures | X1-031 |
| Correctness | Bengali word lists lost vowel signs; substring title matching | X1-046 |
| Reliability | Redis pub/sub engine with Celery and an inline fallback; stale recovery done twice | X1-065..X1-067, X1-106 |
| Reader | Progress and bookmark routes in two families with different access rules; read-once incoherent | X1-020, X1-056..X1-058 |
| Operability | No backups, no limits, deploy does down then up, no CI | X1-080, X1-083 |

Register totals: 136 issues across security, data integrity, correctness, reliability, operability, UX, accessibility, maintainability and test gaps.
