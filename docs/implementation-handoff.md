# Implementation handoff — 19 October 2026

## Current implementation — 19 October 2026

The accepted specification is [implementation-repair-plan.md](implementation-repair-plan.md).
The baseline capability register is [operations/feature-parity.md](operations/feature-parity.md),
pinned to `main@08fc99f9d59221072404b1af4ab501dfc3fd269e`. This section supersedes
older runtime and unfinished-work statements below. No zero-bug, subjective design
acceptance or external production-acceptance claim is made.

Implemented in the current working tree:

- Positive reading classification, versioned source/page evidence, quarantine,
  paced availability retries, Retry-After, persisted host circuit breaking,
  code-version defect recovery, safe metadata rebasing and retained checkpoints.
  Ten-page/30-second collection slices and bounded fair dispatch prevent a large
  book or a backlog of old messages from monopolizing the processing worker.
- Source HTML/EPUB and prepared reader resources switch atomically after all
  checks. Ordinary verified editions remain readable during replacement. Manual
  EPUB replacements also stage/prepare before switching; website uploads must
  match the retained reading evidence. Personal data and old bytes are retained.
- Nightly unfinished-source checks run at 02:00 Asia/Dhaka and automatically
  rebuild changed editions. Availability waits remain automatic; internal defects
  retry only after relevant code changes. No manual editorial approval is required.
- Combined catalog/managed/personal filters and stable sorting, owner-private saved
  catalog/queue views, cards/tables, linked author/category/series directories and
  visible counts. Dedicated physical inventory has grouped XLSX/CSV/PDF/print
  exports. All-page exports preserve the actual filtered scope and permissions.
- Metadata history/edit notes, four annotation views with search/colors/grouping,
  multi-target/multi-scope permission grants and per-item results, revision-pinned
  bulk source retry/recreate/archive plus ordinary pause/resume/cancel controls.
- Kindle history filtering/sorting and explicit recipient-checked resend,
  validated legacy routes, optional notification sounds (off by default),
  bilingual feedback and explicit twelve-hour Dhaka dates/inputs.
- Saved-edition provenance, actual last chapter/location summaries, element/image
  CFI restoration and explicit unresolved-position notices. Exact passage anchors
  for newly created bookmarks preserve the passage after reopening with different
  font sizes and viewport widths; changed quotations produce a visible warning.
- Unassigned book catalog numbers can continue beyond the former 4,095-record
  limit without changing existing ten-character codes or URLs. Mobile search
  buttons stay on one line; native anchors/form focus no longer animate globally.

Runtime and preservation:

- Preview: `http://127.0.0.1:3000/`; browser reference proxy: port 3001.
  PostgreSQL/Redis/RabbitMQ retained volumes remain intact. Processing worker,
  dispatcher and scheduler are running; **delivery workers remain off**. Never
  start duplicate processing services or seed test accounts into preview.
- Private backups preceded additive catalog 0027, ingestion 0013/0014 and
  processing 0014 migrations. No earlier migration was edited or data deleted.
- The initial 344-publication audit quarantined six description-only records;
  six legitimate short/line-break works were retained. Automatic source rechecks
  are scheduled. The final audit checked 814 published operations, all verified;
  an apply pass marked 332 older unchecked publications verified. The runtime
  snapshot contains 838 verified published books, six quarantined records, 3,286
  queued source jobs, one running, 42 automatic waits and zero failed/attention jobs.
  Counts are a moving checkpoint, not a catalog-completion claim.
- Recoveries retain attempts, ownership, notes and good source pages. The large
  collection resumed beyond its former aggregate-cache limit; the cache now has
  a separate bounded 2 GiB disk budget, without raising per-response limits.
- Daily unfinished maintenance remains enabled in preview, schedule
  `8d129fce-d557-51c5-bf0c-d26701ae2d21`. Completed source books publish automatically.
  Thousands of queued books are still being processed; implementation completion
  does not mean the entire source catalog has already finished.

Latest verification:

- Full backend/tools: **1,675 passed**, 13 live checks deselected, warnings treated
  as errors (`parity-final-backend.log`). The subsequent bookmark repair passed
  **45 focused access tests**, including 18 new input/chapter cases; these overlap
  the full gate and are not added to its total (`final-bookmark-text-backend.log`).
- **105 web units**, ESLint, production build, strict generated API/TypeScript,
  mypy (**259 source files**), affected Python lint, architecture/file-size policies
  and whitespace checks pass, including the final bookmark changes. Strict schema
  generation has zero warnings; migration consistency reports no changes.
- Reader: **24 journeys each** in Chromium/WebKit/Android/iOS; four newest reader
  cases additionally pass Linux Firefox. Catalog/admin: **15 journeys each** pass
  Chromium/WebKit/Linux Firefox/Android/iOS. Source controls pass seven journeys
  each in Chromium/Android/iOS; the final mobile search screenshot was inspected.
  Three new bookmark journeys pass in all five profiles (15 combinations).
  Evidence stays under ignored `test-artifacts/foundation/`; exact artifact names
  and the earlier intermittent upload observation are in the capability register.

Implementation and planned simulator gates are complete for the inventoried
repair scope. Remaining external verification and supported boundaries are maintained in the capability
register. Only simulators are available. Actual Kindle receipt, physical devices,
production deployment and independent-machine capacity remain unverified. Direct
Bengali PDF generation requires Pillow shaping support (verified in Linux); hosts
without it offer full filtered print/Save as PDF. Five development-only upstream
lint-chain audit highs remain; production dependencies have no reported findings.
Spatial/media CFI coordinates are preserved but unsupported; the pinned baseline
also did not restore their coordinates precisely. Do not describe those records
as corrupt or silently invent an exact passage.

## Previous correction — source failures, unfinished updates and job clarity (18 October 2026)

Latest user requirements: source books must not remain drafts or need per-book
manual review; repair failed creation; identify updated/finished source books;
make job pages readable and explain queued work; display Asia/Dhaka in a 12-hour
clock throughout the site. This correction is implemented and verified below.
Catalog processing is running again. Do not claim zero bugs, subjective design
acceptance or completion of the remaining catalog queue.

Implemented so far:

- Permit the source's public contents-pager nonce only on its exact read-only
  action/context; keep unrelated hosts, credentials, tokens and nonce requests
  blocked. This repairs books with more than one contents page.
- Partition large book checkpoints into separately bounded document/snapshot/
  projection artifacts without raising storage limits. Legacy artifacts remain
  readable. The actual large anthology that hit the old limit has now succeeded.
- Repair malformed numeric entities/control bytes before HTML/EPUB creation.
  Preserve a single-flow book when an introductory heading otherwise consumes
  its complete body. Strict source/file/reader verification remains enabled.
- Source creation/regeneration uses processing rather than editorial-review
  state. An audited recovery service continues old successful preparations through
  normal worker checks; no direct publication bypass was added.
- Canonical source URLs determine identity. Distinct source books with the same
  title now publish without a manual duplicate decision, preserving existing
  metadata and ownership. Canonical URL uniqueness and historical resolution
  controls remain enforced. Manual forms and lifecycle labels no longer request
  draft review.
- Empty source chapter pages enter a six-hour automatic recheck workflow, with
  fresh source collection and no manual approval step. Availability polls do not
  exhaust the ordinary processing-failure allowance.
- Persist source contents signatures and last-checked evidence; catalog refresh
  checks published unfinished books. Expose an Updates Available filter and
  direct update links. When the source removes a book from its unfinished category,
  retain a completion notice until its updated edition is published. Provenance/
  update checks do not rotate catalog revisions or invalidate queued work.
- Job pages show actual workflow steps, queued-earlier count and next-action
  guidance. Technical IDs/checkpoints and attempt history are expandable. Dashboard
  labels no longer present source processing as drafts. Shared timestamps now use
  Asia/Dhaka, Bengali localized day periods and English AM/PM.

Actual preview repairs already completed:

- **91** previously unpublished books finished normal validation and publication;
  `source-repair-pending-results.json` records 91 successes.
- The failed-job repair pass finished **12 successful publications** and **one
  automatic source-availability wait**, recorded in `source-repair-failed-results.json`.
  The waiting book is `হুমায়ূন আহমেদ রচনাবলী ১০`: all four fetched source chapters
  have no body text, and the source REST endpoint returns HTTP 401. Do not invent
  text or claim that external access has been repaired. Its scheduled recheck is
  an ordinary waiting state, not a manual book-review request.
- Other observed failures (pager links, anthology checkpoint size, foreword
  classification and export control characters) now pass on actual books.

Final verification:

- **1,454 backend/tools tests passed**, 13 live tests deselected, warnings treated
  as errors: `source-repair-backend-final.log`. The 816 focused processing/catalog
  tests also pass; these overlap the full suite. An earlier interrupted run's
  bounded-query assertion was updated to permit only the small JSON update
  projection while still rejecting full source payload/book-body selection.
- **58 web units**, production build, ESLint, strict TypeScript, mypy on **225
  files**, versioned OpenAPI validation/generated types, migration consistency,
  architecture/file-size policies and whitespace checks pass. Evidence uses
  `source-repair-*-release.log`, `source-repair-mypy-final.log` and
  `source-repair-openapi-versioned-final.log`.
- **117 distinct browser project/journey combinations** have passing latest
  results: Chromium 43, WebKit 21, Android 16, iPhone 16 and Linux Firefox 21.
  `source-repair-browser-summary.json` records the evidence logs. Initial new-test
  failures were corrected by matching the rendered label punctuation and explicitly
  refreshing an intercepted idle job; all 12 final clarity checks pass. No browser
  case or lint rule was disabled. Firefox uses the approved pinned Docker image;
  the in-app browser still fails to connect.
- Real-data audit confirms all **103 repaired publications** have available HTML
  and EPUB files plus normal automatic-publication evidence:
  `source-repair-publication-audit-final.log` and `source-repair-published-audit.json`.
  The pre-restoration catalog contained 197 published books and no unpublished
  records. Counts continue increasing as the normal queue runs.
- Actual queued-job, dashboard, unfinished-list, source-wait and phone screenshots
  were inspected after restarting the served production build. Reference-only
  update-notice QA confirms the direct update action and Dhaka timestamp. Evidence:
  `source-repair-final-qa.json` and `source-repair-*.png`.

