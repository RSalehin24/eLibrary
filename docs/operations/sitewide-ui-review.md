# Sitewide UI and UX review — 21 October 2026

Scope: all **53 page route templates**, including legacy redirects, with
**66 concrete route/state variants** covering the four metadata kinds,
authentication forms, linked/unlinked sources, empty results and missing pages.
The repeatable inventory is `tests/web/e2e/layout-routes.mjs`; it uses real private
reference fixtures. It does not seed the preview database or send mail.

## Repairs

| Area | Result |
| --- | --- |
| Branding | One SVG logo includes বাংলা পাঠাগার; its name stays Bengali in English mode. Header, footer and sign-in use the same artwork. |
| General header | Brand, language/account controls and navigation have independent layout rows; links do not break into arbitrary lines. Narrow navigation supports horizontal scrolling and keyboard access. |
| Admin header | Dedicated management shell, permission-filtered navigation and direct Reader View. Mobile controls reflow and active sections scroll into view. Long active labels fit the navigation at 200% text, including Safari; observing the active link also handles font changes without a viewport resize. |
| Account views | Administrators sign in to Admin; Reader View uses their existing personal account and offers Return to Admin. Preferences are account-bound and cannot change authorization. |
| Pagination | Real numbered pages, first/last, nearby pages and ellipses; shorter phone windows; filter/sort preservation. Catalog, library, metadata directories, editions, paper books and admin histories use the shared controls. |
| Pagination layout | Removed conflicting display rules and minimum-content grid overflow. Previous/next controls reflow at 200% text; original overflow assertions remain. |
| Empty pages | Invalid personal/paper-book page numbers use the missing-page flow instead of falsely reporting that the library is empty. |
| Automation | Search, enabled/frequency filters and due/name sorting; exact filtered counts; compact desktop table and phone records. Run Now and Settings & History appear directly on each row. Paused rows do not imply an active next run. |
| Users & Access | Search/status/sort controls have attached labels. Each row groups identity, account state, actual two-step status, grant count and Manage; email is not duplicated for unnamed accounts. Phone records wrap long addresses. |
| Short admin pages | Mobile grid rows no longer stretch the sidebar and insert a large blank area above short forms/results. Book creation has a clear result panel and next actions. |
| Catalog and metadata | Compact mobile browse controls preserve visible links; shared compact search/sort controls and exports below results put the books first. |
| Book tables | Fixed columns and a persistent detail action prevent late-loading save/Kindle controls from moving metadata links. A delayed-response regression checks pointer stability; the original layout moved a category link about 49 px horizontally and 26 px vertically. |
| Local EPUB entry | Clear upload panel, consistent heading/icon, labelled native file selection and associated size/privacy guidance; existing offline reader behavior remains. |
| Language | Added translations for the new controls and corrected reset-filter wording. The static/offline EPUB entry restores the language cookie and localizes streamed metadata after reload. Dates retain 12-hour Dhaka formatting. Links retain visible focus without text decoration. |

## Page inventory

| Family | Routes reviewed |
| --- | --- |
| Public browsing | Home, catalog/results/empty search, contributor/category/series/collection directories and details, book details and editions |
| Public information | About, contact, help, local EPUB entry, legacy library redirect, missing page and missing book |
| Authentication | Sign-in, reset request, valid reset confirmation and invitation password setup |
| Personal library | My Books, private book detail, paper books, notes, profile/security, legacy reader entry and launched reader |
| Kindle | History, composer and cancelled operation detail |
| Admin catalog | Overview, books, create/edit, relationships, creation result, entity hub and list/create/edit for all four metadata kinds |
| Admin processing | Source catalog, linked/unlinked detail, unfinished books, jobs/detail, automation list/create/edit/history |
| Admin access | Account directory/detail, invitation and mail operation detail |

`design-layout.spec.mjs` checks each variant in Bengali and English at **320,
820 and 1366 pixels**, plus **320 pixels with 200% text**: **528 layout scenarios
per browser profile**. It checks HTTP outcomes, document/control overflow,
stretched mobile admin navigation, active-section visibility, persisted language,
book-result/export order and the first desktop result's position. Each variant
also gets full-page Bengali phone/desktop screenshots for visual review.
The checks supplement interaction tests; they do not establish subjective design
acceptance or cover every possible book/file/browser state.

## Verification

The initial layout sweep exposed shared pagination overflow in catalog, source,
job, account and metadata lists. Those original assertions passed after repair
(`ui-review-all-layout-reflow`), along with existing responsive and bilingual admin
journeys. Screenshot review additionally exposed the stretched mobile sidebar,
which now has a geometric regression assertion.

