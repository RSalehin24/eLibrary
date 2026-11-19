# gateway - API contract

Status: DRAFT

The authoritative contract is [07-contracts/http/gateway.md](../../07-contracts/http/gateway.md): routing table, per-request behaviour and the three internal routes. This page does not repeat it.

| Aspect | Summary |
|---|---|
| Public surface | exactly the `/api/<service>/*` paths of identity, catalog, reader and ingestion; no business route of its own |
| Own routes | internal port only: `GET /internal/health`, `GET /internal/ready` (reports identity reachability), `GET /internal/contract` (REQ-GWY-014) |
| Headers it sets for upstream | `X-Request-Id`, `X-User-Id`, `X-User-Scopes`, `X-Grant-Version`, internal service token; all client-supplied values removed first (REQ-GWY-004) |
| Errors it generates | 401 `unauthenticated`, 403 `forbidden` / `mfa_required` / `csrf_invalid`, 404 `not_found`, 413 `body_too_large`, 429 `rate_limited`, 502 `peer_unavailable`, 503 `peer_unavailable`, 504 `timeout`; codes in the [error catalog](../../07-contracts/error-catalog.md) |
| Events | none emitted, none consumed ([events](../../07-contracts/events/README.md)) |
| Open | **O-2**: security headers on pages (gateway covers API responses only until decided) |
