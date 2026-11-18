# Legacy frontend: features (non processing/reader), layouts, hooks, api, utils, entry

Status: DRAFT (research evidence; read-only record)

Root: `archive/app/frontend/src` (paths below relative to it; `index.html` is `archive/app/frontend/index.html`). Read-only analysis, every line of every assigned file read. Stack: React (JSX) + react-router-dom v6 + Vite; no UI library, no data-fetching library (hand-rolled hooks), plain `fetch`.

## 1. Coverage table

| file | lines | fully read |
|---|---|---|
| index.html (frontend root) | 13 | yes |
| main.jsx | 23 | yes |
| App.jsx | 25 | yes |
| layouts/AppShell.jsx | 285 | yes |
| api/auth.js | 36 | yes |
| api/catalog.js | 21 | yes |
| api/client.js | 5 | yes |
| api/constants.js | 4 | yes |
| api/csrf.js | 19 | yes |
| api/download.js | 55 | yes |
| api/errors.js | 31 | yes |
| api/http.js | 69 | yes |
| api/reading.js | 51 | yes |
| api/response.js | 35 | yes |
| api/runtime.js | 142 | yes |
| api/text.js | 117 | yes |
| api/urlNormalization.js | 41 | yes |
| api/urls.js | 42 | yes |
| hooks/useAsyncAction.js | 29 | yes |
| hooks/useDialogA11y.js | 74 | yes |
| hooks/useDynamicFilterOptions.js | 89 | yes |
| hooks/useInfiniteCatalogBooks.js | 296 | yes |
| hooks/usePageTitle.js | 16 | yes |
| hooks/useSessionFlag.js | 37 | yes |
| hooks/useSession.jsx | 81 | yes |
| hooks/useTheme.js | 69 | yes |
| hooks/useToast.jsx | 82 | yes |
| utils/bookExport/constants.js | 31 | yes |
| utils/bookExport/csv.js | 46 | yes |
| utils/bookExport/excel.js | 400 | yes |
| utils/bookExport/helpers.js | 118 | yes |
| utils/bookExport/index.js | 3 | yes |
| utils/bookExport/pdf.js | 292 | yes |
| utils/bookExport/rows.js | 24 | yes |
| utils/bookPresentation/contributors.js | 139 | yes |
| utils/bookPresentation/formatters.js | 29 | yes |
| utils/bookPresentation/index.js | 14 | yes |
| utils/bookPresentation/meta.js | 32 | yes |
| utils/bookPresentation/sources.js | 25 | yes |
| utils/capabilities.js | 12 | yes |
| utils/catalogBooks.js | 33 | yes |
| utils/email.js | 43 | yes |
| utils/export.js | 32 | yes |
| utils/exportSession.js | 76 | yes |
| utils/humanizeError.js | 64 | yes |
| utils/notificationAudio.js | 131 | yes |
| utils/previewLock.js | 54 | yes |
| utils/processingCreatedNotificationBuffer.js | 73 | yes |
| utils/query.js | 38 | yes |
| utils/toastManager.js | 184 | yes |
| features/access/api.js | 5 | yes |
| features/access/constants.js | 30 | yes |
| features/access/utils.js | 59 | yes |
| features/access/components/AccessGrantEditorCard.jsx | 142 | yes |
| features/access/components/AccessGrantRulesCard.jsx | 56 | yes |
| features/access/components/AccessHero.jsx | 41 | yes |
| features/access/components/AccessUserEditorCard.jsx | 291 | yes |
| features/access/components/AccessUsersTableCard.jsx | 270 | yes |
| features/access/hooks/clipboardActions.js | 22 | yes |
| features/access/hooks/useAccessAdminData.js | 90 | yes |
| features/access/hooks/useAccessGrants.js | 209 | yes |
| features/access/hooks/useAccessTabs.js | 39 | yes |
| features/access/hooks/useAccessUsers.js | 296 | yes |
| features/access/hooks/useManagedUserList.js | 260 | yes |
| features/app/AppRoutes.jsx | 130 | yes |
| features/app/BackendStatusModal.jsx | 102 | yes |
| features/app/ProtectedRoute.jsx | 37 | yes |
| features/app/RouteScrollReset.jsx | 61 | yes |
| features/app/SessionRestartHandler.jsx | 31 | yes |
| features/book-detail/api.js | 9 | yes |
| features/book-detail/constants.js | 5 | yes |
| features/book-detail/readerLaunch.js | 42 | yes |
| features/book-detail/utils.js | 272 | yes |
| features/book-detail/components/BookDetailHero.jsx | 316 | yes |
| features/book-detail/components/BookDetailIcons.jsx | 46 | yes |
| features/book-detail/components/BookFilterLinkList.jsx | 28 | yes |
| features/book-detail/components/BookMetadataWorkspace.jsx | 233 | yes |
| features/book-detail/components/BookReaderSections.jsx | 405 | yes |
| features/book-detail/components/BookTocSummary.jsx | 65 | yes |
| features/book-detail/components/PhysicalBookWorkspace.jsx | 310 | yes |
| features/book-detail/hooks/assetMutationActions.js | 59 | yes |
| features/book-detail/hooks/assetPreviewActions.js | 94 | yes |
| features/book-detail/hooks/metadataActions.js | 46 | yes |
| features/book-detail/hooks/reviewAndBookmarkActions.js | 49 | yes |
| features/book-detail/hooks/useBookAssetActions.js | 167 | yes |
| features/book-detail/hooks/useBookDetailActions.js | 77 | yes |
| features/book-detail/hooks/useBookDetailData.js | 280 | yes |
| features/book-detail/hooks/useBookLifecycleActions.js | 51 | yes |
| features/book-detail/hooks/useBookMetadataActions.js | 129 | yes |
| features/book-detail/hooks/useBookOwnershipActions.js | 36 | yes |
| features/book-detail/hooks/useBookReaderAction.js | 36 | yes |
| features/book-detail/hooks/useHtmlPreviewLockState.js | 56 | yes |
| features/catalog/exportUiTiming.js | 16 | yes |
| features/layout/AppTopbar.jsx | 189 | yes |
| features/layout/MobileNavigationIcons.jsx | 62 | yes |
| features/layout/MobileNavigationPanel.jsx | 246 | yes |
| features/layout/NavDropdown.jsx | 66 | yes |
| features/layout/navigation.js | 145 | yes |
| features/layout/ProfileMenu.jsx | 114 | yes |
| features/layout/ReaderTopbarHideButton.jsx | 25 | yes |
| features/layout/utils.js | 10 | yes |
| features/library/libraryExport.js | 31 | yes |
| features/library/libraryFilters.js | 60 | yes |
| features/library/SavedFilterStrip.jsx | 44 | yes |
| features/library/useMyBooksAction.js | 29 | yes |
| features/manual-books/ManualBookComposer.jsx | 252 | yes |
| features/manual-books/manualBookCreate.js | 11 | yes |
| features/manual-books/manualBookExport.js | 31 | yes |
| features/manual-books/manualBookFilters.js | 67 | yes |
| features/manual-books/manualBookOptions.js | 50 | yes |
| features/manual-books/ManualBooksToolbarActions.jsx | 74 | yes |
| features/profile/ProfileEditorForm.jsx | 95 | yes |
| features/profile/ProfileIdentityEditor.jsx | 75 | yes |
| features/profile/ProfileKindleEditor.jsx | 132 | yes |
| features/profile/profileModel.js | 59 | yes |
| features/profile/ProfilePasswordEditor.jsx | 100 | yes |
| features/profile/ProfileReadOnlyView.jsx | 68 | yes |
| features/profile/profileSaveAction.js | 65 | yes |
| features/profile/ProfileSecurityPanel.jsx | 104 | yes |
| features/profile/useProfileDerivedState.js | 78 | yes |
| features/profile/useProfileTwoFactorActions.js | 114 | yes |

