# Phases

Status: DRAFT

Estimates are for one person, part-time (~20 h/week), **planning figures re-baselined at every gate** — not commitments. Each phase ends in something the owner can use or inspect.

| Phase | Deliverable | Contents | Est. weeks | Gate |
|---|---|---|---|---|
| **P0 Foundations** | Decisions, gold corpus, spikes | answer open decisions; build labeling tool; label 200 books; judged queries (≥ 300); duplicate pairs (≥ 150); spikes S-01…S-07; capacity inventory of the legacy data | 6 | G0 |
| **P1 Platform kit** | Empty but real workspace | Docker Compose skeleton (compose.yaml/dev/test, Dockerfiles, Caddy, Postgres init, health-gated startup of a sample service), cargo workspace, lints, CI, contracts codegen, `platform-*`, `domain-text` (normalizer, keys, collation), xtask, testkit, sample service with startup checks | 3 | G1 |
| **P2 Models** | Checked specifications | run and fix existing models; write AccountLifecycle, BookLifecycle, Publication, Progress; model-trace export; CI Q8 | 3 | G2 |
| **P3 Identity & access** | Sign-in works end to end | identity, access (`decide`, capabilities), gateway, minimal admin screens for accounts/grants, demo | 5 | G3 |
| **P4 Public discovery** | Public site with search and preview | prototypes → sign-off; catalog (read side + admin edit), search, content preview/cover, web public pages, seed from gold corpus + partial migration | 6 | G4 |
| **P5 Reading** | Reader | content protected delivery, library (progress, annotations, re-anchor), reader UI, notes page, shelf | 6 | G5 |
| **P6 Ingestion** | Create books from the source | 6a pure pipeline crates (Block IR, structure, classification, entities, builders) vs gold; 6b acquisition adapter, orchestration, publish saga, Review/Jobs/Sources UI, reprocess diff | 12 (6a starts in P1, in parallel) | G6 |
| **P7 Completeness** | Everything else | notify (mail, Kindle), exports, audit viewer, inventory (if kept), remaining admin screens, polishing | 3 | G7 |
| **P8 Hardening & migration** | Production-ready | load, fault injection, security review, a11y audit, restore drill, migration tool + rehearsals | 5 | G8 |
| **P9 Cutover** | Live | cutover runbook, monitoring period, decommission | 2 + 4 observation | G9 |

Total ≈ 45–50 weeks elapsed at part-time pace.

## Allowed parallel tracks

- **6a (pure ingestion crates)** may proceed from P1 because it depends only on `domain-text`, `domain-document` and the gold corpus, not on any service.
- Gold-corpus labeling continues through P1–P2 for the remaining books after G0's minimum.
- Prototype/UX work for P4 starts in P3.

## Not allowed

Adding a dependency without a recorded approval; coding while a requirement or rule is ambiguous (ask first); starting a service's implementation before its `TST-*` plan, API contract and state machine exist; adding a requirement without invariant and verification; accepting a heuristic without a gold metric.

## Scope control

Change requests go through a one-page "plan change": requirement/invariant diff, affected services, effort, which later item is dropped or deferred. Phases that exceed their estimate by 50% trigger a re-plan (risk R-10).
