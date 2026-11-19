# Contracts

Status: DRAFT (rewritten for six Rust services behind Caddy and the gateway: gateway, identity, catalog, reader, ingestion, notify; D-31)

Wire types live in Rust `contracts-*` crates ([ADR-0004](../04-architecture/adr/0004-contract-source-of-truth.md)). This folder holds the human-reviewed catalogs and, once code exists, the generated artifacts. Open points that affect a contract are marked **OPEN (O-n)**; they are listed in [open-points](../_replan/open-points.md) and are not decided here.

| Item | Where | Generated? |
|---|---|---|
| HTTP conventions (surfaces, ids, time, headers, scopes, tickets, pagination) | [http/README.md](http/README.md) | no |
| Gateway (routing, no business API) | [http/gateway.md](http/gateway.md) | no |
| Identity API (public, admin, internal) | [http/identity.md](http/identity.md) | no, then OpenAPI |
| Catalog API (public, shelf, management, internal) | [http/catalog.md](http/catalog.md) | no, then OpenAPI |
| Reader API (open, ticket, book package, personal data) | [http/reader.md](http/reader.md) | no, then OpenAPI |
| Ingestion API (console, requests, jobs, SSE) | [http/ingestion.md](http/ingestion.md) | no, then OpenAPI |
| Notify internal API | [http/notify.md](http/notify.md) | no, then OpenAPI |
| Event catalog and outbox pull API | [events/README.md](events/README.md) | no (reviewed); payload schemas generated into `events/schemas/` |
| Error model and codes | [error-catalog.md](error-catalog.md) | no |
| OpenAPI per service (`identity`, `catalog`, `reader`, `ingestion`, `notify`) | `http/openapi/<service>.json` | yes (CI diff, Q3) |
| Event JSON Schemas | `events/schemas/*.json` | yes |
| TypeScript types and typed client for Angular | `web` app, `core/api/generated/` | yes (see pipeline) |

Per-service pages list every route with its declared scope. They are the review copy of what the contract crates will define; when code exists the crates win and these pages are regenerated or diffed against them. Detail per service lives in `05-services/<service>/api-contract.md` ([identity](../05-services/identity/README.md), [catalog](../05-services/catalog/README.md), [reader](../05-services/reader/README.md), [ingestion](../05-services/ingestion/README.md), [notify](../05-services/notify/README.md)).

## Counts (this revision)

| Service | Public routes (`/api/<svc>/*`) | Internal routes (`/internal/*`) |
|---|---|---|
| gateway | 0 | 0 (health, ready, contract only) |
| identity | 37 | 8 (+ health, ready, contract) |
| catalog | 31 | 7 (+ health, ready, contract) |
| reader | 19 | 2 (+ health, ready, contract) |
| ingestion | 34 | 1 (+ health, ready, contract) |
| notify | 0 | 3 (+ health, ready, contract) |

Events: 8 types plus 1 proposed (`user.deleted`, OPEN O-1). Error codes: see [error-catalog](error-catalog.md).

## Generated-types pipeline (Rust to Angular)

1. Request, response, error and event types are defined once in the `contracts-*` crates with serde plus a schema derive.
2. `xtask codegen` writes one OpenAPI 3.1 document per service and the event JSON Schemas into this folder's mirrors; the files are committed.
3. The same command writes the Angular `core/api/generated/` directory (types and a typed client with one function per operation, covering the four public prefixes `/api/identity`, `/api/catalog`, `/api/reader`, `/api/ingestion`; gateway and notify have no public API). The directory is read-only for humans.
4. CI regenerates everything and fails on any diff (Q3); a Rust-side change that breaks the Angular build therefore fails the pull request, and hand-written wire types are forbidden.
5. The generator for the TypeScript side is not chosen here: any new tool or package needs the owner's approval and a row in the [dependency policy](../04-architecture/dependency-policy.md) (open item).
6. Every operation in the schema carries its declared scope (`x-required-scope`); the client generator and the startup fail-closed check read the same declaration.

## Change policy

- Additive changes (new optional field, new endpoint, new event type) are compatible.
- Removing or renaming a field, tightening validation, or changing meaning is **breaking**: bump the contract major version, serve both for one release (`/v1`, `/v2` or event `v`), then remove.
- Consumers use `deny_unknown_fields = false` for events (forward-compatible) and `true` for requests (strict).
- At this scale (one host, deployed together) a breaking change may ship in one release when all consumers change in the same pull request; the rule above still applies to anything an external client could call.
- Every contract change updates `05-services/<svc>/api-contract.md` in the same pull request.