Totals: 111 files, all fully read (feature+layout+hooks ~11,013 lines, utils ~2,700, entry/api/html ~830). Note: feature folders present are only access, app, book-detail, catalog (one file), layout, library, manual-books, profile (plus processing and reader, excluded). The `features/library`, `features/catalog`, `features/manual-books` folders are helpers only; the screens live in `pages/` (other agent).

## 2. Every API call

Base: `API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api"` (api/constants.js:1). All calls via `apiFetch` (api/http.js) unless noted; `credentials: "include"` (cookie session). Callers listed are in my scope; `pages/*` callers are another agent's scope (marked "page").

| # | method | URL | caller (file:line) | purpose |
|---|---|---|---|---|
| 1 | GET | /csrf/ | api/csrf.js:12 (ensureCsrfCookie before every non-GET); api/runtime.js:72 (probeBackendHealth); BackendStatusModal.jsx:36 (poll every 6 s) | set csrftoken cookie; also used as the health check |
| 2 | GET | /auth/session/ | hooks/useSession.jsx:16 (mount, after login, logout) via authApi.session | who am I: `{authenticated,user}` |
| 3 | GET | /auth/demo-login/ | api/auth.js:6 (caller page) | demo user login (DemoLoginPage) |
| 4 | POST | /auth/login/ | useSession.login:36 (body from LoginPage) | sign in (then refreshSession) |
| 5 | POST | /auth/logout/ | useSession.logout:42 (AppShell.jsx:181,186) | sign out (then refreshSession) |
| 6 | GET | /auth/profile/ | api/auth.js:9 (ProfilePage, page) | load profile (incl. kindle_emails, kindle_sender_email, profile_image_url, role flags) |
| 7 | PATCH | /auth/profile/ (multipart FormData) | profile/profileSaveAction.js:59 | save name, photo, remove photo, kindle emails text, password change |
| 8 | GET | /auth/users/?q&status&sort&offset&limit | access/hooks/useManagedUserList.js:66 | paged managed-user table (response `{rows, pagination:{totalCount,hasMore}}`) |
| 9 | POST | /auth/users/ | useAccessUsers.js:180 | create user |
| 10 | PATCH | /auth/users/{id}/ | useAccessUsers.js:177 | edit user flags/scopes |
| 11 | DELETE | /auth/users/{id}/ | useAccessUsers.js:217 | delete user |
| 12 | POST | /auth/users/{id}/resend-setup-email/ body {} | useAccessUsers.js:241 | resend setup/invite email |
| 13 | POST | /auth/password-reset/ | api/auth.js:23 (PasswordResetPage, page) | request reset email |
| 14 | POST | /auth/password-reset/validate/ | api/auth.js:25 (PasswordLinkPage, page) | validate link token |
| 15 | POST | /auth/password-reset/confirm/ | api/auth.js:27 (PasswordLinkPage, page) | set password (reset and create modes) |
| 16 | GET | /auth/2fa/status/ | api/auth.js:28 (ProfilePage / TwoFactorSetupPage, page) | TOTP status `{enabled,required,pending_setup}` |
| 17 | POST | /auth/2fa/setup/ | profile/useProfileTwoFactorActions.js:23 | begin TOTP; returns `{provisioning_uri, secret, qr_svg}` |
| 18 | POST | /auth/2fa/confirm/ body {token} | useProfileTwoFactorActions.js:48 | confirm code |
| 19 | POST | /auth/2fa/cancel/ body {} | useProfileTwoFactorActions.js:86 | cancel pending setup |
| 20 | POST | /auth/2fa/disable/ body {} | useProfileTwoFactorActions.js:67 | turn TOTP off (only when not admin-required) |
| 21 | POST | /catalog/books/{slug}/my-books/ | api/catalog.js:8; library/useMyBooksAction.js:16; book-detail/useBookOwnershipActions.js:22 | add to My Books (returns `my_books_added_at`) |
| 22 | DELETE | /catalog/books/{slug}/my-books/ | api/catalog.js:12 | remove from My Books |
| 23 | POST | /access/books/{slug}/send-to-kindle/ body {} | api/catalog.js:16 (sendBookToKindle, page); book-detail/assetMutationActions.js:54 | email EPUB to Kindle (response `detail` message) |
| 24 | GET | /catalog/writers/?record_type&series&category&sort=name | hooks/useDynamicFilterOptions.js:35 | author options (cross-filtered) |
| 25 | GET | /catalog/series/?record_type&author&category&sort=name | useDynamicFilterOptions.js:36 | series options |
| 26 | GET | /catalog/categories/?record_type&author&series&sort=name | useDynamicFilterOptions.js:37; manualBookOptions.js:12 (record_type=all) | category options |
| 27 | GET | /catalog/writers/?record_type=all&sort=name | manual-books/manualBookOptions.js:13 | autocomplete suggestions |
| 28 | GET | /catalog/translators/?record_type=all&sort=name | manualBookOptions.js:14 | suggestions |
| 29 | GET | /catalog/editors/?record_type=all&sort=name | manualBookOptions.js:15 | suggestions |
| 30 | GET | /catalog/series/?record_type=all&sort=name | manualBookOptions.js:16 | suggestions |
| 31 | GET | /catalog/publishers/?record_type=all&sort=name | manualBookOptions.js:17 | suggestions |
| 32 | GET | /catalog/books/?{filters}&page&limit=60 | hooks/useInfiniteCatalogBooks.js:87 (default endpoint, used by Library/Home/MyBooks pages) | infinite list; payload `{entries,pagination{page,limit,total_count,page_count,has_previous,has_next}}` or bare array |
| 33 | GET | /catalog/books/?{filters}&page=N&limit=100 (loop through all pages) | library/libraryExport.js:13,20 | fetch everything for CSV/PDF export |
| 34 | GET | /catalog/manual-books/?{filters}&page&limit (infinite) | useInfiniteCatalogBooks with endpoint override (ManualBooksPage, page) | manual list |
| 35 | GET | /catalog/manual-books/?{filters}&page=N&limit=100 loop | manual-books/manualBookExport.js:13,21 | export data |
| 36 | POST | /catalog/manual-books/ body = form (price "" -> null) | manual-books/manualBookCreate.js:4 | create physical book |
| 37 | GET | /catalog/books/{slug}/ | book-detail/useBookDetailData.js:73 (fetchBook; also re-polled every 4 s while job queued/processing :237) | book detail |
| 38 | DELETE | /catalog/books/{slug}/ | useBookLifecycleActions.js:30 | delete book |
| 39 | POST | /catalog/books/{slug}/assets/epub/ (multipart `file`) | assetMutationActions.js:14 | upload/replace EPUB |
| 40 | POST | /catalog/books/{slug}/regenerate/ body {} | assetMutationActions.js:33 | regenerate (`{book,created,job{status}}`) |
| 41 | PATCH | /catalog/books/{slug}/metadata/ | metadataActions.js:28 | save title, summary, contributors[], series[], categories[], notes |
| 42 | GET | /catalog/books/{slug}/metadata-versions/ | useBookDetailData.js:93,185 | history (only if canEditMetadata) |
| 43 | GET | /catalog/books/{slug}/metadata-reviews/ | useBookDetailData.js:94,193 | review log |
| 44 | POST | /catalog/books/{slug}/metadata-reviews/ body {state,notes} | reviewAndBookmarkActions.js:21 | create review |
| 45 | PATCH | /catalog/metadata-reviews/{id}/ body {state} | reviewAndBookmarkActions.js:40 | approve / reject |
| 46 | GET | /access/books/{slug}/reading-session/ | useBookDetailData.js:105 | last_location, progress_percent, last_opened_at (401/403 -> treated as "no reader access") |
| 47 | GET | /access/books/{slug}/bookmarks/ | useBookDetailData.js:113; api/reading.js:20 | bookmarks (401/403 -> []) |
| 48 | POST | /access/books/{slug}/bookmarks/ | api/reading.js:24 (reader, other scope) | create bookmark |
| 49 | DELETE | /access/bookmarks/{id}/ | reviewAndBookmarkActions.js:7; api/reading.js:31 | delete bookmark |
| 50 | GET | /access/me/notes/?book&kind&color&q | api/reading.js:12; BookReaderSections.jsx:44 | notes aggregation: `{highlights, notes, quotes}` |
| 51 | GET | /access/me/reading-progress/ | api/reading.js:16 (page/reader) | all-books progress |
| 52 | GET | /access/books/{slug}/highlights/ | api/reading.js:36 (reader) | highlights |
| 53 | POST | /access/books/{slug}/highlights/ | api/reading.js:39 (reader) | create highlight/note/quote |
| 54 | PATCH | /access/highlights/{id}/ | api/reading.js:46 (reader/NotesPage) | edit |
| 55 | DELETE | /access/highlights/{id}/ | api/reading.js:50 (reader/NotesPage) | delete |
| 56 | GET | /access/references/?view=users or view=access | access/hooks/useAccessAdminData.js:25,29 | user list for grant dropdown + books/categories/writers/scopes |
| 57 | GET | /access/grants/ | useAccessAdminData.js:26 (only on tab "access") | grant records |
| 58 | POST | /access/grants/ body {user,scope,<book|category|contributor>:id,expires_at:null,notes:""} | useAccessGrants.js:132 (one request per scope x target) | create scoped grant |
| 59 | DELETE | /access/grants/{id}/ | useAccessGrants.js:182 | delete grant |
| 60 | POST | /access/books/{slug}/reader-launch/ body {} | book-detail/readerLaunch.js:36 | get reader manifest descriptor, then navigate to `/reader?slug&manifest&appNav=hidden` |
| 61 | any (GET default) | `downloadApiFile(path)` | api/download.js:10 (callers in pages) | fetch file as blob and trigger download via anchor; JSON-without-disposition treated as error |
| 62 | GET (window.open, not fetch) | asset `download_url` (EPUB/cover opened `_blank`; HTML preview in managed named window) | book-detail/assetPreviewActions.js:73,37 | downloads/preview, no JS fetch |

