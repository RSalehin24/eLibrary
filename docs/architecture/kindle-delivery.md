# Asynchronous Kindle delivery

`/kindle/` shows the account's requests. Public/private book actions link to a
recipient selector when the backend grants Kindle access. Readers explicitly
select up to ten addresses currently configured in their profile. Ownership or
an active book/category/author/global SEND_KINDLE grant is required independently
of reading/download/metadata permissions. Required TOTP setup still precedes
private workspaces.

`GET/POST /api/v1/delivery/books/<slug>/kindle/` provides private options and
accepts a revision-checked command. The body contains a client-generated
operation UUID, asset revision, and explicit recipient selection. The backend
normalizes/deduplicates addresses, checks current configuration/permissions,
pins the ready asset, and creates the job/outbox transactionally. An identical
operation returns its existing status; conflicting reuse returns 409. Serving
requests never open SMTP or read the EPUB. Responses use 202, `operation_id`,
and an owner-only `status_url`.

`GET /api/v1/me/kindle/` uses a bounded, owner-bound signed cursor feed.
`GET/POST /api/v1/delivery/operations/<uuid>/` returns the account's own outcome
and accepts revision-checked cancellation. History and cancellation remain
available after book permissions change. Other accounts receive 404. Responses
are private/no-store/noindex, with no storage paths or raw job input. CSRF applies
to commands. Administrative job access remains a separate global permission.

## Worker and delivery meaning

The dedicated `delivery` queue uses the persisted job/attempt/dispatch mechanism
described in [background jobs](background-jobs.md). The worker snapshots bounded
bytes, calculates SHA-256, and reuses the pinned checksum on resume. It checks
current permission, account state, asset revision/book binding, configured
sender, and selected address before each submission. Replaced/missing/empty
assets, revoked permissions, removed addresses, and invalid headers stop work.
Header/MIME validation precedes network submission.

Each address is a processing unit. Confirmed SMTP acceptance and the personal
last-send record commit together before another address is attempted. Accepted
indices are skipped on retry. Pause/cancel is cooperative between units. A late
cancel cannot hide a completely accepted operation or recall earlier messages.
Known 4xx SMTP rejections retry within the job's bounded failure budget;
permanent rejections stop with visible per-address outcomes.

Connection loss during submission or a database failure after SMTP acceptance
produces `needs_attention`, with the affected address marked uncertain. It never
retries automatically. Interrupted workers at `sending` have the same recovery
rule. Confirmed addresses stay recorded, while unstarted/rejected/uncertain
addresses remain distinguishable. SMTP QUIT failure does not erase acceptance.

The UI says **the mail server accepted the message**. It does not claim arrival
on a Kindle device. Readers must check their device and Amazon's approved-sender
configuration. An uncertain command keeps its original operation link and
disables another submission until the outcome is inspected. A known 400
selection error leaves addresses editable and preserves the command identifier.
Private options/forms and pending commands participate in PWA update protection.

## Configuration and limits

Use a real SMTP backend with `EMAIL_HOST`, `EMAIL_PORT`, appropriate TLS/SSL,
credentials when required, and `ACCOUNT_INVITE_FROM_EMAIL`/`DEFAULT_FROM_EMAIL`.
An unauthenticated private relay is supported. The retained Brevo configuration
maps EPUB attachment delivery to SMTP. Console/dummy backends cannot represent
successful delivery in the new workflow. Timeouts accept 1–60 seconds; TLS and
SSL cannot both be enabled. Configuration readiness describes validated settings,
not a live connection or a guarantee of downstream delivery.

`KINDLE_MAX_ATTACHMENT_BYTES` defaults to **20 MiB** and accepts 1 KiB–128 MiB.
This is an application memory/workload policy, not an asserted Amazon/provider
limit. The selector shows the configured bound; large files fail before opening
SMTP. The operator must choose a bound compatible with the relay and workers.
Background soft/hard limits are documented in the jobs guide. Allow processing,
heartbeat, and SMTP connections in resource budgets.

Email configuration and download-name helpers are reused by the retained
routes. Their existing behavior remains covered by compatibility tests.
No new packages were installed for this increment. Credentials, book bytes,
addresses, and provider responses are not included in job diagnostic codes or
broker messages.

## Verification boundary

The combined PostgreSQL suite passed 464 selected tests, including runtime limits
and administrative account/grant checks. These include scoped access, owner-only history,
CSRF, revisions, idempotency, cursor/query bounds, partial sends, resumed work,
asset replacement, permission/address changes, late cancellation, and database
interruption after acceptance. A loopback SMTP server verified real SMTP/MIME
acceptance and a disconnect after message data; repeated delivery did not resend
the uncertain message. No external email was sent.

The production artifact passed 82 complete Chromium journeys, including the
Kindle update/enlargement checks. Recipient selection/correction, cancellation,
uncertain-command handling, private isolation, and all eight planned widths were
covered. The phone selector screenshot was inspected. OpenAPI, strict typing,
Ruff/formatting, ESLint, Node helpers, and build checks passed.

Live RabbitMQ transport/recovery, end-to-end device arrival, administrative
uncertainty resolution, supported cross-browser/physical-device checks,
production routing/configuration, and measured capacity remain outstanding.
The full legacy suite is not passing. This increment does not complete the
reader/reliability phases or authorize production deployment/external mail.
