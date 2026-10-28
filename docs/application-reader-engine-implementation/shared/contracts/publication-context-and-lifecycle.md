# Book identity, metadata context, and file lifecycle

This supplements [private engine v1](private-engine-v1.md) and [data/state rules](data-and-state.md). Implement the transport/identity boundary in E01 and production generation/activation in E06; use the same lifecycle semantics in W03 before separation. All endpoints/records here are target designs.

## Reserve identity before generation

The website owns book identity. Before generating a source build, the engine requests a website context for the configured provider ID, engine source ID, canonical public source URL and operation ID. The website validates current actor processing authority and provider/source identity, then atomically resolves a `SourceBookBinding` with unique `(provider_id, source_id)` and `(provider_id, canonical_source_url)` keys. It also reserves one website book UUID if no current book exists. A reservation is not a public book, a prepared result, ownership, or a grant.

If the source already belongs to a book, return that exact identity. If an ID and URL imply different bindings, reject `409 source_identity_conflict`; do not merge by title or create another book. A changed source URL needs evidence-backed identity resolution before another reservation. The generated manifest and publication event must carry the reserved book/context IDs. Reject a candidate naming another book, actor, provider or source. If another valid build activates first, return a catalog conflict and fetch current context; do not allocate a fresh book to escape it.

At first activation the website creates the reserved Book and its source link within the same locked transaction as active-build pointers and receipt. On retry, unique binding/event/build constraints return the existing result. For an existing book the target revision must match. Initial context uses `catalog_revision: 0`; actual book creation commits revision 1. Reservation/context creation does not publish an empty book. No engine database has a website foreign key.

Source administration and scheduled catalog creation do not automatically add UserBook ownership or reader grants to their requesting account; this retains the behavior asserted in `tests/backend/processing/test_source_processing.py`. Saving a book and independent reading grants remain explicit website actions. Manual upload retains the website's existing intake/access policy; retrying either intake must not invent new ownership or broaden permissions.

## Website context contract

`POST /internal/v1/website/book-contexts/` with scope `website:context` accepts exactly `{schema_version, context_request_id, operation_id, actor_id, provider_id, source_id, source_url, book_id}`; nullable `book_id` is only a hint and must match any existing binding. Use `context_request_id` as Idempotency-Key. Current authority is checked at admission. Response is `{context_id, operation_id, actor_id, provider_id, source_id, book_id, catalog_revision, authority_revision, visibility, active_build_id, metadata, overrides, cover}`. Return `201` for a new reservation/context and `200` for the exact recorded replay.

Context is an immutable snapshot; a fresh request ID gets a current snapshot for the same reserved identity. A job does not alter its older context in place. Current permission/expiry/archive state is checked again before activation; a context is not a durable authority grant. Only source-processing-authorized service calls can reserve/read these values. No user email, personal progress/notes, arbitrary file paths or browser session credentials enter this response.

`metadata` uses the existing neutral book field names after W01 and role/entity validation. `overrides` maps metadata fields to `{value, catalog_revision, origin: administrator}`. An administrator's explicit blank value or removal is an override, not an instruction to restore the source value. Contributor/category/series/edition relationship collections are overridden as whole ordered sets to avoid partially merging contradictory roles/order. No new reset-to-source UI is required. Preserve source-derived facts/provenance separately from these current choices.

`cover` is null or `{cover_revision, media_type, byte_length, sha256}`. If overridden, the engine reads `GET /internal/v1/website/books/{book_id}/covers/{cover_revision}/` with scope `website:context` from the configured website origin. Return only that authorized validated image, never an arbitrary URL. Changed/missing revisions conflict; use streaming limits and hashes from the manifest contract. This permits generation with the current cover without sharing storage credentials.

## Override precedence and revision races

Generation uses automatic source facts for fields without an admin override and the immutable context values for overridden fields. Do not rewrite source-authored body/front matter to make it agree with a catalog override. Generated catalog/EPUB metadata can reflect the override; the verification report identifies it as administrator provenance and separately proves original source body/credits intact. Never fabricate a source span for an admin value.

If an administrator edits/clears a field, changes shared linked metadata, replaces a cover, or archives the book while building, its catalog revision changes and the old candidate cannot activate. Fetch current context, reapply the rules, regenerate affected metadata/cover/artifacts, independently reverify and create a new sealed manifest/event. Reuse unchanged blocks/source evidence; never patch bytes under an existing build ID/hash. A source update can never clear an override simply because the automatic extractor found another value.

