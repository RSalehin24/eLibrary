# Requirements — Library / personal data (LIB)

Status: DRAFT · Service: [library](../05-services/library/README.md)

- **REQ-LIB-001** · MUST · inv: INV-LIB-001 · verify: model, prop · Reading progress is one record per (account, book) with a monotonic revision; a stale write never overwrites a newer one.
- **REQ-LIB-002** · MUST · inv: INV-LIB-002 · verify: prop, gold · Bookmarks, highlights and notes are stored with an `Anchor` (section id + text quote + offsets). When an artifact set changes they are re-anchored; those that cannot be placed become `Orphaned` and stay visible, never deleted.
- **REQ-LIB-003** · MUST · inv: INV-LIB-003 · verify: type, e2e · Personal data is readable and writable only by its owner; account deletion removes it (and emits a deletion event).
- **REQ-LIB-004** · SHOULD · inv: INV-LIB-004 · verify: prop · "My Books" lists books created by or saved to the account; adding twice is idempotent.
- **REQ-LIB-005** · MUST · inv: INV-LIB-005 · verify: e2e · The notes page lists annotations with deep links that open the exact location, or show the orphan state.
- **REQ-LIB-006** · SHOULD · inv: INV-LIB-006 · verify: prop · Saved filters round-trip: applying a saved filter reproduces the identical query.
- **REQ-LIB-007** · SHOULD · inv: INV-LIB-007 · verify: unit · An account can export its notes and highlights as Markdown and JSON.
- **REQ-LIB-008** · MUST · inv: INV-LIB-008 · verify: model, e2e · A reading session is created only after access grants a read decision; at most one active session per (account, book, device class); heartbeat expiry ends the session.
