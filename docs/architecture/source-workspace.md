# Source inspection workspace

Linked-book results now show a title/author cover, editorial state and direct
editing/job actions. **Read Book / Continue Reading** and **Open HTML** appear
above the actual EPUB/HTML files, availability and attachment downloads. HTML
opens a separate tab; the reader opens the prepared EPUB session. These controls
reuse the public book page's reading behavior and existing account permissions;
processing authority alone grants neither HTML preview nor reading access.

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

Both pages are private, `no-store` at the API, and `noindex`. The creation page
combines catalog sync, title/author search, status filters, and a compact book
table. Fetch All, Process All and Schedule Automation stay visible above the
summary panels, including on phones. Manual Upload opens existing manual book
creation. Selection and Process All remain distinct: select-all excludes
unavailable entries and respects the 100-book maximum; Process All queues the
entire eligible catalog through a durable parent job. Source lists, counts and
schedules refresh every fifteen seconds while visible, and active operations
poll every two seconds. Read failures offer a visible retry action.
Refreshes retain selected snapshots. Each available row can also start one book.
On phones table rows become stacked records, with selection controls still
visible. English/Bengali switching preserves selections and form values.
The pages preserve ordinary page/filter links. The source detail labels the
information as requiring editorial verification before publication. External
links explicitly open another tab with `noopener noreferrer`. Invalid schemes,
credentials, whitespace/control characters, malformed hosts/ports, and sensitive
query/fragment values are not exposed as source hyperlinks.

The source detail is a book-result workspace. Its heading is the book title and
current editorial state; generated files and direct editing/review controls are
primary. The source URL and last-seen date are secondary provenance. A linked
book does not repeat the creation form. The detail polls for the new book after
processing, so it does not strand the user on an outdated unlinked record.
Generated EPUB and HTML rows show availability, size and permission-scoped
downloads. EPUB existence and online-reader preparation are distinct states;
already prepared files do not offer a redundant preparation request.

Detail responses include only content counts: chapter count, character count
and an advisory completeness flag for a chapterless text shorter than 1,000
characters. This is a review aid, not proof that longer texts are complete.
Book bodies are loaded only for this detail summary and are not returned; the
paginated list retains its existing bounded projections and a null summary.
Short source introductions remain unpublished review drafts and display an
explicit warning before the file actions.

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
The preceding verification describes the original inspection increment. Later
automation, broker and live-source evidence is recorded in the implementation
handoff. Full metadata inspection and complete original-application workflow
parity remain separate acceptance work.
