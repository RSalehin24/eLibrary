# notify - domain model

Status: DRAFT

Database `notify`, one role. UUIDv7 keys, UTC times from the injected `Clock`. No foreign keys to other services.

## Tables

| Table | Columns | Keys / constraints |
|---|---|---|
| `templates` | `key`, `language` (`bn`\|`en`), `version`, `subject`, `body_html`, `body_text`, `active` | PK `(key, language, version)`; `UNIQUE (key, language) WHERE active`; a key is active only when both languages exist |
| `mail_outbox` | `id`, `source` (`identity`), `event_id`, `kind` (`invite`\|`password_reset`), `request_id`, `user_id`, `address_mask`, `language`, `state` (`queued`\|`sending`\|`sent`\|`retry`\|`failed`), `attempts`, `next_attempt_at`, `lease_until`, `error_class` null, `created_at`, `updated_at` | PK `id`; `UNIQUE (source, event_id, kind)` (claim before send); partial index `(next_attempt_at) WHERE state IN ('queued','retry')` |
| `kindle_deliveries` | `id`, `event_id`, `request_id`, `user_id`, `book_id`, `version_id`, `address_index`, `address_mask` null, `state` (`queued`\|`preflight`\|`sending`\|`sent`\|`rejected`\|`retry`\|`failed`), `reason` null (`unsupported_format`\|`too_large`\|`no_address`\|`sender_not_approved`\|`smtp_failed`), `size_bytes` null, `attempts`, `next_attempt_at`, `lease_until`, `reported_at` null | PK `id`; `UNIQUE (request_id)`; index `(user_id, created_at)`; `CHECK (size_bytes IS NULL OR size_bytes >= 0)` |
| `delivery_log` | `id`, `kind` (`invite`\|`password_reset`\|`kindle`), `ref_id`, `event_id`, `status`, `error_class` null, `reason` null, `address_mask`, `at` | one row per attempt (REQ-NTF-009); INSERT-only for the service role; no link, token or full address |
| `event_cursors` | `source` (`identity`\|`catalog`), `cursor` bigint, `updated_at` | PK `source`; advanced in the same transaction as the outbox insert |
| `quota_counters` | `key` (`user:<id>`, `book:<id>:<user>`), `window_start`, `count` | PK `(key, window_start)`; pruned by the retention job |

The real address and link are fetched from identity at send time and held only in memory and the rendered message; the log keeps a masked form (for example first character and domain) (REQ-NTF-004).

## Value types

`MailKind` and `KindleReason` (closed enums, exhaustive `match`), `FailureClass` (`Retryable` | `Permanent`), `MaskedAddress`, `Secret<T>` for links and credentials (no `Display`/`Debug`), `Attempts` (bounded), `ByteSize`, `EventId`, `RequestId` newtypes. Template variables are typed structs per template (a missing or unknown variable fails the template-set build); every interpolated value is escaped.

## Templates

`invite`, `password_reset`, `kindle_cover_note`; each in `bn` and `en`; selected by the account language (REQ-NTF-003). Password-changed and admin notices are not in the requirements and are out of scope until a requirement exists.

## Limits (provisional until the P0 baseline)

Kindle total mail size 50 MB (also the mail limit; re-verify before launch); Kindle requests 10 per user per hour ([limits](../../04-architecture/cross-cutting/limits.md)) and a per-book per-user cap; concurrent sends a configured small number, one attachment held per send; retry backoff exponential with jitter up to a configured maximum attempt count; lease 5 minutes; SMTP timeout configured; outbox backlog bound with an alert.

## Invariants

| ID | Rule | Realised by |
|---|---|---|
| INV-NTF-001 | no event id gives two accepted sends except after a recorded unknown outcome | unique key, claim before send |
| INV-NTF-002 | a producer's transaction does not depend on notify | pull-only; no synchronous call from producers |
| INV-NTF-003 | every template renders in both locales and escapes parameters | typed variables, set-activation check |
| INV-NTF-004 | no link, token or full address in logs or errors | `Secret`, `MaskedAddress` |
| INV-NTF-005 | Kindle send only after an identity Allow at send time | check in the send step, typed `Allowed` token |
| INV-NTF-006 | every sent Kindle mail passed preflight | `Preflighted` type is the only input of `send` |
| INV-NTF-007 | quota per window; memory per send bounded | `quota_counters`, streaming with size cap |
| INV-NTF-008 | failure class decides retry, not text | `FailureClass` on every error |
| INV-NTF-009 | one delivery-log row per attempt | insert in the attempt transaction |
| INV-NTF-010 | no request path of another service depends on SMTP | isolation, timeouts, bounded backlog |
| INV-NTF-011 | secrets from files; no public route | startup validation, route table |
| INV-NTF-012 | no row older than retention | bounded retention job |
