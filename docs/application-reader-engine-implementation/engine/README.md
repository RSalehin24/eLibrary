# Curation and creation engine: M3–M4

Begin E01 only after W08 and R05 acceptance. Contract design is done during F02, but new intelligence must not delay the required website/reader delivery order.

| Plan | Tasks and responsibility |
| --- | --- |
| [Corpus and local inference](corpus/audit-and-local-inference.md) | E02 complete inventory/reference truth; E03 real local benchmark and resource budget |
| [Structure, entities, and publication](pipeline/structure-entities-and-publication.md) | E04 blocks/hierarchy; E05 identities/canonical document; E06 generation/independent verification/activation |
| [Jobs, updates, and recovery](operations/jobs-updates-and-recovery.md) | E07 scheduling, material updates, faults, fencing, retries and restart |
| [Private interface v1](../shared/contracts/private-engine-v1.md) | E01 transport/status/control/schedules; E06 durable publication receipts |

## E01: service separation

Existing code is under `app/backend/apps/ingestion/{source_processing,source_discovery,source_workspace,catalog_processing,engine,pipeline}`, `apps/processing/{jobs,automations}`, and catalog curated-document models. Read these modules, their IO seams and tests before moving responsibility. Retain pure parsers/exporters/validators where correct; replace website ORM coupling at the service boundary rather than duplicating the pipeline.

Create planned `app/engine` with its own Django settings, logical PostgreSQL database/least-privilege role, storage root, named queues, API, worker and scheduler entrypoints, health/readiness, schema and tests. Use approved Python/Django/Celery/HTTP tooling. Source evidence, curated blocks/entities/documents, source jobs, update probes and schedules become engine-owned. Use new generated migrations and fresh development initialization, not edits to old migrations or cross-service foreign keys.

Website retains catalog/publication/user data and Kindle/account-mail jobs. Source/job/schedule browser APIs become authorized adapters to private engine operations; batch UI reads use bounded status projections. Switch scheduling to exactly one engine scheduler during a quiesced handoff. Website source workers and schedules must stop producing commands before ownership changes. Do not migrate historical queues/checkpoints or run two schedulers against the same source.

Implement durable outbox/inbox/receipt records, source/book context reservations, monotonic job projections, current authority checks, contract versioning, minimum worker/receipt fencing and engine-only artifact staging before replacing an in-process call. These are E01 cutover prerequisites even though E06/E07 later extend publication and recovery. Website owns its copied active files; engine owns generated candidate files. An engine restart or missing model cannot make a prepared website book unreadable. Independent configuration/build/start/test evidence must show the engine cannot read/write website ORM tables directly.

E01 exit includes signed/private-route negative cases, duplicate/lost-response delivery, generated contract consistency, service restart/isolation, and a deterministic no-inference canary through artifact staging. That canary proves integration only; it does not establish semantic accuracy or pass E03/E08.

## E08 acceptance

- Account for every record in the frozen source catalog; totals reconcile with explicit source-unavailable/ambiguous/defective reasons. Source-incomplete is a separate fact, never an excuse for skipped text.
- Maintain 300 source-grounded reference works split into 200 development/100 held-out works, keeping related work/edition/component groups together while covering observed layouts in both sets. Every expected source block, section boundary/order, supported entity and contributor role must be correct for every reference case. Aggregate metrics or relabelling a hard case unevaluable cannot excuse a known wrong case.
- Run actual pinned local inference, measure memory/disk/latency/throughput and projected full-catalog runtime, and publish evaluation results by layout/role/language plus individual case outcomes. Mocked model replies establish transport/schema behavior only.
- Independently traverse EPUB package spine and generated HTML to prove coverage/order, structure, front/body/back classification, links/assets/entity evidence and reader readiness. Repeated meaningful prose remains repeated; navigation text never substitutes for body evidence.
- Use no paid API, free-tier cloud fallback, subscription, additional hardware, or fabricated source text. Unavailable resources produce explicit waiting states; unresolved ambiguity never becomes an editorial-review task.
- Show genuine unfinished-source changes and recovery. Inject source faults, checksum corruption, duplicate commands, broker/database/inference outages, stop requests, worker death, stale revisions, revoked authority and lost publication acknowledgments; all follow the defined state machine.
- Verified source/import builds automatically activate coherent files/resources/catalog metadata. There is no review/approve/publication button required to complete a book. A stale/stopped attempt or changed authority cannot activate it.

Use [test strategy](../shared/verification/test-strategy.md) for checks and evidence. Do not claim full-catalog correctness from the reference sample. If required semantic cases, resources, or real-source evidence are unresolved, record them and leave E08 incomplete; do not lower the standard or hide the records.
