# reader - state machines

Status: DRAFT

## Reading copy

```
 (book.published / version_changed) -> Building --ok--> Ready --book.unpublished--> Withdrawn
                                          |--retryable error (<=5)--> Building
                                          +--permanent / exhausted--> Failed --rebuild--> Building
```
One `Ready` per book (partial unique index). A new version builds beside the old `Ready` copy and replaces it atomically when ready; tickets bound to the old version stay valid until they expire (<= 15 min) unless the book is unpublished. `Failed` and `Building` copies are never served.

## Ticket

```
 Issued --redeem (valid)--> Redeemed --expire--> Expired
   |  \--revoke / grant.changed / user.disabled / unpublish--> Revoked
   +--expire--> Expired
```
Issued only after `/internal/check` allows `read` for a published book. Redeem requires state Issued or Redeemed, `now < expires_at`, user still allowed, copy `Ready` for the bound version. Refresh issues a new ticket and marks the old one Expired. Every transition writes an `opens` row.

## Read-once

```
 Unconsumed --redeem succeeds (package ready to send)--> Consumed (terminal per user+book)
```
Consumption is requested at redeem, after the copy is confirmed `Ready` and before streaming starts; if identity records the consume but the transfer later fails, the open is still consumed (documented residual: the user may ask an admin to delete the `read_once_uses` row and re-grant). Missing copy, build failure, expired or invalid ticket never consume. Open never consumes. Same ticket redeemed again (reload) is allowed; a new ticket after consumption is denied `ReadOnceConsumed`. Model: [ReadOnce.tla](../../03-correctness/formal-models/tla/ReadOnce.tla) (to be re-checked against this ticket-redeem trigger).

## Progress

Single register per `(user, book)`: write applies iff `new.revision > stored.revision`; a conflict returns the stored value (INV-LIB-001).

## Highlight / bookmark

`Created -> (Updated)* -> Deleted` (hard delete by owner). Bookmark create is idempotent on `(user, book, chapter, offset)`; delete is idempotent. After a `book.version_changed`, annotations keep their `version`; on open of a newer version the renderer re-anchors by quote (prefix/exact/suffix) client-side, and an annotation that cannot be placed is shown as unplaced (never deleted, INV-LIB-002). Server-side bulk re-anchoring is out of scope at this scale (Open question).

## Event consumption (pull)

```
 loop: GET source/internal/events?after=cursor -> for each event: apply idempotently + advance cursor (one transaction) -> sleep when empty
```
Idempotent handlers: `book.published` for a `(book,version)` already `Ready` is a no-op; `book.unpublished` on an unknown book is a no-op; `grant.changed` / `user.disabled` revoke matching tickets (`UPDATE ... WHERE revoked_at IS NULL`). A crash re-reads from the stored cursor.
