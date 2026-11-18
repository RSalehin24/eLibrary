Status: DRAFT

# 19. Legacy CSS / design system (archive/app/frontend/src/styles)

Paths relative to `archive/app/frontend/src/styles/`. 56 files, 12,901 lines, all read in full. Plain CSS (no preprocessor, no CSS modules, no utility framework). Class-name BEM-ish with page prefixes. Target for the rebuild: minimalist, light and dark, Angular Material M3. This document records what existed, what is worth keeping as an idea, and what is a problem.

## A. Architecture of the stylesheet

- S1. Entry `app.css` (32 lines) is 32 hand-ordered `@import`s (app.css:1-32). Cascade order is load-bearing: `dark-mode.css` imported 31st, then `reprocessing-page.css` after it, so the reprocessing page is not covered by the dark overrides (it does not need them, see S29). Six barrel files (2-5 lines each: `access-users-and-processing-layout.css`, `processing-automation-and-tables.css`, `processing-skeletons.css`, `page-loaders-and-states.css`, `mobile-responsive-layout.css`, `tablet-responsive-layout.css`) only re-import subfolders. Reason: the 300-line file cap (16b U40); `dark-mode.css` (1806), `notes-page.css` (891), `foundation-and-shell.css` (543) are grandfathered over the cap. Result: file names describe the cap-driven slicing (e.g. `book-metadata-and-hero`, `narrow-phone-and-count-fixes`) not features, so finding a rule needs a search.
- S2. Responsive rules are not co-located with components. They live in 3 layers (`desktop-responsive-layout.css` max-width 980, `tablet-responsive-layout/*` 1200/980/768, `mobile-responsive-layout/*` + `table-responsive-columns.css` 640/420) plus ad hoc `@media` blocks inside component files (my-books-actions 1024/640, catalog-toolbar-primary 768, notes-page 640/768, catalog-property-controls 1100, book-metadata 720, page-loader-profile 900/640, reprocessing 1020/980/640). A single component's behaviour is spread over 4-6 files. A rule can be overridden by a later file at a different width (S27).
- S3. `reserved-layout-overrides.css` is misnamed: it only holds 7 `@keyframes` (`skeleton-shimmer`, `spinner-rotate`, `surface-enter`, `toast-in`, `otp-enter`, `spotlight-enter`, `filter-sheet-enter`). `catalog-toolbar-primary.css` defines a further `@keyframes slideDown` (L261). `scroll-top-in` is in foundation (L528).

## B. Design tokens (what existed)

