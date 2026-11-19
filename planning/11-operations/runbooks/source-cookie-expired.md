# Runbook: source-site cookie expired or expiring

Status: DRAFT

The one source credential is a cookie in a read-only secret file shared by `ingestion-api` and `ingestion-worker`; the database holds only status and expiry (REQ-ING-011). Status: `valid`, `expiring` (3 days before expiry, provisional), `expired`, `missing`.

**Symptoms.** Alert "source credential expiring or expired"; console credential badge; requests in `awaiting_credential`; a probe reports a login page, 401 or 403.

**Impact.** Scraping of pages that need the login stops and affected requests park (nothing fails, nothing is lost). Reading, browsing and already built books are unaffected.

**Quick check.** `POST /credential/check` (operate) enqueues a probe; confirm the status and `checked_at`. Rule out a source outage or a drift hold ([source-drift](source-drift.md)).

**Fix**
1. Log in to the source in a browser with the permitted account (D-03; login is never scripted and never submitted by the platform).
2. Copy the cookie into the secret file on the host (mode 0400, same path as the mounted secret); never paste it into the console, a ticket, chat or a log.
3. Run the probe again; status must become `valid` with a new expiry.
4. Resume parked requests (console action `retry` per request or bulk, bounded).

**If the source challenges the client repeatedly (bot protection).** Do not work around it: no evasion, no extra tools. Stop automation, supply a fresh cookie, and if the source blocks the client, raise it with the source owner as part of the permission discussion (D-03).

**If the cookie was exposed.** Follow [key-compromise](key-compromise.md) (revoke at the source first).

**Verify.** Badge `valid`; parked requests continue; no `auth_required` errors in new jobs.

**Follow-up.** Put the next expiry date in the operator's calendar; the alert fires 3 days ahead.
