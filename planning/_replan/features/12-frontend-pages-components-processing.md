# 12 - Legacy frontend: pages/, components/, features/processing/

Status: DRAFT (research evidence; read-only record)

Root: `archive/app/frontend/src`. Read-only reading, React (JSX) + react-router-dom. All paths below are relative to that root. Scope: `pages/` (21 files), `components/` (30 files), `features/processing/` (25 files). Not covered: `styles/`, `embedded-reader/`, and the hooks/utils/api/features folders those files import (`hooks/useInfiniteCatalogBooks`, `features/access/*`, `features/book-detail/*`, `features/profile/*`, `features/manual-books/*`, `features/library/*`, `features/reader/*`). Behaviour of those is only inferred from call sites and is marked "(inferred)".

## 1. Coverage table

All files read in full, every line (Read tool, whole file in one chunk each). Line counts are from `wc -l`.

| File | Lines | Fully read |
|---|---|---|
| pages/AccessPage.jsx | 170 | yes |
| pages/BookDetailPage.jsx | 437 | yes |
| pages/CategoryPage.jsx | 209 | yes |
| pages/CreatedBooksPage.jsx | 257 | yes |
| pages/DemoLoginPage.jsx | 49 | yes |
| pages/HomePage.jsx | 248 | yes |
| pages/KindleSentPage.jsx | 243 | yes |
| pages/LandingPage.jsx | 57 | yes |
| pages/LibraryPage.jsx | 358 | yes |
| pages/LoginPage.jsx | 206 | yes |
| pages/ManualBooksPage.jsx | 680 | yes |
| pages/NotesPage.jsx | 694 | yes |
| pages/passwordLinkCopy.js | 29 | yes |
| pages/PasswordLinkPage.jsx | 276 | yes |
| pages/PasswordResetPage.jsx | 100 | yes |
| pages/ProfilePage.jsx | 295 | yes |
| pages/ReaderPage.jsx | 83 | yes |
| pages/ReprocessingPage.jsx | 709 | yes |
| pages/SeriesPage.jsx | 209 | yes |
| pages/TwoFactorSetupPage.jsx | 165 | yes |
| pages/WriterPage.jsx | 275 | yes |
| components/AsyncButton.jsx | 36 | yes |
| components/BookCard.jsx | 212 | yes |
| components/BookCardGrid.jsx | 71 | yes |
| components/BookCardSkeleton.jsx | 49 | yes |
| components/BookCoverArt.jsx | 33 | yes |
| components/BookDetailSkeleton.jsx | 151 | yes |
| components/BookRouteLink.jsx | 36 | yes |
| components/BookTable.jsx | 418 | yes |
| components/catalog-toolbar/fields.jsx | 140 | yes |
| components/catalog-toolbar/icons.jsx | 22 | yes |
| components/catalog-toolbar/SearchRow.jsx | 188 | yes |
| components/CatalogToolbar.jsx | 164 | yes |
| components/ConfirmationDialog.jsx | 140 | yes |
| components/EmailInputFeedback.jsx | 63 | yes |
| components/EmptyState.jsx | 11 | yes |
| components/ErrorBoundary.jsx | 64 | yes |
| components/ExportActions.jsx | 77 | yes |
| components/KindleIcons.jsx | 35 | yes |
| components/LoadingSpinner.jsx | 5 | yes |
| components/PageLoader.jsx | 31 | yes |
| components/PageSkeleton.jsx | 273 | yes |
| components/ProcessingCardSkeleton.jsx | 45 | yes |
| components/PropertyTable.jsx | 150 | yes |
| components/PropertyTableControls.jsx | 164 | yes |
| components/ScrollToTopButton.jsx | 54 | yes |
| components/StatusPill.jsx | 10 | yes |
| components/TagInput.jsx | 170 | yes |
| components/ThemeToggle.jsx | 63 | yes |
| components/ToastViewport.jsx | 58 | yes |
| components/TwoFactorSetupPanel.jsx | 100 | yes |
| features/processing/api.js | 29 | yes |
| features/processing/BookProcessingPages.jsx | 7 | yes |
| features/processing/BookProcessingStore.jsx | 108 | yes |
| features/processing/types.js | 84 | yes |
| features/processing/store/processingNotifications.js | 79 | yes |
| features/processing/store/processingStoreConfig.js | 83 | yes |
| features/processing/store/useAutomationActions.js | 148 | yes |
| features/processing/store/useCatalogSyncActions.js | 123 | yes |
| features/processing/store/useProcessingCardRunner.js | 52 | yes |
| features/processing/store/useProcessingStateRuntime.js | 251 | yes |
| features/processing/store/useProcessingStream.js | 107 | yes |
| features/processing/store/useRequestActions.js | 62 | yes |
| features/processing/processing-pages/AutomationPanel.jsx | 281 | yes |
| features/processing/processing-pages/CatalogProcessingPage.jsx | 99 | yes |
| features/processing/processing-pages/CatalogSyncPanel.jsx | 190 | yes |
| features/processing/processing-pages/MultiPageTocProcessingPage.jsx | 103 | yes |
| features/processing/processing-pages/ProcessingDataCard.jsx | 512 | yes |
| features/processing/processing-pages/processingCardState.js | 66 | yes |
| features/processing/processing-pages/processingPageModel.js | 243 | yes |
| features/processing/processing-pages/processingPagePrimitives.jsx | 264 | yes |
| features/processing/processing-pages/processingTableRows.js | 275 | yes |
| features/processing/processing-pages/QueueProcessingPages.jsx | 426 | yes |
| features/processing/processing-pages/TableSkeletonRows.jsx | 77 | yes |
| features/processing/processing-pages/useProcessingCardData.js | 124 | yes |
| features/processing/processing-pages/useProcessingTableData.js | 298 | yes |

Total 76 files, 76 read in full, 12,873 lines. Extra, to verify dead-code claims only: a read-only `grep` over `src/` for symbol usage, and the first 30 lines of `hooks/useSessionFlag.js` (outside my scope, used only to confirm it is sessionStorage).

## 2. Pages

Common shape used by catalog-style pages (Home, Library, MyBooks, Kindle, Categories, Series, Writers etc., Manual): URL query params are the source of truth for applied filters (`filtersFromSearchParams(defaultFilters, searchParams)`), a local `filters` draft state mirrors them (re-synced in an effect), a shared `CatalogToolbar` provides search + sort + filter drawer, and `useInfiniteCatalogBooks` (not in my scope) provides infinite scroll (`entries/books, totalCount, hasMore, initialLoading, loadingMore, refreshing, error, tableShellRef, observeLoadTrigger, removeEntry, updateEntry, prependEntry, reload`). Error state shows only when `error && no rows && !initialLoading`. Result count is blank when error and no rows.

Route paths are not in my files; they are inferred from links and constants: `/home`, `/my-books`, `/library`, `/categories`?, `/series`?, `/writers /translators /editors /publishers` (WriterPage.jsx:56-84 literal), `/create /catalog /on-hold /incomplete /multipage-toc` (processingStoreConfig.js:1-7), `/notes`, `/books/:slug`, `/books/:slug/read` (NotesPage.jsx:617), `/login`, `/reset-password`, `/reset-password/confirm`, `/two-factor-setup`, `/demo`? (DemoLoginPage; route in AppRoutes). The only route mentioned elsewhere: `BookProcessingPages` and `DemoLoginPage` are referenced in `features/app/AppRoutes.jsx` (grep).