Counted: 60 distinct method+URL endpoints invoked via apiFetch (rows 1-60), plus `downloadApiFile` (generic) and window.open asset links. Rows whose only caller is outside my scope: 3, 6, 13-16, 34, 48, 51-55.

Response/error handling (api/http.js, errors.js, runtime.js, text.js):
- Content-Type JSON -> parsed, else text; 204/205 -> null (response.js:1).
- Non-2xx -> `createApiError` message from first of `detail|message|non_field_errors`, else first nested field (text.js:30-85); HTML tags stripped. `error.status`, `error.payload` attached.
- Network failure (no status) -> status 0 error + backend-down evaluation (errors.js:25).
- 0/502/503/504 -> "backend unavailable": probes `/csrf/`; if probe fails dispatches `app:backend-status {state:"down", mode}` -> BackendStatusModal. Mode "restarting" if request is `/csrf/` or `/auth/session/` or failures in window <=3 (2-min window); messages "Please try again in a few minutes. The application is getting ready." vs "There is an error. Please try again after a few hours." (runtime.js:106-113).
- 401 or 403 on any path except exactly `/auth/session/`, `/auth/login/`, `/auth/password-reset/` -> `app:session-expired` event once (runtime.js:115-136); reset on next successful call to `/auth/login/` or `/auth/session/`.
- `humanizeError` (utils/humanizeError.js) maps codes (`network_error, timeout, unauthorized, forbidden, not_found, conflict, rate_limited, validation_error, server_error, otp_required, otp_invalid`) and statuses to friendly copy; hides messages containing traceback/exception/undefined/null/TypeError/SyntaxError or >200 chars. Not used by any file in my scope (callers presumably pages); most hooks show `error.message` raw.

## 3. Per feature folder: user-visible actions and states

### 3.0 App shell, routing (App.jsx, layouts/AppShell.jsx, features/app, features/layout)
- Provider order (main.jsx:14-22): BrowserRouter > SessionProvider > ToastProvider > BookProcessingProvider > App. `bootstrapTheme()` before render (main.jsx:11). `App` renders: AppShell wrapping RouteScrollReset, SessionRestartHandler, BackendStatusModal, ErrorBoundary>AppRoutes, floating ThemeToggle + ScrollToTopButton (App.jsx:12-23).
- AppShell: skip link "Skip to main content" -> `#main-content` (AppShell.jsx:191). Decorative left/right ornaments hidden in reader route. Topbar hidden when on `/reader` unless `?appNav=shown` (AppShell.jsx:27-30); in reader a floating "Hide reader header" button sets `appNav=hidden` with replace-navigate (hideReaderTopbar :163; ReaderTopbarHideButton aria-label "Hide reader header", test id reader-hide-header-button).
- Minimal topbar (no nav, no session box) on `/create-password` and `/two-factor-setup` (AppShell.jsx:25-31,56).
- Close-everything-on-route-change effect (:61-68); outside mousedown closes profile, Book Properties, Processing dropdowns (:70-100); mobile nav: Escape closes (:107), closes when viewport >=981px (:124), body class `app-mobile-nav-open` (:138), auto-expands the group that matches the active route (:150-161).
- AppTopbar.jsx: brand link "RSalehin24 Library" -> `getHomePath(user)` (:51). Mobile hamburger (aria "Open menu"/"Close menu", test id mobile-nav-trigger). Desktop nav (only when authenticated and not minimal): primary links, "Book Properties" dropdown, "Processing" dropdown (only if user has processing items), secondary links. Session box: superuser sees "My Books", "Kindle", "My Notes" links (:119-146); non-superuser sees "All Books" (/home) and "My Notes" (:147-166); then ProfileMenu. Unauthenticated: "Sign in" link (hidden on /login).
- ProfileMenu.jsx: avatar button (photo or 2-letter initials, aria "Open/Close profile menu", test id profile-menu-trigger); dropdown shows name, email, "Profile" link, "Alerts" switch (checked = not muted; label "On"/"Off"; test id profile-alerts-toggle; toggles `toast.muted`, persisted), "Sign Out" button.
- MobileNavigationPanel.jsx: backdrop button, panel with profile summary and close "Close menu", primary links, superuser extra links My Books/Kindle/My Notes, secondary links, collapsible groups "Book Properties" and "Processing", then session links (non-superuser: All Books, My Notes), Profile, Alerts switch (test id mobile-profile-alerts-toggle), "Sign Out".
- NavDropdown.jsx: aria-expanded/haspopup menu button, panel of NavLinks.
- BackendStatusModal.jsx: modal `role=alertdialog` "There is an error." + "Please wait a few minutes while the server restarts." (mode restarting) or "Please wait a few hours and try again." On mount and every 6 s polls `/csrf/` (:48-49); when down shows overlay; while shown polls every 5 s; on recovery, if it had ever been down it does `window.location.reload()` (:14,66). No dismiss button.
- SessionRestartHandler.jsx: on `app:session-expired`: `expireSession("The application has restarted. Please log in again.")`, toast.info same text, navigate `/login` replace with state `{from, reason:"app-restarted"}` unless already on /login.
- RouteScrollReset.jsx: sets `history.scrollRestoration="manual"`; scrolls to top on pathname change (document, html, body, window; plus next animation frame) except `/reader` or when URL has a hash.
- ProtectedRoute.jsx: while session loading -> PageLoader "Loading your session / Checking sign-in and workspace access."; not authenticated -> `<Navigate to="/login" replace state={{from: pathname}}>`; `user.totp_setup_required` and not on `/two-factor-setup` -> Navigate to `/two-factor-setup` with state.from.