Scoped Python lint/format passes for all 28 corrected modules. The retained large
`book_manifest.py` collector has seven existing Ruff diagnostics, identical before
and after the two-line hook change; see `source-repair-retained-lint-baseline.json`.
No diagnostics were suppressed and no unrelated collector refactor was made.

Runtime: retained PostgreSQL/Redis/RabbitMQ containers, preview API 8000/web 3000,
reference API 8002/web 3002 and proxy 3001 are running. No volumes were reset.
Processing-only Celery, dispatcher and scheduler were restored after regression
and subsequent queued books are publishing. **Delivery workers remain off.**
The normal unfinished-source update scan succeeded and checked the one published
unfinished book (`source-repair-real-updates.log`); uncreated category entries stay
in their normal creation queue. The old interrupted operation
`5c0b8f6a-6c1d-5463-ad51-8cd22424f061` was recovered through stale-attempt services
and resumed through the normal worker. Its new attempt hit a source connection
timeout and scheduled a normal automatic retry; it has not published yet. Evidence:
`source-repair-resume-interrupted.log` and `source-repair-worker-final.log`. The
last work audit had no failed/attention source jobs, two retry waits (this timeout
and the missing-text title), one running job and the remaining queued catalog.
Do not rely on old PIDs or restart duplicate workers.

Preview: http://localhost:3000. Source availability, physical devices, external
Kindle delivery and independent-host acceptance retain their documented limits.
No dependencies, migrations, commit or push were added in this correction.

## Current correction — obsolete dashboard review counter (17 October 2026)

The user found “পর্যালোচনা বাকি” still counting every book after manual review
was removed. The dashboard was counting empty `editorial_reviewed_at` timestamps,
including on published books, and omitting legacy `needs_review` records from its
draft total. The review counter is removed in Bengali and English. Drafts now
include both `draft` and legacy `needs_review`; processing, ready, published and
archived statuses have separate counts. The deprecated API `editorial_pending`
field stays zero for compatibility. No stored book states or files were changed.
Automation guidance also describes automatic publication after successful checks.

Verification: **13 focused backend tests**, **57 web units**, **15 overview browser
journeys** across Chromium, WebKit and Linux Firefox, including phone/no-JavaScript
and bilingual cases. Production build, ESLint, strict TypeScript, mypy (221 files),
affected Ruff/format checks, OpenAPI validation/generated contracts, file-size and
architecture policies, and whitespace checks passed. Evidence is
`test-artifacts/foundation/overview-review-*.log`. The restarted preview returned
HTTP 200; actual dashboard counts reconciled, with no review counter, and its
screenshot was visually inspected (`overview-review-dashboard.png`). Processing
continues normally, so live totals change as new books publish. Delivery workers
remain off; no dependencies, migrations, commit or push were added.

## Active correction — original workflows and reader UX (17 October 2026)

The corrections below are implemented and have passed the recorded checks. The
user rejected the earlier parity claim; subjective design acceptance and a
zero-bug guarantee must not be inferred from automated verification. Older
checkpoints below are historical and are superseded by this section.

Latest explicit requirements:

- Show real author/category/series/collection lists immediately, with links to
  their books. Make All Books easy to reach from public/personal pages, with
  actual covers/authors and search. Kindle and My Notes need consistent icons.
- Expose Add to My Books on book actions; the default personal list must include
  saved books and reading history rather than opening an unrelated empty owned list.
- Remove manual editorial approval from book/entity workflows. On 17 October the
  user explicitly chose **automatic publication after successful source checks**.
  Keep validation, permissions, stale revisions and source/file safety checks.
- Automatically compare available source pages/chapters and generated HTML/EPUB
  text. A missing/broken app export is an application defect, not a source category.
- Restore the source website's **Unfinished Books** category as its own list and
  catalog refresh. Keep it distinct from failed jobs or missing collected chapters.
- Fullscreen reading must show **only the book**: no control toggle, exit button,
  page bar or save-status text. Use Escape/double-tap to exit. Compare the retained
  reader and verify actual `দস্যু বনহুর সমগ্র ৪`, not just synthetic short fixtures.

Implemented corrections include direct entity lists/role filters and related books;
public author/category/series directories; visible All Books navigation/cards;
Add/Remove from My Books with the combined default feed; review-free saved
metadata/publication; the source unfinished category; strict source/text/export
verification and automatic publishing with stop/replay guards. Reader controls
are grouped into settings; fullscreen/focus shows only book content, including
when an app update is waiting. Escape/double-tap exits. Appearance changes retain
the passage across page reflow; generated chapter wrappers no longer add a second
40px reader margin. Mobile navigation wraps at enlarged text sizes. Search fields
and author lists use the shared visual system, with consistent action icons.

Passing backend evidence is `catalog-repair-backend-release.log`: **1,437 passed,
13 live tests deselected**, with warnings treated as errors. The final publication
guards also passed **312 focused cases** in
`catalog-repair-backend-final-verified.log`; these overlap the full suite and are
not an additional 312 distinct tests. Current web units pass **56**, retained
frontend units **154**; mypy passes **221 files**. Production build, ESLint,
strict TypeScript, versioned OpenAPI/generation, migration consistency, affected
Python lint and architecture/file-size policies pass.

The broad browser matrix passed **333 journeys**: 169 Chromium, 123 across
WebKit/Android/iPhone and 41 Linux Firefox. Evidence is
`catalog-repair-browser-final.log`, `catalog-repair-browser-platforms-final.log`
and `catalog-repair-browser-firefox-verified.log`. The final visual refinements
also passed **25 layout rechecks** in `catalog-repair-browser-layout-final.log`
and `catalog-repair-browser-layout-firefox.log`. The final served build passed
**31 additional checks** for bilingual feedback, directories, personal-book
actions and manual creation: `catalog-repair-browser-delivery.log` (10),
`catalog-repair-browser-directories-delivery.log` (12),
`catalog-repair-browser-firefox-delivery.log` (6) and
`catalog-repair-browser-creation-delivery.log` (3). These repeated checks are not
separate feature-coverage claims.

Actual regeneration **72f2c41b-d286-45d0-b380-44d5addf7cad** (দস্যু বনহুর সমগ্র ৪)
and **855d5f7c-28c1-49f6-9f77-900e60445aaf** (Devdas) both succeeded and published
through automatic source/export/reader checks, with no manual review. Source
unfinished discovery **b0726b5c-3428-40ba-a544-05842c2e36ce** succeeded and the
separate list contains **60 source-marked entries**. Evidence uses
`catalog-repair-real-execution.log` and `catalog-repair-verified-content-final.*`.
The actual reader's 20 contents entries, 112,503-character chapter and full-viewport
fullscreen with zero visible buttons were checked; screenshots are
`catalog-repair-reader-*.png`. Preview source processing, dispatcher and scheduler
are restored. Delivery workers remain off.

The first complete run had environment errors (engine Redis address and inherited
source fallback settings); deterministic isolation and explicit local Redis
corrected them. Browser runs exposed duplicate/old labels, enlarged navigation
width, reader reflow and the fullscreen update notice, all fixed. The reader test
now uses the reference web proxy instead of a redundant broad route interception
that raced reload cancellation. Source browser fixtures now include actual
HTML and cover files in the reference database, in addition to their EPUB. This
prevents file tests from selecting arbitrary unrelated or EPUB-only records.
Private synthetic fixtures must never enter `bangla_library_preview`. Repeated
reference seeding exposed catalog sequence exhaustion: allocation now reuses an
available slot after the monotonic range is exhausted, retaining the existing
code format, locking and explicit failure when every slot is occupied. Reference
seeding now synchronizes codes after adding relationships; 200 existing synthetic
reference records were corrected through the same service without deleting data.

Legacy sourced records without processing evidence cannot bypass automatic
verification through manual publication; manually added records without a source
retain direct publication. Blocked publication displays the specific next step
in Bengali and English rather than a misleading stale-edit message. Only known
source-check messages are displayed; arbitrary server diagnostics stay hidden.
The TypeScript unit harness now uses the application's ES2022 target so native
Error subclasses behave as they do in production.

The completed build is served at http://localhost:3000/; the direct admin book
list is http://localhost:3000/manage/books/. Preview APIs and reference services
were restarted and returned HTTP 200. Actual admin/author/catalog/unfinished
pages and phone/reader screenshots were visually inspected. Real covers loaded,
HTML opened a new tab, and Read, Kindle and Add to My Books actions were present.
Final live-page evidence is `catalog-repair-final-qa-delivery.log` and
`catalog-repair-final-*.png`. Several earlier interrupted/failed logs remain under
`catalog-repair-*`; use only passing final evidence in completion claims. In-app
Browser still fails bootstrap (`missing sandboxPolicy`); approved Playwright and
its pinned Linux Firefox simulator are the fallback.

Only simulators are available. Physical devices, external Kindle arrival,
independent-machine capacity and a fresh staging host remain unverified. No
dependency or migration was added during these corrections; delivery workers
remain off. No commit or push was requested.

Product Design installation was offered; no connection was confirmed, so it is
skipped. No additional plugin is required to keep implementing the application.

## Current checkpoint — retained reader features and final verification (17 October 2026)

The identified original-app gaps are implemented: regeneration/removal controls,
nested EPUB 3/NCX contents, pinch/tap reader gestures, and supported original
text-CFI bookmarks/highlights and package-relative reading locations. Existing
notes remain intact when an edition no longer matches; the reader reports an
unresolvable position rather than selecting unrelated text. Unicode offsets,
escaped CFI assertions and quotations are checked before restoring a selection.
See [the feature comparison and acceptance limits](operations/feature-parity.md).

Older prepared books remain readable. Their managed EPUB exposes **Update Reader
Files** to add navigation/spine metadata explicitly, with processing overlap and
revision checks. Reader safety preparation stays version **1**; only the new
manifest metadata is version **2**. Do not invalidate existing safe reader files
by conflating those versions. No dependency or migration was added in this
continuation, and no test, lint rule or type check was weakened.

Final verification passed:

- **1,401 backend/tools tests**, with warnings treated as errors; 13 live-source
  tests were deselected for this simulator-only acceptance.
- **51 current web units** and **154 retained frontend units**.
- **323 browser journeys**: 143 broad Chromium journeys, 80 additional
  reader/lifecycle journeys across WebKit, Android, iPhone and Linux Firefox,
  and 100 admin/product journeys across all five profiles.
