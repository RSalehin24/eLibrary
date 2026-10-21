# Protected reading increment

Book details, the source result and the managed book editor share the same
**Read Book / Continue Reading**, **Open HTML**, and permitted **Send to Kindle**
controls. Reading uses the existing prepared
EPUB session; preparation and file downloads are separate actions. The public
book page puts reading controls above metadata and descriptions, including on
phones. Physical books retain their reading-log workflow.

Authenticated electronic-book details also show the current account's saved
percentage, last opening and book-specific notes. The shared personal-notes
workspace supplies note details, revision-checked editing and explicit deletion.
`GET /api/v1/me/{bookmarks,highlights}/?book=<slug>` filters before pagination;
signed cursors bind the account, annotation kind and book filter. Notes remain
available to their author after reading access expires. Reading summaries never
create a reading session or consume read-once access.

Saved-position summaries show the prepared edition's chapter title, chapter
number and, for current chapter-relative positions, progress within that chapter.
They use the existing authorized session endpoint rather than fetching chapter
bodies. The access response's nullable `progress_session_id` identifies the
session that last saved the position; progress writes update this pointer.
Chapter labels and the direct resume action appear only when that pointer
matches the active session. Revoked or quarantined access withholds the pointer.
Launching another session retains the saved position's original pointer until
that reader saves a new position. Session responses include
`progress_matches_edition`, comparing prepared publication identities; a known
edition mismatch opens only an approximate overall percentage and reports that
the previous exact place could not be restored. Existing imported positions
without edition provenance still undergo the reader's structural validation.
Unknown legacy locations, absent provenance and positions outside the edition
retain the stored progress and show an honest fallback without displaying raw
CFI strings or inventing a chapter. The four book-specific note views retain
separate counts for notes, highlights, quotes and bookmarks.

**Open HTML** opens `/api/v1/reading/books/<slug>/html/` in a new tab with
`noopener noreferrer`. The access response includes `html_url` only when a
ready HTML file exists and the account has its existing preview entitlement.
Reading this metadata never consumes an opening. Opening the file uses the
same account lock and read-once policy as the retained preview, returns inline
HTML with private/no-store/noindex headers, and disables scripts, forms and
external requests with CSP. Missing files do not consume an opening. File
downloads remain separate attachments and require their existing entitlement.

The reader uses account-bound session UUIDs in `/reader/<uuid>/`. Session IDs
grant no access independently: Django checks the authenticated account,
expiry, book deletion, ownership or an active scoped reader grant on every
manifest, chapter, and progress request. Responses are private, no-store, and
noindex. The API does not return the legacy bearer token or storage reference.

## Access and concurrency

Reader launches and retained HTML-preview openings lock the account row inside
a transaction before checking and consuming read-once access. Concurrent
openings through either API cannot both succeed. The existing unique opening
record remains authoritative. Durable permissions and ownership retain their
existing behavior. A consumed read-once grant permits the current session until
expiry; it does not permit a new launch. Revocation blocks the current session.
Unprepared books return `409 reader_not_ready` without consuming the opening.

Downloads require download permission or ownership independently of reader
access. Personal library membership still represents ownership; the new UI
does not grant ownership as a side effect of opening or saving a book.

## Preparation and resources

The preparation service snapshots and hashes the EPUB outside reader requests.
Prepared publications are unique by SHA-256 checksum. Workers can reuse an
existing preparation and publish newly extracted directories atomically.
Replacement editions get distinct reader sessions; existing sessions retain
their previous prepared publication.

