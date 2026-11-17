# library

Status: DRAFT

A reader's own space: place in a book, highlights, notes, shelf, saved searches.

| | |
|---|---|
| Owns | reading progress, reading sessions, bookmarks, highlights/notes (anchors), shelf (My Books), saved filters, section-index projections |
| Does not own | book data (catalog), files (content), authorization (access) |
| Requirements | REQ-LIB-001…008 |
| Emits | `AnnotationReanchorDone`, `AnnotationOrphaned`, `ShelfChanged` |
| Consumes | `ArtifactSetActivated` (re-anchor), `BookArchived`, `AccountDisabled` (privacy deletion schedule), `KindleSent` (history view) |
| Calls | access (`decide`, capabilities, openings), content (section index) |
| Called by | web via gateway |

## Reading session flow

1. Reader opens a book → library asks access `decide(Read)`.
2. On Allow: library creates/reuses the reading session, requests chapter index preparation (`Prepared` = section index fetched), then asks access to consume the opening (read-once) and to issue a capability.
3. Web uses the capability against content; heartbeat renews through library → access.
4. Close/idle-expiry ends the session.

## Privacy

All rows keyed by `owner_id` from the verified subject, never from request bodies. Row-level
security policies enforce owner = session owner at the database. Export and deletion are supported.

See [domain model](domain-model.md) · [API](api-contract.md) · [state machines](state-machines.md) · [tests](test-plan.md) · [anchor ADR](../../04-architecture/adr/0015-annotation-anchors.md).
