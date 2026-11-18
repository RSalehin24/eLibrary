# reader - API contract

Status: DRAFT - source of truth: generated schema in [07-contracts](../../07-contracts/http/README.md)

Public prefix `/api/reader`. Caddy forward-auths every route; the user id and scopes arrive as headers from Caddy only. Each route declares its scope in code (fail closed at startup). The ticket travels in the `X-Reader-Ticket` header, never in the URL.

| Method and path | Scope | Request -> response | Errors |
|---|---|---|---|
| `POST /books/{slug}/open` | `read` (or `read_once` grant) | `{}` -> `200 {ticket, expires_at, book:{id, slug, title, version, language}, progress}` ; writes an `opens` row. Does **not** consume read-once. | `not_found` (also for unpublished), `read_denied{reason}`, `copy_unavailable` (503, rebuild queued), `rate_limited` |
| `GET /book` | `read` + ticket header | whole rendered book as one package: `200` content type `application/vnd.elibrary.reading-package+json` (or gzip/zstd by `Accept-Encoding`), `Cache-Control: no-store`. On the first successful redemption of a `read_once` ticket the service calls identity consume. | `ticket_invalid`, `ticket_expired`, `read_once_consumed`, `copy_unavailable`, `read_denied` |
| `POST /tickets/refresh` | `read` + ticket header | extends a still-valid ticket by issuing a new one for the same user/book/version, max total 2 h per open chain; `read_once` books cannot be refreshed after redemption | `ticket_expired`, `refresh_limit` |
| `DELETE /tickets/current` | session | revokes the presented ticket (close book) | none |
| `GET /books/{slug}/progress` | `read` | `{chapter_id, offset, percent, revision}` | `not_found` |
| `PUT /books/{slug}/progress` | `read` + ticket | `{chapter_id, offset, percent, revision}` -> `200` current value; a stale `revision` returns `200` with the stored value and `applied:false` | `ticket_invalid`, `validation` |
| `GET /books/{slug}/bookmarks` | `read` | list, newest first | none |
| `POST /books/{slug}/bookmarks` | `read` + ticket | `{chapter_id, offset, label?}` -> `201` (existing duplicate -> `200` same row) | `ticket_invalid`, `validation`, `limit_exceeded` |
| `DELETE /books/{slug}/bookmarks/{id}` | session (owner only; no ticket, so access loss never traps data) | `204` (idempotent) | `not_found` for other owners' ids |
| `GET /books/{slug}/highlights` | `read` | list | none |
| `POST /books/{slug}/highlights` | `read` + ticket | `{chapter_id, anchor, color, kind, note?}` -> `201` | `ticket_invalid`, `validation`, `limit_exceeded` |
| `PATCH /books/{slug}/highlights/{id}` | session (owner) | `{color?, note?}` with `If-Match` | `stale_revision`, `not_found` |
| `DELETE /books/{slug}/highlights/{id}` | session (owner) | `204` | none |
| `GET /notes?book&q&after` | session | notes page feed with chapter title and deep link `{slug, chapter_id, offset}` | none |
| `GET /notes/export?format=md\|json` | session | all and only the owner's annotations | none |
| `GET /continue` | session | recent books with progress ("continue reading") | none |
| `GET /books/{slug}/search?q=` | `read` + ticket | OPTIONAL (only if cheap): matches `{chapter_id, offset, snippet}` | `validation` |
| `DELETE /me/data` | session | erase the caller's reader rows (also done on `user.disabled` after grace period) | none |

Demo users: `read` is held but write routes (progress, bookmarks, highlights, notes, delete data) return `403 forbidden_demo`; the renderer keeps demo state in memory only.

## Internal

| Route | Caller | Purpose |
|---|---|---|
| `GET /internal/copies/{book_id}` | catalog (optional status) | `{version, state}` so the catalog can show "reading ready" |
| `GET /internal/contract` | all | handshake |

The reader pulls `catalog GET /internal/events?after=` and `identity GET /internal/events?after=`; it exposes no events of its own (no `/internal/events`).

## Error model

Same envelope as identity: `{ "error": { "code", "message", "request_id" } }`. `401 unauthenticated`, `403 read_denied|forbidden_demo|ticket_invalid`, `404 not_found`, `409 stale_revision`, `410 ticket_expired`, `422 validation|limit_exceeded`, `429 rate_limited`, `503 copy_unavailable`. `read_denied.reason` is the closed set from identity (`NoScope`, `ReadOnceConsumed`, `Unpublished`, `DemoRestricted`, `Inactive`, `MfaRequired`).

## Honest-limit contract note

`GET /book` returns the full sanitized text. API docs and the in-app help state that this is entitlement-checked delivery, not copy protection.