### 2.1 HomePage (`pages/HomePage.jsx`) - "All Books"
- Purpose: card grid of the whole catalog for staff/super admin (login redirects superuser to `/home`, others to `/my-books`: LoginPage.jsx:66).
- Data: `useInfiniteCatalogBooks({filters})` on the default books endpoint (endpoint not given -> default, inferred `/catalog/books/`); `useDynamicFilterOptions(filters,setFilters)` returns `authors, seriesList, categories` (dependent filter options, inferred).
- Default filters (16-24): `q, author, series, category, ownership="", record_type="digital", sort="-created_at"`.
- Controls: search box (placeholder "Search all books by title, book ID, or writer..."), sort select (Newest first / Oldest first / Title A-Z / Title Z-A, 28-37), filter drawer fields: Contributor (searchable-select, key `author`), Series, Category (searchable-select), Ownership (select: All books / My books), Type (Digital/Manual/All types) (61-110). Apply filters / Reset buttons are in the drawer (CatalogToolbar). Empty state: "No books found / Adjust the search or filters." with a "Clear all filters" button shown only when applied filters differ from defaults (229-244).
- Card actions (BookCardGrid): My Books toggle (`useMyBooksAction.toggleMyBooks`, busy ids), Send to Kindle (handler 130-149; optimistic `updateEntry(book.id,{has_sent_to_kindle:true,user_kindle_sent_at:now})` after success), Open record link.
- State persistence: `filtersExpanded` in sessionStorage key `filters-expanded:home` (54-57). Filters in URL.
- Loading: skeleton cards (6 initial, 6 incremental). Error: `.page-state-error`.
- Gating: none in file; Kindle button needs `user.kindle_emails.length` and `book.has_epub_asset` (BookCard).

### 2.2 LibraryPage (`pages/LibraryPage.jsx`) - "Books" (table)
- Purpose: table version of catalog with export, saved filters.
- Data: books via `useInfiniteCatalogBooks`; saved filters `GET /saved-filters/?target=catalog` (133) when `authenticated` (reloads on auth change 144-146); export data via `loadLibraryBooksForExport(appliedFilters)` (feature/library, not read).
- Defaults/sort options from `features/library/libraryFilters` (`defaultLibraryFilters`, `librarySortOptions`; not read). Filter fields (51-100): Contributor, Series, Category (searchable), Ownership, Type.
- Controls: search, sort, filter drawer, **ExportActions** CSV and PDF (searchActionsExtra, 281-288), `SavedFilterStrip` (apply chip / delete chip, 330-335).
  - Apply saved filter (205-218): sets filters to `{...defaults, ...savedFilter.params}`, writes to URL, toast `Applied "name".`, 300 ms lockout via `savedFilterAction`.
  - Delete saved filter (220-234): `DELETE /saved-filters/{id}/`, toast "Filter removed.", reload list. No confirmation dialog.
  - Table row actions: My Books Add/Remove (AsyncButton, `showMyBooksAction`), Open. Sort indicators in header for Title, Book ID, Created (BookTable).
- Export flow (236-278): sets `downloadState` mode, fetches ALL matching books (not just loaded page), `getExportBlockState` checks (empty/loading/error -> toast), writes the payload to a "pending export" store (`writePendingExport(LIBRARY_EXPORT_STORAGE_KEY, ...)`, `utils/exportSession`, likely sessionStorage; not read) so a reload mid-export can resume (148-187: on mount, if pending export exists, it resumes), waits `waitForExportUi` and min loader time, then `exportBooksToCsv(items, "catalog-books.csv")` or `exportBooksToPdf(items, "Books Export")`, always clears pending export.
- Persistence: URL filters; `filters-expanded:library` (sessionStorage); pending export (storage).
- Gating: none in file; saved filters only loaded when authenticated.

### 2.3 CreatedBooksPage (`pages/CreatedBooksPage.jsx`) - "My Books"
- Purpose: card grid of the user's own books (default for non-super-admin after login).
- Defaults (15-23): `ownership:"mine"`, `sort:"-requested_at"`, `record_type:"digital"`.
- Data: books via `useInfiniteCatalogBooks`; filter option lists fetched once on mount with three full list calls (64-80): `/catalog/writers/?record_type=all&sort=name`, `/catalog/series/...`, `/catalog/categories/...` (all rows, no pagination, only `.name` used; failure -> `console.error`, no toast).
- Sort options: Newest/Oldest request first, Newest/Oldest book first, Title A-Z/Z-A. Filters: Author, Series, Category (searchable), Type.
- Actions: Remove from My Books (X button on card; `removeBookFromMyBooks(slug)` then `removeEntry(id)` locally, toast; errors toast; per-id busy via `useAsyncAction.pendingKey` - only ONE pending key tracked: `removingBookIds={{[pendingKey]:true}}`), My Books toggle wired to the same remove handler (`onMyBooksToggle={removeFromMyBooks}`), Send to Kindle (as Home).
- Empty: "No books found / Adjust the search or filters." (no clear button). `filtersExpanded` is plain useState (not persisted).
- Note: `createdBookToolbarFields` is declared twice (module level line 41 and `useMemo` at 82); the module-level one is shadowed/unused.

### 2.4 KindleSentPage (`pages/KindleSentPage.jsx`)
- Purpose: books the user sent to Kindle. Defaults: `kindle_sent:"mine"`, `sort:"-sent_at"`. Sort: Newest/Oldest send first, Newest/Oldest book first, Title. Filters: Author, Series, Category, Type (same three full-list loads as CreatedBooks, 61-77).
- Actions: My Books toggle, Send to Kindle (resend). Empty: "You haven't sent any books to Kindle yet." (even when a filter is the cause). `filtersExpanded` not persisted. Duplicates the Home/CreatedBooks logic nearly line for line.

### 2.5 CategoryPage / SeriesPage / WriterPage (`pages/CategoryPage.jsx`, `SeriesPage.jsx`, `WriterPage.jsx`)
- Purpose: property tables (code, name, counts) that link into the library filtered by that value.
- Endpoints: `/catalog/categories/`, `/catalog/series/`, `/catalog/{writers|translators|editors|publishers}/` (WriterPage.jsx:52-85).
- Defaults (identical): `q, record_type:"digital", created_after, created_before, sort:"-book_count"`. Filters: Type, Created after, Created before (date inputs), search. Sort: Most/Fewest books, Code asc/desc, Name A-Z/Z-A, Newest/Oldest first (option order differs slightly between Category and Series: Name before Code in Series).
- Columns: Code, Name/Series, Books, Digital, Manual, Created, Open. Row link: `/library?category=<name>` (series -> `series=`; writers -> `author=<name>`, other contributor roles -> `contributor=<name>&contributor_role=<role>`), carrying `record_type` only when not "digital" (`buildBooksLink`). Note it uses the *draft* `filters.record_type`, not the applied one.
- WriterPage: four tabs via `NavLink` (Writers, Translators, Editors, Publishers; path = route, so tab change is a route change, filters in the query string are kept? `NavLink to={tab.path}` drops the query string - filters reset on tab switch). Active tab derived from `location.pathname`, falls back to Writers.
- States: skeleton rows (5 initial, 3 incremental via PropertyTable), empty label per tab, error as `.page-state-error`. Filters expanded not persisted. No auth gating in files.

