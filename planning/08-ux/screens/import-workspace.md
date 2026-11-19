# Import workspace

Status: DRAFT

**Purpose**: one operator console for the whole ingestion pipeline: catalog sync, requests, REVIEW items, duplicate review, jobs and live progress, with the source credential status always visible. Replaces the legacy ten processing pages.
**Primary action**: depends on the bucket: Start sync, New request, Resolve. One filled button per view.
**Routes**: `/import/mirror`, `/import/requests`, `/import/requests/:id`, `/import/review`, `/import/review/:requestId`, `/import/duplicates`, `/import/duplicates/:id`, `/import/jobs`, `/import/jobs/:id`, `/import/activity`. **Auth**: `operate`. **Service owner**: ingestion (duplicate matching data: catalog). **Requirements**: REQ-WEB-017; REQ-ING-001..036. Flows: [import end to end](../flows/import-end-to-end.md), [review a duplicate](../flows/review-duplicate.md), [automatic publish](../flows/auto-publish.md).

## Data

All from [ingestion contract](../../07-contracts/http/ingestion.md): `GET /console/summary` (versioned snapshot) and `GET /console/events` (SSE with `Last-Event-ID`), credential, mirror entries and syncs, requests and actions, bulk actions, document, review and resolve, builds, diff, log, duplicate reviews, jobs and attempts, automation, rulesets, audit. Acquisition is GET-only (D-03) and there is no upload (D-42), so no screen offers either.

## Structure

- **Header**: source credential chip (`valid`, `expiring`, `expired`, `missing` with expiry and last check; button Check now; when expired a persistent banner "Source cookie expired, ask the host owner to rotate the secret file") and the automation card (schedule, next due, last run, limits; edit with validated interval, time and explicit time zone).
- **Bucket rail** (left rail on expanded and large, tabs scroller on medium, bottom segmented list on compact): Catalog (mirror), Requests, Needs review, Duplicates, Jobs, Activity. Count badges come from the one summary snapshot.
- **One table component** for every bucket: sortable columns, filters in the URL, selection with a sticky bulk-action bar (visible whenever rows are selected), status chips with text, row actions in a menu. On compact the table becomes a list with the same actions.
- **Catalog**: source listing (source-owned fields only) with filters incomplete, state, q; Start sync (page and error budget; idempotent while one runs; mutually exclusive with automation, so the button explains why it is disabled), progress and Cancel; create requests from selected entries (per-item result).
- **Requests**: New request (source URL or title; `Idempotency-Key`; exact duplicate refused with a link to the book). Detail: status and separate outcome (built, needs review, duplicate, failed), attempts and typed last error, curated document summary (sections, entities with evidence and confidence, dropped-block reasons, never full scraped text), builds with gate results (XML, structure, epubcheck, nav/NCX/TOC), reprocess diff against the published build, log. Actions: Retry, Cancel, Reprocess, Discard (allowed-source-state table: invalid ones are disabled with the reason, the server answers 409 otherwise).
- **Needs review**: items below the confidence threshold, locked chapters, layout drift. Per item: evidence (highlighted source blocks) and decision: accept, override value, drop. Nothing guessed is published. Keyboard: `j`/`k`, `1`-`9`, `Enter`.
- **Duplicates**: candidate beside matched catalog books (exact normalized key plus author, category, edition; near-matches listed, never merged). Decisions: create new, create as new edition, confirm duplicate, discard. Create new is disabled for an exact duplicate with the reason.
- **Jobs**: state (queued, running, succeeded, failed, cancelled), lease, attempts, error class (retryable, rate limited, auth required, permanent) in plain words; Cancel (cooperative, per page) and Retry.
- **Activity**: operator-action audit, read only ([audit](audit.md)).
- Publishing is automatic when every gate passed (D-49): a published request shows a link to the book; a build with a failed gate never appears to readers and stays in Needs review or Jobs (failed) for the operator ([automatic publish](../flows/auto-publish.md)). Edit, unpublish and delete are in [Catalog management](catalog-management.md) (`manage_catalog`).

Destructive actions (Discard, Cancel a running job, bulk actions) use the one Material confirm dialog naming the objects. Every command returns a per-item result shown in one grouped snackbar with a "Details" action; nothing is reported as success unless the server confirmed it. Display state follows server-confirmed state, not optimistic guesses.

## Live updates

One SSE connection per tab feeds all buckets (`request.changed`, `job.progress`, `sync.changed`, `credential.changed`, `automation.changed`). On reconnect the web resumes with `Last-Event-ID` or reloads the versioned snapshot; a visible "Reconnecting" chip appears after 5 s. Progress is a determinate bar with polite live text ("12 of 40 pages"). No polling, no forced reload.

## States

| State | Behaviour |
|---|---|
| Loading | skeleton rows, rail counts as placeholders |
| Empty | per bucket: "No requests yet, start by syncing the catalog or adding a request"; "Nothing needs review"; "No duplicates" |
| Ready | table and header |
| Error | banner with Retry; typed messages for `queue_unavailable`, `conflict`, `limit_exceeded` |
| Forbidden | no `operate`: the nav item is absent and the route shows the forbidden state; a 403 `mfa_required` goes to TOTP |
| NotFound | request, job or review no longer exists |
| Offline | stream chip "Reconnecting", actions disabled with reason, last snapshot kept |

## Layout

| Class | Layout |
|---|---|
| compact | one bucket at a time via a segmented list; rows are cards; detail is a separate screen; bulk bar is a bottom bar |
| medium | tabs scroller, compact table, detail in a sheet |
| expanded | bucket rail, dense table, detail in a right drawer |
| large | rail, dense table, detail drawer wider; evidence and decision side by side |

## Copy keys

| Key | en | bn |
|---|---|---|
| `ux.import.title` | Import | ইমপোর্ট |
| `ux.import.bucket.mirror` | Catalog | ক্যাটালগ |
| `ux.import.bucket.requests` | Requests | অনুরোধ |
| `ux.import.bucket.review` | Needs review | পর্যালোচনা দরকার |
| `ux.import.bucket.duplicates` | Duplicates | সদৃশ |
| `ux.import.bucket.jobs` | Jobs | কাজ |
| `ux.import.bucket.activity` | Activity | কার্যকলাপ |
| `ux.import.sync.start` | Start sync | সিঙ্ক শুরু করুন |
| `ux.import.request.new` | New request | নতুন অনুরোধ |
| `ux.import.credential.expired` | The source cookie has expired | সোর্সের কুকি মেয়াদোত্তীর্ণ |
| `ux.import.discard.confirm` | Discard “{title}”? | “{title}” বাতিল করবেন? |
| `ux.import.result.partial` | {ok} done, {failed} failed | {ok}টি সম্পন্ন, {failed}টি ব্যর্থ |

Analytics: none.

## Accessibility

Bucket rail is a labelled navigation; the table has header cells and sortable-column announcements; row selection and bulk bar are keyboard operable with `aria-live` count; progress and snackbar results in polite live regions; evidence highlights have a text marker, not colour only; shortcuts are documented and disable while a text field has focus.

## Open

I-4 (force-generate parameter of retry), I-6 (`awaiting_credential` wording), U-11 (a cross-request list of REVIEW items has no endpoint; `/requests?outcome=needs_review` assumed).
