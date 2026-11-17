# access — test plan

Status: DRAFT

| ID | Level | What | Invariant |
|---|---|---|---|
| TST-ACC-001 | model | `access.als` analyzed: AnonymousLimited, ReadNeedsAccount, DeadGrantsIgnored, Monotonic, ManagementNeedsAuthority, UnpublishedHidden | INV-ACC-001/002/004/005/007/009/012 |
| TST-ACC-002 | prop | `decide` property tests mirror the Alloy assertions on randomly generated facts/grants (≥ 1M cases nightly) | same |
| TST-ACC-003 | prop | Order independence: permuting grants never changes `decide` | INV-ACC-010 |
| TST-ACC-004 | kani | `decide` cannot panic; anonymous never gets Read/Download/Send/Admin (bounded proof, bounded grant count 4) | INV-ACC-001/003 |
| TST-ACC-005 | model | `ReadOnce.tla` checked | INV-ACC-006, INV-LIB-008 |
| TST-ACC-006 | e2e | Two devices race to open a read-once book: exactly one succeeds | INV-ACC-006 |
| TST-ACC-007 | fuzz | Capability parser/verifier: forged, truncated, wrong-audience, expired, wrong-book tokens rejected | INV-ACC-008 |
| TST-ACC-008 | unit | Capability TTL cap; clock skew leeway 60 s with fake clock | INV-ACC-008 |
| TST-ACC-009 | db | Grant mutation + audit row atomic (fault injection between statements) | INV-ACC-011 |
| TST-ACC-010 | e2e | Demo session denied every mutating admin route (table-driven over the route list) | INV-ACC-007 |
| TST-ACC-011 | e2e | Admin without TOTP completed is denied management routes | INV-ACC-009 |
| TST-ACC-012 | prop | Unpublished books: non-privileged subject gets `Unpublished` deny for all actions | INV-ACC-012 |
| TST-ACC-013 | unit | Default policy applies to Active non-demo accounts only | REQ-ACC-002 |
