# Runbook: restore from backup

Status: DRAFT

Backups are **monthly** (D-33): a restore returns the system to the state of the latest good backup and **loses up to 30 days** of changes ([what is lost](../backup-restore.md)). RTO 4 h.

**Symptoms.** Database or volume loss or corruption, host loss, a destructive operator error, or a bad release whose migrations cannot be undone by redeploying previous images.

**Impact.** Outage until restored; afterwards missing changes since the backup.

**Quick check.** Can a smaller step fix it? A bad release is rolled back by redeploying the previous digests (migrations are expand/contract, so old images run on the new schema). Derived data (search index, reader copies) is rebuilt, not restored. Restore only for lost or corrupt primary data.

**Fix**
1. **Stop writers.** `docker compose stop` on `gateway`, `ingestion-worker`, and consumers; keep the evidence (copy the damaged volume or dump) before overwriting.
2. **Choose the set.** Latest good monthly set; verify its manifest and checksums offsite and locally; decrypt.
3. **Restore** exactly as in the [restore drill](../backup-restore.md) steps 1 to 7: secrets, roles, databases, file volumes, `migrate` on the manifest's digests, bring services up on those digests.
4. **Re-apply known post-backup changes** that must not come back: disabled or deleted accounts, role and grant removals, takedowns ([legal](../../10-security/legal-source-content.md)). Use the audit trail kept outside the backup and the admin's list; do not guess.
5. **Rebuild derived state** and let consumers replay events from their restored cursors (idempotent); re-run reconciliation.
6. **Re-ingest** books published after the backup (operator, in bounded batches); users re-add what they lost.
7. **Tell users** what was lost and the date of the backup.

**Verify.** Smoke checks ([launch](launch.md) step 7), reconciliation count zero, an admin and a reader sign in, elapsed time recorded against RTO.

**Follow-up.** Post-incident review; take a fresh backup right after the restore; fix the cause that made restore necessary; consider the backup frequency (owner decision, D-33).
