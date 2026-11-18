# Processing Real-Flow Test Matrix

This matrix mirrors the live-flow processing plan. It intentionally excludes
mocked route coverage, synthetic `remotePages` injection, seeded processing
rows, and simulated runtime interruptions for processing scenarios.

## User Stories

1. As an operator, I need Catalog Manual Sync and Catalog Automation to control one shared catalog runtime so they cannot run at the same time.
2. As an operator, I need button-started and scheduler-started runs inside the same scope to behave identically.
3. As an operator, I need `catalog-records`, `incomplete-records`, and the relevant overview cards to hydrate while sync is still running.
4. As an operator, I need search, filter, and count to stay card-local and reflect the full matched dataset, not only the rows already rendered.
5. As an operator, I need each request-state card to update independently so one card changing does not disturb unrelated cards.
6. As an operator, I need Catalog Automation to create initial requests only for records with no prior request history.
7. As an operator, I need records that leave the live `অসম্পূর্ণ বই` category after a successful incomplete run to move into `Updated`.

## Deterministic Live Scenarios

| Area | Scenario | Expected result |
| --- | --- | --- |
| Catalog runtime | Manual run ownership | Starting Manual Sync disables the Catalog Automation run control until the catalog runtime returns to idle |
| Catalog runtime | Automation run ownership | Starting Catalog Automation disables the Manual Sync run control until the catalog runtime returns to idle |
| Catalog runtime | Scheduler parity | A scheduler-started catalog automation shows the same owner/runtime behavior as a button-started catalog automation |
| Catalog cards | Records hydration during sync | `catalog-records` refetches after each fully reconciled page flush and shows the server-reported total count |
| Catalog cards | Overview hydration during sync | `catalog-overview` refetches only when aggregate counts change during the run |
| Catalog automation | Post-sync request creation | Only records with no request history receive new `initial` requests after catalog automation completes |
| Create cards | Bucket movement | `Requests`, `Queue`, `Processing`, and `Created` refetch only when rows enter or leave their own bucket |
| On Hold cards | Bucket movement | `Paused`, `Failed`, `Duplicate`, and `Deleted` refetch only when rows enter or leave their own bucket |
| On Hold cards | Created to Deleted to Create Again | A real created request moves into `Deleted`, hydrates that card, and then leaves `Deleted` again through `Create Again` |
| On Hold cards | Duplicate to New | A real duplicate request leaves `Duplicate` and re-enters live processing flow through the `New` action |
| Incomplete cards | In-run hydration | `incomplete-records` and `incomplete-overview` hydrate during incomplete sync, not only at the end |
| Updated card | Final diff movement | Records removed from the live `অসম্পূর্ণ বই` category appear in `Updated` after the final successful diff |
| Card-local filters | Search/filter/count | Counts reflect the full matched dataset for the current card filter set, even when only the first 60 rows are rendered |
| Empty state | Empty to non-empty | An empty mounted card becomes non-empty only when live matching rows actually arrive |

## Best-Effort Live Scenarios

| Area | Scenario | Result handling |
| --- | --- | --- |
| Remote source | Source site outage | Verify only if naturally observed in the real run |
| Remote source | Rate limiting or transient omissions | Verify only if naturally observed in the real run |
| Worker runtime | Worker crash or restart | Verify only if naturally observed in the real run |

## Real-Flow Coverage

- `tests/frontend/e2e/processing-pages-live.spec.js`
- `tests/scripts/test-processing-live.sh`
- Live development stack with frontend, backend, worker, processing-worker, beat, Redis, Postgres, and real source site flow
