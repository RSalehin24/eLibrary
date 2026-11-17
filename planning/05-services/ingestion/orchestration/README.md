# Orchestration — jobs, scheduling, sync, review, reprocessing

Status: DRAFT

## Worker loop

```
loop:
  claim = SELECT … FROM jobs WHERE state='Queued' AND next_run<=now ORDER BY priority, created_at
          FOR UPDATE SKIP LOCKED LIMIT 1                  -- sets state=Running, epoch+=1, lease_until=now+120s
  run steps from cursor; after each step: persist JobStepResult(job, step, epoch) IF job.epoch==epoch  -- fencing
  heartbeat every 30s extends lease_until (same epoch check)
  on completion: transition under epoch check
```
Lease expiry is handled by a sweeper (`Running` with `lease_until < now` → `Queued` or `Failed`), per the [model](../../../03-correctness/formal-models/tla/JobLifecycle.tla). Concurrency caps: 4 global, 2 per source (limits table). Priority: manual submissions > reprocess > sync > scheduled rechecks.

## Catalog sync (replaces "Catalog" page automation)

- Job kind `Sync`: pages through the source archive (bounded), upserts `SourceCatalogEntry`, marks new/changed, never fetches book bodies.
- Entries in `Listed` can be bulk-imported (≤ 200 per request) into `Create` jobs; automation settings (`Schedule`) may auto-import with filters (category/author) — off by default.
- Incomplete detection: entries imported earlier whose canonical page shows an "incomplete/ongoing" marker are rechecked every 6 h with backoff (replaces "incomplete" and "multi-page TOC" pages).

## Admin workspaces (three)

| Workspace | Contents |
|---|---|
| **Sources** | source health (last fingerprint, drift), politeness, catalog entries, schedules, sync runs |
| **Jobs** | create from URL/EPUB, live list (SSE), step timeline, logs, cancel/retry |
| **Review** | one inbox of `ReviewItem`s by kind with evidence view and typed resolution actions |

## Reprocessing with diff

1. Select books (ids/filters) and a ruleset version → creates a **diff run** (job kind `Reprocess`, no publish).
2. For each book run stages 2–6 on its stored snapshot; compute `DocumentDiff`: section tree changes (added/removed/renamed/moved), entity changes (old → new, evidence), text-layer changes (counts and samples), anchor impact estimate (how many annotations would be re-anchored/orphaned using `domain-anchor` against stored annotations *counts*, queried via library aggregate).
3. Curator reviews the diff, selects books, applies → each runs the publish saga with a new artifact set; previous set retained.
4. Human overrides (resolved review decisions) are inputs and are re-applied, so a reprocess never undoes a curator's decision.

## Failure handling table

| Failure | Handling |
|---|---|
| Source 5xx/timeouts | step retry with backoff; after N → job `Review(IncompleteSource)` not `Failed` |
| Parse yields zero blocks | `Review(ConservationFailure or NoPublicBody)` |
| Validator invariant false | job `Review(ConservationFailure)`, `invariant_violation` metric pages |
| Content build fails | `Review(BuildFailed)`; retry allowed |
| Catalog unavailable | step retry (idempotent keys); job stays Running within lease renewal until attempts exhausted |
| Worker crash | lease expiry → requeue; outputs recomputed |

## Canaries and drift

Daily canary jobs on fixture books (one per structure shape) run through acquire→validate without publishing. Failure raises `SourceDrift` and pauses new jobs for that adapter ([acquisition](../acquisition/README.md)).

## Observability

Per job: step timings, block counts per stage, conservation ledger summary, review counts; per ruleset: gold metrics gauges; queue depth/age; drift state.
