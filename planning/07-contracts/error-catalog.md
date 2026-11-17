# Error catalog

Status: DRAFT

Stable machine codes. HTTP status is derived per service from the code. Messages are localized from catalogs keyed by code (INV-WEB-009).

| Code | HTTP | Meaning | Retry |
|---|---|---|---|
| `validation_failed` | 422 | field-level errors in `details.fields` | no |
| `body_too_large` | 413 | exceeds limit | no |
| `rate_limited` | 429 | `Retry-After` set | after delay |
| `unauthenticated` | 401 | no valid session | after login |
| `forbidden` | 403 | decision Deny; `details.reason` is a `DenyReason` | no |
| `forbidden_demo` | 403 | demo accounts cannot mutate | no |
| `mfa_required` | 403 | second factor needed | after TOTP |
| `not_found` | 404 | unknown **or** not visible (indistinguishable) | no |
| `conflict` / `stale_revision` | 409 / 412 | revision mismatch | reload |
| `idempotency_conflict` | 422 | key reused with different request | no |
| `invalid_credentials` | 401 | uniform for unknown/known | no |
| `invalid_code` | 422 | TOTP code wrong | yes |
| `link_invalid` | 410 | consumed/expired/superseded/unknown (uniform) | request new |
| `weak_password` | 422 | policy | no |
| `email_taken` | 409 | admin invite | no |
| `invalid_transition` | 409 | state machine forbids | no |
| `read_denied` | 403 | with `DenyReason` (`ReadOnceConsumed`, `NoGrant`, …) | no |
| `capability_invalid` / `capability_expired` / `capability_wrong_book` | 401/403 | token problems | refresh |
| `artifact_set_changed` | 409 | content changed; refetch capability | yes |
| `snapshot_expired` | 410 | search pagination snapshot gone | restart |
| `export_too_large` | 422 | > row cap | narrow filter |
| `limit_exceeded` | 422 | per-account limits (highlights etc.) | no |
| `document_schema_unsupported` | 422 | internal | no |
| `conservation_failed` | 500 | invariant violation (pages) | no |
| `build_failed` | 502 | with `stage` | admin retry |
| `source_unavailable` | 502 | acquisition upstream | auto |
| `source_locked` | 422 | locked chapters | review |
| `peer_unavailable` | 503 | dependency down; `Retry-After` | yes |
| `timeout` | 504 | | yes |
| `internal_error` | 500 | unexpected; request id in body | no |