- Production build, ESLint, strict TypeScript, mypy (214 configured files),
  OpenAPI validation with `--fail-on-warn`, generated contract consistency,
  migration consistency, affected Ruff/formatting, architecture/file-size
  policies and `git diff --check`.

Passing evidence is ignored under `test-artifacts/foundation/`:
`reader-legacy-backend-verified.log`, `reader-legacy-browser-final.log`,
`reader-legacy-platforms-final.log`, `reader-legacy-platform-firefox-final.log`,
`reader-legacy-product.log`, `reader-legacy-product-firefox.log`,
`reader-legacy-build-verified.log`, and the `reader-legacy-*-verified.log`
type/lint checks. Earlier failed runs remain available; some exposed regressions
that were fixed, and the last broad-run setup errors were corrected by pointing
at reference API 8002 and waiting for HTTP readiness before running the suite.

Actual Devdas reader update `d7e60e1d-3fdb-4ab0-83ac-c8336b58fa8d` completed
on its first attempt: manifest version 2, 20 contents entries and 20 spine
resources. Its real cover and 9,887-character first body chapter were checked on
desktop and phone, with no horizontal overflow. Screenshots of book actions,
contents, two-page reading and Bengali immersive reading were visually inspected.
The book remains `needs_review` and unapproved. Evidence:
`reader-legacy-real-update-evidence.json`,
`reader-legacy-real-evidence.json`, and `reader-legacy-real-*.png`.

Preview remains http://localhost:3000/ with API 8000 / `bangla_library_preview`.
Reference web 3001 proxies Next 3002 / API 8002 / `bangla_library`; synthetic
fixtures stay restricted to that reference database. Preview processing-only
worker, dispatcher and scheduler are restored; the worker answered `pong` and
preview readiness/login returned HTTP 200. Delivery workers remain stopped.
Inspect current processes rather than relying on historical PIDs. Pause the
preview worker before another complete Redis/engine test run.

The existing Browser plugin and approved Playwright 1.64.0 installation were
used; no additional plugin was installed. The in-app browser bootstrap still
fails with `missing sandboxPolicy`, so repository Playwright and the documented
pinned Firefox container provide the browser evidence. Only simulators are
available. Physical devices, external Kindle arrival, independent-machine
capacity and a fresh staging host remain unverified. Passing checks establish
the tested behavior; they do not establish subjective design acceptance or a
zero-bug guarantee.

## Current checkpoint — book regeneration and removal (17 October 2026)

