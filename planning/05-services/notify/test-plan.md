# notify — test plan

Status: DRAFT

| ID | Level | What | Invariant |
|---|---|---|---|
| TST-NTF-001 | model | `Outbox.tla` (duplicate delivery, redelivery) | INV-NTF-001, INV-PLT-009 |
| TST-NTF-002 | prop | Same event delivered N times (random interleavings, crash points) → ≤ 1 `Sent` per `(event, kind)` | INV-NTF-001 |
| TST-NTF-003 | prop | Kindle send only with Allow ∧ address owned ∧ size ≤ limit; all other combinations rejected with the expected reason | INV-NTF-002 |
| TST-NTF-004 | unit | All template keys exist in `bn` and `en`; typed variables | INV-NTF-003 |
| TST-NTF-005 | type+unit | Links/tokens never appear in log output or error text (log capture + grep, `Secret` has no Debug) | INV-NTF-004 |
| TST-NTF-006 | fault | Provider outage 24 h → Failed + admin notice; account creation unaffected | REQ-NTF-001 |
| TST-NTF-007 | e2e | Invite → mail sink receives a working link once | REQ-NTF-001 |
