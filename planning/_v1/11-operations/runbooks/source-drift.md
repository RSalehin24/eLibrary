# Runbook — source drift / canary failure

Status: DRAFT

**Symptoms**: `SourceDriftDetected`, canary job fails, adapter paused (new jobs queued but not started).

1. Open Sources workspace → drift detail: compare the new fingerprint with last-known-good (which selectors changed).
2. Fetch a canary page manually (GET) and inspect the structure change.
3. Decide: (a) transient/partial deployment on the source → wait and rerun canaries; (b) real redesign → update the adapter (selectors/parsing) in code + add fixture pages; run the gold snapshot tests (adapter changes must not alter parsing of stored snapshots).
4. Release the adapter; run canaries; accept the new fingerprint; unpause.
5. Reprocess is **not** needed for already-snapshotted books (snapshots are immutable).
6. Follow-up: add the new structure variant to canaries.
