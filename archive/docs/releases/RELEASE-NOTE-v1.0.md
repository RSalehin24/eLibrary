# v1.0 — Rainy Forest

**Bangla Library Platform**
Release Date: May 29, 2026

---

## Overview

v1.0 Rainy Forest is the inaugural release of the Bangla Library Platform — a full-stack system for scraping, structuring, and serving Bengali (and English) ebooks. The platform ingests books from a source site, produces production-quality EPUB and HTML files, and delivers them through a searchable library with granular access control, an in-browser reader, and Kindle delivery.

This release ships 7 Docker services, 20+ user-facing pages, a complete processing pipeline with real-time UI updates, 11 permission scopes, TOTP two-factor authentication, and 42+ end-to-end browser tests.

---

## Architecture

| Service | Role |
|---------|------|
| **PostgreSQL 16** | Primary database |
| **Redis 7** | Celery message broker and result backend |
| **Django Backend** | REST API, authentication, book management, EPUB generation |
| **Celery Worker** | General task queue — book creation pipeline, EPUB generation, Kindle delivery |
| **Processing Worker** | Dedicated queue — catalog sync, incomplete book detection, automation tasks |
| **Celery Beat** | Scheduler for periodic catalog sync and incomplete-check automation |
| **React Frontend** | SPA with Vite dev server (dev) or Nginx (production) |

A one-shot **backend-init** container runs migrations and seeds the superadmin on first boot.

---

## Features

### Book Ingestion & EPUB Generation

- **Automated scraping** pulls book content, cover images, metadata, table of contents, and chapters from a Bengali ebook source site.
- **Structured EPUB output** with a fixed page order: cover, title page, book information, dedication, front sections, table of contents, chapters, and end sections.
- **Programmatic dark-mode cover generation** when no source cover image exists.
- **Language detection** (Bengali / English) with correct field labels applied throughout the EPUB.
- **Smart book information extraction** — title, author, translator, editor, publisher, series, category, ISBN, price, edition — parsed from multiple HTML formats (slash-separated, dash-separated, colon-separated, positional).
- **Dedication isolation** — dedication text (keyword: `উৎসর্গ`) is separated from front matter and rendered on its own page.
- **Front-matter handling** — unnamed prose renders without a heading and appears in the nav as `পূর্বকথা` (Bengali) or `Preliminary Note` (English).
- **Nested TOC preservation** — sub-chapter structure is maintained in both the EPUB NAV and the printed table of contents.
- **Multi-page TOC support** — books with spanning table of contents across multiple source pages are fully supported.
- **Duplicate TOC suppression** — inline plain-text TOCs are dropped when a real linked TOC exists.
- **Empty chapter detection** — chapters that fail content fetch are tracked and surfaced in the book detail page.

### Book Processing Pipeline

- **URL-based submission** — users submit a source book URL and the backend runs scraping, resolution, and EPUB creation as a Celery pipeline.
- **Full lifecycle management** — `initial → queued → processing → created` with pause, resume, retry, and delete at every stage.
- **Duplicate detection** — surfaces possible matches before creating a new book. Resolution options: create as new, create as new edition, or confirm duplicate.
- **Multi-page TOC pipeline** — special handling for books whose source table of contents spans multiple pages.
- **Manual book creation** — operators can create catalog entries without a source URL, attaching metadata, cover images, and file assets directly.
- **Reprocessing** — bulk and per-book reprocessing of existing books with active and history tracking, stop/resume/delete controls.
- **Real-time UI updates** — Server-Sent Events push card-level invalidations to the frontend. Cards update without page refresh.
- **Processing automation** — configurable daily scheduler for catalog sync and incomplete book checks with start/pause/resume/stop controls.

### Catalog Sync

- **Source catalog reconciliation** — compares source site book listings against the local database.
- **Manual and automated sync** share the same runtime, preventing parallel runs.
- **Pause and resume** with durable page-level checkpoints.
- **Incomplete book tracking** — a dedicated automation run identifies books still marked unfinished on the source site and queues them for reprocessing.
- **Post-sync request creation** — creates processing requests only for catalog records that have never been processed.

### Library & Catalog

- **Searchable library** — full-text search by title, book ID, and contributor name.
- **Advanced filtering** — by contributor (author, translator, editor, publisher), series, category, ownership, and record type (digital/manual).
- **Infinite scroll** with server-side pagination.
- **Saved filters** — persist filter presets per user and reapply them.
- **CSV and PDF export** — server-side and client-side generation for Library and Manual Books pages.
- **My Books** — personal bookshelf with ownership toggle on any book card.
- **Book detail page** — hero section with cover, full metadata, source records, extracted entities, dedication, table of contents, empty chapter warnings, and raw provenance JSON.
- **Catalog property pages** — dedicated pages for Categories, Series, Writers, Translators, Editors, and Publishers, each showing catalog codes, book counts, and creation dates.
- **Manual books** — inline composer form for physical book entries with category and contributor autocomplete.