### 3.1 AppRoutes (features/app/AppRoutes.jsx:32-130) route table
Public: `/login`, `/demo-login`, `/reset-password`, `/reset-password/confirm` (PasswordLinkPage mode reset), `/create-password` (mode create). Redirects: `/created-books -> /my-books`, `/compilers -> /editors`, `/processing, /processing-catalog-books, /processing-automation -> /catalog`, `/processing-my-requests, /queue -> /create`, `/processing-failed-requests, /processing-duplicate-requests -> /on-hold`, `/processing-incomplete-check -> /incomplete`, `* -> /`. `/` (protected) -> HomeRedirect to `getHomePath(user)`.
Protected (each wrapped in ProtectedRoute, auth only): `/home /catalog /create /on-hold /incomplete /multipage-toc /reprocessing /library /categories /series /writers /translators /editors /publishers /manual-books /my-books /kindle-sent /books/:slug /access /profile /notes /two-factor-setup /reader`. Note: there is no `/books/:slug/read` route (see bugs).

### 3.2 hooks (global state)
- useSession: state `{loading,authenticated,user,error}`; fetch on mount; `login(body)`; `logout()`; `expireSession(msg)`; `refreshSession()`.
- useToast: `show/info/success/error/dismiss/muted/setMuted/toggleMuted`; auto-dedupe by `type:title-or-description` groupKey (useToast.jsx:38-54); sound plays unless muted; toasts default 3600 ms (`toastManager.js:16`), `holdOpenMs` override; same groupKey updates in place and reschedules, no new sound. Titles default "Success"/"Something went wrong"/"Notice"; string input becomes description.
- Notification sound: WebAudio two-tone presets for success/error/info (notificationAudio.js:3-28).
- useDialogA11y: focus first focusable, Tab trap, body scroll lock, Escape closes unless `locked`, restores focus.
- useAsyncAction: single in-flight action gate keyed by string; returns `pendingKey`.
- useInfiniteCatalogBooks: page size 60 (`CATALOG_TABLE_BATCH_SIZE`), IntersectionObserver trigger 240 px before end (root = table shell), sequence guard to drop stale responses, keeps old rows while refreshing, exposes `prependEntry/updateEntry/removeEntry/reload/loadMore`; error string default "Unable to load records."; resets state on endpoint/filter change.
- useDynamicFilterOptions: cross-filtered author/series/category lists; clears any selected value that is no longer valid (resets filters via setFilters), logs `console.error` on failure, silent otherwise.
- usePageTitle: `"{segment} · eLibrary"`, restores on unmount.
- useSessionFlag: boolean in sessionStorage ("1"/"0").
- useTheme: see section 7.

### 3.3 features/access (Users & Access admin; page consumes these)
- AccessHero: title "Users & Access"; two tab buttons "Users" (test id access-users-tab) and "Access Rules" (access-rules-tab) with aria-pressed. Tab stored in URL `?tab=users|access` (useAccessTabs; invalid value normalised to `users`, URL rewritten with replace).
- AccessUsersTableCard (Users tab): header "Users", search input (placeholder "Search users by name, email, status, or permission..."; clearing input resets), "Filter" select (all / active / disabled / totp_required -> "All users, Active, Disabled, Two-factor required"), "Sort" select (name_asc, name_desc, email_asc, email_desc, status), result count; skeleton rows (5 initial, 3 incremental); infinite scroll trigger on row `len - 30`; columns Name, Email, Status (Active/Disabled), Two-Factor (Required/Enabled/Optional), Account Permissions (chips of scope labels sorted, or "-"), Actions. Row actions: "Locked" label if the row is the current user or a superuser; else "Resend Email" (only if `entry.can_resend_setup_email`; shows "Sending..."), "Edit", "Delete". Empty/error cell: `usersError` or "No users found for the current search and filter."
- Delete confirmation: `requestDeleteUser` stores `pendingDeleteUser`; a confirm dialog is rendered by the page (ConfirmDialog not in my scope); `confirmDeleteUser` -> DELETE then toast "User deleted." and reload.
- AccessUserEditorCard: heading "Create User" / "Edit User" (+ "Cancel" when editing). Fields: Name (disabled/readonly when editing), Email (type=email, required on create, disabled when editing, live feedback via EmailInputFeedback, invalid aria), Password Setup: when editing -> disabled input "Password changes are disabled here"; when "Send Setup Email" on -> note "A setup email with a password-reset link will be sent after the account is created."; else password field with Show/Hide, "Generate new password" (↻, also copies to clipboard, toast "Suggested password copied."), "Copy password" (⧉; toast error "Generate or enter a password first." when empty). Option cards: "Send Setup Email" (create only; default true; checking clears password), "Active Account" (default true), "Require Two-Factor" (default false). "Account Permissions" with "All Permissions" and "Clear" buttons and a checkbox grid of account scopes (from server `account_scopes`); `read:once` and `read:durable` are mutually exclusive (useAccessUsers.js:70-74). Submit "Create User"/"Save User" (spinner "Creating..."/"Saving..."), disabled while submitting or on create with invalid email.
- Validation (useAccessUsers.js:126-154): form `reportValidity()`; create: valid email regex else toast "Enter a valid email address."; create without invite: password required ("Enter a password or send an invite email."); at least one account permission always ("Select at least one account permission."). Create payload: email, full_name, send_invite_email, password (only if not invite), is_active, totp_required, global_scopes. Edit payload: only is_active, totp_required, global_scopes. Errors via `formatApiError` with labels (global_scopes -> "Account permissions", email, password, is_active -> "Active account"). Success toasts: "User updated.", "User created. Setup email sent." / "User created.", "Setup email sent.". After success reloads `/access/references` and the user list.
- Edit starts: form prefilled, switches to users tab, smooth-scrolls to editor.
- Password generator: 18 chars from `ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%^&*` using `crypto.getRandomValues` (Math.random fallback), note `value % 64` modulo bias (utils.js:3-18).
- Access Rules tab: AccessGrantEditorCard "Access Control": User select (excludes current user), Permission checkbox grid (scoped scopes; read:once/read:durable exclusive), "Applies To" toggle Books / Categories / Writers (switching clears selection and search), search box (`Search books|categorys|writers` - pluralised by appending "s": "Search categorys" typo-style bug, AccessGrantEditorCard.jsx:110), checkbox list, "No matches found.", "No scoped permissions are available.", button "Save Access"/"Saving...". Validation toasts: "Select a user first.", "Select at least one permission.", "Select at least one target.", "These access rules already exist." Duplicates skipped (reports "Access updated. Skipped N existing rule(s)."). Request per scope x target (parallel `Promise.all`, not atomic). Target field mapping: book->`book`, category->`category`, writer->`contributor`.
- AccessGrantRulesCard "Current Rules": table User, Permission, Scope (target_label), Actions; own rows show "Locked"; "Delete" uses native `window.confirm("Remove {scope label} from {email}?")` (useAccessGrants.js:172), toast "Access removed."; empty text "No scoped access rules yet." Only grants having book/category/contributor are shown (global grants filtered out, useAccessAdminData.js:70-76).
- useAccessAdminData: loads only if `isSuperAdmin`; users tab -> `/access/references/?view=users`; access tab -> `references/?view=access` + `/access/grants/`. Error -> toast.

