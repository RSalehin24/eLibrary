# identity - state machines

Status: DRAFT

All transitions run in one transaction with the audit row and, where listed, the outbox event. Any pair not listed is unrepresentable (typestate or enum transition function plus a database check).

## User status (REQ-IDN-009, INV-IDN-001, INV-IDN-009)

| From | Event | Guard | To | Side effects |
|---|---|---|---|---|
| (none) | admin invite | `manage_users`, email not taken | Invited | issue invite link; `email.requested` |
| (none) | `seed-first-admin` | no admin exists; not dry-run | Active | audit; no password stored, a setup link is issued |
| Invited | accept link | link `Issued`, not expired, password policy ok | Active | store credential; consume link; audit |
| Invited | resend invite | admin | Invited | supersede old link; new link; `email.requested` |
| Active | suspend | admin; not self; not last active admin | Suspended | revoke all sessions; `user.disabled`; bump `grant_version` |
| Suspended | reactivate | admin; not self | Active | audit; `grant.changed` |
| Invited, Active, Suspended | disable | admin; not self; not last active admin | Disabled | revoke sessions, supersede links; `user.disabled` |
| any | delete | admin; not self; not last admin | (removed) | revoke sessions; erase image; announce (**OPEN O-1**); audit |

Disabled is terminal. The chain is Invited, Active, Suspended, Disabled; there is no other transition. Role change (reader, operator, admin) is a field change, not a status change: admin only, never for oneself, never demoting the last active admin; emits `grant.changed`.

## Link (invite and reset) (REQ-IDN-002, INV-IDN-002)

| From | Event | Guard | To |
|---|---|---|---|
| (none) | issue | same (user, purpose) `Issued` link exists | old becomes Superseded, new Issued |
| Issued | consume | `now < expires_at`, row locked, nonce matches; for reset the user is Active | Consumed |
| Issued | clock passes `expires_at` | | Expired (evaluated at use) |
| Issued | newer link issued | | Superseded |
| Consumed, Expired, Superseded | any | | unchanged; response identical to unknown (`link_invalid`, 410) |

Invite 7 days, reset 24 h. Reset confirm revokes all of the account's sessions and is throttled.

## Reset request (no enumeration, REQ-IDN-008)

Request always returns 202 with the same body and equivalent work: known and Active gives supersede, new link, `email.requested`; otherwise a dummy hash and no row. Limits per address and per account apply before the branch.

## Sign-in and session (REQ-IDN-004, 007, INV-IDN-004, INV-IDN-007)

| From | Event | Guard | To |
|---|---|---|---|
| Anonymous | password ok, Active, TOTP not required | not throttled | Authenticated (cookie, CSRF token returned) |
| Anonymous | password ok, Active, TOTP required | | PendingTotp (authorizes only `/auth/totp/verify`, 5 minutes) |
| PendingTotp | code ok | step greater than `last_accepted_step` | Authenticated (`mfa_ok`) |
| PendingTotp | code wrong or expired | failure counted | PendingTotp or discarded |
| Anonymous | wrong or unknown credentials | | Anonymous (uniform `invalid_credentials`) |
| Authenticated | sign-out, password change (others), suspend, disable, delete | | Revoked |
| Authenticated | idle 12 h or absolute 30 d | injected clock | Revoked |

A suspended or disabled account never reaches Authenticated. `Session<Authenticated>` is constructible only from a password check plus TOTP when required.

## TOTP (REQ-IDN-004, 005, 006, INV-IDN-005)

| From | Event | Guard | To |
|---|---|---|---|
| None | setup | session; re-auth | Pending (secret shown once) |
| Pending | confirm | valid code | Enabled |
| Pending | abandon or new setup | | None or Pending (replaced) |
| Enabled | accepted code | step > last accepted, row locked | Enabled (step recorded) |
| Enabled | disable | password and code; account does not require TOTP | None |
| Enabled | reveal secret | password and code | Enabled |

`Pending` never counts as a second factor. Concurrent verification of one code accepts once.

## Grant (REQ-IDN-011, 012, 017)

Stored fields: `active`, `expires_at`. Derived state: Live iff `active` and (`expires_at` null or `now < expires_at`). Transitions: create (Live), edit expiry or active flag, revoke (active false); all admin only, never for oneself, each emits `grant.changed` and bumps the user's `grant_version`; a duplicate active (user, scope, book) is rejected.

## Reading ticket and read-once (REQ-IDN-020, 021, 022; INV-IDN-020..022)

| From | Event | Guard | To |
|---|---|---|---|
| (none) | mint (`/internal/tickets`) | `decide` allows `read` (and read-once not yet consumed for another ticket) | Minted (hash stored, 15 min, grant version recorded); read-once untouched |
| Minted | verify without redeem | not expired; user Active; grant version unchanged or still allowed; book published; ids match | Minted |
| Minted | verify with `redeem` | as above; no `read_once_uses` row or row has this ticket id | Redeemed (row inserted for read-once; idempotent for the same ticket) |
| Redeemed | verify again, same ticket | | Redeemed (reconnect is not a new opening) |
| Minted, Redeemed | 15 min pass | | Expired (`ticket_expired`) |
| Minted, Redeemed | user disabled, grant changed (version moves past the ticket's), book unpublished, other user or book or version | | rejected (`ticket_invalid`) |
| any | different ticket redeemed for a consumed read-once book | | rejected (`read_once_consumed`) |

Admin reset of the counter deletes the `read_once_uses` row (audited). A missing reading copy does not consume (the reader reports `copy_unavailable` before redeeming).

## Outbox event (REQ-IDN-023)

Written (inside the change transaction) then Visible (committed, ordered by `cursor`) then Retained 30 days and pruned only past all consumer cursors. Events are never updated; redelivery is expected.

## Admin host commands (REQ-IDN-032, 033)

`admin-reset` and `seed-first-admin`: DryRun (default, prints the plan) then Applied only with an explicit flag; seed refuses when an admin exists; reset sets a one-time setup link, never a password; every run is audited.
