# Source automations

`/manage/automations/` provides permission-scoped schedules, local start times,
IANA time zones, enable/disable controls, and paginated run history. It requires
global processing management authority. Creation uses an operation UUID;
updates require the displayed revision. Mutations require the same-origin
session and CSRF token. An uncertain request remains blocked until its saved
state is inspected. Reader accounts cannot use the workspace or APIs.

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

Each run discovers at most 1–200 archive pages. A processing limit of zero only
collects metadata. A limit of 1–100 snapshots that many recently seen, unlinked
sources, excluding active or failed source operations. Each selected record
keeps its original revision and a deterministic child operation UUID. A pause,
retry, or crash between child commit and parent checkpoint cannot duplicate
accepted work. Changed, missing, or rejected source records produce individual
outcomes. Configuration and permission checks fence each child dispatch.
Generated books still require editorial review and publication.

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
