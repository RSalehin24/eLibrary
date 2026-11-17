# Design system

Status: DRAFT

Tokens first; components only use tokens (INV-WEB-006). Values are starting points: the contrast checker in CI (WCAG AA) is the authority.

## Tokens

| Group | Tokens |
|---|---|
| Color roles | `bg`, `bg-subtle`, `surface`, `surface-raised`, `border`, `text`, `text-muted`, `accent`, `accent-contrast`, `danger`, `warning`, `success`, `focus`, `highlight-{yellow,green,blue,pink}` |
| Themes | `light`, `dark`, `sepia` (reader and site). Admin supports light/dark. |
| Type | families `serif-bn` (reading), `sans-bn` (UI), `mono`; scale 12/14/16/18/20/24/30/38/48; line-height 1.4 UI, **1.7–1.9 Bengali reading** |
| Space | 4-px scale: 0,4,8,12,16,24,32,48,64 |
| Radius | 4, 8, 16 |
| Elevation | 0, 1, 2 (borders preferred over shadows in dark) |
| Motion | 120/200/320 ms; `prefers-reduced-motion` → 0 |
| Breakpoints | 360, 600, 900, 1280, 1600 |
| Layout | content max 72ch for text, 1200 px page, 16 px gutter at 360 |

Starting palette (validated in CI): light — bg `#FBFAF7`, text `#1B1B1A`, muted `#5B5A56`, accent `#1F5FBF`; dark — bg `#121212`, text `#E8E6E1`, muted `#A8A59E`, accent `#7FA8F0`; sepia — bg `#F3E9D6`, text `#3B2F20`, muted `#6B5A44`, accent `#8A4B14`.

## Components (each: states, keyboard, a11y notes, bn/en length test)

Button (primary/secondary/ghost/danger, loading), Link, IconButton, Input, TextArea, Select, Combobox (async), TagInput, Checkbox/Radio/Switch, Tabs, SegmentedControl, Pagination (keyset: Next/Prev), Table (sticky header, sortable, selectable, density), Card (book), Cover (with intrinsic ratio), Badge/StatusPill, Toast, Dialog (focus trap), Drawer, Popover/Menu, Tooltip, Breadcrumb, EmptyState, ErrorState, Skeleton, FilterBar (facets as chips), Stepper, DiffView (tree + text), EvidenceView (blocks highlighted), ThemeSwitch, LanguageSwitch.

## Patterns

- **List page**: header (title + count + primary action), filter bar, results (cards or table), pagination, empty/error states.
- **Detail page**: summary header + tabs; destructive actions in a "More" menu.
- **Workspace (admin)**: left list, right detail, sticky bulk-action bar.
- **Form**: label above, helper text, error text tied with `aria-describedby`, submit disabled only while submitting; validation on blur and submit.
- **Review item**: Evidence (source blocks highlighted) on the left, decision controls on the right, keyboard shortcuts for common choices.

## Governance

New component or token requires an entry here with states and an a11y check. Page-specific CSS is forbidden except layout using tokens.
