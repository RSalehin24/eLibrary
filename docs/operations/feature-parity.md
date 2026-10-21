# Application completeness audit — 21 October 2026

## Approved interface redesign — current checkpoint

The separate admin/reader plan is implemented and under final browser verification.
Admin opens Book Creation, readers open My Books, and the new shells, compact
filters, Notes repair, schedule summary/reset and audited source-credit corrections
are described in [the redesign report](interface-redesign.md).
Build, lint, strict web types, 149 web units and the 827-test catalog/auth/ingestion
and 911-test processing/access gates pass. Previous UI screenshots and acceptance
counts below describe the superseded design; they are not proof of this revision.


Baseline: `main@08fc99f9d59221072404b1af4ab501dfc3fd269e`.
Target: `reyan-new-version`, including the current working tree. The retained
frontend differs from the baseline in 13 files; it is supporting evidence only.
This is a capability audit, not an overall completion percentage. “Verified”
means recorded automated evidence; it does not promise zero bugs or design acceptance.

## Sitewide UI follow-up — 21 October 2026

The UI inventory now covers **53 page route templates**, including legacy
redirects, through **66 concrete route/state variants**. Admin and general headers
are separate. Administrators default to Admin and can enter their personal Reader
View or return to Admin with the same account; the preference never changes
permissions. One shared SVG includes বাংলা পাঠাগার without a repeated header name.

Numbered pagination exposes real totals, boundaries and nearby pages, retaining
filters across public, personal and administrative lists. Users & Access now has
labelled search/status/sort controls and grouped account/security/action records.
Automation exposes saved policy, paused/next-run state, filters and direct Run Now
and Settings & History actions. Compact browsing controls place results before
exports; creation results and local EPUB entry have clear next steps.

The sweep corrected mobile grid stretching, pagination overflow, late account
actions moving table links, static EPUB language resets and Safari's oversized
active navigation labels at 200% text. Regression checks retain the original
geometry, visibility and permission requirements. **713 backend/tooling tests**,
**144 web units**, build, lint, strict types/schema, configured mypy and repository
policies pass. The full page inventory, screenshots, accepted browser evidence
and external acceptance boundaries are in
[the sitewide UI review](sitewide-ui-review.md).

Passing records cover **243 Chromium journeys across all 57 specifications**.
The shared seven-specification matrix passes **30 journeys per profile**, **150
combinations** across Chromium, WebKit, Android, iPhone and pinned Linux Firefox,
including **2,640 layout scenarios**. These overlap rather than forming a unique
sum. Firefox's accepted layout run uses a fresh container per page family after
long capture runs lost their renderer; all eight families and assertions remain.
All 14 final Chromium PWA journeys and the sequential sitemap checks pass.

The restored preview's **2:16 pm Asia/Dhaka, 21 October** snapshot has **1,876
verified publications**, six earlier quarantined records, **2,229 queued source
jobs**, one running, **61 automatic retry waits** and **zero failed or
attention-required source jobs** (`ui-review-runtime-final-counts.log`). Processing
continues; these moving totals supersede the older checkpoints below and do not
claim that the entire source catalog has been processed. Delivery remains off.

## Second audit outcome

The first inventory missed live workflows from the pinned version, so its earlier
completion statement was too broad. The second audit restored the omitted controls
listed below and found additional interaction defects through actual browser use.
The register distinguishes retained capabilities, intentional changes and supported
format limits; it does not equate passing tests with a zero-bug guarantee.

The restored workflows cover contributor credits and protected detail previews,
device-local/offline EPUB reading, nested contents, exact note-to-reader links,
note shortcuts, initial-password accounts, account-list controls, authenticator
URL copying, Run Now scheduling, directory sorting, physical-log reset and
card/table save/Kindle actions. Private metadata links and Back navigation preserve
the applicable library view. Desktop My Books tabs now wrap horizontally.
My Books also keeps results ahead of export tools and uses a compact filter row.
Clearing an unsubmitted search resets its input, while submitted saved searches
retain their values when reopened. See [personal-library layout](personal-library-layout.md).

