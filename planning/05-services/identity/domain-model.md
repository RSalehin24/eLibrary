# identity - domain model

Status: DRAFT

One database `identity`, one role. UUIDv7 keys. All timestamps `timestamptz` from the injected clock.

## Tables

| Table | Columns | Keys / constraints / indexes |
|---|---|---|
| `users` | `id`, `email`, `display_name`, `language` (`bn`\|`en`), `status` (`invited`\|`active`\|`suspended`\|`disabled`), `is_demo` bool, `totp_required` bool, `kindle_emails text[]`, `revision` int, `created_at`, `updated_at` | PK `id`; `UNIQUE (lower(email))`; `CHECK (cardinality(kindle_emails) <= 5)`; `CHECK (status <> 'active' OR NOT is_demo OR totp_required = false)`; index `(status)` |
| `user_roles` | `user_id`, `role` (`reader`\|`operator`\|`admin`\|`demo`), `granted_by`, `at` | PK `(user_id, role)`; FK `user_id`; `CHECK` role in the closed set; demo role excludes all others (trigger) |
| `credentials` | `user_id`, `password_hash`, `hash_alg` (`argon2id`\|`legacy_pbkdf2`), `changed_at` | PK `user_id`; absent while `invited` and for the demo account |
| `totp` | `user_id`, `secret_enc`, `state` (`pending`\|`enabled`), `confirmed_at`, `last_accepted_step` bigint | PK `user_id`; secret encrypted with a key from the secret file |
| `sessions` | `id`, `token_hash`, `user_id`, `created_at`, `last_seen_at`, `expires_at`, `mfa_ok`, `revoked_at`, `ua_hash`, `ip_prefix` | PK `id`; `UNIQUE (token_hash)`; index `(user_id) WHERE revoked_at IS NULL` |
| `tokens` | `id`, `user_id`, `purpose` (`invite`\|`reset`), `token_hash`, `expires_at`, `state` (`issued`\|`consumed`\|`superseded`\|`expired`), `created_at` | PK `id`; `UNIQUE (token_hash)`; partial `UNIQUE (user_id, purpose) WHERE state = 'issued'`; only the hash is stored |
| `grants` | `id`, `user_id`, `scope`, `book_id` null, `expires_at` null, `revoked_at` null, `granted_by`, `reason`, `revision` | PK `id`; `CHECK` scope in the closed set; `CHECK (granted_by <> user_id)`; `CHECK` scope not in (`manage_users`, `operate`, `manage_catalog`) when `book_id` set (book targets only for `read`, `read_once`, `download`, `kindle`, `preview`); partial `UNIQUE (user_id, scope, book_id) WHERE revoked_at IS NULL` (nulls distinct handled with `COALESCE`); index `(user_id)` |
| `read_once_uses` | `user_id`, `book_id`, `ticket_id`, `consumed_at` | PK `(user_id, book_id)`; written by `/internal/check` consume call from reader (see [state machines](state-machines.md)) |
| `demo_set` | `book_id`, `added_by`, `added_at` | PK `book_id`; the curated read-only set visible to demo |
| `login_attempts` | `key` (`u:<hash>` or `ip:<prefix>`), `window_start`, `count` | PK `(key, window_start)`; pruned daily |
| `audit_log` | `id` bigserial, `at`, `actor`, `action`, `subject`, `detail jsonb`, `request_id`, `ip_hash`, `ua_hash` | INSERT-only (no UPDATE/DELETE grant to the service role); index `(at)`, `(subject, at)`; retention 1 year (owner decision pending, Q-X3-10) |
| `events` | `id` bigserial (the cursor), `type`, `payload jsonb`, `at` | PK `id`; written in the same transaction as the change; payload never holds secrets |

## Roles and scopes (closed tables, in code and mirrored by a test)

| Role | Scopes |
|---|---|
| `reader` | `browse`, `preview`, `read`, `download`, `kindle` |
| `operator` | those of `reader` plus `operate`, `manage_catalog` |
| `admin` | those of `reader` plus `manage_users`, `manage_catalog` (not `operate`) |
| `demo` | `browse`, `preview`, `read` on `demo_set` only |

`read_once` is never in a role; it exists only as a grant (per book) and, when held for a book, replaces `read` for that book. Having both `read` through a role and `read_once` for a book means the book is read-once (the more restrictive rule wins for that book, stated so the outcome is deterministic).

## Decision function (pure, `domain-identity::decide`)

`decide(subject, scope, book_facts, grants, now) -> Allow | Deny(reason)`, three structured parameters; no I/O, no clock reads. Inputs: subject (status, roles, mfa_ok, demo), required scope, optional `BookFacts {id, published, in_demo_set}`.

`DenyReason` (closed): `Anonymous`, `Inactive`, `MfaRequired`, `NoScope`, `GrantExpired`, `ReadOnceConsumed`, `Unpublished`, `DemoRestricted`, `ForbiddenDemo`.

Rules, in order: anonymous only for public routes (never reaches decide); inactive denies; `manage_users`, `operate`, `manage_catalog` require `mfa_ok` when the user has TOTP enabled; demo allows only `browse`, `preview`, `read` and only for books in `demo_set`; scopes on a book require `published`; allow iff a role scope or a live grant (not revoked, not expired) provides the scope. The union is order independent (REQ-ACC-010).

## Value types

`Email` (<= 254), `Password` (>= 12 chars, < 256, offline breached-list check, no composition rules), `TotpCode` (6 digits), `Token` (256-bit `Secret`), `Scope` and `Role` (closed enums), `KindleEmail`. `Secret<T>` has no `Display`/`Debug` (INV-IDN-003).

## Policies

Session idle 12 h, absolute 30 d, rotated on password change and TOTP confirmation, all revoked on password change, suspend, disable. Demo sessions: absolute 2 h. Throttling per account and per IP (limits doc in 04-architecture). Unknown-account paths do equivalent work.
