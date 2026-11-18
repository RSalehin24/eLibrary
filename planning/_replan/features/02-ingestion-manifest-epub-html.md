# Legacy ingestion pipeline: manifest, EPUB, HTML book, structure audit

Status: DRAFT (research evidence; read-only record)

Root: `archive/app/backend/apps/ingestion/pipeline` (abbrev. `P/`). Spec: `archive/docs/epub-pipeline-specification.md` (291 lines, read fully).
Key limitation: manifest.py delegates entity/role extraction, front-matter splitting, dedup and book-info formatting to modules NOT in my scope (`curated_extractors`, `curated_validation`, `curated_export`, `services/normalization`, `scraper`, `scraper_support/network`). Only call sites are documented here.

## 1. Coverage table

| file | lines | fully read |
|---|---|---|
| P/book_manifest.py | 2327 | yes |
| P/epub_book.py | 304 | yes |
| P/epub_structure_audit.py | 373 | yes |
| P/html_book.py | 248 | yes |
| P/__init__.py | 1 | yes |
| P/epub_properties/__init__.py | 1 | yes |
| P/epub_properties/epub_builder.py | 990 | yes |
| P/epub_properties/labels.py | 120 | yes |
| P/epub_properties/page_templates/*.html (9 files: cover_page 14, dedication 30, generated_cover 95, info_page 36, lesson 72, main_content 13, title_page 14, toc 20, toc_hierarchical 51) | 345 | yes |
| P/epub_properties/fonts/NotoSansBengali-{Regular,Bold}.ttf | binary | no (binary fonts; only their use read) |
| P/html_book_support/preview.py | 132 | yes |
| P/html_book_support/styles.py | 3 (one giant CSS string) | yes |
| P/html_book_support/toc.py | 194 | yes |
| docs/epub-pipeline-specification.md | 291 | yes |

## 2. Feature / action inventory

Format: `[id] behaviour — inputs — rules — outputs — failure handling — file:line`

### 2.1 Manifest: limits and utilities
- [M01] Normalise content limits — dict `content_limits` — keys `max_nodes, max_lesson_pages, max_topic_pages, max_content_chars` (None/""/0/"0"/non-int/<=0 => None = uncapped); `disable_recursive` via `_as_bool` ({"1","true","yes","on"}); `last_chapter_title` cleaned — dict — bad values silently become None — book_manifest.py:62-99
- [M02] `bounded_total(total, limit)` — total<1 or non-int => 1; min with positive limit — :102-107
- [M03] `truncate_html` hard-cuts HTML string at `max_content_chars` (can cut mid-tag) — :110-115
- [M04] `build_query_url` — replaces/adds query params, drops fragment — :118-132
- [M05] `normalized_heading(title)` — clean_display_text, strips regex `\d+\s*Topics?.*$` (case-insens; LearnDash "N Topics" badge), then maps ASCII digits to Bengali digits (`BANGLA_DIGITS`) — :135-140. Side effect: ALL titles get Bengali digits even in English books.
- [M06] `html_text(html)` = clean_display_text(plain_text_from_html) — :143
- [M07] Title/author from landing page — `h1.entry-title` text, else `<title>` split by `split_display_title` (title, author); fallback title literal `"Book Title"` — :249-258; `page_title_from_soup` :241-246
- [M08] Entry terms — `.entry-meta.entry-meta-after-content` else `.entry-meta`; each `<span>` with class `entry-terms-<key>`; values = anchor texts else span text — :269-292
- [M09] `term_display(terms,*keys)` — dedup by `normalize_catalog_text`, join ", " — :295-305. Usage: author = terms `authors|author` else title_author; series = `series`; book_type = `ld_course_category|category` — :2204-2206
- [M10] Cover URL discovery — `figure.entry-image-link.entry-image-single` > `figure.entry-image-link` > any `figure`; img attrs order: data-src, data-lazy-src, src, srcset first url, data-srcset; then `<source srcset>`; urljoin to base — :315-343
- [M11] Cover extension — path/content-type contains webp=>.webp, png=>.png, jpeg/jpg=>.jpg, default .jpg — :346-354
- [M12] Cover download — session GET timeout 60, saves `<output_folder>/book_cover<ext>`; any RequestException => "" (no cover) — :357-371
- [M13] Entry content HTML — candidate selectors in priority `.ld-tab-content.ld-visible.entry-content`, `.ld-tab-content.entry-content`, `article .entry-content`, `.entry-content`; picks the candidate with the longest `get_text()` (avoids "Bookmark" tab); `clean_buttons`; `scraper.remove_redundant_headers(html,title)` — :374-392
- [M14] Source URL normalisation `normalize_content_url` — http/https only; host must equal `settings.SOURCE_SITE_HOST` or `www.`+it (else ""); forced `https`; paths starting `/books/` get trailing slash — :587-601. If SOURCE_SITE_HOST empty, any host accepted.

### 2.2 Manifest: fetching
- [M15] `SourceFetchContext` — requests session, logs in via `login_source_session` on construction, `sleep_seconds=0.5` politeness delay after each success, pages list (url, kind, title, status fetched/failed, status_code, error) and URL cache — :155-238
- [M16] Fetch retry — up to 4 attempts; transient statuses {429,500,502,503,504} backoff `2.0*attempt` s; RequestException retried the same way; timeout 60; `get_with_host_fallback`; non-transient non-200 => None, cache None. Exhausted transient: records page failed — :147-238. Note: when final attempt has transient status the `if ... attempt < MAX` is false so falls to `self.pages.append(page); self.cache[url]=None` (cache set even when cache=False) — :211-213.
- [M17] Safe Referer — `quote(url, safe=":/?=&#%@!$&'()*+,;~")` so Bengali slugs do not break latin-1 header encoding — :865-875

### 2.3 TOC handling (LearnDash scraping)
- [T01] Pager total pages — `.ld-pagination[data-pager-results]` JSON (`&quot;` replaced); prefers pager whose class/context has `course_content` or `pager_context in {course_content_shortcode, course_content}`; else first pager not inside `.ld-item-lesson-item`; default 1 — :395-426
- [T02] Topic pagination discovery per lesson — `data-ld-expand-id` ("ld-expand-<id>" or numeric); collects page numbers from `ld-topic-page=<id>-<n>` hrefs, `data-ld-topic-page` attrs, and nested pagers' total_pages (bounded by `max_topic_pages or max_lesson_pages`) — :429-471
- [T03] Topic pages > 1 fetched via `?ld-topic-page=<lessonId>-<n>` (not cached), re-find lesson item by expand id; sets `_meta.has_topic_pagination` — :546-584
- [T04] Topic entry extraction — container `div#<expand_id>-container` else lesson item; items class contains `ld-table-list-item`; anchor class contains `ld-table-list-item-preview`; title from `span.ld-topic-title`; dedup by normalised URL; post_id from `id` regex `ld-table-list-item-(\d+)` or class `ld-topic-item-(\d+)`; node `{title,url,type:"topic",has_content:True,post_id,children:[]}` — :480-542
- [T05] Embedded lesson-page TOC ("container lesson") — if a lesson has no inline topics, fetch the lesson page (kind `lesson_toc_check`, uncached) and read `.ld-course-navigation .ld-lesson-items` lists that do NOT contain `.ld-is-current-lesson`; direct-child divs with class `ld-lesson-item` become topic nodes; post_id regex `ld-expand-(\d+)` or `ld-lesson-item-(\d+)` — :613-692. Cost: one extra HTTP fetch per topic-less lesson (double fetch with later content fetch).
- [T06] Lesson node — anchor class `ld-item-name`, title in `div.ld-item-title`, `{title or url, url, type:"lesson", has_content:True, post_id, children:topics}`; returns None if neither title nor url; post_id from id/data-ld-expand-id `ld-expand-(\d+)` or class `ld-lesson-item-(\d+)` — :695-729
- [T07] Section headings — child with class `ld-item-list-section-heading` creates `{type:"section", has_content:False}`; lessons that follow nest under it; empty sections dropped — :732-818
- [T08] TOC container — `.ld-item-list.ld-lesson-list .ld-item-list-items` first else `.ld-lesson-list`; if none => fallback `_parse_tab_content_lesson_links` (all `<a>` in `.ld-tab-content` whose href contains `/lessons/`, flat lesson nodes, dedup by URL, no post_id) — :604-610, :738-777. Matches spec "only /lessons/ are chapters".
- [T09] Multi-page TOC fetch — pages 2..N via AJAX `admin-ajax.php?action=ld30_ajax_pager` with nonce from `.ld-pagination[data-pager-nonce]` (not inside lesson item), shortcode_instance JSON from `.ld-item-list[data-shortcode_instance|data-shortcode-instance]`, course_id, params incl. `pager_results[*]`, `shortcode_instance[num]` default 50, `X-Requested-With`; response `data.markup` parsed; fallback to `?ld-courseinfo-lesson-page=N` GET — :878-967, :970-1014
- [T10] TOC merge/dedup — key `(normalize_catalog_text(url), normalize_catalog_text(title))`; repeated section titles across pages merge children into the current section; sections' subtrees marked seen — :821-862. Implements spec "multiple TOCs merged into one".
- [T11] TOC meta — `toc_page_count, has_paginated_toc (total_pages>1 or topic pagination), has_section_headings, source_total_pages, fetched_total_pages, toc_pages_with_content, toc_incomplete (= total_pages>1 and pages_with_content<total_pages; signature of AJAX pager rejection)` — :1016-1031
- [T12] `disable_recursive` => empty TOC and zero meta — :971-980
- [T13] `assign_paths_to_toc` — normalises nodes: clean title (drop empty), `type` default "lesson", `has_content` (None preserved else bool), `path` list from ancestors, `source_url`, `post_id`, `children` only if non-empty — :1034-1056
- [T14] `iter_content_nodes` — yields leaf nodes (no children) with path; recursion continues into children — :1059-1065. Parents with children are never fetched for their own content (container lesson's own text lost).
- [T15] Duplicate-path disambiguation — group content items by cleaned path; if all duplicates have distinct non-empty `source_url` => rename 2nd..nth to `"<title> (<n in Bengali digits>)"`; else keep the item with longest plain text, drop others, and drop duplicate TOC leaves that share effective path — :1068-1175
- [T16] Structure type classification — no TOC: content_items => `single_page_heading_split`; main_content text => `single_page_flow_no_toc`; else `no_public_body`. With TOC: topics + lessons-without-topics => `mixed_lessons_and_topics`; topics => `lesson_topic_nested`; else `flat_lessons`; if sections => prefix `sectioned_` — :1561-1590
- [T17] Completeness rule — `topics_expected = topics + (lessons_without_topics if no topics else 0)`; fetched = len(content_items) (placeholders count as fetched); expected==0 => complete; expected<10 => allowed_missing = max(1, expected//3); else max(1, int(expected*0.05)); `content_incomplete = missing > allowed` — :1593-1615
- [T18] Last-chapter guard — if `limits.last_chapter_title` set and normalised title not among TOC leaf titles or content item titles => `content_incomplete=True` (example comment: "স্বর্গ নরক" for রম্যরচনা ৩৬৫) — :1623-1645
- [T19] Classification output: `type, traits, toc_page_count, has_paginated_toc, has_section_headings, source_total_pages, fetched_total_pages, toc_pages_with_content, toc_incomplete, content_incomplete, topics_expected, topics_fetched, last_chapter_title` — :1647-1661

### 2.4 Content fetching
- [C01] `fetch_content_item` — fetch URL (uncached, kind=node type), extract entry HTML (truncate), decompose soup; returns item `{title,content,type,parent,path,source_url}`; None if no URL — :1377-1462
- [C02] WP REST fallback when content empty and `post_id` known: GET `https://<host>/wp-json/ldlms/v2/sfwd-lessons|sfwd-topic/<id>` (timeout 30), takes `content.rendered` wrapped in `<div class="entry-content">`; any exception swallowed — :1357-1374, :1402-1414
- [C03] Mark-complete unlock — LearnDash sequential gating: finds form with input `sfwd_mark_complete` (or `sfwd_mark_incomplete` => already complete); params post, course_id, nonce, form_action. If content empty and form present: submit, sleep 1.0 s, refetch. If content present and not yet complete: submit anyway so the next lesson unlocks — :1188-1227, :1416-1453. SIDE EFFECT: scraper mutates the (logged-in) account's reading progress on the source site.
- [C04] `_submit_mark_complete` — primary AJAX POST `action=sfwd_mark_complete` to admin-ajax (JSON `success`), fallback direct form POST (form_action or lesson URL); returns bool — :1230-1354
- [C05] Empty-source sentinel `_EMPTY_SOURCE_PAGE` — page fetched but no text => placeholder item `{title,content:"",type,parent,path,source_url,has_content:None}` kept in content_items and node.has_content=None; unreachable => node.has_content=False and item skipped — :1178-1181, :1498-1523
- [C06] `collect_content_items` — iterates leaf nodes, respects `max_nodes`, `gc.collect()` every 20, resume cache via `page_cache.get_cached_items()` keyed by URL (`save_item` after each fetch; has_content semantic: cached dict with content => item.get("has_content",True), else item.get("has_content")) — :1465-1524
- [C07] Top-level `build_manifest_source_pages` pipeline: normalise URL -> limits -> session -> landing fetch (if fails, returns empty manifest with `pages`) -> title/author/terms -> `scraper.create_output_folder(title)` -> cover download -> landing main content -> TOC -> decompose landing -> content items (only if TOC) -> `normalize_body_sections` -> classification -> projection -> manifest (+ `manifest["toc_source"]=toc_nodes`) — :2186-2257

### 2.5 Front matter / book info / dedication / language rules (in `normalize_body_sections`)
- [F01] Initial split via `extract_main_content_segments(landing_main_content)` => (book_info, dedication, residual); both deduped by `dedupe_html_fragment_blocks` — :1957-1959 (logic outside scope)
- [F02] Leading front sections `split_leading_front_sections(residual, has_explicit_body=bool(toc or content_items))` — :1964-1968
- [F03] Type-B single-page inference: if no TOC and no content items, `infer_structured_content_from_main_content`; used only if both toc and items returned — :1973-1981
- [F04] Boundary sections mined from content items `extract_boundary_sections_from_content_items(..., trust_source_toc=has_explicit_body)`, then duplicate path disambiguation — :1983-1991
- [F05] Trailing/back sections only when no explicit body (`split_trailing_front_sections`) — :1993-1995
- [F06] Dedup of front/back sections against book_info + dedication (`dedupe_structured_sections`), `prune_duplicate_main_content` against everything incl. content_items — :1997-2014
- [F07] Residual classification (`classify_residual_main_content`): new key:value => merged into book_info; coherent prose => new front section(s); else discarded; only when structured content exists — :2016-2037. Implements spec "Residual / leftover front text".
- [F08] Title-page promotion `_promote_title_page_front_sections_to_book_info` — when book_info exists: a front section is "title page" if it has NO explicit title, text 1..1200 chars, contains (book title) or (any author word >=3 chars) AND any of keywords `_TITLE_PAGE_KEYWORDS` = প্রকাশ, প্রকাশক, মুদ্রক, সংস্করণ, মূল্য, publisher, printer, press, edition, published, isbn, copyright. Its `<p>` blocks (regex `<p[^>]*>.*?</p>`; fallback line split) are appended to book_info via `merge_front_matter_html_parts`, except blocks equal to title, equal to author, or "title+author" duplicate with length <= len(title)+len(author)+6 — :1664-1700, :1892-1944
- [F09] Pure title duplicate drop `_is_pure_title_duplicate_section` — text <=350 chars; true if (1) starts with book title (NFC, lowercase), (2) starts with author and contains title, (3) `_is_bibliographic_metadata_line` — :1759-1801. Applied in both book_info and no-book_info branches (:2050-2053). Implements spec §5 "title+author only => no preamble".
- [F10] Bibliographic line heuristic — <=200 chars; no newline, at most one `।` and one `.`; parentheses/brackets stripped; split on `\s*[–—/|:]\s*|\s+[-]\s+`; every fragment must be title piece / author piece / digits / in `_BIBLIOGRAPHIC_TOKEN_WORDS` / `_EDITION_MARKER_WORDS` / title-or-author tokens (>=3 chars); needs >=1 title fragment AND >=1 author fragment. Word lists: উপন্যাস গল্প ছোটগল্প গল্পগ্রন্থ প্রবন্ধ কবিতা নাটক কাহিনি কাহিনী রচনাবলী সমগ্র অমনিবাস কিশোর ক্লাসিক সাহিত্য ইতিহাস দর্শন novel "short story" story stories poem poems essay essays drama novella omnibus edition vol volume part series; edition markers খণ্ড পর্ব অধ্যায় সংস্করণ edition vol volume part ম — :1804-1889
- [F11] Language detection `detect_book_language(book_title, author, book_info_html)` — title with Bengali char (U+0980–U+09FF) => "bn"; title with Latin letter only => "en"; else sample of author+book_info: Bengali => bn, Latin => en; default "bn". Author deliberately ignored first — labels.py:15-40
- [F12] Fallback book info when none found — language en: `<p>Title: ..</p>`, `Author:`, `Series:`, `Type:`; bn: `শিরোনাম:`, `লেখক:`, `সিরিজ:`, `বইয়ের ধরন:` (each only if value present) — :2061-2081. Otherwise `format_book_info_html_ordered(book_info, book_title, language)` — :2083.
- [F13] Unnamed front section handling — sections with blank title and non-empty text kept with `title=""` (no nav_title; builder labels them); blank unnamed sections dropped — :2087-2101
- [F14] Drop inline TOC front sections when TOC/content exists — title normalised in {সূচিপত্র, সূচী, বিষয়সূচী, বিষয় সূচী, contents, table of contents, তালিকা} — :1706-1728, :2105. Only matches by TITLE, so untitled plain-text TOC remains (partially violates spec §6 "plain-text TOC dropped").
- [F15] Drop front sections whose title equals a top-level TOC entry title — :1731-1756, :2111. Only top-level toc titles are compared (children not).
- [F16] Result payload from normalize_body_sections: `book_info, dedication, front_sections, back_sections, main_content, toc, content_items` — :2114-2122
- [F17] Constant `SECTION_FALLBACK_TITLE = "অন্যান্য"` defined at :58 but never used in this file (labels handle it).

### 2.6 Manifest build / entity extraction
- [E01] `projection_from_manifest_parts` — projection dict (book_title, author, series, book_type, cover (filename or source URL), cover_source_url, main_content, book_info, dedication, front/back_sections, toc, content_items, output_folder, source_url) — :2125-2153
- [E02] `build_manifest_from_projection` — if content_items but no toc => `generated_toc_from_content_items`; `extract_book_entities(projection, url)` -> (entities, evidences); `extract_sections`; `assets` = entities with `entity_type == "asset"`; structure = given or `{"type": classify_structure(projection)}`. Entity/role extraction logic itself lives in `curated_extractors` (OUT OF SCOPE) — :2156-2183
- [E03] Manifest shape: `schema_version "2026-05-03.1", canonical_url, source_url, book{title,author,series,book_type}, metadata{entry_terms,title_author}, source_structure, projection, entities, evidence, sections, assets, pages` (+ `toc_source` added by caller) — :56, :2165-2183
- [E04] Legacy payload ingestion `build_manifest_from_legacy_payload` — `promote_leading_front_matter(book_info, main_content)`, auto-generate TOC, `build_projection`, synthetic `pages` list (landing + each item with source_url, status "fetched"), `source_structure={"type":..., "legacy_payload":True}` — :2260-2307
- [E05] `manifest_to_projection` — setdefault of every projection key from manifest; used for re-hydration — :2310-2327

### 2.7 EPUB document structure (`epub_book.create_epub`)
- [B01] Entry — accepts curated documents (`is_curated_document` => `curated_document_to_legacy_payload`); `canonical_payload` = has `canonical_manifest` or `canonical_sections` (disables re-derivation of sections) — epub_book.py:73-75
- [B02] Page order: cover, title, info, [dedication], [front_section_N...], toc.xhtml, lesson_N..., [main_content], [back_section_N...], nav (last, linear="no") — epub_book.py:88-299 and epub_builder.py:986
- [B03] Cover — if `resolve_generated_cover_path(output_folder, cover)` exists use it (`add_cover_page`), else `add_generated_cover_page()` — :88-95
- [B04] Info page ALWAYS added (scraped book_info, else fallback template of title/author/translator/series/type lines) — :100-106; template info_page.html:10-33
- [B05] Dedication — `normalize_dedication_heading_and_content(dedication)` => (title, html); page only if html non-empty — :108-115
- [B06] Front/back sections dedup against book_info+dedication; when not canonical and content_items exist, mine boundary sections again (second time; manifest already did) — :117-150. Duplicate processing in manifest, epub_book, html_book.
- [B07] If no front sections and not canonical => `split_leading_front_sections(main_content)`; if no back sections, not canonical, no explicit body => `split_trailing_front_sections` — :151-158
- [B08] Drop blank content items — keeps items with `has_content` key == None AND `source_url` key (empty-source placeholders); else `html_is_blank` check — :24-39, :162
- [B09] Single-page inference — if no content_items but main content: `infer_structured_content_from_main_content`; if >=2 items use them (pre-heading residual becomes front section titled "ভূમિকা"—literal `"ভূমিকা"` even for English books); else Phase B: treat whole blob as virtual lesson titled book title (or "মূল লেখা"), run `expand_content_items_with_subchapters`, promote sub-chapters (>=2) to top-level lessons, parent's intro becomes front section "ভূমিকা" — :164-216
- [B10] Mis-classification rescue — if `len(content_items)<=1`, not canonical, no main content, and >=3 non-blank front sections: promote them all to content items (flat TOC), clear front sections — :225-246
- [B11] TOC page — hierarchical if `toc and content_items`; else flat from content_items (`lesson_{i+1}.xhtml`); no TOC page if neither — :251-264. Spec says TOC always present: violated for books with only main_content (see section 5).
- [B12] Main-content page only for books with no content_items and plain text length >= `SHORT_RESIDUAL_MAIN_CONTENT_LENGTH` (constant from services.normalization; value not read). Title = book title or "মূল লেখা" — :272-274
- [B13] Fail-fast on empty chapters — `_empty_ci` = items with has_content None and source_url; raise ValueError if ratio > 0.95 OR > 1/3 (the 0.95 check is redundant) — :280-294. Note: the manifest completeness rule (5% for >=10 chapters) does not count placeholders as missing, so a 20%-empty book passes classification but a 34% empty book is rejected here.
- [B14] Output file `<book_title>.epub` in output_folder (sanitised) — :303-304
- [B15] `display_value` coerces dict/list author/series/type to string ("display_name","name","title" keys) — :42-54 (duplicated verbatim in html_book_support/toc.py:8-20)

### 2.8 EPUB builder (`EpubBuilder`)
- [P01] Constructor — language = given or `detect_book_language(title, author)` (NOTE: book_info NOT used here, unlike manifest's call); `labels_for(lang)`; Jinja2 `Environment(FileSystemLoader(page_templates))` — autoescape OFF (default); ebooklib `EpubBook` with title, language `bn|en`, author — epub_builder.py:392-429
- [P02] Cover image page — `set_cover(image_name, bytes, create_page=False)` to avoid duplicate ebooklib cover page; `cover_page.xhtml` rendered from cover_page.html; title label "কভার"/"Cover"; inserted at front — :450-472
- [P03] Generated cover PNG — Pillow, 1200x1800 (docstring says 600x900 — wrong), pad 100; vertical gradient #0f2419 -> #1d3c34 (mid) -> #0f2419 (64-row strip resized with BILINEAR); gold accent #c9a96e bars (120x5) top/bottom, gap 72; title bold 84pt cream #f5f1e8 line height 128, wrap by measuring words to max width 1000; series 40pt sage #c4cfbf (optional); gold divider 160x2 (gaps 32/28); author 52pt #e8e3d6, block vertically centred; saved `_generated_cover.png` in output folder — :183-336
- [P04] Cover text sanitation — collapse whitespace; strip leading numeric volume prefix regex `^[\s ]*[০-৯0-9]+[.)।]?[\s ]+`; strip trailing " – tail" (en/em dash or hyphen with spaces; colon excluded) from title if tail is equal to / contained in / contains series, then author; series cleared if == title or author; author cleared if == title — :111-180
- [P05] Cover fonts — bundled NotoSansBengali Bold/Regular, then system paths (`/usr/share/fonts/truetype/noto/...`, DejaVuSans, `/Library/Fonts`, `/System/Library/...`); `language="bn"` HarfBuzz hint passed to Pillow only when text has NO Latin letters (mixed-script drops Latin); TypeError fallback for old Pillow — :14-31, :52-108, :67-80
- [P06] Cover fallback — if Pillow import/save/font fails => `generated_cover.html` (CSS gradient #0d1117 -> #1a1a2e -> #16213e, indigo accents; different palette from the PNG) — :474-508; template generated_cover.html
- [P07] Title page `title.xhtml` — h1 book title, h2 author — :510-522; title_page.html
- [P08] Info page `info.xhtml` — scraped_book_info HTML (`| safe`) else title/author/translator/series/type lines separated by `<br>` — :524-542
- [P09] Dedication `dedication.xhtml` — heading = given title else label; italic centred; nav title always label "উৎসর্গ"/"Dedication" — :544-557
- [P10] Main content `main_content.xhtml` — skipped if blank; nav title = given or label "প্রারম্ভ"/"Preface"; template main_content.html `<title>{{lesson_title}}</title>` (variable never passed => empty title) — :559-573
- [P11] Front sections — unnamed count; nav title: explicit title, else `section.nav_title`, else prefix "অন্যান্য"/"Others" (single) or prefix + local digit index (multiple: Bengali digits for bn, ASCII for en); page heading only when explicit title; ALWAYS re-runs `extract_main_content_segments` on content to strip metadata key-value lines and drops section entirely if nothing remains (even named, e.g. a ভূমিকা with only key:value lines); file names `front_section_<n>.xhtml` numbered only for kept sections; adds entries to `_front_section_entries` — :575-637. Matches spec §5 label rules.
- [P12] Back sections — title = given else "সমাপ্তি N"/"Appendix N" (index from enumeration even if skipped blanks); `back_section_<n>.xhtml` — :639-662
- [P13] TOC registration — `toc.xhtml` chapter created empty and registered immediately (locks spine position), body rendered lazily in `build_epub` using `toc_hierarchical.html`; heading label "সূচিপত্র"/"Contents" — :664-691, :922-928
- [P14] Lesson pages — `lesson_<idx>.xhtml` for every content item (index over ALL items); heading: path len>=2 => full ancestry as h1..h6 (root h1), path len<=1 => legacy single `<h2>{{lesson_title}}</h2>`; empty-source placeholder => blank content; registers `content_pages_by_path[path]` and `fallback_title_to_page.setdefault(title)` — :693-745. Note: content is NOT marked `| safe` but autoescape is off so raw HTML renders.
- [P15] TOC entry resolution — path match first, fallback to title match (first page with that title, causing wrong target for repeated titles); entries without chapter become container entries (no file) wrapped in `epub.Section` with `#toc-section-N` fragment href pointing to first child's file so nav emits `<a>` (epub.js drops span-only items) — :747-817
- [P16] Printed toc content = content entries + back sections (front matter never listed); fallback when no content/main: front sections listed — :905-928 (matches spec: TOC covers chapters; spec says "chapters only", code also lists back sections)
- [P17] nav.xhtml build — walk `self.chapters` in order; first lesson/main_content triggers inserting the whole content tree, others skipped; remaining chapters (cover, title, info, dedication, front, toc, back) become flat entries; backstop appends any lesson file not covered; `book.toc` set from this; spine = chapters + `("nav","no")`; adds NCX and Nav items — :930-988. Spec §7 (NAV covers everything). Spec §1 "NCX/OPF spine TOC must not be added": code adds `EpubNcx` and puts nav in spine as non-linear — arguably contradicts.
- [P18] Build guard — raises `EpubContentMissingError` if no content entries, no main content, and no front/back section entries — :387-390, :878-885
- [P19] Main-content-only books get synthesized single entry for toc/nav — :891-903
- [P20] Output filename sanitation `safe_epub_filename` — replace `/ \`; remove `<>:"/\|?*` and control chars with `_`; collapse spaces; strip " ._"; truncate stem to 200 - ext bytes on code-point boundary (Bengali 3 bytes/char); default "book.epub" — :368-384
- [P21] `html_is_blank` — strips entities `&nbsp; &#160; &#xa0; &zwnj; &#8204; &#x200c;` and tags — :352-365 (same logic duplicated in epub_structure_audit `_strip_html` :67-109)
- [P22] Files written: `cover_page.xhtml, title.xhtml, info.xhtml, dedication.xhtml, front_section_N.xhtml, toc.xhtml, lesson_N.xhtml, main_content.xhtml, back_section_N.xhtml, nav.xhtml, toc.ncx` + cover image; `print()` on save (no logger) — :989-990
- [P23] Labels table (labels.py:44-75): bn = cover কভার, title_page শিরোনাম পৃষ্ঠা, info_page বই বিষয়ক তথ্য, dedication উৎসর্গ, toc সূচিপত্র, main_content প্রারম্ভ, front prefix অন্যান্য, back prefix সমাপ্তি, preamble_nav পূর্বকথা; en = Cover, Title Page, Book Information, Dedication, Contents, Preface, Others, Appendix, Preliminary Note. `html_lang` / `epub_lang` same as code. `to_local_digits`: Bengali digits for bn only (labels.py:111-120).
- [P24] Book-info labels EN (BOOK_INFO_LABELS_EN, labels.py:80-101): title, original_title, author, translator, editor, compiler, illustrator, cover_artist, publisher, other, type, series, category, first_published, publisher_address, edition, language, page_count (Pages), isbn, price. Comment says keys mirror `CANONICAL_BOOK_INFO_KEY_ORDER` in scraped_book_normalization.py (not read). Dict is not used within my files.

### 2.9 HTML book (`html_book.py`, `html_book_support/`)
- [H01] `create_html_book` — same preprocessing as EPUB (curated conversion, dedup, boundary mining, leading/trailing front split) then `save_html` — html_book.py:167-248
- [H02] `save_html` writes single file `<output_folder>/book.html` (UTF-8), prints replace notice — :26-165
- [H03] Language labels via `labels_for(detect_book_language(title, author, book_info))` (here book_info IS included) — :47-53
- [H04] Layout order: header (h1 title, author, optional "Series: X"/"সিরিজ: X" label, book type) → cover (base64 data URI of local file, or URL, or CSS placeholder card with kicker "Book") → book-info section → dedication → front sections → TOC → main content → content sections → back sections — :56-151
- [H05] Cover resolution `resolve_cover_path` — http/https/data URLs pass through; else absolute/relative file in output folder; else match by stem; else any `book_cover.*`; embeds as `data:<mime>;base64` — toc.py:35-74
- [H06] Anchor ids `make_unique_id` — `re.sub(r"\W+","_",name.lower().strip())`, numeric suffix on collision; seed = "__".join(path) — toc.py:23-32, :90-100
- [H07] Hierarchical TOC HTML — link if anchor id and (has_content or no children) else bold text; classes toc-lesson (level 0) / toc-topic; nested `ul.toc-topics` — toc.py:103-127. `has_content` default False for missing key, so entries without the key and with children are not linked (differs from EPUB behavior where parent always links).
- [H08] Content rendering — entries matched to items by path, fallback by (title, parent); skipped if neither item nor children; heading `h{min(6, level+2)}`; level 0 gets `<hr class=lesson-divider>`; content lines indented — toc.py:130-194
- [H09] Preview single-tab guard script injected in `<head>` — localStorage lock key `ebook_preview_lock:<pathname>`, heartbeat 4000 ms, stale after 15000 ms, UUID tab id; second tab replaced with "Preview already open" message via `document.write`; storage-event + beforeunload/pagehide cleanup — preview.py:1-132. Product feature of the preview page, ships inside every HTML export.
- [H10] CSS (styles.py) — fixed stylesheet (Kalpurush/SolaimanLipi/Arial fonts, container 900px, section card colours, print and <=768px media queries); defines `.cover-placeholder-*`, but NOT `.back-section*`/`.main-content` classes used by markup.
- [H11] No escaping of untrusted HTML: book_info, dedication, section html, main content, and content items inserted raw (only titles/author/series use `escape`) — html_book.py / toc.py:177-182. Titles in front/back sections: `section['title']` KeyError if missing (EPUB path uses `.get`).

### 2.10 Structure audit (`epub_structure_audit.audit_epub_structure`)
Pure zipfile/ET auditor for the 300-book regression harness (`tests/scripts/regression_curate_300.sh`). Checks:
- [A01] File exists; valid zip — :217-227
- [A02] Parse `META-INF/container.xml` rootfile then OPF (manifest id->href, spine idrefs) — :116-154, :230-235
- [A03] Spine id must exist in manifest; each spine file classified by basename: cover_page=cover, title=title, info=info, dedication=dedication, toc=toc, main_content=content, nav=nav, `front_section_\d+`=front, `back_section_\d+`=back, `lesson_\d+`=content; others "unrecognised spine file" — :36-50, :91-101, :242-252
- [A04] Slot ranking order cover<title<info<dedication<front<toc<content<back<nav must be non-decreasing — :54-65, :256-271
- [A05] Required cover and title present; info/dedication/toc/nav at most once — :273-281
- [A06] At least one content page — :285-286
- [A07] No blank front/content/back pages (visible text after stripping tags/entities) — :289-298
- [A08] nav.xhtml in spine: parse (`epub:type="toc"` nav preferred); no self link; set equality: every non-nav spine page must appear (by basename), no non-spine stray targets — :301-352
- [A09] toc.xhtml hrefs only to content/back pages (not front, toc, nav) — :354-369
- [A10] Result `EpubAuditResult{ok,errors,spine_files,spine_slots,nav_hrefs,toc_hrefs}` + `to_dict` — :71-88
- Not audited: language labels, empty-placeholder ratio, metadata (title/author/language/identifier), NCX, cover image presence in manifest, nesting depth, link targets existence, duplicate nav titles.

## 3. Data structures

- TOC node (source): `{title, url, type: "lesson"|"topic"|"section", has_content: bool|None, post_id?, children[]}`.
- TOC node (normalised): `{title, type, has_content, path: [str], source_url?, post_id?, children?}`.
- Content item: `{title, content (html), type, parent, path[], source_url, has_content? (None=empty source placeholder)}`.
- Page log: `{url, kind (landing|toc_page|topic_toc_page|lesson_toc_check|lesson|topic|content), title, status fetched|failed, status_code, error?, index?}`.
- Limits: `{max_nodes, max_lesson_pages, max_topic_pages, max_content_chars (None=uncapped), disable_recursive, last_chapter_title}`.
- Projection: see E01. Manifest: see E03. Section: `{title, html, nav_title?}`.
- Source structure types: `single_page_heading_split, single_page_flow_no_toc, no_public_body, flat_lessons, lesson_topic_nested, mixed_lessons_and_topics` (+ `sectioned_` prefix).
- TOC meta (T11), classification (T19).
- EPUB builder unified entry: `{title, file_name|None, children[]}`.
- Audit result (A10).
- Manifest schema version `"2026-05-03.1"`.

## 4. Config knobs

- Django setting `SOURCE_SITE_HOST` (host lock for URLs, AJAX, REST; module-level `_LD_AJAX_URL` freezes it at import time).
- content_limits keys (M01). `last_chapter_title` per-book.
- Constants: `_FETCH_MAX_ATTEMPTS=4`, `_FETCH_RETRY_BACKOFF=2.0`, `_TRANSIENT_HTTP_STATUSES`, fetch sleep 0.5 s (SourceFetchContext arg), request timeout 60 (30 for REST), mark-complete wait 1.0 s, gc every 20 nodes.
- Completeness: <10 chapters allow floor(n/3) (min 1); else 5% (min 1). EPUB gate: >1/3 empty placeholders rejects.
- Front/title heuristics: 1200-char title-page limit, 350-char title-duplicate limit, 200-char bibliographic line limit.
- Cover: 1200x1800, palette, fonts sizes 84/52/40, font search list.
- Labels dictionary and filenames (see P22/P23).
- Preview lock: 4000 ms heartbeat, 15000 ms stale.
- External constant `SHORT_RESIDUAL_MAIN_CONTENT_LENGTH` (not in scope).

## 5. Divergences: spec vs code

1. Spec §1 and §6: TOC "always present in every book". Code adds the TOC page only when `content_items` exist (epub_book.py:254-264); main-content-only and front-section-only books get no toc.xhtml (audit then still passes since toc not required).
2. Spec §1: "NCX/OPF TOC must not be added". Code adds `EpubNcx` and `EpubNav`, and nav.xhtml is appended to the spine (linear="no") (epub_builder.py:986-988).
3. Spec §2: cover "must match exactly the dark-mode card on the site ... same colours". Code uses a hard-coded forest-green palette (comment: "mirroring the source site's dark mode"), cannot be verified here; HTML fallback cover uses a different navy/indigo palette. Cover also lacks translator. Spec says "standard book cover portrait": satisfied (2:3).
4. Spec §3: Book Info is "mandatory, key-value only, strict field order, slash/dash separators parsed". Code order/formatting delegated to `format_book_info_html_ordered` (not read); in builder, if book_info empty, info page falls back to un-labelled lines (`title <br> author ...`) with no keys (info_page.html:15-30), different from manifest's labelled fallback (F12). The manifest fallback gives only title/author/series/type; spec also wants translator/editor/publisher.
5. Spec §3 "English books must use English labels": information-page labels done in `format_book_info_html_ordered` (not verified); but `epub_book.py` hard-codes `"ভূমিকা"` for inferred intro front sections (:179, :215) and `"মূল লেখা"` main-content title (:187, :273); `SECTION_FALLBACK_TITLE`; `normalized_heading` Bengali digits; TOC disambiguation suffix `(১)`; generated_cover.html default 'কভার', toc.html/ toc_hierarchical default 'সূচিপত্র'; HTML book `Series:` OK but "Book" kicker hard-coded English. Spec §13 not fully honoured.
6. Spec §5 nav label for unnamed: "অন্যান্য"/"Others" with numeric suffix: honoured (P11). But labels.py has an unused `preamble_nav` ("পূর্বকথা"/"Preliminary Note") and a comment in epub_builder.py:585-587 still referring to it - stale and contradictory to spec.
7. Spec §5: unnamed sections page has no heading: honoured. Spec says named front section with a title must keep title; code drops a named section whose body, after metadata stripping, is empty (:613-619) - undocumented.
8. Spec §6: plain-text TOC must be dropped "if a real linked TOC exists". Code only drops front sections whose TITLE matches TOC heading list (F14) and ones whose title equals a top-level chapter (F15); a title-less plain-text TOC inside the first chapter/front prose may survive. Spec's list of headings differs (code includes তালিকা and contents).
9. Spec §6/§7: TOC page "chapters only". Code adds back sections to the printed TOC (P16) and audit A09 explicitly permits back targets. Spec §10 End sections are not mentioned for the TOC.
10. Spec §7: "If platform cannot render nesting, link the parent to the first page". Code: container entries become `epub.Section` with href to first child; HTML printed TOC shows plain bold parent (no link) when parent has children and `has_content` falsy (toc.py:112-116, :111 default False). Printed epub toc: `<span>` (not link) for container entries (toc_hierarchical.html:38-42).
11. Spec §8 "only /lessons/ URLs are chapters; /books/ cross-links must not appear". Code only enforces `/lessons/` for the Gutenberg fallback (T08); the main LearnDash path takes any `ld-item-name` anchor and the entry-content cleanup of /books/ links is in `clean_buttons`/scraper (not read). `normalize_content_url` adds `/books/` slash handling, suggesting /books/ URLs can pass as nodes.
12. Spec §8 "never split chapters / no artificial splits" for non-single-page books: epub_book B09/B10 can create chapters from main content or promote front sections when `len(content_items)<=1` (rescue), and `expand_content_items_with_subchapters` is imported; manifest-level `extract_boundary_sections_from_content_items` may also carve front/back from items (trust_source_toc flag). Not verifiable without services/normalization.
13. Spec §9 "front items (first chapter's content) must not bleed into front sections": boundary mining from first/last chapters still runs in manifest (F04) and again in the EPUB/HTML (B06) unless `canonical_payload`.
14. Spec §11 duplication detection (title/author/publisher/translator/edition, BookGroup "create as new edition"): NOT in any file of my scope (lives in submissions/resolution services).
15. Spec §12 smart entity recognition for separators (`/`, `–`, `:`): extraction in `services/normalization` / `curated_extractors`, not in my files. `_is_bibliographic_metadata_line` splits on `– — / | :` and spaced `-`.
16. Spec §5 "section boundary `. text .` in Bengali": not in my files.
17. Spec §14 reference test list: no test code in scope; spec says one book URL returns 404, URLs are placeholders `www.example.com`.
18. Spec §3 requires Translator field before Editor etc; builder passes `translator=` (book_data.get("translator")) only as a template fallback, no editor/publisher; field absent in `projection_from_manifest_parts`.
19. Spec text omits behaviours present in code: mark-complete submission, WP REST fallback, empty-source placeholders, 1/3 empty-chapter gate, completeness thresholds, last-chapter guard, HTML book export + preview lock, structure audit rules.

## 6. Bugs, dead code, duplication, surprises

- BUG (side effect/ethics/ops): scraper submits LearnDash "mark complete" for every lesson it reads (C03) - mutates the logged-in account's progress and needs credentials; rebuild should not replicate or should make it an explicit option.
- BUG: `_LD_AJAX_URL` computed at import time from settings (:1185); stays `https:///wp-admin/...` if SOURCE_SITE_HOST is unset or settings change; `_fetch_learndash_toc_page_ajax` and REST fallback compute at call time (inconsistent).
- BUG: `fetch_soup` caches None for failures even when `cache=False` in the 'give up' path (:211-213) while other paths guard on `cache`.
- BUG: topic `_meta["has_topic_pagination"]` set only when page_number>1 discovered; `scrape_nested_topic_nodes` fetches those pages with one request each and no AJAX - assumes GET param works (the code elsewhere says GET params are ignored for course pager).
- BUG-ish: `iter_content_nodes` yields only leaves; a lesson with both topics and own body text loses its own body. Container-lesson detection (T05) costs a second page fetch.
- BUG: `normalized_heading` converts all digits to Bengali so English TOC titles like "Chapter 1" become "Chapter ১" (spec §13 violation) and `duplicate_path_title` uses Bengali digits.
- BUG: `epub_builder` language detection ignores `book_info` while manifest and HTML use it; the same book can get different language labels in EPUB vs HTML (P01 vs F11/H03).
- BUG: `main_content.html` template uses `{{lesson_title}}` for `<title>` but render passes none (blank title); `info_page.html` last branch references undefined `book_info` (unreachable).
- BUG: `add_back_section_pages` fallback label index uses enumeration index while file index uses registered index: titles "Appendix 3" may sit at `back_section_2`.
- BUG: `_entries_to_nav_nodes` / `_build_content_entries` fall back to title lookup (`fallback_title_to_page.setdefault(title)` keeps FIRST page) so duplicate chapter titles in different parents resolve to the wrong file when paths don't match.
- BUG: generated cover docstring says 600x900 but 1200x1800; `generated_cover.html` uses self-closing `<div ... />` (invalid XHTML-as-HTML; renders nested incorrectly in HTML parsers, OK in strict XHTML).
- BUG: `html_book.py` crashes with KeyError if a front/back section lacks `title`; escaping missing for several fields; `.back-section*`/`.main-content` CSS not defined.
- BUG: `_is_title_page_front_section` requires NO title yet docstring/commentary says "e.g. সতী's first front section"; `author_match` uses substring `part in haystack` with words >=3 chars (e.g. short Latin fragments match unrelated text).
- BUG: `_is_pure_title_duplicate_section` Case 1: any short (<=350) text that merely STARTS with the book title is dropped - a preface titled the same as book start would be lost; `startswith` on lowercased text only.
- BUG: `classify_manifest_structure` counts `len(content_items)` (which includes body-less placeholders) as fetched, so placeholders hide missing coverage; threshold text mentions "Both empty-source and failed count as missing" but code counts placeholders as fetched (comment contradicts code :1599-1604).
- Redundant: `_ratio > 0.95 or _ratio > 1/3` (epub_book.py:290).
- Dead/unused: `SECTION_FALLBACK_TITLE`, `time`/`os`/`quote` imports partially, unused `limits` params in `_parse_tab_content_lesson_links` and `_scrape_embedded_lesson_page_toc`, `labels_for` imported in manifest and unused, `has_class_token` OK; `preamble_nav` label; `BOOK_INFO_LABELS_EN`; templates `toc.html` (flat TOC, unused: builder uses toc_hierarchical for both) and `info_page` branch; `build_navigation_entries` wrapper with a pointless duplicated conditional (:822-827); `add_info_page(additional_info)` never passed; `book_type` passed to `EpubBuilder` but metadata not written to OPF.
- Duplication: `display_value`, `content_path_tuple`, `resolve_entry_path` duplicated in epub_book.py/epub_builder.py/html_book_support/toc.py; `html_is_blank` duplicated in audit; front/back section derivation repeated three times (manifest, epub_book, html_book); `normalize_dedication_heading_and_content` and boundary mining run both at manifest and render time; section handling logic is repeated for EPUB/HTML.
- Surprise: fonts are bundled only for cover rendering; EPUB text pages reference "Kalpurush"/"SolaimanLipi" system fonts and do not embed fonts, so Bengali text may render in fallback fonts on readers lacking them.
- Surprise: `print()` used for output instead of logging in builder/html.
- Surprise: EPUB metadata only sets title/author/language - no identifier/UID, no publisher, no date, no series, no translator; ebooklib supplies default identifier (UUID random?) which differs per build. Not verified.
- Surprise: HTML book downloads/embeds cover as base64 inline; entire book is a single file; each HTML export contains a localStorage lock script that blocks second tab.
- Surprise: scraper hits sequential per-chapter page requests with 0.5 s delay + extra container-lesson probe + REST fallback + mark-complete + retry, i.e. up to ~5 requests per chapter.
- Surprise: manifest `raw_scrape_payload` equals the projection (same object), and `manifest["toc_source"]` stores the full source tree.
- Security: scraped HTML passes unsanitised into XHTML/HTML (Jinja autoescape off, `| safe`); the rebuild must sanitise.
- Architecture note for rebuild: this code mixes scraping, normalisation, manifest, and rendering with Django settings, Pillow, ebooklib, Jinja2, bs4, requests.

## 7. Unread / limits

- Binary fonts `NotoSansBengali-Bold.ttf`, `NotoSansBengali-Regular.ttf` (not text; line counts reported by wc are meaningless). Identified use only.
- Out-of-scope callee modules not read (behaviour only known from call sites): `curated_extractors` (entity/role extraction, `extract_book_entities`, `extract_sections`, `classify_structure`, `build_projection`), `curated_validation.generated_toc_from_content_items`, `curated_export`, `services/normalization` (all front-matter, book-info key ordering `format_book_info_html_ordered`, dedication normalisation, residual classification, `SHORT_RESIDUAL_MAIN_CONTENT_LENGTH`), `scraper` / `scraper_support/network` (`clean_buttons`, `remove_redundant_headers`, login), `submissions_support.assets.resolve_generated_cover_path`, `resolution_support_*`, `common.text`. Entity/role extraction (author/translator/editor/publisher roles) therefore could NOT be documented beyond the call sites; Bengali keyword lists for roles/dedication/book-info live there.
- No code executed; spec URLs not verified.
