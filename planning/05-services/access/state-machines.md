# access — state machines

Status: DRAFT

## Grant

```
 Scheduled ──starts_at──► Live ──expires_at──► Expired
                            │
                            └──revoke──► Revoked
```
`Live` ⇔ `starts_at ≤ now < expires_at ∧ revoked_at is null` (computed from the injected clock; the state
is derived, not stored, so it cannot go stale — INV-ACC-004).

## Opening (read-once)

```
 NoOpening ──session Prepared──► Consumed   (terminal for that (account, book))
```
Preparation failure leaves `NoOpening`. A reconnect with the same `session_id` while `Consumed` returns
`already_consumed_by_this_session` (allowed); a different session returns `ReadOnceConsumed` (denied). Model: [ReadOnce.tla](../../03-correctness/formal-models/tla/ReadOnce.tla).

## Capability

`Issued → Expired` (by time); no other states. Revocation is by non-renewal (bounded by TTL ≤ 300 s) plus, for emergencies, a `kid` rotation that invalidates all capabilities at once (runbook: key compromise).

## Default-policy change

Replacing the default policy is a revisioned write; effects apply to new decisions immediately; an event `DefaultPolicyChanged` lets library/content invalidate caches.
