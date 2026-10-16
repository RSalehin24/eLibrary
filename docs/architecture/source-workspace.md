# Source inspection workspace

`/manage/sources/` and `/manage/sources/<uuid>/` provide the first source-workflow
step: inspect discovered records, check their exact catalog relationship, and
prepare an existing linked book's EPUB or request source processing. The `/api/v1/manage/sources/` routes
require the existing global processing permission or staff/full-control policy.
Metadata-only editors, access-only managers, and readers cannot enter them.

## Efficient reads and permissions

Source title/author filtering and linked/unlinked/removed filters run in SQL
before pagination. Pages default to 50 records, cap at 100, and sort by normalized
title with UUID tie-breakers. Source/book matches use the unique normalized URL
relationship in `BookSource` or an explicit direct catalog link; they do not infer
a match from similar titles. Active and latest operation references are bounded
SQL subqueries, allowing failed linked drafts to reach their recovery workspace.

Matching books and edit permissions are batched after pagination. Source raw
payloads and book bodies are not selected or serialized. The 100-record check
retains at most eight queries and verifies their SQL excludes those large fields.
The serializer returns title, author line, source URL, timestamps, a small book
reference, and the backend-derived edit flag. No whole-catalog snapshot is built.

Metadata permission is independent of processing permission. A processor can
request preparation for an existing linked book without gaining an edit grant
or ownership. Editing links appear only for metadata-authorized books. Removed
books retain a source relationship for review without an editing/preparation action.

## Interface and privacy

Both pages are private, `no-store` at the API, and `noindex`. Cards adapt to narrow
screens and preserve ordinary page/filter links. The source detail labels the
information as requiring editorial verification before publication. External
links explicitly open another tab with `noopener noreferrer`. Invalid schemes,
credentials, whitespace/control characters, malformed hosts/ports, and sensitive
query/fragment values are not exposed as source hyperlinks.

The initial source summary shows only title/author/linkage; full metadata and raw
source inspection remain later workflow work. List refreshes are bounded and
abortable. The existing protected EPUB-preparation component supplies a trackable
job from linked-source detail pages. Source inspection does not publish a book.

## Verification and remaining scope

Sixteen PostgreSQL cases passed for permissions, pagination, SQL filters,
metadata grants, removed/missing records, bounded reads, large-field exclusion,
and unsafe/sensitive hyperlinks. Four focused Chromium journeys passed for
private search/pagination, denied workspaces, phone source details, processing
without a metadata grant, and 200% text at 320 pixels. The phone screenshot was
inspected. TypeScript, ESLint, mypy (127 files), Ruff/formatting, OpenAPI validation,
migration consistency, and the production build passed.
The combined run passed 464 backend tests and all 82 Chromium journeys, including
all eight required viewport widths. The same 18 pre-existing file-size violations
and broader legacy-suite failures remain recorded in the foundation document.
After the final label-spacing adjustment, all fourteen source/responsive checks
passed again and the updated phone detail screenshot was inspected.

Source processing, duplicate/incomplete decisions, draft recovery, and explicit
bulk outcomes are now described in [source processing](source-processing.md).
Source discovery and refresh are described in [source discovery](source-discovery.md).
Full metadata inspection, automation, and
live broker recovery remain required work. No external source site was queried by
these tests and no phase is marked complete from this inspection increment.
