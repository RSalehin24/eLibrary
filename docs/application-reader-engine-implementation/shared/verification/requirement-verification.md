# Renewed verification against the complete requirement document

**Date:** 21 October 2026. **Scope:** every implementation-plan document, the unchanged source requirement document, current repository interfaces/routes, and the executable planning checks. This is a renewed author audit; no application implementation, browser baseline, local-model benchmark or deployment was performed.

The source is [application-reader-engine-plan.md](../../../application-reader-engine-plan.md), SHA-256 `46fd596d22b5f730f3b06fa8c2458c594d2f4a4cfb3efefa765cb2674ea78c96`. Earlier structural checks were useful but insufficient for a claim that whole plans could cause no implementation issue. This review checks full source wording and plan-section references, walks interactions across module boundaries and records five additional corrections as GAP-14–GAP-18 in [the gap audit](gap-audit.md).

## Verifiable requirement traceability

The [mapping](requirements-matrix.csv) now records `kind`, stable `requirement` ID, `source_key`, exact `source_line`, complete `source_text`, implementation `tasks`, `plan`, `plan_section` and expected `verification`. Table rows retain all cells, not merely their title. The validator rejects changed/missing wording, wrong source coordinates, absent plan sections and unmapped obligations even if their old label remains.

| Source content | Mappings |
| --- | ---: |
| Product decisions | 15 |
| Reported issues | 35 |
| Website page families | 30 |
| Reader feature rows | 12 |
| Reader command rows | 17 |
| Processing stage rows | 11 |
| Service ownership rows | 3 |
| Milestone deliverables/exit rows | 6 |
| Source route-inventory areas | 21 |
| Substantive section headings | 40 |
| Individual bullets | 104 |
| Standalone prose clauses/context | 44 |
| Numbered investigation/handoff steps | 9 |
| **Total traceability records** | **347** |

These are overlapping levels of traceability, not 347 independent features or passing runtime tests. The contents navigation and repeated handoff code block are navigation/duplicates; the actual section/step/route requirements are mapped separately. No source requirement is deleted to obtain a pass.

The [reviewed-file manifest](reviewed-plan-files.csv) records SHA-256 for every `.md`, `.csv` and `.py` in this package except the manifest itself. Both modified files and new unreviewed files fail validation. Update these fingerprints only after reviewing the affected content and rerunning relevant checks; regenerating hashes alone is not a review. This binds the report to a concrete complete package and prevents later edits from silently inheriting acceptance.

## Cross-module walkthroughs

Each outcome below was checked against the written sequence, actor, revision, state, failure and test definitions. These are document-level scenario reviews; actual execution remains required in the named tasks.

| Journey / source requirements | Defined path and adverse outcome |
| --- | --- |
| New source book; Publication, ENG-08, C7 | Processing command → website source/book reservation → current immutable metadata context → verified sealed artifacts → durable inbox/receipt → atomic first Book/files activation. Duplicate/lost replies reuse identity and receipt; incomplete files never become ready. |
| Admin edit while rebuilding; Book editing, WEB-17, C8 | Administrator-only direct/indirect writes advance revision and preserve explicit overrides. Stale candidate conflicts, fetches context and regenerates affected bytes. Only explicit edits enqueue alignment; automatic alignment cannot loop. Archive/revocation blocks activation. |
| Progress across tabs and builds; READ-07, B2/B4 | Build-bound revision/mutation receipt; conflict pauses writes and requires an explicit passage choice. Initial restoration never saves a default position. Older-build saves cannot replace current summary; read-once refresh uses its unexpired original session. |
| Run Now and unfinished updates; Schedules, ENG-06/07, C8 | Typed schedule snapshot → kind-specific discovery/probe/creation → frozen scope → idempotent owned/joined children. Bounded scope is never a full census; Process All needs a known complete universe. Pause/cancel does not cancel another run's joined work. |
| Website/reader/engine separation; Integration requirements | Full navigation and distinct reader assets; website session/CSRF/account checks; private scoped engine calls; separate DB/storage ownership; independent health/builds. Engine failure cannot change prepared website-owned bytes; local EPUB never uploads or caches private responses. |
| Publication crash/cancellation/large transfer; C7/C8 | Publication fence orders stop versus handoff; receipt consumer resumes under a fenced lease. Exact stored manifest bytes and explicit ZIP/size policy prevent ambiguous hashes/limits. Staging is immutable; failure cannot point at half-copied files. |
| Combined job lists and late events; Processing list/detail | Monotonic events permit the reservation-backed first book association, reject arbitrary rebinding and filter/count before pagination. Unacknowledged outbox events and active-ID reconciliation prevent a late commit from being lost behind a read cursor. |
| Semantic source correctness; ENG-01–05, C2–C9 | Full frozen inventory, source-mapped blocks, related-work split, bounded evidence-only inference, calibrated evaluation, independent HTML/spine/role verification. Missing evidence, conflicting decisions or a failed model leave an explicit unpassed gate; no editorial approval/cloud fallback. |
| Clean rebuild and retained capabilities; QA-02/03, M0/M5 | User changes/unrelated resources preserved; owned writers stop before reset. Current schema removes physical/review semantics, preserves useful bibliography and current reading behavior; all retained routes/states and prior capabilities get fresh evidence. |

