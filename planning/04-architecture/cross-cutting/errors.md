# Error model

Status: DRAFT

## Shape (all HTTP errors)

```json
{ "error": { "code": "not_found", "message": "…human, localized…",
             "request_id": "…", "details": { … } } }
```

- `code` is a stable machine identifier from the [error catalog](../../07-contracts/error-catalog.md).
- 401 `unauthenticated` (no valid session) and 403 `forbidden` (denied, with `details.reason`) are always distinct; a 403 never ends the client session.
- Each code carries a class `retryable` or `permanent` (`rate_limited` and `auth_required` are refinements used by ingestion jobs); retry never depends on the message.
- The gateway maps upstream failures to the same envelope (502, 503, 504).
- `message` is safe to display; it never contains secrets, stack traces, SQL, or internal ids.
- Status codes are derived from `code` by one exhaustive `fn status(&Error) -> StatusCode` per service.

## Classification

| Class | Examples | Retry? | Alert? |
|---|---|---|---|
| Client | validation, not found, forbidden (403), unauthenticated (401), conflict (stale revision) | no | no |
| Policy | rate limited, quota | after `Retry-After` | metric |
| Transient | timeout, peer unavailable, serialization failure | yes (idempotent) | on sustained rate |
| Permanent | contract mismatch, corrupted artifact, invariant violation | no | page |

An **invariant violation** (a state that must be impossible) is never swallowed: it aborts
the unit of work, records an `invariant_violation` event with context, increments a metric
that pages, and returns `internal_error`. This turns "should never happen" into a signal.

## Rules

1. Library crates define closed error enums (`thiserror`); no `anyhow`, no `Box<dyn Error>` in public signatures.
2. Conversions between crates are explicit `From` impls; no catch-all variant named `Other`.
3. `?` crosses only into the same error type or a documented variant.
4. Background work reports errors as job/outbox state, never logs-and-drops.
5. User-visible messages are localized (bn/en) from catalogs keyed by `code`.
