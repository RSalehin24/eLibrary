# Reader profile and two-factor authentication

`/profile/` provides Bengali name, password, Kindle-address, and authenticator
settings. The page requires a session, uses noindex metadata, and forwards
cookies only to private, no-store Django endpoints. Accounts requiring TOTP
setup reach this screen before private workspaces and retain their intended
internal return path. Public book actions link to setup when necessary.

## Profile changes

`GET/PATCH /api/v1/auth/profile/` whitelists editable fields. Updates lock the
account and require its `updated_at` revision. Missing revisions return 400;
stale revisions return `409 state_conflict` without overwriting another edit.
The UI retains the draft, reports field errors, and never retries mutations
automatically. Saving one section preserves unfinished forms in other sections.
Readers can explicitly discard a form. App updates wait for unsaved forms and
pending commands.

Password changes require the current password, matching confirmation, at least
12 characters, and the existing Django password validators. The current session
receives the new authentication hash; previously authenticated sessions lose
access. Password fields clear after success. Neither passwords nor provisioning
secrets go to browser storage or the service-worker cache.

Successful login/logout broadcasts a data-free account-change notification to
other tabs. They clear their query cache and reload, discarding the previous
account's private DOM and unfinished forms. The sending tab completes its own
navigation. Returning focus, visibility, or a restored page also refreshes the
session; an identity change clears/reloads private state. This fallback works
when BroadcastChannel is unavailable. Account-change reloads are separate from
the user-accepted PWA update flow.

Kindle addresses remain normalized, deduplicated, and restricted to `kindle.com`.
The new profile route bounds them to ten. Owners and readers with an active
book/category/author/global Kindle grant can configure addresses. Authorization
for actually sending each book remains a separate backend decision.

## Authenticator lifecycle

The `/api/v1/auth/2fa/` endpoints expose status, setup, confirmation,
cancellation, and disabling. Setup requires the current password and reuses
an interrupted pending device. It returns a QR image and manual Base32 key;
the UI displays the backend-generated SVG as an image rather than executable
page markup. Cancelling removes only the account's unconfirmed devices.

Confirmation locks the account and device before verifying the code. Invalid
attempts commit django-otp's throttle counters before returning an error.
Successful codes cannot be replayed. Six- and eight-digit devices are supported.
Disabling through the new route requires a password and a fresh code and is
prohibited when the administrator requires TOTP. Login verification is also
locked across both retained and versioned login paths, preventing concurrent
acceptance of one code. Status refresh follows successful commands.

An unconfirmed setup blocks accepted app updates until confirmation or explicit
cancellation. Completed setup offers the preserved private return link. Return
paths reject external URLs, backslashes, and control characters.

## Maintenance authentication

Django's `/admin/` retains staff/active-account access and respects the same
enabled/required TOTP policy. Optional accounts without a confirmed device keep
their password-only behavior. Accounts with TOTP enabled need a verified device
session; required setup cannot be bypassed through the maintenance password form.
The form uses the same locked code verifier as library login, accepts six/eight
digits, preserves CSRF, commits failed-code throttling, and rejects replay.
Missing codes do not consume the device's failure budget. The profile link
provides the setup entry point without unsupported challenge/device actions.

Library login and setup confirmation persist django-otp's verified-device marker
in the current server-side session. Password-only sessions remain unverified;
unconfirmed or other-account devices cannot unlock maintenance. Twelve dedicated
backend checks cover this boundary, including concurrent library/admin login.
Chromium checks exercise the 320-pixel native form without JavaScript and the
handoff from profile confirmation to maintenance.

## Verification and remaining work

On 14 October 2026, 464 selected backend tests passed: 426 new platform tests,
20 retained authentication tests, 16 retained access tests, and two retained processing consistency tests.
Thirty new profile/security cases cover
authorization, CSRF, revisions, password/session behavior, scoped Kindle
configuration, interrupted setup, throttling, replay, required policy,
eight-digit devices, and concurrent setup/confirmation/login. mypy passed 127
new source files with the isolated database and broker environment configured;
django-otp is analyzed using `follow_untyped_imports`, without suppressing
missing-library diagnostics.

The complete 82-journey Chromium run passed against the production standalone
artifact. Account journeys cover drafts/conflicts, address normalization,
password/session changes, resumed/cancelled setup, required return paths,
authenticator login, account changes across tabs, and updates during profile/setup editing. Profile screens
fit all eight planned viewport widths; phone/desktop screenshots were inspected.
Node's fourteen worker/update/authentication/job/password-link helper tests, strict TypeScript, ESLint,
Ruff, OpenAPI validation, migrations, and the production build passed.

The asynchronous [Kindle workflow](kindle-delivery.md) is now implemented locally.
The [password-link receiving workflow](password-links.md) is implemented and
preserves literal password spaces at versioned login. Queued account creation,
invitations, and reset requests are available in [account mail](account-mail.md).
Profile-image editing, live broker/device delivery, bulk access workflows, production routing of
retained authentication endpoints, supported cross-browser checks, physical
devices, and capacity measurements remain outstanding. This increment does
not complete the reader phase or authorize external email delivery.
# Session invalidation on security changes

Account sessions include a durable security revision. Confirming or disabling an
authenticator advances that revision and keeps only the current session, with a
new cookie and the confirmed device marker. Older sessions must authenticate
again. Changing active status or the required-authenticator policy advances the
revision under a user row lock, including maintenance and retained API writes.
Reverting either setting does not revive an older session. Name edits, unchanged
policies, rejected authenticator codes, and pending setup preserve sessions.

Revision zero retains the original Django session hash; secret-key fallback
rotation remains supported. The user uses Django's email identity base and
permission mixin, preserving existing database fields and public name/mail
helpers. Its manager and session integration now pass mypy without suppressions.
The generated account migration adds only the security revision.

Thirteen PostgreSQL regressions verify current/previous cookies, TOTP setup and
disable, policy reversal, stale saves, retained API paths, verification counters,
identity behavior, and signing-key rotation. The combined verification set passed
528 tests before the additional inactive-account guard; focused authentication
checks cover that guard afterward. The Chromium authenticator journey also
checks an independent older session is rejected immediately after confirmation.