### 3.4 features/book-detail (BookDetailPage consumes)
- Hero: Book ID (catalog_code or "Pending"), title, primary contributor (authors as `?author=` links, otherwise labelled role as `?contributor=` links; "Contributor unavailable" if none), supporting contributor groups, Series and Categories as filter links to `/library?...` (carries `record_type=manual` for manual books). Status pills (state, review_state) only for digital books.
- Editors (canEditMetadata) controls: Regenerate icon button (hidden for manual books; spinner while regenerating or active processing; disabled in those states), Delete icon button (disabled while deleting or active processing) -> opens delete confirm dialog (page renders; `confirmDeleteBook`: DELETE, toast "Book deleted.", navigate to `returnTarget` or `/library` with replace).
- Digital book actions: "Open reader" (disabled when `can_launch_reader === false`; "Opening..."; calls reader-launch then navigates `/reader?slug=..&manifest=..&appNav=hidden`; error toast "Reader manifest is not available for this book yet." if no manifest; "Missing reader details. Open a book and try again." if no slug), "Add to My Books"/"Remove from My Books" (toasts "Added to My Books."/"Removed from My Books."), "Send to Kindle"/"Resend to Kindle" (shown only if EPUB asset exists and user has a Kindle email; disabled while sending or processing; toast `payload.detail || "Sent to Kindle."`; then refetches book), "Edit Book" (editor only), asset buttons for every asset with `download_url`: label from `assetLabels` (`html` "Preview HTML", `epub` "Download EPUB", `cover` "Download cover"), "Preparing..." state; HTML preview button shows "Preview Open" and is disabled if a preview window is already open (cross-tab lock) or `can_view_preview_html === false`; "Replace EPUB"/"Upload EPUB" (hidden file input `.epub,application/epub+zip`; "Selecting..." while OS picker open, "Uploading..."; disabled during processing/regeneration). Manual books: only My Books, Edit Book.
- HTML preview: opens a named window `html_preview_{userId}_{bookId}` (popup-blocked toast "Preview window could not be opened. Please allow popups."; re-click focuses existing window with toast "Preview is already open for this book."); lock polled from localStorage keys `ebook_preview_lock:{pathname}` with 15 s TTL, every 1.5 s plus storage/focus/visibility events. Non-HTML assets open `_blank` with `noopener,noreferrer`. Artificial minimum 420 ms loader.
- Processing note: when latest job exists and is active/failed shows "Regenerating book" (job_type reprocess) / "Processing book", body "New book files are being prepared. This page refreshes automatically while the job is running." or `last_error` / "The latest processing job failed."; page polls the book every 4 s while job status is queued/processing.
- BookMetadataWorkspace (editor only): form Title, Summary (4 rows), Contributors textarea "Name|author" one per line (role default author), Series (comma list), Categories (comma list), "Edit note"; button "Save metadata" -> PATCH; toast "Metadata updated."; if slug changes, route replaced. Review form: state select (pending "Awaiting review", needs_review "Needs review", approved "Reviewed", rejected "Needs correction") + Notes, "Save review" -> "Review saved."; "Metadata History" list (source, notes or "No notes", date; empty "No history yet."); "Review Log" list with per-review "Approve"/"Reject" buttons (toast "Review updated."); empty "No reviews yet.".
- BookTocSummary: recursive nested cards; pills for type and content state ("Content ready", "No content on source" when has_content null, "TOC only" when false); fallback label `Section {n}`.
- BookReaderSections: "Reading" card with Progress %, Last location ("Not synced"), Last opened; if no reader access: "Syncs after reading." Four note cards shown only if non-empty: Bookmarks (delete button 🗑, spinner), Notes (API "highlights"), Annotations (API "notes"), Quotes; empty overall "No bookmarks, notes, or quotes yet."; loading spinner; error text; link "Manage all notes →" to `/notes`; each item "Open in reader →" (to `/books/{slug}/read`, broken).
- PhysicalBookWorkspace (manual books): spec grid (Publisher, Binding "Hard Cover"/"Paper Back", Price `৳ x.xx`, Compilation Yes/No, Language English/বাংলা) and "My Reading Log" (status Unread/Reading/Finished buttons, current/total pages with auto status logic, progress slider + bar, start/finish dates, 1-5 star rating click-again to clear, notes textarea, "Save Progress" -> toast "Reading log saved successfully.", "Reset Log" -> `window.confirm("Are you sure you want to reset your reading log for this book?")`, toast "Reading log reset."). Stored ONLY in localStorage per slug (no server).
- Supporting metadata: front matter dedupe/normalisation (identity labels "unique id/book id/catalog code/catalog id/id" collapsed into one "Book ID" entry), extracted entries from contributors/series/categories/front matter, source records fallback from `source_urls` (utils.js:32-186).

