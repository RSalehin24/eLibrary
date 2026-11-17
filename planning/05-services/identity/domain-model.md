# identity — domain model

Status: DRAFT

## Aggregates

| Aggregate | Fields | Constraints |
|---|---|---|
| `Account` | `id` UUIDv7, `email` (unique, case-folded), `display_name`, `status` enum, `language`, `totp_required`, `is_demo`, `kindle_emails[≤5]`, `revision` | `UNIQUE(lower(email))`; status graph per [state machines](state-machines.md) |
| `Credential` | `account_id`, `password_hash`, `hash_alg` (`argon2id`\|`legacy_pbkdf2`), `changed_at` | 1:1 with Active accounts; absent while Invited |
| `TotpEnrolment` | `account_id`, `secret_enc`, `state` (Pending\|Enabled), `confirmed_at`, `last_accepted_step` (u64) | secret encrypted with key from secret store |
| `PasswordLink` | `id`, `account_id`, `purpose` (Setup\|Reset), `token_hash`, `expires_at`, `state` (Issued\|Consumed\|Superseded\|Expired), `nonce` | partial unique index: one `Issued` per (account, purpose) |
| `Session` | `id`, `token_hash`, `account_id`, `created_at`, `last_seen_at`, `expires_at`, `mfa_ok`, `revoked_at`, `ua_hash`, `ip_prefix` | revoked or expired sessions authenticate nothing |
| `LoginAttempt` | `key` (account or IP), `window_start`, `count` | for throttling |
| `AuditEntry` | actor, action, target, request id, at | INSERT-only |

## Value types

`Email` (validated, ≤ 254), `Password` (policy: ≥ 12 chars, not in top-100k list), `TotpCode` (6 digits), `LinkToken` (256-bit, `Secret`), `SessionToken` (256-bit, `Secret`), `KindleEmail`.

## Policies

- Password policy: length ≥ 12, no maximum under 256, breached-list check offline; no composition rules.
- Session: idle 12 h, absolute 30 d, rotated on password change and on TOTP confirmation; all revoked on password change, suspend, disable.
- Throttling: see [limits](../../04-architecture/cross-cutting/limits.md). Responses for unknown accounts perform equivalent work (hash of dummy password) to flatten timing.
