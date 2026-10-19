# Book detail credits and source preview

Public and personal book details show every recorded contributor role, including
translators, editors and publishers. Public credit links filter by that exact
role. Personal credit, category and series links filter My Books, so readers can
continue browsing records that are private to their account.

The detail page also shows retained publication metadata, dedication and nested
contents for digital books. The authenticated
`GET /api/v1/reading/books/{slug}/details/` endpoint requires current reading
permission. Anonymous visitors, revoked or spent read-once grants and quarantined
books cannot fetch the preview. Requesting it does not create a reading session
or consume a read-once opening. Physical books retain their separate reading log.

The response contains plain text and omits raw HTML, source URL fields, chapter
bodies, source snapshots and storage references. Parsing is limited to 65,536 characters of
each retained metadata input. Text previews are limited to 8,000 characters,
metadata to 50 fields and contents to 200 entries with a maximum depth of eight.
Any shortening is reported with `truncated` and a visible notice directing the
reader to the full book. Anonymous catalog metadata remains unchanged.

Regression coverage: `tests/backend/access/test_book_detail_preview.py`,
`tests/web/unit/book-detail-links.test.mjs` and
`tests/web/e2e/book-details.spec.mjs`.
