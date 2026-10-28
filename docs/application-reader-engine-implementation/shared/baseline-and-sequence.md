# Baseline, task dependencies, and change rules

## Current repository evidence

| Concern | Inspected implementation | Consequence for the plan |
| --- | --- | --- |
| Website | `app/web/package.json`, `src/app`, `src/components`, `src/lib` | Next.js/React/TypeScript is the application to change. `app/frontend` is a parity reference. |
| Model | `app/backend/apps/catalog/models/books.py`, `choices.py`, `personal.py`, `editorial.py` | `record_type`, physical-specific metadata/logs, `review_state`, and review timestamps still exist. UI-only removal is insufficient. |
| Writes | `app/backend/apps/catalog/editorial/service.py`, `creation.py` | Metadata saves assign pending review; creation uses needs-review states. Remove those transitions with their callers. |
| Permissions | `app/backend/apps/common/permissions.py`, `apps/accounts/workspaces.py` | Scoped metadata grants currently enable editing. Book writes need the narrower administrator rule in the data plan. |
| Reader | `app/backend/apps/access/reading`, `views/reader_v1.py`; web reader components/helpers | Reuse preparation, permission, sandbox, selection, and location logic when extracting the reader. |
| Progress | `ReaderProgressSerializer`, `ReaderProgressView`, `app/web/src/lib/progress-writer.ts` | Current progress has no write revision. Define and implement conflict handling; preserve latest queued progress after failures. |
| Engine | `app/backend/apps/ingestion/{source_processing,source_discovery,engine,pipeline}`, `apps/processing` | Separate ownership through contracts, not imports of website ORM models in the new engine. |
| Export verification | `app/backend/apps/ingestion/source_processing/export_verification.py` | Existing occurrence checks do not prove package-spine order; an independent verifier is necessary. |
| Offline | `app/web/scripts/package-standalone.mjs`, `src/lib/local-epub`, PWA documentation | Coordinate one root worker and the reader's separately built public shell. |
| Tests | `tests/scripts/verify.sh`, `tests/web/playwright.config.mjs`, `app/web/package.json` | The legacy verifier builds `app/frontend`; it does not establish current website or new service acceptance. |

These are source observations, not a current browser audit. Historical screenshots, counts, catalog totals, and service ports must be rediscovered and never reported as fresh verification.

## Before application coding

- Complete the document checks in [plan review](verification/plan-review.md). This request stops at creating and verifying plans.
- When implementation is requested, execute F01 and F02 before changing application behavior. They are read-only baseline activities. Findings can expand the plan; revise and reverify affected contracts before coding against a changed decision.
- Inventory actual processes, builds, databases, broker/Redis instances, queue names, storage roots, and background writers without printing credentials. Record which isolated environment will run each suite.
- Check `git status`; retain user changes, including the original specification and PDF. Planning-time status showed those two files untracked. Never treat an untracked file as disposable.
- New dependencies require the approval required by AGENTS.md. Already approved repository dependencies do not require renewed approval. Dependency uncertainty blocks the dependent installation, not independent work.

## Ordered tasks

Each row depends on the previous gate deliberately: finish product surfaces before engine intelligence. A task is verified only when its linked plan's exit checks pass. Module plans define the behavior, affected files, regressions, and recovery boundaries.

