# eLibrary — ground-up rebuild plan

Status: DRAFT · v0.2 · Owner: Reyanus Salehin · Six services (D-31) · Updated 2026-11-19

This folder is the single source of truth for rebuilding the Bangla Library
platform from scratch in Rust, as independent services. **No product code is
written until the gates in [12-roadmap](12-roadmap/gates.md) say so.**

## The one rule

> Every requirement has an ID, every ID names the invariant that protects it,
> and every invariant names the mechanism (type, database constraint, formal
> model, property test, gold-corpus metric) that enforces it.

`python3 planning/tools/check_plan.py` enforces this. It must pass before any
plan change is accepted, and it regenerates the
[traceability matrix](02-requirements/traceability.generated.md).

## Start here

| File | Purpose |
|---|---|
| [STATUS.md](STATUS.md) | current stage, next action, blockers — resume from here |
| [DECISIONS.md](DECISIONS.md) | decisions already made |
| [INCONSISTENCIES.md](INCONSISTENCIES.md) | conflicts between rules and plan, with resolutions |
| [00-charter/engineering-philosophy.md](00-charter/engineering-philosophy.md) | language (Rust) and the rules every change follows |
| [00-charter/working-agreement.md](00-charter/working-agreement.md) | how we work: ask at decision points, recommend one option, update docs in the same change, commit only when asked |

## What "no errors after development" means here

Read [03-correctness/claims-and-limits.md](03-correctness/claims-and-limits.md)
first. Short version: we cannot prove arbitrary software error-free. We make
whole error classes *unrepresentable*, *model-check* the concurrent and
security-critical parts, and *measure* the parts that depend on the outside
world (the scraped source site, Bengali text) against a labeled corpus.

## Reading order

| # | Folder | Question it answers |
|---|---|---|
| 00 | [charter](00-charter/) | What are we building, for whom, what is out of scope? |
| 01 | [discovery](01-discovery/) | What exists today, what to keep, what went wrong before? |
| 02 | [requirements](02-requirements/) | Exactly what must be true? (IDs, invariants, verification) |
| 03 | [correctness](03-correctness/) | How do we make errors impossible or detectable? |
| 04 | [architecture](04-architecture/) | Services, data ownership, communication, ADRs |
| 05 | [services](05-services/) | Per-service domain model, API, state machines, tests |
| 06 | [data](06-data/) | Gold corpus, seed and fixtures; nothing is migrated (D-32) |
| 07 | [contracts](07-contracts/) | HTTP and event contracts (the generated-code source) |
| 08 | [ux](08-ux/) | Information architecture, flows, design system, Bengali typography |
| 09 | [testing](09-testing/) | Test strategy and pyramids |
| 10 | [security](10-security/) | Threat model, authorization, abuse, legal |
| 11 | [operations](11-operations/) | Environments, CI/CD, observability, runbooks |
| 12 | [roadmap](12-roadmap/) | Phases, exit gates, spikes |

## Status of decisions

Decisions are in [DECISIONS.md](DECISIONS.md) (D-01..D-52).
[04-architecture/open-decisions.md](04-architecture/open-decisions.md) holds only the open owner points.

## Conventions

- Requirement: `REQ-<DOM>-NNN`; invariant: `INV-<DOM>-NNN`; test: `TST-<DOM>-NNN`.
- Domains: `IDN CAT RDR ING GWY NTF WEB PLT NFR`.
- Every doc starts with `Status:` (`DRAFT`, `REVIEW`, `ACCEPTED`). `ACCEPTED`
  docs may not contain `TBD`, `TODO` or `???` (the checker enforces this).
