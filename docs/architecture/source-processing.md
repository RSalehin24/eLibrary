# Source processing and recovery

Administrators with global processing authority can request a book from an
unlinked, configured source through `/manage/sources/<uuid>/`. Each command pins
the source revision and has a client-generated operation UUID. The transaction
creates the durable job and dispatch together. Repeating that UUID with the same
command returns the same operation; a changed command or an already active source
returns a conflict. Requests never create ownership or access grants.

Automated book creation has one source website. `SOURCE_SITE_HOST` supplies its
hostname and `SOURCE_SITE_CATALOG_URL` optionally overrides its HTTPS catalog
path; application code and navigation contain no provider name. Only that host
and its `www` alias are permitted. A different website in
`SOURCE_SITE_FALLBACK_HOSTS` makes the configuration invalid rather than adding
another provider. Existing manual record entry and EPUB upload remain available.
The overview's **উৎস থেকে বই আনুন** shortcut opens the collection controls and
the three visible steps: collect listings, select books, request preparation.

## Collection and checkpoints

The worker uses the shared manifest collector and curated-document pipeline.
Its transport requires HTTPS, verified TLS, an explicitly configured host,
bounded timeouts, and at most five redirects. Redirect destinations are checked
before another connection. It does not use the legacy direct-IP/TLS fallback.
Responses are limited to 8 MiB; source HTML checkpoints and documents are limited
to 64 MiB and collection to 2,000 pages. Optional source authentication cookies
are read from the existing protected configuration file, bounded and limited to
configured domains. Credentials are never returned by the workspace.

HTML pages are stored as protected immutable artifacts, with the committed index
referenced by the job checkpoint. Page boundaries recheck actor permissions,
source revision, attempt ownership, and requested pause/cancellation. Resuming
uses stored pages rather than fetching them again. A stale attempt can create an
unreferenced artifact but cannot replace a committed checkpoint.

The worker validates the curated title and content before creating a catalog
draft. Conservative exact normalized-title candidates require an administrator's
decision. A PostgreSQL advisory transaction lock prevents concurrent source jobs
from silently creating the same title. An existing primary source relationship
is never reassigned by the worker.

## Drafts, exports, and decisions

New books start in `needs_review`, without indexing eligibility or editorial
approval. The source's direct catalog relationship supports alternate URLs from
the configured website without replacing an existing `BookSource` or changing
the linked book.

The admin job detail supports fetching again, linking an inspected duplicate,
creating a separate draft, resuming an unfinished draft, and cancellation. The
backend derives valid choices from current state. Linking checks both job and
candidate revisions; it preserves the candidate's metadata, assets, and owners.
Incomplete source content requires attention before a book is created.

Exports use the canonical curated document, including short Bengali body
sections. A completed export manifest records relative paths, sizes, and checksums
so pause/resume reuses completed HTML and EPUB files. Completed files are copied
to immutable names in protected asset storage before one transaction updates
asset references. Previous valid files remain available. Publication rechecks
the actor, source, catalog revision, and current attempt and honors a late stop
request. Source drafts cannot be published with unresolved work or missing HTML
and EPUB assets. Source processing prepares checksum-addressed reader resources
before success, and publication requires those resources to be ready. If that
step fails, recovery reuses completed exports and checks their pinned asset
revision instead of replacing them.

Failed exports can resume the existing unchanged draft. A manual recovery decision
starts a fresh allowance of three automatic failures while retaining every
attempt. This prevents an exhausted historical retry count from permanently
stranding a linked draft. Changed catalog content requires inspection and repair;
the worker does not silently replace it.

## Explicit bulk requests

`POST /api/v1/manage/sources/process-selection/` accepts 1–100 explicit records,
each with a unique source UUID, operation UUID, and expected revision. Each record
has its own transaction and result. The response reports accepted operations and
rejected records individually. Unknown records, conflicts, and validation errors
do not undo other accepted records.

The workspace retains failed selections and their snapshots for correction and
removes accepted selections. An uncertain response disables another submission
and exposes the original operation links. No bulk or resolution mutation is
automatically replayed. Pending selections and decisions participate in the PWA
unsaved-work guard. Source lists and job summaries omit source HTML and book
bodies; issue details use the compact checkpoint summary.

## Verification and remaining work

The source increment adds 51 PostgreSQL tests, including the real
collection/curation/catalog/export workflow with a controlled HTTP adapter,
concurrent requests and duplicate titles, stale decisions, permission revocation,
page/export recovery, cancellation, and preservation of previous assets. The
combined backend verification set passed 515 tests. The source requests made by
these tests never connect to an external website.

Discovery/refresh and automations, shared source request pacing, live RabbitMQ
execution/recovery, production Nginx delivery, physical devices, and measured
capacity remain required. These local results do not complete a delivery phase.
