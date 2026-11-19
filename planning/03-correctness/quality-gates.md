# CI quality gates (code side)

Status: DRAFT

Rebuilt 2026-11-19 for six Rust services, the Angular SSR `web` and Docker Compose. Kept from v1: Q1 to Q10 numbering; changed: web checks, container checks, no migration dump (D-32). **None of these gates exists yet**: no code, CI or toolchain is installed, and the thresholds are plans.

Every pull request runs gates Q1–Q11. A phase [exit gate](../12-roadmap/gates.md)
additionally requires the listed human sign-offs.

| Gate | Check | Fails when |
|---|---|---|
| Q1 | `cargo fmt --check`, `cargo clippy --workspace --all-targets -D warnings` with the T-9 deny set and shape thresholds ([coding standards](coding-standards.md)) | any warning; for `web`: ESLint (strict-type-checked), `tsc` strict, Angular template type-check (`strictTemplates`) |
| Q2 | `cargo test --workspace` including proptests (256 cases PR, 10k nightly), service integration tests on ephemeral PostgreSQL, `web` unit tests | any failure |
| Q3 | Contract generation up to date for the six services and the generated TypeScript client; schema diff and version check; every `/api/*` route declares a scope | uncommitted generated diff, breaking change without bump, route without scope |
| Q4 | `sqlx` offline data matches migrated schema; migrations apply forward on an empty database (per service, own role) and on the previous release's schema | drift or failed migration |
| Q5 | `cargo deny` (licenses, bans, advisories), `cargo audit`, `npm audit` (nightly) | known vulnerability not waived with expiry |
| Q6 | Dependency graph rule: service crates depend only on `contracts-*`, `platform-*`, `domain-*` (no service→service) | forbidden edge |
| Q7 | Plan check: `python3 planning/tools/check_plan.py` | any error |
| Q8 | Model check (nightly + when `formal-models/` changes): TLC/Alloy on all models | counterexample |
| Q10 | Dependency register check (`xtask`, once code exists): every lockfile package has an APPROVED entry in the [register](../04-architecture/dependency-policy.md); lockfile unmodified by hand | unapproved or unlisted dependency |
| Q11 | Compose and container checks (from P1): `docker compose config` lint; all ten containers declared with memory limit and restart policy; image build for every service including `web` (Node SSR) and the ingestion image with Java and epubcheck; image scan; only `caddy` publishes host ports; non-root user and read-only root filesystem; no secret in an image or environment; base images pinned by digest; image size limits (Rust at most 100 MB, web at most 50 MB, REQ-NFR-005; the ingestion image is excepted for the Java runtime, size recorded); INV-PLT-001 and INV-PLT-016 assertions | any published domain or database port, root user, missing limit, unpinned base image, secret in an image |
| Q9 | Gold gates (when ingestion or search code or rulesets change): metrics at or above the thresholds recorded at the P0 baseline (OPEN: values; search relevance is SHOULD, O-5); conservation and determinism on the whole corpus. The corpus is third-party content and is never committed or put in a CI image, so Q9 runs on the owner's machine and in the local nightly run, and its result report is the evidence | any regression |

Nightly only: fuzzing (30 min/target), mutation testing (`cargo-mutants`) on pure
cores with score ≥ 85%, Kani proofs, E2E matrix on the ephemeral Compose stack (Playwright, axe, both themes, four widths), load smoke test, fault-injection rows not marked PR. Monthly, by hand: the backup restore drill (INV-PLT-015); it is a drill, not a CI gate.

Waivers: a failing gate may be waived only with a dated entry in
`planning/12-roadmap/waivers.md` naming an owner and an expiry ≤ 30 days.
