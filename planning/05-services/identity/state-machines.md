# identity - state machines

Status: DRAFT

## User status

```
 Invited --accept invite--> Active <--reactivate-- Suspended
    |                         | ^                      ^
    |                         | +------suspend---------+
    +-------disable-----------+--disable--> Disabled (terminal)
```

| From | Event | To | Side effects (same transaction) |
|---|---|---|---|
| none | admin invite | Invited | issue invite token; `email.requested` |
| Invited | accept invite | Active | store credential; audit |
| Active | suspend | Suspended | revoke all sessions; `user.disabled` |
| Suspended | reactivate | Active | audit; `grant.changed` (caches refresh) |
| Invited, Active, Suspended | disable | Disabled | revoke sessions, supersede tokens; `user.disabled` |

Any other pair is unrepresentable (typestate `User<S>`; INV-IDN-001, INV-IDN-008). The seeded admin starts `Active` through the CLI only.

## Invite and reset token

```
 Issued --consume--> Consumed
    |--new token same (user,purpose)--> Superseded
    +--now >= expires_at--> Expired
```

Invite lifetime 7 days, reset 1 hour. Consume succeeds only from `Issued` and `now < expires_at`, in one transaction with a row lock on the token (INV-IDN-002). Terminal states never return to `Issued`. Reset confirm additionally requires user status `active`; a reset token for a `disabled` or `suspended` user is `link_invalid`.

## Reset request (DRAFT proposal, no enumeration)

```
 request(email) --always--> 202 (same body, same work)
     |- known + active   -> supersede old reset token, issue new, outbox email.requested
     +- unknown/other    -> dummy hash, no token, no outbox row
```
Rate limits per address and per IP apply before the branch, so limits do not reveal existence.

## Sign-in and session

```
 anonymous --password ok--> PasswordOk --totp not required--> Authenticated
                               |  +--totp required, code ok--> Authenticated
                               +--5 min / failure--> discarded
 Authenticated --sign-out / revoke / idle 12h / absolute 30d--> Revoked
```
`Authenticated` is constructible only from `PasswordOk` plus a verified TOTP when required (INV-IDN-004). `PasswordOk` authorizes only `/sign-in/totp`.

## TOTP

`None -> Pending (setup) -> Enabled (confirm with a valid code)`; `Enabled -> None` needs current password and code. A step is accepted only if greater than `last_accepted_step`, updated under a row lock (INV-IDN-009). `Pending` never counts as a second factor.

## Grant

`Live` iff `now < expires_at` (or no expiry) and `revoked_at IS NULL`; state is derived from the injected clock, not stored (REQ-ACC-004). `Live -> Revoked` by admin. Each change emits `grant.changed`.

## Read-once (identity side)

```
 NotConsumed --/internal/check consume=true, grant ok, published--> Consumed (terminal per user+book)
```
The row insert is the consumption (PK `(user_id, book_id)`). Reader calls consume only on successful ticket redemption, and not when the reading copy is missing (brief 5.4); a redemption retry with the same `ticket_id` returns `already_consumed_by_this_ticket` (allowed), a different ticket returns `ReadOnceConsumed`.

## Outbox event delivery (producer side)

`Written (in the change transaction) -> Visible (committed, via the cursor) -> Retained`. Events are never updated. Consumers store their cursor; `GET /internal/events?after=n` is a pure read ordered by `id`. Events older than 30 days and acknowledged by all consumers may be pruned. Duplicates and gaps in delivery are impossible, redelivery after a consumer crash is expected.
