# Engine jobs, material changes, schedules, and recovery

Task E07. Reuse current `apps/processing/jobs` claim/checkpoint/heartbeat/dispatch/control patterns, `automations` calendar logic, and `apps/ingestion/source_processing` transport/host-health/update/recovery seams. Move engine-owned state to its database; all website access goes through [private engine v1](../../shared/contracts/private-engine-v1.md).

## Admission, outbox, and fenced execution

- Commit command/inbox/job/outbox atomically before returning Accepted. Stable idempotency keys bind issuer, actor, kind, target/revision and payload hash. Enforce one active processing operation per source and one discovery per provider; different revisions/request IDs do not bypass these uniqueness constraints. Coalesce a newer source revision into one recorded successor; it runs after the active operation safely stops or its publication receipt settles.
- Dispatcher claims durable outbox rows with a lease and retries confirmed transport delivery. Broker acceptance is not book completion. Duplicate messages race through one database claim and have no second effect.
- A worker owns `(job_id, attempt_id, generation)` under a lock. Every checkpoint, stage transition and publication fence verifies that tuple, current authority, source/build revision, and stop request. Increment generation when ownership changes; old attempts cannot write or publish.
- Retain the existing 15-second heartbeat. Target stale-attempt timeout is 90 seconds; a watchdog can reclaim only after it expires under a job lock. Database/broker/heartbeat failure stops protected progress, rather than continuing with uncertain ownership.
- Collect at page boundaries, yielding after at most 10 pages or 30 seconds. Inference and export use bounded chunks with a stop/authority check before and after each. A slow chunk cannot hold a transaction open across network/model work.
- Default one processing worker and one inference worker; at most two outstanding processing dispatches per configured worker. Fairly rotate new work, continuations and due recovery; a repeatedly failing source cannot monopolize dispatch.

## Stop and publication ordering

Pause/cancel on queued/retry-wait jobs acknowledges immediately and invalidates dispatch generation. For running work, show Stop requested until a safe boundary commits paused/cancelled. Resume revalidates inputs/authority and queues a new generation; it never revives a stale worker. Cancelled/succeeded are terminal; a later explicit request gets a new operation.

The irreversible boundary is the engine transaction that commits the sealed publication outbox event. It first checks stop/authority/revision and sets stage `publishing`. After this boundary pause/cancel returns `409 publication_in_progress` and is not accepted; the website may already be activating. The UI disables stop with the reason and reconciles the receipt. If pause/cancel commits first, no publication event can be emitted. Thus an **acknowledged** stop never publishes later; a late rejected stop never falsely promises cancellation.

When publication is rejected before activation, clear the pending publication fence only through a locked recovery transition, record its terminal receipt, and requeue under a new generation after correcting the reason. Do not reuse a rejected event ID for a changed manifest. An activated receipt remains success even if a late UI stop request or lost response occurs. Archive and authority changes are always rechecked by the website at its activation commit.

## Failure classification and timing

Times below are target defaults, configurable within validated bounds and recorded in fixtures. Existing source transport limits remain 8 MiB response, 2 GiB cache, 64 MiB document, and 2,000 pages per work. Default provider pacing is 2 seconds between requests, within the existing valid 0.25–60 second interval. Reuse allowed-host/HTTPS rules and revalidate every redirect (maximum 3), DNS target, port and credential/query policy. Never log source cookies/tokens or fetch arbitrary URLs from model output.

Cache scope, evidence pins and disk-pressure behavior follow the [publication lifecycle](../../shared/contracts/publication-context-and-lifecycle.md); 2 GiB is not a whole-corpus storage allowance. IO/model deadlines, status projections, service-only reconciliation and the website receipt-consumer lease follow [scheduling and status](../../shared/contracts/scheduling-and-status.md).

| Cause | State/reason | Recovery policy |
| --- | --- | --- |
| Timeout/connection/reset/429/5xx | `retry_wait`, typed transport reason | 15s, 1m, 5m, 1h, 2h, 4h, then 6h capped. Honor longer valid Retry-After; bounded deterministic jitter is injected for tests. |
| Provider transient burst | `retry_wait`, `source_circuit_open` | Five failures in five minutes opens five-minute circuit; one half-open probe. Shared per provider, not per worker. |
| Required body/chapter temporarily absent/access-limited | `retry_wait`, `source_content_unavailable` | Recheck after six hours; preserve collected evidence and real cause. Do not call it source-unfinished or successful. |
| Source 404 | `retry_wait`, `source_not_found` | Daily recheck; explicit unavailable catalog classification. Never disappear from census. |
| Source marked unfinished but collected revision complete | Normal processing plus incomplete-source flag | Publish available verified revision; schedule material-change probes. |
| Insufficient memory/disk or inference unavailable | `retry_wait`, resource/inference reason | Probe no more than once per minute, without loading the model/rebuilding unchanged output repeatedly. No cloud fallback. |
| Malformed/unsupported source or ambiguous decisions | Explicit ambiguity/defect with `failed` after bounded analysis | At most two schema/decision retries; version/input-aware recovery. No manual editorial task or fake success. |
| Unsafe URL/archive/evidence or content/order mismatch | `failed`, integrity/security reason | Fail closed; add regression and fix relevant implementation/input before recovery. |
| Revoked/inactive/TOTP-blocked actor | `failed`, `authority_revoked` | No publication. A newly authorized explicit command may run; do not retry to evade revocation. |
| Source/catalog/admin revision changed | Conflict and scoped rebase/rebuild | Invalidate affected stages only; preserve admin overrides; never overwrite newer active metadata/build. |
| Internal reproducible defect | `failed`, defect fingerprint | Retry automatically only after relevant input/extractor/verifier/code version changes. Record first and repeated failures. |
| Unknown publication acknowledgment | Running `publishing` with receipt reconciliation | Poll/retry same event; no duplicate book, no new event with changed payload until old outcome is known. |

