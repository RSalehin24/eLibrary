# Processing Pages Implementation Audit

This document describes the real implementation of the processing pages as of 2026-05-27.

It is based on the frontend routes/components and backend views/services, not on the existing processing docs.

**Note:** The six-page processing model described in earlier sessions has been replaced with a four-page model. Old `/processing-*` routes now redirect to the new routes.

## Verification Performed

- Frontend unit tests: `./tests/scripts/test-frontend-unit.sh`
- Backend test suite: `bash tests/scripts/test-backend.sh`
- Processing Playwright spec: `npm run test:e2e:existing-server -- processing-pages.spec.js --workers=1` from `app/frontend`

## Real Page Model

The processing section currently routes to four pages:

- `Catalog` -> `/catalog` (was `/processing-catalog-books` and `/processing-automation`)
- `Create` -> `/create` (was `/processing-my-requests`)
- `On Hold` -> `/on-hold` (was `/processing-failed-requests` and `/processing-duplicate-requests`)
- `Incomplete` -> `/incomplete` (was `/processing-incomplete-check`)

Additionally, two standalone processing pages exist:

- `/multipage-toc` — Multi-page table of contents processing
- `/reprocessing` — Book reprocessing queue

The routing is defined in [app/frontend/src/features/app/AppRoutes.jsx](../app/frontend/src/features/app/AppRoutes.jsx). Old routes redirect with `<Navigate>`.

The page components are exported from [app/frontend/src/features/processing/BookProcessingPages.jsx](../app/frontend/src/features/processing/BookProcessingPages.jsx):

- `CatalogProcessingPage` from `processing-pages/CatalogProcessingPage.jsx`
- `CreateProcessingPage`, `OnHoldProcessingPage`, `IncompleteProcessingPage` from `processing-pages/QueueProcessingPages.jsx`

## Shared Card Families

### Overview Cards

These are summary-only cards with no row actions.

- `Catalog Overview` (on `/catalog`)
- `Create Overview` (on `/create`)
- `On Hold Overview` (on `/on-hold`)
- `Incomplete Overview` (on `/incomplete`)

They each show counts for their respective pipeline buckets.

### Submission List Card Family

Implemented in `QueueProcessingPages.jsx` as `CreateCard` and `OnHoldCard`. Cards:

- `/create`: `Requests`, `Queue`, `Processing`, `Created`
- `/on-hold`: `Paused`, `Failed`, `Duplicate`, `Deleted`

The request cell shows:

- a primary request label
- a secondary URL/host line when the input is a URL
- an inline error detail column on the `Failed` card

Single-row actions are conditional by card:

- `Created`: `Open` when `linkedBookSlug` is set
- `Paused`: `Resume`, `Delete`
- `Failed`: bulk `Retry`, `Delete` only (no per-row buttons)
- `Duplicate`: `New`, `New Edition`, `Duplicate`, `Delete`
- `Deleted`: `Create Again`

Bulk actions by card:

- `Requests`, `Queue`: `Delete selected`
- `Processing`: `Pause selected`, `Delete selected`
- `Created`: `Delete selected` (also deletes the linked book)
- `Paused`: `Resume selected`, `Delete selected`
- `Failed`: `Retry selected`, `Delete selected`
- `Duplicate`: `New selected`, `New Edition selected`, `Duplicate selected`, `Delete selected`
- `Deleted`: `Create Again selected`

### Processing Job Card Family

Rendered as `Processing` on the `/create` page only.

Columns:

- request
- status
- step
- updated
- action

Step labels come from [jobTypeLabel](app/frontend/src/features/processing/helpers/request.js):

- `ingestion` -> `Create`
- `resolution` -> `Match`
- `reprocess` -> `Regenerate`

Single-row actions:

- `Open`: when the target book exists
- `Recreate`: retries if the target book record was deleted
- `Start`: resumes a queued job without a task id
- `Stop`: stops an active job
- `Resume`: resumes a stopped job
- `Retry`: retries a failed job by retrying the submission
- `Delete`: deletes the job history row when not active

Bulk actions:

- `Resume selected`
- `Stop selected`
- `Delete selected`

### Duplicate Card Family

Visible only on `/on-hold` as the `Duplicate` card.

Columns:

- request
- duplicate review status
- action

Single-row actions:

- `New`: dismiss duplicate and queue a new book
- `New Edition`: treat as a new edition of the existing book
- `Duplicate`: confirm the existing book match
- `Delete`

Bulk actions:

- `New selected`
- `New Edition selected`
- `Duplicate selected`
- `Delete selected`

### Failed Jobs Card Family

Visible on `/on-hold` as the `Failed` card.

