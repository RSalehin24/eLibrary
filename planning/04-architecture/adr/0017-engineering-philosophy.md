# ADR-0017 — Engineering philosophy: the owner's AGENTS.md rules, adapted to Rust

Status: ACCEPTED

## Context
The owner maintains project-agnostic mandatory coding rules (KISS/YAGNI, DRY, SOLID, clean code limits, security, integrity, safety) and a working style (ask at decision points, recommend one option, planning files as design docs, commits only when asked, no dependencies without approval). The plan must obey them rather than introduce its own conventions.

## Decision
Adopt the rules verbatim as the governing philosophy, with the Rust mapping in [engineering philosophy](../../00-charter/engineering-philosophy.md), the process in [working agreement](../../00-charter/working-agreement.md) and the enforceable form in [coding standards](../../03-correctness/coding-standards.md). Conflicts between a rule and the plan are resolved in favor of the rule and logged in INCONSISTENCIES.md.

## Consequences
+ One consistent standard for plan, code and review; rules are checkable (lints, plan check, review checklist).
− Some earlier plan content needed adaptation (parameter limits, dependency approval) — recorded as I-01…I-04.
− Thresholds (20 lines, 3 params, 2 nesting) require tooling confirmation at G1; until verified they are review rules.
