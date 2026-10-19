# Application completeness audit — 19 October 2026

Baseline: `main@08fc99f9d59221072404b1af4ab501dfc3fd269e`.
Target: `reyan-new-version`, including the current working tree. The retained
frontend differs from the baseline in 13 files; it is supporting evidence only.
This is a capability audit, not an overall completion percentage. “Verified”
means recorded automated evidence; it does not promise zero bugs or design acceptance.

## Inventory and repair register

| ID | Previous behavior/evidence | Current surface/status | Repair and acceptance |
| --- | --- | --- | --- |
| CAT-01 | Home/Library search, `pages/HomePage.jsx`, `LibraryPage.jsx` | `/catalog/`, `/manage/books/`: verified search and pagination | Preserve query, permission and language behavior. |
| CAT-02 | Combined contributor/series/category/type/ownership filters, `libraryFilters.js` | Implemented: combined catalog, managed and personal filters | Shareable author/role/category/series/collection/type/ownership URLs; regression and browser checks. |
| CAT-03 | Title/code/creation/request sorting, `libraryFilters.js` | Implemented: title/code/created/added/publisher sorts | Deterministic ties, account/filter-bound cursors and visible selectors; existing default ranking retained. |
| CAT-04 | Saved catalog/queue filters, `SavedFilterStrip.jsx`, common saved-filter API | Implemented: saved catalog and queue filters | Owner-private create/apply/delete; legacy author mapping; strict validated keys and idempotent creation. |
| CAT-05 | CSV/PDF full filtered catalog, `LibraryPage.jsx`, `utils/bookExport` | Implemented: full filtered CSV/PDF/print exports | Scoped all-page exports; formula protection. Bengali/Latin PDF rendered in Linux; host without shaping has explicit failure and print alternative. |
| CAT-06 | Categories/series/writers and role directories, baseline AppRoutes | Implemented: directories, counts, name/count sorting and type/role filters | Counts include visible distinct books only; profile links preserve role and book type. |
| CAT-07 | Card/table browsing and infinite list, baseline BookTable/BookCardGrid | Implemented: card/table choice and pagination | Accessible table headers, related entity links and a contained horizontal scroll region on phones. |
| CAT-08 | Metadata/edition/language/price/binding, baseline BookDetailPage | Verified fields/editing | Retain decimal fidelity, relationships and edition navigation. |
| CAT-09 | Metadata versions/edit notes, BookMetadataWorkspace | Implemented: provenance history and edit notes | Authorized bounded pages, actor names without emails, bilingual labels and Dhaka dates; protected snapshots stay private. |
| PHY-01 | Dedicated physical list, ManualBooksPage | Implemented: dedicated physical inventory | Publisher/binding/language and contributor-role filters, personal scopes and direct manual creation/edit actions. |
| PHY-02 | CSV/PDF/XLSX with grouping, ManualBooksPage/bookExport/excel | Implemented: scoped CSV/PDF/print/XLSX | Grouped multi-sheet XLSX, decimal values, safe cell text and complete filtered results. |
| LIB-01 | Add/remove My Books, CreatedBooksPage/useMyBooksAction | Verified, improved combined feed | Preserve ownership versus saved-book distinctions. |
| LIB-02 | My Books filters and request/title/creation sort | Implemented: combined filters and stable sorts | My Books tabs preserve filters; owned/saved/recent/granted remain distinct. |
| BOOK-01 | Cover, details, Read/HTML/Kindle, BookDetailHero | Verified | Permission-aware actual files; HTML new tab; consistent icons. |
| BOOK-02 | EPUB replace and regenerate, baseline detail hooks | Implemented: atomic source and manual EPUB replacement | Stage and prepare before swapping; current text proof for website uploads; permission/revision rechecks; old bytes/sessions and personal data retained. |
| BOOK-03 | Book-specific notes, progress/location/last-opened | Implemented: last chapter/location, progress and four note views | Proven edition identity only; safe resume or explicit unresolved-place notice without exposing raw CFI. |
| READ-01 | Scroll/page/spread, fullscreen, gestures, themes | Verified reader controls | Fullscreen book only; preserve passage through reflow. |
| READ-02 | Font size 14–30, reader-settings | Implemented: minimum 14, larger sizes retained | Unit boundary checks pass; retain reader browser verification. |
| READ-03 | Nested TOC/search/navigation/bookmarks/highlights/quotes | Implemented: core reader and persistent exact text bookmarks | Existing structural/text CFIs restore; new bookmarks verify the exact stored passage after font/viewport changes. Image-only fallback is explicitly approximate. |
| READ-04 | Legacy CFI/fragment locations | Implemented for structural/text/element CFI and fragments; unsupported coordinates retained | Image/element geometry and missing-fragment regressions. Spatial/media coordinates and stale identities cannot be invented; originals remain intact. |
| NOTE-01 | Four tabs/search/color/grouping, NotesPage | Implemented: four views, search/color/counts/grouping | API regression and four-platform browser workflow pass. |
| NOTE-02 | Recolor/edit/delete notes and quotes | Implemented: note edit/delete/recolor/kind | Stale edits rejected; source selections and text preserved. |
| SRC-01 | Catalog fetch and full/bounded collection | Verified Fetch All/Fetch Pages | Durable progress and ordinary control actions. |
| SRC-02 | Single/selected/all book creation | Verified | Canonical URL identity, no title-only merging. |
| SRC-03 | Main site unfinished category | Implemented: unfinished source scope and automatic changed-edition rebuild | Daily 02:00 Dhaka checks record updates; normal verified editions stay live during replacement. |
| SRC-04 | Multi-page contents list/diagnostics/regenerate | Implemented: multi-page/nested/complex diagnostics | Exact retained snapshot proof, bounded layout summary, filtering and safe backfill for historical jobs. |
| SRC-05 | On-hold/failed bulk retry/pause/resume/recreate | Implemented: revision-pinned bulk pause/resume/cancel/retry/recreate/archive | Individual outcomes, idempotent receipt, book revisions, permission checks and reversible archival; unchanged defects cannot bypass the code gate. |
| SRC-06 | Reprocessing active/history views, ReprocessingPage | Implemented: searchable active/history/recovery views | Type/error/verification/layout/book/batch/schedule filters, saved queue views and related-job links. |
| SRC-07 | Automated curation and incomplete update schedule | Implemented: unfinished scope and rebuild policy | Daily 02:00 Dhaka maintenance installed; idempotence tested. |
| SRC-08 | Source/body/export verification | Implemented: reading classification, edition/page proof, quarantine | Initial 344-book audit quarantined six description-only publications and retained six legitimate short/line-break works. Final 814-publication audit passed; 332 previously unchecked records marked verified. |
| SRC-09 | Retry/checkpoint/restart | Implemented: availability pacing and code-version defect recovery | Retry-After, host circuit breaker, preserved good source pages and selective derived-file rebuild; unchanged repeatable defects held until relevant code changes. |
| SRC-10 | Changed queued source metadata | Implemented for queued, unlinked source operations | Metadata rebase preserves attempt history and invalidates old document state. |
| SRC-11 | Worker recovery/execution | Implemented: bounded fair dispatch and collection continuations | Ten-page/30-second slices, bounded outstanding generations, stale-message fencing; mail delivery outcomes unchanged. |
| ACC-01 | Login/logout/profile/photo/password/TOTP/reset/invite | Verified | Conditional TOTP; preserve private sessions. |
| ACC-02 | Scoped permissions/read once/expiry/revocation | Verified single-grant paths | Keep access boundaries throughout replacements and quarantine. |
| ACC-03 | Multi-target/multi-scope grant creation | Implemented: multi-target and multi-scope grants | Bounded idempotent commands with per-item created/existing/rejected outcomes and explicit Dhaka expiry controls. |
| KIND-01 | Recipient/send/status/resend | Implemented: send/status/history and explicit resend composer | Owner/current-access checks; only still-allowed former recipients selected; uncertain outcomes explained; resend never auto-submits. |
| KIND-02 | Kindle sent list filters/sorts | Implemented: Kindle history filters and six stable sorts | Title/contributor/category/series/type/state/Dhaka-date filters and owner-bound cursors. |
| UX-01 | Feedback/toasts and notification sounds, useToast/notificationAudio | Implemented: shared accessible feedback and optional sounds | Profile completion uses one live notification; inline validation retained; sound defaults off, explicit opt-in, browser-local persistence and no autoplay. |
| UX-02 | Previous layout/theme | Intentionally not retained | Fresh coherent UI; visible main actions; bilingual; no decorative underlines. |
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

Current recorded checks:

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

Persistent spatial/media CFI coordinates remain unsupported and unchanged. The
pinned baseline parser also discarded those coordinates, so this is a supported
format boundary rather than a newly lost coordinate-restoration capability.
Legacy records are preserved and unresolved positions are reported explicitly.
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
