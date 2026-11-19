# Cargo workspace layout and dependency rules

Status: DRAFT

```
elibrary/                       (this repository; legacy kept read-only in archive/)
├── archive/                    legacy Django app and its files (read-only reference, D-22)
├── Cargo.toml                  workspace, lint set (T-9), pinned toolchain
├── rust-toolchain.toml
├── clippy.toml  rustfmt.toml  deny.toml     thresholds (3 params, ~20 lines), formatting, licenses/bans/advisories
├── CLAUDE.md  AGENTS.md  crates/AGENTS.md   seeded from planning/templates (see working agreement)
├── crates/
│   ├── platform-*/             shared infrastructure, no domain knowledge
│   │   ├── platform-config     typed config + startup validation
│   │   ├── platform-http       axum helpers, error mapping, request id, idempotency middleware
│   │   ├── platform-db         sqlx pool, migrations runner, outbox/inbox, queue claim
│   │   ├── platform-obs        tracing, metrics
│   │   ├── platform-time       Clock trait
│   │   └── platform-testkit    fixtures, fake clock, TLA trace replay
│   ├── contracts-*/            wire types — the ONLY cross-service dependency
│   │   ├── contracts-ids       newtype IDs
│   │   ├── contracts-http      shared HTTP wire types: error envelope and common codes, scopes, pagination (I-26)
│   │   ├── contracts-gateway / -identity / -catalog / -reader / -ingestion / -notify
│   │   └── contracts-events    event envelope + payloads
│   ├── domain-*/               pure logic (no I/O, no clock, no randomness)
│   │   ├── domain-text         Normalizer (bn/en), slug, collation keys
│   │   ├── domain-access       Scopes, Roles, Grants, decide() (used by identity only), reading-ticket type (verified by asking identity, D-37)
│   │   ├── domain-document     Block IR, SectionTree, CanonicalDocument, conservation checker
│   │   ├── domain-classify     labels, evidence, lexicons, conflict resolution
│   │   ├── domain-entities     name parsing, roles, alias matching, duplicate policy
│   │   ├── domain-builders     EPUB writer and audit, preview text (deterministic)
│   │   └── domain-anchor       Anchor type, re-anchoring against a reading copy
│   └── svc-*/                  one binary per service
│       ├── svc-gateway (routing, identity check, rate limits, CSRF; no database)
│       ├── svc-identity  svc-catalog  svc-reader
│       ├── svc-ingestion (+ acquisition adapters; binaries: api and worker, one image)
│       └── svc-notify
├── web/                        Angular + Angular Material app (TypeScript, ADR-0014), SSR on Node (D-39); separate package manager workspace
│   └── src/app/core/api/generated/   generated from the Rust contract schema (read-only)
├── xtask/                      codegen (Rust schema → TS client), schema diff, plan check, model trace export
├── models/                     TLA+/Alloy (mirrors planning/03-correctness/formal-models)
├── corpus/                     gold corpus (git-lfs or separate repo), query set
└── deploy/
    ├── compose/                compose.yaml (full stack, ten containers, ADR-0019/0025), compose.dev.yaml, compose.test.yaml (overrides)
    ├── docker/                 one Dockerfile per image (svc-gateway, svc-identity, svc-catalog, svc-reader, svc-ingestion, svc-notify, web, backup), multi-stage
    ├── caddy/Caddyfile         HTTPS and certificate renewal; forwards to web and gateway only
    ├── secrets/                README and file names only; secret values are never committed
    ├── postgres/               init scripts: one database + role per service
    └── scripts/                monthly backup, restore drill, release (image digests), rolling restart, `identity admin-reset` helper
```

## Dependency rules (enforced by Q6 via `cargo metadata` check in `xtask`)

| From | May depend on |
|---|---|
| `domain-*` | other `domain-*`, `contracts-ids`, `contracts-http` (Scope), `platform-time` (Instant value type; I-28), std/third-party pure crates |
| `contracts-*` | `contracts-ids`, `contracts-http`, serde/utoipa |
| `platform-*` | other `platform-*`, `contracts-*` (ids/events only), third-party (I-25) |
| `svc-X` (incl. `svc-gateway`) | `platform-*`, `domain-*`, `contracts-*` (any), **never** `svc-Y` |

Consequences: a service can be built, tested and understood from its own crate plus
shared pure libraries; swapping a peer's implementation requires only its contract.

`svc-gateway` is a service crate like the others ([ADR-0026](adr/0026-gateway-auth-check-via-identity.md)); it holds the route table (generated from each service's declared route scopes) and depends on `contracts-identity` for the authorize call. Caddy holds only HTTPS configuration. `platform-http` provides the scope-declaration macro/registry that makes a service refuse to start when a route lacks a declared scope.

## Per-service crate shape

```
svc-<name>/
  src/main.rs        startup: config → db → migrate check → contract handshake → serve
  src/http/          handlers (thin), one module per resource
  src/app/           use cases (orchestration, transactions)
  src/store/         sqlx queries (compile-time checked; absent in svc-gateway)
  src/events/        `events` outbox writer, `GET /internal/events` handler, cursor-based consumers
  migrations/        forward-only SQL
  tests/             integration tests with ephemeral Postgres
```

Handlers contain no business rules; use cases call `domain-*`; stores contain no
logic beyond persistence.
