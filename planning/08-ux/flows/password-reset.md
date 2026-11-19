# Flow: password reset

Status: DRAFT

Actors: any user with an account. Requirements: REQ-IDN-002, 003, 007, 008.

1. On sign-in the user chooses "Forgot your password?" and opens `/reset-password`.
2. Enters the email; `POST /password-reset/request`. The answer is always the same ("If the address has an account, a link is on its way") whether or not the account exists; throttled.
3. The mail (sent by notify) contains a single-use link to `/reset-password/confirm` (token placement **OPEN U-1**).
4. User sets a new password; `POST /password-reset/confirm`. All of the account's sessions are revoked.
5. The user is sent to `/sign-in` with "Password changed, sign in again"; TOTP applies as usual ([flow](sign-in-totp.md)).

Branches:
- Expired, used or superseded link: "this link is no longer valid" with a button to request a new one.
- Weak password: `weak_password` inline with the policy.
- `rate_limited`: wait hint, form state kept.
- Signed-in user: "sign out first" on the confirm page; a signed-in user changes the password in Settings, Security with re-authentication instead.
- A password-changed notice mail is an open notify point (O-9), not part of this flow.
