# Book detail credits and source preview

Public and personal book details show every recorded contributor role, including
translators, editors and publishers. Public credit links filter by that exact
role. Personal credit, category and series links filter My Books, so readers can
continue browsing records that are private to their account.

Personal list cards, table rows and detail pages retain the selected My Books
view in contributor, category, series and book links. A direct personal detail
request includes a read-only `library_view`: existing All-feed members keep All,
while grant-only books use Granted. The detail return link uses the same view.
This preserves the existing distinction between All and Granted without moving
grant-only books into the All feed. Public metadata and directory links retain
their catalog URLs. Metadata links remain clickable above the card's title-link
overlay.

The detail page also shows retained publication metadata, dedication and nested
contents for digital books. The authenticated
`GET /api/v1/reading/books/{slug}/details/` endpoint requires current reading
permission. Anonymous visitors, revoked or spent read-once grants and quarantined
books cannot fetch the preview. Requesting it does not create a reading session
or consume a read-once opening. Physical books retain their separate reading log.
Its confirmed Reset action clears the form; the saved account log stays unchanged
until the reader chooses Save. Cancelling preserves the draft. Pending or
conflicted writes disable reset to protect unsaved work and revision checks.

The response contains plain text and omits raw HTML, source URL fields, chapter
bodies, source snapshots and storage references. Parsing is limited to 65,536
characters of each retained metadata input. Text previews are limited to 8,000 characters,
metadata to 50 fields and contents to 200 entries with a maximum depth of eight.
Any shortening is reported with `truncated` and a visible notice directing the
reader to the full book. Anonymous catalog metadata remains unchanged.

Regression coverage: `tests/backend/access/test_book_detail_preview.py`,
`tests/web/unit/book-detail-links.test.mjs` and
`tests/web/e2e/book-details.spec.mjs`. Physical reset has separate cancellation,
save and conflict coverage in `tests/web/e2e/physical-reading-reset.spec.mjs`.

Recorded verification on 19 October 2026:

- All nine preview backend tests passed with warnings treated as errors
  (`test-artifacts/foundation/reaudit-book-details-backend.log`). They cover owner
  and grant access, revoked/spent read-once access, quarantine, anonymous metadata,
  bounded nested contents and plain text without raw source fields.
- Four web unit tests passed for nested contents, public role links, personal
  filter links and bilingual publication guidance.
- Both book-detail journeys and both physical-reset journeys passed separately
  in Chromium, Android and iOS browser profiles. Each specification received fresh
  private fixtures. This is 12 project/journey combinations, with logs below
  `test-artifacts/foundation/reaudit-final-catalog-{chromium,android,ios}/`.
- Detail checks include all contributor credits, actual nested lists, protected
  preview access and a 320 px viewport with 200% text. At that size each fact value
  retains more than half the viewport width. The Android screenshot was inspected.
  Reset checks verify cancellation, unchanged persisted data before Save, actual
  cleared data after Save/reload and blocked reset during a pending or conflicted write.

These checks describe tested behavior. They do not establish subjective design
acceptance, physical-device coverage or a zero-bug guarantee.

Recorded private-navigation verification on 20 October 2026:

- All 26 personal-detail, private-library, library-view and catalog-filter backend
  checks passed with warnings treated as errors as part of a 30-test focused
  gate (`test-artifacts/foundation/reaudit-private-navigation-backend.log`). The
  four new detail cases verify grant-only fallback without changing All, owned
  and saved All defaults, revoked and other-account denial, private caching and
  exclusion of library context from public metadata.
- Both journeys in `tests/web/e2e/personal-entity-links.spec.mjs` passed in
  Chromium, WebKit, Android and iOS profiles with fresh private fixtures. These
  eight project/journey combinations cover six actual card/table metadata clicks,
  three direct grant-only detail credit links, the return link to Granted, list
  links retaining their view and direct owned details retaining All. Evidence is
  below `test-artifacts/foundation/reaudit-private-final-{chromium,webkit,android,ios}/`.
- Four detail-link unit tests passed again. The browser title assertion accepts
  the visible book link in both card headings and semantic table row headers;
  it still requires the filtered book to remain visible after every click.
