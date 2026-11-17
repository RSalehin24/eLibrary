# Spikes (time-boxed risk reducers, all in P0)

Status: DRAFT

Each spike answers one question, produces a short written result and an ADR update. Throwaway code stays out of the main workspace.

| ID | Question | Method | Success criteria | Box | Feeds |
|---|---|---|---|---|---|
| S-01 | Can a Rust search engine with custom Bengali analysis hit the relevance bar, or should we use Postgres trigram? | Index 2,000 real catalog rows; implement analyzer chain; run 100 judged queries (seed of the final set) on both options | MRR@10 ≥ 0.85, p95 ≤ 100 ms, rebuild ≤ 10 min | 1 wk | ADR-0008 |
| S-02 | Rust SSR UI + reader: accessible, selectable, fast enough? | Build book page + minimal reader in Leptos; test selection/highlight offsets on Bengali conjuncts, keyboard, screen reader (NVDA/VO), mobile Safari | all pass or reader moves to TS/WASM island | 1.5 wk | ADR-0014, D-02 |
| S-03 | Can Rust shape Bengali for generated covers and are EPUBs valid and deterministic? | `rustybuzz` + `resvg` cover on 30 titles; `zip` writer with fixed metadata; epubcheck | no tofu, legible, byte-identical rebuilds, epubcheck 0 errors | 1 wk | builder README |
| S-04 | Can TLA+/Alloy run in CI and export traces for model-based tests? | Install Java + TLC; run the three existing models; export a trace to JSON and replay in a toy Rust state machine | models run < 5 min; trace replay works | 0.5 wk | ADR-0010, G2 |
| S-05 | What can we legally and technically do with the source? | Review source terms; ask the owner; fetch policy test (GET only) of locked chapter behavior | written answer or documented risk acceptance | 1 wk elapsed | D-03 |
| S-06 | Can we verify legacy Django PBKDF2 hashes and map TOTP devices? | Export 5 test users; verify in Rust; decode OTP secrets | 5/5 verify; TOTP codes validate | 0.5 wk | REQ-MIG-003 |
| S-07 | Is a Postgres queue/outbox adequate? | Benchmark `SKIP LOCKED` claims, lease sweeper, outbox relay at 100 events/s with 4 workers | no duplicate claims, p99 pickup < 1 s | 0.5 wk | ADR-0005 |

Results are recorded as `12-roadmap/spike-results/S-0x.md` (numbers, decision, ADR link). A spike that fails changes the plan before any production code depends on the assumption.
