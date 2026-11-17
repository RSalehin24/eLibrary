# Design system — Material Design 3 on Angular Material

Status: DRAFT

The visual language is **Google Material Design 3** implemented by **Angular Material + CDK** ([ADR-0014](../04-architecture/adr/0014-frontend-technology.md)). Product look comes from **tokens** (color roles, typography, shape, elevation, motion, state layers), never from per-component overrides (INV-WEB-006). Exact theming API names follow the installed Angular Material version's official guide — **verify in spike S-02**.

## Tokens (Material 3 vocabulary)

| Group | Tokens / decisions |
|---|---|
| Color | M3 roles: `primary`, `on-primary`, `primary-container`, `secondary…`, `tertiary…`, `error…`, `surface`, `surface-container-{lowest…highest}`, `on-surface`, `on-surface-variant`, `outline`, `outline-variant`, `inverse-*`; defined through Angular Material's theming API (`mat.theme(...)` emitting CSS variables from M3 tokens; color accepts a palette for primary and optionally tertiary; density 0 to −5 — described by secondary sources, official page unreadable, confirm in S-02). Custom palettes from a seed color need a palette generator (tool chosen in S-02; any generator package requires approval). No "theme-color" schematic was found, so it is not assumed |
| Themes | `light`, `dark` (M3 schemes) and **`sepia`** (custom scheme generated from a sepia seed, reader + site). Admin: light/dark |
| Typography | M3 type scale (display, headline, title, body, label × large/medium/small) mapped to fonts: `sans-bn` (UI), `serif-bn` (reading). Bengali line heights per [typography guide](bangla-typography.md) override the default ratios |
| Shape | M3 corner scale (none, extra-small … full); cards 12 px, dialogs 28 px, buttons full per M3 |
| Elevation | M3 levels 0–5; in dark themes use surface tint/containers rather than shadows |
| State layers | M3 hover/focus/pressed/dragged opacities, kept as tokens |
| Motion | M3 easing/duration tokens; `prefers-reduced-motion` → none |
| Density | M3 density scale: default 0 for public pages, −2/−3 for admin tables |
| Breakpoints | Window size classes (verified in Android's adaptive-layout docs; the m3.material.io page returned 404): compact < 600, medium 600–839, expanded 840–1199, large 1200–1599, extra-large ≥ 1600 (large and extra-large are Android additions beyond M3's core three) |
| Layout | M3 canonical layouts: list-detail (admin workspaces), supporting pane (book page, reader notes), feed (search results) |

Seed colors and the sepia scheme are chosen in the P4 prototype session and validated by the WCAG contrast check in CI (starting hex values previously listed are superseded by the generated schemes).

## Components → Angular Material

**Verified 2026-11-17** against the published package listing of `@angular/material` **21.2.6** (jsDelivr file list; the official docs site is client-rendered and was unreadable). The package contains these component folders: autocomplete, badge, bottom-sheet, button (including FAB and icon button), button-toggle, card, checkbox, chips, datepicker, dialog, divider, expansion, form-field, grid-list, icon, input, list, menu, paginator, progress-bar, progress-spinner, radio, select, sidenav, slide-toggle, slider, snack-bar, sort, stepper, table, tabs, timepicker, toolbar, tooltip, tree — with Material 3 style files (`_m3-*.scss`) for button, card, dialog, chips, badge and others. Whether every one of them is fully M3-styled is still checked by spike S-02.

| Need | Component | Status |
|---|---|---|
| Buttons | Button (filled/tonal/outlined/text), FAB, Icon button | in library |
| Segmented control | `button-toggle` (closest equivalent of the M3 segmented button) | in library, style to M3 tokens |
| Navigation | Toolbar (top app bar), Sidenav (drawer), Tabs, Menu | in library |
| **Navigation rail, navigation bar (bottom), search, side sheet, breadcrumb** | — | **not in the package → built in `shared/` from CDK + tokens** (specs in this folder before building) |
| Containment | Card, Dialog, Bottom sheet, Divider, List, Expansion panel | in library |
| Inputs | Form field + Input, Select, Autocomplete, Checkbox, Radio, Slide toggle, Slider, Datepicker, Timepicker, Chips | in library |
| Feedback | Snack bar, Progress bar/spinner, Badge, Tooltip | in library (job progress uses `aria-live` polite) |
| Data | Table, Paginator (wrap for keyset next/prev), Sort | in library |
| Product-specific (CDK + tokens in `shared/`) | Book cover card, Credit list, Facet filter bar, Diff view, Evidence view, Reader surface, Annotation popover | built; each documented with states, keyboard, a11y |

Missing components are built from CDK primitives and tokens in `shared/` and recorded here. A second UI library requires owner approval. Adaptive navigation by window class therefore needs our own rail/bar components (compact: bar; medium/expanded: rail or drawer).

## Patterns

- **List page**: top app bar + search/filter chips + feed/table + keyset pagination + empty/error states.
- **Detail page**: summary header + tabs or supporting pane; destructive actions in an overflow menu with confirm dialog naming the object.
- **Workspace (admin)**: M3 list-detail layout, sticky bulk-action bar.
- **Form**: M3 text fields (label, supporting text, error text linked with `aria-describedby`); validate on blur and submit.
- **Review item**: evidence pane (highlighted source blocks) + decision pane; keyboard shortcuts.

## Governance

New component or token → entry here with states and an a11y check. Global/page CSS limited to layout using tokens. Angular Material upgrades are deliberate (one major at a time) with visual-regression approval.
