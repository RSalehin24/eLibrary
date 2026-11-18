# Evidence F — data volumes and supporting features

Status: DRAFT

Source: read-only subagent survey; no dumps or secrets opened.

- **Volumes:** no stated counts of books, users, annotations or EPUB sizes anywhere in docs. Only resource facts: host 3.72 GB with a ~2.5 GB container cap, Redis 256 MB, and one big scrape ("মহাভারত", 2,000+ topics) taking 2–4 GB per run. No SQL dumps or `.epub` files in the tree; only `*.example` env files. (Earlier plan figures ≈ 1,800–2,000 books are unverified here.)
- **Kindle:** `BookSendToKindleView`; Django `EmailMessage` with Anymail/Brevo, SMTP fallback; `@kindle.com` validation; multiple Kindle addresses per user; `UserBookKindleSend` log.
- **Saved filters:** per-owner JSON filters for catalog or queue.
- **Downloads:** `books/<slug>/download/<asset_type>/`; `BookOpeningRecord` tracks openings; no download-count model found.
- **Grants:** `PermissionGrant` + `PermissionScope` (see evidence A).
- **Demo account:** `auth/demo-login/` using settings credentials.
- **Admin:** managed users with setup-email resend, 2FA, password reset, Django admin; `AuditLog` written only by ingestion; **no audit viewer API**.
- **Search:** plain ORM `icontains` + normalized-text matching; **no Postgres full-text, trigram or index**.
- **Analytics:** none found.
- **Migrations:** per-app migrations plus a separate `migration/` directory (purpose unconfirmed).
- **Not checked:** frontend src, tests, `logs/`.