- S4. Colour tokens (foundation-and-shell.css:1-129): `--bg` (two radial gradients over a linear gradient), `--surface` (rgba white .72), `--surface-strong` (.9), `--surface-muted`, `--ink` #17392f, `--ink-soft` #325347, `--muted` #5a6f68, `--line` rgba(17,70,54,.2), `--line-strong` (.32), `--accent` #0f4b38, `--accent-strong` #0b3d2e, `--accent-soft` rgba(17,70,54,.08), `--success` #245042, `--warning` #7c6325, `--danger` #8a3434, `--shadow`, `--shadow-soft`. Dark: `--ink` #e6f1ea, `--muted` #8aa39a, `--accent` #5fc79b, `--accent-strong` #7fd5ad, `--success` #6fd2a4, `--warning` #e4c071, `--danger` #f08c8c; bg gradient #0e1a16 -> #142621. Palette is a monochrome forest-green family; success/accent are nearly the same hue so "success" and "brand" are indistinguishable (`.status-ready` uses success, `.status-requeued` uses accent).
- S5. Shape/motion/z tokens: radii `--radius-lg` 22, `-md` 16, `-sm` 12; durations 120/180/320 ms; z `--z-topbar` 12, `--z-dropdown` 30, `--z-dialog` 60, `--z-toast` 80 (foundation L27-36). Token use is partial: real z-index values used instead are 5, 6, 9, 10, 20, 24, 25, 30 (dialog), 40 (toast viewport), 1000 (floating actions, select dropdown, note modal, backend overlay), 99999 (reader toolbar) (reader-shell L141, foundation L483, toasts, auth-controls L77). Token `--z-dialog 60` and `--z-toast 80` are never used by the actual dialog (30) / toast viewport (40).
- S6. Undefined or implicit tokens referenced: `--ink-strong`, `--ink-muted`, `--shadow-md` (foundation L398-424 with fallbacks), `--ink-muted` (notes-page L753, no fallback so colour invalid), `--bg-hover` (manual-books L243, L294: undefined, rule has no effect), `--surface-hover` (with fallback). `background: var(--bg)` is used on inputs (manual-books L285, L343, L359) where `--bg` is a gradient; works but is semantically wrong.
- S7. Typography: one font stack `"Avenir Next","Noto Sans Bengali","Hind Siliguri","Kalpurush","Trebuchet MS","Gill Sans",sans-serif` (foundation L37-39). Latin face first means Bengali glyphs come from fallbacks and depend on installed fonts (no `@font-face`, no web font loaded in this tree). Serif for book covers `"Iowan Old Style","Georgia","Noto Serif Bengali"` (book-card-and-detail-grids L219). Mono `SFMono-Regular, Menlo` (page-loader L3, requeue). Wordmark: cursive `"Chalkboard SE","Chalkduster","Marker Felt",...` italic with glow (foundation L282-354). Sizes: base 16 px, scale in rem (0.56-2.6) AND px (notes-page uses 10/11/12/13/14/16 px, the only file using px); h1 `clamp(1.2rem,1.7vw,1.5rem)` / catalog `clamp(1.4rem,2.2vw,2rem)` / hero `clamp(1.75rem,3vw,2.6rem)`. Tiny uppercase micro-labels with wide tracking everywhere (`.fact-label`, `.eyebrow`, table headers, role pills: 0.56-0.8rem, letter-spacing 0.06-0.16em, weight 700-800). Problems for this product: Bengali has no case (uppercase no-op) and positive letter-spacing breaks conjunct forms (juktakkhor), and 9-11 px text is below readable size.
- S8. Spacing: no scale token. Observed values: gaps 4, 6, 8, 10, 12, 14, 16, 18, 20, 24; paddings 10-24; page shell padding 20 (14 at <=980, 12 at <=768, 10 at <=640, 8 at <=420). Content max width 1180 px (`.page-shell`, `.landing-shell`), profile 760 px, dialog 520, toast 400, backend modal 480.
- S9. Elevation recipe: `--shadow` `0 18px 42px rgba(14,52,39,.12)` and ~40 distinct ad hoc shadows (e.g. `0 10px 18px rgba(12,47,36,.09)`, `inset 0 1px 0 rgba(255,255,255,.38)`). Large radii (12-24 px, pills 999px). Glass: `backdrop-filter: blur(8-18px)` on topbar, cards, tables, dropdowns, sticky headers (foundation L244, profile-menu L19/231, catalog-tables L9, notes-page L14, access-settings L181, mobile nav L120), with an `@supports not` fallback only for `.topbar` (foundation L390). Gradients on almost every control: `linear-gradient(180deg, #135b45 0%, #0b3d2e 100%)` for primary/active, `linear-gradient(180deg, #d84a4a, #a83232)` for danger.
- S10. Decorative layers: two fixed blurred colour blobs `.shell-ornament-*` (foundation L193-213, 360 px, blur 80, opacity .18), entrance animation `surface-enter` (translateY 12 px, 320 ms) on topbar, cards, states (L215-227), `spotlight-enter` (blur+scale) on the catalog toolbar, `filter-sheet-enter` on the filter drawer, skeleton shimmer 1.45 s, hover lift `translateY(-1px)` on buttons/cards and `-4px` on book cards (book-card L45), cover hover scale 1.01.

## C. Dark / light mode handling

