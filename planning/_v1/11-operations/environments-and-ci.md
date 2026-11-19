# Environments and CI/CD

Status: DRAFT

## Pipelines

| Pipeline | Trigger | Steps |
|---|---|---|
| PR | every push | Q1–Q7 gates, unit/property/integration tests, contract diff, plan check, build artifacts |
| Nightly | schedule | fuzzing, mutation tests, Kani proofs, model checking (Q8), E2E matrix, a11y scans, load smoke, `cargo audit` |
| Corpus | on ingestion/search/ruleset changes | gold run (Q9), query-set run, determinism and conservation checks |
| Release | tag | all above + full load + epubcheck on gold outputs + SBOM + signed artifacts + staging deploy + smoke |
| Image build | every merge to `main` and tag | build every service image once (multi-stage), scan, tag with git SHA, push to registry |
| Deploy | manual approval | pull pinned digests, run `migrate` containers (expand), `docker compose up -d --wait` (health gate), smoke, auto-redeploy of previous digests on failure |

## Branching

Trunk-based on `main` with short-lived branches; every merge is green; feature flags only for risky rollouts (flag register). The legacy project is kept read-only in `archive/` at the repository root (D-22); the new system lives in the top-level directories of this repository (`crates/`, `web/`, `deploy/`, …), so legacy files do not bleed in.

## Migrations discipline

Forward-only SQL; **expand → deploy → contract** across releases; each migration has a test that applies it on the previous release's dump; destructive changes (drops) need a second release and a backup note.

## Environments

See [deployment topology](../04-architecture/deployment-topology.md). Staging holds an anonymized, migrated copy; production credentials never exist outside production.

## Observability and on-call

[Observability](../04-architecture/cross-cutting/observability.md). Single operator: alerts by push notification, quiet hours defined, weekly review of alert noise; a runbook link in every alert.
