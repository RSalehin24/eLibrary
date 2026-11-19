# Dependency policy and register

Status: DRAFT

Rule from the owner's `AGENTS.md`: **no new dependencies without approval; prefer the standard library.** This applies to crates, system packages, tools and services. Nothing below is approved yet; every row is PROPOSED. The foundational Rust batch is approved at the start of P1 (D-17) and the npm set after spike S-02 (D-20).

The system has six Rust services (gateway, identity, catalog, reader, ingestion, notify; [ADR-0025](adr/0025-six-services-with-gateway.md)), the `web` SSR app and `caddy`/`postgres` images. The "Used by" column of the register shows which service needs each candidate.

## Process

1. Need arises → check the standard library and existing approved crates first.
2. Write a register entry (row below): purpose, why the standard library is insufficient, alternatives considered, maintenance health (last release, downloads, maintainers), license, `unsafe` usage, transitive weight, security history, features to enable.
3. Owner approves (status `APPROVED`) or declines; recorded in [DECISIONS](../DECISIONS.md).
4. Add via the package manager (`cargo add`, lockfile committed); `cargo deny` licenses/bans/advisories updated; no hand-edited lockfile.
5. Removal when unused is a normal change; the register is kept current by the plan check.

## Principles

Few, large, well-maintained crates over many small ones; avoid crates that duplicate each other; pure-Rust preferred; no crates with network access at build time beyond the registry; vendored/audited if critical (crypto, parsing of hostile input).

## Containers and deployment tooling (PROPOSED, need owner approval at P1 start)

| Area | Candidate | Why | Notes |
|---|---|---|---|
| Container runtime | Docker Engine + Compose v2 plugin | required by D-22 | system packages; owner approves installation |
| Edge proxy image | Caddy (official image, pinned by digest) | D-23, D-31 | HTTPS and certificate auto-renewal only |
| Database image | PostgreSQL 16 (official image, pinned by digest) | D-24 | one container, database + role per service |
| Rust build/runtime base | official `rust` builder + minimal runtime (distroless or `debian-slim`; choice at P1, pinned by digest) | multi-stage service images | musl vs glibc decided at P1 |
| Web build/runtime base | official `node` LTS image (pinned) | Angular build and the SSR server runtime (D-39) | the `web` container runs Node |
| Image registry | private registry or image archive | release transport | decide at P1 |
| Dev mail sink | a SMTP sink image (candidate: Mailpit) | local mail flows for notify | dev/CI only; needs approval |
| Backup tooling | `pg_dump` from the pinned PostgreSQL image plus `tar` in a `backup` job image | monthly backup (D-33) | no new tool beyond the database image |

## Register (all PROPOSED — none installed, none approved)

