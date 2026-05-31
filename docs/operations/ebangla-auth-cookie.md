# ebanglalibrary.com auth cookie: update & sync to the deployed server

The scraper needs a logged-in ebanglalibrary.com session to fetch **multi-page
tables of contents** (LearnDash paginates the lesson list; pages 2+ are only
returned to an authenticated request). Cloudflare blocks every automated login,
so we never script the login itself — we capture the cookie from a real browser
session and ship the resulting `ebangla_auth.json` to wherever the backend runs.

The backend reads the cookie from `EBANGLA_AUTH_STATE_PATH`, which resolves to
`<RUNTIME_STORAGE_DIR>/ebangla_auth.json`:

| Environment     | Path inside container            | Backing host file                                                |
| --------------- | -------------------------------- | ---------------------------------------------------------------- |
| Local Docker    | `/app/storage/ebangla_auth.json` | `app/backend/storage/ebangla_auth.json`                          |
| Deployed server | `/app/storage/ebangla_auth.json` | `${DEPLOY_REMOTE_APP_DIR}/app/backend/storage/ebangla_auth.json` |

`app/backend/storage` is a **bind mount** in every compose service
(`backend`, `worker`, `processing-worker`), so updating the host file updates
the cookie for all running containers immediately — the backend re-reads the
file per scrape session, so **no container restart is required**.

> **Expiry:** the captured `wordpress_logged_in_*` cookie lasts ~1 year **only
> if you tick "Remember Me" at login**. Without it the cookie expires when the
> browser session ends. When the cookie expires, multi-page-TOC books start
> failing with the "Sign-in required" error (see
> [Multi-page TOC failures](#multi-page-toc-failures)). Re-run step 1.

---

## 1. Capture / refresh the cookie locally

1. Open <https://www.ebanglalibrary.com> in **Firefox** and log in.
   **Tick "Remember Me"** so the cookie lasts ~1 year.
2. From the repo root, run:

   ```bash
   bash local/scripts/save-ebangla-auth.sh
   ```

   This reads the `wordpress_logged_in_*` cookie directly from Firefox's cookie
   store and writes it to `app/backend/storage/ebangla_auth.json`. If Firefox's
   cookie can't be read automatically, the script falls back to a manual paste
   prompt (open DevTools → Application → Cookies on ebanglalibrary.com, copy
   the `wordpress_logged_in_*` name and value).

3. Confirm the file exists and is non-empty:

   ```bash
   test -s app/backend/storage/ebangla_auth.json && echo "cookie captured"
   ```

The local Docker stack now picks this up automatically via the storage
bind mount (no restart needed).

---

## 2. Sync the cookie to the deployed server

You have two options. Use **2a** when you're already deploying; use **2b** to
refresh the cookie on a running server without a full deploy.

The commands below assume these values from `deploy/env/.host.env`:

```bash
# Pull these from deploy/env/.host.env (or export them inline)
DEPLOY_USER_NAME=...        # SSH user
DEPLOY_IP=...               # server IP / host
DEPLOY_REMOTE_APP_DIR=...   # absolute repo path on the server

REMOTE="${DEPLOY_USER_NAME}@${DEPLOY_IP}"
REMOTE_STORAGE="${DEPLOY_REMOTE_APP_DIR}/app/backend/storage"
```

### 2a. Automatic sync during deploy

A normal deploy already pushes the cookie. `app/backend/storage` is excluded
from the workspace tarball (it holds runtime data), so the deploy explicitly
copies the cookie via `sync_ebangla_auth_file()` in
[deploy/scripts/deploy_steps/environment_and_domain_checks.sh](../../deploy/scripts/deploy_steps/environment_and_domain_checks.sh).
As long as you ran step 1 before deploying, just run your usual deploy:

```bash
bash deploy/scripts/deploy.sh
```

If no local `ebangla_auth.json` exists, the deploy logs a notice and skips the
cookie sync (multi-page TOC scraping stays limited until you capture one).

### 2b. Manual push to a running server (no full deploy)

Use this to refresh an expired/rotated cookie quickly. Because the storage
directory is bind-mounted into the containers, copying the file to the host
path is enough — running containers read it live on the next scrape.

```bash
# 1. Ensure the remote storage directory exists
ssh "${REMOTE}" "mkdir -p '${REMOTE_STORAGE}'"

# 2. Copy the freshly captured cookie up
scp app/backend/storage/ebangla_auth.json \
    "${REMOTE}:${REMOTE_STORAGE}/ebangla_auth.json"

# 3. Verify it landed and is non-empty
ssh "${REMOTE}" "test -s '${REMOTE_STORAGE}/ebangla_auth.json' && echo 'cookie synced'"
```

No restart is required. If you want to force the running workers to re-read
immediately (e.g. to retry queued books), you can optionally restart just the
scraping services:

```bash
ssh "${REMOTE}" "cd '${DEPLOY_REMOTE_APP_DIR}' && \
  docker compose -f deploy/compose/docker-compose.yml \
    restart processing-worker worker"
```

---

## 3. Verify the cookie works

Regenerate (or create) a book whose source TOC spans multiple pages and confirm
all lesson pages are fetched. If the cookie is valid the lesson count matches
the source; if it's expired the book fails — see below.

---

## Multi-page TOC failures

When a book's source TOC spans multiple pages but the backend can only retrieve
a subset (the typical symptom of an expired/missing cookie), the request is
marked **FAILED** with this error message:

> Sign-in required: the source table of contents spans multiple pages on
> ebanglalibrary.com but only N of M TOC pages could be retrieved. Update the
> ebanglalibrary.com auth cookie and regenerate this book.

These books are also listed on the **Multi-page TOC** processing page, where you
can see, per book, whether it was created successfully or failed. When you see
this error:

1. Refresh the cookie (step 1).
2. Sync it to the server (step 2b).
3. Regenerate the failed book(s).

---

## Reference

- Capture script: [local/scripts/save-ebangla-auth.sh](../../local/scripts/save-ebangla-auth.sh)
- Deploy-time sync: `sync_ebangla_auth_file()` in [deploy/scripts/deploy_steps/environment_and_domain_checks.sh](../../deploy/scripts/deploy_steps/environment_and_domain_checks.sh)
- Path resolution: `EBANGLA_AUTH_STATE_PATH` / `RUNTIME_STORAGE_DIR` in the backend settings
