# notify - domain model

Status: DRAFT

Database `notify` (one role).

| Table | Columns | Keys / constraints / indexes |
|---|---|---|
| `templates` | `key`, `language`, `subject`, `body_html`, `body_text`, `version`, `active` | PK `(key, language, version)`; `UNIQUE (key, language) WHERE active`; every key exists in `bn` and `en` before activation (INV-NTF-003) |
| `mail_outbox` | `id`, `source` (`identity`\|`catalog`), `event_id`, `kind` (`invite`\|`reset`\|`password_changed`\|`admin_notice`), `user_id`, `to_hash`, `language`, `state` (`queued`\|`sending`\|`sent`\|`retry`\|`failed`), `attempts`, `next_attempt_at`, `lease_until`, `provider_message_id` null, `error_code` null, `created_at`, `sent_at` | PK `id`; `UNIQUE (source, event_id, kind)` (claim-before-send); partial index `(next_attempt_at) WHERE state IN ('queued','retry')` |
| `kindle_deliveries` | `id`, `request_id`, `user_id`, `book_id`, `version`, `address_hash`, `state` (`queued`\|`preflight`\|`sending`\|`sent`\|`rejected`\|`retry`\|`failed`), `size_bytes` null, `reject_reason` null, `error_code` null, `attempts`, `next_attempt_at`, `lease_until`, `created_at`, `sent_at` | PK `id`; `UNIQUE (request_id)`; index `(user_id, created_at)`; `CHECK (size_bytes IS NULL OR size_bytes >= 0)` |
| `event_cursors` | `source`, `cursor` bigint, `updated_at` | PK `source`; advanced in the same transaction as the outbox insert |
| `audit_log` | `id`, `at`, `action`, `subject`, `detail jsonb` | INSERT-only; no addresses or links |

`to_hash`/`address_hash` are salted hashes; the real address is read from identity at send time and never stored.

## Templates

`invite`, `reset`, `password_changed`, `kindle_cover_note`, `admin_notice`. Variables are typed structs per template (compile-checked); a missing or unknown variable fails the template-set build. Link variables are `Secret` types.

## Limits

Mail 5 per address per hour; global rate per provider limit; Kindle size <= 50 MB; Kindle 20 per user per day; retries exponential over 24 h (1 min, 5 min, 30 min, 2 h, 6 h, 12 h, 24 h cutoff); lease 5 minutes.
