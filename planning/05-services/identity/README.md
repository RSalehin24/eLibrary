# identity

Status: DRAFT (six-service design, D-31, D-35, D-37, D-38, D-40, D-41, D-44)

Who is this person, have they proven it, and what may they do? The only place that decides who may do what.

| | |
|---|---|
| Owns | users, credentials (Argon2id), opaque sessions, TOTP, invites and reset links, roles, grants, read-once counters, reading tickets, Kindle addresses, profile images, auth and admin audit log, `events` outbox |
| Does not own | books, publication state (catalog supplies it per decision), files, reading state, mail delivery (notify), shelves ("My Books" never grants access) |
| Requirements | REQ-IDN-001...034 (026 and 027 retired by D-35); table below |
| Emits (outbox) | `user.disabled`, `grant.changed`, `email.requested`; `user.deleted` is **OPEN (O-1)** |
| Consumes | none |
| Calls | none (catalog supplies book state in the request body of `/internal/check`; it is not fetched) |
| Called by | gateway (`/internal/authorize`), catalog, reader, ingestion, notify (`/internal/check`, tickets, users, email requests, events), web through the gateway (public, `/me`, admin routes) |
| Tech | Rust; PostgreSQL database `identity` (one role); Argon2id; TOTP (RFC 6238); [dependency policy](../../04-architecture/dependency-policy.md) governs crates |
| Contract | [HTTP contract](../../07-contracts/http/identity.md), [events](../../07-contracts/events/README.md) |

## Responsibilities

1. Authentication: sign-in, uniform failure, throttling, TOTP two-step, opaque sessions with idle and absolute expiry, immediate revocation.
2. Account lifecycle: invite only, first-admin seed, status machine, deletion on request, own-data export, profile image.
3. Authorization: the pure total `decide` function behind `/internal/authorize` and `/internal/check`; deny by default; roles, scopes, grants, publication-state rule, read-once.
4. Reading tickets: the only minter and verifier (D-37); revocation by grant version, user state and book state.
5. Administration: grants, roles, status, read-once reset, audit log, `admin-reset` host command (D-38), one-time first-admin seed.
6. Publishing `user.disabled`, `grant.changed`, `email.requested` through the outbox in the same transaction as the change.

## Non-responsibilities

No wildcard roles (`is_staff`, `is_superuser`, `admin:full_control` do not exist); no ownership concept; no publication-state storage; no sending of mail; no seed, test or advance route in production builds (REQ-IDN-032); no HTTP route for admin recovery.

## Structure

```
identity/src/
  domain/       Role, Scope, GrantSet, Subject, BookFacts, Decision, decide() (pure, no I/O)
  accounts/     status machine (typestate), invite, reset, credential policy
  sessions/     Session<Pending|Authenticated>, store, expiry, revocation
  totp/         enrolment, verify, replay guard
  tickets/      mint, verify, redeem, read-once counter
  grants/       grant and role administration, grant_version
  images/       profile image validation and store
  audit/        append-only writer (same transaction as the change)
  outbox/       events table writer, GET /internal/events
  http/         public routes, internal routes, route-scope declarations
  cli/          `admin-reset`, `seed-first-admin` (dry-run default, host only)
```

`decide` and the state machines take an injected `Clock`; functions stay about 20 lines with at most 3 parameters ([coding standards](../../03-correctness/coding-standards.md)).

## Failure behaviour

| Failure | Behaviour |
|---|---|
| Database unavailable | every decision fails closed (503 to callers, never Allow); readiness false |
| Mail outage | invite and reset still succeed; the `email.requested` row waits for notify (REQ-NTF-002) |
| Caller sends unknown scope or malformed body | typed 422; unknown route scope is a startup refusal in the caller |
| Consumer misses events | repaired by `GET /internal/users/{id}/grant-version` |
| Audit write fails | the change rolls back (same transaction) |
| Clock injected in tests | all expiry paths deterministic |

## Requirements covered

| REQ | Priority | Where designed | Tests |
|---|---|---|---|
| REQ-IDN-001 | MUST | [state machines](state-machines.md) user status; seed command | TST-IDN-001, 006 |
| REQ-IDN-002 | MUST | link token machine | TST-IDN-002, 003 |
| REQ-IDN-003 | MUST | `Secret<T>`, Argon2id policy ([domain model](domain-model.md)) | TST-IDN-004, 005 |
| REQ-IDN-004 | MUST | TOTP + session machines | TST-IDN-006, 007 |
| REQ-IDN-005 | MUST | TOTP replay guard | TST-IDN-008 |
| REQ-IDN-006 | MUST | re-authentication rule | TST-IDN-009 |
| REQ-IDN-007 | MUST | session machine | TST-IDN-010, 011 |
| REQ-IDN-008 | MUST | uniform responses, throttling | TST-IDN-012 |
| REQ-IDN-009 | MUST | user status table | TST-IDN-001, 013 |
| REQ-IDN-010 | MUST | closed `Role` enum | TST-IDN-014 |
| REQ-IDN-011 | MUST | closed `Scope` enum, grant constraints | TST-IDN-014, 015 |
| REQ-IDN-012 | MUST | grant administration, last-admin rule | TST-IDN-016, 017 |
| REQ-IDN-013 | MUST | `decide` | TST-IDN-018, 019 |
| REQ-IDN-014 | MUST | public route set | TST-IDN-020 |
| REQ-IDN-015 | MUST | decision rules; default grant policy is configuration | TST-IDN-021 |
| REQ-IDN-016 | MUST | `BookFacts` rule | TST-IDN-022 |
| REQ-IDN-017 | MUST | injected clock, status gate | TST-IDN-023 |
| REQ-IDN-018 | MUST | monotonicity | TST-IDN-024 |
| REQ-IDN-019 | MUST | determinism | TST-IDN-025 |
| REQ-IDN-020 | MUST | read-once machine, ticket verify | TST-IDN-026, 027 |
| REQ-IDN-021 | MUST | ticket mint | TST-IDN-028, 029 |
| REQ-IDN-022 | MUST | ticket redemption machine | TST-IDN-027, 030 |
| REQ-IDN-023 | MUST | outbox | TST-IDN-031 |
| REQ-IDN-024 | MUST | `/internal/authorize`, route scope declaration | TST-IDN-032 |
| REQ-IDN-025 | MUST | `mfa_ok` rule for management scopes | TST-IDN-033 |
| REQ-IDN-028 | SHOULD | Kindle address list | TST-IDN-034 |
| REQ-IDN-029 | MUST | audit log | TST-IDN-035, 036 |
| REQ-IDN-030 | MUST | `/me/capabilities` | TST-IDN-037 |
| REQ-IDN-031 | MUST | admin list, resend, delete, export; deletion event **OPEN (O-1)** | TST-IDN-038 |
| REQ-IDN-032 | MUST | seed command, build features | TST-IDN-039 |
| REQ-IDN-033 | MUST | `admin-reset` | TST-IDN-040 |
| REQ-IDN-034 | MUST | profile image validation | TST-IDN-041 |

## Open points touching this service

- **O-1**: `user.deleted` event on account deletion (until decided, reader declares `POST /internal/users/{id}/erase`).
- **C-1**: who may read the audit log (`manage_users` assumed in the contract).
- The role-to-scope table is confirmed (D-45; see [domain model](domain-model.md)); reader preferences (D-48) are not stored here.

See [domain model](domain-model.md) | [API](api-contract.md) | [state machines](state-machines.md) | [tests](test-plan.md).
