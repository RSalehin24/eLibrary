# notify - state machines

Status: DRAFT

## Event pull (REQ-NTF-001, INV-NTF-001)

| State | Event | Guard | Next |
|---|---|---|---|
| Idle | poll due | cursor c for a source | Fetching |
| Fetching | page received | non-empty | Storing |
| Fetching | empty page | | Idle (cursor kept) |
| Fetching | source error or timeout | | Idle (backoff, cursor unchanged) |
| Storing | one transaction: insert rows (`UNIQUE` conflict skips) and set cursor | commit | Fetching |
| Storing | crash before commit | | events re-read; duplicates absorbed |

## Mail delivery (outbox row; REQ-NTF-002, 008, 010)

| From | Event | Guard | To |
|---|---|---|---|
| (none) | event stored | unique `(source, event_id, kind)` | Queued |
| Queued, Retry | claim | `next_attempt_at <= now`, `SKIP LOCKED`, lease set | Sending |
| Sending | provider accepted | | Sent (terminal) |
| Sending | error `Retryable` | attempts below the maximum | Retry (`next_attempt_at` by exponential backoff) |
| Sending | error `Retryable` | attempts exhausted | Failed |
| Sending | error `Permanent` (for example identity says account no longer exists) | | Failed |
| Sending | lease expired (crash) | | Retry (one possible repeat, documented) |
| Failed | admin retry through operations | | Queued |

Sent is terminal and never re-claimed. A failed mail never undoes account creation or the reset request. Each attempt writes one `delivery_log` row.

## Kindle delivery (REQ-NTF-005..009)

| From | Event | Guard | To |
|---|---|---|---|
| (none) | `kindle.requested` stored | unique `request_id` | Queued |
| Queued | claim | lease | Preflight |
| Preflight | identity `check` denies `kindle` or account not Active | permanent | Rejected (reason, reported to catalog) |
| Preflight | no valid address on the account | | Rejected `no_address` |
| Preflight | book not published or format not EPUB | | Rejected `unsupported_format` |
| Preflight | total size above 50 MB | | Rejected `too_large` |
| Preflight | owner has not confirmed sender approval | | Rejected `sender_not_approved` |
| Preflight | quota exceeded | | Rejected (limit, no retry) or deferred within the window |
| Preflight | all checks pass | | Sending |
| Sending | sent | | Sent (reported to catalog) |
| Sending | `smtp_failed` retryable | attempts below max | Retry then Sending |
| Sending | retryable exhausted or permanent | | Failed (reported to catalog) |
| Failed | admin retry | | Queued |

Preflight order: identity Allow and account Active, address, publication and format, size, sender approval, quota. Rejections never retry automatically. At most one attachment is held per send; concurrency is a configured bound. Terminal: Sent, Rejected, Failed.

Reported status mapping (catalog and `GET` status routes): Queued and Retry report `queued`; Sent reports `sent`; Rejected (any Preflight failure) and Failed report `failed` with the typed reason or error class. Kindle statuses are `queued`, `sent`, `failed` only. The status report to catalog is retried until acknowledged and does not change the delivery state.

## Template set

`Draft` then `Active` only when every key exists in `bn` and `en` with compiling typed variables; one active version per (key, language); activation atomic for the set.

## Retention job

Selects at most a bounded batch of rows older than the retention for outbox, delivery log and quota counters per run; repeats until none remain; a terminal-state row only (never `queued`, `sending`, `retry`).
