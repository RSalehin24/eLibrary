# Data, API, and state rules

All definitions here are **target behavior**. Reuse existing serializers and response envelopes where compatible. Generate OpenAPI and TypeScript from implemented serializers; this prose is not a replacement generated schema.

## Book and preparation

- A book has bibliographic identity, title, original-language credits, categories, language, series/sequence, edition/group, summary, cover, visibility, revision, and an optional active prepared build. No `record_type`, physical/digital enum, binding/price inventory fields, physical log relation, or review/approval field survives in the active model/API.
- Preserve publisher, language, compilation/structure facts, and bibliographic edition when useful. A field's `manual_` prefix does not prove that its information is physical-only. Retain useful facts under neutral names with all callers updated.
- Intake provenance (`source` or `epub_upload`) records how files arrived; it is not a book type, browse facet, user-facing classification, or permission boundary. New IDs need not match development history.
- Use the existing `updated_at`/`expected_updated_at` revision convention for metadata and annotations. A stale revision returns `409 state_conflict`, changes nothing, and preserves the draft. Validate allowed fields explicitly; reject attempts to write removed/protected fields.
- Private integration additionally uses monotonic integer `catalog_revision` per book and `authority_revision` per actor. Increment catalog revision with a metadata/cover/archive/publication commit, and authority revision with account/grant changes. They are not timestamps or substitutes for current expiry/TOTP/permission checks. Add these counters with generated schema changes at E01; browser metadata forms keep their existing timestamp revision convention.
- Book visibility is `unpublished`, `published`, or `archived`. Preparation uses existing `pending`, `preparing`, `ready`, `failed` meanings. These are independent axes: regenerating a valid published book does not hide its active build.
- No manual publication endpoint is needed to finish creation. Preparation success activates a build and automatically makes a non-archived book available. An explicit administrator archive remains an availability control, never a review gate. A background job must not reverse an archive; explicit restoration uses the administrator lifecycle control and still requires a ready build.

| Event | Preparation/result | Visible behavior |
| --- | --- | --- |
| Accept source/import command | `pending`; job queued | Show queued operation. Never show Prepared merely because a record exists. |
| Start building | `preparing` | Show actual stage; no fabricated page/queue percentages. |
| All integrity checks and reader preparation succeed | `ready`; activate atomically | HTML, EPUB, and reader use the same verified build; automatic publication. |
| First build fails | `failed`; no active build | No Read/download/Kindle success action; show cause and permitted recovery. |
| Replacement fails | Candidate failed; active build retained if correct | Keep the correct active build available; show failed update separately. |
| Active content is proven defective | Unavailable independently of candidate state | Deny protected delivery consistently until a verified replacement exists. |
| Administrator metadata/cover save | Valid revision committed | No pending-review state, loss of availability, or approval task. |
| Source marks work unfinished | Independent `source_incomplete` fact | Do not label the preparation failed solely for this fact. |

## Website API changes

Keep current `/api/v1/catalog/`, `/manage/`, `/me/`, `/reading/`, `/auth/`, and `/delivery/` families. Apply removals across legacy APIs still served by the application as well. Remove physical catalog/export/log endpoints and review/publish-as-approval endpoints from route registration and generated contracts; requests receive `404`. Retire physical/review grant options so administrators cannot recreate them.

Public metadata serializers whitelist safe metadata; never return bodies, source snapshots, private file paths, service credentials, or another account's state. Account-dependent action flags come from current server authorization. Add one authoritative `can_edit_book` capability using the administrator rule; UI consumers must not infer it from metadata grants.

Reuse the error envelope `{code, detail, field_errors}` from `VersionedAPIView`. Invalid fields/unsupported removed filters return `400` at APIs; stale revisions/idempotency conflicts return `409`; unauthenticated requests follow current Django/DRF session behavior; denied actions return `403`; hidden/missing private resources return `404`; rate limits include the existing retry information. A `5xx` or transport timeout never means success.

Website URL/saved-filter normalization discards retired book-type and added/request-date browse keys before constructing API calls. Do not carry their values forward. Keep schedule and grant-expiry date fields. Define a stable secondary ID ordering for paginated lists. Search/filter/sort changes reset page to 1; changing page retains all valid submitted conditions. An out-of-range UI page normalizes once to the last valid page (1 when empty) with no loop; APIs keep their documented validation.

Exports use the same permission-filtered query as results and include all matching rows, without the current page limit. A pending save/export cannot be submitted twice. Saved-state operations are account/book scoped and idempotent; optimistic state rolls back on failure and invalidates affected counts/lists after confirmation.

## Reader locations and concurrent progress

Extend the existing reader session/progress serializers during R03, keeping the paths in `config/api_v1.py`. The target session adds `build_id` and progress `revision`. The target progress PUT accepts `last_location`, finite `progress_percent` (0–100), `build_id`, `expected_revision`, and `mutation_id` (UUID). It returns the committed location, build, and incremented revision. Reusing a mutation ID with the same payload returns the original response; a changed payload is `409 idempotency_conflict`.