### In-Browser EPUB Reader

- **Full-screen reader** powered by epub.js with TOC sidebar, previous/next navigation, and chapter bar.
- **Reading settings** — adjustable font size and three background themes: White, Sepia, Night.
- **Bookmarks** — create, view, and delete bookmarks from within the reader and from the book detail page.
- **Highlights and notes** — highlight text in five colors (yellow, green, blue, pink, underline), add notes to highlights, and create standalone quotes.
- **App header toggle** — show or hide the application navigation while reading.
- **Reading progress tracking** — last location, progress percentage, and last opened timestamp per user per book.
- **Token-based access sessions** — time-limited preview sessions with EPUB download, HTML preview, and bookmark endpoints.

### My Notes

- **Centralized notes dashboard** with four tabs: Bookmarks, Highlights, Notes, and Quotes.
- **Two-column layout** — book sidebar with item counts + items panel with search, color filter, and delete.
- **Note editing** — edit highlight notes, change colors, and manage tags from a single interface.
- **Reader links** — jump directly to the reader at a bookmark or highlight location.

### Kindle Delivery

- **Send to Kindle** from Home, My Books, Kindle Sent, and Book Detail pages.
- **Multiple Kindle email addresses** — users configure one or more `@kindle.com` addresses in their profile.
- **Kindle Sent page** — dedicated page tracking all books sent to Kindle with send date, filters, and re-send capability.
- **SMTP delivery** via Brevo API, SMTP, or Django console backend.

### Authentication & Security

- **Email-based login** — no usernames; users sign in with email and password.
- **Invite-only account creation** — superadmin creates users with password setup links.
- **TOTP two-factor authentication** — mandatory 2FA gate for flagged accounts. Users are forced through `/two-factor-setup` before accessing any protected route.
- **Self-service password reset** — 6-hour link expiry; newer requests invalidate older links.
- **Setup email resend** — onboarding-pending accounts can have setup emails resent with automatic link invalidation.
- **Session-based auth** — Django session cookies with CSRF protection.
- **Secure production cookies** — `Secure`, `SameSite=Lax`, `HttpOnly` flags with `X-Forwarded-Host` support.

### Access Control

- **11 permission scopes**:

  | Scope | Purpose |
  |-------|---------|
  | `submit:create` | Submit book creation requests |
  | `preview:html` | Preview HTML version of books |
  | `read:durable` | Unlimited reader access |
  | `read:once` | Single-open reader access |
  | `download:file` | Download EPUB files |
  | `send:kindle` | Send books to Kindle |
  | `metadata:edit` | Edit book metadata |
  | `processing:manage` | Access processing pages |
  | `access:manage` | Manage user permissions |
  | `source_records:view` | View source record data |
  | `admin:full_control` | Full administrative access |

- **Scoped grants** — permissions can target specific books, categories, or contributors.
- **Time-limited grants** — optional expiry dates on permission grants.
- **Capability-gated navigation** — sidebar items appear or hide based on the user's effective permissions.
- **Read Once enforcement** — single-open access tracked via `BookOpeningRecord` with reader session gating.

### User Management

- **Users & Access page** (superadmin) — create, edit, and delete managed users. Assign account scopes. Suggest passwords. Resend setup emails.
- **Grant management** — create and delete scoped permission grants targeting books, categories, or contributors.
- **Profile page** — edit name, upload profile image, change password, manage Kindle emails, and configure TOTP (setup, disable, copy provisioning URI).

### Responsive Design

- **Mobile navigation** — icon-based side panel for phone viewports.
- **Responsive processing pages** — all pipeline cards and tables adapt to narrow screens.
- **Responsive reader** — full-screen EPUB reader works on mobile devices.
- **Responsive property pages** — catalog tables stack and scroll on small screens.

### Testing

- **42+ Playwright E2E specs** covering:
  - Authentication flows (login, password reset, TOTP setup, forced 2FA, expired links, create password)
  - Processing pages (catalog sync, create pipeline, on-hold actions, incomplete automation, duplicate resolution, SSE notifications, card isolation)
  - Access page (user management, permission grants, invitations, validation, pagination)
  - Library, catalog, manual books, book detail, profile, home filtering
  - Responsive layout tests for navigation, library, manual books, profile, processing, property pages, and reader
