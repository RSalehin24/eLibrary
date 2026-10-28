# Shared design, localization, and route coverage

Tasks W04/W08. Existing routes are under `app/web/src/app`; shared components/styles are under `src/components`, `src/app/*.css`, and message dictionaries under `src/lib`. Extend these seams. Consolidate conflicting rules instead of adding page-specific override layers.

## Design rules fixed before implementation

| Element | Target behavior |
| --- | --- |
| Spacing | Use 4/8/12/16/24/32px tokens. Controls within a group use smaller gaps than separate sections. Remove decorative heading counters. |
| Color and type | Reuse the existing ink/paper/green/surface/line semantic palette and bundled Bengali font. Standardize text/control metrics through shared tokens. Do not introduce another font or icon dependency. |
| Controls | Normal search, sort, filter, and action controls share a 46px height; all interaction targets are at least 44px. Permit growth at 200% text instead of clipping. Native disabled state and visible pending/error feedback are distinct. |
| Headings | One page heading followed by the main task. Consistent title/description/action layout; no oversized instruction block before ordinary results. |
| Container | Reuse one catalog/admin content container; source and unfinished workspaces use the same compact hierarchy. Reading canvas has separate full-viewport rules. |
| Shells | Reader navigation: My Books, Browse, Notes, Kindle. Admin: permission-filtered sections and labelled mobile drawer. Same-account Reader View/Return to Admin; view switching never mutates grants. |
| Brand/navigation | Combined বাংলা পাঠাগার mark without an adjacent repeated name. Active indication uses a consistent non-underlined treatment and accessible current-page state. |
| Cards | Grid children stretch through wrappers; cover treatment is stable; body grows and action footer aligns within each row. Long titles/credits wrap fully. Save/Kindle/progress stay inside the card and outside stretched-link hit areas. |
| Tables | Consistent density/action columns; reserve space while account actions load. Horizontal scrolling stays in a labelled table region, never the entire page. Narrow layouts keep the main action reachable. |
| Pagination | Shared numbered first/last, neighbors, ellipses, current page, and count. Disabled boundaries cannot navigate; preserve submitted filters/sort; reset and out-of-range behavior follows the data contract. |
| Exports | One compact Download list disclosure after results/pagination, exporting the complete filtered scope. |
| Feedback | Distinct loading, empty, no-match, failed/retry, denied, unavailable, stale, saving, saved, and disabled states. Announce outcomes without moving focus unexpectedly. |
| Accessibility | Semantic headings/labels, keyboard order, visible focus, modal focus containment/restoration, 4.5:1 ordinary-text and 3:1 large-text/control contrast, reduced motion, and text enlargement without lost controls. |

At 1366×900, normal catalog results begin by y=320px and applicable ordinary admin tables show at least eight rows. At 390×844, normal browse results begin by y=390px. Define exception screenshots/expectations for empty/error/form pages instead of applying list budgets to them. Check 320/390/820/1366/1920px, portrait/landscape, and 200% text in both languages. Geometry is necessary evidence; rendered inspection and realistic task completion remain required.

## Localization and time

Use existing message dictionaries with complete Bengali and English labels, validation, pending, error, and empty states. Translate interface text, not source book prose/titles/credited names. Preserve Bengali grapheme clusters, original capitalization, numerals in source text, and natural contributor role wording. Curated collections are পাঠতালিকা / Reading Lists.

Store instants in UTC; render and accept application scheduling/expiry times through `Asia/Dhaka`. Display a 12-hour clock with localized date/digits/day periods. Date/time forms show the selected zone and reject invalid/incomplete values before submission. Convert a local entered time exactly once; browser timezone must not shift a schedule. Round-trip midnight/noon, month-end, expiry boundaries, English/Bengali digits, and browser zones outside Dhaka. Interface language persists across website/reader navigation and reload without a mixed-language hydration flash.

## State packs

Every route audits its shell, title, local navigation, controls, summary, content, actions, forms, dialogs, feedback, pagination, exports, and footer. Explicitly mark absent portions not applicable. Expand dynamic parameters into real fixtures; all four managed entity kinds require independent checks.

| Pack | Applicable states/interactions |
| --- | --- |
| `L` list | Populated/loading/empty/no-match/failure/retry, slow/stale responses, query clear/reset, sort, filters, pagination, exports where present, back/forward, account hydration |
| `D` detail | Ready/loading/missing/unavailable/denied/failure, missing cover/metadata, long title/credits, related links, action permissions, active-build consistency |
| `F` form | Clean/dirty/invalid/pending/success/failure/timeout/stale/denied/disabled, duplicate submit, focus/labels, draft retention, navigation/update guards |
| `A` authentication | Anonymous/authenticated/expired/rate-limited/invalid link/TOTP-required/replayed link, safe return destination, pending/error recovery |
| `O` operation | Queued/running/stop-requested/retry-wait/paused/cancelled/failed/uncertain/succeeded, restart, authority/revision changes, real progress and partial bulk results |
| `S` static | Both languages, narrow/wide/enlarged text, keyboard links, missing/configured contact content, not-found/error/offline boundaries |
| `R` reader | Full reader state/command/security matrix in the reader plans; verify website launch/deep-link boundary before extraction |
| `X` removed | No navigation, form, current schema/API/grant/export exposure; direct obsolete route/API is 404; retained features still work |

## Starting route matrix

This table accounts for all 54 current `page.tsx` templates: 49 website routes, 3 reader routes, and 2 removals. Route templates and supported page states must expand when new surfaces are found. Paths here describe product routes, not API routes.

