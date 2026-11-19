# notify

Status: DRAFT

Sends mail (invites, password resets, password-changed notices) and Kindle deliveries over SMTP with retries, so mail failures never block anything else.

| | |
|---|---|
| Owns | outbox of mails, templates, delivery log, Kindle delivery log, event cursors, SMTP credentials (secret file) |
| Does not own | users and tokens (identity), books and EPUB files (catalog), the permission decision |
| Requirements | REQ-NTF-001...004 |
| Emits | none required (delivery state is queryable; no other service consumes it) |
| Consumes | `email.requested` (identity), `kindle.requested` (catalog), pulled from their `GET /internal/events?after=<cursor>` with a stored cursor; idempotent |
| Calls | identity (`/internal/users/{id}/contact`, `/internal/tokens/{event_id}` one-shot link text), catalog (`GET /internal/books/{id}/versions/{v}/epub`, streaming) |
| Called by | web admin (delivery log), nobody else |

## Flow

1. **Pull.** A single in-process loop reads each source's events after its cursor, inserts one outbox row per event under `UNIQUE (source, event_id, kind)` in the same transaction as the cursor advance, and continues. Duplicate or replayed events hit the unique key and do nothing (INV-NTF-001).
2. **Send.** A sender claims due rows with `FOR UPDATE SKIP LOCKED`, renders the template in the user's language (`bn`/`en`), sends through the `MailTransport` trait (SMTP; local sink for dev and tests) and records the result. Transient errors retry with exponential backoff up to 24 h, then `failed` (admin sees it; account creation is never blocked).
3. **Secrets.** Event payloads carry no addresses and no link text. For invites and resets notify fetches the link through the one-shot internal call right before sending; the text is held only in memory and the rendered body (INV-NTF-004).
4. **Kindle.** `kindle.requested` was created by catalog after identity allowed `kindle`. Notify preflights: address is on the user's profile (read from identity), EPUB size <= 50 MB total per email (third-party guidance, re-verify before launch), recorded sender-approval confirmation; then streams the EPUB from catalog, attaches, sends. A failed preflight is `rejected(reason)` with a user-visible reason.

## Safety

- Links, tokens and addresses never appear in logs, events or error text; the log keeps a salted address hash.
- Per-address mail rate (5/h), global send rate, Kindle size cap and per-user daily Kindle cap are enforced before sending.
- Provider outage: backoff, then `failed` plus an admin notice; nothing else blocks.

See [domain model](domain-model.md) | [API](api-contract.md) | [state machines](state-machines.md) | [tests](test-plan.md).
