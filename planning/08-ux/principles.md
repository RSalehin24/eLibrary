# UX principles

Status: DRAFT

Review checklist for every screen. Basis: D-02, D-16, D-25, D-26, D-34, D-39 and [REQ-WEB](../02-requirements/web-ui.md). Changed from v1: minimalist and dual-theme are explicit; admin ingestion is one Import workspace; public pages are metadata only; the 401/403 split is a principle; the legacy defects below are named so they are not copied.

1. **Reading first.** The product is books. Library and detail lead with cover, title, author; chrome recedes. The reader is the best screen in the app.
2. **Minimalist (D-26, REQ-WEB-006).** Restrained colour (one seed hue on neutral tonal surfaces), generous whitespace, flat surfaces, elevation only for overlays, error colour only for failure or destruction, no gradients, glass blur, decorative illustration or entrance animation, no emoji labels. If an element does not help the one next step, remove it.
3. **One obvious next step.** Every screen has one primary action (filled button, at most one per view). Visitor: *Sign in to read*. Reader: *Continue reading* or *Read*. Operator: the next item in the queue.
4. **Light and dark are equal (D-26, REQ-WEB-007).** Every screen, dialog, sheet and the reader is designed and tested in both. Default follows the OS; a persisted choice (System, Light, Dark) overrides. Never a per-screen colour override.
5. **Show state, never mystery (REQ-WEB-001).** Loading, empty, ready, error, forbidden, not found, offline are designed on every screen ([states](screens/states.md)). Errors say what happened and what to do, in the reader's language.
6. **401 and 403 are different (REQ-WEB-002).** Not signed in: go to sign-in and come back to the same place. Signed in but not allowed: say so inline with the reason; the session stays. Never a fake "application restarted".
7. **Public is metadata only (D-34, REQ-WEB-022).** Anonymous visitors see browse, search, covers, summaries. Preview text and reading need sign-in. Public pages are server-rendered.
8. **Fewer places, deeper places.** Seven destinations at most (Library, Notes, Import, Manage, Users, Settings; Sign-in for visitors). Import is one workspace with a bucket rail, not many pages. No duplicate list pages: one Library, one table component, one confirm dialog.
9. **Navigation shows only what the scopes allow (REQ-WEB-003).** Items come from the server capability set; the URL guard agrees; the server stays the authority.
10. **Explain refusals.** A denied action names the reason in plain words and the way forward (sign in, ask an administrator). Disabled controls carry a reason a screen reader can read.
11. **Bengali is first-class (REQ-WEB-011/012).** Typography, digits, line height and conjunct rendering follow the [typography guide](bangla-typography.md); layouts are tested with Bengali text lengths; no string is hard-coded.
12. **One product, three form factors (D-25).** Compact, medium and expanded/large are designed together, not shrunk from desktop: bottom bar, rail, drawer; tables become lists on compact; touch-first and keyboard-complete.
13. **Reversible and safe.** Destructive actions use one Material confirm dialog naming the object, or undo. Batch commands report a per-item result.
14. **Honest limits.** Reading serves the whole book to the browser (D-28), so the book page and reader say plainly that a reader can copy it; access is controlled by entitlement and audit, not DRM (REQ-RDR-010).
15. **Accessible by default (REQ-WEB-008/010).** WCAG 2.2 AA in both themes; see [accessibility](accessibility.md).
16. **No analytics.** The UI sends no usage analytics, trackers or third-party scripts. Every screen spec states "Analytics: none".

## Legacy defects this design must not repeat

| Legacy defect (source) | Rule here |
|---|---|
| 1.8k-line dark-mode override sheet, hard-coded `data-theme="dark"`, System theme broken (X1-091, features/19) | One M3 token set per theme, no overrides; theme applied before first paint |
| Ten breakpoints, rules scattered by breakpoint (features/19 S2) | Four window classes, rules by component |
| Hard-coded colours and `!important` (features/19 S13/S14) | Tokens only; a lint fails on a literal colour |
| Four contributor pages and parallel Home/Library/My Books/Kindle lists (D5 merge list) | One Library, one facet tab bar |
| Ten processing pages, 6 s health poll, forced reload, "application restarted" toast (X1-078/090/096) | One Import workspace, one live stream, typed errors |
| `window.alert` and `window.confirm`, emoji icons, floating theme button | Material dialog and snackbar, Material icons, theme in Settings and top bar |
| Silent blank reader on failure, token in the URL (X1-003/093) | Designed reader error states, ticket only in memory |
| Demo login page | Dropped (D-35) |

## Acceptance process

- Each screen has purpose, primary action, states and a row in the [route map](route-map.md); a screen without these is not built.
- Owner signs off clickable prototypes (Library, Book detail, Reader, Sign-in) before service depth is built.
- Visual regression snapshots (light, dark, reader sepia, `bn` and `en`, 360, 768, 1280 px) are approved once, then guard drift.
