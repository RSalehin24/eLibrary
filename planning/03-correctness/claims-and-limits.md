# Claims and limits — what "no errors" can honestly mean

Status: DRAFT

Rebuilt 2026-11-19 for the six-service design. Kept from v1: the three guarantee classes and the contract. Changed: the residual-risk table (new limits from D-28, D-33, D-39, D-47) and the evidence state.

## What we cannot promise

No method proves arbitrary software free of all errors: program behavior is undecidable in general, the specification itself can be wrong, and the system depends on things we do not control (the source website, the browser, the network, a mail provider, the disk). This plan gives **three kinds of guarantee**, each labeled.

## The three guarantee classes

| Class | Meaning | How established | Applies to |
|---|---|---|---|
| **P — Proven** | Holds in all states within the model or type system | Rust types, DB constraints, TLA+/Alloy exhaustive checking, `cargo kani`/proptest on pure cores | Authorization decision, state machines, outbox and idempotency, ticket redemption, conservation, TOC and nav parity, public-document isolation |
| **M — Measured** | Holds with a quantified rate on a labeled corpus | Gold corpus (120 books, held-out 40), judged query set, thresholds enforced as gates | Entity extraction, structure inference, duplicate policy, Bengali search relevance (SHOULD, O-5), cover legibility |
| **D — Detected** | Cannot be prevented, but is noticed and contained | Validation, quarantine, review queue, canaries, alerts, runbooks, drills | Source site changes, malformed HTML, mail outages, host failure, human error |

Every requirement in [02-requirements](../02-requirements/) is tagged (via its invariants) so you can see which class protects it: [traceability](../02-requirements/traceability.generated.md).

## The contract with the user

1. If a behavior is class **P**, a violation means a bug in the model or in an unproven assumption; both are reportable, and the assumption list is explicit ([assumptions](../00-charter/assumptions-and-constraints.md)).
2. If a behavior is class **M**, the plan states the threshold. A miss below threshold is *expected* at the stated rate and must land in the review queue, not production. Thresholds are set from the P0 baseline and are OPEN until then.
3. If a behavior is class **D**, the plan names the detector and the runbook.
4. Anything not in the three classes is **out of scope** and listed in [goals and non-goals](../00-charter/goals-and-non-goals.md).

## Evidence state (2026-11-19)

Nothing is evidenced yet. No code exists. No model has been run: Java and TLC/Alloy are not installed, and the Python mirror covers only the v1 models. The plan-checker verifies the plan's own consistency, not the system. Every "P" above is therefore a **design claim** until gate G2 (models) and the matching code gates pass. See the [verification log](verification-log.md).

## Explicit residual risks

| Risk | Why it is residual | Containment |
|---|---|---|
| Specification error (we specify the wrong thing) | Models verify the spec, not that the spec matches intent | Owner sign-off at G0, G4, G5; prototypes before backend depth; spec examples as executable acceptance tests |
| A reader can copy a book (D-28) | The reader serves the whole rendered book to the browser; a copy cannot be prevented in a browser | Entitlements, 15-minute tickets, rate limits, audit of opens (D-40); records and UI state this limit; this is not DRM (INV-RDR-010) |
| Up to 30 days of data can be lost (D-33) | Backups are monthly | Restore drill each month; books can be re-ingested; the owner may raise the frequency; INV-NFR-004 states the window |
| Source site redesign, bot protection or withdrawn permission | External | Fixtures, drift detector, canary per structure shape, visible cookie status, jobs halt on drift; ingestion go-live blocked until D-03 permission exists |
| Bengali text edge cases unseen in the gold set | Finite corpus (120 books) | Stratified sampling; review queue; production feedback adds cases |
| Browser and engine differences in the reader and SSR pages | External | Cross-browser E2E matrix (Chromium, Firefox, WebKit), progressive enhancement |
| Hardware, provider or Docker failure on the single host | One host (D-29) | Backups off the host, restore drill, restart policies, health checks, runbooks; no high availability is claimed |
| Model-checker bound | Exhaustive only within finite bounds | Bounds documented per model; small-scope argument plus property tests at larger scale |
| Java and epubcheck inside the ingestion worker (D-47) | A large third-party runtime on the build path | Pinned version, no network, memory cap, timeout; failure blocks publish (fail closed); in-process structure audit is a second gate |
| Developer mistakes in unverified glue | Not everything is formalized; one part-time developer | Smallest possible glue; lints; review checklist; mutation testing on pure cores |
| Six services run by one person | Operations load | Shared platform kit, one Compose file, one rolling-restart script; consolidate only through a new decision (R-08) |
