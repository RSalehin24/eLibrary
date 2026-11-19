# Configuration and startup

Status: DRAFT

## Typed configuration

One `Config` struct per service in `platform-config`, parsed once from files + environment
with `deny_unknown_fields`. Secrets are `Secret<T>`. A config that fails validation
terminates the process before opening any listener.

## Startup sequence (INV-PLT-003)

1. Parse and validate config (limits in range, URLs well-formed, key files present and permissions correct).
2. Connect to the database with the service role; verify it **cannot** connect to other services' databases (self-test in non-production; checked in deployment tests).
3. Compare applied migration version with the binary's embedded expected version; mismatch → exit `E_SCHEMA_VERSION`.
4. Contract handshake with required peers (`/internal/contract`); incompatible → exit `E_CONTRACT`; optional peers → start degraded with a metric.
5. Verify that every `/api/*` route has a declared scope (gateway: that the public allow-list is closed and every proxied prefix exists); a route without one → exit `E_UNDECLARED_ROUTE` (fail closed). The gateway has no database; steps 2 and 3 do not apply to it.
6. Load keys and secret files (permissions 0400), start event consumers (reader, catalog, ingestion, notify; and, in `ingestion-worker`, the job loop), then open listeners and flip `/internal/ready`.

## Health

On the internal port only (never routed by Caddy or the gateway):

- `GET /internal/health` — process alive (no dependencies).
- `GET /internal/ready` — database reachable, migrations current, required keys loaded, job queue or event cursor not stuck beyond threshold. Gateway readiness reports whether identity is reachable.
- Readiness never reflects optional peers; degradation is reported in `/internal/health/detail`.
- `GET /internal/contract` — contract version for the startup handshake.

## Feature flags

Only for gradual rollout of risky behavior (e.g. new ruleset, new search analyzer). Flags are
typed, have an owner and a removal date in this repository's flag register, and are
exercised in both states by tests.
