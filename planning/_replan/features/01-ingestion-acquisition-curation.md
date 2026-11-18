# Legacy ingestion: acquisition (scraper) and curation pipeline

Status: DRAFT (research evidence; read-only record)

Root: `archive/app/backend/apps/ingestion/pipeline`. Source site is a WordPress + LearnDash site (selectors below). External helpers named here (`apps.ingestion.services.normalization`, `resolution_support_network.get_with_host_fallback`, `resolution_support_metadata.split_display_title`, `book_manifest`, `apps.common.text`) were NOT in my scope; their behaviour is unknown beyond call sites.

## 1. Coverage

| file | lines | fully read |
|---|---|---|
| scraper.py | 19 | yes |
| config.py | 30 | yes |
| curated_source.py | 39 | yes |
| curated_export.py | 49 | yes |
| curated_extractors.py | 254 | yes |
| curated_validation.py | 231 | yes |
| curated_pipeline.py | 228 | yes |
| curated_persistence.py | 411 | yes |
| scraper_modules/scrape_limits_and_header_cleanup.py | 255 | yes |
| scraper_modules/front_matter_extraction.py | 254 | yes |
| scraper_modules/metadata_and_inline_toc.py | 301 | yes |
| scraper_modules/recursive_content_nodes.py | 235 | yes |
| scraper_modules/lesson_collection.py | 400 | yes |
| scraper_modules/book_scrape_entrypoint.py | 206 | yes |
| scraper_support/network.py | 230 | yes |
| scraper_support/text.py | 168 | yes |

(The line counts above are `wc -l`; the per-file listing printed by `cat -n` concatenated files, so quoted line numbers below are per file.) 16/16 files, 3,310 lines, all read.

Note on `scraper.py`: it does not import the modules; it `exec`s the six `scraper_modules/*.py` files in order into ONE shared global namespace (order: scrape_limits_and_header_cleanup, front_matter_extraction, metadata_and_inline_toc, recursive_content_nodes, lesson_collection, book_scrape_entrypoint). Each module relies on names imported or defined by earlier/later ones (e.g. `metadata_and_inline_toc` uses `clean_display_text`, `Path`, `settings`, `requests`, `HEADERS`, `Tag`, `urljoin` imported in file 1; `recursive_content_nodes` calls `scrape_all_lessons` from file 5; `lesson_collection` uses `json`, `time`, `re`). Line refs `file:line` use the short module name.

## 2. Feature / action inventory

### 2.1 Configuration and URL handling

- [C1] Book URL list from env — import time of `config.py` — `BOOK_URLS_JSON` (JSON array) parsed first; each entry must be a 2-item list/tuple or dict with `name`/`title`/`url` and `url`, else `ValueError("Each BOOK_URLS entry must be a (name, url) pair ...")`; else single `BOOK_URL` with `BOOK_NAME` (default = the URL); else `[]` — result in module constant `BOOK_URLS` — malformed JSON raises at import — config.py:24-49
- [C2] Source URL normalisation `normalize_source_url` — input externally supplied URL — rules: scheme must be http/https ("Book URL must start with http:// or https://"); if allowed-host set non-empty, `netloc.lower()` must be in it ("Only source site book URLs are allowed"); path must start with `/books/` ("Only direct source site book URLs are supported"); output forced `https`, host replaced by `SOURCE_SITE_HOST` (or the input host if unset), path gets exactly one trailing `/`, query/params/fragment dropped — raises ValueError — network.py:47-60
- [C3] Allowed host set `_get_allowed_source_hosts` — from Django settings `SOURCE_SITE_HOST` + `SOURCE_SITE_FALLBACK_HOSTS`; each host lower-cased, with its `www.` / non-`www.` twin added — network.py:18-39
- [C4] Crawl URL normalisation `normalize_crawl_url(url, base_url="")` — join relative to base, scheme must be http/https else `""`, host must be in allowed set else `""`, forced https, host replaced by SOURCE_SITE_HOST, path default `/`, trailing slash normalised ONLY when path starts `/books/`, keeps params and query, drops fragment — returns `""` on rejection (silently drops off-site links) — metadata_and_inline_toc:280-301
- [C5] Direct-book-root test `is_direct_book_root_url` — path split on `/`, exactly 2 parts and first == `books` — recursive_content_nodes:326-328
- [C6] Query URL builder `build_query_url(base, updates)` — merges into existing query (`keep_blank_values`), values stringified, fragment dropped — used for `ld-courseinfo-lesson-page` and `ld-topic-page` — lesson_collection:4-18

### 2.2 HTTP acquisition

- [H1] Session with retries `create_session_with_retries(retries=3, backoff_factor=1)` — urllib3 `Retry(total=retries, read=0, backoff_factor, status_forcelist=[429,500,502,503,504], allowed_methods=[HEAD,GET,OPTIONS])` mounted on http:// and https:// — network.py:63-76
- [H2] Fetch + parse `get_soup(url, max_retries=3)` — builds session (H1), calls `get_with_host_fallback(session, url, headers=HEADERS, timeout=30)` (external); status 200 -> `BeautifulSoup(decode_html_response(resp), "html.parser")`; any other status -> prints and returns `None` immediately (no retry at this layer); `SSLError` -> sleep `(attempt+1)*5` s then retry; other `RequestException` -> sleep `(attempt+1)*3` s; after `max_retries` returns `None`; session closed in `finally` — logging is `print()` — network.py:98-134
- [H3] Response decoding `decode_html_response` — if `content` is str return it; empty -> `response.text`; encoding = `response.encoding` or header-derived or `apparent_encoding` or `utf-8`; decode with `errors="replace"`; falls back to utf-8 on AttributeError/LookupError/TypeError — network.py:79-95
- [H4] Fixed request header — User-Agent `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36` (browser impersonation) — network.py:10-16
- [H5] Auth cookie loader `login_source_session(session)` — reads JSON state file at `settings.SOURCE_SITE_AUTH_STATE_PATH` (empty -> skip, missing file -> warn, unreadable -> warn); keeps cookies whose `domain.lstrip(".")` is in {host, www.host-twin} with a name; requires at least one cookie name starting `wordpress_logged_in_` else warn and return False; sets all cookies on `www.<host>` (or `www` literally if host unset); returns True — docstring: cookie harvested from a developer's logged-in browser by a "save auth script" because Cloudflare blocks automated login; file lives in `app/backend/storage/` — NOT called anywhere in my files (see section 6) — network.py:137-224
- [H6] Cover download `download_cover_image(soup, output_folder)` — finds `figure.entry-image-link.entry-image-single`; URL = `img[data-src]` else `img[src]`; fallback `<source srcset>` first token; GET with HEADERS, timeout 30, `raise_for_status`; failure -> `None` silently; extension `.webp` if `".webp"` in URL else `.jpg`; writes `<output_folder>/book_cover<ext>`; returns the bare filename — metadata_and_inline_toc:68-96
- [H7] Politeness delay — `time.sleep(1)` between lesson-listing pages only; no delay between lesson/topic/book page fetches — lesson_collection:398
- [H8] Button stripping `clean_buttons(soup)` — decomposes every `<button>` — network.py:227-230

