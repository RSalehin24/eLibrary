Status: DRAFT

# 16b. Legacy frontend unit tests, test tooling, policy scripts

Scope: `archive/tests/frontend/{package.json,playwright.config.js,unit/*}`, `archive/tests/tools`, `archive/tests/policy`, `archive/tests/scripts`. Paths below are relative to `archive/tests/` unless noted. Runner: `node:test` + `node:assert/strict`, ESM (`frontend/package.json:1-3`).

## A. Meta-findings (read first)

- U1. Most "unit tests" do not test production code. Six files inline copies of the functions "verbatim" because Node ESM cannot resolve Vite's extension-less imports (bookExportPrice.test.js:3-7; manualBooksExcelExport.test.js:10; manualBooksModule.test.js:1-6, 20-22; physicalBooksEdit.test.js:11-13, 55-57; tagInputKeyboard.test.js:22-25). They pass even if production code diverges: no regression protection, only a behaviour spec. Rebuild lesson: test the real module (TS + Angular test runner / Vitest with proper resolution), never a copy.
- U2. Five tests are source-grep tests: they read CSS/JSX/YAML as text and regex-match (embeddedReaderScrollbarTheme, embeddedReaderThemeTokenScope, homePageToolbar, localStackConfig, localWorkerConfig). They pin implementation text, not behaviour; brittle and low value. Only the intent is worth keeping (see U20-U24).
- U3. Genuinely importing real modules: accessValidation, apiErrors, apiResponse, apiText, bookDetailReaderLaunch, notificationAudio, processingCreatedNotificationBuffer, readerManifest, toastManager, urlNormalization, and the constants part of manualBooksModule. These specify real contracts (U4-U19).
- U4. Dependency-injection style: schedulers (`schedule/clear`), `AudioContextClass`, `storageApi`, `apiClient`, `navigate`, `createId`, `playSound` are injected so tests are deterministic. Good pattern to keep (clock/IO ports).

## B. Behaviours specified by tests (requirements candidates)

### Email / account access (accessValidation.test.js)
- U5. `normalizeEmail` trims surrounding whitespace (L16-18). `isValidEmail` accepts trimmed valid address, rejects "reader" (L20-24). `getEmailValidationState` returns `{normalizedEmail, hasEmailInput, emailLooksValid}` (L26-37).
- U6. Kindle email rule: only exact domain `kindle.com` valid; `free.kindle.com` and other domains invalid (L39-45). Validation state layers `baseEmailLooksValid` + `kindleDomainLooksValid`; `emailLooksValid` = both (L47-69). Note: `free.kindle.com` is rejected even though Amazon historically allowed it; the new app should confirm the rule (see Unverified).
- U7. `getAccountAccessLabels(account, scopeLabelMap)` maps `global_scopes` to labels and sorts alphabetically by label (L71-86). `formatAccountAccess` joins labels, returns `"-"` when no scopes (L88-101). Scope names seen: `read:durable`, `metadata:edit`.

### API client contract (apiErrors, apiResponse, apiText, urlNormalization)
- U8. 502 responses keep the backend `detail` message as `error.message`, and `error.status` is set (apiErrors.test.js:6-21). Example: Kindle delivery SMTP auth failure surfaced verbatim.
- U9. `parseResponse` on HTTP 204 returns `null` even when content-type is JSON (apiResponse.test.js:6-15).
- U10. Error text extraction (apiText.test.js): `payloadMessage` prefers `detail` string (L11-16); else first field validation message from DRF-style `{field: [msg]}` (L18-25); empty `detail` falls through to nested lists-of-objects errors (`entries[0].content[0]`) (L27-35). `firstPayloadIssue` returns `{field, message}` (L37-47). `payloadFieldMessage(payload, labelMap)` prefixes a label: "Account permissions: ..." (L49-57). `formatApiError` humanizes unmapped field names: `new_password` -> "New Password: ..." (L59-69). Implication: server error shape was Django REST; new contract should carry a stable machine code + field path so the UI need not parse prose.
- U11. `normalizeAppUrl` rewrites absolute backend URLs (host `testserver`) onto the browser origin keeping `/api` path (urlNormalization.test.js:9-17), and rewrites a nested URL inside a `manifest=` query parameter of a launch URL, leaving the outer host untouched (L19-30). `resolveApiUrl("/processing/stream/")` -> `<origin>/api/processing/stream/` (L32-48). Smell: backend emits absolute URLs with the wrong origin; new design should emit relative/opaque URLs.

