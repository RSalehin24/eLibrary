Status: DRAFT

# X3 Roles, actions and permissions (cross-cutting synthesis)

Sources: digests D2 (ingestion), D3 (processing), D4 (accounts/access/catalog), D5 (frontend), D6 (reader). Evidence tags are inherited from those digests (VERIFIED = code line read by the digest author; UNVERIFIED = report-only). Everything under "PROPOSAL" is a recommendation for the rebuild, not a legacy fact. File content was treated as data.

## 1. Actors in the legacy app and what the code lets them do

There is no role field. Privilege = `is_superuser`, `is_staff`, plus `PermissionGrant` rows, plus `UserBook` ownership, plus possession of a reader token. (D4 s3)

| Actor | How identified | What the code actually lets them do |
|---|---|---|
| Anonymous | no session | Health, csrf, session probe, login, password reset request/validate/confirm, demo-login. In ingestion (AllowAny): create submissions (40/h throttle), poll status of up to 200 ids, view a public submission, confirm a title candidate, mint reader action-links (preview token, guest session allowed) for a public submission (D2 s3, s6 #2,3,4,6,7). Nothing else. |
| Demo | ordinary user row reached through GET `demo-login`, password from settings (committed default), ignores `is_active` and TOTP (D4-I5) | Same as an authenticated reader without grants, plus any grants an admin attached to the demo row. Can add any book to My Books and thereby become "owner" (D4-I1). Shared by everyone who clicks the demo link, so notes/bookmarks/progress/Kindle addresses are shared state. |
| Reader (authenticated, no grants) | `is_superuser=False`, `is_staff=False` | Read every non-deleted book in any state including drafts/rejected (D4-I2), reference lists, CSV/PDF export, tickets, saved filters, own profile/2FA, own notes/progress, My Books add/remove (no permission check), own submissions list/delete/retry/stop/resume. May view detail with `primary_source` URL. Cannot edit, cannot see source_records or raw provenance on the API (but UI may show "Raw Provenance" without check, D5 s4). Reader launch/preview/download only via ownership or grants. |
| Reader with grants | `PermissionGrant` active, optional expiry, target global/book/category/AUTHOR-contributor | Whatever the 12 scopes give (s3 below). Scoped grants only for 6 scopes. |
| Owner-by-My-Books | `UserBook(user, book)` row | Bypasses read-once, preview, download, cover, reader launch, Kindle gates for that book. NOT honoured by slug annotation endpoints (D4-I12). Row creatable by anyone for any non-deleted book (D4-I1). Intended meaning was "the person who imported it" (auto-link from own ready submission). |
| Reader-token holder | knows a `PreviewAccessSession.token` (2 h, refreshed on each launch) | Unauthenticated GET of manifest (with the user's bookmarks and highlights inlined), full EPUB, single zip entries, HTML preview. No re-check of grant, user active, or revocation. Writes (progress, bookmarks, highlights) additionally need login and session owner match. Token travels in a URL query string (D6 s3-4). |
| Manager / processing operator (`processing:manage`) | scope (global only) or staff | All ingestion/processing control: see all submissions/jobs, SSE, recover stale jobs, catalog entries CRUD, create books, catalog refresh, curation runs, automation settings, duplicate-review resolve, processing sync/pause/resume/stop, bulk request actions incl. delete-with-book, force_generate (D2 s3, D3 s3.1). Whole processing domain gated by one scope, reads included. |
| Staff (`is_staff`) | Django admin/seed only | Wildcard in `user_has_scope`: every scope, never read-once-limited, sees raw_provenance, source_records, manual books, edit/review/delete any book, manager rights. NOT a user admin (`IsSuperAdmin` = `is_superuser`). UI nav ignores staff for some links (D5 s4). |
| `admin:full_control` holder | grant (API can create it at account level, UNVERIFIED) | Wildcard in `user_has_scope` for any grant in range, matches every scope (D4-I6). Nav shows `/access` but page body refuses non-superusers. |
| Admin / superadmin | `is_superuser` | Users CRUD, resend setup email, grants CRUD and reference data, everything staff can do. Guards: cannot edit/delete self, cannot delete superusers, cannot create grants for self. Can edit/deactivate other superusers. |
| System / worker / scheduler | Celery beat, workers, engine, heartbeat, maintenance tick, `on_commit` projection committer, Redis mirror | Process jobs, sync catalog, create requests automatically, recover stale work, mark assets FAILED and books needs_review when a file is missing (side effect even on GET by any caller, D4-I22). Internal channels (worker:register/heartbeat/done, job:*) are unauthenticated Redis pub/sub (D2 s6). |
| Operator (CLI / Django admin) | shell access | `run_engine`, `process_legacy_batch`, `curate_source_site_books`, `seed_superadmin`, `seed_e2e_data` (destructive, hard-coded password, no production guard), `repair_source_site_metadata` (destructive by default), `backfill_multi_page_toc`; Django admin registers all 6 processing models without read-only protection (D3 s3.1, D4-I29). |
| Source site (external, not a user) | outbound HTTP target | Passive. Scraped content is untrusted; the app logs in to it with SOURCE_SITE_EMAIL/PASSWORD / cookie auth state. Its HTML ends up unsanitised in previews (D4-I4). Operator may need to refresh its auth cookie (D3-F53). |

## 2. Unified action inventory

Legend for "Legacy who": A anon, R any logged-in user, O owner, G grant (named), M manager (staff or processing:manage), S staff, SA superadmin, T token, SYS system. "Should" column is PROPOSAL (see s4 for role names: Reader, Curator, Operator, Admin, Owner-of-book, Service). Audit: Y = audit-worthy.

### 2.1 Session and account

| ID | Action | Legacy endpoint(s) | Legacy who | Should (PROPOSAL) | Data | Side effects | Audit |
|---|---|---|---|---|---|---|---|
| ACT-001 | Health / csrf / session probe | `GET /api/health/`, `csrf/`, `auth/session/` | A | A (health on internal port only) | none | cookie | N |
| ACT-002 | Login (password, optional OTP) | `POST auth/login/` (10/h IP) | A | A, per-account + IP throttle | session, user | session cookie; CSRF exempt | Y (success and failure) |
| ACT-003 | Demo login | `GET auth/demo-login/` | A, creates user, ignores is_active/TOTP | A but only if feature flag on; POST; read-only demo role | demo user row | session created on GET | Y |
| ACT-004 | Logout | `POST auth/logout/` | R | R | session | session end | N |
| ACT-005 | Password reset request | `POST auth/password-reset/` (5/h IP) | A; 404 enumeration | A; uniform response | token nonce | email, bumps nonce | Y |
| ACT-006 | Reset validate / confirm / first password set | `password-reset/validate`, `confirm` | A (confirm refused when logged in), unthrottled | A, throttled; apply password validators | password, nonce | may log in and return `next_step=totp_setup` | Y |
| ACT-007 | Read/edit own profile (name, image, password) | `GET/PATCH auth/profile/` | R | R; image type/size validated | user | password change keeps session | Y for password change |
| ACT-008 | Edit own Kindle addresses | `PATCH auth/profile/` | G send:kindle global (staff/SA pass) | R holding `kindle:send` | `kindle_emails` | none | N |
| ACT-009 | 2FA status / setup / confirm / cancel | `auth/2fa/*` | R | R | TOTP device, raw secret | provisioning URI + QR | Y (setup, confirm) |
| ACT-010 | 2FA disable | `POST auth/2fa/disable/` | R unless required; no re-auth | R unless required, with password + OTP | device | none | Y |

### 2.2 User and access administration

| ID | Action | Legacy endpoint(s) | Legacy who | Should | Data | Side effects | Audit |
|---|---|---|---|---|---|---|---|
| ACT-020 | List/search users | `GET auth/users/` | SA | Admin | users | none | N |
| ACT-021 | Create / invite user | `POST auth/users/` | SA | Admin | user, global grants | invite email; rollback on mail failure | Y |
| ACT-022 | Edit / activate / deactivate user | `PUT/PATCH auth/users/<id>/` | SA (not self; can edit other SAs) | Admin; not self; superadmin changes need second admin or break-glass | user, global grants | `sync_global_grants` hard-deletes grants | Y |
| ACT-023 | Delete user | `DELETE auth/users/<id>/` | SA (not self, not superusers) | Admin; soft-delete plus data export/erasure flow | user cascade | cascades notes, bookmarks | Y |
| ACT-024 | Resend setup email | `POST users/<id>/resend-setup-email/` | SA | Admin | nonce | email; kills old links | Y |
| ACT-025 | Create grant | `POST access/grants/` | SA (not for self) | Admin; two-person for wildcard | grant | none | Y |
| ACT-026 | Delete/revoke grant | `DELETE access/grants/<uuid>/` | SA (not self) | Admin; revocation also revokes live tokens | grant | none today | Y |
| ACT-027 | List grants / reference data | `GET access/grants/`, `references/` | SA | Admin, paginated | all users/books | none | N |
| ACT-028 | Edit grant expiry / active | none (write-once) | nobody | Admin (PATCH) | grant | | Y |

### 2.3 Catalog and metadata

| ID | Action | Legacy endpoint(s) | Legacy who | Should | Data | Side effects | Audit |
|---|---|---|---|---|---|---|---|
| ACT-030 | List/search/filter books | `GET catalog/books/` | R, all states | R sees only published/ready; Curator sees all | book, flags | none | N |
| ACT-031 | Book detail | `GET catalog/books/<slug>/` | R; source_records need grant; raw_provenance staff | R (published); source/provenance fields Curator | book | | N |
| ACT-032 | Reference lists (categories, series, writers...) | `GET catalog/<ref>/` | R | R | counts | | N |
| ACT-033 | Export CSV/PDF, tickets | `catalog/books/export/`, `tickets/` | R, unbounded, no formula guard | R with row cap and escaping | book list | CPU load | Y for bulk export |
| ACT-034 | Add/remove My Books | `POST/DELETE books/<slug>/my-books/` | R, any book, no check | R may shelve a book; shelving grants NO access | UserBook | grants owner bypass today | N once decoupled |
| ACT-035 | Manual (physical) books list | `GET manual-books/` | G physical_books:view | Curator | manual book | | N |
| ACT-036 | Create manual book | `POST manual-books/` | G physical_books:view | Curator | book, contributors | code assigned | Y |
| ACT-037 | Edit metadata | `PATCH/PUT books/<slug>/metadata/` | G metadata:edit (scoped) | Curator, scoped | book, contributors, state | 2 version rows, slug and code change | Y |
| ACT-038 | Upload/replace EPUB | `POST books/<slug>/assets/epub/` | G metadata:edit | Curator | asset | slug may change | Y |
| ACT-039 | Regenerate assets | `POST books/<slug>/regenerate/` | G metadata:edit | Curator | job | job queued | Y |
| ACT-040 | Metadata review create/update | `books/<slug>/metadata-reviews/`, `metadata-reviews/<uuid>/` | G metadata:edit | Curator (reviewer distinct from last editor) | review, review_state | sets book state | Y |
| ACT-041 | List metadata versions | `books/<slug>/metadata-versions/` | G metadata:edit | Curator | versions | | N |
| ACT-042 | Soft delete book | `DELETE books/<slug>/` | G metadata:edit (scoped) | Curator; destructive path Admin | deleted_at | book still reachable via access endpoints (D4-I7) | Y |
| ACT-043 | Restore deleted book | none | nobody | Admin | | | Y |
| ACT-044 | Saved filters CRUD | `saved-filters/` | R own | R own | filter | | N |

### 2.4 Reading, downloading, annotation

| ID | Action | Legacy endpoint(s) | Legacy who | Should | Data | Side effects | Audit |
|---|---|---|---|---|---|---|---|
| ACT-050 | View cover | `books/<slug>/download/cover/` | O, or G any of preview/read/download/read-once, read-once-spent loses it | R for published books (covers are public metadata) | asset | self-heal on missing | N |
| ACT-051 | HTML preview | `download/html/`, `reader/<token>/html/` | O or G preview:html; unsanitised | Reader with `book:preview`, sandboxed origin plus CSP | asset | consumes read-once | Y if read-once |
| ACT-052 | Launch reader (mint token) | `POST books/<slug>/reader-launch/` | O or G (4 scopes); read-once limit | Reader with `book:read` on that book | session, BookOpeningRecord | token created, 2 h, URL query | Y |
| ACT-053 | Fetch manifest / EPUB / HTML by token | `GET reader/<token>/manifest|epub|html/` | T (anonymous) | T bound to user, device-agnostic but re-checked (grant, active, not revoked), header not URL | assets, user notes | self-heal on GET | Y (EPUB fetch counts as read/download) |
| ACT-054 | Download EPUB/file | `download/epub/` | O or G download:file | Reader with `book:download` | file | filename from title | Y |
| ACT-055 | Send to Kindle | `POST books/<slug>/send-to-kindle/` | O or G send:kindle | Reader with `book:kindle` | UserBookKindleSend | outbound email with attachment, synchronous | Y |
| ACT-056 | Save reading position | `reader/<token>/session/`, `books/<slug>/reading-session/` | login + token owner; slug twin needs read access | R with read access | ReadingSession | | N |
| ACT-057 | Bookmark create/list/delete | `reader/<token>/bookmarks/`, slug twin, `bookmarks/<uuid>/` | login + token owner; delete own with no access check | R own rows; no access needed to delete own | Bookmark | duplicate gives 500 | N |
| ACT-058 | Highlight/note create/update/delete | `reader/<token>/highlights/`, slug twin, `highlights/<uuid>/` | same | same | Highlight | | N |
| ACT-059 | My notes / reading progress | `me/notes/`, `me/reading-progress/` | R own | R own, paginated | notes | | N |

### 2.5 Ingestion and processing

| ID | Action | Legacy endpoint(s) | Legacy who | Should | Data | Side effects | Audit |
|---|---|---|---|---|---|---|---|
| ACT-070 | Submit URL/title request | `POST ingestion/submissions/` | A (40/h) | R (invited users) only; anonymous submission dropped | submission, job | scrape of source site, attach to canonical duplicate | Y |
| ACT-071 | Poll status / view submission | `submissions/status/`, `submissions/{id}/` | A (public ones) | R own, Operator all | submission | | N |
| ACT-072 | Confirm title candidate | `submissions/{id}/confirm-candidate/` | A with access check | R own | submission | queues job | Y |
| ACT-073 | Mint reader action-links from a submission | `submissions/{id}/action-links/` | A for public (guest session) | R own, or removed | preview session | guest token | Y |
| ACT-074 | List own submissions/jobs | `submissions/`, `jobs/`, `activity/` | R (managers all) | R own, Operator all | | | N |
| ACT-075 | Delete / bulk-delete / retry / bulk-retry own submission | `submissions/{id}`, `bulk-delete`, `retry`, `bulk-retry` | R (visibility-based, bulk diverges from single) | R own; one rule everywhere | submission | acts on canonical root, so can affect other users' dependents | Y for delete |
| ACT-076 | Stop / resume / delete job, view logs | `jobs/{id}/stop|resume`, `bulk-*`, `logs/` | R + can_manage_job (submitter or manager) | R own, Operator any | job | | Y (manager acts on others') |
| ACT-077 | Job SSE, reprocess summary, recover stale jobs | `jobs/stream/`, `reprocess/summary/`, `jobs/recover/` | M | Operator | jobs | | Y (recover) |
| ACT-078 | Catalog entries list/delete/bulk-delete/create-books | `catalog/entries/*` | M | Operator | catalog entry, request | creates requests, scraping | Y |
| ACT-079 | Catalog refresh start/stop, incomplete-check, create-books | `catalog/refresh/`, `incomplete-check/*` | M | Operator | catalog | crawl of source site | Y |
| ACT-080 | Curation runs create/stop/delete | `catalog/curation-runs/*` | M | Operator | run | bulk book creation | Y |
| ACT-081 | Automation settings get/patch | `catalog/automation/`; processing `automation/*` | M | Operator; Admin for schedule | settings | recurring scrape | Y |
| ACT-082 | Duplicate review list/resolve | `duplicate-reviews/*` | M | Curator (decision), Operator | review, book links | fulfils or re-queues | Y |
| ACT-083 | Processing sync start/pause/resume/stop, records create-requests, bulk request action (delete+book, force_generate, new_edition...) | processing `sync/*`, `records/create-requests`, `requests/action` | `processing:manage` / staff | Operator; delete-with-book and force_generate Curator+Operator | request, record, book | bulk book create/delete, review gate bypass | Y |
| ACT-084 | Source-site cookie refresh | out of band | operator | Operator via secret store | credential | | Y |

### 2.6 System and operator

| ID | Action | Legacy | Legacy who | Should | Audit |
|---|---|---|---|---|---|
| ACT-090 | Run job / pipeline / catalog sync / curation / automation tick | Celery tasks, engine | SYS | Service identity per worker | Y (job outcome) |
| ACT-091 | Recover stale jobs, repair self-linked duplicates | beat tasks | SYS | Service | Y |
| ACT-092 | Self-heal missing asset (mark FAILED, book needs_review) | any asset GET | any caller incl. token holder (D4-I22) | Service only, never from a read | Y |
| ACT-093 | Worker register / heartbeat / done / job assign | Redis pub/sub channels | unauthenticated bus | Authenticated service-to-service | Y (register) |
| ACT-094 | Seed superadmin, e2e seed, repair/backfill/audit commands | management commands | shell | Operator break-glass, prod guard, dry-run default | Y |
| ACT-095 | Test hooks (`remotePages`, advance endpoints) | processing | test settings (UNVERIFIED outside) | not shipped | n/a |

## 3. Legacy permission scopes and grant model

### 3.1 The 12 scopes (D4 s4.1, apps/access/models.py:18-30 VERIFIED)

| Scope | Meaning in code | Account-manageable | Target-scopable |
|---|---|---|---|
| submit:create | implicit for every user; ingestion decides | no | no |
| preview:html | HTML preview; also qualifies reader launch and cover | yes | yes |
| read:durable | reader launch repeatedly | yes | yes |
| read:once | single open (shared HTML+reader counter) | yes | yes |
| download:file | EPUB/file download; qualifies launch/cover | yes | yes |
| send:kindle | Send to Kindle and edit Kindle addresses (global for the profile) | yes | yes |
| metadata:edit | edit/review/version/delete/replace EPUB/regenerate; scoped | yes | yes |
| physical_books:view | list and create manual books | yes | no |
| processing:manage | whole processing/ingestion manager surface | yes | no |
| access:manage | listed in UI nav; page itself requires `is_superuser` (dead scope for real power) | yes | no |
| source_records:view | source_urls/source_records on detail | yes | no |
| admin:full_control | wildcard; matches every scope | no (but API may create it, UNVERIFIED) | no |

### 3.2 Grant model

- `PermissionGrant(user, scope, book | category | contributor, is_active, expires_at, notes, granted_by)`. One target at most. Active = is_active and not expired. Evaluation with a book: global OR that book OR any category of the book OR an AUTHOR-role contributor of the book (translator/editor grants never match). Without a book: global grants only.
- `user_has_scope`: anonymous false; superuser or staff true; else any matching active grant; `admin:full_control` matches every scope. Owner rule is a second, separate route (`user_owns_book`).
- Read-once and read-durable are exclusive only on the exact same target. Read-once is tracked by permanent `BookOpeningRecord`.
- Grants are write-once (no PATCH). `sync_global_grants` (user form) hard-deletes deselected global grants and leaves expired duplicates. Superadmin cannot grant to self.
- `capability_scopes` sent to the UI mixes scoped and global grants, so the UI can show global capability the server will refuse.

### 3.3 Loopholes found

| # | Loophole | Evidence | Effect |
|---|---|---|---|
| L1 | Owner self-grant: any user POSTs `my-books` for any non-deleted book and becomes owner | D4-I1, V | Bypasses every download/preview/launch/Kindle/read-once gate; access control is cosmetic; also exposes drafts/rejected books |
| L2 | Wildcards: `is_staff` and `admin:full_control` pass every scope; staff bypass read-once; staff not user-admin but everything else | D4-I6, V | Unbounded power by one flag; `admin:full_control` creatable through grants API at account level (UNVERIFIED) |
| L3 | Demo login: GET, no credentials, committed default password, ignores is_active and TOTP, user auto-created | D4-I5, V | Free authenticated session for anyone; combined with L1 gives every book. Shared mutable account |
| L4 | Token-only reader routes: manifest/epub/html are AllowAny with the bearer token in a URL; no grant, active-user or revocation check; 2 h refreshed on launch | D4-I3, D6 s4.3 | Revoking a grant or disabling a user does not stop reading; token leaks via history/logs/referrer; read-once relaunch blocked but live token continues; reading equals full download so `download:file` is not content protection |
| L5 | Anonymous ingestion: create submissions, confirm candidates, mint reader action-links with guest session (null user) | D2 s3 | Unauthenticated scraping of the source site and token minting for "public" submissions; throttle only 40/h |
| L6 | Catalog visibility ignores state/review_state | D4-I2, V | Drafts, processing, needs_review, rejected shown to all users with source URL |
| L7 | Soft-deleted books still downloadable/readable/Kindle-sendable; metadata views include deleted | D4-I7 | Delete is not a withdrawal |
| L8 | Annotation endpoints inconsistent: owner blocked on slug twins; own delete/update never rechecked | D4-I12 | Confusing rules; users keep data after losing access (fine) but no data export/erasure |
| L9 | Read-once weaknesses: HTML download consumes it; staff never limited; never reset; durable wins on conflicting grants | D4-I10 | Unpredictable semantics |
| L10 | UI capability sources disagree (hasCapability vs navigation.js vs AccessPage); nav shows pages the server then refuses; routes reachable by URL | D5 s4 | Authorisation only in server, inconsistent |
| L11 | Processing surface gated by one scope; bulk endpoints use visibility rules while single use `can_manage_job`; retry on a non-visible id gives 500; actions on canonical root affect other users' dependents | D2 s4.5, D2 s6 | Cross-user effects; coarse manager rights; delete-with-book from one scope |
| L12 | Grant admin gaps: no duplicate check, no edit, self-block only, superadmins editable by other superadmins, `access:manage` is a no-op scope | D4-I18,19 | Weak admin governance |
| L13 | Unauthenticated worker bus and test hooks (`remotePages`, advance routes), destructive seed/repair commands without prod guard | D2 s6, D3 s3.2, D4-I29 | Internal trust boundary absent |
| L14 | Missing-asset self-heal mutates state on any GET by any token holder | D4-I22 | Anyone with a token can flip a book to needs_review |
| L15 | Unsanitised HTML preview on API origin, profile image uploads unvalidated | D4-I4 | XSS from scraped content on the app origin |
| L16 | No audit: `AuditLog` model never written | D4-I21 | No record of grants, logins, downloads, Kindle sends, deletes |
| L17 | Account enumeration on reset, unthrottled OTP/confirm/resend, no re-auth for 2FA disable | D4-I8,9 | Auth hardening gaps |

## 4. PROPOSAL: clean permission model for the rebuild

All of this section is a proposal for owner decision. Reasons name the legacy defect (Lx) each point fixes. Fits the planned Rust services (identity, access, catalog, content, library, ingestion, notify) plus gateway.

### 4.1 Roles (coarse, assigned per user, stored once in identity)

| Role | Purpose | Replaces |
|---|---|---|
| Reader | default invited member: browse published books, shelve, annotate, own profile, submit requests | authenticated user with no grants |
| Curator | edit/review/delete metadata, manual books, resolve duplicate reviews, regenerate assets | `metadata:edit`, `physical_books:view`, `source_records:view` |
| Operator | run ingestion, sync, automation, recover jobs | `processing:manage` |
| Admin | users, roles, grants, audit view | `is_superuser` for user admin |
| Demo (optional, flag) | read-only showcase | demo-login |

Why: a role bundle replaces `is_staff` plus a bag of scopes, no role is a wildcard (L2). Roles combine; no "superuser flag". A break-glass owner account exists outside the app (CLI, audited).

### 4.2 Scopes (action-level, checked by the service that owns the resource)

Namespace `resource:action`. Roles map to scope sets in identity; services check scopes in the verified token plus resource rules; no wildcard scope exists.
- `catalog:read`, `catalog:read_unpublished`, `catalog:export`
- `metadata:edit`, `metadata:review`, `book:delete`, `book:restore`, `manual_book:write`, `asset:replace`, `asset:regenerate`, `source_record:read`
- `book:preview`, `book:read`, `book:download`, `book:kindle`
- `ingest:submit`, `ingest:operate`, `ingest:automation`, `duplicate:resolve`
- `user:admin`, `grant:admin`, `audit:read`

Reasons: removes dead `access:manage` and `submit:create` (L12), splits read/preview/download so rules can differ (L4: reading is a download in practice, see Q-X3-4), separates `metadata:review` from `metadata:edit` and `ingest:operate` from `duplicate:resolve` (L11).

### 4.3 Grants (per-book and per-category exceptions, not the main mechanism)

- Default content access comes from the role (Reader gets `book:read` on all published books) so the grant table is the exception list, not the permission system. Grant = (user, scope, target {global|book|category|author}, expires_at, granted_by, reason). Restrictive and additive grants are both possible only if the owner wants per-book restriction (Q-X3-3).
- Grants are editable (expiry, active), duplicate-checked, created by Admin only, never for self, and never for `grant:admin`/`user:admin`. Change history is an audit event. (L12)
- Revoking a grant or deactivating a user triggers immediate token revocation (4.7) (L4).
- Read-once: keep only if the owner still wants it (Q-X3-4); if kept, one explicit counter per (user, book, grant) with a reset action and no cross-use of HTML preview (L9).

### 4.4 Ownership rule

- "Owner" means only: the user whose own submission produced or was linked to that book. It is set by the ingestion/library service server-side, never by a client call. It grants read/download/Kindle for that book (and nothing administrative). (L1)
- My Books becomes a pure shelf: add/remove never changes access. A reader can shelve only books they can already read.
- Owner rights are honoured consistently by every endpoint (cover, preview, reader, download, Kindle, annotations). (L8)
- Owner status ends if the book is withdrawn (soft-deleted/unpublished). (L7)

### 4.5 Visibility and deletion

- Catalog list/detail/search/export show only published and non-deleted books to Reader; unpublished states only with `catalog:read_unpublished`. Source URLs only with `source_record:read`. (L6, D4-I15 search leak)
- Every access path (token, download, Kindle, annotations) rejects soft-deleted books. (L7)

### 4.6 Demo account limits

- Off by default; enabled by an explicit config flag; separate role Demo with read-only scopes: `catalog:read` on a fixed demo set of books (public-domain or owner-authored only), no download, no Kindle, no submit, no notes persistence beyond a per-session store, no profile edits.
- Issued per session (ephemeral demo identity, expiring), POST not GET, throttled, no committed password, honours disable switch. (L3)
- Cannot shelve into My Books; no elevation by ownership.

### 4.7 Reader token handling

- Reader launch requires a logged-in user and re-evaluates scope at launch. The token is a short-lived, single-user, single-book capability that is (a) minted server-side, (b) bound to user and book, (c) sent in an Authorization header or HttpOnly same-site cookie scoped to the content origin, never in a URL query, (d) re-validated on every request against active user, grant/ownership and revocation list, (e) revoked on grant removal, user disable, password change and logout, (f) not extended automatically by relaunch beyond a cap, with a refresh endpoint the client can call. (L4)
- No anonymous token minting: ingestion action-links for anonymous guests are removed (L5, Q-X3-1).
- Content (preview HTML, EPUB resources) served from a sandboxed content origin with CSP, nosniff, and sanitised HTML. (L15)
- Fetching an asset never mutates state; missing-asset repair is a service-side job. (L14)
- Every token mint and full-EPUB fetch is an audit event with user, book, IP/UA hash. (L16)

### 4.8 Service-to-service authentication

- Gateway authenticates users (session cookie, CSRF) and forwards a signed internal identity (user id, roles, scopes, request id) to services; services never trust client-supplied identity headers. Each service re-checks scopes for its own resources (defence in depth).
- Workers and services use workload identities (mTLS or signed service tokens with audience and short lifetime), each with a minimal scope set (`ingest:work`, `content:write`, `notify:send`). The job bus (Redis or NATS) requires authentication and per-channel ACLs. (L13)
- No test hook, seed, or advance endpoint compiled into production builds; destructive CLI commands refuse to run in production without an explicit flag and default to dry-run. (L13)
- Outbound scraper credentials (source-site login, cookie state) live in the secret store, read only by the ingestion worker identity.

### 4.9 Other fixes tied to defects

- Server returns one resolved capability set (`/me/capabilities`) that drives nav, route guards and server checks; the UI derives all gates from it. (L10)
- Admin cannot modify own roles; changes to another Admin require a different Admin; at least one break-glass account exists. (L12)
- Single rule for visibility and control of ingestion submissions and jobs (own = submitter, otherwise `ingest:operate`); bulk and single share one policy; unknown or invisible ids return 404 not 500. (L11)
- Throttle every unauthenticated or secret-bearing endpoint (login, reset, confirm, OTP verify, resend, Kindle send). (L17)
- 2FA disable and secret reveal require re-authentication. (L17)
- Soft delete means withdrawal everywhere; restore is an Admin action. (L7)

## 5. Sensitive actions that must be audited (PROPOSAL)

Record actor (user or service), subject, before/after where relevant, time, request id, IP and user agent hash. Append-only.

1. Login success/failure, lockout, logout, demo session issued (ACT-002/003).
2. Password reset request/confirm, password change, email change (ACT-005/006/007).
3. 2FA setup, confirm, disable (ACT-009/010).
4. User create, invite, resend, edit, activate/deactivate, delete, role change (ACT-021 to 024).
5. Grant create, change, revoke, expiry (ACT-025 to 028), including who and why.
6. Reader token mint, token refresh, token revocation, EPUB/HTML/cover full fetch, download, Kindle send with addresses (ACT-052 to 055); read-once consumption and reset.
7. Metadata edit/review/delete/restore, EPUB replace, regenerate, manual book create, force-publish or state override (ACT-036 to 043).
8. Duplicate-review decisions and delete-with-book in ingestion (ACT-082, 083).
9. Bulk operations: bulk delete/retry/stop, create-requests, curation runs, catalog refresh, automation setting changes, recover jobs (ACT-075 to 081).
10. Bulk export (rows count, filters) (ACT-033).
11. Anonymous or invited submission creation and candidate confirmation (ACT-070, 072).
12. Service actions with external effect: scrape start/finish, missing-asset detection, worker register/deregister, stale recovery (ACT-090 to 093).
13. Operator CLI/break-glass commands and secret changes (ACT-084, 094).
14. Account data export or erasure (new).

## 6. Open decisions for the owner

To be asked through AskUserQuestion when the owner reviews this document; recommendation first. Not yet decided.

| ID | Question | Options | Recommendation and why |
|---|---|---|---|
| Q-X3-1 | Keep anonymous ingestion (submit, confirm, action-links, guest tokens)? | (a) invite-only members submit; (b) keep anonymous with captcha/quota; (c) anonymous submit but no reader links | (a): the library is private invite-only, closes L5; legacy anonymous path is an unauthenticated scraper |
| Q-X3-2 | Demo account: keep, and how? | (a) drop; (b) feature-flagged ephemeral read-only role on a fixed demo set; (c) keep legacy behaviour | (b) if a showcase is wanted, otherwise (a); (c) is L3 |
| Q-X3-3 | Content access default | (a) every Reader reads all published books, grants only for exceptions; (b) per-book grant required; (c) category-level default | (a): matches a private invite-only library and shrinks the grant surface; confirm that the legacy grant-per-book intent is not needed |
| Q-X3-4 | Keep read-once and the separate preview/read/download/Kindle scopes? | (a) keep read/download/Kindle, drop read-once and preview as separate scope; (b) keep all; (c) single `book:access` | (a): reading delivers the full EPUB anyway so read-once and download gates are not content protection (D6 s4.4); simplifies |
| Q-X3-5 | Ownership meaning | (a) only the importer through own ingestion; (b) any shelving grants access (legacy); (c) none, grants only | (a): fixes L1 yet keeps the intended behaviour |
| Q-X3-6 | Role set | (a) Reader/Curator/Operator/Admin; (b) just Reader/Admin plus grants; (c) keep staff/superuser flags | (a): separates curation from operations without wildcards |
| Q-X3-7 | Who may see unpublished/draft/needs_review books | (a) Curator and Operator only; (b) everyone as legacy; (c) submitter plus Curator | (c) or (a); (c) lets members follow their own request, recommend (c) |
| Q-X3-8 | Reader token transport and lifetime | (a) HttpOnly cookie on content origin, 2 h sliding with cap, revoke on disable/revoke; (b) header bearer; (c) legacy URL token | (a): fixes L4 without breaking the iframe/epub.js flow; confirm the reader is on a separate origin |
| Q-X3-9 | Superadmin governance | (a) one Admin role, cannot self-edit, another Admin edits Admins, break-glass CLI; (b) two-person approval for wildcard-type changes; (c) legacy | (a): proportionate for a small team |
| Q-X3-10 | Audit scope and retention | (a) all items in s5, append-only, kept 1 year; (b) security events only; (c) none | (a): the legacy `AuditLog` was never written (L16), items in s5 are the minimum to investigate misuse |
| Q-X3-11 | Account data lifecycle | (a) soft-delete users with export/erasure of notes; (b) cascade delete (legacy); (c) keep everything | (a): legacy cascade silently destroys annotations (D4-I23) |
| Q-X3-12 | Kindle addresses and sending | (a) any Reader with `book:kindle`, queued async with size cap and rate limit; (b) grant per user as legacy; (c) drop Kindle | (a) if Kindle remains in scope; legacy was synchronous and unbounded |
| Q-X3-13 | Service-to-service trust | (a) gateway-signed identity plus mTLS/signed service tokens and authenticated bus; (b) network isolation only | (a): defence in depth; (b) repeats L13 |
