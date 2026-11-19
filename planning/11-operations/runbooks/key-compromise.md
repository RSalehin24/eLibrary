# Runbook: key or secret compromise

Status: DRAFT

Revised from v1: there is no capability signing key and no gateway assertion key. Reading tickets are opaque and verified by identity (D-37), so a ticket cannot be forged from a leaked key.

**Symptoms.** A secret file, backup or host account is exposed; a secret appears in a log, repository or image; unexplained sign-ins or opens in the audit log.

**Impact.** Depends on the secret (see step 1).

**Steps**
1. **Contain.** Identify the secret ([inventory](../../10-security/secrets-and-keys.md)): database password, internal service-token key, session/TOTP encryption key, SMTP credential, source-site cookie, backup encryption key, offsite credential.
2. **Service-token key:** generate a new key with a new `kid`, deploy the secret file, rolling restart of the service and its callers; expect a few 401s for under a minute; tokens live 60 s so the old key is useless after the overlap.
3. **Database password:** `ALTER ROLE` in PostgreSQL, replace the secret file, restart that service; review connection logs for the exposure window.
4. **Session/TOTP encryption key:** rotate with the re-encrypt job and **revoke all sessions** (users sign in again); if TOTP seeds may be exposed, require re-enrolment.
5. **SMTP credential:** rotate at the provider, replace the file, restart notify; check the delivery log for mail you did not send.
6. **Source-site cookie:** log out or revoke the session at the source, replace the file with a fresh cookie or an empty one ([source-cookie-expired](source-cookie-expired.md)); ingestion parks new work in `awaiting_credential`.
7. **Backup or offsite key:** create a new key, re-encrypt retained sets, rotate the offsite credential; assume the exposed sets are readable.
8. **If user sessions or tickets may be stolen:** disable the account or change a grant; the grant version and `user.disabled` revoke tickets immediately.
9. **Investigate.** Audit logs (auth, grants, opens, downloads, operator actions, 1 year), gateway logs by request id; fix the window start and end; list affected data and users.
10. **Notify** affected users if personal data was exposed (owner decision on wording).

**Verify.** Services ready; old secret rejected; no 401 storm; alerts quiet for an hour.

**Follow-up.** Root cause; add a detection or test; update the [threat model](../../10-security/threat-model.md).
