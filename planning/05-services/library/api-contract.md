# library — API contract

Status: DRAFT · Source of truth: `contracts-library`

All routes require an authenticated, non-demo session unless noted; the owner is the session subject (never a parameter).

| Method & path | Purpose | Notes |
|---|---|---|
| `POST /library/books/{book_id}/open` | start/reuse reading session | returns `{session_id, capability, section_index_url, progress}` or `Deny(reason)` |
| `POST /library/sessions/{id}/heartbeat` | renew capability, record liveness | 410 when session closed |
| `POST /library/sessions/{id}/close` | end session | idempotent |
| `GET/PUT /library/books/{book_id}/progress` | progress | `PUT` with `revision`; stale → 200 no-op with current value |
| `GET/POST /library/books/{book_id}/bookmarks`, `DELETE /library/bookmarks/{id}` | bookmarks | |
| `GET/POST /library/books/{book_id}/highlights`, `PATCH/DELETE /library/highlights/{id}` | highlights/notes | `If-Match` revision |
| `POST /library/anchors/resolve` | resolve anchors for a section against the active set | returns location or `Orphaned` |
| `GET /library/notes?book&q&state&after` | notes page feed | |
| `GET /library/notes/export?format=md\|json` | export | |
| `GET/PUT/DELETE /library/shelf/{book_id}`, `GET /library/shelf` | My Books | idempotent PUT |
| `GET/POST/DELETE /library/saved-filters` | saved filters | |
| `GET /library/kindle-sent` | sent history | from notify events |

## Internal

`POST /internal/events/*` inboxes for events listed in the README; `GET /internal/contract`.

## Errors

`read_denied(reason)`, `stale_revision`, `session_closed`, `anchor_invalid`, `limit_exceeded(highlights)`.