### Reader launch / manifest (bookDetailReaderLaunch, readerManifest)
- U12. Launch flow: POST `/access/books/{slug}/reader-launch/` with body `{}`, then navigate to `/reader?slug=<slug>&manifest=<urlencoded manifest>&appNav=hidden` (bookDetailReaderLaunch.test.js:9-61). Manifest URL taken from `manifest_url`, falling back to the `manifest` query param inside `launch_url` (L21-32). Reader token is embedded in manifest URL path (`/reader/token-123/manifest/`). Reader hides app nav via `appNav=hidden`.
- U13. Manifest payload normalizes four browser-facing URLs: `epub_download_url`, `html_preview_url`, `reading_session_url`, `bookmarks_url` (readerManifest.test.js:26-44). Tells us the reader consumed: EPUB download, HTML preview, reading-session endpoint, bookmarks endpoint.

### Notifications / toasts (toastManager, notificationAudio, processingCreatedNotificationBuffer)
- U14. Toast manager: push(spec|string, type); subscribe/getState/destroy; `muted` state; `setMuted`. Grouped toasts via `groupKey`: a new push with the same key replaces title/description in place (one toast), does NOT replay sound, and restarts the hold timer (`holdOpenMs: 120000`); toast disappears only after a full quiet window (toastManager.test.js:47-106). Muting keeps toasts visible but suppresses sound (L108-131). `soundType` can differ from visual `type` (L133-154).
- U15. Notification sound: synthesized with WebAudio, two-tone presets per type: success 660 then 880 Hz; error 260 then 196; info 420 then 560 (notificationAudio.test.js:81-105). Resumes suspended AudioContext (resume called once across three plays). `playSound` returns true. Mute preference persists via storage get/set, default false (L107-123).
- U16. Processing "created" notifications are batched: counts accumulate, one flush after 180000 ms (3 min) with the summed count; `flushIfPending()` flushes immediately and cancels timer (returns count); message "N books created." (processingCreatedNotificationBuffer.test.js:50-103). Bug-shaped gap: message has no singular ("1 books created.") and is untested for count 1.

### Manual (physical) books (manualBooksModule, physicalBooksEdit, manualBooksExcelExport, bookExportPrice)
- U17. Constants: `emptyManualBookForm` has binding default `hard_cover`, empty title/publisher/price, empty `writers` and `categories` arrays; `defaultManualBookFilters` = `{q, writer, translator, editor, category, publisher, binding, ownership, record_type:"manual", sort:"-created_at"}`; storage key `manual-books-export`; toolbar fields exclude `sort`; sort options include "Newest first" = `-created_at` (manualBooksModule.test.js:156-195). Only these (real import) test production code in that file.
- U18. Options loading: six parallel catalog GETs (`categories, writers, translators, editors, series, publishers` with `?record_type=all&sort=name`); `contributors` suggestion list = writers+translators+editors merged, case-insensitive de-dup after trim, sorted by `localeCompare` (L201-249). Note default `localeCompare` is not Bengali-aware (see U30).
- U19. Create: empty-string price sent as `null`, other price strings passed through unchanged (decimal as string, e.g. "499.50") (L255-287). Export loads all pages: forces `page=1&limit=100`, reads `pagination.page_count`, fetches sequentially, concatenates; list payload may be bare array or `{entries, pagination}` with defaults (page 1, limit 60) (L25-62, 124-150, 293-354).
- U20. Edit-form mapping (physicalBooksEdit.test.js): book -> form: binding normalized (`hard cover|hard_cover|HARD-COVER` -> `hard_cover`; paperback variants -> `paper_back`; other values -> `""`); price prefers `price` then `manual_price`, falsy -> `""` (note: price 0 maps to `""`, L68-81); language default `bn`; `is_compilation` from either field; contributors roles `author->writers`, `translator`, `editor`, `compiler` canonicalized to editor; legacy `authors[]` fallback (L138-317, 351-366). Form -> payload: single `contributors` array with roles author/translator/editor plus publisher (when set), price `""` -> null, language default `bn`; names are NOT trimmed/collapsed on the way out despite the test title claiming normalization (L269-291 asserts raw spaces preserved) (U29).
- U21. Display rule (mocked): a "writer cell" shows first non-empty of Writer, Translator, Editor when role-limited, else all groups joined; empty -> "—" or "Contributor unavailable" (L319-400). At least one of writer/translator/editor required to save (L402-416).
- U22. Contributor normalization (inlined in 4 files): name normalized NFKC + trim + collapse whitespace + lowercase; role `compiler` is alias of `editor`; missing role -> `other`; de-dup on name|role; an `author` entry is dropped when the same person is also a non-author (translator/editor) in the same book; falls back to `authors[]` (bookExportPrice.test.js:44-75, others identical).
- U23. Excel export (manualBooksExcelExport.test.js): XML escaping of `& < > " '` and stripping of control chars (0x00-0x08, 0x0B, 0x0C, 0x0E-0x1F); binding labels (Hardcover/Paperback, else passthrough); language labels (bn=Bengali, en=English, else passthrough); sheet name sanitizing: replace `\ / : * ? [ ]` with `_`, truncate to 31 chars, trim, fallback `SheetN`; grouping modes `category | publisher | binding | language | contributor`, with `(None)` bucket, a book can appear in several groups (multi-category, multi-contributor), per-group de-dup, insertion order. Sheet-name collision after truncation/sanitizing (two groups -> same name) is untested and illegal in Excel (U31).
- U24. Export rows/CSV (bookExportPrice.test.js): 14 columns in order `Book ID, Title, Writer/Translator/Editor/Publisher, Writers, Translators, Editors, Publishers, Categories, Series, Price, Type, State, Review, Created At`; price "" for null/undefined/"" but "0" for 0; type Manual/Digital by `record_type`; date `Intl.DateTimeFormat("en", {year, month short, day numeric})`; contributor line format `A, B · Translator: X · Editor: Y · Publisher: Z`, fallback "Contributor unavailable"; `escapeCsv` quotes when value contains `, " \n` and doubles quotes; `slugifyFilename` lowercases, `[^a-z0-9]+ -> -`, falls back to `books-export`.

