# ADR-0020 — Five services, nine containers, no gateway

Status: ACCEPTED

Supersedes [ADR-0002](0002-independent-services.md) and [ADR-0008](0008-search-engine.md). Basis: owner decisions D-27 (five services, no gateway) and D-29 (small scale).

## Context
The earlier plan had seven domain services plus a gateway and an SSR web app. At the stated scale (under 5,000 books, under 50 users, one host) the extra boundaries (`access`, `content`, `library`, the gateway) added network hops, projections and failure modes without a matching benefit. Authorization was split from identity, and the file store from the metadata it describes.

## Decision
- Five services: **identity** (accounts, sessions, roles, grants, authorization decisions), **catalog** (books, metadata, publication workflow, asset files, shelves, search), **reader** (reading copies, reading state), **ingestion** (one pipeline; API container plus worker container) and **notify** (mail outbox and delivery).
- Merges: `access` into identity; `content` (assets and preview) into catalog; `library` (progress, annotations) into reader; the gateway is removed (its routing and authentication move to Caddy, [ADR-0024](0024-caddy-forward-auth-deny-by-default.md)).
- Nine containers: `caddy`, `web` (Angular static files), `identity`, `catalog`, `reader`, `ingestion-api`, `ingestion-worker`, `notify`, `postgres`.
- Each service has its own database and role in the single PostgreSQL container, and (where it stores files) its own file volume. No service reads another service's tables or volume; data moves over internal HTTP (streaming for files) and pull-based events ([ADR-0022](0022-pull-based-outbox-events.md)).
- Full-text search is PostgreSQL FTS with Bengali normalization inside catalog; there is no embedded search engine and no cache layer.

## Consequences
+ Fewer containers, fewer contracts, no projections of authorization data; one place decides who may do what.
+ Catalog owns a book's metadata and its files, so publication is one transaction plus one file write.
- Identity is a hard dependency of every authenticated request (Caddy forward-auth); it must stay small and fast.
- Coarser boundaries than before: catalog and ingestion are larger services; internal module boundaries inside each crate carry the separation.
- PostgreSQL FTS has no Bengali analyzer; normalization is ours (see [text and time](../cross-cutting/text-and-time.md)). The search spike must still confirm quality.
