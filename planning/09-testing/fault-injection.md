# Fault injection catalog

Status: DRAFT (six-service design)

Each scenario states the fault, the expected behaviour and the invariant. Faults are injected on the ephemeral Compose stack by container kill (`docker kill`), network cut (`docker network disconnect`), the `source-fixture` and `mail-sink` containers, file-permission and fake-clock overrides. The rows marked PR run on every pull request, all rows run nightly. Per-service rows (TST-*) hold the detail; the IDs below are the catalogue.

| ID | Fault | Expected | Tests | PR |
|---|---|---|---|---|
| FI-01 | Source outage: 404, 5xx bursts, timeout, truncated body, redirect loop, 50 MiB page, 200 sentinel page, 429 with `Retry-After` | typed outcomes, bounded retries and time, no hang; request waits or fails with a reason; no non-GET sent | TST-ING-038, TST-ING-011 | yes |
| FI-02 | Source cookie expires or is rejected mid-scrape | request `awaiting_credential`, status visible on the console; replacing the file plus a passing probe resumes from the cursor | TST-ING-039 | yes |
| FI-03 | Kill the ingestion worker (SIGKILL) at every step boundary and mid-page | request completes once, identical output, exactly one catalog version, no stranded lease beyond the lease length | TST-ING-040, TST-ING-005 | yes |
| FI-04 | Queue lease loss: heartbeat stops (hung thread), lease expires, a second worker claims | zombie write rejected by epoch; one outcome; job returns to `queued` or `failed` by rule | TST-ING-005, TST-ING-001 | yes |
| FI-05 | Mail failure: SMTP down, 5xx or timeout for a long time | notify retries with back-off then marks failed; invites, resets and sign-in keep working; mail sent after recovery | TST-NTF-004, TST-NTF-016 | yes |
| FI-06 | notify down | `email.requested` and `kindle.requested` accumulate in the outbox; account creation and reset request still succeed | TST-NTF-004, TST-CAT-037 | no |
| FI-07 | PostgreSQL down or connection reset mid-transaction (one service, then all) | readiness fails and traffic gets typed 503; retries are idempotent; no duplicate rows; recovery without manual steps | TST-IDN-015, 017, TST-CAT-022 | yes |
| FI-08 | identity down | public metadata browse still works (cached public routes are gateway-independent of sessions); every authenticated route fails closed with a typed error; reader open consumes nothing | TST-RDR-027, TST-GWY rows | yes |
| FI-09 | Reading ticket expiry: replay after 15 minutes, for another book or user, after grant revocation or new version | rejected; web refreshes once; `copy_unavailable` handled (P-3 OPEN) | TST-RDR-007, TST-RDR-008, TST-RDR-030, TST-IDN-030, TST-WEB-019 | yes |
| FI-10 | Read-once, two devices open at once | exactly one redemption consumes it; a missing file consumes nothing | TST-RDR-010 | yes |
| FI-11 | Catalog unreachable while the reader builds a copy | retries, `copy_unavailable` on open, nothing half-built served; later rebuild succeeds | TST-RDR-027 | no |
| FI-12 | Crash between a database commit and the outbox read; duplicate and reordered event delivery; cursor reset | one effect per event; consumers converge; published set equals reader copies | TST-ING-005 (Outbox model), TST-CAT-037, REQ-NFR-013 | yes |
| FI-13 | Publish saga: catalog down, timeout, lost response, crash between call and commit | exactly one version per build identity; failed build leaves nothing visible | TST-ING-031, TST-CAT-022 | yes |
| FI-14 | Corrupt or missing artifact on the file volume (bit flip, deleted) | hash check fails with a typed error and an alert; wrong bytes never served | TST-CAT-020, TST-CAT-021, TST-RDR-005 | no |
| FI-15 | Disk full during build or file write | build fails typed; no partial version visible; space freed and retry succeeds | TST-ING-040, TST-CAT-022 | no |
| FI-16 | Two operators or managers edit or unpublish the same book at once | second gets `stale_revision`; no lost update | TST-CAT-006 | yes |
| FI-17 | Large bodies, slowloris, many connections, rate-limit burst at the gateway | limits enforced; services stay responsive | TST-GWY-009, TST-GWY-010, TST-GWY-013, TST-GWY-014, REQ-NFR-006 | no |
| FI-18 | Clock skew between containers (minutes) | tickets and sessions follow identity's clock only; no panic | TST-IDN-010, TST-IDN-029 | no |
| FI-19 | Restore from the monthly backup into a fresh host | stack consistent, outbox cursors reconcile, RTO within 4 h (REQ-NFR-004); data after the backup is lost by design (D-33) | TST-IDN-013 area drills, TST-NTF-012, TST-ING-036 | no (drill monthly) |
| FI-20 | Memory limit hit on one container (OOM kill) | restart policy brings it back within 15 s; other services unaffected | REQ-NFR-005, 014 | no |

Open: the exact failure behaviour of cached public routes when identity is down (FI-08) follows the gateway design and is not decided here; whether FI-19 is automated or a manual drill is a P1 decision.
