# Status

Status: DRAFT

Resume here. Do not re-derive earlier decisions; read [DECISIONS](DECISIONS.md) and [INCONSISTENCIES](INCONSISTENCIES.md).

## Current stage

**Planning, rewrite complete (2026-11-19); awaiting owner review.** Owner decisions D-22..D-57 are recorded in [DECISIONS](DECISIONS.md): six Rust services (gateway, identity, catalog, reader, ingestion, notify), Caddy for HTTPS only, Angular Material M3 with SSR, Docker Compose, fresh start (nothing migrated, old app shut down, D-32 and D-50), monthly backups (D-33), fully automatic publishing (D-49, D-56, D-57), events-only notify (D-53), batch grants and per-user export (D-54, D-55), gold labelling allowed before source permission for private research only (D-51), reader modes scroll and paged (D-52). Waves A-E are done (charter, discovery, requirements, architecture, contracts, service designs, UX, testing, data, security, operations, roadmap, formal models); wave F is done (three coherence reviews, fix passes A and B, traceability regenerated, [delta](_replan/delta.md) written); `check_plan.py` passes with 215 requirements and 215 invariants. See [rewrite-plan](_replan/rewrite-plan.md). The previous plan is kept read-only in `_v1/`. Implementation started 2026-11-19: cargo workspace plus `crates/domain-text` (DisplayText, ExactKey, FuzzyKey, Slug, BengaliCollator with sort keys; 12 tests pass, clippy clean), `contracts-ids` (BookId, UserId, VersionId, SectionId) and `platform-time` (Instant, Clock, SystemClock); `platform-config` (typed config, unknown-key rejection, `Secret`), `platform-http` (internal health/ready/contract router), and a sample `svc-identity` binary that starts, serves both listeners and fails closed on bad config; 28 tests pass. No services exist yet. Remaining open owner points are in [open-points](_replan/open-points.md).

## Next action (owner)

1. Obtain the source site's written permission (D-03); ingestion go-live (G6) and any publication stay blocked until then. Gold labelling may start without it (D-51).
2. Tooling installs approved and done (D-58): Docker, Rust, Node/npm, Java. Docker works from the session (verified after reboot). Open: epubcheck.
3. Approve the dependency batch at the start of P1 (Rust crates, npm packages, backup encryption and offsite tool; see [dependency policy](04-architecture/dependency-policy.md)).
4. Answer the remaining open points when asked, then start P0 ([phases](12-roadmap/phases.md)).

## Blockers

| Blocker | Blocks | Owner |
|---|---|---|
| D-03 source rights unanswered | ingestion go-live (G6) and any publication (not gold labelling, D-51) | owner |
| epubcheck not installed (Java 27, Rust 1.100, Node 26.13 installed 2026-11-19, D-58) | S-04, gate G2, publish gate (D-47) | assistant (ask before download) |

## Not verified

TLA+/Alloy syntax (never run in TLC/Alloy; logic only confirmed in Python mirrors); all numeric targets (provisional until the gold baseline); estimates (planning figures).
