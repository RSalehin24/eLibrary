# Planning review before implementation

**Review date:** 21 October 2026. **Scope:** the nested implementation plans and their agreement with the supplied specification and inspected repository. This is a planning review, not application acceptance or a guarantee of zero defects.

Source specification SHA-256: `46fd596d22b5f730f3b06fa8c2458c594d2f4a4cfb3efefa765cb2674ea78c96`.

Original PDF SHA-256: `f7546a970d9e7cb899232e76481b9d329daa237c7ad388e91138eb2aad1ee3a8`. Neither original file is changed by this planning work.

## Review scope and method

The author checked actual route files, manifests/scripts, current model/edit/permission/reader/progress/publication/export/scheduling/offline code and existing test organization. The accompanying standard-library [validator](verify_plans.py) checks local links/anchors, requirement-source coverage, task references/dependencies, exact route dispositions, declared repository evidence paths and unresolved planning markers. It starts no service and edits no application state.

Run from the repository root:

```sh
python3 docs/application-reader-engine-implementation/shared/verification/verify_plans.py
.venv/bin/python -m ruff check docs/application-reader-engine-implementation/shared/verification/verify_plans.py
.venv/bin/python -m ruff format --check docs/application-reader-engine-implementation/shared/verification/verify_plans.py
python3 tests/scripts/check-file-size-policy.py
python3 tests/scripts/check-architecture-policy.py
git diff --check
```

The validator is intentionally structural. Semantic contract review and actual implementation tests are separate: a valid link or mapped requirement cannot prove runtime correctness. Re-run planning checks and the affected manual consistency review whenever a source requirement, contract, task dependency or module boundary changes. The source checksum makes unreviewed specification changes fail visibly.

## Contract decisions checked manually

| Risk found during review | Defined resolution |
| --- | --- |
| Metadata save currently creates pending review | W01/W03 remove fields/transitions and assert availability survives valid saves; automatic validation stays. |
| Broad/scoped metadata grants currently allow existing-book writes | W02 defines active/TOTP-complete staff/superuser/global-full-control administrator and applies one server policy to every write/capability. |
| Useful bibliographic facts are stored under `manual_` names | Retain neutral publisher/language/edition/structure facts; remove only physical inventory/type semantics. |
| Old migrations and negative tests retain removed vocabulary | Verify active schema/endpoints/UI, preserve immutable migrations and meaningful absence regressions; no zero-string-match fiction. |
| Progress has no revision and requests can finish out of order | R03 defines revision plus stable mutation ID, one in-flight writer and explicit cross-tab conflict choices; percentage cannot select a winner. |
| Independent reader could collide with assets/root worker | Reader document and asset ownership are explicit; one website-owned worker consumes an independently produced public reader shell. |
| Old reader positions could be misapplied to a replacement | Build-bound anchors; no silent cross-build restore or history migration; bounded active-session file leases. |
| Local reading might accidentally upload or pretend to save account data | Device-only memory/current local-session behavior; no durable local content store or library action success; network-silence/cache tests. |
| Private API lacked complete source/list/schedule read surfaces | Versioned source/operation/schedule list/detail/run interfaces and bounded envelopes are defined alongside commands/artifacts/publication. |
| Website/engine handoff can lose a reply | Durable outbox/inbox/event receipts with stable IDs; activation commit and receipt are atomic. |
| Cancel may race irreversible publication across services | Locked publication outbox fence; accepted earlier stop prevents handoff; later stop returns explicit conflict and reconciles receipt. |
| Source changes or admin edits can race a build | Immutable source revision; catalog revision/authority checks, override-preserving rebase, next-revision rebuild and archive protection. |
| Engine availability could take down browsing | Independent service/artifacts/storage plus resource waiting; prepared files are website-owned. |
| Model could invent structure or execute source instructions | Evidence-only schema decisions, bounded retries, no tool/network authority, complete block accounting and independent verification. |
| Existing export test can pass reordered/nav-only body text | Verify actual package spine and independent source expectations with deliberate false-positive fixtures. |
| An inaccurate/unavailable model might be treated as finished | Real pinned benchmark and case-level gate; failed candidate blocks intelligence, no cloud fallback or lowered threshold. |
| Existing full verifier targets retained frontend | Current website checks are explicit; reader/engine must add genuine independent checks before their gates close. |
| Historical counts and simulator results may overstate acceptance | Fresh per-case evidence, explicit live/model/device/delivery limits, user visual/UX gate and no overlapping totals. |

