# Candidate service splits and scoring (steps 3–4)

Status: DRAFT

Every candidate includes the reader as its own service (F5) and runs each service in its own container (F4). `web`, `edge` (Caddy) and `postgres` exist in all. Scores are my judgment from the evidence (1 = poor, 5 = good), not measurements; weights from [REPLAN](../REPLAN.md) §3.

## Candidates

| | Services (besides web/edge/postgres) | Count |
|---|---|---|
| **C1 Minimal** | gateway · accounts (authN+authZ+mail) · library (catalog + search + artifacts) · reader · ingestion | 5 |
| **C2 Domain split** | gateway · **accounts** (authN+authZ) · **catalog** (metadata + search) · **content** (artifacts) · **reader** (EPUB reading + personal state) · **ingestion** (incl. former processing + builders) · **notify** (mail + Kindle) | 7 |
| **C3 Previous plan** | gateway · identity · access · catalog · content · library · ingestion · notify | 8 |
| **C4 Fine-grained** | C2 + search · audit · sources (crawler) split from pipeline · shelf split from reader | 11 |

## Scores

| Criterion (weight) | C1 | C2 | C3 | C4 |
|---|---|---|---|---|
| Data ownership clarity (25) | 3 | 5 | 4 | 4 |
| Failure isolation (20) | 3 | 4 | 4 | 5 |
| Independent change (15) | 3 | 4 | 4 | 4 |
| One-developer operability: containers, memory, build time (20) | 5 | 4 | 3 | 1 |
| Journey chattiness: browse → read → annotate; ingest → publish (10) | 5 | 4 | 3 | 2 |
| Scaling difference (10) | 2 | 4 | 4 | 5 |
| **Weighted** | **3.5** | **4.25** | **3.7** | **3.5** |

## Why the boundaries

- **accounts = identity + access merged.** Same users, same admin screen ("Users & Access"), same change cadence; legacy kept them in two apps with cross-FKs and a `common` module reaching into both. Capability signing and `decide` stay a separate pure library inside the service so formal checking is not lost.
- **catalog vs content.** Metadata is small, public and searchable; files are large, immutable and protected (legacy mixed them in `catalog.GeneratedAsset` and `access` downloads).
- **reader separate (F5).** Protected, bursty, and the legacy hot spot (whole-EPUB-by-token, duplicate APIs). It also owns personal reading state (progress, bookmarks, highlights, notes, shelf, saved filters) because those writes happen while reading; one owner removes the token/slug duplication.
- **ingestion absorbs `processing`.** The legacy duplicate of records, requests and sync is the clearest design failure in the evidence; one owner for jobs, review and the live queue read model. Builders stay a pure library.
- **notify kept, but first to merge** if toil is too high (it is the only external side-effect service besides ingestion).
- **Rejected:** C4 splits (search, audit, sources/pipeline, shelf) cost a container each on one host for little isolation gain at ~2k books; revisit search if it needs independent scaling.
- **Hard-fail check:** no candidate needs a distributed transaction on a core journey; publish is a saga with idempotent steps (ingestion → content → catalog).

## Rough budget (estimate, not measured)

C2 idle ≈ 1–1.5 GB: 6 Rust services at tens of MB each, `web` (Node SSR) ~150–250 MB, Postgres ~300–500 MB, Caddy ~30 MB; heavy ingestion jobs add transient memory. Legacy production host was 3.72 GB. The real figure is a P1 deliverable.
