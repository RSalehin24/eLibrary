# Entity directory browsing and API compatibility

The approved 21 October interface redesign removes book-type and added-date
controls from all public directories. Names and book counts lead directly to
related books. Public catalog codes and added timestamps no longer occupy each
row. Writers default to the author role; translator, editor, publisher and other
roles remain explicit choices. Selected roles remain in related-book links.

Search and ordering remain available. Collections use the same compact layout
and are labelled **পাঠতালিকা / Reading Lists**. Collections do not expose catalog
code ordering.

Legacy website URLs remove `record_type`, `created_after` and `created_before`,
reset their page and retain search, role and ordering. The same cleanup applies
to the retired controls on catalog, My Books, paper-book, admin-book and Kindle
pages, including saved catalog links. Invalid remaining parameters still use
the normal missing-page flow.

The backend API contract remains compatible: directory responses retain
`catalog_code` and `created_at`; API consumers can still filter book type and
inclusive creation dates in Asia/Dhaka. Invalid dates and reversed ranges return
HTTP 400. Code search/sorting and signed-cursor condition binding remain checked.
Collections return null codes and reject code-sort requests.

Permanent regressions are in `test_directory_dates_codes.py`, the directory and
collection visibility/count tests, `entity-directory-filters.test.mjs`,
`browse-filters.test.mjs` and `entity-directory.spec.mjs`. Earlier screenshots
showing date/type controls describe the superseded interface.

Private-only author, category and series navigation continues to stay within
the reader's current My Books view. Scoped details preserve All or Granted,
and asynchronous save/Kindle controls do not move table metadata links. See
`personal-entity-links.spec.mjs` and [the redesign report](interface-redesign.md).
