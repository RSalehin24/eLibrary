# notify

Status: DRAFT (six-service design, D-30, D-31)

Sends invitation, password-reset and Kindle mails over SMTP with retries and keeps a delivery log, so a mail failure never blocks or slows another service.

| | |
|---|---|
| Owns | outbox of mails and Kindle deliveries, templates (bn, en), delivery log (one row per attempt), event cursors, SMTP credentials (secret file, read-only) |
| Does not own | users, addresses, links (identity); books and EPUB files (catalog); the permission decision (identity) |
| Requirements | REQ-NTF-001...012 (table below) |
| Emits | none (Kindle status is reported to catalog by an internal call) |
| Consumes | `email.requested` (identity), `kindle.requested` (catalog), pulled from `GET /internal/events?after=<cursor>` with a stored cursor, idempotent by event id |
| Calls | identity (`/internal/email-requests/{id}`, `/internal/users/{id}`, `/internal/check`), catalog (EPUB stream, `POST /internal/kindle-requests/{id}/status`), SMTP server |
| Called by | nobody public; trusted services only on the internal port; no `/api/notify/*` route (REQ-NTF-011) |
| Tech | Rust, PostgreSQL database `notify`, `MailTransport` trait (SMTP; local sink for dev and tests); crates per [dependency policy](../../04-architecture/dependency-policy.md) |
| Contract | [HTTP contract](../../07-contracts/http/notify.md), [events](../../07-contracts/events/README.md) |

## Flow

1. **Pull.** One loop per source reads events after its cursor, inserts one outbox row per event under `UNIQUE (source, event_id, kind)` in the same transaction as the cursor advance; duplicates do nothing (REQ-NTF-001).
2. **Send mail.** A sender claims due rows with `FOR UPDATE SKIP LOCKED` and a lease, fetches address and link by reference from identity right before sending, renders the template in the account language, sends through `MailTransport` with a timeout, and records an attempt row (REQ-NTF-002, 003, 009, 010).
3. **Kindle.** On `kindle.requested`: ask identity `/internal/check` for `kindle`, read the address from identity, preflight (EPUB only, total mail size at most 50 MB, address valid, sender-approval confirmed), stream the EPUB from catalog holding at most one attachment per send, send, then report status to catalog (REQ-NTF-005..007, 009).
4. **Failures.** Typed class `retryable` or `permanent`; retryable ones back off exponentially to the maximum attempts then `failed`; permanent never retry (REQ-NTF-008).
5. **Retention.** A bounded job deletes outbox, template-version and delivery-log rows older than the documented retention (REQ-NTF-012).

## Non-responsibilities

No public route; no event production; no storage of real addresses or link text beyond the in-memory render; no permission logic of its own; no mail content composed by other services.

## Structure

```
notify/src/
  pull/        EventPuller per source, cursor store
  outbox/      rows, claim (SKIP LOCKED + lease), state transitions
  templates/   typed variable structs per template, bn and en catalogs, escaping
  transport/   MailTransport trait, SmtpTransport, SinkTransport
  kindle/      preflight (pure), attachment streaming, status report to catalog
  policy/      backoff, FailureClass, rate limits, retention
  http/        internal routes, health, stats, metrics
```

## Failure behaviour

| Failure | Behaviour |
|---|---|
| SMTP down or slow | attempts end with `smtp_failed` (retryable); backoff to the cap then `failed`; backlog bounded and alerted; no other service is affected |
| Identity or catalog unreachable | row stays due with backoff; no send without an identity Allow |
| Crash after SMTP accepted, before `sent` recorded | lease expiry causes at most one repeat (documented at-least-once window) |
| Notify container down | producers keep writing outbox events; nothing blocks; notify catches up from its cursor |
| Template set incomplete | cannot activate; startup refuses |

## Requirements covered

| REQ | Where | Tests |
|---|---|---|
| REQ-NTF-001 | Flow 1; [state machines](state-machines.md) pull | TST-NTF-001, 002 |
| REQ-NTF-002 | Flow 2 | TST-NTF-003, 004 |
| REQ-NTF-003 | templates; [domain model](domain-model.md) | TST-NTF-005 |
| REQ-NTF-004 | masked address, `Secret` types | TST-NTF-006 |
| REQ-NTF-005 | Flow 3; Kindle machine | TST-NTF-007 |
| REQ-NTF-006 | preflight | TST-NTF-008 |
| REQ-NTF-007 | rate limits, memory bound | TST-NTF-009 |
| REQ-NTF-008 | failure classes | TST-NTF-010 |
| REQ-NTF-009 | delivery log, status report | TST-NTF-011 |
| REQ-NTF-010 | isolation | TST-NTF-012 |
| REQ-NTF-011 | secrets, no public route | TST-NTF-013 |
| REQ-NTF-012 | retention job | TST-NTF-014 |

## Open points touching this service

- **C-5** is closed by D-53: notify works from events only; no direct enqueue routes.
- **O-1** does not affect notify. Maximum attempts, backoff values and retention days are provisional until the P0 baseline (O-7 family).

See [domain model](domain-model.md) | [API](api-contract.md) | [state machines](state-machines.md) | [tests](test-plan.md).
