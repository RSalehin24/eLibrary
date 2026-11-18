# Service catalog

Status: DRAFT

Five services plus a static web app, fronted by Caddy; there is no gateway. Each service is its own Rust crate and binary with its own database and role. See [ADR-0020](adr/0020-five-services-no-gateway.md). Basis: D-27, D-28, D-29.

| Service | Owns (source of truth) | Never owns | Sync deps | Emits / consumes |
|---|---|---|---|---|
| **identity** | users, credentials (Argon2), opaque server-side sessions, TOTP, invites, password reset, roles, grants, demo account limits, auth audit log | books, files | none | emits `user.disabled`, `grant.changed`, `email.requested` |
| **catalog** | books, book versions, metadata (title, contributors, series, categories), review and publication state, metadata version history, source links, asset registry and files (EPUB, cover) on its own volume, shelves ("My Books"), PostgreSQL FTS index | accounts, reading state | identity (`/internal/check`) | emits `book.published`, `book.unpublished`, `book.version_changed`, `kindle.requested`; consumes `user.disabled`, `grant.changed` (cache invalidation) |
| **reader** | reading copies (parsed, sanitized books) on its own volume, reading sessions, progress, bookmarks, highlights, notes | the EPUB, entitlements | catalog (fetch EPUB), identity (`/internal/check`) | consumes `book.published`, `book.unpublished`, `book.version_changed`, `user.disabled`, `grant.changed` |
| **ingestion** (`ingestion-api` + `ingestion-worker`) | source mirror, intake requests, jobs, scrape cache (files), curated documents, duplicate reviews, source-site credential and status, automation settings | published books | catalog (`POST /internal/books/{id}/versions`), identity (`/internal/check`) | emits `build.finished` (internal); consumes `book.*` |
| **notify** | outbox of mails, templates, delivery log | accounts, books | catalog (EPUB stream for Kindle) | consumes `email.requested`, `kindle.requested` |
| **web** | static Angular app, UI state | any data | Caddy only | none |

No service reads another service's tables or volume. Data moves by internal HTTP (streaming for files) and by pull-based events ([communication](communication-and-events.md)).

## Infrastructure containers

`caddy` (TLS, routing, forward-auth to identity) and `postgres` (one container, one database and role per service); one-shot `migrate` and `backup` jobs. They own no business semantics. See [deployment topology](deployment-topology.md).

## Why this split

- **identity** is the only place that decides who may do what (authentication and authorization together); merging the former `access` removes the subject-facts projection and a network hop.
- **catalog** owns a book's metadata and its files (EPUB, cover) so publication is one transaction plus one file write; public browse, search and preview live here.
- **reader** isolates parsing of third-party EPUB content and private per-user state from catalog; it fails independently.
- **ingestion** is heavy, hostile-input and failure-prone; it must never take down browsing. API and worker are separate containers of one image.
- **notify** isolates third-party side effects (SMTP) and retries.

## What was merged (historical note)

The previous plan had `access`, `content`, `library` and a `gateway`. `access` merged into identity (grants and decisions); `content` merged into catalog (assets, preview) and reader (rendering); `library` merged into reader (progress, annotations) and catalog (shelves); gateway duties moved to Caddy ([ADR-0024](adr/0024-caddy-forward-auth-deny-by-default.md)). Rejected again: a separate `search` service (FTS is part of catalog), a separate UI-projection service.

## Consolidation escape hatch

If operations toil exceeds the threshold in [risk R-08](../03-correctness/risk-register.md), `notify` may be merged into identity or catalog. Code and database boundaries stay unchanged.
