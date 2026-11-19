# Runbooks

Status: DRAFT

Every alert links to exactly one runbook. Template: *Symptoms → Impact → Quick check → Fix → Verify → Follow-up*.

| Runbook | Trigger |
|---|---|
| [cutover](cutover.md) | planned migration from legacy |
| [key-compromise](key-compromise.md) | suspected signing/secret exposure |
| [source-drift](source-drift.md) | `SourceDriftDetected` / canary failing |
| [outbox-stuck](outbox-stuck.md) | outbox oldest age > 5 min |
| restore | database/artifact loss — see [backup and restore](../backup-restore.md) |
| projection-drift | reconciliation non-zero (rebuild projection from events, then investigate) |
| search-rebuild | index corrupt or analyzer changed |
| bad-ruleset | gold regression found after promotion: demote ruleset, reprocess diff to previous |
