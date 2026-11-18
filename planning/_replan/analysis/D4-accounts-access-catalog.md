Status: DRAFT

# D4 - Legacy accounts, common, access, catalog: synthesis for the Rust rebuild

Sources (synthesised, not re-derived): feature reports 09-accounts-common-access (cited `R09 §n`), 10-catalog (`R10 §n`), test notes 14b (AU1-27), 14c (AC1-16), 14d (AX1-26), 14e (CT1-21), 14f (CT22-34). Code root: `archive/app/backend/apps` (cited as `apps/...:line`). Verification tags: VERIFIED = I read the cited line in code; UNVERIFIED = taken from the reports only.

## 1. Purpose and scope

Legacy system: a private, invite-only Bengali ebook library (Django + DRF, session cookies). Operator (superadmin) imports books from one source website and builds EPUB/HTML/cover assets (ingestion/processing are out of scope here, other domains). Invited readers browse the catalog, read in a web reader, annotate, and send EPUBs to Kindle.

This document covers four legacy apps:
- accounts: user, password setup/reset, TOTP 2FA, profile, Kindle addresses, managed-user admin (`/api/auth/`).
- common: permission functions, TOTP-fence middleware, throttles, text normalisation, saved filters, audit-log model, health/csrf, seed and audit commands (`/api/`).
- access: permission grants, reader sessions/tokens, asset download, preview-HTML normalisation, send-to-Kindle, bookmarks, highlights, notes, reading progress (`/api/access/`).
- catalog: books, contributors/series/categories, catalog codes, manual (physical) books, metadata edit/review/version, My Books, exports, reference lists (`/api/catalog/`, prefix inferred from tests).

Out of scope (only touched where they constrain the above): ingestion, processing, source scraping, email templates, frontend. Migrations were not read by the source reports.

## 2. Features and behaviours

IDs are stable for this document. "Src" cites source report items.

### Accounts and authentication
- D4-F1 Email+password login with optional TOTP code; IP throttle 10/hour; structured error codes `invalid_credentials|otp_required|otp_invalid`. Src R09 §2#8, §3.1, AU1.
- D4-F2 Logout; session probe `GET session/` returning `{authenticated,user}`. Src R09 #6, #9.
- D4-F3 Demo login: one GET creates/logs in a shared demo user with no credentials. Src R09 #7, §3.2.
- D4-F4 Superadmin-managed users ("Users & Access"): list (search/status filter/sort/offset pagination), create (with or without password, optional invite email), update, hard delete, resend setup email. Src R09 #13-18, AU2, AU5-AU8, AU19.
- D4-F5 Invite flow: user created with unusable password and `email_setup_pending`; email link to `/create-password?uid&token`; link is the same mechanism as password reset. Src R09 §3.3-3.5, AU3, AU4, AU19.
- D4-F6 Self-service password reset by email (request, validate, confirm), 6 h expiry, newest link invalidates older, single use. Src R09 #10-12, §3.6, AU9-AU18.
- D4-F7 TOTP 2FA: status, setup (QR + secret), confirm, cancel, disable; admin can mark `totp_required`, in which case the user is fenced until enrolled and cannot disable. Src R09 #21-25, §3.8, AU20, AU21.
- D4-F8 Forced-TOTP middleware: all `/api/` calls return 403 `otp_setup_required` until enrolled, except an allow-list. Src R09 §3.8, AU21. VERIFIED apps/common/middleware.py:5-35.
- D4-F9 Profile: full name, profile image, password change (current password required), remove image. Src R09 #19-20, §5.5, AU22, AU25-AU27.
- D4-F10 Kindle recipient addresses (only @kindle.com), gated by the send:kindle scope; shows the sender address to whitelist at Amazon. Src R09 §5.5, AU23, AU24.
- D4-F11 Bootstrap: `seed_superadmin` command creates/updates the single superadmin from env. Src R09 §8.
- D4-F12 CSRF bootstrap `GET /api/csrf/`, health `GET /api/health/`. Src R09 #1-2.

### Access control and grants
- D4-F13 Permission grants: per-user scope grants, optionally narrowed to one book, one category, or one writer (author contributor); with `is_active`, `expires_at`, notes, granted_by. Src R09 #26-28, §4, AX11, AX13.
- D4-F14 Account-level permission editing through the managed-user form (set of 10 "manageable" scopes synced as global grants). Src R09 §4 sync_global_grants, AU5.
- D4-F15 Read Once vs Durable Read: read:once allows one opening per book (recorded at first reader launch or first HTML download); mutually exclusive with read:durable on the same target. Src R09 §4, §5.1, AC6-AC10.
- D4-F16 Book ownership ("My Books", `UserBook`) acts as an implicit full-access right for that user and book. Src R09 §4 user_owns_book, R10 §4.7, AC3, CT20, CT21. VERIFIED apps/common/permissions.py:39-45,65-99.
- D4-F17 Grant admin API with reference-data endpoint; self-grant/self-delete prohibited. Src R09 #26-29, AX11, AX12.
- D4-F18 Source-record visibility (source_urls/source_records on detail) gated by source_records:view; superadmin sees automatically. Src R10 §4.8, AX15.

### Reading, download, Kindle
- D4-F19 Reader launch creates a time-boxed (2 h) `PreviewAccessSession`; response gives a manifest URL containing an opaque token; token endpoints (manifest, EPUB resources unzipped on the fly, HTML) need no login. Src R09 §5.1, AC2, AX9, AX16.
- D4-F20 Asset download (cover, html, epub) with per-type permission rules; filename from current book title. Src R09 §5.2, AC1, AC4.
- D4-F21 Preview HTML normalisation at serve time: front-matter promotion into a book-info block, leading front sections, dedication cleanup (Bengali/English), local images inlined as base64. Src R09 §5.3, AX1-AX6, AX10, AC16, AX9.
- D4-F22 Send EPUB to the user's Kindle addresses by SMTP (forced SMTP even when Brevo API is configured); per-address result, last-sent timestamp recorded. Src R09 §5.4, AC5, AC11-AC15.
- D4-F23 Self-healing on missing asset file: asset marked FAILED, book to needs_review, 404/409 with re-generate hint. Src R09 §9, AX7.
- D4-F24 Reading position per (user, book) with percent; list of all progress rows. Src R09 #36, #41, #47, AX8, AX16.
- D4-F25 Bookmarks (unique per user/book/location), per slug and per token. Src R09 §5.1, §5.6, AX8, AX16.
- D4-F26 Highlights with colour, kind (highlight|quote), note, tags; per slug and per token. Src R09 §5.1, §5.6, AX17, AX25, AX26.
- D4-F27 "My notes" search view: buckets bookmarks/highlights/notes/quotes with filters book, kind, color, q. Src R09 §5.6, AX18-AX24.
- D4-F28 Saved filters (catalog or queue pages) per user. Src R09 #3-5.

