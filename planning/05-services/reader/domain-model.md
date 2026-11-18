# reader - domain model

Status: DRAFT

Database `reader` (one role), plus the reading-copy volume `/data/reading` owned by this service only.

## Tables

| Table | Columns | Keys / constraints / indexes |
|---|---|---|
| `reading_copies` | `book_id`, `version` int, `slug`, `title`, `language`, `state` (`building`\|`ready`\|`failed`\|`withdrawn`), `package_path`, `package_bytes`, `chapter_count`, `content_hash`, `error_code` null, `attempts`, `built_at`, `withdrawn_at` | PK `(book_id, version)`; index `(slug)`; partial `UNIQUE (book_id) WHERE state = 'ready'` (one current ready copy per book); `CHECK (state <> 'ready' OR package_path IS NOT NULL)` |
| `tickets` | `id` (jti), `user_id`, `book_id`, `version`, `issued_at`, `expires_at`, `redeemed_at` null, `consumed_read_once` bool, `revoked_at` null, `grants_version` bigint, `ip_hash`, `ua_hash` | PK `id`; `CHECK (expires_at = issued_at + interval '15 minutes')`; index `(user_id, book_id)`, `(expires_at)` (sweep) |
| `opens` | `id` bigserial, `at`, `user_id`, `book_id`, `version`, `outcome` (`ticket_issued`\|`redeemed`\|`denied`\|`copy_unavailable`\|`expired`), `reason`, `ip_hash`, `ua_hash` | INSERT-only; index `(user_id, at)`, `(book_id, at)`; retention 1 year |
| `progress` | `user_id`, `book_id`, `chapter_id`, `offset` int, `percent` numeric(5,2), `revision` bigint, `version`, `updated_at` | PK `(user_id, book_id)`; `CHECK (percent BETWEEN 0 AND 100)`; update `WHERE revision < $new` |
| `bookmarks` | `id`, `user_id`, `book_id`, `version`, `chapter_id`, `offset` int, `label` null, `created_at` | PK `id`; `UNIQUE (user_id, book_id, chapter_id, offset)` (duplicate create returns the existing row, never a 500); index `(user_id, book_id)` |
| `highlights` | `id`, `user_id`, `book_id`, `version`, `chapter_id`, `anchor` jsonb (`{quote:{prefix,exact,suffix}, start, end}`), `color` (`yellow`\|`green`\|`blue`\|`pink`\|`underline`), `kind` (`highlight`\|`quote`), `note` text null (<= 4000), `revision`, `created_at`, `updated_at` | PK `id`; `CHECK (length(anchor->'quote'->>'exact') BETWEEN 1 AND 5000)`; index `(user_id, book_id)`; quota <= 5,000 per (user, book) enforced in the insert |
| `event_cursors` | `source` (`catalog`\|`identity`), `cursor` bigint, `updated_at` | PK `source`; advanced in the same transaction as the handler's effect |
| `rebuild_queue` | `book_id`, `version`, `reason`, `queued_at`, `claimed_until` | PK `(book_id, version)`; claimed with `FOR UPDATE SKIP LOCKED` by the in-process worker |

Notes are highlights with a `note`; there is no separate notes table. The notes page is a query over `highlights` where `note IS NOT NULL` or `kind='quote'` (REQ-LIB-005).

## Reading package (file in the volume, one response)

Single file per `(book_id, version)`: `manifest` (title, language, direction, spine order, TOC tree, per-chapter id/title/byte size, resource table), `chapters[]` (sanitized XHTML fragments), `resources[]` (images, fonts, CSS reduced to a safe subset) with content types. Chapter ids are stable within a version and derived from the spine item id plus index. Package size limit 100 MB; a larger book fails the build with `package_too_large`.

## Tickets (token format)

Opaque signed token `base64url(jti || mac)` where `mac = HMAC-SHA256(ticket_key, jti || user || book || version || exp)`; verification also loads the `tickets` row, so revocation is a row update. Key from the secret file, rotated by `kid`. A ticket is valid iff: signature ok, `now < expires_at`, `revoked_at IS NULL`, the user is still active (checked on redeem through `/internal/check`), and the book version's copy is `ready`. Revocation by grant version: `grants_version` at issue is compared to the value learned from `grant.changed` events; a lower value means the user must re-open (cheap re-check through identity on redeem).

## Limits

Open: 30 per user per hour, 10 concurrent live tickets per user. Redeem: each ticket may be redeemed repeatedly while valid (reload) but read-once is consumed once. Progress writes <= 1 per second per book per user. Highlights, bookmarks quotas as above. Rebuild attempts <= 5 with exponential backoff.
