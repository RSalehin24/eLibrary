# Implementation repair specification

## Approved interface redesign — current checkpoint

The separate admin/reader plan is implemented and under final browser verification.
Admin opens Book Creation, readers open My Books, and the new shells, compact
filters, Notes repair, schedule summary/reset and audited source-credit corrections
are described in [the redesign report](operations/interface-redesign.md).
Build, lint, strict web types, 149 web units and the 827-test catalog/auth/ingestion
and 911-test processing/access gates pass. Previous UI screenshots and acceptance
counts below describe the superseded design; they are not proof of this revision.


Accepted 18 October 2026. Feature reference: main@08fc99f. The previous UI is not
the design baseline. The exhaustive capability register and acceptance tasks are
in [the completeness audit](operations/feature-parity.md).

## Sitewide UI follow-up — 21 October 2026

The follow-up implements separate admin/general headers, a combined Bengali logo,
same-account Reader View and Return to Admin, and shared numbered pagination with
exact filtered counts. Automation and Users & Access have direct actions, labelled
filters and responsive records. Browsing/export order, creation results, local
EPUB entry, static language persistence and moving table controls are repaired.
Mobile admin navigation also handles long active labels at 200% text in Safari.

The explicit review inventory represents all **53 page route templates**, including
legacy redirects, with **66 concrete route/state variants**. Bengali/English at
three widths plus enlarged phone text gives **528 scenarios per browser profile**.
Interaction regressions accompany the geometry checks; passing those checks is
not a claim of subjective design acceptance. Current evidence is maintained in
[the sitewide UI review](operations/sitewide-ui-review.md). The earlier source,
reader, data-preservation and external acceptance boundaries below still apply.

The final focused matrix passes **150 project/journey combinations** across five
simulated browser profiles, including **2,640 page-layout scenarios**. Accepted
full-inventory and repair records cover **243 Chromium journeys across all 57
specifications**. **713 backend/tooling tests**, **144 web units**, build, lint,
strict types/schema, configured mypy and repository policies pass. These totals
overlap; the report retains initial failures, accepted reruns and simulator limits.

## Source and reader follow-up — 21 October 2026

The follow-up implements spatial and temporal CFI restoration, private ranged
audio/video delivery, native media controls without autoplay, and embedded media
in the offline local EPUB reader. The remaining reader toolbar sizing defect
is fixed without relaxing its minimum-target assertion. Reader/media/offline
journeys pass in all five simulated browser profiles.

Source validator 3 supports verified linked-book compilations and fixes complete
prose misclassified by later publication references. Versioned automatic recovery
rechecks authority and source revisions, keeps its fair dispatch lane, and cannot
retry unavailable components in a tight loop. Missing chapters/contents use paced
availability retries; collected-text corruption remains an integrity failure.
A named processing queue permits nondestructive recovery from an obsolete broker
backlog. Old messages, source files, notes and attempt history are preserved.

The broad gate passed **1,840 backend/tools tests**, followed by **890 overlapping
access/processing tests** and the final **705 processing tests**, **53 configuration
tests** and **33 tools tests**. **135 web units**, build, lint, generated types,
zero-warning schema, mypy on **276 configured files**, migration consistency and
repository policies pass. The current handoff records actual source repair and
browser evidence; the existing external acceptance and dependency limits remain.

## Earlier delivery status — 20 October 2026

The second baseline audit restored BOOK-04/05, READ-05/06, NOTE-03/04,
ACC-04/05/06, SRC-12, CAT-10, LIB-03 and PHY-03. It also fixed interaction
problems found by real browser use: selection loss, local-reader WebKit events,
covered card controls/metadata, directory labels, narrow facts, private-library
navigation and oversized My Books tabs. The final browsing follow-up compacts the
personal filter toolbar, moves full-filter exports after results, and fixes both
unsubmitted-query clearing and cached saved-search restoration. The pinned
inventory and deliberate format/behavior differences are recorded in the
completeness audit.

The full backend/tools gate passed **1,802 tests**, with 13 live cases excluded;
**64 subsequent focused tests** cover the last private-detail and canonical-export
changes. **125 web units**, 154 retained frontend units and 14 capacity-helper
units pass. Build, lint, generated types/schema, mypy and repository policies pass.
Passing browser records cover the 51 existing specifications and the newest
private navigation in all five browser profiles; exact scope and reruns are in
[the report](operations/feature-parity.md).
The final personal-library/filter/list/export follow-up passes **59 cases** across
the five browser profiles; these overlap the earlier specification inventory.

A retained book exposed a further canonical EPUB export defect. Its complete
106,193-character source now passes both unchanged export checks after the fix.
Normal recovery requeued the job, and its existing dispatch succeeded through
the standard worker during an isolated canary. Both persisted reading files are
ready and verified. Another **24 admission/recovery tests** pass, including the
fixed recovery lane, backlog fairness and bounded capacity. Processing has resumed.
No manual approval gate or verification bypass was introduced.

The first inventory was incomplete, and its completion statement was too broad.
This status does not assert zero bugs, subjective design acceptance, completion
of the live source backlog, physical-device acceptance, external Kindle receipt
or production deployment. Five upstream development-only audit findings remain
open, with zero reported production findings at the recorded audit checkpoint.

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
