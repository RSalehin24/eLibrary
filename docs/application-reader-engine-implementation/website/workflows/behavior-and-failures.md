# Website workflows and failure behavior

Tasks W05–W07. Apply the state packs and all routes from the [interface matrix](../interface/design-and-route-matrix.md). Each row below defines a task outcome, adverse cases, and a regression seam. A displayed disabled action must explain availability; never show an enabled action that is guaranteed to fail.

## W05: discovery and personal library

| Flow | Expected result | Adverse cases and required checks |
| --- | --- | --- |
| Home/role entry | Admin enters creation/first authorized section; reader enters useful My Books/Continue Reading. Reader View and Return to Admin preserve account identity. | Slow account load cannot expose unauthorized links or shift action columns. Anonymous home never includes private summaries. |
| Browse/search | One submitted query controls list, count, pagination, and export. Filters are useful optional metadata; URL back/forward restores the submitted state. | Cancel/ignore superseded responses. Clearing an unsubmitted draft resets the input; saved-search reopening restores its submitted values. Retired filters cannot reappear in generated links. |
| Cards/tables | Long names wrap; equal row heights and consistent footers; save state, progress, and Kindle actions remain usable. | Missing/delayed cover, many credits, Bengali wrapping, account data arriving late, stretched-link overlap, and narrow table scrolling. |
| Book details | Cover/title/credits lead. Read/Continue, Save, permitted Kindle/EPUB, new-tab HTML, linked metadata, notes, and progress have a stable hierarchy. | Test ready, preparing, failed, source-incomplete, archived, denied, and missing independently. Opening HTML preserves safe target/permission behavior. No type/review label. Admin-only Edit. |
| Bibliographic editions | Show current work/edition identity, access, and destinations. | Never treat regenerated files as a mandatory historical edition archive; missing/denied siblings are truthful. |
| Directories | Authors first, explicit other roles; accurate permission-filtered counts and linked books for contributors/categories/series/reading lists. | Empty entity, multiple roles, duplicates, long aliases, ordered lists, source provenance, and hidden collections. No name-similarity-only identity merge. |
| My Books | Saved/owned/recent/granted scopes have clear membership actions/counts; personal detail preserves return context. | Removing a saved-only row updates results/counts; duplicate save/remove does not duplicate membership; failed optimistic write rolls back. |
| Export | Compact post-result disclosure downloads all matching authorized records, using submitted state. | Multiple pages, sort order, no results, failed request, repeated click, Unicode filenames, revoked access, and a scope differing from the visible page. |

Reuse `src/lib/catalog-state.ts`, existing catalog APIs, shared cards/results/pagination/export controls, and query-cache conventions. Extend current catalog/personal-library/entity/details/exports browser specs and corresponding backend discovery/export tests.

## W06: personal activity and account flows

| Flow | Expected result | Adverse cases and required checks |
| --- | --- | --- |
| Notes | Four reachable views: highlights, notes, quotes, bookmarks. Aligned controls; grouped cards; separate Edit and Go to passage. | Exact reader target; slow annotation load cannot clear a selected passage; delete/save conflicts preserve drafts; no-match differs from no annotations; user B cannot access user A's records. |
| Kindle send | Allowed recipients, file/build and target book are clear before explicit Send. Show accepted/queued/running/per-recipient outcomes and private history. | No recipient, unready EPUB, expired grant, double submission, timeout after SMTP acceptance, cancellation race, partial outcomes. Unknown arrival is uncertain, not delivered. Resend is explicit, never an automatic duplicate after uncertainty. |
| Profile | Names/photo/password/Kindle recipients/security are coherent and validated. Changes invalidate affected session/capability data. | Invalid image bytes/type/size, blocked file selection, password/session failures, duplicate recipient, failed upload/removal, required conditional TOTP, and pending updates. |
| Login/TOTP | Field validation, rate limits and next step are clear; TOTP appears only when required by that flow. | Pending submission, expired session, wrong code, recovery, safe same-origin return, logout in another tab, disabled/inactive account. |
| Password setup/reset | Non-enumerating reset request; one-use nonce; setup/reset confirmation and TOTP policy remain server enforced. | Expired/replayed/invalid link, password mismatch, duplicate submit, uncertain mail outcome, back/refresh, unsaved draft/update safety. |
| Help/About/Contact | Accurate bilingual content, readable width, working links and available contact destination. | Narrow/enlarged text, unavailable configured email, keyboard navigation; never fabricate a contact address. |