### 2.6 ManualBooksPage (`pages/ManualBooksPage.jsx`) - "Physical Books' List"
- Purpose: CRUD list of manually entered (physical) books with composer, exports.
- Data: `/catalog/manual-books/` via `useInfiniteCatalogBooks`; option lists from `loadManualBookOptions()` (categories, contributors, writers, translators, editors, series, publishers); reloaded after each create/edit.
- Filters NOT in the URL: `filters`/`appliedFilters` are plain state (45-46) initialised from `defaultManualBookFilters` (feature file, not read). Fields: Writer, Translator, Editor, Category, Publisher (searchable), Binding (Any/Hardcover/Paperback) (80-138). Sort from `manualBookSortOptions`. Search placeholder "Search manual books, book IDs, writers...".
- Header actions (`ManualBooksToolbarActions`, not read): toggle composer, toggle export row.
- Composer (`ManualBookComposer`, not read) fields per form object: title, summary, writers[], translators[], editors[], categories[], series[], is_compilation, binding (default `hard_cover`), publisher, price, language (default "bn" when editing).
  - Create (`handleCreate` 236-294): waits 50 ms for blur state, uses `formRef` (latest form), `createManualBook(form)`, `prependEntry(payload)`, highlights row for 2.6 s, resets the form, KEEPS composer open and refocuses title (batch entry mode), toast "Added <catalog_code>. Ready for the next manual book.", reloads options and `reload({preserveRows:true})`.
  - Edit: row "Edit" button -> `handleEditBook` (296-324) maps book to form (normalises binding text to `hard_cover`/`paper_back`; price string; language default "bn"), submit -> `PATCH /catalog/books/{slug}/metadata/` with `contributors:[{name,role}]` (author/translator/editor + publisher as role "publisher"), toast, closes composer, full `reload()`.
  - "Done" (`handleDone` 326-360): if editing just closes; if form has input (`hasManualBookFormInput`) it CREATES the book first, then closes; else closes and reloads.
- Exports (378-445, expandable row 500-577): group-by select for Excel (No grouping, Category, Publisher, Binding, Language, Contributor), CSV (`manual-books.csv`), PDF ("Physical Books' List Export", optional groupBy), Excel (`manual-books.xlsx` via `exportManualBooksToExcel(items, groupBy)`; no pending-export persistence for Excel). CSV/PDF use the same pending-export resume mechanism with `MANUAL_BOOKS_EXPORT_STORAGE_KEY`.
- Table (BookTable props): publisher column, hide series, hide type, show time (date-time), limit contributor role (one role only: writer, else translator, else editor), row Open + Edit.
- Empty/error/loading as above. Highlighted new row (`is-highlighted`). `buttonsDisabled` does not include `initialLoading` unlike other pages.
- Gating: none in file (route-level, inferred).

### 2.7 BookDetailPage (`pages/BookDetailPage.jsx`)
- Purpose: single book view for digital and manual (physical) records, hero actions, reader sections, metadata editing.
- Data: `useBookDetailData({canEditMetadata, location, navigate, slug, toast, user})` returns `book, bookLinkFilters, bookmarks, detail, editor, htmlPreviewLockedByAssetId, metadataReviews, metadataVersions, readerAccess, readerState, reviewForm, loading, error, fetchBook, replaceBookRoute, ...` (hook not read). Actions via `useBookDetailActions` (not read): delete, regenerate, replace EPUB (file input), send to Kindle, launch reader, delete bookmark, create/update metadata review, save metadata.
- Capabilities (33-34): `metadata:edit`, `source_records:view` via `hasCapability(user, ...)`.
- Layout: `BookDetailHero` (actions; hasKindleEmail; hasSentToKindle), then for manual record: `PhysicalBookWorkspace`; for digital: `BookReaderSections` (bookmarks, progress percent, reader access/state), Source Records card (only if `source_records:view` and records exist; links open in new tab, label Primary/Linked), "Entities and Details" (extracted entries list or sanitised `book_info_html`), "Dedication" (sanitised `dedication_html`), "Table of Contents" (`BookTocSummary`), "Chapters without content (N)" (from `book.empty_chapters`, pill "No content on source" if `has_content===null` else "Fetch failed"), editor workspace `BookMetadataWorkspace` (only `metadata:edit` and non-manual), "Raw Provenance" JSON block (non-manual with `raw_provenance`, labelled "Staff" but shown to anyone who can see the page - no capability check in this file).
- Inline edit of manual books (68-165, 167): `actions.onStartEdit = handleStartEdit` (mutates the actions object returned by the hook each render); opens `ManualBookComposer` in place of the page; submit `PATCH /catalog/books/{slug}/metadata/` via `bookDetailFetch`; on slug change `replaceBookRoute(newSlug)`. Duplicate of ManualBooksPage edit code (same binding normalisation).
- Delete: `ConfirmationDialog` "Delete Book?" / `Delete "<title>"? This will hide it from the catalog.` (soft delete wording).
- Route state: returns to the list the user came from via `location.state.from` (BookRouteLink / `getBookReturnTarget`, fallback `/library`).
- States: skeleton (`BookDetailSkeleton`), error `.page-state-error`. DOMPurify used for HTML blocks.

### 2.8 NotesPage (`pages/NotesPage.jsx`) - "My Notes"
- Purpose: reader annotations of the logged-in user across all books.
- Data: `fetchMyNotes({kind, color?, query?})` from `api/reading` for kinds `bookmarks | highlights | notes | quotes`; response `payload[tab]` array. On mount: loads active tab and background-fetches the other three tabs only to display counts (123-135). Counts are `items.length` of the (unfiltered) response, but after a filtered `loadTab` the active tab's count becomes the filtered length (bug-ish, 111).
- Controls: header search input (debounced 320 ms, server-side), colour filter select (All colors, Green, Yellow, Blue, Pink, Underline; only for Highlights and Notes tabs; reset when leaving those tabs 146), four tabs with counts, result count line.
- Layout: two columns - books list (grouped by `book_slug`, sorted by title, per-book count) on the left; selected group's items on the right (auto-selects when only one group; otherwise "Select a book from the left"). Group collapsible toggle. Link to `/books/<slug>` and "Open in reader" -> `/books/<slug>/read`.
- Item actions: Delete (confirm dialog "Delete bookmark?"/"Delete entry? ... Any note attached to it will also be deleted."; bookmarks use `deleteBookmark`, others `deleteHighlight`), Edit comment (notes tab only; modal with textarea, Ctrl/Cmd+Enter saves, Esc cancels via `useDialogA11y`), colour dots (highlights and notes: updates `color` via `updateHighlight`, no optimistic UI - replaces item with server response). Quote tab shows quote glyphs.
- Local optimistic bits: delete removes from local list and decrements count only after the server succeeds.
- Empty hints per tab (EMPTY_HINTS 41-46). Loading: `PageLoader`. Error: toast only (no error panel).
- Colour list must match the reader (comment line 22 "Must match HIGHLIGHT_COLORS in highlight-methods.js").
- Persistence: none (tab/query/colour are component state, not in URL).
- Surprise: the tab switch effect (137-142) only reloads if tab not loaded or a query/colour is active; stale data after edits made elsewhere.

### 2.9 AccessPage (`pages/AccessPage.jsx`) - "Users & access"
- Gating: `user.is_superuser` only (20, 54-60) else a message. Tabs (`useAccessTabs`, tab id "users" vs grants tab) with `AccessHero`.
- Data (hooks not read): `useAccessAdminData` -> `accountScopes, managedUsers, references, scopedGrants, scopedScopes, scopeLabelMap, loadingAdminData`; `useAccessUsers` (infinite list with search/sort/status filter, edit form, resend setup email, suggest/copy password, select-all/clear permissions, delete); `useAccessGrants` (grant editor: target type switch, target search, toggle scope, toggle target, submit, delete rule).
- Users tab: editor card (create/edit user, per-account scope checkboxes, password suggest/copy/show) + users table card (search, sort, status filter, infinite scroll with observer trigger, edit, delete, resend setup email, shows access labels).
- Grants tab: editor + rules card.
- Delete confirmation: `ConfirmationDialog` "Delete User?" with `Delete <email>? This will permanently remove the account.`
- Loading: `PageLoader variant="management"`.

