# CI quality gates (code side)

Status: DRAFT

Every pull request runs gates Q1–Q11. A phase [exit gate](../12-roadmap/gates.md)
additionally requires the listed human sign-offs.

| Gate | Check | Fails when |
|---|---|---|
| Q1 | `cargo fmt --check`, `cargo clippy --workspace --all-targets -D warnings` with the T-9 deny set and shape thresholds ([coding standards](coding-standards.md)) | any warning |
| Q2 | `cargo test --workspace` including proptests (256 cases PR, 10k nightly) | any failure |
| Q3 | Contract generation up to date; `contracts-*` semver check (`cargo public-api`/schema diff) | uncommitted generated diff or breaking change without bump |
| Q4 | `sqlx` offline data matches migrated schema; migrations apply forward on empty DB and on the last release's dump | drift or failed migration |
| Q5 | `cargo deny` (licenses, bans, advisories), `cargo audit` | known vulnerability not waived with expiry |
| Q6 | Dependency graph rule: service crates depend only on `contracts-*`, `platform-*`, `domain-*` (no service→service) | forbidden edge |
| Q7 | Plan check: `python3 planning/tools/check_plan.py` | any error |
| Q8 | Model check (nightly + when `formal-models/` changes): TLC/Alloy on all models | counterexample |
| Q10 | Dependency register check (`xtask`, once code exists): every lockfile package has an APPROVED entry in the [register](../04-architecture/dependency-policy.md); lockfile unmodified by hand | unapproved or unlisted dependency |
| Q11 | Container checks (from P1): `docker compose config` lint, image build for every service, image scan, INV-PLT-014 assertions | any published domain/DB port, root user, missing limit, unpinned base image |
| Q9 | Gold gates (when ingestion/search code or rulesets change): metrics ≥ thresholds; conservation and determinism on the whole corpus | any regression |

Nightly only: fuzzing (30 min/target), mutation testing (`cargo-mutants`) on pure
cores with score ≥ 85%, Kani proofs, E2E matrix, accessibility scans, load smoke test.

Waivers: a failing gate may be waived only with a dated entry in
`planning/12-roadmap/waivers.md` naming an owner and an expiry ≤ 30 days.
