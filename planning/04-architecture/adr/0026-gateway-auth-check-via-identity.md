# ADR-0026 — Gateway checks every request with identity; Caddy handles HTTPS only

Status: ACCEPTED

Supersedes [ADR-0024](0024-caddy-forward-auth-deny-by-default.md). Basis: D-31, D-34, D-35, D-37, D-41.

## Context
The legacy system defaulted to `AllowAny`, had wildcard roles (`is_staff`, `admin:full_control`) and let ownership bypass gates. ADR-0024 put the authentication call in Caddy; D-31 moves it into a gateway service and limits Caddy to HTTPS and certificate auto-renewal.

## Decision
- **Caddy** terminates TLS and forwards `/` to `web` and `/api/*` to `gateway`; nothing else. It serves no files and makes no authorization decision.
- The **gateway** routes `/api/{identity,catalog,reader,ingestion}/*` to the matching service. For every `/api/*` request except the public routes it calls `identity` `/internal/authorize`; identity returns the verified user id and scopes as headers, which the gateway sets on the upstream request after stripping any client-supplied copies. The gateway also applies rate limits and CSRF checks.
- Services trust those headers only from the gateway on the internal network; service-to-service calls carry an internal service token that the callee verifies. Reading tickets are verified by asking identity (D-37).
- Public routes (no session): identity sign-in, invite acceptance, password reset request and confirm, and catalog browse, search and detail of **metadata only** (D-34). Preview text and reading need sign-in. There is no demo role or demo sign-in (D-35).
- **Deny by default.** Roles `reader`, `operator`, `admin`; scopes `browse`, `preview`, `read`, `read_once`, `download`, `kindle`, `operate`, `manage_catalog`, `manage_users` (`preview` and `read` are separate, D-41). Grants are explicit rows (user, scope, optional book, optional expiry, granted_by). No wildcard roles; "My Books" is a shelf and never grants access.
- Every `/api/*` route declares its required scope in code. A route without a declaration makes the service refuse to start (fail closed). Files are never served by Caddy or the gateway; only services stream them, after a check.

## Consequences
+ One authorization authority (identity) and one enforcement point at the edge (gateway); the scope table is generated from route declarations and testable.
+ Caddy configuration is minimal; the gateway is ordinary Rust under the same tests as other services.
- Every authenticated request costs one internal call to identity; its availability is critical (a short decision cache is allowed only within the staleness bound in [service authentication](../cross-cutting/service-auth.md)).
- Correctness depends on the gateway stripping inbound identity headers and on services being unreachable except through it; both are covered by deployment tests.
