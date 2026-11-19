# catalog

Status: DRAFT (rewritten for the 5-service architecture, D-27/D-28/D-29; basis `_replan/new-architecture.md`)

What books exist, who made them, how to find them, and the files that make them. Public by default, one place for bytes.

| | |
|---|---|
| Owns | books, book versions, metadata with history, credits/agents, series, categories, review and publication state, source links, asset registry and the asset files (EPUB, cover, preview) on its own volume, shelves ("My Books"), PostgreSQL full-text search documents, Kindle-send requests, event outbox |
| Does not own | accounts, roles, grants (identity), reading copies and reading state (reader), mail delivery (notify), scraping, curation and EPUB building (ingestion) |
| Requirements | REQ-CAT-001…008 (009 deferred, D-01), REQ-DSC-001…010, REQ-CON-001, 003, 004, 005 (file serving); REQ-CON-002/007/008/009 are met by ingestion at build time and checked again on intake here; REQ-CON-006 see open points |
| Emits (outbox) | `book.published`, `book.unpublished`, `book.version_changed`, `kindle.requested` |
| Consumes (pull) | `grant.changed`, `user.disabled` from identity (cache invalidation only) |
| Calls | identity `/internal/check` (only for scoped routes that need a per-book decision) |
| Called by | caddy (public and authenticated `/api/catalog/*`), ingestion (create version, duplicate classify, agent resolve), reader (stream EPUB, facts), notify (stream EPUB for Kindle) |

## What changed from the old design

| Old | New |
|---|---|
| separate `content` service: artifact sets, active pointer, capabilities, retention holds | files live in catalog: `assets` rows per version on catalog's volume; the published version is the pointer; no capability tokens, service token for internal streaming |
| separate `gateway` service | caddy routes `/api/catalog/*` and does forward-auth; scope declared per route in code (fail closed) |
| search index as a projection fed by events, shadow rebuild | search document table updated in the same transaction as the publication change; rebuild command from tables |
| `access` decide calls on admin routes | scope check through caddy forward-auth; `manage_catalog` for admin routes |

## Public by construction

Handlers for search, browse, book detail, preview and cover read only rows reachable from `books.published_version_id`. They never take a user id, so a Draft, in-review, archived or deleted book cannot leak (INV-CAT-001, INV-DSC-001). Authenticated routes (download, Kindle, shelves) additionally check the scope via caddy's forward-auth headers.

## Modules

| Module | Responsibility |
|---|---|
| `books` | books, versions, publication workflow, soft delete, slugs/redirects |
| `metadata` | field values, overrides, revision history, credits, series, categories, agents |
| `assets` | write-once file store (content-addressed under the catalog volume), registry, streaming with ranges |
| `search` | normalizer (shared crate `bn-text`, same function as ingestion), search documents, query API (see [search](search.md)) |
| `shelves` | "My Books" and custom shelves; never grants access |
| `kindle` | request issuing, size and rate limits |
| `outbox` | `events` table, `GET /internal/events` |
| `duplicates` | five-case classification used by ingestion |

## Downloads and streaming

Files are never served by caddy from disk. The service streams after the scope check (`download`) or after the internal service token check; `Content-Disposition` uses the current title; `Range` is supported (REQ-CON-005); responses are `Cache-Control: private, no-store`; covers and previews of published books are public and immutable by hash.

## Open points (not decided here)

1. Retention of the previous published version's files (REQ-CON-006 was tied to annotation re-anchoring that now lives in reader): proposal 30 days after archive, then purge.
2. XLSX and PDF export (REQ-CAT-008 SHOULD) would need new dependencies; only streamed CSV is designed.
3. Whether `pg_trgm` (a PostgreSQL contrib extension, not a crate) may be enabled; the design works without it.
4. Scope for shelf mutations (no `shelf` scope exists); designed as `browse` plus signed-in plus not-demo.

See [domain model](domain-model.md) · [API](api-contract.md) · [state machines](state-machines.md) · [tests](test-plan.md) · [search](search.md).
