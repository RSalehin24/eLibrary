# Sign-in and auth shell

Status: DRAFT

**Purpose**: one centered card that hosts every unauthenticated step: sign-in, TOTP, reset request and confirm, invitation acceptance, forced TOTP enrolment.
**Primary action**: Continue (one filled button per step).
**Routes** ([route map](../route-map.md)): `/sign-in`, `/sign-in/totp`, `/sign-in/totp-setup`, `/reset-password`, `/reset-password/confirm`, `/invite`. **Auth**: anonymous (setup step: pending enrolment). **Service owner**: identity. **Requirements**: REQ-WEB-002, 014, 020; REQ-IDN-001..008. Flows: [sign-in with TOTP](../flows/sign-in-totp.md), [invite](../flows/invite-acceptance.md), [reset](../flows/password-reset.md).

## Data

`POST /auth/sign-in`, `/auth/totp/verify`, `/invites/accept`, `/password-reset/request`, `/password-reset/confirm`, `GET /auth/session`, `POST /me/totp/setup` and `/me/totp/confirm` ([identity contract](../../07-contracts/http/identity.md)). The CSRF token arrives with the session response.

## States

| State | Behaviour |
|---|---|
| Loading | button shows a spinner in a reserved slot (width stable); fields disabled |
| Empty | not applicable (form) |
| Ready | step form; focus on the first field |
| Error | `invalid_credentials` (same message for unknown account and wrong password), `invalid_code`, `link_invalid`, `weak_password`, `rate_limited` (with wait hint); inline under the field and announced; fields keep their values except passwords |
| Forbidden | 403 `mfa_required` moves to the TOTP step; inactive account shows "this account cannot sign in, ask an administrator" |
| NotFound | an expired, used or superseded link shows "this link is no longer valid" with a way to request a new one (never a blank form) |
| Offline | banner, retry with backoff, form state kept |

A signed-in user visiting any auth route is redirected to `next` or Library (an invite link while signed in offers "sign out first").

## Layout

| Class | Layout |
|---|---|
| compact | full-width card on `surface`, no elevation, 16 px margins, wordmark above |
| medium and larger | card up to 440 px centered on `surface-container-low`, wordmark above; no illustration |

Steps swap inside the card (no page reload). Top bar has only theme and language toggles.

## Actions

Show or hide password; "Change account" at the TOTP step; link "Forgot password"; resend nothing here (an invite resend is an admin action). The password policy (minimum length, deny list) is shown as supporting text from the server policy. TOTP input accepts paste, `autocomplete="one-time-code"`, six digits. `next` is accepted only if same-origin and in the route table.

## Copy keys

| Key | en | bn |
|---|---|---|
| `ux.signin.title` | Sign in | সাইন ইন |
| `ux.signin.email` | Email | ইমেইল |
| `ux.signin.password` | Password | পাসওয়ার্ড |
| `ux.signin.continue` | Continue | চালিয়ে যান |
| `ux.signin.forgot` | Forgot your password? | পাসওয়ার্ড ভুলে গেছেন? |
| `ux.signin.totp.title` | Enter your verification code | যাচাইকরণ কোড দিন |
| `ux.signin.totp.verify` | Verify | যাচাই করুন |
| `ux.signin.invalid` | Email or password is not correct. | ইমেইল বা পাসওয়ার্ড সঠিক নয়। |
| `ux.reset.title` | Reset your password | পাসওয়ার্ড রিসেট করুন |
| `ux.reset.sent` | If the address has an account, a link is on its way. | ঠিকানাটির অ্যাকাউন্ট থাকলে একটি লিঙ্ক পাঠানো হয়েছে। |
| `ux.invite.title` | Welcome. Choose a password. | স্বাগতম। একটি পাসওয়ার্ড দিন। |
| `ux.link.invalid` | This link is no longer valid. | এই লিঙ্কটি আর বৈধ নয়। |

Analytics: none.

## Accessibility

One `h1` per step; step change moves focus to the heading and is announced; errors linked by `aria-describedby`; first invalid field focused; no CAPTCHA or cognitive test; visible labels (no placeholder-only).

## Open

U-1 (token in path, query or fragment), U-2 (does accepting an invite sign the user in, so forced TOTP setup has a session).
