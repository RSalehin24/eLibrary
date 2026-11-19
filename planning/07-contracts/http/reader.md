# Reader HTTP contract

Status: DRAFT · Service: [reader](../../05-services/reader/README.md) · Requirements: [RDR](../../02-requirements/rdr-reader.md) · Conventions: [README](README.md) · [ADR-0023](../../04-architecture/adr/0023-reader-renders-whole-book.md)

Reader builds a sanitized reading copy of each published EPUB (on `book.published`), serves the **whole rendered book** as one package against a reading ticket (D-28), and stores per-user progress, bookmarks, highlights and notes. The EPUB file itself is never served by the reader and there is no per-chapter content route. Honest limit: a whole book in the browser can be copied; controls are entitlements, short tickets, rate limits and an audit log of opens, not DRM.

Ticket flow: `open` asks identity to decide (`read` scope, publication state, read-once rule) and to mint the ticket; each book request is verified by identity (D-37) with `redeem: true`, which consumes read-once exactly once per account and book.

## Public API (`/api/reader`) - 19 routes

"+ ticket" means the `X-Reader-Ticket` header is required in addition to the session (REQ-RDR-016). Rows owned by the user are readable and writable only by that user (user id from the verified header plus row-level policy).

### Opening and the book

| Method | Path | Scope | Purpose | Errors |
|---|---|---|---|---|
| POST | `/books/{slug}/open` | read | decide and mint: `{ticket, ticket_id, expires_at, version_id, book: {id, slug, title}}`. Rate limited per user (30 opens per hour, [limits](../../04-architecture/cross-cutting/limits.md)); audited. A book on the shelf grants nothing; a non-published or deleted book is `not_found` for readers | `forbidden`, `not_found`, `read_once_consumed`, `copy_unavailable`, `rate_limited` |
| GET | `/books/{slug}/copy` | read | reading-copy state for the current version: `building`, `ready`, `failed` (for the "still building" screen); a withdrawn copy (book unpublished or deleted) is not reported as a state: the book is `not_found`; no side effect | `not_found` |
| GET | `/tickets/{ticket_id}/book` | read + ticket | the whole rendered book in one response: `{book_id, version_id, parser_version, manifest, toc, chapters[{id, title, html}], resources[{id, media_type, sha256, data}]}`; chapter HTML is sanitized (`SafeHtml`), links rewritten to package resources; restrictive CSP, nosniff, `private, no-store`; redeeming consumes read-once once, a retry with the same ticket does not | `ticket_invalid`, `ticket_expired`, `read_once_consumed`, `copy_unavailable`, `forbidden` |
| GET | `/tickets/{ticket_id}/search` | read + ticket | in-book search `?q=` over the reading copy, results `{section_id, snippet, offset}` (SHOULD, REQ-RDR-023) | `ticket_invalid`, `ticket_expired` |

A ticket is refreshed by calling `open` again (one silent re-open in the web app, then a message); there is no refresh chain.

### Progress, bookmarks, highlights, notes

Anchor shape used everywhere: `{section_id, offset, quote?: {exact, prefix, suffix}}`. Items carry `anchor_state`: `placed` or `orphaned` (re-anchored on a version change; never deleted, resolving never errors).

| Method | Path | Scope | Purpose | Errors |
|---|---|---|---|---|
| GET | `/books/{slug}/progress` | read + ticket | own progress `{section_id, offset, percent (0-100), locator, revision}` | |
| PUT | `/books/{slug}/progress` | read + ticket | idempotent upsert; `revision` must increase, a stale write is a no-op returning the stored value; locator length bounded | `validation_failed` |
| GET | `/books/{slug}/bookmarks` | read + ticket | own bookmarks | |
| POST | `/books/{slug}/bookmarks` | read + ticket | `{anchor, label?}`; the same bookmark twice returns the existing one with `created: false` (200), never a 500 | `limit_exceeded` |
| DELETE | `/bookmarks/{id}` | session | delete own; needs no book access | `not_found` |
| GET | `/books/{slug}/highlights` | read + ticket | own highlights and notes for the book | |
| POST | `/books/{slug}/highlights` | read + ticket | `{anchor, color, kind: highlight|quote, note?}`; five colours defined once; note up to 10,000 chars; up to 5,000 per book | `limit_exceeded`, `validation_failed` |
| PATCH | `/highlights/{id}` | session | edit colour, note, kind (`If-Match`) | `stale_revision`, `not_found` |
| DELETE | `/highlights/{id}` | session | delete own | `not_found` |

Notes are modelled as the optional `note` text of a highlight; a separate free-standing note resource is not defined (design assumption, see report).

### Own data across books

| Method | Path | Scope | Purpose | Errors |
|---|---|---|---|---|
| GET | `/me/progress` | session | progress across books (library "continue reading"), paged | |
| GET | `/me/notes` | session | all own annotations across books with deep-link data `{slug, anchor, anchor_state}`; orphans listed | |
| GET | `/me/preferences` | session | reader preferences: theme (`system`, `light`, `dark`, `sepia`), font family, size, line height, margins. Stored per user in the reader service (D-48). | |
| PUT | `/me/preferences` | session | replace preferences (D-48) | `validation_failed` |
| GET | `/me/export` | session | all own reading data as JSON (REQ-RDR-017) | |
| GET | `/me/annotations/export` | session | `?format=md|json` notes and highlights export (SHOULD) | |

## Internal API (`/internal`, service token) - 2 routes

| Method | Path | Caller | Purpose |
|---|---|---|---|
| GET | `/internal/copies` | catalog, ops checks | `{book_id, version_id, state}` keyset listing for the drift reconciliation (reader copies against catalog published versions) |
| POST | `/internal/users/{id}/erase` | identity | erase all reader data of a deleted user; **OPEN (O-1): depends on whether a `user.deleted` event is added; if it is, this route is replaced by the event** |

Also on the internal port: `GET /internal/health`, `GET /internal/ready`, `GET /internal/contract`. The reader exposes no event outbox; it consumes `book.published`, `book.unpublished`, `book.version_changed` (catalog) and `user.disabled`, `grant.changed` (identity) from stored cursors and rebuilds missing copies on startup.