| Area | Candidate | Used by | Std insufficient because | Needed | Notes |
|---|---|---|---|---|---|
| Async runtime | `tokio` | all six | std has no async executor/IO | P1 | single runtime for all services |
| HTTP server | `axum` (on `hyper`/`tower`) | all six | no HTTP in std | P1 | alternative: `actix-web`; choose one |
| HTTP client / proxying | `reqwest` or `hyper` client | gateway (proxy, authorize call), all services (internal calls), ingestion (GET-only acquisition) | no HTTP/TLS in std | P1/P6 | thin GET-only wrapper for acquisition |
| Serialization | `serde` (APPROVED D-62, in use), `serde_json` (APPROVED D-62, dev use) | all six | no derive serialization | P1 | contracts |
| JSON Schema/OpenAPI | `schemars` / `utoipa` | contracts | generating schemas | P1 | one of them (ADR-0004) |
| Database | `sqlx` (Postgres) | identity, catalog, reader, ingestion, notify (not gateway) | no DB client | P1 | compile-time checked queries |
| Errors | `thiserror` | all six | boilerplate for `Error` impls | P1 | optional; hand-written is acceptable |
| Logging/tracing | `tracing`, `tracing-subscriber` | all six | std has only print | P1 | |
| Metrics | `metrics` + Prometheus exporter | all six | none in std | P1 | |
| IDs | `uuid` (APPROVED D-62, in use) | all except gateway | UUID v5/v7 generation | P1 | enable only needed features |
| Time | `time` (APPROVED D-62, in use; jiff not chosen) | all six | std lacks calendar/zone | P1 | choose one; prefer `time` unless jiff features are needed |
| Crypto | `argon2`, `sha2`, `hmac`, `rand`/`getrandom`, `subtle` | identity (hashing, sessions, TOTP), gateway (CSRF token compare) | no crypto in std | P3 | audited RustCrypto family; signature crates (`ed25519-dalek`, PASETO) are no longer needed because tickets are verified by identity (D-37) |
| TOTP | hand-rolled on `hmac`+`sha1` (RFC 6238 is small) or `totp-rs` | identity | | P3 | prefer hand-rolled + tests |
| Cookies | `cookie` (or hand-written header handling) | identity, gateway | no cookie parsing in std | P3 | smallest option preferred |
| SMTP | `lettre` (SMTP transport) | notify | no SMTP in std | P1 | alternative: minimal hand-written SMTP client (not recommended) |
| Image validation | an image decoding crate (`image` or smaller) | identity (profile images, D-44) | no image decoding in std | P3 | validated types and size limit; pick the smallest that checks PNG/JPEG/WebP |
| Unicode | `unicode-normalization` (APPROVED D-59, in use), `unicode-segmentation` | catalog, ingestion, reader | std lacks normalization/graphemes | P1 | |
| Collation | `icu_collator` (+ data; APPROVED D-61, in use, with `icu_locale_core`) | catalog | std has no locale collation | P1 | verify bn data availability |
| HTML parsing | `html5ever` (or `scraper`) | ingestion, reader | no HTML parser in std | P1 | hostile input; fuzzed |
| HTML sanitizing | `ammonia` | ingestion, reader | | P1 | allow-list sanitizer |
| XML parsing | `quick-xml` (OPF, NCX, nav parsing and well-formedness gate) | ingestion, reader | no XML parser in std | P1 | alternative: `roxmltree` |
| ZIP/EPUB | `zip` | ingestion (writer), reader (reader of EPUB) | no archive in std | P1 | reproducible writer |
| Image/SVG/text shaping | `resvg`, `tiny-skia`, `rustybuzz`, an image codec crate | ingestion (covers) | covers need shaping | P6 (spike S-03) | pending spike |
| Full-text search | none: PostgreSQL FTS (and `pg_trgm` extension of the pinned image, if the search spike needs it) | catalog | | P4 (spike S-01) | no embedded engine; `tantivy` withdrawn from the register |
| Frontend framework | `typescript`, `@angular/core`, `@angular/common`, `@angular/router`, `@angular/forms`, `@angular/platform-browser`, `@angular/platform-server`, `@angular/ssr` (+ Angular CLI, build tooling) | web | UI framework and SSR (D-02, D-39) | P4 (verify versions in S-02) | one Angular major, pinned; the SSR server's HTTP layer comes with `@angular/ssr` (confirm in S-02) |
| Frontend design | `@angular/material`, `@angular/cdk` | web | Material Design 3 components and accessibility primitives; D-16 | P4 | the only UI component library; no second library without approval |
| Frontend reactive | `rxjs` | web | peer requirement of Angular HTTP/router | P4 | prefer signals in app code |
| Frontend lint/format | `eslint`, `typescript-eslint`, Angular ESLint plugin, `prettier` or Angular formatting | web | | P4 | dev-dependencies |
| Frontend tests | `vitest` + `jsdom` (Angular CLI default; verified on angular.dev/guide/testing), `@playwright/test`, `axe-core` / Playwright axe integration | web | | P4 | dev-dependencies |
| Frontend codegen | an OpenAPI→TypeScript generator (candidate chosen in S-02) or a small in-repo generator driven by `xtask` | web | typed client from Rust contract schema | P4 | prefer the smallest option |
| Frontend fonts | Noto Serif/Sans Bengali (self-hosted WOFF2; Noto Serif Bengali regular and bold also embedded in EPUBs) | web, ingestion | typography guide | P4 | font files, SIL OFL licence |
| Property testing | `proptest` (APPROVED D-59, in use) | all | std has no generators | P1 | dev-dependency |
| Snapshot tests | `insta` | all | | P1 | dev-dependency |
| Compile-fail tests | `trybuild` | all | | P1 | dev-dependency |
| Benchmarks | `criterion` | all | | when evidence needed | dev-dependency |
| Test DB | `testcontainers` or local Postgres scripts | all with a database | | P1 | prefer scripts if allowed (Compose already provides Postgres) |
| Tools (not linked into binaries) | `cargo-deny`, `cargo-audit`, `cargo-mutants`, `kani`, TLC (Java), Alloy (Java), Playwright, k6 | | | P1–P8 | system packages need approval and a stated reason before install |
| Backup encryption and offsite copy | `age` or `restic` (choose one) | `backup` job (monthly encrypted copy off the host, D-33) | encrypts backups before they leave the host and copies them offsite; `pg_dump` and `tar` alone do neither | P1 | **PROPOSED, pending owner approval** (new tool; state version and license) |
| Runtime tool in the ingestion worker image | Java runtime (JRE) and `epubcheck` | `ingestion-worker` | Build gate runs epubcheck before publish (D-47, REQ-ING-026) | P1 | **PROPOSED, needs owner approval** (new system package; state version, image size and memory) in the dependency batch |

