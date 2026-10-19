# Book metadata history

Open a book in **Admin → Books → Edit** and select **Metadata History**. The
history lists the time, source, editor, and optional edit note for each recorded
change. The site language switch applies to history controls and provenance
labels; dates use Asia/Dhaka in 12-hour format. Book titles, editor names, and
edit notes remain as entered.

An optional edit note can be supplied when saving book details or changing its
authors, categories, series, or edition group. Notes accept up to 2,000 characters
and are saved with the metadata version in the same transaction. A stale or
invalid save creates no history entry. Notes are not editorial approval requests.

`GET /api/v1/manage/books/{slug}/history/` returns `entries` and `pagination`.
`page` starts at 1; `limit` defaults to 10 and accepts 1–100. Entries use a stable
newest-first order and include `id`, `source`, `notes`, `created_at`, and the
editor's `id` and display `name` when available. Existing old slugs still resolve.

History requires metadata-edit access to the selected book. Deleted books and
books outside the actor's scope return 404. Responses are private and uncached.
The endpoint does not load or expose stored snapshots, which can contain the
complete reading text in versions retained from the previous application. It
does not expose editor email addresses. Existing snapshots and files are retained.
