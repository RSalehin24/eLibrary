# Application, reader, and engine implementation plans

**Prepared:** 21 October 2026. **Scope:** planning and plan verification only.

The [product specification](../application-reader-engine-plan.md) defines the required result. This folder defines the work order, module boundaries, expected behavior, failure handling, and evidence required to implement it. Read [AGENTS.md](../../AGENTS.md) first. These documents do not authorize implementation, dependency installation, data resets, external messages, or deployment by themselves.

The latest request requires the plans to be verified before implementation. Start with the latest [whole-package requirement verification](shared/verification/requirement-verification.md). The [plan review](shared/verification/plan-review.md) and [gap audit](shared/verification/gap-audit.md) retain earlier checks and corrections. Application acceptance, model accuracy, and visual acceptance remain separate future gates. No plan can establish that software will have zero defects.

## Folder map

```text
application-reader-engine-implementation/
├── README.md
├── shared/
│   ├── baseline-and-sequence.md
│   ├── contracts/
│   │   ├── service-boundaries.md
│   │   ├── data-and-state.md
│   │   ├── private-engine-v1.md
│   │   ├── publication-context-and-lifecycle.md
│   │   └── scheduling-and-status.md
│   └── verification/
│       ├── requirements-matrix.csv
│       ├── test-strategy.md
│       ├── plan-review.md
│       ├── gap-audit.md
│       ├── requirement-verification.md
│       ├── reviewed-plan-files.csv
│       ├── plan_integrity.py
│       ├── source_coverage.py
│       ├── test_verify_plans.py
│       └── verify_plans.py
├── website/
│   ├── README.md
│   ├── data/unified-books-and-authorization.md
│   ├── interface/design-and-route-matrix.md
│   └── workflows/behavior-and-failures.md
├── reader/
│   ├── README.md
│   ├── service/extraction-and-offline.md
│   └── experience/commands-layout-and-state.md
├── engine/
│   ├── README.md
│   ├── corpus/audit-and-local-inference.md
│   ├── pipeline/structure-entities-and-publication.md
│   └── operations/jobs-updates-and-recovery.md
└── release/
    └── initialization-and-acceptance.md
```

## Read and execute in this order

1. Read the specification and [baseline and task dependencies](shared/baseline-and-sequence.md).
2. Read the [service](shared/contracts/service-boundaries.md), [data/state](shared/contracts/data-and-state.md), [private engine](shared/contracts/private-engine-v1.md), [publication lifecycle](shared/contracts/publication-context-and-lifecycle.md) and [scheduling/status](shared/contracts/scheduling-and-status.md) contracts.
3. Check the [requirement mapping](shared/verification/requirements-matrix.csv), [test strategy](shared/verification/test-strategy.md), and [plan review](shared/verification/plan-review.md). Resolve a planning contradiction before changing affected application code.
4. Complete the [website](website/README.md), then the [reader](reader/README.md), then the [engine](engine/README.md), in the defined task order.
5. Execute [clean initialization and final acceptance](release/initialization-and-acceptance.md).

There is one product book model, no physical/digital classification, no physical-only reading features, no product review/check/approve workflow, and no non-admin cover/metadata editing. EPUB upload remains an intake path. Automatic integrity validation is required. Development history does not need migration. Bengali and English, Asia/Dhaka time, no purchases, and no paid or free-tier cloud inference fallback apply throughout.

## How to use a task plan

Task IDs such as `W01` are implementation tasks; IDs such as `WEB-01` are issues from the specification. The dependency table is authoritative for task order. The CSV maps specification requirements to tasks and planned checks; a mapping is not passing evidence.

Before a task, confirm its prerequisites, read the named existing code, and reproduce the relevant failure or establish a baseline. Implement the smallest coherent change across the producer and its consumers. Add meaningful regressions for changed behavior. Run its checks and inspect its rendered states before marking it verified. Keep each intermediate application usable.

Record task state as `not_started → in_progress → implemented_unverified → verified`. A blocked task retains its incomplete state with a concrete reason; it never becomes verified through a waiver. A new defect reopens its task and acceptance gate. For the separate issue register retain the specification's `investigate → confirmed → implemented/unverified → verified` vocabulary.

Existing code paths below were inspected during planning. Paths described as **planned** do not yet exist. Contract fields and endpoints explicitly marked **target** are requirements to implement, not claims about today's API. Historical documentation provides context; conflicting preservation, physical-book, review, and compatibility requirements are superseded by the product specification.
