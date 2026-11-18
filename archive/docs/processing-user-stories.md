# Processing User Stories

Validated intent for the replacement processing runtime.

## Runtime Units

- Catalog runtime unit: shared by `Manual Sync` and `Catalog Automation`
- Incomplete runtime unit: owned by `Incomplete Automation`

## Catalog Scope

1. As an operator, I want Manual Sync and Catalog Automation to control the same catalog runtime so they never run in parallel and never produce conflicting catalog updates.
2. As an operator, I want a catalog run started by the Manual button, Automation button, or scheduler to use the same pause, resume, checkpoint, reconciliation, and completion behavior.
3. As an operator, I want the Catalog records card to hydrate during a running catalog sync so newly reconciled records appear while the run is still active.
4. As an operator, I want the Catalog overview to hydrate during a running catalog sync so aggregate counts reflect live reconciled data instead of waiting for the run to finish.
5. As an operator, I want Manual Sync disabled while Catalog Automation owns the catalog runtime and Catalog Automation disabled while Manual Sync owns it.
6. As an operator, I want pausing a catalog run to finish the current page first, then persist progress durably so resume can start from page 1 and reconcile up to the saved checkpoint.
7. As an operator, I want Catalog Automation to create initial book creation requests only for records that have never had a request before.

## Incomplete Scope

1. As an operator, I want Incomplete Automation to use the same runtime behavior whether it is started by the run button or the scheduler.
2. As an operator, I want the Incomplete records card to hydrate during an incomplete run so newly seen incomplete titles appear while the run is active.
3. As an operator, I want the Incomplete overview to hydrate during the run so incomplete aggregates reflect live source data.
4. As an operator, I want records that disappear from the `অসম্পূর্ণ বই` source category after a successful run to move into the `Updated` card.
5. As an operator, I want the `Updated` card to let me recreate or delete only those previously incomplete records that are now resolved or removed.

## Request State Pages

1. As an operator, I want the Create page cards to each own one request bucket only: `Requests`, `Queue`, `Processing`, and `Created`.
2. As an operator, I want the On Hold page cards to each own one request bucket only: `Paused`, `Failed`, `Duplicate`, and `Deleted`.
3. As an operator, I want transitions between request buckets to invalidate only the source card, destination card, and affected overview cards.
4. As an operator, I want card-local loaders and disabled controls so activity in one card never blocks unrelated cards.

## Card-Local Search, Filter, And Count

1. As an operator, I want every table card to run search and filter on the full matching dataset for that card, not only on currently rendered rows.
2. As an operator, I want card counts to show the full matched result size even when only the first batch of rows is rendered.
3. As an operator, I want a card with fewer than 60 matched rows to fully hydrate on its first response.
4. As an operator, I want cards with 60 or more matched rows to keep incremental scroll loading without changing scroll behavior.
5. As an operator, I want an empty card to become non-empty automatically when a real runtime transition adds matching rows.
6. As an operator, I want an empty card to remain empty when new rows do not match its current search or filter.

## Overview Cards

1. As an operator, I want overview cards to be backend-owned aggregate views that do not depend on loaded table rows.
2. As an operator, I want overview cards to refetch only when their own aggregates change.
3. As an operator, I want non-aggregate row changes to avoid unnecessary overview refetches.

## Minimal Push And Hydration

1. As an operator, I want the backend to push only invalidation events and tiny runtime metadata, not whole table datasets.
2. As an operator, I want the frontend to refetch only the cards named by the invalidation event.
3. As an operator, I want the backend to flush runtime invalidations at meaningful checkpoints such as page reconciliation, pause, resume, failure, completion, and post-sync request creation instead of on every small row change.