## Implementation entry and limits

The plan fixes ownership, behavior, state transitions, failure/retry rules, field/interface requirements, work order, route coverage and acceptance evidence. F01/F02 are mandatory read-only baseline/revalidation tasks **before application coding** when implementation is requested. They capture current populated renders, runtime configuration and new discoveries; a changed decision must be incorporated and reverified before affected coding begins.

The model/runtime pin and license/size/resource measurement belong to the explicitly gated E03 benchmark and may require dependency approval. Source availability, actual whole-corpus semantic outcomes, strict runtime/build checks, rendered design acceptance, external delivery and physical installation cannot be established by a documentation review. Their success/failure handling and stopping conditions are defined; they are not represented as already passing.

This change creates plans and verification assets only. It does not implement the product, start application services, reset data, install packages/models, send mail, commit, push, or deploy. Keep every implementation task `not_started` until that work is requested and its recorded prerequisites are met.

## Initial executed review results

These are the first planning checkpoint's results. The subsequent [gap audit](gap-audit.md) found and corrected semantic contract gaps, expanded coverage, and records the current follow-up verification. The original structural pass alone was insufficient to confirm that no planning gaps remained.

| Check | Result and evidence scope |
| --- | --- |
| Source requirement traceability | PASS: 120 mappings covering all 35 issues, 15 decisions, 30 website page families and 40 substantive section headings. |
| Task order | PASS: 25 unique tasks; all references exist; dependency graph is acyclic and website/reader gates precede engine work. |
| Route inventory | PASS: all 54 current page templates represented exactly once; 49 website, 3 reader, 2 explicit removals. |
| Links/anchors and repository grounding | PASS: 92 Markdown links checked; all mapped plan files and 18 declared repository evidence paths exist. |
| Validator rejection behavior | PASS: eight negative probes rejected cyclic/unknown prerequisites, missing/duplicate requirements, unknown assigned tasks, broken file/anchor links and missing routes. Probes used in-memory values and a disposable temporary document only. |
| Validator Python lint/format | PASS with installed Ruff. Initial formatting/import/shebang findings were corrected; no rules disabled. |
| Repository policies | PASS: existing file-size and architecture policy scripts. |
| Whitespace and source preservation | PASS: tracked diff and all 21 new planning files checked; original Markdown/PDF hashes match the recorded values. Git no-index exit 1 for a differing new file was distinguished from whitespace diagnostics. |
| Contract consistency | Author review completed for the risks and resolutions listed above. This is not an independent external review or runtime proof. |

**Initial planning status:** structurally verified to the first checkpoint's scope; see the gap audit for current contract/readiness conclusions. All implementation tasks remain not started. Application build/type/backend/browser checks, model inference and visual/UX acceptance were not executed for this planning-only change.

## Implementation route-validator review: 21 October 2026

Implementation removes `/physical-books/` and `/[legacy]/` as W01 requires. The
route check now accepts the absence of exactly those two `Remove W01` entries;
all retained pages remain mandatory and undeclared pages still fail. Its count
remains 54 route obligations from the starting inventory, rather than claiming
54 remaining pages. Added negative regressions reject a missing retained page
and an undeclared page; a positive regression permits the planned removals.
All 30 validator tests passed after this focused review. No source requirement,
ownership decision, dependency, or acceptance condition changed. Only this record,
the route validator, and its tests receive updated reviewed fingerprints.

The earlier not-started statements describe their original planning checkpoints.
Actual implementation status and application evidence are recorded separately in
[implementation progress](../../../application-reader-engine-progress/README.md).