Real defects fixed during verification included asynchronous highlighting clearing
the user's selection, WebKit suppressing local-reader event handlers, stretched
card links covering buttons and metadata links, ambiguous directory labels and
narrow publication facts. A real source export failure also exposed heuristic
chapter inference inserting headings into canonical text. Canonical exports now
retain their authoritative text and explicit contents; verification is unchanged.

## Source and reader follow-up — 21 October 2026

The remaining media-position boundary is now implemented. Imported spatial CFIs
restore an image/video point using rendered media geometry, and temporal CFIs
restore audio/video time after a verified native seek. Invalid geometry, unavailable
media and stale targets report failure without overwriting the saved location.
Protected library media supports byte-range seeking and session-bound permissions;
device-local EPUBs support embedded media offline with autoplay disabled. Reader
toolbar buttons now have 48 px targets after Firefox exposed a subpixel sizing
failure at the former minimum.

Website compilations now collect and independently verify their linked component
books. Every component must provide reading content, and all collected sections
must survive into the combined document and its verified exports. Validator 3
also fixes later publication references misclassifying complete prose. Historical
eligible waits recover once per validator version; missing components, chapters
and contents pages receive paced automatic availability checks. An inconsistency
between collected and extracted text still blocks publication separately.

A read-only audit checked **1,585 source publications: 1,584 verified and one older
partial compilation required regeneration**. The partial edition was quarantined
through the audited repair command, retaining its bytes and personal data. All
three component books were then collected and the replacement published through
the standard worker with verified HTML/EPUB files. Two other validator recoveries
and the stale-contents-page repair also published: **four real canaries passed**.
The compilation's identity, previous bytes and eight backed-up related records
remain intact. Queue routing is now configurable: a fresh preview
queue allows current work to proceed while **more than 236,000 old envelopes**
remain preserved in the old queue. Delivery remains separate with zero consumers.

Verification for this follow-up:

- Broad backend/tools gate: **1,840 passed**, 13 live cases excluded, warnings
  treated as errors (`implement-all-backend-accepted.log`). Later source/access
  changes passed **890 tests**; the final collection/queue behavior passed all
  **705 processing tests**, **53 configuration tests** and **33 tooling tests**.
  These suites overlap and
  are not added into a unique total.
- **135 web unit tests**, production build, ESLint and strict generated API types
  pass. Strict schema generation reports zero warnings; mypy checks **276 configured
  files**. Migration consistency, affected Python lint/format and repository
  architecture/file-size/whitespace policies pass.
- Reader/media/local EPUB: **12 journeys in each of five browser profiles**
  (**60 project/journey combinations**) in `implement-all-touch-{chromium,webkit,
  android,ios,firefox}`. The six legacy-reader journeys also pass each profile in
  `implement-all-final-*`; these overlap earlier acceptance records.
- All three Compose configurations resolve the processing queue consistently;
  the current platform supplies matching dispatcher/worker settings and capacity.
  Queue-name validation rejects unsafe or reserved delivery destinations.

The **12:10 am Asia/Dhaka, 21 October** startup snapshot has **1,704 verified
publications**, six older description-only records quarantined, **2,393 queued
source jobs**, **70 automatic waits** and **zero failed/attention-required source
jobs**. Continuous processing runs; the entire source catalog is still being
processed. This snapshot supersedes the earlier runtime totals below.

## Earlier verification — 20 October 2026

- Full backend/tools gate: **1,802 passed**, 13 live-network cases excluded,
  warnings treated as errors (`reaudit-accepted-backend.log`). The last additive
  private-detail field and canonical export guard subsequently passed **64 focused
  checks**, including existing source verification, recovery and legacy export
  cases. These overlap the full gate and are not added to it as unique tests.
  A final **24-test recovery/admission gate** verifies that code-repaired jobs keep
  their recovery turn after their error code clears, with the two-slot limit and
  new-work/continuation rotation preserved (`reaudit-source-recovery-lane.log`).
