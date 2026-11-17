# Status

Status: DRAFT

Resume here. Do not re-derive earlier decisions; read [DECISIONS](DECISIONS.md) and [INCONSISTENCIES](INCONSISTENCIES.md).

## Current stage

**Planning (pre-P0).** The plan structure, requirements (105), invariants (105), architecture, service designs, UX, roadmap and rules are drafted. No product code exists. The plan check passes; the TLA+/Alloy models are written but **unchecked**.

## Next action (owner)

1. Answer the remaining open decisions in [open-decisions](04-architecture/open-decisions.md): D-05…D-10 and D-17…D-21 (asked as selectable questions with a recommendation). Already decided: D-01 (defer physical books), D-02/D-16 (Angular + Material 3), D-03 (permission + GET-only; obtain the source's written permission), D-04 (every active account reads).
2. Approve or adjust the proposed adaptations I-01…I-04 and I-10 in [INCONSISTENCIES](INCONSISTENCIES.md).
3. Start P0: gold-corpus labeling tool and sampling ([gold corpus](06-data/gold-corpus/README.md)), spikes S-01…S-07 ([spikes](12-roadmap/spikes.md)).

## Blockers

| Blocker | Blocks | Owner |
|---|---|---|
| D-03 source rights unanswered | ingestion go-live (G6), spike S-05 | owner |
| Java not installed on this machine | running TLA+/Alloy/epubcheck (spike S-04, gate G2) — installing needs approval | owner |
| Rust toolchain not installed on this machine | any Rust code, spikes S-03/S-07 — installing needs approval | owner |
| Node/npm and Angular tooling not installed or approved | spike S-02, the web app — installing needs approval | owner |

## Done so far

- Plan folder created and checked (`python3 planning/tools/check_plan.py` → 0 errors).
- Verification pass 2026-11-17: facts checked against primary sources, model logic checked in Python mirrors, 18 corrections logged — see [verification log](03-correctness/verification-log.md) and I-12…I-18.
- Engineering philosophy, working agreement, coding standards and dependency policy added from the owner's `CLAUDE.md`/`AGENTS.md`.

## Not verified

TLA+/Alloy syntax (never run in TLC/Alloy; logic only confirmed in Python mirrors); all numeric targets (provisional until the gold baseline); estimates (planning figures).
