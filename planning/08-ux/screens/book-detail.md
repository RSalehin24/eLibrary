# Book detail

Status: DRAFT

**Purpose**: understand one book and act on it: read, preview, download, send to Kindle; for catalog managers also edit metadata and decide on versions.
**Primary action**: Read (signed in with `read`) or Sign in to read (visitor).
**Routes**: `/books/:slug` with `?tab=overview|metadata|files`. **Auth**: anonymous for Overview and Metadata (metadata only); Files needs sign-in; edit controls need `manage_catalog`. **Service owner**: catalog (Read: reader). **Requirements**: REQ-WEB-016, 022; REQ-CAT-002, 005, 006, 019..023, 029; REQ-RDR-010.

## Data

`GET /books/{slug}`, `/books/{slug}/cover`, `GET /books/{slug}/preview` (preview scope), `GET /books/{slug}/files`, `GET /books/{slug}/files/epub`, `POST /books/{slug}/kindle`, `GET /books/{slug}/kindle-requests`, `PUT/DELETE /shelf/{slug}`; for managers `GET /manage/books/{id}`, `PATCH /manage/books/{id}/metadata` (`If-Match`), `GET .../metadata-history`, `GET .../versions`, `POST .../archive`, `DELETE /manage/books/{id}` (scope **OPEN O-4**); reader `POST /books/{slug}/open` ([reader contract](../../07-contracts/http/reader.md)). Manage endpoints are keyed by id, public ones by slug (**OPEN U-9**).

## Tabs

| Tab | Content | Who |
|---|---|---|
| Overview | cover, title, credits with roles, series, categories, publisher, language, summary; honest read-limit notice; for signed-in with `preview`: contents (TOC) and the preview excerpt (marked noindex, never in the server-rendered HTML for visitors); shelf toggle | all; excerpt signed-in |
| Metadata | read-only structured metadata and source-owned versus operator-owned fields; for `manage_catalog`: edit form, version list with state (published, archived), metadata history, unpublish (archive), delete (confirm naming the book) | all read; managers edit |
| Files | available formats and sizes; Download (needs `download`); Send to Kindle (needs `kindle`) with address select and delivery status (queued, sent, failed with reason); read-once and grant hints | signed in; actions by scope |

Actions that the capability set denies are hidden, except where knowing why helps: Read for a signed-in user without `read` shows a disabled control with "ask an administrator" ([states](states.md)).

## States

| State | Behaviour |
|---|---|
| Loading | skeleton for cover, title, credits |
| Empty | Files: "No files available"; Overview with no preview: the excerpt section is omitted, not an error |
| Ready | as above |
| Error | inline banner and Retry; tabs stay |
| Forbidden | Read: "You do not have access to read this book" with the typed reason (no grant, read-once used, not published); Files for visitor: sign-in prompt (401 path keeps the route) |
| NotFound | unknown, unpublished or deleted slug: NotFound page with a link to Library; a renamed slug is redirected |
| Offline | banner; actions disabled with reason |

Stale edit (`stale_revision`): dialog shows the server value next to the user's change, user chooses to reapply; never a silent merge. Conflict and `no_credit` on save show inline error text.

## Layout

| Class | Layout |
|---|---|
| compact | one column; cover on top, tabs below; sticky bottom action bar with the primary action |
| medium | cover beside title and summary; one column |
| expanded | two panes: cover, actions and facts beside the tab content (manager edit form in the main pane) |
| large | same with a capped measure |

## Read-limit notice

One short text, always on Overview for signed-in readers: "Reading shows the whole book in your browser, so it can be copied. Access is limited to approved accounts and logged." (REQ-RDR-010; no DRM claim).

## Copy keys

| Key | en | bn |
|---|---|---|
| `ux.book.tab.overview` | Overview | সারসংক্ষেপ |
| `ux.book.tab.metadata` | Details | বিবরণ |
| `ux.book.tab.files` | Files | ফাইল |
| `ux.book.read` | Read | পড়ুন |
| `ux.book.signInToRead` | Sign in to read | পড়তে সাইন ইন করুন |
| `ux.book.preview` | Preview | প্রিভিউ |
| `ux.book.download` | Download EPUB | EPUB ডাউনলোড |
| `ux.book.kindle` | Send to Kindle | কিন্ডলে পাঠান |
| `ux.book.readLimit` | Reading shows the whole book in your browser, so it can be copied. Access is limited and logged. | পড়ার সময় পুরো বইটি আপনার ব্রাউজারে দেখানো হয়, তাই কপি করা সম্ভব। প্রবেশাধিকার সীমিত ও নথিভুক্ত। |
| `ux.book.archive` | Archive | আর্কাইভ |
| `ux.book.delete.confirm` | Delete “{title}”? | “{title}” মুছে ফেলবেন? |

Analytics: none.

## SEO

Overview and Metadata are server-rendered: title, canonical URL, meta description from the summary, structured book metadata (metadata only). Preview text is fetched client-side after sign-in and marked noindex (D-34, D-09).

## Accessibility

Tabs follow the ARIA tabs pattern with the tab in the URL; cover has alt text of the title; status chips carry text; delivery-status changes are polite live-region updates; confirm dialogs name the object and focus the safe action.

## Open

U-9 (manage endpoints keyed by id; web needs slug to id), O-4 (scope for delete and CSV export).
