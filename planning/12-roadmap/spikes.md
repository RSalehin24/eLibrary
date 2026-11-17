# Spikes (time-boxed risk reducers, all in P0)

Status: DRAFT

Each spike answers one question, produces a short written result and an ADR update. Throwaway code stays out of the main workspace.

| ID | Question | Method | Success criteria | Box | Feeds |
|---|---|---|---|---|---|
| S-01 | Can a Rust search engine with custom Bengali analysis hit the relevance bar, or should we use Postgres trigram? | Also build an `icu_collator` `bn` collator and confirm it does not silently fall back to root collation; index 2,000 real catalog rows; implement analyzer chain; run 100 judged queries (seed of the final set) on both options | MRR@10 ≥ 0.85, p95 ≤ 100 ms, rebuild ≤ 10 min | 1 wk | ADR-0008 |
| S-02 | Does Angular + Angular Material (M3) cover our screens and Bengali needs? | Pin the current Angular and Material versions; check the official component list against the [screen inventory](../08-ux/screens/README.md) and design-system table; build book page + minimal reader; test SSR/hydration, generated TS client from the Rust schema, selection/highlight offsets on Bengali conjuncts, keyboard, screen reader (NVDA/VO), mobile Safari; confirm ESLint/tsconfig rules from coding standards §16 exist and work; build the missing components (navigation rail, navigation bar, side sheet, search) from CDK + tokens as proof; read the official Angular Material theming pages in a browser (the docs site is client-rendered) and confirm `mat.theme` options, M3 coverage per component, and Expressive status | no blocking component gaps (gaps composable from CDK), axe 0 serious/critical, budgets met, rules enforced | 1.5 wk | ADR-0014 (reopen if failed), dependency register |
| S-03 | Can Rust shape Bengali for generated covers and are EPUBs valid and deterministic? | `rustybuzz` (last release 2024-11: also look for a maintained successor) + `resvg` cover on 30 titles; `zip` writer with fixed metadata; epubcheck | no tofu, legible, byte-identical rebuilds, epubcheck 0 errors | 1 wk | builder README |
| S-04 | Can TLA+/Alloy run in CI and export traces for model-based tests? | Install Java + TLC; run the three existing models; export a trace to JSON and replay in a toy Rust state machine | models run < 5 min; trace replay works | 0.5 wk | ADR-0010, G2 |
| S-05 | What can we legally and technically do with the source? | Review source terms; ask the owner; fetch policy test (GET only) of locked chapter behavior | written answer or documented risk acceptance | 1 wk elapsed | D-03 |
| S-06 | Can we verify legacy Django PBKDF2 hashes and map TOTP devices? | Export 5 test users; verify in Rust; decode OTP secrets | 5/5 verify; TOTP codes validate | 0.5 wk | REQ-MIG-003 |
| S-07 | Is a Postgres queue/outbox adequate? | Benchmark `SKIP LOCKED` claims, lease sweeper, outbox relay at 100 events/s with 4 workers | no duplicate claims, p99 pickup < 1 s | 0.5 wk | ADR-0005 |

Results are recorded as `12-roadmap/spike-results/S-0x.md` (numbers, decision, ADR link). A spike that fails changes the plan before any production code depends on the assumption.
