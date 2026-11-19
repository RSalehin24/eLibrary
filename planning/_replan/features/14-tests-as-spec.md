# 14 — Legacy tests as executable specification (archive/tests)

Status: working notes (read-only extraction from archive/tests; not a plan document)

Scope: all 220 files / 34,416 lines under archive/tests were read in full (blank lines and import blocks were collapsed by tooling when viewing; generated minified helper processingApiMock.js read as one line). Nothing was executed. Detailed per-file notes are in sibling files 14a..14zb (same folder); section 2 below is their concatenation grouped by area.

## 1. Coverage table

| file | lines | fully read |
| --- | --- | --- |
| backend/access/__init__.py | 0 | yes |
| backend/access/test_access_01_cases/download_reader_and_kindle.py | 407 | yes |
| backend/access/test_access_01_cases/kindle_smtp_failures.py | 243 | yes |
| backend/access/test_access_01_cases/kindle_validation_and_html_downloads.py | 99 | yes |
| backend/access/test_access_01.py | 16 | yes |
| backend/access/test_access_02.py | 250 | yes |
| backend/access/test_access_03.py | 289 | yes |
| backend/access/test_access_04.py | 94 | yes |
| backend/access/test_access_05_notes.py | 348 | yes |
| backend/auth/__init__.py | 0 | yes |
| backend/auth/test_auth_01_cases/managed_user_admin_flow.py | 259 | yes |
| backend/auth/test_auth_01_cases/password_reset_flow.py | 236 | yes |
| backend/auth/test_auth_01_cases/password_setup_and_totp_invites.py | 227 | yes |
| backend/auth/test_auth_01_cases/totp_and_managed_user_invites.py | 227 | yes |
| backend/auth/test_auth_01.py | 17 | yes |
| backend/auth/test_auth_02.py | 224 | yes |
| backend/catalog_management/__init__.py | 0 | yes |
| backend/catalog_management/test_catalog_management_01.py | 244 | yes |
| backend/catalog_management/test_catalog_management_02_cases/catalog_references_and_manual_books.py | 253 | yes |
| backend/catalog_management/test_catalog_management_02_cases/exports_and_contributor_filters.py | 128 | yes |
| backend/catalog_management/test_catalog_management_02_cases/my_books.py | 64 | yes |
| backend/catalog_management/test_catalog_management_02.py | 16 | yes |
| backend/catalog_management/test_catalog_management_03.py | 201 | yes |
| backend/catalog_management/test_catalog_management_04.py | 257 | yes |
| backend/engine/conftest.py | 247 | yes |
| backend/engine/constants.py | 24 | yes |
| backend/engine/helpers.py | 199 | yes |
| backend/engine/__init__.py | 0 | yes |
| backend/engine/test_all_job_types.py | 178 | yes |
| backend/engine/test_concurrent_operations.py | 151 | yes |
| backend/engine/test_dispatch_integration.py | 192 | yes |
| backend/engine/test_engine_api.py | 164 | yes |
| backend/engine/test_engine_recovery.py | 233 | yes |
| backend/engine/test_job_dispatch.py | 214 | yes |
| backend/engine/test_processing.py | 228 | yes |
| backend/engine/test_queue_management.py | 177 | yes |
| backend/engine/test_stale_detection.py | 151 | yes |
| backend/engine/test_worker_lifecycle.py | 203 | yes |
| backend/ingestion/__init__.py | 0 | yes |
| backend/ingestion/test_curated_pipeline.py | 751 | yes |
| backend/ingestion/test_ingestion_01.py | 256 | yes |
| backend/ingestion/test_ingestion_02.py | 236 | yes |
| backend/ingestion/test_ingestion_03_cases/source_catalog_entry_filters.py | 247 | yes |
| backend/ingestion/test_ingestion_03_cases/source_catalog_entry_overview.py | 56 | yes |
| backend/ingestion/test_ingestion_03.py | 15 | yes |
| backend/ingestion/test_ingestion_04.py | 227 | yes |
| backend/ingestion/test_ingestion_05.py | 285 | yes |
| backend/ingestion/test_ingestion_06_cases/catalog_automation_views.py | 107 | yes |
| backend/ingestion/test_ingestion_06_cases/catalog_recreation_and_asset_sync.py | 252 | yes |
| backend/ingestion/test_ingestion_06.py | 15 | yes |
| backend/ingestion/test_ingestion_07.py | 258 | yes |
| backend/ingestion/test_ingestion_08.py | 244 | yes |
| backend/ingestion/test_ingestion_09.py | 196 | yes |
| backend/ingestion/test_ingestion_10_cases/queue_fallback_and_retries.py | 259 | yes |
| backend/ingestion/test_ingestion_10_cases/scraper_crawl_and_cover.py | 266 | yes |
| backend/ingestion/test_ingestion_10_cases/stale_processing_recovery.py | 107 | yes |
| backend/ingestion/test_ingestion_10_cases/stale_task_dispatch_guards.py | 234 | yes |
| backend/ingestion/test_ingestion_10.py | 17 | yes |
| backend/ingestion/test_ingestion_11.py | 202 | yes |
| backend/ingestion/test_ingestion_12.py | 247 | yes |
| backend/ingestion/test_ingestion_13.py | 189 | yes |
| backend/ingestion/test_ingestion_14.py | 246 | yes |
| backend/ingestion/test_ingestion_15.py | 243 | yes |
| backend/ingestion/test_ingestion_16.py | 289 | yes |
| backend/ingestion/test_ingestion_17.py | 258 | yes |
| backend/ingestion/test_ingestion_18.py | 238 | yes |
| backend/ingestion/test_ingestion_19.py | 243 | yes |
| backend/ingestion/test_ingestion_20_cases/activity_tasks_and_schedule.py | 225 | yes |
| backend/ingestion/test_ingestion_20_cases/heavy_column_query_efficiency.py | 190 | yes |
| backend/ingestion/test_ingestion_20.py | 15 | yes |
| backend/ingestion/test_ingestion_21_cases/source_site_metadata_fidelity.py | 1157 | yes |
| backend/ingestion/test_ingestion_21.py | 180 | yes |
| backend/ingestion/test_ingestion_22.py | 162 | yes |
| backend/ingestion/test_ingestion_23.py | 205 | yes |
| backend/__init__.py | 1 | yes |
| backend/processing/test_processing_api_cases/automation_ownership_flows.py | 222 | yes |
| backend/processing/test_processing_api_cases/automation_persistence.py | 73 | yes |
| backend/processing/test_processing_api_cases/catalog_automation_matrix_cases.py | 234 | yes |
| backend/processing/test_processing_api_cases/catalog_manual_matrix_cases.py | 225 | yes |
| backend/processing/test_processing_api_cases/catalog_matrix_helpers.py | 67 | yes |
| backend/processing/test_processing_api_cases/catalog_phase_matrix_tests.py | 224 | yes |
| backend/processing/test_processing_api_cases/catalog_phase_pause_behaviour.py | 214 | yes |
| backend/processing/test_processing_api_cases/catalog_phase_resume_flows.py | 270 | yes |
| backend/processing/test_processing_api_cases/catalog_phase_serialization.py | 168 | yes |
| backend/processing/test_processing_api_cases/catalog_sync_parallel.py | 217 | yes |
| backend/processing/test_processing_api_cases/catalog_sync_persistence.py | 218 | yes |
| backend/processing/test_processing_api_cases/checkpoint_and_dispatch_recovery.py | 218 | yes |
| backend/processing/test_processing_api_cases/duplicate_resolution_actions.py | 299 | yes |
| backend/processing/test_processing_api_cases/helpers.py | 246 | yes |
| backend/processing/test_processing_api_cases/incomplete_automation_flows.py | 253 | yes |
| backend/processing/test_processing_api_cases/incomplete_catalog_and_domain_versions.py | 158 | yes |
| backend/processing/test_processing_api_cases/maintenance_and_actions.py | 249 | yes |
| backend/processing/test_processing_api_cases/processing_pipeline_dispatch.py | 213 | yes |
| backend/processing/test_processing_api_cases/queue_fallback_and_reset.py | 243 | yes |
| backend/processing/test_processing_api_cases/read_endpoint_purity.py | 81 | yes |
| backend/processing/test_processing_api_cases/runtime_tick_and_projection_reads.py | 237 | yes |
| backend/processing/test_processing_api_cases/stale_recovery.py | 78 | yes |
| backend/processing/test_processing_api_cases/state_payload_and_tables.py | 231 | yes |
| backend/processing/test_processing_api_cases/ui_version_publication.py | 221 | yes |
| backend/processing/test_processing_api.py | 37 | yes |
| backend/processing/test_processing_contract.py | 196 | yes |
| backend/processing/test_processing_db_consistency.py | 73 | yes |
| backend/processing/test_processing_source.py | 160 | yes |
| backend/test_common.py | 33 | yes |
| backend/test_legacy_pipeline.py | 243 | yes |
| backend/test_spec_books.py | 257 | yes |
| frontend/e2e/access-page-mocked/accessPageMocks.js | 48 | yes |
| frontend/e2e/access-page-mocked-invitations.spec.js | 206 | yes |
| frontend/e2e/access-page-mocked-permissions.spec.js | 89 | yes |
| frontend/e2e/access-page-mocked.spec.js | 1 | yes |
| frontend/e2e/access-page-mocked-validation-and-pagination.spec.js | 242 | yes |
| frontend/e2e/access-page.spec.js | 58 | yes |
| frontend/e2e/auth-pages.spec.js | 41 | yes |
| frontend/e2e/auth-public-create-password-totp.spec.js | 118 | yes |
| frontend/e2e/auth-public-expired-create-password.spec.js | 75 | yes |
| frontend/e2e/auth-public-forced-totp-setup.spec.js | 65 | yes |
| frontend/e2e/auth-public-login-and-reset-request.spec.js | 171 | yes |
| frontend/e2e/auth-public-pages.spec.js | 1 | yes |
| frontend/e2e/auth-public-reset-and-password-validation.spec.js | 84 | yes |
| frontend/e2e/book-detail-page.spec.js | 176 | yes |
| frontend/e2e/catalog-book-tables-mocked.spec.js | 299 | yes |
| frontend/e2e/catalog-pages.spec.js | 82 | yes |
| frontend/e2e/create-books.spec.js | 260 | yes |
| frontend/e2e/globalSetup.js | 142 | yes |
| frontend/e2e/home-filter.spec.js | 80 | yes |
| frontend/e2e/library-page-live.spec.js | 52 | yes |
| frontend/e2e/manual-books.spec.js | 241 | yes |
| frontend/e2e/page-loaders-mocked.spec.js | 254 | yes |
| frontend/e2e/pages/accessPage.js | 99 | yes |
| frontend/e2e/pages/authPage.js | 98 | yes |
| frontend/e2e/pages/bookDetailPage.js | 80 | yes |
| frontend/e2e/pages/catalogPropertyPage.js | 29 | yes |
| frontend/e2e/pages/manualBooksPage.js | 85 | yes |
| frontend/e2e/pages/processingPage.js | 207 | yes |
| frontend/e2e/processing-pages/bootHelpers.js | 18 | yes |
| frontend/e2e/processing-pages/catalogAutomationCases.js | 10 | yes |
| frontend/e2e/processing-pages-catalog-automation-flow.spec.js | 163 | yes |
| frontend/e2e/processing-pages-catalog-loading-and-skeletons.spec.js | 207 | yes |
| frontend/e2e/processing-pages/catalogManualCases.js | 9 | yes |
| frontend/e2e/processing-pages/catalogMatrixHelpers.js | 119 | yes |
| frontend/e2e/processing-pages/catalogProgressCompletion.js | 221 | yes |
| frontend/e2e/processing-pages/catalogProgressStart.js | 142 | yes |
| frontend/e2e/processing-pages-catalog-state-matrix.spec.js | 218 | yes |
| frontend/e2e/processing-pages-catalog-sync-and-record-selection.spec.js | 212 | yes |
| frontend/e2e/processing-pages/catalogSyncState.js | 257 | yes |
| frontend/e2e/processing-pages-create-and-on-hold-actions.spec.js | 180 | yes |
| frontend/e2e/processing-pages-create-card-refreshes.spec.js | 286 | yes |
| frontend/e2e/processing-pages-create-card-state.spec.js | 234 | yes |
| frontend/e2e/processing-pages/fixtures.js | 142 | yes |
| frontend/e2e/processing-pages/index.js | 13 | yes |
| frontend/e2e/processing-pages/interactionHelpers.js | 104 | yes |
| frontend/e2e/processing-pages-live-catalog-runtime.spec.js | 130 | yes |
| frontend/e2e/processing-pages-live-created-lifecycle.spec.js | 112 | yes |
| frontend/e2e/processing-pages-live-duplicate-resolution.spec.js | 96 | yes |
| frontend/e2e/processing-pages-live-incomplete-runtime.spec.js | 92 | yes |
| frontend/e2e/processing-pages-live/processingLiveApi.js | 77 | yes |
| frontend/e2e/processing-pages-live/processingLiveSetup.js | 138 | yes |
| frontend/e2e/processing-pages-live/processingLiveWaiters.js | 116 | yes |
| frontend/e2e/processing-pages-live.spec.js | 1 | yes |
| frontend/e2e/processing-pages-notifications-and-isolation.spec.js | 134 | yes |
| frontend/e2e/processing-pages-on-hold-and-incomplete-actions.spec.js | 219 | yes |
| frontend/e2e/processing-pages/pipelineAdvance.js | 30 | yes |
| frontend/e2e/processing-pages/processingApiMock.js | 45 | yes |
| frontend/e2e/processing-pages.spec.js | 1 | yes |
| frontend/e2e/processing-pages/statePayloads.js | 124 | yes |
| frontend/e2e/processing-pages/stateRows.js | 221 | yes |
| frontend/e2e/processing-test-matrix.md | 48 | yes |
| frontend/e2e/profile-page-mocked.spec.js | 260 | yes |
| frontend/e2e/responsive-layout/apiMocks.js | 334 | yes |
| frontend/e2e/responsive-layout/index.js | 3 | yes |
| frontend/e2e/responsive-layout/layoutAssertions.js | 227 | yes |
| frontend/e2e/responsive-layout-manual-and-profile.spec.js | 118 | yes |
| frontend/e2e/responsive-layout-navigation-and-library.spec.js | 283 | yes |
| frontend/e2e/responsive-layout/processingMocks.js | 270 | yes |
| frontend/e2e/responsive-layout-processing.spec.js | 143 | yes |
| frontend/e2e/responsive-layout-property-and-access.spec.js | 159 | yes |
| frontend/e2e/responsive-layout-reader.spec.js | 81 | yes |
| frontend/e2e/responsive-layout.spec.js | 1 | yes |
| frontend/e2e/support/liveApp.js | 93 | yes |
| frontend/e2e/support/liveEnv.js | 57 | yes |
| frontend/e2e/support/playwright.js | 7 | yes |
| frontend/e2e/support/seedData.js | 71 | yes |
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
| policy/existing_large_files.txt | 46 | yes |
| policy/existing_migrations.txt | 44 | yes |
| pytest.ini | 6 | yes |
| README.md | 156 | yes |
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
| tools/test_env_tools.py | 41 | yes |
| verify_e2e_reprocessing.py | 86 | yes |
| **total** | **34416** | **220/220 yes** |

## 2. Behaviour catalogue (grouped by area; ids are per-area prefixes, each line cites file:line)


### 14a — notes: scripts, policy, root, common, legacy pipeline, spec books

Status: DRAFT (research evidence; read-only record)

IDs: S=scripts/policy, C=common, LP=legacy pipeline, SB=spec books.

#### Scripts and policy
- [S1] README: layers = backend pytest (Django, inside docker), frontend unit `node --test`, Playwright e2e against real Dockerized stack (not SQLite, not mocks for live ones). Seed data prefix "E2E " or `@e2e.local` — README.md:78-83
- [S2] verify.sh order: file-size policy -> architecture policy -> up postgres,redis,backend,frontend -> STOP worker,processing-worker,beat -> wait frontend/backend (120s, backend probe `/api/auth/session/` must return 2xx) -> seed e2e (manage.py seed_e2e_data) -> backend pytest -> frontend unit -> frontend build -> Playwright with `--workers=1` — scripts/verify.sh:98-130
- [S3] e2e script stops worker/processing-worker/beat so synthetic processing rows are not consumed; live-processing script (test-processing-live.sh) keeps them running, sets PLAYWRIGHT_RUN_LIVE_PROCESSING=1, no seeding, `--workers=1` — test-processing-live.sh:63-78
- [S4] Playwright config: testIgnore `**/processing-pages-live*` unless PLAYWRIGHT_RUN_LIVE_PROCESSING=1; timeout 45s; workers 1; fullyParallel false; viewport 1440x900; storageState = .auth/superadmin.json via globalSetup; chromium only; trace on-first-retry — playwright.config.js
- [S5] pytest.ini: DJANGO_SETTINGS_MODULE config.settings; marker `live` = needs live network to source site (deselect `-m "not live"`)
- [S6] regression_curate_300.sh: runs 300-book source-site regression harness in backend container; resumable (skips succeeded URLs); flags --limit, --retry-failed, --purge-exports; state JSON /app/storage/regression-300/state.json
- [S7] verify_e2e_reprocessing.py (root of tests, not a pytest test): picks 15 books with `normalized_source_url` containing "ebanglalibrary.com" (live source site name!), falls back to any non-deleted books; `queue_reprocess_book(book)` returns `(job, created)`; polls ProcessingJob.status in {"succeeded","failed"} every 5s up to 300s; exit 0 if all finished else 1.
- [S8] tools/test_env_tools.py: `parse_env_file` + `render_shell_exports` render `export KEY=<shlex.quote(value)>`; comments skipped; empty value -> `''`; already-quoted value kept literally (quotes quoted); `$` preserved literal; single quote escaped.
- [S9] Policy check-file-size: 300 physical lines max for .css .html .js .jsx .py .sh .ts .tsx .yaml .yml; excluded dirs .git dist node_modules public storage vendor; prefixes docs/ logs/; package-lock.json; exemptions from tests/policy/*.txt (lines, # comments). existing_large_files.txt lists 46 grandfathered files (incl. tests: test_ingestion_21 source_site_metadata_fidelity.py, test_curated_pipeline.py, test_access_05_notes.py, catalog-book-tables-mocked.spec.js). existing_migrations.txt lists 44 migrations (access 4, accounts 5, catalog 22, common 2, ingestion 8 (0001-0008), processing 3) — lists the legacy schema history (e.g. catalog 0020 book_last_kindle_sent_at -> 0021 userbookkindlesend -> 0022 remove column; accounts 0005 user_kindle_emails; ingestion 0008 booksubmission_deleted_status; processing 0003_processing_ui_state; catalog 0013 curated_book_documents, 0015 book_group_and_edition, 0012 userbook).
- [S10] Policy check-architecture: forbids numbered split module paths (`part-1`, `part_2`, `_parts/`), generated part-module loaders (glob("part_*.py"), "Generated loader preserving the public module path"), `apiFetch` outside `app/frontend/src/api/` or `features/<x>/api.(js|jsx|ts|tsx)`, and transport modules (backend `apps/**/views/`, `views.py`, `serializers/`) importing redis, requests, kombu, bs4, boto3, celery, config.celery.
- [S11] Test-split style: tests are split into `*_cases/` dirs with a thin aggregator file (e.g. test_access_01.py imports cases) to satisfy 300-line cap.

#### Saved filters (test_common.py)
- [C1] given logged-in user, when POST /api/saved-filters/ {target:"catalog", name:"Bangla Mysteries", params:{q:"রহস্য", category:"উপন্যাস"}} then 201; GET /api/saved-filters/?target=catalog 200 list with name; SavedFilter(owner,target) count 1; DELETE /api/saved-filters/<id>/ -> 204 — test_common.py:10-33

#### Legacy pipeline / exports (test_legacy_pipeline.py)
- [LP1] generate_exports(book_data) with structured author [{name}], series [{title}], book_type [{name}] writes `book.html` and `<book_title>.epub` (Bengali filename) in output_folder; html contains "cover-placeholder-card" (when cover empty), "ebook_preview_lock:" and "Preview already open" (preview single-open lock via localStorage-like key) — :6-28
- [LP2] existing cover file `book_cover.jpg` is inlined as data:image/jpeg;base64 even if requested cover name is `book_cover.jog` (wrong extension); wrong name not in HTML — :31-51
- [LP3] dedication section renders `<h2 class='dedication-title'>Dedication</h2>` + `<p>For readers.</p>`; the raw leading `<p>Dedication</p>` heading is stripped — :54-74
- [LP4] scraper.extract_dedication(main_content) returns (book_info, dedication, cleaned_content). Leading front matter lines "অনুবাদ: ..", "প্রথম প্রকাশ: .." go to book_info, removed from content, dedication "" — :77-94
- [LP5] Title-prefixed block (h2 title + strong title<br/>অনুবাদ: ...) and "প্রথম প্রকাশ: মার্চ ২০২৩" go to book_info; "ভূমিকা" stays in content — :97-116
- [LP6] Dedication heading "উৎসর্গ" excluded from dedication text; text up to next heading ("প্রারম্ভ কথন") — :119-135
- [LP7] Translator bio paragraph ("অনুবাদক ... পড়ালেখা করছেন") is NOT book_info; stays in content; but "অনুবাদ : X" (space before colon) is book_info — :138-156
- [LP8] Dedication stops before letter excerpt ("যে অনুষ্ঠানে ...", date, "প্রিয় আর্থার,") — :159-179
- [LP9] alias "অনুবাদ" must not match inside word "অনুবাদক": paragraph starting "অনুবাদক ..." yields book_info "" — :182-196
- [LP10] A lone "." paragraph ends the dedication section — :199-217
- [LP11] Inline dedication "উৎসর্গ : পাঠক, আপনাকে…" inside a big preface <p> is extracted; "উৎসর্গ" label dropped; preface "ভূমিকা" stays in content; dedication text removed from content — :220-243

#### Spec books (live, marked `live`) test_spec_books.py
- 13 reference books (URLs now anonymised example.com), per-book checks: bhumika (no cross-book links), shankha_ghosh (toc not empty + parent entries have titles), shopner_brishtimahal (has dedication, dedication not duplicated in front_sections), himu_baba (toc not empty, <=50 content items), hamlet (English book: book_info must not have Bengali labels শিরোনাম: লেখক: অনুবাদক: প্রকাশক: সম্পাদক:), 2001/sherlock/sati/lohit_kiran/hat_chuye/durga_rahasya (toc non-empty and book_info non-empty — "Book info page is empty — must always have content"), sidney_sheldon (toc), ba12_satyajit (toc + parents) — :26-257
- [SB-rules] cross-book link rule: any TOC/content_items URL containing "/books/" but not "/lessons/" is a violation; parent TOC entries with children must have non-empty title; toc empty only OK if main_content has plain text; dedication overlap heuristic >5 common words and >50% overlap flagged; front section containing "উৎসর্গ" in title/text flagged. API: `curate_book_document(url)` -> {"document":..., "projection":...} projection keys: toc, content_items, main_content, dedication, front_sections[{title,html}], book_info.

### 14b — notes: backend/auth (test_auth_01 + cases, test_auth_02)

Status: DRAFT (research evidence; read-only record)
Files: auth/test_auth_01.py (17, facade exec()-ing 4 case files), cases: totp_and_managed_user_invites (227), password_reset_flow (236), managed_user_admin_flow (259), password_setup_and_totp_invites (227), test_auth_02 (224). Abbrev: MU=managed_user_admin_flow, PR=password_reset_flow, PS=password_setup_and_totp_invites, TI=totp_and_managed_user_invites, A2=test_auth_02.

- [AU1] given user w/o device, when POST /api/auth/login/ {email,password} then 200; given user has confirmed TOTPDevice and no otp_token then 400 `code:"otp_required"`; with valid `otp_token` 200 and body has `email` — TI:58
- [AU2] only superadmin may POST /api/auth/users/ (regular user 403); superadmin creates with email, full_name, password, is_active, global_scopes -> 201, new user is_superuser False, is_staff False — TI:100
- [AU3] POST /api/auth/users/ with `send_invite_email:true` and no password -> user has unusable password (`check_password("")` False); 1 mail to the invitee; subject contains "Your RSalehin24 Library account is ready"; body link `http://127.0.0.1:5173/create-password?uid=..&token=..` (no `&amp;` in text body); HTML alternative text/html with inline styles "display: block;", "width: 100%;", "font-size: 18px" — TI:149
- [AU4] invite link host: if FRONTEND_BASE_URL has no port ("http://localhost") the FRONTEND_PORT setting (5173) is appended -> `http://localhost:5173/create-password?...`; HTML footer "This is an automated message from localhost:5173." — TI:193
- [AU5] superadmin create/update/delete managed user: create with totp_required True + global_scopes ["read:durable","download:file"] -> 201; active global grants (book null) == that set; PATCH {full_name,totp_required False,global_scopes:["metadata:edit"]} -> 200, grants REPLACED by exactly the new set; DELETE -> 204 and user row removed (hard delete) — MU:4
- [AU6] GET /api/auth/users/?offset=0&limit=60 with 76 users returns `rows` (60) and `pagination == {offset:0, limit:60, totalCount:76, hasMore:true, nextOffset:60}` (camelCase keys) — MU:63
- [AU7] list filters: `?status=disabled&sort=email_desc` -> only inactive users; `?q=metadata&status=all&sort=email_asc` matches by email/name AND by granted scope text (user with METADATA_EDIT grant); `?q=required&status=all&sort=name_asc` matches users with totp_required True (search term "required" hits the TOTP-required flag); sorts: email_asc, email_desc, name_asc — MU:92
- [AU8] superadmin PATCH own id -> 400 detail "You cannot edit your own account from Users & Access." — MU:149
- [AU9] POST /api/auth/password-reset/confirm/ while authenticated -> 400 detail "Please log out first before resetting a password from this link." (even for invalid uid/token) — MU:172
- [AU10] reset confirm for user with totp_required -> 200, `next_step:"totp_setup"`, user.totp_setup_required True, password changed, user is LOGGED IN (session authenticated true, totp_setup_required true) — MU:196
- [AU11] reset confirm for ordinary user -> 200 `next_step:"login"`, password changed, session stays unauthenticated — MU:231
- [AU12] POST /api/auth/password-reset/ {email} for existing user -> 200 detail "Reset email has been sent."; 1 mail to user; body link `<FRONTEND_BASE_URL>/reset-password/confirm?uid=` ; text "This link stays valid for 6 hours from the time it was generated."; no `&amp;`; HTML has "Reset your password", "Reset Password" (button), "This link stays valid for", "6 hours", "display: block;", "Reset password link:", "This is an automated message from 127.0.0.1:5173." — PR:10
- [AU13] password link expiry 6h (PASSWORD_RESET_TIMEOUT=21600): token validity checked via custom `PasswordLinkTokenGenerator` (clock injectable `_now`); POST /api/auth/password-reset/validate/ {uid,token} at +5h59 -> 200 detail "Password link is valid."; at +6h01 -> 400 "Reset token is invalid or expired." — PR:47
- [AU14] latest reset request invalidates previous links: two POSTs -> 2 mails, same uid, different token; first token validate/confirm -> 400 "Reset token is invalid or expired."; second -> 200 valid / confirm `next_step:"login"` — PR:93
- [AU15] reset confirm with new_password "short" -> 400 detail "Ensure this field has at least 12 characters." (clean message, not a dict; min length 12) — PR:176
- [AU16] reset request for invited user with `email_setup_pending=True` (no password) -> 404 "No user exist with this email.", no mail — PR:201
- [AU17] reset request for unknown email -> 404 "No user exist with this email." (account enumeration is intentionally allowed), no mail — PR:226
- [AU18] reset token is single-use: after successful confirm, same token -> validate 400 and confirm 400 "Reset token is invalid or expired."; password stays the first-set one — PS:4
- [AU19] resend setup email: POST /api/auth/users/<id>/resend-setup-email/ -> 200; new mail, same uid, new token; old create-password link invalid (validate 400 "Reset token is invalid or expired."), new valid; confirming sets password, `next_step:"login"`, `email_setup_pending` False; user has `can_resend_setup_email` True before; setup invites reuse /api/auth/password-reset/validate|confirm/ endpoints — PS:54
- [AU20] TOTP-required invite: after password set via invite link `next_step:"totp_setup"` and `email_setup_pending` stays True; resend-setup-email still 200 with `can_resend_setup_email:true` while TOTP unconfirmed; POST /api/auth/2fa/setup/ (user is logged in by confirm) creates unconfirmed TOTPDevice; POST /api/auth/2fa/confirm/ {token} 200 -> email_setup_pending False; thereafter resend -> 400 detail "This user does not need a setup email." — PS:132
- [AU21] TOTP-required user not yet configured: session.user.totp_required True & totp_setup_required True; GET /api/auth/2fa/status/ -> required True, setup_required True; other APIs (GET /api/catalog/books/) -> 403 `code:"otp_setup_required"`; POST /api/auth/2fa/setup/ -> 200 `provisioning_uri` starts "otpauth://" and contains issuer "RSalehin24%20Library", `qr_svg` contains "<svg"; POST /api/auth/2fa/cancel/ 200 -> status `pending_setup` False, `setup_required` still True; POST /api/auth/2fa/disable/ -> 400 (cannot disable when required) — A2:16
- [AU22] PATCH /api/auth/profile/ {full_name} updates name -> 200 — A2:70
- [AU23] profile kindle emails: user with SEND_KINDLE grant PATCH {kindle_emails_text:"reader@kindle.com\nreader-two@kindle.com\nreader@kindle.com"} -> stored `kindle_emails` deduped, order kept (["reader@kindle.com","reader-two@kindle.com"]); response contains kindle_emails and `kindle_sender_email` = settings.ACCOUNT_INVITE_FROM_EMAIL — A2:90
- [AU24] kindle email not ending @kindle.com -> 400 `{"kindle_emails": ["Enter a Kindle email ending in @kindle.com."]}` — A2:121
- [AU25] profile image: multipart PATCH {full_name, profile_image} -> 200; user.profile_image stored; response `profile_image_url` truthy — A2:147
- [AU26] profile password change: PATCH {current_password,new_password,confirm_new_password} -> 200, new password valid, session still authenticated (stays signed in) — A2:171
- [AU27] wrong current_password -> 400 with `current_password` error key; password unchanged — A2:201

