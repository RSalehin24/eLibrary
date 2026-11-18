# identity - API contract

Status: DRAFT - source of truth: generated schema in [07-contracts](../../07-contracts/http/README.md)

Public prefix `/api/identity`. Caddy forward-auths every `/api/*` request except the public routes marked `public`. Every route lists its required scope (declared in code; a route without a declaration fails startup). `session` = any signed-in non-demo user with no scope beyond that.

## Public and session routes

| Method and path | Scope | Request -> response | Errors |
|---|---|---|---|
| `POST /sign-in` | public | `{email, password}` -> `200 {state:"authenticated"}` or `{state:"totp_required"}` | `invalid_credentials` (uniform), `rate_limited` |
| `POST /sign-in/totp` | public (password-ok pending session) | `{code}` -> `200` | `invalid_code`, `rate_limited` |
| `POST /demo/sign-in` | public | `{}` -> `200` (demo session) | `demo_disabled`, `rate_limited` |
| `POST /sign-out` | session | -> `204` | none |
| `GET /session` | session | -> `{user_id, display_name, roles, scopes, language, demo, expires_at}` (drives the UI; the UI is not authorization) | `unauthenticated` |
| `POST /invites/accept` | public | `{token, password}` -> `200` | `link_invalid` (uniform), `weak_password` |
| `POST /password/reset-request` | public | `{email}` -> `202 {}` always (DRAFT proposal, see README) | `rate_limited` |
| `POST /password/reset-confirm` | public | `{token, password}` -> `200` | `link_invalid`, `weak_password` |
| `GET /me`, `PATCH /me` | session, not demo | profile (`display_name`, `language`, `kindle_emails`) with `If-Match: revision` | `stale_revision`, `forbidden_demo`, `validation` |
| `POST /me/password` | session, not demo | `{current, new}` -> `204`, revokes other sessions | `invalid_credentials`, `weak_password` |
| `POST /me/totp/setup`, `/confirm`, `/disable` | session, not demo | setup returns secret and otpauth URI once; disable needs current password and a code | `invalid_code`, `reauth_required` |

## Administration (`manage_users`, TOTP-complete when enabled)

| Method and path | Request -> response | Errors |
|---|---|---|
| `GET /admin/users?status&q&after` | keyset page of users | none |
| `POST /admin/users` | `{email, display_name, language, roles[]}` -> `201`, creates `invited` user, issues invite token, writes `email.requested` | `email_taken`, `validation` |
| `GET /admin/users/{id}`, `PATCH /admin/users/{id}` | edit name, language, roles; `If-Match` | `stale_revision`, `self_edit_forbidden` (own roles), `last_admin` |
| `POST /admin/users/{id}/resend-invite` | new token supersedes the old | `invalid_transition` |
| `POST /admin/users/{id}/suspend`, `/reactivate`, `/disable` | status change; revokes sessions; emits `user.disabled` on disable and suspend | `invalid_transition` |
| `GET /admin/grants?user&book` , `POST /admin/grants` | `{user_id, scope, book_id?, expires_at?, reason}` | `duplicate_grant`, `self_grant_forbidden`, `scope_not_grantable`, `validation` |
| `PATCH /admin/grants/{id}` | expiry only; `If-Match` | `stale_revision` |
| `DELETE /admin/grants/{id}` | revoke (sets `revoked_at`) | none |
| `GET /admin/demo-set`, `PUT /admin/demo-set/{book_id}`, `DELETE /admin/demo-set/{book_id}` | curated demo books | none |
| `GET /admin/audit?actor&action&after` | audit page | none |

Each grant, role, status and demo-set change writes `audit_log` and, where listed, `events` in the same transaction (REQ-ACC-011).

## Internal (service token required; never routed by Caddy to the outside)

| Route | Request -> response |
|---|---|
| `GET /internal/authorize` | Caddy forwards `Cookie`, `X-Forwarded-Method`, `X-Forwarded-Uri`. Identity matches the route against the registered route-to-scope table. `200` with `X-User-Id`, `X-User-Scopes`, `X-User-Demo`, `X-Request-Id`; `401` unauthenticated; `403 {reason}` missing scope or demo restriction; a route with no registered scope is `403` (fail closed). Services accept these headers only from Caddy's network. |
| `POST /internal/check` | `{user_id, scope, book?: {id, published}}` -> `{allow: true}` or `{allow: false, reason}`. For `read_once` also `consume: bool`: with `consume=true` and the check passing, the use is recorded atomically (PK `(user_id, book_id)` insert), and a second consume returns `ReadOnceConsumed`. Pure read when `consume=false`. |
| `POST /internal/routes` | service boot: registers `{service, routes:[{method, pattern, scope}]}`; replaces that service's table |
| `GET /internal/events?after=<cursor>&limit=` | `{events:[{id,type,payload,at}], next}` ascending by id; empty page returns same cursor; consumers are idempotent |
| `GET /internal/users/{id}/contact` | notify only: `{email, language, kindle_emails}` for sending (never in events) |
| `GET /internal/tokens/{event_id}` | notify only, one-shot: returns the invite or reset link text for a pending `email.requested`, then marks it fetched (secrets never in the event payload) |
| `GET /internal/contract` | handshake |

## Error model

`{ "error": { "code": "<snake_case>", "message": "<safe text>", "request_id": "..." } }` with RFC 9457 fields optional. Status mapping: `401 unauthenticated`, `403 forbidden|forbidden_demo|mfa_required`, `404 not_found`, `409 stale_revision|email_taken|duplicate_grant`, `422 validation|weak_password`, `429 rate_limited` with `Retry-After`. Credential and link failures are uniform and never reveal which part failed.
