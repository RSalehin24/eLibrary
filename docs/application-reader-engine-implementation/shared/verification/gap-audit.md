# Follow-up implementation-plan gap audit

**Date:** 21 October 2026. **Trigger:** request to check whether any implementation-plan gap remains. **Scope:** source-requirement coverage, current repository seams, cross-module contracts and work order. This is an author review supported by executable document/tooling checks; it is not an independent reviewer or a runtime acceptance result.

The original 120 mappings proved structural coverage at issue/decision/page-family/section level. They did not prove every lower-level rule or interaction was defined. The first follow-up closed GAP-01 through GAP-13; a renewed requirement-driven review added GAP-14 through GAP-18. All are closed as planning findings; their product regressions must still pass during implementation. Current exact-wording traceability and verification results are recorded in [requirement verification](requirement-verification.md).

## Findings and resolutions

| ID | Gap found | Planning resolution / required implementation check | Status |
| --- | --- | --- | --- |
| GAP-01 | A mapped heading could hide an omitted bullet, reader feature, command or stage. | [Coverage validator](verify_plans.py) and [source extractor](source_coverage.py) now account for 104 individual bullets, 12 reader features, 17 commands and 11 stages in addition to the original categories. Persisted tests reject missing leaf obligations. | Closed |
| GAP-02 | The engine could publish with a null/guessed book identity and duplicate initial books. | [Publication context](../contracts/publication-context-and-lifecycle.md) reserves a unique website-owned source/book binding before generation; context/book/source/actor IDs must match at first atomic activation. Test concurrent first publication, same-title/different-source and conflicting source ID/URL. | Closed |
| GAP-03 | Rebase had no way to fetch current administrator values/cover, and entity writes could indirectly alter book metadata. | Immutable website context, override precedence including explicit blank/removal, authorized cover transfer and revision conflicts are specified. [W02](../../website/data/unified-books-and-authorization.md) closes linked-entity mutation races; reading-list curation retains its explicit permission boundary. | Closed |
| GAP-04 | A tab could copy another tab's revision then overwrite it, and old-build writes could replace current progress. Read-once/file retirement was underspecified. | [Reading-state rules](../contracts/data-and-state.md) define build-bound progress/receipts, suspend-on-broadcast choices, no-broadcast conflicts, initial-restore save guard, active-build summary isolation, exact session reuse/expiry and two-hour retired-file leases. | Closed |
| GAP-05 | Run Now referred to an undeclared occurrence key and multi-stage schedules lacked precise parent/child semantics. | [Scheduling contract](../contracts/scheduling-and-status.md) defines an exact run endpoint, immutable parent settings, discovery-before-selection, stable child IDs, joins, completion/failure counts and stop propagation only to owned children. | Closed |
| GAP-06 | Website and engine jobs had no complete synchronization/query mechanism after ownership split. | Monotonic outbox/inbox events, service-only projection scope, missed-event reconciliation and combined pre-pagination filtering/counts are defined. Test stale/duplicate events and two-backend pagination/ID collisions. | Closed |
| GAP-07 | The signed assertion did not bind Idempotency-Key, and revoked-origin jobs could lose receipt reconciliation. | [Private authentication](../contracts/private-engine-v1.md) signs key/method/path/query/body and binds actor identity. Service-only artifacts/events/receipts are separated from user-authorized mutations; activation still checks the stored actor. Authority lookup cannot recurse into engine status. | Closed |
| GAP-08 | Pending publication consumers, stalled network/model calls and lost status outcomes lacked bounded restart rules. | Website receipt heartbeat/lease, request/stream/model deadlines, fresh-assertion/same-business-key retries and visible paced reconciliation are defined. Test crashes around commit and delayed old attempts after fencing. | Closed |
| GAP-09 | File/evidence reclamation could remove active resources or confuse a 2 GiB per-job cache with the full corpus. | Reference/pin-checked storage ownership, immutable staging, source/reference evidence pins, transfer/session leases, compact receipts and disk backpressure are defined in the publication lifecycle. | Closed |
| GAP-10 | Earlier tasks could remove review fields or move workers before later tasks restored essential behavior. | W01 includes working replacement lifecycle paths; E01 cutover requires minimum outbox/context/projection/fencing/recovery. E06/E07 extend those foundations; no unusable intermediate release is accepted. | Closed |
| GAP-11 | “Family-disjoint” could exclude layouts from a split; “evaluable” could exclude a difficult reference to pass. | [Corpus plan](../../engine/corpus/audit-and-local-inference.md) splits by related work/edition/component groups while covering layouts and preserving every selected case's pinned expected evidence. Missing truth leaves the gate unresolved; no exclusion or moved denominator. | Closed |
| GAP-12 | A source block or prompt could exceed the context window; overlap conflicts and output truncation lacked an exact policy. | Full request+response token accounting, bounded overlap/outline, source-mapped subspans, tagged evidence-only decisions and bounded ambiguity recovery are specified in E03. No silent truncation or last-response-wins. | Closed |
| GAP-13 | Website contributor/series name uniqueness contradicted the engine's rule to preserve distinct same-name identities. | W01 explicitly replaces the name-only constraints/validation with immutable entity/source bindings; E05/E06 transport and publication reuse evidence-supported entity IDs. Test homonyms, aliases, same-name series and concurrent publication without name-based merging. | Closed |
| GAP-14 | Source labels/headings could pass while required table-cell wording, prose clauses, numbered steps or a target section were absent. | The mapping now preserves every source line and full clause text, validates each target plan anchor, and adds prose/numbered/service/milestone/route-area coverage. A reviewed-file fingerprint manifest rejects changed or unreviewed plans until another actual review. | Closed |
| GAP-15 | Large valid manifests conflicted with the 1 MiB control limit, and the reader-resource transfer format/hash serialization was undefined. | [Private artifacts](../contracts/private-engine-v1.md#sealed-build-manifest) define bounded streamed manifest bytes, stable JSON hashing, ZIP resource packaging and an explicit metadata allowance beyond reading-resource limits. Test large manifests, exact-byte hashes and every expansion/entry bound. | Closed |
| GAP-16 | A valid null-to-reserved book association would be rejected as a changed immutable job relation; a late transaction could disappear behind a timestamp cursor. | [Job projections](../contracts/scheduling-and-status.md#one-current-job-list-across-services) allow only a verified one-time book bind/current-context refresh. Durable unacknowledged events plus nonterminal-ID reconciliation prevent cursor timestamps from being the sole recovery source. | Closed |
| GAP-17 | Schedule phase selection and bounded discovery completion could be confused with a full catalog census. | [Schedule execution](../contracts/scheduling-and-status.md#run-now-and-scheduled-workflow) fixes three supported kinds and their phases, distinguishes configured-scope completion from provider coverage, and prevents Process All before a complete catalog universe exists. | Closed |
| GAP-18 | Automatic metadata alignment could emit another edit event and generate a publication/alignment loop. | [Override lifecycle](../contracts/publication-context-and-lifecycle.md#override-precedence-and-revision-races) emits alignment only from explicit administrator edits, keys/coalesces requests by book/revision and prevents an automatic activation from becoming another administrator edit. | Closed |

## Entry gate and remaining empirical work

**Documentation review:** no known unresolved requirement-coverage or cross-contract finding remains after the corrections above and the recorded checks below. This is a statement about the reviewed scope, not proof that no undiscovered issue exists.

**Application-code entry:** F01/F02 remain not started. Before application coding, obtain the current populated route/section/state baseline, runtime/resource ownership and contract walkthrough evidence specified in [the baseline plan](../baseline-and-sequence.md). Record any discovery that changes an expected result, resolve it and reverify the plan before the affected implementation. The document validator does not grant this entry gate automatically.

**Later milestone evidence:** independent service builds/integration, actual browser states and user visual/UX acceptance, source truth, model/runtime pin/approval and real benchmark/resource feasibility are still future work. Their failure handling and stopping conditions are defined. They cannot be honestly confirmed from Markdown or repository inspection. A failing prerequisite/gate remains incomplete; it is never silently waived to meet a completion claim.

## Reproducible checks

From the repository root:

```sh
python3 docs/application-reader-engine-implementation/shared/verification/verify_plans.py
python3 -m unittest discover -s docs/application-reader-engine-implementation/shared/verification -p 'test_*.py'
.venv/bin/python -m ruff check docs/application-reader-engine-implementation/shared/verification
.venv/bin/python -m ruff format --check docs/application-reader-engine-implementation/shared/verification
PYTHONPATH=app/backend .venv/bin/python -m mypy --config-file mypy.ini docs/application-reader-engine-implementation/shared/verification/verify_plans.py docs/application-reader-engine-implementation/shared/verification/source_coverage.py docs/application-reader-engine-implementation/shared/verification/plan_integrity.py docs/application-reader-engine-implementation/shared/verification/test_verify_plans.py
python3 tests/scripts/check-file-size-policy.py
python3 tests/scripts/check-architecture-policy.py
git diff --check
```

The tests operate on document data and disposable temporary fixtures. They never start application services, seed/reset data, install dependencies or send messages. Whitespace checks also cover untracked plan files through `git diff --no-index --check`; a clean differing-file exit status is distinguished from actual whitespace diagnostics. Original specification/PDF SHA-256 values must remain those recorded in [the original review](plan-review.md).

## First follow-up executed results

These record the earlier 264-mapping/13-finding checkpoint. The renewed [requirement verification](requirement-verification.md) supersedes its counts and records the current 347-clause/18-finding scope.

| Check | Result |
| --- | --- |
| Requirement coverage | PASS: 264 mappings; all 35 issues, 15 decisions, 30 page families, 40 sections, 104 bullets, 12 reader features, 17 commands and 11 processing stages represented. |
| Dependencies, routes, links and evidence paths | PASS: 25 acyclic tasks; 54 current route templates; 122 Markdown links/anchors; 18 declared repository evidence paths. |
| Recorded planning findings | PASS: all 13 have a defined correction and required regression; validator rejects a reopened finding. This checks recorded status, not absence of undiscovered semantic defects. |
| Validator tests | PASS: 19 deterministic standard-library tests, including leaf-coverage, gate-order, task-mapping, missing file/anchor/route, route-ownership and reopened-finding rejection. |
| Python lint, format and type checks | PASS: installed Ruff checks; repository-configured mypy reports no issues in all 3 planning-tool source files. |
| Repository file-size/architecture policies | PASS with the existing policy scripts; no exemptions/rules weakened. |
| Whitespace and preservation | PASS: tracked diff and all 26 untracked planning/tooling files checked. Original Markdown/PDF hashes unchanged. No application source/data/dependency or deployment change. |

**Conclusion:** all recorded findings are closed at the planning level; use the latest requirement-verification report for current results. F01/F02 are still mandatory before application coding, and all runtime/semantic/visual acceptance gates remain unexecuted. Do not convert this conclusion into an unconditional “zero gaps” or “zero bugs” guarantee.
