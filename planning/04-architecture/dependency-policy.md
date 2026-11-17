# Dependency policy and register

Status: DRAFT

Rule from the owner's `AGENTS.md`: **no new dependencies without approval; prefer the standard library.** This applies to crates, system packages, tools and services. Nothing below is approved yet.

## Process

1. Need arises → check the standard library and existing approved crates first.
2. Write a register entry (row below): purpose, why the standard library is insufficient, alternatives considered, maintenance health (last release, downloads, maintainers), license, `unsafe` usage, transitive weight, security history, features to enable.
3. Owner approves (status `APPROVED`) or declines; recorded in [DECISIONS](../DECISIONS.md).
4. Add via the package manager (`cargo add`, lockfile committed); `cargo deny` licenses/bans/advisories updated; no hand-edited lockfile.
5. Removal when unused is a normal change; the register is kept current by the plan check.

## Principles

Few, large, well-maintained crates over many small ones; avoid crates that duplicate each other; pure-Rust preferred; no crates with network access at build time beyond the registry; vendored/audited if critical (crypto, parsing of hostile input).

## Register (all PROPOSED — none installed, none approved)

| Area | Candidate | Std insufficient because | Needed | Notes |
|---|---|---|---|---|
| Async runtime | `tokio` | std has no async executor/IO | P1 | single runtime for all services |
| HTTP server | `axum` (on `hyper`/`tower`) | no HTTP in std | P1 | alternative: `actix-web`; choose one |
| HTTP client | `reqwest` or `hyper` client | no HTTP/TLS in std | P1/P6 | acquisition uses a thin GET-only wrapper |
| Serialization | `serde`, `serde_json` | no derive serialization | P1 | contracts |
| JSON Schema/OpenAPI | `schemars` / `utoipa` | generating schemas | P1 | one of them (ADR-0004) |
| Database | `sqlx` (Postgres) | no DB client | P1 | compile-time checked queries |
| Errors | `thiserror` | boilerplate for `Error` impls | P1 | optional; hand-written is acceptable |
| Logging/tracing | `tracing`, `tracing-subscriber` | std has only `log`-less printing | P1 | |
| Metrics | `metrics` + Prometheus exporter | none in std | P1 | |
| IDs | `uuid` | UUID v5/v7 generation | P1 | |
| Time | `time` or `jiff` | std lacks calendar/zone | P1 | choose one |
| Crypto | `argon2`, `sha2`, `hmac`, `ed25519-dalek` (or a PASETO crate), `rand`/`getrandom`, `subtle` | no crypto in std | P3 | audited RustCrypto family |
| TOTP | `totp-rs` or hand-rolled on `hmac`+`sha1` (RFC 6238 is small) | | P3 | prefer hand-rolled + tests if approved |
| Unicode | `unicode-normalization`, `unicode-segmentation` | std lacks normalization/graphemes | P1 | |
| Collation | `icu_collator` (+ data) | std has no locale collation | P1 | verify bn data availability |
| HTML parsing | `html5ever` (or `scraper`) | no HTML parser in std | P1(6a) | hostile input; fuzzed |
| HTML sanitizing | `ammonia` | | P1(6a) | |
| ZIP/EPUB | `zip` | no archive in std | P1(6a) | reproducible writer |
| Image/SVG/text shaping | `resvg`, `tiny-skia`, `rustybuzz`, an image codec crate | covers need shaping | P6 (spike S-03) | pending spike |
| Search engine | `tantivy` | no FTS in std | P4 (spike S-01) | pending spike; fallback Postgres |
| Frontend | `leptos` (or other) | | P4 (spike S-02, D-02) | pending decision |
| Property testing | `proptest` | std has no generators | P1 | dev-dependency |
| Snapshot tests | `insta` | | P1 | dev-dependency |
| Compile-fail tests | `trybuild` | | P1 | dev-dependency |
| Benchmarks | `criterion` | | when evidence needed | dev-dependency |
| Test DB | `testcontainers` or local Postgres scripts | | P1 | prefer scripts if allowed |
| Tools (not linked into binaries) | `cargo-deny`, `cargo-audit`, `cargo-mutants`, `kani`, TLC (Java), Alloy (Java), `epubcheck` (Java), Playwright, k6 | | P1–P8 | system packages need approval and a stated reason before install |

Counts and versions are recorded when approved, not guessed here.

## Decline-by-default examples

ORMs; macros-heavy frameworks; crates that wrap std; utility crates for one function; anything pulling large transitive trees; anything unmaintained for > 12 months; AI/ML crates (no local inference in v1).
