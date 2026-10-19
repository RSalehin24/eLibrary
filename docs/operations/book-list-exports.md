# Book lists, exports and compatibility routes

The catalog, My Books and management lists expose CSV/PDF downloads for the
complete filtered result. Exports use the same authorization and filters as the
list; changing the list page does not truncate an export. CSV values that could
be interpreted as spreadsheet formulas are quoted as text. Timestamps use Dhaka
time in 12-hour notation.

Physical inventory is at `/physical-books/`. It has contributor/category/series,
publisher, binding and language filters, plus grouped XLSX/PDF exports. XLSX can
group by category, publisher, binding, language or contributor; books belonging
to several categories appear in each relevant sheet. Sheet names are sanitized
and made unique after Excel's 31-character limit. Every cell is explicit text,
so a title cannot become an executable formula. Physical viewing grants remain
scoped to their book/category/writer; a revoked grant stops future exports.

The supplied Linux API image contains the bundled Bengali font and RAQM shaping.
Mixed Bengali/Latin PDF cells use separate script fonts to preserve both sets of
glyphs. Hosts without shaping return an actionable error instead of a broken PDF.
**Print / Save as PDF** opens the entire filtered list in a new tab, using native
browser text shaping; choose the browser's Print menu and Save as PDF. This path
also works on the development Mac without adding dependencies.

## Previous bookmarks

| Previous route | Current equivalent |
| --- | --- |
| `/home`, `/library` | `/catalog/`, preserving catalog filters |
| `/writers`, `/translators`, `/editors`, `/compilers`, `/publishers` | `/contributors/` with the corresponding role |
| `/manual-books` | `/physical-books/` |
| `/created-books` | `/my-books/` |
| `/kindle-sent` | `/kindle/` |
| `/access` | `/manage/users-access/` |
| `/two-factor-setup` | `/profile/` |
| `/processing`, `/processing-catalog-books` | `/manage/sources/` |
| `/processing-automation` | `/manage/automations/` |
| `/create`, `/processing-my-requests` | `/manage/sources/?status=unlinked` |
| `/queue` | `/manage/jobs/` |
| `/on-hold`, `/processing-failed-requests`, `/processing-duplicate-requests` | `/manage/jobs/?view=recovery` |
| `/incomplete`, `/processing-incomplete-check` | `/manage/unfinished/` |
| `/reprocessing` | `/manage/jobs/?kind=process_source` |
| `/multipage-toc`, `/processing-multi-page-toc` | `/manage/jobs/?kind=process_source&layout=multi_page` |
| `/reader?slug=...` | The book's personal detail page, then its authorized Read action |

Current canonical routes retain their meaning. In particular `/catalog/` is the
public book catalog; the old source-catalog role is available through the
processing aliases above. Unknown routes remain 404. Redirects do not copy
external `next`, manifest or launch URLs. Destination pages continue to enforce
their own login, two-step setup and scoped permissions. Legacy reader links
cannot automatically consume a one-time reading grant.

Multi-page contents aliases select the corresponding source-layout filter in
the processing list. Source layout comes from collected document evidence;
books that have not yet been inspected stay unclassified.
