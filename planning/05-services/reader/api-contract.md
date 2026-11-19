# reader - API contract (summary)

Status: DRAFT

Endpoints are owned by [07-contracts/http/reader.md](../../07-contracts/http/reader.md) (19 public routes, 2 internal routes plus health, ready, contract). This page records how the service honours the cross-cutting rules; it does not repeat the routes.

## Authorization per route class

| Class | Needs | Notes |
|---|---|---|
| `open`, `copy` | session + scope `read` (`preview` is a separate scope, D-41) | `open` asks identity to decide and mint; a shelf entry grants nothing; non-published or deleted is `not_found` |
| `tickets/{ticket_id}/book`, `/search` | session + `read` + `X-Reader-Ticket` header | `{ticket_id}` is a non-secret handle; the secret travels only in the header; identity verifies on every call |
| progress, bookmark and highlight create and read | session + `read` + ticket | owner from the verified header, never from the body |
| bookmark and highlight delete or edit by id, `/me/*` | session | needs no book access, so a user who lost access can still manage and export their data |
| internal | service token | `GET /internal/copies` (drift listing), erase route **OPEN (O-1)** |

## Rules honoured

- **No file or chapter route** (REQ-RDR-008): one package response; the EPUB never leaves the reader's fetch from catalog.
- **Headers on the package and resources**: `private, no-store`, `X-Content-Type-Options: nosniff`, restrictive CSP (no script, no external loads) (REQ-RDR-025).
- **Tickets**: never in a URL or query string, never logged; log redaction test (TST-RDR-004).
- **GET side effects**: only the audit row; a missing copy returns `copy_unavailable` and may enqueue an idempotent rebuild job, never changes entitlement or catalog state.
- **Concurrency and idempotency**: progress `revision` increases or the write is a no-op returning the stored value; bookmark duplicates return the existing row (`created: false`); highlight edit uses `If-Match`.
- **Errors**: `ticket_invalid`, `ticket_expired`, `read_once_consumed`, `copy_unavailable`, `forbidden`, `not_found`, `validation_failed`, `limit_exceeded`, `stale_revision`, `rate_limited` ([error catalog](../../07-contracts/error-catalog.md)). Web maps each to a visible state with a retry (REQ-RDR-022).
- **Rate limits**: open 30 per user per hour; ticket verification and redemption are bounded per user (value to be added to limits).
- **Export**: `/me/export` JSON of all own reading data (REQ-RDR-017); `/me/annotations/export?format=md|json` (SHOULD, REQ-RDR-019).

## Open items

- O-1: the erase route is replaced by an event if `user.deleted` is added.
