# Edge and service-to-service authentication

Status: DRAFT

## Browser to Caddy to service

The browser holds an opaque session cookie (HttpOnly, Secure, SameSite=Lax, [ADR-0011](../adr/0011-authentication.md)). For every `/api/*` request except the public routes, Caddy calls `identity /internal/authorize` (forward-auth) with the cookie. Identity answers 2xx with the verified user id and scopes as headers, or 401/403. Caddy copies those headers onto the upstream request and removes any client-supplied copies. There is no gateway and no signed subject assertion ([ADR-0024](../adr/0024-caddy-forward-auth-deny-by-default.md)).

Public routes (no session): identity sign-in, invite acceptance, password reset request and confirm, demo sign-in (rate-limited POST), catalog public browse, search metadata and published preview text.

## Service to service

Each internal call carries an **internal service token** naming the caller and callee, short-lived (at most 60 s), signed with the caller's key. The callee checks a static allow-list `{caller -> permitted routes}` generated from the contract crates. Calls that act for a user pass the verified user id; the callee asks identity (`/internal/check`) when the action depends on a grant. Services trust the identity headers only on requests arriving from Caddy (network position plus allow-list), never from other callers.

## Scope declaration (fail closed)

Every `/api/*` route declares its required scope in code (`browse`, `preview`, `read`, `read_once`, `download`, `kindle`, `operate`, `manage_catalog`, `manage_users`, or an explicit `public`). The service verifies at startup that every route has a declaration and refuses to start otherwise; at run time it rejects a request whose forwarded scopes do not include the declared one. Ownership and "My Books" never grant access.

## Reading tickets

Issued by `reader` after an identity check; signed, bound to user, book and version, 15 minutes, header or body only, never in a URL, invalid after `user.disabled` or `grant.changed` ([ADR-0023](../adr/0023-reader-renders-whole-book.md)).

## Keys

| Key | Holder | Verifiers | Rotation |
|---|---|---|---|
| Service-token keys (one per service) | each service | peers | 90 d, overlapping `kid` |
| Reading-ticket key | reader | reader | 90 d, 2 active `kid`s |
| Session/TOTP encryption key | identity | identity | 180 d with re-encrypt job |

Key material is loaded from Compose secret files (0400), never from environment variables of child processes or logs ([secrets](../../10-security/secrets-and-keys.md)).

## Trust rules

1. A service never authorizes from a forwarded header alone for a grant-dependent action; it asks identity.
2. Anonymous exists only on declared public routes; a missing identity header on any other route is a rejection, never anonymous.
3. Internal routes (`/internal/*`) are unreachable from the public edge: Caddy does not route them.
