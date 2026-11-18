# 13 - Legacy Reader UI (features/reader + embedded-reader + public/epub-reader)

Status: DRAFT (research evidence; read-only record)

Root: `archive/app/frontend`. Read-only analysis of the legacy EPUB reader front end. Paths below are relative to that root.
Abbreviations: `SRC` = `src/embedded-reader/static/js/reader`, `M` = `SRC/reader-application-methods`, `PUB` = `public/epub-reader/static/js/reader`, `FR` = `src/features/reader`.

Key architectural fact: the reader is a **vanilla-JS class (`ReaderApplication`) wrapping a vendored epub.js 0.3 build**, mounted by three thin React hooks/components. It talks to the backend only through a **launch manifest** (URLs for EPUB download, reading-session, bookmarks, highlights). `public/epub-reader/` is an older, standalone, orphaned fork (no highlights/bookmarks) that nothing in the frontend references.

---

## 1. Coverage table

All text files read in full (every line). Binary/vendored files listed in section 8.

| File | Lines | Fully read |
|---|---|---|
| FR/api.js | 9 | yes |
| FR/assets.js | 26 | yes |
| FR/manifest.js | 37 | yes |
| FR/params.js | 27 | yes |
| FR/ReaderUnavailable.jsx | 36 | yes |
| FR/ReaderViewport.jsx | 238 | yes |
| FR/useReaderBoot.js | 112 | yes |
| FR/useReaderLaunch.js | 144 | yes |
| src/embedded-reader static/js/app/boot-reader.js | 48 | yes |
| .../js/app/pwa.js | 44 | yes |
| SRC/reader-application.js | 160 | yes |
| SRC/reader-settings.js | 58 | yes |
| SRC/utils/dom-helpers.js | 61 | yes |
| SRC/utils/double-tap-toggle.js | 160 | yes |
| SRC/utils/gesture-handlers.js | 2 | yes |
| SRC/utils/swipe-gestures.js | 181 | yes |
| SRC/utils/toc-helpers.js | 136 | yes |
| SRC/controllers/iframe-bridge-controller.js | 279 | yes |
| SRC/controllers/iframe-link-interceptor.js | 83 | yes |
| SRC/controllers/loading-indicator-controller.js | 52 | yes |
| SRC/controllers/settings-panel-controller.js | 131 | yes |
| SRC/controllers/shortcut-dialog-controller.js | 100 | yes |
| SRC/controllers/theme-manager.js | 218 | yes |
| SRC/controllers/theme-palettes.js | 51 | yes |
| SRC/controllers/theme-document-application.js | 86 | yes |
| SRC/controllers/theme-document-styles.js | 170 | yes |
| SRC/controllers/theme-element-coloring.js | 106 | yes |
| SRC/controllers/theme-page-application.js | 126 | yes |
| SRC/controllers/theme-scroll-container.js | 82 | yes |
| M/startup-session-methods.js | 223 | yes (52-line import header skimmed as imports only) |
| M/event-binding-methods.js | 235 | yes (same) |
| M/book-initialization-methods.js | 259 | yes (same) |
| M/reading-state-navigation-methods.js | 324 | yes (header + Bengali numeral helper read) |
| M/keyboard-gesture-toc-methods.js | 247 | yes |
| M/theme-viewport-methods.js | 278 | yes |
| M/immersive-fullscreen-methods.js | 266 | yes |
| M/cleanup-resize-methods.js | 97 | yes |
| M/highlight-methods.js | 1355 | yes |
| css/base/helpers.css | 46 | yes |
| css/base/iconfont.css | 33 | yes (line 3 is a base64 woff2, treated as data, not decoded) |
| css/base/reset.css | 104 | yes |
| css/components/landing-screen.css | 225 | yes |
| css/components/reader-layout.css | 4 | yes (4 @imports) |
| css/components/reader-layout/reader-frame-and-toc.css | 355 | yes |
| css/components/reader-layout/reader-settings-and-viewer.css | 247 | yes |
| css/components/reader-layout/immersive-fullscreen-and-loading.css | 209 | yes |
| css/components/reader-layout/responsive-reader-layout.css | 264 | yes |
| css/components/shortcuts-dialog.css | 216 | yes |
| css/themes/theme-overrides.css | 176 | yes |
| css/themes/theme-tokens.css | 175 | yes |
| static/img/book.svg | 15 | yes |
| public/epub-reader/index.html | 283 | yes |
| public/epub-reader/README.md | 89 | yes |
| public/epub-reader/CNAME, VERSION | 0 / 1 | yes |
| public/epub-reader/manifest.webmanifest | 26 | yes |
| public/epub-reader/service-worker.js | 200 | yes |
| public/epub-reader/docs/FEATURE_BEHAVIOR_BASELINE.md | 85 | yes |
| public/epub-reader/tests/*.test.mjs (5 files) | 93+85+208+101+49 | yes |
| PUB/reader-application.js (monolith) | 1414 | yes |
| PUB/reader-settings.js | 57 | yes |
| PUB/controllers/theme-manager.js (monolith) | 675 | yes |
| PUB/controllers/iframe-bridge-controller.js | 336 | yes |
| PUB/utils/gesture-handlers.js (monolith) | 322 | yes |
| PUB/utils/toc-helpers.js | 65 | yes |
| public static/css/components/reader-layout.css (monolith) | 856 | yes |
| public css/themes/theme-overrides.css | 119 | yes |
| public css/themes/theme-tokens.css | 152 | yes |
| public twins of boot-reader.js, pwa.js, loading-indicator, settings-panel, shortcut-dialog, dom-helpers, helpers/iconfont/reset/landing/shortcuts css, book.svg | various | yes - `cmp` proves byte-identical to the src copy that was read |

Totals: about 120 files in scope counting both copies; 0 text files left unread (binary + vendored in section 8).

---

## 2. Launch / boot sequence (React path, the only one the product uses)

1. `pages/ReaderPage.jsx` (outside my scope, only referenced) calls `useReaderLaunch`, then `useReaderBoot`, and renders `ReaderViewport` or `ReaderUnavailable`.
2. **useReaderLaunch** (FR/useReaderLaunch.js:17-135). Inputs: route `slug`, query params `launch`, `manifest`. Decodes with `decodeURIComponent` (params.js:1-11).
   - If `manifest` param present: absolutise via `resolveAppUrl`; if changed or a `launch` param exists, `setSearchParams(replace)` sets `manifest`, deletes `launch`, defaults `appNav=hidden` (lines 38-57).
   - Else if `launch` param: extract `?manifest=` from the launch URL (params.js:13-27), set it (59-78).
   - Else needs slug (`"Missing reader details. Open a book and try again."`, line 81), then `POST /access/books/{slug}/reader-launch/` with `{}` body (84-87). Response normalised (6 URL fields, manifest.js:14-37) and `manifest_url || manifest_from(launch_url)` used (manifest.js:7-12). Missing -> `"Reader manifest is not available for this book yet."` (94).
   - Errors -> `setError` + `toast.error` (112-116) -> `ReaderUnavailable`.
3. **useReaderBoot** runs when `manifestUrl` exists (FR/useReaderBoot.js:35-100):
   - Seeds `localStorage["epub_reader_theme_index"]` from the app theme (0 light, 2 dark) only if unset or currently 0/2 (44-55). Sepia (1) is never overwritten at boot.
   - Appends 7 `<link rel=stylesheet>` to `document.head` (assets.js:9-17; order: reset, iconfont, helpers, shortcuts, layout, tokens, overrides). `landing-screen.css` is NOT loaded in React.
   - Dynamic-imports `runtime-entry.js` and `reader-application.js` (assets.js:19-26), `await ensureEpubRuntime()` (builds the webpack-style module table, sets `window.ePub`), then `new ReaderApplication(); instance.init();` and `setIsReaderBooted(true)`. `finally` -> `setLoading(false)`.
   - Cleanup: `instance.destroy()`, removes the style nodes (20-23, 94-99).
   - Second effect (103-109): when the app theme changes after boot, calls `instance.applyThemeByIndex(0|2)` (so a user's sepia choice is overwritten whenever the app theme toggles).
4. **ReaderViewport** (FR/ReaderViewport.jsx) renders the whole reader DOM in React (`#epub-contents-panel`, nav buttons, `#reader-settings-panel`, `#reader-bookmark-btn`, `#reader-chapter-name`/`#reader-location`, `#viewer`). Initial background colour derives from `localStorage` theme (7-18) to avoid a flash. Boot overlay `PageLoader` until `isReaderBooted` (227-235). It contains NO `#shortcut-modal`, `#open-epub`, `.open-ebook-page`, `#reader-chapter-label`.
5. **ReaderApplication constructor** (SRC/reader-application.js:64-146): query DOM nodes (M/startup:55-70); read stored theme/font (clamped, defaults theme 0, font 20); create LoadingIndicator (min 180 ms), ThemeManager (`setInitialState` immediately adds class `theme-type-N` to `.epub-container`, theme-manager.js:58-75), ShortcutDialog (modal null in React), IframeBridge (`#viewer iframe`), SettingsPanel (trigger `.iconshezhi`), swipe binder.
6. **init()** (M/startup:166-189): throws if `window.ePub` missing; `bindEvents` (all delegated on `document`), `setupReaderWrapperContainerModeToggle`, `setupKeyboardShortcuts`, aria sync, `syncSystemThemeColor(undefined, "#0B3D2E")` (theme-color metas), `fullscreenchange`/`webkitfullscreenchange` listeners, then `loadManifestLaunchIfPresent`.
7. **loadManifestLaunchIfPresent** (M/startup:124-165): reads `?manifest=` from `window.location.search` (so it relies on React having already written it), shows loader, `fetch(manifest, {credentials:"include", Accept: json})`; requires `epub_download_url` (else throws); stores `launchManifest`; `showElementFlex(.epub-reader-container)` (CSS default is `display:none`), `initializeBook(epub_download_url, {initialLocation: manifest.reading_session.last_location, launchManifest})`. On any failure only `console.error` + loader hide: **no user-visible error** (see bugs).
8. **initializeBook** (M/book-initialization:56-197):
   - New session id, teardown previous book, show loader, normalise manifest, `seedHighlightsFromManifest` (manifest.highlights[] -> in-memory Map).
   - `window.ePub(url, {requestCredentials:true})` (cookies sent for protected EPUB), `book.renderTo("viewer", {flow:"scrolled-doc", width:"100%", height:"100%"})`.
   - Registers rendition handlers (`rendered` -> reapply theme; `relocated` -> update href/section/TOC/progress sync/iframe interactions) + highlight handlers.
   - `rendition.display(initialLocation)` falling back to `display()` on failure; then registers 3 themes, sets font size, applies theme, wires swipe, waits for iframe content ready (images loaded or 10 s), hides loader, syncs TOC selection, queues progress save, schedules iframe interactions at +200 ms.
   - In parallel: `book.ready` -> `locations.generate()` (for percentages; failure only logged); `book.loaded.navigation` -> TOC tree render + chapter bar.
   - Fatal errors (`handleFatalBookError`) -> `closeBook()` which hides the reader container (in React => blank area; no message).

Standalone (public copy) boot: `index.html` loads `pwa.js` + `boot-reader.js` (module) -> `ensureEpubRuntime` -> `new ReaderApplication().init()`, stored on `window.__epubReaderApp`; shows landing page with file picker; `?manifest=` supported (README:56-62).

---

## 3. Reader features and actions

### 3.1 Navigation
- **Prev/Next arrow buttons** `.prev-btn`/`.next-btn` (ReaderViewport.jsx:200-222; handler M/event-binding:87-97). Step is by **spine section** (`changePrev/Next`, M/reading-state-navigation:149-166), `book.section(n).href` then `display(href)` (167-228). Hidden at <=560 px (responsive css:209-211) and in immersive mode.
- **Keyboard**: ArrowLeft/Right prev/next (M/keyboard-gesture-toc:104-107). Ignored when focus is in input/textarea/select/contenteditable/role=textbox (78-87) or `defaultPrevented`; also ignored while shortcut modal is open except Escape (89-96). Same handler is attached inside each iframe document (199).
- **Swipe** (SRC/utils/swipe-gestures.js:154-168): within 600 ms, left swipe >=90 px and |dx|>2|dy| -> next; right swipe >=100 px and |dx|>4|dy| -> prev. Bound on `#viewer` container (M/keyboard-gesture-toc:138-144) and on iframe `body` (143, 189).
- **Internal link interception**: clicks on `<a href>` inside the iframe that are not external/`mailto:`/`tel:`/`data:`/`javascript:`/`blob:`/`//`/`http(s)` (but `urn:epub:` allowed) are cancelled and routed to `display(resolvedHref)`; bare `#frag` is resolved against current href (iframe-link-interceptor.js:4-66; M/keyboard-gesture-toc:157-180). External links are left alone (iframe default navigation).
- **TOC**: toggle `.iconmulu` slides the panel (class `close` on `.epub-contents` and `.reader-wrapper`, +resizes viewer after 320 ms, M/keyboard-gesture-toc:209-228). Tree rendered by `renderTocTree` with `.toc-toggle` expanders (toc-helpers.js:44-73); parent label click collapses an open node (M/theme-viewport:55-75), expander click toggles (M/event-binding:176-187), leaf click navigates (77-84). `syncSelectedTocItem` marks `.selected` + `aria-current` and auto-expands ancestors (toc-helpers.js:75-120). Matching is by loose href suffix.
- **Chapter bar / location** (M/reading-state-navigation:260-323; `#reader-chapter-name`, `#reader-location`): breadcrumb "Part > Chapter" from `ancestorLabels`, prefers a leaf TOC entry when several share a file; location text is `"<flat TOC index> / <flat TOC count>"` (not a page number); digits localised to Bengali when book language starts with `bn` (49-54, 318).
- Legacy `#reader-chapter-label` + `syncChapterLabel` (M/theme-viewport:140-171) is dead in React (element absent) and also used by `lookupChapterLabel` (highlight-methods.js:596) for highlight/bookmark labels.

### 3.2 Themes
- Three themes (SRC/reader-settings.js:14-42): white (#000 on #fff), sepia (#704214 on #f4eacd), night (#bdcadb on #1b1f2a). Index persisted to `localStorage["epub_reader_theme_index"]` (theme-manager.js:127, 136-142).
- Triggers: settings buttons `.bg-btn[data-type]` (M/theme-viewport:242-246), Ctrl/Cmd+1/2/3 (keyboard:118-126), two-finger tap cycles (swipe-gestures.js:129-142), app theme change (useReaderBoot:103-109).
- `setTheme` (theme-manager.js:121-134): `rendition.themes.select`, container class `theme-type-N`, applies styles to every iframe doc, updates `<meta name=theme-color>` (+ light/dark media variants, msapplication; on Android also sets html/body bg; theme-page-application.js:34-65).
- Iframe injection (theme-document-styles.js, theme-document-application.js, theme-element-coloring.js): injects `<style id=epub-mobile-reset>` (<=640 px resets margins, images max-width) and `<style id=epub-theme-overrides>` (forces `body, body *` colour + `-webkit-text-fill-color` with `!important`, link palette per theme, scrollbar palette, selection tint `${link}55`, user-select text), paints inline `style` colour on every element, and installs a `MutationObserver` (style/class/childList) to repaint new nodes via rAF. Re-applied at +0/60/220/600 ms (theme-page-application.js:122-125). Links excluded from forced colour. Skips img/video/audio/canvas/source/picture/script/style.
- Scroll host heuristic (theme-scroll-container.js): if iframe `body` cannot scroll and the largest structural child holds >180 chars and >50% of text, that child becomes `.reader-scroll-container`; re-validated over 2 rAFs.
- CSS tokens per theme `--page-background`, `--toc-*`, `--nav-*`, `--settings-*`, `--reader-*`, scrollbar vars (theme-tokens.css:1-175), applied via `theme-overrides.css`.

### 3.3 Font size
- Range 14-30 px, step 2, default 20 (reader-settings.js:44-47). Settings `A`/`A` buttons (`data-tag=small|big`, M/theme-viewport:233-241 / keyboard:233-241), Ctrl/Cmd +/=/-  (keyboard:127-133, `preventDefault` so it hijacks browser zoom), pinch (24 px per step, swipe-gestures.js:119-126). Applied via `rendition.themes.fontSize("<n>px")`; persisted `localStorage["epub_reader_font_size"]` (theme-manager.js:91-106). Buttons set `disabled`+`aria-disabled` at limits (M/theme-viewport:123-135).

### 3.4 Settings panel
`SettingsPanelController` (131 lines): `.setting-wrapper` toggled by class `show`, `aria-hidden`/`aria-expanded` kept in sync; closes on outside click (document `click`), on window blur when focus is inside the iframe, on iframe click (listener registered through the bridge) and on Escape (keyboard:108-110).

### 3.5 Fullscreen / immersive mode
- Toggle: key `F` (needs an open book), double-tap / double-click on non-interactive area (double-tap-toggle.js: 300 ms window, <12 px movement; bound on viewer container and iframe body). 
- `toggleImmersiveMode` (M/immersive-fullscreen:55-200): adds `immersive-reading` class (hides TOC, nav bar, arrows, chapter bar; `.reader-wrapper` becomes fixed full-screen), requests Fullscreen API on `.reader-wrapper` (with webkit fallbacks), verifies after 140 ms and rolls back if the browser refused, then runs staged `resizeReaderViewport` at 0/120/280/520 ms (exit: 0/140/320/620 ms plus 220 ms resize delay).
- On exit resets viewport meta (`initial/min/max-scale=1, user-scalable=no, viewport-fit=cover`) for 420 ms to defeat mobile zoom (202-258).
- Browser-initiated exit (Esc) handled via `fullscreenchange` (M/theme-viewport:172-183). The app's own Escape handler does NOT exit immersive.
- Wrapper resize uses `rendition.resize(w,h)` with 4 fallbacks for measuring size (theme-viewport:211-277).

### 3.6 Bookmarks
- Only **create**. Nav button `#reader-bookmark-btn` and a toolbar button both call `createBookmarkAtCurrentLocation` (highlight-methods.js:1253-1298): needs `launchManifest.bookmarks_url`; `POST {location: cfi, chapter_href, chapter_label, label: chapter_label || "Bookmarked page"}` with `credentials: include` + `X-CSRFToken` from the `csrftoken` cookie; on success stores in an in-memory Map, tints the button amber (`#f59e0b`) and tooltip "Page already bookmarked" if the current CFI equals a bookmark created **in this session** (1236-1249); toolbar feedback "Bookmarked"; failure -> `window.alert("Could not save bookmark. Please try again.")`.
- No list, delete, jump-to or de-duplication in the reader; bookmarks are not seeded from the manifest (only highlights are, line 70-80). Handler attached once per button (`_bookmarkHandlerAttached`, 1226).

### 3.7 Highlights / underline / quotes / notes
- **Selection toolbar** (`ensureHighlightToolbar`, highlight-methods.js:373-521): dark floating toolbar in the parent document; 5 swatches **green #a5d6a7, yellow #ffeb3b, blue #90caf9, pink #f48fb1, underline #f9a825**; buttons: note-with-comment (green + modal), save-as-quote, copy selection, bookmark. Mousedown/touchstart `preventDefault` so the iframe selection survives. Positioned above the selection (flips below), clamped to viewport (605-656). Hidden on page change, new selection start, outside mousedown.
- Selection detection: per-content `mouseup`/`touchend` in iframe (`bindHighlightContents`, 127-190) plus epub.js `selected` event (121-124); builds `pendingSelection {cfiRange, text (<=5000 chars), chapterHref, chapterLabel}` (558-594).
- **Kinds**: `highlight` (colour) and `quote` (`createQuoteFromSelection`, 861-863: color fixed "yellow", kind "quote"). Underline is a *colour* of kind highlight.
- **Create** (`_persistSelection`, 865-1002): in-flight guard; needs `launchManifest.highlights_url`; `POST {cfi_range, text, chapter_href, chapter_label, color, kind, note}`; server response stored by `id`; applied; toolbar feedback "Saved"/"Quote saved"; errors -> `console.error` + `window.alert("Could not save selection. Please try again.")`; selection cleared in every iframe.
- **Note with comment**: promise-based modal "Add a comment" (693-855): textarea, optional colour dots (non-underline), Ctrl/Cmd+Enter saves, Esc/overlay cancels; dark mode from `html.dark` or `prefers-color-scheme`.
- **Duplicate handling** (885-932): same `kind` and (same `cfi_range` OR identical trimmed text within the same chapter) => no new row; if colour differs `PATCH {highlights_url}/{id}/ {color}`; message "Color updated" even when nothing changed.
- **Click an existing annotation** -> menu (`showAnnotationMenu`, 1006-1179) with Edit (inline textarea -> `PATCH {note}`) and Delete (`DELETE`). Outside-click dismissal attached to parent doc and every iframe doc. No colour change and no tag UI there.
- **Tags**: not present in any reader code. Only `note`, `color`, `kind`, `text`, chapter fields exist.
- **Copy** (658-688): `navigator.clipboard.writeText`, fallback `execCommand("copy")`.

### 3.8 Progress save / resume
- Save: on every `relocated` and after first display, `queueReadingStateSync` (M/reading-state-navigation:63-90): needs `launchManifest.reading_session_url`; payload `{last_location: <href without #fragment, URI-decoded>, progress_percent: round(percentageFromCfi*1000)/10 clamped 0-100}`; **350 ms trailing debounce**; `POST` with `credentials: include`, JSON, `X-CSRFToken`; failure only `console.error`. Timer cleared on teardown (so the last position before closing within 350 ms is lost).
- Resume: `manifest.reading_session.last_location` -> `rendition.display(thatHref)`; failure falls back to `display()` (book start). **Only the chapter file is restored, never the scroll position or CFI** (flow is scrolled-doc).
- `progress_percent` is derived from `book.locations` (epub.js location generation at default granularity, generated after `book.ready`); not saved until generated.

### 3.9 Settings persistence (storage keys)
- `localStorage["epub_reader_theme_index"]` (int 0-2), `localStorage["epub_reader_font_size"]` (int 14-30). Read with try/catch (M/startup:71-81). No other client storage in the reader. Server-side state: reading session, bookmarks, highlights (via manifest URLs).

### 3.10 Loading, error, empty states
- Page-level boot overlay `PageLoader` "Opening reader / Loading EPUB reader assets." (ReaderViewport.jsx:227-235).
- In-viewer spinner: class `loading` on `.reader-wrapper-container` with minimum visible time 180 ms (loading-indicator-controller.js).
- Launch/boot errors: `ReaderUnavailable` heading "Reader unavailable" + message + "Show/Hide main header" and "Back to book" buttons + toast. Boot failure message "Failed to initialize EPUB reader."
- Silent failures: manifest fetch/parse error, EPUB create/render error, locations/TOC failure, reading-state POST failure (console only). Highlight/bookmark save failure uses `window.alert`.
- Local-file failure (standalone only): FileReader error/abort -> back to landing page.

### 3.11 App-shell integration controls
- "Toggle main header" (`toggleAppNav`) and "Back to book" (`navigate(targetBookPath)`) buttons in the reader nav (ReaderViewport.jsx:150-191); `appNav=hidden` default query param.

### 3.12 Accessibility
- Semantic buttons with `aria-label`, `aria-controls`, `aria-expanded` on TOC and settings triggers (kept in sync), `aria-haspopup`, `role="group"` + `aria-hidden` on the settings panel, `aria-pressed` on theme buttons, `aria-disabled` on font buttons, `aria-current` on the TOC selection, `section aria-label="EPUB reader"`, `role="toolbar"` on the highlight toolbar, focus-visible outlines, `prefers-reduced-motion` handling (reset.css:95-104), skip link to `#reader-controls` (standalone only; css in reset.css:72-93), shortcut modal focus trap + focus restore + Esc (shortcut-dialog-controller.js; standalone only), `aria-live=polite` on the legacy chapter label (standalone only).
- Gaps: note modal has no role=dialog/focus trap/label for textarea; annotation menu and highlight toolbar are mouse/touch only (no keyboard path to create/edit/delete annotations); iframe content gets no landmarks; `user-scalable=no` is forced after fullscreen exit.

### 3.13 Service worker / PWA (standalone copy only; not used in React app)
- `public/epub-reader/service-worker.js`: cache `epub-reader-v6`; install pre-caches ~35 shell files (HTML, manifest, css, js, runtime, images) with `Promise.allSettled` and `skipWaiting`; activate deletes other caches + `clients.claim`; fetch handler: same-origin GET http(s) only; network-first for navigation and `.html/.js/.css/.webmanifest` (fallback to cache, then `index.html`, then `503 Offline`); **cache-first for everything else** (images, any `.epub`, JSON) with put-on-miss; query-string requests never match cache (except navigation). Pre-cache list names only the monolith's modules, so it would not match the src (split) tree.
- `pwa.js` registers `./service-worker.js` (`updateViaCache:"none"`) on `load`, calls `registration.update()`, and toggles `html.reader-open` via a MutationObserver on `.open-ebook-page`.
- `manifest.webmanifest`: standalone, name "Simple EPUB Reader", theme/bg `#0B3D2E`, 192/512 PNG icons, `purpose: any` only (no maskable). `CNAME` = `ereader.rsalehin24.me`, version `v1.1`.

### 3.14 Other
- Standalone landing page: file picker (`.epub`), shortcuts modal (keyboard + gesture lists), copyright text, `landing-screen.css`.
- Shortcuts modal in src exists in JS/CSS but has no DOM in React => unreachable.
- Safe-area insets (`env(safe-area-inset-*)`) throughout; `100dvh`; touch-action manipulation; `overscroll-behavior:none` on root (standalone).

**Feature count**: 11 navigation/TOC/chapter, 6 theme, 3 font, 3 settings-panel/persistence, 5 fullscreen/immersive, 3 bookmark, 9 highlight/quote/note, 3 progress, 4 states/errors, 2 app-shell, 5 a11y, 4 PWA/SW, 3 standalone-only extras = about 61 distinct behaviours (about 45 user-facing in the React path).

---

## 4. How highlights are anchored and re-rendered

- **Anchor**: epub.js CFI range string (`cfi_range`) from `contents.cfiFromRange(range)` (highlight-methods.js:168) or the `selected` event argument. Stored with the plain `text` (<=5000), `chapter_href`, `chapter_label`. CFIs are relative to the EPUB package/spine position of the source file; they depend on the exact DOM structure of the EPUB XHTML (epub.js ignores its own injected nodes via a filter, but see risk below).
- **Seed**: `launchManifest.highlights[]` (each needs `id`, `cfi_range`, `color`, `kind`, `note`) loaded into `this.highlights` (Map) before display (70-80). Created/updated rows come from the API response.
- **Render**: `rendition.annotations.highlight(cfi, {id,color}, onClick, "epubjs-hl", {fill, fill-opacity:0.3})` for colours; `annotations.underline(cfi, {id}, onClick, "epub-underline")` for the underline colour; quotes use `annotations.underline(..., {id, color:"quote"}, onClick, "epubjs-quote")`. epub.js draws an SVG overlay (marks-pane) **in the parent document** over the iframe, so CSS is injected into the parent head (`ensureParentAnnotationStyles`, 32-58): rects 0.35 opacity, `mix-blend-mode: multiply` for themes 0/1 and `screen` (0.55 opacity) for night, orange 2.5 px underline `#e67e22`, purple 1.5 px quote line `#c084fc`, pointer cursor.
- **Re-render triggers**: `applyPendingHighlights` runs at attach, on `rendered`, `displayed`, `relocated`, and per-content via `rendition.hooks.content` (95-118). An `appliedHighlightIds` Set prevents double-adding; epub.js itself re-attaches stored annotations to a section whenever it is rendered. No re-layout re-anchoring is done after font-size or resize (relies on marks-pane recalculation).
- **Remove**: `annotations.remove(cfi, type)` where type is the remembered `"highlight"|"underline"` (`appliedHighlightTypes`), plus quote DOM undo (267-282).
- **Quote decoration**: for kind `quote`, `contents.range(cfi).extractContents()` is wrapped in `<span class="epubjs-quote-text" data-quote-id>` and flanked by two `<span class="epubjs-quote-mark">` curly quotes inserted **into the book DOM** (284-341). Idempotent per iframe through `data-quote-id`; failures (range across elements) are silently skipped.
- **Click handling**: annotation click callback -> `showAnnotationMenu(id, event)` positions below the SVG `<g>` rect.

---

## 5. Differences between the two copies

| Aspect | `src/embedded-reader` (used by React app) | `public/epub-reader` (standalone, orphan) |
|---|---|---|
| Structure | `ReaderApplication` class + 9 mixin files via `Object.assign(prototype)`; theme manager split into 6 modules; gestures split into `double-tap-toggle.js` + `swipe-gestures.js`; link interceptor extracted | One 1414-line `reader-application.js`; 675-line `theme-manager.js`; 322-line `gesture-handlers.js`; iframe bridge has link interception inline |
| Highlights / quotes / notes / bookmarks | yes (`highlight-methods.js`, 1355 lines) | none |
| Manifest fetch | `credentials:"include"`, `resolveAppUrl()` on URLs, imports `features/reader/manifest.js` and `api/urls.js` (cross-dependency into React tree) | plain `fetch`, no credentials, raw URL |
| Progress POST | adds `credentials:include` and `X-CSRFToken` | none (cannot authenticate to Django) |
| EPUB request | `ePub(url, {requestCredentials:true})` | `ePub(source, {})` |
| TOC | collapsible tree (`renderTocTree`, expand/collapse, auto-expand ancestors), loose href match | flat list with `margin-left`, first item pre-selected, exact `data-href === currentHref` match |
| Chapter bar | breadcrumb + "i / N" (`#reader-chapter-name/#reader-location`) and legacy `#reader-chapter-label` | `#reader-chapter-label` element exists in HTML but no JS fills it (selector not even defined) |
| Selection vs double-tap | double-tap/click does not toggle or clear while text is selected (`hasActiveTextSelection`) | always clears selection |
| Theme container class | applied at construction (`setInitialState`) to avoid flash | applied only on first `setTheme` |
| `::selection` tint | injected per theme | absent |
| Theme CSS | adds `.epub-container{background:var(--page-background)}`, `--reader-text-dim` token, chapter-bar CSS, split reader-layout into 4 files | single 856-line `reader-layout.css`, no chapter bar CSS |
| Entry | no `index.html`; `boot-reader.js`/`pwa.js` present but unused in React; `window.__epubReaderApp` never set in React | `index.html` landing page + SW + manifest + README + docs + tests |
| `landing-screen.css`, shortcuts css, iconfont, helpers, reset, book.svg, PNGs, vendored runtime | identical bytes | identical bytes |
| Tests | none | 5 test files |

Neither copy is "the source of truth" documented: the public README does not mention highlights or the split layout.

---

## 6. Tests present (all under `public/epub-reader/tests`, run with `node --test tests/*.test.mjs`, no deps)

- `accessibility-ui.test.mjs`: regex over `index.html` and JS source: `open-new-book` is a `<button>`, skip link exists, nav controls have aria-labels, aria-controls/expanded wiring, `aria-pressed`, TOC helper renders `<button>` rows (no `role=button`), source contains `syncTocToggleAriaState`, `aria-expanded` and `aria-pressed` setters, `button.disabled = isDisabled`.
- `interaction-controller-contract.test.mjs`: shortcut controller has focus trap/restore; CSS has `.bg-btn.is-active`, `[aria-pressed=true]`, `.size-btn:disabled`; app never adds `close` class to viewer; theme manager source contains `validateScrollContainer`, `bodyCanScroll`, `body.reader-scroll-host` rule, `isDocumentUsable`, user-select text; fullscreen resize functions exist; vendored modules use `pagehide` not `unload`; SW uses `ignoreSearch:false` and returns null on query strings; app source has `getLaunchManifestUrl`, `loadManifestLaunchIfPresent`, `epub_download_url`, `reading_session_url`, `queueReadingStateSync(location)`, `fetch(syncUrl,`.
- `responsive-layout.test.mjs`: regex over CSS for safe-area vars, no page scroll, reduced motion, breakpoints (1200/1024/900/720/560, heights 760/620, landscape 500), immersive padding, compact TOC rail rules at 700 px, iframe sizing, landing breakpoints.
- `theme-visual-contract.test.mjs`: token variables present, no `--nav-close-*`, overrides keep `wrapper-main` as background host, nav icons inline SVG, theme manager source has `const scrollbarPaletteByTheme = {` etc.
- `playwright-smoke.test.mjs` (skipped when Playwright absent): static server, 390x844 viewport; asserts compact TOC rail hides main + settings, immersive mode keeps padding and clears `loading`, injected iframe theme style contains `user-select:text` and `body, body *` but no `div {` reset.
- Not tested anywhere: highlights, bookmarks, quotes, progress POST payload/debounce, resume, launch hooks, React components, src (split) tree. Several tests are string greps on the standalone source and would fail against the refactored src tree (e.g. `const scrollbarPaletteByTheme`, `queueReadingStateSync(location)` inside one file).

---

## 7. Bugs, duplication, surprises

1. **Initial progress POST sends the page URL.** In `initializeBook`'s second `.then`, `location` is not in scope, so it resolves to the global `window.location` (M/book-initialization:147; same in public:518). `buildReadingStatePayload` then reads `location.href` and would POST `last_location = <reader page URL without hash>` if no `relocated` event overrides within the 350 ms debounce. On resume `display(thatUrl)` fails and falls back to the book start.
2. **Resume is chapter-level only**: `last_location` is the spine href; CFI/scroll offset is never saved, though `progress_percent` is. Backend column `last_location` is `CharField(255)` (`backend/apps/access/models.py:155`).
3. **Silent blank screen**: `.epub-reader-container` defaults to `display:none` and is shown only after the manifest loads; manifest failure, 401/403, missing `epub_download_url` or EPUB render error only `console.error` + hide the loader, leaving an empty page with no message and no retry (React layer's `ReaderUnavailable` is not reached).
4. **Bookmark button goes dead after a reader re-boot without remounting**: `_attachNavBookmarkButton` marks the DOM node `_bookmarkHandlerAttached` (highlight-methods.js:1226) and closes over the first instance's `sessionId`; a later instance (e.g. toast identity change re-running `useReaderBoot`'s effect, or manifest change) never rebinds, and the old handler fails `isSessionActive`.
5. **`sameSpan` de-duplication is wrong for repeated text**: identical trimmed text in the same chapter is treated as the same highlight, so highlighting a repeated phrase elsewhere only recolours the first one (885-896).
6. **Quote decoration mutates the book DOM** (`extractContents`/`insertNode`, 308-331): can break later CFI resolution/text offsets and persists only until iframe re-render; quote highlights for ranges crossing elements lose the italics/marks.
7. **Teardown leaks**: toolbar `<div>` and its document-level `mousedown` dismissal listener (511-518), annotation-menu listeners, and highlight state are never removed in `destroy()` (M/startup:190-222 only handles generic controllers); `this.highlights`/`bookmarks` survive across books within the instance (seed only clears highlights).
8. **State drift between React and legacy code**: theme index mapping duplicated in `ReaderViewport.jsx` (READER_BG_BY_INDEX), `useReaderBoot.js` (0/2 constants) and `reader-settings.js`; app-theme changes overwrite a user's sepia choice; `useReaderBoot` effect depends on `toast` (re-boots if identity changes) with an eslint-disable.
9. **Dead code in React mode**: shortcuts modal + `#open-shortcuts`, file picker (`#open-new-book/#open-epub`), landing page, `syncChapterLabel`, `renderToc` flat renderer, `landing-screen.css`, `boot-reader.js`, `pwa.js`. The file picker and landing page were the original product (a local EPUB reader).
10. **Duplication**: 52-line import header + `TOC_*`/delay constants + `readCookie` copy-pasted into 8 mixin files and `reader-application.js` (most imports unused; `readCookie` defined 5x); POST/PATCH/DELETE fetch boilerplate repeated ~6x in highlight-methods; gesture/theme logic duplicated across the two copies; `normalizeHrefForComparison`/suffix matching reimplemented in `syncSectionWithHref`, `updateChapterBar`, `syncChapterLabel`, `syncSelectedTocItem`.
11. **Fragile href matching** (`endsWith` in both directions) can select the wrong TOC/spine item when filenames share suffixes (e.g. `1.xhtml` vs `11.xhtml`).
12. **Heavy theme enforcement**: forces `color !important` + inline style on every element in the book and watches mutations; overrides publisher styling (including intentional coloured text); repaint timers at 60/220/600 ms; blanket `margin:0 !important` on html/body/top-level wrappers.
13. **Back-end coupling from JS**: reader code imports `../../../../api/urls.js` and `features/reader/manifest.js` (embedded module depends on app code); hard-coded endpoint shapes (`/access/books/{slug}/reader-launch/`, `{highlights_url}/{id}/`) and CSRF cookie name `csrftoken` (Django).
14. **A11y/UX gaps**: annotation features unreachable by keyboard; `window.alert` for errors; `user-scalable=no` after fullscreen exit; Ctrl/Cmd +/- hijacks browser zoom; Escape does not leave immersive mode; note modal lacks dialog semantics; emoji labels (💬 ❝ ⧉ 🔖 ✏️ 🗑) as button text.
15. **Standalone SW risks**: cache-first for any same-origin non-code GET, including `.epub` downloads and JSON, with no auth/Vary handling and no size cap; precache list tied to the monolith file set; `skipWaiting`+`clients.claim` always. Public `README` claims "No External Dependencies" while bundling epub.js/JSZip.
16. **Location indicator is not a page number**: "i / N" is the TOC entry index; Bengali numerals are special-cased.
17. Misc: `bindDoubleTapToggle` swallows `click` default (`preventDefault`) on the whole viewer including links outside the iframe's interactive filter; `annotation menu` anchor selector omits `g.epubjs-quote`; `showToolbarFeedback("Color updated")` fires even when colour unchanged; `queueReadingStateSync` is cancelled at teardown (last position may be lost).
18. Vendored `epub.js` has a `selected` event and CFI APIs the app depends on; it is a build-time snapshot with no bundled license header for epub.js itself (upstream BSD-2-Clause) - verify before reuse.

### Vendored runtime (identified only)
- `static/js/vendor/epub-runtime/` (identical in both copies): webpack-style module table split into 8 `*.modules.js` files (27,360 lines total) plus `module-loader.js` (113) and `runtime-entry.js` (57). Entry module 32 exports the `ePub` factory with `VERSION = "0.3"` (core-utilities module 1) i.e. **epub.js 0.3.x** (exact patch not stated in code). Bundled third-party: JSZip 3.5.0 (MIT or GPLv3 dual), jQuery/Sizzle build 2020-05-04 (MIT), feross `buffer` (MIT) and `ieee754` (BSD-3), xmldom, pako, lie, setImmediate shims, es5-ext style polyfills, marks-pane (`Pane`, `Highlight`, `Underline`, `Mark`).
- API surface the own code calls: global `window.ePub(source, {requestCredentials})`; `book.renderTo("viewer", {flow:"scrolled-doc", width, height})`, `book.ready`, `book.loaded.navigation`, `book.navigation.toc`, `book.locations.generate()/percentageFromCfi()`, `book.spine.spineItems`, `book.section(i)`, `book.packaging.metadata.language`, `book.destroy()`; `rendition.display(hrefOrCfi)`, `.on("rendered"|"relocated"|"displayed"|"selected")`, `.currentLocation()` (start.cfi/href), `.themes.register/select/fontSize`, `.resize(w,h)`, `.getContents()`, `.destroy()`, `.manager`, `.hooks.content.register`, `.annotations.highlight/underline/remove`; `contents.cfiFromRange`, `.range(cfi)`, `.window`, `.document`, `.iframe`.

---

## 8. Unread files and why

- **Vendored epub runtime** (`src/embedded-reader/static/js/vendor/epub-runtime/**` and `public/epub-reader/static/js/vendor/epub-runtime/**`, 27,360 + 170 lines each): excluded by the task; only headers, module-loader, runtime-entry, version constant, license fragments and API call sites were inspected. Both trees are byte-identical (`diff -rq` empty).
- **PNG binaries** (`favicon.png`, `icon-192.png`, `icon-512.png` in each copy): binary images, `cmp`-identical between copies, not viewed.
- `iconfont.css` line 3 base64 woff2 glyph font: read as data, not decoded; glyph `::before` rules are disabled in the reader layout (`content:none !important`, reader-settings-and-viewer.css:212-218) in favour of inline SVG.
- Files outside my scope that the reader depends on and were NOT read: `pages/ReaderPage.jsx`, `components/PageLoader`, `api/client`, `api/urls.js`, `styles/app/reader-shell-and-request-controls.css` (base styles of `.reader-nav-extra*`, `.reader-header-icon`, `.reader-boot-overlay`, `.reader-page-fullscreen`), `dark-mode.css`, and the backend manifest/serializers.
- Items I could not verify: whether `ReaderViewport` is mounted before `useReaderBoot` runs (constructor queries the DOM); how highlights/bookmarks created here are listed/opened elsewhere (the reader only accepts `manifest`, no cfi deep-link param).
