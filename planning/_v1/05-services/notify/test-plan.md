# notify - test plan

Status: DRAFT

| ID | Level | What | Maps to |
|---|---|---|---|
| TST-NTF-001 | model | `Outbox.tla` (duplicate delivery, redelivery, cursor) re-checked for the pull-cursor design | INV-NTF-001, INV-PLT-009 |
| TST-NTF-002 | prop | Same event delivered N times (random interleavings, crash points between insert and cursor) -> at most one `Sent` per `(source, event, kind)` | INV-NTF-001 |
| TST-NTF-003 | prop | Kindle send only when user active, address on profile, published version, size <= limit; every other combination rejected with the expected reason | INV-NTF-002 |
| TST-NTF-004 | unit | All template keys exist in `bn` and `en`; typed variables; incomplete set cannot activate | INV-NTF-003 |
| TST-NTF-005 | type+unit | Links, tokens and addresses never appear in logs or error text (log capture and grep; `Secret` has no Debug) | INV-NTF-004 |
| TST-NTF-006 | fault | Provider outage 24 h -> `failed` plus admin notice; account creation unaffected | REQ-NTF-001 |
| TST-NTF-007 | e2e | Invite -> mail sink receives a working link once; resend supersedes | REQ-NTF-001 |
| TST-NTF-008 | contract | Cursor API consumer: ordered pages, empty page keeps cursor, restart resumes without loss | brief section 3 (no REQ id yet) |
| TST-NTF-009 | e2e | Language selection by user language (`bn`, `en`) | REQ-NTF-003 |
| TST-NTF-010 | unit | Per-address and Kindle daily rate limits | REQ-NTF-001/002 |
| TST-NTF-011 | e2e | Kindle: sender-approval missing -> `rejected` with reason visible in `GET /me/kindle` | REQ-NTF-002 |
| TST-NTF-012 | fault | Crash after provider accept before `Sent`: at most one repeat, documented residual | INV-NTF-001 |
