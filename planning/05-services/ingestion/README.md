# ingestion

Status: DRAFT (rewritten for the six-service architecture, D-31/D-32; basis `_replan/new-architecture.md` section 6; requirements [ING](../../02-requirements/ing-ingestion.md); HTTP contract [ingestion](../../07-contracts/http/ingestion.md))

The single pipeline from the source site to a candidate book version in the catalog: mirror sync, request, scrape, curate and validate, duplicate review, EPUB build, publish. Operator-only (`operate`). Intake is scrape-only (D-42, REQ-ING-031): there is no manual upload. Nothing is migrated from the legacy app (D-32): books are re-ingested by this pipeline.

| | |
|---|---|
| Owns | source mirror, requests, jobs and leases, scrape cache (files), curated documents (files + rows), review items, duplicate reviews, build artifacts (candidates), source-credential status, automation settings, sync runs, console event outbox, ingestion audit log |
| Does not own | books, versions and files (catalog), accounts and scopes (identity), mail (notify), the reading copy (reader) |
| Containers | `ingestion-api` (HTTP + SSE; inserts rows, never runs pipeline work) and `ingestion-worker` (same image, command `worker`: claimer, executors, reaper, scheduler tick, event consumer, retention) |
| Emits | outbox `events` for the console: `request.changed`, `job.progress`, `sync.changed`, `credential.changed`, `automation.changed`, `build.finished` (internal only) |
| Consumes | catalog `book.published`, `book.unpublished`, `book.version_changed` (pull with stored cursor, idempotent) |
| Calls | the source site (GET only); catalog internal API (`POST /internal/books/{id}/versions`, `POST /internal/books/match`, `GET /internal/books`, `GET /internal/events`); identity `POST /internal/check` for `operate` |
| Called by | web operator console through the gateway (`/api/ingestion/*`, scope `operate`) |

## Pipeline

```
 mirror sync ─► request ─► scrape ─► curate/validate ─► duplicate review ─► build EPUB ─► publish (automatic when all gates passed)
 (GET listing)  (one model) (GET only) (pure, versioned)  (explicit state)    (audit gate)    idempotent; only after every gate passed
                                                                                              │
                                  catalog publishes in the same call ─► outcome published
```

- Every arrow is a row in `jobs`, claimed with `FOR UPDATE SKIP LOCKED`. No work in an HTTP handler, no Redis, no Celery, no inline fallback (REQ-ING-005).
- Curate, validate, duplicate classification and build are pure functions of `(scrape manifest, ruleset version, overrides, builder version)`; derived artifacts are regenerable (REQ-ING-013).
- Nothing is dropped silently: dropped blocks carry a reason code (REQ-ING-014); unresolved facts become review items.
- A failed build never leaves anything visible: catalog sees nothing until every gate passed and `publish` succeeds; then the book is visible with no human step (D-49). Anything that fails a gate stays in the review queue (duplicate review, `needs_review`, `failed`) where an operator acts.

## Design rules (answer the legacy defects)

| Rule | Where |
|---|---|
| One request model; execution status separate from domain outcome | [domain model](domain-model.md), [state machines](state-machines.md) |
| Source mirror and workflow state are separate tables; re-sync never touches workflow | `mirror_entries` vs `requests` |
| Postgres queue: leases, heartbeat from the working thread, typed errors, cooperative cancel per page, idempotent steps | [orchestration](orchestration/README.md), [state machines](state-machines.md) |
| GET-only acquisition, explicit source cookie (secret file), visible expiry status, polite delay, honest User-Agent, scrape cache as files | [acquisition](acquisition/README.md) |
| Bengali-correct normalization (NFC, vowel signs kept), tested lexicon, whole-token matching | [domain model](domain-model.md), [rulesets](rulesets/README.md) |
| Structure, TOC, front matter, dedication, book info | [structure](structure/README.md), [classification](classification/README.md), [block-ir](block-ir/README.md), [entities](entities/README.md) |
| Duplicate rule: exact normalized key + author + category + edition; near matches listed, never merged | [entities](entities/README.md), [domain model](domain-model.md) |
| EPUB build: escaping on, sanitized, images and fonts packaged, nav + NCX, audit gate | [builder](builder/README.md) |
| Publish saga: idempotent candidate to catalog | [orchestration](orchestration/README.md), [state machines](state-machines.md) |
| Console live updates: SSE + versioned snapshot | [API](api-contract.md) |
| Automation: stored `next_due`, claimed under lock | [state machines](state-machines.md) |
| Retention: raw pages 30 days | [domain model](domain-model.md), [orchestration](orchestration/README.md) |

## Requirement coverage (every REQ-ING row)

