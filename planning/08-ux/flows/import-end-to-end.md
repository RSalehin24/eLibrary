# Flow: import a book end to end

Status: DRAFT

Actors: operator (`operate`) only; publishing is automatic (D-49). Requirements: REQ-WEB-017; REQ-ING-001..036; D-03 (GET only), D-42 (no upload).

1. Operator opens Import. The header shows the credential chip; if `expired` or `missing` a banner explains the source cookie must be rotated by the host owner (Check now re-probes). Scrapes will wait or fail with `auth_required` until then.
2. Catalog bucket: Start sync (`POST /mirror/syncs`); live progress arrives on the SSE stream; Cancel is cooperative. The listing shows source books, incomplete ones flagged.
3. Select entries and Create requests (`POST /requests/from-mirror`) or use New request with a URL or title (`POST /requests`, idempotent). Per-item results appear in one snackbar. An exact duplicate is refused with a link to the existing book.
4. Requests bucket: each request moves queued, scraping, curating, then one of the outcomes. The Jobs bucket shows attempts, leases and typed errors; retryable errors are retried by the system, permanent ones wait for an operator.
5. Outcome `needs_review`: the request appears under Needs review; the operator resolves items (accept, override, drop) ([review flow](review-duplicate.md) covers duplicates; items follow the same pattern). Nothing guessed is published.
6. Outcome `duplicate`: Duplicates bucket ([flow](review-duplicate.md)).
7. Build: an EPUB is built and must pass the gates (XML, structure, epubcheck, nav/NCX/TOC); the request detail shows gate results. A failed gate leaves nothing visible and the request stays in the review queue (`needs_review` or `failed`) for the operator.
8. Publish step: when every gate passed, ingestion calls catalog, which publishes the version at once, with no human step ([automatic publish](auto-publish.md)).
9. The book is `published`, the reader builds its copy, and the request shows Published with a link to the book.

Branches:
- Cancel a running job: confirm naming the request; cooperative, checked per page.
- Retry a failed job or request (allowed-source-state table; invalid action disabled with reason, server 409 otherwise).
- Reprocess: structured diff against the published build before the rebuild runs; if its gates pass it replaces the published version automatically.
- Stream lost: "Reconnecting", resume by `Last-Event-ID` or reload the snapshot.
- Queue unavailable: `queue_unavailable` message, nothing runs inline.
- A re-sync never overwrites workflow state (mirror fields and workflow state are separate).
