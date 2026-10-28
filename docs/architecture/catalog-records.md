# Catalog records, intake and publication

The current implementation follows the [product specification](../application-reader-engine-plan.md).
[Implementation evidence](../application-reader-engine-progress/README.md) records
checks separately from acceptance; older physical-book and review workflows are
superseded.

## Unified records and authority

Books have title, summary, edition, publisher, language and compilation metadata.
There is no physical/digital classification, inventory price/binding, physical
reading log, or editorial approval state. Historical migrations remain immutable;
new removal migrations support initialization of an empty PostgreSQL database.
Disposable physical records must not be converted into empty books.

`POST /api/v1/manage/books/` accepts an operation UUID and whitelisted metadata.
It creates an unpublished `draft`, with indexing disabled by default. It does not
assign ownership or access grants. An active account with completed required TOTP
and current global metadata-creation authority can perform initial intake.

Existing-book metadata, cover, EPUB replacement, removal and relationship edits
require an active, TOTP-ready staff account, superuser, or current **global**
`admin:full_control` grant. Scoped full control and metadata grants do not qualify.
Scoped metadata users retain their existing authorized listing/export access and
entity workspace, with book editor/file actions hidden. Direct mutation services
reload and lock the current actor before checking administrator identity.

The creation UUID identifies the book and immutable creation audit. Replaying the
same creator's original command returns its current record; changed input or a
colliding creator conflicts. `GET /api/v1/manage/book-creations/<uuid>/` provides
an owner-only outcome check. The form retains its operation UUID and validation
draft and blocks automatic replay after an uncertain response.

## Automatic EPUB intake

The creation result accepts multipart `file` and `expected_updated_at` at
`POST /api/v1/manage/book-creations/<uuid>/epub/`. This is limited to the creator's
first unprepared draft with no source or assets. It confers no existing-book edit
right. An identical successful file replay returns the original outcome; replacing
an already completed intake requires an administrator.

Administrators replace EPUBs at `POST /api/v1/manage/books/<slug>/epub/`.
Uploads are limited to 24 MiB, within the Next.js proxy's existing 32 MiB limit.
Archive, manifest, path, expansion, encryption and resource checks run before
activation. The upload produces HTML from the retained ordered spine, including
confined links, safe local resources and supported formatting. Scripted resources
or unsupported structures fail with a recoverable validation error. Successful
reader preparation and HTML conversion activate both files atomically and publish
the book automatically. There is no separate Prepare, Review or Publish step.

The actor and catalog revision are checked again after preparation. Stale edits,
revocation and source-work conflicts prevent replacement. File and persistence
failures retain the previous active pointers. Uploaded replacements of a source
book must also pass the retained source-text proof. Archived books stay archived.
File selection and unsaved metadata are preserved on failure; uncertain outcomes
require an explicit current-result check before another submission.

## Metadata and covers

Metadata updates require `expected_updated_at`; a stale command returns a conflict.
Valid edits preserve published availability and record authoritative overrides so
source regeneration cannot silently replace them. Embedded file metadata is a
separate concern: `file_metadata_may_differ` reports saved overrides, and the editor
explains that downloads may still contain earlier information. A successful form
save does not claim to have rewritten EPUB bytes.

`POST /api/v1/manage/books/<slug>/cover/` accepts `image` and the expected revision;
`DELETE` accepts the revision. Actual PNG/JPEG/WebP bytes are checked against the
5 MiB and 2048×2048 limits, normalized to PNG, and stored under a new private name.
The final pointer, override and audit commit together after current authority and
revision checks. Explicit removal is an override too. Source regeneration retains
an administrator's chosen cover, or their removal, including the embedded EPUB
cover. Failure preserves the previous cover and publication state.

## Regeneration and removal

The editor provides bilingual Regenerate and Remove confirmation dialogs with
focus restoration and draft/pending guards. `GET .../controls/` reports the current
revision, available commands and an actionable reason when regeneration is blocked.
`POST .../regenerate/` also requires processing authority, a stable operation UUID
and a configured source. New source content, verified exports and prepared reader
resources activate through the existing background-job workflow. Catalog changes
or revoked authority prevent stale activation. Complete source preparation publishes
automatically; failed preparation can resume completed work without duplicating it.

`DELETE /api/v1/manage/books/<slug>/` requires current administrator authority,
CSRF protection and the expected revision. It marks the book removed and records
an audit; public discovery and content access stop. Personal records remain private.
Only disposable reference fixtures are used for browser removal tests.

Catalog-code allocation and title/relationship operations retain their PostgreSQL
locks and conflict handling. See [entity administration](catalog-entities.md) and
the [implementation checks](../application-reader-engine-progress/README.md) for
current evidence and remaining milestone gates.
