# Status

Status: DRAFT

Resume here. Do not re-derive earlier decisions; read [DECISIONS](DECISIONS.md) and [INCONSISTENCIES](INCONSISTENCIES.md).

## Current stage

**Planning (pre-P0).** The plan structure, requirements (105), invariants (105), architecture, service designs, UX, roadmap and rules are drafted. No product code exists. The plan check passes; the TLA+/Alloy models are written but **unchecked**.

## Next action (owner)

1. Review and answer the open decisions in [open-decisions](04-architecture/open-decisions.md) — recommendations are given, "yes" is enough. Blocking soonest: D-03 (rights; blocks ingestion go-live), D-04 (default reading), D-01 (physical books), D-02 (frontend).
2. Approve or adjust the proposed adaptations I-01…I-04 in [INCONSISTENCIES](INCONSISTENCIES.md).
3. Start P0: gold-corpus labeling tool and sampling ([gold corpus](06-data/gold-corpus/README.md)), spikes S-01…S-07 ([spikes](12-roadmap/spikes.md)).

## Blockers

| Blocker | Blocks | Owner |
|---|---|---|
| D-03 source rights unanswered | ingestion go-live (G6), spike S-05 | owner |
| Java not installed on this machine | running TLA+/Alloy/epubcheck (spike S-04, gate G2) — installing needs approval | owner |
| Rust toolchain not installed on this machine | any code, spike S-02/S-03/S-07 — installing needs approval | owner |

## Done so far

- Plan folder created and checked (`python3 planning/tools/check_plan.py` → 0 errors).
- Engineering philosophy, working agreement, coding standards and dependency policy added from the owner's `CLAUDE.md`/`AGENTS.md`.

## Not verified

TLA+/Alloy models (never run); all numeric targets (provisional until the gold baseline); estimates (planning figures).
