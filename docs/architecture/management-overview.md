# Administration Overview

`/manage/` now shows actionable, permission-scoped information instead of a
welcome-only page. Django supplies anonymous-inaccessible, private/no-store/noindex
snapshots through `/api/v1/manage/overview/` and `/api/v1/manage/overview/work/`.

## What administrators can see

- Metadata administrators see counts for their manageable books only: total,
  processing, published and archived records. An Awaiting Publication count appears
  only when unpublished manual or historical records remain; it combines the API's
  legacy draft and ready counts. These records do not require manual review.
  Source books publish automatically after validation. Published books remain published regardless of the
  old editorial-review timestamp. Scoped grants, deletion and revocation use the
  existing catalog authorization query. The deprecated `editorial_pending` API
  field remains zero for compatibility and is not displayed.
- Global processors see source counts with exact catalog linkage, including
  unlinked and removed records, and processing-job state counts.
- Global access administrators see account counts and invitation work for
  targets they can edit. Protected accounts, their own account, and password
  reset activity are excluded from mail work summaries.
- Readers and disabled accounts cannot open either API. A processor cannot
  observe account-mail counts or failures. Unsupported sections return null.

Work summaries report actual queued/running/retry/paused/failed/attention states
and the five most recent failures with detail links. They omit raw inputs,
checkpoints, book bodies, mail bodies, credentials, and tokens. Invitation issue
titles are generic and disclose no recipient addresses.

Recent issues sort by completion time, falling back to their last update when
completion is missing. Older failures without completion timestamps cannot crowd
newer failures out of the five-item list.

Queue age measures elapsed time since `available_at` for currently eligible
queued/retry jobs. A future retry does not inflate it. Resuming paused work
starts a new availability period; the operation's original creation time remains
separate. No estimated percentage or invented execution progress is displayed.

## Refresh and layout

The initial snapshot is server rendered, including ordinary detail/navigation
links without JavaScript. Work status refreshes every two seconds while active
and fifteen seconds while idle, backs off on read failure, and suspends hidden-tab
polling. Those requests do not repeat catalog/source/account aggregates.
Administrators explicitly refresh the static summary using “সব তথ্য আবার দেখুন”.
Both snapshot timestamps remain visible. Failed refreshes retain prior data with
a notice that it may be stale.

Cards adapt continuously to available width and support keyboard/touch actions.
SQL aggregation and a fixed five-issue limit keep query counts bounded as job
volume grows. Book summaries select only the necessary metadata before aggregation;
issue queries join the book title without reading full content.

## Verification boundary

Thirteen PostgreSQL cases cover lifecycle counts without manual review, roles,
scoped books, deletion/revocation, exact source
links, future retries, resumed queue age, protected/reset mail isolation, detail
links, missing completion timestamps, and fixed query counts after adding 100 jobs.
Browser regression coverage includes Bengali/English counts with no review
counter, automatic-publication guidance in automation, no-JavaScript rendering,
work-only polling and permission-scoped failure navigation. Phone/desktop
screenshots are inspected against the served production build. Current results
and remaining simulator acceptance limits are recorded in
[the implementation handoff](../implementation-handoff.md).
