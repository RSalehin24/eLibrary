# Processing Use Cases

These use cases are intended to be executed against the real development application.

## UC-01 Manual Catalog Sync Start And Hydration

- Entry conditions: catalog runtime is idle.
- Trigger: operator clicks `Start Sync` on the Catalog manual sync card.
- Runtime scope: `catalog`
- Expected behavior:
  - catalog runtime owner becomes `manual`
  - manual sync card enters `syncing`
  - automation run control becomes disabled
  - each fully reconciled source page invalidates `catalog-records`, `catalog-overview`, and `catalog-sync`
  - mounted catalog records card refetches and hydrates with newly reconciled rows
  - mounted catalog overview refetches only if aggregates changed

## UC-02 Manual Catalog Pause And Resume

- Entry conditions: a live manual catalog sync is in progress.
- Trigger: operator clicks `Pause`.
- Runtime scope: `catalog`
- Expected behavior:
  - runtime enters `pausing`
  - current source page finishes first
  - checkpoint is stored in the database and mirrored in Redis
  - owner remains `manual`
  - manual card exposes `Resume`
  - resume starts from page 1, reconciles previously saved rows through the saved checkpoint, then continues with new pages

## UC-03 Catalog Automation Run Button

- Entry conditions: catalog runtime is idle and catalog automation settings are already saved.
- Trigger: operator clicks the catalog automation run button.
- Runtime scope: `catalog`
- Expected behavior:
  - runtime owner becomes `catalog_automation`
  - manual run button becomes disabled
  - sync behavior matches UC-01 and UC-02 except the owning controller is the automation card
  - after sync completion, initial requests are created only for records with no prior request history
  - post-sync request creation invalidates `catalog-overview`, `create-requests`, and `create-overview`

## UC-04 Catalog Automation Scheduler Run

- Entry conditions: catalog automation is enabled and due by saved wall-clock settings.
- Trigger: real beat scheduler starts the due run.
- Runtime scope: `catalog`
- Expected behavior:
  - runtime owner becomes `catalog_automation`
  - UI behavior matches UC-03
  - if manual sync already owns the runtime, the scheduled automation waits and does not take ownership until the catalog runtime returns to idle

## UC-05 Incomplete Automation Start And Hydration

- Entry conditions: incomplete runtime is idle.
- Trigger: operator clicks the incomplete automation run button or the scheduler starts it.
- Runtime scope: `incomplete`
- Expected behavior:
  - runtime owner becomes `incomplete_automation`
  - source fetch uses the live `অসম্পূর্ণ বই` category only
  - each reconciled page invalidates `incomplete-records`, `incomplete-overview`, and `incomplete-automation`
  - mounted incomplete records card hydrates as new incomplete rows are discovered
  - final resolved/removed diff invalidates `incomplete-records`, `Updated`, and `incomplete-overview`

## UC-06 Create Page Bucket Movement

- Entry conditions: a real request exists in `initial`.
- Trigger: background worker advances the real pipeline.
- Runtime scope: request pipeline
- Expected behavior:
  - `initial -> queued` invalidates `create-requests`, `create-queue`, and `create-overview`
  - `queued -> processing` invalidates `create-queue`, `create-processing`, and `create-overview`
  - `processing -> created` invalidates `create-processing`, `create-created`, and `create-overview`

## UC-07 On Hold Bucket Movement

- Entry conditions: a real request moves into a holding state.
- Trigger: pause, failure, duplicate resolution, or delete action.
- Runtime scope: request pipeline
- Expected behavior:
  - `processing -> paused` invalidates `create-processing`, `on-hold-paused`, `create-overview`, and `on-hold-overview`
  - `processing -> failed` invalidates `create-processing`, `on-hold-failed`, `create-overview`, and `on-hold-overview`
  - duplicate decisions invalidate only duplicate-related cards plus any destination card and overviews affected by bucket changes

## UC-08 Card-Local Search, Filter, Count, And Empty-State

- Entry conditions: a table card is mounted with card-local search/filter state.
- Trigger: live invalidation refetch caused by runtime progress or a row transition.
- Runtime scope: card-local fetch
- Expected behavior:
  - refetch preserves the current `q`, `category`, and `status`
  - count reflects full matched result size for that card and those filters
  - if new rows match the filters, they appear
  - if new rows do not match the filters, the card remains unchanged
  - if the card was empty and now has matching rows, the empty state is replaced

## UC-09 Created To Deleted To Create Again

- Entry conditions: a real request exists in `create-created`.
- Trigger: operator deletes the created request and then uses `Create Again` from `on-hold-deleted`.
- Runtime scope: request pipeline
- Expected behavior:
  - deleting the created request moves the row into `on-hold-deleted`
  - the previously empty or smaller Deleted card hydrates with the real row
  - `Create Again` removes the row from `on-hold-deleted`
  - the same request re-enters live processing flow and appears in a non-deleted request bucket

## UC-10 Duplicate To New

- Entry conditions: a real request exists in `on-hold-duplicate`.
- Trigger: operator marks the duplicate request as `New`.
- Runtime scope: request pipeline
- Expected behavior:
  - the row leaves the Duplicate card
  - the request re-enters live processing flow
  - duplicate-card search/filter/count remain server-backed for the full matching dataset throughout the transition
