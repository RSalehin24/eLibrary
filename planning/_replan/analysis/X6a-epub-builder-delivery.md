Status: DRAFT

# X6a - EPUB builder and delivery (legacy Django, first-hand trace)

Base path: `archive/app/backend/apps/` (abbrev `B/`). Everything below was read directly; "NOT READ" is stated explicitly.

## 1. Files read

| File | Lines | Fully read |
|---|---|---|
| B/ingestion/pipeline/epub_properties/epub_builder.py | 990 | yes |
| .../epub_properties/labels.py | 120 | yes |
| .../epub_properties/page_templates/*.html (cover_page 14, dedication 30, generated_cover 95, info_page 36, lesson 72, main_content 13, title_page 14, toc_hierarchical 51, toc 20) | 345 | yes (all 9) |
| .../epub_properties/fonts/ | listing only: NotoSansBengali-Regular.ttf, NotoSansBengali-Bold.ttf | list only (binary) |
| B/ingestion/pipeline/epub_book.py (caller of builder; not in the brief but needed to trace the payload) | 304 | yes |
| B/ingestion/pipeline/html_book.py | 248 | yes |
| .../html_book_support/preview.py 132, styles.py 3 (one-line CSS string), toc.py 194 | 329 | yes |
| B/ingestion/pipeline/epub_structure_audit.py | 373 | yes |
| B/access/views/assets.py | 296 | yes |
| B/access/views/shared.py (helpers assets.py imports) | 280 | yes |
| B/access/views/preview_html.py | 18 | yes |
| B/access/services/preview_html.py (the only file in access/services besides a 1-line `__init__`) | 209 | yes |
| B/accounts/kindle.py | 19 | yes |
| B/common/permissions.py | 151 | yes |

## 2. EPUB build trace (payload -> .epub)

Library: `ebooklib.epub` plus `jinja2` (epub_builder.py:3-4). Entry point is `create_epub(book_data)` (epub_book.py:56), which uses `EpubBuilder` (epub_builder.py:392).

Payload (documented at epub_book.py:60-71): `book_title, author, series, book_type, cover, main_content, toc (nested list), content_items, output_folder`. It also reads `book_info, dedication, front_sections, back_sections, translator, canonical_manifest/canonical_sections` (epub_book.py:75,102,105,117-126). A "curated document" is first converted to this legacy payload shape (epub_book.py:73-74).

Step by step (epub_book.py):
1. Builder created. Title and author go straight in (`display_value` flattens dict/list authors, 42-54). Language is auto-detected from the title: Latin letters and no Bengali means `en`, otherwise `bn` (labels.py:15-40; builder 399). The `language=` argument is never passed by `create_epub` (epub_book.py:77-83).
2. Cover (88-95): a real cover image resolved by `resolve_generated_cover_path` (that function is in ingestion/services/submissions_support/assets.py, NOT READ). If found, `add_cover_page`. Otherwise `add_generated_cover_page` (builder 474).
3. Title page (98), info page (103), dedication page only if dedication HTML exists (108-115).
4. Structure inference. Existing front/back sections are de-duplicated against book_info/dedication. Unless the payload is canonical, `extract_boundary_sections_from_content_items`, `split_leading_front_sections` and `split_trailing_front_sections` (all in ingestion/services/normalization.py, NOT READ) mine front and back matter from the text (epub_book.py:127-158). Blank content items are dropped (162). A single-blob book is split into chapters by heading inference (170-216). A rescue promotes front sections to chapters when 3 or more are substantive and 1 or fewer chapters exist (225-246).
5. Front section pages (248-249). TOC page: hierarchical if `toc and content_items` (254), flat list from items (259-264). Main-content page only for single-flow books, only if the plain text is at least `SHORT_RESIDUAL_MAIN_CONTENT_LENGTH` (272-274).
6. Empty-chapter guard: raises `ValueError` if the share of placeholder chapters (`has_content is None` and `source_url` present) is over 1/3 (epub_book.py:280-294). `_ratio > 0.95 or _ratio > 1/3` is redundant (the first is implied by the second).
7. Lesson pages (297), back-section pages (299-300), then `build_epub(f"{book_title}.epub", toc_structure=toc)` (303-304).

### Page types and file names (the builder's fixed vocabulary)
- `cover_page.xhtml` (img of the cover) or the HTML fallback `generated_cover.html` (builder 450-508).
- `title.xhtml` (title and author, template `title_page.html`, 510-522).
- `info.xhtml`. If scraped book-info HTML exists it is rendered raw. Otherwise it renders a `<p>` with title, author, translator, series, type, additional_info (builder 524-542; template info_page.html:10-33).
- `dedication.xhtml` (544-557).
- `front_section_N.xhtml`, via `lesson.html` (575-637). Metadata lines are stripped through `extract_main_content_segments` (611-620), and metadata-only sections are dropped.
- `toc.xhtml`, registered early to fix its spine slot, with its body rendered late in `build_epub` (664-691, 922-928). It uses `toc_hierarchical.html`. `toc.html` (flat) is NOT used by this code path: `add_toc_page` registers an empty chapter and `build_epub` renders only `toc_hierarchical.html`.
- `lesson_N.xhtml` (693-745). Heading logic: path length 2 or more renders h1..h6 for the ancestry chain, otherwise a single h2 title. The template shows no heading if the title is empty.
- `main_content.xhtml` (559-573), `back_section_N.xhtml` (639-662).
- Labels: Bengali or English strings (labels.py:44-75). Digits are localised to Bengali numerals for "Others 1" and similar fallback titles (labels.py:108-120).

### Package, OPF, nav, NCX
- Metadata set on `EpubBook`: title (`set_title`), language (`set_language`, `bn` or `en`), a single author (`add_author`) (builder 405-407). That is all. Not set anywhere in the files I read: identifier/UUID, publisher, series, `book_type`, translator, description, date, subjects. NOT VERIFIED what ebooklib does with a missing identifier (library code NOT READ). `series` and `book_type` are used only on the info page and the generated cover.
- Cover image registered via `book.set_cover(name, bytes, create_page=False)` (builder 454-458), so the image is the OPF cover item while the cover page is a separate custom xhtml. The cover file is opened with `open(...).read()` and never closed (builder 456).
- Spine: `[*self.chapters, ("nav","no")]` (builder 986). Order is registration order, with the cover inserted at index 0 (`insert_front=True`, 435-448).
- Navigation: `book.toc` is built from a unified entries tree (`_entries_to_nav_nodes`, 782-817). Container nodes become `epub.Section` with a synthetic `#toc-section-N` href so epub.js does not drop span-only items (comment at 787-791). A backstop appends any lesson missing from the tree (958-983). `EpubNcx` and `EpubNav` are both added (987-988), so there is an EPUB3 nav plus an NCX for EPUB2/Kindle. `write_epub` writes to `output_folder/<filename>` (989).
- The printed toc.xhtml lists the content tree plus back sections only. nav.xhtml lists every page (builder 905-956, mirrored by the audit).
- Success is reported by `print(...)` (990). There is no logging and no return value.

### CSS and fonts
- No stylesheet file is added to the EPUB (no `EpubItem` of CSS, no `add_item` for a font anywhere in epub_builder.py, which I read in full). All styling is inline `style=` attributes plus a per-page `<style>` block in the templates. Fonts are referenced by name only: `"Kalpurush", "SolaimanLipi", "Noto Sans Bengali", Arial` (lesson.html:11-13; generated_cover.html:36-37; toc_hierarchical.html:13-14). Other pages use `Arial` only (title_page, info_page, dedication, main_content, cover_page). So the reading device must supply a Bengali font. Fonts are NOT embedded in the EPUB.
- Bundled NotoSansBengali TTFs (builder 10-12) are used only to draw the generated cover PNG (Pillow), with fallbacks to system font paths (16-31, 52-64). If no font loads, the title is skipped (`title_font` None gives `title_lines=[]`, builder 262).
- Hard-coded colours and layout in `style=`: for example `color:#2c3e50`, `margin: 100px 40px 60px 40px`, `width/height:100%` (title_page.html:8, info_page.html:8).

### Bengali typography handling
- Cover PNG: 1200x1800 canvas (builder 213; the docstring at 477 wrongly says 600x900), Pillow/libraqm shaping with `language="bn"` only when the text has no Latin letters (a workaround because the hint drops Latin glyphs in mixed text, builder 67-80). `TypeError` fallback for old Pillow (96-99, 252-254). Whether libraqm is installed is not checked: without it the `language` kwarg is probably rejected or ignored. NOT VERIFIED.
- Word wrap is by whitespace with measured pixel width (83-108). A single over-long word is not split.
- Cover input clean-up: strips leading Bengali or Latin numeric prefix `^\s*[০-৯0-9]+[.)।]?\s+`, trims a trailing " - series" or " - author" tail, and removes duplicate fields (113-180).
- No text normalisation (NFC, ZWJ/ZWNJ) in the builder. The only awareness of ZWNJ is in the blank-page test (`&zwnj;`, `&#8204;`; builder 353, audit 68).
- `lang` attribute on every `<html>` is `bn` or `en` (templates). `dir` is not needed (Bengali is LTR).

## 3. HTML book trace (html_book.py)

This produces the "preview" `book.html` (a single self-contained page), not the EPUB. Same inference steps as epub_book.py (html_book.py:186-232), then `save_html` (26-165):
1. Static f-string assembly of one document. Fixed single-line CSS (`generate_css`, styles.py). Cover is inlined as a base64 `data:` URI (`html_cover_source`, toc.py:64-74). Without a cover it shows a CSS placeholder card with an English "Book" kicker (html_book.py:84-87).
2. Sections in order: header (title, author, series label "Series" or "সিরিজ", type), cover, book-info block, dedication, front sections, a TOC with anchors (`make_unique_id`, toc.py:23-32; `\W+` to `_`), main content, chapters (heading level `min(6, level+2)`, toc.py:149-150; two-level indent), back sections.
3. Anchor ids come from `re.sub(r"\W+","_")` on a lower-cased title path. Bengali word characters survive (Python `\W` is Unicode-aware).
4. Written to `output_folder/book.html` (159-163). `print` only.
5. `render_preview_single_tab_guard_script()` is injected into the `<head>` of the book (html_book.py:62; preview.py:1-132). Inline `<script>` with a localStorage lock keyed by `window.location.pathname`, 4 s heartbeat and 15 s stale timeout. A second tab calls `document.open()/write()` to replace itself with a "Preview already open" page. It is client-side only and trivially bypassed.
6. NB: `book_data["toc"]`, `["content_items"]`, `["main_content"]`, `["cover"]`, `["output_folder"]`, `["series"]`, `["book_type"]` are hard indexes, so a missing key gives `KeyError` (html_book.py:199-200,224,237-244).

## 4. Escaping / sanitisation findings

- **Jinja2 `Environment` is created with NO autoescape** (epub_builder.py:401-403; default is off). So every `{{ var }}` in every template is unescaped, not just the ones marked `| safe`. Affected plain-text fields: `book_title`, `author`, `series`, `book_type`, `translator`, `additional_info`, `lesson_title`, `heading_text`, `dedication_title`, `entry.title`, `entry.file_name` (e.g. title_page.html:10-11, lesson.html:5,54-67, toc_hierarchical.html:24,34-36, generated_cover.html:86-91). A title containing `&`, `<` or `"` would emit malformed XHTML or, if attacker-controlled, markup. Titles like "A & B" are plausible in a library, so this is a correctness bug as well as a security one.
- `| safe` appears explicitly at dedication.html:27 and info_page.html:12. The main body fields (`lesson_content`, `main_content`) are plain `{{ }}` and are intentionally raw HTML; with autoescape off they behave the same as `| safe`. The input is scraped or curated HTML.
- **No HTML sanitisation anywhere in the files I read.** Content HTML goes unchanged into XHTML pages and into book.html. The only transformation is normalisation of front/back matter (normalization.py NOT READ, so I cannot say whether it sanitises). Scripts, event handlers, `javascript:` URLs, iframes and external `<img src>` in source content would survive.
- html_book.py does `html.escape` on titles, author, series and type (lines 61,68,69,73,75,86) and TOC titles (toc.py:109,173), but `cover_src` is not escaped and is put in a single-quoted attribute (html_book.py:82). A cover string starting `http://` or `https://` (accepted unmodified, toc.py:36-37) containing `'` can break out of the attribute. `entry_id`, `anchor_id` come from `\W+` replacement so they are safe. `labels` strings are trusted constants. `book_info`, `dedication`, section HTML and `main_content` are raw (html_book.py:94-95,107-108,117-118,135,178-181).
- access/services/preview_html.py:94-96,109-111 builds soup fragments with f-string `{title}` unescaped (dedication and front-section titles).
- **Preview HTML is served as an HTTP response of the API origin** (`HttpResponse(html, content_type=asset.content_type or "text/html")`, access/views/preview_html.py:9-11). Stored script in book HTML would execute in the API origin. Whether a CSP, sandbox, separate origin or `X-Content-Type-Options` is applied is NOT READ (middleware and settings not read). JWT or cookie exposure on that origin is therefore unknown.
- The EPUB audit does not parse content pages as XML (see section 6), so malformed XHTML passes it.

## 5. Download / preview / cover / Kindle trace

### URLs and roles
- `BookAssetDownloadView.get(request, slug, asset_type)` (assets.py:117-155). `IsAuthenticated` only. Book is fetched by slug (`get_object_or_404`, no visibility or lifecycle filter, so draft or hidden books are also addressable if the user has a grant). The URL route is not shown here (urls file NOT READ).
- Permission by type (assets.py:122-141; common/permissions.py):
  - `cover`: `user_can_view_book_cover` -> `user_can_launch_reader` = owner, OR (not read-once-consumed AND scope any of PREVIEW_HTML/READ_DURABLE/DOWNLOAD_FILE/READ_ONCE) (permissions.py:81-99).
  - `html`: explicit read-once check first (assets.py:125-128), then `user_can_view_preview_html` (owner, or not read-once-consumed AND PREVIEW_HTML scope, permissions.py:69-74). After a successful grant of a user with READ_ONCE and no READ_DURABLE, a `BookOpeningRecord` is created with `get_or_create` (assets.py:130-139). That is the "read once" ledger: the first HTML fetch consumes the single read.
  - everything else (EPUB and any other `asset_type` string that resolves): `user_can_download_book_assets` = DOWNLOAD_FILE scope or owner (permissions.py:65-66, assets.py:141).
- `user_has_scope` returns True for any superuser or staff (permissions.py:31-32), and the scope check also accepts `ADMIN_FULL_CONTROL` (35). Grants can be global, by book, by category, or by author (contributor with role AUTHOR) (permissions.py:16-24). "Owned" = a `UserBook` row or an annotated flag (permissions.py:39-45).
- The raise in assets.py:143-144 is `PermissionDenied` (HTTP 403) with the same message for all types ("download access"), even for cover and preview.

### Delivery
- Non-HTML: `FileResponse(open_asset_stream(asset), as_attachment=True, filename=asset_download_filename(...))` (assets.py:151-155). Filename = `safe_download_stem(book.title)` + suffix; EPUB forced to `.epub`, HTML `.html`, cover uses source suffix or mimetype guess (shared.py:108-126). Stem sanitiser replaces `<>:"/\|?*` by `-`; it does not remove control chars or bound length (unlike the builder's `safe_epub_filename`, epub_builder.py:368-384, which strips controls and caps at 200 bytes). Starlette/Django header encoding of non-ASCII is handled by Django's `FileResponse` (RFC 5987 `filename*`), not verified in this code.
- Cover is also sent with `as_attachment=True` (condition `asset.asset_type != HTML`, always true in that branch), so images are downloads, not inline. How the UI shows covers is NOT READ.
- No `Cache-Control: no-store` on these two responses. `apply_no_store_headers` exists (shared.py:26-30) but is not applied in assets.py.
- Asset resolution: `resolve_asset` takes the first `READY` row of that type (shared.py:62-66), `Http404` otherwise. The file is a Django FileField with a fallback to `legacy_path` on local disk (shared.py:87-97,164-171). Missing file flow: `missing_asset_response` marks the asset FAILED and clears its paths, tries to queue regeneration if a source URL exists (HTTP 409 with job id), else sets the book to NEEDS_REVIEW and returns 404 (shared.py:174-234). A GET therefore mutates state, and any user with access can trigger a reprocess job through a missing file (`queue_reprocess_book(book, actor=actor)`, shared.py:202, implementation NOT READ).

### Preview HTML
- `html_asset_response` -> `normalize_preview_html` (access/services/preview_html.py:187-206): reads the whole file, decodes with `errors="replace"`, parses with BeautifulSoup `html.parser`, promotes leading front matter and dedication into proper sections (121-184), and replaces every local `<img src>` (relative, no scheme, not starting with `/` or `#`) by a base64 data URI of a file looked up by basename (or same stem) in the HTML's own directory, with cover fallback (23-65, 196-204). This uses only the basename, so there is no traversal outside the asset folder, but it does inline any sibling file whose stem matches. It re-serialises only if something changed. Memory cost: full book plus base64 images is built in RAM per request.

### Kindle
- `BookSendToKindleView.post` (assets.py:158-293): `IsAuthenticated`; permission `user_can_send_to_kindle` = SEND_KINDLE scope or owner (permissions.py:77-78).
- Kindle email rule: user stores a list `request.user.kindle_emails`. Each entry is validated by `validate_kindle_email_address`: Django `validate_email`, lower-cased, domain must be exactly `kindle.com` (accounts/kindle.py:4-19). Invalid or blank entries are silently skipped (assets.py:38-47). If none are valid -> 400 "Add at least one Kindle email" (166-175). `@free.kindle.com` and `@kindle.amazon.com`-style variants are rejected. Where emails are validated on save and the list-length limit is NOT READ (accounts serializers).
- What is sent: one `EmailMessage` per Kindle address, subject = `book.title`, empty body, one attachment: the whole EPUB bytes, MIME `application/epub+zip`, name from `asset_download_filename` (assets.py:181-182,222-229). The EPUB is read fully into memory once (`read_asset_bytes`, shared.py:149-161). Sender = `ACCOUNT_INVITE_FROM_EMAIL` or `DEFAULT_FROM_EMAIL`, stripped of quotes and parsed with `parseaddr` (183-190). The subject is unsanitised book title (Django rejects newlines in headers, so a header-injection error would raise inside `send`; it is caught as a generic failure).
- Size limits: none in this code. No check against Amazon's attachment cap, no check of the EPUB size at all. NOT READ: SMTP provider limit.
- Backend: Brevo API backend (`anymail.backends.brevo`) is rejected for EPUB and replaced by plain SMTP (assets.py:32-55). SMTP kwargs come from settings: host, user, password, port (default 587), TLS (default True), SSL, timeout (default 20 s) (76-97). If SMTP host, user or password is blank -> 502 with a text that tells the operator what to configure (198-214). Note that this error text, which leaks configuration hints (variable names) but no secret values, goes to the end user. A non-Brevo backend (console, smtp, other) is used as-is; for those the "no credentials" guard is skipped unless the backend is SMTP.
- Failure handling: loop over addresses with a single shared connection; `SMTPAuthenticationError` aborts the loop and marks the rest failed (230-240); other exceptions mark that address failed and continue (241-247). Zero delivered -> 502 with `failedEmails` and `senderEmail` (254-273). Partial success -> 200 with `deliveredEmails`, `failedEmails` (286-293). `finally` closes the connection, logging close errors (251-252, 104-114).
- Success record: `UserBookKindleSend` rows for (user, book) are deleted and recreated (275-276), so only the latest send is stored, with no history and no per-day or rate limit in this view. The delete+create is not in a transaction. Throttling: NOT READ (DRF settings not read).
- Email send is synchronous in the request thread (timeout 20 s per socket op, times N addresses). No queue.
- "Approved sender" requirement from Amazon is only mentioned in the error text (262-263); nothing in code checks it.

## 6. What the audit (epub_structure_audit.py) checks

Pure functions over a finished .epub using only zipfile, ElementTree and regex (audit 1-24). Docstring says it is for the "300-book regression harness" (`tests/scripts/regression_curate_300.sh`, not read). Checks (audit 209-373):
1. File exists and is a valid zip (217-227).
2. `container.xml` -> OPF parse; manifest id->href and spine idrefs (116-154, 231-238); every spine idref exists in the manifest (242-246).
3. Each spine file maps to a slot from its file name only (`cover_page.xhtml`, `title.xhtml`, `info`, `dedication`, `toc`, `main_content`, `nav`, `front_section_N`, `back_section_N`, `lesson_N`); any other name is "unrecognised spine file" (38-101, 247-252).
4. Slot order is monotonically non-decreasing: cover, title, info, dedication, front, toc, content, back, nav (54-65, 259-271).
5. cover and title present; info/dedication/toc/nav appear at most once; at least one content page (273-286). A book with only front sections (the rescue case at builder 875-885) would fail the "spine has no content pages" check.
6. Blank-page check on front, content and back pages: strips tags and some whitespace entities (288-298, 104-109). The check runs on the whole XHTML, including `<style>` and `<title>` text, so a page that has a heading or a title but no body text still passes. Equivalent builder check at epub_builder.py:356-365.
7. nav.xhtml: ordered hrefs from `<nav epub:type="toc">`; no self link; comprehensive (every non-nav spine page present, no stray non-spine targets) (157-185, 300-352).
8. Printed toc.xhtml links only to content or back pages (354-369), with a regex fallback if XML parse fails (188-206).
Not checked: well-formedness of content XHTML, manifest items missing from the archive other than spine docs, image presence or cover media type, OPF metadata completeness (identifier, title, language, creator), NCX consistency, fonts/CSS, duplicate or broken internal links, EPUB validity (no epubcheck), mimetype first-entry rule, file size. The module is test-harness only; nothing I read calls it during production builds (I did not find a runtime caller; the `grep` for callers failed in the zsh shell so this is NOT VERIFIED).
Docstring line 4 refers to `apps.ingestion.pipeline.epub_book.create_epub`, which matches.

## 7. Findings

| # | Type | Sev | Finding | Evidence |
|---|---|---|---|---|
| 1 | bug/security | High | Jinja environment has autoescape off; all metadata, titles and headings are emitted raw into XHTML (ampersands, angle brackets produce invalid XHTML, or injection). | epub_builder.py:401-403; title_page.html:10-11; lesson.html:54-67; toc_hierarchical.html:24,36 |
| 2 | security | High (conditional) | Content HTML is not sanitised before it goes into EPUB, book.html and the served preview; preview is served as `text/html` from the API origin. Impact depends on CSP/origin (NOT READ). | dedication.html:27; lesson.html:69; html_book.py:94,107,117,135,178; access/views/preview_html.py:11 |
| 3 | design | High | Fonts are not embedded; EPUB has no stylesheet; Bengali rendering depends on the reader device having Kalpurush/SolaimanLipi/Noto. Kindle devices often lack these (they fall back to a default Bengali font or tofu). Bundled Noto TTF is only used for the cover PNG. | epub_builder.py (no font/CSS add_item), lesson.html:11-13 |
| 4 | design | Med | Missing OPF metadata: no identifier, publisher, series, contributor roles. Only title, language, one author. | epub_builder.py:405-407 |
| 5 | bug | Med | In-content images are never fetched or packaged into the EPUB; only the cover is. Any `<img>` in chapter HTML keeps its original `src` (broken offline, external request in readers). | epub_builder.py (no image handling beyond cover) |
| 6 | bug | Med | Docstring/placeholders mismatch: empty-source chapters are blanked (`content = ""`) while epub_book.py:28-31 says they render an "unavailable" notice. Chapters also are blank, which the audit then reports as blank pages (but the epub_book guard aborts the whole build if more than a third are placeholders, so at most about 33% are blank). | epub_builder.py:708-709; epub_book.py:24-31,280-294 |
| 7 | bug | Low | `main_content.html` uses `{{lesson_title}}` which is never passed (empty `<title>`); `info_page.html` uses undefined `book_info`; `cover_page.html`, `title_page.html`, `info_page.html` have hard-coded English `<title>` regardless of language; `toc.html` and `build_navigation_entries` are dead; `build_navigation_entries` has an always-identical conditional. | main_content.html:5; info_page.html:32; cover_page.html:5; epub_builder.py:822-827 |
| 8 | bug | Low | Cover file handle leaks (`open().read()` without close). Builder docstring says 600x900 but code makes 1200x1800. Redundant ratio condition. | epub_builder.py:456,477,213; epub_book.py:290 |
| 9 | design | Med | Page-type templates have HTML5-isms invalid in XHTML (`<meta charset>` without close, `<div ... />` self-closing, `<!DOCTYPE html>` plus `xmlns` mix). Whether ebooklib re-serialises and fixes this is NOT READ (library). Audit cannot detect it. | generated_cover.html:85,90; cover_page.html:4 |
| 10 | design | Med | Layout is inline-styled and fixed pixel margins (40-100 px) which waste space on e-ink/Kindle; `width:100%; height:100%` and `display:flex` on e-reader pages are poorly supported by Kindle. | title_page.html:8; dedication.html:9-18 |
| 11 | design | Med | Audit is shallow: no epubcheck, no XML well-formedness of pages, no metadata check, no image/cover check. Slot detection by file-name regex ties the audit to builder naming. | audit 91-101, section 6 |
| 12 | bug | Low | `safe_download_stem` does not limit length or strip control characters; the builder's `safe_epub_filename` does. Two different file-name sanitisers. | shared.py:108-110; epub_builder.py:368-384 |
| 13 | security/design | Med | Kindle send is synchronous, unthrottled (in this file), no size check, all files read to RAM, and one EPUB per address. A user with SEND_KINDLE can fan out email (to their own validated @kindle.com addresses only), so spam risk is bounded to addresses they stored; still no rate limit seen. Email sending errors reveal ops hints to end users. | assets.py:181,222-247,198-214 |
| 14 | design | Low | Kindle domain rule only `kindle.com` (not `free.kindle.com`); invalid stored addresses are silently skipped, so the user gets 400 with no pointer to which. | accounts/kindle.py:4; assets.py:38-47 |
| 15 | design | Med | GET download mutates state (marks asset FAILED, queues reprocess, flips book to NEEDS_REVIEW) on a missing file; a user with download rights can trigger it. | shared.py:174-234 |
| 16 | bug | Low | Read-once ledger is written in the GET of the HTML preview, before the response is delivered; a failed delivery (missing asset 404) happens after the access check but the record is written before `resolve_asset` (assets.py:131-139 vs 146-150), so a missing file can consume a user's single read. | assets.py:130-150 |
| 17 | design | Low | Single-tab "guard" for the preview is a client-side localStorage lock only; it is not a security control. | preview.py:1-132 |
| 18 | design | Low | Cache headers: downloads and preview lack no-store; helper exists but unused here. | shared.py:26-30; assets.py:151-155 |
| 19 | design | Low | `Book` fetched by slug without lifecycle filter in both views. | assets.py:121,162 |

## 8. Keep / change / drop for a rebuild

Keep
- The page vocabulary and spine order (cover, title, info, dedication, front, toc, content, back, nav); the nav-comprehensive/printed-toc-content-scoped rule; nested nav with a section node that has a real href; both nav.xhtml and NCX.
- Bengali/English label sets, the language detection by title idea (but make it an explicit metadata field), Bengali numerals for fallback labels.
- Cover generation fallback with Bengali shaping (HarfBuzz/raqm) and the mixed-script caution; cover input clean-up rules.
- Filename sanitiser with UTF-8 byte-length cap (safe_epub_filename).
- Permission model (owner or scope, global/book/category/author grants, read-once ledger), Kindle rule "validated @kindle.com list", per-address results with partial success reporting, "Brevo API cannot attach EPUB, use SMTP" knowledge.
- Audit idea as a post-build gate, extended.

Change
- Autoescape on; treat chapter HTML as a typed, sanitised fragment (allow-list sanitiser such as ammonia in Rust; strip scripts/events/iframes/external resources) before packaging, and only then call it safe.
- Embed fonts (OFL Noto Sans Bengali is licence-compatible) and a single shared stylesheet with `@font-face`; use relative units, no fixed pixel margins; avoid flex/100% height. Keep fonts out of the cover PNG path separately.
- Fetch and package in-content images with media types and manifest entries; rewrite `src`.
- Full OPF metadata: stable `dc:identifier` (book UUID), title, creator with roles, language, series via `belongs-to-collection`, publisher, date, modified.
- Valid XHTML generation (serialise via an XML writer, not string templates), then validate with epubcheck in CI.
- Build errors as typed results (no `print`); log with structured fields.
- Kindle: asynchronous job with retry, size limit check, rate limit/audit, outcome per address stored with history, reading the file as a stream where possible.
- Downloads: no-store/private headers, visibility filter before permission, side-effect-free GETs (recovery as an explicit admin/job action), read-once recorded only after the asset is actually served.
- Serve HTML preview (if kept) from a sandboxed, cookie-less origin with CSP, or stop serving book HTML directly and use a reader that renders sanitised content.

Drop
- `toc.html` (flat, unused), `build_navigation_entries` wrapper, `html_book.py` single-file HTML as a separate generator unless the web reader needs it (use one content model instead), client-side single-tab lock script, the 'pythonic' heuristics duplicated between epub_book.py and html_book.py (front/back mining runs twice with copy-pasted code).

## 9. Not read / unknown

- `apps/ingestion/services/normalization.py` (front/back inference, dedication normalisation, `extract_main_content_segments`, `plain_text_from_html`, `SHORT_RESIDUAL_MAIN_CONTENT_LENGTH`): NOT READ; so whether any sanitisation or XML-escaping is done upstream is unknown.
- `curated_export.py` (curated document -> legacy payload), `submissions_support/assets.py` (`resolve_generated_cover_path`, cover download and type checks), `submissions.py` (`queue_reprocess_book`): NOT READ.
- ebooklib / Jinja / Pillow library behaviour (identifier default, XHTML re-serialisation, CSS default, raqm availability): NOT READ.
- Callers that run `audit_epub_structure` in production; the regression script under tests: NOT READ; grep for callers failed (zsh glob) so not verified.
- URL routing, DRF throttling/settings, middleware/CSP/CORS/cookie settings, `Book`/`GeneratedAsset`/`UserBookKindleSend`/`PermissionGrant` models, `accounts` serializers for `kindle_emails` (length limit, validation timing), `PreviewAccessSession` reader flow (other views): NOT READ.
- Storage backend (S3 vs local) details, upload size limits, whether `GeneratedAssetType` has more types than cover/html/epub: NOT READ.