| Route | Disposition/task | Access and required pack |
| --- | --- | --- |
| `/` | Website W05 | Public entry; signed-in role destination; L/S |
| `/catalog/` | Website W05 | Public safe metadata; account action variants; L |
| `/books/[slug]/` | Website W05 | Public metadata; action grants; D |
| `/books/[slug]/editions/` | Website W05 | Public current bibliographic editions/access; L/D |
| `/contributors/` | Website W05 | Public author-first/other-role directory; L |
| `/contributors/[slug]/` | Website W05 | Public linked-book detail; D/L |
| `/categories/` | Website W05 | Public directory; L |
| `/categories/[slug]/` | Website W05 | Public linked-book detail; D/L |
| `/series/` | Website W05 | Public directory; L |
| `/series/[slug]/` | Website W05 | Public ordered linked books; D/L |
| `/collections/` | Website W05 | Public visible reading lists; L |
| `/collections/[slug]/` | Website W05 | Visible list, ordered linked books; D/L |
| `/my-books/` | Website W05 | Own saved/owned/recent/granted library; L |
| `/my-books/[slug]/` | Website W05 | Own context, notes/progress and actions; D |
| `/physical-books/` | Remove W01 | X |
| `/notes/` | Website W06 | Own highlights/notes/quotes/bookmarks; L/F |
| `/profile/` | Website W06 | Own account/security/recipients/photo; F/A |
| `/reader/` | Reader R01 | Reader entry/availability, website launch boundary; R |
| `/reader/[identifier]/` | Reader R01 | Account-bound current session; R |
| `/local-reader/` | Reader R01/R04 | Anonymous/device-only, offline shell; R |
| `/kindle/` | Website W06 | Own operation history; L/O |
| `/kindle/books/[slug]/` | Website W06 | Authorized send and recipients; D/F |
| `/kindle/operations/[identifier]/` | Website W06 | Own operation and explicit resend/cancel; O |
| `/login/` | Website W06 | A/F |
| `/create-password/` | Website W06 | One-use invitation/setup link; A/F |
| `/reset-password/` | Website W06 | Non-enumerating request flow; A/F |
| `/reset-password/confirm/` | Website W06 | One-use reset confirmation/TOTP; A/F |
| `/help/` | Website W06 | S |
| `/about/` | Website W06 | S |
| `/contact/` | Website W06 | S; configured contact destination |
| `/[legacy]/` | Remove W01 | X; ordinary not-found handles unknown routes |
| `/manage/` | Website W04/W07 | Authorized first destination; admin creation first; D |
| `/manage/overview/` | Website W07 | Authorized operational summary; L/O |
| `/manage/books/` | Website W07 | Authorized list; only admins get Edit/Files mutation; L |
| `/manage/books/new/` | Website W03/W07 | Existing intake authority, unified EPUB flow; F/O |
| `/manage/books/[slug]/` | Website W02/W07 | Admin editor/files; D/F/O |
| `/manage/books/[slug]/relationships/` | Website W02/W07 | Admin associations/order/editions; D/F |
| `/manage/book-creations/[identifier]/` | Website W03/W07 | Authorized own creation result; D/O |
| `/manage/entities/` | Website W07 | Authorized contributor hub with entity tabs; L |
| `/manage/entities/[kind]/` | Website W07 | Four authorized kinds; L |
| `/manage/entities/[kind]/new/` | Website W07 | Current global creation authority; F |
| `/manage/entities/[kind]/[identifier]/` | Website W07 | Current global/scoped entity authority; D/F |
| `/manage/sources/` | Website W07 | Current processing/source visibility rules; L/F/O |
| `/manage/sources/[identifier]/` | Website W07 | Authorized source/evidence/recovery, no review; D/O |
| `/manage/unfinished/` | Website W07 | Source-marked unfinished plus actual change scopes; L/O |
| `/manage/jobs/` | Website W07 | Authorized source/preparation/operation list; L/O |
| `/manage/jobs/[identifier]/` | Website W07 | Authorized operation controls/details; D/O |
| `/manage/automations/` | Website W07 | Authorized schedule list/run/history; L/O |
| `/manage/automations/new/` | Website W07 | Current processing authority; F |
| `/manage/automations/[identifier]/` | Website W07 | Authorized edit/run/history; D/F/O |
| `/manage/users-access/` | Website W07 | Current access administration; L |
| `/manage/users-access/[identifier]/` | Website W07 | Protected-account/self-edit/grant boundaries; D/F/O |
| `/manage/users-access/invite/` | Website W07 | Invitation creation and queued mail; F/O |
| `/manage/users-access/mail/[identifier]/` | Website W07 | Authorized private delivery status/retry; D/O |

Reader route ownership switches in R01. W08 must verify the retained reader entry integration, but the extracted reader's visual acceptance is R05. No new history page, physical inventory, reviewer inbox, or compatibility redirect is needed.

## W04 and W08 evidence

Build shared headings/controls/cards/table/pagination/dialog/feedback with catalog, book details, My Books, source creation, unfinished, schedules, and users/access as representative pages. Apply the same system to all remaining rows; do not mark a row complete from a shared-component test alone.

Extend existing `tests/web/e2e/design-layout.spec.mjs`, `layout-routes.mjs`, `workspace-views.spec.mjs`, `numbered-pagination.spec.mjs`, and `admin-lists.spec.mjs`. Preserve original failing assertions/screenshots, review actual renders, and link accepted evidence per route/state. Inspect header wrapping, action hit areas, focus, mobile safe areas, covers, no-match feedback, delayed hydration, and 200% text explicitly.
