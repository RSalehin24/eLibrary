# gateway - domain model

Status: DRAFT

The gateway has **no database** and no domain entities (REQ-GWY-008, INV-GWY-008). It has only configuration and bounded in-memory runtime structures. All types are newtypes or closed enums; functions follow the [coding standards](../../03-correctness/coding-standards.md) (about 20 lines, at most 3 parameters, two nesting levels).

## Value types

| Type | Meaning | Rule |
|---|---|---|
| `RequestId` | UUIDv7 text | generated when absent; a supplied value is accepted only when it parses and is at most 64 ASCII chars, otherwise replaced |
| `Upstream` | enum `Identity`, `Catalog`, `Reader`, `Ingestion` | exhaustive `match`; no `Notify` variant (notify has no public route) |
| `RouteClass` | enum `Public`, `Protected` | from the `PublicRoutes` table only |
| `RouteBodyClass` | enum `Json`, `Upload`, `Stream` | picks header, body and timeout limits |
| `Verdict` | enum `Allow{user_id, scopes, grant_version}`, `Unauthenticated`, `Denied{reason}`, `Unavailable` | the whole result of the identity call; `Unavailable` is also produced by any error or timeout |
| `ClientKey` | enum `Address(IpPrefix)`, `Subject(UserId)` | rate-limit key |
| `Secret<T>` | cookie, CSRF token, service token, reading ticket | no `Display`/`Debug`, never logged (REQ-GWY-004) |

## Static tables (code, mirrored by tests)

| Table | Content | Change rule |
|---|---|---|
| `RouteTable` | `/api/identity/*`, `/api/catalog/*`, `/api/reader/*`, `/api/ingestion/*`; nothing for `/api/notify/*` or `/internal/*` | contract change |
| `PublicRoutes` (closed) | identity sign-in, TOTP verify (pending-session cookie), invite acceptance, password-reset request and confirm; catalog metadata browse, search and detail, covers and summaries; no preview or reading route (D-34) | plan change only (REQ-GWY-003); a test compares it with the list in [IDN](../../02-requirements/idn-identity.md) REQ-IDN-014 |
| `RouteLimits` | per `RouteBodyClass`: max header bytes, max body bytes, timeout; values from [limits](../../04-architecture/cross-cutting/limits.md) | config validated at startup |

## Runtime structures (all bounded, in memory)

| Structure | Bound | Behaviour at the bound |
|---|---|---|
| `RateLimiter` (token bucket per `ClientKey`, separate tables for anonymous, authentication routes, subject) | maximum keys per table; entries expire after an idle window | evict least recently used among non-limited keys; limited keys are never evicted early (INV-GWY-007) |
| `ConcurrencyGate` per `Upstream` | 64 in flight (limits table) | 503 with `Retry-After` |
| `StreamRegistry` | 20 open streams total, 3 per user (limits table) | 429 `rate_limited` |

## Invariants

| ID | Rule | Realised by |
|---|---|---|
| INV-GWY-001 | public paths equal the route table; `/internal/*` never routed | `RouteTable` has no internal variant |
| INV-GWY-002 | forward only after Allow or on a public route | `Verdict` is the only way to build a `ForwardRequest`; `Unavailable` cannot |
| INV-GWY-003 | allow-list has no preview or reading route | table plus equality test |
| INV-GWY-004 | no unproduced identity header reaches upstream | headers are stripped, then set from `Verdict::Allow` in one function |
| INV-GWY-005 | cookie mutations need CSRF | `Method` class check before step 5; identity verifies the token |
| INV-GWY-006 | one request id end to end | `RequestId` created once and passed down |
| INV-GWY-007 | rate tables bounded, quotas hold | `RateLimiter` capacity + property tests |
| INV-GWY-008 | no domain or storage crate dependency | `cargo deny`/dependency check |
| INV-GWY-009 | security headers on every response | response layer applied last |
| INV-GWY-010 | no buffering above bounds | streamed bodies, size-limited readers |
| INV-GWY-011 | no file-system root for assets | configuration has no path setting; review |
| INV-GWY-012 | every generated error is the typed envelope | one `GatewayError -> response` function |
| INV-GWY-013 | stream closed on revocation or idle | `StreamRegistry` + periodic re-authorize |
| INV-GWY-014 | health not reachable from the edge | bound to the internal port only |
