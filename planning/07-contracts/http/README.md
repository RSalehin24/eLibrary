# HTTP conventions

Status: DRAFT

| Topic | Rule |
|---|---|
| Base path | `/api/<area>/…` public; `/internal/…` private |
| Format | JSON (UTF-8), RFC 3339 UTC timestamps, UUIDs lowercase, enums `snake_case` strings |
| Versioning | URL prefix only on breaking change (`/api/v2/…`); contract crate version in `X-Contract-Version` response header |
| Pagination | keyset: `?after=<opaque token>&limit=<n ≤ 200>`; response `{items, next}`; no offsets for unbounded lists |
| Filtering | repeated params for OR within a facet; distinct params for AND across facets |
| Concurrency | `ETag`/`If-Match` carrying the aggregate `revision`; mismatch → 412 or 409 `stale_revision` |
| Idempotency | `Idempotency-Key` header on non-idempotent POSTs; 24 h dedupe window |
| Errors | [error model](../../04-architecture/cross-cutting/errors.md); codes in [catalog](../error-catalog.md) |
| Auth | cookie session via gateway for browsers; `Authorization: Capability …` for protected bytes |
| CSRF | header `X-CSRF-Token` on cookie-authenticated mutations |
| Caching | public GETs `Cache-Control: public, max-age=60, stale-while-revalidate=300` + `ETag`; private `no-store` |
| Languages | `Accept-Language` (`bn`, `en`); `Content-Language` echoes |
| Limits | see [limits](../../04-architecture/cross-cutting/limits.md) |
| Streaming | SSE for job stream; heartbeat comment every 15 s; `Last-Event-ID` resume |
