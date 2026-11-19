# Contracts

Status: DRAFT (rewritten for 5 services, no gateway: identity, catalog, reader, ingestion, notify; D-27)

Wire types live in Rust `contracts-*` crates ([ADR-0004](../04-architecture/adr/0004-contract-source-of-truth.md)). This folder holds the human-reviewed catalogs and, once code exists, the generated artifacts.

| Item | Where | Generated? |
|---|---|---|
| HTTP conventions (ids, time, auth, scopes, tickets, pagination) | [http/README.md](http/README.md) | no |
| Event catalog and outbox pull API | [events/README.md](events/README.md) | no (reviewed); payload schemas generated into `events/schemas/` |
| Error model and codes | [error-catalog.md](error-catalog.md) | no |
| OpenAPI per service (`identity`, `catalog`, `reader`, `ingestion`, `notify`) | `http/openapi/<service>.json` | yes (CI diff, Q3) |
| Event JSON Schemas | `events/schemas/*.json` | yes |
| TypeScript types and typed client for Angular | `web` app, `core/api/generated/` | yes (see pipeline) |

## Generated-types pipeline (Rust to Angular)

1. Request, response, error and event types are defined once in the `contracts-*` crates with serde plus a schema derive.
2. `xtask codegen` writes one OpenAPI 3.1 document per service and the event JSON Schemas into this folder's mirrors; the files are committed.
3. The same command writes the Angular `core/api/generated/` directory (types and a typed client with one function per operation, covering the four public prefixes `/api/identity`, `/api/catalog`, `/api/reader`, `/api/ingestion`; `notify` has an admin surface only). The directory is read-only for humans.
4. CI regenerates everything and fails on any diff (Q3); a Rust-side change that breaks the Angular build therefore fails the pull request, and hand-written wire types are forbidden.
5. The generator for the TypeScript side is not chosen here: any new tool or package needs the owner's approval and a row in the [dependency policy](../04-architecture/dependency-policy.md) (open item).
6. Every operation in the schema carries its declared scope (`x-required-scope`); the client generator and the startup fail-closed check read the same declaration.

## Change policy

- Additive changes (new optional field, new endpoint, new event type) are compatible.
- Removing or renaming a field, tightening validation, or changing meaning is **breaking**: bump the contract major version, serve both for one release (`/v1`, `/v2` or event `v`), then remove.
- Consumers use `deny_unknown_fields = false` for events (forward-compatible) and `true` for requests (strict).
- At this scale (one host, deployed together) a breaking change may ship in one release when all consumers change in the same pull request; the rule above still applies to anything an external client could call.
- Every contract change updates `05-services/<svc>/api-contract.md` in the same pull request.