Columns:

- request
- updated
- inline error detail

Visible actions are bulk-only:

- `Retry selected`
- `Delete selected`

There are no per-row action buttons on this card.

### Run History Card Family

Visible on `/catalog` (catalog automation runs) and `/incomplete` (incomplete automation runs).

Columns:

- run summary
- status
- mode
- updated
- action

Single-row actions:

- `Stop`: when the run is `queued` or `processing`
- `Delete`: remove the run from history

Bulk actions:

- `Stop selected`
- `Delete selected`

### Catalog Books Card Family

Visible only on `Catalog`.

Columns:

- book
- categories
- curation status
- local book
- updated
- action

Top controls:

- search
- status filter
- sort
- page size
- pagination
- sync catalog / stop sync

Bulk actions:

- `Create selected`
- `Delete selected`

Single-row actions:

- `Open`: when the local book exists and the catalog row is `ready`
- `Create`: create a book from a `new`, `failed`, `stopped`, `unfinished`, `deleted`, or `requeued` row
- `Resume`: same button path as `Create`, but the label becomes `Resume` when the row status is `stopped`
- `Delete`: delete the catalog row

The actual "create is still running" tracking for this card is implemented through `catalogCreationTracker` plus [resolvePendingCatalogCreationEntries](app/frontend/src/features/processing/helpers/catalog.js).

### Incomplete Catalog Card Family

Visible only on `Incomplete Requests`.

Columns:

- book
- local categories
- source categories
- synthetic status
- action

Top actions:

- `Reload`
- `Reprocess selected`

Single-row action:

- `Reprocess`

The row status here is derived locally:

- `ready` when the book was removed from unfinished
- `unfinished` when the catalog still marks it unfinished
- `needs_review` when the book is missing from the catalog snapshot

### Removed From Unfinished Card

Visible only on `Incomplete Requests`.

Columns:

- book
- updated

Actions:

- none

It is just a filtered informational list with search and range filters.

## Page-By-Page Inventory

## `/catalog` — Catalog

Rendered by [app/frontend/src/features/processing/processing-pages/CatalogProcessingPage.jsx](../app/frontend/src/features/processing/processing-pages/CatalogProcessingPage.jsx)

Visible cards:

- `Catalog Overview`
- `Catalog Sync` (manual sync)
- `Automation` (catalog automation settings)
- `Catalog Books`

What is unique here:

- `Catalog Sync` and `Automation` share the same catalog runtime so they cannot run in parallel.
- `Catalog Books` is the only catalog snapshot browser with sync, sort, paging, and create-from-catalog actions.
- Create progress is tracked until the catalog entry reaches a terminal state via `catalogCreationTracker` in [app/frontend/src/features/processing/helpers/catalog.js](../app/frontend/src/features/processing/helpers/catalog.js).

Current notes:

- duplicate outcomes surface through the On Hold page, not as a first-class catalog snapshot status
- consolidated from the old `/processing-catalog-books` and `/processing-automation` pages

## `/create` — Create

Rendered by [app/frontend/src/features/processing/processing-pages/QueueProcessingPages.jsx](../app/frontend/src/features/processing/processing-pages/QueueProcessingPages.jsx) as `CreateProcessingPage`.

Visible cards:

- `Create Overview`
- `Requests`
- `Queue`
- `Processing`
- `Created`

What is unique here:

- The full create pipeline is visible in one place: requests → queue → processing → created.
- `Created` rows expose an `Open` link directly to the book when available.
- Delete on `Created` rows also deletes the linked book.

Current notes:

- replaces the old `/processing-my-requests` page

## `/on-hold` — On Hold

Rendered by [app/frontend/src/features/processing/processing-pages/QueueProcessingPages.jsx](../app/frontend/src/features/processing/processing-pages/QueueProcessingPages.jsx) as `OnHoldProcessingPage`.

Visible cards:

- `On Hold Overview`
- `Paused`
- `Failed`
- `Duplicate`
- `Deleted`

What is unique here:

- All four hold states — paused, failed, duplicate, deleted — are consolidated onto one page.
- `Failed` exposes an inline error reason column; all actions on this card are bulk-only.
- `Duplicate` supports three resolution paths: `New`, `New Edition`, and `Duplicate` (confirm match).
- `Deleted` only allows `Create Again` bulk action.

Current notes:

- replaces the old `/processing-failed-requests` and `/processing-duplicate-requests` pages
- the old "Deplicate" typo has been corrected to "Duplicate"

## `/incomplete` — Incomplete

Rendered by [app/frontend/src/features/processing/processing-pages/QueueProcessingPages.jsx](../app/frontend/src/features/processing/processing-pages/QueueProcessingPages.jsx) as `IncompleteProcessingPage`.

