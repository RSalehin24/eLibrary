# Runbook — key or secret compromise

Status: DRAFT

1. **Contain**: identify the key (capability, gateway assertion, service key, TOTP/session encryption, DB password, mail credential, source cookie).
2. **Capability key**: generate new `kid`, publish public key, deactivate old `kid` → all outstanding capabilities fail within seconds; readers' sessions renew transparently on next heartbeat.
3. **Gateway/service keys**: rotate, restart dependents (rolling); expect a few 401s.
4. **Session/TOTP encryption key**: rotate and force session revocation; if TOTP seeds may be exposed, require re-enrolment.
5. **DB/mail credentials**: rotate at the provider/DB, deploy new files, restart.
6. **Source cookie**: revoke at the source, replace.
7. **Investigate**: audit log, access logs by `kid` and request id; determine the window; assess data exposure; notify affected users if personal data was exposed.
8. **Follow-up**: root cause, add a detection/test, update threat model.
