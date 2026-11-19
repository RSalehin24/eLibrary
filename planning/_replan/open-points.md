# Open points awaiting the owner (not decided)

Status: ACTIVE

Raised by writers; each is asked with `AskUserQuestion` when the wave that needs it runs. Recommendation in brackets.

| # | Point | Recommendation |
|---|---|---|
| O-1 | `user.deleted` event (account deletion) in the event list | add it |
| O-2 | Who sets security headers: gateway for API, web container for pages, Caddy only HSTS? | yes |
| O-3 | Work/edition grouping modelled, or only the human "new edition" action | not modelled |
| O-4 | Scope that guards CSV export and book deletion (`manage_catalog`)? | `manage_catalog` |
| O-5 | Search relevance gate (MRR/recall) MUST or SHOULD at this scale | SHOULD |
| O-6 | Where reader preferences (font, theme) are stored | reader service |
| O-7 | NFR numbers (latency, 10 rps, 8 GB, 100 GB, 1 MB body, 100-row page, 5,000-row CSV, 90 s start) | accept as provisional until the P0 baseline |

## Design questions to settle in the service designs (re-added; Wave B1 had dropped them)

| # | Question | Where it is resolved |
|---|---|---|
| Q-1 | Bengali full-text search quality on PostgreSQL meets the relevance target? | Spike S-01 at P0 (measured, not an owner decision) |
| Q-2 | What happens to bookmarks and highlights when a book gets a new published version (re-anchoring)? ADR-0015 and ADR-0023 must be reconciled | reader service design (Wave C) |
| Q-3 | Model the pull-based outbox (cursor reset, crash) in TLA+ | formal-models rework (Wave E) |
| Q-4 | Caddy publishes port 80 only for the certificate flow (stated in deployment-topology, missing from the brief) | confirm in deployment docs |

## Raised by contract writer B2 (not decided)

| # | Point | Recommendation |
|---|---|---|
| C-1 | Who may read identity's audit log (written as `manage_users`) | `manage_users` |
| C-2 | Does ingestion choose the book UUID in `POST /internal/books/{id}/versions`? | yes (idempotent publish) |
| C-3 | `POST /internal/books/match` added for duplicate matching (not in the brief) | keep; add to the brief |
| C-4 | Notes modelled as a field of a highlight (not a separate entity) | keep |
| C-6 | Invented provisional limits: profile image 2 MiB, 20 SSE streams (3 per user), upstream concurrency 64, Kindle 10 per hour | accept as provisional until the P0 baseline |

## Raised by service writer C1 (not decided)

| # | Point | Recommendation |
|---|---|---|
| O-8 | Role-to-scope table: operator = reader + operate + manage_catalog; admin = reader + manage_users + manage_catalog (carried from v1, unconfirmed) | confirm; owner decision |
| O-9 | notify mail kinds dropped without a requirement: password-changed notice and admin notice | add a password-changed notice (security signal), skip admin notice |
| O-10 | Web has no test-plan file (rows are in its README) | add 05-services/web test rows to 09-testing |

## Raised by service writer C2 (not decided)

| # | Point | Recommendation |
|---|---|---|
| P-2 | Annotations on a new version (Q-2): A server re-anchoring, B lazy client re-anchoring, C pin readers to the version they annotated | A (server re-anchoring); ADR-0015 then needs the update described in `reader/anchors.md` |
| P-3 | Does identity `verify` reject a ticket bound to a superseded version, or does the reader answer `copy_unavailable` and the web re-opens once? | reader answers `copy_unavailable` (as assumed) |
| P-4 | Reader CSS policy: drop publisher stylesheets, keep an inline-style allow-list | accept |
| P-5 | New limits rows: package size, saved-filter count, progress-write rate, purge delay | add as provisional |

## Raised by service writer C3 (not decided)

| # | Point | Recommendation |
|---|---|---|
| I-1 | epubcheck needs a Java runtime: run it in the worker container, or only in CI | CI only (keep Java out of the runtime image); the in-process structure audit stays the runtime gate |
| I-2 | Generated cover method; crates for HTTP, HTML, sanitizer, ZIP, XML | decide in the dependency batch (P1) |
| I-3 | Translator difference gives `needs_review` (INV-ING-023 has four outcomes) | yes, `needs_review` |
| I-4 | Force-generate: a parameter of `retry` (not in the HTTP contract yet) | add to the contract |
| I-5 | Contributor linking moved into catalog intake; catalog design to confirm | confirm |
| I-6 | `awaiting_credential` request state wording differs between state machine and HTTP contract | align to the state machine |
| I-7 | Provisional numbers: lease 120 s, back-off base 30 s, `job_log` 30 days, 6 h cooldown, 3-day expiring window | accept as provisional |

## Answered 2026-11-19 (moved to DECISIONS)

O-8 role scopes = D-45 · P-2/Q-2 annotations = D-46 · I-1 epubcheck = D-47 · O-6 reader preferences = D-48 · U-3 approval surface = D-49 (no manual approval; the whole publish process is automatic) · U-6 reader modes = D-52 (scroll and paged) · D-50 (old app shut down) and D-51 (gold labelling before permission, private research only) close the roadmap questions on the old host and on P0 labelling

Answered later the same day: C-5 notify direct routes = D-53 (events only) · U-12 identity batch grants = D-54 · export per service = D-55 · P-1 version states is moot: D-56 (versions are born `published`, no `draft` or `in_review`) · D-57 (publish gate fails closed when epubcheck cannot run)
