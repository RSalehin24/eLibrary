Status: DRAFT

# D1. Ingestion: acquisition (scraper), manifest, curation, EPUB and HTML output

Sources: report 01 (`features/01-ingestion-acquisition-curation.md`, cited R1:<id>) and report 02 (`features/02-ingestion-manifest-epub-html.md`, cited R2:<id>). Code root: `archive/app/backend/apps/ingestion/pipeline` (abbrev `P/`). Verification marks: VERIFIED = I read the cited line in code; UNVERIFIED = taken from the report only. Report 01 section numbers for bugs are cited as R1:B#; report 02 bugs as R2:§6. Behaviours implemented in modules neither report read (`services/normalization`, `resolution_support_*`, `apps.common.text`, submissions services) are only known from call sites and are flagged.

## 1. Purpose and scope

Purpose: turn one public book page of a single source website (WordPress + LearnDash course site; a "book" is a LearnDash course, chapters are lessons, sub-chapters are topics) into (a) a structured, validated, versioned "curated document" persisted in the catalogue, and (b) a downloadable EPUB (and a single-file HTML book) with a fixed page order, Bengali/English labels, generated cover and a nested navigation.

In scope for this analysis:
- Acquisition: URL rules, HTTP session/retries, optional logged-in cookie, landing-page metadata, TOC discovery (paginated, nested, sectioned), per-chapter content fetching, cover download, limits.
- Manifest: a "source manifest" (pages log, projection, entities, sections, structure classification, completeness gate) built from the crawl (R2) and a second, older recursive scraper path (R1).
- Curation: extractors (entities/evidence/sections), validation (statuses), persistence (versioned CuratedBookDocument and book upsert).
- Output: EPUB builder, page templates, labels, generated cover, HTML book, EPUB structure auditor.

Out of scope here (owned by other analyses, only touched at call sites): duplicate detection and BookGroup resolution (spec §11), submission workflow/jobs, front-matter normalisation internals (`services/normalization`), book-info key ordering, role/entity keyword lists, send-to-Kindle, reader.

Two parallel acquisition implementations exist in the legacy code and a rebuild must pick one design:
1. `scraper.py` + `scraper_modules/*` (R1): recursive crawl, `exec`-glued modules, produces the "legacy payload".
2. `book_manifest.py` (R2): manifest-first crawl with AJAX pager, REST fallback, mark-complete unlock, resume cache, completeness gate; this is the current entry (`build_manifest_source_pages`, called by R1:P1). `build_manifest_from_legacy_payload` (R2:E04 / R1:P7) bridges old payloads.

## 2. Features and behaviours

Stable IDs D1-F#. Source IDs in brackets.

### 2.1 URL and configuration
- D1-F1 Source URL allow-list and canonicalisation: only http/https; host must equal the configured source host (or its www twin, plus fallback hosts); book URLs must be under `/books/`; forced https; host rewritten to the configured host; exactly one trailing slash; query/fragment dropped. Violations raise errors. A second, slightly different normaliser (content URL) returns "" instead of raising and only slashes `/books/` paths. [R1:C2,C3,C4,C5; R2:M14]
- D1-F2 Book URL list from env (`BOOK_URLS_JSON` or `BOOK_URL`/`BOOK_NAME`), evaluated at import. [R1:C1, B21]
- D1-F3 Content limits per run: max_nodes (320 default in R1 scraper), max_depth 6, max_lesson_pages 20, max_content_chars 120000, plus `max_topic_pages`, `disable_recursive`, `last_chapter_title` (R2). R2 treats None/0/invalid as "uncapped". [R1:L1-L4; R2:M01,M02]

### 2.2 HTTP acquisition
- D1-F4 HTTP session with retry: R1 urllib3 Retry (3, backoff 1, statuses 429/5xx, GET/HEAD/OPTIONS) plus a manual loop (SSL error wait 5s*n, other errors 3s*n), timeout 30 s; non-200 returns None. R2: up to 4 attempts, transient {429,500,502,503,504} backoff 2.0*attempt, timeout 60 s, a page log entry per fetch, URL cache, 0.5 s delay after each success. [R1:H1,H2,H3,H7; R2:M15,M16]
- D1-F5 Browser impersonation header (Chrome 144 User-Agent), safe Referer encoding for non-Latin slugs. [R1:H4; R2:M17]
- D1-F6 Optional authenticated session from a saved cookie file (`wordpress_logged_in_*`), because Cloudflare blocks automated login; R2's fetch context calls `login_source_session` on construction, giving access to logged-in-only content. [R1:H5; R2:M15]
- D1-F7 Host fallback on fetch (`get_with_host_fallback`, external, behaviour unknown). [R1:§5; R2:M16]