### 2.3 Page metadata scraping

- [M1] Title/author `extract_title_and_author(soup)` — `<title>` text -> `split_display_title` (external); no title tag -> `("Book Title", "")` (sentinel that curated_validation later rejects) — metadata_and_inline_toc:37-43
- [M2] Book meta `scrape_book_meta(soup)` — container `div.entry-meta.entry-meta-after-content`; spans `entry-terms-authors` (author), `entry-terms-series` (series), `entry-terms-ld_course_category` (book_type); each is the comma-joined text of its `<a>` links (span with no links -> `""`); missing container -> three empty strings — metadata_and_inline_toc:45-66
- [M3] Author precedence — `meta_author or title_author` — book_scrape_entrypoint:468-469
- [M4] Output folder `create_output_folder(title)` — `<RUNTIME_STORAGE_DIR>/media/scraped-books/<sanitized title>`; mkdir parents; re-uses if exists (collision between same-titled books); prints — side effect on disk during scrape — metadata_and_inline_toc:20-35
- [M5] Folder name sanitiser `sanitize_folder_name` — strip; `[<>:"/\\|?*]` -> `_`; whitespace runs -> `_`; truncate char-by-char until <=255 UTF-8 bytes; strip `_`; empty -> `"book"` — front_matter_extraction:502-509
- [M6] Main content container `scrape_main_content` — first match of CSS `.ld-tab-content.ld-visible.entry-content`, `.ld-tab-content.entry-content`, `article .entry-content`, `.entry-content`; strips buttons; `decode_contents()`; passes through `remove_redundant_headers(content, "")` (empty title => effectively only a re-serialisation) — metadata_and_inline_toc:98-110. Same selector chain duplicated in `scrape_lesson_content` (lesson_collection:419-430)
- [M7] Digit normalisation of headings `normalize_structured_heading_title` — `clean_display_text` then ASCII digits 0-9 -> Bengali digits ০-৯ (`ASCII_TO_BANGLA_DIGITS`) — applied to every node title, TOC title, lesson title — metadata_and_inline_toc:5,13-17

### 2.4 Limits

- [L1] Default limits `DEFAULT_SCRAPE_LIMITS = {max_nodes: 320, max_depth: 6, max_lesson_pages: 20, max_content_chars: 120000}` — `normalize_scrape_limits(content_limits)`: each key int-parsed, fallback default on TypeError/ValueError, floor `max(1, v)`; non-dict -> defaults — scrape_limits:32-53
- [L2] Hard truncation `truncate_scraped_content` — if len > max chars, `content[:max]` (cuts raw HTML, can break tags; non-int or <=0 limit = no truncation) — scrape_limits:56-66
- [L3] `disable_recursive` flag in `content_limits` — truthy bool, or string in {"1","true","yes","on"} (case-insens); when set: toc=[], content_items=[], main_content only truncated — book_scrape_entrypoint:481-501
- [L4] `max_lesson_pages` is reused for BOTH lesson-listing pages and topic-pagination pages (`max_pages`, `max_topic_pages`) — recursive_content_nodes:433-437

### 2.5 Redundant-header removal (`remove_redundant_headers`, scrape_limits:68-225)

- [R1] Entry — HTML + title; no title -> only re-serialises; returns `str(soup)`
- [R2] Heading pass — all h1-h6 not inside ol/ul with non-empty text; removed if `is_title_duplicate(text,title)` else if `is_section_duplicate(text,title)`
- [R3] Paragraph pass — each `<p>` not inside ol/ul; candidate `<strong>` tags (direct children, else all descendants); if strong text is a title duplicate AND `len(norm(p_text)) < len(norm(strong_text))*1.5` -> whole `<p>` removed (break); elif strong is a section duplicate -> `<p>` removed
- [R4] `is_title_duplicate(header, main_title)` — `texts_are_similar` (R-text rules), else compares `extract_core_title` of both with `texts_are_similar`, else substring either way when both cores >5 chars
- [R5] `is_section_duplicate(header, lesson_title)` — intended: header like "প্রথম খণ্ড" duplicates title containing "১ম খণ্ড". Mapping table: প্রথম->[১ম, প্রথম, 1ম], দ্বিতীয়->[২য়,…,2য়], তৃতীয়->[৩য়,…,3য়], চতুর্থ->[৪র্থ,…,4র্থ], পঞ্চম->[৫ম,…,5ম], ষষ্ঠ->[৬ষ্ঠ,…,6ষ্ঠ], সপ্তম->[৭ম,…,7ম], অষ্টম->[৮ম,…,8ম], নবম->[৯ম,…,9ম], দশম->[১০ম,…,10ম]. Requires normalised header to contain the literal `'খণড'` and title too (see bug B1: this literal is the vowel-mark-stripped spelling and never matches normalised text)
- [R6] Debug printing with ✓ when `debug=True`

