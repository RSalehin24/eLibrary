# Library

Status: DRAFT

**Purpose**: the one place to browse, search and filter books, with My Books and Sent to Kindle as scope chips. Replaces the legacy Home, Library, My Books, Kindle-sent and six facet pages.
**Primary action**: open a book. Signed-in readers with progress also get Continue reading.
**Routes**: `/library` and `/library?...` (public), `?scope=mine|kindle` (signed in). **Service owner**: catalog (progress row: reader). **Requirements**: REQ-WEB-015, 022; REQ-CAT-008, 009, 014..017, 025, 026, 033.

## Data

`GET /books` (q, facets, sort, keyset `after`), `GET /browse/{facet}` and `/browse/{facet}/{id}`, `GET /books/{slug}/cover`, `GET /shelf`, `PUT/DELETE /shelf/{slug}`, `GET/POST/DELETE /saved-filters`; reader `GET /me/progress` for the Continue row ([catalog](../../07-contracts/http/catalog.md), [reader](../../07-contracts/http/reader.md)). Anonymous calls carry no cookie and the page is server-rendered.

## Structure

1. Top app bar with search field (the query lives in the URL).
2. Scope chips: All, My Books, Sent to Kindle (the last two only when signed in; for anonymous they are hidden, a direct URL goes to sign-in and returns).
3. Facet tab bar (Material tabs): Books, Categories, Series, Writers, Translators and editors, Publishers. Tabs open the facet index; choosing an entry shows that facet's books in the same list. One component serves all facets.
4. Toolbar: sort (relevance, title with Bengali collation, recent), card/list toggle (button toggle), Filters button, saved filters menu (signed in).
5. Results as cover cards or list rows; "Load more" keyset paging (no page-number jumps); result count equals the facet count.
6. Continue reading row on top for signed-in users with progress (hidden when empty).

Filters and sort live in the URL; a saved filter stores the query and reapplies it identically. One filter sheet holds writer, translator, editor, publisher, series, category, language: AND across facets, OR within one. A card shows cover, title, writers; a shelf toggle (signed in) and a lock-free "available" signal only; never preview text.

## States

| State | Behaviour |
|---|---|
| Loading | skeleton cards sized to final content (no layout shift); chips and toolbar stay |
| Empty | "No books found" with the active filters listed as removable chips and a Clear filters button; in My Books: "Nothing here yet, add books from the library"; in Sent to Kindle: "Nothing sent yet" |
| Ready | grid or list |
| Error | inline banner with Retry; toolbar stays usable |
| Forbidden | scope chip target without `kindle`: inline "not allowed" with reason; session stays |
| NotFound | unknown facet entry: "This writer or series does not exist" with link to the facet index |
| Offline | cached page stays, banner "offline", retry with backoff |

## Layout

| Class | Layout |
|---|---|
| compact | 2-column cover grid or one-column list; filters in a modal bottom sheet; bottom nav bar |
| medium | 3-4 columns; filters in a side sheet; rail |
| expanded | 4-6 columns; persistent side filter panel; rail |
| large | 5-8 columns; persistent panel; permanent drawer; max content width |

## Actions

Search; choose scope; switch facet; sort; toggle view; open filter sheet; save filter (name, duplicate name gives a typed message, limit shown); delete saved filter; add or remove from My Books (optimistic, rolled back on failure with snackbar); open book.

## Copy keys

| Key | en | bn |
|---|---|---|
| `ux.library.title` | Library | লাইব্রেরি |
| `ux.library.search` | Search books, writers, series | বই, লেখক বা সিরিজ খুঁজুন |
| `ux.library.scope.all` | All | সব |
| `ux.library.scope.mine` | My Books | আমার বই |
| `ux.library.scope.kindle` | Sent to Kindle | কিন্ডলে পাঠানো |
| `ux.library.filters` | Filters | ফিল্টার |
| `ux.library.empty` | No books found | কোনো বই পাওয়া যায়নি |
| `ux.library.clear` | Clear filters | ফিল্টার মুছুন |
| `ux.library.continue` | Continue reading | পড়া চালিয়ে যান |
| `ux.library.saveFilter` | Save this filter | ফিল্টারটি সংরক্ষণ করুন |
| `ux.library.loadMore` | Show more | আরও দেখুন |

Analytics: none.

## SEO and rendering

`/library` and facet indexes are server-rendered with title, canonical URL and structured metadata (metadata only). Parameterised URLs are `noindex` with a canonical to `/library` (provisional).

## Accessibility

Result list is a labelled list; the count and "n more loaded" are polite live-region updates; filter sheet is a focus-trapped dialog with Esc; chips are a toggle group with `aria-pressed`; cards are one link target with the shelf toggle as a separate labelled button (48 px).

## Open

U-5 (no cross-book list of Kindle requests in the catalog contract).
