# Claims and limits — what "no errors" can honestly mean

Status: DRAFT

## What we cannot promise

No method proves arbitrary software free of all errors: program behavior is
undecidable in general, the specification itself can be wrong, and our system
depends on things we do not control (the source website, the browser, the
network, a mail provider, the disk). A plan that claims otherwise would hide its
risks. This plan instead gives **three kinds of guarantee**, each labeled.

## The three guarantee classes

| Class | Meaning | How established | Applies to |
|---|---|---|---|
| **P — Proven** | Holds in all states within the model/type system | Rust types, DB constraints, TLA+/Alloy exhaustive checking, `cargo kani`/proptest on pure cores | Authorization, state machines, outbox, idempotency, conservation, TOC/nav parity, preview isolation |
| **M — Measured** | Holds with a quantified rate on a labeled corpus | Gold corpus, judged query set, thresholds enforced as CI gates | Entity extraction, structure inference, search relevance, cover legibility |
| **D — Detected** | Cannot be prevented, but is noticed and contained | Validation, quarantine, review queue, canaries, alerts, runbooks | Source site changes, malformed HTML, third-party outages, human error |

Every requirement in [02-requirements](../02-requirements/) is tagged (via its
invariants) so you can see which class protects it:
[traceability](../02-requirements/traceability.generated.md).

## The contract with the user

1. If a behavior is class **P**, a violation means a bug in the model or in an unproven assumption — both are reportable, and the assumption list is explicit ([assumptions](../00-charter/assumptions-and-constraints.md)).
2. If a behavior is class **M**, the plan states the threshold. A miss below threshold is *expected* at the stated rate and must land in the review queue, not production.
3. If a behavior is class **D**, the plan names the detector and the runbook.
4. Anything not in the three classes is **out of scope** and listed in [goals and non-goals](../00-charter/goals-and-non-goals.md).

## Explicit residual risks

| Risk | Why it is residual | Containment |
|---|---|---|
| Specification error (we specify the wrong thing) | Models verify the spec, not that the spec matches intent | User sign-off gates G0, G4; usability sessions; spec examples as executable acceptance tests |
| Source site redesign | External | Schema-drift detector, canary book per structure type, jobs halt on drift (not mass-fail) |
| Bengali text edge cases unseen in the gold set | Finite corpus | Stratified sampling; production feedback loop adds cases; review queue |
| Browser/engine differences in the reader | External | Cross-browser E2E matrix (Chromium, Firefox, WebKit); progressive enhancement |
| Hardware/provider failure | External | Backups, restore drills, health checks, runbooks |
| Model-checker bound | Exhaustive only within finite bounds | Bounds documented per model; small-scope hypothesis + property tests at larger scale |
| Developer mistakes in unverified glue code | Not everything is formalized | Smallest possible glue; lints; review checklist; mutation testing on pure cores |