Counts and versions are recorded when approved, not guessed here.

## Verification of the register (2026-11-17, docs.rs pages; crates.io and lib.rs were unreadable, downloads unknown)

All 46 crates/tools listed at that date exist (the register has since been revised for the six-service design; `lettre`, `quick-xml`, `cookie` and an image crate are not yet verified) and none is yanked or deprecated at its latest version. Items needing attention before approval:

| Crate | Finding | Action |
|---|---|---|
| `rustybuzz` 0.20.1 | last release 2024-11-12 (~2 years old) | S-03 must check shaping quality and for a maintained successor before approving |
| `subtle` 2.6.1 | last release 2024-06-24 | acceptable for a small stable crate; review at approval |
| `proptest` 1.12.0 | page says it "mainly sees passive maintenance" | acceptable for dev-dependency; note |
| `tracing-subscriber` 0.3.23 | badge "maintenance-experimental" | review at approval |
| `jiff` 1.0.0 | first 1.0 release 2026-11-15 | prefer `time` 0.3.55 unless jiff features are needed; decide at approval |
| `pasetors` 0.8.1 (no longer needed, D-37) | "has not undergone any third-party security audit" (supports v4.public and v4.local) | alternative `rusty_paseto` 0.10.1 (v4 public/local via feature flags); compare at approval |
| `uuid` 1.29.3 | features `v7`, `v5` confirmed | enable only needed features |
| `icu_collator` 2.4.0 | CLDR has `bn.xml`; baked locale list not shown | S-01 builds a `bn` collator and checks it does not fall back to root |
| `utoipa` 6.0.0, `sqlx` 0.9.0, `axum` 0.8.9, `reqwest` 0.13.5, `tantivy` 0.27.0 (withdrawn), `ed25519-dalek` 3.0.0 (no longer needed) | current latest per docs.rs | pin exact versions on approval |
| `totp-rs` 6.0.0 | exists | hand-rolled TOTP on `hmac`+`sha2` remains the preferred minimal option |

Full evidence: [verification log](../03-correctness/verification-log.md).

## Decline-by-default examples

ORMs; macros-heavy frameworks; crates that wrap std; utility crates for one function; anything pulling large transitive trees; anything unmaintained for > 12 months; AI/ML crates (no local inference in v1).
