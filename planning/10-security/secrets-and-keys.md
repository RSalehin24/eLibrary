# Secrets and keys

Status: DRAFT

Rules (REQ-PLT-016, INV-PLT-016; legacy X1-002, X1-013):

1. Every secret is a **read-only file** (Compose secret under `/run/secrets`, mode 0400, owned by the service user). Never an image layer, an environment value, a command-line argument, a log line, a committed `.env` or a URL.
2. **No defaults.** There is no built-in password, key or admin account in any build. A missing, empty or too-short secret stops the service before it opens a listener (INV-PLT-003).
3. Startup validation (per service, [config](../04-architecture/cross-cutting/config-and-startup.md)): file exists, readable, permissions not broader than 0400, minimum length, and not equal to any known placeholder. The database self-test also proves a service role cannot reach another service's database.
4. `Secret<T>` wraps every loaded value: no `Debug`, `Display` or serialization, constant-time comparison (INV-IDN-003).
5. Deploy and scripts never print secrets. Secrets are generated on the host by a documented command (random bytes), never typed into a shared file and never copied through a laptop or `/tmp`.
6. CI secret scanning on every push; images are scanned for secret patterns (Q11).
7. Dev and CI use generated throwaway secrets created by `xtask`; production secret files exist only on the production host and in the encrypted backup bundle.

## Inventory

| Secret | Holder | Storage | Rotation | On compromise |
|---|---|---|---|---|
| Database password, one per service role | that service and `migrate` | secret file | 180 d | rotate in PostgreSQL, replace file, restart that service; review connection logs |
| Internal service-token key, one per service | that service (peers verify with its public part or shared key per the key table in [service-auth](../04-architecture/cross-cutting/service-auth.md)) | secret file, overlapping `kid` | 90 d | rotate the key, rolling restart of callers and callees; tokens live 60 s |
| Session/TOTP encryption key | identity | secret file | 180 d with a re-encrypt job | re-encrypt; if TOTP seeds may be exposed force re-enrolment; revoke sessions |
| SMTP credential | notify | secret file | 180 d | rotate at the mail provider, replace file, restart notify |
| Source-site cookie | `ingestion-api`, `ingestion-worker` (same read-only file) | secret file; only status and expiry in the database | when it expires or on suspicion | see lifecycle below and [source-cookie-expired](../11-operations/runbooks/source-cookie-expired.md) |
| Backup encryption key | operator | offline copy plus a second custodian copy, never on the host's backup target | yearly or on suspicion | re-encrypt retained backups with the new key |
| Offsite storage credential | backup job | secret file on the host, write-only scope where the target allows | 180 d | rotate at the provider |
| TLS certificates | `caddy` | `caddy_data` volume, ACME automatic | automatic | alert at < 14 d to expiry ([observability](../04-architecture/cross-cutting/observability.md)) |

No reading-ticket signing key exists: tickets are opaque, stored hashed in identity and verified by identity (D-37). There is no gateway assertion key: the gateway sets identity headers from identity's reply and services accept them only from the gateway with a valid service token.

The `seed-first-admin` command takes no password: it creates the first admin and a one-time setup link (INV-IDN-032). `admin-reset` works the same way (D-38). Neither stores or prints a password.

## Source-site cookie lifecycle (D-03, REQ-ING-011)

1. **Obtain.** The operator logs into the source in a browser with the account permitted by the source (D-03: permission is outstanding, so before go-live this is a fixture only). Login is never scripted and the platform never sends a login form.
2. **Install.** The operator writes the cookie to the secret file on the host (mode 0400); the same file is mounted read-only into `ingestion-api` and `ingestion-worker`. No rebuild and no database write of the value.
3. **Check.** A daily probe job and `POST /credential/check` read the file and make one GET to an allow-listed page; the console shows `valid`, `expiring` (3 days before `expires_at`, provisional), `expired` or `missing` (ingestion contract, `GET /credential`). A metric `source_credential_days_left` feeds the alert.
4. **Use.** Sent only on GETs to allow-listed source hosts; never in argv, logs, responses, the database or the browser (INV-ING-011).
5. **Expire.** A request that meets a login page or 401/403 is `auth_required` and parks in `awaiting_credential`; nothing else fails. The operator follows the source-cookie-expired runbook, replaces the file and resumes the parked requests.
6. **Retire.** If compromised or permission is withdrawn: overwrite the file with an empty one, revoke the session at the source, then follow the [key-compromise](../11-operations/runbooks/key-compromise.md) runbook.

## Open

- The exact signing scheme of service tokens (shared key or key pair per service) is defined in the service-auth design; this document states only the rotation and storage rules.
