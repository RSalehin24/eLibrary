# Abuse resistance and privacy

Status: DRAFT

Kept from v1: the control table and the data inventory form. Changed: public surface is metadata only (D-34); no uploads (D-42); no demo (D-35); no cache layer, so counters live in the gateway's bounded memory tables (REQ-GWY-007); audit scope and retention follow D-40; erasure is an admin action on request (D-30).

Numbers come from [limits](../04-architecture/cross-cutting/limits.md); those marked provisional wait for the P0 baseline (O-7).

## Abuse controls

| Surface | Control | Requirement / invariant |
|---|---|---|
| Public browse, search, detail, cover | gateway per-IP token bucket (20 req/s, burst 60), query length 200, page size 24 default and 100 max, bounded result window; only `PublicDocument` data is reachable | INV-GWY-007, INV-CAT-017, INV-CAT-012 |
| Scraping of our own site | the public surface holds metadata and covers only; preview text and reading need a session; per-user open limit 30/h; a reading copy is the whole book, so copying by a signed-in reader is an accepted limit (see threat T-24); audit of every open is the deterrent | INV-RDR-011 |
| Sign-in, reset, invite acceptance | 5 attempts per 15 min per account and 20 per 15 min per IP; uniform response, status and timing; lockout is a delay, not a permanent lock, to avoid lock-out DoS | INV-IDN-008, REQ-IDN |
| Account enumeration | identical response for known and unknown addresses on sign-in, reset and resend | INV-IDN-008 |
| Cookie-authenticated writes | CSRF token and Origin check at the gateway | INV-GWY-005 |
| Downloads | `download` scope by explicit grant only; each download audited (actor, book, version) | INV-CAT-023, INV-CAT-031 |
| Kindle | `kindle` scope; at most 5 addresses per user; 10 sends per hour per user (provisional); send only after identity Allow; size at most 50 MiB | INV-NTF-005, INV-NTF-007, INV-IDN-028 |
| Mail volume | notify retries are bounded; invites are admin only; reset links expire in 24 h, setup links in 7 d | INV-NTF-008, INV-IDN-002 |
| Profile images | allow-listed types, SVG refused, 2 MiB (provisional), re-encoded; served only through identity to authorized viewers | INV-IDN-034 |
| Console and exports | `operate` / `manage_catalog` scopes; bulk actions bounded with per-item results; CSV at most 5,000 rows and cells starting with `=`, `+`, `-`, `@` escaped | INV-ING-008, INV-CAT-027 |
| SSE streams | 20 total and 3 per user; closed when the session is revoked | INV-GWY-013 |
| Source site (outbound abuse) | GET only, 2 concurrent requests per host, 0.5 s delay, honest User-Agent, no evasion of bot protection | INV-ING-010 |

An optional proof-of-work or captcha switch (v1 idea) is not part of the design; it would need a new dependency and an owner decision.

## Personal data inventory

| Data | Owner service | Purpose | Retention | User rights |
|---|---|---|---|---|
| Email, display name, status, roles, grants | identity | sign-in, mail, authorization | until the account is deleted | export (JSON), delete on request |
| Password hash (Argon2), TOTP secret (encrypted), sessions | identity | authentication | hash and secret until deletion; sessions 12 h idle / 30 d absolute | deleted with the account |
| Profile image (D-44) | identity volume | display | until replaced or account deleted | replace, delete |
| Kindle addresses (at most 5) | identity | deliveries | until removed or account deleted | edit, delete |
| Reading progress, bookmarks, highlights, notes, preferences (D-48) | reader | the feature | until the account is deleted | JSON export (and Markdown notes), delete |
| Shelf ("My Books"), saved filters (D-43) | catalog | the feature | until the account is deleted | delete; export of these two is OPEN (the identity and reader exports exist; catalog's own export route is not in the contract) |
| Audit rows (auth, grants, roles, publish/unpublish/delete, operator actions, opens, downloads; D-40) | identity, catalog, reader, ingestion | accountability | 1 year then pruned by a retention job | not user-editable; the audit holds user ids and hashed IP, not content |
| Reading ticket records | identity | revocation, read-once | until expiry plus the audit row | none |
| Mail outbox and delivery log (addresses by reference, no body kept longer than needed) | notify | delivery diagnostics | bounded retention job; value is a notify design number (REQ-NTF-012) | deleted by the job |
| IP address and user agent | gateway logs, audit | rate limits, security | log rotation by the Docker driver (size and file bound); audit keeps a hashed IP only | none |
| Backups of all of the above | host and offsite | recovery | monthly set, retention in [backup](../11-operations/backup-restore.md) | see erasure below |

Principles: collect the minimum; no third-party analytics or fonts; no personal data in log lines beyond hashed subject ids and request ids (INV-PLT-019); no book text and no personal data are sent to any external service; only notify sends mail, only to the account's own addresses.

## Export and erasure

- **Export.** A signed-in user can download their own data as JSON: identity data from `GET /me/export` and reading data from the reader's export route (INV-RDR-017, INV-RDR-019). Whether one combined file is offered is a web design detail.
- **Erase.** Erasure is on request: an admin deletes the account (`DELETE /users/{id}`, `manage_users`). Identity removes the user row, sessions, grants and Kindle addresses (INV-IDN-031) and the reader removes all of the user's reading data (INV-RDR-017). **How the other services learn about the deletion is OPEN (O-1):** a `user.deleted` event pulled from identity (recommended) or the internal `POST /users/{id}/erase` call. Shelf entries and saved filters in catalog are covered by the same open point.
- **Audit rows are kept** for their 1-year retention after deletion (they hold the user id only); this is the one deliberate exception, justified by accountability, and is stated here so it is a decision of record, not an accident. The owner may confirm or change this.
- **Backups.** A deleted account can reappear after a restore from an older monthly backup. The restore runbook includes a step to re-apply deletions recorded since the backup (from the audit trail kept outside the backup, or the admin's own list). Backups are not edited individually.
- **Time limit.** Deletion is performed by the admin on request; the target is completion within 7 days (provisional, owner may change).

## Audit retention

1 year (D-40), pruned by a bounded retention job in each service (REQ-PLT-021, INV-PLT-021). The audit tables have no UPDATE or DELETE privilege for any service role except the retention job's own narrow role (INV-PLT-009). Who may read identity's audit log is OPEN (C-1; recommended `manage_users`).