- **125 web units**, **154 retained frontend units**, **14 capacity-helper units**,
  production build, ESLint, strict generated API/TypeScript, mypy on **270 configured
  files** plus the retained exporter, affected Python lint, migration consistency,
  architecture/file-size policies and whitespace checks pass.
- The prior full specification inventory has passing records for **216 distinct
  Chromium journeys in 51 specifications**;
  three earlier failing specifications were rerun after fixing a stale contributor
  selector and excluding host-suspension failures. The two newest private-navigation
  journeys additionally pass Chromium, WebKit, Android, iPhone and Linux Firefox.
  Browser records use fresh private data per specification. The runner now matches
  exact filenames to prevent overlapping specification names running twice.
- Account/automation: **six journeys per Chromium/WebKit/Android/iPhone profile**.
  Notes/legacy reader/list controls: **nine per profile**. Local EPUB: **three per
  profile**, also passing pinned Linux Firefox. Credits/reset and directory checks,
  personal-library layout and private-navigation checks pass their recorded profiles.
  Groups overlap; their counts are not added into a completion percentage.
- The final browsing follow-up passes **11 journeys per Chromium/WebKit/Android/
  iPhone profile**, **13 in Linux Firefox** including exports, and two additional
  Chromium export journeys: **59 project/journey cases** within this follow-up.
  These exercise bilingual layout, 320 px enlarged text, clearing unsaved queries,
  saved-search restoration, filtered CSV/print/XLSX exports and private list actions.
  Passing records are under `continuation-final-{chromium,webkit,android,ios}`,
  `continuation-exports-final`, `continuation-personal-firefox-final`, and the
  catalog/list/export subdirectories of `continuation-library-firefox`. Its first
  personal-library run hit a synthetic account-switch race; the fresh seven-case
  Firefox run passed after leaving the old document before changing its test session.
  Dedicated active-document account-isolation tests remain intact.
- Dependency findings remain **zero production** and **five high development-only**
  findings in the compatible upstream lint chain, last rechecked 20 October.
  No audit result, lint rule, peer check or type check was bypassed.

The final read-only source audit checked **880 publications and verified all 880**.
The repaired book subsequently succeeded on attempt 2 through a standard-worker
canary after normal code-version recovery. Its published HTML and EPUB files are
both ready and pass the unchanged export proof. The moving runtime checkpoint has
**1,476 verified publications**, 2,616 queued jobs, one running, 74 automatic waits
and no failed/attention-required source jobs; six earlier description-only source
records remain quarantined. This snapshot was captured at **9:52 pm Asia/Dhaka on
20 October 2026** (`continuation-runtime-counts.log`). Processing continues and
delivery stays off; the remaining source catalog is not yet fully processed.

The broad run exposed test-infrastructure faults as well: an AMQP URL was used
as a Redis hostname, engine startup recovery lacked a database fixture, and wait
helpers used wall time. Fixtures now reuse the application's Redis resolver,
separate the test Redis server, enable database recovery explicitly and use bounded
monotonic polling. Regression tests preserve the original time budgets.

## Inventory and repair register

