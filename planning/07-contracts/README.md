# Contracts

Status: DRAFT

Wire types live in Rust `contracts-*` crates ([ADR-0004](../04-architecture/adr/0004-contract-source-of-truth.md)).
This folder holds the **human-reviewed catalogs** and, once code exists, the generated artifacts.

| Item | Where | Generated? |
|---|---|---|
| HTTP conventions | [http/README.md](http/README.md) | no |
| Event catalog | [events/README.md](events/README.md) | no (reviewed); payload schemas generated into `events/schemas/` |
| Error catalog | [error-catalog.md](error-catalog.md) | no |
| OpenAPI per service | `http/openapi/<service>.json` | yes (CI diff, Q3) |
| Event JSON Schemas | `events/schemas/*.json` | yes |

## Change policy

- Additive changes (new optional field, new endpoint, new event type) are compatible.
- Removing/renaming a field, tightening validation, or changing meaning is **breaking**: bump the contract major version, serve both for one release (`/v1`, `/v2` or event `version`), then remove.
- Consumers use `deny_unknown_fields = false` for events (forward-compatible) and `true` for requests (strict).
- Every contract change updates the corresponding doc in `05-services/<svc>/api-contract.md` in the same pull request.
