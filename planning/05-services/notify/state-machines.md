# notify - state machines

Status: DRAFT

## Event pull (outbox cursor)

```
 read cursor c -> GET source/internal/events?after=c -> insert outbox rows (UNIQUE conflict = skip) + set cursor in ONE transaction -> repeat; empty page -> sleep
```
Crash before the transaction: events are re-read. Crash after: cursor already moved. Duplicates are absorbed by the unique key (INV-NTF-001, REQ-NTF-001).

## Mail delivery (outbox row)

```
 Queued --claim (lease)--> Sending --send ok--> Sent
                              |--transient error--> Retry(next_attempt_at) --due--> Sending   (attempts < N, within 24 h)
                              +--permanent error / attempts exhausted--> Failed --admin retry--> Queued
 Sending --lease expired (crash)--> Retry
```
**Claim-before-send**: the row exists in `Queued` under `UNIQUE (source, event_id, kind)` before any send, and `Sending` is entered by a leased claim. A crash after the provider accepted but before `Sent` is recorded can cause one repeat on lease expiry; this residual at-least-once window is documented and bounded to one extra attempt (providers without idempotency tokens). `Sent` is terminal and never re-claimed.

## Kindle delivery

```
 Queued --> Preflight --reject--> Rejected (terminal, user-visible reason)
               |
               +--ok--> Sending --ok--> Sent
                           |--transient--> Retry --> Sending
                           +--permanent / exhausted--> Failed --admin retry--> Queued
```
Preflight checks, in order: user active and address present on the profile; EPUB exists for a published version; size <= 50 MB; sender-approval confirmed; daily cap. Rejections never retry automatically. The EPUB is streamed from catalog during `Sending` (not stored). Terminal: `Sent`, `Rejected`, `Failed`.

## Template set

`Draft -> Active` (all keys in `bn` and `en`, typed variables compile); exactly one active version per (key, language); activation is atomic for the set.
