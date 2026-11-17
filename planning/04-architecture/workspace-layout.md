# Cargo workspace layout and dependency rules

Status: DRAFT

```
elibrary/                       (new repository or new top-level directory; legacy kept read-only)
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
│   │   ├── contracts-identity / -access / -catalog / -content / -library / -ingestion / -notify
│   │   └── contracts-events    event envelope + payloads
│   ├── domain-*/               pure logic (no I/O, no clock, no randomness)
│   │   ├── domain-text         Normalizer (bn/en), slug, collation keys
│   │   ├── domain-access       Facts, Grants, decide(), Capability
│   │   ├── domain-document     Block IR, SectionTree, CanonicalDocument, conservation checker
│   │   ├── domain-classify     labels, evidence, lexicons, conflict resolution
│   │   ├── domain-entities     name parsing, roles, alias matching, duplicate policy
│   │   ├── domain-builders     EPUB/HTML/preview/cover builders (deterministic)
│   │   └── domain-anchor       Anchor type, re-anchoring algorithm
│   └── svc-*/                  one binary per service
│       ├── svc-identity  svc-access  svc-catalog  svc-content  svc-library
│       ├── svc-ingestion (+ acquisition adapters)  svc-notify
│       └── svc-gateway
├── web/                        Angular + Angular Material app (TypeScript, ADR-0014); separate package manager workspace
│   └── src/app/core/api/generated/   generated from the Rust contract schema (read-only)
├── xtask/                      codegen (Rust schema → TS client), schema diff, plan check, model trace export
├── models/                     TLA+/Alloy (mirrors planning/03-correctness/formal-models)
├── corpus/                     gold corpus (git-lfs or separate repo), query set
└── deploy/                     compose/systemd, nginx, backup scripts
```

## Dependency rules (enforced by Q6 via `cargo metadata` check in `xtask`)

| From | May depend on |
|---|---|
| `domain-*` | other `domain-*`, `contracts-ids`, std/third-party pure crates |
| `contracts-*` | `contracts-ids`, serde/schemars |
| `platform-*` | `contracts-*` (ids/events only), third-party |
| `svc-X` | `platform-*`, `domain-*`, `contracts-*` (any), **never** `svc-Y` |

Consequences: a service can be built, tested and understood from its own crate plus
shared pure libraries; swapping a peer's implementation requires only its contract.

## Per-service crate shape

```
svc-<name>/
  src/main.rs        startup: config → db → migrate check → contract handshake → serve
  src/http/          handlers (thin), one module per resource
  src/app/           use cases (orchestration, transactions)
  src/store/         sqlx queries (compile-time checked)
  src/events/        outbox producers, inbox consumers
  migrations/        forward-only SQL
  tests/             integration tests with ephemeral Postgres
```

Handlers contain no business rules; use cases call `domain-*`; stores contain no
logic beyond persistence.