Mock/flaky: tests use locmem email backend, patch of token-generator clock; no skips.

### 14c — notes: backend/access test_access_01 (+cases: download_reader_and_kindle 407, kindle_smtp_failures 243, kindle_validation_and_html_downloads 99, facade 16)

Status: DRAFT (research evidence; read-only record)
Fixtures pattern: Book(title, state="ready", review_state="approved") + GeneratedAsset(asset_type EPUB/HTML/COVER, status READY, legacy_path=<tmp file>, file_size) + PermissionGrant(user, book, scope).
Routes: GET /api/access/books/<slug>/download/{epub|html|cover}/, POST /api/access/books/<slug>/reader-launch/, POST /api/access/books/<slug>/send-to-kindle/

- [AC1] given user without grant, GET download/epub -> 403; with book-scoped DOWNLOAD_FILE grant -> 200 and Content-Disposition filename "Access Book.epub" (either `filename="X"` or RFC5987 `filename*=utf-8''<quoted>`) — download_reader_and_kindle.py:37
- [AC2] with PREVIEW_HTML grant, POST reader-launch -> 200 `{manifest_url}`; GET manifest_url -> 200 with `book.slug`, `reading_session_url`, `bookmarks_url` — :37-83
- [AC3] book OWNER (user has a BookSubmission with linked_book=book, status READY, resolution RESOLVED, input_type url) needs no explicit grants: list `/api/catalog/books/?ownership=mine` first row has `cover_download_url` ending `/api/access/books/<slug>/download/cover/`; book detail `assets[]` entries have `asset_type` + `download_url` for cover/html/epub; all three downloads 200 and reader-launch 200 — :85
- [AC4] download filenames use CURRENT book title, not stored file name: title "বর্তমান বই নাম" -> epub "বর্তমান বই নাম.epub", cover "বর্তমান বই নাম.jpg"; reader manifest `epub_download_url` also serves with the same filename — :155
- [AC5] send-to-kindle: user.kindle_emails=[a@kindle.com,b@kindle.com], SEND_KINDLE grant -> 200 payload `{deliveredEmails:[both], failedEmails:[], senderEmail:<ACCOUNT_INVITE_FROM_EMAIL>}`; one mail per address, empty body, attachment[0] filename "<Book Title>.epub" — :205
- [AC6] READ_ONCE grant: first reader-launch 200, second 403 — :238
- [AC7] READ_ONCE + PREVIEW_HTML: first GET download/html 200, second 403 (HTML preview counts as the one read) — :266
- [AC8] READ_ONCE + PREVIEW_HTML: after one HTML download, reader-launch 403 (HTML and reader share the single "once") — :295
- [AC9] READ_ONCE alone (no PREVIEW_HTML): download/html 403 (not consumed), reader-launch #1 200, #2 403 — :334
- [AC10] read:once and read:durable mutually exclusive: ManagedUserCreateSerializer with global_scopes ["read:once","read:durable"] invalid (error key `global_scopes`); PermissionGrantSerializer for a (user,book) already holding READ_ONCE adding read:durable invalid, message mentions "Read Once and Durable Read" — :376
- [AC11] Kindle via Brevo: when EMAIL_BACKEND is `anymail.backends.brevo.EmailBackend` (an API backend that cannot be used for attachments to Kindle), view builds an SMTP connection `django.core.mail.backends.smtp.EmailBackend` explicitly (get_connection(backend=smtp, host=EMAIL_HOST, port, username=EMAIL_HOST_USER, password=EMAIL_HOST_PASSWORD, use_tls)) and closes it; message body is "" — kindle_smtp_failures.py:12, :77
- [AC12] missing SMTP host/password -> 502 with detail containing "Kindle delivery requires SMTP", `failedEmails:[addr]`, `senderEmail` — :144
- [AC13] SMTPAuthenticationError(535) -> 502 detail contains "could not authenticate with Brevo SMTP" and "API key will not work for SMTP"; failedEmails=[addr]; connection closed — :184
- [AC14] kindle_emails not ending @kindle.com (legacy data "reader-two@example.com") are ignored at send time: only valid one delivered, failedEmails [] — kindle_validation_and_html_downloads.py:4
- [AC15] no Kindle emails configured -> 400 detail "Add at least one Kindle email in your profile before sending." — :36
- [AC16] HTML download inlines stale relative cover refs: HTML `<img src='book_image.hpg' class='cover-image'>` + ready COVER asset -> response contains `data:image/jpeg;base64,` and not the original src — :63

Mock heavy: monkeypatch of apps.access.views.assets.get_connection and EmailMessage.send (module path `apps.access.views.assets`).

### 14d — notes: backend/access test_access_02 (250), 03 (289), 04 (94), 05_notes (348), __init__ (0)

Status: DRAFT (research evidence; read-only record)

#### Preview HTML normalisation (test_access_02)  — function `normalize_preview_book_sections(soup, dedication_html=None) -> bool(updated)`; operates on the generated `book.html` DOM (BeautifulSoup html.parser)
- [AX1] given `div.dedication-section` with h2.dedication-title "উৎসর্গ" and content with redundant "উৎসর্গ", "উৎসর্গ :" paragraphs, then updated True and `div.dedication-content` text starts with the real text "পাঠক, আপনাকে" (redundant label paragraphs stripped) — test_access_02.py:33
- [AX2] no dedication section but `dedication_html="<p>উৎসর্গ : পাঠক, আপনাকে…</p>"` supplied (from book data) -> section inserted before main-content; text starts "পাঠক, আপনাকে" — :64
- [AX3] no `.main-content` at all (only container/book-header/toc-section) + dedication_html -> `div.dedication-section > div.dedication-content` still inserted — :90
- [AX4] standard Bengali dedication keeps title "উৎসর্গ"; content retained; returns updated True — :119
- [AX5] English dedication content (paragraph "Dedication" + "For everyone who kept reading.") -> heading becomes "Dedication", the repeated "Dedication" paragraph removed from content, text kept — :151
- [AX6] leading h2 sections in main-content before the first real chapter ("সহস্রাব্দ সংস্করণের কথা", "প্রারম্ভ কথন", before "অধ্যায় ১") are moved into `h2.front-section-title` blocks and removed from `.main-content`; "অধ্যায় ১" content stays — :184
- [AX7] missing stored file (GeneratedAsset.file path unlinked): GET download/cover -> 404 detail "This file is no longer available in storage. Please regenerate the book."; asset.status becomes FAILED, asset.file.name "" ; book.state "needs_review" and review_state "needs_review" (self-heal on missing file) — :224

#### Reader state, grants, scopes (test_access_03)
- [AX8] reading-session & bookmarks endpoints (`/api/access/books/<slug>/reading-session/`, `/bookmarks/`) GET -> 403 without reader access; with READ_DURABLE book grant POST reading-session {last_location:"chapter-1", progress_percent:12} -> 200; POST bookmarks {location,label,note} -> 201 — test_access_03.py:35
- [AX9] preview session token: PreviewAccessSession(book) .token; GET `/api/access/reader/<token>/html/` (no login needed) 200; HTML inlines stale relative cover (`book_image.hpg`) as data:image/jpeg;base64 — :61
- [AX10] preview HTML promotes leading front matter: "অনুবাদ: ..." and "প্রথম প্রকাশ: ..." extracted into a `book-info-section` and removed from `<div class="main-content">`; "ভূমিকা" stays — :98
- [AX11] only superadmin can manage grants: non-super GET /api/access/references/ -> 403; superadmin gets `account_scopes` and `scoped_scopes` lists of {value,...}; `admin:full_control` NOT in account_scopes; `access:manage` NOT in scoped_scopes; POST /api/access/grants/ {user, book, scope:DOWNLOAD_FILE, notes} -> 201; DELETE /api/access/grants/<id>/ -> 204 — :144
- [AX12] superadmin cannot create or delete a scoped grant for themselves: POST grant with user=self -> 403; deleting a grant whose user is self -> 403; for another user 201 — :179
- [AX13] category- and writer-scoped grants: grant with `category` applies to books in the category (BookCategory); grant with `contributor` applies to books with BookContributor role AUTHOR; `user_has_scope(user, [scope], book=...)` true only for matching books — :217
- [AX14] catalog endpoints require authentication: anonymous GET /api/catalog/books/ and /api/catalog/books/<slug>/ -> 403 (not 401) — :238
- [AX15] BookSource: unique per book (second BookSource for same book -> IntegrityError; one source per book); book detail `source_urls` and `source_records` are [] without VIEW_SOURCE_RECORDS grant; with grant -> `source_urls[0]` is URL, `source_records[0].url`; superadmin sees them automatically — :249

#### Reader token endpoints (test_access_04)
- [AX16] reader flow: launch -> manifest (`epub_download_url`, `reading_session_url`, `bookmarks_url`); epub is served as unzipped resources under `epub_download_url`: `META-INF/container.xml` (contains "OEBPS/content.opf") and `OEBPS/text/chapter-1.xhtml` ("Seeded EPUB chapter one for reader coverage."); GET/POST reading-session {last_location:"chapter-2", progress_percent:47} 200 echoing last_location; POST bookmarks 201; GET list len 1; DELETE `/api/access/reader/<token>/bookmarks/<id>/` 204. Note PREVIEW_HTML grant alone suffices for reader-launch — test_access_04.py:35

#### Notes (test_access_05_notes): models Highlight(user, book, cfi_range, text, color, kind), Bookmark(user, book, location, label), HighlightKind {HIGHLIGHT="highlight", QUOTE="quote"}
- [AX17] Highlight.kind defaults "highlight"; "quote" persists — :78, :92
- [AX18] GET /api/access/me/notes/ returns three buckets `bookmarks`, `highlights`, `quotes`; item `kind` field; quotes separate from highlights — :113
- [AX19] `?kind=quotes` or `?kind=highlights` returns only that bucket key (others absent); (`kind=bookmarks` implied) — :146
- [AX20] `?color=yellow` filters highlights only (with kind=highlights) — :180
- [AX21] `?q=hello` substring search over highlight text — :197
- [AX22] `?book=<slug>` filter — :214
- [AX23] unauthenticated -> 401 or 403 — :234
- [AX24] notes are per user (no leakage) — :240
- [AX25] reader token highlight endpoint (`manifest.highlights_url`) POST {cfi_range,text,color,kind:"quote"} -> 201 `kind:"quote"`, appears in quotes not highlights; omitted kind -> "highlight" — :263, :297
- [AX26] slug endpoint POST /api/access/books/<slug>/highlights/ {cfi_range,text,color[,kind]} -> 403 without read access; 201 with READ_DURABLE, `kind:"quote"` honoured — :329

### 14e — notes: backend/catalog_management test_01 (244), test_02 facade (16) + cases catalog_references_and_manual_books (253), exports_and_contributor_filters (128), my_books (64)

Status: DRAFT (research evidence; read-only record)
Helpers used: get_or_create_contributor/series/category, replace_book_relations(book, contributors=[{name,role}], series_names=, category_names=), Contributor.normalized_name, CATALOG_CODE_LENGTH, derive_category_catalog_code_from_book_code, derive_writer_catalog_code_from_book_code, MetadataVersion, MetadataReview.

- [CT1] PATCH /api/catalog/books/<slug>/metadata/ (superadmin) with title, summary, contributors [{name:"লেখক-এক",role:author},{name:"অনুবাদক এক",role:translator}], series ["রহস্য-সিরিজ"], categories ["উপন্যাস","উপন্যাস"], notes -> 200; names that differ only in punctuation/hyphen REUSE the existing Contributor/Series/Category (matched on normalized_name; counts stay 1); duplicate category in payload collapsed; MetadataVersion count for book == 2 (before + after snapshot) — test_catalog_management_01.py:33
- [CT2] Book slug and normalized_title preserve Bengali combining marks (title "ম্যালিস" -> slug "ম্যালিস", unicode slug); title change regenerates slug ("ম্যালিস-সমগ্র") on save — :70
- [CT3] duplicate titles allowed for same source_site (""): two books same normalized_title, different slugs — :85
- [CT4] detail lookup accepts `slugify(title, allow_unicode=True)` legacy slug — :102
- [CT5] book detail derives contributors from `book_info_html` front matter when missing: "অনুবাদ: অনুবাদক এক" -> contributors has {name, role:"translator"}; "প্রকাশক: প্রকাশনী ঘর" -> role "publisher"; `front_matter` list of {key:"first_published", label:"প্রথম প্রকাশ", value:"২০০৫", role:""} (translator/publisher are NOT repeated in front_matter; only other keys like first_published) — :114
- [CT6] fallback to leading `main_content_html` when book_info empty: translators "সালমান হক", "ইশরাক অর্ণব" split on comma as two translator contributors; front_matter first_published "মার্চ ২০২৩" — :145
- [CT7] if same person listed as author AND translator (from book_info), detail `authors` hides them (["সালমান হক"] only), contributors has translator role not author for that person — :178
- [CT8] list endpoint `/api/catalog/books/` rows include `authors` (names, authors only) and `contributors` ([{name,role}]) incl. translators for card display — :204
- [CT9] author names with initial periods preserved ("আর্থার সি. ক্লার্ক") in list & detail (no splitting at '.') — :222
- [CT10] catalog codes: category, contributor (writer), book each get `catalog_code` of length CATALOG_CODE_LENGTH; all distinct; book code ENCODES category and writer codes: derive_category_catalog_code_from_book_code(book.code)==category.code, derive_writer_...==writer.code — catalog_references_and_manual_books.py:33
- [CT11] reference listing endpoints for a normal logged-in user: GET /api/catalog/{categories,series,writers,translators,compilers,editors,publishers}/ -> 200 arrays of {name, catalog_code, book_count}; counts 1; names are cleaned (trailing stray ")" removed from "তালিকা অনুবাদক)"); junk/non-name contributors ("and elaborate purports") excluded from translators; editors endpoint = union of editor and compiler role contributors — :58
- [CT12] reference listing search `q` is normalised for Bangla: punctuation ignored ("ড. মুহম্মদ শহীদুল্লাহ" found by "ড মুহম্মদ শহীদুল্লাহ"; "অ-আ সিরিজ" by "অ আ সিরিজ"; "ভাষা-বিজ্ঞান" by "ভাষা বিজ্ঞান"); param `record_type=all` — :130
- [CT13] reference listing optional pagination: `?page=2&limit=2` -> `{entries:[...], pagination:{page, limit, total_count, page_count, has_previous, has_next}}` (3 items -> page 2 has 1 entry, page_count 2, has_previous true, has_next false); without page/limit it is a plain array — :157
- [CT14] POST /api/catalog/manual-books/ (any logged-in user) with title, summary, writers[], translators[], compilers[], editors[], categories[], series[], is_compilation, binding:"paper_back", publisher, price:"350.00" -> 201; payload `record_type:"manual"`, catalog_code length OK, translators list, `compilers == []` and `editors == [compiler, editor]` (compilers merged into editors), `is_compilation true`, `binding == "Paper Back"` (humanised), publisher, `price == "350.00"` string; relations created (author, category, publisher contributors) and book code derives writer/category codes; GET /api/catalog/manual-books/ only record_type manual and includes it; default GET /api/catalog/books/ EXCLUDES manual records; `?record_type=all` includes them — :189
- [CT15] manual-book listing pagination same shape as reference listing (entries/pagination) — exports_and_contributor_filters.py:4
- [CT16] GET /api/catalog/books/export/?format=csv -> 200 text/csv (utf-8 with BOM, decode `utf-8-sig`); header contains "Book ID,Title,Writer / Translator / Editor / Publisher"; cell strings "Translator: <name>", "Publisher: <name>", compiler and editor names merged into the same column — :41
- [CT17] book list filter `contributor_code=<code>&contributor_role=translator&record_type=all` returns only books where that contributor has that role — :71
- [CT18] `contributor_role=editor` filter also includes books where the contributor has legacy role `compiler` — :90
- [CT19] PDF export `/api/catalog/books/export/?format=pdf` -> application/pdf starting `%PDF`; `/api/catalog/books/tickets/` -> application/pdf (label/ticket sheet). Test skipped if `reportlab` missing (importorskip) — :109
- [CT20] My Books: row has `is_in_my_books` False, `my_books_added_at` None; POST /api/catalog/books/<slug>/my-books/ idempotent (twice 200, one UserBook), returns is_in_my_books True + my_books_added_at; `?ownership=mine` returns only user's books; detail has `is_in_my_books`; DELETE idempotent (204 twice), then `ownership=mine` == [] — my_books.py:9
- [CT21] creating a BookSubmission with `linked_book` (status ready, resolution resolved) automatically creates UserBook ownership (signal/model save) -> appears in `ownership=mine` — :46

### 14f — notes: backend/catalog_management test_03 (201), test_04 (257)

Status: DRAFT (research evidence; read-only record)

