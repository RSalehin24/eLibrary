# Processing Live Test Matrix

All scenarios below are intended for the real development application with no mocked processing data or synthetic remote page payloads.

## Deterministic Live Scenarios

| Area       | Scenario                                       | Runtime Scope                   | Expected Result                                                                                               |
| ---------- | ---------------------------------------------- | ------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Catalog    | Manual sync start                              | `catalog`                       | Manual card becomes owner, automation run is disabled, catalog records hydrate during the run                 |
| Catalog    | Manual pause and resume                        | `catalog`                       | Current page finishes, checkpoint persists, resume restarts from page 1 and reconciles through checkpoint     |
| Catalog    | Automation run button                          | `catalog`                       | Automation card becomes owner, manual run is disabled, runtime behavior matches manual flow                   |
| Catalog    | Automation scheduler start                     | `catalog`                       | Scheduler-started run behaves the same as run-button start and appears on the automation card                 |
| Catalog    | Post-sync request creation                     | `catalog`                       | Only records with no request history receive new initial requests                                             |
| Catalog    | Search/filter/count                            | `catalog-records`               | Search/filter are server-side and count reflects full matched dataset                                         |
| Catalog    | Empty card hydration                           | `catalog-records`               | Empty card becomes non-empty when live matching rows are reconciled                                           |
| Create     | Requests to Queue to Processing to Created     | request pipeline                | Only affected cards and create overview refetch on each real transition                                       |
| On Hold    | Paused / Failed / Duplicate / Deleted movement | request pipeline                | Only source, destination, and affected overview cards refetch                                                 |
| On Hold    | Created to Deleted to Create Again             | request pipeline                | Deleted card hydrates from the real row and the recreated request leaves Deleted for a live processing bucket |
| On Hold    | Duplicate to New                               | request pipeline                | Duplicate card loses the real row and the request re-enters live processing flow without mocked transitions   |
| Incomplete | Run button start                               | `incomplete`                    | Incomplete records hydrate during the run and updated records appear after final diff                         |
| Incomplete | Scheduler start                                | `incomplete`                    | Scheduler run behaves the same as run-button start                                                            |
| Incomplete | Search/filter/count                            | `incomplete-records`, `Updated` | Counts reflect full matched datasets and filters stay card-local                                              |
| Overviews  | Aggregate-only refresh                         | all overview cards              | Overviews refetch only when their own aggregates change                                                       |

## Best-Effort Live Scenarios

| Area           | Scenario                                       | Runtime Scope            | Result Handling                                            |
| -------------- | ---------------------------------------------- | ------------------------ | ---------------------------------------------------------- |
| Remote source  | Source site outage during sync                | `catalog` / `incomplete` | Verify behavior only if naturally observed in the live run |
| Remote source  | Rate limiting or transient source failures     | `catalog` / `incomplete` | Verify behavior only if naturally observed in the live run |
| Worker runtime | Worker crash or restart during processing      | request pipeline         | Verify behavior only if naturally observed in the live run |
| Source drift   | Temporary omission of incomplete-category rows | `incomplete`             | Verify behavior only if naturally observed in the live run |

## 300-Book EPUB Structure Regression

The harness at [tests/scripts/regression_curate_300.sh](../tests/scripts/regression_curate_300.sh) scrapes and exports up to 300 source site URLs sampled in [test-artifacts/source-site-audit-selection.json](../test-artifacts/source-site-audit-selection.json) and runs [apps/ingestion/pipeline/epub_structure_audit.py](../app/backend/apps/ingestion/pipeline/epub_structure_audit.py) on each produced EPUB.

Asserted invariants per book:

- spine order is `cover → title → info? → dedication? → front_section_* → toc → (lesson_+ | main_content) → back_section_* → nav`;
- the EPUB-3 `nav.xhtml` is comprehensive — it links to every readable page in the book (cover, title, info, dedication, front sections, the printed TOC page, content chapters, back sections) and never to itself; the printed `toc.xhtml` is content-scoped — it lists only content chapters (and back sections when present);
- `nav.xhtml` does not link to itself;
- no content/front/back page is blank (visible text after tag/whitespace stripping).

Run:

```
tests/scripts/regression_curate_300.sh                  # full 300-URL pass
tests/scripts/regression_curate_300.sh --limit 25       # smoke
tests/scripts/regression_curate_300.sh --retry-failed   # rework failures from prior runs
```

State is persisted to `/app/storage/regression-300/state.json` inside the backend container after every URL, so the harness is fully resumable across crashes and container restarts. Exit code is `0` only if every recorded URL has verdict `ok`.

## Acceptance Notes

- No Playwright route mocking is allowed for processing runtime coverage.
- No synthetic `remotePages` payload injection is allowed for processing runtime coverage.
- No seeded synthetic processing rows are allowed.
- Real data creation is allowed only through the real application flow itself.