- **Backend pytest suite** covering:
  - Access: Kindle validation, HTML downloads, reader sessions, bookmarks, highlights, notes
  - Ingestion: 22 test files covering scraper, queue, resolution, normalization, stale recovery, automation, catalog recreation, asset sync
  - Processing: state payloads, automation, catalog sync, dispatch, stale recovery, checkpoint, UI version, DB consistency
  - Catalog: references, manual books, exports, contributor filters
- **Frontend unit tests** for activity tracking, request formatting, and job filter helpers.
- **300-book EPUB structure regression harness** with resumable state and structural invariant assertions.

### Deployment

- **Docker Compose** for both local development and production.
- **One-command deployment** via `deploy/scripts/deploy.sh`.
- **Nginx + Certbot** for TLS at the edge.
- **Celery workers** split across dedicated queues (general + processing) for isolation.
- **Celery beat** for scheduled automation (catalog sync, incomplete checks).
- **Database migration tooling** for moving data between environments with dry-run support.
- **Log streaming** — dedicated scripts for viewing local and remote logs per service.

---

## Pages

| Route | Page | Access |
|-------|------|--------|
| `/login` | Login | Public |
| `/reset-password` | Password Reset Request | Public |
| `/reset-password/confirm` | Password Reset Confirm | Public |
| `/create-password` | Create Password (invite) | Public |
| `/two-factor-setup` | TOTP Setup | Protected (forced) |
| `/` | Landing / Home Redirect | Protected |
| `/home` | All Books (superadmin) | Protected |
| `/my-books` | My Books | Protected |
| `/library` | Library (table view) | Protected |
| `/books/:slug` | Book Detail | Protected |
| `/reader` | EPUB Reader | Protected (token) |
| `/categories` | Categories | Protected |
| `/series` | Series | Protected |
| `/writers` | Writers | Protected |
| `/translators` | Translators | Protected |
| `/editors` | Editors | Protected |
| `/publishers` | Publishers | Protected |
| `/manual-books` | Manual Books | Protected |
| `/catalog` | Catalog Processing | Protected (processing:manage) |
| `/create` | Create Processing | Protected (processing:manage) |
| `/on-hold` | On Hold Processing | Protected (processing:manage) |
| `/incomplete` | Incomplete Processing | Protected (processing:manage) |
| `/multipage-toc` | Multi-Page TOC Processing | Protected (processing:manage) |
| `/reprocessing` | Reprocessing | Protected (processing:manage) |
| `/access` | Users & Access | Protected (access:manage) |
| `/profile` | Profile | Protected |
| `/notes` | My Notes | Protected |
| `/kindle-sent` | Kindle Sent | Protected |

---

## Key Commands

| Command | Purpose |
|---------|---------|
| `local/scripts/generate-env.sh` | Generate local environment files |
| `local/scripts/dev.sh up` | Start the full local Docker stack |
| `tests/scripts/test-all.sh` | Run the complete test suite |
| `tests/scripts/test-backend.sh` | Run backend pytest only |
| `tests/scripts/test-frontend-unit.sh` | Run frontend unit tests only |
| `tests/scripts/test-e2e.sh` | Run Playwright E2E tests only |
| `tests/scripts/seed-e2e-data.sh` | Seed deterministic E2E data |
| `tests/scripts/verify.sh --repeat 3` | Verify the full suite N times |
| `deploy/scripts/deploy.sh` | Deploy to production |
| `logs/scripts/show-logs.sh backend remote` | Stream remote backend logs |

All scripts support `-h` / `--help`.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Django 5.2 + Django REST Framework (Python 3.12) |
| Task Queue | Celery 5.6 + Redis 7 |
| Frontend | React 18 + Vite 5 (JavaScript) |
| Database | PostgreSQL 16 |
| 2FA | django-otp (TOTP) |
| Email | Brevo (Sendinblue) via django-anymail |
| Containerization | Docker Compose |
| Edge / TLS | Nginx 1.27 + Certbot |
| Testing | pytest, node --test, Playwright |

---

## Known Limitations

- No automated CI/CD pipeline — tests are run manually via shell scripts.
- EPUB reader does not support annotation export.
- No rate limiting on API endpoints.
- Catalog sync is single-threaded per run.
- Manual book creation does not support bulk import.

---

## What's Next

- CI/CD integration with GitHub Actions.
- Bulk manual book import via CSV.
- Annotation export (highlights, notes, quotes).
- Rate limiting and API throttling.
- Performance optimizations for large catalog syncs.
- Accessibility audit and WCAG 2.1 AA compliance.

---

## License

This project is licensed under the [GNU Affero General Public License v3.0](../LICENSE). Derivative works and network-hosted deployments must release their source code under the same license.

---

## Credits

Built with Django, React, Celery, PostgreSQL, Redis, and Docker.
EPUB processing powered by ebooklib and BeautifulSoup.
Browser testing powered by Playwright.