- S11. Mechanism: `<html data-theme="light|dark">` optional attribute plus `color-scheme: light dark`. Tokens defined 4 times (light default, `@media (prefers-color-scheme: dark) :root:not([data-theme="light"])`, `[data-theme="light"]`, `[data-theme="dark"]`); light block copied verbatim twice, dark block copied twice (foundation L1-129; ~100 duplicated lines). A theme toggle exists (`.theme-toggle`, `.theme-toggle-floating` 44 px fixed bottom-right, foundation L438-496) and a toggle in the profile menu.
- S12. Defect (high): all component-level dark overrides in `dark-mode.css` (1806 lines, ~330 selector groups) are scoped to `[data-theme="dark"]` only, not to the OS media query. With OS dark and no explicit `data-theme`, tokens turn dark but every hard-coded white/pale-green component (buttons, cards, tables, toolbar, dialogs, nav panels, toasts) stays light, giving unreadable light-on-light/dark-on-dark mixes. Only `.admin-tab-card` was given the media-query variant (access-settings-fields L251-287). Unless the app always writes `data-theme` at boot, this is a live bug; cannot verify from CSS alone.
- S13. Root cause: components hard-code light colours (rgba whites, `#135b45`, `#fffffff5`, `#0c2f2414`, `#f4f9f6f0`) instead of tokens, so each component needs a shadow rule in dark-mode.css; many dark rules also re-specify shadows/gradients. About 55% of the 1806 lines duplicate component structure. Some pages (reprocessing-page.css, notes-page.css mostly, nothing else) used tokens only and need no overrides (reprocessing-page.css:1-5 states this explicitly).
- S14. Specificity wars: dark rules need tricks such as repeating the full attribute chain (`input:not([type=checkbox]):not([type=radio]):not([type=range])`), and a comment documents that `.access-page .detail-facts select` (0,2,1) beats the global dark rule (dark-mode L466-467) and had to be re-overridden. `!important` appears in ~35 places (custom-select search input, reading-status buttons, `.catalog-page-header h1`, `.checkbox-row`, `.reader-nav-extra-btn`, tablet nav `.table-mobile-cards min-width`, `catalog-table-shell--incremental` column widths, hero no-cover).
- S15. Off-palette colours that do not follow either theme: mobile nav sub-links lime `#d0f0c0`/`#0f3d0f`/`#0f7a0f` (tablet navigation-drawer L207-217), multipage badge blue `#1d4ed8` and red (processing-automation L212-228), reading status amber/emerald (`#b45309`, `#f59e0b`, `#10b981`), star `#eab308`, underline highlight violet `#7c3aed`, paused blue `#1f5d8c`, pending amber `#8b5200`, manual pill amber `#8f5a17`, delete red `#c0392b`. No semantic token for "info" or "warning" fill.
- S16. Reader: `.reader-page-fullscreen`, `.reader-fullscreen-frame` forced white (reader-shell L129-136, desktop-responsive L22/L39); dark override sets `#0e1a16`. The embedded reader has its own theme token files (`.theme-type-1/-2`, see 16b U26) which are scoped to the host container so reader themes do not leak.
- Keep as idea: user choice of Light / Dark / System, persisted, with `color-scheme` set so native controls follow. Do not keep: attribute-only overrides, token duplication, dark shadow stylesheet.

## D. Layout patterns