### 2.10 ProfilePage (`pages/ProfilePage.jsx`)
- Data: `authApi.profile()` + `authApi.twoFactorStatus()` in parallel; reloads on `user.id` change. Capability `send:kindle` gates Kindle email section.
- Modes: read-only view vs edit form (button Edit/Cancel). Edit fields: full name, profile image (file input, preview via `URL.createObjectURL` - never revoked, remove image), Kindle emails (dynamic list, add/remove, validation states, shows sender email), password change (current, new, confirm, show/hide toggles, collapsible), 2-factor panel (open setup -> QR + secret + token confirm, copy provisioning URL, cancel setup, disable TOTP) - hooks `useProfileTwoFactorActions`, `profileSaveAction`, `useProfileDerivedState` (not read).
- States: `PageLoader variant="profile"`; errors via toast (`humanizeError`).

### 2.11 Auth pages
- **LoginPage** (`pages/LoginPage.jsx`): two phases, `credentials` then `otp`. Email validation (`getEmailValidationState`) with live `EmailInputFeedback`; submit disabled until valid email + non-empty password. Password show/hide. Server error code `otp_required` switches to OTP phase (toast info); `otp_invalid` stays in OTP phase with error toast. In OTP phase email/password become read-only; "Change account" returns to credentials. After login: `totp_setup_required` -> `/two-factor-setup`, else `/home` (superuser) or `/my-books`. Authenticated visitors redirected immediately. Link "Reset password".
- **DemoLoginPage**: on mount, if not authenticated and not attempted, `authApi.demoLogin()` then `refreshSession()`; failure -> toast "Demo login failed..." and `/login`; authenticated -> redirect by role. Shows spinner.
- **PasswordResetPage**: email form -> `authApi.passwordReset({email})`, toast with `response.detail`. If URL has `uid` and `token` it redirects to `/reset-password/confirm?uid=&token=`. Submit disabled until valid email. Always shows server detail (enumeration-safe depends on server).
- **PasswordLinkPage** (mode `create` or `reset`; copy in `passwordLinkCopy.js`): validates link on mount (`authApi.passwordResetValidate({uid,token})`), shows "link expired" heading for invalid/expired (only toast for non-expiry errors). If user is already logged in shows "Log out first" with Log out button. Form: new password + confirm (each with show/hide); client checks they match; `authApi.passwordResetConfirm({uid,token,new_password})`; response `next_step === "totp_setup"` -> refreshSession + `/two-factor-setup` else toast + `/login`. Expiry detection compares error *message strings* ("Invalid reset link.", "Reset token is invalid or expired.") - brittle. No client password-strength rules.
- **TwoFactorSetupPage**: requires authenticated and `user.totp_setup_required` (else redirect `/login` with state or `/home`). Auto-calls `authApi.twoFactorSetup()` once, shows `TwoFactorSetupPanel` (QR SVG, setup URL, secret, copy button, token input, "Verify and Continue"), `authApi.twoFactorConfirm({token})`, refreshSession, goes to `location.state.from || "/home"`. No Cancel (required mode). Retry button "Prepare setup" if the first call fails.

### 2.12 LandingPage (`pages/LandingPage.jsx`)
- Static marketing/welcome page ("RSalehin24 Library"), buttons Open Create Books (`/create`), Open Library (`/library`) or Sign in. **Never imported anywhere** (grep: only its own definition). Dead.

### 2.13 ReaderPage (`pages/ReaderPage.jsx`)
- Wrapper for the embedded reader. URL params: `slug`, `launch`, `manifest`, `appNav` (default "hidden"; toggled to "shown" via `setSearchParams(..., {replace:true})`). Hooks `useReaderLaunch` (resolves launch token / manifest URL, sets loading/error), `useReaderBoot` (boots the reader into the DOM from `manifestUrl`, theme-aware), `useTheme` (third tuple value `resolvedTheme`). Back target `/books/<encodeURIComponent(slug)>` or `/create`. States: `PageLoader variant="reader"`, `ReaderUnavailable`, `ReaderViewport`.

### 2.14 ReprocessingPage (`pages/ReprocessingPage.jsx`)
- Purpose: admin view of `job_type=reprocess` ingestion jobs. Does NOT use the BookProcessing store; has its own data hook, own SSE, own polling (see section 3.6). Reuses processing-page chrome (`PageFrame pageId="reprocessing"`, `OverviewPanel`).
- API (features/processing/api.js): `GET /ingestion/jobs/?job_type=reprocess&limit=200`, `GET /ingestion/jobs/reprocess/summary/` (`queued, active, done, failed, stopped`), `POST /ingestion/jobs/{id}/stop/`, `DELETE /ingestion/jobs/{id}/`, `POST /ingestion/jobs/{id}/resume/`.
- Two tables, client-side filtered/paged:
  - **Active** (status `queued` or `processing`; search by book title or submission_input): columns checkbox, Book (link via BookRouteLink if `target_book_slug` and not deleted, else muted title with "Deleted" tag), Status badge (Queued / Active), Retries, Started (hidden on small), Updated, row actions. Row actions: Stop (queued or processing), Delete (queued only). Bulk: Stop (any selected active job), Delete (only the selected ones with status queued).
  - **History** (succeeded, failed, cancelled; search also includes `last_error`): columns checkbox, Book, Status (Done / Failed / Stopped), Retries (hidden sm), Error (hidden md; truncated at 72 chars with full text as title), Finished (`finished_at || updated_at`), actions. Row actions: Open (book link, when slug and not deleted), Resume (failed or cancelled), Delete (all). Bulk: Resume (failed/cancelled only), Delete (all selected).
- Progressive rendering: 60 rows at a time, IntersectionObserver sentinel row inside the table shell (not server pagination; all jobs already loaded, max 200).
- Selection: per table `Set` of ids; select-all selects visible rows only; "N selected" counter counts visible selected only.
- Relative time `RelTime` ("just now", "Nm ago", "Nh ago", "Nd ago", tooltip locale date) is computed on render, does not tick.
- Empty: "No active reprocessing jobs." / "No matching jobs." / "No history." / "No matching records."
- No confirmation dialogs for any destructive action. Errors of stop/resume/delete are NOT caught: `act()` uses try/finally without catch, so a failed request rejects with no toast (unhandled promise rejection); `Promise.all` in bulk handlers aborts `clearSelection()` on first failure.
- Permission gating not in file (route-level, inferred). The base store is gated on `processing:manage`, but this page calls the API directly.

## 3. Processing UI in depth (`features/processing/`)

### 3.1 Provider and context (`BookProcessingStore.jsx`)
- `BookProcessingProvider` wraps the app (mounted in app shell, not in my scope). It reads session, toast and the current location.
- `canLoadProcessingState = authenticated && !loading && hasCapability(user, "processing:manage")` (23-24). Everything below is disabled when false.
- `processingPage = processingPageForPathname(pathname)`: `/catalog -> "catalog"`, `/create -> "create"`, `/on-hold -> "on-hold"`, `/incomplete -> "incomplete"`, `/multipage-toc -> "multipage"`. State is loaded and the stream opened ONLY while on one of these routes. The Reprocessing page is not in this map.
- Context value exposes: all action functions, `busyCards` map, `canLoadProcessingState`, `getDomainVersion(cardKey)`, `isSharedProcessingCard(key)`, `processingState` (+ `Error`, `InitialLoading`, `Loaded`, `Refreshing`), `streamMode`.
- `useBookProcessing()` throws outside the provider.