### 2.6 Text similarity (`scraper_support/text.py`)

- [T1] `normalize_text` — NFKC, lower; whitespace -> single space; keep only chars whose Unicode category starts with L, N or M (drops punctuation, danda `।`, ZWJ/ZWNJ); collapse spaces — text.py:5-22
- [T2] `normalize_bengali_numbers` — returns list of variants: base normalised; Bengali digits -> ASCII digits variant; for each word in table {প্রথম:"1ম", দ্বিতীয়:"2য়", তৃতীয়:"3য়", চতুর্থ:"4র্থ", পঞ্চম:"5ম", ষষ্ঠ:"6ষ্ঠ", সপ্তম:"7ম", অষ্টম:"8ম", নবম:"9ম", দশম:"10ম"} present in normalised text, a replaced variant (word->digit string, no Bengali-digit conversion on top) — text.py:28-76
- [T3] `extract_core_title` — normalise, split on spaces, cut at first token (index>0) containing any of `["লখক","অনবদক","সমপদক","রপনতর","মল","অনবদ","রচন","সকলন"]` (intended: লেখক/অনুবাদক/সম্পাদক/রূপান্তর/মূল/অনুবাদ/রচনা/সংকলন, but spelled with vowel signs removed) — text.py:79-103
- [T4] `texts_are_similar(a,b)` — in order: (1) normalised equal; (2) both len>10 and one contained in the other; (3) core titles both len>5 and equal or one contained; (4) any pair of number-variants equal, or both len>10 and substring; (5) for prefixes `["লখক","অনবদক","সমপদক","মল"]` remove prefix from both normalised strings and compare equal (non-empty) — text.py:106-168. Used for header dedupe (R4) and for matching inline-TOC entries to content (S6) and de-duping nested content — substring rules make false positives likely

### 2.7 Front matter / dedication detection (front_matter_extraction.py; used by the local `extract_content_sections`)

Constants: `FRONT_MATTER_LABEL_PATTERNS = [লেখক, অনুবাদ, অনুবাদক, সম্পাদক, সম্পাদ, প্রকাশক, প্রথম প্রকাশ, প্রকাশকাল, মূল, edition, publisher, published, translator, author]`; `DEDICATION_PATTERNS = [উৎসর্গ, অনুবাদকের উৎসর্গ, লেখকের উৎসর্গ, dedication]`; `BODY_SECTION_PATTERNS = [ভূমিকা, প্রস্তাবনা, লেখকের কথা, অনুবাদকের কথা, প্রকাশকের কথা, সূচিপত্র, অধ্যায়, অধ্যায়(dup), পর্ব, chapter, preface, introduction]`; `SEPARATOR_PARAGRAPH_VALUES = {".", "।", "..", "..."}`; `BLOCK_TAG_NAMES = h1-h6,p,li,blockquote`; `MAX_METADATA_TEXT_LENGTH=320`, `MAX_METADATA_VALUE_LENGTH=180`, `MAX_TITLE_PREFIX_LENGTH=140`, `MAX_DEDICATION_BLOCK_LENGTH=220`; `DEDICATION_INLINE_PREFIX_PATTERN = ^\s*(?:অনুবাদকের\s+উৎসর্গ|লেখকের\s+উৎসর্গ|উৎসর্গ|dedication)\s*[:ঃ\-–—]?\s*` (IGNORECASE).

- [F1] `clean_front_matter_label` — strip, then strip chars ` :ঃ-–—`
- [F2] `text_matches_patterns(text, patterns)` — true if cleaned-lowercase pattern is a SUBSTRING of cleaned text or normalised pattern is substring of `normalize_text(text)`
- [F3] `looks_like_front_matter_label(label)` — substring test of any normalised label pattern (unused locally)
- [F4] `count_sentence_markers` — count of `[।.!?]`
- [F5] `looks_like_title_prefix(prefix)` — cleaned (stripped of ` -–—|/`) non-empty, <=140 chars, no `:`/`ঃ`, matches none of label+dedication+body patterns; true if the original prefix contains `-`,`–`,`—` OR (2..10 words and len>=8)
- [F6] `search_front_matter_label_value(text, strong_text, has_break)` — text <=320 chars; for every label (longest first) regex `{label}\s*(?:[:ঃ]\s*|[-–—]\s*|\s+)(?P<value>.+)$` (IGNORECASE, all matches); value cleaned, must be non-empty and <=180. Score: prefix empty +8; elif looks like title prefix +6; elif `<br>` present and prefix<=120 +5; elif strong text equals prefix +4; elif prefix<=14 chars +1; else -3; +3 if label appears in the strong text; +1 if value<=80; +1 if value has <=1 sentence marker; candidate accepted only if score>=5; best = highest (score, earlier start). Returns `{label (strong text if it contained label, else pattern), value, score, start}`
- [F7] `extract_front_matter_label_value(paragraph)` — wrapper over F6 using paragraph text, joined `<strong>` text, `<br>` presence (unused locally)
- [F8] `is_dedication_heading(text, strong_text, tag_name)` — heading text (strong preferred) <=120 chars; must NOT match body-section patterns; MUST match dedication patterns; must not look like a label/value; and (tag is h1-h6 or has strong text or <=5 words)
- [F9] `is_body_section_marker` — non-empty; matches body patterns with len<=80; or heading tag whose normalised text matches `(অধ্যা|পর্ব|chapter)`
- [F10] `should_continue_dedication_block` — empty/separator -> continue; body marker -> stop; heading that is not a dedication heading -> stop; label/value -> stop; another dedication heading -> stop; len>220 -> stop; else continue iff <=3 sentence markers
- [F11] `extract_content_sections(html)` — iterate block tags; while in dedication, absorb blocks per F10 (removing from soup, skipping separators); a block with a label/value (F6) is moved into book_info and removed; a dedication heading starts dedication (inline remainder after prefix emitted as `<p>`), heading removed; stray separators removed once any info/dedication seen; returns `(book_info_html, dedication_html, remaining_html)` joined with `\n` — front_matter_extraction:445-493. NOT used by `scrape_book_data` (see B5)
- [F12] `extract_dedication(html)` — delegates to `normalization.extract_main_content_segments` (external) — this is what the scraper actually calls — front_matter_extraction:495-500

