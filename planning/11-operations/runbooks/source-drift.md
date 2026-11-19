# Runbook: source drift / canary failure

Status: DRAFT

Kept from v1 with the new names: console instead of Sources workspace, requests instead of jobs on engine state.

**Symptoms.** `SourceDriftDetected`; the structure fingerprint changed; a canary fixture fails; new scrape jobs of that adapter are on hold (running ones finish); requests raise a `SourceDrift` review item.

**Impact.** No new scrapes for that source; existing books and reading are unaffected.

**Quick check**
1. Console review item: compare the new fingerprint with last known good (which CSS tokens or landmarks changed).
2. Fetch one canary page by GET and look at the structure change. GET only; never log in or submit anything on the source (D-03).
3. Is the page a bot-challenge or login page (status 200 with a sentinel title)? That is a page error, see [source-cookie-expired](source-cookie-expired.md).

**Fix**
- Transient or partial rollout on the source: wait, rerun the canaries; if the fingerprint returns to last known good the hold lifts.
- Real redesign: update the adapter in code, add fixture pages for the new shape, run the gold snapshot tests (an adapter change must not alter parsing of stored snapshots), release it through the normal pipeline, run canaries, accept the new fingerprint, lift the hold.
- Existing snapshotted books need no reprocess.

**Verify.** Canaries pass; a test request scrapes and builds; no `SourceDrift` items remain open.

**Follow-up.** Add the new structure variant to the canaries.