### Catalog
- D4-F29 Book list with rich filters, sort, optional pagination, record type (digital default, manual, all). Src R10 §2#1, §3, CT30, CT31.
- D4-F30 Book detail: assets with gated download URLs, front-matter-derived contributors, TOC with empty-chapter detection, provenance for staff. Src R10 §4.8, CT4-CT9.
- D4-F31 Reference lists with book counts: categories, series, writers, translators, compilers, editors, publishers; optional pagination; Bangla-punctuation-insensitive search. Src R10 §2#4-10, §3, CT11-CT13.
- D4-F32 Manual (physical) books: create and list; fields binding, publisher, price, language, compilation flag. Src R10 §4.5, CT14, CT15.
- D4-F33 Metadata edit with before/after version snapshots; relation replacement; catalog code recompute. Src R10 §2#13, §4.6, CT1, CT24.
- D4-F34 Metadata review records (pending/approved/rejected/needs_review) that also set the book's review state. Src R10 §2#19-21, CT28.
- D4-F35 EPUB replace upload and re-generate (queue reprocess job). Src R10 §2#14-15, CT33, CT34.
- D4-F36 Soft delete of a book (scope metadata:edit, possibly book-scoped). Src R10 §2#23, CT25, CT26.
- D4-F37 My Books add/remove (idempotent); filter `ownership=mine`; sort by date added; `kindle_sent=mine`. Src R10 §4.7, CT20, CT29.
- D4-F38 Exports: CSV, PDF list, ticket/label PDF sheet. Src R10 §4.11, CT16, CT19.
- D4-F39 Catalog codes: 10-char structured code on books, writers, series, categories. Src R10 §4.1, CT10.
- D4-F40 Slug scheme: unicode slugs, regenerated on rename, legacy-slug fallback. Src R10 §4.2, CT2, CT4.
- D4-F41 Contributor handling: role-aware dedupe (a person with a non-author role is not also shown as author), compilers shown with editors, front-matter parsing, noise filtering. Src R10 §4.3, CT5-CT9, CT24.
- D4-F42 Maintenance commands: curated-catalog audit, source-site metadata repair, source-site batch audit, E2E seeder. Src R10 §6, R09 §8.

## 3. Actions by actor (role x action matrix)

Roles as the code defines them. There is no "reader" role flag: a reader is an authenticated user with `is_superuser=False`, `is_staff=False` plus grants and ownership. "Staff" (`is_staff`) can only be set via Django admin or seed (managed-user serializers do not expose it) and is a full wildcard in `user_has_scope`. "Demo" is an ordinary user row (email from settings) reached via `demo-login`; it receives only the implicit baseline and whatever grants an admin gives it. Anonymous = unauthenticated.

Legend: Y = allowed, N = denied, G = only with the named grant (global, or scoped to that book/category/writer), O = also allowed by ownership (UserBook), T = token holder, E = see note.

| Action | Anonymous | Reader (no grants) | Reader (with grant) | Demo | Staff | Superadmin |
|---|---|---|---|---|---|---|
| Health, csrf | Y | Y | Y | Y | Y | Y |
| Session probe | Y | Y | Y | Y | Y | Y |
| Demo login | Y (no credentials) | Y (no-op) | Y | Y | Y | Y |
| Login, reset request/validate/confirm | Y | N when logged in (confirm only) | same | same | same | same |
| Profile read/edit | N | Y | Y | Y | Y | Y |
| Kindle address edit | N | N | G send:kindle (global only) | N unless granted | Y | Y |
| 2FA setup/confirm/cancel | N | Y | Y | Y | Y | Y |
| 2FA disable | N | Y unless `totp_required` | same | same | same | same |
| List/read any non-deleted book (any state) | N | Y | Y | Y | Y | Y |
| Reference lists, export CSV/PDF, tickets | N | Y | Y | Y | Y | Y |
| Add/remove My Books (self) | N | Y | Y | Y | Y | Y |
| Source URL in book list (`primary_source`) | N | Y | Y | Y | Y | Y |
| source_urls/source_records on detail | N | N | G source_records:view | N | Y | Y |
| raw_provenance on detail | N | N | N | N | Y (`is_staff`) | Y (staff flag is set on superadmin) |
| Manual books list/create | N | N | G physical_books:view | N | Y | Y |
| Edit metadata, upload EPUB, regenerate, reviews, versions, delete book | N | N | G metadata:edit (book/category/writer scope allowed) | N | Y | Y |
| View cover / launch reader | N | O | G preview:html, read:durable, download:file or read:once | O | Y | Y |
| View HTML preview | N | O | G preview:html (blocked once read-once spent) | O | Y | Y |
| Download EPUB/file | N | O | G download:file | O | Y | Y |
| Send to Kindle | N | O (needs saved addresses) | G send:kindle | O | Y | Y |
| Bookmarks/highlights/progress on a book via slug | N | N unless live preview session | G any of 4 read scopes or live session (owners are NOT covered) | same | Y | Y |
| Reader-token endpoints | T (token only) | T | T | T | T | T |
| Own notes list, progress list, delete own bookmark/highlight | N | Y | Y | Y | Y | Y |
| Saved filters (own) | N | Y | Y | Y | Y | Y |
| Users admin (list/create/edit/delete/resend) | N | N | N | N | N (IsSuperAdmin = `is_superuser`) | Y (not self-edit, not delete superusers) |
| Grants admin and reference data | N | N | N | N | N | Y (not for self) |
| Processing/duplicate-review endpoints (other domain) | N | N | G processing:manage | N | Y | Y |

Notes on the matrix:
- Staff passes every `user_has_scope` check, including both read:once and read:durable, so staff are never read-once limited. VERIFIED apps/common/permissions.py:31-32,48-62.
- `IsSuperAdmin` is `is_superuser` only; staff are not user-admins. VERIFIED permissions.py:148-151.
- Whoever holds a grant with scope `admin:full_control` anywhere in range acts as a wildcard in `user_has_scope`. VERIFIED permissions.py:34-36.
- Test CT14 says "any logged-in user" may create manual books, but the view requires physical_books:view (global scope check, no book). VERIFIED apps/catalog/views/books.py:79. The test likely authenticates as superadmin; treat the code as truth. UNVERIFIED test fixture.
- `capability_scopes` (sent to the UI): superadmin gets a fixed list of 12 scopes; others get `submit:create` plus every active grant scope of ANY target (global and scoped mixed), so UI can overstate global rights. VERIFIED accounts/models.py:113-140.
- `submit:create` is implicit for every user (appears in `capability_scopes` for all; ingestion decides what it does).

## 4. Business rules and invariants

### 4.1 Scope vocabulary
- 12 scopes: submit:create, preview:html, read:durable, download:file, metadata:edit, physical_books:view, processing:manage, access:manage, source_records:view, admin:full_control, send:kindle, read:once. VERIFIED apps/access/models.py:18-30.
- Account-manageable (10, set through the user form): access:manage, processing:manage, source_records:view, metadata:edit, physical_books:view, read:once, send:kindle, read:durable, preview:html, download:file. VERIFIED models.py:33-44.
- Target-scopable (6, may carry book/category/writer): metadata:edit, read:once, send:kindle, read:durable, preview:html, download:file. VERIFIED models.py:46-53. submit:create and admin:full_control are not UI-manageable.
- Scope names in the profile/UI: "Durable Read", "Download Ebook", "Edit Metadata", "Manage Access", "Manage Processing", "View Records' Source", "View Physical Books List".

