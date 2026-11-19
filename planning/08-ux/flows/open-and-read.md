# Flow: open and read a book

Status: DRAFT

Actors: visitor, then reader. Requirements: REQ-WEB-015, 016, 021, 022; REQ-RDR-005..009, 012, 022; D-34, D-37, D-41.

1. Visitor opens `/library` (server-rendered, metadata only), searches in Bengali or Latin; `GET /books?q=`.
2. Opens `/books/:slug`: cover, credits, summary, read-limit notice. The preview excerpt and Read are not available to a visitor; the primary action is "Sign in to read".
3. Visitor chooses it: 401 path to `/sign-in?next=/books/:slug/read`; after sign-in ([flow](sign-in-totp.md)) the user returns to the reader route.
4. Signed in, the Overview shows the preview excerpt (`preview` scope) and the primary action Read (or Continue reading with progress).
5. Read: `POST /api/reader/books/{slug}/open` checks `read`, publication state and the read-once rule and returns a ticket (15 minutes, held only in memory).
6. The web requests `GET /tickets/{ticket_id}/book` with the ticket in `X-Reader-Ticket`; the whole package arrives in one response and is rendered. Read-once is consumed at this redemption, not at open.
7. The reader restores progress (section and offset), preferences (theme, size, family) and shows the book. Progress is saved on section change and on page hide with increasing revisions.

Branches:
- No `read` scope or read-once used or book not published: Forbidden state with the typed reason; nothing is consumed.
- Copy still building: "Preparing the book" with polite retry.
- Ticket expires while reading: one silent re-open and continue; if that fails, a message with Retry (annotation writes keep working through the session).
- New version published while reading: next open uses the new copy; annotations are re-anchored by the server, unplaceable ones are Orphaned (D-46).
- Offline: reading continues from memory; writes retry; "not saved" marker.
- Window rotation or mode change keeps the place.
