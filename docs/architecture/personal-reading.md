# Personal library and paper reading

`/my-books/` defaults to a combined list of owned, saved and previously read
books. Owned, saved, recent and granted tabs remain available. Book actions expose
Add to My Books / Remove from My Books and a direct link to the personal list.
Saving a book records an idempotent personal preference; it creates neither
ownership nor permissions. Private metadata requires ownership or current reader
scope. Expired or revoked grants remove private books from the saved and granted
feeds. Cursors bind to the account, view, search, and ordering.

Published editions link only published, approved, undeleted siblings in the same
explicit edition group. Ungrouped books have no siblings. The full editions list
uses bounded pagination and ordinary server-rendered links.

Paper books expose publisher, decimal price, binding, and compilation metadata.
Their private reading log persists status, current and total pages, dates, rating,
and notes per account. Revision conflicts preserve the draft. Paper records do
not offer EPUB launches or downloads. Recent reading combines digital progress
and paper logs by actual activity time.

Profile images accept one PNG, JPEG, or WebP frame, up to 5 MiB and 2048 pixels per
side. Pillow produces a metadata-free PNG no larger than 512 pixels. Storage uses
random names; the authenticated API serves only the current account's image with
private, uncached responses. Updates use the profile revision. Replaced files are
removed after commit; failed persistence cleans the newly stored object.

Coverage includes visibility and expired grants, cursor isolation, save replay,
revision conflicts, paper validation, private image delivery and normalization,
CSRF, persistence failures, public edition isolation, and responsive browser
journeys. Migration `catalog.0026_personal_reading` creates the two personal models.
