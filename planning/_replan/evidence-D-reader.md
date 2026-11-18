# Evidence D — legacy reader

Status: DRAFT

Source: read-only subagent survey of the reader frontend, `epub-reader` runtime and `apps/access` reader views.

- **Start:** `POST /access/books/<slug>/reader-launch/` (login, scope and Read-Once checks) creates a `PreviewAccessSession` (random token, 2 h expiry, launch count). `GET /access/reader/<token>/manifest/` is AllowAny and token-gated, returns book info, URLs and saved progress/bookmarks/highlights. **The whole EPUB goes to the browser** (`/epub/`, and per-entry `/epub/<path>`) and `/html/`; no-store headers; no DRM or watermarking. Bookmark/highlight/session endpoints need login.
- **Browser engine:** vendored unminified epub.js bundle (~27k lines) running in an iframe, flow scrolled-doc. The reader exists **twice** (`public/epub-reader` standalone PWA and `src/embedded-reader`), no recorded upstream version or licence file.
- **Features:** themes White/Sepia/Night; font size 14–30 px; TOC; keyboard, swipe, pinch, double-tap fullscreen; highlights (5 colours, highlight/quote, note, tags, CFI); bookmarks; progress sync (`last_location`, `progress_percent`) and resume; a11y (skip link, ARIA, focus trap). **Absent:** in-book search, font family, true offline books (service worker caches the app shell only).
- **Server data:** PreviewAccessSession, ReadingSession (unique user+book), Bookmark, Highlight, BookOpeningRecord (Read Once). Endpoints under `/access/`.
- **Tests:** 27 source/contract-string tests in 5 files, no tests of backend reader views or the React layer.
- **Keep:** token-scoped launch with expiry; permission checks; resume and progress; bookmarks/highlights with notes; themes, font size; TOC/keyboard/touch; download and Kindle. **Drop/decide:** duplicate copy, GitHub Pages deploy, vendored dump (use a maintained library only with approval), two API families, whole-EPUB-by-token with AllowAny. **Gaps to decide:** in-book search, font family, offline, DRM.
