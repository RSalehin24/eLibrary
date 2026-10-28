# Implementation state

Read the [handover entry](README.md) first. This records source changes as of
28 October 2026; application evidence was produced on 21 October unless stated.

## Milestones and acceptance

| Tasks | Actual state |
| --- | --- |
| F01/F02 | Baseline route/issue inventory and contract/environment walkthrough recorded |
| W01 | Unified schema/removal implementation; generated new migrations; prior backend gate passed |
| W02 | Administrator book writes, indirect entity protection and explicit identities implemented; latest UI capability changes need fresh build/browser verification |
| W03 | Automatic EPUB/HTML/reader preparation, publication, first intake and cover replacement implemented; prior backend/core browser evidence exists |
| W04–W07 | Retained website updated; current workflow/state/profile verification unfinished |
| W08 | Open: recorded browser failures, latest-source rebuild, remaining profile/state/visual checks and user acceptance |
| R01–R05 | Independent reader not started |
| E01–E08 | Independent engine/local inference/corpus work not started |
| REL01/REL02 | Initialization/release acceptance not started; no deployment performed |

The [website gate](../../application-reader-engine-implementation/website/README.md)
states: “Record the user's visual/UX acceptance separately from automated checks.
If it has not occurred, W08 remains awaiting acceptance and engine work does not
proceed through this gate.” The task dependency table also makes W08 a prerequisite
for R01. Do not interpret “Implement” as evidence that visual acceptance occurred.

## Data and API changes

- Removed book physical/digital classification, physical inventory/reading logs,
  manual binding/price, review states/timestamps/models and duplicate-review flows.
- Removed physical and obsolete alias pages/APIs, manual book publish/review
  endpoints and physical XLSX export. Reading-list publication remains intentional.
- Renamed ordinary bibliographic fields to `publisher`, `language`, `is_compilation`.
  Added `Book.metadata_overrides` to preserve administrator changes on regeneration.
- Retired query/body fields fail API validation; website and saved-filter links
  discard retired browsing constraints. Generated OpenAPI/TypeScript were updated.
- Removed the zero-valued `editorial_pending` overview compatibility field.

Generated new migrations, applied previously on the empty disposable reference:

| App | Migration |
| --- | --- |
| access | `0016_alter_permissiongrant_scope.py` |
| catalog | `0028_remove_physicalreadinglog_book_and_more.py` |
| catalog | `0029_book_metadata_overrides.py` |
| ingestion | `0015_remove_booksubmission_review_state_and_more.py` |
| ingestion | `0016_delete_duplicatereview.py` |

Historical migrations and original specification/PDF remain intact. The separate
user preview retains its older schema; these incompatible removals require a
deliberate environment decision, not an automatic preview migration.

## Authorization and identity

`apps/common/permissions.py:is_book_administrator` centralizes active,
TOTP-ready staff/superuser/current global `admin:full_control` authority. Scoped
admin/metadata grants, ownership or intake alone do not confer existing-book edits.
Modern and retained legacy metadata/files/regeneration/deletion writes use the
appropriate guard and revision checks. Non-admins retain authorized inspection
and exports; book edit/file controls are hidden.

Contributor/category/series edits that affect books require an administrator.
Kind locks protect association/edit races. An administrator entity edit advances
affected book revisions and records relationship overrides. Reading-list curation
is the explicit exception and does not mutate book metadata.

Contributor and series names are no longer unique identity keys. New
`EntitySourceBinding` uses namespace/source key and an exactly-one-target database
constraint. Explicit UUIDs and source bindings provide replay without name-only
merging. Selectors show catalog codes and submit UUIDs.

Primary seams: `catalog/editorial/{entity_service,relationships,service}.py`,
`catalog/entity_identity.py`, `catalog/models/entity_identity.py`,
`catalog/discovery/management.py`, workspace/access serializers and managed forms.

## Intake, assets and publication

Successful EPUB uploads prepare protected reader resources and ordered
EPUB-derived HTML before atomically activating files and publishing. Empty intake
stays unpublished; archived books are not implicitly republished. Stale authority,
revision conflicts, invalid content and storage/database failures preserve prior
active pointers. Unsupported/active resources fail explicitly.

`epub_html.py` / `epub_html_resources.py` retain spine ordering, scope anchors/CSS,
and handle safe embedded resources with explicit encoding/size limits. Existing
source-text checks and preparation are reused. The normal source preparation path
publishes automatically after validation, without human review.

`epub_intake.py` permits a creator's first EPUB for their own empty draft creation.
It supports identical-checksum replay, rejects a changed replay and grants no
subsequent ownership or existing-book edit capability.

Cover upload/remove validates actual PNG/JPEG/WebP bytes, size/dimensions, stages
immutable files and commits revision/audit/override together. Source regeneration
preserves both an explicit cover and explicit removal, including embedded EPUB
cover bytes. `common/images.py` shares image validation with profile uploads.
The editor warns that saved catalog metadata can differ from embedded file metadata.

## Website, reader boundary and tooling

Current UI is **`app/web` (Next.js/React/TypeScript)**. `app/frontend` is the retained
Vite parity reference; legacy README/verifier commands do not establish M1 acceptance.
The integrated reader still lives inside the website/backend. Header wrapping was
fixed for narrow/enlarged text; Kindle filter grid minimums were corrected.

The layout spec now checks all five widths at normal and 200% text in both
languages. Five Playwright projects now select all specifications rather than a
mobile subset. `run_isolated.py` gained the approved pinned Firefox container path
with read-only source/private writable artifacts; its three tooling tests passed.

Other module splits preserve public seams and the 300-line policy: book-list
serializers; legacy date handling; submission links; ingestion job configuration,
controls and recovery. Two old exec-loaded test facades now use explicit module
imports. Do not rerun old ignored mutation scripts; prior syntax/import issues
were corrected and the broad backend suite passed afterward.

## Latest changes not yet covered by a new production build

These were made after the last served build and complete Chromium run began:

1. Managed entity detail adds `can_edit`; linked non-admin entity forms show a
   bilingual read-only explanation. Seven new backend cases passed inside a
   47-case focused run. New `linked-entity-permissions.spec.mjs` has not run.
2. Selected contributor labels **and accessible action names** now include catalog
   codes; the same-name browser regression checks the code before and after reload.
   This latest component/regression change has not run against a fresh build.
3. Two legacy intake guidance translations now describe automatic EPUB publication;
   the affected unit assertions were updated but not rerun after that change.
4. Browser fixes: account uses configured base URL; jobs expects current upload
   success copy; responsive test separates scoped inspection from admin editing;
   overview expects the removed review counter to be absent. Some were picked up
   later in the run; account/jobs still require reruns.

OpenAPI and client were regenerated for `can_edit`; repeated-generation identity
after this latest regeneration still needs verification. Mypy with the backend
import path, including a clean non-incremental run, passed on 293 configured files.

The exact failure list and restart order are in
[verification and next steps](verification-and-next-steps.md).
