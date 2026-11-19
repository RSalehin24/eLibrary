# catalog

Status: DRAFT (rewritten for the six-service design, D-29, D-31, D-32, D-34, D-36, D-41..D-43; basis `_replan/new-architecture.md`)

What books exist, who made them, how to find them, and the only place that holds their files. Public metadata, signed-in preview and files, one writer of book state.

| | |
|---|---|
| Owns | books, book versions, metadata (title, credits, series, categories) with history, agents and aliases, publication state, tombstones, source links, asset registry and the asset files (EPUB, cover, preview artifact) on its own volume, shelves ("My Books"), saved filters (D-43), PostgreSQL full-text search documents, Kindle requests (status copy), event outbox, audit log of catalog changes |
| Does not own | accounts, roles, grants, tickets (identity); reading copies and reading state (reader); mail delivery (notify); scraping, curation, duplicate review, EPUB building (ingestion); routing and rate limits (gateway) |
| Talks to | identity (`/internal/check` for per-book decisions; pulls `user.disabled`, `grant.changed`; `user.deleted` OPEN O-1); called by ingestion (publish, match), reader (EPUB stream, facts, listing), notify (EPUB stream, Kindle status), gateway (all `/api/catalog/*`) |
| Emits (outbox) | `book.published`, `book.unpublished`, `book.version_changed`, `kindle.requested` |
| Tech | Rust service, PostgreSQL schema `catalog` (role `catalog`), volume `catalog_files`; no cache layer, no search engine (D-29) |
| Contract | [HTTP](../../07-contracts/http/catalog.md) · [events](../../07-contracts/events/README.md) · requirements [CAT](../../02-requirements/cat-catalog.md) |

## Requirements covered

| REQ | Where |
|---|---|
| REQ-CAT-001, 021, 022 | [state machines](state-machines.md), [versions](versions.md), [domain model](domain-model.md) |
| REQ-CAT-002, 003, 030, 032 | [domain model](domain-model.md) (one visibility filter), [API](api-contract.md) |
| REQ-CAT-004, 005, 006, 007 | [domain model](domain-model.md) |
| REQ-CAT-008, 015, 016, 017 | [search](search.md), [API](api-contract.md) |
| REQ-CAT-009 .. 014, 018 | [search](search.md) |
| REQ-CAT-012, 019 | [search](search.md), [domain model](domain-model.md) (`PublicDocument`, `PreviewArtifact`) |
| REQ-CAT-020, 023, 028 | [files](files.md) |
| REQ-CAT-024 | events and cursors in [domain model](domain-model.md), [state machines](state-machines.md) |
| REQ-CAT-025, 026, 033 | shelf and saved filters in [domain model](domain-model.md) |
| REQ-CAT-027 | [API](api-contract.md) (CSV), [test plan](test-plan.md) |
| REQ-CAT-029 | Kindle in [files](files.md), [state machines](state-machines.md) |
| REQ-CAT-031 | `audit_log` in [domain model](domain-model.md) |

Every REQ-CAT id also has a row in the [test plan](test-plan.md).

## Responsibilities

1. Serve public metadata (browse, search, detail, cover) to anyone (D-34); serve preview to `preview`, EPUB to `download`, Kindle send to `kindle`; reader-facing queries see only published, non-deleted versions by construction.
2. Accept gate-passing builds from ingestion (`POST /internal/books/{id}/versions`) and publish them in the same transaction with no approval step (D-49); unpublish, edit and delete are manual `manage_catalog` actions; keep the previous version's files until the next one is published.
3. Keep metadata edits as commands with optimistic concurrency, history, and separate source-owned and operator-owned fields.
4. Maintain the full-text index in the same transaction as visibility changes; Bengali normalization shared by index and query.
5. Write every state change and its event in one transaction (outbox); audit with the actor.

## Non-responsibilities

- No scraping, no EPUB building, no manual EPUB upload (D-42).
- No decision of who may do what: it asks identity and treats a missing decision as deny.
- No serving of files by Caddy or the gateway; no reading-copy parsing.
- No work/edition grouping and no catalog codes (D-36); a "new edition" is a human action (O-3 OPEN: modelling of work/edition grouping is not decided; none is modelled here).
- Physical-book inventory stays deferred (D-01).

## Structure

Crate layout follows [workspace layout](../../04-architecture/workspace-layout.md) and [coding standards](../../03-correctness/coding-standards.md): `domain` (version state types, `Slug`, `Sha256`, `PublicDocument`, `PreviewArtifact`), `store` (the only module that touches SQL; one `visible_books` filter), `search` (normalizer call, query builder), `files` (blob store), `api` (routes with declared scopes; startup fails if a route has none), `events` (outbox writer, identity cursor consumer), `jobs` (reconciler, verify job, orphan sweep, retention).

## Failure behaviour

| Failure | Behaviour |
|---|---|
| Identity unreachable | scoped routes fail closed (503), public metadata routes keep working; cached `Allow` at most 5 s keyed by grant version |
| Ingestion retries a publish after a crash | same build identity returns the same version; no second version (REQ-CAT-022) |
| Crash between blob rename and commit | orphan blob swept after 24 h; no row, no visible version |
| Blob missing or hash mismatch on read | the GET returns an error and changes nothing (REQ-CAT-032); a verify job reports it and blocks publish and restore of that version |
| Reader or notify down | events wait in the outbox (30 days); consumers catch up from their cursor; `GET /internal/books` is the resync source |
| Notify never reports a Kindle status | request stays `queued`; shown as such; no automatic resend |
| Index drift | reconciler compares `search_docs` ids with published ids and alerts; `rebuild` command restores equality (REQ-CAT-013) |

## Open items (not decided here)

| # | Item |
|---|---|
| O-1 | `user.deleted`: catalog removes the user's shelf and saved filters on it (otherwise an internal erase call is needed) |
| O-3 | Work/edition grouping: not modelled; owner decision pending |
| O-4 | Scope guarding CSV export and book deletion (`manage_catalog` recommended) |
| O-5 | Search relevance gate MUST or SHOULD (written as SHOULD, REQ-CAT-018) |
| O-7 | Provisional numbers (page 100, CSV 5,000 rows, 30 s index latency) |
| Q-1 | Bengali FTS quality is measured by spike S-01 at P0 |
| mapping | Version state names: see [state machines](state-machines.md) "Naming" |

See also [domain model](domain-model.md) · [API](api-contract.md) · [state machines](state-machines.md) · [versions](versions.md) · [files](files.md) · [search](search.md) · [tests](test-plan.md).
