# notify — state machines

Status: DRAFT

## Mail delivery

```
 Claimed ──send ok──► Sent
    │
    ├──transient error──► RetryWait(next_attempt_at) ──► Claimed   (attempts < N)
    ├──permanent error / attempts exhausted──► Failed ──admin retry──► Claimed
    └──preflight reject (Kindle only)──► Rejected
```

**Claim-before-send**: the row is inserted in `Claimed` under `UNIQUE(event_id, kind)` before any send. A crash after send but before
`Sent` could cause a repeat; the provider message id check (when supported) and the
`Claimed` row prevent a *second claim*, and the repeat is bounded to one attempt-after-crash,
documented as the residual at-least-once window for providers without idempotency tokens.

## Kindle send

`Requested → Preflight → (Rejected | Claimed → Sent | Failed)`; terminal states are `Sent`, `Rejected`, `Failed`.

## Template set

`Draft → Active` (all keys × languages present, variable structs compile); only one `Active` version.
