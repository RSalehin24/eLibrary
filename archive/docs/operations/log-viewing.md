# Log Viewing

Use [logs/scripts/show-logs.sh](../../logs/scripts/show-logs.sh) for both local and deployed environments.

Captured log files are written to:

- `logs/local/frontend/frontend.log`
- `logs/local/backend/backend.log`
- `logs/local/celery/worker.log`
- `logs/local/celery/beat.log`
- `logs/remote/frontend/frontend.log`
- `logs/remote/backend/backend.log`
- `logs/remote/celery/worker.log`
- `logs/remote/celery/beat.log`

Those generated log files are gitignored, while the `.gitkeep` files inside `logs/local/**` and `logs/remote/**` keep the folder structure in the repository.

## Local Logs

When the local stack is started through `local/scripts/dev.sh up` or `./run_local.sh`, Docker Compose watch is already active. Compose watch sync and rebuild messages appear in the attached `local/scripts/dev.sh up` session. The local logs below are the quickest way to confirm the resulting app reload and restart behavior after editing source files.

Frontend dev server logs:

```bash
logs/scripts/show-logs.sh frontend
```

Backend service logs:

```bash
logs/scripts/show-logs.sh backend
```

Individual Celery logs:

```bash
logs/scripts/show-logs.sh worker
logs/scripts/show-logs.sh beat
```

For the backend group, the script tails these files inside `logs/local/`:

- `backend`
- `worker`
- `beat`

Use those local logs to confirm watch results:

- `frontend` shows Vite dev-server and hot reload output after Compose syncs files under `app/frontend`
- `backend` shows Django autoreload output after Compose syncs files under `app/backend`
- `worker` and `beat` show container restarts triggered by Compose watch updates to `app/backend/apps` or `app/backend/config`

## Remote Logs

Remote backend logs:

```bash
logs/scripts/show-logs.sh backend remote
```

Remote worker logs:

```bash
logs/scripts/show-logs.sh worker remote
```

Remote beat logs:

```bash
logs/scripts/show-logs.sh beat remote
```

Remote frontend logs:

```bash
logs/scripts/show-logs.sh frontend remote
```

Remote log behavior:

- `backend remote` streams the remote `backend`, `worker`, and `beat` Docker Compose logs together and writes them to `logs/remote/backend/backend.log`
- `worker remote` streams only the remote Celery worker logs and writes them to `logs/remote/celery/worker.log`
- `beat remote` streams only the remote Celery beat logs and writes them to `logs/remote/celery/beat.log`
- `frontend remote` streams remote Nginx access/error logs and writes them to `logs/remote/frontend/frontend.log`

Every repo-facing script also supports `-h` or `--help` to print usage without running the underlying action.

## Deploy Settings Used For Remote Logs

Remote log streaming uses `deploy/env/.host.env`, especially:

- `DEPLOY_USER_NAME`
- `DEPLOY_IP`
- `DEPLOY_REMOTE_APP_DIR` if you override the default remote path
