# Verification ladder

Status: DRAFT

Rebuilt 2026-11-19 for the six-service design. Kept from v1: the ladder; changed: components, capability verification replaced by identity-checked tickets, Compose added to L7 and L8. No level is evidenced yet: no code exists and no model has been run (Java not installed).

Components get the strongest affordable level. Higher levels cost more, so they are
reserved for code where a bug is costly and the logic is small and pure.

| Level | Technique | Tooling | Applied to |
|---|---|---|---|
| L0 | Type-driven design, lints | `rustc`, `clippy` (deny set), `cargo deny` | Everything |
| L1 | Database constraints | PostgreSQL CHECK, UNIQUE, EXCLUDE, FK within a service, row-level policies | Every table |
| L2 | Unit + property tests | `proptest`, `insta` snapshots | All pure logic |
| L3 | Model-based testing | Implementation steps compared to the TLA+ state machine | Job lifecycle, account lifecycle, tickets, outbox, publish saga |
| L4 | Exhaustive model checking | TLA+/TLC (or Apalache), Alloy Analyzer | State machines, authorization, protocols |
| L5 | Deductive/bounded proof of code | `kani` (bounded model checker), optionally `verus`/`creusot` | identity `decide`, `Normalizer` idempotency bounds, ticket check, sanitizer idempotency, section-tree builder |
| L6 | Corpus measurement | Gold corpus, judged queries, metrics as CI gates | Extraction, structure, search |
| L7 | Fault injection | Container kill, network cut, source and mail fixtures, disk-full, duplicate delivery on the ephemeral Compose stack ([fault injection](../09-testing/fault-injection.md)) | Job queue, outbox, publish saga, reader copy build |
| L8 | Operational drills | Monthly backup restore into an empty stack, rolling restart and rollback to the previous image, secret and cookie rotation | Backups, deploys, secrets |

## Assignment by component

| Component | Minimum level | Why |
|---|---|---|
| identity `decide`, ticket verify | L5 + L4 | Security core; small and pure |
| Job lease, outbox producer and consumers, read-once ticket, publish saga | L4 + L3 | Concurrency and idempotency |
| Identity flows (link, login, TOTP, session) | L4 (model) + L2 | Auth state machine |
| Version lifecycle, reading copy lifecycle, delivery | L4 + L1 + L2 | State machines with an external effect |
| Sanitizer, anchors, normalizer, duplicate key | L2 + L5 on core functions + L6 | Pure, hostile input |
| Section tree, conservation, EPUB builder | L2 + L5 on core functions + L6 | Pure, structural |
| Classifiers and entity extraction | L6 (+L2 for helpers) | Heuristic by nature |
| Search analyzer (PostgreSQL FTS configuration) | L6 + L2 | Relevance is measured |
| HTTP handlers, gateway routing | L0 + L1 + L2 (+contract tests, e2e) | Thin glue |
| Compose stack (ports, limits, users, networks) | L0 static checks + e2e | Configuration is code (Q11) |
| Backups | L8 | Only a restore proves a backup |
| UI (including SSR pages) | L0 (exhaustive states) + E2E + a11y scans + review | Human judgement |

## Rule: no unverified claim

A requirement may name a mechanism only if the mechanism exists in the repository
and runs in CI. The checker (`tools/check_plan.py`) verifies the *plan* side of
this; CI gates in [quality-gates](quality-gates.md) verify the *code* side.