### 3.5 features/profile (ProfilePage consumes)
- Read-only view: avatar/initials, name, email, role pill ("Super Admin" if is_superuser, "Staff" if is_staff, else "User"), rows Name, Email, Role, Two-Factor ("Set up"/"Not set up"), Kindle Mails (list or "Not set", only when user can send to Kindle).
- Edit form: photo upload (`accept="image/*"`, "Upload profile photo", "Remove Photo"), Name (editable), Email (disabled), collapsible "Change Password" (Current/New/Confirm with Show/Hide toggles; autoComplete current-password/new-password), collapsible "Kindle Mails" (only if canSendToKindle) with instructions about allowing the sender email in Amazon "Manage Your Content and Devices > Preferences > Personal Document Settings" and disabling "Personal Document Archiving" for multiple emails; per-row email input with live feedback ("Kindle email looks good."; invalid: "Enter a valid email address." or "Use a Kindle email ending in @kindle.com."), delete row (when >1), add row (disabled unless all rows valid). "Save Changes" disabled when saving, no changes, or invalid Kindle email.
- Save validation (profileSaveAction.js:27-42) toasts: "Enter your current password to change it.", "Enter a new password.", "The new password fields must match.", Kindle invalid message. Body is multipart FormData: `full_name`, `profile_image`, `remove_profile_image=true`, `kindle_emails_text` (newline-joined), `current_password`, `new_password`, `confirm_new_password`. After success: reset editor, refreshSession, toast "Profile updated." No client-side password strength rules.
- Security panel: status pill, rows Status / Requirement ("Required by admin"/"Optional") / Method ("Authenticator app"/"Not configured"); buttons "Setup Authenticator"/"Hide Setup"/"Preparing...", "Turn Off" (only enabled-and-not-required; "Turning off..."); no confirmation dialog on Turn Off. Setup panel (component TwoFactorSetupPanel, other scope) with QR, secret, copy URL ("Setup URL copied."/"Could not copy the setup URL."), token submit, cancel. Success toasts "Two-factor enabled." / "Two-factor disabled."; error feedback inline (setup/cancel) or toast (confirm/disable).

### 3.6 features/manual-books (ManualBooksPage consumes)
- Toolbar: icon buttons "Export options" (toggles export row; aria-expanded) and "Add manual book"/"Close add book form" (+ icon, accent).
- Composer form (id `manual-book-composer`): Title; TagInputs Writer, Translator, Editor, Category ("Select or create"), Series, Publisher (single value: last tag wins); selects Compilation No/Yes, Binding (Select / Hard Cover / Paper Back; default `hard_cover`), Language (বাংলা `bn` default / English `en`); Price (number min 0 step 0.01, "" -> null); Summary textarea. Buttons: "Add & next" (or "Save" when editing; "Adding..."/"Saving..."), "Clear fields" (resets to `emptyManualBookForm`), "Done". Placeholders "Loading..." while suggestions load. Keyboard: Ctrl/Cmd + ArrowRight/ArrowLeft jumps to next/previous field in the fixed sequence Title, Writer, Translator, Editor, Category, Series, Compilation, Binding, Publisher, Price, Language, Summary (ManualBookComposer.jsx:41-86). No required-field validation in this component (title validation presumably in page/server).
- Filters: writer, translator, editor, category, publisher (text), binding select (Any/Hardcover/Paperback), sort select (-created_at default, created_at, title, -title, manual_publisher, -manual_publisher); defaults `record_type:"manual"`, `ownership`.

### 3.7 features/library
- Filters: `q`, `author` ("Contributor"), `series`, `category`, `contributor`, `contributor_role`, `ownership` (All books / My books = `mine`), `record_type` (digital default / manual / all), `sort` (-created_at "Newest first", created_at, -requested_at "Newest request first", requested_at, catalog_code, -catalog_code, title, -title).
- SavedFilterStrip: chip per saved filter (apply -> "Applying...", delete `×` with aria "Delete {name}", `…` while deleting); hidden if none. (Saved filters API is not in my files: persistence is in the page or removed.)
- useMyBooksAction: toggles My Books on a row with optimistic-after-success update (`is_in_my_books`, `my_books_added_at`) and the same toasts; errors toast raw `error.message`.

### 3.8 features/catalog
- Only `exportUiTiming.js`: `waitForExportUi` (two rAFs so loader paints) and `waitForMinimumLoader(startedAt, 240)`.

## 4. Navigation and permission gating (exact rules)

Capability check (utils/capabilities.js:1-12): `hasCapability(user, scope)` is true if user exists AND (`is_superuser` OR `is_staff` OR `capabilities` includes `admin:full_control` OR includes `scope`). Used in AppShell only (`processing:manage`, `physical_books:view`).

navigation.js:
- `getHomePath(user)`: `is_superuser` -> `/home`, else `/my-books`. Used for brand link and `/` redirect. (Unauthenticated `/` -> `/login` via ProtectedRoute.)
- `bookPropertiesItems`: Books `/library`, Categories `/categories`, Series `/series`, Writers `/writers`, "Physical Books' List" `/manual-books` (capabilityRequired -> `physical_books:view`). Dropdown shown to every authenticated, non-minimal user.
- `processingItems` (all capabilityRequired -> `processing:manage`): Catalog `/catalog`, Create `/create`, On Hold `/on-hold`, Incomplete `/incomplete`, Multi-page TOC `/multipage-toc`, Reprocessing `/reprocessing`. Dropdown rendered only if at least one visible.
- `primaryNavigation(user)`: superuser -> Home `/home`, Users & Access `/access`. Non-superuser -> My Books `/my-books` always; plus Kindle `/kindle-sent` only if `capabilities` includes `admin:full_control` or `send:kindle` (is_staff does NOT grant it here, unlike hasCapability).
- `secondaryNavigation(user)`: superuser -> none; others -> Users & Access `/access` only if capabilities includes `admin:full_control` or `access:manage`.
- Session-box extras (AppTopbar.jsx:119-166): superuser: My Books, Kindle, My Notes (always, regardless of capability); non-superuser: All Books (`/home`) + My Notes.
- `authenticatedNavigation` (full lists: superuser Home, Users & Access; others My Books, Kindle, All Books, Users & Access, My Notes unconditionally) is computed in AppShell and passed as `navigation` prop but never used by AppTopbar/MobileNavigationPanel; `hasNotesLink` unused. Dead code that contradicts the live rules.
- Route-level gating: ONLY authentication (`ProtectedRoute`) and forced TOTP setup redirect. There is no client-side role/capability guard on any route (`/access`, `/catalog`, `/create`, `/manual-books`, `/home` etc. are reachable by URL by any logged-in user; enforcement relies on server returning 403 -> which triggers the global session-expired handling, see bugs). Access admin hooks gate data load on `isSuperAdmin` passed by the page.
- Component-level gating in my scope: book-detail edit controls via `canEditMetadata` prop (computed in page, not in my files), Kindle button via `hasKindleEmail` prop and EPUB asset presence, My Books actions on all books, HTML preview via `can_view_preview_html`, reader via `can_launch_reader`, account actions locked for self and superusers (`entry.is_superuser`), grant editor excludes self, `can_resend_setup_email` flag from server, profile Kindle section via `canSendToKindle` (page-computed), Turn Off 2FA hidden when `twoFactor.required`.
- Reader route: topbar hidden by `appNav` param; `/two-factor-setup` and `/create-password` minimal topbar.

