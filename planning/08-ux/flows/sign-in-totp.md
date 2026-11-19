# Flow: sign in with TOTP

Status: DRAFT

Actors: any active user. Requirements: REQ-IDN-004, 005, 007, 008; REQ-WEB-002.

1. Visitor opens a protected URL or `/sign-in?next=<route>`; `next` is checked as same-origin and in the route table.
2. Enters email and password; `POST /auth/sign-in`. The server sets the session cookie and returns the CSRF token.
3. Response `totp_required`: the card moves to `/sign-in/totp` (pending session, no authenticated access yet). Response `active`: go to step 6.
4. Enters the six-digit code (paste and one-time-code autofill allowed); `POST /auth/totp/verify`.
5. Success: session becomes active; the CSRF token is kept in memory.
6. Redirect to `next` (default Library); navigation is built from `GET /me/capabilities`.

Branches:
- Wrong credentials: one uniform message (no account enumeration); `rate_limited` shows a wait hint; passwords are cleared, email kept.
- Wrong or reused code: `invalid_code` inline, field cleared and focused; a used time step is rejected, the user waits for the next code.
- Account requires TOTP but none enrolled: forced setup step (**OPEN U-2**), no access until confirmed.
- Suspended or disabled account: sign-in is refused with "this account cannot sign in, ask an administrator".
- Session expires later (401): sign-in with the same `next`.
- Sign out: `POST /auth/sign-out`, return to Library as a visitor.
