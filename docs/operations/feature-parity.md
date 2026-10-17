# Feature comparison and acceptance

This comparison covers the retained React application in `app/frontend` and the
current Next.js application in `app/web`. Passing tests demonstrates the checked
behavior. It does not establish subjective design acceptance or guarantee that
the application has no bugs.

## Implemented workflows

| Earlier workflow | Current surface and checked behavior |
| --- | --- |
| Catalog search and metadata | Public catalog, author/category/series directories, role filters, saved details, collections and edition links. Draft metadata stays private. Managers have visible All Books links, cards and related-book navigation. |
| Source book creation | `/manage/sources/`: Fetch All, bounded fetching, selectable rows, single/bulk creation, Process All, visible progress and job controls. Automated creation uses one configured website. |
| Automation | Schedule creation/editing, catalog scope, full/limited processing, time zone and revision-checked commands. |
| Manual books and EPUBs | Direct manual-entry action, digital/paper records, EPUB validation/upload, preparation and publication without a manual-review gate. |
| Source unfinished books | Dedicated `/manage/unfinished/` list and refresh of the source website's unfinished category. Extraction/export failures remain separate processing problems. |
| Automatic source publication | Compare fetched page/chapter evidence, collected text and actual HTML/EPUB text. Prepare reader resources before publishing automatically. Missing or failed source content blocks publication; previous unverified exports require regeneration. |
| Regeneration and removal | Visible bilingual managed-editor actions, revision/permission checks, confirmation, source rebuilding, explicit recovery and retained files/reader records. Removal hides the record without deleting its data. |
| Generated files | Actual permission-checked EPUB/HTML downloads, file availability, preparation status and short-content warnings. HTML preview opens a separate tab. |
| Book covers | Real protected cover assets on cards, details, source results and editors; image validation and title/author fallback. |
| Reading and Kindle actions | Shared Read/Continue, Open HTML and Send to Kindle actions on permitted book/source/editor surfaces. Recipient selection, request history and cancellation retain their permission boundaries. |
| EPUB reader | Scrolling/single/spread views, text size, font/theme/spacing/width, nested EPUB 3/NCX contents, full-book search, page/chapter navigation, keyboard/swipe/pinch/tap gestures, fullscreen/focus and persistent appearance. Older prepared books have an explicit reader-file update action that preserves current access. |
| Personal reading data | Saved progress, bookmarks, highlights, quotes and revision-checked private notes. Electronic-book details show progress, last opening and book-specific notes. Paper books retain separate logs. |
| My Books | Visible Add/Remove actions and a combined default list of owned, saved and previously read books. Separate saved/owned/recent/granted tabs remain available. Adding a book never grants reading rights. |
| Original reader locations | Package-relative paths/fragments and supported text CFI bookmarks/highlights resolve into the current reader. Spine identity, text assertions and quotation matching reject stale targets while retaining original notes. |
| Accounts and access | Profile/photo/password, conditional TOTP challenge, required setup, invitation/reset workflows, scoped grants and account isolation. |
| Bengali and English | Shared language preference across public, account, admin and reader screens; localized interface dates/numbers. Book text, titles and author names retain their original language. |
| Installation and updates | Manifest/install simulation, offline notice, private-cache exclusion and update guards for unfinished forms/reading position. Update notices stay available in admin and normal reading; immersive reading shows only book content. |

The original book-detail comparison uses
`app/frontend/src/features/book-detail/components/BookDetailHero.jsx`,
`BookReaderSections.jsx` and the action hooks. Reader comparison uses
`app/frontend/public/epub-reader/static/js/reader/reader-application.js` and
`app/frontend/public/epub-reader/static/js/reader/utils/gesture-handlers.js`.

## Remaining validation and content limits

- The identified regenerate/removal, nested-contents, gesture and text-CFI gaps
  are implemented. The current new-reader progress format remains chapter/fraction;
  live layout changes preserve the visible text. Stale CFIs and nontext media
  CFIs are retained as data and reported when they cannot be resolved.
- Devdas regeneration now embeds its real cover in the EPUB. The short Shakespeare
  draft retains its earlier exported files; its display cover alone is recovered.
- The short Shakespeare draft remains flagged: 0 collected chapters and 524
  source characters. Successful file generation does not certify a complete book.

## Acceptance boundary

Only simulators are available. Physical-device behavior, external Kindle arrival,
a real staging/fresh host and independent-machine capacity acceptance cannot be
inferred from local browser or Docker checks. No external mail is authorized or
required for these checks; delivery workers remain stopped. The user explicitly
authorized automatic publication after successful source checks on 17 October.
Synthetic fixtures remain restricted to the isolated reference database.

Current verification counts and evidence are recorded at the top of
[the implementation handoff](../implementation-handoff.md). Private fixtures and
screenshots stay in ignored `test-artifacts/foundation/`; never print credentials
or seed synthetic fixtures into `bangla_library_preview`.
