# reader - state machines

Status: DRAFT

## Reading copy lifecycle (REQ-RDR-001, 004; INV-RDR-001, 004)

```
 book.published / replaced --> Building --ok--> Ready --book.unpublished / deleted--> Withdrawn
                                  |--retryable error (attempts < max)--> Building
                                  +--permanent or exhausted--> Failed --operator rebuild or startup resync--> Building
 Withdrawn --book.published again (undelete / restore)--> Building (or Ready if the hash matches)
```

| From | To | Trigger | Guard |
|---|---|---|---|
| (none) | Building | `book.published` or `book.version_changed` (`replaced`) only, startup resync of a missing copy | no Ready copy for `(book_id, version_id)`; job idempotent |
| Building | Ready | build finished | `content_hash` computed; package file renamed into place; in one transaction the new Ready replaces the previous Ready copy of the same book (partial unique index) |
| Building | Building | retryable error (catalog unreachable, timeout) | attempts below the cap, exponential backoff |
| Building | Failed | permanent error (`not_an_epub`, `package_too_large`, parse error) or attempts exhausted | typed `error_code` stored |
| Failed | Building | manual rebuild or resync | operator action audited |
| Ready | Withdrawn | `book.unpublished` (archived or deleted) for this book | files kept until the retention sweep |
| Withdrawn | Building | `book.published` for the same `(book_id, version_id)` | idempotent |

Only Ready is served. A new version builds beside the old Ready copy and replaces it atomically; the replaced copy becomes Withdrawn (reason `replaced`), so a ticket still bound to the old version gets `copy_unavailable` on redeem and web re-opens silently (one retry) to get a ticket for the new version; the reader never serves a mixed copy. (Assumption: whether identity itself rejects a ticket for a superseded version is not specified in the identity contract; listed in the report.) `Failed` and `Building` copies are never served. Annotations are never touched by a copy change except for the re-anchoring step ([anchors](anchors.md)).

## Ticket (state names are identity's: Minted, Redeemed, Expired; minted and verified by identity, not stored here; REQ-RDR-005..007, 009)

```
 (none) --open: identity allows read + published + read-once rule--> Minted
 Minted --verify redeem (valid)--> Redeemed(read-once consumed once)
 Redeemed --verify again, same ticket (reload)--> Redeemed (no new consumption)
 Minted|Redeemed --15 min--> Expired (ticket_expired)
 Minted|Redeemed --grant.changed / user.disabled / unpublish (seen by identity at verify)--> rejected (typed denial ticket_invalid)
```

Every redemption asks identity (D-37); the reader keeps no ticket row, only `opens` audit rows. The reader's events `user.disabled`, `grant.changed`, `book.unpublished` additionally drop cached state; correctness does not depend on them because the next verify is rejected. Refresh is calling `open` again (one silent re-open in web, then a message); there is no refresh chain.

## Read-once (REQ-RDR-009; model [ReadOnce.tla](../../03-correctness/formal-models/tla/ReadOnce.tla), to be re-checked against the verify trigger)

```
 Unconsumed --first successful redeem--> Consumed (terminal per account and book)
```

Consumption happens inside identity's `verify` with `redeem: true`, after the reader has confirmed the copy is Ready and before streaming starts; it is one atomic insert, so two simultaneous redemptions consume it once. Open never consumes; a missing or Building copy, an invalid or expired ticket never consumes. Same ticket again is a reconnect, not a new opening. A new ticket after consumption is denied `read_once_consumed`. Residual risk: a transfer that fails after consumption stays consumed; an admin can reset it in identity (documented). The rule applies to every role.

## Progress (REQ-RDR-012)

One register per `(user, book)`: a write applies iff `new.revision > stored.revision`; otherwise it is a no-op returning the stored value. Idempotent PUT.

## Bookmark and highlight

`Created --(Edited)*--> Deleted` (hard delete by the owner). Bookmark create is idempotent on `(user, book, section, offset)`; delete is idempotent. Anchor state: `placed <-> orphaned` across version changes; never deleted by a version change ([anchors](anchors.md)).

## Event consumption (pull; REQ-RDR-024)

```
 loop: GET source /internal/events?after=cursor -> apply each event idempotently and advance the cursor in one transaction -> sleep when empty
```

| Event | Handler (idempotent) |
|---|---|
| `book.published` | enqueue copy build unless a Ready copy exists for the key |
| `book.version_changed` (`replaced`) | enqueue build; after Ready, run re-anchoring (D-46) |
| `book.unpublished` | mark copies Withdrawn; unknown book is a no-op |
| `user.disabled`, `grant.changed` | drop cached decisions; keep the highest `grant_version` |
| `user.deleted` | **OPEN (O-1)** erase the user's reader data |

A lost cursor resynchronizes from `GET /internal/books`; startup rebuilds missing copies.