The current managed editor now exposes bilingual Regenerate Book and Remove Book
controls before files and metadata. Regeneration reuses source-processing jobs,
pins actor/source/book revisions, preserves edited metadata, personal records,
old assets and prepared sessions, and returns the book to review. Explicit retry
and preparation recovery retain completed content/exports. Removal retains data
and files while blocking catalog/reader access. No existing preview book was
removed. See [the contracts and recovery rules](architecture/catalog-records.md#regeneration-and-removal).

Fixed the controls' inconsistent timezone serialization, a translation collision
with the catalog heading, keyboard focus after confirmation, cramped enlarged-text
navigation/dialog headings, and stale capabilities after saving metadata. Added
concurrent-request, scope/revocation, stale-input, uncertain-response, retention,
embedded-cover and preparation-recovery regressions. No dependency or migration
was added; OpenAPI/TypeScript were generated using the documented tooling.

Verification: the full backend/tools run passed **1,383 tests**, with warnings as
errors and 13 live tests deselected. The final focused run passed **29 tests**,
including two final regressions added after the full run was collected. Current
web units passed **42 tests**. The production build, lint, strict TypeScript,
mypy (213 files), OpenAPI validation with `--fail-on-warn`, migration consistency,
Ruff/formatting, architecture/size policies and `git diff --check` passed.
The final broad Chromium run passed **139 journeys**; the new controls passed
another **20 journeys** across WebKit, Android/iPhone simulators and Linux Firefox.
Dialog/mobile screenshots were inspected. Logs use the `lifecycle-*` prefix under
ignored `test-artifacts/foundation/`. Earlier failed runs are retained as evidence;
use `lifecycle-browser-verified.log`, `lifecycle-browser-matrix-restored.log`,
`lifecycle-browser-matrix-firefox-restored.log`, `lifecycle-backend-complete.log`
and `lifecycle-backend-release.log` for the passing final results.

Actual Devdas regeneration operation `25388629-d6ab-4fb6-8dc6-c6cdebd5e82d`
completed on its first attempt: 20 prepared spine resources, a 140,712-byte EPUB,
the real cover embedded in that EPUB, all resources present, and one before/after
content snapshot. The book remains `needs_review`, without editorial approval;
it was not published. Evidence: `lifecycle-real-regeneration-evidence.json`.
The short Shakespeare draft remains flagged and was not regenerated/published.

The host simulator stopped after the successful Chromium run. Colima was restarted
with its existing disk, and only retained foundation PostgreSQL/Redis and the
preview broker containers were started. Preview/reference servers were restored;
the data and completed regeneration survived. The other four browser profiles
then passed their final control checks. Delivery workers remain stopped. Inspect
current listeners/processes before restoring processing/dispatcher/scheduler;
the pre-restart process identifiers are stale. Preview is still port 3000 with
`bangla_library_preview`; reference port 3001 proxies 3002/8002 with `bangla_library`.
The in-app browser still fails bootstrap (`missing sandboxPolicy`); approved
repository Playwright and the pinned Firefox container were used.

Continue the [remaining reader parity work](operations/feature-parity.md). Complete
legacy parity and zero bugs are not established; do not claim either.

## Current checkpoint — reader, covers and feature comparison (17 October 2026)

The user requested confirmation of complete original-app feature parity, better
UI/UX and no bugs. That confirmation is **not established**. Continue from
[the explicit comparison and remaining work](operations/feature-parity.md);
automated passing results are not subjective design acceptance or a zero-bug
guarantee. This checkpoint supersedes earlier reader/cover and verification notes.

Implemented and checked:

- Public/private book details, source results and managed editors share permitted
  Read/Continue, Open HTML and Send to Kindle actions. Missing original EPUB bytes
  hide download/delivery while an existing prepared publication remains readable.
  The Kindle composer retains explicit recipients; opening it does not send mail.
- Real JPEG/PNG/WebP covers use protected delivery with draft/public authorization
  and title/author fallbacks. Cover-only CDN downloads use a fresh cookie-free,
  bounded transport and do not extend the host policy for book/chapter content.
  Recovered the actual covers for the two existing preview drafts without
  replacing exported EPUB/HTML bytes or changing publication/editorial status.
- The EPUB reader has scroll/single/spread views, text resizing, font/theme/line
  spacing/width preferences, contents, full-book inert-text search, page/chapter
  navigation, keyboard/swipe handling and immersive fullscreen/focus. Restored
  the original Ctrl/Command theme/text shortcuts with form/dialog exclusions.
  Live font/view/viewport changes preserve the visible passage. Native fullscreen
  uses the document root so app-update notices stay visible.
- WebKit parent-owned chapter keyboard handlers now work with the iframe and
  resource sandbox. Explicit `script-src 'none'` continues to block authored
  scripts, inline event handlers and JavaScript URLs; injected browser probes
  verify this boundary. Chapter resources remain account/session protected.
- Electronic-book details show personal reading percentage, last opening and
  book-specific notes through the shared note workspace. API filters bind signed
  cursors to account, annotation kind and book; another account's notes/progress
  are never included. The new notes regression uses its own account, preserving
  the reading fixtures' initial positions across browser profiles.
- Fixed hidden PWA prompts by rendering updates outside the hidden admin/reader
  footer; updates still wait for unfinished work and save the current position.
  Fixed the initial session-response race, stale source status after job creation,
  and overflowing catalog codes at 320px with 200% text.
- Closed EPUB cover handles and database connections owned by legacy engine
  threads. Shutdown signals/joins those threads. Retained stream tests now
  consume their files, and processing API fixtures explicitly restore their own
  default rows after transactional test cleanup. Warnings remain errors.
- Updated stale browser labels/selectors while preserving the actual workflows.
  Upload tests use a unique valid ZIP comment so cached preparation cannot hide
  the preparation workflow. Tests still exercise conflicts, uncertain writes,
  permissions, actual bytes, CSP, failure retries and draft preservation.

Current-build browser verification: **282 journeys passed** — 134 broad Chromium
journeys, 11 reader/detail journeys in each of the other four profiles, 20
admin/result journeys in all five profiles, and four additional reader-update
journeys. Profiles are Chromium, WebKit, Linux Firefox, Android and iPhone
simulators. **41 current web units and 154 retained frontend units** passed.
Production build, ESLint, strict TypeScript, mypy (210 configured files), affected
Ruff/formatting, migration consistency and architecture/file-size checks passed.
The versioned OpenAPI contract passed validation with `--fail-on-warn`; OpenAPI
and TypeScript files were generated using the documented tools.

The final full backend/tools run passed **1,361 tests**, with warnings treated as
errors; **13 live-source tests were deselected** because this acceptance uses
simulators. The log is `reader-parity-backend-verified.log`. No test, lint rule or
type check was weakened. The initial full run exposed retained resource leaks
and a physical-book response assertion that needed the two new nullable summary
fields; both were corrected before this clean run.

Actual Devdas visual checks opened 20 spine resources, inspected the first body
chapter (9,887 visible characters), confirmed the real cover and found no
horizontal overflow. Immersive reading occupied 870/1,000px on desktop and
722/844px on phone. Phone/desktop screenshots were visually inspected. The short
Shakespeare draft remains flagged at 0 source chapters / 524 characters; file
generation is not certification that the source supplied a complete book.

Evidence is ignored under `test-artifacts/foundation/`: `reader-parity-*-verified.log`,
`reader-parity-product-release.log`, `reader-parity-build-release.log`,
`reader-parity-unit-release.log`, `reader-parity-legacy-units.log`,
`reader-parity-final-real-evidence.json`, and `reader-parity-final-*.png`.
The in-app browser bootstrap still fails with `missing sandboxPolicy`; the
approved repository Playwright runner and pinned Firefox container were used.
No dependencies, subagents, permission grants, commits, fake preview seeds or
publication changes were introduced. Only simulators are available.

Continue at http://localhost:3000/ and `/manage/sources/`. Preview API 8000 uses
**bangla_library_preview**. Reference web 3001 proxies Next3002/API8002 using
**bangla_library**, with synthetic source configuration. Fresh browser fixtures
are restricted to that reference database. Detached preview/reference servers
are running; inspect listeners rather than reusing old PIDs. Delivery workers
remain stopped and no external mail was sent. The preview processing-only worker,
dispatcher and source scheduler were restored after the Redis pub/sub engine
tests finished. The worker answered `pong`; preview liveness/readiness and the
public page returned HTTP 200. Reference services have no workers. Do not run another full
engine test suite alongside the preview worker; pause it first.

## Current checkpoint — reading actions and shared product design (17 October 2026)

The user again rejected the overall interface and specifically reported missing
reading controls and HTML opening as a download. This checkpoint supersedes the
previous design descriptions. The original book detail was opened at 5173 and
its hero/action implementation compared. Do not claim subjective design
acceptance, original-feature parity or production deployment from these checks.

Implemented:

- Consolidated the shared visual foundation across public pages, account forms
  and management: one set of colors, surfaces, type sizing, control sizes and
  responsive spacing. Branding/header/footer rules live in `branding.css`,
  shared foundations in `globals.css`, public/account layouts in `product.css`
  and admin-specific layouts in `admin-console.css`. Replaced conflicting
  earlier presentation rules instead of appending another general override.
- Public navigation shows its active section. Workspace links have consistent
  icons and visible labels. The home page has functional shortcuts to books,
  notes and browsing. Empty published catalogs are stated accurately; no fake
  books were added or drafts published to fill the page.
- Public cards and details use reusable title/author covers. Book details put
  reading actions above facts and descriptions. Phone details keep a compact
  cover beside the title and full-width actions below, rather than pushing the
  reading button beneath a large cover. Profile and login forms share the same
  form styling, and all existing Bengali/English behavior remains available.
- Source results show the book, author, editorial state and editing/job links.
  Shared **Read Book / Continue Reading** and **Open HTML** controls appear
  above generated files on source results and the book editor. Public book
  details use those same controls. EPUB/HTML attachment downloads remain
  separate. Physical book editors omit the electronic-file section.
- Added `/api/v1/reading/books/<slug>/html/`: authenticated inline HTML,
  existing preview permission, existing serialized read-once consumption,
  private/no-store/noindex headers, script/form/network restrictions, protected
  Nginx storage delivery and development streaming. Access metadata offers
  `html_url` only for an available, permitted HTML file and never consumes an
  opening. Missing/failed/removed files and disabled accounts are denied.
  Processing/download permission alone does not grant HTML preview access.
- HTML links use a separate tab with `noopener noreferrer`; the source/editor
  remains open. Reader actions launch/resume the existing prepared EPUB reader.
  Permissions refresh on public-page refocus and poll in the managed result.
  The actual 16-chapter Devdas book opened in both reader and HTML preview.
  Browser verification found 149,240 visible HTML characters and opened an
  actual chapter in the prepared reader; it does not stop at a cover/title.
  The reading inspection intercepts progress writes to preserve account position.
- All four primary creation actions remain visible on phones. A new regression
  checks that desktop sync/eligible-book/schedule information aligns with its
  corresponding button. The short-text advisory on the Shakespeare sample is
  retained; opening that file is not certification of completeness.

Verification: **76 focused backend tests**, **35 web unit tests**, and **115
browser journeys** passed. Browser checks cover 21 admin/language/result journeys
and two reader/public-detail journeys in each of Chromium, WebKit, Linux Firefox,
Android and iPhone simulators. They open real HTML tabs, inspect book text and
inline headers, open actual prepared reader content, and check permission-denied
states. The final toolbar alignment adjustment passed 55 targeted reruns.
**120 additional layout observations** across 320–1920px, both languages and
200% text reported no horizontal overflow or browser exceptions; published
reference book details were also inspected at four widths in both languages.
The final grouped admin toolbar received another 16 width/language observations
without overflow. The first book row measured about 665px on desktop and
759px/778px on the Bengali/English phone layouts after the completed sync loaded.
Production build, ESLint, TypeScript, mypy (210 files), affected Ruff/format,
migration consistency, architecture/file-size policies and whitespace checks
passed. OpenAPI and TypeScript schemas were generated using their tools; the
unchanged legacy schema warnings/errors remain in the generation log. Full
legacy-suite parity, physical devices and production deployment remain unverified.

Evidence is ignored under `test-artifacts/foundation/`: `redesign-*-final.log`,
`redesign-viewports-final.json`, `redesign-final-measurements.json`, reviewed
`redesign-final-{desktop,phone}-{home,admin,book}-{en,bn}.png` and the original
book-page comparison. Browser bootstrap still fails with `missing sandboxPolicy`;
repository Playwright and the already approved pinned Firefox container were
used. No dependency, subagent, permission grant, commit, publication, fake data
seed or deletion was introduced.

Continue using http://localhost:3000/ and `/manage/sources/`. A chaptered result is
`/manage/sources/90692eaf-0b50-400a-9c7e-35911f6be9c8/`. Preview API 8000 uses
**bangla_library_preview**. Reference API 8002/frontend 3001 and original Vite
5173 retain **bangla_library**. Inspect current listeners rather than relying on
older PIDs below. Existing credentials and background processing are preserved;
delivery workers remain stopped. Only simulators are available.

## Current checkpoint — usable book results and consistent design (17 October 2026)

The user rejected the previous design again and identified two concrete failures:
the source detail displayed EPUB/HTML format names without download controls,
and Bengali dates included English AM/UTC. This checkpoint supersedes the older
layout descriptions below. Do not equate automated checks with user acceptance.

Implemented:

- Public/admin screens share green/neutral colors, control sizing and local
  Noto Sans Bengali assets reused from the existing EPUB fonts. Removed the
  duplicate admin workflow navigation, dark/blue admin styling, large summary
  cards, public sample-book illustration and conflicting old source-card rules.
  The catalog has one compact action toolbar followed by search and book rows.
  Selection actions appear when books are selected. Main actions and all admin
  sections remain visible on phones; no hamburger or disclosure hides them.
- Measured actual preview first-row position improved from approximately
  **932px to 581px on desktop**, and **1,425px to 783px at 390×844**. Both
  languages and 320px/200% text were checked. These are measurements, not a
  claim that the user has accepted the design.
- Source detail is now a book-result page headed by title and editorial state.
  It offers EPUB/HTML downloads, file sizes/availability, distinct online-reader
  preparation state, direct editing/review/publishing and job links. Source URL
  and last-seen information follow the result. Linked books do not repeat the
  creation form. A file already prepared for reading does not offer another
  preparation request. Missing files and denied download access are explicit.
- The book editor exposes generated files before the form and keeps
  save/review/publish controls above its fields. Profiles have section anchors
  and a wider two-column identity/photo layout; section navigation preserves
  unsaved values. The public home leads with book search and published books.
- Added permission-checked `/api/v1/manage/assets/<uuid>/download/`. It requires
  processing authority **and** the existing book download entitlement; a
  processing-only account gains no new file permission. Actual private draft
  EPUB/HTML files stream in development and use protected Nginx redirects in
  production, with attachment filenames, correct MIME, no-store/noindex,
  nosniff and sandbox headers. Disabled accounts, removed books and unavailable
  files are rejected. Asset metadata returns actual availability, supported
  download URL, prepared-reader state and active preparation identifier.
- Source detail returns chapter/character counts without exposing text. A
  chapterless text shorter than 1,000 characters gets an advisory warning
  before the file controls. Counts are detail-only; list SQL remains bounded.
  A longer text is not thereby certified complete. The reported Shakespeare
  sample has **0 chapters / 524 characters** and is visibly flagged. Its actual
  EPUB (**4,455 bytes**) and HTML (**10,734 bytes**) both downloaded with HTTP
  200. The draft and its previous attempts remain intact and unpublished.
- Bengali dates now read like `১৭ অক্টোবর, ২০২৬, ০৩:১৮ (ইউটিসি)` using an
  explicit Bengali numbering system and 24-hour clock. English retains Latin
  digits and UTC. Safari's different default numbering system is covered;
  shared numeric formatting also uses explicit Bengali/Latin digits.

Verification: **65 focused backend tests**, **35 web unit tests**, and **100
focused browser checks** passed: 19 admin/language/result journeys plus one
reader journey in each of Chromium, WebKit, Linux Firefox, Android and iPhone
simulators. The final small layout adjustments received targeted reruns.
The last public-header/result-page build passed another 32 language/result
journeys across Chromium, WebKit, Android and iPhone, and the 43 layout
observations were repeated without overflow. Real
download checks inspect returned MIME/attachment headers and EPUB ZIP bytes.
Missing-file, permission, preparation and short-content paths have regressions.
The expanded backend checks exposed unclosed streams in three existing test
paths; those responses are now consumed/closed while all assertions remain.
Warnings remain errors. No checks were skipped or weakened.

An additional **43 layout observations** covered home/help/catalog/profile/admin
at eight widths from 320–1920px and enlarged text, with no horizontal overflow.
Production build, TypeScript, ESLint, mypy (**210 files**), affected Ruff/format,
migration consistency, architecture/file-size policies and whitespace checks
passed. OpenAPI and TypeScript schemas were generated with their tools; the
existing legacy API serializer/collision warnings remain in the generator log.
The new versioned routes validate and type-check. Full legacy-suite parity,
physical devices, external email and production deployment were not established.

Evidence and reviewed screenshots are ignored under `test-artifacts/foundation/`:
`ux-{backend,build,types,lint,unit,browser,firefox,reader}-final.log`,
`ux-reader-firefox-final.log`, `ux-polish-final.log`, `ux-viewports-final.json`,
`ux-final-evidence.json` and `ux-final-*.png`. The original UI was opened again
at 5173 for comparison and left intact. The in-app browser failed to connect
(`missing sandboxPolicy`); repository Playwright and the approved pinned
Firefox container provided verification. No new dependency, subagent, commit,
push, data deletion, permission grant or publication was performed.

Continue using http://localhost:3000/ and `/manage/sources/`. API 8000 uses
**bangla_library_preview**; reference API 8002 and reader frontend 3001 use the
preserved test database. The original Vite reference runs on 5173. Delivery
workers remain stopped. Inspect active processes before restarting, preserve
existing credentials and do not seed fixtures into the user-facing preview.

## Current checkpoint — whole-site languages and admin controls (17 October 2026)

This checkpoint supersedes the older interface and runtime descriptions below.
The user requires **Bengali and English throughout the new website**, visible
administrative controls, no link underlines, one configured automated book
source, and retained manual EPUB upload. Only simulators are available.

Implemented:

- A shared language switch covers public pages, authentication/recovery,
  personal books/notes, profile/security, Kindle, reader controls and all
  management screens. Authored text, accessible labels, controlled page titles,
  dates, numbers, file-picker labels and supported field-validation messages
  follow the preference. Switching preserves typed values, selected files/books
  and reader settings. The whitelisted `library-language` cookie persists across
  reload/navigation; the old admin cookie remains a compatibility fallback.
  Book titles, author names, chapter text and personal notes remain original
  data. Unknown diagnostic strings remain inspectable. Offline content presents
  both languages without caching account or book responses.
- Administration has a dedicated header, always-visible section navigation,
  compact tables and native dialogs. **Fetch All**, **Process All** and
  **Schedule Automation** are direct controls above the summary panels and
  remain within the initial 390×844 phone viewport. Manual book creation and
  EPUB upload remain available. Link underlines and decorative management
  arrows have been removed; hover/focus feedback remains visible.
- Fetch All follows the catalog through its terminal page. A 2,000-page safety
  ceiling produces a visible failure if pages still remain; it cannot report a
  full scan from a capped result. Bounded fetching remains available.
- Process All queues the entire eligible catalog through a durable
  `process_catalog` parent, rather than the current page or a 100-record browser
  selection. It excludes linked books, active jobs and unresolved failures.
  Batches of 50 pin source revisions and use deterministic child identifiers,
  saved pending work and a UUID cursor. Permission/configuration fencing,
  idempotency, pause/resume and interrupted-attempt recovery remain enforced.
  **Pause Queueing/Stop Queueing** affect remaining dispatch; already queued
  child jobs continue and expose their own controls. Parent success means book
  jobs were queued, not that all children succeeded or were published.
- Schedules select full/bounded catalog fetching and full/bounded/no book
  creation, with first date, local time, IANA zone, frequency and enable control.
  Run history links to the batch parent and counts actual child book jobs.
  Existing schedules retain bounded defaults. Source lists/options/schedules
  poll while visible; failures provide explicit refresh feedback.
- Optional external/unavailable/oversized covers use a generated cover. Their
  original URL remains provenance, never a local export path. Book/chapter
  requests remain restricted to the one configured source and its www alias.
  Generated migration `processing.0013_catalog_batch_controls` adds the batch
  kind/parent relationship, active-batch constraint and automation mode fields.
  OpenAPI and the TypeScript schema were regenerated using their tools.

Verification completed:

- **155 focused backend cases** passed: 83 catalog/discovery/automation cases
  and 72 worker/API/pipeline/recovery/reading cases, including optional external
  covers, a 105-record batch, exclusions, partial rejection, permission changes,
  duplicate prevention and paused recovery.
- **34 web unit tests** and **80 focused browser checks** passed. The latter
  comprise 14 console/usability/site-language checks, one reader-language check
  and one historical-empty-catalog check in each of Chromium, WebKit, Linux
  Firefox, Android and iPhone simulators. Checks cover full-fetch/full-processing
  commands, schedule saving, selection/typed-file retention, validation messages,
  title switching, permissions, lost-response blocking and 320px/200% text.
  Submission tests intercept writes; fake records are not seeded into the
  application preview. Reader checks use the preserved test database on 8002.
- ESLint, strict TypeScript, production build, mypy (208 files), affected Python
  Ruff/formatting, migration consistency, OpenAPI validation, architecture/file
  size policies and whitespace checks passed. Logs and reviewed desktop/phone
  screenshots are under ignored `test-artifacts/foundation/`, with
  `admin-console-*-final.log`, `reader-language-*-final.log`,
  `admin-controls-*-final.log` and `admin-console-final-*.png` names.
- Live Fetch All job `253149fc-fb23-407e-ac8c-b4e88bf31334` succeeded through
  **71 pages / 4,169 encountered listings**, including a recognized terminal
  page. The catalog has over 4,160 distinct real source entries; repeated
  listings and later source changes mean that count differs from encounters.
- Live UI-created **দেবদাস**, job `c8a3575e-d386-447d-9cd9-f14709c52176`,
  succeeded through **17 pages / 16 chapters**, approximately 147,388 body
  characters, a 105,400-byte EPUB and 419,484-byte HTML asset. Both assets are
  ready and the book remains `needs_review`, without automatic publication.
  Sanitized evidence: `admin-controls-live-chaptered-verified.json`.
- The earlier English source sample, job
  `b7393c5d-abad-4099-9142-70f77d3fd405`, succeeded after the cover fix, but its
  source page supplies only a 524-character introduction and no chapter links.
  Its unpublished review draft and attempt history are preserved. Do not count
  that sample as proof of a complete book import or publish it without review.

Current preview: http://localhost:3000/; creation controls:
http://localhost:3000/manage/sources/. The API on 8000, processing-only Celery
worker, dispatcher and source-automation scheduler use **bangla_library_preview**.
The scheduler has no saved preview schedules yet. Delivery workers remain stopped.
API readiness returned 200 and the processing worker replied `pong`. The isolated
reader verification frontend on 3001 uses reference API 8002 and the preserved
**bangla_library** test database. Do not seed the preview, print private runtime
files/fixture credentials, or start delivery workers. Inspect ports/processes
before restarting; older PIDs below are historical.

The in-app browser bootstrap failed with `missing sandboxPolicy`; verification
used the already approved repository Playwright installation. Native macOS
Firefox fails upstream, so Firefox ran in the approved pinned Playwright Docker
image. No dependencies, subagents, commits, pushes, destructive cleanup,
external email delivery or physical-device checks were introduced. The complete
legacy suite and original-app workflow parity are **not established** by these
focused results; do not claim production acceptance from them.

## Catalog sync correction — 17 October 2026

The reported job `e3dfd5b5-bec7-400c-933f-632ea0274f55` fetched a real archive
containing 60 book records, but its parser recognized neither the facet listing
nor the JavaScript pager. It incorrectly completed with zero records. That job
and its saved page remain intact. Discovery now shares text-anchor extraction
with the retained resolver, follows `_paged` queries, and rejects unrecognized,
initially empty, malformed, or repeated pages instead of reporting empty success.
Known empty terminal pages end a scan while preserving prior committed books.
Historical zero-book successes show “No Books Found” with a link to sync again;
populated results link directly to selecting books for creation in both languages.

A fresh authenticated live sync, `2e087f75-4399-4024-90b2-db98f0ee5d9a`, succeeded
in the preview database: 20 pages, 1,200 encountered records, and 1,195 distinct
saved listings. More pages remain beyond the requested limit. This verifies live
catalog discovery; it does not establish full live book-generation acceptance.
Manual upload and the single configured website policy remain available.

Verification: 61 focused backend cases (including 15 archive regressions), 30 web
unit tests, and 40 browser checks across Chromium, WebKit, Linux Firefox, Android,
and iPhone simulators passed. ESLint, TypeScript, mypy (202 files), scoped source
Ruff/format checks, architecture/file-size policies, and the production build
passed. The populated live catalog, working selection controls, old-job warning,
and desktop/phone screenshots were checked directly. These are focused checks;
the entire backend suite was not rerun for this correction. The retained resolver
still has its pre-existing broad-exception lint findings outside the extracted
catalog logic; this change does not suppress them.

## Latest checkpoint — UI comparison and bilingual administration (17 October)

The user rejected the new UI and its awkward Bengali wording. They explicitly
want **both English and Bengali** for administration. Do not equate passing
automated tests with usability or parity with the original application.

The original Vite app was opened and visually compared with the replacement.
It has dedicated Catalog, Create, On Hold, Incomplete, Multi-page TOC and
Reprocessing workflows. The replacement had verbose instructions, scattered
source/job controls, and lists starting below the first screen. Its full parity
with those original workflows is **not established**. Keep the original app.

Implemented and verified in this continuation:

- Administration has an English/Bengali switch. It preserves typed values,
  selected records and native menu state, and remembers its supported preference
  in a cookie used by private server rendering. Translations cover management
  navigation, creation, book/editorial fields, entities, processing, automations,
  users and invitations. Public browsing, the personal profile and reader remain
  Bengali; do not claim application-wide bilingual support.
- The source screen is now a compact creation workspace with catalog sync,
  search/status filters, a selectable table, select-all/clear, one-book creation,
  bulk creation and existing job links. Unavailable sources remain disabled;
  selected snapshots and operation identifiers are retained. The 100-book limit,
  partial outcomes, and uncertain-response replay protection remain enforced.
  Manual entry/EPUB upload remains available. The source provider is still
  configured externally and remains the only automated provider.
- Phone navigation uses a native disclosure. Creation controls remain within
  the first phone screen at normal text size; selection remains usable at 320px
  and 200% text. Without JavaScript the navigation disclosure stays open.
- Overview copy is shorter, wait ages use seconds/minutes/hours/days, processing
  counts link to their filters, and readable issue explanations replace raw codes
  in the overview. Job details retain diagnostic codes.
- The preview now uses a separate **bangla_library_preview** PostgreSQL database
  on the existing localhost 55432 instance. Only the two previously supplied
  administrator/reading-reader accounts and their existing sessions were copied;
  passwords and account security were preserved. It starts with zero books,
  sources and failed/queued jobs. The original **bangla_library** test database
  and all its records remain intact; nothing was deleted. Do not seed fixtures
  into the application preview again.
- The browser fixture guard now requires the exact **bangla_library** name and
  port 55432, and rejects production. Six regressions cover rejection before any
  write and supported port representations. The former port-only check also
  accepted the application preview database and has been fixed.

Verification: **40 focused browser checks** passed (eight each in Chromium,
WebKit, Linux Firefox, Android and iPhone simulators); **29 web unit tests** and
**six fixture-safety tests** passed. Web lint/type checking/production build,
affected Python lint/formatting, architecture/file-size policies and whitespace
checks passed. Browser submission tests intercept writes and do not create fake
records in the preview. Existing UI assertions were updated for the new labels
and table, without removing permission/outcome checks. The complete older suite
was not rerun in this continuation; its previous evidence below is historical.

The original administrator credentials were used for an actual successful login
to the separated preview. Disabled OTP remains absent. Reviewed actual-preview
screenshots: `admin-preview-{en,bn,phone}.png`; sanitized login/count evidence:
`admin-preview-verification.json`. Logs are `admin-usability-{build,browsers,
firefox,unit}-final.log` under ignored `test-artifacts/foundation/`. No live-site
import, physical-device acceptance or external email delivery was established.

Current local runtime:

- New app: http://localhost:3000/, creation: `/manage/sources/`; Next PID 56030.
- Preview API: 8000, PID 50447, using **bangla_library_preview**.
- Original UI/reference: http://localhost:5173/, PID 50584, proxying original API
  8002, PID 50461, using preserved **bangla_library**.
- Preview processing worker PID 50734 and dispatcher PID 50742 use the existing
  preview RabbitMQ project and new database. Delivery workers/schedulers remain stopped. Worker
  control ping returned `pong`, and API readiness returned HTTP 200.
- Ignored `ui-runtime.py`/`ui-runtime.json` now default to the separated preview
  database and disable the legacy engine there. Explicit environment values take
  precedence, allowing the original API to retain its original database/engine.
  Never print these private files or the account/session transfer file.

Inspect processes before restarting. Keep full browser fixture runs on a
dedicated test API/frontend connected to **bangla_library**, not the user-facing
preview. The new focused usability checks can run safely on the preview because
they intercept all submissions. No commits, pushes, destructive cleanup, new
dependencies or subagents were used.

## Latest checkpoint — administration and book creation

The user's latest direction is **one configured website for automated book
creation, plus manual uploads**. Provider names belong in configuration, not
runtime application code. The existing historical migration remains untouched.
Do not reintroduce other provider choices or remove manual entry/upload.

Implemented in this continuation:

- Login initially contains email/password only. The existing authenticated
  `otp_required` response reveals and focuses the security code. Invalid
  credentials do not reveal it; editing credentials clears the challenge;
  invalid codes and temporary failures preserve it. Existing six/eight-digit
  code support and backend checks remain in place.
- Native SVG branding, version-two PWA icons, fresh hashed installation
  previews, and responsive home/login/profile/header styling. Immutable old
  icon and preview files remain available. Account touch controls remain 44px.
- Administrator profiles now expose **পরিচালনায় যান**. Management has direct
  source-import/manual-entry/job shortcuts, visible source workflow steps, and
  current-section navigation. Existing permissions still enforce every entry.
- Automated processing accepts only `SOURCE_SITE_HOST` and its `www` alias.
  An unrelated fallback hostname invalidates configuration. The local preview
  now reads the actual source configuration from the existing ignored local
  environment file, rather than the test placeholder.
- Manual digital records expose EPUB upload in their editor. The new multipart
  versioned endpoint checks archive/manifest safety, a 24 MiB limit, scoped
  metadata access, current revision and unfinished source work. It preserves
  previous files, records an audit, clears review, and grants no ownership.
  The Next proxy permits 32 MiB requests, matching the production proxy ceiling.
  Existing persisted preparation jobs prepare uploaded resources for reading.
- Parallel setup exposed catalog identifier allocation races. Model saves and
  the existing code generators now share a transaction-scoped PostgreSQL lock.
  Four deterministic concurrency cases cover books/authors/categories/series;
  existing codes and their format remain unchanged.
- Local RabbitMQ startup exposed development-only transient queue declarations
  and a legacy Redis factory using an AMQP broker URL. Control queues are now
  durable and event queues exclusive in every environment. Redis state uses a
  Redis configuration independently of the task broker, retaining legacy Redis
  broker support. No deprecated broker feature was enabled.

Current verification:

- **32 Chromium, 32 WebKit, 32 Linux Firefox, 13 Android, 13 iPhone** focused
  journeys passed, including actual enabled TOTP login, invalid challenges,
  administrator/reader navigation, uploads and responsive layouts. Artifacts:
  `ui-{chromium,webkit,android,ios}-final.log` and `ui-firefox-rerun.log` in
  `test-artifacts/foundation/`. Firefox uses the already approved matching image.
- **293 catalog/source/security cases** passed with thread and pytest warnings
  treated as errors (`ui-backend-accepted.log`). The complete non-live audit
  passed **1,289**, with 13 live-network cases excluded
  (`ui-full-backend-final.log` / `.xml`). Its one existing Django URL-field
  deprecation warning remains; no check was weakened.
- **21 web helper tests**, web lint/type checking, final production standalone
  build (`ui-build-accepted.log`), mypy on **201 source files**, affected Python
  lint, migration consistency, file/architecture policies and whitespace pass.
- An actual **11 MiB EPUB** passed the local Next proxy, then completed its
  persisted RabbitMQ preparation job through the local processing worker.
  Reader readiness is recorded in `ui-upload-worker-accepted.json`.
- The user's original administrator credentials still sign in without an OTP
  field and open management/source/manual-entry controls. Accounts were not
  reset or enrolled in two-factor authentication. Final reviewed screenshots
  include `admin-controls-final.png`, `source-controls-final.png` and
  `profile-final-phone.png`.

The local preview is at `http://localhost:3000/`, with administration at
`/manage/`, source import at `/manage/sources/`, and manual entry at
`/manage/books/new/`. Preview RabbitMQ is the separate
`elibrary-preview-broker` Docker project, bound to localhost 5673/15673 with the
approved pinned image. Private runtime configuration/bootstrap and logs are
under ignored `test-artifacts/foundation/ui-*`; never dump their credentials.
API/worker/dispatcher use `ui-runtime.py`, which reads source settings from
`local/env/.env` and broker/Redis settings from private `ui-runtime.json`.
Delivery workers and schedulers remain stopped; no external email was sent.
At handoff, Next3000 is PID 37616, Django8000 PID 39372, processing worker
PID 41094, and dispatcher PID 41095. Inspect listeners/processes before any
restart. The worker answered its RabbitMQ control ping and API readiness returned
HTTP 200. Final runtime logs are `ui-{processing-worker,dispatcher}-final.log`.

The legacy engine integration tests use real Redis. Pause preview processing
while running that suite, or use a separate Redis server. Logical databases do
not isolate [Redis Pub/Sub channels](https://redis.io/docs/latest/develop/pubsub/#database--scoping).
A preview worker heartbeat contaminated the first full run's worker-capacity
assertion and an optional logical-database isolation probe; the clean full rerun
passed with preview processing paused. Never run two pytest processes against
the same automatically managed test database.
The capacity assertion also passed individually with preview processing paused
(`ui-engine-paused-preview.log`); the preview worker/dispatcher were restarted
afterward and remain running.

See `architecture/account-navigation.md`, `architecture/catalog-records.md` and
`architecture/source-processing.md`. Earlier simulator acceptance remains
historical evidence; physical resources and live source acceptance are outside
the user's simulator-only verification scope. No commits/pushes/deployment or
destructive cleanup were performed.

## Previous checkpoint — simulator acceptance

This section supersedes the historical checkpoints below. Continue the user's
full implementation/fix request without repeating already completed work.
No commit, push, production deployment, external email/account action, purchase,
destructive cleanup, or volume reset is authorized. No subagents were used.

Implemented since the entity checkpoint:

- Saved/recent/granted library feeds, revision-checked private paper-reading logs,
  public cross-edition browsing, and private normalized profile images. Generated
  and applied `catalog.0026_personal_reading`; API contracts/types regenerated.
  See `architecture/personal-reading.md`.
- Bengali title/contributor query intent and reviewed Romanized aliases; home
  Organization and collection ItemList JSON-LD match visible content.
- Every remaining application `exec(compile(...))` source loader was replaced
  with normal Python modules. Compatibility exports remain; tests patch actual
  consumers/definitions without removing assertions. Natural processing/seed
  boundaries keep all file-policy targets within 300 lines. See
  `architecture/legacy-imports.md`.
- CSRF rejection retry is limited to one explicit `403 csrf_failed` response,
  which Django rejects before a handler runs. Other/uncertain failures are not
  replayed. Sign-in/out share the mutation helper. A new browser regression
  verifies identical retry payloads.
- Cross-tab session response races, 320px paper forms, WebKit sandboxed reader
  observation, reading-position capture/resize, and dialog focus were fixed.
  Authored reader scripts remain disabled. Safari installation help was added.
- Real worker SIGKILL/lease recovery and duplicate-publication checks passed.
  Isolated HTTPS startup now waits for proxy readiness with a deadline; two
  deterministic regression tests cover startup and timeout.
- Capacity harness fixture/response diagnostics are sanitized; sessions, duration,
  chapter paths and expiry are validated. Public reads explicitly clear reader
  cookies, and reports filter metric fields. Fourteen dependency-free regressions
  cover these paths, both documented summary shapes, and unknown-format failure.
- The guarded k6 runner completed HTTPS simulations at 1, 5, and 20 virtual
  users. Ubuntu/Debian package-install simulations passed after selecting each
  distribution's own repository/key URL and validating OS metadata before apt.
  Accepted-install/standalone/reinstall journeys and browser lab timings were
  added. See `operations/simulator-acceptance.md` for the complete current scope.

Verification already passed:

- Complete non-live backend/tools audit: **1,247 passed**, 13 live source-network
  cases excluded, thread-exception warnings treated as errors. Artifact:
  `test-artifacts/foundation/full-backend-final.log` / `.xml`.
- The latest separate tools run passed **7**, including the two subsequently
  added HTTPS startup cases (`tools-final.log`).
- Capacity harness checks passed **14** with simulated runtime modules
  (`capacity-unit-final.log`), plus syntax and lint. API readiness and the local
  web home both returned HTTP 200 after restarting the development API.
- Latest simulator continuation: **19 tools tests**, **18 performance helper
  tests**, **12 focused installation browser checks**, **33 mail/search cases**,
  and **12 browser timing observations** passed. Three actual k6 HTTPS runs
  and both Linux installer simulations passed. The fresh web helper run passed
  **21**; TypeScript, ESLint and affected source/shell/policy checks also pass.
  Mypy was rerun successfully on all 199 configured source files. Fresh npm
  audits still report zero production and five development-only findings;
  the latest available Next lint patch also retains the unpatched chain.
  Artifacts and measurement limits are in `operations/simulator-acceptance.md`.
- Final clean matrix: **108 Chromium**, **108 WebKit**, **108 Firefox**;
  Android Pixel 7 and iPhone 13 profiles each passed **30** journeys. All use
  the final reader/Safari build and fresh per-project fixtures. Artifacts are
  `matrix-accepted-{chromium,webkit,firefox,android,ios}.log` and
  `matrix-accepted-results.json` under `test-artifacts/foundation/`.
- Progress failures now remain visible while new positions queue, with automatic
  saves paused until explicit recovery. Three focused Firefox repetitions and
  two unit regressions also passed. The catalog creation/status test checks its
  independent status page in a second tab, preserving rendered-content,
  mobile-width, and creator-only permission assertions without waiting for a
  streamed editor response to close.
- **21 web helper tests**, **154 retained frontend unit tests**, both production
  builds, strict TypeScript, ESLint, mypy on **199 configured source files**,
  affected Python lint/format, validated semantically unchanged OpenAPI,
  migration consistency, file-size/architecture policies, and diff whitespace.
- Production npm audit: **0** findings. Development audit: **5 high** findings
  in the lint chain remain unresolved, with no unsafe forced dependency change.
- Synthetic disposable PostgreSQL profile: 10,000 books, twenty samples per
  intent, four SQL queries/request, median 15.65–22.61 ms and p95 24.59–46.10 ms.
  EXPLAIN/BUFFERS JSON is in `test-artifacts/performance/discovery-profile.json`.
  This is not concurrent HTTPS capacity or production corpus relevance.
- Rebuilt Docker API/frontend/proxy passed current HTTPS/public/protected-byte,
  real RabbitMQ preparation, broker/cache failure, broker/API/frontend replacement,
  active preparation SIGKILL/normal lease recovery, one ready publication,
  duplicate replay, and separate-project backup/restore/progress/paused-job
  recovery. Logs: `deployment-platform-current.log`,
  `deployment-recovery-current.log`, `deployment-restore-current.log`,
  `deployment-help-confirm.log`, and the final reader build check
  `deployment-final-verified.log`. See `operations/local-platform-verification.md`.

Approvals persist: Playwright 1.64.0 and matching bundles; temporary ESLint
9.39.4 exception with all lint rules retained; development `types-reportlab` and
`types-qrcode`; approved base images; and Docker installation simulation.
The user's subsequent “do them?” authorizes the documented Grafana k6 2.3.0
image and local acceptance simulations. The user then explicitly required
**simulators only** because physical/staging resources are unavailable. The
pinned image is installed. Actual k6 HTTPS runs at 1, 5, and 20 virtual users
passed with zero failed checks; the 20-user run measured 55.19 requests/second,
public p95 154.17 ms and protected-reading p95 42.50 ms. It used a 47-record
fixture catalog and a shared 2-CPU VM; no production-capacity claim is implied.
Fourteen JS harness regressions, four browser-metric regressions, and twelve new
Python runner/installer checks pass. Ubuntu/Debian package-install simulations
passed with Docker 29.9.1 and Compose 5.6.0; only systemd startup was simulated. See
`operations/capacity-verification.md` for commands, scope, and the image pin.

Running infrastructure:

- Foundation PostgreSQL 55432 / Redis 56379 retain their original volumes.
- Development Django8000 PID 39372 and standalone Next3000 PID 37616 are running.
  Inspect with `lsof` before restarting. Next uses `ui-build-accepted.log`.
  Private logs remain
  under ignored `test-artifacts/foundation/`; never dump credentials/session URLs.
- Production test project `elibrary-platform-test-kjzj4dcz` and restore projects
  are stopped, with volumes retained. Private config/fixture remains in
  `test-artifacts/deployment/isolated-yxc_0c_9/`. No external SMTP was configured.
- Linux Firefox uses the approved matching Playwright Noble image and
  `tests/web/container-browser.mjs`. Do not run it beside a full Docker stack on
  this 2-CPU/2-GiB VM. Mount the repo read-only, test-artifacts read/write.
- A full browser run consumes its fixture. Restart Django to reset disposable
  LocMem login quotas and seed a NEW private fixture immediately before each
  full run. Never seed another fixture while a full run is active: Overview
  assertions depend on that fixture being the newest failure set. Preserve
  existing database/media files; no resets. Include SMTP readiness settings
  from the historical infrastructure section; keep delivery workers stopped.

The requested implementation and simulator verification are complete locally,
including the final Docker reader build, measured HTTPS load, and Linux package
installation. The isolated application and restore stacks are stopped with all
volumes retained. Five development-only lint dependency findings remain
unresolved because the publisher has no patched release; no check was weakened.

Physical installations, external mailbox/Kindle acceptance, production editorial
judgment, field Web Vitals, and separate-machine capacity are outside the user's
current simulator-only scope. Do not claim those real-world criteria passed.
The simulator report records the evidence and limits without marking the original
physical acceptance criteria complete.

## Historical checkpoints

Continuation checkpoint after entity and book relationship administration.
Continue the accepted Bengali library plan; **the full plan is not complete**.
Read root `AGENTS.md`, preserve all existing tracked/untracked edits, and do not
restart implementation or repeat completed discovery.

## Scope and authorization

Implement the accepted six-phase Next.js/Django/PostgreSQL/Celery/RabbitMQ/Redis
plan, with Bengali public discovery, reader and admin workspaces, responsive PWA,
SEO, portable deployment, and measured capacity. The user wants implementation
continued until complete. No commits, pushes, destructive cleanup, production
deployment, external emails/account actions, or purchases are authorized.
No subagents are authorized. New dependencies still require explicit approval.

Approved dependencies are installed in `.venv`, `app/web/node_modules`, and the
retained frontend. The user explicitly approved isolated local downloads/builds
and tests of Python 3.12.15, Node 22.23.3, Nginx 1.30.6, and RabbitMQ 4.3.6 images.
Their digests are pinned in `deploy/compose/platform.yml` and Dockerfiles.
Current Playwright/browser upgrades and an ESLint support exception remain
unapproved; see `docs/architecture/verification-tooling.md`.

## Completed and verified checkpoint

Core delivered work includes public Bengali SSR discovery/search/entity pages,
reviewed editorial metadata, SEO/sitemaps/slug history, scoped permissions,
transaction-safe read-once launches, prepared protected EPUB resources, reader
progress/appearance/bookmarks/highlights/notes, profile/password/TOTP/session
invalidation, Kindle requests, invitations/reset links, access administration,
source inspection/discovery/processing, explicit bulk outcomes, persisted jobs,
source automations, admin overview, responsive layouts, and PWA offline/update
handling. Detailed architecture documentation is in `docs/architecture/`.

This session additionally completed:

- Shared source request pacing, protected Nginx byte delivery, production settings,
  shared Redis quotas, health checks, and production exclusion of legacy routes
  and legacy engine signal listeners.
- Container images, fresh migrations and static publication, configurable HTTPS
  origin/ports, graceful scheduler/dispatcher termination, Docker DNS refresh in
  Nginx, stable RabbitMQ hostname, compatible durable control/exclusive event queues.
- Actual isolated HTTPS integration, live confirmed dispatch/preparation, duplicate
  delivery, broker/cache outages, broker/API/frontend replacement, stale-attempt
  recovery, and a separate-project database/media/runtime backup/restore drill.
- Digital/paper-book record creation, immutable UUID request replay/status,
  revision-checked edition/language/publisher/decimal price/binding/compilation
  fields, no ownership assignment, current-actor editorial authority checks,
  and a fix preserving editorial save confirmation on server refresh.

Earlier verification **before the entity/relationship continuation below**:

- 701 selected PostgreSQL tests passed (77 files), including 26 new catalog cases.
- All 93 Chromium browser journeys passed with a fresh fixture and restarted
  disposable development API. Existing Playwright 1.53/Chromium 138 was used.
- 18 Node tests; mypy on 181 source files; strict TypeScript; ESLint; local and
  Docker Next.js production builds; OpenAPI validation; migration consistency;
  Ruff on affected modules; architecture policy; `git diff --check` passed.
- Full legacy suite is not passing: earlier 243 passes/40 failures need audit;
  three failures reproduced on unchanged HEAD. File-size policy still reports
  18 pre-existing violations; no exemptions or checks were weakened.

See `docs/operations/local-platform-verification.md`,
`docs/operations/platform-deployment.md`, and
`docs/architecture/catalog-records.md` for tested behavior and limitations.

## Completed continuation — entity and relationship administration

The previously unfinished backend now has tested responsive Bengali management
screens at `/manage/entities/`, kind-specific lists, creation, and UUID detail
pages. Kinds: contributors, categories, series, collections. Creation requires
global metadata authority; contributor/category grants manage only the exact
granted entity. Entity metadata reuses the book editor's text/SEO fields.

Creation replay now verifies the audit target UUID. Normalized-name checks and
kind locks cover both creation and renames, including collections. Creation and
updates take kind locks before entity row locks, including legacy UUID collisions.
Lists fetch only displayed fields. Collection detail includes ordered book IDs
and labels in two queries, with no deferred reverse-FK queries. Invalid selection rolls back
all metadata/order/audit changes. Review, publication, withdrawal, and slug
history are covered. Collections accept up to 100 unique selected books.

`/manage/books/<slug>/relationships/` and its versioned API manage contributor
roles, categories, ordered series, and explicit edition grouping. Global metadata
authority is required because these relationships also determine scoped access.
Changes snapshot the old relationships and reset review. Creating a group changes
and snapshots both editions; moving/detaching affects only the edited book.
Commands serialize before taking book locks, including reciprocal edition links.
Public cross-edition browsing is still outstanding.

Remote selectors use bounded, debounced, cancelled searches; selections survive
search changes. Entity creation invalidates cached reference results. Forms keep
drafts on validation/conflict, retain uncertain creation UUIDs, block uncertain
repeated writes, and participate in the PWA update guard. API types regenerated;
mypy coverage expanded to 189 files. No dependency added.

The full browser run also exposed old Overview ordering: PostgreSQL sorted null
completion times ahead of newer failures. It now orders by completion time with
update-time fallback, with a regression test. New relationship browser tests use
their own entities so they cannot change the existing scoped editor fixture.

Verification at this continuation:

- 706 foundation PostgreSQL tests passed in 75 files, including 62 new cases
  for entities, relationships, grouping, and Overview failure ordering.
- All 101 Chromium journeys passed with a fresh fixture and restarted local API,
  including eight new entity/relationship journeys and cached-reference refresh.
- 18 Node tests; mypy on 189 source files; strict TypeScript; ESLint; Next.js
  production build; OpenAPI validation; migration consistency; affected Ruff and
  formatting; architecture policy; `git diff --check` passed.
- 320-pixel/200%-text entity and relationship screenshots were inspected.
- Current Docker application images were not rebuilt for this continuation;
  the isolated deployment results above apply to the earlier checkpoint.
- Full legacy-suite failures and the same 18 file-size violations remain open.

See `docs/architecture/catalog-entities.md` for contracts, authority, grouping,
and regression coverage. Tests are in `test_managed_entities.py`,
`test_managed_collections.py`, `test_entity_authority.py`,
`test_entity_concurrency.py`, `test_book_relationships.py`, and the Overview suite.
Browser additions are `entities.spec.mjs` and `book-relationships.spec.mjs`.

## Running/local infrastructure

Existing foundation project: `local/compose/docker-compose.yml` plus
`local/compose/platform-test.yml`, project `elibrary-foundation`.
PostgreSQL localhost 55432 (`bangla_library`), Redis 56379. Never reset its volumes.

Backend test prefix:

```sh
PYTHONPATH=app/backend DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55432/bangla_library CELERY_BROKER_URL=redis://127.0.0.1:56379/0
```

Production test project `elibrary-platform-test-kjzj4dcz` has its private env and
fixture in ignored `test-artifacts/deployment/isolated-yxc_0c_9/`. Never print the
env contents/expanded Compose configuration or private fixture values. It binds
18080/18443; test origin `https://library.example.test:18443`.
Production test services stopped successfully (session 40546, exit 0).
Restore projects are stopped and volumes retained. No data was deleted.
The Colima VM has only 2 CPUs/2 GiB RAM/no swap. Run one full test stack at a time.

Local Django port 8000 runs current code with `--noreload` (PID 39942). Next
standalone port 3000 runs the verified entity/relationship build (PID 37136).
Private server logs are in ignored `test-artifacts/foundation/` files. A separate
local protected-proxy test also has
Django 8001 and rootless Nginx 8082; inspect processes before restarting.
Stop servers with output filtered to exit metadata: Django buffers can contain
reader-session URLs. Do not print credentials or reader tokens.

For every complete browser run, restart development Django to reset its disposable
LocMem login quota and generate a **fresh** fixture with `tests/web/seed_preview.py`.
Include `SOURCE_SITE_HOST=source.example.test` when seeding/running Django.
The UI suite also needs local SMTP readiness settings: use
`EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST=127.0.0.1`,
`EMAIL_PORT=1025`, `EMAIL_USE_TLS=false`, and synthetic
`ACCOUNT_INVITE_FROM_EMAIL=library@example.test` / `DEFAULT_FROM_EMAIL=library@example.test`.
Keep workers stopped for this UI-only run; requests queue work without sending mail.
Omitting SMTP configuration disables Kindle requests and fails those journeys.
The seed guard rejects production/non-55432 databases; do not weaken it.
Set `FOUNDATION_FIXTURE_PATH` to a new private file and
`FOUNDATION_CANONICAL_ORIGIN=https://library.example.test` for browser tests.
Full fixtures are consumed by the tests; never reuse one for another full run.

## Remaining accepted work

Public cross-edition browsing; saved/recent/granted library views; remaining
physical-book reader workflows; profile images;
legacy source-exec facade removal and failing legacy/policy checks; Bengali search
corpus/query intent/editorial launch content/SEO and performance acceptance;
supported Firefox/WebKit tooling, actual Android/iOS installation and PWA checks;
fresh Ubuntu/Debian host verification; active-worker interruption scenarios;
actual external/device delivery; and isolated k6 capacity tests with documented
separate load-generation hardware. No capacity or actual-device acceptance is
established. Do not mark the full plan complete or invent a completion percentage.

## Active continuation — personal reading and verification (16 October)

The user subsequently requested full implementation and issue fixing, then
repeatedly asked to continue. Continue working; this is an active checkpoint.
Do not stop at the previous entity increment.

New implementation: saved/recent/granted library feeds, private paper reading
logs, published cross-edition links/full list, and private normalized profile
images. `catalog.0026_personal_reading` was generated/applied. Contracts/types
were regenerated. See `architecture/personal-reading.md` and new tests in
`tests/backend/catalog_management/test_personal_library_views.py`,
`test_physical_reading.py`, `test_public_editions.py`,
`tests/backend/auth/test_profile_images.py`, and
`tests/web/e2e/personal-library.spec.mjs`.

The user explicitly approved Playwright 1.64.0/browser bundles, the temporary
ESLint 9.39.4 exception with all rules retained, and `types-reportlab` /
`types-qrcode` development stubs. These are installed and pinned. The user also
requested Docker installation simulation for unavailable external/device test
resources. Actual physical-device installation and external mail delivery must
not be represented as simulated proof. A pending async approval request for the
pinned Grafana k6 2.3.0 image has not been answered at this checkpoint.

Retained audit: a complete non-live run passed **1,234 tests** (13 live cases
explicitly deselected) in `full-backend-audit-4.log`. It exposed Redis observer
shutdown warnings; the fixture now stops and joins before closing. All **84
engine tests pass with thread-exception warnings treated as errors**. The old
source scraper, normalization, and submission loaders use explicit imports;
retry/failure/regeneration helpers were separated without removing assertions.
All **180 ingestion tests passed** after the last extraction. Full suite needs
rerunning after final changes. Mypy passes all **199 configured source files**,
with no error suppression. Ruff, architecture and 300-line size policies pass.
All **154 retained frontend unit tests** passed. Keep all pre-existing edits.

Search now combines title and contributor terms and reviewed Romanized aliases;
31 corpus/discovery/pagination cases passed. Ten of these are new synthetic
corpus cases. Home Organization and collection ItemList structured data were
added with browser assertions, not yet in a passing full matrix.

Browser findings and current work:
- Playwright's Firefox fails on macOS 27 before launching (upstream issue 42768).
  The matching Ubuntu Noble image was downloaded with the user's Docker/bundle
  authorization: `mcr.microsoft.com/playwright:v1.64.0-noble` digest
  `sha256:06a9939e57531807f8d5fd76ce44b53165ffb7d7501d87ab10e285c20b1e971f`.
  `tests/web/container-browser.mjs` forwards container loopback 3000/8000 to host
  services, preserving trusted host/origin headers. Mount repo read-only and
  ignored test-artifacts read/write; `/private/tmp` is not shared with Colima.
- General browser tests block service workers so injected network failures are
  intercepted consistently; PWA and reader specs explicitly allow workers and
  exercise the actual worker. Status assertions now identify their expected
  message instead of assuming the entire page has only one status region.
- Account switching had a real in-flight session race. Focus now cancels the old
  session read before refetching; server-rendered private layouts use an account
  snapshot guard. All three focused account-isolation tests passed, including
  the new first-response timing regression.
- Chromium full run passed 105/106 before the latest fixes. Password-link reset
  passed independently with a fresh fixture, but the full run needs confirming.
- Latest WebKit full run: **104/107 passed**. Remaining failures were reset mock
  timing, immediate update saving zero progress, and resize position. Fixes now
  in source: wait for the actual write, synchronous capture before flush,
  parent-realm position/selection observation for script-disabled WebKit frames,
  resize sampling guard, and explicit dialog opener focus restoration. Reader
  scripts stay disabled. Need rebuild and rerun focused/full checks.
- The latest Linux Firefox full run passed 90/106 before shared status/timing,
  container port-8000 forwarding, and reader-CSP assertion fixes. Run again with
  a fresh fixture; do not reuse consumed password/session/source fixtures.

Current build `reader-flush-build.log` is running. Previous standalone PID 65801
was stopped for it. Restart from `app/web` with HTTPS PUBLIC_SITE_URL and
HOSTNAME=127.0.0.1 PORT=3000 when complete. Current Django8000 is PID 65781 with
SMTP readiness configuration from above. Restart it for each full browser run
(to reset disposable LocMem login quotas). Workers remain stopped for UI tests.
Private fixture `/private/tmp/elibrary-webkit-final-20261016-h.json` is consumed.
Fresh, unused fixture `test-artifacts/foundation/firefox-final-fixture.json` was
created but not yet run. Protect fixture contents. Use separate browser output
paths per run, since Playwright clears its output directory.

A real worker SIGKILL integration scenario is implemented but unverified:
`tests/deployment/interruption_fixture.py` creates 100 substantial EPUB chapters;
`verify_active_worker_interruption` waits for actual preparation, kills/restarts
only the isolated test worker, waits for normal lease recovery, and verifies
one prepared publication and duplicate suppression. `compose_client.py` copies
this new script; `job_probe.py` exposes the guarded fixture action and stage.
Run after rebuilding isolated API/frontend images. The production test project
is still stopped with all volumes retained. Existing isolated directory remains
`test-artifacts/deployment/isolated-yxc_0c_9/`; never print its environment.

Still required: finalize all browser checks and fresh Docker simulator build/
recovery checks; measured search plans and local capacity harness/results;
update architecture/operations docs to match actual evidence. Full product and
external/device/capacity acceptance remains incomplete. No commit or push.

Latest checkpoint correction: the three focused WebKit failures are now fixed
and passed together (`webkit-last-fixes.log`). Before flushing progress, the hook
captures the actual chapter position; observation skips resize geometry changes,
and closing the reader dialog explicitly restores opener focus. The last build
`reader-flush-build.log` passed and standalone is running again (inspect port
3000 for PID). Linux Firefox full rerun `firefox-final-b.log` is now running via
Docker with the previously-unused `firefox-final-fixture.json` and separate
`firefox-final-browser` output. Do not change/rebuild the standalone while it runs.
The next unused Chromium fixture is `/private/tmp/elibrary-chromium-final-20261016-i.json`.

`tests/performance/test_discovery_profile.py` is running a guarded pytest test DB
profile with 10,000 synthetic books, 20 samples for each of three intents, and
EXPLAIN ANALYZE/BUFFERS JSON. Report target is ignored
`test-artifacts/performance/discovery-profile.json`. Its first attempt failed
because the catalog-code length was guessed; corrected to the existing
`catalog_code_from_int` generator and now rerunning. Do not cite results until
this run passes. It leaves no persistent corpus in the development database.
