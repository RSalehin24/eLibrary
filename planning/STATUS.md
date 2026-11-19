# Status

Status: DRAFT

Resume here. Do not re-derive earlier decisions; read [DECISIONS](DECISIONS.md) and [INCONSISTENCIES](INCONSISTENCIES.md).

## Current stage

**Planning, rewrite complete (2026-11-19); awaiting owner review.** Owner decisions D-22..D-57 are recorded in [DECISIONS](DECISIONS.md): six Rust services (gateway, identity, catalog, reader, ingestion, notify), Caddy for HTTPS only, Angular Material M3 with SSR, Docker Compose, fresh start (nothing migrated, old app shut down, D-32 and D-50), monthly backups (D-33), fully automatic publishing (D-49, D-56, D-57), events-only notify (D-53), batch grants and per-user export (D-54, D-55), gold labelling allowed before source permission for private research only (D-51), reader modes scroll and paged (D-52). Waves A-E are done (charter, discovery, requirements, architecture, contracts, service designs, UX, testing, data, security, operations, roadmap, formal models); wave F is done (three coherence reviews, fix passes A and B, traceability regenerated, [delta](_replan/delta.md) written); `check_plan.py` passes with 215 requirements and 215 invariants. See [rewrite-plan](_replan/rewrite-plan.md). The previous plan is kept read-only in `_v1/`. No product code exists. Remaining open owner points are in [open-points](_replan/open-points.md).

## Next action (owner)

1. Obtain the source site's written permission (D-03); ingestion go-live (G6) and any publication stay blocked until then. Gold labelling may start without it (D-51).
2. Approve the tooling installs (each needs your OK): Docker Engine and Compose, Rust toolchain, Node/npm, Java runtime plus epubcheck (D-47).
3. Approve the dependency batch at the start of P1 (Rust crates, npm packages, backup encryption and offsite tool; see [dependency policy](04-architecture/dependency-policy.md)).
4. Answer the remaining open points when asked, then start P0 ([phases](12-roadmap/phases.md)).

## Blockers

| Blocker | Blocks | Owner |
|---|---|---|
| D-03 source rights unanswered | ingestion go-live (G6) and any publication (not gold labelling, D-51) | owner |
| Java not installed on this machine | running TLA+/Alloy/epubcheck (spike S-04, gate G2) — installing needs approval | owner |
| Docker Engine + Compose not verified/approved on this machine | local stack, image builds (P1) — installing needs approval | owner |
| Rust toolchain not installed on this machine | any Rust code, spikes S-03/S-07 — installing needs approval | owner |
| Node/npm and Angular tooling not installed or approved | spike S-02, the web app — installing needs approval | owner |

## Not verified

TLA+/Alloy syntax (never run in TLC/Alloy; logic only confirmed in Python mirrors); all numeric targets (provisional until the gold baseline); estimates (planning figures).
