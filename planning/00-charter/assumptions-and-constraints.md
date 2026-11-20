# Assumptions and constraints

Status: DRAFT

Basis: [new architecture](../_replan/new-architecture.md) sections 1, 9, 10; decisions D-03, D-11, D-22, D-24, D-29, D-31, D-32.

## Constraints

- **C-1** Backend and shared contract code are Rust (stable toolchain pinned). Web is TypeScript with Angular and Angular Material (M3); types are generated from the Rust contracts (D-02, D-11).
- **C-2** Six Rust services (gateway, identity, catalog, reader, ingestion, notify), each in its own container; ingestion has an API and a worker container from one image (D-31). Other containers: caddy, web, postgres.
- **C-3** Development and deployment are Docker Compose; one PostgreSQL container with one database and role per service (D-22, D-24). No Redis, no broker, no search engine, no cache layer (D-29).
- **C-4** Caddy handles HTTPS and certificate renewal only; routing, session checks, rate limits and CSRF are the gateway's job (D-31).
- **C-5** One host. Scale target under 5,000 books and under 50 users (D-29). One developer and one operator: the operational surface stays small.
- **C-6** Fresh start: no data is migrated from the legacy app; users are re-invited and books re-ingested (D-32). The legacy deployment is shut down and archived (D-50); nothing in the plan depends on it.
- **C-7** Acquisition from the source site is GET-only; no form is ever submitted (D-03). Pre-permission fetches for gold labelling are private research only: GET-only, never committed or published (D-51).
- **C-8** Bengali is the primary content language, English secondary; all text handling is Unicode-correct (vowel signs and conjuncts preserved). Interface languages Bengali and English (D-08).
- **C-9** Anonymous visitors may see public browse/search metadata, covers and summaries only; preview text and reading require an account (D-34, D-12). Account creation is by invitation.
- **C-10** No new dependency (crate, npm package, tool, system package) without owner approval, registered in the dependency policy (D-17, D-20).
- **C-11** No service reads another service's tables or volume; data moves by internal HTTP and pull-based events (new architecture sections 2, 3).
- **C-12** Never commit secrets, personal data, third-party book content or the gold corpus.

## Assumptions

| ID | Assumption | Verified by |
|---|---|---|
| A-1 | The source site keeps its LearnDash structure and listing pages | Fixture tests and a canary job; drift detector |
| A-2 | The owner's own source account entitles ingestion for a private library; the source has not consented to republication to invited readers | Decision D-99 (risk accepted by the owner; replaces the permission blocker of D-03) |
| A-3 | PostgreSQL `FOR UPDATE SKIP LOCKED` suffices for a handful of concurrent jobs | Load test of the job queue |
| A-4 | PostgreSQL FTS with Bengali normalization finds books well enough at under 5,000 books | Query set with expected hits |
| A-5 | Whole-book delivery to the browser is fast enough for typical EPUBs | Reader spike on the largest corpus book |
| A-6 | The source session cookie can be refreshed by the operator out of band and mounted as a secret file | Operator drill in the launch runbook |
| A-7 | Under 5,000 books and under 50 users fits one host's CPU, memory and disk | Measured after the first full ingest |
| A-8 | A Bengali font with an open licence (Noto Serif Bengali, SIL OFL) may be embedded in EPUBs | Licence check (assistant default D-30) |
| A-9 | An SMTP provider is available for invites, resets and Kindle delivery | Launch checklist |
