# Backup and restore

Status: DRAFT

Decision D-33 (2026-11-19): backups are **monthly**; data loss up to 30 days is accepted. RPO up to 30 days, RTO at most 4 hours (REQ-NFR-004, REQ-PLT-015, INV-PLT-015, INV-NFR-004). Supersedes v1 (WAL archiving, RPO 15 min). Legacy defect answered: X1-080 (no backups at all).

## What can be lost (stated plainly)

Everything written after the latest good monthly backup, up to 30 days, is gone after a restore:

| Lost | Consequence |
|---|---|
| Reading progress, bookmarks, highlights, notes, reader preferences | users re-read and re-annotate from the backup state |
| Shelf entries, saved filters | re-added by users |
| User changes: new accounts, invites accepted, password and TOTP changes, grants and role changes, disabled accounts | admin must redo grants and re-invite; **a user disabled after the backup becomes active again** until the admin re-applies it; erasures requested after the backup must be re-applied |
| Review and publish decisions, manual metadata edits, new book versions | operator repeats them; books published after the backup are re-ingested by the pipeline |
| Audit rows and ticket/open records after the backup | accountability gap for that period |
| Mail outbox state | invites or resets pending at the time may need re-sending |

Not lost: nothing that exists in a backup set; books can always be re-ingested from the source (if permission exists, D-03). The owner may later choose a higher frequency (D-33 allows the assistant to recommend it): a weekly backup would cut the window to 7 days at no design change, since backup is a scripted job. Not decided here.

## What is backed up

| Data | Method | Frequency | Offsite | Verification |
|---|---|---|---|---|
| Every service database (`identity`, `catalog`, `reader`, `ingestion`, `notify`) | `pg_dump` per database (custom format) by the `backup` one-shot job, plus roles and globals dump | monthly | yes, encrypted before leaving the host | restore drill; row counts and checksums recorded in a manifest |
| File volumes `identity_files`, `catalog_files`, `ingestion_files` (`reader_files` is not backed up: reader copies are regenerable from catalog EPUBs, D-33) | consistent copy (volume snapshot or `tar` while writers are quiesced) | monthly | yes | file counts and sha256 manifest check (catalog files are sha256-addressed) |
| Secrets bundle (secret files) | encrypted bundle, separate from the data set | on change and monthly | offline copy plus second custodian | restore drill uses it |
| Search index, reader copies, scrape cache | optional: search index is derived (rebuildable, INV-CAT-013); reader copies are derived from catalog EPUBs; scrape cache is third-party raw content kept at most 30 days | included only if cheap | n/a | rebuilt in the drill |
| Configuration (`compose.yaml`, release digests) | in the repository | per release | n/a | n/a |

Each backup set carries a manifest: date, release digests, schema versions, per-file sha256, per-database row counts. The job writes to a new directory and never overwrites an older set.

## Offsite copy and retention

- A copy of each monthly set goes off the host (a different failure domain). **OPEN:** the offsite target and the encryption tool (the v1 plan named `age` and `restic`; each is a new tool needing owner approval in the [dependency policy](../04-architecture/dependency-policy.md)). The plan only requires: encrypted before leaving the host, key kept apart ([secrets](../10-security/secrets-and-keys.md)), write-only credential where the target allows.
- Retention: keep the last 6 monthly sets locally and offsite (provisional; owner may change). A claim or erasure may require deleting specific sets ([legal](../10-security/legal-source-content.md), [abuse-and-privacy](../10-security/abuse-and-privacy.md)).
- Alert: backup older than 35 days ([observability](../04-architecture/cross-cutting/observability.md)).

## Restore drill (scripted: `xtask restore-drill`)

Purpose: prove the latest set restores into an empty stack that passes smoke checks, within RTO 4 h (INV-PLT-015). Frequency: monthly, right after each backup, and always before a major release.

1. Provision an empty host or VM with Docker and Compose only (no data, nothing from the old host except the backup set and the secrets bundle).
2. Fetch the latest offsite set; verify the manifest and checksums; decrypt.
3. Restore secrets into Compose secret files (0400).
4. Start `postgres` only; create roles; restore each database (`pg_restore`, stop on error); restore the file volumes.
5. Run `migrate` for the release digests recorded in the manifest (forward only; refuses if the schema is newer than the binary).
6. `docker compose up -d --wait` with those digests; startup checks must pass ([config](../04-architecture/cross-cutting/config-and-startup.md)).
7. Rebuild derived state: search index rebuild (INV-CAT-013), reader copies for published books if volumes were not backed up, event cursors continue from their stored values.
8. Smoke ([launch smoke checks](runbooks/launch.md)): sample 50 books open in the reader, 20 accounts sign in (known test accounts in staging; in a real restore, the admin plus one reader), search finds known titles, the reconciliation count of published books equals the reader copies (INV-NFR-013).
9. Record elapsed time against RTO 4 h; open an issue for every step that needed manual work; store the drill record with the date.

The drill runs against staging data in routine drills; a drill with production backups is done on an isolated host and then destroyed.

## Real restore

See [restore runbook](runbooks/restore.md). It adds: stop writers, decide the restore point, re-apply known post-backup changes (disables, erasures), tell users what was lost.

## Open

- Offsite target, encryption tool and storage credential (owner; new dependency or service).
- Backup frequency: monthly is decided; any higher frequency is an owner choice.
