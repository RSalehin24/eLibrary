# Runbook — outbox stuck

Status: DRAFT

**Symptoms**: `outbox_oldest_age_seconds` > 300; downstream projections lag (search, library refs, notifications).

1. Which service? Check relay worker health and last error in `/health/detail`.
2. Which subscriber? Look for repeated non-2xx in the delivery log; if one consumer is down, others should continue (per-subscriber cursors). If not, that is a bug: open an incident.
3. Consumer down → restart it; the relay retries with backoff; events are idempotent so replay is safe.
4. Poison event (consumer returns 4xx repeatedly): after 7 d or manual action it is dead-lettered; inspect payload, fix consumer, replay from the dead-letter table (`xtask outbox replay`).
5. Verify: oldest age returns to < 60 s; projection drift metric = 0 after reconciliation.