- S17. App shell: `.shell` padding 20; sticky glass `.topbar` (`top:12px`, z 12, radius 18, `grid-template-columns: 1fr auto auto`, max 1180) with brand, `.topnav` (nav links with `nav-dropdown` panels), session box (theme toggle, profile avatar menu). Reader mode: `.shell-reader-mode` zero padding and a topbar with `margin: 0 92px 18px 20px` leaving room for a fixed floating hide button (`.reader-topbar-floating-hide`, positioned using `--reader-topbar-offset/height` custom properties and `env(safe-area-inset-*)`); app navigation hidden with `appNav=hidden` (16b U12).
- S18. Mobile navigation (<=980): topnav and session box hidden, hamburger `.mobile-nav-trigger` opens a fixed `.mobile-nav-panel` (inset 76px 12px auto, radius 22, blur 18, `max-height: calc(100dvh - 88px)`) with a backdrop (z 24/25), collapsible groups (`max-height 0 -> 320px`), body scroll lock class `app-mobile-nav-open`. 42 px trigger, 46-48 px links. Good ideas: dvh units, safe-area insets, scroll lock; bad: panel is display:none until the media query then display:block (no focus trap styles visible), group animation via max-height.
- S19. Page header patterns: (a) `catalog-page-header` grid `auto 1fr` title + toolbar; (b) `--property-layout` grid areas `"title toolbar" "controls controls"`, with 10+ variants for sticky, stacked, inline, bare; (c) `notes-page-header` sticky; (d) `admin-hero-card` sticky; sticky offsets are magic numbers `top: 86px` (80 at <=980, 78 for the toolbar wrap) coupled to the topbar height. The "phantom row" bug is patched by 3 separate comments/overrides (toasts-and-catalog-page L176-188, 283-296; catalog-property-controls L1-5; tablet 768 L322-348).
- S20. Grids: book cards `.book-grid` (auto-fit minmax(220px,1fr) at first, later forced to 2 columns by `repeat(2,1fr)` gap 20, 1 column at <=640; manual-books L216-219), book card itself a 2-col grid `156px | 1fr`, min-height 360, left 4 px gold-to-green accent bar, hover lift 4 px; detail hero `300px | 1fr`; facts grid 4 col; `.detail-facts` auto-fit 160; admin tabs 2-col; processing grids 2-col with fixed `--processing-list-card-height: 724px` lists; forms 2- and 4-col (`manual-book-form-grid` span-3/span-2).
- S21. Tables: `.catalog-table` fixed layout, min-width 980-1172, sticky `th`, fixed `colgroup` widths per column class (`book-table-col-*`), `.simple-table` min-width 720, `.processing-table` min-width 980-1140 with ~40 column-width classes (table-columns.css), `.property-table`. Below 768 px tables convert to stacked "cards" via `.table-mobile-cards` with `td[data-label]::before` (tablet records-processing L44-116), a good responsive pattern (labels from `data-label`). Below desktop widths others rely on horizontal scroll inside `overflow:auto` shells.
- S22. Components inventory (class families): buttons (`primary/ghost/danger/warning/icon/toolbar-icon/asset-link/candidate/nav-link`), pills/status (`status-pill` + `status-<state>` with 12 states: ready, succeeded, approved, pending, queued, processing, needs_review, ambiguous, pending_resolution, cancelled, stopped, requeued, failed, invalid, rejected; `table-type-pill-digital/manual`, `reprocess-badge--*`), chips (`tag-chip`, `saved-filter-chip`, `property-tag`, `access-permission-chip`), toggle switch (`profile-menu-toggle`, `processing-switch`: 60x30 pill with ON/OFF text inside, two near-duplicate implementations), tabs (`contributor-tab`, `admin-tab-card`, `manual-books-tab`, `notes-tab`), searchable select (`custom-select-*`), tag input with suggestion list (`tag-*`; behaviour in 16b U25), toast (`toast-*`, type success/error/info, viewport top-right 400 px, z 40), dialog (`dialog-card` 520 px radius 24, backdrop blur 8), TOTP QR card, password field with Show button, rating stars, progress slider, details/summary error disclosures, skeletons for every page, drop zone for cover (`manual-book-drop-zone`), tooltips (`book-card-tooltip`), scroll-to-top, backend-status overlay ("backend down" modal, table-responsive-columns L157-188), error boundary.

## E. Accessibility review

