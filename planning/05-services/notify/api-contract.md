# notify — API contract

Status: DRAFT · Source of truth: `contracts-notify`

notify is event-driven; its HTTP surface is small.

## Admin (via gateway)

| Method & path | Auth | Purpose |
|---|---|---|
| `GET /admin/mail?state&kind&after` | `ManageAccess` | delivery log (addresses masked) |
| `POST /admin/mail/{id}/retry` | `ManageAccess` | retry a Failed delivery |
| `GET /admin/kindle?state&after` | `ManageAccess` | Kindle log |
| `GET /admin/templates`, `PUT /admin/templates/{key}/{lang}` | `ManageAccess` | templates (revisioned) |

## Internal

| Route | Caller | Purpose |
|---|---|---|
| `POST /internal/events/{type}` | outbox relays | event inbox, idempotent on `(consumer, event_id)` |
| `GET /internal/contract` | all | handshake |

## Event contracts consumed

`PasswordLinkIssued{account_id, link_ref, purpose, language}` · `KindleRequested{request_id, owner_id, book_id, address_ref}` · `JobFailed{job_id, reason_code}`.

## Event contracts emitted

`MailSent{delivery_id, kind}` · `MailFailed{delivery_id, kind, error_code}` · `KindleSent{request_id, owner_id, book_id, at}` · `KindleFailed{request_id, reason_code}` — none carries addresses or links.
