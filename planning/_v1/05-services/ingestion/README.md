# ingestion

Status: DRAFT (rewritten for the 5-service architecture, D-27/D-29; basis `_replan/new-architecture.md` section 6)

The single pipeline from the source site (or an uploaded EPUB) to a candidate book in the catalog: mirror sync, request, scrape, curate and validate, duplicate review, EPUB build, publish to catalog. Operator-only.

| | |
|---|---|
| Owns | source mirror, intake requests, jobs and leases, scrape cache (files), curated documents (files + rows), review items, duplicate reviews, build artifacts (candidates), source credential and its status, automation settings, sync runs, console event outbox |
| Does not own | published books and files (catalog), accounts and scopes (identity), mail (notify), the reader copy (reader) |
| Requirements | REQ-ING-001…016, REQ-CAT-006 (duplicate policy, applied here with catalog data), REQ-CON-002/007/008/009 (EPUB build), REQ-DSC-002 (normalization shared with catalog) |
| Containers | `ingestion-api` (HTTP, SSE) and `ingestion-worker` (same image, command `worker`): scheduler loop, job claimer, executors |
| Emits | internal outbox `events` for the console: `request.changed`, `job.progress`, `sync.changed`, `credential.changed`, `automation.changed`, `build.finished` |
| Consumes | catalog `book.published`, `book.unpublished`, `book.version_changed` (pull with cursor) |
| Calls | catalog internal API (shell, duplicate classify, agent resolve, intake), the source site (GET only), identity `/internal/check` only through caddy forward-auth headers |
| Called by | web operator console via caddy (`/api/ingestion/*`, scope `operate`) |

## Pipeline

```
 mirror sync ──► request ──► scrape ──► curate / validate ──► duplicate check ──► build EPUB ──► publish (catalog intake, in_review)
 (GET listing)   (one model)  (GET only)  (pure, versioned)     (review state)      (audit gate)      only after build success
                                                                                                         │
                                         catalog approval (manage_catalog) ──► book.published ──► request: published
```

- Every arrow is a row in `jobs`, claimed with `FOR UPDATE SKIP LOCKED` (no inline work in any HTTP handler, no Redis, no Celery).
- Stages curate, validate, duplicate classification and build are pure functions of `(curated document, ruleset version, builder version)`; their results are cached by those keys.
- Nothing is dropped silently (INV-ING-002): dropped blocks carry a reason code; unresolved facts become review items.
- A failed or unfinished build never leaves anything visible: the catalog sees nothing until the publish step succeeds, and even then the version is `in_review` until a human approves.

## Design rules (from the brief and the analysis)

| Rule | Where |
|---|---|
| One request model (replaces `BookSubmission` + `BookCreationRequest`, `SourceCatalogEntry` + `BookRecord`, `ProcessingJob` + engine state) | [domain model](domain-model.md) |
| Source mirror columns and workflow state are different tables; re-sync never touches workflow | `mirror_entries` vs `requests` |
| Postgres jobs: leases with heartbeat, visibility timeout, attempt counter, fencing epoch, typed errors, idempotent steps, cancel flag per page | [state machines](state-machines.md) |
| Acquisition is GET-only; no source form is ever submitted (D-03) | `SourceClient` exposes only `get` (INV-ING-012) |
| One explicit source credential, rotatable, visible status | `source_credentials`, credential state machine |
| Correct Bengali normalization and exact matching rules; duplicate review is a state | domain model sections "Bengali normalization", "Matching rules" |
| EPUB build: escaping on, sanitized, images and fonts packaged, complete OPF, audit gate | domain model "Build" |
| Console live updates by SSE from outbox + LISTEN/NOTIFY with versioned snapshot | [API](api-contract.md) |
| Automation fixes the legacy idle-run defect | [state machines](state-machines.md) "Automation sequence" |

## Sub-designs (kept, to be reconciled)

The folders below hold the detailed designs of the pure stages and remain valid where they do not mention the removed `content` service, saga steps `content.put_document`, or `Snapshot` blobs in a content-addressed store; those parts are superseded by this folder: [acquisition](acquisition/README.md) · [block-ir](block-ir/README.md) · [structure](structure/README.md) · [classification](classification/README.md) · [entities](entities/README.md) · [builder](builder/README.md) · [orchestration](orchestration/README.md) · [rulesets](rulesets/README.md).

See [domain model](domain-model.md) · [API](api-contract.md) · [state machines](state-machines.md) · [tests](test-plan.md) · [gold corpus](../../06-data/gold-corpus/README.md).

## Open points (not decided here)

1. Source credential storage: encrypted column with a key from a secret file (needs a crypto crate, dependency approval) or plain column restricted by the database role.
2. Which Bengali font(s) to embed in EPUBs and the cover (OFL asset, repository addition) and subsetting.
3. Honest User-Agent versus the source's Cloudflare behavior (legacy D6); fallback if the source blocks an identified client.
4. Retention of raw scraped pages (third-party copyright) and curated documents of cancelled requests.
5. Default values: error budget, politeness delay and concurrency, requests per automation run, similarity threshold for fuzzy suggestions.
6. Whether reader-role users may ever file a request (designed operator-only).
7. Whether catalog approval is done by `operate` users or only `manage_catalog` holders (designed: `manage_catalog`).
