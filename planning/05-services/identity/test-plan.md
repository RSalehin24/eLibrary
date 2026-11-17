# identity — test plan

Status: DRAFT

| ID | Level | What | Invariant |
|---|---|---|---|
| TST-IDN-001 | model | `AccountLifecycle.tla` checked (status graph, link single-use, supersede, TOTP, revoke) | INV-IDN-001/002/004/005/008 |
| TST-IDN-002 | prop | Random sequences of {invite, issue, consume, expire, suspend, login, logout} never reach a state forbidden by the model (trace replay) | INV-IDN-001/005/008 |
| TST-IDN-003 | unit | Link consume races: two concurrent consumes → exactly one success | INV-IDN-002 |
| TST-IDN-004 | type | Compile-fail tests (`trybuild`): constructing `Session<Authenticated>` without TOTP when required; formatting `Secret` | INV-IDN-003/004 |
| TST-IDN-005 | prop | Unknown vs known account responses equal in status/body/shape; timing within bucket (statistical, tolerance documented) | INV-IDN-006 |
| TST-IDN-006 | e2e | Invite → email (sink) → set password → login → TOTP setup → login with TOTP | REQ-IDN-001/004 |
| TST-IDN-007 | e2e | Suspend revokes active session within one request; password change revokes others | INV-IDN-005 |
| TST-IDN-008 | unit | Kindle address validation and limit 5 | INV-IDN-007 |
| TST-IDN-009 | unit | Legacy PBKDF2 hash verifies; rehash to Argon2id; wrong password rejected | INV-MIG-003 |
| TST-IDN-010 | fuzz | Token and email parsers; no panic | INV-PLT-004 |
| TST-IDN-012 | prop+unit | TOTP replay: the same valid code verified twice (and an earlier step after a later one) is rejected; concurrent verifications of one code accept exactly once (row lock on `last_accepted_step`) | INV-IDN-009 |
| TST-IDN-011 | e2e | Demo session cannot change profile/password (403 `forbidden_demo`) | INV-ACC-007 |