### 2.3 Landing-page metadata
- D1-F8 Title/author from `h1.entry-title` or `<title>` split ("Book Title" sentinel if absent); author precedence = meta terms author over title-split author. [R1:M1,M3; R2:M07]
- D1-F9 Entry-term metadata (`entry-terms-authors|series|ld_course_category`): author, series, book type, comma-joined and deduped. [R1:M2; R2:M08,M09]
- D1-F10 Cover discovery and download: figure selectors, attribute order (data-src, data-lazy-src, src, srcset...), extension from URL/content-type (webp/png/jpg), saved as `book_cover.<ext>` in a per-title output folder; failure silently yields no cover (generated cover used later). [R1:H6,B10; R2:M10,M11,M12]
- D1-F11 Entry-content extraction: priority selectors; R2 picks the candidate with the longest text (avoids the "Bookmark" tab); buttons removed; redundant headers removed. [R1:M6; R2:M13]
- D1-F12 Digit normalisation: ASCII digits in titles are converted to Bengali digits everywhere (including English books). [R1:M7; R2:M05]
- D1-F13 Per-book output folder `<RUNTIME_STORAGE_DIR>/media/scraped-books/<sanitised title>` holding cover, generated cover, EPUB, HTML. Sanitiser strips illegal characters and truncates to 255 UTF-8 bytes. [R1:M4,M5]

### 2.4 TOC discovery (LearnDash)
- D1-F14 Paginated lesson list: total pages from `.ld-pagination[data-pager-results]`; pages 2..N via the `ld30_ajax_pager` AJAX endpoint with nonce + shortcode_instance, falling back to `?ld-courseinfo-lesson-page=N`. R2 detects AJAX rejection as `toc_incomplete`. [R1:D1,D5; R2:T01,T09,T11]
- D1-F15 Lesson nodes, topic nodes (inline in lesson item, with topic pagination via `?ld-topic-page=<lessonId>-<n>`), embedded lesson-page TOC for "container lessons" (extra fetch), section headings (`ld-item-list-section-heading`) producing nested `section` nodes, and a Gutenberg/tab fallback that takes `/lessons/` links. [R1:D2-D4; R2:T02-T08]
- D1-F16 TOC merge/dedup across pages by (url,title), merging repeated section titles. [R2:T10]
- D1-F17 TOC meta + path assignment: every node gets a normalised title, type, `has_content` (bool or None), `path` of ancestor titles, `source_url`, `post_id`. [R2:T11,T13]
- D1-F18 Duplicate-path disambiguation: distinct source URLs get " (n)" suffix (Bengali digits), otherwise keep the longest text and drop the rest. [R2:T15]
- D1-F19 Inline TOC detection inside a single page (heading such as সূচিপত্র/contents followed by lists or linked paragraphs) and body split by headings; used when the book has no LearnDash lessons. [R1:S1-S10, K3]

### 2.5 Content fetching
- D1-F20 Per-leaf content fetch with limits, resume cache keyed by URL (`page_cache`), `gc.collect()` every 20 nodes; only leaf nodes are fetched. [R2:C01,C06,T14]
- D1-F21 Content fallback via WP REST API `wp-json/ldlms/v2/sfwd-lessons|sfwd-topic/<id>` when the page body is empty. [R2:C02]
- D1-F22 Mark-complete unlock: submits LearnDash `sfwd_mark_complete` for locked/sequential lessons (and for lessons with content not yet completed) so the next lesson unlocks. Mutates the logged-in source account's progress. [R2:C03,C04]
- D1-F23 Empty-source placeholder: a page fetched OK but with no text becomes an item with `has_content=None` and counts toward an empty-chapter gate; unreachable pages get `has_content=False` and are skipped. [R2:C05]
- D1-F24 Recursive node crawl (R1 scraper): cycle detection, depth/node caps, cache, inline TOC fallback, flatten to content items. [R1:K1-K5]
- D1-F25 Redundant-header removal and text-similarity matching used to drop chapter titles repeated as first heading/bold paragraph and to match TOC entries to inline content. [R1:R1-R6,T1-T4]

### 2.6 Front/back matter, book info, dedication
- D1-F26 Split landing content into book_info (key:value lines), dedication, residual; leading front sections, trailing back sections, residual classification, boundary sections mined from first/last chapters, title-page promotion into book info, pure-title-duplicate drop, inline-TOC section drop, front section equal to top-level TOC drop, dedupe against references. [R2:F01-F16; R1:F1-F12, B-B] (internals in `services/normalization`, not read)
- D1-F27 Language detection (bn/en) from title, then author/book_info; drives labels. EPUB builder and HTML/manifest call it with different inputs. [R2:F11,P01,H03]
- D1-F28 Fallback book-info when none was found (bn/en labelled lines). [R2:F12]

