# Requirements — Identity (IDN)

Status: DRAFT · Service: [identity](../05-services/identity/README.md)

Line format: `REQ-ID · priority · inv: <invariants> · verify: <methods> · statement`

- **REQ-IDN-001** · MUST · inv: INV-IDN-001 · verify: model, type, e2e · Accounts are created only by an administrator invitation (or the one-time superadmin seed). There is no public sign-up. An account becomes Active only when its owner sets a password through a valid setup link.
- **REQ-IDN-002** · MUST · inv: INV-IDN-002 · verify: model, prop, unit · Setup and reset links are single-use, expire, are bound to one account and a nonce, are stored only as hashes, and a reused, expired or superseded link is rejected with the same response.
- **REQ-IDN-003** · MUST · inv: INV-IDN-003 · verify: type, unit · Passwords are hashed with Argon2id. Secrets (passwords, tokens, TOTP seeds) have no `Display`/`Debug` implementation and cannot be logged.
- **REQ-IDN-004** · MUST · inv: INV-IDN-004 · verify: model, e2e · TOTP enrolment is two-step (set up, then confirm with a valid code). When an account requires TOTP, no authenticated session exists until the second factor succeeds.
- **REQ-IDN-005** · MUST · inv: INV-IDN-005 · verify: model, prop, e2e · Sessions are opaque server-side tokens, hashed at rest, with idle and absolute expiry. Logout, suspension, disablement and password change revoke affected sessions immediately.
- **REQ-IDN-006** · MUST · inv: INV-IDN-006 · verify: prop, e2e · Login and reset endpoints are throttled per account and per address and return indistinguishable responses for unknown and known accounts (no enumeration).
- **REQ-IDN-007** · MUST · inv: INV-ACC-007 · verify: model, e2e · The demo link signs in a dedicated demo account whose sessions can never perform a mutating action (including profile and password changes).
- **REQ-IDN-008** · SHOULD · inv: INV-IDN-007 · verify: type, unit · Accounts may hold up to 5 Kindle addresses; each is a validated `KindleEmail` newtype; only the owner can change them.
- **REQ-IDN-010** · MUST · inv: INV-IDN-009 · verify: model, prop, unit · A TOTP code is single-use: once a time step has been accepted for an account, the same step (and earlier ones) is rejected, so a captured code cannot be replayed (RFC 6238 requirement).
- **REQ-IDN-009** · MUST · inv: INV-IDN-008 · verify: model, unit · Account status transitions follow Invited → Active ⇄ Suspended → Disabled; no other transition exists; every transition emits an event.
