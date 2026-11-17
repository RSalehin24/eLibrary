# gateway

Status: DRAFT

The only public listener. Terminates nothing of business logic.

| | |
|---|---|
| Responsibilities | routing by [route table](routing-table.md), session → subject assertion, CSRF, rate limiting, request id, security headers, response caching for public GETs, error normalization |
| Non-responsibilities | authorization decisions (services/access), data, rendering |
| Requirements | REQ-GWY-001…005, REQ-PLT-005 |
| Calls | identity (`sessions/resolve`, cached ≤ 5 s), every routed service |

## Request pipeline (fixed order)

1. Assign `request_id` (accept a valid inbound one only from the trusted proxy).
2. Size/timeouts/headers limits ([limits](../../04-architecture/cross-cutting/limits.md)).
3. Rate limit (per IP, then per subject once known): token bucket in memory with periodic persisted counters for auth endpoints.
4. Resolve session cookie → `Subject` (Anonymous when absent or invalid). Mint a 60 s subject assertion.
5. CSRF check for non-GET with cookie auth: double-submit token + `Origin` match + `SameSite=Lax` cookie.
6. Route (exact match against the table; unknown → 404, never proxied).
7. Forward with assertion + service credential; stream response.
8. Add security headers; cache headers for public GETs per route; log.

## Public caching

Only routes marked `cache: public` in the table; keys include language and exclude cookies; stale-while-revalidate allowed; authenticated responses always `private, no-store`.

## Failure behavior

Upstream unavailable → 503 with the typed error body and `Retry-After`; public cached responses may be served stale ≤ 10 min when upstream is down (`stale-if-error`).
