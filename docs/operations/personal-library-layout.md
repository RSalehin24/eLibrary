# Personal library browsing and reset

My Books keeps search, sorting, saved views and the existing card/table controls
above the results. Its filter toolbar shares one compact row when space permits;
expanded filters and enlarged text can grow vertically without horizontal page
overflow. Export controls follow the results and pagination, and still export the
complete filtered personal view rather than only the current page.

A clear link appears in My Books when there are conditions to clear. Clearing an
unsubmitted search also resets the controlled input when the URL is already clear.
The current All/Owned/Saved/Recent/Granted view is retained. Other catalog surfaces
keep their existing clear links, including physical-only binding filters.

When the URL has submitted conditions, ordinary navigation handles the reset.
The outgoing form is not mutated: returning to its cached saved-search route must
restore the submitted values. The shared condition helper recognizes empty/default
record types, locked physical types, queries, sort orders and physical filters.
Modified-click and JavaScript-disabled navigation retain the link's normal behavior.

Regression evidence is in `tests/web/unit/catalog-filters.test.mjs` and the browser
specifications `personal-library`, `catalog-filters`, `book-list-actions` and
`book-exports`. Browser checks cover both languages, desktop/phone placement,
320 px enlarged text, actual filtered CSV downloads, saved-search navigation,
physical binding reset and account-private reading logs. Synthetic account
switches in data-isolation checks leave the old document first so the real session
guard does not race the test's navigation; dedicated account-isolation tests retain
their active-document account-switch coverage.
