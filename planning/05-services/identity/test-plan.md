# identity - test plan

Status: DRAFT

| ID | Level | What | Maps to |
|---|---|---|---|
| TST-IDN-001 | model | `AccountLifecycle.tla` checked (status graph, token single-use, supersede, TOTP, revoke) | INV-IDN-001/002/004/005/008 |
| TST-IDN-002 | prop | Random sequences of invite, issue, consume, expire, suspend, sign-in, sign-out never reach a forbidden state (trace replay) | INV-IDN-001/005/008 |
| TST-IDN-003 | unit | Two concurrent token consumes: exactly one success | INV-IDN-002 |
| TST-IDN-004 | type | `trybuild`: `Session<Authenticated>` unconstructible without TOTP when required; formatting `Secret` fails | INV-IDN-003/004 |
| TST-IDN-005 | prop | Reset request and sign-in: unknown vs known account give equal status, body shape and timing bucket | INV-IDN-006 |
| TST-IDN-006 | e2e | Invite -> mail sink -> accept -> sign in -> TOTP setup -> sign in with TOTP | REQ-IDN-001/004 |
| TST-IDN-007 | e2e | Suspend revokes a live session within one request; password change revokes others | INV-IDN-005 |
| TST-IDN-008 | unit | Kindle address validation and limit 5 | INV-IDN-007 |
| TST-IDN-009 | unit | Legacy PBKDF2 hash verifies, rehashes to Argon2id, wrong password rejected | REQ-MIG-003 |
| TST-IDN-010 | fuzz | Token, email and cookie parsers do not panic | INV-PLT-004 |
| TST-IDN-011 | e2e | Demo session cannot change profile, password, shelf; no download or Kindle (403 `forbidden_demo`) | INV-ACC-007, REQ-IDN-007 |
| TST-IDN-012 | prop+unit | TOTP replay rejected; concurrent verifications of one code accept once | INV-IDN-009 |
| TST-IDN-013 | model | `access.als` analysed against the new scope table: anonymous limited, dead grants ignored, monotonic, management needs authority, unpublished hidden | INV-ACC-001/002/004/005/007/009/012 |
| TST-IDN-014 | prop | `decide` mirrors the model on random facts/grants; permuting grants never changes the result; cannot panic | INV-ACC-003/010 |
| TST-IDN-015 | e2e | Startup test: a service registering a route without a scope declaration fails; unregistered path through `/internal/authorize` returns 403 | REQ-ACC-003 |
| TST-IDN-016 | unit | Role table has no wildcard: no role contains every scope; `admin` lacks `operate`; test fails when a role or scope is added without updating the table | REQ-ACC-001/003 |
| TST-IDN-017 | e2e | A user cannot self-grant, cannot edit own roles, cannot grant `manage_users` at book level; last admin cannot be disabled | REQ-ACC-007 |
| TST-IDN-018 | db | Grant/role/status mutation and audit row commit together (fault injection); `audit_log` rejects UPDATE/DELETE | INV-ACC-011 |
| TST-IDN-019 | e2e | Admin without completed TOTP denied `manage_users` routes | INV-ACC-009 |
| TST-IDN-020 | e2e | Read-once race: two concurrent consumes -> one success; same ticket retry allowed; consume skipped when reader reports missing copy | INV-ACC-006 |
| TST-IDN-021 | contract | `/internal/events` cursor: ordered, no duplicates inside a page, empty page keeps cursor, restart from cursor reproduces events | brief section 3 (no REQ id yet) |
| TST-IDN-022 | e2e | Demo sign-in is POST only, rate limited, honours the disable flag, sees only `demo_set` books | REQ-IDN-007 |
| TST-IDN-023 | unit | Unpublished book denies read/preview/download for every role | INV-ACC-012 |