Visible cards:

- `Incomplete Overview`
- `Automation` (incomplete-check automation settings)
- `Incomplete` (read-only list of currently incomplete records)
- `Updated` (records resolved since the last run)

What is unique here:

- `Automation` controls when the incomplete-check run fires.
- `Incomplete` is read-only: records are reconciled by the backend automation, not by per-row operator action.
- `Updated` rows can be recreated or deleted after resolution.

Current notes:

- replaces the old `/processing-incomplete-check` page
- `Updated` replaces the old `Removed from Unfinished` card

## Clear Bugs

### 1. Catalog sync stop is optimistic in the UI but not safely cancellable in the backend

Frontend stop flow:

- [CatalogProcessingPage.jsx](../app/frontend/src/features/processing/processing-pages/CatalogProcessingPage.jsx) sets optimistic runtime state immediately when the user pauses sync, before the backend confirms the stop

Backend stop flow:

- [cancel_source_catalog_refresh in services/curation.py](../app/backend/apps/ingestion/services/curation.py) revokes the Celery task and immediately finalizes the refresh state as stopped/idle
- [process_source_catalog_refresh in services/curation_support/source_refresh.py](../app/backend/apps/ingestion/services/curation_support/source_refresh.py) then calls `TitleResolver().refresh_catalog(...)`
- [TitleResolver.refresh_catalog in services/resolution.py](../app/backend/apps/ingestion/services/resolution.py) has no cooperative cancellation checks inside its page loop

Result:

- the UI can show "stopped"
- the persisted refresh state can already be idle
- the background sync work can still keep fetching/upserting catalog pages until the worker is actually killed or the loop finishes

This matches the reported behavior: start sync, stop it, but syncing continues in the background.

### 2. Selection checkboxes are generally not locked during pending actions

Across the submission, job, duplicate, failed-job, and run-history tables:

- bulk buttons usually disable correctly while `bulkActionKey` is active
- row action buttons usually disable correctly while `busyActionId`, `busyRunId`, or global lock flags are active
- select-all checkboxes and row checkboxes are usually still enabled

This is visible in the card and action components inside `QueueProcessingPages.jsx` and `CatalogProcessingPage.jsx`.

Effect:

- while a single or bulk action is pending, the user can still change row selection
- that does not satisfy the requested lock rule that selection and actions should stay disabled until the action finishes

### 3. Incomplete-page reprocess is only tracked until queueing returns, not until the request finishes

`Catalog Books` correctly keeps `Create` locked through tracked pending work.

`Incomplete` records are read-only in the current implementation. The `Updated` (resolved) card does allow `Recreate` and `Delete` bulk actions, but tracking does not continue until the resulting request reaches a terminal state:

- the busy lock is set only around the recreate API call
- after the API returns, the lock is released
- there is no equivalent to the catalog page's `catalogCreationTracker`

Effect:

- `Recreate selected` can stop showing loading even though the resulting request is still queued or processing
- controls can re-enable before the request reaches a terminal state (`created`, `paused`, `failed`, `duplicate`)

### 4. On Hold page does not distinguish originating pipeline stage

Rows on `/on-hold` (Paused, Failed, Duplicate, Deleted) do not carry a label for whether they came from the Create pipeline or from another source. The `origin` field is preserved but is not exposed as a user-visible filter.

Effect:

- operators cannot narrow On Hold rows by the page the request came from
- the stored `origin` value is not surfaced as a filter on `/on-hold`

## Requires Structural Change Or Explicit Product Direction

These are not small one-line fixes.

- If failed and on-hold rows must be filterable by the pipeline stage they came from, that originating stage has to be stored on the request row in a way richer than the current `origin`.
- If create tracking must continue until terminal state for rows recreated from `/incomplete`, an equivalent to the catalog page's `catalogCreationTracker` must be added for the Incomplete `Updated` card.
- If checkbox selection must be locked during pending bulk or row actions, a selection-lock flag needs to be wired into every card's checkbox and select-all rendering path.

## Existing Test Coverage Gaps

The current automated coverage is useful, but it does not fully prove all behavior.

Covered today:

- shared helper logic
- catalog tracked create loading/disable behavior
- basic pause/resume/delete flows on visible queue cards
- mocked catalog sync start/stop UI behavior
- automation settings save and persist flows

Not covered well enough:

- true backend cancellation of source catalog refresh after stop
- checkbox lock behavior during single and bulk actions on every card family
- incomplete-page recreate tracking until terminal state
- filtering on-hold rows by originating pipeline stage
