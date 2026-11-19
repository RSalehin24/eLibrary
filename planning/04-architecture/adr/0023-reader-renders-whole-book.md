# ADR-0023 — The reader service renders and serves the whole book

Status: ACCEPTED

Supersedes [ADR-0016](0016-chapter-served-reader.md) and the reader-token parts of [ADR-0006](0006-capability-tokens.md). Basis: owner decisions D-28 and D-37.

## Context
D-06 had the browser receive chapters one at a time under capabilities issued by the former `access` service. The owner (D-28) decided that the reader service renders and serves the whole book given the EPUB. The legacy reader also placed a token in the URL, had token-only content routes and no revocation.

## Decision
1. On `book.published` the reader fetches the EPUB from catalog (internal streaming call), parses it once (OPF, spine, TOC, XHTML, images, fonts), sanitizes every XHTML document with an allow-list, rewrites resource links, and stores a **reading copy** keyed by `(book_id, version)` on the reader's own volume.
2. `POST /api/reader/books/{slug}/open` checks the `read` scope (and the `read_once` rule) with identity and publication state, then returns a **reading ticket**: bound to user, book and version, valid 15 minutes, carried in a header or body and never in a URL. The reader verifies every ticket by asking identity (D-37); there is no local signature verification.
3. `GET /api/reader/tickets/{ticket}/book` serves the whole reading copy in one response (manifest, TOC, chapters, resources). The browser renders it with a purpose-built renderer (reading modes, typography, light and dark themes). The EPUB file itself is not served by the reader.
4. Read-once is consumed when a ticket is successfully redeemed for the book, not at open time and not when a file is missing.
5. Tickets are revocable immediately: because identity is asked on every use (D-37), disabling a user or changing a grant takes effect on the next request; `user.disabled` and `grant.changed` events additionally drop cached reading sessions.
6. Progress, bookmarks (create and delete), highlights and notes require the signed-in session in addition to the ticket and belong to the user.
7. Optional, only if cheap: in-book search over the reading copy.

## Honest limit
Serving the whole book to the browser means an authorized reader can copy it. The controls are entitlements, short-lived tickets, rate limits and an audit log of opens. **This is not DRM and the plan does not claim to prevent copying.** Requirements and records must state this wording and must not promise otherwise.

## Consequences
+ One service owns parsing, sanitizing and per-user reading state; no per-chapter round trips; simple client.
+ Ticket handling closes the legacy URL-token defect.
- A copy of the whole book is in the browser for the ticket's life and beyond (cannot be prevented).
- Annotation anchors ([ADR-0015](0015-annotation-anchors.md)) refer to a reading copy `(book_id, version)` instead of the old artifact set; re-anchoring is settled by [ADR-0015](0015-annotation-anchors.md) (D-46).
