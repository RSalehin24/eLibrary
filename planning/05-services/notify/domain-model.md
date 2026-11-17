# notify — domain model

Status: DRAFT

| Entity | Fields | Constraints |
|---|---|---|
| `Template` | `key`, `language`, `subject`, `body_html`, `body_text`, `version` | `(key, language)` unique; every key exists in `bn` and `en` (INV-NTF-003) |
| `MailDelivery` | `id`, `event_id`, `kind`, `to_hash`, `language`, `state`, `attempts`, `next_attempt_at`, `provider_message_id?`, `error_code?` | `UNIQUE(event_id, kind)` — claim-before-send (INV-NTF-001) |
| `KindleSend` | `id`, `request_id` (unique), `owner_id`, `book_id`, `address_ref`, `state`, `size_bytes?`, `error_code?`, `attempts` | one row per request; history exposed via events |
| `AddressProjection` | `account_id`, `email`, `kindle_emails[]` | from identity events; used for preflight |
| `AuditEntry` | INSERT-only | |

`to_hash` stores a salted hash of the address, not the address; the address is read from the projection at send time.

## Templates

`account_invite`, `password_reset`, `password_changed`, `kindle_delivery` (cover note), `admin_job_failed`. Variables are typed per template (compile-checked structs); unknown or missing variables fail the build of the template set.

## Limits

Per-address mail rate (5/h), global send rate per provider limits, Kindle size 50 MB, retries 24 h exponential.
