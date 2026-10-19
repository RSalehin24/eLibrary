# Implementation repair specification

Accepted 18 October 2026. Feature reference: main@08fc99f. The previous UI is not
the design baseline. The exhaustive capability register and acceptance tasks are
in [the completeness audit](operations/feature-parity.md).

## Delivery status — 19 October 2026

The inventoried implementation and simulator acceptance steps below are delivered.
The completeness audit records each capability, final evidence and supported
boundaries. The final full backend/tools gate passed 1,675 checks; subsequent
exact-bookmark changes passed 45 focused access checks and all five browser
profiles. All 105 web units, build, lint, types and repository policy checks pass.
This status does not claim zero bugs, completion of the live source backlog,
physical-device acceptance, external Kindle receipt or production deployment.
Five upstream development-only audit findings remain explicit in the report.

## Ordered delivery

1. Prevent incomplete publication (SRC-08): classify reading evidence, retain
   versioned evidence/page manifests, quarantine suspect existing books across
   catalog/read/HTML/download/Kindle without deleting personal data.
2. Recover unattended (SRC-09/10/11): metadata-safe rebase, selective invalidation,
   recurring availability retries, Retry-After/circuit breaker, bounded collection
   continuations, fair queue and bounded dispatch. Preserve mail delivery policies.
3. Make editions atomic (BOOK-02/SRC-03/07): stage assets and reader resources,
   publish in one transaction; keep ordinary verified editions live, hide suspect
   editions. Daily 02:00 Dhaka unfinished checks auto-build changed editions.
4. Restore CAT/PHY/NOTE/ACC/KIND features in the audit; add visible bulk source/job
   recovery and diagnostics. Reuse existing validated services, expose versioned
   contracts and regenerate clients. No manual editorial review gate.
5. Complete UX/QA/OPS acceptance: coherent bilingual design, explicit 12-hour Dhaka
   inputs and displays, old-route mappings, tests, quality and simulator deployment.

## Invariants

One configured provider, no provider name hardcoded; manual entry/uploads retained.
Local extraction only; no AI-generated prose. No fabricated completeness score.
Stable canonical identity and no title-based merge. Preserve prior bytes, owners,
notes, progress and attempt history. No suppressed tests/types/lint or new unapproved
package. Add migrations via Django, never edit previous migrations. Delivery stays off.

## Recovery and scheduling defaults

Source transient retries: 15s, 1m, 5m then 1h, 2h, 4h and 6h capped, without terminal
failure solely from availability attempts. Honor Retry-After. Five host transient
failures in five minutes opens a five-minute circuit, then one probe. Missing text
/access waits recheck in six hours, 404 daily. Stop unsafe URLs/revoked authority.
Repeatable internal defects get a diagnostic fingerprint and await relevant code
version changes. Collection yields at a page boundary after 10 pages or 30s.
At most two outstanding processing dispatches per configured worker; default one
worker. Fairly rotate new work, continuations and due recovery probes.

## Acceptance and rollout

Deterministic fixtures cover descriptions versus short works, missing/nested/paged
chapters, repeated source bytes, source updates, export order/text integrity, large
books, duplicate messages, interruption at each stage, metadata/permission races,
quarantine and atomic rollback. Audit reports have per-feature evidence and status.
Back up before applying additive migrations/data repair. Dry-run existing-book audit,
canary known problematic types, then resume normal catalog work. Never erase history
to improve dashboard counts. Every remaining task stays explicitly open in handoff.