## 5. Auth / session / CSRF / 2FA client flow
1. App mount: SessionProvider calls GET `/auth/session/`; `loading:true` until it returns. Failure -> `authenticated:false` with `error` message (network down also triggers BackendStatusModal).
2. ProtectedRoute: loader -> `/login` (with `state.from`) -> forced `/two-factor-setup` when `user.totp_setup_required`.
3. CSRF: Django cookie `csrftoken`. Before any non-GET/HEAD/OPTIONS call `ensureCsrfCookie()` does GET `/csrf/` (de-duplicated promise) then header `X-CSRFToken` is read from `document.cookie`. A fetch is done on EVERY mutating request (no caching of the "ready" state: promise reset in `.finally`), so every POST costs a GET first. FormData requests skip JSON content-type (browser boundary).
4. Login: `useSession.login(body)` POST `/auth/login/` then GET `/auth/session/`. OTP handling (`otp_required`/`otp_invalid` codes appear in humanizeError) is within LoginPage (not in my scope); no client TOTP logic in these files other than setup. `/auth/demo-login/` GET exists for demo page.
5. Logout: POST `/auth/logout/` then session refresh (-> unauthenticated). Topbar closes menu first. No redirect code in AppShell; ProtectedRoute handles it on next render.
6. Session expiry: any 401/403 (outside the three exempt paths) fires `app:session-expired` once; SessionRestartHandler clears session and redirects to /login with the "application has restarted" message regardless of the true cause. Re-armed after successful `/auth/login/` or `/auth/session/`.
7. TOTP self-service (Profile): setup -> POST `/auth/2fa/setup/` returns provisioning_uri, secret, QR SVG; confirm with `{token}`; cancel; disable. After confirm/disable `refreshSession()` then reload profile. Required TOTP (admin flag `totp_required`) forces `totp_setup_required` redirect and hides Turn Off.
8. Password: reset request, link validation and confirm are three POSTs (page). Admin invite uses "setup email with password-reset link". Profile password change sends current + new + confirm in the same PATCH multipart.
9. Backend health: `/csrf/` GET doubles as health probe; 6-second polling for the entire session lifetime.

## 6. Export features (CSV / PDF / Excel)

Data collection:
- Library (digital/manual/all): `loadLibraryBooksForExport(filters)` pages `/catalog/books/` at limit 100 sequentially (page 1 then 2..page_count) using the active filters (libraryExport.js).
- Manual books: same via `/catalog/manual-books/` (manualBookExport.js).
- Gate (`utils/export.js:getExportBlockState`): blocks with error message if list errored; "Wait until the {nounPlural} list finishes loading before exporting." while loading; "There are no {nounPlural} to export." when empty; "A {singular} is still processing. Export after processing finishes." / "{n} {plural} are still processing..." if any item has `state === "processing"`. Type "error" or "info" (shown as toast by pages).
- Pending-export resume (`utils/exportSession.js`): sessionStorage key from caller (`catalog-books-export` for library, `manual-books-export` for manual; constants in libraryFilters.js:1 and manualBookFilters.js:1). Payload `{mode, items[], startedAt}`; discarded if malformed or older than 10 minutes. Purpose: resume an export after a reload/mode change.
- UI timing: two rAF wait then minimum loader 240 ms (`catalog/exportUiTiming.js`).

Row model (`utils/bookExport/rows.js`): catalogCode, title, contributors (= `getBookIdentityContributorLine`: authors, then "Translator: ..", "Editor: ..", "Publisher: .." joined " · ", fallback "Contributor unavailable"), authors, translators, editors, publishers (role `publisher` contributors), categories (", "), series (", "), type ("Manual" if `record_type==="manual"` else "Digital"), price (string or ""), state, review (`review_state`), createdAt (`formatBookDate`: `en` locale "Mon D, YYYY").
Contributors are normalised (NFKC, trim, case-fold dedupe by name|role, `compiler` -> `editor`, an author who is also non-author is dropped).

CSV (`csv.js:exportBooksToCsv(books, filename)`): header exactly `Book ID, Title, Writer / Translator / Editor / Publisher, Writers, Translators, Editors, Publishers, Categories, Series, Price, Type, State, Review, Created At`. Escaping: quote if value contains `"`, `,` or `\n` (not `\r`); doubles quotes. UTF-8 BOM (`﻿`) prepended, `\n` line breaks, `text/csv;charset=utf-8`. No formula-injection guard (values starting `=`,`+`,`-`,`@`). `downloadBlob` via temporary anchor, revoke after 1 s.

PDF (`pdf.js:exportBooksToPdf(books, title, groupBy="")`): fully client-side with no library. Renders each page on a 2D canvas (logical 1320x934, scale 2) -> JPEG (quality 0.92) -> hand-written PDF 1.4 with one image XObject per page, MediaBox 842x595 (A4 landscape). Output is an image: text not selectable/searchable, large file size. Layout constants in `constants.js`: margins 40/34, header 36 px, row min height 42, 6 line cap per cell with ellipsis, 8 columns (widths 100 ID, 230 Title, 280 Contributors, 140 Category, 120 Series, 80 Price, 90 Type, 200 Created; note sum 1240 = canvas minus margins 1240). Defaults for empty cells: ID "Pending", title "Untitled", contributors "Contributor unavailable", category "Unsorted", series "Standalone". Page chrome: title (26 px), "{n} books exported", date (locale short) and "Page N"; fonts "Avenir Next", "Noto Sans Bengali", "Hind Siliguri", sans-serif. Optional grouping (`category|publisher|binding|language|contributor`) inserts group header rows "{Capitalised groupBy}: {label}"; a book with multiple categories/contributors appears under each. Filename `slugifyFilename(title).pdf` (`[^a-z0-9]+` -> "-", fallback `books-export`): a Bengali-only title becomes `books-export.pdf`. Footer count uses `books.length` (not the number of rows after multi-group duplication).
Excel (`excel.js:exportManualBooksToExcel(books, groupBy, filename="manual-books.xlsx")`): manual books only; handwritten minimal OOXML + ZIP "store" (no compression) with CRC-32; all cells are shared strings (no number/date types; price is text). Headers: Book ID, Title, Writer(s), Translator(s), Editor(s), Publisher, Category, Binding (Hardcover/Paperback), Language (Bengali/English), Price, Created At. One sheet "Physical Books", or one sheet per group (sheet name sanitised: `\ / : * ? [ ]` -> `_`, max 31 chars, empty -> `SheetN`; duplicate sheet names after truncation are not de-duplicated -> invalid workbook risk). Group keys "(None)" fallback; multi-valued fields duplicate books across sheets. Strips XML-illegal control characters. The doc comment says "for Google Docs compatibility".

## 7. Theme, local/session storage keys, URL query params

Theme (hooks/useTheme.js): values `light | dark | system`; default `dark` when nothing stored or invalid (note: `readStoredTheme` default "dark", not "system"). `index.html` has `<html data-theme="dark">`. `system` removes the `data-theme` attribute (CSS media query decides); `matchMedia('(prefers-color-scheme: dark)')` listener keeps `resolvedTheme`. Applied before first render (`bootstrapTheme`). UI control: `components/ThemeToggle` (other scope) floating bottom-right.

localStorage:
- `elibrary:theme` (light|dark|system).
- `app.notifications.muted` ("1"/"0") (toast sound mute / "Alerts" switch).
- `elibrary_physical_reading_log_{slug}` (JSON: status, currentPage, totalPages, rating, startDate, finishedDate, notes).
- `ebook_preview_lock:{pathname}` (read only here; JSON `{tabId, ts}`; active if < 15 s old). Written by the HTML preview (not in my files).
sessionStorage:
- `catalog-books-export`, `manual-books-export` (pending export, 10-min TTL) via exportSession.
- `useSessionFlag(key)` boolean flags (keys supplied by callers in pages).
Cookies: `csrftoken` (read), session cookie via credentials include.

