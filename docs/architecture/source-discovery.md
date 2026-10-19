# Source discovery

The Sources workspace exposes the configured HTTPS archive and a bounded page
limit. `SOURCE_SITE_CATALOG_URL` can specify an archive; otherwise the configured
source host's `/books/` path is used. Archive URLs must pass the same host and
credential checks as source processing. Missing or unsafe configuration produces
a disabled form without exposing credentials.

The private `/api/v1/manage/sources/discovery/` endpoint returns options and accepts
an operation UUID, configuration revision, and 1–200 pages (default 20). `fetch_all`
instead follows the archive through its terminal page, with a 2,000-page safety
ceiling. Reaching that ceiling with another page remaining fails visibly as
`source_catalog_scan_limit`, preserving earlier results. The main Fetch All
button and optional Fetch Pages form show progress and cooperative controls
inline, without leaving the selectable catalog. Commands
require processing authority and CSRF protection. They persist a logical job and
dispatch atomically; repeated commands share one operation. PostgreSQL permits
only one active discovery operation. The worker rechecks authority and the pinned
configuration before fetching and committing each page.

`catalog_scope=unfinished` selects the same website's `/genres/অসম্পূর্ণ-বই/`
archive; the scope is pinned into the command and configuration revision. The
separate `/manage/unfinished/` screen filters source provenance, not failed
exports. Each committed entry preserves other raw metadata and records the scan.
A complete unbounded scan resolves records absent from the category. Partial or
failed scans retain earlier unfinished flags. An empty first page is accepted
only for a recognized unfinished archive, where it means no unfinished books.

Catalog refresh also checks published unfinished books against their published
source signature. The signature includes body text, chapter links, pager counts
and the source modification timestamp, excluding rotating pager nonces. Private
list responses select only the small `source_update` JSON field rather than the
complete source payload. The Unfinished Books screen exposes Updates Available,
last-check time and an Update Book link. A complete scan retains a completion
notice for books removed from the source's unfinished category until their new
edition is published. Successful publication resets the comparison baseline.
These provenance checks preserve the catalog revision used by queued work.
Failed checks retain their previous evidence and are retried on the next refresh.

Archive pages use the controlled, bounded source transport and page checkpoints.
The parser reads ordinary archive links and next-page links, rejects login pages,
unsafe destinations, invalid metadata, and pagination loops. Each page contains at
most 1,000 source records. Reaching the chosen page limit records that more pages
remain rather than claiming a complete scan.

Facet-based archives use the same text-anchor extraction as the retained resolver,
skipping cover-only links. Their JavaScript pager is followed through server-side
`_paged` queries while preserving existing filters. A recognized empty archive page
ends a scan after books have been collected. An empty first page, an unrecognized
layout, malformed listings, or repeated page contents fail visibly; they never
produce a successful zero-book sync. Earlier committed pages remain available.
Historical zero-book successes are labeled “No Books Found” in the interface and
link back to catalog sync. Successful results link to book selection and creation.

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
The test counts above describe the original discovery increment. Current results
and remaining deployment/capacity acceptance limits are recorded in
[the implementation handoff](../implementation-handoff.md).
