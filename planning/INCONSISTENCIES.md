# Inconsistencies and rule conflicts

Status: DRAFT

Where the plan and the owner's rules disagreed, or an earlier plan statement was corrected. Newest last. `Resolution` states what the plan now says.

| ID | Found | Conflict | Resolution | Needs owner |
|---|---|---|---|---|
| I-01 | 2026-11-17 | Rule: no dependencies without approval, prefer std. The first plan draft named ~25 crates as if chosen (axum, sqlx, tantivy, leptos…). | All crates are `PROPOSED` in the [dependency register](04-architecture/dependency-policy.md); nothing is approved or installed; ADR-0018 adds an approval step to P1 and a plan/CI check. Earlier docs that name crates are descriptive candidates. | Approve the foundational set at P1 start |
| I-02 | 2026-11-17 | Rule: max 3 parameters. The access README showed `decide(subject, action, resource, grants, policy, now)` (6). | Changed to a single `DecisionInput` struct plus the policy handle (`decide(input, policy) -> Decision`); same applies to all pseudo-code in service docs. Lint threshold planned in coding standards. | no |
| I-03 | 2026-11-17 | Rule wording is OOP/SOLID (classes, inheritance language); Rust has traits, no inheritance. | Mapped explicitly in [engineering philosophy](00-charter/engineering-philosophy.md): composition, traits as interfaces, enums for open/closed, conformance suites for substitutability. | Confirm mapping is acceptable |
| I-04 | 2026-11-17 | Rule: ~20-line functions, ≤ 2 nesting levels. Some plan designs (pipeline stages, classification decoder) describe long algorithms. | Stage functions are composed of small named functions; thresholds enforced by clippy settings. The exact lint names/config keys are **to verify** at G1 against the installed clippy (not asserted as fact). | Confirm hard cap 30 lines / threshold values |
| I-05 | 2026-11-17 | `AGENTS.md` is git-ignored in this repository (commit 08fc99f); the owner's rules live in the PC Setup project. | Rules are restated in `planning/00-charter` (tracked); templates for `CLAUDE.md`/`crates/AGENTS.md` in `planning/templates/`; P1 decides whether the new codebase tracks `AGENTS.md`. | Decide at P1 |
| I-06 | 2026-11-17 | Plan used decision ids D-01…D-10 for open questions; owner's convention is a numbered decision *log*. | D-01…D-10 stay as question ids in open-decisions; answered ones move to `DECISIONS.md`; new owner-level decisions continue at D-11. | no |
| I-07 | 2026-11-17 | Plan gates referenced CI jobs (Q1–Q9) though no CI exists and no Rust/Java is installed here. | Gates are specifications; Q10 (dependency register check) added; formal models labeled **unchecked** until run. | no |
| I-08 | 2026-11-17 | Rule: "Done = build, lint, type-check, tests pass". For a plan-only repository there is no build. | For planning, "done" = `python3 planning/tools/check_plan.py` passes plus self-review; stated in the working agreement. | no |