### 3.2 Card keys and "shared" cards (`store/processingStoreConfig.js`)
- 19 `PROCESSING_CARD_KEYS`: catalog-overview, catalog-sync, catalog-automation, catalog-records, create-overview, create-requests, create-queue, create-processing, create-created, on-hold-overview, on-hold-paused, on-hold-failed, on-hold-duplicate, on-hold-deleted, incomplete-overview, incomplete-automation, incomplete-records, incomplete-completed, multipage-records.
- 7 "shared" cards served from one aggregate `GET /processing/state/?includeLists=0`: catalog-overview, catalog-sync, catalog-automation, create-overview, on-hold-overview, incomplete-overview, incomplete-automation. The other 12 are list cards (tables) fetched independently.
- `processingPath(path)` appends `includeLists=0` (or `&includeLists=0`) to every non-stream state/action URL (including POST actions).
- Sync scopes: `catalog`, `incomplete`. `scopedSyncPath(scope, action)` = `/processing/sync/{scope}/{action}/`.
- `versionSignature(versions, domains)` = `domain:ver|...` string used to detect whether shared versions changed.

### 3.3 Versioning model
- The server publishes monotonically increasing integer `versions[cardKey]`. Client holds `domainVersions` state (+ ref). `applyProcessingVersions(incoming)` only accepts known card keys and strictly greater values; returns `{changed, sharedChanged}`.
- If a shared card version changed, the store queues a reload of `/processing/state/`. If only a list card version changed, nothing is refetched centrally; each list-card hook compares `getDomainVersion(cardKey)` with the version it loaded and refetches itself.
- Sources of version updates: (1) SSE `versions` event payload `{versions:{...}}`, (2) the `versions` field of any action response (`runCardAction` -> `applyProcessingVersions(payload.versions)`), (3) `versions` field in `/processing/state/` and table payloads (`payload.version`).

### 3.4 State loading runtime (`store/useProcessingStateRuntime.js`)
- Single-flight loader `loadProcessingState`: if a request is in flight, remembers (via `reloadQueuedRef`) that another load is needed when the known shared signature differs from the one that was queued; returns the same promise.
- Fetch: `processingFetch("/processing/state/?includeLists=0", {cache:"no-store"})`.
- Request-id guard: ignores responses older than the last applied (`requestId < appliedRequestIdRef`). A response is applied only when the client's known shared signature equals the payload's shared signature; if newer versions arrived meanwhile the payload is NOT applied (status stays loading/refreshing) and a reload follows.
- Status object: `{data, loadedOnce, initialLoading, refreshing, error}`. First load -> `initialLoading`, later -> `refreshing` (stale data kept, no flash). Errors keep old data, set `error`, `loadedOnce:true`.
- Triggers: page changed, not loaded yet, or shared signature changed vs applied. Leaving processing routes or losing capability resets everything (versions, status, refs).
- Surprise: reload logic leans on 7 refs and a self-referencing ref (`loadProcessingStateRef`); behaviour is hard to reason about and there is no retry/backoff on error.

### 3.5 SSE / stream and fallback polling (`store/useProcessingStream.js`)
- `new EventSource(resolveProcessingStreamUrl("/processing/stream/?page=<page>"), {withCredentials:true})`, one connection per processing page (re-created when page changes). Events: `connected` (-> streamMode "connected"), `versions` (JSON, -> `applyProcessingVersions`; shared change -> queue reload; parse errors swallowed), `onerror` (-> "reconnecting"; EventSource auto-reconnects natively). No heartbeat/idle timeout handling, no manual reconnect, no `Last-Event-ID`.
- `streamMode` values: `idle`, `connecting`, `connected`, `reconnecting`, `unsupported`.
- Fallback poll: while `streamMode` is `reconnecting` or `unsupported`, `loadProcessingState()` every **15 000 ms**. NOTE: this refreshes only the shared `/processing/state/`; list cards advance only if versions in that payload exceed what they hold, so in fallback mode list tables update only when the shared payload bumps their versions.
- UI: `PageFrame` shows a muted line "Live updates reconnecting. Refresh checks continue every 15 seconds." or "Live updates are unavailable in this browser." (`processingStreamStatusMessage`).

### 3.6 Reprocessing SSE (separate)
- `new EventSource(resolveProcessingStreamUrl("/ingestion/jobs/stream/"), {withCredentials:true})`; events `connected`, `job-update` (any -> full `load()` of jobs + summary, no payload used); `onerror` -> "reconnecting"; fallback poll `POLL_MS = 15_000`. On transient fetch errors retains old data silently (no error UI). `loadedOnce` set true even after an error (page then shows zeros).
- Also has an extra effect that closes `eventSourceRef` on unmount, duplicating the SSE effect's cleanup.

### 3.7 Card actions runner and invalidation (`store/useProcessingCardRunner.js`)
- `runCardAction(cardId, request, {onSuccess, errorMessage})`: increments `busyCards[cardId]` counter, awaits request, applies `payload.versions` (queues state reload if shared change), calls `onSuccess(payload, toast)`, returns payload. On error: toast `errorMessage || err.message || "Unable to complete the action."` except for HTTP 401/403 (silent), returns `null`. Decrements busy counter in `finally`. Returning `null` is how callers detect failure.
- No client-side optimistic mutation of table rows. After an action, rows/cards change only when the server bumps versions and each list card refetches (card invalidation = version bump). Bulk selection is cleared by `ProcessingDataCard.runAction` only when the action returned a truthy result.
- Busy keys: `catalog-sync`, `catalog-records`, `catalog-automation-save`, `catalog-automation-run` (shared by run/pause/resume/stop), `incomplete-automation-save`, `incomplete-automation-run`, and per-card ids passed by request actions (`create-queue`, `on-hold-failed`, etc. - note the page components check `busyCards["create-<cardId>"]`, `["on-hold-<cardId>"]`, `["incomplete-completed"]`, `["multipage-records"]`, `["catalog-records"]` which equal the cardKey strings passed to the actions).

### 3.8 Action endpoints (all `POST`, path gets `includeLists=0`)
| Action | Endpoint | Body | Toast |
|---|---|---|---|
| startCatalogSync(remotePages?) | `/processing/sync/start/` | `{remotePages:[[{...}]]}` only when valid non-empty (`catalogRemotePages` validates array of arrays of objects) | info "Sync started" |
| pauseCatalogSync | `/processing/sync/catalog/pause/` | - | info "Pause requested" |
| resumeCatalogSync | `/processing/sync/catalog/resume/` | `{runMode:"manual"}` | info "Sync resumed" |
| stopCatalogSync | `/processing/sync/catalog/stop/` | - | none (UNUSED by UI) |
| createRequestsForRecords(ids) | `/processing/records/create-requests/` | `{ids}` | success "Requests created" (uses `createdCount`) or info "No requests created" |
| saveCatalog/IncompleteAutomation(form) | `/processing/automation/{catalog|incomplete}/` | `{enabled, interval, time}` | success "<Title> saved" |
| runCatalog/IncompleteAutomation | `/processing/automation/{...}/run/` | - | info |
| pause...Automation | `/processing/sync/{scope}/pause/` | - | info |
| resume...Automation | `/processing/sync/{scope}/resume/` | `{runMode:"catalog_automation"|"incomplete_automation"}` | info |
| stop...Automation | `/processing/sync/{scope}/stop/` | - | none (UNUSED) |
| Request actions | `/processing/requests/action/` | `{ids, action, ...extra}` | per-action copy |

Request actions (`useRequestActions`): `delete` (extra `deleteBook` bool), `pause`, `resume`, `retry`, `new`, `new_edition`, `confirm_duplicate`, `create_again`, `recreate`, `force_generate`. Toast copy in `processingNotifications.js`; when `changedCount` is 0 -> info "No changes applied: The selected rows were already in the requested state." The `delete` toast is "Book deleted" if `deleteBook` else "Request deleted". `useRequestActions` returns a fresh object every render (not memoised) so the context `useMemo` never stabilises (perf issue).

