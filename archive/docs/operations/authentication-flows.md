# Authentication Flows

This document captures the intended invite, password recovery, and mandatory two-factor onboarding behavior for the Bangla Library Platform.

## User Stories

- As an invited user, I want the invite email to open a dedicated password creation page so I can create my first password without being dropped into the generic password reset flow.
- As an invited user, I should not receive a public password reset email until I finish the intended first-time setup flow.
- As a returning user who forgot a password, I want a public password reset request page that accepts my email and sends me a secure reset link.
- As a returning user who requests another reset email, I want only the newest reset link to work so any older reset links become invalid immediately.
- As a user whose account requires two-factor authentication, I want to be forced into authenticator setup immediately after password creation or reset so I cannot access the rest of the application until setup is complete.
- As an administrator, I want `Require Two-Factor` to be enforced consistently across invite onboarding, password creation, and later sign-ins.
- As an administrator, I want to resend a setup email while onboarding is still incomplete so older setup links stop working and the user can use the newest one.

## Use Cases

### Invited Account Activation

1. A super admin creates a managed user and sends an invite email.
2. The invite email links to `/create-password?uid=...&token=...`.
3. The invited user creates a password.
4. If the account does not require TOTP, the user is returned to the sign-in flow.
5. If the account requires TOTP and has not configured it yet, the backend signs the user into a restricted setup session and the frontend sends the user to `/two-factor-setup`.
6. The user cannot continue to the rest of the application until TOTP setup is verified.
7. The public reset-password request does not send a reset link while invite onboarding is still pending.

### Setup Email Resend

1. A super admin opens Users & Access for an onboarding-pending account.
2. The user row shows `Resend Email` until the invited user has created a password and, when required, completed TOTP setup.
3. Sending a fresh setup email issues a new `/create-password?uid=...&token=...` link.
4. Any older setup link becomes invalid immediately and opens an expired-link page instead of the password form.
5. The resend action disappears after onboarding is complete.

### Self-Service Password Recovery

1. A user opens `/reset-password`.
2. The user enters an email address and submits the form.
3. The public form button reads `Reset Password`.
4. The backend returns `Reset email has been sent.` when an active account can use self-service reset, using `/reset-password/confirm?uid=...&token=...`.
5. Each reset link stays valid for 6 hours from the time it is generated, and the reset email states that expiry window.
6. If the user requests another reset email before using the earlier one, only the newest reset link remains valid.
7. The backend returns `No user exist with this email.` when no eligible self-service reset account matches the email, including invite-onboarding accounts that must finish `/create-password`.
8. The user opens the reset link and chooses a new password.
9. If the account still needs mandatory TOTP setup, the user is sent directly into `/two-factor-setup`.
10. Otherwise, the user returns to the normal sign-in flow.

### Mandatory TOTP Enforcement

1. A signed-in user with `totp_setup_required=true` attempts to open any protected route.
2. The frontend redirects the user to `/two-factor-setup`.
3. The page keeps the public brand header, but no navigation links, profile menu, or other normal header actions are available.
4. The backend middleware blocks protected API calls other than session, logout, profile, and TOTP setup endpoints until setup is complete.
5. After successful TOTP verification, the user is returned to the originally requested route or `/home`.

## Automated Test Cases

| Test Case | Layer | Main Location |
| --- | --- | --- |
| Invite email uses `/create-password` and preserves localhost ports when configured | Backend `pytest` | `tests/backend/auth/test_auth_01.py` |
| Invite-only accounts do not receive public reset emails while setup is pending | Backend `pytest` | `tests/backend/auth/test_auth_01.py` |
| Resending a setup email invalidates any earlier create-password link | Backend `pytest` | `tests/backend/auth/test_auth_01.py` |
| Password reset request email uses `/reset-password/confirm`, keeps a literal query string in the plain-text body, renders the styled HTML layout, and states the 6-hour expiry | Backend `pytest` | `tests/backend/auth/test_auth_01.py` |
| Password reset links remain valid for under 6 hours and fail after the 6-hour window | Backend `pytest` | `tests/backend/auth/test_auth_01.py` |
| A newer password reset request invalidates every earlier reset link for that account | Backend `pytest` | `tests/backend/auth/test_auth_01.py` |
| Password confirmation logs in only users who still must complete TOTP setup | Backend `pytest` | `tests/backend/auth/test_auth_01.py` |
| Sign-in keeps `Continue` disabled until email and password are complete and shows live email-format feedback | Playwright | `tests/frontend/e2e/auth-public-pages.spec.js` |
| Public reset page collects an email address, uses the `Reset Password` CTA, and shows the minimal success/error toasts | Playwright | `tests/frontend/e2e/auth-public-pages.spec.js` |
| Invite password creation sends required users into the forced TOTP setup gate | Playwright | `tests/frontend/e2e/auth-public-pages.spec.js` |
| Users & Access can resend setup mail for onboarding-pending accounts with a minimal toast | Playwright | `tests/frontend/e2e/access-page-mocked.spec.js` |
| Protected routes redirect `totp_setup_required` users into the setup gate with the brand-only public header | Playwright | `tests/frontend/e2e/auth-public-pages.spec.js` |