- [CT22] staff (superadmin) POST /api/ingestion/duplicate-reviews/<id>/resolve/ {decision:"confirm_existing", notes} -> 200; submission.linked_book = existing_book, submission.status "ready", review.status "confirmed". Fixture: submission(input_type title, resolution_confidence 0.82, status duplicate, review_state needs_review) + DuplicateReview(submission, existing_book) — test_catalog_management_03.py:33
- [CT23] METADATA_EDIT book-scoped grant lets a non-staff user PATCH /api/catalog/books/<slug>/metadata/ {summary, notes} -> 200 — :67
- [CT24] metadata update dedups roles per person: payload [{ইশরাক, author},{ইশরাক, translator},{কেইগো, author},{কেইগো, editor}] -> stored (ইশরাক, translator) and (কেইগো, editor) ONLY; author role dropped when same name has translator or editor role — :85
- [CT25] METADATA_EDIT book grant allows DELETE /api/catalog/books/<slug>/ -> 204, soft delete: deleted_at set, state "soft_deleted" — :115
- [CT26] user without METADATA_EDIT DELETE book -> 403, deleted_at None — :130
- [CT27] PROCESSING_MANAGE global grant (non-staff) can resolve duplicate reviews (confirm_existing links book) — :143
- [CT28] metadata-reviews: POST /api/catalog/books/<slug>/metadata-reviews/ {state:"approved", notes} (editor with METADATA_EDIT) -> 201, book.review_state="approved", 1 MetadataReview; GET list -> [{state:"approved"}]; PATCH /api/catalog/metadata-reviews/<id>/ {state:"rejected",notes} -> 200, book.review_state "rejected" — :174
- [CT29] `?ownership=mine&sort=-requested_at`: only books where user has a submission linked; ordered by user's newest submission created_at desc (shared_book newest 2h ago before owner_book 2 days ago); other users' books excluded; rows have `latest_submission_at` (latest submission of THAT user) — test_catalog_management_04.py:35
- [CT30] book list paginated when `page` & `limit` given: `?record_type=all&sort=created_at&limit=2&page=2` -> `{entries:[...], pagination:{page, limit, total_count, page_count, has_previous, has_next}}`, `sort=created_at` ascending (third created book on page 2) — :96
- [CT31] book search normalises Bangla punctuation: q "অ আ ক খুনের কাঁটা" matches title "অ-আ-ক-খুনের কাঁটা"; `series=` filter "পি কে বাসু কাঁটা সিরিজ" matches "পি. কে. বাসু - কাঁটা সিরিজ"; `category=` "গোয়েন্দা ডিটেকটিভ" matches "গোয়েন্দা (ডিটেকটিভ)" — :119
- [CT32] performance rule: book list query must NOT select heavy columns summary, raw_scraped_metadata, raw_scrape_payload, main_content_html, book_info_html, dedication_html, toc, content_items (deferred) — :149
- [CT33] metadata editor POST /api/catalog/books/<slug>/assets/epub/ multipart `file` -> 200; replaces EPUB: asset.status ready, file_size = new length, legacy_path cleared "", new bytes stored in file field, OLD file deleted from disk, response `assets[]` includes epub — :188
- [CT34] metadata editor POST /api/catalog/books/<slug>/regenerate/ {} -> 202 `{created:true, job:{job_type:"reprocess"...}, book:{state:"processing", latest_processing_job:{status:"queued"}}}`; calls `queue_reprocess_book(book, actor=user)` (mocked in test via monkeypatch "apps.catalog.views.queue_reprocess_book") — :215

### 14g — notes: backend/engine (Central Job Engine, Redis pub/sub) — files conftest 247, constants 24, helpers 199, __init__ 0, test_all_job_types 178, test_concurrent_operations 151, test_dispatch_integration 192, test_engine_api 164, test_engine_recovery 233, test_job_dispatch 214, test_processing 228, test_queue_management 177, test_stale_detection 151, test_worker_lifecycle 203

Status: DRAFT (research evidence; read-only record)

#### Architecture revealed by the tests (all run against REAL Redis + real Postgres in Docker, no mocks; slow, sleep-based)
- Engine class `JobEngine(redis_client, heartbeat_timeout=15, heartbeat_check_interval=2.0)` with `.start()`/`.stop()` (background thread subscribing to channels). Module functions: `list_workers(status=None)`, `get_job_status(job_id)`, `get_queue_depth()`, `get_worker_detail(hostname)`, `reassign_job(job_id, hostname)->bool`, `get_engine_status()` -> {running, worker_count, queue_depth, active_jobs}, `dispatch_job(job_id, job_type, handler)` (Django side).
- Redis keys: `engine:worker:{hostname}` (hash: hostname, status, capabilities (JSON list), current_job, registered_at, last_heartbeat, pool_size, concurrency), `engine:queue:pending` (list, FIFO), `engine:active` (hash job_id -> hostname), `engine:job:handlers` (hash job_id -> handler), `engine:state`.
- Channels: engine:channel:worker:{register,heartbeat,deregister,done,stale}, engine:channel:job:{request,assigned,reassigned,completed}.
- Worker statuses: idle, processing, stale, offline. Heartbeat timeout 15s (test constant).
- Messages: register {hostname, capabilities, pool_size, concurrency, timestamp}; heartbeat {hostname}; done {hostname, job_id, status succeeded|failed, error_message}; job request {job_id, job_type, handler, args}. `publish_job_request` helper: HSET handlers, RPUSH queue, PUBLISH request. `dispatch_job` (Django) does the same (queue + handler saved immediately, even with engine down).