### 2.8 Inline TOC and content split

- [S1] Inline-TOC heading patterns `INLINE_TOC_PATTERNS = ("সূচীপত্র","সুচিপত্র","সূচী","table of contents","contents")` — heading must be <=60 chars and normalise EXACTLY equal to a pattern — scrape_limits:30; metadata:124-130
- [S2] `inline_toc_container` — if soup has exactly one top-level tag and it is div/article/section, descend into it
- [S3] TOC detection `extract_inline_toc_and_content(html)` — first block (direct child tags) that is an inline-TOC heading; subsequent consecutive `ul`/`ol` blocks are TOC lists (stop at first non-list); entries via S4. Fallback if no list entries: consecutive `<p>` blocks each containing `a[href]`, using `normalize_crawl_url(href)` (off-site links dropped) and Bengali-digit title; stop at first `<p>` without link or without valid entries. No entries -> `([], [], original)`
- [S4] List entry extraction — only direct `li` children; title from first `<a>` (else the li); entry `{title, url (href if a else ""), type:"lesson", has_content:True}`; nested direct `ul/ol` -> `children` recursively; empty titles skipped — metadata:133-156
- [S5] Body split after TOC — blocks after the TOC; a block is a "heading" if text<=180 chars and (tag h1-h6, or all its text equals its `<strong>` text); heading starts a new section and is removed; subsequent blocks appended to the section (`str(block)`) and removed; sections with no content parts are dropped; blocks before the first heading stay in the page HTML; TOC blocks finally removed; items `{title, content, type:"lesson", parent:None}` — metadata:176-277
- [S6] `consume_inline_content_item(title, remaining)` — pops the first remaining inline item whose title is `texts_are_similar` to the TOC entry title — recursive_content_nodes:331-339
- [S7] `crawl_inline_toc_entry` — per TOC entry: consume matching local content (cleaned via S9 + truncation); recurse children first; if entry has an href that is not `#...` and passes `normalize_crawl_url(base)`, fetch it as a node (S10) and overlay: local content used only if linked node has none, title forced to TOC title, type forced, children merged unique; otherwise build a node from local content only; empty entries (no title/content/children) -> None — lesson_collection:21-93
- [S8] `merge_unique_children` — dedupe by `(normalize_text(title), type)` — recursive_content_nodes:342-356
- [S9] `clean_content_html(html, title)` — `remove_redundant_headers`, strip; if visible text empty -> `""` — metadata:304-314
- [S10] `build_content_node(title, type, content, children)` — dict `{title (Bengali digits), type (default "lesson"), content, children}` — metadata:317-323

### 2.9 LearnDash lesson / topic discovery (lesson_collection.py)

- [D1] Total pages `get_total_pages(soup)` — `div.ld-pagination.ld-pagination-page-course_content_shortcode[data-pager-results]` JSON (after replacing `&quot;`->`"`) `total_pages`; any failure -> 1
- [D2] Lesson list `scrape_lesson_list(soup, page_url, max_topic_pages)` — every `div` whose class contains `ld-item-lesson-item`; needs `a.ld-item-name` containing `div.ld-item-title`; title text with regex `\d+\s*Topics.*$` (IGNORECASE, ASCII digits only) removed then Bengali-digit normalised; result `{title, url (href), topics, has_topics, listing_url}`
- [D3] Topics `scrape_nested_topics/extract_topic_entries` — requires `data-ld-expand-id` on the lesson item; topics inside `div#<expand_id>-container` `div.ld-table-list-item` with `a.ld-table-list-item-preview[href]`; title from `span.ld-topic-title` else anchor text; dedupe by normalised URL (or raw href) within lesson; entries `(title, url)`
- [D4] Topic pagination `topic_page_numbers` — page numbers gathered from `ld-topic-page=<expand_id>-<n>` query values in any href, from `data-ld-topic-page="<expand_id>-<n>"` attributes, and from `div.ld-pagination[data-pager-results].total_pages` (range 1..total, capped by max_topic_pages); always includes 1; filtered `>=1` and `<= max_topic_pages`; extra pages fetched via `build_query_url(page_url, {"ld-topic-page": f"{expand_id}-{n}"})` and the lesson item re-found by `data-ld-expand-id` (missing/failed fetch skipped) — NOTE: page 2+ fetches have no sleep
- [D5] All lessons `scrape_all_lessons(book_url, max_pages, max_topic_pages)` — loops page=1.. with `ld-courseinfo-lesson-page=<page>`; stop if page > max_pages, fetch failed, or `page >= get_total_pages`; `TypeError` fallback to `scrape_lesson_list(soup)` (compat with old signature); dedupe lessons by `(normalize_text(url), normalize_text(title))`; sleep 1s between pages
- [D6] `scrape_lesson_content(url, title)` — fetch + selector chain + `remove_redundant_headers(content, title)` — appears unused here
- [D7] `build_toc_structure(lessons_data)` — flat lesson/topic TOC with `has_content: True` — appears unused here

### 2.10 Recursive crawl

