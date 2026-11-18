# EPUB Reader Feature & Behavior Baseline

Last updated: 2026-02-24

This document defines the current expected behavior of the application. Future changes should preserve this baseline unless intentionally changed.

## 1. App Flow
- Landing page is shown first.
- Selecting an `.epub` file opens reader view and hides landing view.
- Closing book clears reader state and returns to landing view.

## 2. Rendering
- EPUB renders inside `#viewer` using epub.js runtime with `flow: scrolled-doc`.
- TOC is generated from EPUB navigation.
- Clicking TOC item navigates to the related section.
- Internal book links are intercepted and routed through reader navigation.

## 3. Reader Controls
- Previous/Next buttons navigate sections.
- TOC button toggles TOC panel open/close.
- Settings button toggles reading settings panel.
- Close button exits current book session.

## 4. Theme & Typography
- Themes: White, Sepia, Night.
- Font size range: 14px to 30px (step 2px).
- Theme index and font size persist in localStorage.
- Theme text color is enforced across text elements in iframe content (including inline-colored text).
- Top-level wrapper margins inside iframe content (`body > div/main/section/article`) are reset to 0.

## 5. Keyboard Behavior
- `ArrowLeft` / `ArrowRight`: previous/next section.
- `F`: toggle immersive/fullscreen mode.
- `Esc`: close shortcuts modal and settings panel.
- `Ctrl/Cmd + 1/2/3`: switch theme.
- `Ctrl/Cmd + + / -`: increase/decrease font size.
- Shortcuts are ignored when focus is in editable controls.

## 6. Touch & Gesture Behavior
- Swipe left/right: next/previous section.
- Two-finger pinch: font size adjustment.
- Two-finger tap: cycle theme.
- Double tap/click on non-interactive area: toggle immersive mode.

## 7. Responsive Behavior
- Reader and TOC are side by side across breakpoints.
- Small-screen TOC-open compact mode keeps only primary TOC control visible on reader rail.
- In compact TOC-open mode, reader main area is visually hidden and non-clickable.
- Prev/Next arrows are hidden on small widths.

## 8. Immersive/Fullscreen Behavior
- Immersive mode hides TOC and nav arrows.
- Safe-area-aware padding is applied in immersive mode.
- Viewport resize is stabilized with staged timers.
- Loader appears during transitions and is hidden after resize/content readiness callbacks.

## 9. Scroll Ownership (Critical)
- Browser page itself must not scroll (both landing screen and reader screen).
- Root `html/body` are locked against page-level scrolling.
- Only internal containers may scroll:
  - Landing content container
  - TOC panel
  - EPUB iframe content
- Reader iframe uses `body` as primary scroll host.
- Inner container scroll fallback is used only when iframe `body` cannot scroll.

## 10. Accessibility & Semantics
- Skip link to reader controls is present.
- Reader controls include ARIA labels and relationships.
- Settings panel updates `aria-expanded` / `aria-hidden` states.
- Theme buttons update `aria-pressed`.
- Font size controls update disabled state.
- Shortcuts modal traps focus and restores focus on close.

## 11. PWA & Offline
- Service worker registration is enabled.
- App shell assets are cached.
- Cache matching for query-stringed requests is strict to reduce stale mismatch.

## 12. Runtime Policy Compliance
- Runtime teardown listeners use `pagehide` in key runtime managers (instead of `unload`) to avoid permission-policy warnings.

## 13. Validation Baseline
- `node --test tests/*.test.mjs` should pass.
- Existing suite includes accessibility, responsive contracts, interaction/runtime contracts, and optional Playwright smoke tests.
