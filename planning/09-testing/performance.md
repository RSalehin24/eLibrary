# Performance and capacity

Status: DRAFT (targets from REQ-NFR-002, 003, 005, 014; numbers provisional until the P0 baseline, O-7)

Scale is small (D-29): under 5,000 books, under 50 users, one host, one PostgreSQL, no cache. Load is generated against the ephemeral Compose stack through caddy and the gateway with 5,000 synthetic books ([seed and fixtures](../06-data/seed-and-fixtures.md)). Kept from v1: method, front-end budgets idea. Changed: v1's 50 rps targets are replaced by the REQ-NFR figures.

| Scenario | Load | Target |
|---|---|---|
| Public search | 10 rps sustained, 30 rps burst, mixed Bengali and Latin queries over 5,000 books | p95 at most 250 ms, errors under 0.1% |
| Book detail | 10 rps | p95 at most 300 ms |
| Authorization overhead | every `/api/*` request | gateway plus identity p95 at most 25 ms |
| Open a book (ticket) | 10 concurrent readers | p95 at most 300 ms |
| Whole-book package | 10 concurrent readers, book up to 5 MB | p95 at most 1.5 s |
| Mixed | 20 signed-in sessions, 10 readers, 2 concurrent ingestion jobs | no degradation of reading latency targets while ingestion runs |
| Reading copy build | one 5 MB book | recorded as a baseline (no REQ figure; OPEN: set a target after P0) |
| Outbox | burst of 500 events | drains and the published set equals the reader copy set (REQ-NFR-013); drain time recorded |
| Footprint | stack idle and under load | idle within 4 GB, load within 8 GB; Rust image at most 100 MB, web image at most 50 MB (REQ-NFR-005) |
| Sign-in page first load | cold cache, throttled network | transfers at most 500 KB compressed (REQ-NFR-005) |
| Availability | not load-tested | REQ-NFR-001 (99.5% per month) is observed during the G9 4-week observation, not by a test run |
| Startup | cold stack; one service restart | ready within 90 s; single service within 15 s (REQ-NFR-014) |
| Index rebuild | 5,000 books | recorded as a baseline (OPEN: target after spike S-01) |
| Gold run | corpus of up to 200 books, ingestion stages | recorded; run locally and in nightly only |

Method: k6 scripts in `xtask load`; a one-minute smoke load with relaxed targets in the nightly run, the full load before every release; flame graphs on regression. CSV export of 5,000 rows and a 100-row page are measured for memory (REQ-NFR-006).

Front-end budgets (provisional): LCP at most 2.0 s on a mid-range phone over 4G, CLS under 0.05, SSR first byte included; library pages hydrate without layout shift; the reader bundle size is recorded. Search relevance (MRR, recall) is a SHOULD gate (O-5) fed by the gold judged queries and spike S-01 (Q-1).