- [K1] `scrape_recursive_content_node(url, title_hint, node_type, cache, active_urls, prefetched_soup, prefetched_main_content, crawl_state, crawl_limits, depth)` — rules in order: invalid URL -> bare node; `depth > max_depth` -> bare node; `visited_nodes >= max_nodes` -> bare node; cache hit (only when no prefetch) -> new dict with hinted title/type but SHARED `children` list; URL currently in `active_urls` (cycle) -> bare node; else counter++ and mark active; fetch (`prefetched_soup or get_soup`); failed fetch -> bare node cached; title = hint or page title or URL (digits -> Bengali); main content = prefetched or `scrape_main_content`; when not prefetched, `extract_main_content_segments(main_content)` discards book_info/dedication and keeps the rest; cleaned content truncated to max_content_chars; `finally` removes URL from active set — recursive_content_nodes:359-536
- [K2] Book/root expansion — if path starts `/books/` and (node_type == "book" or direct book root URL): `scrape_all_lessons`; for each lesson, URL normalised against the listing URL; lesson with topics -> fetch each topic as node_type "topic" at depth+1, fetch the lesson page as "lesson", force title/type, merge topic children; lesson without topics -> fetch lesson node
- [K3] Fallback to inline TOC — if no lesson children: `extract_inline_toc_and_content(main_content)` -> children via S7; page content replaced by the leftover HTML (cleaned/truncated)
- [K4] TOC projection `content_node_to_toc_entry` — drops nodes with no title, or no content and no children; entry `{title, type, has_content: bool(content), path:[...], children?}` — lesson_collection:96-122
- [K5] Flatten `flatten_content_nodes(nodes, parent_path, max_items)` — depth-first, emits only nodes with content: `{title, content, type, parent (last path element or None), path}`; stops at `max_items` (= max_nodes) — lesson_collection:125-161

### 2.11 Book orchestration `scrape_book_data(book_url, *, content_limits)` (book_scrape_entrypoint:460-606)

- [B-A] Steps: normalise URL; `get_soup` (fail -> print, return None); title/author; meta; output folder; cover; main content; `extract_dedication` -> book_info + dedication; `dedupe_html_fragment_blocks` on each (external); limits; recursive crawl (unless disabled) with prefetched soup/main content, fresh cache/active/crawl_state; TOC from root children; content_items via flatten; `main_content = root_node.get("content", main_content)` (always present, may be `""`)
- [B-B] `has_explicit_body = bool(toc or content_items)`; `split_leading_front_sections(main, has_explicit_body=...)` (external) -> front_sections; if no toc/items: `infer_structured_content_from_main_content(main, book_title=)` and adopt only if both toc AND items returned; if items: `extract_boundary_sections_from_content_items(items, toc, trust_source_toc=has_explicit_body)` -> extra front/back sections and rewritten toc/items; if no explicit body: `split_trailing_front_sections` -> back_sections; `dedupe_structured_sections` for front/back with reference fragments [book_info, dedication]; `prune_duplicate_main_content(main, reference_fragments=[book_info, dedication, front html..., back html...], content_items)` (all external)
- [B-C] Returns dict `{book_title, author, series, book_type, cover (filename or None), main_content, book_info, dedication, front_sections, back_sections, toc, content_items, output_folder}`

### 2.12 Curation pipeline

- [P1] `fetch_source_pages(url, content_limits, page_cache)` — normalises URL then `book_manifest.build_manifest_source_pages` (external) — curated_source:7-13
- [P2] `build_source_snapshot(source_pages)` — fetched_urls = canonical URL + every page with `status == "fetched"` and a url + every `content_items[*].source_url` in the raw payload; sorted unique non-empty; snapshot `{schema_version, source_url, canonical_url, pages, fetched_urls, manifest, raw_scrape_payload}` — curated_source:16-35
- [P3] `normalize_scraped_payload` — non-dict -> `{}`; `promote_leading_front_matter(book_info, main_content)` (external) rewrites both; if content_items exist but no toc -> toc generated via V1 — curated_pipeline:23-35
- [P4] `build_book_metadata` — `{canonical_url, archive_title, page_title, clean_title (all = cleaned title), subtitle:"", alternate_title:"", original_title:"", volume_or_part:"", collection_title:"", incomplete_marker: structure_type=="incomplete"}` — curated_pipeline:38-51
- [P5] `build_curated_document(snapshot)` — two branches. Manifest branch (snapshot has manifest): projection = normalised `manifest_to_projection(manifest)`, structure_type = `manifest.source_structure.type` or `classify_structure`, entities/evidence/sections/assets from manifest (sections fall back to `extract_sections`, assets fall back to entities with type "asset"), validates with `raw_scrape_payload=projection`. Legacy branch: normalise raw payload; empty -> `empty_invalid_document`; classify, extract entities/evidence/sections/projection, assets = asset entities. Both: status DRAFT then replaced by validation status; copies 13 projection keys to the document top level; `source_snapshot_ref {fetched_urls, page_count}` — curated_pipeline:90-200
- [P6] `empty_invalid_document` — empty document run through validation (status INVALID because title/body missing) — curated_pipeline:54-87
- [P7] `curate_scraped_book_data(source_url, scraped_data)` — legacy payload -> `build_manifest_from_legacy_payload` -> snapshot -> document; returns `{document, source_snapshot, projection, status, validation}` — curated_pipeline:203-212
- [P8] `curate_book_document(source_url, content_limits, page_cache)` — live fetch variant of P7 — curated_pipeline:215-225
- [P9] Export helpers: `is_curated_document` (dict with keys `projection` and `validation`); `curated_document_to_legacy_payload` (manifest projection overlaid by document projection; defaults for 13 keys; adds `canonical_manifest`, `canonical_sections`, `curated_document_version`, `curated_document_status`); `curated_document_with_projection` (merge + spread at top level) — curated_export:7-49

### 2.13 Extractors (curated_extractors.py)