Reuse `src/components/personal-notes.tsx`, profile/security/password/Kindle components, annotation and account APIs, `src/lib/account-channel.ts`, and existing account-boundary/unsaved-change/update mechanisms. Do not send external mail as part of fixtures; verification uses loopback SMTP and synthetic recipients. Real external delivery requires a separate explicit request.

## W07: administrative flows

| Flow | Expected result | Adverse cases and required checks |
| --- | --- | --- |
| Overview | Real authorized counts, oldest eligible work, active jobs, actionable faults and destination links. | Refresh job status independently of static counts; no wall of unrelated statistics or invented progress. |
| Book Creation/source list | Fetch All, Process All, EPUB upload, and Scheduling are discoverable. Selection says current page/explicit IDs/all matching and freezes scope at confirmation. | New rows after selection, stale catalog revision, duplicate command, per-item denial/already-active/skipped/failure, interrupted parent. Queueing complete never means all books prepared. |
| Source detail | Source identity, linked current book, structure/update evidence, actual generated files, reader launch, and permitted recovery controls. | Missing/unavailable/partial source, failed extraction, denied source access, stale build; no Check/Review button or manual publication requirement. |
| Unfinished Books | Same compact source container, source-unfinished/all-updated scopes, last sync, actual body/structure/credit/cover/completion changes and regeneration status. | Source finished later, metadata-only change, unchanged contents with changed body, temporary unavailability, bad extraction. Never equate source unfinished with failed preparation. |
| Managed books/editor | Search/table/files/admin Edit; valid saves preserve availability and draft context across metadata/files/relationships sections. | Conflict, revocation, upload failure, unknown save outcome, pending replacement, unsaved file selection, duplicate links/roles/order, and catalog title/slug change. No historical revision feature is required. |
| EPUB intake/result | Validated file/metadata, real preparation and useful Read/HTML/EPUB/management result destinations. | Wrong type/size/ZIP, no ready files, duplicate intake, source-text mismatch on replacement, preparation failure. No “digital book” choice or manual Publish step. |
| Managed entities | Consistent four-kind list/create/edit, accurate roles/counts, provenance and links; reading-list ordering. | Exact scoped contributor/category restrictions, remote-search cancellation, duplicate names, unsupported kind, stale save. Linked book metadata/associations require admin authority; ordinary authorized reading-list curation follows W02's explicit exception. |
| Jobs | Real states/stages, understandable wait/queue estimate, pause/resume/cancel/recovery, optional technical details. | Stop requested is distinct from stopped; conflicting revision, lost lease, restart, stale worker, expired authority, rejected publication, ambiguous technical result. |
| Schedules | Task/scope/time/enabled/next run, direct Run Now/settings/history, complete Reset. | Current supported frequencies, month-end, Dhaka midnight/noon, disabled/null next run, duplicate scheduler tick, manual/scheduled overlap, missed occurrences, revoked run-as account. |
| Users/access | Search, account detail, identity/security/invitations/grants, expiry and protected/self-edit rules are clear. | Last administrator/protected account policies, forbidden self-escalation, stale updates, expiry at commit, partial bulk grant results, cancelled remote lookup. Do not widen grant policies during UI cleanup. |
| Invitations/mail | Queued private outcome, explicit permitted resend/cancel, correct one-use links. | Unknown SMTP outcome does not automatically send again; another account cannot inspect link/history; loopback verification only. |

Reuse existing `src/api/{sources,source-processing,jobs,automations,managed-access,account-mail}.ts`, management components, and `tests/backend/processing/`, `tests/backend/auth/` plus current source/automation/jobs/admin/account browser specs. When E01 moves ownership, website source/job/schedule adapters switch to private contracts together with backend callers; account/Kindle delivery stays website-owned.

## Common mutation and polling policy

Serialize one user mutation per form; disable duplicate submission through button and actual keyboard handlers. Validation errors retain all input and put focus on an error summary/field. A `409` preserves the draft and offers fetch-latest/reapply; do not silently overwrite. A timeout queries the stable operation/idempotency outcome before enabling a new request. Never clear an unsaved form merely because polling refreshed a parent query.

Use existing bounded polling with backoff/visibility cleanup. Abort obsolete reads and ignore stale completions after route, selection, account, or source-revision changes. Display a failed refresh with retry while preserving the last confirmed data; do not show stale data as a new success. Long-lived pending/failed state has a useful next action.

W05–W07 close only after the applicable state packs, permission checks, keyboard/touch operations, and bilingual rendered inspection pass. Apply [test strategy](../../shared/verification/test-strategy.md), including regression demonstrations and explicit limits of simulated delivery/devices.
