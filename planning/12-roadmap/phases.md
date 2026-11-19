# Phases

Status: DRAFT

Re-baselined 2026-11-19 for six Rust services (gateway, identity, catalog, reader, ingestion, notify) plus the Angular SSR `web`, `caddy` and `postgres`, all in Docker Compose (D-22, D-31, D-39). Fresh start: nothing is migrated from the old app and there is no cutover (D-32); the legacy deployment is already shut down and archived by the owner (D-50), so no phase depends on it. Kept from v1: the phase idea, gates, parallel tracks and scope control; changed: contents, order of services, estimates, the launch phase.

Estimates are for one person, part-time (about 20 h/week), **planning figures** (the author's judgement, not measurements), re-baselined at every gate. Each phase ends in something the owner can use or inspect.

| Phase | Deliverable | Contents | Est. weeks | Gate |
|---|---|---|---|---|
| **P0 Foundations** | Decisions, gold corpus, spikes | answer the open points (`_replan/open-points.md`); approve tool installs (Docker, Node, Java, Rust); permission request to the source sent (D-03); gold corpus of **120 books** (80 dev, 40 holdout), 200 judged queries, 100 duplicate pairs, 300 normalizer pairs, label guidelines, labeling page ([gold corpus](../06-data/gold-corpus/README.md)); labelling is **not blocked** by the source permission (private research only, GET-only, nothing committed or published, D-51); spikes S-01 (Bengali FTS), S-02 (Angular Material M3 and SSR audit), S-04 (EPUB build, epubcheck, Java tooling), S-05 (source adapter fixtures), S-07 (queue and outbox), S-08 (whole-book reader) | 7 | G0 |
| **P1 Platform kit** | Empty but real workspace and a stack of ten sample containers | dependency approval batch (Rust crates, D-17; system packages Docker Engine and Compose, Java runtime and epubcheck, D-47; Node; npm after S-02, D-20); Compose skeleton for all ten containers (`caddy`, `web`, `gateway`, `identity`, `catalog`, `reader`, `ingestion-api`, `ingestion-worker`, `notify`, `postgres`) plus the `migrate` and `backup` one-shots, each service a sample with startup checks and readiness; cargo workspace, lints (D-19), CI gates Q1 to Q7, Q10, Q11; `platform-*` crates (config, startup, errors, telemetry, clock, ids, outbox pull client, service token); `domain-text` (Bengali normalizer, collation, slug); contract crates and codegen (Rust schema to the TypeScript client and service fakes); `xtask`; testkit; S-06 (memory budget), S-09 (backup dry run) | 4 | G1 |
| **P2 Formal models** | Checked specifications | install and run TLC and Alloy (owner approval); write the nine planned models and three extensions ([planned models](../03-correctness/formal-models/planned-models.md)); fix the stale parts of `access.als`; run and fix the four existing models; counterexamples resolved in the model or the requirement; trace export; Q8 in CI | 4 | G2 |
| **P3 Identity and gateway** | Sign-in works end to end | identity (invites, sessions, TOTP, reset, roles and scopes D-45, grants, tickets, audit D-40, profile image D-44, host-command admin recovery D-38), gateway (routing, authorize call, CSRF, rate limits, security headers), web shell (sign-in card shell, settings, users and access), `notify` replaced by a contract-generated fake until P7 (OPEN question 1) | 6 | G3 |
| **P4 Catalog and public pages** | Public site with search; library for signed-in users | prototypes (home, search, book detail, library) signed off first; catalog (books, versions, metadata, review workflow, internal publish endpoint, files, shelf "My Books", saved filters D-43, downloads, PostgreSQL FTS with Bengali normalization, events); `web` SSR public pages with metadata only (D-34, D-39); library screens; seed of 5,000 synthetic books ([seed and fixtures](../06-data/seed-and-fixtures.md)); no legacy data | 7 | G4 |
| **P5 Reading** | The reader | reader service (reading copy build from the EPUB, sanitizer, whole-book package, ticket open and redeem through identity, read-once, progress, bookmarks, highlights and notes, server re-anchoring D-46, preferences D-48, JSON export); reader prototype signed off first; reader UI with light, dark and reading modes; event consumption from catalog and identity | 6 | G5 |
| **P6 Ingestion** | Books are created from the source | 6a pure pipeline crates (Block IR, structure, classification, entities, normalization, duplicate key, EPUB builder) against the gold corpus (starts in P1, in parallel); 6b source adapter (GET only, D-03), mirror sync, requests, Postgres job queue and worker, scrape cache, curate and validate, duplicate review, build with epubcheck in the worker (D-47), publish saga to catalog, console API and SSE, automation runs, source credential status, Import workspace UI; live acquisition stays blocked until the source's written permission exists (D-03, D-51) | 12 | G6 |
| **P7 Notify, audit viewer, completeness** | Everything else | notify (invites, resets, Kindle with delivery status), audit viewer, CSV export, account export and erasure, remaining admin and settings screens, polishing; every requirement has a passing verification | 4 | G7 |
| **P8 Hardening** | Production-ready | load against the capacity targets, fault injection FI-01 to FI-20, security review of every threat-model item, pen-test checklist, **monthly backup restore drill passed twice**, rolling restart and rollback rehearsal, final accessibility audit, documentation current | 4 | G8 |
| **P9 Launch** | Live | launch runbook (fresh host, certificates, first admin by host command, invites, first ingestion batch once permission exists, first production backup and restore), 4-week observation; no migration, no cutover (D-32) | 2 + 4 observation | G9 |

Total about 56 weeks of work plus 4 weeks of observation. Allowing the parallel tracks below to overlap (about 4 weeks), elapsed time is roughly 52 to 60 weeks at part-time pace. These are planning figures.

## Allowed parallel tracks

- **6a (pure ingestion crates)** may proceed from P1 because it depends only on `domain-text`, the document types and the gold corpus, not on any service.
- Gold-corpus labeling continues through P1 and P2 for books beyond the G0 minimum.
- Prototype and UX work for P4 and P5 starts during P3 and P4 respectively.
- Tool installs and approvals are batched: one request before P0 spikes (Docker, Node, Java) and the dependency batch at the start of P1.

## Not allowed

Adding a dependency without a recorded approval; coding while a requirement or rule is ambiguous (ask first); starting a service's implementation before its test plan, API contract and state machine exist; adding a requirement without invariant and verification; accepting a heuristic without a gold metric; contacting the live source site from tests or CI; committing the gold corpus.

## Scope control

Change requests go through a one-page plan change: requirement and invariant diff, affected services, effort, which later item is dropped or deferred. A phase that exceeds its estimate by 50% triggers a re-plan (risk R-10). Reduce scope before relaxing a gate.

## Open questions (not decided here)

1. Does invite delivery by real mail have to work before P7? If yes, the minimal mail path of `notify` moves into P3.
2. Is the monthly backup also taken before every release (proposal in risk R-17)?