- [E1] `stable_section_id(prefix, value, index)` -> `"{prefix}-{index:04d}-{sha1(normalize_catalog_text(value) or str(index))[:10]}"`
- [E2] `evidence(...)` and `entity(...)` builders (value cleaned, confidence float, entity adds `normalized_value`)
- [E3] `append_unique_entity` — dedupe key `(entity_type, role, normalized_value)`; empty normalised value skipped
- [E4] `extract_book_entities` — WORK entity (role "book", conf 1.0, location `raw_scrape_payload.book_title`) + evidence extractor "title"; contributors from `normalize_scraped_book` (external): role default AUTHOR; PUBLISHER -> ORGANIZATION else PERSON; location `...book_info` unless AUTHOR (`...author`); confidence 0.95 non-author / 0.9 author; evidence extractor "metadata"; series entities (role "series", 0.95); category entities (role "site_category", location `...book_type`, 0.95); publication events from `extract_front_matter_entries(book_info)` for keys in `{edition, first_published, language, original_title, page_count}` (conf 0.92, evidence "front_matter_label", text `"{label}: {value}"`); cover ASSET (role "cover_image", 0.95, evidence "cover"); content images (E5)
- [E5] `extract_image_entities` — scans HTML of main_content, book_info, dedication and every `content_items.N.content`; each `<img>` src or data-src; ASSET role "content_image" conf 0.88 payload `{alt, index}`; evidence extractor "content_image"
- [E6] `extract_sections` — order: title-page (type TITLE_PAGE, html empty, path [title]); book-info (title "বই তথ্য") if book_info; dedication (title "উৎসর্গ") if dedication; each front section (`front-NNNN-hash`, conf 0.9); generated-toc (title "সূচিপত্র", location `curated.generated_toc`, empty html) if toc or content_items; residual main-content (id `main-content`, title = book title or "মূল লেখা", conf 0.84, type BODY if no content_items else FRONT_MATTER); each content item (`body-...`, id from path joined `" / "`, conf 0.93, payload `{type, parent}`, source_url = item's or book's); each back section (`back-...`, 0.9, BACK_MATTER); sequential `sort_order`
- [E7] `build_projection` — author names from normalised contributors with role AUTHOR joined `", "` else raw `author`; 13-key projection + `source_url`
- [E8] `classify_structure` -> `"nested_toc"` (any toc entry has children), `"flat_toc"` (toc and items), `"no_toc_heading_split"` (items only), `"single_flow_no_toc"` (main content has text), else `"incomplete"`

### 2.14 Validation (curated_validation.py)

Statuses: any error -> INVALID if one of the three hard errors present else REVIEW_REQUIRED; no errors -> VALIDATED. `is_valid = not errors`.
- [V1] Title — missing: "Missing required title." (hard); normalised title in {"book title","page not found"}: "Non-book fallback title extracted: X."
- [V2] Missing canonical URL (hard); no non-empty BODY section: "Missing body content." (hard)
- [V3] "Structured content is missing a generated TOC." when items but no toc
- [V4] Content-item checks — non-dict, missing title/path, "Content item has no body: X." (only when `has_content` key is present and non-None, see B3); duplicate paths "Duplicate content path: X."
- [V5] TOC leaf checks — "TOC content leaf has no extracted body: X." (leaf, type != "section", `has_content is False`); "Dead TOC leaf without content: X." (leaf whose path is not among content-item paths [items having text or `has_content` None] and `has_content` truthy/absent)
- [V6] Source-chrome detection — only BODY sections; blocks = h1-h6,p,li,blockquote texts (or whole plain text if none); patterns `("leave a reply","logged in","login","my account","related books","প্রাসঙ্গিক বই","মন্তব্য করুন","লগইন")`; contains-patterns `{"logged in","login","লগইন"}` match as whole words anywhere in a block; others must equal the block or be its prefix followed by a space; blocks >160 chars (`SOURCE_CHROME_MAX_BLOCK_LENGTH`) skipped except exact equality; one hit per (section, pattern) -> error "Source chrome found in body section ID: PATTERN."
- [V7] Fetch errors — page not `fetched`: "Source page was not fetched: URL (code)."; fetched but status_code non-200 and non-zero: "Source page returned non-200 status: ..."
- [V8] Warnings — "Main content was fetched but not assigned to a curated section." (raw main has text but no section with location `raw_scrape_payload.main_content`); "Low-confidence sections: ..." for confidence <0.75 (unreachable, see B4)
- [V9] Summary `{is_valid, status, errors, warnings, body_section_count, entity_count, section_count}`
- [V10] Helpers: `generated_toc_from_content_items` (title/type/`has_content` None-or-bool/path), `path_tuple`, `iter_toc_entries`, `duplicate_paths`, `dead_toc_leaves`, `empty_content_toc_leaves`

### 2.15 Persistence (curated_persistence.py)

- [W1] Slimming for storage — drop heavy keys `{main_content, book_info, dedication, front_sections, back_sections, content_items}` and `manifest` from projections, replacing with `content_summary` (char counts, per-item `{title, type, parent, path, source_url, content_chars}`); sections keep all fields but `html` -> `html_chars`; snapshots drop/slim raw payload and manifest (`slim_projection`, `slim_section_payload`, `slim_manifest`, `slim_source_snapshot`, `slim_document_payload`). NOTE the full content therefore is stored only in `CuratedSection.html` rows and `Book.*_html/content_items/toc` columns
- [W2] `next_document_version(source_url)` = max(version for that source_url)+1
- [W3] `persist_curated_document(result, book, job)` — up to 5 attempts creating `CuratedBookDocument` (book, source_job, source_url, canonical_url, version, status, structure_type, title=`book.clean_title`, validation_summary, slimmed source_snapshot, document with `model_version`) inside `transaction.atomic`, retry on IntegrityError (unique-version race); after 5 failures raises IntegrityError; then one row per entity (`CuratedEntity`), per section (`CuratedSection`, with full html), per evidence (`CuratedEvidence`) linking entity by key `(entity_type, role, normalized_value, source_location)` and section by `section_id` (evidence never carries `section_id`, so section FK is always None). Row-by-row `objects.create` (no bulk)
- [W4] `_count_empty_toc_chapters` — recursive count of non-"section" nodes whose `has_content is not True` (None counts as empty) -> `Book.empty_chapters_count`
- [W5] `persist_curated_book_with_hooks(...)` (and thin `persist_curated_book`) — normalise payload (series/book_type lists joined `", "`) via `normalize_scraped_book`; cleaned dedication via `clean_extracted_dedication_html`; raw metadata `{**raw_strings, source_url, curated_document_status}`; lifecycle: status == VALIDATED -> `LifecycleState.READY` + `ReviewState.PENDING`, anything else -> `NEEDS_REVIEW` + `NEEDS_REVIEW`
- [W6] Book matching order — `target_book` or `find_deleted_book_by_title(title)` (soft-deleted book is revived: `deleted_at=None`) or `find_existing_matching_book(title, normalized)`; found -> update fields (`deleted_at,state,review_state,raw_scraped_metadata,raw_scrape_payload,main_content_html,book_info_html,dedication_html,toc,content_items,empty_chapters_count,cover_source_url,updated_at`); else create `Book` inside atomic; on IntegrityError fall back to `find_existing_book_by_source_url(normalized_url)` or `find_existing_matching_book`, re-raise if none; existing book's title is NOT updated
- [W7] `cover_source_url` = `projection.cover_source_url` or `manifest.projection.cover_source_url` or `projection.cover` (which for the legacy scraper is a local filename) or `""`
- [W8] Relations/source — `replace_book_relations(book, contributors, series_names, category_names)` (injected, external); `BookSource.update_or_create(normalized_source_url=…, defaults={book, source_url, source_title, raw_metadata})`
- [W9] After the document row exists, writes `curated_document_model_id/version` into `book.raw_scrape_payload`
- [W10] BookGroup hint — `job.submission.raw_payload["target_book_group_id"]` (set by a "new_edition" duplicate resolution) attaches the book to that `BookGroup` if the book has no group; invalid id ignored
- [W11] Creates `MetadataVersion(book, snapshot=curated_document.document, source="curated")`; returns `(book, curated_document)`
- [W12] Dependency-injected hooks (`*_fn` params) exist for testing

