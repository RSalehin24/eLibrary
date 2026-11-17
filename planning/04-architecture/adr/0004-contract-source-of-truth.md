# ADR-0004 — Rust contract crates are the source of truth

Status: REVIEW

## Context
"Contract-first" with a separate OpenAPI authoring step doubles the work and the Rust generators for server stubs are less mature than the reverse direction.

## Decision
Wire types live in `contracts-*` crates (serde + schemars/utoipa). OpenAPI 3.1 and JSON Schema documents are generated, committed under `planning/07-contracts` mirrors, and diffed in CI (Q3). The Angular app's TypeScript types and typed API client are generated from the committed schema (ADR-0014); hand-written wire types are forbidden. Breaking changes require a major bump of the contract crate and a dual-support release.

## Consequences
+ One definition; drift is impossible by construction (INV-PLT-002).
− Non-Rust consumers depend on generated artifacts; acceptable.
