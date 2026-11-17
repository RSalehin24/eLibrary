# Error model

Status: DRAFT

## Shape (all HTTP errors)

```json
{ "error": { "code": "book_not_found", "message": "…human, localized…",
             "request_id": "…", "details": { … } } }
```

- `code` is a stable machine identifier from the [error catalog](../../07-contracts/error-catalog.md).
- `message` is safe to display; it never contains secrets, stack traces, SQL, or internal ids.
- Status codes are derived from `code` by one exhaustive `fn status(&Error) -> StatusCode` per service.

## Classification

| Class | Examples | Retry? | Alert? |
|---|---|---|---|
| Client | validation, not found, forbidden, conflict (stale revision) | no | no |
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