### 4.2 Grant evaluation
- Grant is active iff `is_active` and (`expires_at` null or in the future). VERIFIED models.py:57-61.
- Without a book: only global grants (book, category, contributor all null) count. With a book: global OR grant on that book OR grant on any category of the book OR grant on a contributor who has the AUTHOR role on that book (translator/editor grants do not apply). VERIFIED permissions.py:8-24.
- `user_has_scope`: anonymous false; superuser or staff true; else any matching active grant, where `admin:full_control` matches every scope. VERIFIED permissions.py:27-36.
- A grant targets at most one of book/category/contributor; target-bearing grants must use a scoped scope; contributor must have at least one author contribution. UNVERIFIED (R09 #27; serializer not re-read).
- Mutual exclusion: read:once and read:durable cannot be active together on the same exact target (exact-target comparison only; global durable plus book-level once is allowed, and the limit logic lets durable win). R09 #27, §9; AC10. Part VERIFIED: durable override at permissions.py:58-59.
- Account-level grants via the grants API are not restricted to the 10 manageable scopes (could create global `admin:full_control`). UNVERIFIED (R09 #27).
- Self-service guard: a superadmin cannot create or delete a grant whose user is themselves (403); `granted_by` is recorded. AX12, R09 #27-28.
- `sync_global_grants` (user form): hard-deletes global grants of manageable scopes that were deselected, creates missing ones, never touches scoped grants; expired/inactive global grants of kept scopes stay and a new duplicate is added. UNVERIFIED (R09 §4).
- Grants cannot be edited after creation (no PATCH): is_active and expires_at are write-once. UNVERIFIED (R09 #28).

### 4.3 Ownership rule (critical)
- `user_owns_book` is true if a `UserBook` row exists for (user, book). VERIFIED permissions.py:39-45.
- Owners bypass every read gate: cover, HTML preview, reader launch (owner returns True before scope check), download of files and Kindle send. VERIFIED permissions.py:65-99.
- `UserBook` can be created by any authenticated user for any non-deleted book via `POST books/<slug>/my-books/` with no permission check, no state check. VERIFIED apps/catalog/views/books.py:94-106. Therefore every logged-in user can grant themselves full access (download EPUB, HTML, cover, Kindle, reader launch) to any book. See issue D4-I1.
- The same `UserBook` is also created automatically when a user's own submission is linked to a ready/resolved book (CT21, AC3; the code lives in ingestion/models/submissions.py, grep-confirmed to reference UserBook; behaviour UNVERIFIED). This is the intended meaning of "owner": the person who imported the book.
- Ownership is NOT honoured by `ensure_book_reader_access` (bookmarks/highlights/reading-session by slug): owners with no grant get 403 unless a live preview session exists. VERIFIED apps/access/views/shared.py:237-249.

### 4.4 Read Once
- Limit applies to a user who is not superuser, not owner, holds read:once for the book, does not hold read:durable, and a `BookOpeningRecord(user, book)` exists. VERIFIED permissions.py:48-62.
- Record is created on first reader launch or first HTML download (only for non-superuser, non-owner, read:once and no durable). R09 §5.1-5.2; AC6-AC9. UNVERIFIED (view code not re-read).
- Consequences (tests AC6-AC9): second launch 403; HTML download then launch 403 and vice versa when both read:once and preview:html held; read:once alone cannot download HTML (not consumed) but can launch once.
- The record is permanent, shared across HTML and reader, never cleared when the grant changes. A live 2 h reader token continues to work after the limit applies; relaunch is blocked even within the live session because the limit check precedes session reuse. R09 §5.1, §9.
- Staff bypass the limit (see matrix).

### 4.5 Reader tokens and sessions
- Launch rule: owner, or not read-once-limited and any of preview:html, read:durable, download:file, read:once; or an existing live session. Else 403 "You do not have reader access for this book." R09 §5.1.
- Session: one `PreviewAccessSession` per launch moment (reused if exists), `launch_count += 1`, `expires_at = now + 2 h` refreshed on each launch only, token `secrets.token_urlsafe(32)` unique. VERIFIED apps/access/models.py:10-15,117-142.
- Token endpoints (manifest, epub, html) have no login: the token is the credential; they do not re-check grants, user active flag or revoked scopes. R09 §5.1, §9.5. Reading-position, bookmark and highlight token endpoints do require login AND `session.user_id == request.user.id`.
- Guest sessions (null user) are modelled and handled but nothing creates them. R09 §5.1.
- The manifest embeds user's bookmarks and highlights and URLs for session/bookmarks/highlights; responses carry no-store headers. R09 §5.1.

### 4.6 Downloads and previews
- cover: same permission as reader launch (so a read-once-spent user loses the cover). html: owner; else not read-once-limited AND preview:html. epub and other types: download:file or owner. 403 text "You do not have download access for this book." R09 §5.2; permissions.py:65-99 VERIFIED.
- Assets must be READY; a missing file triggers the self-heal flow (4.9).
- Download filenames use the current book title with `<>:"/\|?*` replaced and trimmed; extension by type. R09 §5.2; AC4.
- HTML previews are served raw (after normalisation) from the API origin; no CSP or sanitising. R09 §5.3.
- Soft-deleted books are still reachable through the access endpoints because they look up `Book` by slug without a `deleted_at` filter. VERIFIED apps/access/views/assets.py:121,162; reader.py:40; sessions.py:81-106; notes.py:95,101.
- Metadata `source_urls` and `source_records` appear on the detail only with source_records:view (or staff). R10 §4.8; AX15.

### 4.7 Kindle rules
- Permission: send:kindle (book-aware) or owner. VERIFIED apps/access/views/assets.py:163 and permissions.py:77-78.
- Addresses: stored on the user as a JSON list; accepted domain exactly `kindle.com` (no subdomains such as free.kindle.com), lowercased, deduped in order; editing the list in the profile needs the global send:kindle scope (staff/superuser pass). At send time addresses failing the validator are ignored silently (AC14). R09 §5.4-5.5; AU23-24.
- None valid: 400 "Add at least one Kindle email in your profile before sending."
- Sender: ACCOUNT_INVITE_FROM_EMAIL or DEFAULT_FROM_EMAIL (display name stripped); shown to the user via `kindle_sender_email` so they can whitelist it with Amazon.
- Transport: SMTP only. If the configured backend is the Brevo API backend it is replaced by SMTP (the API cannot send attachments), using host/port/user/password/TLS/timeout env; missing credentials gives 502 with explanation and `failedEmails`; SMTP auth failure stops the loop and marks all remaining failed. AC11-AC13.
- One message per address on one connection: subject = title, empty body, attachment `application/epub+zip`. Partial success returns 200 with delivered/failed lists. R09 §5.4; AC5.
- On any delivery records `UserBookKindleSend(user, book)` replacing prior row (last-sent timestamp). No rate limit, no size check, synchronous. R09 §5.4.

### 4.8 Reader content (bookmarks, highlights, notes, progress)
- Bookmark: location(<=255) required, label, note, chapter_href/label, preview_text(<=280); unique per (user, book, location). VERIFIED models.py:164-176.
- Highlight: cfi_range(<=1024), text required, note, colour in yellow|green|blue|pink|underline, kind highlight|quote, tags list (trimmed, unique, non-strings rejected); no uniqueness constraint. VERIFIED models.py:179-210.
- Reading position: one per (user, book); last_location(<=255); progress_percent float without 0-100 validation. VERIFIED models.py:145-161.
- Notes view buckets: bookmarks; highlights = kind highlight with empty note; notes = kind highlight with non-empty note; quotes = kind quote. Filters book, kind, color (highlights/notes only), q. Unknown kind returns `{}`. R09 §5.6; AX18-AX24.
- Per-user isolation (AX24). Deletes/updates of own bookmarks/highlights do not re-check book access, so users keep management after losing access. R09 §5.6.

### 4.9 Missing asset self-heal
Serving an asset whose stored file is absent: marks asset FAILED, clears file info, sets book.state and review_state to needs_review (or queues reprocess and returns 409), returns 404 "This file is no longer available in storage. Please regenerate the book." Any user with a valid token or download rights can trigger it, and a storage read error is treated as missing. R09 §9; AX7.

### 4.10 Authentication and account rules
- Email is the login identifier (unique); no username.
- Password minimum: reset/confirm and admin create/update enforce length >= 12 only; profile change additionally runs the project validators. R09 #12, §5.5.
- Login: inactive users fail as invalid credentials. If a confirmed TOTP device exists, `otp_token` is mandatory; the first confirmed device is used (no ordering). Users with `totp_required` but no device log in without OTP and are fenced by the middleware. R09 §3.1.
- Password-reset eligibility: active, has usable password, not `email_setup_pending`; else 404 "No user exist with this email." (deliberate enumeration, AU16-AU17).
- Token: custom generator hashing pk, password, last_login (to the second), timestamp, email, `password_setup_nonce`, `email_setup_pending`; validity 6 h (PASSWORD_RESET_TIMEOUT default 21600, VERIFIED settings.py:104). Any new request or resend bumps the nonce and kills older links (AU14, AU19); a used link is dead (AU18).
- Login after the link was issued also invalidates it (last_login in hash). R09 §9.
- Reset confirm while logged in is refused (AU9). Confirm for a user who must enrol TOTP logs them in and returns `next_step=totp_setup`; others `next_step=login`. AU10-AU11.
- TOTP-required invitees stay `email_setup_pending` until their device is confirmed; resend remains possible in that window; afterwards "This user does not need a setup email." AU20.
- Admin cannot edit self from Users & Access (AU8), cannot delete superusers or self, cannot send setup email to superusers or self; can edit/deactivate other superusers. R09 #16-18, §9.10.
- Create-user validation: at least one account permission must be selected (when supplied); read:once and read:durable exclusive; invite requires active; no password and no invite is an error. R09 #14.
- Invite email failure rolls back the whole user creation (atomic) with a message mentioning Brevo. R09 #14.
- TOTP: issuer "RSalehin24 Library", provisioning URI and QR SVG returned (AU21); secret returned raw; disabling blocked when admin requires it; no password re-auth.
- Disabled users lose session access on the next request (user lookup rejects inactive). R09 §3.9.
- Forced TOTP fence allow-list: session, demo-login, logout, profile, 2fa status/setup/confirm/cancel/disable, csrf. VERIFIED middleware.py:5-16. Health and non-API paths are not fenced beyond that.
- Demo login: user is created with `totp_required` false and a settings-provided password; login ignores is_active and TOTP. VERIFIED auth_and_password_views.py:160-184.
- Throttles: login 10/hour per IP, password_reset 5/hour per IP, register 5/hour (unused route), submission 40/hour (ingestion). VERIFIED settings.py:211-215. Not throttled: demo-login, reset validate/confirm, 2fa confirm, resend, kindle send.
- Sessions: HttpOnly, SameSite Lax, Secure by environment; password change in profile keeps the session (`update_session_auth_hash`). VERIFIED settings.py:231-235 (cookie flags only).
- CSRF enforced by DRF session auth for authenticated unsafe methods only; the login endpoint itself is exempt.

### 4.11 Catalog visibility and search rules
- Base queryset excludes only soft-deleted books (`deleted_at IS NULL`); it does NOT filter by `state` or `review_state`, so drafts, processing, needs_review and rejected books are visible to every authenticated user in list, detail and exports. VERIFIED apps/catalog/views/shared.py:325-356.
- The list annotates per-user flags (is_in_my_books, user_owns_book, my_books_added_at, has_sent_to_kindle, user_kindle_sent_at, latest_submission_at) and defers heavy columns (summary, raw_*, html, toc, content_items); test CT32 makes deferring a hard requirement.
- Default list is digital only; `record_type=all|digital|manual`; manual list is a separate permission-gated endpoint.
- `q` searches: catalog_code, title, any contributor name and code, series, category name and code, and linked submissions' original/normalised input (other users' inputs included unless `ownership=mine`). Not searched: summary, publisher, edition, source URLs, slug. R10 §3.
- Fuzzy matching: raw icontains OR normalised contains OR tokens joined by optional punctuation regex. normalisation keeps Unicode letters/numbers/marks (so Bengali combining signs survive), lowers, drops all other characters (so "a-b" becomes "ab"). R09 §7; CT12, CT31.
- Filters: category/series fuzzy; author/translator/editor/publisher by role+name; exact codes; ownership=mine; kindle_sent=mine; state/review_state/submission_status/processing_status exact; created_after/before; binding; sort whitelist with `requested_at` and `sent_at` only valid with the matching filter. R10 §3.
- Pagination only when `page` or `limit` is present (shape changes from array to `{entries,pagination}`); limit clamps 1..100 (default 10 for books, 60 elsewhere); page clamps to last page. R10 §3; CT13, CT15, CT30.
- Reference lists return only entities with book_count > 0, exclude noise contributor names (prose-fragment regex) except publishers, and use cleaned display names. R10 §3; CT11.
- Export respects the same filters, ignores paging, loads everything.

### 4.12 Catalog data invariants
- Catalog code (10 chars, alphabet `23456789ABCDEFGHJKLMNPQRSTUVWXYZ`, 32 symbols no 0/1/I/O): unique, nullable, uppercased. Entity code payload = 2-bit type tag + 16-bit sequence + 32-bit salt; book code = tag + 16-bit category sequence + 16-bit writer sequence + 12-bit per-pair sequence + 4-bit check; all passed through an affine scramble mod 32^10 with constants in source. R10 §4.1; CT10 asserts the book code decodes to category and writer codes.
- A book's code is recomputed when its primary category (first by name) or primary author (first author by sort order) changes, so it is not a stable ID. R10 §4.1, §7.1.
- Capacity limits: 65535 entities per type, 4095 books per (category, writer) pair; beyond that a ValueError.
- Slug: unique, unicode, from `unicode_slugify(title)`; changes on every title change; duplicates get `-2`, `-3`; legacy fallback `slugify(title, allow_unicode=True)` accepted for detail (CT4). Duplicate titles are allowed (CT3).
- Contributors: unique by both name and normalised_name; roles author, translator, compiler, editor, illustrator, cover_artist, publisher, other; (book, contributor, role) unique; an author entry is dropped when the same normalised person appears under a non-author role (CT7, CT24); editors list always includes compilers; manual create folds compilers into editors (CT14). Names cleaned: strip edge punctuation and unbalanced brackets (CT9 keeps initials such as "সি.").
- Series and categories: flat; name and normalised name unique; manual book requires at least one category.
- One `GeneratedAsset` per (book, type html|epub|cover) with status pending|ready|failed; one `BookSource` per book (unique), normalised URL globally unique. VERIFIED/UNVERIFIED mix: R10 §4.2, §4.9; AX15.
- `Book.state` default draft (LifecycleState: draft, processing, needs_review, ready, published, archived, soft_deleted); `review_state` default pending (pending, needs_review, approved, rejected). R09 §6; R10 §4.6.
- Manual book: state ready, review approved, source_site `manual-library:<uuid>`; publisher stored both as `manual_publisher` and a publisher contributor; price Decimal(10,2); binding hard_cover|paper_back; language bn|en. R10 §4.5.

### 4.13 Metadata review and versioning rules
- Metadata PATCH (even PUT) is always partial; allowed fields title, summary, state, review_state, book_info_html, dedication_html, main_content_html, toc, contributors, series, categories, notes, price, binding, is_compilation, publisher, language. R10 §2#13.
- Contributors, if sent, must include at least one entry with role author/translator/editor/compiler (publisher-only fails). R10 §4.6.
- Each edit writes two `MetadataVersion` rows (`manual_edit_before`, `manual_edit_after`), snapshot JSON; list returns metadata only (no snapshot, no revert). CT1; R10 §4.6.
- Relations are replaced wholesale (delete-all, recreate) only for keys provided; catalog code recomputed. Not transactional.
- `state` and `review_state` can be written directly with no transition rules or review record.
- Review create: sets book.review_state to the review state; reviewer = actor unless state pending; `metadata_last_reviewed_at` set only for approved/rejected. Review update always sets reviewer = actor and book.review_state. CT28; R10 §2#20-21.
- Scoped metadata:edit holders may edit, review, delete only within their book scope (inline checks). CT23, CT25-CT26.
- Metadata edit/review/version views look books up without the deleted filter (soft-deleted editable). R10 §7.4. UNVERIFIED in code.
- Soft delete sets `deleted_at` and state soft_deleted; no restore API; ingestion resurrects a deleted book of the same normalised title and source site. R10 §4.2.

## 5. Data handled / owned

All ids are UUID unless noted; most tables have created_at/updated_at (TimeStampedModel). Hard deletes everywhere except Book (soft).

### Accounts
- User (int pk, Django AbstractUser without username): email unique; full_name(255); profile_image (file, public via media); kindle_emails (JSON list); totp_required bool; email_setup_pending bool; password_setup_nonce uint; is_active, is_staff, is_superuser; last_login. VERIFIED accounts/models.py:46-54. Derived: has_totp_enabled (confirmed device exists), requires_totp_setup, can_resend_setup_email, global_grant_scopes, capability_scopes.
- TOTPDevice (django-otp): per user, name "default", confirmed flag, key; unconfirmed rows deleted at each setup/cancel.
- Sessions: Django session table. Lifecycle: created by login/demo-login/reset-confirm (TOTP-pending), destroyed by logout; no listing, no "log out everywhere".

### Access
- PermissionGrant: user, nullable book/category/contributor, scope(32), is_active, expires_at, granted_by (SET_NULL), notes. Lifecycle: created by admin API or user-form sync; hard-deleted; never edited. VERIFIED models.py:67-114.
- PreviewAccessSession: token(128, unique), user (nullable), book, source_submission (SET_NULL), expires_at (+2 h), launch_count. VERIFIED models.py:117-142.
- ReadingSession: user, book, preview_session (SET_NULL), last_location, progress_percent, last_opened_at(auto_now); unique(user, book). VERIFIED.
- Bookmark and Highlight as in 4.8. VERIFIED.
- BookOpeningRecord: user, book; unique(user, book); permanent. VERIFIED models.py:213-218.

### Common
- AuditLog: actor (SET_NULL), verb, target_type, target_id, request_id, remote_addr, user_agent, payload JSON. No code writes to it in these apps. R09 §6.
- SavedFilter: owner (CASCADE), target catalog|queue, name(120), params JSON (unvalidated); unique (owner, target, name). R09 §6.
- Abstract mixins: UUID pk, timestamps, SoftDelete (deleted_at), LifecycleState, ReviewState.

### Catalog
- Book: title, normalized_title, slug, catalog_code, record_type digital|manual, state, review_state, metadata_last_reviewed_at, deleted_at, source_site, edition/normalized_edition, group (BookGroup), summary, book_info_html, dedication_html, main_content_html, toc (nested JSON), content_items, cover_source_url, empty_chapters_count, raw_scraped_metadata, raw_scrape_payload, manual_* fields (is_compilation, binding, publisher, price, language). R10 §4.
- Contributor, Series, Category: name, normalized_name (both unique), slug (unique), catalog_code. Joins BookContributor(role, raw_value, sort_order), BookSeries(sort_order, raw_value), BookCategory(raw_value).
- GeneratedAsset: book, asset_type, status, file, storage_path, legacy_path, content_type, file_size, checksum, is_protected, source_job; unique (book, type).
- BookSource: source_url, normalized_source_url (global unique), source_title/type/site, is_primary; unique per book.
- UserBook (My Books/ownership) and UserBookKindleSend: (user, book) unique; the latter holds the last send time. VERIFIED apps/catalog/models/books.py:157-178.
- MetadataVersion: book, snapshot JSON, source, notes, created_by. MetadataReview: book, state, requested_by, reviewer, notes.
- BookGroup (canonical title/note) used by ingestion duplicate handling; no catalog API.
- Curated models (CuratedBookDocument/Entity/Section/Evidence): written by ingestion, read-only here.
- Personal data classes: email, full name, profile image, Kindle emails, reading position, annotations, grants (access history), opening records. Secrets: password hashes, TOTP keys, reset tokens (derived, not stored), reader tokens (stored plain).

## 6. Interfaces

Conventions: JSON; session cookie plus CSRF header for authenticated unsafe methods; error bodies `{detail}` (auth) or field maps (DRF validation) or `{detail,code}` (login/TOTP). 403 for unauthenticated on DRF endpoints, not 401 (AX14), except notes which accept 401 or 403 (AX23). "Perm" column uses the legacy names.

### 6.1 common (`/api/`)
| Method | Path | Perm | Request | Response |
|---|---|---|---|---|
| GET | health/ | any | - | `{status,environment,service}` |
| GET | csrf/ | any | - | `{csrfToken}` + cookie |
| GET | saved-filters/ | auth | `?target` | list of `{id,target,name,params,created_at}` |
| POST | saved-filters/ | auth | target(catalog|queue), name<=120, params object | 201; duplicate name yields 500 (bug) |
| DELETE | saved-filters/<uuid>/ | auth, own | - | 204 |

### 6.2 accounts (`/api/auth/`)
| Method | Path | Perm | Request | Response |
|---|---|---|---|---|
| GET | session/ | any | - | `{authenticated,user}` |
| GET | demo-login/ | any | - | UserSerializer; creates session (side effect on GET) |
| POST | login/ | any, 10/h IP | email,password,otp_token? | 200 user; 400 `{detail,code}` |
| POST | logout/ | auth | - | 204 |
| POST | password-reset/ | any, 5/h | email | 200 / 404 enumeration |
| POST | password-reset/validate/ | any | uid,token | 200 / 400 |
| POST | password-reset/confirm/ | any, logged-out only | uid,token,new_password(>=12) | 200 `{detail,next_step[,user]}` |
| GET/PATCH | profile/ | auth (JSON/form/multipart) | full_name, profile_image, remove_profile_image, current/new/confirm password, kindle_emails / kindle_emails_text | ProfileSerializer incl. `kindle_sender_email`, `profile_image_url` |
| GET | 2fa/status/ | auth | - | `{enabled,pending_setup,required,setup_required}` |
| POST | 2fa/setup/ | auth | - | `{provisioning_uri,secret,qr_svg}` |
| POST | 2fa/confirm/ | auth | token | 200 / 400 |
| POST | 2fa/cancel/ | auth | - | 200 |
| POST | 2fa/disable/ | auth | - | 200 / 400 if required or none |
| GET | users/ | superadmin | q,status(all|active|disabled|totp_required),sort(name_asc|name_desc|email_asc|email_desc|status),offset,limit(1..180, default 60) | `{rows,pagination{offset,limit,totalCount,hasMore,nextOffset}}` |
| POST | users/ | superadmin | email,full_name,password?,is_active,totp_required,send_invite_email,global_scopes[] | 201 |
| GET/PUT/PATCH/DELETE | users/<int>/ | superadmin | fields as above (no self-edit) | user / 204 |
| POST | users/<int>/resend-setup-email/ | superadmin | - | ManagedUser |
Unrouted dead code: RegisterView.

### 6.3 access (`/api/access/`)
| Method | Path | Perm | Notes |
|---|---|---|---|
| GET/POST | grants/ | superadmin | list all grants (unpaginated); create (user,book|category|contributor,scope,is_active,expires_at,notes); 403 on self |
| DELETE | grants/<uuid>/ | superadmin | 204; 403 on self |
| GET | references/ | superadmin | users, books, categories, writers, account_scopes, scoped_scopes; `?view=users` gives only scopes; unpaginated |
| GET | books/<slug>/download/<cover|html|epub>/ | auth + rules 4.6 | file or normalised HTML |
| POST | books/<slug>/send-to-kindle/ | auth + 4.7 | `{detail,deliveredEmails,failedEmails,senderEmail}`; 400/502 on failure |
| POST | books/<slug>/reader-launch/ | auth + 4.5 | `{launch_url,manifest_url,expires_at}` |
| GET | reader/<token>/manifest/ | token | book, epub_download_url, html_preview_url, reading_session_url, bookmarks_url, highlights_url, reading_session, bookmarks[], highlights[] |
| GET | reader/<token>/epub/ and epub/<path>/ | token | EPUB file inline, or one zip entry (unzipped resource) |
| GET | reader/<token>/html/ | token | normalised preview HTML |
| GET/POST | reader/<token>/session/ | login + token owner | last_location, progress_percent |
| GET/POST | reader/<token>/bookmarks/ ; DELETE .../<uuid>/ | login + token owner | |
| GET/POST | reader/<token>/highlights/ ; PATCH/DELETE .../<uuid>/ | login + token owner | |
| GET/POST | books/<slug>/reading-session/, /bookmarks/, /highlights/ | auth + read access | |
| DELETE | bookmarks/<uuid>/ ; PATCH/DELETE highlights/<uuid>/ | auth, own | no access re-check |
| GET | me/notes/ | auth | `?book,kind,color,q`, buckets by kind |
| GET | me/reading-progress/ | auth | all rows, unpaginated |

### 6.4 catalog (`/api/catalog/`)
| Method | Path | Perm | Notes |
|---|---|---|---|
| GET | books/ | auth | filters 4.11; array or `{entries,pagination}` |
| GET | books/export/?format=csv|pdf | auth | UTF-8 BOM CSV or PDF; 503 without reportlab |
| GET | books/tickets/ | auth | PDF label sheet |
| GET | categories/ series/ writers/ translators/ compilers/ editors/ publishers/ | auth | counts; optional pagination |
| GET/POST | manual-books/ | physical_books:view | create returns detail 201 |
| PATCH/PUT | books/<slug>/metadata/ | metadata:edit (scoped) | returns detail |
| POST | books/<slug>/assets/epub/ | metadata:edit | multipart `file`, `.epub` extension only |
| POST | books/<slug>/regenerate/ | metadata:edit | 202 `{book,job,created}` |
| POST/DELETE | books/<slug>/my-books/ | auth | idempotent; no permission check (D4-I1) |
| GET | books/<slug>/metadata-versions/ | metadata:edit | list of `{id,source,notes,created_at}` |
| GET/POST | books/<slug>/metadata-reviews/ | metadata:edit | state, notes |
| PATCH/PUT | metadata-reviews/<uuid>/ | metadata:edit | |
| GET | books/<slug>/ | auth | detail; slug fallback scan |
| DELETE | books/<slug>/ | metadata:edit (scoped) | soft delete 204 |
Slug segment is `<path:slug>` (may contain "/"), catch-all last. No endpoints for category/series/writer CRUD, merge, rename, delete, restore of books, groups/editions, or Kindle (that lives under access).

### 6.5 Management commands
`seed_superadmin` (env-driven), `seed_e2e_data` (destructive, hard-coded test password; test only), `source_site_batch_audit`, `audit_curated_catalog`, `repair_source_site_metadata` (destructive by default, `--dry-run` safeguard). R09 §8; R10 §6.

## 7. States and processes

### 7.1 User lifecycle
States are flag combinations on User:
- invited: `is_active`, unusable password, `email_setup_pending=True`.
- password set, TOTP enrolment pending: usable password, `totp_required`, no confirmed device, `email_setup_pending` still True; session granted after reset-confirm but fenced.
- active: usable password, pending False.
- disabled: `is_active=False` (cannot log in; existing sessions fail on the next request).
- deleted: hard delete cascading grants, bookmarks, highlights, sessions, My Books, Kindle sends (superusers and self cannot be deleted).
Transitions: create (admin) -> invited (or active when a password is given); reset-confirm -> active or TOTP-pending; confirm TOTP -> active; admin deactivates/reactivates; delete.

### 7.2 Invite and password-setup process
1. Superadmin POST users/ with send_invite_email: atomic create, password unusable, `email_setup_pending=True`, nonce 0 to 1, email with link `{frontend}/create-password?uid=<b64 pk>&token=<tok>`; delivery failure rolls back user creation.
2. Frontend POST password-reset/validate/ then password-reset/confirm/ with new password >= 12 chars.
3. Confirm: password set, nonce +1 (invalidates link), `email_setup_pending = totp_required and not totp_enabled`; if TOTP still required, log in and return `next_step=totp_setup`, else `next_step=login`.
4. TOTP step: 2fa/setup then 2fa/confirm clears `email_setup_pending`.
5. Resend (superadmin) while pending: nonce +1 under row lock, new email, old link dead. Link host: `FRONTEND_BASE_URL`; when it is localhost without port, FRONTEND_PORT is appended (AU4). Without FRONTEND_BASE_URL the link is built from the request host (poisoning risk, D4-I11). Mail templates: HTML with inline styles plus text part; subject "Your RSalehin24 Library account is ready" (AU3).

### 7.3 Self-service password reset
Request (5/h): lookup active user by email (case-insensitive) with usable password and not pending; else 404. Lock row, nonce +1, email with `/reset-password/confirm?uid&token`, text "valid for 6 hours". Validate and confirm use the same token generator; expiry enforced by timestamp (tests at +5h59 valid, +6h01 invalid, AU13). Confirm: refused if logged in; password set (>=12 chars); TOTP-required users are logged in and routed to enrolment (AU10).

### 7.4 Login and TOTP
- Login: authenticate, if confirmed device then require `otp_token` (400 `otp_required` if missing, `otp_invalid` if wrong), create session.
- TOTP enrolment: setup deletes unconfirmed devices, creates an unconfirmed device, returns URI/secret/QR; confirm verifies a token, marks it confirmed. Cancel removes unconfirmed. Disable removes all devices (only if not admin-required). Calling setup while enabled adds a second device; login uses the first confirmed one (undefined order).
- Fence: while `requires_totp_setup`, only the allow-list under 4.10 responds.

### 7.5 Read-once and reader session
Launch: check read-once limit -> check permission/live session -> record opening (if read-once) -> create or reuse session (2 h, refreshed) -> return URLs. HTML download follows the same limit/record rule. Session expiry only ends token access; opening records last forever.

### 7.6 Grant lifecycle
Create (API) -> active (optionally expiring) -> expires by time or is deleted; no edit, deactivate or history. User-form sync deletes and recreates global grants.

### 7.7 Asset lifecycle (access/catalog view)
pending -> ready (processing or EPUB upload) -> failed (missing file detected on access, or processing error). Failure flips the book to needs_review and can queue reprocess.

### 7.8 Book states and review
- `state`: draft (default) -> processing -> ready/published; needs_review, archived, soft_deleted. Writable freely by metadata PATCH; soft delete via DELETE; no state restricts catalog visibility (4.11).
- `review_state`: pending, needs_review, approved, rejected. Changed by review POST/PATCH or directly by metadata PATCH or by the missing-asset self-heal. `metadata_last_reviewed_at` set only for approved/rejected.
- "Quarantined" in the audit command is `review_state=rejected` and `state=archived`. R10 §6.
- Manual books are born ready/approved.

### 7.9 Catalog code generation
Entity: sequence = max decoded sequence of valid codes in that table + 1 (full scan), embedded with a type tag and a salt, scrambled. Book: embeds primary category sequence, primary author sequence and per-pair counter (max + 1 over all books incl. deleted) plus 4-bit check. Save inserts with null code then updates; relation replacement recomputes; code kept only if embedded sequences still match. No locking: the unique constraint is the only race guard. Details in 4.12.

### 7.10 Metadata edit
snapshot before -> apply fields -> save (slug may change) -> replace relations -> recompute code -> snapshot after. Not atomic.

### 7.11 Kindle send
Check permission -> validate addresses -> resolve ready EPUB (or self-heal) -> read file into memory -> choose SMTP -> one message per address -> record last-send -> respond with delivered/failed. See 4.7.

## 8. Issues

Severity: C critical, H high, M medium, L low. V = verified in code by me; U = from reports only.

| ID | Sev | Issue | Ver |
|---|---|---|---|
| D4-I1 | C | Any authenticated user can POST `books/<slug>/my-books/` and thereby become "owner", which bypasses read-once, preview, download, cover, reader launch and Kindle gates for that book. Access control is therefore effectively cosmetic; the gating by grants can be defeated by one request. Also gives access to drafts/rejected books. | V (views/books.py:94-106; permissions.py:39-99) |
| D4-I2 | H | Catalog list/detail/exports/reference lists show every non-deleted book regardless of state or review_state (draft, processing, needs_review, rejected) to every logged-in user, with `primary_source` URL on list rows. | V (shared.py:325-356) |
| D4-I3 | H | Reader token endpoints (manifest, EPUB, HTML) are unauthenticated; token only credential; no re-check of grant, user active, or read-once; tokens sit in `launch_url` query string (history, logs); 2 h refreshed on each launch; revoking access does not revoke live tokens. | V (models.py; token design) U for endpoints |
| D4-I4 | H | Preview HTML and HTML download are served unsanitised from the API origin (scraped content can run script); no CSP/nosniff. Profile image upload has no type/size validation (SVG active content). | U |
| D4-I5 | H | Demo login: GET with side effects, no credentials, ignores `is_active` and TOTP, committed default demo password in settings (value not reproduced here), shared account whose rights are whatever grants exist. | V (auth_and_password_views.py:160-184; settings.py:107-108) |
| D4-I6 | H | `is_staff` and `admin:full_control` are wildcards; `is_staff` also bypasses read-once; `admin:full_control` can be granted via API at account level. | V (permissions.py:27-36); API part U |
| D4-I7 | H | Soft-deleted books still downloadable, readable, Kindle-sendable and have tokens: access views look up `Book` by slug with no `deleted_at` filter; metadata edit/review views also include deleted books. | V for access; U for metadata |
| D4-I8 | M | Password-reset request exposes account existence via 404 (documented as intentional AU17). Validate/confirm/2fa-confirm/resend unthrottled; no per-user rate limit on OTP; reset confirm uses only length 12 without validators. | U |
| D4-I9 | M | 2fa/disable and 2fa/setup need no password or OTP re-auth; setup works while enabled (second device); verification uses first device with no ordering; secret returned raw. | U |
| D4-I10 | M | Read Once semantics are messy: consumed by HTML download too; staff never limited; record never reset when grants change; relaunch blocked even within live session; `user_has_scope` staff short-circuit makes durable always win for staff. | V partial (permissions.py:48-62); rest U |
| D4-I11 | M | Reset/invite links built from request Host when FRONTEND_BASE_URL is unset: password-reset poisoning. | U |
| D4-I12 | M | Owner not honoured by bookmarks/highlights/reading-session slug endpoints (inconsistent with launch). | V (shared.py:237-249) |
| D4-I13 | M | Duplicate-insert bugs return 500 instead of 400: SavedFilter (owner,target,name) and Bookmark (user,book,location) because serializers omit the unique-together fields. | U (DRF reasoning, not executed) |
| D4-I14 | M | Role+name filters (`author`, `translator`, `editor`) use chained `.filter()` on multi-valued joins, so role and name can match different contributors; `publisher` filter is correct. | U |
| D4-I15 | M | Search leaks other users' submission input text as catalog search hits unless `ownership=mine`. | U |
| D4-I16 | M | Catalog codes are not stable IDs (change when primary category/author changes); max+1 table scan, race, 65535/4095 capacity limits, weak 4-bit check, scramble constants in source. | U (R10 §4.1; CT10 confirms the encoding) |
| D4-I17 | M | Metadata edit: no transitions or locking; direct write of state/review_state; not transactional; two versions per edit even if unchanged; no snapshot retrieval/revert; publisher stored in two places (field and contributor) so they drift; PUT is silently partial. | U |
| D4-I18 | M | Admin user-management quirks: superusers editable/deactivatable by other superusers; `global_scopes` may be omitted entirely at create (no grants); search keyword hack (query "e" matches every active/disabled/required user); `sync_global_grants` leaves expired grants and duplicates. | U |
| D4-I19 | M | Grants cannot be edited after creation; no duplicate-grant check; no expiry UI path; reference endpoint dumps all users/books unpaginated. | U |
| D4-I20 | M | Kindle send: synchronous, whole EPUB in memory, no size cap (Kindle 50 MB limit not enforced), no throttle, API-key vs SMTP confusion with Brevo; forced SMTP. | U |
| D4-I21 | M | `AuditLog` model exists but is never written: no audit of grants, logins, downloads, Kindle sends, user deletion, TOTP changes. | U |
| D4-I22 | M | `missing_asset_response` mutates state on GET and a transient storage error can flip a book to needs_review. | U |
| D4-I23 | M | `ensure_book_reader_access`-protected annotation endpoints do not re-check on update/delete (fine) but nothing exports or deletes user data on account removal except cascade. | U |
| D4-I24 | L | Slug changes on rename with no redirects; slug fallback scans all books; `<path:slug>` catch-all route ordering sensitivity. | U |
| D4-I25 | L | Export: CSV formula injection unescaped; PDF fonts depend on host files (Bengali tofu on fallback); no row cap; `format` query name collides with DRF format override. | U |
| D4-I26 | L | Pagination contract changes shape depending on `page`/`limit`; different default limits (10 vs 60); page clamped. | U |
| D4-I27 | L | Performance: N+1 `has_epub_asset`, 6 joins for `q`, unbounded exports, whole EPUB zip reopened per resource request, whole HTML plus images in memory per preview request. | U |
| D4-I28 | L | Unrouted `RegisterView`; unused `user_owns_book` serialization; exec-stitched modules (`accounts/views.py`, seed command); duplicated helpers in audit modules with divergent behaviour; `--media-root` unused. | U |
| D4-I29 | L | `seed_e2e_data` has a hard-coded test password and no production guard (clears cache, deletes all CatalogCurationRun, resets processing); `repair_source_site_metadata` destructive by default; `source_site_batch_audit --cookie-header` puts a session cookie on the command line. `seed_superadmin` exits 0 on missing password. | U |
| D4-I30 | L | Doc mismatch: authentication-flows doc omits demo-login and csrf in the fence allow-list (code includes them). | V (middleware.py:5-16) |
| D4-I31 | L | Test fixture CT14 says any logged-in user can create manual books; code requires physical_books:view. Test or doc is wrong. | V (views/books.py:79) |
| D4-I32 | L | CSRF not enforced on unauthenticated login; no concurrent-session management; capability_scopes mixes scoped grants into global capabilities. | V for capability_scopes (accounts/models.py:131-140); rest U |

## 9. Keep / change / drop for a rebuild

### Keep (behaviour worth preserving)
- Invite-only onboarding by email link with password creation, 6 h expiry, single-use, newest-wins; resend for pending invites; TOTP enrolment as part of the invite when required. Reason: core to a private library; behaviour is covered by tests AU3-AU21.
- Scope-based grants with optional target (book / category / writer) and expiry; mutual exclusion of read-once and durable. Reason: this is the product's rights model.
- Forced-TOTP fence with allow-list; admin-required TOTP not self-disableable.
- Reader model: time-boxed opaque reader session, EPUB served as unzipped resources, manifest bundling annotation URLs, per-user reading position, bookmarks, highlights with kind (highlight|quote), colours, tags; "my notes" view with filters.
- Download filenames from current title; Kindle send with per-address result, SMTP, recorded last-send, Kindle address validation, sender shown for whitelisting.
- Ownership as a concept for the importer of a book (submitter), but not self-addable.
- Catalog: Bangla-aware punctuation-insensitive search, role-aware contributor dedupe, front-matter-derived contributors, flat categories/series, manual books, metadata versions and reviews, reference lists with counts, CSV/PDF export, deferred heavy columns in list responses (CT32).
- Soft delete with a defined restore path; asset self-heal idea (but not as a side effect on GET).

### Change
- Make ownership/My Books a pure bookmark-style "shelf" with NO access effect; compute access from grants and from an immutable importer relation set by the system. (D4-I1)
- Visibility: filter by book state and review state for readers (only published/approved to non-privileged users; privileged views for editors). (D4-I2, D4-I7)
- Reader tokens: bind to user and verify current rights on each request, or keep as short-lived signed bearer sent in a header/cookie, not in a URL; revoke on grant change; never log. (D4-I3)
- Serve user-supplied/scraped HTML only sanitised or in a sandboxed iframe on a separate origin with CSP; validate image uploads (type, size) and serve from a distinct origin. (D4-I4)
- Remove the demo-login as designed; if a demo is wanted, make it a read-only role with explicit seeded grants, POST-only, throttled, disableable. (D4-I5)
- Replace Django wildcards: staff flag dropped; define explicit roles (superadmin, admin/staff with named capabilities, reader) and drop `admin:full_control` as an API-grantable scope.
- Rebuild grants as editable, auditable records (history, deactivate, change expiry); unique constraint per (user, scope, target); reuse a single "effective permissions" function and surface scoped vs global capabilities separately.
- Read-once redesigned explicitly: choose what consumes the single read (e.g. reader launch only), per-user reset by admin, and clear semantics in the UI.
- Use stable opaque IDs for books/entities and keep catalog codes optional/derived and stable (assigned once, not recomputed from relations); allocate sequences in the database with a sequence or unique-retry.
- Throttle per user and per IP for all token-guessable endpoints (OTP, reset, resend, Kindle); require password or current OTP to disable or re-enrol TOTP; make 2fa device single; consider recovery codes.
- Password reset: uniform response for unknown email (or keep enumeration only if the owner prefers; the tests treated it as intentional, so confirm); apply the same password policy everywhere; never build links from request Host.
- Write an audit log for grants, user changes, logins, downloads, Kindle sends, TOTP changes.
- Pagination: one response contract (always `{items,page,...}` or cursor); one default limit; validate all enums and return 400.
- Metadata editing: transactional with optimistic locking, state transitions through the review workflow, version restore, soft-delete checks; keep the publisher in one place.
- Kindle send as a background job with size check, throttle, and status; do not mutate state during GET.
- Authorize book lookups by default (soft-deleted excluded) in every access/metadata endpoint.
- Fix filter semantics (one join for role+name), escape CSV fields, bundle PDF fonts in the app.

### Drop
- Hard-coded demo and E2E passwords, committed defaults for secrets.
- Unrouted register view, exec-stitched module pattern, duplicated audit helpers, unused options and annotations.
- Search over other users' submission text.
- Full-table reference dumps; unbounded exports without a cap (replace with streamed export).
- Slug fallback that scans all books (replace with stored legacy slugs/redirects).
- `staff` bypass flag; `Book` `edition`/`group` can stay out of catalog scope until ingestion design decides (not exposed today).

## 10. Open questions

1. Who is a "reader" operationally: do all invited users receive explicit grants, or should a default policy (e.g. read durable for all approved books) exist? Today an ungranted reader can read nothing except via the My Books loophole.
2. Is the My Books shelf intended to double as ownership? If ownership should remain for importers, should co-importers of the same title share it?
3. Should non-privileged readers ever see draft/needs_review/rejected books? Is the shared operator-and-reader catalog one view or two?
4. Keep the intentional account-enumeration on password reset (AU17), or move to a uniform response?
5. Demo account: still required (public preview)? If so, what may it do?
6. Read Once: exact consumption rule and whether admins can reset; is the legacy HTML-consumes-read behaviour wanted?
7. Should staff exist as a role separate from superadmin (editor, metadata-only, processing-only)? The legacy had `is_staff` as an accidental wildcard and no UI to set it.
8. Are catalog codes visible to users or used on physical labels (tickets PDF suggests yes)? If so they must be stable and printable; confirm the alphabet and length.
9. Per-category and per-writer grants: are they used in practice? They add real complexity (joins on each check).
10. Is the 2 h reader session length, and sending sessions in a URL, required by the frontend, or can reader auth move to cookie/header?
11. Kindle: domains other than kindle.com (e.g. regional kindle.com subdomains are rejected today); size limit; per-user daily limit?
12. Was the AuditLog ever written by other apps (ingestion/processing)? Not verified here.
13. Is `source_records:view` still needed as a separate scope, or folded into an editor role?
14. Which is authoritative on manual-book creation permission: tests (any user) or code (physical_books:view)?
15. Retention: what happens to annotations, progress and Kindle history when a user is deleted (today cascade-delete) and should user deletion export data first?
16. Profile images: needed at all for a private library?
17. Unverified paths worth a code check before design freeze: grant serializer validation (R09 #27), `sync_global_grants`, read-once recording in launch/download views, metadata views' deleted filter, `UserBook` signal in ingestion/models/submissions.py.


