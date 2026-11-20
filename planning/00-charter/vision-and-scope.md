# Vision and scope

Status: DRAFT

Basis: [new architecture brief](../_replan/new-architecture.md), [owner requirements](../_replan/owner-requirements.md), decisions D-03, D-12, D-26, D-28, D-29, D-31, D-32 in [DECISIONS](../DECISIONS.md). Replaces the v1 text (7-service plan, legacy migration).

## Vision

A calm, minimalist, trustworthy **private, invite-only Bengali ebook library**. Invited people read in a first-class reader, keep their place and notes, and send books to a Kindle. A small operator team grows the library from one source website through one pipeline and publishes only what has passed review. Visitors without an account can see only public browse/search metadata, covers and summaries (D-34); preview text and reading need sign-in.

## Users

| Persona | Needs | Main surfaces |
|---|---|---|
| Visitor (no account) | Find a book, see its metadata, cover and summary, decide to ask for an invite | Library (public), Book detail |
| Reader (role `reader`) | Browse, read, keep progress, bookmarks, highlights, notes, shelf, Kindle send | Library, Book detail, Reader, Settings |
| Operator (role `operator`) | Mirror the source, create requests, review duplicates, run builds, watch jobs, rotate the source cookie | Import workspace |
| Catalog manager (scope `manage_catalog`) | Edit metadata, unpublish or delete books (no approval step, D-49) | Book detail (metadata), Import workspace |
| Admin (role `admin`) | Invite and disable users, grant and revoke scopes | Users and access |

Roles and scopes: [new architecture](../_replan/new-architecture.md) section 4. Scope is deny by default and every grant is an explicit row.

## Product shape

Six Rust services behind Caddy (HTTPS only): **gateway** (routing, session check, rate limits, CSRF), **identity** (users, sessions, TOTP, invites, grants), **catalog** (books, versions, metadata, search, files, shelf), **reader** (reading copies, tickets, progress, annotations), **ingestion** (source mirror, requests, jobs, curate, build, publish; API and worker containers), **notify** (mail outbox). The web UI is an Angular Material (Material Design 3) static app. Everything runs as Docker Compose containers, one per component, on one host with one PostgreSQL (one database and role per service). Scale target: under 5,000 books and under 50 users (D-29). Detail: [new architecture](../_replan/new-architecture.md) sections 1-3, 9.

## In scope (v1)

1. Public browse, search and detail of metadata, covers and summaries (D-34); sign-in, invite acceptance, password reset, TOTP.
2. Roles, scopes and explicit grants, including `read_once` and `download`; the shelf ("My Books") never grants access.
3. Catalog: browse, search (PostgreSQL FTS with Bengali normalization), facets, book detail, publication workflow (draft, published, archived; automatic publish when all gates pass, D-49), metadata editing with version history, CSV export, EPUB download, cover.
4. Reader: reading copy built once per published version; whole-book rendering in the browser against a 15-minute ticket; reading modes, typography, themes; progress, bookmarks, highlights, notes; "My Notes" view; in-book search only if cheap.
5. Kindle delivery as an asynchronous mail job with delivery status.
6. Ingestion: one pipeline (mirror sync, request, GET-only scrape, curate and validate, duplicate review, EPUB build, publish to catalog), operator console with live updates, source-cookie status.
7. Platform and operations: structured logs, health, audit log (1 year), monthly backups (D-33; up to 30 days of user changes may be lost) with a restore drill, resource limits, secrets as files, rolling restart per service, a launch runbook.
8. UI: Material Design 3, minimalist, light and dark both first-class (OS preference plus persisted toggle), WCAG AA, four window classes (compact, medium, expanded, large), Bengali and English interface (D-08).

## Out of scope (v1)

See [goals and non-goals](goals-and-non-goals.md): public sign-up, DRM, PWA/offline, social features, payments, migrating legacy data (D-32), manual EPUB upload (D-42), XLSX/PDF export, Redis or a message broker, physical-book inventory (deferred to v1.1, D-01), native apps, multi-tenant libraries.

## Honest limit of the reader

The reader serves the whole rendered book to the signed-in browser (D-28). A reader can therefore copy what they can read. Controls are entitlements, short tickets, rate limits and an audit log of opens; they are not DRM. Plan, UI copy and legal notes must say so.

## Source permission

Acquisition is GET-only and never submits a source-site form (D-03). Go-live rests on the owner's own account with the risk accepted by the owner (D-99), not on written permission from the source.

## Deliberate changes from the legacy app

| Legacy (archived) | New | Evidence |
|---|---|---|
| Six Django apps, two parallel book pipelines, three-way record split | Six services, one ingestion pipeline | [X1-106, X1-030](../_replan/analysis/X1-issues-register.md) |
| Everything behind login, yet anonymous submission endpoints | Public metadata browse only; all else authenticated, intake needs `operate` | X1-006 |
| Wildcard roles, shelf grants access | Deny by default, explicit scopes, shelf is not an entitlement | X1-001, X1-008 |
| Celery, Redis, custom engine, inline fallback | PostgreSQL job queue with leases, no inline execution | X1-065..X1-067 |
| Scraper posts "mark complete" to the source | GET-only acquisition | X1-012 |
| Reader token in URL, `/media/` unauthenticated | Header/body ticket; files streamed only by services after a check | X1-003, X1-011 |
| Migration toolkit | Fresh start, users re-invited, books re-ingested (D-32) | [D7](../_replan/analysis/D7-ops-schema.md) |