Saving a valid administrator edit immediately updates website metadata/cover and retains availability; it does not falsely claim the active EPUB bytes already changed. Queue metadata/cover alignment once through a website outbox event; source books use a `metadata_refresh` processing intent and uploaded books use website-owned preparation. A metadata refresh reuses verified body resources and does not trigger body inference without changed source input. Show alignment pending/failed separately from book availability and retain a permitted retry. Archive remains explicit and blocks automatic activation.

Only an explicit administrator metadata/cover mutation creates that alignment command, keyed by book ID and its requested catalog revision. Completing automatic alignment may advance catalog/build revision but does not emit another administrator-edit event. Coalesce superseded pending alignment requests to the newest permitted revision; preserve terminal receipts and never modify a command's original payload/key. This prevents an automatic publication→alignment→publication loop.

## Crash-safe staging and activation

Artifacts are immutable and grouped by build ID, not mutable `book/latest` paths. Write into a confined temporary build directory on the destination filesystem, stream with byte/hash limits, flush/finalize complete files, and atomically rename to a sealed directory before publishing a DB pointer. Filesystem publication and DB commit are separate: a crash after sealing but before DB activation leaves an unreferenced candidate, never half an active book. Never overwrite bytes already referenced by an active build.

Use one logical DB transaction for current actor/authority/grant checks, catalog revision and archive checks, source binding/first Book creation, all active artifact pointers, build metadata and activated receipt. Lock in a documented stable order: actor/authority guard, source binding, entity/binding guards in kind/ID order, books in UUID order, publication receipt. Entity/relationship mutation paths use the same guards so a contributor cannot become linked during an unlinked-entity permission check. Grant/account/book mutation paths use the same actor/book guards where authority changes apply. Do not hold these locks during downloads, model execution, export or preparation.

Two actors creating the same source serialize on the source binding. A grant expiry is evaluated at the activation instant even if authority revision has not changed. The website confirms source identity and current command origin from the stored context, not an arbitrary actor supplied in an event. A stale revision or denied activation is a terminal rejected receipt with no public mutation. The engine reconciles it before creating a different candidate/event.

## Storage retention and reclamation

| Material | Required lifetime / reclamation rule |
| --- | --- |
| Active website HTML/EPUB/cover/reader resources | Retain while active. Never delete through engine cleanup. Download/Kindle operations pin the immutable bytes they are actually using. |
| Superseded website build | Stop new openings. Retain bytes for existing authorized session/transfer pins; reader leases follow the two-hour retirement rule. Remove files only after pins expire and the build is still inactive. Keep compact build identity so notes can state an unavailable target without a false exact link. |
| Pending publication/engine sealed artifacts | Retain until the website receipt is terminal and reconciled; never remove evidence/files still needed by a retry or pending transfer. |
| Engine current-source evidence, frozen audit/reference snapshots, active-job checkpoints | Pin by source revision/job/evaluation manifest. Do not evict the evidence needed for the current build, active resumable work or unfinished evaluation. Older unrelated development history is not pinned merely because it exists. |
| Unreferenced failed/cancelled staging | An application-scoped cleanup may remove it after 24 hours and after verifying no active lease/outbox/inbox/receipt/reference needs it. Preserve bounded cause/checksum diagnostics. No cleanup is executed by this planning request. |
| Source cache budget | Existing 2 GiB bound is per operation's collection, not a 2 GiB whole-corpus promise. Measure total storage plus pinned evidence and website copies against E03's disk reserve; apply backpressure when pins prevent reclamation. Never silently evict current evidence to pass the budget. |
| Idempotency and terminal receipts | Retain compact key/payload-hash/outcome/source-build mapping while the operation/build or retry path exists, including terminal results. Pruning large logs must not allow an old key/event to create a second effect. |

Cleanup takes a locked, reference-checked claim for an owned build, moves it out of serving scope and rechecks current references before removal. Creating/renewing a transfer pin uses the same guard. A DB/IO failure leaves it retryable and visible; errors are not swallowed. Cleanup cannot traverse outside owned roots or delete another service's files, public asset caches, source documents or credentials. No historical generated-edition archive is required.

## Required regression scenarios

First activation duplicated/replayed concurrently; same title/different sources; same source/different operation IDs; source URL/ID conflict; actor revocation/expiry during transfer; null-target reservation; admin blank/role-order/cover override during generation; archived book; identical body with metadata-only change; failed EPUB→HTML conversion; crash before/after sealing and DB activation; old session/delivery pin during replacement; notes referencing reclaimed files; disk full with pinned evidence; cleanup racing a new pin; retry after terminal-receipt compaction. Check both intended output and absence of duplicate/partial/unauthorized effects.
