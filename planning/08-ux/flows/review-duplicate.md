# Flow: review a duplicate

Status: DRAFT

Actors: operator (`operate`). Requirements: REQ-ING-023; INV: exact normalized title key plus author, category and edition; no fuzzy merge.

1. A request whose match found an existing or similar book gets outcome `duplicate` and appears in Import, Duplicates with a count badge.
2. Operator opens `/import/duplicates/:id`. The page shows the candidate (title, writers, category, edition, source, page count) beside each matched catalog book (cover, metadata, state) with the matching fields marked in text (not only colour). Near-matches are listed for a human to decide and are never merged automatically.
3. Operator chooses one of: Create as new book, Create as new edition, Confirm duplicate (the existing book stays; the request ends), Discard (confirm).
4. `POST /duplicate-reviews/{id}/resolve`. Create new is disabled for an exact duplicate with the reason, and the server refuses it (`duplicate_book`).
5. The result is shown in a snackbar; the next open review opens with a "Next" action; keyboard: `j` and `k` between reviews, `1`-`4` choose an action, `Enter` confirms.
6. Create paths continue in [import end to end](import-end-to-end.md) from the build step.

Branches:
- Already resolved by someone else: `invalid_transition` shows the current state with Refresh.
- Matched book was unpublished or deleted meanwhile: the match panel shows its state.
- A translator difference is not a duplicate and not a review: the records are different books (`new_work`, D-92), so no review is opened for it; the match panel may still list the other translation as a near match.
