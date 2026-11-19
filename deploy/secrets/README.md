# Secrets

Secret values are never committed. Each file here is one secret, named as in
`deploy/compose/compose.yaml`; create them on the host. Compose bind-mounts each file as it is, so containers (other uids) need it
readable: file mode 0444, protected by this directory being 0700 (`chmod 700 deploy/secrets`).

- `postgres_password` (dev: `head -c 24 /dev/urandom | base64 > deploy/secrets/postgres_password`)
- `<service>_db_password` for identity, catalog, reader, ingestion and notify (same command; read by that service and by the postgres init script)
