# EPUB Reader ![Version](https://img.shields.io/badge/version-v1.1-blue)

## Version

Current release: **v1.1**

### What's New in v1.1

- Added PWA support so the reader can be installed from Chrome as a standalone app.
- Added a web app manifest and app icons for installability.
- Added service worker registration and offline app-shell caching.

A modern, minimalist web-based EPUB reader. Open and read EPUB files directly in your browser with a clean, responsive interface and multiple reading features.

## Features

- **Open EPUB Files**: Select and load EPUB books from your device for instant reading.
- **Table of Contents Navigation**: Browse and jump to chapters using a sidebar TOC.
- **Page Navigation**: Use arrow buttons, keyboard arrows, or swipe gestures (on touch devices) to move between pages/sections.
- **Font Size Adjustment**: Easily increase or decrease the text size for comfortable reading, including pinch-to-zoom on touch devices.
- **Theme Switching**: Choose between White, Sepia, and Night reading modes. Cycle themes with two-finger tap gesture.
- **Immersive Fullscreen Mode**: Double-tap/click to toggle a distraction-free fullscreen reading experience. Keyboard shortcut (F) supported.
- **Improved Touch & Keyboard Support**: Enhanced gestures for navigation, theme switching, and fullscreen toggle. Keyboard shortcuts for theme and font size adjustments.
- **Responsive Design**: Optimized for both desktop and mobile devices.
- **Custom Styles**: Enhanced appearance with custom CSS for a pleasant reading experience.
- **Image Support**: Displays images embedded in EPUB files.
- **Fast Loading**: Loader animation for smooth transitions between chapters and actions.
- **No External Dependencies**: Works fully offline after loading.
- **Installable App (PWA)**: Can be installed from Chrome as a standalone app window.

## Project Structure

- `index.html` — Main entry point for the EPUB reader web app.
- `static/` — All static assets grouped by type:
  - `static/css/base/` — Global base styles (`reset.css`, `iconfont.css`, `helpers.css`).
  - `static/css/components/` — UI component styles (`landing-screen.css`, `shortcuts-dialog.css`, `reader-layout.css`).
  - `static/css/themes/` — Theme tokens and theme overrides (`theme-tokens.css`, `theme-overrides.css`).
  - `static/js/app/` — App startup scripts (`boot-reader.js`, `pwa.js`).
  - `static/js/reader/` — Reader modules by responsibility:
    - `reader-application.js` — App orchestration and lifecycle.
    - `controllers/` — Focused controllers (theme, loading, shortcuts, iframe bridge, settings panel).
    - `utils/` — Shared DOM, TOC, and gesture helpers.
    - `reader-settings.js` — Constants/selectors/theme defaults.
  - `static/js/vendor/epub-runtime/` — EPUB engine loader (`runtime-entry.js`, `module-loader.js`) and responsibility-based runtime module groups.
  - `static/img/` — Image assets (logo, favicon, app icons).
- `CNAME` — Custom domain config (for GitHub Pages or similar hosting).

## Usage

1. Serve the project from a local/static web server and open `index.html` in your browser.
2. Click "Open EPUB book" and select an EPUB file from your device.
3. Use the sidebar to navigate chapters, the top bar for settings, and the main area to read.
4. Adjust font size, switch themes, or enter fullscreen for immersive reading.
5. In Chrome, use the install icon in the address bar (or menu > "Install app") to install it.

### Backend launch manifest mode

The reader also supports a backend-issued launch contract:

- `/?manifest=<absolute manifest url>`

When that query parameter is present, the reader fetches the manifest, opens the protected EPUB automatically, and syncs reading progress back through the backend-provided `reading_session_url`.

## Testing

Run the local contract tests (no external dependencies):

```bash
node --test tests/*.test.mjs
```

Optional JavaScript syntax validation:

```bash
for file in $(rg --files -g '*.js' .); do node --check "$file"; done
```

Optional browser smoke tests (requires Playwright installed with browsers):

```bash
node --test tests/playwright-smoke.test.mjs
```

## Deployment

This project is static and can be hosted on any web server or GitHub Pages. The `CNAME` file is for custom domain support.
For installability, serve it over HTTPS (or `http://localhost` during development).


