# notify - API contract

Status: DRAFT

Authoritative contract: [07-contracts/http/notify.md](../../07-contracts/http/notify.md). Events: [events catalog](../../07-contracts/events/README.md).

| Aspect | Summary |
|---|---|
| Public routes | none; the gateway does not route `/api/notify/*` (REQ-NTF-011) |
| Primary input | pulling `email.requested` (identity; kinds `invite`, `password_reset`, `password_changed`) and `kindle.requested` (catalog) with a stored cursor, idempotent by event id |
| Internal routes (service token) | `GET /internal/messages/{id}`, `GET /internal/kindle-deliveries/{id}`, `GET /internal/stats`, plus health, ready, contract. No enqueue routes: events only (D-53) |
| Outbound calls | identity `GET /internal/email-requests/{id}`, `GET /internal/users/{id}`, `POST /internal/check`; catalog EPUB stream and `POST /internal/kindle-requests/{id}/status` |
| Errors and reasons | typed delivery reasons `unsupported_format`, `too_large`, `no_address`, `sender_not_approved`, `smtp_failed` ([error catalog](../../07-contracts/error-catalog.md)); each has a class |
| Observability | outbox depth and age, failed count, per-attempt metrics on `/metrics` |
