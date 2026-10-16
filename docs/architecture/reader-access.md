# Protected reading increment

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

Prepared XHTML runs in a sandboxed iframe with scripts disabled. CSP limits
styles, images and fonts to the current session's resource prefix, allows inline
styles/data images, and restricts embedding to the same origin. Preparation
removes automatic refresh redirects and base tags while preserving XML/SVG
markup. Prepared manifests carry a safety-policy version; older preparations
must be prepared again before opening. A browser regression confirms that an
embedded image cannot request unrelated authenticated routes. The development streaming fallback has matching
authorization and no-store headers. Django's public media route is limited to
profile images; generated and prepared book directories have no public route.
Production Nginx internal-file delivery still needs implementation.

An operator can prepare an existing ready EPUB using the installed environment:

```sh
PYTHONPATH=app/backend .venv/bin/python app/backend/manage.py prepare_reader_assets --asset <generated-asset-uuid>
```

This command needs the application's database/storage settings. A managed
preparation action and persisted worker/dispatch/recovery implementation are now
available; see [background jobs](background-jobs.md). Real RabbitMQ interruption
verification still awaits image approval. The UI accurately identifies books
whose resources are not prepared.

## Reading and progress

The current screen provides chapter navigation, a keyboard accessible contents
dialog, appearance controls, protected EPUB download, and account-specific
progress. It debounces progress writes by two seconds and saves during sustained
reading every fifteen seconds. Writes are serialized; newer pending positions
replace obsolete pending positions. Failures remain visible and offer a retry.
The launch command is not automatically replayed. Unload saving is best effort.
The persisted locator stores chapter index and measured scroll fraction. During
resizing and appearance changes, the active document also keeps its visible text
block in view. Exact persisted text anchors remain later reader work.

## Annotations

Bookmarks store normalized chapter/scroll positions and use an edition-specific
database uniqueness constraint. Repeating a save returns the same record without
overwriting an existing note. Highlights and quotes use validated text offsets,
plain text, colors, tags, and notes. Both are tied to the prepared publication,
so a replacement EPUB does not display marks from another edition. The reader
can create and revisit bookmarks, select text, save a highlight/quote, and restore
its marks after reloading. Legacy CFI values remain stored and readable as notes;
the new renderer does not treat them as validated text offsets.

Personal notes use account-filtered, signed cursor collections with short
previews and separate full details. They remain available to their author after
reader access expires or is revoked. Updating notes locks the record and checks
its revision; simultaneous editors receive one success and one `409` conflict.
Deletion requires an explicit user action. All mutations enforce session CSRF.

## Verification and remaining scope

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
sandbox disallows scripts. The parent page observes changes every 200 ms while
visible, without enabling authored scripts. Resize geometry changes are excluded
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
