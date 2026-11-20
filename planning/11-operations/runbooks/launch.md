# Runbook: launch (first start of production)

Status: DRAFT

Replaces v1 "cutover" (D-32: nothing is migrated; users are re-invited, books are re-ingested). The legacy deployment is already shut down and archived (D-50); no step here depends on it and readers have no library until this launch completes.

**Preconditions**
- Release gates for the phase passed; release `release.env` with image digests exists; staging smoke and a restore drill passed ([backup](../backup-restore.md)).
- DNS points to the host; ports 80 and 443 free (Caddy publishes both; 80 only for the certificate flow).
- Secret files generated on the host with mode 0400 ([secrets](../../10-security/secrets-and-keys.md)); no value was typed into a shared file or printed.
- **Source access (D-99, gate G6):** the owner's source cookie is in place before step 5; without it stop after step 4 and run the pipeline on fixtures only.

**Steps**
1. **Start the stack.** `postgres`, then `migrate` one-shots, then `docker compose up -d --wait` on the pinned digests. Startup checks must pass; a service that refuses to start names its failed check (missing secret, schema version, undeclared route).
2. **Seed the first admin.** Run identity `seed-first-admin` as a host command. It defaults to a dry run; read the plan, then run it with the explicit apply flag. It refuses if an admin exists, takes no password and prints a one-time setup link instead. Open the link, set a password, enrol TOTP.
3. **Invite users.** In Users and access, invite the first readers (reader role gives `browse`, `preview`, `read`, `kindle` by default; `download` and `read_once` only by explicit grant). Confirm one invite mail arrives (notify delivery log).
4. **Create the operator** (role `operator`) if different from the admin.
5. **Install the source credential.** Place the source-site cookie file in the secret location, mode 0400, restart nothing (it is read from the mounted file). Check the console: status `valid` with an expiry ([source-cookie-expired](source-cookie-expired.md) for later renewal).
6. **First import.** In the Import workspace: run a catalog sync (page budget as configured), pick one small book, create a request, watch scrape, curate, duplicate review, build and epubcheck gates. With every gate passed the book becomes `published` automatically (D-49; no approval); check it in the Library, and unpublish (`manage_catalog`) if it is wrong. Then queue the rest in bounded batches; automation stays off until the first batch is reviewed.
7. **Smoke checks.** (a) public browse and search show metadata only and no preview text; (b) a signed-out request to a preview or reader route returns 401; (c) a reader opens the book and the reader shows it; progress survives a reload; (d) `download` is refused for a reader without the grant; (e) a Kindle send reaches the notify log; (f) an unpublished book is invisible to readers; (g) health and readiness of all ten containers are green and only Caddy has published ports; (h) logs contain no secret or token.
8. **Backup.** Take the first backup immediately and copy it offsite; record the date. The monthly cycle starts here ([backup](../backup-restore.md)); the data-loss window is 30 days.
9. **Announce** to the invited users, stating what the no-DRM limit and the 30-day backup window mean for them if the owner wishes to.

**Rollback.** Before users exist: `docker compose down -v` is allowed on a launch that has no real data; after users exist use the normal rollback (previous digests) or [restore](restore.md).

**Verify.** All smoke checks pass; first backup is offsite; admin can sign in with TOTP; alerts are armed.

**Follow-up.** Record the launch date and release digests; schedule the first restore drill.