Availability probes do not consume a finite technical-defect budget and turn a temporarily unavailable source into a permanent success/failure fiction. A bounded recovery process can remain waiting with a real next time. SMTP uncertainty is website-owned and retains explicit reconciliation/resend rules; source retry policy never applies to email.

## Update detection and selective regeneration

Probe body paragraphs, section hierarchy/order, contributor/edition facts, cover bytes and source completion status, using immutable hashes and source evidence. Table-of-contents equality alone is not No change. Ignore only evidenced transport/site-chrome differences. Store observed revision separately from active published revision and latest attempted revision.

| Change | Invalidated work | UI summary |
| --- | --- | --- |
| Body/component/section order | Affected collection/blocks/structure/canonical/export/verification | Changed chapters/parts and revision; current valid book remains available during rebuild. |
| Supported bibliographic credit/fact | Entities/canonical metadata/export/verification | Actual changed roles/facts; respect admin overrides and revision conflicts. |
| Cover only | Cover artifact/manifest and impacted export/verification | Cover changed; no unnecessary body inference. |
| Source completion only | Source completion metadata and any affected generation | Source now finished/unfinished; distinct from collection errors. |
| Meaningless chrome only | Probe/evidence record | No content change; do not manufacture an updated book. |

An unfinished workspace shows last successful sync, failed/latest probe separately, all/updated scope, changed portions, active book, queued/rebuilding status and precise recovery cause. No Review/Check/Approve action appears. A failed probe cannot advance the successful-sync timestamp or clear the last known change.

When a newer source revision arrives after a publication fence, the fenced immutable snapshot may finish; enqueue the newer revision next. Expected catalog revision prevents an older candidate from overwriting a newer activation. A refresh arriving before the fence invalidates the affected candidate and requires a new verified manifest.

## Scheduling

Use `Asia/Dhaka` instants and existing frequency enum/calendar helpers (daily/weekly/biweekly/monthly/bimonthly/quarterly/four-monthly/half-yearly). New schedule forms default to daily at the next 02:00 Dhaka slot and disabled; enabling is an explicit saved action. A configured unfinished-sync schedule uses the same mechanism, not a hidden second cron implementation. Preserve existing bounded page/processing-limit options in command input and visible scope.

Uniqueness key is `(schedule_id, scheduled_due_at)` for scheduled runs. Lock schedule revision/due time before creating run+outbox and advancing. Manual Run Now uses an idempotent command and joins/reports an already-active operation for overlapping targets. Do not execute a duplicate merely because one request came from the UI.

After downtime, queue at most one catch-up run for the due scope and record the missed count; advance to the next future occurrence instead of flooding every missed slot. Use the original local anchor for month-end clamping so a February run does not permanently shift all later months to the 28th. Disabled schedules show no next run. Current run-as authority is checked each run; revoked schedules record blocked reason without executing. Reset restores all fields, including scope, enabled/time/frequency/limits.

The exact Run Now request, parent workflow, post-discovery selection, child idempotency, stop propagation and combined job-list projection are defined in [scheduling and status](../../shared/contracts/scheduling-and-status.md). Implement them before moving production scheduler ownership; a bare kind/scope command cannot silently stand in for a multi-stage schedule.

## Fault tests and observability

Inject duplicate message, crash before/after each checkpoint, heartbeat loss, stale lease, concurrent claim, stop versus publication fence, outbox sent/reply lost, website commit/reply lost, corrupted/missing staged file, source update, admin edit/archive, grant revocation, broker/DB/model outage, scheduler overlap/missed tick and resource exhaustion. Assert both final state and absence of unintended writes/publication. Use actual isolated PostgreSQL/broker/Redis for lifecycle tests; deterministic model fixtures only for integration.

Log bounded event/stage/reason/version/generation/operation/build/receipt IDs with durations, retry time and queue/heartbeat metrics. Do not log credentials, raw assertions, book bodies, user notes, recipient addresses, or private source cookies. Recovery reports show counts plus explicit unresolved reasons, not a fabricated completeness score. Reuse regressions in `tests/backend/processing`, `tests/backend/engine` and source fixtures; never run their Redis Pub/Sub integration against the active preview server.
