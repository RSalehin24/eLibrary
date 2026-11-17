# Backup and restore

Status: DRAFT

RPO ≤ 15 min, RTO ≤ 1 h (G-6, INV-PLT-008).

| Data | Method | Frequency | Offsite | Verification |
|---|---|---|---|---|
| PostgreSQL (all service DBs) | base backup + WAL archiving (pgBackRest or `wal-g`) | base daily, WAL continuous | yes, encrypted (age) | automated restore into scratch DB nightly + row-count/invariant checks |
| Artifact store | restic snapshot of content-addressed dirs (append-only; deduped) | hourly incremental | yes | monthly `restic check --read-data-subset` |
| Snapshots (ingestion raw pages) | same as artifacts | hourly | yes | same |
| Search index | not backed up (rebuildable) | — | — | rebuild drill |
| Keys/secrets | encrypted bundle | on change | offline copy | annual restore test |
| Config | in repository | — | — | — |

## Restore drill (quarterly, scripted: `xtask restore-drill`)

1. Provision a fresh host/VM.
2. Restore secrets, databases to a target time, artifact stores.
3. Start services; startup checks must pass (schema/contract).
4. Run reconciliation: projection drift = 0 (rebuild from events if needed), search rebuild, sample 50 books readable, 20 accounts log in.
5. Record elapsed time vs RTO; file issues for any step that needed manual intervention.
