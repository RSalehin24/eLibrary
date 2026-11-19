# Configuration and startup

Status: DRAFT

## Typed configuration

One `Config` struct per service in `platform-config`, parsed once from files + environment
with `deny_unknown_fields`. Secrets are `Secret<T>`. A config that fails validation
terminates the process before opening any listener.

## Startup sequence (INV-PLT-001)

1. Parse and validate config (limits in range, URLs well-formed, key files present and permissions correct).
2. Connect to the database with the service role; verify it **cannot** connect to other services' databases (self-test in non-production; checked in deployment tests).
3. Compare applied migration version with the binary's embedded expected version; mismatch → exit `E_SCHEMA_VERSION`.
4. Contract handshake with required peers (`/internal/contract`); incompatible → exit `E_CONTRACT`; optional peers → start degraded with a metric.
5. Verify that every `/api/*` route has a declared scope; a route without one → exit `E_UNDECLARED_ROUTE` (fail closed).
6. Load keys, start event consumers (and, in `ingestion-worker`, the job loop), then open listeners and flip `/health/ready`.

## Health

- `/health/live` — process alive (no dependencies).
- `/health/ready` — database reachable, migrations current, required keys loaded, job queue or event cursor not stuck beyond threshold.
- Readiness never reflects optional peers; degradation is reported in `/health/detail` (internal only).

## Feature flags

Only for gradual rollout of risky behavior (e.g. new ruleset, new search analyzer). Flags are
typed, have an owner and a removal date in this repository's flag register, and are
exercised in both states by tests.