### Tag input component (tagInputKeyboard.test.js, pure state machine)
- U25. Suggestions: exclude already-chosen values (case-insensitive), substring filter case-insensitive on trimmed input, cap 6. Keys: ArrowDown/Up cycle with wrap (-1 -> 0; Up from -1 or 0 -> last); Tab picks highlighted else first suggestion; Enter or `,` picks highlighted else commits free text; Escape closes dropdown only if open; Backspace on empty input removes last tag; ArrowLeft/Right fire field-navigation callbacks only when input empty. Add guard: trim + collapse internal whitespace, ignore empty, ignore case-insensitive duplicate (clears input). Blur commits typed text (regression: "Add & next" button blurred the input and lost the typed Bengali name) (L432-517). Bengali strings used as fixtures (e.g. ফারসীম মান্নান মহাম্মাদী). Accessibility gap: no aria-activedescendant/listbox semantics are tested; Escape sets `focused:false` rather than just closing.

### Source-grep tests (intent only)
- U26. Reader embedded CSS: scrollbar theming must target `.epub-container .epub-reader-container .epub-contents` with `scrollbar-color: var(--scrollbar-thumb) var(--scrollbar-track)`, never `body.epub-container` alone (embeddedReaderScrollbarTheme.test.js:10-25). Theme tokens must be scoped to `body.epub-container` / `.reader-page-fullscreen.epub-container` with `.theme-type-1` and `.theme-type-2` variants and never to a bare `.epub-container` (embeddedReaderThemeTokenScope.test.js:10-32). Intent: embedded reader must not leak theme variables onto the host app (a reader theme leak bug). Reader had at least two themes (type-1, type-2).
- U27. HomePage (homePageToolbar.test.js:10-27): home catalog toolbar takes sort value/options from filter field `sort`, `onSortChange` updates filters and the URL search params via `cleanQueryParams`; BookCardGrid has an `observeLoadTrigger` (infinite scroll via IntersectionObserver). Requirement candidates: sort + filters are URL-addressable; catalog uses infinite scroll.
- U28. Ops-config tests (localStackConfig, localWorkerConfig): docker-compose passes `CELERY_TASK_ALWAYS_EAGER` default 0; the ingestion worker is pinned to single task: `CELERY_WORKER_CONCURRENCY=1`, `PREFETCH_MULTIPLIER=1`, `MAX_TASKS_PER_CHILD=1`, `--pool=solo` (localWorkerConfig.test.js:10-55). Implies ingestion is memory/CPU heavy, must run one book at a time and recycle the process after each task; carry into the new ingestion service as a concurrency=1 + process-isolation requirement.

## C. Bugs, gaps, smells found

