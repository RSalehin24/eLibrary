# ingestion — state machines

Status: DRAFT

Formal model: [JobLifecycle.tla](../../03-correctness/formal-models/tla/JobLifecycle.tla) (abstracts the steps below to `Running`).

## Job

```
New ─enqueue (no other active job for source_key)─► Queued ─claim(epoch+1, lease)─► Running ─complete─► Published
                                                       ▲                              │  │
                                                       │ lease expiry (attempts<N)    │  ├─needs human─► Review ─resolve(retry)─► Queued
                                                       └──────────────────────────────┘  │                │
                                                                lease expiry (attempts=N) └─► Failed      └─cancel─► Cancelled
```
Active = Queued, Running, Review. Terminal = Published, Failed, Cancelled.

## Steps inside Running (cursor persisted after each step; each step idempotent by `(job, step, epoch)`)

```
Acquire → Snapshot → Parse → Structure → Classify → Entities → Validate → Deduplicate → DraftUpsert → ContentBuild → Publish → Done
```
- Any step may return `NeedsReview(kind)` → job moves to Review with the step recorded.
- A worker writes results only if its `epoch` equals the job's current epoch (fencing); stale workers' writes are rejected (zombie protection).
- Resume after lease expiry restarts from the last completed step (outputs are pure, so recomputation is safe).
- `Publish` is the only step with outside-visible effect; it is the saga in [communication](../../04-architecture/communication-and-events.md).

## Catalog sync job

`Listing(page n) → Diff against entries → Upsert → (n+1 | Done)`; page signature loop detection (repeat → stop with `SourceDrift` review); bounded pages; resumable by cursor.

## Review item

`Open → Resolved | Dismissed`; resolving requires an action valid for the kind (typed enum per kind); resolving may re-enqueue the job (`Review → Queued`) with the resolution persisted as an *override input* to the pure stages (not a mutation of their outputs), so reprocessing reproduces the human decision.

## Ruleset

`Candidate → (gold gate passes) → Promoted → Retired`; promotion also requires a shadow reprocess diff review for published books ([rulesets](rulesets/README.md)).

## Schedule

`Idle → Due → (job created) → Idle`; `next_run` computed from the injected clock; a missed run during downtime is run once (no backlog storms).
