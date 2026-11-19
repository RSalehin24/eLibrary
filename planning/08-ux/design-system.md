# Design system - Material Design 3 on Angular Material

Status: DRAFT

The visual language is Google Material Design 3 (D-16) implemented with Angular Material and CDK ([ADR-0014](../04-architecture/adr/0014-frontend-technology.md)). Product look comes from tokens, never from per-component overrides. Exact theming API names follow the installed Angular Material version's official guide (verify in spike S-02). Changed from v1: four window classes (no extra-large), minimalist rules, dual-theme mechanics, legacy defects named.

## Tokens

| Group | Decision |
|---|---|
| Colour | M3 roles (`primary`, `on-primary`, `primary-container`, `secondary`, `tertiary`, `error`, `surface`, `surface-container-*`, `on-surface`, `on-surface-variant`, `outline`, `outline-variant`, `inverse-*`) plus extended `success` and `warning` roles (M3 has none). One seed hue (calm deep green proposed, final value at the prototype session); neutral surfaces carry the page; `primary` is used sparingly (one filled button per view, active nav item, focus). Generated schemes, never hand-edited hex |
| Themes | `light` and `dark` (M3 schemes, both first-class on every screen) and `sepia` (reader only, [reader screen](screens/reader.md)). One definition per theme; components read tokens only (REQ-WEB-007) |
| Typography | M3 type scale mapped to `sans-bn` (UI) and `serif-bn` (reading); Bengali line heights from the [typography guide](bangla-typography.md) |
| Shape | M3 corner scale: small 8, medium 12, large 16, extra-large 28 (dialogs, sheets), full (chips, switches) |
| Elevation | level 0 for content (tonal or outlined surfaces), 2 for menus, 3 for dialogs and sheets; dark themes use tonal surface containers, not shadows |
| State layers | M3 hover 8%, focus 10%, pressed 10%, drag 16%, disabled 38% content and 12% container |
| Motion | M3 standard easing, 100/200/300 ms; no entrance animations; `prefers-reduced-motion` shortens everything to near zero |
| Z layers | five named layers (sticky, drawer, dialog, snackbar, tooltip) in one token file |
| Density | 0 on reader-facing screens; -2 on operator and admin tables |

## Themes: mechanics (REQ-WEB-007, 008)

- Default follows `prefers-color-scheme`. A persisted choice System / Light / Dark overrides; "System" always resolves to a concrete value.
- The choice is stored in a cookie (so SSR can emit the right class) and mirrored in local storage; a tiny inline script in the document head sets the class before first paint from the cookie, falling back to `matchMedia`. No flash, no hard-coded `data-theme` on `<html>`.
- `color-scheme: light dark` is set so native controls and scrollbars follow.
- No per-component dark override, no second stylesheet. Contrast (4.5:1 text, 3:1 UI and focus) is checked on every token pair, both themes, in CI.
- Reader themes: light, dark, sepia. The reader follows the app by default and a user choice is stored per user in the reader service (D-48). Annotation colours are five tokens with light and dark tints.

## Window classes and adaptive layout (D-25, REQ-WEB-009)

Four classes from the CDK `BreakpointObserver` into one `WindowClass` signal; components never read `window.innerWidth`. SSR renders compact and hydrates without layout shift.

| Aspect | compact (< 600) | medium (600-839) | expanded (840-1199) | large (>= 1200) |
|---|---|---|---|---|
| Navigation | bottom bar (4-5) + top app bar | rail | rail | permanent drawer |
| Margins / columns | 16 px / 4 | 24 px / 8 | 24 px / 12 | 24+ px / 12, max content width |
| Book grid | 2 columns | 3-4 | 4-6 | 5-8 |
| Library filters | modal bottom sheet | side sheet | side panel | persistent side panel |
| Book detail | one column, sticky bottom action bar | one column, cover beside summary | list-detail style, actions in a pane | same, wider measure |
| Reader | full-bleed, chrome auto-hides, notes in bottom sheet | full-bleed, notes side sheet | centered measure, notes supporting pane | same |
| Operator and admin tables | become lists, detail as a separate screen | compact table, detail as a sheet | dense table with detail drawer | same |
| Dialogs | full-screen for forms | centered | centered | centered |

Rules: touch targets at least 48 px with spacing; no hover-only affordance; right `inputmode` and `autocomplete`; safe-area insets; text reflows at 200% zoom; orientation change keeps position, scroll and form state; images carry intrinsic sizes (layout shift budget CLS < 0.05); layout is never chosen by user-agent sniffing. Checked at 360, 768, 1280 and 1920 px in light and dark, `bn` and `en`.

## Components

Angular Material and CDK provide: buttons (filled, tonal, outlined, text), FAB, icon button, button toggle (segmented control), toolbar (top app bar), sidenav (drawer), tabs, menu, card, dialog, bottom sheet, divider, list, expansion, form field, input, select, autocomplete, checkbox, radio, slide toggle, slider, chips, snack bar, progress bar and spinner, badge, tooltip, table, paginator, sort, stepper, datepicker. The v1 package check (`@angular/material` 21.2.6) is carried over; whether each is fully M3-styled is checked by spike S-02.

Built in `shared/` from CDK primitives and tokens, each documented here with states, keyboard and a11y before use: **navigation bar** (bottom), **navigation rail**, **side sheet**, **search field**, **book cover card**, **status chip set** (queued, running, succeeded, failed, cancelled, needs review, pending resolution), **data table with list collapse**, **confirm dialog** (one, configurable label and tone), **reader surface**, **annotation popover and bottom sheet**, **diff view**, **evidence view**. A second UI library needs owner approval (REQ-WEB-005).

## Patterns

- **List screen**: top app bar, search and filter chips, feed or table, keyset "load more", empty and error states.
- **Detail screen**: summary header, tabs; destructive actions in an overflow menu with a confirm dialog naming the object.
- **Workspace (operator)**: bucket rail, one table component, one live stream, per-item results in a snackbar.
- **Form**: M3 text fields (label, supporting text, error text linked by `aria-describedby`); validate on blur and submit; focus first error; form state survives reconnect and rotation.
- **Feedback**: snackbar for results (queue, grouped), dialog for confirmation, inline banner for persistent conditions (credential expired). Never `window.alert` or `window.confirm`.
- **Status**: tonal chip with text; colour never the only signal.
- **Icons**: Material Symbols only; no emoji in labels.

## Legacy CSS defects not carried over

Dark-mode override sheet and attribute-only dark rules; ten breakpoints; hard-coded colours and `!important`; glass blur, gradients, ornamental blobs, entrance and hover-lift animation, uppercase tracked labels; duplicated near-identical toggle and tab variants; floating theme button; file splitting by line cap. Details in [principles](principles.md).

## Governance

A new component or token gets an entry here with states and an a11y check. Global CSS is limited to layout using tokens. Angular Material upgrades are deliberate, one major at a time, with visual regression approval.