### 3.9 Request state model (`types.js`)
Request states: `initial, queued, processing, created, paused, failed, duplicate, deleted`; book creation state adds `not_created`. Terminal: created, failed, duplicate, deleted. Active: initial, queued, processing. Holding: paused. Labels in `REQUEST_STATE_LABELS` ("Initial", "Queued", ...). Typedefs only (JSDoc); only `REQUEST_STATE_LABELS` is used by the UI (other exports unused here).

### 3.10 Pages and cards

Common card: `ProcessingDataCard` (`processing-pages/ProcessingDataCard.jsx`).
- Props: `pageId, cardId, cardKey, title, actions[], busy, readOnly, detailsLabel, showDetailsColumn, emptyLabel("No records."), className, fullSpan, bookColumnMode ("combined"|"split"|"wide"), actionLabel, renderRowAction, countPlacement ("title"|"inline-tools")`. `description` props are passed by pages but never rendered by the card (ignored).
- Header: title, count badge (server `totalCount`, or shared count from `/processing/state/` before the table loads, or a skeleton), debounce-less search input (placeholder "Search name, URL, category, writer, translator, or publisher"; each keystroke changes filters and triggers a refetch; disabled while `busy`), Filters toggle with active count, bulk-action buttons (`AsyncButton`, label + `(N selected)`, `danger` -> ghost danger style, loading label "Working", disabled when no selection or initial loading).
- Filter drawer: Category select (options from server facets `filters.categoryOptions`), Status select (`statusOptions`, labelled via `REQUEST_STATE_LABELS`). `ActiveFilters` chips show chosen category/status. Filter drawer open state not persisted.
- Table columns (conditional): checkbox (only when `actions.length>0 && !readOnly`), Book (combined: title + MultiPageTocBadge + secondary URL line) or split Name and URL (URL shown as text, not a link), Credits (Writer / Translator / Publisher), Category ("Uncategorized" default), Status (label), Details (optional; `requestDetails(row)`: checkpoint with saved date, or curated-validation errors joined with " • " when error equals "Curated document requires review before asset generation.", else error message, "Confirmed duplicate", "Confirmed new", "Resumed from saved progress", default "Ready"), Updated (`formatDate`: locale string in `Asia/Dhaka` timezone, "Never" if missing), optional Action column (`renderRowAction(row)` else "-").
- Selection: `selectedIds` array; pruned to visible ids whenever rows change; select-all selects only rows with `row.selectable`; per-row checkbox disabled when `!row.selectable` or busy. `runAction(action)` calls `action.onAction(ids, selectedRows)`; clears selection when the result is truthy.
- States: initial skeleton rows (5; also shown when shared count > 0 but table not yet loaded), incremental skeleton (3 rows) while loading more, empty cell shows `tableError || emptyLabel` (table error and empty share the same cell), busy bar "Working" with spinner, `aria-busy`.
- Infinite scroll: server paging (`useProcessingTableData`), see 3.11.

Pages:

1. **Catalog** (`/catalog`, `CatalogProcessingPage.jsx`, requires `processing:manage`)
   - Overview stats (card `catalog-overview`): Records, Remaining (`notCreated`), Creating (`active`), Books (`created`), On Hold (`onHold`).
   - Cards `CatalogSyncPanel` "Manual" and `AutomationPanel` "Automation" (see 3.12), then data card `catalog-records` "Book Records" (split Name/URL columns, no details column, inline count). Bulk action: "Create Book" -> `createRequestsForRecords(ids)`. Selectable rows are those the server marks `selectable` (records without an active request).
   - Cross-panel optimistic state: `optimisticCatalogRuntime` lifted into this page via `onOptimisticSyncChange`; `effectiveCatalogSync` overlays it on the server sync card so both panels see the other's pending state. Mutual exclusion: the manual panel's control is disabled when automation owns the active phase (`automationRuntimeOwnsCatalog`), the automation panel's controls disabled when manual owns it (`manualRuntimeOwnsCatalog`).
2. **Create** (`/create`, `QueueProcessingPages.jsx` `CreateProcessingPage`)
   - Overview: Queue, Processing, Created, Requests (`create-overview` summary.queue/processing/created/requests).
   - Cards (state filter in brackets, from `processingTableRows.requestStateMap`; actual filtering is server-side): **Queue** (`queued`) bulk Delete; **Processing** (`processing`) bulk Pause, Delete; **Created** (`created`) bulk Delete (with `deleteBook:true` - also deletes the linked book; no confirmation dialog) and a row action column "Open" (BookRouteLink to `linkedBookSlug`, only if present); **Requests** (`initial`) bulk Delete. All with details column hidden.
   - Card order in UI: Queue, Processing, Created, Requests.
3. **On Hold** (`/on-hold`)
   - Overview: Paused, Failed, Duplicate, Deleted.
   - **Paused**: Resume, Delete. **Failed** (details label "Error Reason"): Force Generate, Retry, Delete. **Duplicate**: New, New Edition, Duplicate (confirm), Delete. **Deleted**: Create Again only.
4. **Incomplete** (`/incomplete`)
   - Overview: Incomplete, Updated (`resolved`).
   - `AutomationPanel` (pageId incomplete, full width). Card **Incomplete** (`incomplete-records`, `readOnly`, split columns, no actions/checkbox). Card **Updated** (`incomplete-completed`): bulk "Recreate Book" (`recreate`) and Delete.
5. **Multi-page TOC** (`/multipage-toc`, `MultiPageTocProcessingPage.jsx`)
   - Summary NOT from shared state: fetches `GET /processing/table/?card=multipage-records&offset=0&limit=1&includeFacets=0` and reads `payload.summary` ({total, created, failed, processing}) refetched when the card version changes. Stats: Multi-page books, Created, Failed, In progress.
   - Card `multipage-records`: details column ("Details"), full-span, bulk "Regenerate": splits selection into rows with state `created` (-> `recreate`) and others (-> `force_generate`), runs both with `Promise.all` and returns an array (always truthy, so selection always clears even if both calls failed/returned null). Rows show `MultiPageTocBadge` "TOC fetched/source" (incomplete styling when fetched < source, tooltip about sign-in).
6. **Reprocessing**: see 2.14 (outside the store).

Which states enable which action (derived from the card -> state mapping): Delete in Queue/Processing/Created/Requests/Paused/Failed/Duplicate; Pause only Processing; Resume only Paused; Retry and Force Generate only Failed; New / New Edition / Duplicate only Duplicate; Create Again only Deleted; Recreate Book only Updated (created); Create Book only Catalog records not yet requested. The client does not enforce per-state rules beyond "card = state" plus the `selectable` flag; backend decides via `changedCount`.

### 3.11 Table data hook (`processing-pages/useProcessingTableData.js`)
- Server pagination: `GET /processing/table/?card=<key>&offset&limit=60&includeFacets=1|0&q&category&status`, `cache:"no-store"`. Response shape: `{rows, pagination:{totalCount, hasMore}, filters:{categoryOptions, statusOptions}, version, summary?}`.
- Lazy loading by visibility: an IntersectionObserver (`rootMargin "300px 0px"`, threshold 0.1) on the card element; the first fetch only starts when the card is visible (and, without filters, after the shared state loaded). If shared count for the card is 0 the table is marked loaded with no request.
- Versioned refresh: when `getDomainVersion(cardKey) > loadedVersion` and the card is visible and nothing in flight, refetch from offset 0 with `limit = rows.length` (re-fetches everything loaded so far, could be large after long scrolling) and without facets. Not visible cards defer refresh until visible.
- Infinite scroll: row at index `len - 30` (`PROCESSING_TABLE_PREFETCH_TRIGGER`) gets the observer (`rootMargin` bottom 240px, root = table shell); `loadMore` debounced 120 ms; appends rows. A filter change resets state (rows cleared, new request id) - it does not abort in-flight requests, it ignores their results via request id.
- Errors: stored as `error`, table shows error text in the empty row; there is no retry control.
- Search typing is not debounced, so each keystroke fires a request (stale ones ignored).

