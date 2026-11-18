# reader

Status: DRAFT

Renders a published book once, serves the whole of it to a signed-in reader on a short ticket, and keeps that reader's place, bookmarks, highlights and notes. Replaces `library` and the reading parts of `content` (D-27, D-28).

| | |
|---|---|
| Owns | reading copies (parsed, sanitized books) on its own volume, tickets, open audit, progress, bookmarks, highlights, notes, catalog event cursor |
| Does not own | books and EPUB files (catalog), accounts and scopes (identity), the "My Books" shelf (catalog), mail (notify) |
| Requirements | REQ-LIB-001, 002, 003, 005, 007, 008 (REQ-LIB-004/006 move to catalog; REQ-CON reading parts: see Open questions) |
| Emits | none (no outbox needed; nothing else consumes reader state) |
| Consumes | `book.published`, `book.unpublished`, `book.version_changed` (catalog `/internal/events`, pulled with a stored cursor), `user.disabled`, `grant.changed` (identity) |
| Calls | catalog (`GET /internal/books/{id}/versions/{v}/epub`, streaming, service token), identity (`/internal/check`) |
| Called by | web through Caddy (`/api/reader/*`) |

## Flow (brief section 5)

1. **Build.** On `book.published` or `book.version_changed` the reader fetches the EPUB, parses it once (OPF, spine, TOC, XHTML, images, fonts), sanitizes every XHTML document with an allow-list, rewrites resource links, writes a **reading copy** keyed by `(book_id, version)` to its volume and records it `ready`. On `book.unpublished` the copy is marked `withdrawn` (files kept until the retention sweep) and open tickets stop working.
2. **Open.** `POST /api/reader/books/{slug}/open` (scope `read`): reader asks identity `/internal/check` (scope, publication, read-once rule, without consuming) and returns a **ticket**: signed, bound to user + book + version, valid **15 minutes**, delivered in the response **body** and sent back in the `X-Reader-Ticket` **header**; never in a URL, log or query string.
3. **Redeem.** `GET /api/reader/book` with the ticket header serves the **whole rendered book in one response** (manifest, TOC, chapters, resources as one package). The browser renders it with its own small renderer (modes, typography, themes). The EPUB file is never served by the reader.
4. **Read-once.** Consumed when the ticket is *successfully redeemed* (the package is ready to be sent), via `/internal/check` with `consume=true`. Not at open; not when the reading copy is missing or the build is not `ready`.
5. **State.** Progress, bookmarks (create and delete), highlights, notes need the signed-in session **and** a live ticket for that book, and belong to the user (owner from the verified `X-User-Id`, never from the body).
6. **Optional, only if cheap:** in-book search (`GET .../search?q=`) over the reading copy text; not part of the committed scope.

## Honest limit (state it wherever access is documented)

Because the whole book is delivered to the browser, a signed-in reader can copy it. Reader controls are entitlements checked at open, 15-minute tickets, rate limits and an audit log of opens. They are **not DRM** and are not claimed to prevent copying. `read_once` limits openings, not what a person does with an opened book.

## Safety

- Sanitization is an allow-list; scripts, handlers, external loads, `javascript:` and `data:` navigations are removed. Images and fonts are served from the same package, same origin, with CSP and `nosniff`. Sanitized output is the only thing stored for serving.
- Fetching content never mutates entitlement state; a missing copy returns `copy_unavailable` and queues a rebuild (idempotent job), never a state flip elsewhere.
- Row-level security keeps personal rows owner-only (INV-LIB-003). Account disable stops tickets (event plus ticket check against identity on redeem).

See [domain model](domain-model.md) | [API](api-contract.md) | [state machines](state-machines.md) | [tests](test-plan.md).
