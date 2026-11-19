# gateway

Status: DRAFT (six-service design, D-31)

The only door to the backend. It routes `/api/<service>/*`, asks identity whether the request may proceed, applies rate limits, CSRF and size bounds, stamps request ids and headers, and maps failures to the typed error envelope. It holds no business logic, no database and no scope decisions of its own (REQ-GWY-008).

| | |
|---|---|
| Owns | the route table, the public allow-list (closed, in code), bounded in-memory rate-limit tables, the open-stream registry. No persistent data. |
| Does not own | sessions, users, scopes, grants (identity); any domain type; files; pages (`web`); TLS (Caddy) |
| Requirements | REQ-GWY-001...014 (coverage table below) |
| Emits / consumes | no events |
| Talks to | identity (`POST /internal/authorize`), catalog, reader, ingestion-api, identity public routes (upstreams, internal HTTP with service token) |
| Called by | Caddy (everything except `/`), nothing else |
| Tech | Rust, async HTTP server and client, streaming bodies; crates per [dependency policy](../../04-architecture/dependency-policy.md) (no new dependency without owner approval) |
| Contract | [HTTP contract](../../07-contracts/http/gateway.md) |

## Non-responsibilities

No scope names or role logic (it forwards what identity returns); no database, no cache service (counters are in memory); no file serving from disk, no `/media/` (REQ-GWY-011); no event production or consumption; no page rendering; the gateway crate depends on no domain or storage crate (INV-GWY-008).

## Request pipeline (fixed order)

1. Reject non-`/api/` paths, `/internal/*` and unknown service prefixes with 404 (REQ-GWY-001).
2. Accept or generate the request id; strip every client-supplied identity header (REQ-GWY-004, REQ-GWY-006).
3. Classify the route: `Public` (closed allow-list, REQ-GWY-003) or `Protected`.
4. Rate-limit by address, and by subject once known (REQ-GWY-007).
5. Protected: call identity `/internal/authorize` with method, path, cookie, origin and CSRF token (REQ-GWY-002, REQ-GWY-005). Allow gives user id, scopes, grant version; 401, 403 pass through; error or timeout gives 503 (never allow).
6. Check size and concurrency bounds, then forward with identity headers and the internal service token; stream both directions (REQ-GWY-010, REQ-GWY-011).
7. Map upstream failure to the envelope; add security headers; return the request id (REQ-GWY-009, REQ-GWY-012).

## Structure (crates, small modules)

```
gateway/src/
  main.rs            config load, startup checks, server bind (public port + internal port)
  routes.rs          RouteTable: prefix -> Upstream (exhaustive enum); PublicRoutes allow-list
  pipeline.rs        the seven steps above, one small function each
  authorize.rs       identity client, AuthorizeOutcome -> Decision mapping
  limits.rs          RateLimiter (bounded table), ConcurrencyGate, StreamRegistry
  headers.rs         strip / stamp identity headers, security headers
  errors.rs          GatewayError -> envelope + status (one exhaustive function)
  health.rs          /internal/health, /internal/ready, /internal/contract
```

## Failure behaviour

| Failure | Result |
|---|---|
| Identity unreachable, slow or returns garbage | 503 `peer_unavailable` + `Retry-After`; never forwarded (INV-GWY-002) |
| Upstream timeout / failure / overload | 504 `timeout` / 502 `peer_unavailable` / 503 (REQ-GWY-012) |
| Rate-limit table full | oldest-idle keys evicted; limited keys stay limited; memory never exceeds the bound (INV-GWY-007) |
| Stream session revoked or idle | stream closed by the gateway (REQ-GWY-013) |
| Gateway restart | counters reset (accepted at this scale); no data lost; sessions live in identity |

Open points touching this service: **O-2** (who sets security headers on pages: the gateway covers API responses only until decided); **Q-4** (Caddy publishes port 80 only for the certificate flow; confirm in deployment docs).

## Requirements covered

| REQ | Where |
|---|---|
| REQ-GWY-001 | pipeline step 1; [test plan](test-plan.md) TST-GWY-001 |
| REQ-GWY-002 | step 5; [state machines](state-machines.md) request decision; TST-GWY-002/003 |
| REQ-GWY-003 | [domain model](domain-model.md) `PublicRoutes`; TST-GWY-004 |
| REQ-GWY-004 | step 2; TST-GWY-005/006 |
| REQ-GWY-005 | step 5; TST-GWY-007 |
| REQ-GWY-006 | step 2; TST-GWY-008 |
| REQ-GWY-007 | step 4; TST-GWY-009/010 |
| REQ-GWY-008 | non-responsibilities; TST-GWY-011 |
| REQ-GWY-009 | step 7; TST-GWY-012 (O-2 open for pages) |
| REQ-GWY-010 | step 6; TST-GWY-013/014 |
| REQ-GWY-011 | step 6; TST-GWY-015 |
| REQ-GWY-012 | step 7; TST-GWY-016 |
| REQ-GWY-013 | [state machines](state-machines.md) stream; TST-GWY-017 |
| REQ-GWY-014 | `health.rs`; TST-GWY-018 |

See [domain model](domain-model.md) | [API](api-contract.md) | [state machines](state-machines.md) | [tests](test-plan.md).