- Good: skip link (foundation L357-375); global `:focus-visible` outline (L182-185) with dark colour override (dark-mode L1093); `prefers-reduced-motion` handled twice (foundation L378-387 and mobile L147-155, the latter uses `animation: none !important` which also kills skeleton shimmer and spinners, conflicting with the former that keeps them near-zero duration); required-field marker with `:has` (foundation L428-436); `.sr-only`; `aria-selected` styled in notes tabs; `cursor` rules; 44 px minimum input/touch heights in forms; `env(safe-area-inset-*)`; focus ring on custom switches via sibling selector (profile-menu L144-147).
- Gaps: many controls below 44 px (reader header icons 30 px, notes icon buttons ~20 px with opacity .45, card action buttons 34-38 px, processing automation buttons 30 px, switch text .56rem); muted/placeholder colours e.g. `rgba(50,83,71,.68)` on pale glass and `opacity:.45` icon buttons likely fail 4.5:1; outline removed (`outline:none`) on search inputs and custom-select trigger with only a faint border change as replacement (catalog-toolbar-primary L189-191, catalog-property-controls L281-284); information conveyed by colour alone for status pills (but text is present); "danger" red used for non-destructive state (e.g. Kindle `is-sent` and "in my books" turn red, hover on "added" turns red: a toggled state shown with the destructive colour, see S28); uppercase and tracking (S7); text sizes in px with fixed rem mix; hover-only tooltips hidden below 640.
- Dialogs/modals: backdrop and card styled, but no styles for `:focus`-trap, `role` hints; note modal and dialog use different z values.

## F. Per-page style inventory (which file styles which screen)

