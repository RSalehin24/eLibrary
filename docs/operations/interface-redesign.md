# Admin and reader interface redesign — 21 October 2026

This implements the separately approved admin and reader designs. It supersedes
previous UI acceptance claims in the older sitewide review; previous feature and
external acceptance records remain historical evidence.

## Navigation and page structure

| Area | Implemented behavior |
| --- | --- |
| Admin home | `/manage/` opens Book Creation, or the first section the account may use. The operational overview remains at `/manage/overview/`. |
| Admin shell | Six permission-filtered sections: Book Creation, Books, Authors & Categories, Processing, Schedules and Users. Desktop sidebar and labelled mobile drawer. Reader View keeps the same account. |
| Reader home | Signed-in readers open My Books; their selected Reader View persists across reloads. My Books, Browse Books, Notes and Kindle form the main navigation and phone bottom tabs. |
| Account menu | Profile, paper books, local EPUB and help are secondary destinations. Sign In stays visible for guests. Language changes preserve form values. |
| Branding | One shared wordmark includes বাংলা পাঠাগার. No repeated adjacent name, underlined navigation or decorative heading counters. |
| Context | Related author/category/series/reading-list pages retain Browse as the active section. Unfinished books retain Book Creation. |

## Admin workflows

Book Creation exposes Fetch All, Process All, Upload EPUB, Add Paper Book and
Schedule Automation for authorized accounts. Website Catalog and Unfinished
Books are local tabs. Selection actions appear after selection. Existing
request IDs, revision checks, uncertain-response protection and real job
receipts remain in use; an accepted request opens its progress receipt.

The books page defaults to a compact table with covers, linked authors,
categories, lifecycle state, Edit and Files. The editor places metadata first and links to files
and history without discarding unsaved forms. Real reading, new-tab HTML, EPUB
and Kindle controls continue to use the existing permission and availability APIs.

Schedules have direct Run Now and settings/history actions. Search and state
stay visible; frequency and ordering use an optional panel. Creation groups task,
catalog scope and timing, followed by a summary. Reset restores all fields,
including the displayed and submitted twelve-hour time. Next-run display remains
in Asia/Dhaka.

Users have a compact search/state/sort row and an account table. Account details
link to Profile, Access, Security and Mail History. Existing self-edit restrictions,
grants, bulk access, invitation and mail uncertainty controls remain intact.

Processing preserves automatic recovery, actionable next steps and technical
job details. Source rows use the actual active job state, so queued, running,
retrying, paused and attention states no longer all display Running. UUIDs and attempt/checkpoint information remain in expandable
technical sections instead of becoming the main explanation of a job.

## Reader workflows

Default book lists start with a compact title and search/sort row. Author,
category, series and **Reading List / পাঠতালিকা** conditions use an inline panel.
Saved searches remain available from a compact control, outside the search form.
A failed search offers Retry and does not falsely report an empty library.

My Books retains All, Owned, Saved, Recent and Granted views. Continue Reading
uses the existing private recent-reading feed and permission API; completed
books are excluded. Resume opens the actual saved reading session. Expired
permission and unavailable preparation are explained rather than producing an
empty action area.

Cards retain covers and save/Kindle actions. Tables reserve horizontal action
space so delayed account controls do not move metadata links. Book details and
the EPUB reader retain their reading, download, annotation, search, fullscreen,
text-size and viewing-mode capabilities.

Notes has four reachable views, aligned search/color controls, book groups,
separate note editing and Open in Reader actions, and distinct empty, no-match,
loading and recoverable error states. Kindle history uses compact search/state/
ordering controls and optional author/category/series conditions; resend still
requires recipient confirmation.

## Retired filters and contributor corrections

Book-type and added/request-date controls are removed from browsing filters.
Website links containing `record_type`, `created_after`, `created_before`,
`from_date` or `to_date` remove those constraints and reset pagination while
preserving other conditions. Saved-filter links discard the same retired keys.
The backend continues validating its legacy API contracts. Book type remains in
book creation/metadata; scheduling and expiry dates remain functional.

The public writer directory defaults to authors. Other contributor roles remain
explicit choices. Public rows show names and book counts without catalog codes
or added timestamps. Collection directories use the same compact structure.

Automatic extraction uses explicit source credits and verified spelling aliases,
without fuzzy person merging. Four verified preview books received audited
credit corrections: translator attribution, a malformed cover credit, duplicated
publisher prose and a non-credit sentence. Books, contributor identities, files,
notes and source evidence are retained. `সূচীপত্র` remains a valid publisher.

`repair_source_credits` defaults to a dry run. `--apply` records before/after
relationships and metadata history. `--restore AUDIT_ID --apply` restores their
original IDs only if no later credit edit conflicts. Processing was restarted
with a warm shutdown to load the extraction fix; delivery workers remain stopped.

## Verification

Build, ESLint, strict TypeScript, all 149 web units, configured mypy and the
additional credit modules pass. Backend checks pass with warnings treated as
errors: 827 catalog/auth/ingestion tests, 918 processing/access tests and 61
common/tooling tests. The 205-test normalization/credit repeat overlaps those
gates. Source status projection retains the existing eight-query bound for
one hundred rows. OpenAPI and generated clients include the additive state field.

The browser inventory includes all 54 page templates through 67 concrete
route/state variants. It retains overflow, visibility, permissions, pagination
and delayed-control assertions, and checks both phone and desktop at 200% text.
`workspace-design.spec.mjs` additionally enforces the approved result-placement,
row-density, navigation, error-recovery, schedule-reset and resume behavior.

Final browser matrix results are being recorded in the sitewide review. Populated
preview pages were inspected in both languages at desktop and phone sizes.
Simulated browser evidence does not establish physical-device installation,
external Kindle delivery or an absolute absence of bugs.
