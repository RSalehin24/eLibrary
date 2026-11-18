# identity

Status: DRAFT

Who is this person, have they proven it, and what may they do? The only place that decides who may do what (D-27; absorbs the former `access` service).

| | |
|---|---|
| Owns | users, credentials (Argon2id), opaque sessions (cookie), TOTP, invites, password reset, roles, grants, demo-account limits, auth/grant audit log, `events` outbox |
| Does not own | books, files, reading state, mail delivery |
| Requirements | REQ-IDN-001...010, REQ-ACC-001...012 (reword pending, see Open questions), REQ-MIG-003 |
| Emits (outbox) | `user.disabled`, `grant.changed`, `email.requested` (invite, reset, password-changed) |
| Consumes | none (it is a producer only) |
| Calls | none |
| Called by | Caddy (`/internal/authorize`, forward-auth on every `/api/*` request), catalog / reader / ingestion (`/internal/check`), notify (pulls `/internal/events`), web (public and `/me`, `/admin` routes) |

## Permission model (brief section 4, binding)

- Deny by default. Roles: `reader`, `operator`, `admin`, `demo`. Scopes: `browse`, `preview`, `read`, `read_once`, `download`, `kindle`, `operate`, `manage_catalog`, `manage_users`.
- **No wildcard roles.** There is no `is_staff`, no `is_superuser`, no `admin:full_control`. A role is a fixed, enumerated scope set (table in [domain model](domain-model.md)); `admin` does not imply `operate` unless the table lists it.
- Grants are explicit rows `(user, scope, optional book, optional expiry, granted_by)`. Role scopes are global; grants add per-book exceptions (for example `read_once` on one book). Union only, no deny rows, so adding a grant never removes a permission (REQ-ACC-005).
- **Ownership is a shelf only.** "My Books" lives in catalog and never grants access; identity has no ownership concept (fixes legacy L1).
- Every `/api/*` route declares its required scope in code; a route with no declaration is rejected at startup (fail closed). Each service registers its route-to-scope table with identity at boot; identity serves it through `/internal/authorize`.
- Publication state is enforced by the owning service (catalog/reader), because identity does not know books: `/internal/check` receives the book facts from the caller and applies the scope and grant rules; only `published` versions are readable.

## Authentication

- Argon2id passwords (policy in [domain model](domain-model.md)); optional TOTP (two-step enrolment, single-use time step); opaque 256-bit session token in an HttpOnly, Secure, SameSite=Lax cookie, only its hash stored.
- Accounts are created only by an admin **invite** (or the one-time CLI seed). No public sign-up. Invite acceptance and password reset share one token mechanism with a `purpose`.
- **Reset without account enumeration (DRAFT proposal, not decided):** `POST /api/identity/password/reset-request` always returns `202` with the same body and does equivalent work for known and unknown addresses (dummy hash, same outbox write path, mail only when the account exists and is Active); rate limited per address and per IP. `confirm` returns one uniform `link_invalid` for unknown, used, expired or superseded tokens. Open question lists the choices.
- **Demo is a restricted real account** (`demo` role, `is_demo=true`): signed in by a rate-limited `POST /api/identity/demo/sign-in` (never GET), no stored default password, no TOTP, read-only curated set, no download or Kindle, no mutations of profile, password or shelf, disabled by config flag.

## Internal endpoints

| Route | Caller | Purpose |
|---|---|---|
| `GET /internal/authorize` | Caddy forward-auth | cookie to verified `X-User-Id`, `X-User-Scopes`, `X-User-Demo` headers, or `401`/`403` |
| `POST /internal/check` | catalog, reader, ingestion | decide one `(user, scope, book?)` with caller-supplied book facts |
| `GET /internal/events?after=` | notify, reader, catalog | outbox cursor API |

Service-to-service calls carry an internal service token (audience-bound, short-lived); identity verifies it on `/internal/*`.

See [domain model](domain-model.md) | [API](api-contract.md) | [state machines](state-machines.md) | [tests](test-plan.md).
