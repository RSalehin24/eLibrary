# reader

Status: DRAFT (rewritten for the six-service design: D-28, D-31, D-37, D-40, D-41; [ADR-0023](../../04-architecture/adr/0023-reader-renders-whole-book.md); basis `_replan/new-architecture.md` section 5)

Builds a safe reading copy of each published EPUB, opens it for a signed-in reader against a short ticket, serves the whole book in one package, and keeps the reader's place, bookmarks, highlights and notes.

| | |
|---|---|
| Owns | reading copies (parsed, sanitized books) on its own volume, open and redemption audit, progress, bookmarks, highlights and notes, annotation anchor state, catalog and identity event cursors; per-user reader preferences (`preferences`, D-48) |
| Does not own | books and EPUB files (catalog), accounts, scopes, tickets and read-once counters (identity mints and verifies; the reader holds no ticket table and no signing key), the "My Books" shelf (catalog), mail (notify) |
| Talks to | catalog (stream EPUB `GET /internal/books/{id}/versions/{v}/epub`; pull `book.*` events; `GET /internal/books` resync), identity (`/internal/tickets` mint, `/internal/tickets/verify`, `/internal/check`; pull `user.disabled`, `grant.changed`); called by the gateway (`/api/reader/*`) and by web through it |
| Emits | nothing (no outbox; nothing consumes reader state) |
| Tech | Rust service, PostgreSQL database `reader` (role `reader`, row-level policy on personal tables), volume `reader_files` (not backed up: regenerable, D-33) |
| Contract | [HTTP](../../07-contracts/http/reader.md) · [events](../../07-contracts/events/README.md) · requirements [RDR](../../02-requirements/rdr-reader.md) |

## Requirements covered

| REQ | Where |
|---|---|
| REQ-RDR-001, 002, 003, 004 | [reading copy](reading-copy.md), [state machines](state-machines.md) |
| REQ-RDR-005, 006, 007, 009 | flow below, [state machines](state-machines.md) (ticket, read-once) |
| REQ-RDR-008, 025 | whole-book package, [reading copy](reading-copy.md) |
| REQ-RDR-010 | honest limit below |
| REQ-RDR-011 | `opens` audit and rate limits in [domain model](domain-model.md) |
| REQ-RDR-012, 013, 014, 016, 017, 018, 019 | personal data in [domain model](domain-model.md) |
| REQ-RDR-015 | [anchors](anchors.md) |
| REQ-RDR-020, 021, 022, 023 | browser renderer is in [web](../web/README.md); reader supplies the package, the state fields and the search route; preferences in the `preferences` table (REQ-RDR-026, D-48) |
| REQ-RDR-024 | event consumption in [state machines](state-machines.md) |

Every REQ-RDR id also has a [test plan](test-plan.md) row.

## Flow

1. **Build.** On `book.published` (and for `replaced` changes) the reader streams the EPUB from catalog for that `version_id`, parses it once, sanitizes every XHTML document, rewrites resource links, stores the copy keyed by `(book_id, version_id)` and marks it Ready ([reading copy](reading-copy.md)). The step is idempotent per key.
2. **Open.** `POST /api/reader/books/{slug}/open` (scope `read`, 30 opens per user per hour): the reader asks identity to decide and mint a ticket (`read` scope, published and not deleted, read-once rule without consuming). Identity is the only minter. The ticket is bound to user, book, version and grant version, valid 15 minutes, returned in the response body, sent back in the `X-Reader-Ticket` header, never in a URL. Shelf membership grants nothing. The open is audited.
3. **Redeem.** `GET /api/reader/tickets/{ticket_id}/book` with the ticket header: the reader asks identity to verify with `redeem: true` (D-37: every time, no local signature check). Only a `Verified<ReadingTicket>` reaches the handler. Identity re-checks grant version, active state and publication state and consumes read-once atomically, once per account and book; a reconnect with the same ticket is not a new opening. Then the whole package is returned in one response.
4. **Personal data.** Progress, bookmarks, highlights, notes need the signed-in session plus the ticket (create and read; delete and edit by id need only the session) and belong to the user from the verified identity header, never from the body.
5. **Search in the book** (SHOULD): `GET /api/reader/tickets/{ticket_id}/search` over the reading copy text.

## Honest limit (state it wherever access is documented, REQ-RDR-010)

Serving the whole book to the browser means a signed-in reader can copy it. The controls are entitlements checked at open and redeem, 15-minute tickets verified every time, rate limits and an audit log of opens. This is **not DRM** and the plan does not claim to prevent copying. `read_once` limits how many times a book can be opened, not what a person does with an opened book. The same wording appears in API docs and in the in-app help.

## Non-responsibilities

No EPUB file or per-chapter route (REQ-RDR-008); no scraping or building; no scope decisions; no reading of catalog tables; no events emitted; no shelf. The browser renderer, themes and keyboard behaviour belong to [web](../web/README.md).

## Structure

`copy` (parser, sanitizer producing `SafeHtml`, package writer, text layer), `tickets` (`Verified<ReadingTicket>` constructor calling identity), `anchors` ([anchors](anchors.md)), `store` (SQL, owner-parameterized queries), `api` (routes with declared scopes), `events` (cursor consumers), `jobs` (copy build, re-anchor, startup rebuild, drift report).

## Failure behaviour

| Failure | Behaviour |
|---|---|
| Identity unreachable at open or redeem | fail closed (503); nothing is served or consumed |
| Catalog unreachable during build | retry with backoff; `copy_unavailable` on open; nothing half-built is served; rebuild later |
| Copy still Building or Failed | `copy_unavailable` with state from `GET /books/{slug}/copy`; read-once is not consumed |
| Reader restart or lost cursor | resync from `GET /internal/books`; rebuild missing copies on startup (REQ-RDR-024) |
| Duplicate or reordered events | idempotent handlers; cursor advances only with the effect |
| Book unpublished or deleted | copy marked Withdrawn; next redeem fails at identity; annotations kept |
| Hostile EPUB (bomb, malformed XHTML) | build fails typed (`Failed`), never panics, never stored unsanitized |

## Open items (not decided here)

| # | Item |
|---|---|
| O-1 | `user.deleted` event or `POST /internal/users/{id}/erase` for erasure of reader data; **OPEN** |
| C-4 | Notes are a field of a highlight (kept in the contract); **OPEN** |
| sanitizer | CSS policy (publisher styles) in [reading copy](reading-copy.md) is a proposal |

See also [domain model](domain-model.md) · [API](api-contract.md) · [state machines](state-machines.md) · [tests](test-plan.md).