The website serializes writes for `(account, book, build_id)`. Add a build-bound progress record and mutation receipt through generated R03 migrations; the existing book summary is a projection, not a second writable position. A stale revision returns `409 progress_conflict` without moving the stored position. Do not compare percentages to pick the winner: readers can intentionally move backwards. One tab coalesces its own pending locations and allows one write in flight. Lost responses retry the same mutation ID; a new captured location uses a new ID only after the prior outcome is reconciled. Retain compact receipts for the build's reading lifetime and bind them to account/book/build; replay from another account or build cannot succeed.

After a confirmed save, broadcast only account-context generation, book/build IDs and committed revision using the existing account-channel pattern; never send a session credential or passage text. A receiving tab fetches the authorized current progress. It does not attach a newer revision to a different local passage. If it has no unsaved movement, suspend its writes and offer to resume the other session; either resume that confirmed passage or explicitly save this local passage against the fetched revision. A tab with unsaved movement keeps its passage and stops automatic writes on conflict. Show “Continue from other session” and “Save this position”; a second conflict stays visible. No background retry silently overwrites another tab. Without BroadcastChannel, the next versioned PUT still detects a conflict; correctness never depends on receiving the broadcast.

Use anchors tied to the current build/chapter and a verified text selection/offset; media positions include resource and time (and spatial position where supported). Capture before reflow and restore after layout/fonts/images settle. Do not publish transient scroll offsets during restoration. Invalid/unresolvable anchors show an explicit fallback to chapter start; do not claim an exact resume. An old-build anchor is never applied to a new build automatically.

New sessions and annotations work within their prepared build. When a newer build activates, an already open session may finish on its valid leased resources; a genuinely new opening uses the new build. Writes from an older open build update only that build's position; they cannot replace the active-build Continue Reading summary. A summary exposes a mismatched old-build position as unavailable for exact resume rather than reusing its coordinates. The UI explains that older targets cannot be opened when their files are no longer retained; existing note text remains readable/editable/deletable under its ownership/revision rules. No historical CFI/annotation migration or generated-edition archive is required.

Reader refresh/session GET resumes the existing session without consuming another read-once opening. A read-once account can use its still-valid original session/build until its fixed expiry; it cannot launch a replacement build or extend the old lease through refresh. An expired/consumed opening remains denied unless current independent durable/ownership authority permits a new opening. Test concurrent reader/HTML launches under the same account lock; failed preparation consumes nothing. The retained default session duration is two hours. Retired files are leased at most until the earlier of the original session expiry and two hours after replacement; retirement never renews a session. Current permission/defect checks still deny requests immediately when applicable. Resource/file cleanup follows the [publication lifecycle](publication-context-and-lifecycle.md).

## Jobs and truthfulness

Retain the current job states `queued`, `running`, `retry_wait`, `paused`, `cancelled`, `succeeded`, `failed`, `needs_attention`. `needs_attention` means an explicit uncertain technical outcome; it must never be relabelled Needs Review or require editorial approval. Structured `reason_code`, `stage`, `available_at`, generation, and attempt IDs explain what can happen next.

| From | Event | To/constraint |
| --- | --- | --- |
| `queued` | Successful fenced claim | `running` |
| `queued`, `retry_wait` | Pause/cancel accepted | `paused` / `cancelled`; invalidate pending dispatch generation |
| `running` | Pause/cancel requested before publication fence | Remain `running` with Stop requested until a safe boundary acknowledges it |
| `running` | Safe boundary honors stop | `paused` / `cancelled`; no subsequent publication by the old attempt |
| `running` | Retryable fault/resource wait | `retry_wait` with cause and next time |
| `running` | Proven permanent defect/invalid input | `failed`; do not loop unchanged input/code |
| `running` | Uncertain external effect | `needs_attention`; reconcile receipt before retry |
| `running` | Durable publication receipt/defined operation completed | `succeeded`; parent queueing success does not imply child success |
| `paused` | Authorized resume | `queued` with a new fenced generation |
| `failed`, `needs_attention`, `retry_wait` | Valid recovery/reconciliation | `queued` only under the recovery policy; never bypass validation |
| `cancelled`, `succeeded` | New request | New idempotent operation; never resurrect a terminal attempt |

Revalidate current revision/authority under locks before state changes. A command with a stale revision has no side effect. Per-target bulk results distinguish accepted, already active, skipped, denied, and failed; report partial completion honestly. Detailed worker behavior is defined in the [engine operations plan](../../engine/operations/jobs-updates-and-recovery.md).

Once the engine has atomically committed the publication outbox event and set stage `publishing`, pause/cancel returns `409 publication_in_progress` until its receipt is resolved. It does not acknowledge a stop after the irreversible handoff has begun. The receipt/locked recovery policy is defined in the engine operations plan.
