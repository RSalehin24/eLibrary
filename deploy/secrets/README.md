# Secrets

Secret values are never committed. Each file here is one secret, named as in
`deploy/compose/compose.yaml`; create them on the host (mode 0400).

- `postgres_password` (dev: `head -c 24 /dev/urandom | base64 > deploy/secrets/postgres_password`)
