# System context

Status: DRAFT

```
 Visitor ─┐                                      ┌──────────── Source site (read-only)
 Reader  ─┼─► Caddy (TLS, routing, forward-auth) │                    ▲
 Admin   ─┘     │        │                       │                    │ acquisition (GET only)
                │        └─► web (static)        │              ┌─────┴───────────────┐
                │  /internal/authorize            │              │ ingestion-api/worker│
                ▼                                 │              └─────┬───────────────┘
            identity ◄──────── /internal/check ─ catalog ◄── reader     │ POST /internal/books/{id}/versions
                │                  │  (files)       │ pull events      ▼
                └── events ────────┴───────────────►│ ───────────► notify ──► SMTP / Kindle
                                   PostgreSQL (one database + role per service) + per-service file volumes
```

## Actors and external systems

| Actor/System | Interaction | Trust |
|---|---|---|
| Visitor | Public routes: browse, search metadata, published preview, sign-in | untrusted |
| Reader | Authenticated: read, annotate, download, Kindle, per granted scope | authenticated, authorized per grant |
| Operator / administrator | Import workspace (`operate`), users and access (`manage_users`), catalog (`manage_catalog`) | authenticated, MFA when required |
| Demo user | Real restricted account: curated read-only set, no mutations, download or Kindle | authenticated, restricted |
| Source site | Read-only HTTP GET by ingestion | untrusted content; may change or fail |
| Mail provider / Amazon Kindle address | Outbound mail from notify | untrusted delivery |

## Trust boundaries

1. **Internet and Caddy**: everything crossing is untrusted; Caddy is the only public listener. Client-supplied identity headers are stripped.
2. **Caddy and identity**: Caddy forward-authenticates every non-public `/api/*` request; identity returns the verified user id and scopes.
3. **Services and services**: internal network only; internal service token on every call; each service re-checks the scope it declared for the route.
4. **Ingestion and source site**: scraped content is hostile input; parsed and sanitized before it leaves ingestion.
5. **Reader and EPUB content**: every XHTML document is sanitized with an allow-list before storage in the reading copy.

Honest limit: a reader who may read a book receives the whole rendered book and can copy it; the controls are not DRM ([ADR-0023](adr/0023-reader-renders-whole-book.md)).

## What keeps working when something is down

| Down | Still works | Degrades |
|---|---|---|
| ingestion (api or worker) | Everything user-facing | New books stop; jobs resume after restart (leases expire) |
| notify | Everything; mails wait in the outbox | Invitations, resets, Kindle delayed |
| identity | Public routes | All authenticated requests fail closed (401/503); demo and sign-in fail |
| catalog | Already-open reading sessions on tickets (until expiry) | Browse, search, downloads, publication, new reading copies |
| reader | Browse, search, downloads | Reading and reading state |
| postgres | Nothing | Everything (single host, accepted at D-29 scale; backups and restore drill) |
