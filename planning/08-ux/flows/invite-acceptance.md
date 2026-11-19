# Flow: invite acceptance

Status: DRAFT

Actors: admin (`manage_users`), invitee. Requirements: REQ-IDN-001, 002, 003, 004, 031; REQ-NTF mail. There is no public sign-up.

1. Admin opens Users and access, chooses Invite, enters email, display name, role, language; `POST /users`. The account is `invited`; an `email.requested` event leads notify to send the link. A mail failure does not undo the account; the row shows "mail not sent, Resend".
2. Invitee opens the link in the mail: `/invite` (token placement **OPEN U-1**). The page checks nothing server-side until submit; the token is removed from the address bar after it is read.
3. Invitee chooses a password (policy shown from the server: minimum length, deny list); `POST /invites/accept`.
4. Success activates the account. If the account requires TOTP the response has `next_step: totp_setup`; whether the user is signed in at this point is **OPEN U-2**. Otherwise the user is sent to `/sign-in` with "Your account is ready".
5. First sign-in follows [sign-in with TOTP](sign-in-totp.md).

Branches:
- Link expired, used or superseded: "this link is no longer valid"; the page tells the user to ask the administrator for a new invite (no self-service resend, to avoid enumeration).
- Weak password: `weak_password` inline with the policy.
- Admin resends: `POST /users/{id}/resend-invite` creates a new link and supersedes the old one; the old link then shows the invalid state.
- Email already used: `email_taken` in the invite dialog.
- Invitee already signed in as someone else: "sign out first".
