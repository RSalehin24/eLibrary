# Error catalog

Status: DRAFT (rewritten for six services, tickets verified by identity, internal service tokens; no demo account, D-35)

Stable machine codes. One envelope everywhere: `{ "error": { "code", "message", "request_id", "details"? } }`. HTTP status is derived per service from the code by one exhaustive function. Messages are localized from catalogs keyed by code (INV-WEB-009) and never carry secrets, SQL or internal ids. Every code has a class, `retryable` or `permanent`; retry decisions use the class, never the message. Model: [errors](../04-architecture/cross-cutting/errors.md).

## 401 versus 403 (always distinct)

| Status | Code | Meaning | Client behaviour |
|---|---|---|---|
| 401 | `unauthenticated` | no valid session: `details.reason` in `missing`, `expired`, `revoked` | clear session state and go to sign-in |
| 403 | `forbidden` | valid session, action denied; `details.reason` is one of the deny reasons below | show the denial; **never end the session**; the UI derives gates from `/me/capabilities`, the server stays the authority |
| 403 | `mfa_required` | the account requires TOTP and this session has not completed it | go to the TOTP step |
| 403 | `csrf_invalid` | missing or wrong CSRF token or `Origin` | reload the session response for a new token |
| 401 | `service_token_invalid` | internal call without a valid token, or caller not allowed on the route (internal routes only) | none (service bug) |

### Deny reasons (`details.reason` of `forbidden`, from identity `decide`)

`no_scope` (scope or grant missing), `grant_expired`, `account_inactive` (invited, suspended or disabled), `mfa_incomplete` (mapped to `mfa_required`), `read_once_consumed` (mapped to its own code), `self_action` (an admin acting on their own account), `last_admin`. `book_not_published` and `book_deleted` are mapped to `not_found` for a subject without `manage_catalog`, so a non-visible book is indistinguishable from an unknown one.

## Common

| Code | HTTP | Meaning | Class |
|---|---|---|---|
| `validation_failed` | 422 | field-level errors in `details.fields` | permanent |
| `body_too_large` | 413 | exceeds limit | permanent |
| `rate_limited` | 429 | `Retry-After` set | retryable |
| `not_found` | 404 | unknown **or** not visible (indistinguishable) | permanent |
| `conflict` | 409 | uniqueness or state conflict with a field path | permanent |
| `stale_revision` | 412 | `If-Match` revision mismatch; reload, never merge | permanent |
| `idempotency_conflict` | 422 | key reused with a different request | permanent |
| `invalid_transition` | 409 | state machine forbids the action in this state | permanent |
| `limit_exceeded` | 422 | per-account, per-book or bulk-size limit | permanent |
| `peer_unavailable` | 503 | dependency down or identity unreachable (never allowed on error); `Retry-After` | retryable |
| `queue_unavailable` | 503 | the job queue cannot accept work; nothing ran inline | retryable |
| `timeout` | 504 | | retryable |
| `internal_error` | 500 | unexpected; request id in body | permanent |
| `route_scope_missing` | 500 | a route without a declared scope (the service refuses to start; never reaches a client) | permanent |

## Identity

| Code | HTTP | Meaning | Class |
|---|---|---|---|
| `invalid_credentials` | 401 | uniform for unknown or wrong | permanent |
| `invalid_code` | 422 | TOTP code wrong or step already used | retryable |
| `link_invalid` | 410 | consumed, expired, superseded or unknown (uniform) | permanent (request a new one) |
| `weak_password` | 422 | policy | permanent |
| `email_taken` | 409 | invite for an existing address | permanent |
| `duplicate_grant` | 409 | same user, scope and book already granted | permanent |
| `invalid_image` | 422 | profile image type or size rejected | permanent |

## Reading

| Code | HTTP | Meaning | Class |
|---|---|---|---|
| `ticket_invalid` | 403 | missing, malformed, wrong user, book or version, revoked, or issued before a grant change or user disable | permanent (open the book again) |
| `ticket_expired` | 410 | older than 15 minutes | retryable (reopen) |
| `read_once_consumed` | 403 | the single reading was used | permanent |
| `copy_unavailable` | 503 | reading copy not Ready yet (building or failed); `Retry-After` | retryable |

## Catalog

| Code | HTTP | Meaning | Class |
|---|---|---|---|
| `export_too_large` | 422 | CSV over the row cap | permanent (narrow the filter) |
| `no_credit` | 422 | a published book needs a writer, translator, editor or compiler credit | permanent |
| `slug_taken` | 409 | slug already used | permanent |
| `duplicate_saved_filter` | 409 | same name or query already saved | permanent |
| `kindle_not_available` | 422 | no Kindle address, no published EPUB, or file above the size cap | permanent |
| `invalid_artifact` | 422 | internal publish: checksum, size or type mismatch | permanent |

## Ingestion

| Code | HTTP | Meaning | Class |
|---|---|---|---|
| `duplicate_book` | 409 | exact duplicate in catalog; goes to duplicate review | permanent |
| `auth_required` | 409 | source credential missing, expired or rejected; request `awaiting_credential` | `auth_required`, after a new cookie |
| `source_unavailable` | 502 | source site error or timeout | retryable |
| `source_rate_limited` | 429 | source asked to slow down; retry-after honoured | `rate_limited` |
| `source_locked` | 422 | locked chapters; review item | permanent (review) |
| `source_changed` | 422 | layout drift detected | permanent (review) |
| `invalid_document` | 422 | curated document invalid | permanent |
| `conservation_failed` | 500 | invariant violation (alerts) | permanent |
| `build_failed` | 422 | audit gate failed; `details.stage` | permanent (operator retry) |
| `catalog_rejected` | 422 | catalog refused the publish call (hash mismatch, missing credit, slug taken) | permanent (review) |

Job-level retry decisions use only the class (`retryable`, `rate_limited` with retry-after, `auth_required`, `permanent`) attached to these codes ([ingestion orchestration](../05-services/ingestion/orchestration/README.md)), never the message text.

## Notify (typed reasons in the delivery log and internal responses)

| Reason | Meaning | Class |
|---|---|---|
| `unsupported_format` | not an EPUB | permanent |
| `too_large` | total mail size above 50 MB | permanent |
| `no_address` | missing or invalid Kindle address | permanent |
| `sender_not_approved` | owner has not confirmed our sender on the Amazon approved list | permanent |
| `smtp_failed` | SMTP error or timeout | retryable to the maximum attempt count, then `failed` |

Removed since the earlier design: `forbidden_demo` and `DemoRestricted` (D-35), `refresh_limit` (no refresh chain), `epub_invalid` (no manual upload, D-42).
