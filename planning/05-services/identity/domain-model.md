# identity - domain model

Status: DRAFT

Database `identity`, one role. UUIDv7 keys. All times `timestamptz` UTC from the injected `Clock`. Enums are database enums or `CHECK` constraints (REQ-PLT-023). No foreign keys to other services; book and user ids elsewhere are opaque.

## Tables

| Table | Columns | Keys / constraints |
|---|---|---|
| `users` | `id`, `email`, `display_name`, `language` (`bn`\|`en`), `status` (`invited`\|`active`\|`suspended`\|`disabled`), `role` (`reader`\|`operator`\|`admin`), `totp_required` bool, `grant_version` bigint, `revision`, `created_at`, `updated_at` | PK `id`; `UNIQUE (lower(email))`; one role per user (single column, closed enum) |
| `kindle_addresses` | `user_id`, `position` (0..4), `address` | PK `(user_id, position)`; `CHECK position < 5`; `KindleEmail` validated in code |
| `credentials` | `user_id`, `password_hash` (Argon2id), `changed_at` | PK `user_id`; absent while `invited` |
| `totp` | `user_id`, `secret_enc`, `state` (`pending`\|`enabled`), `confirmed_at`, `last_accepted_step` bigint, `failed_count` | PK `user_id`; secret encrypted with a key from a secret file |
| `sessions` | `id`, `token_hash`, `user_id`, `state` (`pending_totp`\|`authenticated`), `csrf_hash`, `created_at`, `last_seen_at`, `expires_at`, `revoked_at`, `ua_hash`, `ip_prefix` | PK `id`; `UNIQUE (token_hash)`; partial index `(user_id) WHERE revoked_at IS NULL` |
| `links` | `id`, `user_id`, `purpose` (`invite`\|`reset`), `token_hash`, `nonce`, `state` (`issued`\|`consumed`\|`superseded`\|`expired`), `expires_at`, `request_id`, `created_at` | PK `id`; `UNIQUE (token_hash)`; partial `UNIQUE (user_id, purpose) WHERE state = 'issued'`; only hashes stored |
| `grants` | `id`, `user_id`, `scope`, `book_id` null, `expires_at` null, `active` bool, `granted_by`, `reason`, `revision`, `created_at` | PK `id`; `CHECK` scope in the closed set; `CHECK (granted_by <> user_id)`; `CHECK (book_id IS NULL OR scope IN ('preview','read','read_once','download','kindle'))`; partial `UNIQUE (user_id, scope, COALESCE(book_id, nil)) WHERE active` |
| `read_once_uses` | `user_id`, `book_id`, `ticket_id`, `consumed_at` | PK `(user_id, book_id)`; the insert is the consumption; admin reset deletes the row (audited) |
| `tickets` | `id` (ticket id, non-secret), `secret_hash`, `user_id`, `book_id`, `version_id`, `grant_version`, `issued_at`, `expires_at`, `redeemed_at` null | PK `id`; `UNIQUE (secret_hash)`; `CHECK (expires_at <= issued_at + interval '15 minutes')`; pruned by retention |
| `profile_images` | `user_id`, `content_type`, `bytes` (or file ref), `size`, `sha256`, `updated_at` | PK `user_id`; type in allow-list (no SVG); size under the limit |
| `login_attempts` | `key`, `window_start`, `count` | PK `(key, window_start)`; pruned |
| `audit_log` | `id` bigserial, `at`, `actor`, `subject`, `action`, `detail jsonb`, `request_id`, `address`, `ua_hash` | INSERT-only for the service role; indexes `(at)`, `(subject, at)`; retention 1 year |
| `events` | `cursor` bigserial, `id` uuid, `type`, `v`, `subject_id`, `request_id`, `payload jsonb`, `at` | written in the change transaction; payload holds no secret, address or link |
| `email_requests` | `request_id`, `kind` (`invite`\|`password_reset`), `user_id`, `language`, `link_ref`, `created_at` | link is read by notify by reference once; never in events or logs |
| `config_defaults` | `key`, `value` | default grants of a new reader (`browse`, `preview`, `read`, `kindle`) are configuration (D-30) |

## Value types

`Email` (at most 254), `Password` (minimum length and deny list, REQ-IDN-003), `TotpCode` (6 digits), `KindleEmail`, `Scope` and `Role` (closed enums, exhaustive `match`), `GrantVersion`, `TicketId`, `Secret<T>` (no `Display`, `Debug`, `Serialize`; constant-time compare). Ids are newtypes (`UserId`, `BookId`, `VersionId`, `SessionId`, `GrantId`).

## Roles and scopes (closed, in code, mirrored by a test)

| Role | Role scopes |
|---|---|
| `reader` | the configured default grants: `browse`, `preview`, `read`, `kindle` |
| `operator` | confirmed (D-45): reader scopes plus `operate`, `manage_catalog` |
| `admin` | confirmed (D-45): reader scopes plus `manage_users`, `manage_catalog` (no `operate`) |

`download` and `read_once` are never in a role; they exist only as grants. A user holding `read_once` for a book and `read` by role is read-once for that book (the stricter rule wins; stated so the result is deterministic). The assignment of `operate` and `manage_catalog` to `operator` and `admin` is confirmed by the owner (D-45).