| REQ | Where specified | Tests |
|---|---|---|
| REQ-ING-001 | [domain model](domain-model.md) Requests; [state machines](state-machines.md) Request | TST-ING-001 |
| REQ-ING-002 | domain model Source mirror; state machines Sync run | TST-ING-002 |
| REQ-ING-003 | state machines Sync run | TST-ING-003 |
| REQ-ING-004 | domain model Jobs; state machines Job | TST-ING-004, TST-ING-005 |
| REQ-ING-005 | [API](api-contract.md) rule 1; [orchestration](orchestration/README.md) | TST-ING-006 |
| REQ-ING-006 | domain model typed errors; orchestration | TST-ING-007 |
| REQ-ING-007 | state machines Job (cancel, idempotency); acquisition | TST-ING-008, TST-ING-040 |
| REQ-ING-008 | state machines action table; API | TST-ING-009 |
| REQ-ING-009 | API; domain model audit | TST-ING-010 |
| REQ-ING-010 | [acquisition](acquisition/README.md) | TST-ING-011, TST-ING-038, TST-ING-042 |
| REQ-ING-011 | acquisition Credential; state machines Credential | TST-ING-012, TST-ING-039 |
| REQ-ING-012 | domain model Scrape cache; acquisition | TST-ING-013, TST-ING-036 |
| REQ-ING-013 | domain model Curated document; [block-ir](block-ir/README.md) | TST-ING-014 |
| REQ-ING-014 | block-ir Conservation ledger | TST-ING-015 |
| REQ-ING-015 | [structure](structure/README.md); [builder](builder/README.md) | TST-ING-016 |
| REQ-ING-016 | structure Type A | TST-ING-017 |
| REQ-ING-017 | structure Type B | TST-ING-018 |
| REQ-ING-018 | acquisition Completeness; domain model Validation | TST-ING-019 |
| REQ-ING-019 | [entities](entities/README.md); [classification](classification/README.md) | TST-ING-020 |
| REQ-ING-020 | classification post-decode rules | TST-ING-021 |
| REQ-ING-021 | classification R8; builder labels | TST-ING-022 |
| REQ-ING-022 | domain model Bengali normalization; [rulesets](rulesets/README.md) | TST-ING-023 |
| REQ-ING-023 | domain model Duplicate review; entities section 4; state machines Duplicate review | TST-ING-024, TST-ING-025 |
| REQ-ING-024 | builder Rules for the writer | TST-ING-026 |
| REQ-ING-025 | builder | TST-ING-027 |
| REQ-ING-026 | builder Validation gate | TST-ING-028 |
| REQ-ING-027 | builder Cover; acquisition | TST-ING-029 |
| REQ-ING-028 | builder Preview | TST-ING-030 |
| REQ-ING-029 | orchestration Publish; state machines Publish | TST-ING-031, TST-ING-040 |
| REQ-ING-030 | rulesets | TST-ING-032, TST-ING-041 |
| REQ-ING-031 | this page (intake); API | TST-ING-033 |
| REQ-ING-032 | API Live updates | TST-ING-034 |
| REQ-ING-033 | state machines Automation | TST-ING-035 |
| REQ-ING-034 | domain model Retention; orchestration | TST-ING-036 |
| REQ-ING-035 | domain model audit and logs; API | TST-ING-037 |
| REQ-ING-036 | state machines Publish; orchestration Publish | TST-ING-043 |

The authoritative test ids are in [test plan](test-plan.md); the column above is a pointer and the test plan wins on any mismatch.

## Open points (not decided here)

| # | Point | Status |
|---|---|---|
| OPEN-1 | Closed by D-99: owner's own account, risk accepted. Locked chapters are never unlocked by submitting a form | closed |
| OPEN-2 | epubcheck runs in the worker before publish (D-47, decided); the Java runtime and epubcheck install in the worker image still need approval in the P1 dependency batch | owner (tooling install) |
| OPEN-3 | Generated fallback cover (REQ-ING-027): text shaping and rasterisation need a crate or tool; method not chosen | owner (dependency batch) |
| OPEN-4 | Crates for HTTP client, HTML parser, sanitizer, ZIP, templating, Unicode normalization, XML: none approved yet (D-17 batch at P1 start); this design names roles, not crates | owner (dependency batch) |
| OPEN-5 | Contract open points C-2 (ingestion chooses the book UUID for `POST /internal/books/{id}/versions`; resolved yes by D-85) and C-3 (`POST /internal/books/match` kept, D-86) | open-points.md |
| OPEN-6 | O-3: work/edition grouping is not modelled; "new edition" is a human action only; the model has no work entity | open-points.md |
| OPEN-7 | O-4: scope guarding CSV export and book deletion (not an ingestion route today) | open-points.md |
| OPEN-8 | Numbers marked "provisional" (job-log retention, lease length, back-off base, worker slots) are tuned at the P0 baseline (O-7) | open-points.md |