- U29. physicalBooksEdit "normalizes spaces" test (L269-291) asserts the OPPOSITE (raw `"  Alice   Name  "` is kept). Contributor names are not normalized when sent; only the TagInput collapses whitespace. Server must normalize or the UI must.
- U30. `localeCompare` used for sorting suggestions (U18) has no locale argument; Bengali collation depends on runtime. Rebuild: use `Intl.Collator("bn")` or server-side sort.
- U31. Excel sheet names are not made unique after sanitize/truncate (U23); grouping label `(None)` and a real category named "(None)" would merge.
- U32. `slugifyFilename` strips non-ASCII, so a Bengali-only name always becomes `books-export` (bookExportPrice.test.js:30-38, 426-444). `escapeCsv` does not quote `\r` and does not guard CSV/formula injection (cells starting `= + - @`).
- U33. `price` zero: export keeps "0" (L251-255) but edit form maps price `0` to `""` (physicalBooksEdit L81 `priceVal ? ... : ""`), silently turning a free book into "no price". Inconsistent.
- U34. `createdNotificationDescription` has no plural handling (U16).
- U35. Test titles overpromise ("Comprehensive integration and unit tests", manualBooksModule.test.js:2) when most logic is a copy (U1).
- U36. Hard-coded environment strings (`http://testserver`, `127.0.0.1:5173`) show URL rewriting depended on a Django test host leaking into responses (U11).
- U37. Ticking-timer fake scheduler duplicated verbatim in toastManager.test.js and processingCreatedNotificationBuffer.test.js (no shared helper). Test-code duplication.

## D. Test tooling / policy / scripts

- U38. Playwright (frontend/playwright.config.js): base URL `PLAYWRIGHT_BASE_URL` default `http://127.0.0.1:5173`; 1 worker, not fully parallel; timeout 45 s; viewport 1440x900; Chromium only; storageState `.auth/superadmin.json` produced by `./e2e/globalSetup.js`; trace on first retry; live-processing specs (`**/processing-pages-live*`) ignored unless `PLAYWRIGHT_RUN_LIVE_PROCESSING=1` (L12-17). Playwright resolved from `app/frontend/package.json` via `createRequire` (L5-6). E2E tests log in as a seeded superadmin.
- U39. `tools/test_env_tools.py`: `render_shell_exports(parse_env_file(path))` emits `export KEY=<shlex-quoted value>`; skips comments; keeps empty values; `$` stays literal; already-quoted values are NOT unquoted (quotes become part of the value, shlex-quoted); single quotes escaped (L7-41). Tests a tiny helper `automation/lib/env_tools`.
- U40. `scripts/check-file-size-policy.py`: 300 physical-line cap on first-party `.css .html .js .jsx .py .sh .ts .tsx .yaml .yml` under git (cached+untracked), excluding dist, node_modules, public, storage, vendor, `docs/`, `logs/`, `package-lock.json`, and files listed in `policy/*.txt` (L11-78). `policy/existing_large_files.txt` is the grandfather list of 46 legacy files over 300 lines (incl. `dark-mode.css`, `notes-page.css`, `foundation-and-shell.css`, `catalog-tables.css`, `access-settings-fields.css`, `tablet-responsive-layout/catalog-property-controls.css`, `docker-compose.yml`, pages `LibraryPage/NotesPage/ReprocessingPage/ManualBooksPage/BookDetailPage`, `BookTable.jsx`). Comment says "Legacy files exceeding the 300-line limit". The CSS split into dozens of tiny files (styles tree) is a direct artefact of this rule.
- U41. `scripts/check-architecture-policy.py`: bans numbered split modules (`part-N`, `part_N`, `_parts/`), generated loaders (`glob("part_*.py")`), `apiFetch` outside `app/frontend/src/api/` or `features/<x>/api.{js,ts}`, and Python transport modules (`views`, `serializers`) importing external I/O clients (`redis, requests, kombu, bs4, boto3, celery, config.celery`) (L12-97). Evidence the team had earlier worked around the 300-line rule by auto-splitting files into "parts" and then banned that. Layering rule worth keeping: HTTP layer must not do I/O directly.
- U42. `policy/existing_migrations.txt`: 44 frozen Django migrations (access 4, accounts 5, catalog 22, common 2, ingestion 8, processing 3). Domain growth signal: catalog 22 migrations, e.g. codes, manual record type, contributors compiler role, curated book documents, group/edition, user kindle sends. Not read for content (list only).
- U43. `scripts/verify.sh`: pipeline = file-size policy, architecture policy, docker compose up (postgres redis backend frontend), stop worker/processing-worker/beat, wait for URLs, seed deterministic E2E data, backend pytest inside the container (`/workspace/tests/pytest.ini`), frontend unit tests (host), frontend build inside container, Playwright (`--workers=1`), with `--repeat N` (flake hunting) (L10-131). `test-all.sh` just execs verify.sh. `test-backend.sh` starts all services incl. worker/beat/processing-worker; `test-e2e.sh` stops workers so seeded data is stable; `test-processing-live.sh` runs the live processing spec against the real stack with workers on, no seeding; `test-frontend-unit.sh` needs no Docker. `seed-e2e-data.sh` runs `manage.py seed_e2e_data` in backend. All wait-for-url helpers are copy-pasted in 4 scripts (duplication). Health URL: `GET /api/auth/session/` used as readiness probe (not a real health endpoint).
- U44. `scripts/regression_curate_300.sh`: runs a 300-URL source-site regression harness inside the backend container (`python scripts/regression_curate_300.py`), resumable via state JSON `/app/storage/regression-300/state.json`, flags `--limit N`, `--retry-failed`, `--purge-exports`. Evidence the ingestion scraped third-party site(s) and kept a 300-book regression corpus; the new project must keep copyrighted content out of the repo (CLAUDE.md hard rule). Note unquoted `$*` interpolation into `sh -lc` (shell injection / quoting hazard with args containing spaces).

