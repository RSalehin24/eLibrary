# Administration Overview

`/manage/` now shows actionable, permission-scoped information instead of a
welcome-only page. Django supplies anonymous-inaccessible, private/no-store/noindex
snapshots through `/api/v1/manage/overview/` and `/api/v1/manage/overview/work/`.

## What administrators can see

- Metadata administrators see counts for their manageable books only: total,
  drafts, published records, and outstanding editorial review. Scoped grants,
  deletion, and revocation use the existing catalog authorization query.
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

Eleven PostgreSQL cases cover roles, scoped books, deletion/revocation, exact source
links, future retries, resumed queue age, protected/reset mail isolation, detail
links, missing completion timestamps, and fixed query counts after adding 100 jobs.
The current foundation regression run passed 706 backend tests. Four focused Chromium Overview journeys and ten
responsive checks passed, including no-JavaScript rendering, work-only polling,
failure navigation, all eight widths, and 200% text. Phone/desktop screenshots
were inspected. TypeScript, ESLint, mypy, Ruff, OpenAPI validation, and the
standalone production build passed.
The complete Chromium run passed all 101 journeys against the standalone build.

Source-processing/automation runs still need the new persisted workflow, so their
outcomes are not fabricated here. Live broker/worker interruption, physical-device
installation, production deployment, and the agreed capacity measurements remain
unverified. This increment does not complete the administration phase.