## 3. Data structures

- **Scrape result** (`scrape_book_data`): see B-C. `cover` is a filename in a local folder, not a URL.
- **Content node** (internal): `{title, type: book|lesson|topic|section, content: html, children: [node]}`.
- **TOC entry**: `{title, type, has_content: bool|None, path: [str], children?: [entry], url? (inline only)}`.
- **Content item**: `{title, content: html, type, parent: str|None, path: [str], source_url?}` (no `has_content` key from the scraper).
- **Lesson record**: `{title, url, topics: [(title,url)], has_topics, listing_url}`.
- **Front/back section**: `{title, html}`.
- **Snapshot**: `{schema_version, source_url, canonical_url, pages:[{url,status,status_code,...}], fetched_urls, manifest, raw_scrape_payload}`.
- **Curated document**: `{schema_version, source_url, canonical_url, status, structure_type, book{...P4}, entities, sections, evidence, assets, projection, manifest?, source_snapshot_ref, validation, + 13 flattened projection keys}`.
- **Entity**: `{value, entity_type, role, source_url, source_location, evidence_text, confidence, normalized_value, payload}`. **Evidence**: same without normalized_value, plus `extractor`. **Section**: `{section_id, section_type, title, path, source_url, source_location, html, confidence, sort_order, payload}`.
- Entity types used: WORK, PERSON, ORGANIZATION, SERIES, CATEGORY, PUBLICATION_EVENT, ASSET. Section types: TITLE_PAGE, BOOK_INFO, DEDICATION, FRONT_MATTER, GENERATED_TOC, BODY, BACK_MATTER. Doc statuses: DRAFT, VALIDATED, INVALID, REVIEW_REQUIRED. Structure types: nested_toc, flat_toc, no_toc_heading_split, single_flow_no_toc, incomplete.
- DB models touched: Book, BookSource, BookGroup, CuratedBookDocument, CuratedEntity, CuratedSection, CuratedEvidence, MetadataVersion.
- Source-location convention: `raw_scrape_payload.<key>[.index]` or `curated.generated_toc`.

## 4. Config knobs

- Env: `BOOK_URLS_JSON`, `BOOK_URL`, `BOOK_NAME`.
- Django settings: `SOURCE_SITE_HOST`, `SOURCE_SITE_FALLBACK_HOSTS` (list), `SOURCE_SITE_AUTH_STATE_PATH`, `RUNTIME_STORAGE_DIR`.
- `content_limits` dict: `max_nodes` 320, `max_depth` 6, `max_lesson_pages` 20, `max_content_chars` 120000, `disable_recursive`.
- Hard-coded: retries 3 / backoff 1 / statuses 429,500,502,503,504 / read=0; request timeout 30 s; SSL wait 5 s*n, other wait 3 s*n; lesson page delay 1 s; Chrome 144 UA; folder name 255 bytes; front-matter thresholds (F-section constants); inline TOC heading 60 chars, content heading 180 chars; chrome block 160 chars; low-confidence 0.75; persist version retries 5; confidences 1.0/0.95/0.93/0.92/0.9/0.88/0.84.

## 5. External calls

- HTTP GET only, to the single source site (host from settings; `www.` twin and fallback hosts allowed; always rewritten to https and `SOURCE_SITE_HOST`). Pages fetched: book page `/books/<slug>/`, listing pages `?ld-courseinfo-lesson-page=N`, topic pages `?ld-topic-page=<id>-N`, each lesson/topic/linked page (only `/books/` paths get trailing-slash normalisation but any path on the allowed host is fetched), cover image URL (not host-restricted: any host the `img` points to).
- Headers: only the browser User-Agent. Cookies: optional WordPress login cookies from the auth state file (H5) — gives access to logged-in-only content; no other cookie handling. Redirects follow requests defaults. Retries: urllib3 on 429/5xx (connect/status), manual loop on exceptions; 4xx other than 429 are terminal (`None`).
- Host fallback behaviour is inside external `get_with_host_fallback`.

## 6. Bugs, dead code, duplication, hidden coupling, surprises

