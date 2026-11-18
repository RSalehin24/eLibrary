# 14a — notes: scripts, policy, root, common, legacy pipeline, spec books

Status: DRAFT (research evidence; read-only record)

IDs: S=scripts/policy, C=common, LP=legacy pipeline, SB=spec books.

## Scripts and policy
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

## Saved filters (test_common.py)
- [C1] given logged-in user, when POST /api/saved-filters/ {target:"catalog", name:"Bangla Mysteries", params:{q:"রহস্য", category:"উপন্যাস"}} then 201; GET /api/saved-filters/?target=catalog 200 list with name; SavedFilter(owner,target) count 1; DELETE /api/saved-filters/<id>/ -> 204 — test_common.py:10-33

## Legacy pipeline / exports (test_legacy_pipeline.py)
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

## Spec books (live, marked `live`) test_spec_books.py
- 13 reference books (URLs now anonymised example.com), per-book checks: bhumika (no cross-book links), shankha_ghosh (toc not empty + parent entries have titles), shopner_brishtimahal (has dedication, dedication not duplicated in front_sections), himu_baba (toc not empty, <=50 content items), hamlet (English book: book_info must not have Bengali labels শিরোনাম: লেখক: অনুবাদক: প্রকাশক: সম্পাদক:), 2001/sherlock/sati/lohit_kiran/hat_chuye/durga_rahasya (toc non-empty and book_info non-empty — "Book info page is empty — must always have content"), sidney_sheldon (toc), ba12_satyajit (toc + parents) — :26-257
- [SB-rules] cross-book link rule: any TOC/content_items URL containing "/books/" but not "/lessons/" is a violation; parent TOC entries with children must have non-empty title; toc empty only OK if main_content has plain text; dedication overlap heuristic >5 common words and >50% overlap flagged; front section containing "উৎসর্গ" in title/text flagged. API: `curate_book_document(url)` -> {"document":..., "projection":...} projection keys: toc, content_items, main_content, dedication, front_sections[{title,html}], book_info.
