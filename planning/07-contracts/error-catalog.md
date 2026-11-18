# Error catalog

Status: DRAFT (rewritten for 5 services, reading tickets and internal service tokens)

Stable machine codes. One envelope everywhere: `{ "error": { "code", "message", "request_id", "details"? } }`. HTTP status is derived per service from the code by one exhaustive function. Messages are localized from catalogs keyed by code (INV-WEB-009) and never carry secrets, SQL or internal ids. Model: [errors](../04-architecture/cross-cutting/errors.md).

## Common

| Code | HTTP | Meaning | Retry |
|---|---|---|---|
| `validation_failed` | 422 | field-level errors in `details.fields` | no |
| `body_too_large` | 413 | exceeds limit | no |
| `rate_limited` | 429 | `Retry-After` set | after delay |
| `unauthenticated` | 401 | no valid session | after sign-in |
| `forbidden` | 403 | scope or grant missing; `details.reason` from identity | no |
| `forbidden_demo` | 403 | the demo account cannot mutate or download | no |
| `mfa_required` | 403 | second factor needed | after TOTP |
| `not_found` | 404 | unknown **or** not visible (indistinguishable) | no |
| `conflict` / `stale_revision` | 409 / 412 | revision mismatch | reload |
| `idempotency_conflict` | 422 | key reused with different request | no |
| `invalid_transition` | 409 | state machine forbids the action in this state | no |
| `limit_exceeded` | 422 | per-account or per-book limits | no |
| `peer_unavailable` | 503 | dependency down; `Retry-After` | yes |
| `timeout` | 504 | | yes |
| `internal_error` | 500 | unexpected; request id in body | no |
| `service_token_invalid` | 401 | internal call without a valid token, or caller not allowed for the route | no |
| `route_scope_missing` | 403 | identity has no scope registered for the route (fail closed) | no |

## Identity

| Code | HTTP | Meaning | Retry |
|---|---|---|---|
| `invalid_credentials` | 401 | uniform for unknown or wrong | no |
| `invalid_code` | 422 | TOTP code wrong | yes |
| `link_invalid` | 410 | consumed, expired, superseded or unknown (uniform) | request new |
| `weak_password` | 422 | policy | no |
| `email_taken` | 409 | invite for an existing address | no |
| `duplicate_grant` | 409 | same user, scope and book already granted | no |

## Reading

| Code | HTTP | Meaning | Retry |
|---|---|---|---|
| `read_denied` | 403 | `details.reason` in `NoScope`, `ReadOnceConsumed`, `Unpublished`, `DemoRestricted`, `Inactive`, `MfaRequired` | no |
| `ticket_invalid` | 403 | missing, malformed, wrong user/book/version, or revoked | open the book again |
| `ticket_expired` | 410 | older than 15 minutes | refresh or reopen |
| `read_once_consumed` | 403 | the single read was used | no |
| `refresh_limit` | 403 | refresh chain exceeded | reopen |
| `copy_unavailable` | 503 | reading copy not built yet (rebuild queued) | yes |

## Catalog

| Code | HTTP | Meaning | Retry |
|---|---|---|---|
| `export_too_large` | 422 | CSV over the row cap | narrow filter |
| `duplicate_book` | 409 | intake matched an exact duplicate | no |
| `epub_invalid` | 422 | intake EPUB failed zip, image or sanitize checks | no |

## Ingestion

| Code | HTTP | Meaning | Retry |
|---|---|---|---|
| `auth_required` | 409 | source credential missing, expired or rejected; request `awaiting_credential` | after new cookie |
| `source_unavailable` | 502 | source site error or timeout | auto (job retry) |
| `source_locked` | 422 | locked chapters; review item | review |
| `source_changed` | 422 | layout drift detected | review |
| `invalid_document` | 422 | curated document invalid | no |
| `conservation_failed` | 500 | invariant violation (alerts) | no |
| `build_failed` | 422 | audit gate failed; `details.stage` | operator retry |
| `catalog_rejected` | 422 | catalog refused the candidate | review |

Job-level retry decisions use only the class `retryable` or `permanent` attached to these codes ([ingestion orchestration](../05-services/ingestion/orchestration/README.md)), never the message text.
