Status: DRAFT

# D6 - Reader and design language (legacy analysis for the rebuild)

Sources: `features/13-reader-ui.md` (read in full), `features/19-styles.md` (read in full), reader parts of `features/14c-notes-access-01.md` and `features/09-accounts-common-access.md` (section 5.1, 5.2, 5.6, bugs). Crucial claims were re-checked in code under `archive/app/` (paths below are relative to `archive/app/`). Tags: VERIFIED = I opened the code line in this pass; UNVERIFIED (doc) = taken from the feature docs only.

## 1. Purpose and scope

Purpose: give the designers of the new Rust + Angular Material (M3) app a complete, accurate picture of what the legacy reading experience did, how it was wired to the backend, where it was broken, and what to keep, change or drop. The new app will have the EPUB reader as its own service, so section 5 compares the possible meanings of that phrase.

In scope: the in-app reader (launch, manifest, rendering, TOC, themes, fonts, selection, highlights/quotes/notes, bookmarks, progress), the backend data and permissions behind it (preview vs read vs download), and the legacy visual design language (tokens, type, spacing, breakpoints, dark mode).

Out of scope: the rest of the catalog UI, ingestion, Kindle sending (touched only where it shares gating), notes page UI beyond the reader's data.

Corrections and caveats up front:
- The reader that ships is `src/embedded-reader` (class `ReaderApplication` + vendored epub.js 0.3) mounted by 3 React files in `src/features/reader`. `public/epub-reader` is an older standalone orphan copy (no highlights/bookmarks, with PWA service worker). Only the first is product behaviour. (13-reader-ui section 5; UNVERIFIED doc, but `ls` of `frontend/src/features/reader` VERIFIED the React side.)
- Notes/"My notes" page and reader share the same Highlight/Bookmark tables.

## 2. Reader features and behaviours

Source column: doc section in 13-reader-ui unless stated. All behaviours are UNVERIFIED (doc) unless a code cite is given. "React path" means what a user actually experienced.

### 2.1 Layout and navigation
- D6-F1 Layout mode: single continuous scroll per spine section (`flow: "scrolled-doc"`, width/height 100%); no paginated or two-page mode. (3.1/ section 2 step 8)
- D6-F2 Section stepping: prev/next buttons move one spine section (not a page); buttons hidden at <=560 px and in immersive mode. (3.1)
- D6-F3 Immersive/fullscreen mode: key `F`, double-tap/double-click on a non-interactive area; hides TOC, nav bar, arrows, chapter bar; requests Fullscreen API with webkit fallbacks, rolls back if refused; staged viewport resizes at 0/120/280/520 ms; safe-area aware. Esc exits only through the browser (app Escape handler does not). (3.5)
- D6-F4 Chapter bar: breadcrumb "Part > Chapter" plus location text "<TOC index> / <TOC count>", not a page number; digits localised to Bengali when book language starts `bn`. (3.1)
- D6-F5 App-shell controls: "Toggle main header" and "Back to book"; `appNav=hidden` default query param. (3.11)
- D6-F6 Internal link interception: in-book links routed to `display(href)`; external, `mailto:`, `tel:`, `data:`, `javascript:`, `blob:` left alone. (3.1)

### 2.2 Table of contents
- D6-F7 Collapsible TOC tree in a sliding side panel (`.iconmulu`), expanders, leaf click navigates, current item gets `.selected` + `aria-current` with ancestors auto-expanded. Matching is a loose two-way `endsWith` on href (bug, see 7). (3.1)

