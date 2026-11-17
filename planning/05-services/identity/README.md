# identity

Status: DRAFT

Who is this person, and have they proven it? Nothing else.

| | |
|---|---|
| Owns | accounts, credentials (Argon2id), TOTP enrolment, password links, sessions, Kindle addresses, login throttling |
| Does not own | what an account may do (access), books, personal reading data |
| Requirements | REQ-IDN-001…009, REQ-MIG-003 |
| Emits | `AccountInvited`, `AccountActivated`, `AccountSuspended`, `AccountReactivated`, `AccountDisabled`, `PasswordLinkIssued`, `SessionRevoked` |
| Consumes | none |
| Calls | none |
| Called by | gateway (session resolve), access (subject facts), notify (addresses) |

## Design notes

- Roles do not exist here. An account is a person with credentials; abilities are grants in `access`.
- The setup link and the reset link are the same mechanism with different `purpose`; issuing a new link supersedes the previous one for that account and purpose.
- `PasswordLinkIssued` carries a one-time secret **reference** (not the secret): notify fetches the link text through a one-shot internal call to avoid persisting secrets in the event log.
- Demo account: a normal account with `is_demo=true`; the flag is part of the subject assertion; mutations from demo sessions are rejected by access.
- Superadmin seed: a CLI (`identity seed-admin`), idempotent, interactive password, prints nothing secret.

See [domain model](domain-model.md) · [API](api-contract.md) · [state machines](state-machines.md) · [tests](test-plan.md).
