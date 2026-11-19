# Edge and service-to-service authentication

Status: DRAFT (gateway design, D-31, D-37)

## Browser to Caddy to gateway to service

The browser holds an opaque session cookie (HttpOnly, Secure, SameSite=Lax, [ADR-0011](../adr/0011-authentication.md)). Caddy only terminates HTTPS, renews certificates and forwards `/` to `web` and `/api/*` to `gateway` ([ADR-0026](../adr/0026-gateway-auth-check-via-identity.md), to be aligned with D-31 by its owner; full secret inventory: ../../10-security/secrets-and-keys.md). For every `/api/*` request except the closed public allow-list, the gateway calls `identity POST /internal/authorize` with the cookie, method, path, origin and CSRF token. Identity answers Allow with the verified user id, scopes and grant version, 401 (no valid session) or 403 (session denied: inactive account, TOTP incomplete). The gateway removes every client-supplied identity header and sets them from the reply; it fails closed (identity unreachable gives 503, never an allow). The gateway holds no scope decisions of its own.

Public routes (no session): identity sign-in, invite acceptance, password reset request and confirm, catalog metadata browse, search, detail and cover (D-34). Preview text and reading need sign-in. No demo sign-in exists (D-35).

## Service to service

Each internal call carries an **internal service token** naming the caller and callee, short-lived (at most 60 s), signed with the caller's key. The callee checks a static allow-list `{caller -> permitted routes}` generated from the contract crates. A service accepts the identity headers only on requests that arrive from the gateway with a valid token, never from other callers. When an action depends on a grant, a book or a book state, the service asks identity (`POST /internal/check`); it never authorizes from a forwarded header alone for those.

## Scope declaration (fail closed)

Every `/api/*` route declares its required scope in code (`browse`, `preview`, `read`, `read_once`, `download`, `kindle`, `operate`, `manage_catalog`, `manage_users`, `session`, or an explicit `public`). The service verifies at startup that every route has a declaration and refuses to start otherwise; at run time it rejects a request whose forwarded scopes do not include the declared one (403 `forbidden`, reason `no_scope`). Management scopes are present in the forwarded scopes only when the session completed TOTP where the account requires it. Ownership, importing and "My Books" never grant access.

## Reading tickets (D-37)

Reader calls identity to decide and mint (`/internal/tickets`); the ticket is an opaque random value stored (hashed) only by identity, bound to user, book and version and carrying the grant version, valid 15 minutes, header or body only, never in a URL. Reader verifies every redemption with identity (`/internal/tickets/verify`), so revocation (disabled user, grant change, unpublished book) is immediate and no verification key lives in the reader ([ADR-0023](../adr/0023-reader-renders-whole-book.md)).

## Keys

| Key | Holder | Verifiers | Rotation |
|---|---|---|---|
| Service-token keys (one per service) | each service | peers | 90 d, overlapping `kid` |
| Session/TOTP encryption key | identity | identity | 180 d with re-encrypt job |
| Source-site cookie | secret file mounted read-only into the ingestion containers | ingestion | by the operator, no rebuild |

Key material is loaded from Compose secret files (0400), never from environment variables or logs ([secrets](../../10-security/secrets-and-keys.md)).

## Trust rules

1. A service never authorizes from a forwarded header alone for a grant-dependent action; it asks identity.
2. Anonymous exists only on declared public routes; a missing identity header on any other route is a rejection, never anonymous.
3. Internal routes (`/internal/*`) are unreachable from the public edge: neither Caddy nor the gateway routes them.
4. Admin recovery is a documented host command, not an HTTP route (D-38).
