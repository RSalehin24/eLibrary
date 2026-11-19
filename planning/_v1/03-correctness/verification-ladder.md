# Verification ladder

Status: DRAFT

Components get the strongest affordable level. Higher levels cost more, so they are
reserved for code where a bug is costly and the logic is small and pure.

| Level | Technique | Tooling | Applied to |
|---|---|---|---|
| L0 | Type-driven design, lints | `rustc`, `clippy` (deny set), `cargo deny` | Everything |
| L1 | Database constraints | PostgreSQL CHECK, UNIQUE, EXCLUDE, FK within a service, row-level policies | Every table |
| L2 | Unit + property tests | `proptest`, `insta` snapshots | All pure logic |
| L3 | Model-based testing | Implementation steps compared to the TLA+ state machine | Job lifecycle, sessions, outbox |
| L4 | Exhaustive model checking | TLA+/TLC (or Apalache), Alloy Analyzer | State machines, authorization, protocols |
| L5 | Deductive/bounded proof of code | `kani` (bounded model checker), optionally `verus`/`creusot` | `access::decide`, `Normalizer` idempotency bounds, capability verify, section-tree builder |
| L6 | Corpus measurement | Gold corpus, judged queries, metrics as CI gates | Extraction, structure, search |
| L7 | Fault injection | Kill/timeout/disk-full/duplicate-delivery tests, toxiproxy | Orchestration, outbox, builders |
| L8 | Operational drills | Restore, rollback, key rotation | Backups, migration, secrets |

## Assignment by component

| Component | Minimum level | Why |
|---|---|---|
| `access::decide`, capability verify | L5 + L4 | Security core; small and pure |
| Job lifecycle, outbox relay/consumers, read-once | L4 + L3 | Concurrency |
| Identity flows (link, login, TOTP, session) | L4 (model) + L2 | Auth state machine |
| Section tree, conservation, builders | L2 + L5 on core functions + L6 | Pure, structural |
| Classifiers & entity extraction | L6 (+L2 for helpers) | Heuristic by nature |
| Search analyzer | L6 + L2 | Relevance is measured |
| HTTP handlers | L0 + L1 + L2 (+contract tests) | Thin glue |
| UI | L0 (exhaustive states) + E2E + a11y scans + review | Human judgement |

## Rule: no unverified claim

A requirement may name a mechanism only if the mechanism exists in the repository
and runs in CI. The checker (`tools/check_plan.py`) verifies the *plan* side of
this; CI gates in [quality-gates](quality-gates.md) verify the *code* side.
