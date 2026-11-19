# Runbook: outbox stuck (pull-based events)

Status: DRAFT

Events are pulled, not pushed ([ADR-0022](../../04-architecture/adr/0022-pull-based-outbox-events.md)): each producer keeps an `events` outbox table and serves `GET /internal/events?after=<cursor>`; each consumer keeps its own cursor, is idempotent and tolerates duplicates.

**Symptoms.** Alert "event cursor lag > 5 min" (consumer cursor against the producer's latest cursor); the reader lacks a newly published book; a disabled user can still act; Kindle or mail requests not sent; `reader copy drift` above zero.

**Impact.** Stale projections (reader copies, grant caches) and delayed mail. Safety does not depend on events: identity verifies every ticket and decision live (D-37), so a disabled user or revoked grant stays blocked at the next check.

**Quick check**
1. Which consumer lags? Compare its stored cursor with the producer's last cursor (metrics, `/internal/health/detail`).
2. Is the producer's `/internal/events` answering (producer healthy, DB reachable, service token accepted)?
3. Is the consumer's last error the same event repeatedly (a poison event) or a transport error?

**Fix**
- Producer or network down: restart the failing container; the consumer resumes from its stored cursor with no loss.
- Consumer crashed: restart it; redelivery is safe because handlers are idempotent and the cursor advances only after the event is applied (INV-RDR-024).
- Poison event (the consumer fails the same event after retries): inspect the event payload and the consumer error; fix the consumer (hotfix release) rather than skipping. Skipping an event by moving the cursor is a last resort and must be written in the incident record with the event id.
- Cursor lost or corrupted: reset the consumer to the oldest retained cursor and let it replay (events are retained 30 days and pruned only past all consumer cursors). If the needed events were pruned, rebuild the projection from the producer's current state (reader copies from catalog's published versions).

**Verify.** Lag below 60 s; `reader copy drift` = 0; published books in catalog equal reader copies (INV-NFR-013).

**Follow-up.** Add a test for the failing event shape; if retention nearly expired, review the pruning guard. The cursor-reset behaviour is to be modelled (open point Q-3).