### 2.3 Themes
- D6-F8 Three reader themes: white (#000 on #fff), sepia (#704214 on #f4eacd), night (#bdcadb on #1b1f2a). Persisted in `localStorage["epub_reader_theme_index"]`. Triggers: settings buttons, Ctrl/Cmd+1/2/3, two-finger tap cycles, app theme change. (3.2)
- D6-F9 Theme enforcement inside the book iframe: injected `<style>` forcing `color !important` on `body, body *`, inline colour on every element, MutationObserver repaint, re-apply at +0/60/220/600 ms, link and scrollbar palettes, `::selection` tint; skips media elements. (3.2)
- D6-F10 Theme-colour meta tags (`theme-color` light/dark, msapplication) follow the reader theme. (3.2)
- D6-F11 Flash prevention: container class `theme-type-N` set in the constructor; React viewport reads stored theme for the initial background. (section 2 steps 4-5)

### 2.4 Fonts and typography
- D6-F12 Font size 14-30 px, step 2, default 20; A-/A+ buttons, Ctrl/Cmd +/-/= (hijacks browser zoom), pinch (24 px per step). Persisted `epub_reader_font_size`. Applied by `rendition.themes.fontSize`. (3.3)
- D6-F13 No font-family choice, no line-height, margin or width controls; book CSS decides, with blanket `margin:0 !important` on html/body/top wrappers at <=640 px. (3.2, bug 12)
- D6-F14 Bengali typography: nothing reader-specific beyond Bengali numerals in the chapter bar; glyphs depend on installed fonts / book CSS (no `@font-face`, see 19-styles S7). UNVERIFIED (doc) for the reader iframe font stack.

### 2.5 Search and selection
- D6-F15 In-book full-text search: NOT PRESENT in the reader (no search code listed anywhere in 13-reader-ui). Notes page has server-side text search (`q`) over saved notes only (09-accounts 5.6).
- D6-F16 Selection capture: `mouseup`/`touchend` in the iframe plus epub.js `selected` event; builds `{cfiRange, text (<=5000), chapterHref, chapterLabel}`. (3.7)
- D6-F17 Floating selection toolbar (parent document, `role=toolbar`): 5 swatches (green #a5d6a7, yellow #ffeb3b, blue #90caf9, pink #f48fb1, underline #f9a825), note-with-comment, save-as-quote, copy, bookmark; positioned above selection, flips below, clamped; mouse/touch only. (3.7)

### 2.6 Highlights, quotes, notes
- D6-F18 Highlight kinds: `highlight` (colour; underline is a colour) and `quote`. Server stores colour in {yellow, green, blue, pink, underline} and kind in {highlight, quote} (09-accounts 5.1; model color max 16 VERIFIED `backend/apps/access/models.py:~200` via grep of `color = ...max_length=16`).
- D6-F19 Create: POST to `highlights_url` with `{cfi_range, text, chapter_href, chapter_label, color, kind, note}`; CSRF header from `csrftoken` cookie, `credentials: include` (VERIFIED `embedded-reader/.../highlight-methods.js:902-914`). Error shown by `window.alert`.
- D6-F20 Note with comment: modal "Add a comment" (textarea, optional colour dots, Ctrl/Cmd+Enter saves, Esc cancels). Not a real dialog (no role, focus trap). (3.7, 3.12)
- D6-F21 Duplicate handling: same kind and (same CFI range or same trimmed text in the same chapter) is treated as the same annotation; differing colour triggers PATCH. Wrong for repeated phrases (bug 5). (3.7)
- D6-F22 Edit/delete: click an annotation to get a menu with Edit (inline textarea, PATCH `note`) and Delete. No colour change, no tag UI in the reader, although the server supports a `tags` list. (3.7; 09-accounts 5.1)
- D6-F23 Rendering: epub.js SVG marks-pane overlay in the parent document; multiply blend for white/sepia, screen for night; quote kind additionally mutates the book DOM with wrapper span + curly-quote marks (bug 6). Re-applied on rendered/displayed/relocated/content hooks. (section 4)
- D6-F24 Copy selection: Clipboard API with `execCommand` fallback. (3.7)

### 2.7 Bookmarks
- D6-F25 Create only: nav button and toolbar button POST `{location: cfi, chapter_href, chapter_label, label}`; success tints the button amber only if the CFI matches a bookmark made in this session. No list, delete, jump-to or de-dup in the reader; bookmarks are not seeded from the manifest even though the manifest contains them. (3.6, 09-accounts 5.1)

### 2.8 Progress
- D6-F26 Progress sync: on every `relocated` and after first display, 350 ms trailing debounce POST `{last_location: <chapter href, no fragment>, progress_percent: 0-100 (1 decimal)}` to `reading_session_url`; failure only logged. Percent comes from `book.locations.generate()`, so nothing is saved until locations exist. (3.8)
- D6-F27 Resume: chapter file only, never CFI or scroll offset; on failure falls back to book start. (3.8)

### 2.9 Keyboard, touch, gestures
- D6-F28 Keyboard: ArrowLeft/Right = prev/next; F = immersive; Ctrl/Cmd+1/2/3 theme; Ctrl/Cmd +/- font; Esc closes settings panel. Ignored in text inputs; handlers also attached inside each iframe. The shortcuts help modal exists in code but has no DOM in React (unreachable). (3.1, 3.14)
- D6-F29 Touch: swipe left >=90 px (|dx|>2|dy|, <600 ms) = next, right >=100 px (|dx|>4|dy|) = prev, bound on viewer and iframe body; pinch = font size; two-finger tap = cycle theme; double-tap = immersive (not while text is selected). (3.1, 3.3, 3.5)
- D6-F30 Settings panel: theme buttons, font buttons, closes on outside click, window blur, iframe click, Escape. (3.4)

### 2.10 Offline and PWA
- D6-F31 Offline: NONE in the product path. A service worker (cache-first for `.epub`/JSON, precache of ~35 files) and a manifest exist only in the orphan standalone copy and are not registered by the React app. (3.13) Reader requests are `Cache-Control: no-store` server side (09-accounts 5.1), which would defeat offline anyway.
- D6-F32 Local-file reading (file picker) exists only in the orphan standalone copy; dead in React. (3.14, bug 9)

### 2.11 States, errors, accessibility
- D6-F33 States: page-level loader "Opening reader", in-viewer spinner (min 180 ms), `ReaderUnavailable` for launch errors. Manifest/EPUB/render failures are silent blank screens (bug 3). (3.10)
- D6-F34 Accessibility present: aria-label/controls/expanded/pressed/current/disabled on controls, focus-visible outlines, reduced-motion in reset CSS, safe-area insets. Gaps listed in section 7. (3.12)

Feature count per the source doc: about 61 distinct behaviours, about 45 user-facing in the React path.

## 3. Reader lifecycle (step by step)

Endpoints use the `/api/access/` prefix (VERIFIED `backend/apps/access/urls.py:34-43`).

1. User opens a book and chooses Read. Route `/reader/:slug` (or `/reader?manifest=...`) renders `pages/ReaderPage.jsx` (83 lines, VERIFIED it composes `useReaderLaunch`, `useReaderBoot`, `ReaderViewport`; `appNav` default "hidden", lines 21-22).
2. `useReaderLaunch` (VERIFIED `features/reader/useReaderLaunch.js:84`): if the URL has no `manifest`/`launch` param, `POST /api/access/books/{slug}/reader-launch/` with `{}`. Cookie session auth + CSRF (the shared `apiFetch`).
3. Server `ReaderLaunchView` (VERIFIED `backend/apps/access/views/reader.py:35-77`), IsAuthenticated:
   a. 404 if slug unknown.
   b. Non-superuser, non-owner with a Read Once opening record gets 403 "already opened" (lines 41-44).
   c. `allowed = user_can_launch_reader`; also looks up a still-valid `PreviewAccessSession`; neither -> 403 "You do not have reader access for this book." (46-49).
   d. Read-Once-only users (no durable scope, not owner/superuser): `BookOpeningRecord` get_or_create, which consumes the single read (51-60).
   e. Creates `PreviewAccessSession(user, book)` if none; `launch_count += 1`; `expires_at = now + 2 h` refreshed on every launch (VERIFIED lines 62-67; `default_preview_expiry` = 2 hours, `models.py:14-15`). Token default `generate_access_token`, unique CharField(128) (`models.py:118`); 09-accounts says `secrets.token_urlsafe(32)` (UNVERIFIED for the generator body).
   f. Returns `{launch_url, manifest_url, expires_at}`; `launch_url = FRONTEND_BASE_URL + "/reader?manifest=" + urlquote(manifest_url)` (VERIFIED line 72-73). The token therefore sits inside a URL query string.
4. Client normalises the response (6 URL fields), writes `?manifest=<url>` to the address bar (`setSearchParams(replace)`), deletes `launch`.
5. `useReaderBoot`: seeds `localStorage["epub_reader_theme_index"]` from the app theme only when unset or 0/2 (VERIFIED `useReaderBoot.js:40-56`); appends 7 stylesheet links; dynamically imports `runtime-entry.js` (builds `window.ePub`) and `reader-application.js`; `new ReaderApplication().init()`.
6. `init()` -> `loadManifestLaunchIfPresent` reads `manifest` from `window.location.search`, `fetch(manifest, {credentials:"include", Accept: json})` -> `GET /api/access/reader/<token>/manifest/`. AllowAny; the token is the credential (VERIFIED `reader.py:80`).
7. Server manifest (VERIFIED `reader.py:80-100`, rest per 09-accounts 5.1): 404 unless an EPUB asset exists (first row, status not filtered, line 84); if file missing, a "missing asset" flow with side effects; returns `{book:{title,slug}, epub_download_url, html_preview_url, reading_session_url, bookmarks_url, highlights_url, reading_session, bookmarks[], highlights[]}` with no-store headers; for a user-bound session it get_or_creates the `ReadingSession` and inlines all the user's bookmarks and highlights for the book. Guest sessions get empty URLs.
8. Client requires `epub_download_url`, shows the reader container, `ePub(url, {requestCredentials:true})`, `renderTo("viewer", {flow:"scrolled-doc"})`, seeds highlights Map from `manifest.highlights[]`, `rendition.display(manifest.reading_session.last_location)` with fallback to `display()`.
9. Chapter/resource loading: epub.js downloads the whole EPUB once from `GET /api/access/reader/<token>/epub/` (READY asset only, inline FileResponse, no-store) and unzips in the browser with JSZip. Server also exposes `GET .../epub/<asset_path>` that reads a single zip entry (whole file read per call, `..` rejected) - the legacy client path does not need it when epub.js receives the whole archive (UNVERIFIED which of the two epub.js used; the manifest names only `epub_download_url`). Spine sections render in an iframe via the blob/archive resolver (UNVERIFIED mechanism detail).
10. After display: `book.locations.generate()` (browser-side, for percentages), TOC from `book.loaded.navigation`, theme application, swipe/double-tap/keyboard binding inside iframe, loader hidden.
11. Progress sync: each `relocated` event queues `POST /api/access/reader/<token>/session/` (the `reading_session_url` from the manifest) with `{last_location, progress_percent}`, 350 ms debounce. Server requires IsAuthenticated and `session.user_id == request.user.id` (else 403), then updates the single `ReadingSession(user, book)` row (09-accounts 5.1; model `unique_together (user, book)` VERIFIED `models.py:~160`).
12. Annotations: `POST/PATCH/DELETE` to `.../reader/<token>/highlights/[<uuid>/]` and `POST .../bookmarks/` (VERIFIED routes `urls.py:40-43`).
13. Token expiry: 2 h from last launch; expired or unknown token -> 404 "Reader session is unavailable." The client has no refresh path, so a reader left open >2 h gets silent failures on the next progress/annotation call (inference from the endpoints plus 13-reader-ui bug 3; UNVERIFIED in browser).
14. Teardown: `instance.destroy()`; the pending 350 ms progress timer is dropped (last move before closing can be lost).

Initial-progress bug (VERIFIED): `book-initialization-methods.js:147` calls `this.queueReadingStateSync(location)` where `location` is not a local, so it is `window.location`; the payload builder can therefore post the reader page URL as `last_location` until a `relocated` event overrides it.

## 4. What the server stores and exposes for the reader

### 4.1 Data (Django models in `backend/apps/access/models.py`)
- `PreviewAccessSession` (VERIFIED :117-): id UUID, `token` CharField(128) unique, `user` FK nullable (guest-capable but nothing creates guests), `book` FK, `source_submission` FK nullable, `launch_count`, `expires_at` (2 h), timestamps.
- `ReadingSession` (VERIFIED :155-156 fields): one row per `(user, book)` (`unique_together`), `last_location` CharField(255), `progress_percent` FloatField default 0 with no 0-100 validation, `last_opened_at`, link to the preview session.
- `Bookmark`: `(user, book, location)` unique; fields location (<=255), label, note, chapter_href, chapter_label, preview_text (<=280). Duplicate location yields a 500 instead of 400 (09-accounts bugs).
- `Highlight`: `cfi_range` <=1024, chapter_href, chapter_label, `text` (required), `note`, `color` (yellow|green|blue|pink|underline), `kind` (highlight|quote), `tags` JSON list (trimmed, unique, empties dropped). No unique constraint. (09-accounts 5.1, 5.6; model fragments VERIFIED :195-200.)
- `BookOpeningRecord(user, book)` is the Read Once ledger. `PermissionGrant` rows carry scopes with optional expiry and book/category/contributor target.

### 4.2 API exposed (all under `/api/access/`)
| Endpoint | Auth | Purpose |
|---|---|---|
| POST `books/<slug>/reader-launch/` | session, IsAuthenticated | create/refresh preview session, return manifest URL |
| GET `reader/<token>/manifest/` | token only (AllowAny) | manifest incl. bookmarks and highlights |
| GET `reader/<token>/epub/` and `.../epub/<path>` | token only | stream EPUB inline / single zip entry |
| GET `reader/<token>/html/` | token only | normalized preview HTML |
| GET/POST `reader/<token>/session/` | session + token owner | progress |
| GET/POST `reader/<token>/bookmarks/`, DELETE `.../<uuid>/` | session + token owner | bookmarks |
| GET/POST `reader/<token>/highlights/`, PATCH/DELETE `.../<uuid>/` | session + token owner | highlights |
| GET/POST `books/<slug>/reading-session|bookmarks|highlights/` | session + `ensure_book_reader_access` | slug-based twins (used by non-reader pages) |
| DELETE `bookmarks/<uuid>/`, PATCH/DELETE `highlights/<uuid>/` | session, own rows only, no access check | management after access loss |
| GET `me/notes/`, `me/reading-progress/` | session | notes page and "continue reading" list (no pagination) |
(Table from 09-accounts section 1 list items 32-47 and 5.1/5.6; route list VERIFIED `urls.py`.)

### 4.3 Auth model
Two credentials in one flow: Django session cookie + CSRF for launch and all writes, and a bearer-like token in the URL for manifest/epub/html. Token endpoints do not re-check user active status, current grants or revocation (09-accounts 5.1, 3 bugs 5; manifest view having `AllowAny` VERIFIED `reader.py:80,124,166`). Token lifetime 2 h, extended on every launch. Manifest/epub/html and token writes are no-store; slug download endpoints are not.

### 4.4 Permission gating: preview vs read vs download (09-accounts 4, 5.2; UNVERIFIED unless noted)
Scopes: `preview:html`, `read:once`, `read:durable`, `download:file`, `send:kindle` plus owner rule (user has a READY, RESOLVED URL submission for the book) and superuser.
- Launch reader (`user_can_launch_reader`): owner true; read-once-exhausted false; else any of preview:html, read:durable, download:file, read:once. Cover view uses the same rule.
- Preview HTML (`user_can_view_preview_html`): owner true; read-once-exhausted false; else preview:html. Downloading HTML under Read Once consumes the single open.
- Download file (`user_can_download_book_assets`): `download:file` or owner; EPUB is served as attachment with the CURRENT title as filename.
- Annotations on slug endpoints: `ensure_book_reader_access` = any of the four scopes OR live session; owners without grants are blocked there (inconsistent with launch; VERIFIED `views/shared.py:237-249`, no owner check).
- Read Once: first launch OK, second 403 (tests AC6, AC8, AC9 in 14c); HTML+reader share one "once".
- Revocation: grants do not kill live tokens.
So "preview" (HTML), "read" (reader) and "download" (EPUB file) are three separate permissions, but the reader itself delivers the entire EPUB to the browser, so reading effectively equals a download for anyone technically able to read the network response. The `download:file` gate is therefore a UI/filename control, not content protection (inference).

## 5. Architecture of the legacy reader and what it implies for a separate reader service

### 5.1 Legacy structure
- Vanilla JS class `ReaderApplication` (160-line core + 9 prototype mixins via `Object.assign`, 6 theme modules, 2 gesture modules, 6 controllers) wrapping epub.js 0.3.x; mounted by `ReaderViewport.jsx` (238 lines, renders the whole reader DOM in React), `useReaderLaunch.js` (144), `useReaderBoot.js` (112). (13-reader-ui sections 1-2; file list VERIFIED `ls`.)
- Vendored runtime: 8 `*.modules.js` files, 27,360 lines, webpack-style table assigned to `window.ePub`; bundles JSZip 3.5.0, jQuery/Sizzle, xmldom, pako, marks-pane. `src/embedded-reader` is 1.3 MB on disk (VERIFIED `du`); the whole tree is duplicated byte-for-byte in `public/epub-reader` (another 1.3 MB). The epub.js licence header is not bundled (BSD-2 upstream; check).
- `highlight-methods.js` alone is 1355 lines and mixes UI (toolbar, modal, menu), persistence (fetch boilerplate repeated 6x) and rendering.
- Coupling to the old stack: imports `api/urls.js` and `features/reader/manifest.js` from the React tree; hard-coded Django endpoint shapes; reads the `csrftoken` cookie (VERIFIED `highlight-methods.js:902`); depends on cookie credentials on every request; theme index mapping duplicated in three files; relies on `window.location.search` having been written by React before `init()`; DOM must exist before the constructor runs (UNVERIFIED order).
- Not unit-tested: highlights, bookmarks, progress, launch. The 5 tests only exercise the orphan copy and several would fail on the split source (13-reader-ui section 6).

Implication: the reader's real contract with the backend is small and clean - a manifest JSON, an EPUB byte stream, and four small CRUD resources (session, bookmarks, highlights). Everything else (rendering, themes, gestures) is client-only. Rewriting it as a typed Angular component/library against that contract removes the vendored blob's coupling; keeping epub.js as a dependency is a separate decision (needs owner approval per the dependency policy).

### 5.2 Three meanings of "EPUB reader as its own service"

A. Server parses and serves chapters. A reader service opens the EPUB (zip, OPF, nav), serves the TOC/spine as JSON and each chapter as sanitized XHTML/HTML (+ resources by URL); browser renders chapters in its own DOM or iframe.
- Pros: server can sanitize scripts/CSS (fixes stored-XSS vector, 09-accounts bug 6); authorisation per resource (no whole-file hand-over, so read can be genuinely separate from download); can pre-compute locations/page counts, search index, font subsetting; small payload per chapter helps slow phones; one place to normalise Bengali text/fonts; easy token/permission re-check per request; supports server-side full-text search.
- Cons: must implement a robust EPUB 2/3 parser, CSS rewriting, link/resource rewriting, fixed-layout and SVG edge cases (large surface); CFI anchoring must be reproduced or replaced by own anchors; more server CPU/memory and caching design; offline reading harder (needs per-chapter caching).
- Risks: rewriting breaks book styling; per-request unzip cost (legacy sub-resource route already reads the whole zip per call, 09-accounts 5.1); anchor drift if re-parsed content changes (highlights orphaned). Annotations stored against server-generated anchors must be versioned.

B. Browser renders the EPUB. The service only authenticates and streams the EPUB file plus the CRUD APIs; parsing, pagination, CFI and rendering happen client-side (epub.js or a replacement).
- Pros: closest to legacy, smallest server code; mature CFI/pagination available if epub.js is accepted; offline-friendly (cache the file); simple scaling (static byte serving with range requests).
- Cons: the whole book leaves the server (read = download in practice, so permission tiers are policy only); heavy client bundle and parsing on low-end phones; scripts in books run in the browser unless sandboxed (iframe `sandbox`, CSP required); theming of arbitrary publisher CSS is brittle (legacy force-colour hack); locations generation is slow for big books.
- Risks: epub.js is little maintained and a vendored 27k-line blob (supply chain, licence header missing); DOM-mutating quote decoration; token in URL stays a leakage risk unless replaced by header or cookie.

C. Both (hybrid). The service parses once at ingestion/first open and stores a normalised, sanitized package (manifest JSON, per-chapter HTML, resource map, anchor map, TOC, search index); the browser renders the normalised chapters with a thin Angular renderer, and may still download the original EPUB as the separately gated "download".
- Pros: keeps real read-vs-download separation; sanitisation and a stable anchor scheme are done once; fast chapter delivery; search possible; the original EPUB remains the source of truth and is also what Send-to-Kindle needs; client stays thin (no epub.js parse); offline possible by caching normalised chapters.
- Cons: two representations to keep in sync (invalidate on reprocess); biggest build; must define the normalised format and anchor scheme and a migration for legacy CFI highlights (new data model suffices if legacy data is not carried over; UNVERIFIED whether legacy highlights must be migrated - open question).
- Risks: scope creep; subtle rendering differences vs original EPUB (fixed-layout, math, SVG); anchor stability when reprocessing a book.

### 5.3 Recommendation
Choose C in two steps. Step 1 (MVP): the reader service does auth + streaming + CRUD with a server-produced per-book "reading package" (TOC JSON, spine with sanitized chapter HTML and rewritten resource URLs, a stable per-block anchor scheme); the Angular reader renders those chapters natively (no epub.js, no iframe-theme hacks, themes are plain CSS custom properties). Step 2: add search, offline caching and a paginated mode. Rationale: the product is private and invite-only, so the main protection goal is to separate read from download and to remove the stored-XSS and token-in-URL issues; both need the server to mediate content, which A/C give and B cannot. Fall back to B (with epub.js, if the owner approves the dependency) only if C proves too costly; B is acceptable if the owner decides read=download is fine and wants speed of delivery. This is a recommendation, not a decision; it should go through the project's decision process.

Whichever option: the reader service owns launch/session/tokens, progress, bookmarks, highlights and notes APIs; the catalog/access services own entitlement (scope grants, Read Once ledger) and the reader asks them for a decision rather than reading their tables.

## 6. Design language of the legacy app (distilled from 19-styles)

All items UNVERIFIED (doc) unless a cite is shown; S-numbers refer to 19-styles.

- Stack: plain CSS, 56 files, 12,901 lines, no preprocessor or framework; app.css is 32 ordered `@import`s; file slicing driven by a 300-line cap (S1).
- Colour: monochrome forest-green family on translucent glass. Light: ink #17392f, ink-soft #325347, muted #5a6f68, accent #0f4b38, accent-strong #0b3d2e, success #245042, warning #7c6325, danger #8a3434, line rgba(17,70,54,.2). Dark: bg gradient #0e1a16 to #142621, ink #e6f1ea, muted #8aa39a, accent #5fc79b, accent-strong #7fd5ad, success #6fd2a4, warning #e4c071, danger #f08c8c. Success and brand are nearly the same hue (S4).
- Shape and motion: radii 22/16/12 px, pills 999 px; durations 120/180/320 ms; z-index tokens exist but real values range 5 to 99999 (S5).
- Typography: single stack "Avenir Next", "Noto Sans Bengali", "Hind Siliguri", "Kalpurush", sans (Latin first, no `@font-face`); book-cover serif; cursive wordmark; base 16 px; headings via `clamp()`; many 0.56-0.8 rem uppercase micro-labels with 0.06-0.16 em tracking (S7). Notes page alone uses px.
- Spacing: no scale; observed gaps 4-24, shell padding 20/14/12/10/8 by breakpoint; content max-width 1180 (profile 760, dialog 520, toast 400) (S8).
- Elevation: one `--shadow` plus ~40 ad hoc shadows; gradients on nearly every control (primary `#135b45 to #0b3d2e`, danger `#d84a4a to #a83232`); glass blur 8-18 px on many layers; decorative blurred blobs, entrance and hover-lift animations (S9, S10).
- Breakpoints: 1200, 1100, 1024, 1020, 980, 900, 768, 720, 640, 420 (ten values, about three real tiers: 980, 768, 640); desktop-first max-width; no container queries (S27, G).
- Components: buttons (gradient primary/ghost/danger), status pills (12+ states), chips, two near-duplicate toggle switches, tabs (4 variants), searchable select, tag input, toasts (top-right, 400 px), dialog (520 px, radius 24, blur backdrop), skeletons for every page, tables that become stacked cards with `data-label` below 768, sticky glass topbar plus mobile drawer with scroll lock (S17-S22).
- Dark mode: tokens defined 4x; `dark-mode.css` is 1806 lines scoped to `[data-theme="dark"]` only (S11-S14). Reader has independent paper/sepia/night themes scoped to its container (S16).
- Accessibility baseline: skip link, `:focus-visible` outline, `.sr-only`, reduced motion (two conflicting rules), 44 px inputs, safe-area insets; many sub-44 px targets, muted text likely below 4.5:1, `outline:none` on search inputs (E).
- Best local example: `reprocessing-page.css`, token-only, status badge family, column-hide helpers (S29).

## 7. Issues

Severity: H/M/L. Status: VERIFIED (code opened now) or UNVERIFIED (doc only).

| # | Issue | Sev | Status |
|---|---|---|---|
| I1 | Dark-mode bug, mechanism confirmed: `index.html:2` hard-codes `<html data-theme="dark">`; `hooks/useTheme.js:19-21` removes the attribute for "system" (default stored value is "dark", line 10-11). With "System" and OS dark (or light), component dark overrides scoped to `[data-theme="dark"]` do not apply while tokens flip via the media query: mixed light/dark UI. In addition, a light-preferring user sees a dark flash until the effect runs (no inline pre-paint script found in index.html, lines 1-11). Default "dark" masks the bug for most users. | H | VERIFIED (attribute handling) / UNVERIFIED (visual result) |
| I2 | Reader token is the sole credential for manifest, EPUB, HTML; no check for user active state, current grant or revocation; lives 2 h and is extended on every launch; appears in `launch_url` and address bar (`?manifest=<...token...>`) so lands in history and logs; no throttle on token routes. | H | VERIFIED (AllowAny `reader.py:80,124,166`; launch URL `reader.py:72-73`); revocation gap UNVERIFIED (doc) |
| I3 | Scraped book HTML served unsanitized from the API origin (`/html/`, slug HTML download) - stored XSS risk; no CSP or `X-Content-Type-Options`. The EPUB iframe content in the reader also runs book markup without a documented sandbox. | H | UNVERIFIED (doc) |
| I4 | Read = download in practice (whole EPUB streamed to browser), so `download:file` cannot protect content; also Read Once can be bypassed by an offline copy. | M | inference from VERIFIED manifest/epub routes |
| I5 | Initial progress POST uses `window.location` (undefined local `location`) at `book-initialization-methods.js:147`. | M | VERIFIED |
| I6 | Resume only restores chapter, not position; pending debounced progress lost on close; progress_percent not range-validated, `last_location` max 255 (CFIs can exceed). | M | UNVERIFIED (doc); field definitions VERIFIED `models.py:155-156` |
| I7 | Silent failures: manifest fetch, 401/403, missing EPUB, render error leave a blank page with no message or retry; saves use `window.alert`. Expired token (2 h) has no refresh. | M | UNVERIFIED (doc) |
| I8 | Theme sync clobbers the user's sepia choice: boot seeding only when stored is unset/0/2 (VERIFIED `useReaderBoot.js:46-51`) but the effect at lines 103-109 calls `applyThemeByIndex(0|2)` on every app theme change. | L | VERIFIED |
| I9 | Duplicate bookmark location returns HTTP 500 (serializer drops user/book so unique validator not generated); saved-filter same class. | M | UNVERIFIED (doc) |
| I10 | Owner without grants can launch the reader but gets 403 on slug bookmarks/highlights/session (no owner rule in `ensure_book_reader_access`, VERIFIED `views/shared.py:237-249`). Token routes work, so the reader works while the notes pages may not. | M | VERIFIED |
| I11 | Manifest picks the first EPUB asset regardless of status; GET with side effects (marks asset FAILED, queues reprocess) on a transient storage error. | M | VERIFIED line 84 (no status filter); side effects UNVERIFIED (doc) |
| I12 | Sub-resource route reads whole zip into memory per call; no size cap (zip-bomb). | L | UNVERIFIED (doc) |
| I13 | Bookmark button goes dead after reader re-boot (stale handler, `_bookmarkHandlerAttached`); teardown leaks toolbar/listeners; dedup by text mis-merges repeated phrases; quote decoration mutates book DOM; fragile `endsWith` href matching. | M | UNVERIFIED (doc) |
| I14 | Accessibility: annotation features unreachable by keyboard; note modal lacks dialog semantics; Ctrl/Cmd +/- hijacks browser zoom; `user-scalable=no` forced after fullscreen exit; Esc does not leave immersive; emoji as button labels; sub-44 px targets; muted text contrast; `outline:none` on inputs; two conflicting reduced-motion rules. | M | UNVERIFIED (doc) |
| I15 | Duplication: reader tree copied twice (1.3 MB each), 52-line import header copied into 8 files, `readCookie` x5, fetch boilerplate x6, theme index mapping in 3 places; dead code in React mode (shortcuts modal, file picker, landing, SW). | L | duplicate trees VERIFIED (`du`); rest UNVERIFIED (doc) |
| I16 | Heavy theme enforcement (`!important` colour on every element, mutation observer, timed repaint) overrides publisher styling and costs CPU. | M | UNVERIFIED (doc) |
| I17 | CSS: tokens duplicated 4x, 1806-line dark sheet, undefined tokens (`--ink-muted`, `--bg-hover`), ~35 `!important`, red/green semantic overload, uppercase + tracking labels harmful to Bengali, glass blur everywhere, ten breakpoints, sub-44 px targets. | M | UNVERIFIED (doc, S6-S28) |
| I18 | Downloads lack no-store; cover sent as attachment; no audit log writes for downloads/reader opens. | L | UNVERIFIED (doc) |
| I19 | Location label "i / N" is TOC index, not a page; Bengali digits only for chapter bar. | L | UNVERIFIED (doc) |

## 8. Keep / change / drop for the rebuild

### 8.1 Keep (as behaviour)
- Server-issued, expiring reading session and a manifest-style launch response (but see change list).
- Light/Dark/System theme choice, persisted; reader-specific themes (paper, sepia, night).
- Font-size control (add more), progress percentage and resume, bookmarks, highlights with colour + underline, notes, quotes, copy, immersive mode, TOC tree with ancestors expanded, chapter breadcrumb, Bengali numerals for bn books, swipe/arrow navigation, safe-area handling, reduced-motion handling, skip link, 44 px targets, tables-to-cards on phones, skeletons sized to final content, status taxonomy as tonal chips, per-user Read Once concept (if still wanted).
- Server-side notes listing/search over annotations (`me/notes` filters kind/color/q).

### 8.2 Change
- Launch: no token in the URL; use short-lived reading session id with HttpOnly cookie or Authorization header, re-check entitlement on every resource request, refresh before expiry, revoke on grant removal. Reader URL stays `/read/:bookId` with position in the hash/state, not credentials.
- Anchors: store resilient anchors (chapter id + text-quote selector with prefix/suffix + offset, or CFI if option B) so highlights survive font/layout changes and reprocessing; store scroll/offset position in progress, not just chapter.
- Progress: save with `sendBeacon`/flush on pagehide, validate 0-100, accept long locators, idempotent PUT.
- Bookmarks: list, delete, jump, de-dup server side (409/200 existing, never 500); show bookmarked state from server data.
- Annotations: tags UI optional, colour change, edit, keyboard-accessible creation (shortcut + selection menu as a real popover), proper dialog for notes (focus trap, labelled), no `window.alert`; error snackbars with retry.
- Errors: always visible, retry, session-expiry recovery.
- Theme sync: reader keeps its own choice unless the user selects "match app".
- Dark mode: tokens only, one definition (section 8.4); set theme before first paint with an inline script reading storage and `prefers-color-scheme`.
- Typography controls: add font family (serif/sans/Bengali-optimised), line height, margins/width, text alignment; defaults tuned for Bengali.
- In-book search; page or percent location instead of TOC index; optional paginated mode.
- Sanitised content and CSP (iframe sandbox or server-sanitized chapter HTML).
- Keyboard: do not hijack browser zoom; Esc leaves immersive.

### 8.3 Drop
Vendored 27k-line epub runtime copy and the orphan `public/epub-reader` tree; local-file picker/landing page; legacy flat TOC; service-worker cache-first for EPUB/JSON; DOM-mutating quote decoration; per-element forced colouring; `user-scalable=no`; emoji button labels; token in query string; duplicate cross-tree imports; glass blur, blobs, gradients, cursive wordmark, entrance/hover-lift animation, uppercase tracked labels, red-as-state colours; `!important` and the 1806-line dark sheet; ten-breakpoint ladder.

### 8.4 Minimalist M3 light/dark direction (proposal, not a decision)

Principles: Angular Material 3 system tokens (`--mat-sys-*` / `--md-sys-*`) as the single source; calm green seed colour; flat tonal surfaces; no glass; elevation only for overlays; every colour comes from a token so dark mode needs zero component overrides.

Token set (semantic, one definition per theme, via `color-scheme: light dark` and `light-dark()` or a `:root` + `[data-theme="dark"]` + `prefers-color-scheme` triple that shares one source):
- Colour roles: primary, on-primary, primary-container, on-primary-container; secondary (+container); tertiary (info/accent, distinct hue from primary); error (+container); surface, surface-container-lowest..highest, on-surface, on-surface-variant, outline, outline-variant, inverse-surface; plus extended success and warning roles (container + on-container) because M3 has none; scrim.
- Seed: deep green (legacy #0f4b38 as seed; primary tone 40 light / 80 dark). Success must differ from primary: give success a teal-leaning or yellow-green hue, or use icon + label and reserve colour to the tonal chip.
- State layers: hover 8%, focus 10%, pressed 10%, drag 16%, disabled 38% content / 12% container (M3 defaults).
- Reader palette (scoped to reader container): paper (#fff / #1a1a1a text), sepia (#f4eacd / #704214 base kept from legacy), night (#1b1f2a / #bdcadb kept), optional true-black for OLED; text contrast >= 7:1 for body (AAA). Annotation colours defined once as five tokens with light and dark tint variants (green, yellow, blue, pink, underline), at 30-35% fill, using the theme's blend mode.
- Shape: small 8, medium 12, large 16, extra-large 28 (dialogs/sheets), full for chips/switches. Legacy 12-24 collapses to this scale.
- Elevation: M3 levels 0-3 only (cards level 0 outlined or tonal; menus level 2; dialogs level 3); drop ad hoc shadows.
- Motion: durations 100/200/300 ms with M3 standard easing; no entrance animations; respect `prefers-reduced-motion` (one rule, keeps spinners but shortens everything else).
- z-index: five named layers (sticky 10, drawer 20, dialog 30, snackbar 40, tooltip 50), single token file.

Type scale (M3 roles; Bengali-first):
- Families: UI `"Noto Sans Bengali"` (variable web font, self-hosted, `font-display: swap`) with Latin companion Inter or Roboto; reading serif `"Noto Serif Bengali"` plus Latin serif; mono only for code. Load Bengali first so metrics do not depend on installed fonts.
- Sizes (rem, px at 16): display-small 36/44, headline-large 32/40, headline-medium 28/36, headline-small 24/32, title-large 22/28, title-medium 16/24 (500), title-small 14/20, body-large 16/28 (Bengali needs about 1.6-1.75 line height), body-medium 14/24, body-small 12/20, label-large 14/20, label-medium 12/16, label-small 11/16 as an absolute floor (prefer 12).
- Rules: no uppercase transforms, no positive letter-spacing on Bengali text (breaks conjuncts), min 14 px for meaningful text; reader body default 20 px (legacy default) with range 14-32 and line height 1.7-1.9.

Spacing: 4 px base grid; scale 4, 8, 12, 16, 24, 32, 48, 64 (tokens `--space-1..8`); page gutter 16 compact, 24 medium, 24-32 expanded; content max-width 1200 for catalog, 720-760 for reading column (about 60-75 characters), 560 for forms/dialogs.

Breakpoints / window size classes (M3), mobile-first with `min-width`, plus container queries for components:
- Compact 0-599 (single column, bottom navigation or top app bar + drawer, tables become cards, 16 px gutters, reader chrome auto-hides, sheet-style bottom dialogs).
- Medium 600-839 (navigation rail, 2-column grids, reader TOC as modal drawer).
- Expanded 840-1199 (rail or permanent drawer, 3-4 column grids, reader TOC as side panel).
- Large 1200+ and extra-large 1600+ only add max-width centering, not new layouts.
Replace the legacy ten widths with these four, defined once as SCSS/CSS custom media or an Angular CDK `BreakpointObserver` constant, co-located per component, never in a global "tablet" sheet.

Components (Angular Material): top app bar + navigation rail/drawer, filled/tonal/outlined/text buttons (no gradients), tonal chips for status with icon + text, list/card with tonal surface, data table with sticky header collapsing to list on compact, M3 dialog and bottom sheet, snackbar for errors, segmented buttons for theme (System/Light/Dark), slider for font size, progress indicator and skeletons that match final sizes. Red/error only for destructive or failure.

Dark mode: three-state setting (System/Light/Dark) stored in localStorage; inline pre-bootstrap script sets `data-theme` and `color-scheme` before first paint; components reference only tokens so there is no override stylesheet; test both themes in CI with contrast checks (>= 4.5:1 text, 3:1 UI). Fix of legacy I1: the System state must resolve to a concrete light/dark value (apply `data-theme` always, listen to `matchMedia` changes), never leave the attribute off.

Accessibility defaults: 48 px touch targets (M3), visible 3 px focus ring from token, keyboard path for every reader action (annotate via shortcut + popover), screen-reader live region for location changes, dialogs with focus trap, reduced motion, text-scaling to 200% without clipping.

## 9. Open questions

1. Option A, B or C (section 5.3)? Does the owner accept epub.js as a dependency (needs approval) or prefer a custom renderer on server-normalised chapters?
2. Is read-vs-download separation a real requirement (content protection) or only a policy label? It decides whether the full EPUB may reach the browser.
3. Must legacy highlights, bookmarks and reading progress be migrated? CFI anchors from epub.js will not map onto a new anchor scheme without a conversion job.
4. Should Read Once survive? It couples reader launch to a consumable ledger and to HTML preview; the reader service needs a clear entitlement interface.
5. Is in-book search, paginated mode, font-family/line-height controls, offline reading and PWA in scope for the first release?
6. Do annotations need tags (server supports; reader never exposed them) and shared/exported notes (Markdown/CSV/Kindle clippings)?
7. Reader session lifetime and refresh: keep 2 h, sliding, or tied to the user session? Guests/preview sessions: needed at all (model allowed null user; nothing created them)?
8. Should the reader read HTML preview (scraped HTML) at all, given sanitisation cost, or only the built EPUB?
9. Single-package reader service vs reader library embedded in the main web app (deployment unit) - what is the reader service's own database ownership (progress, bookmarks, highlights)?
10. What is the Bengali font hosting plan (self-hosted subset, licence, size budget) and the Bengali line-breaking and numeral policy in UI beyond reader?
11. Are 3 reader themes enough, and should the reader follow the app theme automatically by default?
12. Not verified by me: browser-side behaviour of expired tokens, epub.js resource loading path (whole-file vs per-entry), visual result of the System-theme bug, `models.py` exact line numbers for Highlight/Bookmark (cited approximately).
