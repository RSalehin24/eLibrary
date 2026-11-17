# library — state machines

Status: DRAFT

## Reading session

```
 (none) ─open + Allow─► Preparing ─section index ok + opening consumed (if read-once)─► Active ─close/idle/timeout─► Closed
              │                │
              │                └──fail──► (discarded; opening NOT consumed)
              └─Deny──► (no session)
```
Heartbeat extends `Active`; missing heartbeat for 90 s → `Closed`. A second `open` for the same
(owner, book, device class) while `Active` returns the existing session (reconnect; not a new opening).

## Annotation anchor

```
 Anchored ──artifact set changes──► Anchored (unchanged text) | Reanchored | Orphaned
 Orphaned ──user places it / later set matches──► Reanchored
```
Transitions are produced by the pure re-anchor function; the persisted state is replaced only
together with the new `artifact_set_id`.

## Progress

Single register with a monotonic `revision`; the write rule is `if new.revision > stored.revision then replace`. Clients use `max(server, local)+1` after a conflict.

## Re-anchor job

`Pending(set S′) → Running → Done` per (owner, book); idempotent; emits `AnnotationReanchorDone` when all of a book's annotations are processed; content retention listens for it.
