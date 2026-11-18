# Deployment Assets

This folder contains the production deployment definition, deploy-time env templates, and the remote automation scripts.

## Folder Layout

- `deploy/compose/`: production Docker Compose definition
- `deploy/docker/`: production backend/frontend container images and Nginx container config
- `deploy/env/`: deploy env templates plus generated local deploy env files
- `deploy/scripts/`: deploy orchestration and host bootstrap scripts

## Primary Entry Points

- Main deploy script: `deploy/scripts/deploy.sh`
- Deploy env scaffolding: `deploy/scripts/generate-env.sh`
- Host Docker install: `deploy/scripts/install-docker.sh`
- Host Nginx install: `deploy/scripts/install-nginx.sh`
- Host Nginx/Certbot setup: `deploy/scripts/setup-host-nginx.sh`

All repo-facing helpers in `deploy/scripts/` support `-h` or `--help`.

## Common Workflow

```bash
deploy/scripts/generate-env.sh production
deploy/scripts/generate-env.sh host
deploy/scripts/deploy.sh
```

On the first successful deployment to a remote app directory, `deploy/scripts/deploy.sh` prints the configured super admin email and password once so you can record them for later access.

The deployed compose stack now includes a one-shot `backend-init` bootstrap service so migrations and super admin seeding complete before `backend`, `worker`, and `beat` start.
Deploy scripts load `deploy/env/.app.env` directly into the shell environment before invoking Docker Compose, so secrets containing `$` are passed literally without generating a second env file.

## Related Docs

- Full deployment guide: [docs/operations/deployment.md](../docs/operations/deployment.md)
- Remote log viewing: [docs/operations/log-viewing.md](../docs/operations/log-viewing.md)
