# Gateway HTTP contract

Status: DRAFT · Service: [gateway](../../05-services/gateway/README.md) · Requirements: [GWY](../../02-requirements/gwy-gateway.md)

The gateway has **no business API** and no database (REQ-GWY-008). It routes, checks the session with identity, applies rate limits and CSRF, sets request ids and headers, and maps errors.

## Routing table

| Public path | Upstream | Notes |
|---|---|---|
| `/api/identity/*` | identity (internal HTTP) | public allow-list routes skip the session check |
| `/api/catalog/*` | catalog | files are proxied as a stream from the service, never read from disk |
| `/api/reader/*` | reader | the book package is streamed |
| `/api/ingestion/*` | ingestion-api | SSE passes through unbuffered (REQ-GWY-013) |
| `/api/notify/*`, `/internal/*`, anything else | none | 404; `/internal/*` is never routed |

Pages (`/`) go from Caddy to `web`, not through the gateway.

## Per-request behaviour

1. Validate or generate `X-Request-Id`; remove every client-supplied `X-User-*`, `X-Grant-Version`, `Authorization: Service` and ticket-unrelated internal header.
2. Unless the route is on the public allow-list: call identity `POST /internal/authorize` `{method, path, cookie, origin, csrf_token?}`. Allow returns user id, scopes and grant version; no or invalid session gives 401 `unauthenticated`; a denied session (suspended or disabled account, TOTP incomplete for a management route) gives 403; identity unreachable or timed out gives 503 `peer_unavailable`. Never allow on error.
3. For cookie-authenticated mutations require `X-CSRF-Token` bound to the session and a matching `Origin`; the gateway checks `Origin` and identity verifies the token inside `/internal/authorize` (403 `csrf_invalid`).
4. Apply rate limits (per address and per subject; stricter for anonymous and authentication routes) held in bounded in-memory tables: 429 `rate_limited` with `Retry-After`.
5. Forward with the identity headers and the internal service token; enforce header and body size per route class, timeouts, per-upstream concurrency and the open-stream limit.
6. Map failures: upstream timeout 504 `timeout`, upstream failure 502 `peer_unavailable`, overload 503. The gateway never logs cookies, tickets or authorization headers.
7. Set security headers on API responses (CSP, HSTS, frame, referrer, content-type options). Who sets headers on pages: **OPEN (O-2)**.

## Internal routes (internal port only)

| Method | Path | Purpose |
|---|---|---|
| GET | `/internal/health` | liveness |
| GET | `/internal/ready` | readiness: reports whether identity is reachable |
| GET | `/internal/contract` | contract version |

The gateway emits and consumes no events.
