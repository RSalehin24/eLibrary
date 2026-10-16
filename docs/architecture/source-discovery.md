# Source discovery

The Sources workspace exposes the configured HTTPS archive and a bounded page
limit. `SOURCE_SITE_CATALOG_URL` can specify an archive; otherwise the configured
source host's `/books/` path is used. Archive URLs must pass the same host and
credential checks as source processing. Missing or unsafe configuration produces
a disabled form without exposing credentials.

The private `/api/v1/manage/sources/discovery/` endpoint returns options and accepts
an operation UUID, configuration revision, and 1–200 pages (default 20). Commands
require processing authority and CSRF protection. They persist a logical job and
dispatch atomically; repeated commands share one operation. PostgreSQL permits
only one active discovery operation. The worker rechecks authority and the pinned
configuration before fetching and committing each page.

Archive pages use the controlled, bounded source transport and page checkpoints.
The parser reads ordinary archive links and next-page links, rejects login pages,
unsafe destinations, invalid metadata, and pagination loops. Each page contains at
most 1,000 source records. Reaching the chosen page limit records that more pages
remain rather than claiming a complete scan.

Page commits batch source inserts and updates in a transaction. Unchanged records
receive a new `last_seen_at` without changing their metadata revision. Changed
titles/authors advance the revision so an in-progress book job cannot silently
use changed input. Existing raw metadata, explicit catalog links, catalog books,
editorial content, and ownership are preserved. Discovery creates source records;
processing selected records remains a separate action or an explicitly configured
[automation](source-automations.md).

The normal Jobs workspace provides measured page/record counts, pause, resume,
and cancellation. Resuming continues from the committed next-page checkpoint,
without restarting committed pages. A failed operation remains inspectable; a
new command can collect the configured archive again safely.

Nineteen PostgreSQL cases passed for the controlled HTML-to-source workflow,
bounded pagination, record preservation, configuration/authority fencing,
idempotency, paused recovery, CSRF, input errors, and private configuration.
Source discovery does not contact an external website during these checks.
All 88 Chromium journeys passed with the source-discovery form and job controls,
including 320-pixel enlarged text. The combined backend set passed 551 cases.
Discovery and processing share PostgreSQL-backed per-host request pacing.
`SOURCE_REQUEST_INTERVAL_SECONDS` defaults to 2 and accepts 0.25–60 seconds.
The `www` alias shares the same window. Waiting holds no database transaction
and rechecks authority and cooperative stops at least once a second. Requests,
including redirects, must acquire a window before transport. Cache reads do not
consume source bandwidth. Invalid pacing configuration fails the operation.
Live broker recovery, production deployment, and capacity verification remain
required work.
