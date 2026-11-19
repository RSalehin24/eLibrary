# Environments and CI/CD

Status: DRAFT

Everything runs under Docker Compose, one container per component (D-22, [deployment topology](../04-architecture/deployment-topology.md)). Kept from v1: pipelines, trunk-based branching, expand/contract migrations. Changed: no legacy migration or cutover (D-32), no WAL, six services plus `web`, epubcheck and a Java runtime in the worker (D-47), Q-gates renumbered to the current [quality gates](../03-correctness/quality-gates.md).

## Environments

| Env | Compose files | Data | Secrets | Notes |
|---|---|---|---|---|
| dev | `compose.yaml` + `compose.dev.yaml` | synthetic seed | generated throwaway files by `xtask` | bind-mounted source, debug logs, local certificate, mail-sink container, fake clock flag; no real source credential |
| ci | `compose.yaml` + `compose.test.yaml` | fixtures, gold corpus (never committed) | generated per run | ephemeral Postgres per run; E2E runner container; no network egress to the real source (fixtures only) |
| staging | `compose.yaml` + staging override | synthetic seed (nothing is migrated, D-32) | its own secret files, never production's | same images and digests as production; separate host or project name; used for the restore drill and smoke |
| production | `compose.yaml` + production override | real, launched fresh ([launch](runbooks/launch.md)) | secret files on the host only | users invited, books ingested by the pipeline |

Dev, staging and production run the **same images and the same `compose.yaml`**; only the override and the secrets differ. Production credentials never exist outside production and its encrypted backup.

## Image build and release

- CI builds each image once from the merged commit (multi-stage, non-root, read-only root, minimal base pinned by digest), scans it, tags it with the git SHA and pushes it to a registry (registry choice is a dependency-register item, not decided here).
- A release is a `release.env` holding the SHA and the **image digests**; `compose.yaml` references digests only, never `latest`.
- The `ingestion` image (both containers) carries the Java runtime and epubcheck (D-47); the Java package is a new system package that needs approval in the P1 dependency batch; its memory is inside the worker `mem_limit`.
- Deploy (manual approval): pull digests, run `migrate` one-shots (expand phase, forward-only), `docker compose up -d --wait` as a rolling restart one service at a time (never `down` then `up`), run smoke checks, and automatically redeploy the previous digests if the health gate fails (REQ-PLT-022, INV-PLT-022). The previous images stay available until the new ones are healthy.
- A backup is taken before a release that contains a destructive (contract-phase) migration, in addition to the monthly one.
- Deploy never prints secrets and never copies local uncommitted files (legacy X1-013, X1-081).

## Pipelines

| Pipeline | Trigger | Steps |
|---|---|---|
| PR | every push | Q1 to Q7, Q10, Q11 (from P1), unit, property and integration tests, contract diff, plan check, image build and scan |
| Nightly | schedule | fuzzing, mutation tests, model checking (Q8), E2E matrix, a11y scans, load smoke, `cargo audit`, epubcheck over gold outputs |
| Corpus | ingestion, search or ruleset change | Q9 gold gates, query-set run, determinism and conservation |
| Release | tag | all of the above plus full load test, SBOM, staging deploy and smoke, then manual production approval |
| Restore drill | monthly, after each backup, and before major releases | `xtask restore-drill` ([backup](backup-restore.md)) |

## Gates Q1 to Q11

Definitions live in [quality gates](../03-correctness/quality-gates.md); this table says where each runs.

| Gate | What | Runs in |
|---|---|---|
| Q1 | fmt, clippy deny set, shape thresholds | PR |
| Q2 | tests incl. property tests (256 cases PR, 10k nightly) | PR, nightly |
| Q3 | contracts generated and semver-checked | PR |
| Q4 | sqlx offline data, migrations apply on empty DB and on the last release's dump | PR |
| Q5 | `cargo deny`, `cargo audit` | PR, nightly |
| Q6 | no service-to-service crate edge | PR |
| Q7 | `python3 planning/tools/check_plan.py` | PR |
| Q8 | TLC and Alloy models | nightly, on model change |
| Q9 | gold corpus metrics, conservation, determinism | corpus pipeline |
| Q10 | every locked dependency has an APPROVED register entry | PR (once code exists) |
| Q11 | container checks: compose lint, image build, image scan, only caddy publishes ports, non-root, limits, pinned digests | PR (from P1), release |

## Branching and migrations

Trunk-based on `main`, short-lived branches, every merge green; feature flags only for risky rollouts. Legacy code stays read-only in `archive/` (D-22). SQL migrations are forward-only: expand, deploy, contract across releases; each has a test that applies it to the previous release's dump; a drop needs a second release and a fresh backup.

## Observability and on-call

See [observability](../04-architecture/cross-cutting/observability.md). A single operator: alerts by push notification with quiet hours, a weekly look at alert noise, and one runbook link per alert ([runbooks](runbooks/README.md)).

## Open

- Registry choice, encryption/backup tool, Java package: dependency batch at P1.
- Whether CI runs epubcheck over gold outputs only, or also in-process in PRs, is a test-plan detail; the runtime gate is in the worker (D-47).
