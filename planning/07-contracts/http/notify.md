# Notify HTTP contract

Status: DRAFT · Service: [notify](../../05-services/notify/README.md) · Requirements: [NTF](../../02-requirements/ntf-notify.md) · Conventions: [README](README.md)

Notify sends invitation, password-reset and Kindle mails over SMTP with retries and keeps the delivery log. It has **no public route** (REQ-NTF-011): the gateway does not route `/api/notify/*`. Its only input is pulling `email.requested` (identity) and `kindle.requested` (catalog) from the producers' outbox endpoints with a stored cursor, handled idempotently by event id (D-53: no direct enqueue routes). The internal API below is read-only status and operations.

## Internal API (`/internal`, service token) - 3 routes

| Method | Path | Caller | Purpose | Errors |
|---|---|---|---|---|
| GET | `/internal/messages/{message_id}` | identity, catalog | status `queued`, `sending`, `sent`, `failed` with error class and masked address | `not_found` |
| GET | `/internal/kindle-deliveries/{delivery_id}` | catalog | delivery status and typed reason (`unsupported_format`, `too_large`, `no_address`, `sender_not_approved`, `smtp_failed`) | `not_found` |
| GET | `/internal/stats` | operations | outbox depth and age, failed count (metrics source; also exported on `/metrics`) | |

Also on the internal port: `GET /internal/health`, `GET /internal/ready`, `GET /internal/contract`.

Behaviour fixed by the requirements: failures carry a class `retryable` or `permanent`; retryable ones back off exponentially to a maximum attempt count and then end in a visible `failed` state; permanent ones are never retried; one row per attempt in the delivery log (kind, status, error class, time, masked address, event id); links, tokens and addresses never reach logs or error messages; SMTP calls have timeouts and a bounded backlog; Kindle status is reported back to catalog by `POST /internal/kindle-requests/{request_id}/status` ([catalog](catalog.md)). Notify emits no events.

## Status mapping

Notify states map to the reported status as follows: Queued and Retry report `queued`; Sending reports `sending` on the message route; Sent reports `sent`; Failed reports `failed` with the error class; Rejected and Preflight failure report `failed` with the typed reason. Kindle statuses sent to catalog are only `queued`, `sent`, `failed`.