| ID | Previous behavior/evidence | Current surface/status | Repair and acceptance |
| --- | --- | --- | --- |
| BOOK-04 | Supporting contributor credits/links, BookDetailHero | Implemented; scoped checks passed | Translator/editor/publisher and other supported roles visible; public and personal related-book links preserve role and visibility scope. |
| BOOK-05 | Source front matter/dedication/nested contents, BookDetailPage | Implemented; scoped checks passed | Authenticated read-access-bound plain-text preview with explicit size/entry/depth limits and truncation notice; no raw HTML/source URL leak. |
| READ-05 | Local EPUB file picker and offline standalone shell, public/epub-reader | Implemented; scoped checks passed | Device-only ZIP parsing and resource rendering; 24 MiB archive/64 MiB expanded bounds, CRC validation, script/network isolation, reusable reading controls and public offline shell only. |
| READ-06 | Collapse/expand nested contents and reveal current ancestors, toc-helpers | Implemented; scoped checks passed | Accessible toggles, keyboard operation and current-chapter ancestry; shared local/library component. |
| NOTE-03 | Open each note/quote/highlight/bookmark in reader, NotesPage | Implemented; scoped checks passed | Owner/current-read-access checks, retained edition and exact verified target; read-once session reuse without opening another edition. |
| NOTE-04 | Ctrl/Command+Enter saves note, NotesPage/highlight methods | Implemented; scoped checks passed | Shared form shortcut retains ordinary validation and prevents duplicate submissions. |
| ACC-04 | Initial-password account creation with optional disabled status, AccessUserEditorCard | Implemented; scoped checks passed | Superadministrator only; chosen/generated password follows existing validation, secret-free idempotency receipts, no setup mail. Invitation remains default. |
| ACC-05 | User name/email/status sorts and status/permission keyword search | Implemented; scoped checks passed | Stable ID ties and existing access visibility; expired grants do not create effective-permission matches. |
| ACC-06 | Copy authenticator setup URL, TwoFactorSetupPanel | Implemented; scoped checks passed | Existing provisioning URI, explicit clipboard gesture and failure feedback, no secret logging. |
| SRC-12 | Run a saved automation immediately, AutomationPanel | Implemented; scoped checks passed | Preserve the next scheduled run, exact configuration, normal authority/admission rules, pinned revision and idempotent command. |
| CAT-10 | Writer/category/series date filters, code/date sorts and columns | Intentionally simplified in the approved redesign | Public date/type filters and code/date row metadata removed at the user’s request; valid name/count/code/date sorting and legacy API validation retained. Collections reject unsupported code sorting. |
| LIB-03 | Save/remove and Kindle shortcuts on book cards and table rows | Implemented; scoped checks passed | One bounded private permission-checked batch per result set; reuse ordinary save mutation and explicit Kindle composer. |
| PHY-03 | Reset physical reading log, Reset Log control | Implemented; scoped checks passed | Confirmation clears the draft only; explicit Save persists it with revision checks. Cancellation, pending writes and conflicts preserve data. |
| CAT-01 | Home/Library search, `pages/HomePage.jsx`, `LibraryPage.jsx` | `/catalog/`, `/manage/books/`: verified search and pagination | Preserve query, permission and language behavior. |
| CAT-02 | Combined contributor/series/category/type/ownership filters, `libraryFilters.js` | Implemented: combined catalog, managed and personal filters | Shareable author/role/category/series/reading-list/ownership conditions; old website type/date conditions are removed. Backend legacy validation remains compatible. |
| CAT-03 | Title/code/creation/request sorting, `libraryFilters.js` | Implemented: title/code/created/added/publisher sorts | Deterministic ties, account/filter-bound cursors and visible selectors; existing default ranking retained. |
| CAT-04 | Saved catalog/queue filters, `SavedFilterStrip.jsx`, common saved-filter API | Implemented: saved catalog and queue filters | Owner-private create/apply/delete; legacy author mapping; strict validated keys and idempotent creation. |
| CAT-05 | CSV/PDF full filtered catalog, `LibraryPage.jsx`, `utils/bookExport` | Implemented: full filtered CSV/PDF/print exports | Scoped all-page exports; formula protection. Bengali/Latin PDF rendered in Linux; host without shaping has explicit failure and print alternative. |
| CAT-06 | Categories/series/writers and role directories, baseline AppRoutes | Implemented: compact directories, counts, sorting and explicit contributor roles | Authors are the default; counts include visible distinct books only. Related-book links preserve role and visibility without retired type constraints. |
| CAT-07 | Card/table browsing and infinite list, baseline BookTable/BookCardGrid | Implemented: card/table choice and pagination | Accessible table headers, related entity links and a contained horizontal scroll region on phones. |
| CAT-08 | Metadata/edition/language/price/binding, baseline BookDetailPage | Verified fields/editing | Retain decimal fidelity, relationships and edition navigation. |
| CAT-09 | Metadata versions/edit notes, BookMetadataWorkspace | Implemented: provenance history and edit notes | Authorized bounded pages, actor names without emails, bilingual labels and Dhaka dates; protected snapshots stay private. |
| PHY-01 | Dedicated physical list, ManualBooksPage | Implemented: dedicated physical inventory | Publisher/binding/language and contributor-role filters, personal scopes and direct manual creation/edit actions. |
| PHY-02 | CSV/PDF/XLSX with grouping, ManualBooksPage/bookExport/excel | Implemented: scoped CSV/PDF/print/XLSX | Grouped multi-sheet XLSX, decimal values, safe cell text and complete filtered results. |
| LIB-01 | Add/remove My Books, CreatedBooksPage/useMyBooksAction | Verified, improved combined feed | Preserve ownership versus saved-book distinctions. |
| LIB-02 | My Books filters and request/title/creation sort | Implemented: combined filters and stable sorts | Compact controls keep results ahead of exports; query reset and saved-search restoration are verified; tabs preserve filters and owned/saved/recent/granted remain distinct. |
| BOOK-01 | Cover, details, Read/HTML/Kindle, BookDetailHero | Verified | Permission-aware actual files; HTML new tab; consistent icons. |
| BOOK-02 | EPUB replace and regenerate, baseline detail hooks | Implemented: atomic source and manual EPUB replacement | Stage and prepare before swapping; current text proof for website uploads; permission/revision rechecks; old bytes/sessions and personal data retained. |
| BOOK-03 | Book-specific notes, progress/location/last-opened | Implemented: last chapter/location, progress and four note views | Proven edition identity only; safe resume or explicit unresolved-place notice without exposing raw CFI. |
| READ-01 | Scroll/page/spread, fullscreen, gestures, themes | Verified reader controls | Fullscreen book only; preserve passage through reflow. |
| READ-02 | Font size 14–30, reader-settings | Implemented: minimum 14, larger sizes retained | Unit boundary checks pass; retain reader browser verification. |
| READ-03 | Nested TOC/search/navigation/bookmarks/highlights/quotes | Implemented: core reader and persistent exact text bookmarks | Existing structural/text CFIs restore; new bookmarks verify the exact stored passage after font/viewport changes. Image-only fallback is explicitly approximate. |
| READ-04 | Legacy CFI/fragment locations | Implemented for structural/text/element/spatial/temporal CFI and fragments | Image/video geometry, verified audio/video seek and missing-fragment regressions; bounded identity/offset checks. Unresolvable originals remain intact with a bilingual notice. |
| NOTE-01 | Four tabs/search/color/grouping, NotesPage | Implemented: four views, search/color/counts/grouping | API regression and four-platform browser workflow pass. |
| NOTE-02 | Recolor/edit/delete notes and quotes | Implemented: note edit/delete/recolor/kind | Stale edits rejected; source selections and text preserved. |
| SRC-01 | Catalog fetch and full/bounded collection | Verified Fetch All/Fetch Pages | Durable progress and ordinary control actions. |
| SRC-02 | Single/selected/all book creation | Verified | Canonical URL identity, no title-only merging. |
| SRC-03 | Main site unfinished category | Implemented: unfinished source scope and automatic changed-edition rebuild | Daily 02:00 Dhaka checks record updates; normal verified editions stay live during replacement. |
| SRC-04 | Multi-page contents list/diagnostics/regenerate | Implemented: multi-page/nested/complex diagnostics | Exact retained snapshot proof, bounded layout summary, filtering and safe backfill for historical jobs. |
| SRC-05 | On-hold/failed bulk retry/pause/resume/recreate | Implemented: revision-pinned bulk pause/resume/cancel/retry/recreate/archive | Individual outcomes, idempotent receipt, book revisions, permission checks and reversible archival; unchanged defects cannot bypass the code gate. |
| SRC-06 | Reprocessing active/history views, ReprocessingPage | Implemented: searchable active/history/recovery views | Type/error/verification/layout/book/batch/schedule filters, saved queue views and related-job links. |
| SRC-07 | Automated curation and incomplete update schedule | Implemented: unfinished scope and rebuild policy | Daily 02:00 Dhaka maintenance installed; idempotence tested. |
| SRC-08 | Source/body/export verification | Implemented: reading classification, edition/page/component proof, quarantine | Latest 1,585-publication audit verified 1,584 and identified one older partial compilation for ordinary regeneration. Linked collections now require complete independently verified components; all text/export checks remain enabled. |
| SRC-09 | Retry/checkpoint/restart | Implemented: availability pacing and code-version defect recovery | Retry-After, host circuit breaker, preserved good source pages and selective derived-file rebuild; unchanged repeatable defects held until relevant code changes. |
| SRC-10 | Changed queued source metadata | Implemented for queued, unlinked source operations | Metadata rebase preserves attempt history and invalidates old document state. |
| SRC-11 | Worker recovery/execution | Implemented: bounded fair dispatch and collection continuations | Ten-page/30-second slices, bounded outstanding generations, stale-message fencing and configurable processing queue; code/validator repairs retain their recovery turn; mail delivery outcomes unchanged. |
| ACC-01 | Login/logout/profile/photo/password/TOTP/reset/invite | Verified | Conditional TOTP; preserve private sessions. |
| ACC-02 | Scoped permissions/read once/expiry/revocation | Verified single-grant paths | Keep access boundaries throughout replacements and quarantine. |
| ACC-03 | Multi-target/multi-scope grant creation | Implemented: multi-target and multi-scope grants | Bounded idempotent commands with per-item created/existing/rejected outcomes and explicit Dhaka expiry controls. |
| KIND-01 | Recipient/send/status/resend | Implemented: send/status/history and explicit resend composer | Owner/current-access checks; only still-allowed former recipients selected; uncertain outcomes explained; resend never auto-submits. |
| KIND-02 | Kindle sent list filters/sorts | Implemented: Kindle history filters and six stable sorts | Compact title/state/sort controls and optional contributor/category/series conditions with owner-bound cursors. Website type/request-date filters were removed at the user’s request; API validation remains compatible. |
| UX-01 | Feedback/toasts and notification sounds, useToast/notificationAudio | Implemented: shared accessible feedback and optional sounds | Profile completion uses one live notification; inline validation retained; sound defaults off, explicit opt-in, browser-local persistence and no autoplay. |
| UX-02 | Previous layout/theme | Intentionally changed; sitewide layout and interaction review implemented | Six-section admin shell and phone drawer; four-destination reader navigation and phone bottom tabs; combined logo, same-account Reader View, compact filters, Notes views, actual processing states, numbered pagination, direct schedule/account controls and both languages. See the sitewide UI review; subjective design acceptance remains the user’s decision. |
| UX-03 | Old routes/book links | Implemented: validated legacy aliases | Library/role/physical/Kindle/admin/source/reader equivalents; unsafe redirects ignored and target authorization preserved. |
| OPS-01 | Health/recovery/backup/install | Simulator verified | Re-run changed deployment paths; actual external acceptance unverified. |
| OPS-02 | Production delivery | Unverified externally | Keep delivery off; local mail sink only. |
| QA-01 | Code quality/dependencies | Code checks passing; five development-only npm audit highs remain | Retained collector lint findings fixed. Upstream framework lint dependency constraints recorded; no forced incompatible downgrade or weakened lint. |
| QA-02 | Original editorial approval/unsafe bypass/history deletion | Intentionally changed | No review gate, fabricated text, unsafe source bypass or hard deletion. |

