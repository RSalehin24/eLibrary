# Flow: grant management

Status: DRAFT

Actors: admin (`manage_users`, TOTP completed). Requirements: REQ-WEB-018; REQ-IDN-010..012, 017, 018, 020.

1. Admin opens `/admin/users`, searches the user, opens the detail (drawer or full screen).
2. The detail shows the role defaults (read only) and the explicit grants (scope, book or all books, expiry, granted by, reason). `download` and `read_once` exist only as explicit grants.
3. Add grant: pick scopes (several allowed), optionally one book and an expiry, and enter the required reason. The set is sent as one batched atomic request (contract gap **U-12**). Duplicate active grants are refused (`duplicate_grant`) and named in the error.
4. The change is audited in the same transaction and emits `grant.changed`; outstanding reading tickets for that user stop verifying; the detail refreshes.
5. Edit an expiry or deactivate a grant (`PATCH /grants/{id}`, `If-Match`); revoke (`DELETE`, confirm naming user and scope).
6. Read-once: for a book the admin may reset the counter for that user (confirm).
7. Role change and status changes (suspend, reactivate, disable) use confirm dialogs; disabling signs the user out and emits `user.disabled`.

Branches:
- Own account: grant, role and status controls are disabled with "You cannot change your own access"; the server enforces it.
- Last admin: demotion or removal refused with the reason. Lock-out recovery is a documented host command (D-38), not a screen.
- `stale_revision`: shows the stored grant with Refresh.
- 403 `mfa_required` when the admin session has not completed TOTP: go to the TOTP step.
- Delete account: confirm explains that reading data is erased (event shape **OPEN O-1**).
