# Identity HTTP contract

Status: DRAFT · Service: [identity](../../05-services/identity/README.md) · Requirements: [IDN](../../02-requirements/idn-identity.md) · Conventions: [README](README.md)

Identity owns users, credentials (Argon2id), sessions (opaque, server-side, cookie), TOTP, invites, password reset, roles, grants, reading tickets, read-once counters, profile images (D-44) and the audit log (D-40). It is the only place that decides who may do what. **Admin reset is not exposed over HTTP**: it is a documented host command (D-38) that refuses to run unless used on the host; admins cannot change themselves or remove the last admin. No seed, test or advance route is compiled into production builds.

Roles: `reader`, `operator`, `admin`. Scopes: `browse`, `preview`, `read`, `read_once`, `download`, `kindle`, `operate`, `manage_catalog`, `manage_users`. Default grants of a new reader (`browse`, `preview`, `read`, `kindle`) are configuration (D-30, D-41).

## Public API (`/api/identity`) - 37 routes

### Session and sign-in

| Method | Path | Scope | Purpose | Errors |
|---|---|---|---|---|
| POST | `/auth/sign-in` | public | `{email, password}`; sets the session cookie. Response `{status: "active", user, csrf_token}` or `{status: "totp_required"}` (pending session, no authenticated access yet). Uniform for unknown and wrong credentials; throttled | `invalid_credentials`, `rate_limited` |
| POST | `/auth/totp/verify` | public | `{code}` with the pending-session cookie; completes sign-in; a used time step is rejected | `invalid_code`, `rate_limited` |
| POST | `/auth/sign-out` | session | revokes this session | |
| GET | `/auth/session` | session | `{user, csrf_token, expires_at}`; 401 when there is no valid session | `unauthenticated` |
| POST | `/invites/accept` | public | `{token, password}`; the link activates the account (Invited to Active) and, where TOTP is required, returns `next_step: "totp_setup"` | `link_invalid`, `weak_password` |
| POST | `/password-reset/request` | public | `{email}`; always 202 (no enumeration); mail through `email.requested` | `rate_limited` |
| POST | `/password-reset/confirm` | public | `{token, password}`; revokes the account's sessions; throttled | `link_invalid`, `weak_password`, `rate_limited` |

### Own account

| Method | Path | Scope | Purpose | Errors |
|---|---|---|---|---|
| GET | `/me` | session | profile: id, email, display name, language, role, status, has_image, totp_enabled | |
| PATCH | `/me` | session | display name, language | `validation_failed` |
| GET | `/me/capabilities` | session | the one resolved capability set: role, effective scopes, TOTP state; the web app derives navigation and route guards only from it, the server stays the authority | |
| POST | `/me/password` | session | `{current_password, new_password, code?}` (re-authentication); keeps this session, revokes others | `invalid_credentials`, `weak_password` |
| PUT | `/me/profile-image` | session | image bytes (validated type by bytes, size limit in [limits](../../04-architecture/cross-cutting/limits.md)) | `invalid_image`, `body_too_large` |
| DELETE | `/me/profile-image` | session | remove the image | |
| GET | `/users/{id}/profile-image` | session | stream of a user's image (`private, no-store`); allowed only to the owner or a holder of `manage_users` (REQ-IDN-034) | `not_found`, `forbidden` |
| GET | `/me/totp` | session | status (`off`, `pending`, `on`, `required`) | |
| POST | `/me/totp/setup` | session | starts enrolment; returns provisioning URI and secret once | |
| POST | `/me/totp/confirm` | session | `{code}`; enables TOTP (two-step) | `invalid_code` |
| POST | `/me/totp/disable` | session | `{password, code}` re-authentication; refused when the account requires TOTP | `invalid_credentials`, `invalid_code`, `forbidden` |
| POST | `/me/totp/reveal` | session | `{password, code}`; shows the secret again | `invalid_credentials`, `invalid_code` |
| GET | `/me/kindle-addresses` | kindle | up to 5 validated addresses | |
| PUT | `/me/kindle-addresses` | kindle | replace the list (`KindleEmail` newtype each, at most 5) | `validation_failed`, `limit_exceeded` |
| GET | `/me/export` | session | the user's own identity data as JSON (D-30); reader and catalog data are exported by their own routes | |

### Administration (`manage_users`, session completed TOTP where required)

