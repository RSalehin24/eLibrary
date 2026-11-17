# identity — state machines

Status: DRAFT

## Account status

```
 Invited ──consume setup link──► Active ◄──reactivate── Suspended
    │                              │ ▲                       ▲
    │                              │ └──────suspend──────────┘
    └──────disable─────────────────┴──disable──► Disabled (terminal)
```

| From | Event | To | Side effects |
|---|---|---|---|
| (none) | invite | Invited | issue Setup link; emit `AccountInvited`, `PasswordLinkIssued` |
| Invited | consume Setup link | Active | store credential; emit `AccountActivated` |
| Active | suspend | Suspended | revoke all sessions; emit `AccountSuspended` |
| Suspended | reactivate | Active | emit `AccountReactivated` |
| Invited/Active/Suspended | disable | Disabled | revoke sessions, supersede links; emit `AccountDisabled` |

Any other pair is unrepresentable (`fn transition(Account<S>, Event) -> Result<Account<S'>>`). Modeled in planned `AccountLifecycle` (INV-IDN-001, INV-IDN-008).

## Link

`Issued → Consumed | Superseded | Expired`. Terminal states never return to `Issued`. A consume succeeds only from `Issued` and `now < expires_at`, atomically with the status change (single transaction, row lock) — INV-IDN-002.

## Session / login

```
 (anonymous) ─password ok──► PasswordOk ─(totp not required)────────────► Authenticated
                               │ └─(totp required)─totp ok──────────────►  │
                               └─timeout/ fail ──► (discarded)              ├─logout/revoke/expire──► Revoked
```

`Authenticated` is constructible only from `PasswordOk` and, when required, a verified TOTP (INV-IDN-004). `PasswordOk` sessions are not usable for any other route and expire after 5 minutes.

## TOTP enrolment

`None → Pending (setup) → Enabled (confirm with valid code)`; `Enabled → None (disable, requires current password + code)`. A `Pending` enrolment never counts as a second factor.
