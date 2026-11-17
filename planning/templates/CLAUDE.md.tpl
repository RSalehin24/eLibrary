# eLibrary (Rust rebuild) — project instructions  [template: copy to repo root in phase P1]

Resume work from `planning/STATUS.md` (current stage, next action, blockers). Read it first; do not re-derive earlier decisions (`planning/DECISIONS.md`).

## DECISION REQUESTS — MANDATORY, NEVER VIOLATE
Whenever a decision/approval/choice is needed from the user, ask it with the `AskUserQuestion` tool (selectable in Claude Code): one decision per question, 2–4 concrete options each with a one-line consequence, the recommended option listed first and labeled `(Recommended)` with the reason. Never ask decisions as plain text or hide them in a plan; never proceed on an unanswered decision; record answers in `planning/DECISIONS.md`. If the tool is unavailable, state question, options and recommendation explicitly and wait.

## Coding rules (mandatory)
@AGENTS.md
@crates/AGENTS.md
@web/AGENTS.md

Precedence: the owner's explicit instruction, then the nearest `AGENTS.md` to the edited file, then the root `AGENTS.md`. The rules below apply on top.

## Project facts
- Rust workspace of independent services (identity, access, catalog, content, library, ingestion, notify) + gateway; web UI in TypeScript/Angular with Angular Material (Material Design 3), types generated from the Rust contracts. Contracts are Rust crates; services depend only on `contracts-*`, `platform-*`, `domain-*` (never on each other).
- Plan = design docs: `planning/` (requirements → invariants → mechanisms). Run `python3 planning/tools/check_plan.py` after any plan change.
- Legacy Django app and the `reyan-new-version` branch are read-only reference.

## Hard rules
- No new dependencies (crates, tools, system packages) without the owner's approval; record in `planning/04-architecture/dependency-policy.md`.
- Never weaken lints/tests/types; waivers are dated entries in `planning/12-roadmap/waivers.md`.
- Never commit secrets, `.env`, personal data, third-party book content or the gold corpus.
- Commit/push only when asked; small imperative messages; branch, no force-push, no history rewrite.
- Ambiguity or rule conflict → ask before coding; recommend one option.
- Update affected plan docs in the same change; log deviations in `planning/INCONSISTENCIES.md`.

## Working style
- Read only what you need; delegate broad reading to read-only exploration and keep conclusions.
- End each stage with a short summary in the folder README and `planning/STATUS.md`.
- Report what was changed vs only inspected, and what could not be verified.