## Evidence and boundaries

Baseline frontend evidence is rooted at `app/frontend/src` in the pinned commit;
current surfaces are under `app/web/src`. Baseline API inventory comes from the
six Django app URL modules, including API-only catalog export/ticket support.
Implemented rows describe the delivered capability; any partial or unsupported boundary remains explicit. They are not an overall parity percentage.

Earlier acceptance evidence — before the second audit:

- Full backend/tools gate: **1,675 passed**, 13 live checks excluded, warnings
  treated as errors (`parity-final-backend.log`). The subsequent bookmark change
  passed **45 focused access checks**, including 18 new input/chapter regressions.
  Those focused checks overlap the broad gate and are not added to its total.
- **105 web units**, production build, ESLint, strict generated TypeScript/API,
  mypy on **259 files**, affected Python lint and repository policies pass.
- Reader: **24 journeys each** in Chromium/WebKit/Android/iOS, plus four newest
  cases in pinned Linux Firefox. Catalog/admin: **15 journeys each** in Chromium,
  WebKit, Linux Firefox, Android and iOS. The three exact-bookmark cases additionally
  pass in all five profiles (**15 additional project/journey combinations**).
- Source diagnostics/bulk recovery: **seven journeys each** in Chromium, Android
  and iOS. Final mobile runs also verify a real single-line Search button and
  inspect the 390 px screenshot. Four-platform notification and personal-note
  journeys pass. These groups overlap; counts are not added into a completion score.
