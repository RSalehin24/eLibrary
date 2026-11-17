# Runbook — cutover from legacy

Status: DRAFT

Preconditions: gate G8 passed; two clean rehearsals on staging with an empty reconciliation report; rollback rehearsed; announcement sent 7 days ahead; D-03 answered.

1. **T-24 h** — Verify backups (legacy and new), freeze ruleset promotion, confirm certificates and DNS TTL ≤ 5 min.
2. **T-0** — Put legacy in read-only mode (maintenance banner; writes rejected). Record legacy DB dump hash.
3. Run the ETL ([migration](../../06-data/legacy-migration/README.md)) on the frozen dump into production databases.
4. Run reconciliation. **Stop** on any unexplained difference (go to rollback).
5. Start all new services; startup checks must pass; run smoke: top-100 books, 20 random highlights, 20 logins (sampled test accounts with known passwords), search known titles, one admin job on a fixture URL (no publish).
6. Switch the proxy to the new gateway. Watch dashboards 60 minutes (error rate, latency, auth failures, outbox age).
7. Announce; keep legacy running read-only for 30 days.

**Rollback** (any time before decommission): proxy → legacy, re-enable legacy writes. Changes made in the new system after cutover are exported by a script (accounts created, annotations) for manual replay; the window is kept short by decision at step 6 (≤ 60 min).

**Decommission gate** (≥ 30 days): no Sev1/Sev2 incidents attributable to migration; final export of legacy archived offsite; owner sign-off.
