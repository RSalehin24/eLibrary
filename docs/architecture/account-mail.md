# Queued invitations and password reset requests

The Users & Access workspace now creates invited accounts, resends setup links,
and shows private mail operations. `/reset-password/` accepts anonymous reset
requests. Both flows use the existing persisted jobs, attempts, outbox dispatcher,
and `delivery` queue. Serving requests never open SMTP connections.

## Account and permission boundary

`POST /api/v1/manage/invitations/` accepts an operation UUID, email, name, and
required-TOTP policy. Global access management is required. The transaction
creates an ordinary active account with an unusable password, pending setup,
and its mail job/dispatch. It assigns no staff flags, privileges, grants, or book
ownership. Case-insensitive existing emails and unknown privilege fields fail.
Identical operation IDs return the original request; conflicting reuse returns 409.

`POST /api/v1/manage/users/<id>/invitation/` requires the current account revision
and a new operation UUID. It applies the existing protected-account policy,
advances the setup nonce, and queues mail atomically. This invalidates old links
and supersedes old queued mail. Completed/disabled accounts cannot resend setup.
Invitation delivery rechecks current account state and administrator authority.

`/api/v1/manage/users/<id>/mail/` provides bounded, paginated invitation history.
`/api/v1/manage/mail/<uuid>/` provides status and revision-checked pause/cancel/resume.
These require access management and an editable target. Reset operations are
excluded. Processing-only managers cannot list, inspect, or control account mail
through either interface. Raw input, tokens, email bodies, and addresses are not
returned. All responses and pages are private/no-store/noindex.

## Anonymous reset and receiving links

`POST /api/v1/auth/password-reset/` requires real CSRF and the retained five/hour
anonymous limit. It returns the same generic 202 response for eligible, missing,
disabled, unusable-password, and pending-setup accounts. It exposes no job ID or
public status lookup. A five-minute durable account cooldown prevents concurrent
requests from repeatedly invalidating links. Eligible requests advance the nonce
and queue a job in one transaction. Signed-in users use Profile instead.

The worker generates nonce-backed links with credentials in URL fragments, so
HTTP navigation does not include them. Tokens and complete links are never saved
in job inputs/checkpoints. A fingerprint of the relevant account revision detects
password, login, email, nonce, or setup changes before submission. The existing
[confirmation/setup endpoints](password-links.md) consume links transactionally,
preserve literal password spaces, and enforce the required-TOTP setup gate.

## SMTP and recovery

Configure `EMAIL_BACKEND`, SMTP host/port/credentials/TLS, sender, and
`FRONTEND_BASE_URL` in the secure environment. The worker requires configured SMTP;
console output cannot expose a password link. The frontend origin must be HTTPS
or local HTTP, without credentials, paths, query, or fragment. No cloud mail
provider is required. SMTP connections have bounded timeouts.

Account text mail and Kindle attachments share the checked SMTP adapter and error
classification. Confirmed acceptance and terminal success commit together. An SMTP
disconnect or database interruption after submission produces `needs_attention`;
stale `sending` attempts also require review. None automatically resends. Known
transient rejection retries with the existing bounded backoff/failure budget.
Cancellation is cooperative before submission; confirmed late acceptance remains
recorded. Acceptance by the mail service does not prove inbox arrival.

The mail status page exposes actionable states without invented percentages.
Visible polling uses two seconds while active, fifteen while idle, backoff after
failure, and no hidden-tab polling. Uncertain writes retain their original UUID
and disable resubmission. Invitation/reset drafts guard app updates and unloads.

## Verification boundary

Tests cover idempotency, concurrent creation/resend/reset, CSRF, throttles,
protected accounts, supersession, role isolation, SMTP rejection/uncertainty,
database interruption after acceptance, stale attempts, cancellation, and real
loopback SMTP. Forty-two new backend cases also verify an accepted invitation
through password consumption and the required-TOTP gate; the combined mail
platform run passed 454 backend cases. Chromium covers phone controls, resend, generic reset feedback,
uncertain writes, all eight widths, 200% text at 320 pixels, and app-update guards.
The full browser run passed 78 journeys; phone/desktop invitation screenshots
were inspected. No dependencies were added and no external email was sent.

Live RabbitMQ dispatch/interruption remains unverified pending the existing image
approval. Production SMTP/domain setup and real inbox arrival require authorized
infrastructure. Bulk per-record invitation outcomes, remaining administration,
physical installation, portable deployment, and capacity acceptance remain work.
