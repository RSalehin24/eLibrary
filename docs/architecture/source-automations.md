# Source automations

Saved schedules also expose **Run Now**. `POST
/api/v1/manage/automations/<id>/runs/` accepts a client UUID and the saved schedule
revision. It locks and rechecks the caller and existing `run_as` account, then
reuses the scheduled occurrence admission and post-discovery processing pipeline.
The saved scope, page/book limits and rebuild policy apply. Disabled schedules
can run once; their enabled flag, next occurrence, calendar counter and revision
remain unchanged. The caller cannot override `run_as` or the saved policy.

An identifier-only audit receipt makes retries return the same queued or blocked
run, including after later schedule edits. Another caller or changed revision
cannot reuse its identifier. A currently active discovery or revoked saved owner
produces the ordinary recorded blocked outcome; normal job controls remain on
the linked progress page. Uncertain browser responses stop resubmission. Manual
admission does not bypass source availability, verification, permissions or mail
delivery policies.

`/manage/automations/` provides permission-scoped schedules, local start times,
IANA time zones, enable/disable controls, and paginated run history. It requires
global processing management authority. Creation uses an operation UUID;
updates require the displayed revision. Mutations require the same-origin
session and CSRF token. An uncertain request remains blocked until its saved
state is inspected. Reader accounts cannot use the workspace or APIs.

The schedule directory supports name search (`q`), enabled/disabled selection
(`enabled`), saved frequency (`frequency`) and name/next-occurrence sorting
(`sort`). Parameters are validated independently from history pagination;
counts include the same filters as the rows. Due-time ordering places paused
schedules last and uses the identifier to break ties. Numbered pagination retains
the active filters. Each row exposes Run Now and Settings & History directly;
phone records keep the same actions. Paused schedules display their paused state
instead of implying that their saved occurrence will run. Run Now reuses the same
revision, idempotency and uncertain-response safeguards as the detail screen.

Daily, weekly, fortnightly, and one/two/three/four/six-month schedules retain
their original local time. Monthly dates use the original anchor: January 31
becomes February's last day and then March 31. New starts in a daylight saving
gap are rejected. Later gap occurrences move forward; ambiguous occurrences use
the first offset once. The schedule's zone is independent of the operator's
browser and the server's default zone.

Run `python manage.py schedule_source_automations` as a separate service. Its
default 15-second interval is configurable from 1–60 seconds; `--once` runs one
bounded tick. SIGTERM and SIGINT stop between ticks. Each tick handles at most
20 due schedules. PostgreSQL locks and the unique occurrence key prevent
concurrent schedulers from creating duplicate runs. The job, dispatch record,
run history, and next occurrence commit together; the dispatcher performs
confirmed broker publication separately.

After downtime, one current run represents the missed period. Older occurrences
are counted in history, rather than dispatching a backlog. Revoked execution
authority, invalid source configuration, or another active discovery job create
a blocked run with a bounded reason. Every later occurrence rechecks the
current authority. Saving a schedule explicitly changes execution authority to
the saving administrator. Disabling prevents future runs; existing work remains
visible and controllable through Jobs.

Schedules choose full-catalog fetching (`fetch_all`) or a limit of 1–200 archive
pages. Processing can queue every eligible book (`process_all`), use a bounded
limit, or only fetch the catalog. Full mode creates one durable catalog batch
with a run association and a deterministic identifier. Run history links to that
parent's queueing controls and counts actual child book jobs separately. A retry
cannot duplicate the batch or accepted children. The main creation screen opens
the schedule form directly and links to saved schedules and their next run times.

In bounded mode, a processing limit of zero only
collects metadata. A limit of 1–100 snapshots that many recently seen, unlinked
sources, excluding active or failed source operations. Each selected record
keeps its original revision and a deterministic child operation UUID. A pause,
retry, or crash between child commit and parent checkpoint cannot duplicate
accepted work. Changed, missing, or rejected source records produce individual
outcomes. Configuration and permission checks fence each child dispatch.
Generated books publish automatically after successful source, chapter and file
verification. Missing source content waits for its next recheck; it cannot bypass
verification through a manual run.

Run history shows discovery state, processing counts, rejected dispatches,
missed occurrences, and links to job controls. Child job lists retain the run
filter across status changes and pagination. Active history polls every two
seconds, idle history every fifteen, with hidden-tab suspension and failure
backoff. The API reads bounded projections and aggregated counts, keeping
query counts independent of the displayed page size. Private pages and API
responses are noindex and no-store.

The isolated PostgreSQL and controlled-source tests cover scheduling,
calendar behavior, permission/CSRF enforcement, stale edits, idempotency,
concurrent schedulers, recovery, partial failures, and bounded history reads.
These checks do not contact source websites or use a live broker. Production
service deployment remains separate acceptance work. Discovery and processing
now share the request pacing described in [source discovery](source-discovery.md).