## E. Keep / drop for the rebuild

Keep as requirements: U5-U7, U8-U10 (error-surface rule), U12-U16, U19-U25, U27, U28, U39 idea, U41 layering. Drop: inlined-copy test style (U1), source-grep tests (U2, U26 except intent), prose-based error parsing (U10), absolute-URL rewriting (U11), grandfather lists (U40), part-splitting.

## Coverage table

| File | Lines | Fully read |
|---|---|---|
| frontend/package.json | 3 | yes |
| frontend/playwright.config.js | 35 | yes |
| frontend/unit/accessValidation.test.js | 101 | yes |
| frontend/unit/apiErrors.test.js | 21 | yes |
| frontend/unit/apiResponse.test.js | 15 | yes |
| frontend/unit/apiText.test.js | 69 | yes |
| frontend/unit/bookDetailReaderLaunch.test.js | 61 | yes |
| frontend/unit/bookExportPrice.test.js | 444 | yes |
| frontend/unit/embeddedReaderScrollbarTheme.test.js | 25 | yes |
| frontend/unit/embeddedReaderThemeTokenScope.test.js | 32 | yes |
| frontend/unit/homePageToolbar.test.js | 27 | yes |
| frontend/unit/localStackConfig.test.js | 29 | yes |
| frontend/unit/localWorkerConfig.test.js | 55 | yes |
| frontend/unit/manualBooksExcelExport.test.js | 328 | yes |
| frontend/unit/manualBooksModule.test.js | 354 | yes |
| frontend/unit/notificationAudio.test.js | 123 | yes |
| frontend/unit/physicalBooksEdit.test.js | 419 | yes |
| frontend/unit/processingCreatedNotificationBuffer.test.js | 103 | yes |
| frontend/unit/readerManifest.test.js | 44 | yes |
| frontend/unit/tagInputKeyboard.test.js | 544 | yes |
| frontend/unit/toastManager.test.js | 154 | yes |
| frontend/unit/urlNormalization.test.js | 48 | yes |
| tools/test_env_tools.py | 41 | yes |
| policy/existing_large_files.txt | 46 | yes |
| policy/existing_migrations.txt | 44 | yes |
| scripts/check-architecture-policy.py | 110 | yes |
| scripts/check-file-size-policy.py | 111 | yes |
| scripts/regression_curate_300.sh | 35 | yes |
| scripts/seed-e2e-data.sh | 69 | yes |
| scripts/test-all.sh | 9 | yes |
| scripts/test-backend.sh | 89 | yes |
| scripts/test-e2e.sh | 89 | yes |
| scripts/test-frontend-unit.sh | 37 | yes |
| scripts/test-processing-live.sh | 78 | yes |
| scripts/verify.sh | 131 | yes |

## Unverified items

- Production sources behind the tests (`app/frontend/src/**`) were NOT read; "verbatim" claims in inlined tests are unverified, so current production behaviour may differ (U1).
- Whether Amazon Kindle addresses on `free.kindle.com` are invalid by product intent (U6) is from the test only.
- Whether the tests currently pass was not checked (no code run).
- Content of the 44 migrations and what `automation/lib/env_tools`, `seed_e2e_data`, `regression_curate_300.py` do internally.

## Unread files and why

- `tests/frontend/e2e/*` and `node_modules`: excluded by task. `tests/pytest.ini`, `tests/backend/*`: outside slice.
