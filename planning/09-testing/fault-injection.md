# Fault injection catalog

Status: DRAFT

Each scenario states the injected fault, the expected behavior, and the asserted invariant. Automated in nightly runs; selected ones run on every PR.

| ID | Fault | Expected | Invariant |
|---|---|---|---|
| FI-01 | Kill ingestion worker after each pipeline step (every cut point) | Job resumes from cursor; identical outputs; ≤ 1 publish | INV-ING-010/016 |
| FI-02 | Kill between `content.put_document` and `catalog.publish` | Book stays Draft; saga resumes; nothing half-visible | INV-CON-001, INV-ING-016 |
| FI-03 | Duplicate event delivery ×5 / reordered across aggregates | One effect per event; projections converge | INV-PLT-009 |
| FI-04 | Crash between DB commit and outbox relay send | Event delivered after restart | INV-PLT-009 |
| FI-05 | Mail provider timeout / 5xx for 24 h | Retry then Failed + admin notice; account flows unaffected | INV-NTF-001 |
| FI-06 | Access service down | Public pages OK; reads/admin fail closed with typed error; existing capabilities valid ≤ TTL | INV-ACC-008, INV-ACC-003 |
| FI-07 | Identity down | Anonymous browsing OK; login fails typed; assertions cached ≤ 5 s | REQ-IDN-005 |
| FI-08 | Content store: corrupt blob (bit flip), missing blob | Hash check fails → typed error, alert, never serve wrong bytes | INV-CON-001 |
| FI-09 | Disk full during build | Build fails typed; no partial set visible; GC recovers | INV-CON-001 |
| FI-10 | Postgres failover / connection reset mid-transaction | Retry with idempotency; no duplicate rows | INV-PLT-003 |
| FI-11 | Clock skew ±5 min between services | Capability leeway honored; beyond leeway denied; no panics | INV-ACC-008, INV-PLT-010 |
| FI-12 | Source returns: 404, 429, 5xx bursts, timeouts, truncated body, redirect loop, 50 MiB page, locked placeholder | Typed outcomes; bounded time; reviews raised | INV-ING-006/012 |
| FI-13 | Search index corrupted/deleted | Rebuild from events; browse works meanwhile | INV-DSC-005 |
| FI-14 | Two admins edit the same book concurrently | Second gets `stale_revision`; no lost update | INV-CAT-004 |
| FI-15 | Two devices open read-once book simultaneously | Exactly one succeeds | INV-ACC-006 |
| FI-16 | Capability replayed after expiry / for another book | Rejected | INV-ACC-008 |
| FI-17 | Large request bodies, slowloris, many connections | Limits enforced; service stays responsive | INV-PLT-005 |
| FI-18 | Restore database from backup into a fresh host | System consistent; projections reconcile; drift metrics zero | INV-PLT-008 |
