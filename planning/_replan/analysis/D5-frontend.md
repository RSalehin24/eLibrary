Status: DRAFT

# D5 - Legacy frontend analysis (for the Rust + Angular Material rebuild)

Sources: reports 11 (features/api/utils), 12 (pages/components/processing), 16a (E2E tests), 16b (unit tests), cited as R11 section/line, R12 section, E<n> (16a), U<n> (16b). Code under `archive/app/frontend/src` (abbrev. `src/`) was spot-checked where claims were crucial; each is marked VERIFIED (read in code, file:line) or UNVERIFIED (report only). Legacy stack: React + react-router v6 + Vite, hand-rolled hooks, plain `fetch`, Django session cookie + CSRF.

## 1. Purpose and scope

Legacy UI serves three audiences of a private, invite-only Bengali ebook library:
- Reader (invited user): browse the catalog, keep a "My Books" shelf, open the in-browser EPUB reader, bookmark/highlight/note/quote, send EPUB to Kindle, manage own profile/2FA/Kindle addresses. (R11 3.4, 3.5; R12 2.1-2.8)
- Operator / super admin: invite and manage users, grant scoped access, edit book metadata and review state, curate physical (manual) books, export lists. (R11 3.3, 3.4, 3.6)
- Operator (processing): import from one source website via a request pipeline: sync catalog records, create requests, watch queue/processing/created/on-hold/incomplete/multipage/reprocessing, automation schedules. (R12 3)

Scope of this document: every screen, action, state, API call, client-state rule and defect found in those four reports, with the rebuild decision per item. Out of scope: backend internals, the embedded reader engine internals (`features/reader/*`, `embedded-reader/`, not covered by the reports beyond launch/manifest), CSS.

Reports did not read: `features/reader/*`, `styles/`, `embedded-reader/`, `pages` wiring for `useBookDetailData` and `useBookDetailActions` beyond call sites (R12 1, 7). Reader behaviour is therefore thin in this analysis (see Open questions).

## 2. Screens and routes inventory

Route table VERIFIED at `src/features/app/AppRoutes.jsx:37-62, 77-127`. Guard: `ProtectedRoute` only checks authenticated + forced TOTP (`src/features/app/ProtectedRoute.jsx:5-37`, VERIFIED). No route has a role/capability guard (VERIFIED: protectedRoutes list wraps every element identically, AppRoutes.jsx:64-72). "Who" below = who the NAV shows it to / who the page logic permits; true authority is the server (403).

Shell-wide behaviours (R11 3.0): skip-link; topbar hidden on `/reader` unless `appNav=shown`; minimal topbar on `/create-password` and `/two-factor-setup`; profile menu (avatar, Profile, Alerts switch, Sign Out); mobile drawer below ~981px (R11 3.0 says "viewport >=981px" closes it; E180 tests suggest switch between 821 and 1024, so ~980 consistent); floating ThemeToggle and ScrollToTopButton; BackendStatusModal; ErrorBoundary; route-change scroll reset.

Legend for states: L = loading, E = empty, X = error.

### 2.1 Public / auth screens

| Route | Who | Shows | Actions | States |
|---|---|---|---|---|
| `/login` | anyone; authenticated visitors are redirected | Heading "Sign in"; email, password, then TOTP step | Submit "Continue" (disabled until valid email + password; becomes "Verify" in OTP phase); show/hide password; "Change account"; link "Reset password". Server code `otp_required` switches to OTP phase, `otp_invalid` stays with error toast. Post-login redirect: `totp_setup_required` -> `/two-factor-setup`, else superuser `/home`, others `/my-books`. (R12 2.11; E30-E32) | live email feedback ("Enter a valid email address." / "Email looks good."); must not poll processing state or show restart toast (E32) |
| `/demo-login` | anyone | Spinner; calls `GET /auth/demo-login/` then session refresh, redirect by role | none; failure toast + `/login` (R12 2.11) | L only |
| `/reset-password` | anyone | Email form, heading "Reset your password" | "Reset Password" (disabled until valid email); if URL has `uid`+`token` redirects to `/reset-password/confirm`; shows server `detail` (E34). Test shows 404 "No user exist with this email." displayed verbatim: user enumeration | - |
| `/reset-password/confirm?uid&token` | anyone (logged-in user sees "Log out first") | Heading "New password"; fields New/Confirm | Validates link on mount; submit "Reset password"; success `next_step` login -> `/login`, `totp_setup` -> refresh session + `/two-factor-setup` (E35, E38) | invalid/expired -> heading "The link has expired", no form |
| `/create-password?uid&token` | invitee | Heading "Create password"; same form | POST confirm with `{uid,token,new_password}` only (confirm matched client-side) (E36); needs 12+ char password (server rule, E15/E37) | expired: "The link has been expired" (copy differs from reset, E39) |
| `/two-factor-setup` | authenticated with `totp_setup_required` | QR (server SVG), secret, setup URL + copy, 6-digit token | "Verify and Continue"; "Prepare setup" retry if the first call fails; no Cancel (required mode); then to `location.state.from` or `/home` (R12 2.11) | minimal topbar; non-required user is redirected away |
| `*` and legacy aliases | anyone | n/a | `/created-books -> /my-books`, `/compilers -> /editors`, `/processing*` -> `/catalog`/`/create`/`/on-hold`/`/incomplete`, `/queue -> /create`, `* -> /` (VERIFIED AppRoutes.jsx:52, 87-127) | - |

### 2.2 Reader-facing screens