#### Behaviours
- [EN1] given idle worker w/ capability matching handler, when job request published then job in `engine:active` -> worker hostname, worker status processing; worker is the only one assigned (never double-assigned) — test_job_dispatch.py:19, :100
- [EN2] given single worker busy, second job is queued (queue len 1) and not active; when first completes, next queued job assigned and queue empties (workers have concurrency 1) — test_job_dispatch.py:33, :51; test_processing.py:41
- [EN3] FIFO: queue order == publication order — test_job_dispatch.py:75; with several workers the set is checked (order may vary) — test_queue_management.py:96
- [EN4] routing is by HANDLER capability, not job_type: handler "catalog_sync" goes to worker with capabilities ["catalog_sync"] even if job_type "process"; handlers seen: process_submission (reprocess), catalog_sync (ingestion, catalog_sync), curation, automation, pipeline; unknown handler with no capable worker stays queued (queue 1, not active) — test_job_dispatch.py:127,158; test_all_job_types.py:19-178
- [EN5] queued job retains its handler until a capable worker frees up; CH_JOB_ASSIGNED event {job_id, worker_hostname, handler:"pipeline"} — test_job_dispatch.py:177
- [EN6] completion: job removed from active, worker status idle, current_job ""; CH_JOB_COMPLETED event {job_id, status:"succeeded"}; failure event {status:"failed", error_message}; failure frees worker and does NOT auto-consume (queue later assigned normally); double completion is idempotent — test_processing.py:19-228
- [EN7] N workers/M jobs: first N jobs active, rest queued (2 workers/5 jobs -> 3 queued; 3 workers/9 jobs -> 6 queued, 3 active; 2 workers/10 jobs: active+queue==10, no loss); freed workers pick next queued — test_queue_management.py, test_concurrent_operations.py
- [EN8] concurrent: two workers + two jobs each get one; 10 simultaneous registrations all register; double completion from two workers of same job leaves job inactive — test_concurrent_operations.py:19-135
- [EN9] registration: key created with status idle, capabilities JSON; re-register same hostname updates capabilities (["catalog_sync"] replaces); sets `registered_at` — test_worker_lifecycle.py:19-66
- [EN10] heartbeat updates `last_heartbeat`; idle stays idle — :80, :94
- [EN11] stale detection (with checker): no heartbeat for HEARTBEAT_TIMEOUT(15)+ s -> status "stale", CH_WORKER_STALE {hostname}; idle worker also goes stale but no jobs requeued; a heartbeat from a stale worker returns it to idle — test_stale_detection.py:19,32,84,98; test_worker_lifecycle.py:107,119
- [EN12] stale worker holding a job: job reassigned to a healthy idle worker (within ~10s), CH_JOB_REASSIGNED {job_id}; in DB test `ProcessingJob.worker_hostname` updated to healthy worker — test_stale_detection.py:46,115; test_dispatch_integration.py:125
- [EN13] deregister removes worker key; idempotent; unknown worker no-op; deregistering a worker with a current_job removes job from active and RE-QUEUES it (lpos in pending) — test_worker_lifecycle.py:139-203
- [EN14] API: list_workers (+status filter), get_job_status -> {job_id, worker_hostname, status:"processing"} or None when unknown/completed, get_queue_depth (1 active + 4 queued -> 4), get_worker_detail incl. capabilities or None, reassign_job(job_id, new_hostname) True and active owner changes, get_engine_status keys — test_engine_api.py
- [EN15] DB sync: engine on assignment writes `ProcessingJob.worker_hostname`; on completion sets `status "succeeded"` + `finished_at`; on failure `status "failed"` + `last_error` message (needs django_db(transaction=True)) — test_dispatch_integration.py:27-82
- [EN16] dispatch while engine down: `dispatch_job` immediately puts job in `engine:queue:pending` and handler in `engine:job:handlers`; a later-started engine + registering worker assigns it — test_dispatch_integration.py:164
- [EN17] restart recovery: workers remain registered after engine restart; pending queue is re-processed; active jobs of offline/missing workers are removed from active and re-queued; active jobs of live workers remain mapped (worker stays processing); completed jobs stay completed — test_engine_recovery.py:19-130
- [EN18] startup DB recovery (after Redis wiped): QUEUED and PROCESSING `BookCreationRequest` rows (model with book_record -> BookRecord(id,name,url), states QUEUED/PROCESSING) and QUEUED `ProcessingJob` rows are re-enqueued into `engine:queue:pending`; PROCESSING requests reset to QUEUED in DB; handlers set: BookCreationRequest -> "pipeline", ProcessingJob -> "process_submission" — test_engine_recovery.py:155
- [EN-test] conftest: session-scoped real Redis client (REDIS_HOST or CELERY_BROKER_URL env, default redis://redis:6379/0), autouse fixture deletes all `engine:*` keys before each test; `engine` fixture starts engine thread + 0.2s sleep; `engine_with_heartbeat_check` timeout 15s check 2s; `captured_events` pubsub capture for assigned/reassigned/completed/stale. Fakes: `FakeWorker` (register, heartbeat, claim_job, complete_job, fail_job, deregister).
- Rebuild note: this engine is infrastructure the rebuild may replace; contract value = states (idle/processing/stale/offline), capability-based routing, FIFO, requeue-on-worker-death, DB recovery on startup, idempotent completion.

### 14h — notes: backend/processing top-level: test_processing_api.py (37, facade exec of 24 case files), test_processing_contract.py (196), test_processing_db_consistency.py (73), test_processing_source.py (160)

Status: DRAFT (research evidence; read-only record)

- [PR1] Processing data model contract: BookRecord fields id (string PK, e.g. "test-record-1"), name, url, category, writer, translator, composer, publisher, created_at, updated_at, book_creation_state (choices == BookCreationState.values); BookCreationRequest fields id (string PK), book_record FK->BookRecord, state (choices == BookCreationRequestState.values), created_at, updated_at, progress (nullable), error_message (blank), is_resumed, is_confirmed_not_duplicate, duplicate_of_request (nullable), duplicate_of_record (nullable), linked_book (nullable); ProcessingUiDomainVersion(domain, version, created_at, updated_at); ProcessingUiProjection(key, payload, created_at, updated_at) — test_processing_contract.py:29
- [PR2] admin registered with fields: BookRecord adds linked_book, was_incomplete, resolved_from_incomplete, will_resolve_to_category, is_duplicate, duplicate_of_record; BookCreationRequest adds duplicate_confirmed, pipeline_outcome; ProcessingSyncState(singleton_key, status, progress, remote_pages, page_index, fetched_count, skipped_count, updated_count, appended_count, message); ProcessingAutomationSettings(kind, enabled, interval, time, saved, last_run_at, status_message) — :82
- [PR3] Celery task names must be discoverable: apps.processing.tasks.run_processing_sync_task, apps.processing.tasks.kickoff_book_creation_request_task, apps.ingestion.tasks.run_catalog_automation_schedule_task, apps.ingestion.tasks.recover_stale_processing_jobs_task — :171
- [PR4] Debug settings include dev ports: CSRF_TRUSTED_ORIGINS has http://127.0.0.1:5181, CORS_ALLOWED_ORIGINS http://localhost:5181 — :179
- [PR5] GET /api/processing/state/ -> 403 for anonymous and for regular user without processing access — :185
- [PR6] DB trigger consistency (Postgres triggers): updating BookCreationRequest.state via ORM bulk update() mirrors into BookRecord.book_creation_state ("initial" -> "failed"); raw SQL UPDATE processing_bookcreationrequest SET state='created' mirrors "created"; afterwards a direct BookRecord.objects.update(book_creation_state="failed") is OVERRIDDEN back to "created" (record state is derived from request state; trigger enforces) — test_processing_db_consistency.py:10, :39
- [PR7] processing source helpers (apps.processing.source): `normalize_source_url("https://example.com/books/example-book")` -> "https://www.example.com/books/example-book/" (adds www and trailing slash); `scrape_book(url)` calls scraper.scrape_book_data(normalized_url, content_limits={max_nodes:48,max_depth:3,max_lesson_pages:2,max_content_chars:12000,disable_recursive:False}) (cheap "processing" limits); `generate_exports(payload)` calls html_book.create_html_book(payload) and epub_book.create_epub(payload); must NOT use ingestion legacy_adapter — test_processing_source.py:5
- [PR8] limits are configurable via settings PROCESSING_SCRAPER_MAX_NODES/_MAX_DEPTH/_MAX_LESSON_PAGES/_MAX_CONTENT_CHARS/_DISABLE_RECURSIVE — :71
- [PR9] `scrape_book_high_fidelity(url)` uses large recursive limits: max_nodes 320, max_depth 6, max_lesson_pages 20, max_content_chars 120000, disable_recursive False — :87
- [PR10] network.get_soup(url): session from create_session_with_retries(retries=3, backoff_factor=1); fetch through get_with_host_fallback (tries host variants) with headers=network.HEADERS, timeout=30; response bytes decoded as UTF-8 even if encoding header missing (Bangla heading preserved); session closed — :119
- Mock heavy: monkeypatch of scraper/network internals.

### 14i — notes: backend/processing/test_processing_api_cases part 1 (catalog sync two-phase state machine)

Status: DRAFT (research evidence; read-only record)
Files: helpers.py (246), catalog_matrix_helpers.py (67), catalog_manual_matrix_cases.py (225), catalog_automation_matrix_cases.py (234), incomplete_catalog_and_domain_versions.py (158), catalog_phase_matrix_tests.py (224), catalog_phase_pause_behaviour.py (214), catalog_phase_resume_flows.py (270).

#### Test harness (reveals API shape)
- State endpoint `GET /api/processing/state/[?includeLists=0]` returns JSON with `sync` (status, phase, runMode, pageIndex, fetchedCount, updatedCount, message, progress{phaseStatuses{sync,request_creation}, phaseStates{sync|request_creation:{status, owner, savedData, baseSyncCheckpointToken}}, requestCreation{baseCheckpointToken,lastRecordId,processedCount,createdCount,unsupportedCount}, savedData{runMode,triggerSource,sessionId,checkpointToken,nextPageIndex,fetchedCount}}) and `automation.catalog.statusMessage`.
- Mutation endpoints return `{ok:true, versions:{<domain>:<n>...}}` (UI domain version map, `PROCESSING_CARD_KEYS`) — client refetches via versions. Test harness has "advance" endpoints POST /api/processing/sync/advance/ (optional /sync/<scope>/advance/) and /api/processing/pipeline/advance/ -> {advancedCount} which tests call in place of background workers (deterministic ticking).
- Sync endpoints seen: POST /api/processing/sync/start/ (body optional {remotePages:[[...records], ..., []]} for tests), /sync/pause/, /sync/resume/ {runMode}, /sync/catalog/pause/, /sync/catalog/resume/ {runMode: manual|catalog_automation}, /automation/catalog/run/, /automation/incomplete/run/.
- Record payload for remote pages: {id, name, url, category, writer, translator, composer, publisher, updatedAt}.
- Status vocabularies: top-level sync status in {idle, syncing, pausing, paused}; phase status in {not_started, running, pausing, paused, completed}; phase in {sync, request_creation}; runMode in {manual, catalog_automation, incomplete_automation}; trigger source "button"; compat: `phaseStatuses` maps "pausing"->"running"; `phaseStates` keeps real value.
- Two phases: Phase 1 "sync" (fetch remote catalog pages -> BookRecord upserts), Phase 2 "request_creation" (create BookCreationRequest state "initial" for each record, batch size constant CATALOG_REQUEST_CREATION_BATCH_SIZE), each with owner (manual | catalog_automation), checkpoint tokens (`catalog_sync_checkpoint_token(session_id, next_page_index, fetched_count)`); request-creation is anchored to a base sync checkpoint token.

#### Behaviours
- [PA1] automation rerun after completion: automation/catalog/run -> sync, advance -> request_creation, advance -> status idle with both phaseStatuses completed; running automation again restarts from page 0: status syncing phase sync, pageIndex 0, fetchedCount 0, message "Automated catalog sync is running.", sync running, request_creation not_started, no `requestCreation` key — catalog_phase_matrix_tests.py:4
- [PA2] Manual matrix (initial -> action -> expected) from catalog_manual_matrix_cases.py (sync_status,request_creation_status):
  1. (not_started,not_started) + POST /sync/start -> syncing/sync/manual, sync running
  2. (running,not_started) + /sync/catalog/pause -> status pausing, sync pausing
  3. (pausing,not_started) + /sync/start -> stays pausing (no-op)
  4. (paused,not_started) + /sync/catalog/resume {runMode:manual} -> syncing, sync running
  5. (completed,not_started) + /sync/start -> syncing/sync running (restart) request_creation not_started
  6. (completed,running[owner catalog_automation]) + /sync/start -> status syncing, PHASE request_creation, runMode catalog_automation (manual start does NOT interrupt running automation request creation; it just reports it), requestCreation payload kept
  7. (completed,pausing) + /sync/start -> pausing/request_creation/catalog_automation
  8. (completed,paused) + /sync/start -> syncing, phase sync running, runMode manual, request_creation stays paused with its checkpoint (new sync runs while phase-2 stays paused)
  9. (completed,completed) + /sync/start -> syncing sync running, request_creation reset to not_started, requestCreation cleared
  10. (paused,paused) + /sync/catalog/resume {manual} -> syncing sync running, request_creation stays paused with checkpoint
- [PA3] Automation matrix (catalog_automation_matrix_cases.py) with POST /automation/catalog/run (or resume {runMode:catalog_automation}):
  1. (not_started,not_started) run -> syncing/sync, runMode catalog_automation, sync owner catalog_automation
  2. (running,not_started) + /sync/catalog/pause -> pausing/sync
  3. (pausing,not_started) + run -> stays pausing
  4. (paused,not_started) + resume -> syncing sync running
  5. (completed[manual],not_started) + run -> syncing PHASE request_creation (phase 1 skipped because sync completed), request_creation running owner catalog_automation, requestCreation {baseCheckpointToken, lastRecordId "", processedCount 0, createdCount 0, unsupportedCount 0}
  6. (completed,running) + pause -> pausing/request_creation
  7. (completed,pausing) + run -> stays pausing
  8. (completed,paused) + resume(auto) -> syncing/request_creation running (resumes phase 2)
  9. (completed,completed) + run -> restart: syncing/sync, sync owner catalog_automation, request_creation not_started, requestCreation None
  10. (paused,paused) + resume(auto) -> syncing/request_creation, sync stays paused, request_creation running
- [PA4] pausing phase 1 while phase 2 paused: pause request keeps phase-2 checkpoint (processedCount 7, createdCount 5, lastRecordId, baseSyncCheckpointToken unchanged); serialize_sync_state keeps `phaseStates.sync.status=pausing` with savedData.checkpointToken and `phaseStates.request_creation.status=paused`; phaseStatuses sync "running" (compat) — catalog_phase_matrix_tests.py:102, :148
- [PA5] automation run from a completed sync checkpoint starts phase 2 directly: message "Creating book requests from the synced catalog records.", phaseStates.request_creation.baseSyncCheckpointToken == requestCreation.baseCheckpointToken — :192
- [PA6] data repair: if stored progress claims BOTH phases running, serialization normalises: when progress.phase == "sync" -> sync running, request_creation paused; when phase == "request_creation" -> sync completed, request_creation running — catalog_phase_pause_behaviour.py:19
- [PA7] pause requested during a page advance is honoured: after the current page upsert, sync status paused, savedData.nextPageIndex 1, fetchedCount 1; page 1 records persisted, page 2 not — :117
- [PA8] same for incomplete sync batch advance: runMode "incomplete_automation", status paused, updatedCount 1, only first record resolved_from_incomplete True — :158
- [PA9] manual sync start takes over a paused automation runtime: automation run -> pause (pausing) -> advance -> paused (runMode catalog_automation, fetchedCount 1) -> POST /sync/start -> syncing, runMode "manual", message "Continuing catalog sync from the saved endpoint.", pageIndex 1 fetchedCount 1 (resumes from saved page, does not restart); final advance -> idle; records persisted; NO BookCreationRequest created (manual sync does not create requests) — catalog_phase_resume_flows.py:4
- [PA10] automation run takes over paused manual runtime: message "Continuing automated catalog sync from the saved endpoint.", runMode catalog_automation, pageIndex 1; subsequent advance enters request_creation then idle; BookCreationRequest rows created — :52
- [PA11] request creation phase pause/resume: with batch size 1 and 2 existing + 1 synced record: pause -> message "Pausing automated request creation after the current batch finishes."; advance -> paused, requestCreation processedCount 1, createdCount 1; POST /sync/resume/ {runMode:"catalog_automation"} -> message "Resuming automated request creation from saved progress."; advances -> processed 2 ... finally idle; 3 BookCreationRequest rows state "initial"; `automation.catalog.statusMessage == "Created 3 requests."` — :100
- [PA12] manual start from paused automation request creation preserves phase-2 checkpoint: new manual sync message "Syncing catalog records.", pageIndex 0 fetchedCount 0, request_creation remains paused with processedCount 1 and OLD baseSyncCheckpointToken; when manual sync completes, status paused with message starting "Sync complete.", sync phaseStatus completed (new checkpoint token differs), request_creation still paused; BookCreationRequest count remains 1; then automation run resumes phase 2 with message "Resuming automated request creation from saved progress." using the OLD base token; advancing completes -> idle, 2 requests — :172
- [PA13] parse_incomplete_catalog_page(soup): reads `article h2.entry-title a` -> entries {source_url (made absolute https://www.example.com/books/...), title "Sample Incomplete Book", author_line "Sample Author" (split on " - "), raw_data.metadata_source "incomplete_archive_page"} — incomplete_catalog_and_domain_versions.py:3
- [PA14] fetch_live_incomplete_page(...) returns [] when a paginated page HTTP 404s (end of archive) — :35
- [PA15] UI domain invalidation rules: `processing_domains_for_request_change(old_state,new_state,record=)`: regular request change -> includes "create-requests" and "create-queue", excludes incomplete domains (PROCESSING_CARD_INCOMPLETE_OVERVIEW, "incomplete-records", "incomplete-completed"); request progression also includes "catalog-overview", "catalog-records"; `processing_domains_for_record_change(before,after,current_request_state=)`: when an incomplete record becomes resolved (category replaced, resolved_from_incomplete True, state created) includes incomplete overview, "incomplete-records", "incomplete-completed"; during hydration (before None) includes overview and records but NOT "incomplete-completed" — :62-158
- Domain keys seen: create-requests, create-queue, catalog-overview, catalog-records, incomplete-records, incomplete-completed, PROCESSING_CARD_INCOMPLETE_OVERVIEW.

### 14j — notes: processing api cases part 2: catalog_phase_serialization (168), catalog_sync_parallel (217), catalog_sync_persistence (218)

Status: DRAFT (research evidence; read-only record)

- [PB1] manual and automation resume DIFFERENT paused phases from the same both-paused state: given sync paused + request_creation paused (manual owner for sync), POST /sync/start -> syncing/sync, runMode manual, message "Continuing catalog sync from the saved endpoint.", sync running, request_creation stays paused with identical requestCreation payload; POST /automation/catalog/run from same state -> syncing/request_creation, runMode catalog_automation, message "Resuming automated request creation from saved progress.", sync stays paused, request_creation running — catalog_phase_serialization.py:4
- [PB2] legacy progress migration on read: stored progress {runMode catalog_automation, phase request_creation, checkpoint, savedData{sessionId, checkpointToken "legacy-catalog-session:0:1:1", nextPageIndex, fetchedCount, requestCreation{...}}} with status paused -> serialize_sync_state yields phaseStatuses sync completed / request_creation paused, phaseStates with baseSyncCheckpointToken from requestCreation.baseCheckpointToken — :67
- [PB3] legacy pausing progress (status pausing, phase sync, phaseStatuses sync running / request_creation paused, savedData.requestCreation with baseCheckpointToken legacy-catalog-pausing:0:1:4) -> status stays pausing; phaseStates.sync.status pausing with savedAt preserved; request_creation paused with its old base token — :116
- checkpoint token format: "<sessionId>:<?0>:<nextPageIndex>:<fetchedCount>" e.g. "legacy-catalog-pausing:0:2:8".
- [PB4] refresh_catalog_parallel(concurrency=n) (source catalog refresh from archive pages; deps mocked: create_session_with_retries, TitleResolver.archive_query_params/parse_catalog_page, get_with_host_fallback, fetch_source_page_metadata, upsert_source_catalog_entry, source_catalog_entry_payload, upsert_remote_records): returns {appended_count, updated_count, total}: empty page -> zeros; single page of 2 -> total 2; stops at first empty page (3 pages + [] -> total 3); duplicate URLs across pages deduplicated (total 2); entry whose metadata fetch raises is skipped (others counted); page whose fetch raises is skipped but crawling continues to later pages (total 1) — catalog_sync_parallel.py:152-208. (Page query params are `page` and `q`.)
- [PB5] manual sync persistence: records pushed through `remotePages` (test hook in POST /sync/start/ body) are NOT written at start (existing "Existing" unchanged; updatedCount 0, status syncing); each /sync/advance/ processes one page: page 1 updates existing record (name, url, category, writer, translator, publisher all replaced from remote; updatedCount 1), page 2 appends new record (appendedCount 1); pause -> pausing; advance -> paused with savedData.nextPageIndex 2; resume -> syncing; advance -> idle with skippedCount 0, appendedCount 1; starting again resets: message "Syncing catalog records.", pageIndex 0, fetchedCount 0 — catalog_sync_persistence.py:4
- [PB6] sync progress is mirrored into a checkpoint store (Redis) under `processing_sync_checkpoint_key("catalog")` as JSON {status, progress.savedData.nextPageIndex, fetchedCount,...} on start/pause/advance, and the key is DELETED on POST /api/processing/sync/stop/ — :137 (store faked via processing_checkpoint_client)
- [PB7] when no remotePages are provided, sync reads persisted `SourceCatalogEntry` rows (source_url, title, author_line, normalized_title, normalized_display, raw_data{category, publisher}) and creates BookRecord with id=str(entry.id), name=title, url=source_url, category=raw_data.category, writer=author_line, publisher=raw_data.publisher; two advances -> idle — :193

### 14k — notes: processing api cases part 3: checkpoint_and_dispatch_recovery (218), duplicate_resolution_actions (299), incomplete_automation_flows (253)


- [PC1] stale Redis checkpoint mirror is repaired from DB: DB sync_state paused pageIndex 3 fetched 42; mirror says pageIndex 1/fetched 7; after serialize_sync_state + sync_checkpoint_progress, payload pageIndex 3 and mirror rewritten to pageIndex 3, fetchedCount 42, savedData.nextPageIndex 3 (DB is source of truth) — checkpoint_and_dispatch_recovery.py:4
- [PC2] mirror key removed when runtime returns idle / stop_sync("catalog") — :68
- [PC3] pipeline does not re-enqueue a QUEUED request while its dispatch is pending: POST /api/processing/records/create-requests/ {ids:[recordId]} -> request id "request-<recordId>", state queued, Celery task kickoff_book_creation_request_task.apply_async(args=(requestId,), queue="processing") called once; repeated pipeline advance returns advancedCount 0 and no new dispatch — :88
- [PC4] pipeline dispatches queued request even with an initial backlog: advance with one queued + one initial request -> advancedCount 2, both end queued (initial -> queued then dispatched), only the already-queued one dispatched in that tick — :155
- [PC5] action create_again (POST /api/processing/requests/action/ {ids, action:"create_again"}) on a deleted request whose record is linked to an existing Book: pipeline reuses linked book and finishes `created`; linked_book kept, duplicate links cleared, record.book_creation_state created, is_duplicate False — duplicate_resolution_actions.py:4
- [PC6] repair_self_linked_duplicate_requests(): a duplicate request linked to a book that is its own (record.linked_book == request.linked_book, duplicate) is repaired to `created`; leaves on-hold-duplicate card table empty (GET /api/processing/table/?card=on-hold-duplicate -> pagination.totalCount 0) and appears in `create-created` card rows (row key `requestId` or `id`) — :83
- [PC7] action confirm_duplicate locks the duplicate record until the original request reaches a terminal state: duplicate row in `payload["records"]` has `selectable false` while original is `processing`; after original -> failed row becomes selectable true — :127
- [PC8] action `new` on duplicate: request state -> initial, is_confirmed_not_duplicate True, duplicate_confirmed False, duplicate_of_request/record None, linked_book None; record book_creation_state initial, linked_book None, is_duplicate False — :177
- [PC9] action `new_edition`: existing book gets a BookGroup (group.canonical_title == book title), submission.raw_payload["target_book_group_id"] = group id so the new book joins the same group; request restarted like `new` — :232
- [PC10] incomplete automation (POST /api/processing/automation/incomplete/run/): runMode "incomplete_automation"; pause -> pausing -> advance paused (first batch resolved only); RESUME RESTARTS FROM THE BEGINNING (message "Restarting incomplete catalog sync from the beginning."); completion message "Incomplete catalog sync complete. Updated 2 books." (singular "1 book") — incomplete_automation_flows.py:4, :105
- [PC11] incomplete sync pulls pages from `incomplete_sync_remote_pages()` into the sync state remote_pages — :70
- [PC12] live incomplete mode (should_use_live_incomplete_fetch True): no `remotePages` in payload, progress.savedData.liveFetch True; one page fetched per advance (fetch_live_incomplete_page(resolver, page_number) pages 1 then 2 -> []), records created; at the end stale incomplete records (not seen live) are resolved: resolved_from_incomplete True and category replaced by will_resolve_to_category ("Novel") — :105
- [PC13] live incomplete pause/resume: paused state keeps liveFetch + nextPageIndex 1 and remote_pages len 1; resume resets page_index 0 and remote_pages [] — :184
- Mock heavy: monkeypatching services functions and Celery apply_async; fixed `time.sleep(0.1)` polling loops.

### 14l — notes: processing api cases part 4: automation_ownership_flows (222), automation_persistence (73), maintenance_and_actions (249), processing_pipeline_dispatch (213), queue_fallback_and_reset (243), read_endpoint_purity (81), stale_recovery (78), runtime_tick_and_projection_reads (237), state_payload_and_tables (231), ui_version_publication (221)


- [PD1] card tables `GET /api/processing/table/?card=<id>`: on-hold-paused/failed/duplicate/deleted and create-requests(initial)/create-queue(queued)/create-processing/create-created each list ONLY requests of that state; rows have `requestId`, `status`; `filters.statusOptions == [state]` — automation_ownership_flows.py:4; state_payload_and_tables.py:153
- [PD2] catalog automation waits for a running manual sync: manual sync running, POST /automation/catalog/run keeps runMode "manual" and creates no requests; after manual completes (2 advances; new records only persisted as pages advance) run again -> runMode catalog_automation; 3 advances -> idle; BookCreationRequest state "initial" for BOTH existing and new records; statusMessage "Created 2 requests." (singular "Created 1 request.") — :43; processing_pipeline_dispatch.py:4
- [PD3] security toggle: `allow_processing_remote_page_payloads()` False (production) makes `remotePages` in POST /sync/start/ be ignored (records not created), and stale stored remote_pages ignored by automation, which falls back to SourceCatalogEntry rows — :110, :130
- [PD4] automation pause/resume/stop: resume message "Continuing automated catalog sync from the saved endpoint.", pageIndex 1; POST /sync/stop/ -> idle, message and `automation.catalog.statusMessage` "Automated catalog sync stopped." — :177
- [PD5] saving automation settings: POST /api/processing/automation/catalog/ {enabled:true, interval:"weekly", time:"04:30"}; /automation/incomplete/ {enabled, interval:"daily", time:"03:00"}; catalog run creates requests (state initial) only for records NOT already created (record state not_created yes; created no); incomplete run: record category replaced with will_resolve_to_category ("Novel"), resolved_from_incomplete True, and a BookCreationRequest state "created" exists for it — automation_persistence.py:4
- [PD6] GET /api/processing/state/ must NOT recover stale processing requests (read-only); only `mark_stale_processing_requests()` / `run_processing_maintenance()` do: request processing & updated_at 25 min old -> queued, record queued; maintenance result {recoveredCount:1, repairedCount:0, syncRecoveredCount}; stale threshold <25 min (tests use 25-30 min); resumed request keeps progress checkpoint (savedData.scrapedData) and is_resumed True — maintenance_and_actions.py:4,45; stale_recovery.py:6
- [PD7] stale sync recovery: sync status syncing with lost task_id and old updated_at (30 min) -> maintenance clears task_id, keeps status syncing and nextPageIndex; run_processing_runtime_tick() twice then completes the sync (record created) — stale_recovery.py:38
- [PD8] created rows in table carry `linkedBookId`, `linkedBookSlug` — maintenance_and_actions.py:75
- [PD9] duplicate detection is backend owned (processing app, not the legacy submission flow): create-requests for a record whose URL matches an existing Book via find_existing_book_by_source_url -> request ends `duplicate`, submission None, duplicate_of_request/record set to the original, record state duplicate; no BookSubmission or ProcessingJob created — :104
- [PD10] request actions POST /api/processing/requests/action/ {ids, action}: `resume` (paused -> initial, is_resumed True), `retry` (failed -> initial, error_message cleared), `delete` with deleteBook:true (created -> deleted and linked Book soft-deleted: deleted_at set) — :170. Other actions seen elsewhere: create_again, confirm_duplicate, new, new_edition.
- [PD11] POST /api/processing/records/create-requests/ {ids:[recordId]}: creates request with id "request-<recordId>", state initial (record book_creation_state initial); pipeline ticks then create the Book through processing services (scrape -> exports -> persist): final request.state created, record.book_creation_state created, request.submission_id None, linked_book set (title "Request Record", `raw_scraped_metadata.source_url` normalized URL), NO BookSubmission/ProcessingJob rows (processing pipeline independent of ingestion queue). Test polls up to 20 x 0.25s — processing_pipeline_dispatch.py:46
- [PD12] Celery task kickoff_book_creation_request_task: acks_late True and reject_on_worker_lost True; missing request -> returns {request_id, state:"deleted", submission_id:"", missing:True}; run_processing_sync_task("default") returns JSON-safe snapshot {singleton_key:"catalog", status, run_mode, page_index, fetched_count, remote_pages} — :139-166
- [PD13] dispatch: create-requests when jobs not inline: apply_async(args=(requestId,), queue="processing") WITHOUT probing worker availability (even if processing_workers_available False); request becomes queued with progress["_dispatchTaskId"]; if apply_async raises (broker down) pipeline falls back to running the request inline; stale dispatch marker (progress._dispatchRequestedAt 5 min old) is re-dispatched with a new task id; fresh marker is NOT re-dispatched — queue_fallback_and_reset.py:4,53,103
- [PD14] dispatch_sync_task(sync_state, force=True): apply_async(args=("catalog",), queue="processing", task_id=sync_state.task_id), sets queue_name "processing", clears last_error — :159
- [PD15] reset_processing_data(revoke_tasks=True, purge_queue=True): revokes celery tasks for request progress dispatch id and sync task id, purges processing queue, deletes all BookCreationRequest, records -> not_created, sync idle with task_id/queue_name cleared — :190
- [PD16] GET endpoints are pure: /api/processing/state/?includeLists=0, /table/?card=catalog-records, /card/?card=catalog-sync do not advance a pausing sync or processing pipeline, do not run due automations (ProcessingAutomationSettings.last_run_at stays None) — read_endpoint_purity.py; runtime_tick_and_projection_reads.py:104,138
- [PD17] SSE stream GET /api/processing/stream/?page=catalog: first chunk "event: connected\ndata: {}\n\n" then "event: versions\ndata: {json {versions:{...}}}"; does not advance sync — runtime_tick_and_projection_reads.py:4
- [PD18] processing_state_payload reads `sync` from projection rows only (ProcessingUiProjection keys "catalog-sync", "incomplete-automation"); with several rows the most recently updated wins (incomplete idle last) — :172
- [PD19] run_processing_runtime_tick() (no browser): advances sync and pipeline: result {advancedCount:1, sync:{catalog:{status idle}}}; initial request -> queued when workers unavailable and not inline — :53
- [PD20] automation defaults: state returns interval "weekly", time "03:00", statusMessage "" even if DB row holds legacy defaults (daily 02:00/03:00 "Not configured."); read does not modify the DB rows — state_payload_and_tables.py:4; ui_version_publication.py:178
- [PD21] summary payload `GET /api/processing/state/?includeLists=0`: no `records`/`requests`, has `versions`, `summary.catalog.{records,onHold}`, `summary.onHold.failed`, `summary.incomplete.incomplete`, `summary.notifications.latestFailedMessage` (failed request error message), `cards{catalog-overview, create-overview, catalog-sync}.card` — :50
- [PD22] catalog-records table pagination: limit 60, offset: `pagination{totalCount, hasMore, nextOffset}` and top-level `hasMore`; filters.categoryOptions, statusOptions; rows sorted not_created first then created; `category=Poetry&status=created` filter — :91
- [PD23] upsert_remote_records race: if concurrent insert wins (IntegrityError on create), recovers by updating the competing row (appended 0, updated 1, skipped 0; fields from payload) — :192
- [PD24] UI version publication (ProcessingUiDomainVersion): save_sync_state(catalog) bumps `catalog-sync` +1 on commit but NOT `catalog-automation` (projection refreshed silently: catalog-automation projection sync.status/message updated); incomplete sync bumps only `incomplete-automation`; collect_processing_ui_version_updates() context returns committed bumps; request action mutation response `versions` excludes unrelated bumps (catalog-sync); catalog record upsert bumps catalog-overview + catalog-records but not create-requests — ui_version_publication.py:4-178
- [PD25] display URLs: state records have `url` (percent-encoded original) plus `displayUrl` (decoded Bangla) and `displayPath` ("books/<decoded slug>") — :194
- Mock heavy: patches many `apps.processing.services.*` functions and Celery; all deterministic via explicit advance calls.

### 14m — notes: backend/ingestion test_ingestion_01 (256), 02 (236), 03 + 2 cases (15+247+56), 04 (227), 05 (285), 06 + 2 cases (15+107+252), 07 (258), 08 (244)


Domain: BookSubmission (input_type url|title, origin user|curation|automation, status queued|processing|ready|failed|cancelled|duplicate, resolution_status resolved|exact_match|ambiguous, resolved_url, raw_payload), ProcessingJob (status queued|processing|succeeded|failed|cancelled, job_type create|reprocess, task_id, queue_name, cancel_requested, last_error, worker_hostname), DuplicateReview (submission, existing_book, status pending|confirmed), SourceCatalogEntry (source_url, title, author_line, normalized_title, normalized_display, raw_data{category,publisher,metadata_source: archive_page|book_page|incomplete_archive_page}), SourceCatalogRefreshState (singleton_key "default", status queued|processing, max_pages, requested_by), CatalogCurationRun (trigger manual|scheduled, mode pending|all, status, refresh_catalog, refresh_max_pages, summary{queued_creates, queued_updates, status_counts}), CatalogAutomationSettings (enabled, daily_run_time, frequency daily|weekly|monthly, mode, refresh_max_pages), TitleResolutionAttempt, MatchCandidate(rank, candidate_title/author/url, confidence).

- [IN1] normalize_text keeps Bengali combining marks ("ম্যালিস" unchanged) — test_ingestion_01.py:62
- [IN2] get_with_host_fallback: when requests raises DNS-resolution ConnectionError ("Failed to resolve host (Name resolution)") for www.example.com it resolves host via resolve_host_with_dns_fallback and retries via direct-IP HTTPS (get_via_direct_ip_https(session,url,host,ip,params)); non-DNS ConnectionError ("Connection reset by peer") is re-raised unmasked, direct IP not tried — :66, :113
- [IN3] POST /api/ingestion/submissions/ {input_type:"title", content:"স্যাম্পল বুক", auto_process:false} -> 201 list; item resolution_status "exact_match", status "queued", resolved_url from the SourceCatalogEntry (title resolved from catalog without guessing) — :131
- [IN4] POST /api/ingestion/submissions/status/ {ids:[...]} returns only submissions visible to the user (own), in REQUESTED order, hidden ones dropped — :164
- [IN5] TitleResolver(session).resolve(title): crawls archive bucket (https://www.example.com/books/ with params `_a_z=<first letter>` and `_paged=n`, stops at empty page `<div class="facetwp-template" data-name="books">` with no `.fwpl-result`), parses `div.fwpl-item a` text "Title - Author" splitting author; exact title match -> status exact_match, resolved_url, entry stored (title "ম্যালিস", author_line "সৈকত মুখোপাধ্যায়"); two entries with same title -> status "ambiguous", resolved_url "", candidates [{url,...}] — :201; test_ingestion_02.py:63
- [IN6] exact match enriches from the book page: fetches book page and stores raw_data.metadata_source "book_page" (authors from span.entry-terms-authors, series from span.entry-terms-series, title from <title> split " - ") and title becomes clean "ম্যালিস" even if archive text was "ম্যালিস উপন্যাস" — test_ingestion_02.py:112
- [IN7] direct URL submissions store page metadata: create_submission_records(submitter=None, parsed_entries=[{kind:"url", value}], auto_process=False) saves raw_payload["source_page_metadata"] (via capture_source_page_metadata(url)) — :167
- [IN8] POST /api/ingestion/catalog/refresh/ {max_pages:3} (superadmin) -> 202 {status:"queued", max_pages:3, requested_by_email}; SourceCatalogRefreshState singleton "default" QUEUED, requested_by set — :196
- [IN9] GET /api/ingestion/catalog/entries/ includes `sync_state` {status "processing", max_pages} — :221
- [IN10] catalog entries listing: `?status=new&limit=1` filters BEFORE pagination, returns `summary{total,new,ready,deleted,failed,queued,processing}` computed for the filtered set (total 1), `pagination{total_count,page_count}`, `entries[]` with `curation_status` (new | ready | deleted | failed | queued | processing | stopped) — test_ingestion_03_cases/source_catalog_entry_filters.py:63,104
- [IN11] curation status rules: entry whose BookSource -> Book has READY html+epub assets = "ready"; no book & no submission = "new"; book soft-deleted (deleted_at) = "deleted"; latest curation-origin submission queued/job queued = "queued"; processing = "processing"; failed submission+job = "failed" (+ latest_submission_status, latest_job_status); cancelled submission = "stopped". Queued and processing are counted separately in summary — :145; test_ingestion_05.py:113,207
- [IN12] `?include_summary=0&include_sync_state=0&sort=title_asc&limit=1` omits summary and sync_state keys, sorted ascending by title — :217
- [IN13] `?view=overview` returns summary over all entries (total 2, failed 1, ready 1) but `entries` only reviewable rows (the failed one) — source_catalog_entry_overview.py:4
- [IN14] GET /api/ingestion/catalog/incomplete-check/ : summary{queued}, entries[{book_title, author_line}] where the author line comes from the Book's BookContributors (not stale catalog), for books in category "অসম্পূর্ণ বই" — test_ingestion_04.py:63
- [IN15] TitleResolver.refresh_catalog(max_pages): stores long source URLs (>200 chars supported), splits "Title - Author"; continues past pages whose entries already exist (does not stop at first all-known page); returns only NEW entries as dicts {source_url,title,author_line,normalized_title,normalized_display,raw_data{title,display_title,author_line,metadata_source:"archive_page"}}; requests CATALOG_URL with {} then {"_paged":2} — :113, :153
- [IN16] long URLs storable across SourceCatalogEntry, BookSource, BookSubmission, TitleResolutionAttempt, MatchCandidate (migration expand_url_field_lengths) — test_ingestion_05.py:63
- [IN17] source_catalog_entry_snapshots(queryset) -> (snapshots, summary) with `categories` from raw_data.category for new, from Book categories for ready; works with small lookup chunks (SOURCE_LOOKUP_CHUNK_SIZE=1) — :113, :152
- [IN18] POST /api/ingestion/catalog/entries/create-books/ {ids:[entryId]} (processing manager) -> 202 {queued_creates:1, skipped_deleted:0}; calls create_submission_records(submitter=admin, parsed_entries=[{kind:"url", value:source_url}], auto_process=True, origin=CURATION); soft-deleted books' entries are also re-created (skipped_deleted 0) — test_ingestion_05.py:240; catalog_recreation_and_asset_sync.py:64
- [IN19] find_existing_book_by_source_url ignores soft-deleted books (uses BookSource.normalized_source_url) — test_ingestion_05.py:273
- [IN20] POST /api/ingestion/catalog/curation-runs/ {mode:"pending", refresh_catalog:true, refresh_max_pages:80} -> 202 run {id, status "queued"}; POST .../curation-runs/<id>/stop/ -> run cancelled (revoke_curation_task) — catalog_automation_views.py:4; test_ingestion_07.py:173
- [IN21] PATCH /api/ingestion/catalog/automation/ {enabled, daily_run_time:"03:45", frequency:"weekly", mode:"all", refresh_max_pages:40} -> 200 {settings:{...}} (time serialised "03:45:00") — :30
- [IN22] list filters: GET /api/ingestion/jobs/?origin=user and /submissions/?origin=curation filter by submission origin; POST /api/ingestion/jobs/recover/ {origin:"user"} -> 202 {recovered_jobs:1}, re-dispatches only queued jobs WITHOUT task_id (job with task_id "already-dispatched" untouched) — :58
- [IN23] process_catalog_curation_run(run_id): stopped (cancelled) catalog entry with no local book -> new create via create_submission_records(submitter=None, origin=AUTOMATION); with local book -> queue_reprocess_book(book, actor=None, origin=AUTOMATION); summary queued_creates/queued_updates/status_counts["stopped"]; run.status SUCCEEDED — catalog_recreation_and_asset_sync.py:107,159
- [IN24] sync_assets(...) raises ValueError("Missing generated assets: EPUB...") when epub file absent: Book state/review_state -> "needs_review"; HTML asset READY, EPUB asset FAILED — :223
- [IN25] ?q= search on submissions/jobs/duplicate-reviews matches percent-encoded source URLs by decoded Bangla title words (both "খেয়া" and "খেয়া রবীন্দ্রনাথ ঠাকুর") — test_ingestion_07.py:63
- [IN26] POST /api/ingestion/jobs/<id>/stop/: queued job -> job & submission CANCELLED (revoke_processing_task); processing job -> revoke(task_id, terminate=True), CANCELLED, cancel_requested False — :100, :134
- [IN27] run_due_catalog_automation(now): enabled settings with daily_run_time earlier than now => creates ONE scheduled CatalogCurationRun (trigger "scheduled"); second call same day -> {ran:False, reason:"already_ran"}; weekly frequency: last run 3 days ago -> not due ("already_ran") — :201, :236
- [IN28] next_catalog_automation_run_at(settings, now): monthly frequency from latest run 2026-01-31 06:30 -> next in Feb (day 28/29, month-end clamp) — test_ingestion_08.py:63
- [IN29] Front matter: extract_front_matter_entries(book_info_html) -> [{key: translator|first_published|publisher, label, value, role}] for labels "অনুবাদ", "প্রথম প্রকাশ", "প্রকাশক" with optional space before ':'; normalize_scraped_book(book dict) -> {contributors:[{name,role}],...} splitting translators on "," and the connector "ও"; publisher "প্রকাশনী" -> role publisher — :92, :183
- [IN30] promote_leading_front_matter(book_info_html, main_content_html) -> (book_info, cleaned_main): moves title-prefixed "অনুবাদ: ..." and "প্রথম প্রকাশ: ..." from main content; "ভূমিকা" and body stay — :125
- [IN31] translator biography prose is not a translator: value "মাকসুদুজ্জামান খান বায়োটেকনোলজি ... করছেন। তিনি ... ভাষান্তর করেছেন।, মাকসুদুজ্জামান খান" yields only translator ["মাকসুদুজ্জামান খান"]; pure prose with no name-like value yields no translator entry — :164, :201
- [IN32] clean_extracted_dedication_html removes repeated "উৎসর্গ" heading paragraphs (also inside <strong>), keeps dedication text and dates; inline "উৎসর্গ :<br/>পাঠক, আপনাকে…" keeps the text, drops the label — :221, :236

### 14n — notes: backend/ingestion test_ingestion_09 (196), 10 facade (17) + cases scraper_crawl_and_cover (266), queue_fallback_and_retries (259), stale_task_dispatch_guards (234), stale_processing_recovery (107), test_ingestion_11 (202)


Constants: MAX_PROCESSING_JOB_ATTEMPTS = 3 (process_submission_task.max_retries == 2).

- [IN33] extract_main_content_segments(main_html) -> (book_info, dedication_html, cleaned_main): drops repeated "উৎসর্গ" heading paragraphs (plain and <strong>); dedication stops BEFORE a strong-only title paragraph ("কবির মন্তব্য"), which and following text remain in main content — test_ingestion_09.py:62,81
- [IN34] split_leading_front_sections(main_html) -> (sections [{title, html}], cleaned_main): a multi-line strong-only paragraph (title + "ভাষান্তর : ..." via <br/>) is one section heading (title joined by "\n"), following text is section html; "সূচীপত্র" TOC heading and list removed from cleaned main — :101
- [IN35] legacy_scraper.extract_inline_toc_and_content(main_html) -> (toc, content_items, cleaned_main): "সূচীপত্র" (TOC) list with #anchor links + h3 id sections builds toc [{title}] and content_items [{title, content}] and removes TOC and section bodies from main (keeps the h2 book title); a TOC of external book links with no section bodies yields toc entries with content_items [] and TOC removed; paragraph-style TOC ("সূচী ॥" followed by <p><a href=".../lessons/..."> links) yields toc entries with `url`, content_items [], link paragraphs removed but book-title paragraph stays — :124,151,176
- [IN36] normalize_scraped_book: authors "ইশরাক অর্ণব, কেইগো হিগাশিনো, সালমান হক" with translator "ইশরাক অর্ণব" and editor "কেইগো হিগাশিনো" in book_info -> contributors (সালমান হক author), (ইশরাক translator), (কেইগো editor); author role dropped for people who also have translator/editor role — test_ingestion_10_cases/queue_fallback_and_retries.py:3
- [IN37] queue_submission(submission) when Celery apply_async raises (Redis down): runs inline fallback — job.queue_name "inline-fallback", job.last_error contains "Celery dispatch failed", submission becomes READY on success; inline retries up to 3 total attempts (attempt retry_count 0,1,2) then re-raises last error (job FAILED, retry_count 2) — :27,60,102
- [IN38] process_submission_task(job_id) returns JSON-safe {job_id, submission_id, book_id:"", status} — :138
- [IN39] process_submission_job(job_id, retry_count, task_id): intermediate failure (retry_count < 2) -> job back to QUEUED with retry_count+1 and last_error containing "attempt 2 of 3", task_id/queue kept, submission stays QUEUED with empty error_message, exception re-raised for Celery retry; final attempt -> job FAILED, task_id/queue_name cleared, submission FAILED with error_message == the exception text — :168,216
- [IN40] legacy_scraper.scrape_book_data(url) recursion: root page TOC links to a child book page which has lessons (scrape_all_lessons) -> nested toc [{title:"সংগ্রহ খণ্ড", children:[{title:"অধ্যায় ১"}]}]; content_items flatten in order with `path` ["সংগ্রহ খণ্ড"], ["সংগ্রহ খণ্ড","অধ্যায় ১"] and content; leading landing prose is promoted into `front_sections` when explicit body structure exists, "সূচীপত্র" not left in main_content — scraper_crawl_and_cover.py:72
- [IN41] download_cover_image(soup, folder): finds `figure.entry-image-link.entry-image-single img` src, downloads with retry session (headers HEADERS, timeout 30), saves as `book_cover.<ext of url>` (webp kept) — :169
- [IN42] scrape_all_lessons(url): paginated lesson list via `?ld-courseinfo-lesson-page=N`, sleeps 1 second between pages — :226
- [IN43] recover_stale_processing_jobs(limit): job PROCESSING started 45 min ago -> revoke task (terminate=True), re-dispatch via process_submission_task.apply_async(args=[job_id], kwargs={attempt_offset: retry_count+1}, task_id=new id), job QUEUED with retry_count+1, last_error set, submission QUEUED; returns count recovered; exhausted (retry_count == 2) -> revoked, NOT dispatched, job FAILED, task_id/queue cleared, submission FAILED (error_message == job.last_error), returns 0 — stale_processing_recovery.py:4,67 (stale threshold < 45 min)
- [IN44] process_source_catalog_refresh(task_id): ignores stale/replaced tasks: a task id that no longer matches state.task_id is a no-op (no refresh); if the user stopped it mid-run (state IDLE, last_error "Stopped by user.") completion is ignored and refreshed_entries stays 0; if replaced by a newer task, neither completion nor failure of the old task modifies state — stale_task_dispatch_guards.py:4-96
- [IN45] eager-mode dispatch (CELERY_TASK_ALWAYS_EAGER): if the eager task raises after marking the job/state/run FAILED, dispatch_processing_job / dispatch_source_catalog_refresh / dispatch_catalog_curation_run return the FAILED object (queue_name "celery", task_id set) and do NOT run the inline fallback again — :130,173,208
- [IN46] create_submission_records for a URL that already has an in-progress canonical submission: new submission links `canonical_submission_id`, copies status (processing), raw_payload["deduplicated"] True; queue_submission(duplicate) returns the existing job (still 1 job) — test_ingestion_11.py:63
- [IN47] a URL previously READY but whose linked book is soft-deleted is NOT reused: new submission has no linked_book, no canonical, status QUEUED — :99
- [IN48] a URL whose earlier submission FAILED is not reused: new submission queued with canonical None — :130
- [IN49] POST /api/ingestion/submissions/<id>/retry/ on a ready-but-book-deleted submission -> 202; clears reused state (linked_book None, duplicate_of_book None, review_state pending, raw_payload keys served_from_database, existing_book_source, linked_book_slug removed), status QUEUED, one QUEUED ProcessingJob — :157

### 14o — notes: backend/ingestion test_ingestion_12 (247), 13 (189), 14 (246), 15 (243), 16 (289)


- [IN50] POST /api/ingestion/submissions/bulk-retry/ {ids:[...]} -> 202 {queued_count, skipped_invalid, skipped_duplicate_targets, skipped_missing}: duplicate submissions pointing to the same canonical submission collapse to one target (3 ids -> queued 2, skipped_duplicate_targets 1); canonical + independent submissions become QUEUED with 1 queued job each — test_ingestion_12.py:63
- [IN51] POST /api/ingestion/jobs/<id>/resume/ on a CANCELLED job -> 202; job QUEUED, cancel_requested False, task_id cleared, submission QUEUED, error_message "" — :133
- [IN52] POST /api/ingestion/jobs/bulk-resume/ {ids} -> 202 {resumed_count, skipped_invalid} — :176
- [IN53] detect_metadata_duplicate(book_data{book_title, author, book_type, series, book_info}) -> existing Book or None. Ignores soft-deleted books; does NOT match same title with different author; different category (book_type) no match; target series differing from existing series no match; differing translators (book_info "অনুবাদক: X") no match — test_ingestion_12.py:228,240; test_ingestion_14.py:171,191,223
- [IN54] find_exact_existing_book(book_data) requires title + author overlap (+ category + translators agree): same title different author -> None; same author -> the book; different categories -> None; different translators -> None — test_ingestion_13.py:63; test_ingestion_14.py:146; test_ingestion_15.py:63
- [IN55] process_submission_job recovers from an IntegrityError on constraint `uniq_book_source_normalized_title` (book create raced): it re-looks up an existing book by source URL (>=2 lookups) and links to it -> submission READY, linked_book == existing — test_ingestion_13.py:92
- [IN56] BUT if the existing same-title book has a DIFFERENT source URL, the conflict is NOT resolved by reusing it: IntegrityError re-raised, job returned to QUEUED retry_count 1, submission QUEUED, linked_book None — test_ingestion_14.py:63. (Rule: reuse is by source_url, never title alone.)
- [IN57] title submissions never auto-fulfil from a title-only local match: create_submission_records(parsed_entries=[{kind:"title", value}]) with resolver UNRESOLVED -> submission NEEDS_REVIEW (review_state needs_review, error "No confident catalog match was found."), linked_book None, raw_payload.served_from_database absent — test_ingestion_15.py:95
- [IN58] scraped data with `cover: None` is OK: Book.cover_source_url == "" (no NULL violation) — :124
- [IN59] re-creating a deleted book from its source URL REUSES the soft-deleted Book (same id, deleted_at cleared, BookSource kept) with raw_payload.served_from_database False; processing the same job again is idempotent (no re-run: same linked book, status READY) — :172
- [IN60] public (no login) submissions: GET /api/ingestion/submissions/<id>/ -> 200 with `candidates` (ranked MatchCandidates, confidence 0.92 / 0.61) when raw_payload.submitted_publicly; POST .../confirm-candidate/ {candidate_id} -> 200, queue_submission(submission, actor=None) called, submission.resolved_url = candidate url, resolution_status RESOLVED, status QUEUED — test_ingestion_16.py:63
- [IN61] POST /api/ingestion/submissions/<id>/action-links/ (anonymous, public ready submission with linked book) -> 200 {launch_url, epub_download_url, html_preview_url, manifest_url}; creates PreviewAccessSession(source_submission, user None); guest manifest has reading_session_url "", bookmarks_url "", reading_session None, bookmarks []; guest reader session/bookmarks endpoints (/api/access/reader/<token>/session/, /bookmarks/) -> 403 — :125
- [IN62] submission whose linked book is soft-deleted: detail `status:"deleted"`, `linked_book_deleted: true`, `linked_book_slug ""`, linked_book.title still present — :188
- [IN63] action-links for soft-deleted linked book -> 410 detail "This book was deleted." — :217
- [IN64] DELETE /api/ingestion/submissions/<id>/ on queued submission -> 204, submission status DELETED, job CANCELLED (task revoked); POST .../retry/ -> 202, submission QUEUED again with a new queued job — :246

### 14p — notes: backend/ingestion test_ingestion_17 (258), 18 (238), 19 (243)


- [IN65] GET /api/ingestion/duplicate-reviews/ defaults to PENDING reviews only; `?status=dismissed` lists dismissed ones — test_ingestion_17.py:63
- [IN66] POST /api/ingestion/duplicate-reviews/<id>/resolve/ {decision:"dismiss"} ("keep new") for a review whose existing book is soft-deleted: review DISMISSED; submission QUEUED, review_state pending, linked_book/duplicate_of_book cleared, raw_payload.served_from_database removed, one queued ProcessingJob (recreate) — :121. Other decisions: confirm_existing (links existing book, submission ready, review "confirmed").
- [IN67] POST /api/ingestion/submissions/ (anonymous allowed) {entries:[url, title], auto_process:true} -> 201 array: URL entry matching an existing BookSource is served from DB (`served_from_database` true, `linked_book_slug`), title entry is NOT (served_from_database false, linked_book_slug "", status in queued|processing|needs_review|ready); no PreviewAccessSession created for anonymous — :168
- [IN68] ambiguous title (two catalog entries "স্যাম্পল বুক এক/দুই" for "স্যাম্পল বুক") -> status "needs_review" with 2 `candidates`; POST confirm-candidate {candidate_id} (authenticated, any user) -> 200, queue_submission called, submission QUEUED & resolution_status "resolved" — :206
- [IN69] process_submission_job persists: Book (single), contributors split on comma — authors "লেখক এক, লেখক দুই" (both author), "অনুবাদ:" -> translator, "সম্পাদক:" -> editor from book_info; `dedication_html` of just the label "<p>উৎসর্গ</p>" becomes "" (empty dedication discarded); content_items stored as scraped; exports receive dedication = book.dedication_html, content_items = book.content_items, book_title; GeneratedAssets HTML, EPUB, COVER exist; job SUCCEEDED, submission READY — test_ingestion_18.py:63
- [IN70] cover asset resolution: scraped cover name "book_image.hpg" (wrong extension) but exports wrote `book_cover.jpg` -> COVER asset status READY (resolved by globbing the actual cover file), legacy_path "" — :130
- [IN71] single-copy storage: assets are moved into MEDIA_ROOT/generated/<book.slug>/ (files: book.html, book_cover.jpg, exactly one *.epub => 3 files), temp output folder removed, every GeneratedAsset has `file` set and legacy_path "" — :182
- [IN72] re-sync of assets (sync_assets again for same book) REPLACES the media files rather than duplicating (still 3 files, content from second run, output dir deleted) — test_ingestion_19.py:63
- [IN73] URL submission checks the database first: POST /api/ingestion/submissions/ {input_type:"url", content, auto_process:true} for an existing source -> 201, status "ready", served_from_database true, linked_book_slug, NO ProcessingJob, and a PreviewAccessSession(user, book) is created for the logged-in user — :139
- [IN74] title submissions never reuse a local book by title: served_from_database false, linked slug "" — :172
- [IN75] canonical names: authors "লেখক এক, লেখক-এক, লেখক এক", series "রহস্য সিরিজ, রহস্য-সিরিজ", categories "উপন্যাস, উপন্যাস", translators "অনুবাদক এক, অনুবাদক-এক" collapse to one Contributor/Series/Category each via normalized_name — :197

### 14q — notes: backend/ingestion test_ingestion_20 facade (15) + activity_tasks_and_schedule (225) + heavy_column_query_efficiency (190); test_ingestion_21 facade/head (180); test_ingestion_22 (162); test_ingestion_23 (205)


- [IN76] GET /api/ingestion/activity/ for a regular user: only their own work visible; payload {can_manage_processing:false, has_visible_activity:true, active_scopes:["submissions","jobs"]} (another user's processing work not counted) — activity_tasks_and_schedule.py:50
- [IN77] same for superadmin/manager: can_manage_processing true; active_scopes is the SET {submissions, jobs, source_jobs (curation origin), automation_jobs (automation origin), runs (CatalogCurationRun), catalog_refresh (SourceCatalogRefreshState processing)} — :97
- [IN78] run_catalog_automation_schedule_task(): ProgrammingError 'relation "ingestion_catalogautomationsettings" does not exist' => returns {"ran": False, "reason": "schema_not_ready"}; other ProgrammingError (missing column) is re-raised — :150,162
- [IN79] recover_stale_processing_jobs_task(): recovers per origin with a shared limit budget 100: USER first (limit 100), CURATION (100 - already recovered), AUTOMATION only if catalog automation settings.enabled (limit again reduced); returns {"recovered_jobs": total} (2+1 -> 3; enabled: 1+2+4 -> 7) — :173,200
- [IN80] performance guard: list endpoints submissions (`?limit=1&origin=curation`), jobs, duplicate-reviews must not select heavy Book columns (summary, raw_scraped_metadata, raw_scrape_payload, main_content_html, book_info_html, dedication_html, toc, content_items), nor ProcessingJob.payload, nor TitleResolutionAttempt.raw_results — heavy_column_query_efficiency.py:4,64,116 (checked via CaptureQueriesContext)
- [IN81] test_ingestion_21 head: helper contributor_pairs; see 14r for metadata-fidelity cases. Pure unit rules here: split_display_title("আনন্দসঙ্গী – ২ ছোটগল্প") keeps the suffix in title with empty author; "সংকলন – X" -> editor, "প্রচ্ছদ – X" -> cover_artist (new role), marketing prose sentence is NOT a contributor — test_ingestion_21.py:31
- [IN82] translator/publisher cleaned to names only: "... – অনুবাদ : জি. এইচ. হাবীব / পাশ্চাত্য দর্শনের ইতিহাস ..." -> translator "জি. এইচ. হাবীব"; "প্রকাশক – ঐতিহ্য" -> publisher "ঐতিহ্য"; authors from author field "ইয়স্তেন গার্ডার, জি. এইচ. হাবীব" but translator person removed from authors — :58
- [IN83] lowercase English prose ("and elaborate purports") or title-case prose ("Readers Ways") after "অনুবাদ :" are NOT translator names (only author remains) — :79
- [IN84] extract_front_matter_entries("<p>প্রথম সংস্করণ: বৈশাখ ১৩৮২</p>") -> [{key:"edition", label:"প্রথম সংস্করণ", value:"বৈশাখ ১৩৮২", role:"", roles:[]}] — :105
- [IN85] source-generated floating TOC widget (`#ftwp-container-outer` / ftwp-in-post) is stripped from book content — :119
- [IN86] repaired_opf_nav_spine(opf) -> (repaired, changed): an OPF whose spine starts with `<itemref idref="nav"/>` is repaired to `<itemref idref="nav" linear="no"/>` and not first — :138
- [IN87] EpubBuilder(book_title, author, output_folder): title with "/" sanitized in filename ("তিন গোয়েন্দা ভলিউম ৪/১.epub" -> "তিন গোয়েন্দা ভলিউম ৪_১.epub"); package at EPUB/content.opf, nav never the first spine itemref — :158
- [IN88] classify_incoming_book(scraped, normalize_scraped_book_fn=) -> {verdict, matched_book}: verdicts CLASSIFY_NEW_WORK (no title match, or authors differ), CLASSIFY_EXACT_DUPLICATE (title+authors+translators+publisher+edition all overlap), CLASSIFY_NEW_EDITION (same title+authors but publisher OR edition OR translators differ; matched_book is the existing), CLASSIFY_NEEDS_REVIEW (existing has no authors, or incoming has no authors; matched_book returned). Book has manual_publisher and edition fields — test_ingestion_22.py:71-155
- [IN89] audit_epub_structure(path) -> result{ok, errors, spine_slots, nav_hrefs, toc_hrefs}; slots via _classify_slot: cover_page->cover, title, info, dedication, toc, nav, front_section_N->front, back_section_N->back, lesson_N / main_content -> content, unknown -> None — test_ingestion_23.py:45
- [IN90] well-formed EPUB (create_epub(payload) with book_info, dedication, front_sections, back_sections, toc, content_items): spine order cover -> title -> info -> dedication -> front -> toc -> content -> back -> nav (nav last); nav.xhtml lists EVERY readable page (cover_page, title, info, dedication, front_section_1, toc, lesson_1, back_section_1); printed toc.xhtml is content-scoped (only lesson links, no cover/title/info/dedication/front/toc/nav) — :59
- [IN91] auditor errors: missing file -> "does not exist"; blank lesson page (markup only) -> "blank content"; nav linking to itself -> "links to itself"; toc.xhtml linking to cover -> "non-content target"; nav lacking front matter -> "missing entries" — :96-168

### 14r — notes: backend/ingestion/test_ingestion_21_cases/source_site_metadata_fidelity.py (1157 lines; all read) — contributor/role extraction, structure inference, EPUB structure rules


Roles seen: author, translator, editor, publisher, compiler (legacy; merges into editor), cover_artist (প্রচ্ছদ), illustrator (অলংকরণ / বানান সংশোধন ও বর্ণ অলংকরণ). Each contributor: {name, role, raw_value}.

- [MF1] split_display_title(display): conservative — "আনা ফ্রাঙ্ক-এর ডায়েরি" stays whole (author ""); " – " splits title from author line; "গডফাদার – মারিয়ো পুজো / রূপান্তর: শেখ আবদুল হাকিম" -> ("গডফাদার", "মারিয়ো পুজো / রূপান্তর: শেখ আবদুল হাকিম"); "পিরানদেল্লোর গল্প – সম্পাদনা : বুদ্ধদেব বসু" -> ("পিরানদেল্লোর গল্প","সম্পাদনা : বুদ্ধদেব বসু") — :33
- [MF2] extract_contributor_evidence(text, default_roles=None) -> {contributors, authors}: exact phrases keep full names without word loss: "অনুবাদ করেছেন – মো: রিয়াজ উদ্দিন খান" -> translator; "রূপান্তর: X" -> translator; "X সম্পাদিত" -> editor; "প্রকাশক X" -> publisher; English "Published by ATMAJAA PUBLISHERS" -> publisher, "Edited by Moheul Islam Mithu" -> editor; inline "TITLE by Avijit Pal Published by ATMAJAA PUBLISHERS" -> author + publisher; "... by Maurice Leblanc Edited by ..." -> author + editor; publisher address trimmed ("PATRA BHARATI at 3/1 College Row, Kolkata 700009" -> "PATRA BHARATI"). Rejected (empty result): role-only phrase ("মূল কিতাব পরিমার্জন ও সম্পাদনায়"), role-mixed prose ("অশীন দাশগুপ্ত সহযোগী সম্পাদক রুদ্রাংশু ..."), committee role ("বিভাগ (সদস্য সচিব)"), "সম্পাদনা পরিষদ", dated location ("ঢাকা, বাংলাদেশ ২২/০৭/২২"), numeric-only ("১"), too-short name ("মো"); dangling ")" stripped ("অনুবাদ: সালমান হক)" -> "সালমান হক") — :47
- [MF3] front matter + weak author resolution keeps exact names/roles: entries[0].value "মো: রিয়াজ উদ্দিন খান" (trailing ")" removed); "অনুবাদ ও সম্পাদনা – বুদ্ধদেব বসু" gives `roles ["translator","editor"]`; non-role entries mapped by key (first_published "মার্চ ২০২৩"); author field "মারিয়ো পুজো / রূপান্তর: শেখ আবদুল হাকিম" resolves author মারিয়ো পুজো + translator শেখ আবদুল হাকিম; no name contains "করেছেন" or ends with ")" — :186
- [MF4] line breaks in front matter: address on the next line is not part of publisher; "প্রচ্ছদ স্বর্ণাভ বেরা<br/>প্রকাশক অভিষেক আইচ ও অরিজিৎ ভদ্র দ্য কাফে টেবল" -> cover_artist only (ambiguous publisher string not created); multiline credits: translator "বিমুগ্ধ সরকার রক্তিম", cover_artist "সজল চৌধুরী", illustrators জাকির হোসেন and সজল চৌধুরী (from "বানান সংশোধন ও বর্ণ অলংকরণ: ..."), author preserved; "ভূমিপ্রকাশের পক্ষে ... প্রকাশিত" ignored — :225
- [MF5] standalone role label line takes its value from the next line(s): "প্রকাশক<br/>শ্রীসনৎকুমার গুপ্ত<br/>বঙ্গীয়-সাহিত্য-পরিষৎ" -> publisher "শ্রীসনৎকুমার গুপ্ত" (first line only); "সম্পাদক : A, B" -> two editors; audit_scraped_book(...) returns missing_contributors [] and unsupported_contributors [] for that fixture — :321
- [MF6] prose mentioning "প্রকাশক পত্রভারতীর কাছে কৃতজ্ঞতা ..." creates no publisher — :375
- [MF7] "প্রকাশক: প্রথমা, প্রকাশকাল: বাংলা সন ১৩৮৪, ভাষা: বাংলা, বইয়ের পাতার সংখ্যা: ১০১" -> front matter keys publisher "প্রথমা", first_published "বাংলা সন ১৩৮৪", language "বাংলা", page_count "১০১"; contributors only publisher প্রথমা + author — :398
- [MF8] dedupe helpers (applied before export): merge_front_matter_html_parts (repeated blocks once), dedupe_html_fragment_blocks, dedupe_structured_sections(sections, reference_fragments=) (drops repeated section with trimmed text and text identical to reference like publisher name), prune_duplicate_main_content(main, reference_fragments, content_items) -> "" when only duplicates — :434
- [MF9] infer_structured_content_from_main_content(main_html, book_title) -> (toc, content_items, cleaned_main): headings-only books: each h2 becomes toc entry + content_items (path [title]); preface text before first heading stays in main; loose italic chapter markers ("প্রথম অধ্যায়" in <em>) with 3+ markers also split; numeric single flow ("২.", "৩." paragraphs; first segment titled "১") -> toc ["১","২","৩"], main becomes "" — :468,489,519
- [MF10] dedupe_structured_sections drops source navigation link lists (section "সূচী" with only book links) keeps real preface — :542
- [MF11] extract_boundary_sections_from_content_items(content_items, toc) -> (front_sections, back_sections, toc, items): "অনুবাদকের কথা" heading at start of first chapter moves to front sections, "সম্পাদকের কথা" at end of last chapter moves to back sections; chapter content cleaned — :563
- [MF12] single-page book end to end (extract_main_content_segments -> split_leading_front_sections -> infer_structured -> boundary): front matter keys first_published "জানুয়ারি ২০২৪", edition "বৈশাখ ১৩৮২"; dedication "পাঠক, আপনাকে…" without label; front_sections ["ভূমিকা"], back_sections ["নমুনা অধ্যায়" (sample chapter after main chapters)], toc [প্রথম অধ্যায়, দ্বিতীয় অধ্যায়]; HTML export order: dedication-section < front-section < toc-section < chapters < back-section; EPUB contains EPUB/dedication.xhtml, front_section_1, toc, lesson_1, lesson_2, back_section_1; nav.xhtml lists dedication, front_section_1, toc, lessons then back_section_1, never itself; content.opf order front_section_1 < toc < lesson... < back_section_1 — :605
- [MF13] blank dedication -> no dedication.xhtml in EPUB and not in OPF — :704
- [MF14] audit_scraped_book allows container TOC nodes (lesson has_content False with child topics having content): duplicate_content_paths/duplicate_toc_paths/dead_toc_paths/missing_toc_paths_for_content all empty, has_deltas False — :733
- [MF15] EpubBuilder sequence add_title_page, add_info_page, add_dedication_page, add_front_section_pages, add_hierarchical_toc_page, add_lesson_pages, build_epub(name, toc_structure): toc.xhtml hrefs == ["lesson_1.xhtml"] only; nav lists title, info, dedication, front_section_1, toc, lesson_1 (not nav itself); OPF has nav with linear="no" — :774
- [MF16] upsert_source_catalog_entry preserves the archive display title when page metadata overwrites: raw_data.display_title and full_title stay "গডফাদার – মারিয়ো পুজো / রূপান্তর: শেখ আবদুল হাকিম", meta_author_line "মারিয়ো পুজো" (parse_source_page_metadata reads <title>, canonical link, span.entry-terms-authors) — :849
- [MF17] compare_source_report_to_production(source_report, production_detail) -> {has_deltas, missing_contributors, polluted_contributors (name truncated e.g. "মো: রিয়াজ উদ্দিন"), role_mismatches [{name, source_roles, production_roles}], missing_content_paths [(path tuple)], production_dead_toc_paths, missing_ready_assets ["cover","epub"]} — :887
- [MF18] scrape_book_data on LearnDash-style course pages: lesson list via `?ld-courseinfo-lesson-page=1` HTML (`.ld-item-lesson-item[data-ld-expand-id]`, `.ld-item-title`, `.ld-table-list-item-preview` topics, extra topic pages `&ld-topic-page=42-2`, pagination `data-pager-results={"total_pages":1}`); title "পাঠ 1 3 Topics" normalized to "পাঠ ১" (Latin digits -> Bengali, count suffix removed), topics "1. ভূমিকা" -> "১. ভূমিকা"; content_items with paths; topic with empty content ("3. ফাঁকা") is PRUNED from toc and content (dead leaf) — :976
- [MF19] build_navigation_entries(toc) -> hierarchical (entry, children) for content only; front matter (title page "শিরোনাম পৃষ্ঠা", info "বই বিষয়ক তথ্য") are not in navigation targets — :1113
- Business rule revealed: contributor extraction is evidence-based, conservative (precision over recall), role-aware and multi-role; junk is rejected rather than stored.

### 14s — notes: backend/ingestion/test_curated_pipeline.py (751 lines; all read) — curated document model + manifest parser


API: curate_book_document(url) -> {document, projection, status, validation{status,errors}, source_snapshot{pages[{url,kind,status,status_code}]}}; validate_document(document, snapshot); persist_curated_book(curated, source_url) -> (Book, CuratedBookDocument); verify_curated_result(curated_document, book) -> errors; source_chrome_hits(sections); build_manifest_from_legacy_payload; book_manifest.{collect_learndash_toc, assign_paths_to_toc, normalize_manifest_limits, SourceFetchContext, fetch_content_item, normalize_body_sections, disambiguate_duplicate_content_paths}. Management command `curate_source_site_books --offset --batch-size --skip-existing --report-path --require-validated --continue-on-error --require-catalog-match`.
Statuses: CuratedDocumentStatus.VALIDATED | REVIEW_REQUIRED. Structure types: "flat_toc" (also nested).

- [CP1] curated document of a book (translator "অনুবাদ : জি. এইচ. হাবীব", publisher, "প্রথম সংস্করণ: বৈশাখ ১৩৮২", dedication, front/back sections): status VALIDATED, structure_type "flat_toc", projection.toc generated from content items ("প্রথম অধ্যায়"), entities {(role,value)} include translator, publisher, edition; section types in order = [title_page, book_info, dedication, front_matter, generated_toc, body, back_matter] — :75
- [CP2] structural failures route to review: duplicate content path -> status REVIEW_REQUIRED with error "Duplicate content path: এক." — :100
- [CP3] source-chrome detection (website UI text leaked into content) is whole-phrase: "প্রাসঙ্গিক বইপত্র" (inside a Bangla word) and prose containing "মন্তব্য করুন" are NOT flagged; "প্রাসঙ্গিক বই" label paragraph IS flagged -> [{section_id:"body", pattern:"প্রাসঙ্গিক বই"}] — :125,137,151
- [CP4] validation rejects partial fetches: any source page with status failed -> REVIEW_REQUIRED, error "Source page was not fetched: <url> (404)." — :163
- [CP5] empty discovered TOC leaf -> error "TOC content leaf has no extracted body: শূন্য অধ্যায়." — :193
- [CP6] persist_curated_book writes: Book(title, state READY, review_state PENDING), raw_scrape_payload with curated_document_model_id and content_summary.content_item_count (heavy `content_items` NOT duplicated into raw payload), book.content_items kept; CuratedBookDocument (1), CuratedEntity (translator), CuratedSection (body); sections stored without raw html — :215
- [CP7] verify_curated_result detects mismatch: error "Persisted content_items do not match projection." — :237
- [CP8] curate command: `--skip-existing` skips already curated sources (report processed 0, skipped_existing 1, results[0].skipped True); normal run report {processed, validated, verified, verification_failures 0, results[{verification_errors [], book_id, curated_document_id}]}; `--require-validated` -> review-required documents are NOT persisted (report review_required 1, failed 1, validation_errors listed, 0 CuratedBookDocument); `--require-catalog-match` compares catalog entry to extraction -> catalog_mismatches 1, blocked 1, catalog_errors "Catalog title mismatch: expected ভুল বই; extracted সোফির জগৎ.", nothing persisted — :253,294,328,365
- [CP9] review-required curated book (when persisted) -> Book.state needs_review, review_state needs_review, NO generated assets — :401
- [CP10] generate_exports(curated["document"]) accepts the curated document payload: writes book.html and "<title>.epub" — :419
- [CP11] LearnDash manifest parser: collect_learndash_toc preserves section headings (ld-item-list-section-heading "প্রথম খণ্ড") as parents, nested topics, pagination (`data-pager-results {"total_pages":2}` -> fetches `?ld-courseinfo-lesson-page=2`), has_paginated_toc True; paths ["প্রথম খণ্ড","অধ্যায় ১","প্রসঙ্গ ১"]; relative links made absolute — :429
- [CP12] manifest content fetch does not retain soups (ctx.cache {} , pages kept 1) — memory rule — :503
- [CP13] front matter stops before a numeric body marker ("০১.", "০২."): "ভূমিকা — অপ্রাপণীয়া" becomes front section; numeric segments become content items titled "১","২"; main_content "" — :538
- [CP14] duplicate source-backed paths are disambiguated by suffix: second "সেইসব ঈদ" -> "সেইসব ঈদ (২)" in both toc and items — :560
- [CP15] container lessons (no inline topics) are probed: each lesson page fetched; sub-chapters taken from `.ld-course-navigation` second `.ld-lesson-items` container (the one WITHOUT .ld-is-current-lesson) as topic children (type "topic" with url); story content on the container lesson does not prevent expansion; leaf lesson stays a leaf — :605

### 14t — notes: frontend/unit part A (accessValidation 101, apiErrors 21, apiResponse 15, apiText 69, bookDetailReaderLaunch 61, bookExportPrice 444, embeddedReaderScrollbarTheme 25, embeddedReaderThemeTokenScope 32, homePageToolbar 27, localStackConfig 29, localWorkerConfig 55, notificationAudio 123, processingCreatedNotificationBuffer 103, readerManifest 44) + package.json (type module) + playwright.config.js


Runner: `node --test` (node:test + assert/strict), no bundler; modules import app/frontend/src/... by path.

- [FU1] email utils: normalizeEmail trims; isValidEmail("reader@example.com") true, "reader" false, whitespace ok; getEmailValidationState -> {normalizedEmail, hasEmailInput, emailLooksValid}; isValidKindleEmail true only for exact domain `@kindle.com` (not free.kindle.com, not example.com); getKindleEmailValidationState -> {normalizedEmail, hasEmailInput, emailLooksValid (kindle-aware), baseEmailLooksValid, kindleDomainLooksValid} — accessValidation.test.js
- [FU2] getAccountAccessLabels(account{global_scopes}, scopeLabelMap) -> labels mapped and SORTED alphabetically (["Edit metadata","Read durable books"]); formatAccountAccess joins labels, "-" when none — same file
- [FU3] createApiError({status,path,payload}) keeps backend `detail` as message (even for 502), exposes `.status` — apiErrors.test.js
- [FU4] parseResponse(204 with json content-type) -> null — apiResponse.test.js
- [FU5] payloadMessage: prefers `detail` string; else first field validation message; skips empty detail and descends into nested arrays/objects (`entries[0].content[0]`); firstPayloadIssue -> {field, message}; payloadFieldMessage(payload, labelMap) -> "Account permissions: Select at least one account permission."; formatApiError({message,payload}) humanises unmapped field ("New Password: Ensure this field has at least 12 characters.") — apiText.test.js
- [FU6] reader launch: buildBookReaderLocation(launchPayload, slug) -> "/reader?slug=<slug>&manifest=<encoded manifest_url>&appNav=hidden"; falls back to the `manifest` query param inside launch_url; launchBookReader({slug, apiClient, navigate}) POSTs `/access/books/<slug>/reader-launch/` with {method:"POST", body:{}} then navigates — bookDetailReaderLaunch.test.js
- [FU7] reader manifest: resolveReaderManifestUrl(payload, normalizeUrl) extracts manifest from launch_url; normalizeReaderManifestPayload rewrites epub_download_url, html_preview_url, reading_session_url, bookmarks_url to the browser origin — readerManifest.test.js
- [FU8] export price (logic inlined because Node cannot resolve extension-less imports — weak test: it tests a COPY, not production code): bookExportRows(books) row fields {catalogCode,title,contributors,authors,translators,editors,publishers,categories,series,type,price,state,review,createdAt}; price: string kept, numeric -> String, 0 -> "0", null/undefined/"" -> ""; type manual->"Manual" else "Digital"; created date "Mar 15, 2024" (en short); contributors line "Alice Author · Translator: Bob · Editor: Carol · Publisher: X" or "Contributor unavailable"; compiler role folded into editor; authors who also appear as non-author roles are hidden; null books -> [] ; CSV header (14 columns): Book ID, Title, Writer / Translator / Editor / Publisher, Writers, Translators, Editors, Publishers, Categories, Series, Price, Type, State, Review, Created At (Price between Series and Type); escapeCsv quotes values with , " or newline and doubles quotes, null -> ""; slugifyFilename lowercases, non-alnum -> "-", trims, fallback "books-export" — bookExportPrice.test.js
- [FU9] source-text tests (grep CSS/JSX): embedded reader theme tokens are scoped to `body.epub-container, .reader-page-fullscreen.epub-container` (+ `.theme-type-1/2`), never bare `.epub-container {`; scrollbar theming targets `.epub-container .epub-reader-container .epub-contents` with `scrollbar-color: var(--scrollbar-thumb) var(--scrollbar-track)`, not `body.epub-container` — embeddedReader*.test.js (brittle: assert source text)
- [FU10] HomePage wires `sort` filter field options into CatalogToolbar (sortValue, sortOptions, onSortChange sets search params) and BookCardGrid gets observeLoadTrigger (infinite scroll) — homePageToolbar.test.js (source-grep)
- [FU11] infra-as-test: local docker-compose passes `CELERY_TASK_ALWAYS_EAGER: ${CELERY_TASK_ALWAYS_EAGER:-0}`; app.env.example documents `CELERY_TASK_ALWAYS_EAGER=0`; worker pinned single-task: CELERY_WORKER_CONCURRENCY 1, PREFETCH_MULTIPLIER 1, MAX_TASKS_PER_CHILD 1, flags --pool=solo --concurrency=1 --prefetch-multiplier=1 --max-tasks-per-child=1 — localStackConfig/localWorkerConfig tests (memory-safety rule for scraper worker)
- [FU12] notification audio: createNotificationSoundPlayer({AudioContextClass}) returns playSound(type) -> true; one AudioContext created lazily and resumed once (resume called once when suspended); two-tone presets: success 660Hz then 880Hz, error 260Hz then 196Hz, info 420Hz then 560Hz; mute preference read/write via injected storage (readNotificationSoundMuted default false, writeNotificationSoundMuted) — notificationAudio.test.js
- [FU13] created-notification buffer: createCreatedNotificationBuffer({intervalMs:180000, onFlush(count), schedule, clear}); addCompletedCount accumulates (3+2=5), one timer, flushes once after 3 minutes (179999ms: nothing; +1ms: flush [5]); flushIfPending() flushes immediately and returns count (10) and cancels timer; message createdNotificationDescription(10) = "10 books created." — processingCreatedNotificationBuffer.test.js

### 14u — notes: frontend/unit part B: manualBooksExcelExport (328), manualBooksModule (354), physicalBooksEdit (419), tagInputKeyboard (544), toastManager (154), urlNormalization (48)


WEAKNESS: most of these tests inline a verbatim COPY of production logic (because Node ESM cannot resolve extension-less Vite imports) — they test the copy, not the app. Only manualBookFilters.js, toastManager.js, urlNormalization.js/urls.js are imported for real.

- [FU14] Manual books Excel export: escapeXml (& < > " ' escaped, control chars \x00-\x08,\x0B,\x0C,\x0E-\x1F stripped); bindingLabel(hard_cover|Hard Cover|hardcover -> "Hardcover"; paperback variants -> "Paperback"; other kept; "" -> ""); languageLabel(bn->"Bengali", en->"English", other kept); safeSheetName: replace \ / : * ? [ ] with "_", cut to 31 chars, trim, empty -> "Sheet<index+1>"; groupBooks(books, groupBy) groups into worksheets: category (multi-category books appear in each; none -> "(None)"), publisher (publisher or manual_publisher), binding (normalised labels), language, contributor (authors+translators+editors names; compiler==editor; same name de-duplicated; author hidden if same person is also non-author; legacy `authors` fallback; none -> "(None)"); order of first appearance — manualBooksExcelExport.test.js
- [FU15] Manual books module: emptyManualBookForm default binding "hard_cover", empty title/writers/categories/publisher/price; defaultManualBookFilters = {q,writer,translator,editor,category,publisher,binding,ownership: "" ; record_type:"manual", sort:"-created_at"}; MANUAL_BOOKS_EXPORT_STORAGE_KEY "manual-books-export"; toolbar fields exclude `sort`; sort options include {value:"-created_at", label:"Newest first"} — manualBooksModule.test.js
- [FU16] loadManualBookOptions fetches in parallel six reference lists `/catalog/{categories,writers,translators,editors,series,publishers}/?record_type=all&sort=name` and merges contributor suggestions (writers+translators+editors) de-duplicated case-insensitively after trimming, sorted A-Z (localeCompare)
- [FU17] createManualBook(form) POST `/catalog/manual-books/` with price "" -> null, other price kept ("499.50")
- [FU18] loadManualBooksForExport pages through `/catalog/manual-books/?record_type=manual&page=N&limit=100` (page size 100) using pagination.page_count and concatenates entries (3 pages)
- [FU19] Physical book edit mapping: mapBookToComposerForm(book): reads fields with manual_* fallbacks (manual_binding, manual_publisher, manual_price, manual_is_compilation, manual_language); binding normalised to "hard_cover"|"paper_back"|"" (case/space/underscore insensitive: "  Hard   Cover ", "HARD_COVER", "paperback"); price -> string ("150"), null -> ""; language default "bn"; writers/translators/editors from contributor roles (compiler -> editors); fall back to `authors` when no contributors; mapComposerFormToPayload(form) -> {title, summary, contributors:[authors..., translators..., editors..., publisher as role "publisher" if non-empty], categories, series, is_compilation, binding, publisher, price ("" -> null), language}; names are NOT trimmed in payload (sent as typed; server normalises) — physicalBooksEdit.test.js
- [FU20] writer-cell display rule: limitContributorRole -> "Writer: X" if authors else "Translator: X" if translators else "Editor: X" else "—"; otherwise all parts joined ("Writer: A, Translator: T, Editor: E") or "Contributor unavailable"; contributor validation: at least one of writer/translator/editor required
- [FU21] TagInput keyboard state machine (copy): suggestions = prefix-insensitive substring filter, excluding already-selected (case-insensitive), capped at 6; ArrowDown/ArrowUp cycle with wrap (from -1: Up jumps to last); Tab selects highlighted or first suggestion; Enter or "," confirms highlighted suggestion else free text; Escape closes dropdown (focus false, highlight -1) only when suggestions visible; Backspace on empty input removes last tag; ArrowLeft/Right call field-navigation callbacks only when input empty; duplicates (case-insensitive) and whitespace-only ignored silently; internal whitespace collapsed ("ফারসীম  মান্নান" -> single spaces); BLUR commits typed text (regression: "Add & next" button lost typed writer) — tagInputKeyboard.test.js
- [FU22] createToastManager({schedule, clear, createId, playSound}): push(toast|string, type) with groupKey merges into the existing toast (title/description replaced, sound NOT replayed, timer reset); holdOpenMs 120000 keeps a grouped toast open for a quiet window (119000ms still visible, new arrival resets timer, disappears 1001ms later); setMuted(true) keeps toasts but suppresses sound (snapshot.muted); `soundType` can differ from visual `type` (info toast plays "error" sound); API: getState, subscribe(cb) -> unsubscribe, push, setMuted, destroy — toastManager.test.js
- [FU23] URL normalisation: normalizeAppUrl(url, {currentOrigin, apiBaseUrl:"/api"}) rewrites absolute backend API URLs ("http://testserver/api/...") to current origin; for launch URLs rewrites the nested encoded `manifest` param only (host frontend.test preserved); resolveApiUrl("/processing/stream/") = `<window.location.origin>/api/processing/stream/` — urlNormalization.test.js

### 14v — notes: frontend/e2e part 1: globalSetup (142), support/{liveApp 93, liveEnv 57, playwright 7, seedData 71}, access-page (58), auth-pages (41), auth-public-* (create-password-totp 118, expired-create-password 75, forced-totp-setup 65, login-and-reset-request 171, reset-and-password-validation 84, pages 1), catalog-pages (82), home-filter (80), library-page-live (52), pages/authPage (98), pages/accessPage (99)


#### Harness
- globalSetup: waits for frontend/backend (fetch + curl fallback, accepts 200/302/401, 120s), optionally starts docker stack (unless PLAYWRIGHT_SKIP_STACK_START=1) and runs seed script (unless PLAYWRIGHT_SKIP_E2E_SEED=1), then logs in headless as super admin (SUPER_ADMIN_EMAIL / SUPER_ADMIN_PASSWORD from local/env/.env, defaults admin@example.com/changeme; 3 attempts) and saves storage state at tests/frontend/.auth/superadmin.json. Login sequence: /login -> fill "Email" and "Password" labels -> button /Continue|Verify/ -> wait /home heading "All Books".
- `loginAsSuperAdmin(page)` per test (retries 3x; resilient to existing session; refreshes storage state). installWindowOpenRecorder stubs window.open to record URLs (readOpenedUrls).
- Public tests use `test.use({storageState:{cookies:[],origins:[]}})` and route-mock **/api/auth/session/, **/api/csrf/ (204), etc.
- Selectors rely on roles/labels and `data-testid`: access-users-section, access-user-form, access-users-table, access-grant-form, access-rules-table, access-rules-tab; classes .book-card, .catalog-search-sort .catalog-toolbar-select, .catalog-filter-field, .custom-select-trigger/.custom-select-search-input/.custom-select-option-button, .book-table tbody tr, header.topbar(.topbar-public) .topnav .session-box .profile-menu-trigger, section.auth-setup-card.login-card, .login-email-feedback(-valid|-invalid), .backend-status-overlay.

#### Behaviours
- [E1] Access page (live): /access heading "Users & Access"; search users "access-manager" + status filter "active", Edit seeded user, check checkbox "Require Two-Factor", "Save User" -> toast "User updated."; filters (search text and status select) persist after save; after reload the checkbox is still checked — access-page.spec.js
- [E2] Access rules (live): tab "Access Rules"; select user by email label, tick permission "Edit metadata", target type button "Books", search targets "Access Grant", tick book "E2E Access Grant Book", "Save Access" -> rule row shows book title and user email in rules table
- [E3] Home after sign-in: heading "All Books"; seeded books "E2E Home Library Book", "E2E Search Companion Book" visible; search box placeholder "Search all books by title, book ID, or writer..." + Enter with "Companion" leaves only the companion book — auth-pages.spec.js
- [E4] home shows `.book-card`, sort select (`.catalog-search-sort .catalog-toolbar-select`) and a "Filters" button
- [E5] Home filters: opening Filters, choosing Contributor "E2E Writer" via searchable select restricts the Series options (contains "E2E Starter Series") and Category options (contains "E2E Fiction") — dependent/faceted filters (uses fixed 2s wait; flaky-prone) — home-filter.spec.js
- [E6] Library page (live): /library heading "Books"; first request `/api/catalog/books/?page=1&limit=60`; changing sort select to "title" issues a request with sort=title, limit 60; table rows `.book-table tbody tr` — library-page-live.spec.js
- [E7] Catalog property pages: /categories (search placeholder "Search categories or codes..."), /series ("Search series or codes..."), /writers ("Search writers or codes..."): search "E2E Fiction"/"E2E Starter Series"/"E2E Writer", open result -> URL /library with filtered books (primary book / companion book / access book links visible); /created-books heading "My Books", search placeholder "Search your books by title or book ID...", Enter keeps "E2E Detail Book" — catalog-pages.spec.js
- [E8] Login page does NOT request /api/processing/state/ and shows no "The application has restarted. Please log in again." status nor "Authentication credentials were not provided." alert — auth-public-login-and-reset-request.spec.js
- [E9] Sign-in form: Continue disabled until valid email AND password; invalid "reader" shows `.login-email-feedback-invalid` "Enter a valid email address."; valid shows "Email looks good."
- [E10] /reset-password heading "Reset your password": button "Reset Password" disabled until valid email; no helper text "Enter your email address and we'll send you a secure password reset link."; POST /api/auth/password-reset/ {email}; success text "Reset email has been sent."; 404 shows "No user exist with this email." only
- [E11] /reset-password/confirm?uid&token (heading "New password"): validate request on load; invalid/expired -> heading "The link has expired", no "Reset password" button — auth-public-reset-and-password-validation.spec.js
- [E12] /create-password?uid&token (heading "Create password"): short password 400 detail -> error alert titled "Something went wrong" with the detail text "Ensure this field has at least 12 characters."
- [E13] create-password with TOTP-required user: confirm body {uid, token, new_password}; success detail "Password saved. Continue with two-factor setup." next_step "totp_setup" -> toast "Password created. Set up two-factor authentication to continue." -> /two-factor-setup, heading "Set up two-factor authentication", public header only (no nav, session box, My Books link or profile menu), button "Verify and Continue"; page on this route must not show text "Your administrator requires an authenticator app before you can use the rest of Bangla Library." (copy suppressed in invite flow) — auth-public-create-password-totp.spec.js. Public topbar on /create-password has no "Sign in" link and no session box.
- [E14] expired create-password link: first validate OK, after submit (confirm 200 next_step login -> /login), revisiting the same link validates again -> 400 -> heading "The link has been expired" (note different wording from reset: "has expired") and no "Create password" button; confirm called once — auth-public-expired-create-password.spec.js
- [E15] forced TOTP gate: authenticated session with totp_required & totp_setup_required true visiting /home is redirected to /two-factor-setup (public topbar, no nav/session/profile) — auth-public-forced-totp-setup.spec.js
- Session payload shape used in mocks: {authenticated, user:{id,email,full_name,profile_image_url,is_active,is_staff,is_superuser,totp_enabled,totp_required,totp_setup_required,capabilities:[]}}; 2FA setup payload {provisioning_uri, secret, qr_svg}. Brand text in UI/emails: "RSalehin24 Library" (email/issuer) vs "Bangla Library" (UI) — inconsistent.
- Seed data (support/seedData.js): access user access-manager@e2e.local "E2E Access Manager"; books: homePrimary "E2E Home Library Book", homeSecondary "E2E Search Companion Book", detail "E2E Detail Book" (source https://www.example.com/books/e2e-detail-book/), preview "E2E Preview Book", access "E2E Access Grant Book", incomplete "E2E Incomplete Catalog Book"; catalogFilters category "E2E Fiction", series "E2E Starter Series", writer "E2E Writer"; 19 submissions (alpha, beta; user pending/processing/stopped/deleted/failed; automation pending/ready/processing/queued/stopped/deleted; curation ready/processing/queued/stopped/deleted; duplicateReview); catalog entries "000 E2E Alpha Catalog Book", "001 E2E Beta Catalog Book"; processing failedLogMessage "Seeded failed job log entry.", scheduled run summaries "7 create" (active) / "2 create" (failed); bookmark label "Seeded Bookmark".

### 14w — notes: frontend/e2e part 2: access-page-mocked (+ accessPageMocks 48, invitations 206, permissions 89, validation-and-pagination 242, facade 1), book-detail-page (176), pages/bookDetailPage (80), create-books (260), manual-books (241), pages/manualBooksPage (85), pages/catalogPropertyPage (29)


- [E16] Access page create user (mocked): form data-testid access-user-form, fields placeholder "Full name", input[type=email], checkbox "Require Two-Factor", permission checkboxes by label ("Read durable books"), button "Create User"; with setup email default ON the POST body is exactly {email, full_name, is_active:true, totp_required:true, send_invite_email:true, global_scopes:["read:durable"]} (no password); success toast "User created. Setup email sent." — access-page-mocked-invitations.spec.js
- [E17] users table: pending invitee (can_resend_setup_email true) row has buttons "Resend Email" and "Edit"; the superuser row shows "Locked" (cannot be edited here) — same file
- [E18] permissions chips: each global scope is its own `.access-permission-chip` labelled via references.account_scopes (value->label: "Edit metadata", "Read durable books"); users payload {rows, pagination{offset,limit,totalCount,hasMore,nextOffset}}; user row fields {id,email,full_name,is_active,is_superuser,totp_required,totp_enabled,global_scopes,grant_count,can_resend_setup_email}; references payload {users,books,categories,writers,account_scopes[{value,label}],scoped_scopes} — permissions spec
- [E19] users list infinite scroll: first page 60 rows (page size 60), scrolling to row ~30 triggers offset=60 request, all 85 rows rendered — validation-and-pagination spec
- [E20] create-user form validates email live: "invalid-email" -> `.login-email-feedback-invalid` "Enter a valid email address.", Create User disabled, no POST
- [E21] direct-password user (uncheck "Send Setup Email", placeholder "Create password" with "short"): server 400 {password:[...]} -> alert "Something went wrong" + "Password: Ensure this field has at least 12 characters." (field label prefix)
- [E22] Book detail (live, seed "E2E Detail Book"): data-testid book-detail-hero, book-metadata-workspace, book-asset-html, book-asset-epub, book-send-to-kindle-button, book-open-reader-button; headings "Table of Contents", "Entities and Details"; TOC shows "Chapter 1" — book-detail-page.spec.js
- [E23] Open reader: URL /reader?...manifest=...; `#reader-view`, `#viewer iframe` visible (epub rendered inside iframe, content non-empty); controls: button "Toggle table of contents" (aria-expanded true by default, toggles), TOC items `.slide-contents-item-label` (clicked item gets aria-current=true), "Open reading settings" (panel #reader-settings-panel aria-hidden false), "Increase font size" raises localStorage `epub_reader_font_size` (default 20), theme button "Night" aria-pressed true and localStorage `epub_reader_theme_index` = "2", "Next section" keeps iframe
- [E24] metadata editing: fill Title in workspace, remove a bookmark ("Delete bookmark" on `.notes-item` card with label "Seeded Bookmark") WITHOUT losing the unsaved title; "Save metadata" navigates to /books/e2e-detail-book-updated (slug follows title), persists after reload, bookmark gone, no "Opening" text; test restores title in `finally` (stateful live test)
- [E25] HTML preview lock: localStorage key `ebook_preview_lock:/api/access/books/<slug>/download/html/` = {tabId, ts} (recent) disables the HTML preview button (single preview tab at a time) while EPUB button enabled; clicking EPUB opens `/api/access/books/<slug>/download/epub/` via window.open
- [E26] /create (mocked processing API, EventSource replaced by mock that emits "connected"): heading level 1 "Create"; card data-testid create-requests-card with row create-requests-row-<requestId>; text "Create EPUB" must NOT appear. State payload shapes: summary{catalog{records,notCreated,active,created,onHold}, notifications{pipelineActive,activeSync,hasActiveWork}, create{requests,queue,processing,created}, onHold{paused,failed,duplicate,deleted}, incomplete{incomplete,completed}}, sync{status,progress,fetchedCount,skippedCount,updatedCount,appendedCount,message "Ready to sync.",remotePages,pageIndex}, syncStates{catalog,incomplete}, automation{catalog|incomplete:{enabled,interval,time,saved,lastRunAt,statusMessage}}, versions map of 18 domains (catalog-overview, catalog-sync, catalog-automation, catalog-records, create-overview, create-requests, create-queue, create-processing, create-created, on-hold-overview, on-hold-paused/failed/duplicate/deleted, incomplete-overview, incomplete-automation, incomplete-records, incomplete-completed); table payload {card, version, rows[{id,title,url,displayUrl,category,writer,translator,composer,publisher,status,updatedAt,linkedBookSlug,selectable}], pagination{offset,limit,totalCount,hasMore}, filters{categoryOptions,statusOptions}}; record fields {id,name,url,category,writer,translator,composer,publisher,createdAt,updatedAt,bookCreationState,selectable,latestRequestId}; request fields {id,bookRecordId,state,createdAt,updatedAt,progress,errorMessage,isResumed,isConfirmedNotDuplicate,duplicateOfRequestId,duplicateOfRecordId,duplicateConfirmed,linkedBookId}; ui.pipelineDelayMs 2000. Session user capability "processing:manage".
- [E27] Manual books page (/manual-books heading "Physical Books' List"): "Add manual book" opens `#manual-book-composer`; fields Title, tag fields Writer, Category (label.tag-field input); "Add & next" saves; search placeholder "Search manual books, book IDs, writers..." finds unique title — manual-books.spec.js
- [E28] blur commit: typing tags WITHOUT Enter then submitting still saves (tags committed on blur)
- [E29] "Done": with filled form saves, closes composer, book findable; with empty form closes without saving; with title only (missing required Writer and Category) keeps composer open (validation error); toolbar button "Close add book form" with input saves then closes; "Clear fields" button exists
- [E30] sort select options: no catalog_code / -catalog_code; has manual_publisher, -manual_publisher labelled "Publisher A-Z"/"Publisher Z-A"
- [E31] filters drawer fields: Writer, Translator, Editor, Category, Publisher, Binding (select with Any, Hardcover, Paperback)
- [E32] "Export options" toggle shows `.manual-books-download-row` group-by select (No grouping, Category, Publisher, Binding, Language, Contributor); button "Excel export" downloads file named `manual-books.xlsx`
- Catalog property page model: rows `tbody tr` with link "Open" to /library filtered

### 14x — notes: frontend/e2e part 3: catalog-book-tables-mocked (299), page-loaders-mocked (254), profile-page-mocked (260)


- [E33] Book list pages share inline controls and incremental loading: /library (heading "Books", TABLE view), /home ("All Books", cards), /created-books ("My Books", cards). With 75 mocked books: `.catalog-result-count` text "75"; order in `.catalog-search-actions`: sort select, filter toggle, result count; first request page=1 limit=60; table `.book-table tbody tr` 60 rows (cards `.book-card:not(.book-card-skeleton)` 60); scrolling to row ~30 shows `book-table-load-more-skeleton` / `book-grid-load-more-skeleton` while page 2 pending; then 75 rows; page 2 request limit 60 — catalog-book-tables-mocked.spec.js
- [E34] List API shape (mock): GET /api/catalog/books/?page&limit&q&sort&ownership=mine -> {entries[], pagination{page,limit,total_count,page_count,has_previous,has_next}}; book fields {id,slug,catalog_code,title,authors,categories,series,record_type (manual|digital),created_at,primary_source{display_path},is_in_my_books,my_books_added_at}; POST/DELETE `/api/catalog/books/<slug>/my-books/` (POST 200 book, DELETE 204); `/api/saved-filters/` returns []
- [E35] Books table "My Books" action: button aria-label "Add <title> to My Books"; on click it is disabled, aria-busy true, text "Adding...", two `.button-label-spinner-slot` elements (symmetric slots so label stays centred: grid columns first==third); afterwards button "Remove <title> from My Books" enabled and its label is horizontally centred (<1px offset)
- [E36] My Books cards expose compact remove button `.book-card-remove-button`: position absolute with top/right set, background NOT red (rgb(220,38,38)), at least 38x38 px (touch target)
- [E37] Loaders: catalog property pages (/categories) keep header visible with in-table skeleton `property-table-table-skeleton` while loading; contributor tabs (/writers -> link "Translators") replace stale rows with the skeleton until the next list loads (stale "Writer One" gone); property rows {id,catalog_code,name,book_count,digital_book_count,manual_book_count,created_at}; /access shows `.page-loader-variant-management` until users/grants/references load; /create-password shows `.page-loader-variant-auth` while session request is pending — page-loaders-mocked.spec.js
- [E38] Profile page (mocked): /profile heading "Profile"; button "Edit" reveals section "Two-Factor Authentication"; profile menu `profile-menu-trigger` has `profile-alerts-toggle` checkbox (checked by default) persisted in localStorage key `app.notifications.muted`; "Setup Authenticator" -> heading "Authenticator Setup" (no toast), "Cancel Setup" hides it (no toast); verify with code 000000 -> 400 "Invalid TOTP token." shown as alert (dismiss via "Dismiss notification"), valid code -> status "Two-factor enabled." (label "Verification Code", button "Verify and Enable")
- [E39] Kindle mails section ("Kindle Mails", collapsed; "Expand"): shows sender email (library-sender@example.com) and text "Personal Document Settings"; fields "Kindle Email 1", "Kindle Email 2", button "Add Kindle Email" (disabled until current entry is a valid kindle address), "Save Changes" -> toast "Profile updated." ; PATCH multipart with `kindle_emails_text` newline-separated; validation messages: invalid -> "Enter a valid email address."; other domain -> "Use a Kindle email ending in @kindle.com."; valid -> "Kindle email looks good."
- Note on wording drift: backend error "Enter a Kindle email ending in @kindle.com." vs UI "Use a Kindle email ending in @kindle.com."

### 14y — notes: frontend/e2e processing mock harness: processing-test-matrix.md (48), pages/processingPage.js (207, see 14z), processing-pages/{index 13, bootHelpers 18, fixtures 142, stateRows 221, statePayloads 124, catalogSyncState 257, catalogProgressStart 142, catalogProgressCompletion 221, catalogMatrixHelpers 119, catalogManualCases 9, catalogAutomationCases 10, pipelineAdvance 30, processingApiMock 45 (minified single-line), interactionHelpers 104}, processing-pages.spec.js (1, facade)


WARNING: the harness re-implements the backend processing state machine in JS (a second copy) — duplicated logic; the rebuild should have one source of truth and generated types.

#### processing-test-matrix.md (design intent for live tests)
User stories: (1) Manual Sync and Catalog Automation control ONE shared catalog runtime and cannot run at the same time; (2) button-started and scheduler-started runs behave identically; (3) catalog-records, incomplete-records and overview cards hydrate while sync still runs; (4) search/filter/count are card-local and reflect the full matched dataset, not only rendered rows; (5) each request-state card updates independently; (6) Catalog Automation creates `initial` requests only for records with no prior request history; (7) records that leave the live "অসম্পূর্ণ বই" category after a successful incomplete run move to `Updated`.
Deterministic live scenarios (area/scenario): manual run ownership (Manual Sync disables Automation run until idle) and the reverse; scheduler parity; catalog-records refetch after each fully reconciled page flush with server-reported total; catalog-overview refetches only when aggregate counts change; post-sync request creation only for records with no request history; Create cards (Requests, Queue, Processing, Created) refetch only when rows enter/leave their own bucket; same for On Hold (Paused, Failed, Duplicate, Deleted); Created -> Deleted -> Create Again; Duplicate -> New; incomplete cards hydrate during run; Updated card after final diff; card-local filters counts over full dataset (even if first 60 rendered); empty -> non-empty only when live rows arrive. Best-effort (only if naturally observed): source outage, rate limiting, worker crash. Real-flow coverage = processing-pages-live*.spec.js + test-processing-live.sh against live dev stack with worker, processing-worker, beat, Redis, Postgres, real source site.

#### Mock-derived rules (UI contract)
- Cards/domains (PROCESSING_CARD_KEYS, 18): catalog-overview, catalog-sync, catalog-automation, catalog-records, create-overview, create-requests, create-queue, create-processing, create-created, on-hold-overview, on-hold-paused, on-hold-failed, on-hold-duplicate, on-hold-deleted, incomplete-overview, incomplete-automation, incomplete-records, incomplete-completed.
- Request states: initial, queued, processing, created, paused, failed, duplicate, deleted. Mock pipeline tick: initial->queued->processing->(created | failed | duplicate by `pipelineOutcome`). created gets linkedBookId "linked-<recordId>" and slug "<recordId>-book". PROCESSING TIMEOUT 20 minutes (PROCESSING_TIMEOUT_MS) -> state failed with message "Processing exceeded 20 minutes without completing." (backend maintenance test uses 25-30 minute stale thresholds and re-queues instead — inconsistency to resolve).
- Record selectability (checkbox): a record is selectable unless it has a latest request that blocks it; blocking = any request whose state is not failed/deleted; confirmed duplicate: selectable only when the original request is failed/deleted.
- Incomplete category keywords: "incomplete", "unfinished", "অসম্পূর্ণ", "অসম্পূর্ণ বই" (case-insensitive substring).
- Table payload: rows[{id, recordId, requestId, title, url, displayUrl (decoded), displayPath, category, writer, translator, publisher, status, updatedAt, selectable, progressCheckpoint, progressSavedAt, errorMessage, isResumed, isConfirmedNotDuplicate, linkedBookId, linkedBookSlug, duplicateOfRequestId, duplicateOfRecordId, duplicateConfirmed}], pagination{offset,limit,totalCount,returnedCount,hasMore,nextOffset}, filters{categoryOptions,statusOptions} only when includeFacets (query includeFacets=0 disables), query params card, q, category, status, offset, limit. Search matches title,url,displayUrl,displayPath,writer,translator,publisher,category,status and request details (checkpoint, error message, "Confirmed duplicate", "Confirmed new", "Resumed from saved progress"). catalog-records ordering: not_created first, then others, then title localeCompare.
- Summary payload: catalog{records,notCreated,active,created,onHold}, create{requests,queue,processing,created}, onHold{paused,failed,duplicate,deleted}, incomplete{incomplete,resolved}, notifications{activeRequests,createdCount,failedCount,duplicateCount,latestFailedMessage}. (Earlier create-books mock used incomplete.completed and notifications.pipelineActive — payload keys drift between mocks.)
- GET /api/processing/state/?includeLists=0 returns {sync, syncStates{catalog,incomplete}, automation, ui, orchestration{manualPipelineAdvance:false}, summary, versions}; includeLists=1 also records/requests. GET /api/processing/card/?card=<key> returns {card, summary|sync|automation, version}. Mutations return {ok:true, versions:{changed domains}, createdCount|changedCount}.
- SSE: GET /api/processing/stream/ emits "connected" then "versions" {eventId, versions}; client refetches changed domains; client must degrade when EventSource is unsupported (eventSourceMode "unsupported") and on stream error.
- Endpoints mocked: POST sync/start (body {remotePages}), sync[/scope]/pause|advance|resume|stop, records/create-requests {ids}, requests/action {ids, action: delete|pause|resume|retry|new|confirm_duplicate|create_again|recreate}, automation/catalog (settings save -> saved:true, statusMessage "Saved."), automation/catalog/run, automation/incomplete, automation/incomplete/run (message "Incomplete catalog sync is running.").
- Messages: "Syncing catalog records.", "Automated catalog sync is running.", "Continuing catalog sync from the saved endpoint.", "Continuing automated catalog sync from the saved endpoint.", "Creating book requests from the synced catalog records.", "Resuming automated request creation from saved progress.", "Pausing after the current page finishes.", "Pausing automated catalog sync after the current page finishes.", "Pausing automated request creation after the current batch finishes.", "Pausing incomplete catalog sync after the current batch finishes.", "Sync progress saved. Catalog now has N book record(s).", "Saved progress for N record(s) before pausing.", "Saved request creation progress after scanning N record(s).", "Sync complete. Updated X, Skipped Y, Added Z.", "Automated catalog sync complete. Updated X, Skipped Y, Added Z.", "Scanned N catalog record(s); created M request(s) so far.", "Created N requests.", "Resolved N book(s).", "Incomplete catalog sync complete. Updated N book(s).", "Catalog sync stopped.", "Automated catalog sync stopped.", "Incomplete catalog sync stopped.", "Restarting incomplete catalog sync from the beginning.", "Ready to sync." (singular/plural handled: "1 book" vs "N books").
- Reconcile page: new record appended (appendedCount++), existing with different updatedAt updated (updatedCount++, bookCreationState preserved), same updatedAt skipped (skippedCount++). Catalog request creation batch default 50 (ui.catalogRequestBatchSize), scans records sorted by id after lastRecordId; creates a request when no request and record not_created, or latest request failed/deleted.
- Catalog button matrix (manual cases vs automation cases) — controls and testids: `catalog-sync-start-btn` (aria-label "Start sync", data-state idle), `catalog-sync-pause-btn` ("Pause sync" syncing / "Pausing sync" pausing disabled), `catalog-sync-resume-btn` ("Resume sync", data-state paused), `catalog-automation-run-btn` (labels "Run automated catalog sync" idle, "Pause automated catalog sync" syncing, "Pausing automated catalog sync" pausing disabled, "Resume automated catalog sync" paused, "Pause automated request creation", "Pausing automated request creation", "Resume automated request creation"). Ten phase combos each (not_started/not_started, running/not_started, pausing/not_started, paused/not_started, completed/not_started, completed/running, completed/pausing, completed/paused, completed/completed, paused/paused). Key outcomes: when the catalog runtime is owned by manual sync (running/pausing/…), automation run is DISABLED and vice versa (manual Start disabled while automation owns sync or request creation is running/pausing); paused sync -> Resume sync enabled and automation shows "Resume automated catalog sync" enabled; completed/not_started: automation shows Run and after click becomes "Pause automated request creation"; completed/paused: automation shows "Resume automated request creation" and manual "Start sync" is enabled; completed/completed: both Start/Run enabled (restart).
- Test hooks: data-testid patterns `<page>-<card>-card`, `<page>-<card>-row-<id>`, `<page>-<card>-select-<id>`, `<page>-<card>-count`, `<page>-automation-run-btn`, `<page>-automation-enabled` (inside `.processing-switch`); Filters button per card (accessible name starts "Filters"); notification sound spied via fake AudioContext events.

### 14z — notes: frontend/e2e processing specs part A (mocked): pages/processingPage.js (207), catalog-automation-flow (163), catalog-loading-and-skeletons (207), catalog-state-matrix (218), catalog-sync-and-record-selection (212), create-and-on-hold-actions (180), create-card-refreshes (286), create-card-state (234)


Routes: /catalog, /create, /on-hold, /incomplete (+ nav "Processing" button menu with links "Catalog"...). Page models: ProcessingPageModel uses `section.processing-card` found by heading title ("Catalog Books", "Automation", "Incomplete"), `.processing-card-head`, `.processing-card-count`, `.catalog-result-count`, `.catalog-filter-drawer(.is-open)`, `.processing-collapsible-stack`, buttons Expand/Collapse, "Save automation" -> toast "Automation saved.", "Reprocess selected", dialog confirm button "Delete".

- [E40] Catalog automation run (mock): enable switch (`catalog-automation-enabled`), interval select (weekly), time 04:30, `catalog-automation-save-btn` -> `catalog-automation-status` "Saved"; run -> button data-state syncing; creates requests for records with NO request or whose latest request is failed/deleted (3 of 5: new, failed, deleted) but NOT created or paused; status "Created 3 request(s)"; /create then shows them auto-advanced to Created; paused-old stays out of Created — processing-pages-catalog-automation-flow.spec.js:1. (Backend test PD5 only covers not_created; matrix doc story 6 says "no prior request history" — three-way inconsistency.)
- [E41] paused catalog sync: automation button aria-label "Resume automated catalog sync" data-state paused AND manual `catalog-sync-resume-btn` ("Resume sync") both enabled ("either card can resume phase one"); clicking automation continues with "Continuing automated catalog sync from the saved endpoint."
- [E42] completed sync (phaseStatuses sync completed / request_creation not_started): manual Start enabled; automation "Run automated catalog sync" starts request creation directly (skips phase 1): "Creating book requests from the synced catalog records." then "Created 1 request".
- [E43] Loading skeletons keep identical dimensions to loaded controls (automation run, toggle, interval, time, save, manual sync button, records count, table row height within 1px): testids `*-skeleton`: catalog-automation-run-skeleton, catalog-sync-control-skeleton, catalog-automation-enabled-skeleton, ...-interval-skeleton, ...-time-skeleton, ...-save-skeleton, catalog-records-table-skeleton, `.processing-value-skeleton`, `.processing-status-skeleton` (no layout shift rule) — loading-and-skeletons spec
- [E44] Bangla source URLs are displayed decoded in catalog rows (display text decoded; encoded fragment not shown)
- [E45] Manual sync completes automatically without explicit pause: Start -> `catalog-sync-loader` visible, toast/status "Sync started", pause button data-state syncing, rows from remote pages appear, finally Start enabled and `catalog-sync-progress` contains "Sync complete"
- [E46] Manual start must NOT repost stale incomplete-automation page ids: POST sync/start body has no `remotePages`
- [E47] Dual paused (sync paused + request_creation paused): Resume sync (paused) + automation "Resume automated request creation" (paused) — catalog-state-matrix spec; manual & automation matrix rows executed per case (see 14y)
- [E48] "catalog cards normalize stale record totals against live overview count": overview shows 3 even if message says 1; progress and automation statusMessage rewritten to "Catalog now has 3 book records."
- [E49] Create/On-hold/Incomplete overview cards use shared processing state (GET state) — no per-card `/card/` requests for create-overview, on-hold-overview, incomplete-overview, incomplete-automation; stat testids create-overview-stat-requests, on-hold-overview-stat-paused, incomplete-overview-stat-incomplete
- [E50] Without EventSource support: `create-stream-status` shows "Live updates are unavailable in this browser." and the page polls shared state (intervals >=15s replaced by 25ms in test) so updates still appear
- [E51] Catalog page details: heading level1 "Catalog"; records table headers include Name, URL; automation interval default weekly, time 03:00, status element absent until a message; automation controls heights 30px (button and toggle); sync button 58x58px colour rgb(236,255,246); sync flow: Start -> loader -> Pause (data-state pausing) -> Resume appears; progress "Catalog now has 2 book records" ... final summary `catalog-sync-progress-summary` "Sync complete." and details "Updated 1, Skipped 0, Added 1."; overview stat becomes 3
- [E52] Card-local search (catalog-records-search) matches writer, URL fragment, category, translator, publisher; count `catalog-records-count`; filters drawer: `catalog-records-category-filter` (select), `catalog-records-status-filter` (select; label "Not created" for not_created), active chips `catalog-records-active-filters`; a record in `processing` state has a DISABLED row checkbox; select record + `catalog-records-create-btn` -> `catalog-records-loader`, button disabled, request appears in /create (any of requests/queue/processing/created)
- [E53] Pausing manual sync persists across navigating away from processing routes: after leaving to Home and returning (Processing menu -> Catalog) the Resume button is visible within 1.2s with "Catalog now has 1 book record" (state recovered from server, not component memory)
- [E54] Infinite scroll in processing tables: 95 records, only first 60 rendered (record-70 absent), count shows 95, scrolling to row 30 shows `catalog-records-load-more-skeleton` then rows up to 70+ present; loading skeleton row is `display: table-row` with `td` `table-cell`
- [E55] Create page: card counts per bucket; created rows have "Open" link href `/books/<linkedBookSlug>`; searching "initial a" narrows only that card; category filter chips; bulk "delete" (`create-requests-delete-btn`) shows card-local loader and disables the button while OTHER cards stay enabled; Processing card has `create-processing-pause-btn` -> request moves to On Hold > Paused with detail "Paused at processing"; Created card `create-created-delete-btn` -> On Hold > Deleted
- [E56] On Hold page: overview stat paused; Failed table has column "Error Reason" and shows error text; Paused row shows checkpoint ("chapter-4"); actions: Paused `on-hold-paused-resume-btn` (-> back to Create Requests), Failed `on-hold-failed-retry-btn`, Duplicate `on-hold-duplicate-new-btn` (-> Create Requests as new), Deleted `on-hold-deleted-create-again-btn` (-> Create Requests)
- [E57] Offscreen create cards lazy-load: with a 430x520 viewport, `table:create-created` is not fetched (and version bumps do not trigger it) until the card scrolls into view; counts still come from shared state
- [E58] Version-driven refresh semantics: bumping version of one card refetches only that card's table (`create-requests`), not others; background refresh keeps already-loaded rows (no skeleton flash) until new data arrives; an SSE event with a version equal to the one already applied by an action does NOT trigger another fetch; shared (overview) version bump refetches shared state exactly once; a bump arriving while a state load is in flight is not dropped (second fetch happens, total 2)
- [E59] Card isolation: searching Requests ("alpha") and filtering Queue (category Science) are independent; deleting from Queue keeps Requests search "alpha" and its checkboxes enabled
- [E60] Phase-two checkpoint preserved when manual sync is started while request creation is paused: Start -> "Sync complete." (not "Continuing ..."), automation still "Resume automated request creation"; resuming -> "Resuming automated request creation from saved progress." then "Created 1 request"; /create > Created shows both requests
- [E61] Create cards are status-scoped; tables for requests/queue/processing have 6 header columns and no "Details" column (`.processing-col-details` absent); Created table has 7 columns including "Open"; empty cards show "No records." and keep it after load (no skeleton, no count skeleton) once loaded

### 14za — notes: frontend/e2e processing specs part B: notifications-and-isolation (134), on-hold-and-incomplete-actions (219), processing-pages-live-{catalog-runtime 130, created-lifecycle 112, duplicate-resolution 96, incomplete-runtime 92} + processing-pages-live/{processingLiveApi 77, processingLiveSetup 138, processingLiveWaiters 116} + processing-pages-live.spec.js (1 facade)


#### Mocked
- [E62] Toasts/sounds: creating requests from Catalog shows status toast "Requests created" and plays sound (fake AudioContext count > 0); profile menu `profile-alerts-toggle` (Alerts) off => no more sounds but toasts still shown (e.g. "Catalog automation saved"); there is no separate `notification-mute-toggle` in the processing page (must be absent) — processing-pages-notifications-and-isolation.spec.js
- [E63] Busy-card isolation: retry on Failed card shows `on-hold-failed-loader` and disables its own checkboxes while Duplicate card remains interactive; both loaders may be visible together; rows leave their cards when done
- [E64] Pipeline notifications: duplicate-outcome request lands in On Hold > Duplicate; failed-outcome request in Failed with "Pipeline failed after retries."; processing request idle >20 min (now = iso(40), updated iso(5)) fails with "Processing exceeded 20 minutes without completing."
- [E65] On Hold cards each show only own status (paused row shows checkpoint "saved-chapter"; failed row shows error text; duplicate; deleted) — on-hold-and-incomplete-actions.spec.js
- [E66] Duplicate action "Duplicate" (`on-hold-duplicate-duplicate-btn`, confirm duplicate) -> row detail "Confirmed duplicate"; the duplicate's record checkbox in Catalog is DISABLED while the original request is processing; after original becomes failed the checkbox is enabled (after reload)
- [E67] Incomplete page: overview stats `incomplete-overview-stat-incomplete` and `-resolved`; Incomplete records table is READ-ONLY (no select-all, no row checkbox, no recreate button), headers Name and URL (not "Book"); shows full URL text; automation defaults weekly 03:00, status element hidden until a message; control heights 30px; search "missing writer" -> count 1; category filter "Incomplete"; enable+save -> status "Saved"; run -> data-state syncing, the record resolves into Completed list as `request-incomplete-book` (a created request is synthesised), incomplete count 0; Completed card actions: `incomplete-completed-recreate-btn` (-> Create > Requests), `incomplete-completed-delete-btn` (-> On Hold > Deleted); loader `incomplete-completed-loader`
- [E68] Paused incomplete automation: run button aria-label "Resume incomplete catalog sync", data-state paused; clicking restarts from the beginning (status "Restarting incomplete catalog sync from the beginning.")

#### Live (needs full stack incl. real source site, workers; excluded unless PLAYWRIGHT_RUN_LIVE_PROCESSING=1)
- Helpers: login via API (/api/csrf/ then POST /api/auth/login/ with CSRF header from cookie csrftoken); `processingGet/Post` against `/api/processing/...?includeLists=0`; waiters poll cards/tables (default 90 x 1s; record to reach terminal card up to 180 x 1s); `ensureProcessingQuiescent`: POST sync/catalog/stop, sync/incomplete/stop, disable both automations (weekly 03:00), wait until catalog-sync and incomplete-automation idle and create-overview (requests+queue+processing)==0; `ensureCreatedRequest`: reuses an existing created request else creates requests for up to 5 selectable catalog records and waits for real processing to finish (create-created / on-hold-failed / on-hold-duplicate); `ensureDuplicateRequest`: needs a naturally occurring duplicate else test is skipped.
- [E69] catalog runtime: UI count `catalog-records-count` equals server `pagination.totalCount` (also under search q); manual Start disables automation run; pause -> server status paused; resume button visible; automation aria-label "Resume automated catalog sync" — processing-pages-live-catalog-runtime.spec.js
- [E70] automation run shares ownership with manual (manual Start disabled); scheduled automation (daily at next minute) starts with `sync.triggerSource == "scheduler"`, runMode catalog_automation, status in syncing|pausing|paused — within 150s; manual Start disabled during it; cleanup stops sync and disables automation
- [E71] created lifecycle: delete a created request -> appears in on-hold-deleted (server) and UI counts match; "Create Again" removes it from deleted and it reappears in create-created or on-hold-failed after real reprocessing (up to 180s) — created-lifecycle spec
- [E72] duplicate resolution: "New" removes the request from duplicate and it re-enters create-requests|queue|processing|created or on-hold-failed — duplicate-resolution spec (SKIPPED when no live duplicate exists)
- [E73] incomplete runtime: incomplete automation runs separately from catalog (catalog Start stays enabled while incomplete runs); scheduled incomplete automation has triggerSource scheduler, runMode incomplete_automation
- Fragility: these tests depend on real source site content, timing (1s polling, minute boundaries), leftover DB state, and workers.

### 14zb — notes: frontend/e2e responsive layouts: responsive-layout/{index 3, layoutAssertions 227, apiMocks 334, processingMocks 270}, responsive-layout.spec.js (1), -navigation-and-library (283), -property-and-access (159), -manual-and-profile (118), -processing (143), -reader (81)


Breakpoints/layout contract revealed (CSS pixel viewport -> expected behaviour). Specs run serial, unauthenticated storage state with mocked session (is_superuser + capability processing:manage) except reader (live).

- [R1] 1440x900 desktop: primary nav `nav[aria-label="Primary"]` visible, `mobile-nav-trigger` hidden; Home `.book-grid` has 2 columns (!), library `.book-table` is a real table (thead shown, rows `table-row`, cells `table-cell`); /access users table desktop mode; users header toolbar single row; `.access-user-editor-primary-row` >1 grid columns; /catalog `.processing-table` desktop mode; profile editor `.profile-form-grid` has 2 columns; no horizontal overflow (scrollWidth <= innerWidth+2) — navigation-and-library spec
- [R2] 1024x768 tablet landscape: desktop nav, trigger hidden, `.brand-block`, `.topnav`, `.session-box` do not overlap
- [R3] 820x1180 and 768x1024: Primary nav hidden, hamburger `mobile-nav-trigger` visible; drawer `#app-mobile-nav` has links "My Books", group buttons "Book Properties" (expands links incl. "Books"), "Processing" (only if user has processing capability); at 768 the book grid is still 2 columns
- [R4] 390x844 phone: book grid 1 column on /home and /created-books; first book cover fills card width (art within 2px of inner card width, cover within 1px of art); no page overflow
- [R5] Phone drawer for user without processing links: no "Processing" button; panel height < viewport-120 and bottom gap >= 40px (collapses to content)
- [R6] Route change resets scroll to top (after scrolling Home to bottom, clicking "Users & Access" link lands at scrollY 0)
- [R7] Phone library toolbar (`.catalog-page-header--property-layout`): result count flush right/top; two export buttons ("CSV export", PDF) share a row filling `.catalog-search-actions-extra`; filter toggle gap 6px; filter+sort fill header width on one row, filter narrower than sort; search flush left/right; saved filter chips `.saved-filter-apply` (long names visible); table converts to card mode (thead display none, rows block, cells grid with data-label) — "cardified" tables via `td[data-label]`
- [R8] Phone property pages (/categories, /series, /writers): `.property-table` card mode; name cell (`td[data-label="Name"]`, "Series" for series) fills the row width (<=2px); writer tabs (Writers, Translators, Editors, Publishers links) keep `.property-table` with 7 `col` and 7 `th` while loading (skeleton) and never show previous tab rows (property-and-access spec); contributor API for tabs returns either array or {entries, pagination}
- [R9] Phone /access: `.access-user-editor-primary-row` 1 column; users header toolbar: title, search, count on one line (gaps >=6px mobile / >=8 desktop), filter & sort selects on second row (mobile) — selects have disabled first options "Filter" and "Sort" and no inline labels; users table shell scrolls vertically (overflow-y auto/scroll and scrollHeight>clientHeight); card mode
- [R10] Phone /manual-books: add button (`aria-label="Add manual book"`) right-aligned <=48px wide; "Export options" toggle reveals `.manual-books-download-row` with 3 export buttons (CSV, PDF, Excel) all inside the row and viewport; composer `.manual-book-form-grid` all 1 column; no overflow
- [R11] 320x568 profile editor: headings "Change Password"; `.profile-form-grid` and `.profile-password-grid` are 1 column; "Save Changes" reachable
- [R12] Phone /catalog processing: `.processing-card-grid` 1 column; records card header: count right-aligned & vertically centred on title row; filter toggle gap 6px and narrower than action button; action button (`catalog-records-create-btn`) below the filter and fills `.processing-card-head-actions`; automation card header controls on same row as title; processing table in card mode (cells grid; select cell inline-flex); card shell scrolls and PEEKS the next row (first row fully visible, second row starts visible but clipped) to hint scroll; /processing-incomplete-check (legacy route alias of Incomplete page, heading level 1 "Incomplete") has inline filter+count in header (title left of filter left of count same row) for records and completed cards
- [R13] Live reader (needs seeded stack): 844x390 landscape: book detail hero and reader contained, iframe visible, no overflow; 390x844: TOC toggle collapses sidebar and `.reader-wrapper` width >300px; reading settings panel `#reader-settings-panel` fully within reader/viewport bounds
- Mock payload conventions (apiMocks): session user {id,email,full_name,profile_image_url,is_active,is_staff,is_superuser,capabilities,totp_*}; books with fields incl. `latest_submission_at`; managed users {id,email,full_name,is_active,is_superuser,totp_required,totp_enabled,global_scopes,grant_count,can_resend_setup_email}; references {users,books,categories,writers,account_scopes,scoped_scopes}; profile {kindle_emails,kindle_sender_email,...}; writers/series/categories suggestion payload arrays of {name}; manual books mock includes compilers endpoint (/api/catalog/compilers/) and publishers.

## 3. Business rules revealed only by tests (not obvious from endpoints/models)

Access and auth
- Read-once is a single shared allowance across reader launch AND HTML preview download; READ_ONCE and READ_DURABLE are mutually exclusive (global scopes and per-target grants). Owners of a book (a submission of theirs links to it, i.e. UserBook) need no explicit grants for download/reader.
- Superadmin cannot create/delete scoped grants for themselves and cannot edit own account in Users & Access; scopes `admin:full_control` and `access:manage` are never offered in the reference lists.
- Password-reset: unknown email returns 404 "No user exist with this email." (enumeration is deliberate); invited users with pending setup are treated as unknown for reset; newest link invalidates older ones; links are single-use and expire after 6 h; reset while logged in is refused; TOTP-required accounts are logged in after setting a password and forced into authenticator setup; TOTP-required invite stays "resend setup email"-able until the authenticator is confirmed.
- Kindle: addresses must end @kindle.com (not free.kindle.com); invalid legacy addresses silently skipped at send time; delivery uses SMTP even when the primary mail backend is an HTTP API (Brevo); specific 502 messages for missing SMTP config and SMTP auth failures.
- Anonymous catalog access -> 403 (not 401).

Catalog / metadata
- Names are matched on normalised form (punctuation, hyphens, dots, brackets ignored; Bengali marks preserved) for search, filters, reuse of Contributor/Series/Category, and duplicate detection.
- Contributor roles: compiler == editor; same person as author AND translator/editor keeps only the non-author role; translator prose/bio is never a name; roles extracted from front matter (translator, editor, publisher, cover_artist, illustrator, edition, first_published, language, page_count).
- Catalog codes: fixed-length codes for category, writer and book; a book code encodes its category and writer codes.
- Manual (physical) books are a separate record_type excluded from the default book list; price is a string with 2 decimals, binding humanised ("Paper Back"), compilers merged into editors.
- Soft delete sets deleted_at and state soft_deleted; deleted books are ignored by duplicate detection and source-URL lookup, re-creation REUSES the deleted Book row.
- Heavy columns (content, raw payloads, toc) must never be loaded by list endpoints (query-level assertions).
- Duplicate classification: new_work / exact_duplicate / new_edition (publisher, edition or translator differs) / needs_review (missing authors); reuse only by source URL, never by title alone.

Ingestion
- Retry policy: 3 total attempts; failed intermediate attempts keep job QUEUED with "attempt N of 3"; final attempt FAILED; if the queue broker is down the job runs inline ("inline-fallback"), still max 3 attempts.
- Stale processing jobs (>= ~30-45 min in tests) are revoked and re-queued with attempt offset, except exhausted ones which fail. Recovery budget: USER first, then CURATION, AUTOMATION only if automation enabled, shared limit 100.
- Stale task guards: a task whose id no longer matches the state row must do nothing (stop/replace races); eager failures must not trigger inline fallback.
- Missing generated EPUB after export is a hard error that flags the book needs_review; assets move into MEDIA_ROOT/generated/<slug>/ with exactly html + cover + one epub.
- Public (no-login) submissions are allowed; they produce guest preview sessions with no bookmarks/reading state.
- Catalog curation automation: one scheduled run per period (daily/weekly/monthly with month-end clamp); runs create or re-process "stopped" entries.
- Curated document validation routes anything structurally suspicious (duplicate paths, unfetched pages, empty leaves, leaked site chrome) to REVIEW_REQUIRED and persists without assets.
- EPUB structure rules: spine cover->title->info->dedication->front->toc->content->back->nav (nav linear="no"); nav lists every readable page; printed toc content-only; no blank pages; empty dedication page omitted.

Processing (new pipeline)
- Catalog runtime is ONE shared state machine with two phases (sync, request creation), each with status/owner/checkpoint; manual vs automation ownership rules are enumerated in two 10-row matrices; pause is cooperative (after current page/batch); resume of incomplete sync restarts from the beginning; manual start never destroys the paused phase-2 checkpoint.
- GET endpoints are pure (never advance work, never run schedules); state recovery is only done by maintenance/runtime tick; stale-processing threshold differs between backend tests (25-30 min requeue) and UI mock (20 min -> failed).
- Request lifecycle initial->queued->processing->created|failed|duplicate; paused/deleted via actions; duplicate resolution actions: confirm_duplicate (locks record until original terminal), new, new_edition (BookGroup), create_again.
- DB trigger keeps BookRecord.book_creation_state equal to its request state (cannot be overridden directly).
- UI domain versions: each mutation returns only changed domains; SSE emits versions; clients refetch only changed card tables; offscreen cards lazy-load.
- Processing task dispatch uses the "processing" queue without probing workers, with fallback to inline when the broker fails, and stale dispatch markers (>~2-5 min) are re-dispatched.
- Remote-page injection (`remotePages`) is a test-only override gated by a setting (disabled in production).

Frontend behaviours
- Toast grouping with quiet window (120 s hold), per-type sounds, global mute stored locally, sounds independent of visual type; created-notification batching every 3 minutes.
- Preview-lock: only one HTML preview tab at a time (localStorage lock key).
- Forms: tag inputs commit on blur; Done/close auto-saves a non-empty composer; email validation messages ("Enter a valid email address.", "Email looks good.").
- Responsive: <= 820 px mobile drawer; tables turn into labelled cards on phones; no horizontal overflow at 320-1440 px.

## 4. Skipped, flaky, live-dependent or heavily mocked tests

- Live-site dependent: backend/test_spec_books.py (13 parametrised books, marker `live`, network to the source site; excluded from normal runs); scripts/regression_curate_300.sh (300-book harness); verify_e2e_reprocessing.py (real source URLs, polls 300 s, not a pytest test); frontend e2e processing-pages-live* (4 specs, run only with PLAYWRIGHT_RUN_LIVE_PROCESSING=1 and full worker stack; depend on real source data, scheduler minute boundaries, leftover state).
- Conditionally skipped: processing-pages-live-duplicate-resolution (skips when no natural duplicate exists); test_book_pdf_and_ticket_exports_return_pdf (importorskip reportlab).
- Real infrastructure, slow and timing-based: backend/engine/* use real Redis + Postgres, many time.sleep(0.2-0.5), stale-detection waits ~20 s each; dispatch_integration needs transaction=True.
- Fixed waits / flake-prone: home-filter.spec (waitForTimeout 2000), page.waitForTimeout in several processing specs (150-4500 ms), pipeline polling loops (20 x 0.25 s) in processing backend tests, library-page-live, book-detail live tests that mutate and restore data (title edit with finally block).
- Mock-heavy / test the copy not the app: frontend unit bookExportPrice, manualBooksExcelExport, manualBooksModule (mostly), physicalBooksEdit, tagInputKeyboard inline verbatim copies of production code because Node cannot resolve extension-less Vite imports; embeddedReader*/homePageToolbar/localStackConfig/localWorkerConfig assert on source TEXT (regex over CSS/JSX/compose files).
- Heavy monkeypatching: kindle SMTP tests (patch get_connection/EmailMessage.send), processing source tests, curation tests (patch Celery apply_async, services functions), catalog sync parallel (9 patched deps), whole Playwright processing harness is a JS re-implementation of the backend state machine (~1,500 lines).
- Facade pattern: several test_*.py files exec() sibling case files into their own globals to stay under the 300-line cap (test_access_01, test_auth_01, test_catalog_management_02, test_ingestion_03/06/10/20/21, test_processing_api (24 case files)); the test_processing_api cases share one namespace via exec so order matters.
- Empty/placeholder: access-page-mocked.spec.js, auth-public-pages.spec.js, processing-pages.spec.js, processing-pages-live.spec.js, responsive-layout.spec.js (1 comment line each); backend __init__.py files.
- No explicit pytest.skip/xfail besides the above; no frontend unit tests for React components (no DOM runner).

## 5. Policy checks (tests/scripts) and what they enforce

- check-file-size-policy.py: every first-party file (.css .html .js .jsx .py .sh .ts .tsx .yaml .yml tracked by git, not in dist/node_modules/public/storage/vendor/.git/docs/logs, not package-lock.json) must be <= 300 physical lines; exemptions listed one-per-line in tests/policy/*.txt (46 grandfathered large files in existing_large_files.txt incl. 3 big test files; existing_migrations.txt lists 44 legacy migrations as a historical record). Output sorted by size descending.
- check-architecture-policy.py: (1) no numbered split modules (`part-1`, `part_2`, `_parts/`); (2) no generated "part_*.py" / "part_*.sh" loaders (the facade exec pattern is tolerated because it uses a named cases dir); (3) frontend `apiFetch` may only be used inside `src/api/` or `src/features/<name>/api.(js|jsx|ts|tsx)`; (4) backend transport modules (`apps/**/views/`, `views.py`, `serializers/`) must not import redis, requests, kombu, bs4, boto3, celery, config.celery.
- Both run first in tests/scripts/verify.sh; verify.sh then: bring up stack, STOP worker/processing-worker/beat, seed e2e data, backend pytest in container, frontend unit tests, frontend production build, Playwright `--workers=1`.
- tools/test_env_tools.py: env-file parser/exporter quoting rules (shlex.quote; `$` literal; single-quote escape).

## 6. Seed data used (shape and counts)

- E2E seed (`manage.py seed_e2e_data`, implementation not in tests; shape from support/seedData.js): 1 access user (access-manager@e2e.local, "E2E Access Manager"); 6 named books (E2E Home Library Book, E2E Search Companion Book, E2E Detail Book with source URL https://www.example.com/books/e2e-detail-book/ + a bookmark "Seeded Bookmark" + a TOC with "Chapter 1" + a real EPUB, E2E Preview Book, E2E Access Grant Book, E2E Incomplete Catalog Book); filter facets: category "E2E Fiction", series "E2E Starter Series", writer "E2E Writer" (all linked); 19 ingestion submissions in varied states/origins (alpha/beta, user pending/processing/stopped/deleted/failed, automation pending/ready/processing/queued/stopped/deleted, curation ready/processing/queued/stopped/deleted, duplicate review); 2 source catalog entries ("000 E2E Alpha Catalog Book", "001 E2E Beta Catalog Book"); processing log entries ("Seeded failed job log entry.", scheduled runs "7 create" active / "2 create" failed). Prefix "E2E " / domain @e2e.local; super admin from SUPER_ADMIN_EMAIL / SUPER_ADMIN_PASSWORD env (defaults admin@example.com / changeme).
- Backend pytest fixtures are per-test factories (no shared seed): users (strong-password-123 / -456), books with Bengali titles, GeneratedAsset files in tmp_path, BookSubmission/ProcessingJob rows, `build_simple_epub()` helper (EPUB with META-INF/container.xml, OEBPS/content.opf, OEBPS/text/chapter-1.xhtml containing "Seeded EPUB chapter one for reader coverage.").
- Volume fixtures: 76 users (pagination 60), 75/85/95 rows for infinite-scroll tests, 24 books for responsive tests.
- All URLs in tests are anonymised (example.com / example.test); the real source site name only appears in verify_e2e_reprocessing.py ("ebanglalibrary.com").

## 7. Unread files and why

None. All 220 files (34,416 lines) were read. Caveats: (a) views of Python tests collapsed blank lines, import statements and a few repetitive boilerplate lines (e.g. `password="strong-password-123",`, `book=book,`) by tooling; (b) processingApiMock.js is a single minified line, read in full; (c) no file contained secrets; `.env` files are not in tests (liveEnv.js only references local/env/.env by path). Implementations of seed_e2e_data, build_simple_epub and the app modules are outside this scope and were not read.

## 8. Cross-cutting inconsistencies surfaced by the tests (for planning)

- Stale-processing handling: backend maintenance re-queues after >=25 min; UI mock marks failed after 20 min ("Processing exceeded 20 minutes without completing.").
- Catalog automation request creation scope: backend test = records not created; frontend mock = no history OR latest failed/deleted; plan doc story = "no prior request history".
- Two parallel ingestion pipelines coexist: legacy submissions/jobs (apps.ingestion) and the new processing app (BookRecord/BookCreationRequest) that explicitly must not use the legacy flow; a Redis job engine (engine/*) is a third orchestration layer. A rebuild should pick one.
- Branding: "RSalehin24 Library" (emails, TOTP issuer) vs "Bangla Library" (UI copy).
- Kindle validation wording differs backend vs UI; "has expired" vs "has been expired" headings.
- Summary payload keys drift between mocks (incomplete.resolved vs completed; notifications keys).
- Home grid is 2 columns at 1440 px (not responsive growth) — confirm intent.