## Decision function

`decide(subject, scope, book_facts, grants, now) -> Allow | Deny(reason)` is pure and total: no I/O, no clock reads, no panics; `book_facts` is `Option<BookFacts {id, state, deleted}>` supplied by the caller.

Rules in order: (1) inactive subject (`invited`, `suspended`, `disabled`) denies everything (`account_inactive`); (2) management scopes (`manage_users`, `manage_catalog`, `operate`) require `mfa_ok` when the account requires TOTP (`mfa_incomplete`); (3) a book scope needs facts; for a subject without `manage_catalog`, state must be `published` and not deleted (`book_not_published`, `book_deleted`); (4) allow iff a role scope or a live grant (active, `now < expires_at`) provides the scope for this book or globally; an expired grant that was the only source gives `grant_expired`, otherwise `no_scope`; (5) `read_once` for the book with a recorded use gives `read_once_consumed` (only for a different ticket id); (6) `self_action` and `last_admin` are produced by administration commands, not `decide`.

`DenyReason` (closed): `NoScope`, `GrantExpired`, `AccountInactive`, `MfaIncomplete`, `BookNotPublished`, `BookDeleted`, `ReadOnceConsumed`, `SelfAction`, `LastAdmin`.

## Invariants

| ID | Rule | Realised by |
|---|---|---|
| INV-IDN-001 | no Active account without a valid link or first-admin seed | typestate `User<S>`, status transitions |
| INV-IDN-002 | link consumed once, never after expiry or supersession | row lock + partial unique index |
| INV-IDN-003 | `Secret<T>` cannot be formatted or compared non-constant-time | type, compile-fail test |
| INV-IDN-004 | authenticated session only after the second factor when required | `Session<Authenticated>` constructor |
| INV-IDN-005 | last accepted TOTP step only increases | row lock, `CHECK` via update guard |
| INV-IDN-006 | disable TOTP and password change need a fresh credential check | command type carries `Reauth` |
| INV-IDN-007 | revoked or expired session never allows | `revoked_at`, expiry in the lookup |
| INV-IDN-008 | sign-in and reset responses independent of account existence | dummy hash, same path |
| INV-IDN-009 | status changes follow the transition relation | enum transition function + trigger |
| INV-IDN-010 | scopes are the union of role and active grants; no wildcard | closed enums |
| INV-IDN-011 | `preview`/`read` distinct; valid grant rows; unique active | `CHECK`s and partial unique index |
| INV-IDN-012 | actor differs from subject; audit in the same transaction | `CHECK`, transaction helper |
| INV-IDN-013 | no match means Deny | `decide` ends in Deny |
| INV-IDN-014 | anonymous has only the public set | route declaration |
| INV-IDN-015 | no decision input from shelf, ownership or submissions | `decide` signature |
| INV-IDN-016 | non-`manage_catalog` Allow implies published and not deleted | rule (3) |
| INV-IDN-017 | expired or revoked grant contributes nothing | rule (4) with injected clock |
| INV-IDN-018 | adding a grant never removes a permission (except read-once) | property test |
| INV-IDN-019 | `decide` is a pure function of its inputs | no I/O in signature |
| INV-IDN-020 | read-once consumed on redemption only, once per user and book | `read_once_uses` PK |
| INV-IDN-021 | tickets: opaque, hashed, at most 15 min, bound, never in a URL | `tickets` constraints, route design |
| INV-IDN-022 | redemption idempotent; foreign, expired, pre-revocation tickets rejected | verify function, grant version compare |
| INV-IDN-023 | events written in the change transaction | outbox writer |
| INV-IDN-024 | every route declares a scope; missing means refuse to start | route table builder |
| INV-IDN-025 | management actions need a TOTP-complete session when required | rule (2) |
| INV-IDN-028 | at most 5 validated Kindle addresses, owner only with `kindle` | `CHECK`, route scope |
| INV-IDN-029 | append-only audit, 1 year | no UPDATE/DELETE grant, retention job |
| INV-IDN-030 | one resolved capability set; 401 vs 403 distinct | `/me/capabilities`, error mapping |
| INV-IDN-031 | bounded admin listing; deletion announced | keyset pagination, event OPEN (O-1) |
| INV-IDN-032 | no seed, test or advance route in production | build features, CLI guard |
| INV-IDN-033 | recovery only by the host command | no HTTP route, static check |
| INV-IDN-034 | profile image allow-listed, validated, never public | `images` module, route scope `session` |

INV-IDN-026 and 027 are retired (D-35); numbers are not reused.

## Policies (configuration, validated at startup)

Session idle 12 h and absolute 30 d (limits table), rotated on password change and TOTP confirmation, all other sessions revoked on password change, suspend, disable, delete. Invite link 7 days, reset link 24 h ([limits](../../04-architecture/cross-cutting/limits.md)). Login attempts 5 per 15 min per account and 20 per 15 min per address. Ticket lifetime 900 s. Profile image 2 MiB (provisional, C-6). Audit retention 1 year.