Current limits: 128 MiB compressed input, 256 MiB expanded data, 32 MiB per
resource, 2 MiB metadata XML, 10,000 archive entries, and compression ratio 100.
Preparation rejects traversal, absolute or duplicate paths, backslashes,
encrypted/special entries including symlinks, missing resources, external
manifest references, XML DTD/entity declarations, and invalid media types.
Only resources declared by the EPUB manifest are served. Chapters follow the
package spine; labels come from visible chapter headings with numbered fallback.
The package structure follows the [W3C EPUB specification](https://www.w3.org/TR/epub-33/).
Archive limits address [Python's documented decompression hazards](https://docs.python.org/3.12/library/zipfile.html#decompression-pitfalls).

Prepared XHTML runs in a sandboxed iframe with authored scripts disabled. Both
iframe and resource sandbox allow the parent's event handlers to operate in
WebKit; explicit `script-src 'none'` still blocks every authored script, inline
handler and JavaScript URL. CSP limits
styles, images and fonts to the current session's resource prefix, allows inline
styles/data images, and restricts embedding to the same origin. Preparation
removes automatic refresh redirects and base tags while preserving XML/SVG
markup. Prepared manifests carry a safety-policy version; older preparations
must be prepared again before opening. A browser regression confirms that an
embedded image cannot request unrelated authenticated routes. The development streaming fallback has matching
authorization and no-store headers. Django's public media route is limited to
profile images; generated and prepared book directories have no public route.
Production Nginx internal-file delivery is implemented and locally verified;
see [protected file delivery](protected-file-delivery.md).

An operator can prepare an existing ready EPUB using the installed environment:

```sh
PYTHONPATH=app/backend .venv/bin/python app/backend/manage.py prepare_reader_assets --asset <generated-asset-uuid>
```

This command needs the application's database/storage settings. A managed
preparation action and persisted worker/dispatch/recovery implementation are now
available; see [background jobs](background-jobs.md). The UI accurately identifies books
whose resources are not prepared.

Reader metadata has a separate `manifest_version` (currently 2). A contents/CFI
metadata upgrade does not change the safety-policy version or invalidate an
existing reading session. Managed assets expose `reader_update_available`; an
older prepared book offers **Update Reader Files** while staying readable.
Explicit preparation rebuilds its directory atomically and retains previous
files. Source regeneration and reader updates serialize through the book lock;
an unfinished source job blocks a competing update and supplies its progress link.

EPUB 3 `toc` navigation and EPUB 2 NCX retain their hierarchy, labels and local
section fragments. Only readable spine targets become buttons. External,
traversing, queried and missing targets are excluded. Contents parsing uses
bounded metadata, at most 2,000 entries and depth 8; unusable optional navigation
falls back to the spine. External DTD declarations are discarded without a
network request, while internal declarations/entities are rejected. The UI uses
nested semantic lists and ordinary buttons, with the existing dialog focus rules.

## Reading and progress

The reader provides scrolling, single-page and two-page views (one page on narrow
screens), actual page/chapter navigation, swipe and keyboard navigation, text-size
controls, fonts, themes, line spacing and reading width. Appearance preferences
are validated and persisted locally; unavailable storage has a visible notice.
Contents and full-book text search open accessible dialogs. Search parses inert
chapter text, supports Bengali, returns up to 100 exact matches and reports
unavailable chapters with an explicit retry.
Nested contents has separate keyboard-accessible expand/collapse controls.
Changing chapters expands the current chapter's ancestors; collapsing a branch
does not navigate. The same contents component serves account and local readers.

Fullscreen uses the document root. Browsers without native fullscreen offer a
viewport-filling focus mode. Immersive reading shows only the book: the header,
toolbar, page/chapter bars and save-status text are hidden. Escape or double-tap
returns to the controls; F also toggles fullscreen/focus. Text size and view
selection are grouped in Reading Settings. The
retained Ctrl/Command 1/2/3 and +/− shortcuts change theme/text size. Shortcuts do
not intercept editing or open dialogs. Reader settings explain these controls
in both interface languages.

Double taps toggle immersive fullscreen/focus; pinching resizes text and a
stationary two-finger tap cycles themes. Swipes are limited to paged views.
Gestures ignore links, controls, existing selections, cancellations and slow or
vertical drags. Synthetic touch/mouse follow-up events cannot toggle twice.
Buttons, keyboard controls and text selection remain available.

Account-specific progress debounces writes by two seconds and saves during sustained
reading every fifteen seconds. Writes are serialized; newer pending positions
replace obsolete pending positions. Failures remain visible and offer a retry.
The launch command is not automatically replayed. Unload saving is best effort.
The persisted locator stores chapter index and measured scroll fraction. During
resizing and appearance changes, the active document also keeps its visible text
block in view. Ordinary progress remains a chapter/fraction locator; explicit
bookmarks additionally capture a persistent text anchor as described below.

## Annotations

New text bookmarks store the chapter, UTF-16 offset and a short exact quotation
in the existing bounded location field. They reuse the reader's text-range
machinery, which counts text through highlight wrappers. Restoration verifies
the stored quotation before navigating and reports a mismatch without changing
the original bookmark. These anchors survive reopening with different font
sizes, reading views and viewport widths. Image-only positions or places where
no text anchor can be captured retain a chapter/fraction bookmark and show an
explicit approximate-position notice. Existing chapter/fraction and imported
CFI bookmarks continue to work. All bookmarks use an edition-specific database
uniqueness constraint. Repeating a save returns the same record without
overwriting an existing note. Highlights and quotes use validated text offsets,
plain text, colors, tags, and notes. Both are tied to the prepared publication,
so a replacement EPUB does not display marks from another edition. The reader
can create and revisit bookmarks, select text, save a highlight/quote, and restore
its marks after reloading. Legacy CFI values remain stored and readable as notes;
the reader now resolves supported legacy text points/ranges and element points
into the current document. Image and other element points use the resolved
element's geometry when a collapsed range has no text rectangle. Hidden or
missing targets report a restoration failure. The bounded parser follows [EPUB CFI's structural and UTF-16 offset rules](https://w3c.github.io/epub-specs/epub33/epubcfi/),
checks spine/item identity and element/text assertions, and rejects malformed
syntax and out-of-range targets. Image/video spatial points resolve against the
rendered media, accounting for object-fit letterboxing, borders and padding.
Audio/video temporal points wait for metadata and an actual settled seek without
starting playback. Both ends of a media range must identify the same element and
have valid ordered offsets. Unknown geometry, unavailable media, rejected seeks
and stale identities produce the bilingual restoration notice; original CFIs
remain intact. Pending restoration survives reader rerenders and suppresses
progress writes until it settles. The restored point stays at its viewport
position through text and control reflow. A legacy highlight
is painted only when the resolved text matches the original quotation. Its
original CFI and note are retained. A missing/stale target shows an explicit
bilingual notice rather than marking different text. Existing chapter/fraction
bookmarks continue to work, and original package-relative reading paths and
fragments open their actual chapter; an absent fragment identifier shows the
restoration notice. Annotations from a different prepared
publication remain excluded by the existing edition filter.

Authorized embedded audio/video uses native controls with autoplay disabled.
The reader's CSP permits media only under that account-bound session's resource
prefix, and permission is rechecked for each resource request. Development media
responses support single byte ranges, open-ended and suffix ranges, and correct
206/416 responses so native seeking works. Production retains protected Nginx
delivery. Unsupported multiple ranges use the full response, in accordance with
[HTTP range semantics](https://www.rfc-editor.org/rfc/rfc9110.html#name-range).
Reader keyboard navigation does not intercept native audio/video controls.

Personal notes use account-filtered, signed cursor collections with short
previews and separate full details. They remain available to their author after
reader access expires or is revoked. Updating notes locks the record and checks
its revision; simultaneous editors receive one success and one `409` conflict.
Deletion requires an explicit user action. All mutations enforce session CSRF.

Every personal bookmark, highlight, note and quote has an Open in Reader action.
The launch endpoint checks the annotation's owner and current book access, then
opens its retained prepared edition instead of interpreting the saved location
against a replacement EPUB. Legacy annotations without an edition use the current
edition with structural/text checks. Missing or obsolete prepared resources return
`reader_not_ready`; the annotation is kept. Session-scoped detail GET endpoints
verify that requested annotations belong to that account, book and edition before
the server renders the exact target. Highlights verify their original quotation
before selecting text. Launching does not overwrite saved reading progress.
Painting saved highlights preserves the verified active selection, including when
annotations arrive after an exact passage has already opened.
An active session for that edition is reused, including a currently valid
Read Once session; this never grants another opening after that session expires.
The note editor disables navigation while edits are unsaved or a mutation is pending.
Ctrl/Command + Enter saves notes in both the personal editor and reader selection
form; pending saves cannot be resubmitted with the shortcut.

Catalog and My Books cards and table rows include save/remove actions and the
permitted Kindle composer link. One private `GET /api/v1/me/book-controls/`
request takes up to 100 validated repeated `slugs` parameters. It returns only
visible books, with saved state and Kindle availability computed from current
ownership/scoped grants, quarantine state and an available ready EPUB. Paper
books never show Kindle actions. The existing save mutation and query cache are
shared with detail pages; a list batch seeds save state without a read per row.
Removing a saved book refreshes My Books so saved-only rows disappear immediately.

## Verification and remaining scope

The counts below describe earlier increments. Current reader, cover, bilingual
detail/notes and full-suite evidence is recorded at the top of
[the handoff](../implementation-handoff.md). The original-app comparison and
remaining parity work are explicit in [feature comparison](../operations/feature-parity.md).

The new reader backend tests plus seven retained access cases passed 40 tests;
after adding annotations, resource isolation, and profile/security, the complete
selected platform suite now passes 464, including 426 new cases and retained
authentication, access, and processing cases.
The generated access migrations apply on an empty PostgreSQL database and on
the isolated preview database. mypy, Ruff, TypeScript, ESLint, and production
build passed. All 82 Chromium journeys passed against the standalone build on
2026-10-14, including launch, CSP script isolation, chapter links, appearance,
failed progress saves with explicit retry, and widths 320 through 1920 pixels.
Phone and desktop reader screenshots were visually inspected. These checks
also caught and now cover the resource proxy path and a chapter loading before
React attached its scroll listener. The new annotation journey covers bookmark
creation, Bengali selection, highlight persistence, stale-note conflicts,
retained drafts, successful edits, and deletion. The PWA increment adds separate
offline/update journeys; see [PWA verification](pwa.md).

Profile/security is available; see [account settings](account-settings.md).
The asynchronous Kindle workflow is implemented; see [delivery](kindle-delivery.md).
[Password-link confirmation/setup](password-links.md) and
[queued invitation/reset requests](account-mail.md) are available. Live
broker/device delivery and profile-image editing,
live queued EPUB preparation, Nginx acceleration,
physical devices, field web vitals, cold-cache recovery, and capacity acceptance
remain unverified. This increment does not complete the reader phase.

## WebKit chapter observation

WebKit 27.2 suppresses document scroll/selection callbacks inside chapters whose
sandbox disallows scripts. The current CSP/sandbox combination permits parent
callbacks while still prohibiting authored scripts; regressions inject authored
scripts and inline handlers and verify that neither executes. The parent also
observes changes every 200 ms while visible. Resize geometry changes are excluded
until the saved text anchor is restored. Progress flushes capture the actual
position synchronously, including before an accepted PWA update. Navigation from
an internal chapter link reconciles the iframe URL with the reader's chapter
state. Dialog closure explicitly restores the triggering button's focus, which
Safari does not establish on pointer activation. Unit and browser regressions
cover observation cleanup, text selection, saving, resizing, updates, and focus.

After a progress write fails, new reading positions remain queued while the
failure and retry control stay visible. Debounced/periodic saves pause until an
explicit retry succeeds; the unload handler can still attempt the latest
position. Concurrent flushes share the existing request, and a failed older
request cannot replace a newer queued position. Unit tests and repeated Firefox
journeys cover the failure, continued reading, and latest-position retry.
