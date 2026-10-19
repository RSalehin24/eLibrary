# Manual EPUB replacement

The existing managed-book EPUB upload endpoint accepts files up to 24 MiB. It
stores a protected candidate, validates and prepares every reader resource, and
then checks the editor's current authority and the book's metadata revision again.
The active asset changes only after these steps succeed in one database
transaction. Published books stay published throughout preparation. New manual
book records become ready and retain the explicit Publish action; no editorial
review step is required.

The prior protected file and prepared publication remain available to existing
reader sessions. A protected `before_epub_upload` metadata version retains the
old asset reference and checksum. Ownership, bookmarks, notes and progress do not
change. Metadata history responses never expose the protected snapshot.

For a website-backed book, an upload must match every body section from the
current verified source edition. Matching checks the actual reader spine, so
text hidden in extra archive entries cannot satisfy it. Missing, outdated or
quarantined source evidence requires automatic source regeneration first. Manual
upload cannot clear source quarantine or bypass the source checks.

Invalid resources return a file validation error. Metadata changes and revoked
authority reject the final switch. Storage/preparation failures return a temporary
unavailable response. In each case, the previous active asset remains unchanged.
Unused candidates and prepared resources remain protected; the upload service
never deletes historical files as part of an unsuccessful replacement.

Regression coverage: `test_epub_uploads.py`, `test_epub_atomic_replacement.py`,
`test_epub_source_replacement.py`, and the bilingual admin language unit tests.