| Method | Path | Scope | Purpose | Errors |
|---|---|---|---|---|
| GET | `/users` | manage_users | bounded keyset list with `q` search, `status`, `role` filters | |
| POST | `/users` | manage_users | invite `{email, display_name, role, language}`; account is `invited`; emits `email.requested`; a mail failure does not undo the account | `email_taken` |
| GET | `/users/{id}` | manage_users | detail with role, status, grants summary | `not_found` |
| PATCH | `/users/{id}` | manage_users | display name, language (`If-Match`) | `stale_revision` |
| POST | `/users/{id}/resend-invite` | manage_users | new setup link; supersedes older ones | `invalid_transition` |
| PUT | `/users/{id}/status` | manage_users | `{status: active|suspended|disabled}`; transitions as in [identity state machines](../../05-services/identity/state-machines.md): Invited to Active, Active to Suspended and back, and Invited, Active or Suspended directly to Disabled (terminal); revokes sessions; emits `user.disabled` for suspend and for disable | `invalid_transition`, `forbidden` (self, last admin) |
| PUT | `/users/{id}/role` | manage_users | `{role}`; never for oneself, never demoting the last admin | `forbidden`, `invalid_transition` |
| DELETE | `/users/{id}` | manage_users | deletes the account on request (D-30); announces it so services erase user-owned data (event OPEN, O-1) | `forbidden` |
| GET | `/grants` | manage_users | list by `user_id`, `scope`, `book_id` | |
| POST | `/grants` | manage_users | `{user_id, scope, book_id?, expires_at?, reason}`; never for oneself; the database rejects an unknown scope, a book on a non-book scope and a duplicate active grant; emits `grant.changed` | `duplicate_grant`, `forbidden`, `validation_failed` |
| PATCH | `/grants/{id}` | manage_users | edit expiry or active flag; emits `grant.changed` | `stale_revision` |
| DELETE | `/grants/{id}` | manage_users | revoke; emits `grant.changed` | |
| POST | `/grants/batch` | manage_users | `{user_id, grant: [{scope, book_id?, expires_at?}], revoke: [grant_id], reason}`; atomic: all scopes are granted or revoked together or none (D-54, REQ-WEB-018); same rules as single grants (never for oneself, duplicates rejected); one `grant.changed` per user and request | `duplicate_grant`, `forbidden`, `validation_failed` |
| POST | `/users/{id}/read-once/{book_id}/reset` | manage_users | reset the read-once counter for one user and book | |
| GET | `/audit` | manage_users | append-only audit log, filter by actor, subject, action, period; who may read it is **OPEN (not in the open-points list; recommendation: `manage_users`)** | |

All administration changes are audited in the same transaction. Audit scope (D-40): sign-in, failures, lockout, sign-out, reset, password and TOTP changes, user create, invite, edit, status and role changes, grants, ticket mint and redemption; retention 1 year.

## Internal API (`/internal`, service token) - 8 routes

| Method | Path | Caller | Purpose |
|---|---|---|---|
| POST | `/internal/authorize` | gateway | `{method, path, cookie, origin, csrf_token?}`; identity also verifies the CSRF token for mutations; Allow returns `{user_id, scopes, grant_version}` (rendered as headers by the gateway); no session gives 401; denied session (inactive account, TOTP incomplete) gives 403 with a reason |
| POST | `/internal/check` | catalog, reader, ingestion, notify | `{user_id, scope, book_id?, book_state?}` returns `{decision: "allow"}` or `{decision: "deny", reason}`; total, deny by default, grant-order independent; reasons below. Callers may cache an Allow for at most 5 s keyed by `grant_version` |
| POST | `/internal/tickets` | reader | mint a reading ticket `{user_id, book_id, version_id}` after the same decision as `/internal/check` for `read` plus the `read_once` rule; returns `{ticket, ticket_id, expires_at}` (15 minutes, bound to user, book, version and grant version). Does not consume read-once |
| POST | `/internal/tickets/verify` | reader | `{ticket_id, ticket, book_id, version_id, redeem}` (D-37: every time); verifies, re-checks grant version and active state; `redeem: true` consumes read-once atomically, idempotently for the same ticket (a reconnect is not a new opening); returns `{user_id}` or a typed denial (`ticket_invalid`, `ticket_expired`, `read_once_consumed`) |
| GET | `/internal/users/{id}` | notify, catalog | `{status, language, kindle_addresses[]}`; addresses are read at send time and never copied into events |
| GET | `/internal/email-requests/{request_id}` | notify | the mail to send, by reference: `{kind, to, language, link}`; the link is never placed in an event or log |
| GET | `/internal/users/{id}/grant-version` | reader, catalog | current grant version for cache and ticket invalidation after a missed event |
| GET | `/internal/events` | reader, catalog, notify | outbox pull: `user.disabled`, `grant.changed`, `email.requested` (and `user.deleted` if O-1 is accepted) |

Deny reasons (`/internal/check`, `/internal/authorize`): `no_scope`, `grant_expired`, `account_inactive` (suspended, disabled, invited), `mfa_incomplete`, `book_not_published`, `book_deleted`, `read_once_consumed`, `self_action`, `last_admin`. A caller maps them to HTTP in the [error catalog](../error-catalog.md); `book_not_published` and `book_deleted` for a subject without `manage_catalog` surface as 404.

Also on the internal port: `GET /internal/health`, `GET /internal/ready`, `GET /internal/contract`.
