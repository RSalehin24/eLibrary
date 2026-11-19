# Flow: send to Kindle

Status: DRAFT

Actors: reader with `kindle`. Requirements: REQ-CAT-029, REQ-IDN-028; notify delivery. Default readers have `kindle` (new-architecture section 10).

1. First use: Book detail, Files tab shows "Add a Kindle address" because the user has none; the action opens Settings, Kindle ([settings](../screens/settings.md)).
2. Settings shows the sender address and the instruction to approve it in the user's Amazon account; the user adds up to 5 addresses (each validated; `PUT /me/kindle-addresses`).
3. On the book's Files tab the user selects an address and chooses Send to Kindle; `POST /books/{slug}/kindle {address_index}` returns 202 with a request id. The button is disabled with a reason while a request is in flight.
4. The Files tab shows the delivery status for this book from `GET /books/{slug}/kindle-requests`: queued, sent, or failed with a reason in plain words. Status changes are announced politely; the status is refreshed on focus and on a bounded timer while queued.
5. The Library chip "Sent to Kindle" lists books the user has sent (cross-book list **OPEN U-5**).

Branches:
- No `kindle` scope: the action is hidden; a direct URL shows Forbidden.
- File too large or not available (`kindle_not_available`): message with the reason and no retry.
- `limit_exceeded` or `rate_limited`: message with the wait.
- Failed delivery: reason shown with Retry (a new request).
- Book not published or deleted: NotFound; earlier requests stop resolving.
