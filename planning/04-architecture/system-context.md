# System context

Status: DRAFT

```
 Visitor ─┐
 Reader  ─┼─► Caddy (HTTPS, certificates) ─┬─► web (Angular SSR, Node)           Source site (read-only)
 Admin   ─┘                                 └─► gateway                                   ▲ acquisition (GET only)
                                                │ /internal/authorize                     │
                                                ▼                              ┌──────────┴──────────┐
                                             identity ◄── /internal/check ─┐   │ ingestion-api/worker│
                                                │                          │   └──────────┬──────────┘
                      gateway routes /api/* ──► catalog ◄── reader (fetch EPUB)           │ POST /internal/books/{id}/versions
                                                │ pull events                             ▼
                                                └───────────────────────────────► notify ──► SMTP / Kindle
                                   PostgreSQL (one database + role per service) + per-service file volumes
```

## Actors and external systems

| Actor/System | Interaction | Trust |
|---|---|---|
| Visitor | Public routes: browse, search, detail of metadata only (D-34); sign-in, invite acceptance, password reset | untrusted |
| Reader | Authenticated: preview text, read, annotate, download, Kindle, per granted scope | authenticated, authorized per grant |
| Operator / administrator | Import workspace (`operate`), users and access (`manage_users`), catalog (`manage_catalog`) | authenticated, MFA when required |
| Source site | Read-only HTTP GET by ingestion | untrusted content; may change or fail |
| Mail provider / Amazon Kindle address | Outbound mail from notify | untrusted delivery |

## Trust boundaries

1. **Internet and Caddy**: everything crossing is untrusted; Caddy is the only public listener and does HTTPS and certificate renewal only; it forwards to `web` or `gateway`.
2. **Gateway and identity**: the gateway asks identity to authorize every non-public `/api/*` request; identity returns the verified user id and scopes; the gateway strips client-supplied identity headers and sets the verified ones.
3. **Services and services**: internal network only; internal service token on every call; each service re-checks the scope it declared for the route and trusts identity headers only from the gateway.
4. **Ingestion and source site**: scraped content is hostile input; parsed and sanitized before it leaves ingestion.
5. **Reader and EPUB content**: every XHTML document is sanitized with an allow-list before storage in the reading copy.

Honest limit: a reader who may read a book receives the whole rendered book and can copy it; the controls are not DRM ([ADR-0023](adr/0023-reader-renders-whole-book.md)). Reading tickets are verified by asking identity (D-37).

## What keeps working when something is down

| Down | Still works | Degrades |
|---|---|---|
| ingestion (api or worker) | Everything user-facing | New books stop; jobs resume after restart (leases expire) |
| notify | Everything; mails wait in the outbox | Invitations, resets, Kindle delayed |
| identity | Public metadata routes | All authenticated requests and sign-in fail closed (401/503) |
| gateway | Nothing via `/api/*`; server-rendered pages without API data | All API access (fail closed) |
| catalog | Already-open reading sessions on tickets (until expiry) | Browse, search, downloads, publication, new reading copies |
| reader | Browse, search, downloads | Reading and reading state |
| postgres | Nothing | Everything (single host, accepted at D-29 scale; monthly backups and restore drill, D-33) |
