# notify

Status: DRAFT

Sends things to the outside world — mail and Kindle — exactly once in effect.

| | |
|---|---|
| Owns | templates, outbound mail log, Kindle send log, provider credentials |
| Does not own | accounts, links (identity), books/EPUBs (content), permission (access) |
| Requirements | REQ-NTF-001…004 |
| Emits | `MailSent`, `MailFailed`, `KindleSent`, `KindleFailed` |
| Consumes | `PasswordLinkIssued`, `AccountInvited` (identity), `KindleRequested` (library), `JobFailed` (ingestion, admin notices) |
| Calls | identity (one-shot link text), content (EPUB via service capability), access (`decide SendToKindle` at request time done by library; notify re-verifies the capability) |

## Kindle flow

1. Library verifies `Allow(SendToKindle)` and the chosen address belongs to the account; it emits `KindleRequested{owner, book, address_id, request_id}`.
2. Notify preflight: address verified, EPUB size ≤ provider limit (50 MB), format supported; a failed preflight records `Rejected(reason)` and emits `KindleFailed` (user-visible reason).
3. Claim-before-send row `(request_id)`; fetch EPUB; send; record result; emit `KindleSent`.

## Safety

- Links and tokens appear only inside `Secret`-wrapped fields and the rendered mail body; never in logs, events, or error text (INV-NTF-004).
- Provider outage: retry with backoff up to 24 h, then `Failed` and an admin notice; account creation is never blocked.
- Mail goes through a `MailTransport` trait with three implementations: SMTP, provider API, and a local sink for dev/tests.

See [domain model](domain-model.md) · [API](api-contract.md) · [state machines](state-machines.md) · [tests](test-plan.md).
