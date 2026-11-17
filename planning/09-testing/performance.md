# Performance and capacity

Status: DRAFT

| Scenario | Load | Target |
|---|---|---|
| Public search | 50 rps, mixed Bengali/Latin queries from the judged set | p95 ≤ 250 ms server-side, error rate < 0.1% |
| Book page SSR | 50 rps | p95 TTFB ≤ 300 ms (cache cold), ≤ 80 ms (warm) |
| Chapter fetch | 20 rps, 50 KB–300 KB | p95 ≤ 400 ms |
| Reader open | 5 rps | p95 ≤ 800 ms to first paint of content |
| Ingestion | 4 concurrent jobs, 400-chapter book | pure stages ≤ 10 s CPU; end-to-end bounded by source politeness (1 rps) |
| Gold run | 200 books, stages 2–6 | ≤ 5 min on CI hardware (keeps the gate fast) |
| Index rebuild | 2,000 books + previews | ≤ 10 min |
| Outbox | 100 events/s sustained | oldest pending age < 1 s p99 |
| Memory | each service at load | < 512 MiB RSS (ingestion < 1 GiB) |

Methods: k6 scripts in `xtask load`; flame graphs on regressions; budgets enforced by a smoke load in CI (1 min, relaxed targets) and full load before releases.

Front-end budgets: public page ≤ 100 KB JS (gz) (0 for browse/search with progressive enhancement), LCP ≤ 2.0 s on mid-range mobile over 4G, CLS < 0.05, reader JS ≤ 250 KB.
