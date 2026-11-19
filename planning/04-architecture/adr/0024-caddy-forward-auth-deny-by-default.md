# ADR-0024 — Caddy forward-auth and deny-by-default scope declaration

Status: SUPERSEDED

Superseded by [ADR-0026](0026-gateway-auth-check-via-identity.md) (D-31: the gateway, not Caddy, asks identity; Caddy handles HTTPS only; the demo role and demo sign-in were dropped by D-35; public preview text was dropped by D-34). Kept as history; the deny-by-default and scope-declaration rules below carry over unchanged.

Originally superseded the gateway design (assertion minting, `X-Subject-Assertion`, [ADR-0011](0011-authentication.md) gateway caching note). Basis: D-27.

## Context
The legacy system defaulted to `AllowAny`, had wildcard roles (`is_staff`, `admin:full_control`), and let ownership bypass gates. With the gateway removed, authentication must happen at the edge without a custom proxy.

## Decision
- **Caddy** terminates TLS and routes `/` to `web` and `/api/{identity,catalog,reader,ingestion}/*` to the matching service. For every `/api/*` request except the public routes it calls `identity` `/internal/authorize` (Caddy `forward_auth`). Identity returns the verified user id and scopes as response headers, which Caddy copies to the upstream request.
- Services trust those identity headers only when the request comes from Caddy on the internal network; Caddy strips any client-supplied copies. Service-to-service calls carry an internal service token that the callee verifies.
- Public routes (no session): sign-in, invite acceptance, password reset request and confirm, demo sign-in (a rate-limited POST), catalog public browse, search metadata and published preview text (D-12).
- **Deny by default.** Roles `reader`, `operator`, `admin`, `demo`; scopes `browse`, `preview`, `read`, `read_once`, `download`, `kindle`, `operate`, `manage_catalog`, `manage_users`. Grants are explicit rows (user, scope, optional book, optional expiry, granted_by). No wildcard roles; "My Books" is a shelf and never grants access.
- Every `/api/*` route declares its required scope in code. A route without a declaration makes the service refuse to start (fail closed). Files are never served by Caddy directly; only services stream them, after a check.

## Consequences
+ One authorization authority; the scope table is generated from route declarations and testable.
+ No custom gateway code to maintain.
- Every authenticated request costs one internal call to identity; identity availability is critical (a short cache of decisions is allowed only within the staleness bound in [service authentication](../cross-cutting/service-auth.md)).
- Correctness depends on Caddy stripping inbound identity headers; this is covered by a deployment test.
