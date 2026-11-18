# Source site auth cookie: update & sync to the deployed server

The scraper needs a logged-in source site session to fetch **multi-page
tables of contents** (LearnDash paginates the lesson list; pages 2+ are only
returned to an authenticated request). Cloudflare blocks every automated login,
so we never script the login itself — we capture the cookie from a real browser
session and ship the resulting `source_site_auth.json` to wherever the backend runs.

The backend reads the cookie from `SOURCE_SITE_AUTH_STATE_PATH`, which resolves to
`<RUNTIME_STORAGE_DIR>/source_site_auth.json`:

| Environment     | Path inside container               | Backing host file                                                        |
| --------------- | ------------------------------------ | ------------------------------------------------------------------------ |
| Local Docker    | `/app/storage/source_site_auth.json` | `app/backend/storage/source_site_auth.json`                              |
| Deployed server | `/app/storage/source_site_auth.json` | `${DEPLOY_REMOTE_APP_DIR}/app/backend/storage/source_site_auth.json`     |

`app/backend/storage` is a **bind mount** in every compose service
(`backend`, `worker`, `processing-worker`), so updating the host file updates
the cookie for all running containers immediately — the backend re-reads the
file per scrape session, so **no container restart is required**.

## How to refresh the cookie

### 1. Capture from Firefox

Open <https://www.example.com> in **Firefox** and log in.

Run the capture script:

```bash
bash local/scripts/save-source-site-auth.sh
```

This reads the `wordpress_logged_in_*` cookie from the Firefox cookie store and
writes it to `app/backend/storage/source_site_auth.json`.

### 2. Verify the capture

```bash
test -s app/backend/storage/source_site_auth.json && echo "cookie captured"
```

### 3. Deploy-time sync

The deploy script (`deploy/scripts/deploy.sh`) automatically calls
`sync_source_site_auth_file()` which copies the local
`app/backend/storage/source_site_auth.json` to the remote server via `scp`.

### 4. Manual sync (if needed)

```bash
scp app/backend/storage/source_site_auth.json \
  "${REMOTE}:${REMOTE_STORAGE}/source_site_auth.json"
```

Verify on the remote:

```bash
ssh "${REMOTE}" "test -s '${REMOTE_STORAGE}/source_site_auth.json' && echo 'cookie synced'"
```

## Troubleshooting

### Multi-page TOC scraping fails

If you see an error like:

> Sign-in required: the source table of contents spans multiple pages on
> the source site but only N of M TOC pages could be retrieved. Update the
> source site auth cookie and regenerate this book.

The auth cookie has expired. Refresh it by running the capture script again.

### Cookie file not found

Check `SOURCE_SITE_AUTH_STATE_PATH` in your environment. If unset, the backend
defaults to `<RUNTIME_STORAGE_DIR>/source_site_auth.json`.

## Related docs

- Capture script: `local/scripts/save-source-site-auth.sh`
- Deploy-time sync: `sync_source_site_auth_file()` in `deploy/scripts/deploy_steps/environment_and_domain_checks.sh`
- Path resolution: `SOURCE_SITE_AUTH_STATE_PATH` / `RUNTIME_STORAGE_DIR` in the backend settings
