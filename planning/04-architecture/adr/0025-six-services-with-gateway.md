# ADR-0025 — Six services including a gateway, ten containers

Status: ACCEPTED

Supersedes [ADR-0020](0020-five-services-no-gateway.md) (and through it [ADR-0002](0002-independent-services.md) and [ADR-0008](0008-search-engine.md)). Basis: owner decisions D-31 (six services), D-28, D-29, D-39.

## Context
ADR-0020 chose five services and no gateway, moving authentication into Caddy. The owner (D-31) kept the gateway and notify as separate services and restricted Caddy to HTTPS and certificate renewal. Scale is unchanged (D-29): under 5,000 books, under 50 users, one host.

## Decision
- Six Rust services: **gateway** (routing, session check against identity, rate limits, CSRF; owns no data), **identity** (accounts, sessions, TOTP, invites, roles, grants, profile images, audit log, authorization decisions), **catalog** (books, versions, metadata, publication workflow, files, shelves, saved filters, PostgreSQL FTS), **reader** (reading copies, reading tickets, reading state), **ingestion** (one pipeline; API container plus worker container) and **notify** (mail outbox and delivery).
- Ten containers: `caddy`, `web` (Angular SSR on Node), `gateway`, `identity`, `catalog`, `reader`, `ingestion-api`, `ingestion-worker`, `notify`, `postgres`.
- Kept from ADR-0020: `access` merged into identity, `content` into catalog and reader, `library` into reader and catalog; full-text search is PostgreSQL FTS with Bengali normalization inside catalog; no embedded engine, no cache layer, no broker.
- Each service has its own database and role in the single PostgreSQL container (the gateway has none) and, where it stores files, its own volume. No service reads another's tables or volume; data moves over internal HTTP and pull-based events ([ADR-0022](0022-pull-based-outbox-events.md)).
- Consolidation escape hatch: `notify` may be merged into identity or catalog if operations toil exceeds the threshold in the risk register; this would need a new decision because D-31 keeps it separate.

## Consequences
+ One place (gateway) holds routing, rate limits and CSRF for every `/api/*` route; services stay free of edge concerns.
+ Caddy is configuration only; no custom proxy logic there.
- One more container and one more hop per request than ADR-0020; the gateway and identity are hard dependencies of every authenticated request, so both must stay small and fast.
- Coarser boundaries inside catalog and ingestion; module boundaries inside each crate carry the separation.
