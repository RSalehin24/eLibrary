# Working agreement (how we work on this project)

Status: ACCEPTED

Adapted from the owner's `CLAUDE.md` working style. Applies to every contributor, human or AI assistant.

## Asking and deciding

1. **Ask at decision points; recommend one option, do not survey all options.** Every open question has a recommendation in [open decisions](../04-architecture/open-decisions.md).
2. **Ambiguous requirement or rule conflict → ask before coding.** Record the answer in [DECISIONS](../DECISIONS.md) the same day.
3. **Flag deviations from earlier decisions** in [INCONSISTENCIES](../INCONSISTENCIES.md) when they happen, not later.
4. Ask before long research, many parallel agents, installing anything, or changing system configuration. Say why before each privileged or system-level change, and report what changed.

## Planning files are the design docs

- A change to behavior updates the affected plan/docs **in the same change** (requirement, invariant, service doc, test plan).
- Facts live in files: decisions → `DECISIONS.md`, conflicts → `INCONSISTENCIES.md`, progress/next action/blockers → `STATUS.md`.
- Resume work from `STATUS.md`; do not re-derive earlier decisions.
- Read before writing: search the repository and plan first; extend existing definitions instead of adding parallel ones.

## Change discipline

- Minimal change that satisfies the task; no unrelated refactors or files.
- Each change leaves the system working and checks green (`check_plan.py` for the plan; Q-gates for code once it exists).
- Add or update tests with each change (happy path, edge cases, failures); every bug fix gets a regression test.
- Definition of done: build, lint, type-check and tests pass; self-reviewed against [engineering philosophy](engineering-philosophy.md) and the [coding standards](../03-correctness/coding-standards.md); summary states what changed, what was verified, what was not.

## Stage hygiene (keeps context small)

- End each phase/stage by writing a short summary into its folder README and updating `STATUS.md`; the owner may then clear the working context before the next stage.
- Delegate broad reading to read-only exploration and keep only conclusions; read only the part of a file that is needed.
- Default effort medium; raise it for architecture and UX design.

## Git

- Commit and push **only when asked**. Small, imperative commit messages. Never rewrite shared history; no force-push.
- Work on a branch, not on the default branch; merge by the owner's decision.
- Secrets, `.env`, personal data, third-party book content and the gold corpus are never committed to this repository (see [legal](../10-security/legal-source-content.md)).

## Seed files for the new codebase

When the Rust workspace is created (phase P1), seed `CLAUDE.md` and `crates/AGENTS.md` from `planning/templates/*.tpl` so the same rules govern code. The owner's root `AGENTS.md` is copied as-is (it is project-agnostic and ignored by this repository's current `.gitignore`; decide in P1 whether to track it in the new codebase).

## Communication

User-facing answers: organized, concise, plain language; say clearly what was **changed** and what was only **inspected**.
