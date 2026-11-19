# Service catalog

Status: DRAFT

Six Rust services plus a server-rendered web app, behind Caddy (HTTPS only) and a gateway. Each service is its own crate and binary with its own database and role (the gateway has none). See [ADR-0025](adr/0025-six-services-with-gateway.md). Basis: D-28, D-29, D-31, D-39. Detail per service: [gateway](../05-services/gateway/README.md), [identity](../05-services/identity/README.md), [catalog](../05-services/catalog/README.md), [reader](../05-services/reader/README.md), [ingestion](../05-services/ingestion/README.md), [notify](../05-services/notify/README.md), [web](../05-services/web/README.md).

| Service | Owns (source of truth) | Never owns | Sync deps | Emits / consumes |
|---|---|---|---|---|
| **gateway** | nothing persistent (routing table, rate-limit counters in memory) | any data | identity (`/internal/authorize`), every routed service | none |
| **identity** | users, credentials (Argon2), opaque server-side sessions, TOTP, invites, password reset, roles, grants, profile images (D-44), audit log (D-40, retained 1 year) | books, files | none | emits `user.disabled`, `grant.changed`, `email.requested` |
| **catalog** | books, book versions, metadata (title, contributors, series, categories), review and publication state, metadata version history, source links, asset registry and files (EPUB, cover) on its own volume, shelves ("My Books"), saved filters (D-43), PostgreSQL FTS index | accounts, reading state | identity (`/internal/check`) | emits `book.published`, `book.unpublished`, `book.version_changed`, `kindle.requested`; consumes `user.disabled`, `grant.changed` (cache invalidation) |
| **reader** | reading copies (parsed, sanitized books) on its own volume, reading sessions, progress, bookmarks, highlights, notes | the EPUB, entitlements | catalog (fetch EPUB), identity (`/internal/check`, ticket verification D-37) | consumes `book.published`, `book.unpublished`, `book.version_changed`, `user.disabled`, `grant.changed` |
| **ingestion** (`ingestion-api` + `ingestion-worker`) | source mirror, intake requests, jobs, scrape cache (files), curated documents, duplicate reviews, source-site credential status, automation settings | published books | catalog (`POST /internal/books/{id}/versions`), identity (`/internal/check`) | emits `build.finished` (internal); consumes `book.*` |
| **notify** | outbox of mails, templates, delivery log | accounts, books | catalog (EPUB stream for Kindle) | consumes `email.requested`, `kindle.requested` |
| **web** | Angular SSR app (Node), UI state | any data | gateway (API), catalog metadata for SSR pages via gateway | none |

No service reads another service's tables or volume. Data moves by internal HTTP (streaming for files) and by pull-based events ([communication](communication-and-events.md), ownership in [data ownership](data-ownership.md)).

Cross-cutting platform and non-functional requirements (REQ-PLT, REQ-NFR) and who implements and tests each are listed in [platform ownership](platform-ownership.md).

## Infrastructure containers

`caddy` (HTTPS and certificate auto-renewal only) and `postgres` (one container, one database and role per service); one-shot `migrate` and `backup` jobs. They own no business semantics. See [deployment topology](deployment-topology.md).

## Why this split

- **gateway** is the single enforcement point at the edge: routing, session check against identity, rate limits, CSRF. It holds no data, so it can restart freely.
- **identity** is the only place that decides who may do what (authentication and authorization together); no subject-facts projection elsewhere.
- **catalog** owns a book's metadata and its files (EPUB, cover) so publication is one transaction plus one file write; metadata-only public browse, search and detail live here (D-34).
- **reader** isolates parsing of third-party EPUB content and private per-user state from catalog; it fails independently.
- **ingestion** is heavy, hostile-input and failure-prone; it must never take down browsing. API and worker are separate containers of one image.
- **notify** isolates third-party side effects (SMTP) and retries; kept separate from identity (D-31).

## What was merged (historical note)

The first plan had `access`, `content`, `library` and a `gateway`. `access` merged into identity (grants and decisions); `content` into catalog (files) and reader (rendering); `library` into reader (progress, annotations) and catalog (shelves). D-27 then dropped the gateway; D-31 restored it as a separate service ([ADR-0026](adr/0026-gateway-auth-check-via-identity.md)). Rejected again: a separate `search` service (FTS is part of catalog), a separate UI-projection service.

## Consolidation escape hatch

If operations toil exceeds the threshold in [risk R-08](../03-correctness/risk-register.md), a merge of `notify` into identity or catalog could be reconsidered; D-31 keeps them separate today, so this needs a new owner decision. Code and database boundaries would stay unchanged.