URL query params / location state in my scope:
- `/reader?slug=&manifest=&appNav=hidden|shown` (`appNav` default hidden when launched from book detail; topbar shown only when `appNav=shown`; `manifest` is a URL which may itself contain `manifest` param, normalised by `normalizeAppUrl`).
- `/access?tab=users|access`.
- `/library?author|contributor|series|category=...[&record_type=manual]` built by BookFilterLinkList; full library filter keys listed in 3.7; manual keys in 3.6; `filtersFromSearchParams(defaultFilters, searchParams)` only reads keys present in defaults (query.js:27).
- API list query strings built by `toQueryString` (drops empty/null; trims).
- Location state: `{from: pathname}` on login redirects; `{from, reason:"app-restarted"}` on session expiry; book route replacement preserves `location.state`.
- Page title pattern `"{segment} · eLibrary"`; static title "RSalehin24 Library" (index.html); brand mark "RSalehin24" + "Library".

## 8. Bugs, duplication, surprises

Bugs/risks:
1. Any 401 or 403 on an ordinary API call (including a legitimate permission-denied 403, e.g. user hits `/access/grants/` or a catalog admin action without rights) triggers the global "application has restarted, log in again" flow: session cleared in the client and redirect to /login (runtime.js:115-127 + SessionRestartHandler). The server session is NOT actually invalidated. Rebuild must distinguish 401 (unauthenticated) from 403 (forbidden).
2. Broken links: BookReaderSections uses `/books/${slug}/read` (4 places) but no such route exists; `*` redirects to `/` -> home redirect. Readers are at `/reader?...` and need a reader-launch call.
3. No route-level authorisation: any signed-in user can open `/access`, `/catalog`, `/create`, `/manual-books`, etc.; only nav hiding. Inconsistent capability rules: `hasCapability` honours `is_staff` and `admin:full_control`; `primaryNavigation`/`secondaryNavigation` ignore `is_staff`; superuser nav shows Kindle and My Books links without capability checks.
4. Dead/duplicated nav code: `authenticatedNavigation`, `hasNotesLink`, `navigation` prop unused; `isLoginRoute`, etc.
5. Access grant target search placeholder is built as `Search ${targetType}s` -> "Search categorys".
6. Access: `read:once`/`read:durable` exclusivity enforced client-side only; the user list is fetched twice (`/auth/users/` paged for the table and `/access/references/?view=users` for the grant dropdown).
7. Grants: N x M parallel POSTs, non-transactional; partial failure leaves a mix with only a generic error toast.
8. CSRF: `ensureCsrfCookie` issues an extra GET `/csrf/` before every mutation.
9. `apiFetch` serialises body only if truthy (`options.body ? JSON.stringify : undefined`): falsy bodies (0, "", false) are dropped.
10. Excel export: no de-duplication of truncated sheet names; all cells strings; ZIP without compression; CSV has no formula-injection protection and does not quote `\r`.
11. PDF export is image-only (not accessible/searchable); header says "{books.length} books exported" even with group duplicates; filename for non-Latin titles collapses to `books-export.pdf`.
12. Password generator modulo bias; client has no password policy (only presence/match).
13. ProfileKindleEditor nests `<p>` inside `<p>` (invalid HTML) and hard-codes key by index for email rows (focus loss on delete).
14. Profile `useProfileDerivedState`: `hasProfileChanges` compares serialized emails to `profile.kindle_emails.join("\n")` (trim differences ok) - OK; `twoFactorStatusLabel` maps `enabled` to "Set up".
15. `useDynamicFilterOptions` uses an effect with `setFilters` identity dependency and a ref cache key; builds URLs with unencoded `record_type`; on error only logs to console.
16. `useManagedUserList` effect keys on `fetchUsers` which depends on `userListFilters` (re-fetch on every filter keystroke, no debounce) - search triggers one request per keystroke (page/hook has no debounce in these files).
17. `BackendStatusModal` polls `/csrf/` every 6 s for the whole session (constant background traffic) and force reloads the page on recovery (loses unsaved form state).
18. `useSession` memo depends on `[session]` only while functions are recreated each render (fine) but `login` ignores the OTP flow here.
19. Physical-book reading log lives only in `localStorage` (lost on another device/browser) while the rest of reading progress is server-side.
20. `PhysicalBookWorkspace` uses `parseInt` logic that allows `currentPage > totalPages` to flip to "finished" even when totalPages typed later; `window.confirm` used for reset.
21. `BookDetailHero`: preview-lock reading uses `localStorage` of other tabs with 15 s TTL; stale lock keys never deleted by this code.
22. Title mismatch: index.html "RSalehin24 Library" vs `usePageTitle` base "eLibrary".
23. `PhysicalBookWorkspace` and `BookReaderSections` use emoji as icons (🔖 📝 💬 ❝ 🗑 📖).
24. Mixed confirmation mechanisms: native `window.confirm` (grant delete, reading-log reset) vs custom dialogs (user delete, book delete).
25. `humanizeError` exists but almost all hooks surface raw `error.message`.

Duplication:
- `groupBooks`, `bindingLabel`, `languageLabel` copied in `excel.js` and `pdf.js`; `initialsForUser` in `layout/utils.js` and `profile/profileModel.js`; `waitForMinimumLoader` in `catalog/exportUiTiming.js` and `book-detail/utils.js` (different defaults 240/320) with `waitForUiFrame`/`waitForExportUi`; `loadLibraryBooksForExport` vs `loadManualBooksForExport` identical except path; add/remove My Books logic duplicated in `useMyBooksAction` and `useBookOwnershipActions`; contributor toggling logic duplicated in `useAccessUsers`/`useAccessGrants`; `ProfileMenu` alerts switch duplicated in MobileNavigationPanel; `*Fetch` wrappers (`catalogFetch`, `accessFetch`, `bookDetailFetch`) are all `apiFetch`.

Surprises worth carrying to the rebuild:
- Business meaning of terms: "Notes" in UI = API "highlights"; "Annotations" = API "notes"; plus "Quotes".
- Kindle: only `@kindle.com` addresses accepted client-side; multiple Kindle emails per user with serialized newline text.
- Roles: `is_superuser` determines the whole home/nav layout; capability strings seen: `admin:full_control`, `processing:manage`, `physical_books:view`, `send:kindle`, `access:manage`, scopes `read:once`, `read:durable`; grants per book/category/contributor (writer).
- Record types: `digital`, `manual`, `all`; digital states `draft, processing, queued, ready, published, archived`, review states `pending, needs_review, approved, rejected`; processing job states `queued, processing, succeeded, failed, cancelled/stopped`; other statuses in `meta.js`: `pending_resolution, ambiguous, duplicate, new, unfinished, deleted`.
- Book slug can change after metadata save/regenerate/EPUB replace; clients must re-route.
- Currency symbol `৳` and Bengali (`bn`) default language for physical books.
- Created-books notification buffer util: batch "N books created." toast every 3 minutes (`processingCreatedNotificationBuffer.js`) used by processing store (other scope).

## 9. Unread files and why
None of my assigned files were left unread. Excluded by assignment and not read: `features/processing/**`, `features/reader/**` (note `features/book-detail/readerLaunch.js` imports `../reader/manifest.js:resolveReaderManifestUrl` which I did not read), `styles/`, `pages/`, `components/`, `embedded-reader/`. Behaviour that lives in those (page-level wiring, `canEditMetadata` computation, ConfirmDialog, TagInput, TwoFactorSetupPanel, login OTP form, saved-filter persistence) is therefore described only as far as the props/hook usage in my files shows.
