# ingestion

Status: DRAFT

Turns an unreliable external website (or an uploaded EPUB) into a validated canonical book document, safely and repeatably.

| | |
|---|---|
| Owns | sources, source catalog entries, snapshots, jobs & leases, drafts, rulesets, review items, gold-corpus metrics, schedules |
| Does not own | published books (catalog), files (content), accounts |
| Requirements | REQ-ING-001…016, REQ-CAT-006 (policy), REQ-CON-002/007 (via builders) |
| Emits | `JobStateChanged`, `ReviewRequested`, `DocumentValidated`, `JobFailed`, `SourceDriftDetected` |
| Calls | catalog (draft upsert, agent resolve, duplicate classify, publish), content (put document), access (`decide ManageIngestion/Submit`) |
| Called by | web admin via gateway |

## Pipeline

```
Source URL / EPUB upload
   │  (1) ACQUIRE      impure, GET-only, polite, logged         ─► Snapshot (immutable, hashed)
   │  (2) PARSE        pure: HTML ─► Block IR                    ─► Blocks (stable BlockId)
   │  (3) STRUCTURE    pure: source TOC / inference ─► SectionTree + evidence
   │  (4) CLASSIFY     pure: sequence labeling over front/back regions ─► labeled blocks
   │  (5) ENTITIES     pure: key-values ─► Names, roles, dates, edition; resolve to Agents (read-only query)
   │  (6) VALIDATE     pure: invariants (conservation, completeness, order, dedupe) ─► CanonicalDocument | ReviewItem[]
   │  (7) DEDUPLICATE  query catalog: five-case policy ─► ExactDuplicate | NewEdition | NewTranslation | NewWork | NeedsReview
   └─ (8) PUBLISH SAGA catalog.upsert_draft → content.put_document(builds) → catalog.publish
```

Stages 2–6 are pure functions of `(snapshot, ruleset)`; their outputs are cached by `(snapshot_hash, ruleset_version)`.
Each stage returns a typed result: `Ok(output, evidence)` or `Err(Review(reason))`. Nothing is silently dropped (INV-ING-002).

## Sub-designs

| Folder | Concern |
|---|---|
| [acquisition](acquisition/README.md) | fetching, politeness, completeness evidence, drift, locked chapters |
| [block-ir](block-ir/README.md) | HTML → blocks, ids, chrome |
| [structure](structure/README.md) | source TOC, single-page inference, ordering, nesting |
| [classification](classification/README.md) | front/back matter sequence labeling, residual policy |
| [entities](entities/README.md) | names, roles, dates, aliases, resolution, duplicate policy |
| [builder](builder/README.md) | page order, EPUB/HTML/preview/cover, determinism |
| [orchestration](orchestration/README.md) | jobs, scheduling, catalog sync, review queue, reprocessing |
| [rulesets](rulesets/README.md) | versioning, gold gates, promotion |

Also: [domain model](domain-model.md) · [API](api-contract.md) · [state machines](state-machines.md) · [tests](test-plan.md) · [gold corpus](../../06-data/gold-corpus/README.md).

## Why this is hard (and where the plan answers it)

| Difficulty | Answer |
|---|---|
| Chapter order and nesting must match a printed book | Tree from source TOC is authoritative; one tree renders TOC and nav; completeness proof |
| Entity recognition in free Bengali/English text | Sequence labeling with grammar + lexicons + evidence; positive name recognition; review queue for ambiguity |
| Heuristics regress | Gold corpus gate, ruleset versions, reprocess diffs |
| Hostile/changing source | Read-only, polite, snapshots, drift detector, canaries |
| Duplicates/editions | One pure five-case decision function with labeled pairs |
| Partial failure | Lease/fencing job model, idempotent steps, saga with compensation |
