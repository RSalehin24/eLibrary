# Environments and CI/CD

Status: DRAFT

## Pipelines

| Pipeline | Trigger | Steps |
|---|---|---|
| PR | every push | Q1–Q7 gates, unit/property/integration tests, contract diff, plan check, build artifacts |
| Nightly | schedule | fuzzing, mutation tests, Kani proofs, model checking (Q8), E2E matrix, a11y scans, load smoke, `cargo audit` |
| Corpus | on ingestion/search/ruleset changes | gold run (Q9), query-set run, determinism and conservation checks |
| Release | tag | all above + full load + epubcheck on gold outputs + SBOM + signed artifacts + staging deploy + smoke |
| Deploy | manual approval | run migrations (expand), switch symlink, health gate, smoke, auto-rollback on failure |

## Branching

Trunk-based on `main` with short-lived branches; every merge is green; feature flags only for risky rollouts (flag register). Legacy code stays in the existing repository history; the new system starts in a clean top-level directory or repository (decision at P1) so legacy files do not bleed in.

## Migrations discipline

Forward-only SQL; **expand → deploy → contract** across releases; each migration has a test that applies it on the previous release's dump; destructive changes (drops) need a second release and a backup note.

## Environments

See [deployment topology](../04-architecture/deployment-topology.md). Staging holds an anonymized, migrated copy; production credentials never exist outside production.

## Observability and on-call

[Observability](../04-architecture/cross-cutting/observability.md). Single operator: alerts by push notification, quiet hours defined, weekly review of alert noise; a runbook link in every alert.