### 2.7 Manifest, classification, completeness
- D1-F29 Manifest with schema_version "2026-05-03.1": canonical/source url, book, metadata, source_structure, projection, entities, evidence, sections, assets, pages log, toc_source tree. [R2:E01-E05, C07]
- D1-F30 Structure classification: `single_page_heading_split`, `single_page_flow_no_toc`, `no_public_body`, `flat_lessons`, `lesson_topic_nested`, `mixed_lessons_and_topics`, prefix `sectioned_`; curated structure types: nested_toc, flat_toc, no_toc_heading_split, single_flow_no_toc, incomplete. [R2:T16; R1:E8]
- D1-F31 Completeness rule: expected = topics (+ topic-less lessons if no topics); allowed missing = max(1, n//3) when n<10 else max(1, int(5%)); plus "last chapter title" guard to catch truncated crawls. [R2:T17,T18,T19]
- D1-F32 Legacy payload to manifest bridge and manifest-to-projection re-hydration. [R2:E04,E05]

### 2.8 Curation
- D1-F33 Source snapshot (pages, fetched_urls, manifest, raw payload). [R1:P1,P2]
- D1-F34 Curated document build: entities (WORK, PERSON, ORGANIZATION, SERIES, CATEGORY, PUBLICATION_EVENT, ASSET) with confidence and evidence, sections (TITLE_PAGE, BOOK_INFO, DEDICATION, FRONT_MATTER, GENERATED_TOC, BODY, BACK_MATTER) with stable ids and sort order, assets (cover, content images), 13-key projection. [R1:P3-P9,E1-E8]
- D1-F35 Validation statuses (VALIDATED, REVIEW_REQUIRED, INVALID) with hard errors (missing title, missing canonical URL, missing body), structural errors (missing TOC, empty or duplicate content paths, dead TOC leaves), source-chrome detection, fetch errors and warnings. [R1:V1-V10]
- D1-F36 Persistence: versioned `CuratedBookDocument` per source_url (retry on version race), entity/section/evidence rows, book upsert by title/source-url match including revival of soft-deleted books, `BookSource`, relations, `MetadataVersion` snapshot, BookGroup hint from a prior duplicate resolution, `empty_chapters_count`. Lifecycle: VALIDATED goes to READY + review PENDING, anything else NEEDS_REVIEW + NEEDS_REVIEW. [R1:W1-W12]

### 2.9 Output
- D1-F37 EPUB page order and structure: cover, title, info (always), dedication (optional), front sections, toc, lesson pages, main content (only for chapter-less books), back sections, nav (last, non-linear). [R2:B02-B14,P01-P22]
- D1-F38 Generated cover PNG (1200x1800, gradient + gold accents, bundled Noto Sans Bengali) with title/series/author sanitisation; HTML-cover fallback. [R2:P03-P06]
- D1-F39 Hierarchical navigation (nested toc, container entries pointing to first child, back sections listed, front matter not listed), nav.xhtml plus NCX. [R2:P13-P17]
- D1-F40 Labels table and book-info labels, bn/en, local digits for bn. [R2:P23,P24]
- D1-F41 Single-page inference for books without TOC: split by headings into chapters, sub-chapter promotion, intro as front section; mis-classification rescue (promote >=3 front sections when <=1 item). [R2:B09,B10]
- D1-F42 Fail-fast gate: refuse EPUB when more than 1/3 of chapters are empty placeholders. [R2:B13]
- D1-F43 Safe EPUB filename (illegal chars removed, 200-byte stem truncation on code-point boundary). [R2:P20]
- D1-F44 HTML book export (`book.html`): single file, cover as base64, same preprocessing, single-tab preview lock script, fixed CSS. [R2:H01-H11]
- D1-F45 EPUB structure audit (zip/OPF/spine/nav consistency rules) used by a 300-book regression harness. [R2:A01-A10]

## 3. Actions by actor

### Operator
- Submits a book URL (and optionally content limits and `last_chapter_title`) for import; the URL is canonicalised and rejected if off-site or not under `/books/`. [D1-F1, F3]
- Provides/refreshes the source-site login cookie file out of band (developer-run "save auth" script on the host, since automated login is blocked). [D1-F6]
- Reviews curated documents in status REVIEW_REQUIRED/INVALID (book state NEEDS_REVIEW); VALIDATED books become READY with review PENDING. [D1-F36]
- Resolves duplicates (new edition) which set `target_book_group_id` read at persistence. [D1-F36] (resolution UI out of scope)
- Downloads or triggers generation of EPUB (and HTML) for a book. [D1-F37, F44]
- Optionally runs the audit harness over curated sample books. [D1-F45]

### System
- Canonicalise URL; fetch landing page; extract metadata and cover; discover TOC (all pages, topics, sections); fetch each leaf (with retries, REST fallback, mark-complete unlock, placeholders); classify; complete front/back/book-info/dedication; apply completeness gate. [D1-F1..F31]
- Build snapshot, curated document, validate, persist new version, upsert book, record sources and metadata version. [D1-F33..F36]
- Build EPUB: derive sections (again), pick/generate cover, render pages with Jinja2, build nav/NCX, gate on empty chapters, write file. [D1-F37..F43]
- Resume a partially fetched import from the page cache so already fetched leaves are not re-requested. [D1-F20]

## 4. Business rules and invariants

Acquisition and identity
- BR1 Only the configured source host (and www twin and fallback hosts) may be fetched; book roots must be `/books/<slug>/`. Cover URL host is NOT restricted in R1 (SSRF-ish; R1:B10). Chapter links on the allowed host but outside `/books/` are fetched in R1 (R1:§5).
- BR2 Only `/lessons/` links are chapters in the fallback path (spec §8); the main LearnDash path takes any `ld-item-name` anchor. [R2 §5.11]
- BR3 Politeness: at least 0.5 s after each successful fetch (R2); R1 sleeps 1 s only between lesson-list pages. Topic-page fetches in R1 are unthrottled.
- BR4 One book is identified by normalised source URL; a CuratedBookDocument version is max(version for source_url)+1 and unique per source_url+version. [R1:W2,W3]
- BR5 A leaf with a visible empty body is "empty source" (placeholder), not "failed"; placeholder counts differ between classification and EPUB gate (see §8).

Quality gates
- BR6 Document status: any error means INVALID if one of three hard errors (title, canonical URL, body) else REVIEW_REQUIRED; none means VALIDATED. `is_valid = not errors`. [R1:V1-V9]
- BR7 Source chrome (login/related books/leave a reply etc.) found in a body section is an error. Titles "Book Title" and "Page not found" are rejected as non-book fallbacks (Cloudflare/404 pages returned as 200 would otherwise pass). [R1:V1,V6,B23]
- BR8 Completeness: allowed missing = max(1, n//3) for n<10, else max(1, int(0.05 n)); last-chapter title must be present when supplied. EPUB build separately rejects >1/3 empty placeholders. [R2:T17,T18,B13]
- BR9 Content truncation at max_content_chars is silent and may break HTML. [R1:L2,B13; R2:M03]

Content/structure
- BR10 Only leaf nodes get fetched content; parents with children never keep their own text. [R2:T14] (data loss for container lessons)
- BR11 Duplicate paths are disambiguated with Bengali numerals or resolved by longest text. [R2:T15]
- BR12 Digits in titles are always Bengali digits. [R1:M7; R2:M05]
- BR13 Front matter never appears in the printed TOC; the printed TOC lists chapters plus back sections. [R2:P16]
- BR14 Info page is always present; cover always present (generated if missing); dedication only when non-empty; nav is last and non-linear. [R2:B02-B05]
- BR15 Spine order is non-decreasing in the slot ranking cover<title<info<dedication<front<toc<content<back<nav; nav must reference every spine page exactly; toc page links only to content/back pages. [R2:A04,A08,A09]
- BR16 Unnamed front sections: no heading, nav title "অন্যান্য"/"Others" plus index; named sections with only key:value lines are dropped. [R2:P11]
- BR17 Language labels: bn digits only for bn. [R2:P23]
- BR18 Book lifecycle after persistence: VALIDATED to READY/PENDING, others to NEEDS_REVIEW; soft-deleted book with the same title is revived automatically; existing book titles are not refreshed. [R1:W5,W6]
- BR19 Confidences are fixed constants (1.0/0.95/0.93/0.92/0.9/0.88/0.84); the <0.75 warning is unreachable. [R1:E-series, B4]

## 5. Data handled and owned

Entities (legacy names; rebuild will redesign):
- Book (lifecycle state, review state, raw metadata, raw scrape payload, main content/book info/dedication HTML, toc JSON, content_items JSON, empty_chapters_count, cover_source_url, deleted_at). Full content lives in Book columns and CuratedSection rows. [R1:W1,W5,W6]
- BookSource (normalised_source_url, source_url, source_title, raw_metadata) upserted per book. [R1:W8]
- BookGroup (edition grouping), attached via job submission hint. [R1:W10]
- CuratedBookDocument (book, source_job, source_url, canonical_url, version, status, structure_type, title, validation_summary, slimmed source_snapshot, document with model_version). CuratedEntity, CuratedSection (full html), CuratedEvidence (links entity; section FK never set). [R1:W3]
- MetadataVersion (snapshot=document, source "curated"). [R1:W11]
- Page cache (resumable items by URL) and page log (url, kind, title, status, status_code, error, index). [R2:C06, §3]
- Disk artifacts per book: `book_cover.*`, `_generated_cover.png`, `<title>.epub`, `book.html`. [R1:M4; R2:P20,P22,H02]

Key structures (field level, from reports)
- Projection (13 keys + source_url): book_title, author, series, book_type, cover, cover_source_url, main_content, book_info, dedication, front_sections, back_sections, toc, content_items, output_folder. [R2:E01]
- TOC node: title, type lesson|topic|section, has_content bool|None, path[], source_url, post_id, children. Content item: title, content html, type, parent, path[], source_url, has_content (None = empty placeholder). Section: title, html, optional nav_title. [R2 §3]
- Entity: value, entity_type, role, source_url, source_location, evidence_text, confidence, normalized_value, payload. Section: section_id (`prefix-NNNN-sha1[:10]`), type, title, path, source_url, source_location, html, confidence, sort_order, payload. [R1:E1,§3]
- Manifest: see D1-F29. Validation summary: is_valid, status, errors, warnings, body_section_count, entity_count, section_count.

Lifecycles
- Import attempt: fetched pages -> manifest -> snapshot -> curated document (DRAFT -> VALIDATED|REVIEW_REQUIRED|INVALID) -> new version row. Versions are append-only per source URL; the book row is updated in place.
- Book: READY/PENDING review or NEEDS_REVIEW; soft delete and revival by title.
- Storage slimming: heavy projection keys are replaced by `content_summary` in stored documents and snapshots to save space. [R1:W1]

Data to treat as third-party copyrighted: all scraped chapter content and cover images (rebuild must never commit them; see project rules).

## 6. Interfaces

External site (single host) — all GET unless noted:
- Book landing `/books/<slug>/`; lesson list `?ld-courseinfo-lesson-page=N`; topic pages `?ld-topic-page=<lessonId>-<n>`; each lesson/topic page; cover image URL (any host in R1).
- POST `wp-admin/admin-ajax.php` with `action=ld30_ajax_pager` (needs nonce from page, shortcode_instance JSON, `X-Requested-With`). [R2:T09]
- POST `wp-admin/admin-ajax.php` `action=sfwd_mark_complete` (fallback direct form POST). [R2:C04]
- GET `wp-json/ldlms/v2/sfwd-lessons|sfwd-topic/<id>` (timeout 30). [R2:C02]
- Cookies: `wordpress_logged_in_*` from a JSON auth-state file (`SOURCE_SITE_AUTH_STATE_PATH`, in backend storage). Only header: browser User-Agent (+Referer, X-Requested-With on AJAX).
- Source markup dependencies (fragile): `entry-meta`, `entry-terms-*`, `figure.entry-image-link.entry-image-single`, `.ld-tab-content`, `.entry-content`, `ld-item-lesson-item`, `ld-item-name`, `ld-item-title`, `ld-table-list-item(-preview)`, `ld-topic-title`, `ld-pagination[data-pager-results|data-pager-nonce]`, `data-ld-expand-id`, `ld-item-list-section-heading`, `.ld-course-navigation .ld-lesson-items`, `ld-is-current-lesson`, `sfwd_mark_complete` form, English "N Topics" badge text. [R1:B24; R2:T-series]

Configuration: env `BOOK_URLS_JSON`, `BOOK_URL`, `BOOK_NAME`; settings `SOURCE_SITE_HOST`, `SOURCE_SITE_FALLBACK_HOSTS`, `SOURCE_SITE_AUTH_STATE_PATH`, `RUNTIME_STORAGE_DIR`; content_limits dict.

Internal interfaces (function level; become service APIs in a rebuild):
- `build_manifest_source_pages(url, limits, page_cache)` -> manifest + pages. `curate_book_document` / `curate_scraped_book_data` -> {document, source_snapshot, projection, status, validation}. `persist_curated_book_with_hooks(result, book, job)` -> (book, curated document). `create_epub(book_data)` / `create_html_book(...)`. `audit_epub_structure(path)` -> `EpubAuditResult{ok, errors, spine_files, spine_slots, nav_hrefs, toc_hrefs}`.

Files produced:
- EPUB parts: `cover_page.xhtml`, `title.xhtml`, `info.xhtml`, `dedication.xhtml`, `front_section_N.xhtml`, `toc.xhtml`, `lesson_N.xhtml`, `main_content.xhtml`, `back_section_N.xhtml`, `nav.xhtml`, `toc.ncx`, cover image, `_generated_cover.png`. [R2:P22]
- Templates (9): cover_page, dedication, generated_cover, info_page, lesson, main_content, title_page, toc (unused), toc_hierarchical. Bundled fonts NotoSansBengali Regular/Bold (cover only; EPUB text references Kalpurush/SolaimanLipi system fonts and embeds none). EPUB metadata: title, author, language only. [R2:§6]
- `book.html` single file. Stylesheet is one fixed CSS string.

Libraries involved (legacy): requests/urllib3, BeautifulSoup, ebooklib, Jinja2, Pillow, Django ORM. Dependency decisions for the rebuild belong in the dependency policy.

## 7. States and processes

### 7.1 End-to-end import (R2 manifest path)
1. Normalise URL (reject off-site). 2. Normalise limits. 3. Create fetch context (session, optional login cookies, page log, cache). 4. Fetch landing; on failure return an empty manifest carrying the page log (status failed). 5. Extract title/author/terms; create output folder; download cover; extract entry content. 6. Build TOC (unless `disable_recursive`): page 1, pages 2..N via AJAX else query GET, topic pages, embedded lesson TOC probes, sections, merge/dedupe. 7. Assign paths. 8. Fetch leaf content (only if a TOC exists): page, REST fallback, mark-complete unlock, placeholder; save each item to resume cache; honour max_nodes. 9. Normalise front/back/book info/dedication. 10. Disambiguate duplicate paths. 11. Classify structure + completeness. 12. Projection, manifest. 13. Snapshot -> curated document -> validation -> persistence (version N+1) -> book upsert -> READY or NEEDS_REVIEW. 14. EPUB/HTML generation is a separate step on demand with its own gates.

### 7.2 Fetch state machine (per URL)
- fetched(200) -> parsed.
- transient (429/5xx) or RequestException -> retry with linear backoff up to 4 attempts -> then failed (cached as None even if cache=False; VERIFIED-by-report only).
- non-transient non-200 -> failed immediately (status code visible in R2 page log; R1 returns None with only a print).
- 200 but challenge/404 page: parsed as a book; caught only by sentinel-title validation.

### 7.3 Leaf content states
- has_content True (text), None (fetched but empty source; kept as placeholder), False (unreachable; skipped). Locked page: empty body + mark-complete form -> submit, wait 1 s, refetch; else placeholder.

### 7.4 Curated document status
DRAFT -> VALIDATED | REVIEW_REQUIRED | INVALID (computed once). Book: READY (+review PENDING) or NEEDS_REVIEW.

### 7.5 EPUB build
Derive sections (unless canonical payload) -> cover -> pages -> toc (lazy rendered) -> nav build -> fail-fast gates (`EpubContentMissingError` if no content/main/front/back; ValueError if >1/3 empty) -> save file (print). The audit is a separate offline check.

### 7.6 Failure modes and retries
- Partial TOC when AJAX pager is rejected: flagged `toc_incomplete`, fed into completeness. Silent omission when max_nodes/max_depth exceeded (R1:B14). Truncated content silent. Version-race IntegrityError retried up to 5 times; then raised. Persistence not wrapped in one transaction -> partial state (book saved, document rows missing) (R1:B18). Resume: page cache avoids re-fetching leaves after a crash (R2:C06).
- Rough request cost: up to ~5 requests per chapter (container probe, content, REST, mark-complete, refetch) at 0.5 s spacing.

## 8. Issues

Legend: Sev = H/M/L; V = VERIFIED (I read the code), U = UNVERIFIED (from report).

| # | Issue | Sev | Verif |
|---|---|---|---|
| I1 | Scraper POSTs LearnDash mark-complete for every lesson read, altering the logged-in source account's progress; requires credentials; undeclared side effect on a third-party site. Calls at book_manifest.py:1426 (empty content) and :1453 (content present, not complete). | H | V (book_manifest.py:1416-1453) |
| I2 | Bengali literals in `extract_core_title` are spelled without vowel signs/virama (`লখক`, `অনবদক`, `সমপদক`, `রপনতর`, `মল`...), while `normalize_text` keeps combining marks, so core-title truncation and prefix stripping never match real text; `is_section_duplicate` (`খণড`) is dead. Lossy-encoding accident. | M | V for text.py:85-94 literals; normalize_text mark-keeping and scrape_limits `'খণড'` U |
| I3 | `epub_book.py:290` `_ratio > 0.95 or _ratio > 1/3` is redundant; the real gate is 1/3 while manifest completeness allows only 5% (n>=10) missing but counts placeholders as fetched, so a 20%-empty book passes classification and is later accepted by EPUB. The two gates are inconsistent. | M | V (epub_book.py:276-294); classification counting U |
| I4 | `_LD_AJAX_URL` computed at import from settings (book_manifest.py:1185); with unset host becomes `https:///wp-admin/...`; other paths compute at call time. | L | V |
| I5 | Scraped HTML inserted unsanitised into XHTML/HTML (Jinja2 autoescape off, `| safe`); HTML book similarly raw. Stored-XSS/EPUB injection risk if source is compromised. | H | U |
| I6 | `exec`-based module glue in `scraper.py` (shared namespace, duplicate helpers, traceback confusion). | M | U |
| I7 | Silent data loss: HTML truncation mid-tag, nodes beyond max_nodes/depth vanish, `max_lesson_pages` doubles as topic cap, parents with children lose own body (container lesson text). | H | U |
| I8 | Cache aliasing in recursive crawl (shared `children` lists, mutated cached dicts). | M | U |
| I9 | Persistence not atomic across Book/BookSource/relations/document rows; evidence->section link always None; row-by-row inserts; existing book title never refreshed; soft-deleted book revived by title match automatically (title collision between different books is possible). | H | U |
| I10 | Title-based matching: same-titled books share an output folder (overwriting cover/EPUB) and may be merged into one Book. | M | U |
| I11 | Cover download: operator-precedence bug, `srcset` None crash, extension guessed, URL host unrestricted (SSRF-ish), `cover_source_url` can hold a local filename. | M | U |
| I12 | Validation uses substring-based pattern matching with false positives (word "login" in prose forces REVIEW_REQUIRED; "chapter"/"পর্ব" in short text marks body markers; `texts_are_similar` substring rule mis-assigns content); error strings used as control flow. | M | U |
| I13 | Digit conversion to Bengali applied to English titles ("Chapter ১"); spec §13 violated. | M | U |
| I14 | Language detection inconsistent (EPUB builder ignores book_info; manifest/HTML use it), so EPUB and HTML of one book can differ. | M | U |
| I15 | Hard-coded Bengali strings in EPUB for English books ("ভূমিকা", "মূল লেখা", "সূচিপত্র" defaults). | L | U |
| I16 | Duplicated logic: front/back derivation repeated in manifest, EPUB and HTML; display_value/path helpers/html_is_blank duplicated; boundary mining run twice (can double-carve or disagree). | M | U |
| I17 | EPUB metadata minimal (no stable identifier, date, series, translator; random UUID per build possible), fonts not embedded for text, NCX + nav both added (contradicts spec §1 "NCX must not be added"). | M | U |
| I18 | Spec/code divergences listed in R2 §5 (TOC not always present; plain-text TOC may survive; back sections in TOC; named sections silently dropped; no duplication detection in scope; Book Info order delegated; translator absent from projection). | M | U |
| I19 | R1 scraper writes files and prints to stdout (no logging), no per-book isolation; R2 uses logger in places and print in builders. | L | U |
| I20 | Fragility to site markup/Cloudflare changes; HTTP 200 challenge pages indistinguishable except by sentinel titles; non-200 reason not surfaced in R1. | M | U |
| I21 | Cache sets None on final transient failure even when `cache=False` (inconsistent with other branches). | L | U |
| I22 | Evidence rows duplicated for repeated images; low-confidence warning unreachable; unused code (`extract_content_sections`, `build_toc_structure`, `scrape_lesson_content`, label `preamble_nav`, unused templates). | L | U |
| I23 | HTML book: KeyError when a section lacks `title`; CSS classes missing; ships a localStorage lock script in every export that blocks a second tab. | L | U |
| I24 | `login_source_session` has no caller in the R1 files read; wiring confirmed only in R2's fetch context. | L | U (not checked beyond reports) |

Security summary: third-party account cookies on disk, unrestricted cover host, unsanitised HTML, mutation of third-party account state, and browser impersonation to evade Cloudflare (compliance/ToS risk).

## 9. Keep / change / drop recommendations for the rebuild

Keep (behaviour, not code):
- K1 Host allow-list + canonical `/books/<slug>/` URL rule and the "off-site links are dropped, not fetched" stance. Reason: security boundary. [F1]
- K2 Manifest-first design with a per-page fetch log (url, kind, status, status code, error) and a resumable per-leaf cache; completeness classification with a configurable threshold and last-chapter guard. Reason: proven operational controls. [F20, F29-F31]
- K3 Structure types and the tri-state leaf (text / empty source / unreachable). Reason: distinguishes source gaps from our failures. [F23, F30]
- K4 Curated document model: versioned, append-only per source URL, entities with evidence and confidence, stable section IDs, validation statuses and the READY vs NEEDS_REVIEW lifecycle. [F33-F36]
- K5 Validation checks: missing title/body/canonical, duplicate paths, dead TOC leaves, source chrome, non-200 pages, sentinel titles. Reason: they catch real failure modes (Cloudflare 200 pages). [F35]
- K6 Source-agnostic metadata mapping (author, series, category), title/author disambiguation of duplicate chapters. [F9, F18]
- K7 EPUB page order, label tables (bn/en), generated cover, nested nav with container entries linking to first child, safe filename, structure audit as a CI/regression gate. [F37-F40, F43, F45]
- K8 Fail-fast empty-chapter gate (single threshold, configured once). [F42]
- K9 Rate limiting and retry policy (transient statuses, bounded backoff, SSL retry) as a library-level behaviour. [F4]

Change:
- C1 Replace the two acquisition code paths with ONE crawler service; module boundaries real (no `exec`). Isolate site-specific selectors behind a source adapter with fixture tests, so a markup change is one patch.
- C2 Make mark-complete an explicit, off-by-default, audited operator option (or drop, see D1); record every use. Prefer a content-access path that does not mutate the source account (REST with permission) if the owner allows.
- C3 Sanitise all scraped HTML with an allow-list before storing and again at render; escape titles; render EPUB XHTML via a templating step with strict escaping.
- C4 One source of truth for front/back/book-info splitting, executed once at ingestion and stored as canonical sections; EPUB/HTML renderers consume them without re-deriving (remove triple duplication).
- C5 Atomic persistence: one transaction for book + document + rows, bulk inserts, link evidence to sections, refresh title on re-import, no automatic revival by title; match by normalised source URL first and ask the operator on title-only collisions.
- C6 Truncation: parse-aware truncation or reject with an explicit flag; surface omissions caused by limits (max_nodes/depth) as validation errors, not silent drops. Separate topic-page cap from lesson-page cap.
- C7 Unify gates: one numeric threshold for missing chapters used by classification and EPUB build; count placeholders consistently.
- C8 Language handled as an explicit stored field (detected once, overridable), used by all outputs; labels table keyed by language, no hard-coded Bengali fallbacks; digit localisation only for bn.
- C9 Cover handling: restrict cover host, validate image type by bytes, store size and checksum, no filename in `cover_source_url`; render the generated cover from the same palette spec as the site (or document the palette) and keep a text-only fallback.
- C10 EPUB metadata: stable identifier derived from book id + version, dc:publisher/date/series/translator where available, embed fonts if licensing allows; decide NCX vs nav-only per the spec and then make the audit enforce it.
- C11 Replace brittle substring/pattern heuristics with Unicode-correct matching (fix vowel-mark literals; use word-boundary matching; unit-test with a gold corpus held outside git). Keep heuristics isolated and versioned (model_version).
- C12 Logging with structured fields and job correlation instead of `print`; job queue with resumable steps per leaf.
- C13 Keep operator controls for limits and `last_chapter_title` but validate them and record in the job.

Drop:
- D1 Mark-complete as default behaviour (see C2). Reason: modifies a third-party account; ToS/ethics.
- D2 Dead code: `extract_content_sections`, `build_toc_structure`, `scrape_lesson_content`, `looks_like_front_matter_label`, flat `toc.html`, `preamble_nav`, `SECTION_FALLBACK_TITLE`, redundant 0.95 check, unreachable low-confidence warning.
- D3 Import-time env evaluation and import-time computed URLs.
- D4 Per-title output folders on shared disk; use content-addressed object storage keyed by book id/version.
- D5 The preview-lock script embedded in every HTML export (move to the preview page of the app if wanted).
- D6 Browser-impersonation User-Agent as a design principle; identify honestly if the source permits, and note the Cloudflare constraint as an owner decision.
- D7 Slimming-by-key-deletion of stored JSON; model stored data explicitly (summary table + section rows).

## 10. Open questions

1. Does the owner permit the mark-complete side effect or an authenticated crawl at all, and is there an agreement with the source site (ToS/robots)? Affects whether ingestion needs credentials at all.
2. Is the HTML single-file book still a product requirement, or only EPUB?
3. Which of the two legacy crawlers is authoritative for edge cases (inline-TOC books, single-page books with no LearnDash lessons)? Report 02's manifest path handles heading-split/single-flow via `services/normalization`, whose logic (book-info key order, dedication normalisation, residual classification, role keyword lists, `SHORT_RESIDUAL_MAIN_CONTENT_LENGTH`) was not read by either report and must be analysed before redesign.
4. What exact site "dark-mode card" palette does the spec require for the generated cover (spec §2)? Current code uses forest green; unverifiable here.
5. Must the TOC page exist in every book (spec §1/§6) including main-content-only books?
6. Should NCX be omitted (spec §1) given reading apps and Send-to-Kindle conversion behaviour? Needs a test on target readers.
7. Duplicate detection (spec §11) and entity recognition (§12) live outside D1; which service owns them in the rebuild?
8. Retention: which raw source pages/snapshots may be stored (copyright), and for how long?
9. Intended semantic of the `bookmark` tab/locked pages: are they always locked by sequential progression, or can some chapters be paywalled?
10. Is `login_source_session`'s cookie-file harvest still how auth is supplied in production, and who refreshes it (cookie expiry handling is absent)?
11. Error reporting contract to the operator: which failures block (INVALID), which allow review (REVIEW_REQUIRED), and should completeness failures block publication?
12. Are the regression expectations (300-book harness, reference test list in spec §14) available as a gold corpus outside the repo?

