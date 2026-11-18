# Evidence E — legacy operations and tests

Status: DRAFT

Source: read-only subagent survey of `archive/{deploy,local,local-production,migration,automation,tests,docs/operations}`; `.env.example` files and `logs/README.md` were not readable (deny rule).

- **Compose (3 near-copies: dev, local-prod, prod):** postgres 16, redis 7, one-shot `backend-init`, `backend` (gunicorn), `worker`, `processing-worker`, `engine`, `beat`, `frontend` (node build → nginx). One Python image for all backend services. Internal-only network; ports bound to 127.0.0.1; healthchecks and `service_completed_successfully` gating; `develop.watch` for dev.
- **TLS/proxy:** host-level Nginx + Certbot installed by a 279-line script, outside Compose.
- **Secrets:** `.env` files scaffolded/merged by scripts, insecure defaults in anchors, no Docker secrets.
- **Backups:** **none scheduled**; only a 4-phase server-to-server migration tool (~1,900 lines bash: drain, `pg_dumpall`, Redis RDB, storage tarballs, checksums, row-count manifest).
- **Deploy:** ~4.6k lines of bash over SSH; full rebuild and recreate each time (interrupts in-flight tasks; `acks_late` redelivers).
- **Tests:** ~481 pytest functions (20.6k lines), 20 node unit files, 42 Playwright specs (9.6k lines) against the real Docker stack, `verify.sh` all-in-one flow, `live` marker for tests that hit the source.
- **Pain:** triplicated compose config, migrate/collectstatic/seed on every start, host paths for static/media, manual cookie refresh, per-process memory limits, custom docker wrapper for dev.
- **Reusable ideas:** topology with init-gating and healthchecks, internal network, multi-stage frontend, `develop.watch`, one env base + overrides, migration freeze/checksum/row-count verification, test layering and deterministic E2E seed.
