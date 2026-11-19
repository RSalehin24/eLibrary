# Runbooks

Status: DRAFT

Every alert links to exactly one runbook. Template: Symptoms, Impact, Quick check, Fix, Verify, Follow-up. All commands are `docker compose` or `xtask` wrappers on the host; nothing here logs a secret. The cutover runbook is gone (D-32, fresh start); first start is [launch](launch.md).

| Runbook | Trigger |
|---|---|
| [launch](launch.md) | first start of production: admin seed, source credential, first import, smoke checks |
| [admin-reset](admin-reset.md) | an admin is locked out (D-38, host command only) |
| [key-compromise](key-compromise.md) | suspected secret exposure |
| [outbox-stuck](outbox-stuck.md) | event cursor lag above 5 min or `GET /internal/events` failing |
| [queue-lease-stuck](queue-lease-stuck.md) | ingestion jobs stay `running` with expired leases, or queue age grows |
| [source-drift](source-drift.md) | `SourceDriftDetected` or a failing canary |
| [source-cookie-expired](source-cookie-expired.md) | credential `expiring` or `expired`; requests parked in `awaiting_credential` |
| [restore](restore.md) | database or volume loss; restore from the monthly backup |
| projection-drift | reader copies differ from published books: replay events from the cursor, then investigate (runbook to be written when the reader design fixes the reconcile command; listed as a gap) |
| search-rebuild | index corrupt or analyzer changed: rebuild from the book tables (INV-CAT-013); command defined by the catalog design (gap) |
| bad-ruleset | gold regression after promotion: demote the ruleset, reprocess the diff (ruleset design, INV-ING-030; gap) |

Related: [backup and restore](../backup-restore.md), [environments and CI](../environments-and-ci.md), [secrets](../../10-security/secrets-and-keys.md).
