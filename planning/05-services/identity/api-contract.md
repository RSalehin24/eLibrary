# identity — API contract

Status: DRAFT · Source of truth: `contracts-identity` (generated schema in [07-contracts](../../07-contracts/http/README.md))

| Method & path (public via gateway) | Auth | Purpose | Notable errors |
|---|---|---|---|
| `POST /auth/login` | anonymous | email+password → `Authenticated` or `NeedsTotp` | `invalid_credentials` (uniform), `rate_limited` |
| `POST /auth/totp/verify` | password-ok session | complete second factor | `invalid_code` |
| `POST /auth/logout` | session | revoke current | — |
| `GET /auth/session` | session? | current subject, expiry, abilities digest | — |
| `POST /auth/demo` | anonymous | sign in demo account | `demo_disabled` |
| `POST /auth/password/forgot` | anonymous | request reset (always 202) | `rate_limited` |
| `GET /auth/links/{token}` | anonymous | validate link (purpose, account hint) | `link_invalid` (uniform) |
| `POST /auth/links/{token}/consume` | anonymous | set password | `link_invalid`, `weak_password` |
| `GET/PATCH /me/profile` | session (non-demo) | name, language, Kindle addresses | `stale_revision` |
| `POST /me/password` | session | change password (needs current) | `invalid_credentials`, `weak_password` |
| `POST /me/totp/setup`, `/confirm`, `/disable` | session | TOTP enrolment | `invalid_code` |
| `GET/POST /admin/accounts`, `GET/PATCH /admin/accounts/{id}` | management | list/invite/update | `email_taken`, `stale_revision` |
| `POST /admin/accounts/{id}/resend-link` | management | issue new link (supersedes) | — |
| `POST /admin/accounts/{id}/suspend` `/reactivate` `/disable` | management | status changes | `invalid_transition` |

## Internal (not public)

| Route | Caller | Purpose |
|---|---|---|
| `POST /internal/sessions/resolve` | gateway | cookie token → subject facts |
| `GET /internal/accounts/{id}/facts` | access | `{active, totp_required, mfa_ok?, demo}` |
| `GET /internal/links/{ref}` | notify | one-shot link text for mail (consumed on read, expires 10 min) |
| `GET /internal/contract` | all | version handshake |

## Conventions

All mutations accept `Idempotency-Key`. Errors use the [error model](../../04-architecture/cross-cutting/errors.md). Admin routes require `Allow<ManageAccess>` witness from access.
