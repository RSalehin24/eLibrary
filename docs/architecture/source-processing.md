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
The overview's **ওয়েবসাইট থেকে বই তৈরি / Create from Website** shortcut opens
catalog sync and the selectable book table. **সব বইয়ের তথ্য আনুন / Fetch All**
collects the full catalog; **নির্বাচিত বই তৈরি করুন / Create Selected Books**
queues the selected records. Manual entry/upload remains a separate direct link.

## Collection and checkpoints

The worker uses the shared manifest collector and curated-document pipeline.
Its transport requires HTTPS, verified TLS, an explicitly configured host,
bounded timeouts, and at most five redirects. Redirect destinations are checked
before another connection. It does not use the legacy direct-IP/TLS fallback.
Responses are limited to 8 MiB; source HTML checkpoints and documents are limited
to 64 MiB and collection to 2,000 pages. Optional source authentication cookies
are read from the existing protected configuration file, bounded and limited to
configured domains. Credentials are never returned by the workspace.

Optional covers permit the configured source host, its `www` alias and that
host's `cdn.` subdomain. CDN images use a separate bounded transport with source
authentication cookies cleared. Redirects stay within that CDN host; book and
chapter URLs retain the stricter source policy. Downloaded covers must verify
as JPEG, PNG or WebP with at most 20 million pixels. Unavailable, disallowed,
invalid or oversized optional media falls back to a generated cover. A remote
URL remains provenance and is never treated as a local export file.

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

New books start in `needs_review` internally while processing, displayed as Draft.
Manual editorial approval is not required. Successful automatic verification and
reader preparation publish the book; indexing eligibility remains explicit. The source's direct catalog relationship supports alternate URLs from
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
before success, and publication requires those resources to be ready.

Verification reruns document validation against fetched-page evidence, requires
all available contents pages and chapters, and compares collected source text
with its assigned book sections. Generated HTML and EPUB body text must match
the curated content. Missing text blocks publication, even when earlier stored
validation reported success. Short complete source text remains valid. The source
website's unfinished category is separate from extraction/export failures.

Automatic publication rechecks permissions, source/book/asset revisions and stop
requests under locks, records its evidence in the audit log and checkpoints the
publication transaction. Recovery after publication verifies the pinned edition
instead of publishing twice. Old jobs or sourced records without verification
evidence require regeneration before a manual publish command can succeed.
Publication feedback explains the required action in Bengali and English rather
than treating every blocked check as a stale edit. Manually added records without
a source retain direct publication. If that step fails, recovery reuses completed
exports and checks their pinned asset
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

## Process All

`GET/POST /api/v1/manage/sources/process-all/` exposes eligible counts and creates
one durable `process_catalog` parent. It requires processing authority, CSRF,
an operation UUID and the displayed configuration revision. There is at most one
active catalog batch. The worker snapshots eligible, pre-existing unlinked
sources in batches of 50 using a UUID cursor, excluding active and failed work.
It rechecks permission/configuration and pins each source revision before
dispatch. Deterministic child identifiers and saved pending batches allow
pause/resume or attempt recovery without duplicate book jobs. This action is
independent of the current filter, page and explicit-selection limit of 100.

Inline progress and job detail distinguish queued and rejected entries, with
links to child jobs filtered by `parent_job`. Pause Queueing and Stop Queueing
control dispatch of remaining entries; already queued book jobs continue. Parent
success means queueing finished, not that every child book has completed or been
published. Existing book jobs have their own progress and recovery controls.
Generated drafts still require editorial review; an available introduction alone
does not prove that the source supplied the complete published book.

## Inspecting generated files

`GET /api/v1/manage/books/<slug>/assets/` returns each file's availability,
download URL, online-reader readiness and active preparation identifier, without
storage paths. Existence is checked independently of the saved `ready` status.
The source-result page and book editor show EPUB/HTML downloads, missing-file
states and preparation controls near the beginning of the workflow. Editorial
save/review/publish actions stay visible above the long form.

`GET /api/v1/manage/assets/<uuid>/download/` requires global processing authority
and the existing book download entitlement, rechecked on every request. A
processing-only grant does not create download authority. Disabled accounts,
removed books, missing/failed assets and unsupported formats are rejected.
Development streams actual file bytes; production uses the existing protected
Nginx redirect. Both return an attachment with the correct EPUB/HTML MIME type,
private/no-store, noindex and nosniff headers. HTML attachments also use a sandbox
policy; raw generated HTML is not rendered inside the application.

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
