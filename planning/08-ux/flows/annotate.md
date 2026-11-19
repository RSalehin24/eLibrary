# Flow: annotate

Status: DRAFT

Actors: reader with `read`. Requirements: REQ-RDR-013..016, 018, 019.

1. In the reader the user selects text by pointer, touch or keyboard (`Shift` + arrows then `A` to open the annotation surface).
2. The annotation surface appears: a popover on medium and larger windows, a bottom sheet on compact. Choices: one of five colours (highlight), Add note, Save as quote, Copy, Bookmark.
3. Highlight: `POST /books/{slug}/highlights` with the anchor (section, quote with prefix and suffix, offset) and colour; the mark appears at once and shows "saving" until confirmed.
4. Note: the labelled note field opens (focus trapped; `Ctrl/Cmd+Enter` saves, Esc cancels); stored as a field of the highlight.
5. Bookmark: `POST /books/{slug}/bookmarks`; a duplicate returns the existing one (`created: false`) and the UI shows it as already bookmarked, not an error.
6. Editing: choose the highlight, change colour or note (`PATCH /highlights/{id}` with `If-Match`), or delete (confirm if it has a note).
7. Notes list: the side or bottom sheet lists this book's bookmarks, highlights and notes; selecting one jumps to it. Across books the user opens `/notes` and follows deep links to `/books/:slug/read?at=`.

Branches:
- Save fails: the mark stays with a "not saved" marker and a Retry in a snackbar; never `alert`.
- `limit_exceeded` (5,000 per book, note length): message with the limit.
- `stale_revision`: shows the stored value and offers to reapply.
- Anchor cannot be placed after a new version: the note is Orphaned, stays visible in Notes with the saved quote, can be re-placed manually.
- Ticket expired: annotation writes use the session and still work; reading re-opens once.
- Export (Markdown or JSON) from Notes.