Module coverage includes website data/design/workflows/gate; reader service/local-offline/commands/state/gate; engine service/corpus/structure/entities/generation/recovery/gate; all five shared contracts; baseline, release, test strategy and verification tooling. Obsolete historical requirements do not override the revised source decisions.

## Reproducible verification

Run the [gap-audit commands](gap-audit.md#reproducible-checks), with Ruff/mypy including all four planning-tool source files (`verify_plans.py`, `source_coverage.py`, `plan_integrity.py`, `test_verify_plans.py`). The standard-library tests exercise missing/mutated requirements, sections, gates, files, fingerprints and reopened findings; they do not start application services or edit application data.

| Executed check | Result |
| --- | --- |
| Exact requirement traceability | PASS: all 347 records match their original source wording/line and a real target plan section; all 13 source-content categories reconcile. |
| Task, route and link consistency | PASS: 25 acyclic tasks, 54 current route templates, 137 Markdown links/anchors, all 347 mapping target sections and 18 declared repository evidence paths. |
| Planning findings | PASS: all 18 recorded findings closed, including the five additional corrections in this renewed audit. A reopened finding blocks validation. |
| Whole-package integrity | PASS: 28 reviewed file fingerprints match; the manifest is the 29th package file and deliberately excludes its own hash. Any changed/new/missing reviewed file fails validation. |
| Validator regressions | PASS: 27 standard-library tests, including altered wording/line, missing plan section, unreviewed/changed files and duplicate manifest entries. |
| Python lint/format/type checks | PASS: installed Ruff checks and repository-configured mypy on all four planning-tool source files; no suppressed rules or type-check scope changes. |
| Existing repository policies | PASS: file-size and architecture checks. |
| Whitespace and preservation | PASS: tracked diff and all 29 planning/tooling files; original requirement Markdown/PDF hashes unchanged. No application source/data/dependency/deployment modification. |

These are newly executed documentation/tooling checks. Application build/backend/browser/model and visual/UX acceptance have not been executed in this planning review and are not included in its pass result.

## What can be confirmed

**Document alignment:** the whole planning package has been reviewed against the recorded requirements, and all currently identified planning findings have defined resolutions and required regression checks. An exact source-to-plan mapping, task ordering, route reconciliation and reviewed-file fingerprint are executable and repeatable.

**Implementation entry remains conditional:** F01/F02 current populated-page/state evidence, environment ownership and contract walkthrough are still unexecuted. They must pass before application coding. Real service integration, model/runtime feasibility/approval, source accuracy, browser/visual/UX acceptance and failure injections are later explicit gates. If any check reveals a new discrepancy, reopen the finding, correct/reverify the affected plan and keep dependent implementation blocked until its decision is resolved.

This audit cannot establish that no undiscovered gap or defect will ever arise during implementation. It establishes a reviewable requirement-aligned plan with all known findings closed and a mandatory process for detecting and resolving new ones. Do not call the software—or its runtime/visual acceptance—verified from this report alone.