| Task | Milestone | Depends on | Deliverable | Detailed plan |
| --- | --- | --- | --- | --- |
| F01 | M0 | None | Current issue/capability/route/section/state register and reproducible baseline | [Baseline](#baseline-records) |
| F02 | M0 | F01 | Reverified contracts, fixtures, scoped environment, and test assignments | [Contracts](contracts/service-boundaries.md) |
| W01 | M1 | F02 | Unified book schema and removal of physical/review features | [Website data](../website/data/unified-books-and-authorization.md) |
| W02 | M1 | W01 | Administrator-only book writes, API capabilities, and negative permissions | [Website data](../website/data/unified-books-and-authorization.md) |
| W03 | M1 | W02 | Automatic preparation/publication for source and uploaded books | [Website data](../website/data/unified-books-and-authorization.md) |
| W04 | M1 | W03 | Shared design system, admin/reader shells, and bilingual formatting | [Website interface](../website/interface/design-and-route-matrix.md) |
| W05 | M1 | W04 | Catalog, directories, details, personal library, pagination, and exports | [Website workflows](../website/workflows/behavior-and-failures.md) |
| W06 | M1 | W05 | Notes, authentication, profile, Kindle, and information pages | [Website workflows](../website/workflows/behavior-and-failures.md) |
| W07 | M1 | W06 | Creation, unfinished, management, schedules, users/access/mail flows | [Website workflows](../website/workflows/behavior-and-failures.md) |
| W08 | M1 | W07 | Entire website visual, functional, permission, and parity acceptance | [Website gate](../website/README.md) |
| R01 | M2 | W08 | Independent reader build, proxy, health, and session integration | [Reader service](../reader/service/extraction-and-offline.md) |
| R02 | M2 | R01 | Reading canvas, tools, fullscreen, and one command registry | [Reader experience](../reader/experience/commands-layout-and-state.md) |
| R03 | M2 | R02 | Current-book anchors, revisioned progress, search, and annotations | [Reader experience](../reader/experience/commands-layout-and-state.md) |
| R04 | M2 | R03 | Rich content, isolated local EPUB, offline shell, and update coordination | [Reader service](../reader/service/extraction-and-offline.md) |
| R05 | M2 | R04 | Reader quality, parity, security, and service integration acceptance | [Reader gate](../reader/README.md) |
| E01 | M3 | R05 | Independent engine runtime, logical database/storage, and private transport | [Engine module](../engine/README.md) |
| E02 | M3 | E01 | Frozen full-catalog audit and 200/100 reference split | [Corpus plan](../engine/corpus/audit-and-local-inference.md) |
| E03 | M3 | E02 | Real local inference benchmark and measured execution budget | [Corpus plan](../engine/corpus/audit-and-local-inference.md) |
| E04 | M4 | E03 | Evidence-preserving collection, blocks, and structural interpretation | [Pipeline](../engine/pipeline/structure-entities-and-publication.md) |
| E05 | M4 | E04 | Evidence-based identities/roles and canonical document | [Pipeline](../engine/pipeline/structure-entities-and-publication.md) |
| E06 | M4 | E05 | HTML/EPUB generation, independent verification, and atomic handoff | [Pipeline](../engine/pipeline/structure-entities-and-publication.md) |
| E07 | M4 | E06 | Material updates, schedules, fencing, idempotency, and recovery | [Engine operations](../engine/operations/jobs-updates-and-recovery.md) |
| E08 | M4 | E07 | Corpus correctness, fault handling, and engine acceptance | [Engine gate](../engine/README.md) |
| REL01 | M5 | E08 | Clean application initialization and canaries | [Release](../release/initialization-and-acceptance.md) |
| REL02 | M5 | REL01 | Full integration, evidence reconciliation, and user visual/UX acceptance | [Release](../release/initialization-and-acceptance.md) |

## Baseline records

F01 records every source issue ID and newly found defect with route, role, language, viewport, state, reproduction steps, expected result, screenshot, root cause, task, regression, and evidence. Keep the full page-section inventory even where a portion is not applicable; record why.

Compare the retained frontend and embedded reader with the pinned baseline in [feature parity](../../operations/feature-parity.md). For each capability record `present`, `missing`, `incomplete`, `intentionally_removed_or_changed`, or `verified`, its new destination, and interaction evidence. Physical features, type classification, reviews, historical-data migration, and obsolete URL compatibility are intentionally removed. A prior passing count closes nothing in this revision.

F02 records the precise service route table, field/state definitions, permission matrix, failure scenarios, fixture ownership, and commands from these plans. It checks discovery findings against these definitions. Runtime ports are environment configuration, not product requirements. F02 changes a plan only with a recorded reason and repeat of its affected plan checks.

F01/F02 are not considered executed by the document validator. The pre-code entry gate requires current issue/route/section/state evidence, runtime/resource ownership, explicit readiness of required approved tooling, and a walkthrough of the publication-context, schedule/projection, progress/read-once and failure contracts. If a case still lacks an expected result or reveals a contradiction, record it in the gap audit and resolve/reverify the affected plan before coding. These read-only discovery tasks are authorized only when requested; this turn does not start product implementation or claim their evidence exists.

## Atomic changes and recovery

Update a schema, serializers, callers, generated clients, fixtures, and relevant regressions together. Generate new Django migrations through its tooling; never edit an existing migration. Stop affected development writers for schema resets or coordinated incompatible changes. Unsupported service contract versions fail explicitly; do not retain removed development APIs as compatibility layers.

Before merging a task's change into a usable development build, establish its happy path, failed/pending behavior, cancellation/permission behavior, and rollback boundary. For code regressions restore the last usable code/build without discarding unrelated source edits. For disposable schema experiments use a correctly scoped fresh initialization; a down migration that restores removed product features is not a release strategy.

Never clear queues, rebuild service-worker assets, reseed browser fixtures, or run Redis integration tests while another acceptance run depends on those resources. Keep discovery/schedule tests sequential. Commit, push, and production deployment remain separate actions requiring an explicit request.