### 3.12 Sync and automation panels
- **CatalogSyncPanel** ("Manual"): single icon button, three modes: Start sync (idle), Pause sync (when manual owns an active sync phase; shows "Pausing sync" and disabled while pausing), Resume sync (when sync phase is `paused`). Disabled while `catalog-sync` busy, when another mode owns the runtime (`otherModeOwnsRuntime`: request creation active or sync owned by someone other than manual) or blocked by the automation panel. Status footer: spinner + "Syncing"/"Pausing" and up to two lines (first sentence, rest) from the server message after rewriting "Catalog now has N book records." with the live `summary.records`.
- **AutomationPanel** (catalog and incomplete): controls = icon-only Run/Pause/Resume, On/Off switch, Interval select (daily, weekly, biweekly, monthly), Time input, Save button. Catalog automation has two phases (`sync`, `request_creation`); logic decides whether the button starts sync, resumes sync, starts request creation directly (when sync completed and request creation not started), or resumes request creation, with distinct messages (lines 64-84). Incomplete uses simple status (`idle|syncing|pausing|paused`) plus `runMode`. Controls disabled when saving/running or the other runtime owns the work.
- Form state is local, reset from server whenever `enabled/interval/time` change (draft edits lost on any server push of changed values).
- Defaults: `DEFAULT_SYNC_CARD {status:"idle", runMode:"manual", message:"Ready to sync."}`, `DEFAULT_AUTOMATION_CARD {enabled:false, interval:"weekly", time:"03:00", saved:false, lastRunAt:null, statusMessage:""}`.
- **Optimistic updates** (only place in the processing UI): clicking Start/Pause/Resume immediately overlays `{status:"syncing"|"pausing", message, phase}` on the displayed sync state. The overlay is dropped when the server state matches (status and phase) but held for at least `OPTIMISTIC_SYNC_MIN_MS = 2000` ms to avoid flicker, and force-dropped after `OPTIMISTIC_SYNC_MAX_MS = 4000` ms; also dropped immediately if the action returns a falsy result (failure). Incomplete page keeps a second overlay `pendingNonCatalogSync`.
- Catalog phase model (`processingPageModel.js`): sync phases `sync` and `request_creation`; phase statuses `not_started, running, pausing, paused, completed`; owner run modes `manual`, `catalog_automation`, `incomplete_automation`. `catalogPhaseStatus` derives status from `sync.progress.phaseStates[phase].status`, falling back to `progress.phaseStatuses`, then to overall `sync.status` heuristics (`savedData` implies sync completed). `catalogPhaseOwner` falls back to `savedData.runMode || sync.runMode`, request creation always attributed to `catalog_automation`.
- Hook `useProcessingCardData` (non-shared cards only) polls `GET /processing/card/?card=<key>` every **2000 ms** while `data.sync.status` is `syncing` or `pausing`, in addition to version-driven refetch. Currently none of the pages use it for a non-shared card that has `sync` (sync cards are shared), so this 2 s polling branch is effectively dead code; shared cards read from the aggregate state.
- `processingCardState.js`: client-side derivation of a card from the aggregate `/processing/state/` payload (`cards[cardKey]` if present, else rebuilt from `summary/syncStates/automation`). `processingCardCountFromState` maps list-card keys to summary counts for the pre-load count badges.

### 3.13 Dead / legacy code in processing
- `processingTableRows.js`: `tableRowsForCard, filterTableRows, rowFromRecord, rowFromRequest, recordSelectable, latestRequestByRecordId, compareRequestDates, requestBlocksSelection, categoryIsIncomplete, sortedUniqueValues` have no importers (only `processingCardPath` and `processingTablePath` are used). It documents the OLD client-side model (records + requests joined in the browser, selectable = no active request or confirmed duplicate whose original failed/deleted; "incomplete" detected by category keywords including Bangla "অসম্পূর্ণ"), now moved server-side.
- `stopCatalogSync`, `stopCatalogAutomation`, `stopIncompleteAutomation` (exposed by the store, never rendered; `StopIcon` imported in two panels but unused).
- `BOOK_CREATION_*`, `TERMINAL_*`, `ACTIVE_*`, `HOLDING_*` constants in `types.js`.
- `description` prop on `ProcessingDataCard` pages.

## 4. Shared components (`components/`)

| Component | What it does |
|---|---|
| AsyncButton | Button with stable-width spinner slots, `loading`, optional `loadingLabel`, `aria-busy`, disables when loading. |
| BookCard / BookCardGrid / BookCardSkeleton | Card grid item: cover (`BookCoverArt`), catalog code ("Pending" if none), title, contributor groups as filter links to `/library?...`, Categories and Series chips (links; "Unsorted"/"Standalone"), "Manual entry" vs "Library record", "Added on <date>" (`my_books_added_at || latest_submission_at`), "Open record" link. Optional overlays: X remove-from-My-Books button, Kindle send/resend button (only if `hasKindleEmail && book.has_epub_asset`; sent icon when `has_sent_to_kindle`), My Books +/check toggle. Grid shows 6 skeleton cards initially and 6 while loading more; attaches the infinite-scroll observer to the card at `len - CATALOG_TABLE_PREFETCH_TRIGGER`. Busy state per id from three maps. |
| BookCoverArt | `<img>` from `resolveAppUrl(book.cover_download_url)` with lazy loading; falls back to a text placeholder (title + primary contributor) on missing/failed image. |
| BookTable | Catalog table: Book ID, Title (+ source display path for digital), Contributors (grouped by role, or limited to a single role), Category, Series, Publisher, Type pill, Created (date or date-time), My Books Add/Remove, Action (Open [+ Edit]). Options hide/show columns; sort indicator for Title, Book ID, Created (`aria-sort`); mobile card layout via `data-label`; skeleton rows (5/5); `is-highlighted` row; empty row. |
| BookRouteLink | `Link` that passes `state.from` = current path so detail page can return; helpers `getCurrentRoutePath`, `getBookReturnTarget` (only accepts strings beginning with `/`). |
| BookDetailSkeleton / PageSkeleton / PageLoader / ProcessingCardSkeleton / TableSkeletonRows | Loading placeholders. `PageLoader` takes `variant` (table, management, profile, auth, reader, card, generic) and gives `role=status` with screen-reader text. |
| CatalogToolbar + SearchRow + fields + icons | Search form with 400 ms debounced auto-submit, Enter to submit immediately (IME-composition aware), sort select, Filters toggle with active-count badge (counts fields whose value differs from default), result count with spinner, extra actions slot, collapsible filter drawer with fields (`select`, `searchable-select`, text/date input) and Apply / Reset buttons. `onSearchClear` fires immediately when the query becomes empty. Searchable select closes on outside click, filters options by label/value, autofocuses its search box. |
| ConfirmationDialog | Modal with focus trap, Escape/backdrop cancel (blocked while loading), scroll lock, focus restore; confirm button is always the danger-styled `AsyncButton` with hard-coded loading label "Deleting..." (wrong for non-delete uses). Fixed element id `confirmation-dialog-title`. |
| EmailInputFeedback | Live valid/invalid message with icon (`role=status`) using `utils/email`. |
| EmptyState | Title, body and optional actions. |
| ErrorBoundary | Class component; fallback card with "Try again" (resets state) and "Reload page"; logs to console only (no remote reporting). |
| ExportActions | CSV and PDF icon buttons with per-mode loading; disabled while any export runs. |
| KindleIcons | Send and Sent SVGs (sent icon uses fixed `white` stroke). |
| LoadingSpinner | Span with CSS var size. |
| PropertyTable | Generic table for catalog entity lists, infinite-scroll observer, skeleton rows, clones `tr` children to add `data-label` from headers. |
| PropertyTableControls | Unused: client pagination hook + Sort/Rows/First/Prev/Next/Last controls (rows 5,10,20,35,50,100). |
| ScrollToTopButton | Fixed button shown after scrolling > 1 viewport, only on `/home`, `/my-books`, `/notes` (not `/library`, `/categories`, etc.). |
| StatusPill | Pill using `getStatusMeta(value)` (used only by BookDetailHero). |
| TagInput | Chip multi-input with suggestions (max 6, excluding existing, case-insensitive), Enter or comma adds, Backspace removes last, Tab picks suggestion, arrow keys, Esc; commits typed text on blur; exposes `focus()` and `contains()`. Used by the manual book composer. |
| ThemeToggle | Sun/moon button; toggles between light and dark based on the *resolved* theme (never sets "system"). |
| ToastViewport | Renders toast list with icon by type (`success`, `error`, other = info), dismiss button, `role=alert` for errors. |
| TwoFactorSetupPanel | QR (`qr_svg` injected with `dangerouslySetInnerHTML`, unsanitised, trusts server), setup URL, secret, copy URL, optional Cancel (not when `required`), 6-digit token input, confirm button. |

