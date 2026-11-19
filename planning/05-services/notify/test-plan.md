# notify - test plan

Status: DRAFT

Levels: model, prop, unit, type, db, e2e (Compose stack with a mail sink and stub identity/catalog), fault, drill.

| ID | Level | What | Maps to |
|---|---|---|---|
| TST-NTF-001 | model | outbox and pull-cursor model (duplicate delivery, redelivery, crash between insert and cursor) | REQ-NTF-001; INV-NTF-001 |
| TST-NTF-002 | prop | same event delivered N times with random interleavings and crash points: at most one `Sent` per `(source, event, kind)` except after a recorded unknown outcome | REQ-NTF-001; INV-NTF-001 |
| TST-NTF-003 | e2e | invite and reset: one mail per issued link; resend supersedes; mail sink receives a working link once | REQ-NTF-002 |
| TST-NTF-004 | fault | SMTP outage and notify down: account creation and reset request still succeed and the mail is sent after recovery | REQ-NTF-002; INV-NTF-002 |
| TST-NTF-005 | unit | every template exists in `bn` and `en`; language chosen by account; parameters escaped; incomplete set cannot activate | REQ-NTF-003; INV-NTF-003 |
| TST-NTF-006 | type+unit | links, tokens, addresses absent from logs and error text (log capture and search); delivery log holds a masked address | REQ-NTF-004; INV-NTF-004 |
| TST-NTF-007 | model+e2e | Kindle send needs an identity Allow at request and at send, an Active account, an address and a published book; every other combination rejected with the typed reason | REQ-NTF-005; INV-NTF-005 |
| TST-NTF-008 | prop | preflight matrix: format, size at 50 MB -1/exact/+1, address validity, sender approval; every sent mail passed preflight | REQ-NTF-006; INV-NTF-006 |
| TST-NTF-009 | prop+e2e | per-user and per-book quotas hold per window; memory stays under one attachment with concurrent sends at the configured bound | REQ-NTF-007; INV-NTF-007 |
| TST-NTF-010 | prop | retryable errors back off and end in `failed` at the cap; permanent errors never retry; changing error text changes nothing | REQ-NTF-008; INV-NTF-008 |
| TST-NTF-011 | db+e2e | one delivery-log row per attempt; Kindle status reaches catalog and shows on the book's Files tab; report retried until acknowledged | REQ-NTF-009; INV-NTF-009 |
| TST-NTF-012 | drill+e2e | SMTP slow or down and notify unhealthy: other services' latency and results unchanged; timeouts fire; backlog alert raised | REQ-NTF-010; INV-NTF-010 |
| TST-NTF-013 | review+e2e | credentials and sender from secret files; startup refuses bad config; no public route; unauthenticated internal call refused | REQ-NTF-011; INV-NTF-011 |
| TST-NTF-014 | db+unit | retention job deletes only expired terminal rows, in bounded batches | REQ-NTF-012; INV-NTF-012 |
| TST-NTF-015 | contract | cursor consumer: ordered pages, empty page keeps cursor, restart resumes without loss | REQ-NTF-001 |
| TST-NTF-016 | fault | crash after provider accept and before `sent`: at most one repeat (documented residual window) | REQ-NTF-001; INV-NTF-001 |