Current implementation checks: **713 backend/tooling tests**, **144 web unit tests**,
production build, ESLint, strict TypeScript, mypy on **277 configured files**,
zero-warning regenerated OpenAPI/client contracts, migration consistency,
affected Python lint/format, architecture/file-size and whitespace checks.
Backend coverage includes existing query-count budgets, filtered totals,
account visibility and automation filters. No test, lint or type rule was weakened.

The first broad browser run also found the table shift, filter-label/reset issues
and the static reader's language reset. The legacy branding/navigation assertions
were updated to the explicitly requested combined logo and separate admin header;
their visibility, permission and overflow checks remain. Browser routing in the
layout-only sweep disables HTTP cache to inspect fresh responses; separate PWA
and local-reader journeys continue to verify actual service-worker/offline behavior.

Accepted browser coverage:

| Gate | Accepted scope |
| --- | --- |
| Chromium specification inventory | Passing records for **243 journeys across all 57 specifications**, combining the broad run with focused repairs and reruns. This is not a claim that the initial run was green. |
| Shared focused matrix | **30 journeys per profile**, **150 combinations** across Chromium, WebKit, Android, iPhone and pinned Linux Firefox. Seven specifications cover page layouts, account/view navigation, numbered pagination, local EPUB, language persistence, sign-in and schedule/account controls. |
| Page layout inventory | **528 scenarios per profile**, **2,640 total**. Each record retains its route key, language, width, text scale and measured problems; all accepted records have no reported geometry problems. |
| PWA and update behavior | All **14 Chromium PWA journeys** pass against the final unchanged build, including unsaved forms, offline launch and reader-position persistence. These overlap the specification inventory. |

The focused matrix overlaps the Chromium inventory; the 2,640 layout states are
nested within its page-family tests. These numbers must not be summed as a unique
test total. `ui-review-accepted-evidence.json` records the accepted specification
logs and verifies the scenario counts, rather than counting retries twice.

The layout assertions poll the same bounds after the browser applies asynchronous
resize handling. They retain the active-section, overflow and result-placement
requirements. Two long single-process Linux Firefox captures lost their renderer
while taking screenshots. The accepted Firefox run executes **all eight page
families**, each in a fresh pinned container/browser with a 1,500 MiB memory cap
and 512 MiB shared memory. No page family or assertion is omitted. This establishes
the recorded page checks; it does not establish unrestricted long-session memory
behavior under the smaller container limits.

Sitemap enumeration was rerun sequentially after fixture seeding stopped; concurrent
seeding changes the global public catalog between sitemap batches. The complete
canonical-URL, uniqueness and private-path assertions remain. PWA checks ran with
build artifacts fixed, because the update simulator reads the generated worker.

Accepted local artifacts under ignored `test-artifacts/foundation/`:

- `ui-review-full-chromium`, `ui-review-accepted-chromium`,
  `ui-review-final-ready-chromium`, `ui-review-navigation-chromium`,
  `ui-review-seo-serial`: broad inventory and the accepted Chromium reruns.
- `ui-review-final-ready-webkit`, `ui-review-navigation-webkit`: accepted WebKit
  interactions and final layouts/navigation.
- `ui-review-final-{android,ios}`, `ui-review-admin-{android,ios}`: mobile matrix.
- `ui-review-final-firefox`, `ui-review-accepted-firefox-layout`,
  `ui-review-firefox-page-groups`: accepted Firefox interactions and fresh
  page-family captures; the two earlier whole-capture failures remain recorded.
- `ui-review-backend-regressions.log`, `ui-review-navigation-final-{units,build,
  typecheck,lint}.log`, `ui-review-final-mypy.log`, `ui-review-schema-final.log`:
  implementation gates. Fixture JSON files contain private test credentials and
  must not be published.

Representative inspected reference screenshots: [automation desktop](../../test-artifacts/foundation/ui-review-delivery-visuals/automations-1366.png),
[accounts on a phone](../../test-artifacts/foundation/ui-review-delivery-visuals/users-access-390.png)
and [enlarged English navigation](../../test-artifacts/foundation/ui-review-enlarged-tab-repair.png).
Reference data is synthetic. The separate preview's actual first cover images
were also checked for successful loading. Preview **http://localhost:3000/** and
API readiness return HTTP 200; its source processing continues. Delivery remains
off and no preview fixtures were added. Earlier source/reader capability boundaries
remain in [the completeness report](feature-parity.md).

Only simulators are available. Real device installation, external Kindle receipt,
production deployment and independent-machine load remain outside this review.
The earlier development-only lint dependency findings remain recorded separately.
No zero-bug or universal visual-perfectness claim is made.