| Route | Who | Shows | Actions | States |
|---|---|---|---|---|
| `/my-books` ("My Books") | every user; superuser home is `/home` | Card grid of own shelf; defaults `ownership=mine`, `sort=-requested_at`, `record_type=digital`; search "Search your books by title or book ID..." (R12 2.3; E68) | search, sort (newest/oldest request, newest/oldest book, title A-Z/Z-A), filter drawer (Author, Series, Category, Type), remove from My Books (X on card), Send to Kindle, Open record | 6 skeleton cards initial/6 incremental; E "No books found / Adjust the search or filters." (no clear button); X panel `.page-state-error`; filter drawer open state not persisted |
| `/home` ("All Books") | superuser's home; others reach it via "All Books" link (R11 4) | Card grid of whole digital catalog; search "Search all books by title, book ID, or writer..." | search, sort (4 options), filters: Contributor, Series, Category (cross-filtered), Ownership (All/My books), Type; My Books toggle; Send to Kindle; Open record. Drawer state in sessionStorage `filters-expanded:home` | as above plus "Clear all filters" button when filters differ from defaults |
| `/library` ("Books") | all authenticated (Book Properties menu) | Table of books (Book ID, Title, Contributors, Category, Series, Type, Created, My Books, Open); phone = cardified rows | search, sort (8 options incl. catalog code, request date), filter drawer (Contributor, Series, Category, Ownership, Type), CSV and PDF export of ALL matches, saved-filter chips (apply/delete, no confirm), My Books Add/Remove | skeleton rows 5/5; resume of an interrupted export after reload (R12 2.2); `GET /saved-filters/?target=catalog` |
| `/kindle-sent` ("Kindle") | nav shows to `admin:full_control` or `send:kindle` holders; superuser via session box (R11 4) | Card grid of books user sent; defaults `kindle_sent=mine`, `sort=-sent_at` | search, sort, filters Author/Series/Category/Type, My Books toggle, resend to Kindle | E "You haven't sent any books to Kindle yet." even when a filter caused it (R12 2.4) |
| `/books/:slug` | all authenticated | Digital book: hero (Book ID or "Pending", title, contributor links, series/category filter links, state + review pills), reading progress, bookmarks/notes/annotations/quotes cards, Source Records (cap `source_records:view`), Entities and Details, Dedication, Table of Contents, empty chapters list, metadata workspace (cap `metadata:edit`), "Raw Provenance" JSON. Manual book: spec grid + "My Reading Log" | See 3.x features; editors also Regenerate, Delete, Edit book, Replace/Upload EPUB, Save metadata, review form, Approve/Reject (R11 3.4; R12 2.7) | `BookDetailSkeleton`; X `.page-state-error`; processing note while job active; page polls 4 s while job queued/processing (R11 API #37) |
| `/reader?slug&manifest&appNav` | readers with reader access (`can_launch_reader`) | Embedded EPUB reader; topbar hidden by default, floating "Hide reader header"; own Settings, TOC, themes (E53) | Launch comes from book detail via `POST /access/books/{slug}/reader-launch/`; back to `/books/{slug}` | `PageLoader variant=reader`, `ReaderUnavailable`; reader internals not covered |
| `/notes` ("My Notes") | all authenticated | Two-column master/detail: books list grouped by `book_slug` (left), items (right); four tabs Bookmarks, Notes(API highlights), Annotations(API notes), Quotes with counts (R12 2.8) | debounced (320 ms) server-side search, colour filter (Highlights/Notes tabs), edit comment modal (Ctrl/Cmd+Enter save), recolour, delete with confirm, "Open in reader" | `PageLoader`; X toast only; E per-tab hints. Link `/books/{slug}/read` is dead (see Issues) |
| `/profile` | all authenticated | Read-only view or edit form: photo, name, (email read-only), role pill, Kindle emails (only if `send:kindle`), change password, 2FA panel | Edit/Cancel, upload/remove photo, edit name, add/remove/validate Kindle addresses, change password (current/new/confirm), set up/confirm/cancel/turn-off authenticator, copy setup URL, Save Changes | `PageLoader variant=profile`; errors via toast; 2FA setup/cancel errors inline (E85) |

### 2.3 Browse-by-property screens

| Route | Shows | Actions | States |
|---|---|---|---|
| `/categories`, `/series` | Property table: Code, Name, Books, Digital, Manual, Created, Open | search, Type filter, created-after/before dates, sort (book count, code, name, date); row "Open" -> `/library?category=` / `series=` (builds link from the DRAFT record_type, R12 2.5) | skeleton rows 5/3; E per page |
| `/writers`, `/translators`, `/editors`, `/publishers` (one WriterPage, 4 tabs by route) | Same table; "Open" -> `/library?author=<name>` or `contributor=<name>&contributor_role=<role>` | as above; switching tab drops query string (filters reset) | previous tab rows replaced by skeleton (E80, E190) |

### 2.4 Operator screens

| Route | Who | Shows | Actions | States |
|---|---|---|---|---|
| `/access` ("Users & Access") | Page body: `is_superuser` only (VERIFIED AccessPage.jsx:20, 54-60; others see "Users & access settings are available only to the super admin account."). Nav shows link also to `admin:full_control`/`access:manage` holders (VERIFIED navigation.js:129-135): mismatch | Tabs `?tab=users|access`. Users: create/edit form + infinite table (Name, Email, Status, Two-Factor, Permissions, Actions). Access Rules: grant editor + current rules table | Create user (invite-by-email or password), edit flags (active, require 2FA, scopes), resend setup email, delete (confirm dialog), generate/copy password; grant: user x permissions x target (Books/Categories/Writers) -> one POST per scope x target; delete rule via `window.confirm` | `PageLoader variant=management` until users + grants + references loaded (E81); E "No users found for the current search and filter." / "No scoped access rules yet."; self and superuser rows "Locked" |
| `/manual-books` ("Physical Books' List") | nav: `physical_books:view` (VERIFIED hasCapability true for staff, capabilities.js:6-11) | Table of manual (physical) books with composer | Add manual book (composer: Title, Writer, Translator, Editor, Category, Series, Publisher, Compilation, Binding, Price, Language, Summary; "Add & next", "Clear fields", "Done"), edit, export options (CSV, PDF, Excel with group-by), search, filter drawer (Writer, Translator, Editor, Category, Publisher, Binding) , sort | filters not in URL; "Done" with partial form creates silently (R12 6.8); Writer and Category required per E70-E71 |
| `/catalog` | `processing:manage` (or staff/superuser) | Overview stats (Records, Remaining, Creating, Books, On Hold), Manual sync panel, Automation panel, Book Records table | Start/Pause/Resume sync; automation On/Off, interval, time, Save, Run/Pause/Resume; select records -> "Create Book"; search + category/status filters | skeletons, optimistic overlay 2-4 s on sync controls; stream status line |
| `/create` | same | Overview (Queue, Processing, Created, Requests); 4 cards | Queue: Delete; Processing: Pause, Delete; Created: Delete (also deletes linked book, no confirm), Open; Requests: Delete | per-card busy bar, lazy-load when scrolled into view |
| `/on-hold` | same | Overview (Paused, Failed, Duplicate, Deleted); 4 cards | Paused: Resume, Delete. Failed: Force Generate, Retry, Delete. Duplicate: New, New Edition, Duplicate (confirm), Delete. Deleted: Create Again | as above |
| `/incomplete` | same | Overview (Incomplete, Updated), Automation panel, read-only Incomplete table, Updated table | Updated: Recreate Book, Delete; automation controls | paused incomplete run cannot truly resume: "Resume" restarts (E150) |
| `/multipage-toc` | same | Stats (Multi-page books, Created, Failed, In progress), Records table with TOC fetched/source badge | bulk Regenerate (created -> recreate, others -> force_generate) | |
| `/reprocessing` | same (gating inferred) | Active and History tables of `reprocess` ingestion jobs; own SSE | Stop (queued/processing), Delete (queued), Resume (failed/cancelled), Delete history, bulk variants | E "No active reprocessing jobs." etc.; failures uncaught (R12 2.14) |
| Dead: `LandingPage` | never routed (R12 2.12) | | | |

## 3. Features and behaviours

Stable IDs D5-F<n>; sources in brackets.

Auth, session, account
- D5-F1 Cookie session bootstrap `GET /auth/session/` on mount; loader until resolved. [R11 5.1]
- D5-F2 Login with email+password, two-step TOTP (`otp_required`/`otp_invalid`). [R12 2.11; E30]
- D5-F3 Forced 2FA setup gate: user with `totp_setup_required` redirected to `/two-factor-setup` from any protected route (VERIFIED ProtectedRoute.jsx:23-34). [E42]
- D5-F4 Invite-by-email: admin creates user, setup email with link; invitee sets password on `/create-password`; resend setup email; link single-use. [R11 3.3; E36, E39]
- D5-F5 Password reset request + link validation + confirm. [R12 2.11]
- D5-F6 Self-service profile: name, photo, Kindle emails, password change, 2FA lifecycle (setup, confirm, cancel, disable unless admin-required). [R11 3.5; E82-E86]
- D5-F7 Demo login (GET `/auth/demo-login/`). [R11 API #3]
- D5-F8 Logout (POST then session refresh). [R11 5.5]

Catalog and shelf
- D5-F9 Card-grid and table catalog views with search, sort, filter drawer, infinite scroll (page size 60, trigger ~30 rows before end), URL-addressable filters. [R11 3.2; R12 2; E62, U27]
- D5-F10 Cross-filtered (faceted) Contributor/Series/Category options that clear invalid selections. [R11 3.2; E69]
- D5-F11 My Books add/remove (optimistic after success), with `my_books_added_at`; sort by request date. [R11 3.7; E65]
- D5-F12 Property browse tables (categories, series, writers, translators, editors, publishers) with counts and link into filtered library. [R12 2.5]
- D5-F13 Saved filters (list, apply, delete; no create UI found in these reports). [R12 2.2; E64, E185]
- D5-F14 Record types digital / manual / all; ownership all / mine; kindle_sent mine. [R11 3.7]

Book detail and reading
- D5-F15 Book hero with identity, contributor and filter links, status pills (digital only). [R11 3.4]
- D5-F16 Open reader via launch call returning manifest URL; navigate to `/reader` with `appNav=hidden`. [R11 3.4; U12]
- D5-F17 Reading progress card (percent, last location, last opened); "Syncs after reading." if no reader access. [R11 3.4]
- D5-F18 Bookmarks, Notes (highlights), Annotations, Quotes per book and across books (NotesPage), colour filter, comment edit, delete. [R11 3.4; R12 2.8]
- D5-F19 Downloads: EPUB, cover; HTML preview in a named window guarded by a cross-tab localStorage lock (15 s TTL). [R11 3.4]
- D5-F20 Send to Kindle (needs EPUB asset + user Kindle email); refetch after; "has sent" marker on cards. [R11 3.4; R12 2.1]
- D5-F21 Physical-book personal reading log (status, pages, rating, dates, notes) stored ONLY in localStorage. [R11 3.4]
- D5-F22 HTML preview and TOC rendering, empty-chapter list with "No content on source" vs "Fetch failed". [R11 3.4; R12 2.7]

Editing and curation (operator)
- D5-F23 Metadata edit (title, summary, contributors "Name|role" per line, series, categories, edit note); slug may change so client reroutes. [R11 3.4; E54]
- D5-F24 Metadata review workflow: states pending / needs_review / approved / rejected; review log, approve/reject; metadata version history. [R11 3.4]
- D5-F25 Regenerate EPUB, replace/upload EPUB, delete book (soft-delete wording). [R11 3.4; R12 2.7]
- D5-F26 Manual (physical) book CRUD with batch-entry composer and keyboard field navigation (Ctrl/Cmd+Arrow). [R11 3.6; R12 2.6]
- D5-F27 TagInput component with suggestions (max 6), Enter/comma/Tab/Backspace semantics, commit on blur. [R12 4; U25]
- D5-F28 Export CSV / PDF / Excel (see rules). [R11 6]

Admin
- D5-F29 User management: search, status filter, sort, infinite scroll, create/edit/delete, resend invite, scope checkboxes, password generator. [R11 3.3]
- D5-F30 Scoped access grants (read:once/read:durable exclusive; per book / category / writer). [R11 3.3; E20]
- D5-F31 Admin-required 2FA flag per user (`totp_required`). [R11 3.3]

Processing (operator)
- D5-F32 Versioned live state: server per-card integer versions pushed by SSE, client refetches only changed cards; fallback 15 s poll. [R12 3.3-3.5; E111]
- D5-F33 Catalog two-phase sync (sync, request_creation) with Manual and Automation controls sharing one runtime and mutual exclusion; optimistic overlay. [R12 3.12; E105, E116]
- D5-F34 Request pipeline buckets and actions (Queue, Processing, Created, Requests; Paused, Failed, Duplicate, Deleted). [R12 3.10; E140-E144]
- D5-F35 Incomplete-books flow (category keyword detection incl. Bangla, recreate, delete). [R12 3.10; E104, E150]
- D5-F36 Multipage TOC regenerate. [R12 3.10]
- D5-F37 Reprocessing jobs console with its own SSE. [R12 2.14, 3.6]
- D5-F38 Batched "N books created." notification every 3 min (flush on demand). [U16]

Cross-cutting
- D5-F39 Toasts (dedupe by groupKey, sound with two-tone WebAudio, mute "Alerts" switch persisted). [R11 3.2; U14-U15; E83]
- D5-F40 Theme light/dark/system persisted (`elibrary:theme`, default dark). [R11 7]
- D5-F41 Backend-down modal with health polling and auto-reload. [R11 3.0]
- D5-F42 Responsive: drawer nav on narrow; tables cardified on phone via `data-label`. [E180-E189]

## 4. Role x screen/action matrix

Legacy roles as the client sees them: anonymous; reader (authenticated, no capabilities); reader with `send:kindle`; capability holder (e.g. `processing:manage`, `metadata:edit`, `physical_books:view`, `source_records:view`, `access:manage`, `admin:full_control`); staff (`is_staff`); superuser. Client capability check = superuser OR staff OR `admin:full_control` OR the scope (VERIFIED `src/utils/capabilities.js:1-12`). Nav rules are DIFFERENT and do not honour staff (VERIFIED `navigation.js:93-138`). Legend: Y = allowed/visible, nav = only link visibility, srv = left to server (403), - = no.

| Screen / action | Anon | Reader | Reader + send:kindle | Cap holder / staff | Superuser |
|---|---|---|---|---|---|
| Login, reset, create-password | Y | redirected | redirected | redirected | redirected |
| Home redirect target | `/login` | `/my-books` | `/my-books` | `/my-books` | `/home` (VERIFIED navigation.js:68-70) |
| `/my-books`, `/home`, `/library`, property tables, `/notes`, `/profile`, `/books/:slug` | - | Y | Y | Y | Y (My Books/Kindle/My Notes shown in session box regardless of caps, R11 4) |
| `/kindle-sent` link | - | hidden | Y | Y if `admin:full_control` or `send:kindle` only (staff alone does NOT see it) | Y |
| Send to Kindle / Kindle emails in profile | - | hidden | Y (also requires EPUB asset + saved Kindle email) | Y via same cap | Y |
| Read online (reader launch) | - | Y if `can_launch_reader` from server | same | same | same |
| HTML preview | - | per `can_view_preview_html` | same | same | same |
| Edit metadata, review, regenerate, replace EPUB, delete book | - | - | - | Y if `metadata:edit` (staff always Y) | Y |
| Source Records card | - | - | - | needs `source_records:view` | Y |
| "Raw Provenance" JSON | - | shown to anyone on the page, no capability check in page file (UNVERIFIED; R12 2.7, 6.7) | | | |
| `/manual-books` link | - | hidden | hidden | needs `physical_books:view` (staff Y) | Y |
| Processing menu and `/catalog /create /on-hold /incomplete /multipage-toc` | - | hidden in nav; route reachable by URL (srv) | same | `processing:manage` (staff Y) | Y |
| `/reprocessing` | - | URL reachable; page calls API directly | same | Processing menu item (R11 4 lists Reprocessing under processingItems, `processing:manage`) | Y |
| `/access` page body | - | "available only to super admin" message | same | message unless `is_superuser` (VERIFIED AccessPage.jsx:54-60) although nav shows the link to `access:manage` / `admin:full_control` holders (VERIFIED navigation.js:129-135) | Y |
| Create/edit/delete users, resend invite | - | - | - | - (UI), server may differ | Y; own row and other superusers "Locked" |
| Grant scoped access | - | - | - | - | Y; own user excluded from dropdown |
| Own 2FA turn-off | - | Y unless admin-required | same | same | same |
| Alerts mute, theme, My Notes | - | Y | Y | Y | Y |

Observations: (a) the only authoritative client gate is `is_superuser` in AccessPage and `canLoadProcessingState` in the processing store; (b) E151/E193 confirm no tests for non-privileged access to restricted routes; (c) a rebuild should drive nav and route guards from ONE permission set returned by the server (VERIFIED the three sources disagree: hasCapability, navigation.js, AccessPage).

## 5. Business and UI rules

Validation
- Email (all forms): trim, regex `^[^\s@]+@[^\s@]+\.[^\s@]+$` (VERIFIED `src/utils/email.js:1`). Live feedback: none when empty, invalid message "Enter a valid email address.", valid "Email looks good." (E31).
- Kindle email rule: valid email AND domain exactly `kindle.com` (case-insensitive) (VERIFIED email.js:24-31); message "Use a Kindle email ending in @kindle.com."; `free.kindle.com` rejected (U6). Multiple addresses per user, persisted as newline-joined text `kindle_emails_text`; add-row button disabled until every row is valid; Save disabled while any invalid or no change (R11 3.5). The user is told to allow the sender address (`kindle_sender_email`) in Amazon "Personal Document Settings" and, for multiple addresses, turn off "Personal Document Archiving" (R11 3.5, E86). Send-to-Kindle button appears only if the book has an EPUB asset and the user has a Kindle address (R11 3.4). Server error `detail` (e.g. SMTP failure) is surfaced verbatim, status 502 (U8).
- Password: client checks only presence and match (R11 3.5, 12 2.11). Server enforces min length 12 (E15, E37). Admin generator: 18 chars from `ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%^&*` using `crypto.getRandomValues` with `% 64` modulo bias (R11 3.3). 
- Create user: valid email; password required unless "Send Setup Email" (default on); at least one account permission; `read:once` and `read:durable` mutually exclusive (client only) (R11 3.3).
- Grants: user, at least one permission, at least one target; duplicates skipped; one POST per scope x target, not atomic.
- Profile: current password needed to change; new fields must match.
- Manual book: Title; at least one of writer/translator/editor (U21); Writer and Category required per E70/E71 (conflict: R11 3.6 says no required-field validation in the composer, so enforcement location is UNVERIFIED); price number >= 0 step 0.01, "" -> null (zero price lost in the edit mapping, U33); binding `hard_cover` (default) | `paper_back`; language `bn` default | `en`; currency symbol Taka.

Tag input (D5-F27, U25): suggestions exclude chosen values (case-insensitive), substring match, max 6; ArrowDown/Up cycle with wrap; Tab takes highlighted else first suggestion; Enter or comma commits highlighted else free text; Esc closes dropdown; Backspace on empty removes last tag; Arrow Left/Right fire field-navigation only when empty; add guard trims and collapses whitespace, ignores empty and case-insensitive duplicates; blur commits typed text (regression: lost Bengali names when clicking "Add & next"). Single-value fields (Series, Publisher): last tag wins (R11 3.6).

Export (R11 6; U19-U24, U31-U32)
- Source: fetches ALL pages at limit 100 for the active filters (not just the loaded page). Gate: blocked while loading, on error, when empty, or if any item `state==="processing"` (messages in R11 6).
- CSV: 14 columns in fixed order (`Book ID, Title, Writer / Translator / Editor / Publisher, Writers, Translators, Editors, Publishers, Categories, Series, Price, Type, State, Review, Created At`), UTF-8 BOM, `\n`, quoted on `, " \n`; no `\r` quote and no formula-injection guard.
- PDF: client-built image-only PDF, A4 landscape, 8 columns, optional group-by; not searchable; filename slug collapses Bengali to `books-export`.
- Excel (manual only): handwritten OOXML zip, sheets per group (category, publisher, binding, language, contributor), invalid sheet-name chars replaced, 31-char truncation without de-dup, "(None)" bucket, books duplicated across groups.
- Pending-export resume in sessionStorage (10-minute TTL) so reload mid-export resumes; 240 ms minimum loader.
- Contributor normalisation (NFKC, trim, whitespace collapse, case-fold; `compiler` = `editor`; author dropped if same person is translator/editor) is duplicated four times (U22).

Notifications and toasts (R11 3.2; U14-U16; E147)
- Default toast life 3600 ms; same `groupKey` (type:title) replaces in place, restarts the hold timer, and does NOT replay the sound; a `holdOpenMs` override exists (tests use 120 000 ms). Muting suppresses sound only; toasts stay visible. Sound presets: success 660 then 880 Hz, error 260 then 196, info 420 then 560. Mute persisted in `app.notifications.muted`.
- Processing "created" events are batched: counts summed, one toast "N books created." after 180 000 ms, or immediately via flush. No singular form (U34).
- Error toasts use `role=alert`; others `role=status`; each has a dismiss button. Toast copy "Something went wrong" default for errors.

Other rules
- Reader launch: `appNav=hidden` default; manifest URL carried in query; four URLs inside the manifest (EPUB, HTML preview, reading session, bookmarks) (U13).
- HTML preview: one window per book/user (`html_preview_{userId}_{bookId}`), cross-tab lock via localStorage key `ebook_preview_lock:{pathname}`, 15 s TTL, poll 1.5 s.
- Book slug can change after metadata save / regenerate / EPUB replace; client must reroute.
- Return-to-list: `location.state.from` accepted only if starts with `/`.
- Record state vocab: digital `draft, processing, queued, ready, published, archived`; review `pending, needs_review, approved, rejected`; request `initial, queued, processing, created, paused, failed, duplicate, deleted` (R11 8, R12 3.9).
- Processing time zone fixed to Asia/Dhaka in formatDate (R12 6.12).
- Delete wording "This will hide it from the catalog." (soft delete) vs user "permanently remove the account" (R12 2.7, 2.9).

## 6. Data shown and API consumed

Base `/api`; `credentials: include`; non-GET calls first `GET /csrf/` to set `csrftoken` then header `X-CSRFToken` (VERIFIED `src/api/csrf.js:10-19`: promise de-duped only while in flight, then reset, so every mutation pays a GET). Count in R11: 60 distinct endpoints through `apiFetch` plus blob download and `window.open` assets. Processing endpoints are listed in R12 3.8/E110.

| Group | Endpoint | Shape / purpose | Caller |
|---|---|---|---|
| Session | `GET /csrf/` (also health probe), `GET /auth/session/` -> `{authenticated,user}` with `id,email,full_name,profile_image_url,is_active,is_staff,is_superuser,totp_enabled,totp_required,totp_setup_required,capabilities[]` (E7) | useSession |
| Auth | `POST /auth/login/`, `POST /auth/logout/`, `GET /auth/demo-login/`, `POST /auth/password-reset/`, `.../validate/`, `.../confirm/` (body `{uid,token,new_password}`; response `next_step: "totp_setup"|"login"`) | useSession, auth pages |
| Profile | `GET /auth/profile/`, `PATCH /auth/profile/` (multipart: `full_name, profile_image, remove_profile_image, kindle_emails_text, current_password, new_password, confirm_new_password`) | ProfilePage, profileSaveAction |
| 2FA | `GET /auth/2fa/status/` -> `{enabled,required,pending_setup,setup_required}`; `POST .../setup/` -> `{provisioning_uri,secret,qr_svg}`; `.../confirm/ {token}`; `.../cancel/`; `.../disable/` | profile, TwoFactorSetupPage |
| Users | `GET /auth/users/?q&status&sort&offset&limit` -> `{rows,pagination:{offset,limit,totalCount,hasMore,nextOffset}}`; row `id,email,full_name,is_active,is_superuser,totp_required,totp_enabled,global_scopes[],grant_count,can_resend_setup_email`; `POST /auth/users/` (`{email,full_name,is_active,totp_required,send_invite_email,global_scopes,password?}`), `PATCH/DELETE /auth/users/{id}/`, `POST .../resend-setup-email/` | useManagedUserList, useAccessUsers |
| Access admin | `GET /access/references/?view=users|access` -> `{users,books,categories,writers,account_scopes:[{value,label}],scoped_scopes}`; `GET/POST /access/grants/` (body `{user,scope,book|category|contributor,expires_at:null,notes:""}`); `DELETE /access/grants/{id}/` | useAccessAdminData, useAccessGrants |
| Catalog list | `GET /catalog/books/?q&author&series&category&contributor&contributor_role&ownership&record_type&sort&kindle_sent&page&limit` -> `{entries[],pagination{page,limit,total_count,page_count,has_previous,has_next}}` or bare array; entry has `id,slug,catalog_code,title,authors,categories,series,record_type,created_at,primary_source{display_path},is_in_my_books,my_books_added_at,has_epub_asset,has_sent_to_kindle,user_kindle_sent_at,cover_download_url,latest_submission_at` | useInfiniteCatalogBooks, exports (limit 100 loop) |
| Facets | `GET /catalog/{writers,series,categories,translators,editors,publishers}/?record_type&...&sort=name` -> bare array of `{name}` in some mocks, `{entries,pagination}` in others (E190, E202; UNVERIFIED which is real); property rows `{id,catalog_code,name,book_count,digital_book_count,manual_book_count,created_at}` | useDynamicFilterOptions, property pages, manual options |
| Manual books | `GET /catalog/manual-books/` (same list shape); `POST /catalog/manual-books/`; edit via `PATCH /catalog/books/{slug}/metadata/` with `contributors:[{name,role}]` | ManualBooksPage, BookDetailPage |
| Book detail | `GET /catalog/books/{slug}/` (polled every 4 s while job active); `DELETE`; `POST .../assets/epub/` (multipart `file`); `POST .../regenerate/` -> `{book,created,job{status}}`; `PATCH .../metadata/`; `GET .../metadata-versions/`; `GET/POST .../metadata-reviews/`; `PATCH /catalog/metadata-reviews/{id}/ {state}` | book-detail hooks |
| Shelf | `POST/DELETE /catalog/books/{slug}/my-books/` | useMyBooksAction |
| Kindle | `POST /access/books/{slug}/send-to-kindle/` -> `{detail}` | hero, cards |
| Reading | `GET /access/books/{slug}/reading-session/` (401/403 treated as no reader access); `GET/POST /access/books/{slug}/bookmarks/`; `DELETE /access/bookmarks/{id}/`; `GET/POST /access/books/{slug}/highlights/`; `PATCH/DELETE /access/highlights/{id}/`; `GET /access/me/notes/?book&kind&color&q` -> `{highlights,notes,quotes}` (+ bookmarks); `GET /access/me/reading-progress/`; `POST /access/books/{slug}/reader-launch/` -> `{manifest_url|launch_url}`; downloads `GET /access/books/{slug}/download/{html|epub}/` (E55) | reading.js, readerLaunch.js |
| Saved filters | `GET /saved-filters/?target=catalog`, `DELETE /saved-filters/{id}/`, (create unknown) | LibraryPage |
| Processing | `GET /processing/state/?includeLists=0` (summary, sync, syncStates, automation, versions); `GET /processing/table/?card&offset&limit=60&includeFacets&q&category&status` -> `{rows,pagination,filters{categoryOptions,statusOptions},version,summary?}`; `GET /processing/card/?card=`; `GET /processing/stream/?page=` (SSE); `POST /processing/sync/{start|scope/pause|resume|stop}/`; `POST /processing/records/create-requests/ {ids}`; `POST /processing/requests/action/ {ids,action,...}`; `POST /processing/automation/{catalog|incomplete}/` and `/run/` | processing store |
| Ingestion jobs | `GET /ingestion/jobs/?job_type=reprocess&limit=200`, `GET /ingestion/jobs/reprocess/summary/`, `POST /ingestion/jobs/{id}/stop|resume/`, `DELETE /ingestion/jobs/{id}/`, `GET /ingestion/jobs/stream/` (SSE) | ReprocessingPage |

Error handling contract (R11 2; U8-U11): JSON parsed else text; 204/205 -> null (U9); message from `detail|message|non_field_errors|first field` (DRF style); network/0/502/503/504 -> backend-unavailable flow; HTML tags stripped from messages. The client also rewrote absolute backend URLs onto the browser origin (U11) and a nested `manifest=` URL: a symptom of the server emitting wrong-origin absolute URLs.

Data presented per entity (condensed): Book (code, title, contributors by role, series, categories, cover, state/review, source records, provenance, TOC tree with content states, empty chapters, dedication/info HTML sanitised with DOMPurify); User (name, email, status, 2FA, scopes); Grant (user, scope, target label); Reading (progress %, last location, last opened, bookmarks, highlights/notes/quotes with colours green, yellow, blue, pink, underline); Processing row (title, URL, credits, category, status, details, updated).

## 7. Client state and real-time

Auth and session
- Cookie session with CSRF cookie; no token in JS. `useSession` holds `{loading,authenticated,user,error}`; login = POST then re-GET session; logout = POST then re-GET.
- Any 401 or 403 outside `/auth/session/`, `/auth/login/`, `/auth/password-reset/` dispatches `app:session-expired` once (VERIFIED `src/api/runtime.js:115-136`); `SessionRestartHandler` then clears client session, toasts "The application has restarted. Please log in again.", and redirects to `/login` with `reason:"app-restarted"` (VERIFIED `SessionRestartHandler.jsx:12-23`). So a plain 403 (permission denied) logs the user out client-side. The notification re-arms only after a later `/auth/login/` or `/auth/session/` call (VERIFIED runtime.js:138-142).
- Backend health: `GET /csrf/` polled every 6 s for the whole session by `BackendStatusModal`; overlay `role=alertdialog`, polls 5 s while shown, hard `window.location.reload()` on recovery (R11 3.0; UNVERIFIED line-level).

Persistence
- localStorage: `elibrary:theme` (light|dark|system, default dark), `app.notifications.muted`, `elibrary_physical_reading_log_{slug}`, `ebook_preview_lock:{pathname}`; reader keys `epub_reader_font_size` (default 20), `epub_reader_theme_index` (E53).
- sessionStorage: `filters-expanded:home|library`, pending exports (`catalog-books-export`, `manual-books-export`, 10 min TTL), `useSessionFlag` flags.
- URL as source of truth for list filters/sort/search (Home, Library, My Books, Kindle, property pages, access tab); ManualBooks and Notes keep state in component only.

Caching and fetching
- No query cache library. Each list hook (`useInfiniteCatalogBooks`) uses a sequence id to drop stale responses, keeps old rows during refresh, exposes prepend/update/remove/reload. Typeahead requests are not debounced in user management (one request per keystroke, R11 8.16) and processing card search; catalog toolbar search debounces 400 ms; notes search 320 ms.
- Option lists: Home/Library use cross-filtered options; My Books and Kindle fetch ALL writers/series/categories unpaginated at each mount (R12 2.3).
- Optimistic updates are rare: My Books/Kindle flags updated after server success; catalog sync overlay 2000-4000 ms; everything else waits for the server.

Real-time (SSE and polling)
- Processing: one `EventSource('/processing/stream/?page=<page>', {withCredentials:true})` per processing route, only while on `/catalog /create /on-hold /incomplete /multipage-toc` and user has `processing:manage`/staff/superuser. Events `connected` and `versions` `{versions:{cardKey:int}}`; `onerror` -> `reconnecting` (browser auto-retries) (VERIFIED `useProcessingStream.js:35-63`). Parse errors swallowed (VERIFIED :52). Fallback: while `reconnecting` or `unsupported`, `loadProcessingState()` every 15 000 ms (VERIFIED :81-98). No heartbeat, no backoff, no Last-Event-ID.
- Versioning model: server integer versions per card key (19 keys, 7 shared via one aggregate state, 12 list cards each refetching themselves). Client accepts only strictly greater versions; shared change queues a reload of `/processing/state/`; list cards refetch when `getDomainVersion(key) > loadedVersion` and the card is visible; refetch uses `limit = rows.length` (re-pulls everything scrolled); action responses also carry `versions`. State applied only when the client's shared signature equals payload's (stale payload ignored). (R12 3.3-3.4; E111, E146)
- Reprocessing page: separate SSE `/ingestion/jobs/stream/` events `connected`, `job-update` (any -> full reload of jobs + summary), 15 s poll fallback (R12 3.6).
- Book detail: polls the book every 4 s while latest job is queued/processing (R11 API #37).
- Preview lock: localStorage poll 1.5 s plus storage/focus/visibility events (R11 3.4).
- Page background traffic summary: CSRF health 6 s always, plus SSE or 15 s polling on processing pages, plus 4 s on active-job book pages.

## 8. Issues

Severity: H high, M medium, L low. V = VERIFIED in code (file:line), U = UNVERIFIED (report only).

Security and authorisation
- D5-I1 (H, V) Any 401/403 on ordinary calls triggers the global "application has restarted, log in again" flow, clearing the client session although the server session is valid. A legitimate permission-denied 403 therefore logs the user out. `src/api/runtime.js:115-127`, `SessionRestartHandler.jsx:12-23`.
- D5-I2 (H, V) No route-level role guard; every protected route is reachable by URL for any signed-in user, relying on server 403 (and I1 turns that 403 into a forced logout). `AppRoutes.jsx:37-72`.
- D5-I3 (M, V) Three inconsistent permission models: `hasCapability` honours staff and `admin:full_control` (capabilities.js:6-11); `primaryNavigation` ignores staff for Kindle (navigation.js:107-112); `/access` page body requires superuser only (AccessPage.jsx:54-60) while nav shows it to `access:manage` holders (navigation.js:129-135), who then see a "super admin only" message. 
- D5-I4 (M, U) "Raw Provenance" card labelled Staff but no capability check in the page file (R12 6.7).
- D5-I5 (M, U) User enumeration: reset request shows 404 "No user exist with this email." (E34).
- D5-I6 (M, U) Reset-link expiry detection compares English error strings (R12 2.11); no client password policy; server min 12.
- D5-I7 (L, U) `qr_svg` injected with `dangerouslySetInnerHTML` unsanitised (R12 4).
- D5-I8 (M, U) CSV export lacks formula-injection guard and `\r` quoting (R11 6; U32).
- D5-I9 (L, U) Password generator modulo bias (R11 3.3).

Functional bugs
- D5-I10 (H, V) Broken deep links: `/books/{slug}/read` used in NotesPage (NotesPage.jsx:617, V) and BookReaderSections (R11, 4 places, U); no such route exists and `*` redirects to `/` (AppRoutes.jsx:127, V). "Open in reader" from notes/book detail goes to the home page.
- D5-I11 (M, U) Reprocessing `act()` has no catch: failed stop/resume/delete gives no toast and an unhandled rejection; bulk `Promise.all` abandons selection clear (R12 2.14).
- D5-I12 (M, U) Multipage "Regenerate" returns an array so selection clears even when both calls failed (R12 3.10).
- D5-I13 (M, U) Destructive actions without confirmation: Created-card delete also deletes the linked book, Reprocessing stop/delete, saved-filter delete, bulk deletes (R12 6.4).
- D5-I14 (M, U) Grants: N x M non-transactional POSTs; partial failure leaves a mix with one generic toast (R11 8.7).
- D5-I15 (L, U) Placeholder bug "Search categorys" (R11 3.3).
- D5-I16 (M, U) Physical-book personal reading log only in localStorage: lost on another browser/device while digital progress is server-side (R11 3.4).
- D5-I17 (M, U) Price 0 maps to `""` on edit, silently turning a free book into "no price" (U33).
- D5-I18 (L, U) NotesPage tab count overwritten by the filtered count (R12 2.8); stale tabs after edits elsewhere.
- D5-I19 (L, U) WriterPage tab switch drops filters; property "Open" link built from draft record_type (R12 2.5, 6.13).
- D5-I20 (L, U) `apiFetch` drops falsy bodies (R11 8.9); `ConfirmationDialog` hardcodes "Deleting..." label and danger style (R12 6.3).
- D5-I21 (L, U) Expired-link copy differs ("has expired" vs "has been expired", E39); TOTP issuer "Bangla Library" vs "RSalehin24 Library" vs page title "eLibrary" (E84, E202).
- D5-I22 (M, U) ManualBooksPage "Done" creates a book from a half-filled form silently; 50 ms setTimeout blur hack; filters not in URL (R12 6.8).

Performance and technical debt
- D5-I23 (M, V) Extra `GET /csrf/` before every mutation (csrf.js:10-19). 
- D5-I24 (M, U) CSRF health poll every 6 s for the session lifetime plus forced page reload on recovery (loses unsaved form state) (R11 3.0, 8.17).
- D5-I25 (M, U) Processing SSE has no heartbeat/backoff; fallback polls only the shared state so list cards advance only through versions in that payload; refetch uses `limit=rows.length` (R12 6.10-6.11); hard-to-reason 7-ref state machine (R12 3.4); context value never memoised (R12 6.9).
- D5-I26 (L, U) Keystroke-level requests (no debounce) in user search and processing card search (R11 8.16; R12 3.11).
- D5-I27 (M, U) Dead code: LandingPage, PropertyTableControls, 10 helpers in `processingTableRows.js`, stop actions, 2 s card polling, `authenticatedNavigation`, `hasNotesLink` (R11 8.4; R12 6.1).
- D5-I28 (M, U) Heavy duplication: Home/MyBooks/Kindle pages, Category/Series/Writer pages (95%), manual-book edit mapping (two places), export resume, password reveal, My Books toggle logic, contributor normalisation x4 (R11 8; R12 6.2; U22).
- D5-I29 (L, U) Exports: image-only PDF (not accessible, not searchable, large), Excel sheet names not de-duplicated, hand-written zip, `slugifyFilename` collapses Bengali names (R11 6; U31-U32). `localeCompare` without locale for Bengali sorting (U30).
- D5-I30 (L, U) Time zone hard-coded Asia/Dhaka in processing dates; reprocessing relative time uses browser locale (R12 6.12).
- D5-I31 (L, U) Emoji used as icons; mixed native `window.confirm` and custom dialogs; `humanizeError` exists but is unused by most hooks (R11 8.23-8.25).
- D5-I32 (L, U) Server emits absolute URLs with wrong origin so client rewrites them (U11).
- D5-I33 (L, U) Accessibility: TagInput lacks listbox semantics (U25); notification sound has no visual-only alternative besides toast; `ScrollToTopButton` only on three routes (R12 6.14).

Test gaps (E204, E151, U1-U2)
- D5-I34 (H, U) Unit tests mostly test inlined copies of code, five are source-grep tests; no regression protection.
- D5-I35 (M, U) Untested: Send-to-Kindle flow, highlights/annotations, reader progress/bookmark creation, non-admin access to restricted routes, scope effects, metadata edit/review workflow, TOTP login step, password-reset-then-login, session expiry/logout, manual book edit/delete, saved-filter creation, export content, Bangla UI.
- D5-I36 (M, U) E2E suite flaky by design: fixed sleeps, shared mutable live state, login retried 3x, pixel assertions (E200-E201); mock contracts drifted (E202).

## 9. Keep / change / drop for the Angular rebuild

Keep (behaviour worth carrying)
- Invite-only model: invite by email, resend, single-use link, forced/optional TOTP, admin-required flag. Reason: product core (D5-F3, F4, F6, F31).
- My Books shelf, Kindle send with multi-address and `@kindle.com` rule (confirm `free.kindle.com`, Open Q), sender-address instructions.
- URL-addressable list filters, search/sort/filter drawer, infinite scroll, skeleton loading with no layout shift, empty states, cardified tables on phones.
- Cross-filtered facets (author/series/category) but served as one server call.
- Scoped access grants (book/category/writer) and global scopes; user list with search/status/sort.
- Reading data model: progress, bookmarks, highlights, notes, quotes with colours; cross-book "My Notes".
- Book detail sections: identity, contributors, TOC, source records for staff, metadata review workflow.
- Manual (physical) books incl. batch-entry composer, tag/chip inputs with commit-on-blur, keyboard field jump, Excel/CSV export with grouping.
- Processing console concepts: card buckets, per-card server versions, SSE with fallback, optimistic sync controls, mutual exclusion of Manual vs Automation, per-card busy state, lazy-load of off-screen cards.
- Toast grouping, sound mute ("Alerts"), batched "N books created" notification (add plurals), theme persistence with system option.
- Test design: injected clock/storage/audio ports (U4).

Change
- Auth errors: distinguish 401 (go to login) from 403 (inline "not allowed"); never fake "application restarted".
- One server-supplied permission set drives nav, route guards (Angular `CanMatch`), and component visibility; guard `/access`, processing, manual-books, raw provenance on both sides.
- Error contract: stable machine code + field path + message, not prose parsing; relative/opaque URLs, no origin rewriting.
- CSRF: with Rust token/cookie design fetch once or use SameSite+header check; no per-mutation GET; real `/health` endpoint, no 6 s browser poll (use SSE connection state / on-failure retry with backoff) and no forced reload.
- Reader and reading log: persist physical-book log server-side; fix dead `/read` links (route `/reader/:slug` with launch resolved on the server).
- Exports: server-generated or text-based PDF (selectable text, Bengali font), formula-safe CSV (prefix `'`), unique sheet names, Bengali-aware filenames and `Intl.Collator('bn')`.
- Streams: SSE with heartbeat, `Last-Event-ID`, exponential backoff, and fallback that refreshes all visible cards; send the delta or a changed-card list rather than refetching `rows.length`; one stream abstraction for processing and reprocessing.
- Signals/RxJS store (NgRx SignalStore or plain signals) for session, theme, toasts, processing state instead of 7-ref hooks.
- Material 3: one confirm dialog (Material dialog) with configurable label/tone; replace `window.confirm` and emoji with Material icons; snackbar queue for toasts (grouped), dialogs for confirmations.
- Grants: single batched endpoint (users x scopes x targets, atomic).
- Normalise contributors on the server; one shared TagInput (Material chips with autocomplete).
- Password rules shown client-side (min 12) from server policy; generator uses unbiased sampling.
- Order of dates/time zone from user/server config rather than hard-coded Asia/Dhaka.
- Tests: test real modules with Vitest/Angular testing, contract-test API mocks from one OpenAPI/Rust-generated schema; no source-grep tests.

Drop
- LandingPage, PropertyTableControls, dead processing helpers, unused stop actions, `authenticatedNavigation`, 2 s card polling, demo login unless Owner wants it.
- Duplicate pages (see merge list), saved-filter strip if no creation path exists (UNVERIFIED; confirm), `/processing-*` legacy aliases (keep only a few redirects if old links matter).
- Image-only PDF renderer and hand-rolled zip/OOXML (replace with a vetted approach after dependency approval).
- Pixel-exact test assertions, brittle fixed sleeps, 300-line-per-file CSS fragmentation.

Merge / simplify for a minimalist M3 design
1. One "Library" screen replaces Home, Library and Kindle-sent: single catalog view with a view toggle (cards/list), segmented chips for scope (All, My Books, Sent to Kindle), type (digital/physical) and one filter sheet; Home is just the default scope for admin. My Books becomes a scope chip, not a separate page; deep links preserved via query.
2. One "Browse" screen replaces Categories, Series, Writers, Translators, Editors, Publishers: tab bar by facet (Material tabs), shared table/list component, same filters.
3. Book detail: tabs/sections (Overview, Contents, Notes, Details/Source, Edit for editors) instead of one long page; physical-book workspace as a section of the same screen; metadata edit as a side sheet.
4. Profile and security in one page with sections; 2FA setup as stepper dialog; drop the separate `/two-factor-setup` unless forced (reuse same stepper full-screen).
5. Notes: master/detail on tablet+, list-with-drill-in on phone; tabs by kind.
6. Admin "Users" and "Access" as two tabs in one screen, but grants better surfaced per user (user drawer shows their grants) to remove the user-vs-rule tables and the double user fetch.
7. Processing: collapse Catalog, Create, On Hold, Incomplete, Multipage, Reprocessing into one "Import" workspace with a bucket rail (Records, Queue, Processing, Created, Paused, Failed, Duplicate, Deleted, Incomplete, Multipage, Reprocess) sharing one table component and one live stream; Sync/Automation as a header card. Count badges from one summary.
8. Auth screens (login, reset request, reset confirm, create-password, demo) are all one card shell with different steps; reset-confirm and create-password are the same form with different copy.
9. Responsive: Material navigation bar (phone), rail (tablet), drawer (desktop) driven by one nav config; removes dual-topbar/profile-dropdown/mobile-panel triplication.
10. Settings sheet for theme (light/dark/system), alerts sound on/off; ThemeToggle floating button dropped.

## 10. Open questions

1. Reader: what does the embedded reader need from the host (manifest contract, reading-session sync cadence, highlight colours, themes)? Reports only cover launch and e2e behaviours (R11 9, R12 7). Is the reader being rebuilt or reused?
2. Which role model is intended: superuser vs staff vs capability list? Should `access:manage` users see `/access`, and can a non-superuser create users? Evidence conflicts (D5-I3).
3. Is `free.kindle.com` valid? Should the Kindle address allow only `@kindle.com`? Should the user see which book was sent when (data exists: `user_kindle_sent_at`)?
4. Saved filters: no creation UI found in the four reports; is it a live feature or half-removed? Contract of POST unknown.
5. Contributor facet endpoints: bare array vs `{entries,pagination}` (E190); processing summary field names `resolved` vs `completed` (E115); which are authoritative? Moot for the rebuild but affects migration of operator habits.
6. Is the HTML preview feature (named window plus cross-tab lock) required, or can preview be an in-app route? Cross-tab locking exists to limit concurrent previews: is that a licensing or load rule?
7. Is demo login to be kept (public demo account)?
8. Processing: are Reprocessing and Multipage TOC separate concepts the operator needs, or merged in the rebuild? Should "Delete linked book" from Created require confirmation? Single-operator or many (one global catalog runtime was observed, E161)?
9. Time zone for automation `time` and display (Asia/Dhaka hard-coded in UI; server timezone unknown, E164).
10. Physical-book reading log: keep personal logging, and server-side for sync across devices?
11. Notification model: keep sound alerts? Browser notifications? Is the 3-minute batching window a requirement?
12. Bengali UI: UI strings are English (data is Bengali). Is Bengali localisation of the UI a goal? Fonts (Noto Sans Bengali, Hind Siliguri) used in PDF.
13. Does the new design keep export-to-PDF client side? Who consumes PDF/Excel (operator for offline catalogue)?
14. Exact responsive breakpoints (between 821 and 1024 px unpinned; R11 uses 981 px) and whether 2-column desktop book grid was a mock artefact (16a unverified).
15. Not verified here: BackendStatusModal polling lines, `BookReaderSections` link lines, `useBookDetailData` polling, TagInput blur logic, `utils/exportSession` storage type (R12 says sessionStorage unconfirmed; R11 says sessionStorage).