- Latest dependency audit: **zero production findings** and **five high
  development-only findings** in the upstream lint chain. No audit, lint rule,
  peer check or type check was disabled.

The evidence is scoped to the exercised behaviors. It includes Bengali/English,
keyboard and native controls, 320/390 px layouts, enlarged text and the applicable
browser profiles. The audit does not assert that every possible interaction or
future website layout is free of defects. The final retained-source audit checked
**814 published source operations**, all with positive reading-content verification.
A separate apply pass verified **332 previously unchecked publications** without
changing their catalog revision or deleting history. At the recorded runtime
checkpoint there were **838 verified published books**, six quarantined source
records, 3,286 queued source jobs, one running and 42 automatic retry waits; there
were no failed or attention-required source jobs. Counts change while workers run.
Thousands of source books are still queued; the catalog is not fully processed.

Only simulators are available. Actual Kindle receipt, physical device installation,
production-host deployment and independent-machine capacity remain unverified.
No passwords, private source bodies or session credentials belong in this report.

Persistent spatial/media CFI coordinates now restore supported image/video points
and audio/video timestamps. Original records remain preserved; unavailable codecs,
unsupported geometry and stale identities produce an explicit unresolved-position
notice. DRM, authored scripts and external media remain outside the local EPUB
reader's supported format and isolation boundary.
Direct Bengali PDF output requires text shaping support; Linux rendering passed,
and hosts without it retain the full filtered browser print/Save as PDF route.

The final upload journeys passed in all five profiles. An earlier WebKit run
missed an invalid-upload alert once; 17 diagnostic attempts and final project
runs did not reproduce it. The page's unconditional smooth scrolling was removed
after diagnostics showed continuing page movement during form interaction. This
reduces a demonstrated interaction risk, but does not establish the one-off
failure's exact cause. The regression now verifies the actual HTTP 400 response
as well as the visible validation message. Keep this observation if it recurs.

Verification artifacts are under ignored `test-artifacts/foundation/`:
`parity-final-backend.log`, `final-bookmark-text-backend.log`,
`parity-final-web-{unit,lint}.log`, `parity-final-{build,types,mypy,schema,migrations}.log`,
`parity-final-admin-{chromium,webkit,android,ios}.log`, `final-admin-firefox.log`,
`final-reader-matrix-*.log`, `final-reader-new-firefox.log`,
`final-bookmark-precision-*.log`, `source-controls-*-final.log`,
`parity-final-publication-audit*.jsonl` and `parity-final-runtime-counts.log`.
Fixture files contain private test credentials and must not be published.
