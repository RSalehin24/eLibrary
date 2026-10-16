# Password-link confirmation and account setup

`/create-password/` and `/reset-password/confirm/` share the new Bengali
password-link form. `/api/v1/auth/password-links/inspect/` checks a link, and
`/api/v1/auth/password-links/confirm/` consumes it. Both anonymous POST operations
require same-origin CSRF and share a separate 20/hour anonymous limit. The retained
password-reset-request limit remains 5/hour.

## Link and password rules

The nonce-backed generator is shared with the retained invitation/reset system.
The configured six-hour lifetime remains unchanged. Validation rejects missing,
malformed, disabled-account, superseded, consumed, and expired links. Inspection
returns only the setup/reset purpose and whether TOTP setup is required; it does
not disclose email addresses, account IDs, devices, or tokens.

Confirmation locks the user, validates the current token, enforces matching
passwords with a 12-character minimum and Django's configured password validators,
changes the password, advances the nonce, and updates the account revision in
one transaction. Concurrent confirmations have one winner. A successful password
change invalidates old authenticated sessions. Unknown fields are rejected;
failed validation leaves the link usable.
Workspace login preserves literal leading/trailing password spaces and shares
the 4096-character input bound with password creation. The retained login view
keeps its existing serializer; the versioned view selects the stricter serializer.

Signed-in accounts must sign out before using a link. Existing confirmed TOTP
devices are preserved; resetting a password cannot produce a verified-device
session. An account that requires unfinished TOTP setup receives a restricted
session and continues to Profile. It cannot read/manage/deliver until setup is
complete. Optional setup/reset accounts continue to the ordinary login flow.

## Browser behavior

The form accepts fragment credentials and retained query-string email links,
then removes the credentials from the visible URL. They are submitted in POST
bodies and remain in browser memory while the page is open. They are not stored
in local storage, rendered into server HTML, or cached by the service worker.
Newly queued email links should use fragments to keep credentials out of HTTP
request URLs; the retained query-link sender is unchanged.

Passwords and partial edits participate in unload/app-update guards. Correctable
400 errors retain editable fields; uncertain confirmation disables submission
and directs the reader to check login or reopen the latest mail link. There are
no automatic confirmation retries. Reopening a fragment link on the same page
reloads and validates it, including after successful consumption; an old success
screen is not reused. Native unload protection still applies to unfinished edits.

Both routes are `noindex`, contain generic server HTML, and remain outside the
public sitemaps. No new dependencies were installed and no external mail was sent.

## Verification boundary

Twenty-three PostgreSQL cases cover privacy, real CSRF, throttling, strict fields,
password rules, sessions, required/optional setup, device preservation, invalid
identifiers, expiry/supersession, and a real concurrent confirmation. The focused
run with retained authentication passed 41 cases before adding the strict-field
case; the subsequent combined access/link check passed 44. The shared validation
check also passed with editorial cases (74 total).

Five focused Chromium checks passed against the standalone build: reset and
old-session invalidation, consumed-link reopening, required setup at 320 pixels,
correctable/uncertain outcomes, invalid-link privacy, and the app-update guard.
Two Node helper cases cover fragment/query parsing and duplicate/missing/oversized
credentials. TypeScript, ESLint, mypy (111 files), Ruff, OpenAPI validation,
migration consistency, architecture policy, and the production build passed.
The combined platform run passed 464 backend tests and all 82 Chromium journeys.
The literal-password-space regression failed before the serializer fix and passed
afterward; seven password-link/login/workspace browser checks passed on the final
artifact with passwords containing spaces. Existing file-size/legacy-suite
failures remain recorded in the foundation document.

This is the confirmation/setup step. [Queued account mail](account-mail.md) now
adds anonymous reset requests, invitation creation/resend, and private outcomes.
Live SMTP task transport through RabbitMQ remains unverified. Physical devices
and supported Firefox/WebKit checks remain
unverified. The full reader/administration phases remain incomplete.
