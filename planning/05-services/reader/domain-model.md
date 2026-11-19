# reader - domain model

Status: DRAFT (rewritten: tickets live in identity, no signing key here; D-37, D-40)

Database `reader` (one role), volume `/data/reading` owned by this service only. Row-level security on every personal table: `user_id = current_setting('app.user_id')`, set per request from the verified identity header. No cross-service foreign keys.

## Entities and value types

| Type | Meaning | Invariant |
|---|---|---|
| `ReadingCopy` | derived, sanitized whole book for `(book_id, version_id)` | INV-RDR-001..004 |
| `SafeHtml` | HTML produced only by the allow-list sanitizer; the only type the package writer accepts; sanitizer is idempotent | INV-RDR-003 |
| `Verified<ReadingTicket>` | constructed only by calling identity `verify`; book handlers accept nothing else | INV-RDR-006 |
| `Anchor` | `{section_id, offset, quote?{exact, prefix, suffix}}` plus `anchored_version` | INV-RDR-015 |
| `AnchorState` | `placed` or `orphaned` | INV-RDR-015 |
| `Progress`, `Bookmark`, `Highlight` (with optional note) | per-user reading state | INV-RDR-012..014, 016 |
| `OpenEvent` | audit row of an open or a redemption | INV-RDR-011 |

## Tables

| Table | Columns | Keys, constraints, indexes |
|---|---|---|
| `reading_copies` | `book_id`, `version_id`, `slug`, `title`, `language`, `state` (`building` \| `ready` \| `failed` \| `withdrawn`), `parser_version`, `package_path`, `package_bytes`, `section_count`, `content_hash`, `error_code?`, `attempts`, `built_at?`, `withdrawn_at?`, `created_at`, `updated_at` | PK `(book_id, version_id)`; index `(slug)`; partial `UNIQUE(book_id) WHERE state='ready'` (one served copy per book); `CHECK (state <> 'ready' OR package_path IS NOT NULL)`; `attempts` capped. INV-RDR-001, 004 |
| `opens` | `id` bigserial, `at`, `user_id`, `book_id`, `version_id`, `ticket_id?` (non-secret handle), `outcome` (`ticket_issued` \| `redeemed` \| `denied` \| `copy_unavailable` \| `expired`), `reason?`, `request_id` | INSERT-only (REVOKE UPDATE, DELETE); never contains the ticket secret; index `(user_id, at)`, `(book_id, at)`; retention 1 year (D-40). INV-RDR-011 |
| `progress` | `user_id`, `book_id`, `version_id`, `section_id`, `offset` int, `percent` numeric(5,2), `locator` text, `revision` bigint, `updated_at` | PK `(user_id, book_id)`; `CHECK (percent BETWEEN 0 AND 100)`; `CHECK (length(locator) <= L)` where L exceeds the longest allowed anchor encoding; update `WHERE revision < $new` (stale write is a no-op returning the stored value). INV-RDR-012 |
| `bookmarks` | `id`, `user_id`, `book_id`, `anchor` (jsonb), `anchored_version`, `anchor_state`, `label?`, `created_at` | `UNIQUE(user_id, book_id, section_id, offset)` (generated columns from the anchor; a duplicate create returns the existing row with `created: false`); quota per (user, book) bounded (value to be added to [limits](../../04-architecture/cross-cutting/limits.md), contract names `limit_exceeded`). INV-RDR-013 |
| `highlights` | `id`, `user_id`, `book_id`, `anchor` (jsonb), `anchored_version`, `anchor_state`, `color` (five values defined once), `kind` (`highlight` \| `quote`), `note?` (<= 10,000 chars), `revision`, `created_at`, `updated_at` | `CHECK (length(anchor->'quote'->>'exact') BETWEEN 1 AND 5000)` when a quote exists; quota 5,000 per (user, book) enforced in the insert; `If-Match` on edit. Notes are the `note` field (C-4, OPEN). INV-RDR-014 |
| `anchor_log` | `id`, `annotation_kind`, `annotation_id`, `from_version`, `to_version`, `from_state`, `to_state`, `method` (`exact`, `fuzzy`, `section_only`, `none`), `at` | append-only; measures re-anchoring ([anchors](anchors.md)); written by server re-anchoring (D-46) |
| `event_cursors` | `source` (`catalog` \| `identity`), `cursor` bigint, `updated_at` | PK `source`; advanced in the same transaction as the handler's effect. INV-RDR-024 |
| `copy_jobs` | `book_id`, `version_id`, `reason`, `queued_at`, `claimed_until?`, `attempts` | PK `(book_id, version_id)`; claimed with `FOR UPDATE SKIP LOCKED` by an in-process worker; idempotent |
| `preferences` | `user_id` (PK), `theme`, `font_family`, `size`, `line_height`, `margins`, `revision` | per-user reader preferences (D-48); route `/me/preferences` |

## Reading package (file, one response)

Single file per `(book_id, version_id)` in the volume: manifest (title, language, direction, spine order, TOC tree, per-section id, title and size, resource table), sanitized section HTML, resources (images, fonts, CSS reduced to a safe subset) with media type and sha256. Details: [reading copy](reading-copy.md). A package size bound applies (a limits row is to be added; the EPUB cap of 50 MiB and base64 overhead set the order of magnitude); an oversize book fails the build with `package_too_large`.

## Invariants by id

| INV | Enforced by |
|---|---|
| INV-RDR-001 | primary key and idempotent job |
| INV-RDR-002 | pure `parse` function, parser version stored |
| INV-RDR-003 | `SafeHtml` type, fuzzing |
| INV-RDR-004 | partial unique index, atomic replace, annotations in separate tables with no FK to copies |
| INV-RDR-005..007 | identity mint and verify; `Verified<ReadingTicket>` |
| INV-RDR-008 | no route returns the EPUB or one chapter |
| INV-RDR-009 | read-once consumed by identity inside `verify(redeem: true)` |
| INV-RDR-010 | review of docs and UI text |
| INV-RDR-011 | `opens` table and per-user limits |
| INV-RDR-012..016 | constraints above, RLS, owner from header |
| INV-RDR-017, 019 | export queries scoped to `user_id` |
| INV-RDR-024, 025 | cursor transaction, read-only GET connection except the audit row |

## Limits (from [limits](../../04-architecture/cross-cutting/limits.md))

Opens 30 per user per hour; ticket TTL 15 minutes; highlights 5,000 per book per account; note 10,000 characters; progress writes bounded per second per book (value to be added); copy build attempts bounded with backoff.
