# 14d — notes: backend/access test_access_02 (250), 03 (289), 04 (94), 05_notes (348), __init__ (0)

Status: DRAFT (research evidence; read-only record)

## Preview HTML normalisation (test_access_02)  — function `normalize_preview_book_sections(soup, dedication_html=None) -> bool(updated)`; operates on the generated `book.html` DOM (BeautifulSoup html.parser)
- [AX1] given `div.dedication-section` with h2.dedication-title "উৎসর্গ" and content with redundant "উৎসর্গ", "উৎসর্গ :" paragraphs, then updated True and `div.dedication-content` text starts with the real text "পাঠক, আপনাকে" (redundant label paragraphs stripped) — test_access_02.py:33
- [AX2] no dedication section but `dedication_html="<p>উৎসর্গ : পাঠক, আপনাকে…</p>"` supplied (from book data) -> section inserted before main-content; text starts "পাঠক, আপনাকে" — :64
- [AX3] no `.main-content` at all (only container/book-header/toc-section) + dedication_html -> `div.dedication-section > div.dedication-content` still inserted — :90
- [AX4] standard Bengali dedication keeps title "উৎসর্গ"; content retained; returns updated True — :119
- [AX5] English dedication content (paragraph "Dedication" + "For everyone who kept reading.") -> heading becomes "Dedication", the repeated "Dedication" paragraph removed from content, text kept — :151
- [AX6] leading h2 sections in main-content before the first real chapter ("সহস্রাব্দ সংস্করণের কথা", "প্রারম্ভ কথন", before "অধ্যায় ১") are moved into `h2.front-section-title` blocks and removed from `.main-content`; "অধ্যায় ১" content stays — :184
- [AX7] missing stored file (GeneratedAsset.file path unlinked): GET download/cover -> 404 detail "This file is no longer available in storage. Please regenerate the book."; asset.status becomes FAILED, asset.file.name "" ; book.state "needs_review" and review_state "needs_review" (self-heal on missing file) — :224

## Reader state, grants, scopes (test_access_03)
- [AX8] reading-session & bookmarks endpoints (`/api/access/books/<slug>/reading-session/`, `/bookmarks/`) GET -> 403 without reader access; with READ_DURABLE book grant POST reading-session {last_location:"chapter-1", progress_percent:12} -> 200; POST bookmarks {location,label,note} -> 201 — test_access_03.py:35
- [AX9] preview session token: PreviewAccessSession(book) .token; GET `/api/access/reader/<token>/html/` (no login needed) 200; HTML inlines stale relative cover (`book_image.hpg`) as data:image/jpeg;base64 — :61
- [AX10] preview HTML promotes leading front matter: "অনুবাদ: ..." and "প্রথম প্রকাশ: ..." extracted into a `book-info-section` and removed from `<div class="main-content">`; "ভূমিকা" stays — :98
- [AX11] only superadmin can manage grants: non-super GET /api/access/references/ -> 403; superadmin gets `account_scopes` and `scoped_scopes` lists of {value,...}; `admin:full_control` NOT in account_scopes; `access:manage` NOT in scoped_scopes; POST /api/access/grants/ {user, book, scope:DOWNLOAD_FILE, notes} -> 201; DELETE /api/access/grants/<id>/ -> 204 — :144
- [AX12] superadmin cannot create or delete a scoped grant for themselves: POST grant with user=self -> 403; deleting a grant whose user is self -> 403; for another user 201 — :179
- [AX13] category- and writer-scoped grants: grant with `category` applies to books in the category (BookCategory); grant with `contributor` applies to books with BookContributor role AUTHOR; `user_has_scope(user, [scope], book=...)` true only for matching books — :217
- [AX14] catalog endpoints require authentication: anonymous GET /api/catalog/books/ and /api/catalog/books/<slug>/ -> 403 (not 401) — :238
- [AX15] BookSource: unique per book (second BookSource for same book -> IntegrityError; one source per book); book detail `source_urls` and `source_records` are [] without VIEW_SOURCE_RECORDS grant; with grant -> `source_urls[0]` is URL, `source_records[0].url`; superadmin sees them automatically — :249

## Reader token endpoints (test_access_04)
- [AX16] reader flow: launch -> manifest (`epub_download_url`, `reading_session_url`, `bookmarks_url`); epub is served as unzipped resources under `epub_download_url`: `META-INF/container.xml` (contains "OEBPS/content.opf") and `OEBPS/text/chapter-1.xhtml` ("Seeded EPUB chapter one for reader coverage."); GET/POST reading-session {last_location:"chapter-2", progress_percent:47} 200 echoing last_location; POST bookmarks 201; GET list len 1; DELETE `/api/access/reader/<token>/bookmarks/<id>/` 204. Note PREVIEW_HTML grant alone suffices for reader-launch — test_access_04.py:35

## Notes (test_access_05_notes): models Highlight(user, book, cfi_range, text, color, kind), Bookmark(user, book, location, label), HighlightKind {HIGHLIGHT="highlight", QUOTE="quote"}
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
