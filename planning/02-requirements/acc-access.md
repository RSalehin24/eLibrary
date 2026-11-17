# Requirements — Access (ACC)

Status: DRAFT · Service: [access](../05-services/access/README.md)

- **REQ-ACC-001** · MUST · inv: INV-ACC-001 · verify: model, prop · Anonymous subjects may Search, view catalog metadata and view Preview. They can never Read full text, Download, SendToKindle, or perform any management action.
- **REQ-ACC-002** · MUST · inv: INV-ACC-002 · verify: model, prop · Reading full text requires an authenticated, Active account and an applicable grant (global, category, author or book scope), or the book is owned by the account. Default grants for new accounts are configuration, not code (decision D-04).
- **REQ-ACC-003** · MUST · inv: INV-ACC-003 · verify: model, type · Authorization is deny-by-default. `decide` is total and returns `Allow` or `Deny(reason)`; there is no code path that authorizes without calling it.
- **REQ-ACC-004** · MUST · inv: INV-ACC-004 · verify: model, prop · Expired or revoked grants have no effect, evaluated against an injected clock.
- **REQ-ACC-005** · MUST · inv: INV-ACC-005 · verify: model, prop · Adding a grant never removes an existing permission (monotonicity). The only non-monotonic rule is read-once consumption.
- **REQ-ACC-006** · MUST · inv: INV-ACC-006 · verify: model, prop, e2e · Read-once allows exactly one opening per account and book. A reconnect, refresh or proxy retry within the same reading session is not a new opening. A failed preparation does not consume the opening.
- **REQ-ACC-007** · MUST · inv: INV-ACC-007 · verify: model, e2e · Demo accounts and accounts without management grants cannot invoke mutating administrative actions.
- **REQ-ACC-008** · MUST · inv: INV-ACC-008 · verify: type, prop, fuzz · Capabilities are signed, expire within 5 minutes, and are bound to subject, book, artifact set and action. Verifiers validate them offline with the public key.
- **REQ-ACC-009** · MUST · inv: INV-ACC-009 · verify: model, e2e · Management actions require a session that completed TOTP whenever the account requires TOTP.
- **REQ-ACC-010** · MUST · inv: INV-ACC-010 · verify: prop · Decisions do not depend on grant order and are deterministic for identical inputs.
- **REQ-ACC-011** · MUST · inv: INV-ACC-011 · verify: db, e2e · Every grant creation, change and revocation is recorded in the append-only audit log in the same transaction.
- **REQ-ACC-012** · SHOULD · inv: INV-ACC-012 · verify: model, prop · Unpublished (Draft/Archived) books are visible only to subjects with metadata or management grants; to others they behave as nonexistent.
