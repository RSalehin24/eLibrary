# Source job diagnostics and defect recovery

The processing list at `/manage/jobs/` combines search, job state/type, source
verification and contents-layout filters. The filters remain in the URL and can
be saved privately for the signed-in account. Search covers book/source title,
error code, job UUID and a diagnostic fingerprint prefix of 12–64 hexadecimal
characters. It never searches authentication inputs or source bodies.

`layout=multi_page` means the collected source manifest records paginated
contents or more than one contents page. Chapter page count alone is not that
evidence. `layout=nested` selects actual nested/sectioned contents structures;
`complex` combines those two conditions. `inline` selects source reading text
contained on a single page. `unclassified` explicitly identifies jobs without
retained layout proof. Selecting a layout always scopes the result to source
processing jobs, regardless of the other filters.

Multi-page/nested job cards and details show collected/expected **contents**
pages separately from chapter verification and collected source pages. Missing
contents pages continue to block publication. Previous `/multipage-toc/` and
`/processing-multi-page-toc/` links target the multi-page processing view.

## Existing job proof

New collection summaries retain a bounded layout object without source URLs,
HTML or storage paths. Existing snapshots can be inspected without mutation:

```sh
python app/backend/manage.py backfill_source_layouts --limit 10000
python app/backend/manage.py backfill_source_layouts --job <job-uuid> --apply
```

The command reads each job's exact retained `document_ref`; it does not infer a
historical job's layout from the current book. Apply changes diagnostic summary
fields only. Job state, revision, generation, verification verdict and attempt
history remain intact. Running jobs and snapshots that change during inspection
are skipped. Missing snapshots stay unclassified rather than reporting invented
coverage.

## Repeatable internal defects

Source `processing_internal_error`, `source_export_content_mismatch`,
`source_exports_missing` and `invalid_epub` outcomes retain a fingerprint derived
from their bounded error code, stage and relevant code version. The version is a
SHA-256 digest of the actual source/export/reader Python files involved, cached
per process. Restart workers and the dispatcher after deploying changed code;
mutating a running process's source tree is not a deployment mechanism.

The job view explains that processing is held and links to jobs with the same
fingerprint. It exposes no stack trace, private body, credential or filesystem
path. An unchanged code version cannot be retried through the source-resolution
workflow. Availability, rate limits, missing source text, permissions and mail
delivery keep their existing, separate policies.

After a relevant code update and dispatcher restart, normal reconciliation
considers up to 50 held source defects per tick. Changed code permits one fresh
bounded execution; another deterministic failure records the new version and
holds again. Recovery rechecks processing authority, source identity/revision,
book revision and the existing recovery choices. Cancelled jobs and jobs whose
assets have already been committed are excluded.

Good source pages and the curated document are retained. Derived exports,
staged asset references and prepared reader references are invalidated so the
fixed code rebuilds them. Previous physical files, publications, personal data
and attempt history are preserved. Each recovery adds an audit entry and a new
dispatch generation. Explicit inspection is also available:

```sh
python app/backend/manage.py recover_source_defects --limit 50
python app/backend/manage.py recover_source_defects --job <job-uuid> --apply
```

Dry-run output distinguishes a possible retry from a job still awaiting code or
input changes. Apply uses the same transaction and authority checks as automatic
reconciliation. It does not override source safety or publication checks.

## Explicit bulk recovery

`POST /api/v1/manage/jobs/bulk-control/` accepts 1–100 distinct jobs and an
idempotent operation UUID. Existing pause, resume and cancel commands remain
separate from source-only recovery actions:

| Action | Behavior |
| --- | --- |
| `retry_source` | Uses the job's actual safe retry or preparation-resume choice. Unlinked collection repairs retain good chapter pages and refresh the landing page. An unchanged code defect stays held. |
| `recreate_source` | Starts a new edition through the normal website regeneration service, retaining the book identity, previous files and personal data. A failed recovery is cancelled only in the same successful transaction. |
| `archive_book` | Withdraws the selected book into its reversible archived state through the existing lifecycle service. It does not delete the book or files. |

Every entry pins the displayed job revision. Recreate/archive additionally
require `expected_book_updated_at`; metadata authority and existing lifecycle
checks are applied to each book. A stale or unauthorized item cannot cancel the
old recovery operation. Recreate also respects the internal defect code gate.
Items with other active processing must be finished or stopped before changing
the book.

Results report each entry as accepted, conflict, not found, forbidden or rejected.
Other valid items still succeed. The operation receipt includes the action,
selection and both revisions; retrying the exact request returns the original
result after states change. Reusing its UUID for different revisions or an
unrelated account is rejected. New regeneration identifiers derive from the
bulk UUID and selected job UUID, so uncertain responses cannot create duplicate
editions.

Job list responses expose safe `source_recovery_actions` separately from generic
job `actions`, together with the current book revision. The list offers selection
for failed/recoverable source jobs and visible bilingual retry, recreate and
archive buttons. A control is enabled only when every selected job supports it.
Failed work never uses the paused-job resume command. The response omits private
inputs and reading bodies, and recovery choices do not add per-row SQL queries.

## Processing queue rotation

`BACKGROUND_PROCESSING_QUEUE` selects the durable-job processing destination and
defaults to `processing`. Use the same value for the dispatcher and processing
worker's `--queues` argument. The current platform Compose file supplies both;
its configured worker concurrency also sets the dispatch admission capacity.
Names are bounded to 255 ASCII bytes using letters, digits, dots, underscores and
hyphens, with an initial letter or digit. The reserved `delivery` and `amq.`
names are rejected. Account mail and Kindle continue to route to `delivery`.

A large backlog of obsolete broker envelopes can delay current fenced work even
when the database admission limit is small. To move current source jobs safely:

1. Stop the dispatcher, scheduler and processing workers gracefully, allowing
   the active attempt to finish. Preserve the broker queues and persistent data.
2. Set a fresh processing queue consistently for publisher and worker.
3. Inspect `python manage.py rebalance_source_dispatches`. Run it with `--apply`
   to fence already-published, unstarted current source tickets and create fresh
   generations through the existing audited admission service.
4. Start one matching processing pool, dispatcher and scheduler. Confirm that
   current work advances, outstanding dispatches remain bounded and no consumer
   was added to the delivery queue.

Old envelopes and attempt history remain intact. Generation checks reject old
tickets if their queue is consumed later. The rebalance command is source-only;
it does not replay an uncertain mail outcome or move other job kinds. Review
non-source pending work separately before changing a shared production queue.
Do not purge a queue to improve its dashboard count.