## 5. Local storage / URL state

- URL query params (page filters): HomePage, LibraryPage, CreatedBooksPage, KindleSentPage, CategoryPage, SeriesPage, WriterPage via `filtersFromSearchParams` / `cleanQueryParams` (`utils/query`, not read). Keys: `q, author, series, category, ownership, record_type, sort, kindle_sent, created_after, created_before, contributor, contributor_role` (the last two only as outgoing link params from WriterPage and BookTable/BookCard).
- URL for reader: `slug`, `launch`, `manifest`, `appNav` (hidden|shown). Password pages: `uid`, `token`.
- Router `location.state.from` for return-to-list navigation (BookRouteLink) and for post-2FA return (`/login` state `{from:"/two-factor-setup"}`).
- sessionStorage: `filters-expanded:home`, `filters-expanded:library` (via `useSessionFlag`, value "1"/"0"). Pending export payloads (`LIBRARY_EXPORT_STORAGE_KEY`, `MANUAL_BOOKS_EXPORT_STORAGE_KEY`) via `utils/exportSession` (storage type not verified; stores the full item list).
- Not persisted anywhere: ManualBooksPage filters, Notes tab/query/colour, processing card filters and drawer state, Reprocessing search and selection, theme (handled in `useTheme`, not read).
- No localStorage usage inside my files.

## 6. Bugs, duplication, surprises

1. **Dead pages and code**: `LandingPage` is never imported; `PropertyTableControls`/`useClientPagination` never used; 10 helpers in `processingTableRows.js` dead; stop actions and `StopIcon` unused; `useProcessingCardData` 2 s polling effectively unused.
2. **Duplication**: Home, CreatedBooks and KindleSent copy the same Kindle send handler (identical optimistic `updateEntry`), the same filter plumbing and the same three full-list option fetches (CreatedBooks/KindleSent fetch ALL writers, series and categories, unpaginated, on every mount; Home/Library use `useDynamicFilterOptions` instead). Category, Series and Writer pages are 95% identical (three copies of defaults/filterFields/buildBooksLink). Manual book edit-form mapping and PATCH payload are duplicated between ManualBooksPage and BookDetailPage; PDF/CSV pending-export resume code is duplicated between Library and ManualBooks; password reveal block duplicated across Login/PasswordLink/Profile; the "pause/resume/run" optimistic logic is duplicated in AutomationPanel and CatalogSyncPanel.
3. **ConfirmationDialog** hard-codes loading label "Deleting..." and the danger style for every confirm, including notes/user deletes (ok) but would be wrong for future non-delete confirmations.
4. **Destructive actions without confirmation**: processing "Delete" with `deleteBook:true` (deletes linked books), all Reprocessing deletes/stops, saved-filter delete, bulk deletes.
5. **Unhandled failures**: Reprocessing `act()` has no catch (no toast, unhandled rejection; bulk `Promise.all` leaves selection uncleared). Processing multipage "Regenerate" returns an array so selection clears even on failure. NotesPage count is overwritten with filtered count.
6. **Password/auth**: link-expiry detection by matching English error message text; no client password policy; 2FA QR SVG injected unsanitised (server trusted); `PasswordLinkPage` shows "Log out first" with back link to `/home`.
7. **Raw Provenance** card on the book detail page is labelled "Staff" but not capability-gated in this file (might be filtered server-side).
8. **ManualBooksPage**: `hasManualBookFormInput` treats `binding !== "hard_cover"` as input, but the edit path sets binding `""` for unknown values; "Done" creates a book from a half-filled form silently; 50 ms `setTimeout` hack for blur ordering; filters not in URL (inconsistent with every other list).
9. **Context churn**: `useRequestActions` and `useAutomationActions` return new objects each render so the provider `useMemo` recomputes every render; all consumers re-render on any busy change.
10. **Stream fallback weakness**: during `reconnecting`, only the aggregate state is polled; list cards depend on version bumps inside it. No backoff, no max retry, no heartbeat; SSE URL built via `resolveApiUrl` (cookies via `withCredentials`).
11. **Row refresh cost**: version-driven table refetch uses `limit = rows.length`, so a long-scrolled table refetches everything on every bump.
12. **Time zone** hard-coded to `Asia/Dhaka` in `processingPageModel.formatDate`; Reprocessing `RelTime` uses browser locale.
13. **WriterPage tabs** reset filters (NavLink drops query). **Category/Series/Writer** link builder uses draft `filters.record_type` rather than `appliedFilters`.
14. **ScrollToTopButton** limited to three routes.
15. **Strings**: user-facing text includes emoji in NotesPage hints and buttons (`💬`, `❝`, `✏️`); Bengali keywords for "incomplete" category in code; English-only copy.
16. **Accessibility details**: Notes modal uses `useDialogA11y`, ConfirmationDialog duplicates its own trap; `BookCard` actions use `preventDefault` although not inside a link.
17. `BookDetailPage` mutates `actions.onStartEdit` from the hook result each render (hidden coupling).
18. `CreatedBooksPage` `removingBookIds={{[removeAction.pendingKey]: true}}` supports one in-flight removal only.

## 7. Unread files and why

None of the 76 assigned files is unread. Files referenced but intentionally out of scope (behaviour inferred from usage only): `hooks/*` (useInfiniteCatalogBooks, useDynamicFilterOptions, useMyBooksAction, useSession, useToast, useTheme, useDialogA11y, usePageTitle, useAsyncAction), `utils/*` (query, bookPresentation, bookExport, export, exportSession, capabilities, humanizeError, email, catalogBooks), `api/*` (client, catalog, reading), `features/access/*`, `features/book-detail/*`, `features/profile/*`, `features/manual-books/*`, `features/library/*`, `features/catalog/exportUiTiming`, `features/reader/*`, `features/app/AppRoutes.jsx` (route table and guards), `styles/`, `embedded-reader/`.
