# Requirements — Library / personal data (LIB)

Status: DRAFT · Service: [reader](../05-services/reader/README.md) (progress, bookmarks, highlights, notes, reading sessions) and [catalog](../05-services/catalog/README.md) (shelves). D-27: the former library service is split between them; ids keep the LIB prefix

- **REQ-LIB-001** · MUST · inv: INV-LIB-001 · verify: model, prop · Reading progress is one record per (account, book) with a monotonic revision; a stale write never overwrites a newer one.
- **REQ-LIB-002** · MUST · inv: INV-LIB-002 · verify: prop, gold · Bookmarks, highlights and notes are stored with an `Anchor` (section id + text quote + offsets). When a book version changes (`book.version_changed`) they are re-anchored against the new reading copy; those that cannot be placed become `Orphaned` and stay visible, never deleted.
- **REQ-LIB-003** · MUST · inv: INV-LIB-003 · verify: type, e2e · Personal data is readable and writable only by its owner; account deletion by an admin removes it; a user can export their own reading data as JSON.
- **REQ-LIB-004** · SHOULD · inv: INV-LIB-004 · verify: prop · "My Books" is a shelf in catalog listing books saved by the account; adding twice is idempotent. It never grants access. Shelf mutations need `browse`, a signed-in session and a non-demo account.
- **REQ-LIB-005** · MUST · inv: INV-LIB-005 · verify: e2e · The notes page lists annotations with deep links that open the exact location, or show the orphan state.
- **REQ-LIB-006** · SHOULD · inv: INV-LIB-006 · verify: prop · Saved filters round-trip: applying a saved filter reproduces the identical query.
- **REQ-LIB-007** · SHOULD · inv: INV-LIB-007 · verify: unit · An account can export its notes and highlights as Markdown and JSON.
- **REQ-LIB-008** · MUST · inv: INV-LIB-008 · verify: model, e2e · A reading session is created only after identity allows `read` and a reading ticket is redeemed; at most one active session per (account, book, device class); heartbeat expiry ends the session.
