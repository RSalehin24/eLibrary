# Runbook: ingestion queue or lease stuck

Status: DRAFT

The queue is the `jobs` table in the ingestion database, claimed with `FOR UPDATE SKIP LOCKED` under a lease (120 s visibility timeout, heartbeat every 30 s, provisional). Lease expiry moves a job from running back to queued (INV-ING-004). No work runs inside an HTTP request.

**Symptoms.** Jobs show `running` with no progress; queue depth or oldest-job age keeps growing; lease expiries rise; a request does not leave `scraping` or `building`.

**Impact.** Imports pause; reading and browsing are unaffected.

**Quick check**
1. Is `ingestion-worker` running and ready (`docker compose ps`, readiness)? Memory kills (JVM for epubcheck or a large book) show as restarts.
2. Console `GET /jobs?state=running` and `/jobs/{id}`: lease holder, last heartbeat, attempt counter, error class.
3. Is the credential `expired` (`auth_required` parks requests, not jobs; see [source-cookie-expired](source-cookie-expired.md))? Is a drift hold active ([source-drift](source-drift.md))?
4. Global limit reached (2 concurrent jobs, 2 per source)? Then it is queueing, not stuck.

**Fix**
- Worker down or out of memory: restart `ingestion-worker`; leases expire by themselves and the jobs are re-queued; steps are idempotent.
- A job stays leased after the worker is healthy: wait one lease period; if it is still running, set the cancel flag (`POST /jobs/{id}/cancel`, checked before each page and between stages), then retry (`POST /jobs/{id}/retry`).
- A job that keeps expiring on the same book (attempts reach 3): it moves to `failed` with a typed error; read `/jobs/{id}/attempts`; fix the cause (page size, block count over bounds, memory limit) and retry.
- Queue age grows with no expiries: check the database (connections, locks) and the worker loop log lines carrying the job id.

**Verify.** Oldest queued age falls; no job `running` past its lease without heartbeat; request statuses advance.

**Follow-up.** If epubcheck memory caused it, adjust the worker `mem_limit` or JVM heap cap (measured at P1) through the limits table; never raise it without recording the new total memory budget.
