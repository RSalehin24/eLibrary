# identity - API contract

Status: DRAFT

Authoritative contract: [07-contracts/http/identity.md](../../07-contracts/http/identity.md) (37 public routes, 8 internal routes, deny reasons). Events: [events catalog](../../07-contracts/events/README.md). This page only maps the contract to the design and does not duplicate the endpoints.

| Contract area | Design owner (this folder) | Notes |
|---|---|---|
| Session and sign-in (7 routes) | [state machines](state-machines.md) sign-in, session, link | public routes are the closed set in [gateway](../gateway/domain-model.md); responses uniform for unknown accounts (REQ-IDN-008) |
| Own account, TOTP, Kindle addresses, profile image, export | TOTP, image sections | re-authentication on password change, TOTP disable and reveal (REQ-IDN-006); image served only to owner and admins (REQ-IDN-034) |
| Administration (users, role, status, grants including `POST /grants/batch`, read-once reset, audit) | user status, grant | `manage_users` with a TOTP-complete session; never for oneself; audit in the same transaction |
| `/internal/authorize` | `decide` plus session lookup | returns user id, scopes, grant version for the gateway to render as headers; verifies CSRF for mutations |
| `/internal/check` | `decide` | callers may cache Allow at most 5 s keyed by `grant_version` |
| `/internal/tickets`, `/internal/tickets/verify` | [ticket machine](state-machines.md) | verify on every redemption (D-37); `redeem: true` consumes read-once atomically |
| `/internal/users/{id}`, `/internal/email-requests/{id}`, `/internal/users/{id}/grant-version`, `/internal/events` | outbox and by-reference mail | addresses and links never enter events |
| Host commands | `admin-reset`, `seed-first-admin` | not HTTP (D-38, REQ-IDN-032/033) |

Route-scope declarations: every public route is declared `public`, `session` or a scope name in code; startup fails otherwise (REQ-IDN-024).

Open: **O-1** (`user.deleted`), **C-1** (audit read scope).