- B1. Bengali literals in `text.py` (`লখক`, `অনবদক`, `সমপদক`, `রপনতর`, `মল`, `অনবদ`, `রচন`, `সকলন`) and the `'খণড'` literal in `scrape_limits` are vowel-sign/virama-stripped spellings, while `normalize_text` KEEPS combining marks (category M). They therefore never match real normalised Bengali text: `extract_core_title` never truncates, the prefix-stripping branch of `texts_are_similar` is a no-op (except coincidental substrings, e.g. `মল` inside other words), and `is_section_duplicate` (the "প্রথম খণ্ড" vs "১ম খণ্ড" logic) is dead. Probably a lossy encoding accident from an earlier version.
- B2. `normalize_bengali_numbers` word map yields ASCII digits ("1ম"), but titles are normalised to Bengali digits elsewhere (M7), so word<->digit matches mostly fail unless both sides pass through the ASCII branch.
- B3. `has_content` coupling: scraper content items carry no `has_content`, so `item.get("has_content") is not None` is False and "Content item has no body" never fires for them; `dead_toc_leaves` treats them as always present. Behaviour depends on the manifest builder adding `has_content`.
- B4. Low-confidence warning (<0.75) is unreachable: lowest emitted section confidence is 0.84 (unless the manifest supplies others).
- B5. `extract_content_sections` (local front-matter extractor with scoring) is unused by `scrape_book_data`, which calls `extract_main_content_segments` from `services.normalization` instead; likely duplicate logic (cannot verify other callers). Also unused: `looks_like_front_matter_label`, `extract_front_matter_label_value`, `build_toc_structure`, `scrape_lesson_content`, `login_source_session` (no caller in my files), `_get_allowed_source_hosts` imported but only used via other modules, `shutil`/`unicodedata`-style unused imports in module 1.
- B6. `scraper.py` `exec` of module sources into one namespace: no real modules, no per-module imports, cross-file name dependencies, tracebacks refer to string-compiled paths, duplicates (`_get_source_site_host` defined in both `network.py` and `metadata_and_inline_toc.py`; `normalize_source_url` duplicated imports). Rebuild must not copy this.
- B7. `BODY_SECTION_PATTERNS` lists `অধ্যায়` twice (possibly different Unicode forms; indistinguishable in the dump).
- B8. Pattern matching is substring-based and context free: `text_matches_patterns` / `is_body_section_marker` flag any <=80-char text containing "chapter", "পর্ব", "introduction"; label regex can match labels in the middle of words (e.g. "author", "মূল"); `texts_are_similar` substring rule (>10 chars) and `consume_inline_content_item` can mis-assign content.
- B9. Source-chrome validator rejects a book whose body contains a short block that includes the word "login"/"লগইন"/"logged in" as a whole word (legit prose about logging in) — a false positive that forces REVIEW_REQUIRED.
- B10. `download_cover_image`: operator precedence `img.get("data-src") or img.get("src") if img else None`; `source.get("srcset").split()` crashes with AttributeError if `srcset` missing; writes `.jpg` for non-webp regardless of real type; fixed filename `book_cover.*`; cover URL not host-restricted; returned value is a filename, yet `cover_source_url` falls back to this filename (not a URL).
- B11. Scraping writes to disk (`media/scraped-books/<title>`) and uses `print()`; folder shared by same-title books.
- B12. Cache aliasing: cached node dicts are returned/mutated (`lesson_node["children"] = ...`, `linked_node[...] = ...`), and cache hits share the `children` list, so overlays can leak into other occurrences.
- B13. Truncation `content[:120000]` can cut inside tags/entities; no signal that truncation occurred (silent data loss).
- B14. `max_lesson_pages` doubles as topic page cap; topic-page fetches are un-throttled; nodes beyond `max_nodes`/`max_depth` become empty nodes that vanish from the TOC (silent omission, validation passes unless a TOC leaf is dead).
- B15. `main_content = root_node.get("content", main_content)` replaces landing HTML with a header-stripped, possibly truncated copy; may be `""`.
- B16. `remove_redundant_headers(content, "")` in `scrape_main_content` is effectively an HTML re-serialisation (parse/str) — wasteful, changes markup.
- B17. Lesson/topic pages fetched via recursion discard book_info/dedication segments (`_, _, main_content = extract_main_content_segments`).
- B18. Persistence is not wrapped in one transaction: Book/BookSource/relations may be saved while curated-document rows fail (partial state); the book saved twice; entities/sections/evidence inserted row by row; evidence->section link always None; `book_title` KeyError if projection lacks it; existing book titles are never refreshed; soft-deleted book revival by title match is automatic.
- B19. `build_curated_document` duplicates the 13-key flattening and validation block across two branches; `normalize_scraped_payload` runs on both paths.
- B20. Evidence is appended even when its entity was deduped away (duplicate evidence rows for repeated images); series/category entities have no evidence.
- B21. `config.py` evaluates env at import and raises on bad JSON; `_normalize_entry` accepts a dict `name` falling back to title/url.
- B22. Validation error strings double as control flow (`hard_missing` compares exact strings).
- B23. `get_soup`: double retry layers (urllib3 `total=3` on status plus manual loop) with `read=0`; non-200 returns None without surfacing the status code (only `print`), so callers cannot distinguish 404 from 403/Cloudflare challenge; HTML for challenge pages with status 200 would be parsed as a book (hence validation sentinel titles "Book Title"/"Page not found").
- B24. Hard-coded dependence on site specifics: LearnDash CSS classes (`ld-item-lesson-item`, `ld-item-name`, `ld-item-title`, `ld-table-list-item`, `ld-table-list-item-preview`, `ld-topic-title`, `ld-pagination*`, `data-ld-expand-id`, `data-pager-results`, `ld-topic-page`, `ld-courseinfo-lesson-page`), WordPress `entry-meta`, `entry-terms-*`, `figure.entry-image-link.entry-image-single`, English "Topics" text.

## 7. Not read / not verifiable

All 16 assigned files were read completely. Not read (out of scope): `book_manifest.py`, `epub_*`, `html_book*`, and the external helpers listed in the header (normalization, resolution_support_*, apps.common.text, catalog services/models). Behaviours dependent on them are described only from call sites. Whether `login_source_session`, `extract_content_sections`, `scrape_lesson_content`, `build_toc_structure` have callers elsewhere was not checked.