| Screen / area | Main files (lines) |
|---|---|
| Global shell, topbar, brand, theme toggle, floating actions | foundation-and-shell (543), navigation-and-buttons (274), profile-menu-and-page-layout (282) |
| Mobile/tablet nav drawer | tablet-responsive-layout/navigation-drawer (253), base-and-reader-topbar (71) |
| Login / OTP / password reset / TOTP setup | page-loaders-and-states/auth-controls-and-dialogs (144), profile-reader-and-auth-loaders (171), profile-security-and-access-users (275, TOTP part) |
| Catalog (library, home, search/filter/sort toolbar, saved filters, pagination) | catalog-toolbar-primary (316), -secondary (258), catalog-property-controls (432), toasts-and-catalog-page (296), catalog-tables (340), book-card-and-detail-grids (247), manual-books-and-book-grid (442) |
| Book detail (hero, facts, source records, TOC, raw provenance, status notes, delete/refresh) | book-metadata-and-hero (252), book-source-and-toc-panels (273), book-card-and-detail-grids |
| My books / Kindle send / add-remove | my-books-actions (276) |
| Manual (physical) books list, composer form, tag inputs, reading log (status, stars, progress) | manual-books-and-book-grid (442), catalog-tables (340) |
| Notes / highlights (two-column list, tabs, colour dots, edit modal) | notes-page (891) |
| Reader shell (fullscreen frame, toolbar overlay, hide button) | reader-shell-and-request-controls (241), desktop-responsive (260), tablet reader parts |
| Requests / submissions (add by URL, cards) | cards-and-submissions (248), reader-shell-and-request-controls (request rows) |
| Profile (photo, details, password, Kindle emails, security) | profile-settings-layout (250), profile-security-and-access-users (275), access-settings-fields (333) |
| Admin access / users (tabs, user table, permission chips, invite) | access-settings-fields, profile-security-and-access-users, access-users-processing-layout/access-users-table-layout (145) |
| Processing dashboard (cards, bulk bar, automation schedule, sync, tables, requeue, errors) | processing-card-toolbar (221), access-users-processing-layout/processing-card-layout (260), processing-automation-and-tables/* (462), processing-skeletons/* (464) |
| Reprocessing jobs | reprocessing-page (297) |
| Skeleton loaders (books, processing, page-level) | book-and-processing-skeletons (242), page-loader-foundation (136), profile-reader-and-auth-loaders (171) |
| Responsive overrides | desktop-responsive (260), table-responsive-columns (188), tablet/* (1,071), mobile/* (441) |
| Dark overrides | dark-mode (1806) |

Feature signals (what the UI supported, useful for requirements): catalog search + sort + filter drawer + saved filters + incremental loading (`catalog-table-shell--incremental`); digital vs manual book types; contributor roles (author, translator, editor, publisher) shown as role labels; categories, series, publishers, bindings (hardcover/paperback), price, language; per-user "my books" with Kindle send (sent state, resend) ; notes/highlights with colours incl. underline and quote types, grouped by book, open in reader; reading log (unread/reading/finished, rating 1-5, progress); admin access scopes as permission chips; TOTP 2FA and OTP login; processing pipeline UI with queues, pause/run, automation schedule (time, frequency), catalog sync, requeue, failed/on-hold lists, multipage badge ("incomplete"); reprocessing with statuses queued/processing/succeeded/failed/cancelled; export (CSV, Excel, PDF); backend-offline overlay; error boundary.

## G. Breakpoints observed

max-width: 1200, 1100 (one rule), 1024 (two blocks), 1020 (reprocessing), 980 (main tablet/desktop split; most used), 900 (loaders), 768 (main phone/tablet split), 720 (one rule), 640 (main phone), 420 (narrow phone). Ten different values for roughly three real tiers; no min-width/mobile-first, no container queries. `:where(...)>*{min-width:0}` guard exists (tablet base L7) to stop grid blowout: a good defensive rule.

## H. Duplicated / dead / conflicting CSS

- S23. Duplicates: token blocks (S11); `.scope-card` declared twice consecutively (profile-security L109-121); `.skeleton-line-card-id` twice with widths 118 and 126 (book-and-processing-skeletons L133-140); `.processing-inline-loader` defined in two files with different layout (sync/automation-switches L188-195 vs skeleton-primitives L1-10); `.book-grid` defined thrice (cards L37-41, manual-books L216-219 forced 2 cols, mobile 1 col); `.book-card` defined in cards-and-submissions L60-92 and book-card-and-detail-grids L1-30 with different grids (78px|1fr vs 156px|1fr); `.book-card-id` twice; `.status-pill`/`.status-*` split over cards, access-settings, book-metadata; `.dialog-actions` twice (3-col grid vs flex, mobile grid); `.reduced-motion` twice; two toggle-switch implementations; many `*-button` gradients copy-pasted (`#d84a4a -> #a83232` appears in 12+ places: danger-button, book-delete-control, my-books-toggle, kindle-button, resend-kindle, notes-icon-btn--danger, delete controls and their dark twins).
- S24. Likely dead or unreferenced (cannot verify without reading components): `.shell-ornament` right/left (if removed in JSX), `.detail-card-brs`, `.compact-card`, `.audience-rule-*`, `.candidate-*`, `.landing-*` (legacy request landing), `.hero-copy`, `.nav-dropdown-item` (only in dark rule), `.mobile-nav-session` variants, `.table-note`. Dark rules for classes never defined in light CSS: `.nav-dropdown-item`, `.catalog-table-surface`, `.catalog-table-row`, `.catalog-table-header` (dark-mode L388-398; the comment at L1334 says class names were updated), `.settings-panel`, `.profile-settings-section`, `.modal-panel`, `.confirmation-dialog`, `.auth-dialog`, `.auth-surface`, `.reader-access-card`, `.reader-thumbnail-bg`, `.automation-card`, `.sync-card`, `.sync-icon-button`, `.processing-layout-card` : likely stale.
- S25. Name drift / misleading names: `reserved-layout-overrides.css` (keyframes), `mobile-responsive-layout/narrow-phone-and-count-fixes.css` (contains tablet-ish 640 rule and 420 fixes), `.catalog-*` classes reused for processing and access-users toolbars (`catalog-search-field.processing-search-field`, `access-users-toolbar .catalog-toolbar-select`) so a change to the catalog toolbar breaks other pages; one component styled by an override pyramid of 3-5 selectors (`.catalog-page-header--property-layout ...` is overridden in 6 media blocks).
- S26. Fixed pixel magic: `min-height:124px` toolbars, `724px` list cards, `97.5px`, `248px`, `146px`, `69px`, `42.36px` (notes `brs-note-header max-height`), sticky `86px`, table min widths 720-1172; heights chosen to avoid layout shift of skeleton vs loaded content (intent good: skeleton must match final size).
- S27. Conflicting responsive layers: `.book-grid` 2-col forced after the auto-fit rule; `.processing-card-head-line` grid redefined in desktop 980, tablet 768 and reprocessing 980; `.catalog-toolbar-topline.has-secondary` etc. Order-dependent; adding a rule in the wrong file silently loses.
- S28. Semantic colour misuse: red gradient means "delete" and also "in my books", "Kindle sent", and `is-added:hover`; green means "added" and "primary" and "active"; the same state (toggle on) is colour-coded differently in `book-card-toggle-button`, `my-books-toggle`, `kindle`. Rebuild: state through icon + label + tonal colour, red only for destructive.
- S29. Best-practice sample: `reprocessing-page.css` (297 lines) uses only tokens, a status-badge family `--queued/--processing/--succeeded/--failed/--cancelled`, column-hide helper classes (`.reprocess-hide-md` <=1020, `.reprocess-hide-sm` <=640), sentinel row for infinite scroll (`.reprocess-sentinel-cell`). Models the target approach (still has a hard-coded `#c0392b`).

## I. Worth keeping as design ideas (for M3 minimalist)

1. A tiny semantic token set (surface, on-surface, muted, line, accent, success, warning, danger) driven by M3 system tokens; one definition per theme via `color-scheme` + `light-dark()` or `prefers-color-scheme` + `[data-theme]`.
2. Tri-state theme (System/Light/Dark) with persistence and a visible toggle; reader keeps its own paper/sepia/dark themes.
3. Calm green identity (deep green accent on neutral surfaces) as the seed colour for an M3 palette; drop glass, gradients, ornaments, wordmark glow.
4. Status taxonomy to tonal chips with text (queued, processing, succeeded, failed, cancelled, needs review, pending resolution, requeued).
5. Table -> stacked cards on phones with `data-label` captions; sticky header tables on desktop; fixed column widths with truncation.
6. Skeletons sized to match final content (prevent layout shift); stable-width buttons with reserved spinner slot (`button-label--stable`).
7. Safe-area insets, `dvh`, `:where(...)>*{min-width:0}` guard, skip link, reduced motion, 44 px targets, `scrollbar-gutter: stable`.
8. Responsive tiers reduced to three container/viewport widths (compact < 600, medium 600-839, expanded >= 840 per M3).
9. Bengali-first typography: Noto Sans Bengali / Hind Siliguri as primary (web fonts loaded), no uppercase, no letter-spacing, body 16-18 px, line-height 1.6+ for Bengali; separate serif for reading.
10. Sticky page header with search/sort/filter drawer and URL-addressable filters (16b U27).

## J. Problems to avoid in rebuild (summary)

Attribute-only dark overrides (S12); hard-coded colours (S13); 1.8k-line shadow dark sheet; duplicate token blocks (S11); file splitting driven by a line cap (S1); responsive rules scattered by breakpoint instead of by component (S2); `!important` (S14); reuse of `catalog-*` classes across pages (S25); fixed pixel heights (S26); red/green overloaded semantics (S28); uppercase+tracking labels (S7); sub-44 px targets (E); undefined tokens (S6); heavy glass blur on many layers (S9) which also costs paint performance on low-end phones.

## Coverage table

| File (under src/styles) | Lines | Fully read |
|---|---|---|
| app.css | 32 | yes |
| app/access-settings-fields.css | 333 | yes |
| app/access-users-and-processing-layout.css | 2 | yes |
| app/access-users-processing-layout/access-users-table-layout.css | 145 | yes |
| app/access-users-processing-layout/processing-card-layout.css | 260 | yes |
| app/book-and-processing-skeletons.css | 242 | yes |
| app/book-card-and-detail-grids.css | 247 | yes |
| app/book-metadata-and-hero.css | 252 | yes |
| app/book-source-and-toc-panels.css | 273 | yes |
| app/cards-and-submissions.css | 248 | yes |
| app/catalog-property-controls.css | 432 | yes |
| app/catalog-tables.css | 340 | yes |
| app/catalog-toolbar-primary.css | 316 | yes |
| app/catalog-toolbar-secondary.css | 258 | yes |
| app/dark-mode.css | 1806 | yes |
| app/desktop-responsive-layout.css | 260 | yes |
| app/foundation-and-shell.css | 543 | yes |
| app/manual-books-and-book-grid.css | 442 | yes |
| app/mobile-responsive-layout.css | 3 | yes |
| app/mobile-responsive-layout/catalog-and-toolbar.css | 207 | yes |
| app/mobile-responsive-layout/narrow-phone-and-count-fixes.css | 83 | yes |
| app/mobile-responsive-layout/processing-books-and-reader.css | 151 | yes |
| app/my-books-actions.css | 276 | yes |
| app/navigation-and-buttons.css | 274 | yes |
| app/notes-page.css | 891 | yes |
| app/page-loaders-and-states.css | 3 | yes |
| app/page-loaders-and-states/auth-controls-and-dialogs.css | 144 | yes |
| app/page-loaders-and-states/page-loader-foundation.css | 136 | yes |
| app/page-loaders-and-states/profile-reader-and-auth-loaders.css | 171 | yes |
| app/processing-automation-and-tables.css | 3 | yes |
| app/processing-automation-and-tables/automation-fields-and-status.css | 138 | yes |
| app/processing-automation-and-tables/automation-switches-and-filters.css | 228 | yes |
| app/processing-automation-and-tables/sync-card-and-icon-buttons.css | 96 | yes |
| app/processing-card-toolbar.css | 221 | yes |
| app/processing-skeletons.css | 3 | yes |
| app/processing-skeletons/requeue-and-error-states.css | 202 | yes |
| app/processing-skeletons/skeleton-primitives.css | 111 | yes |
| app/processing-skeletons/table-columns.css | 151 | yes |
| app/profile-menu-and-page-layout.css | 282 | yes |
| app/profile-security-and-access-users.css | 275 | yes |
| app/profile-settings-layout.css | 250 | yes |
| app/reader-shell-and-request-controls.css | 241 | yes |
| app/reprocessing-page.css | 297 | yes |
| app/reserved-layout-overrides.css | 74 | yes |
| app/table-responsive-columns.css | 188 | yes |
| app/tablet-responsive-layout.css | 5 | yes |
| app/tablet-responsive-layout/base-and-reader-topbar.css | 71 | yes |
| app/tablet-responsive-layout/catalog-access-and-reader.css | 109 | yes |
| app/tablet-responsive-layout/catalog-property-controls.css | 349 | yes |
| app/tablet-responsive-layout/navigation-drawer.css | 253 | yes |
| app/tablet-responsive-layout/records-processing-and-reader.css | 288 | yes |

Total: 56 files listed by `find` (12,901 lines), all read.

## Unverified items

- Whether JS always sets `data-theme` at boot (S12 severity depends on it); not checked (components not read).
- Dead-class list (S24) is inferred from CSS alone; no JSX/TSX searched, so every "likely dead" claim needs a component grep.
- Contrast ratios (E) are judged by eye from rgba values over assumed backgrounds, not computed.
- Counts such as "~330 selector groups", "~35 !important", "~40 shadows" are estimates from reading, not tool counts.
- Which web fonts are actually loaded (index.html / font files) is outside this slice.
- Embedded reader CSS (`src/embedded-reader/static/css/**`) is outside this slice; only its tested intent is in 16b U26.

## Unread files and why

- None in `src/styles`. Embedded-reader CSS, index.html and component files were out of scope.
