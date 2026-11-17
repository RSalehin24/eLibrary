# System context

Status: DRAFT

```
 Visitor ─┐                                      ┌──────────── Source site(s) (read-only)
 Reader  ─┼─► Edge (TLS) ─► gateway ─► web (SSR)│                    ▲
 Admin   ─┘                    │                 │                    │ acquisition (GET only)
                               │                 │              ┌─────┴──────┐
        ┌────────────┬─────────┼──────────┬──────┴───┐          │ ingestion  │
        ▼            ▼         ▼          ▼          ▼          └─────┬──────┘
    identity ◄──► access    catalog     content     library           │ commands + events
        │                   (+search)      ▲                          ▼
        └─── events ───────────┬───────────┴──── events ────────► notify ──► SMTP / Kindle
                               ▼
                  PostgreSQL (one database per service) + artifact store (files/S3)
```

## Actors and external systems

| Actor/System | Interaction | Trust |
|---|---|---|
| Visitor | Public pages: search, book, preview | untrusted |
| Reader | Authenticated: read, annotate, download, Kindle | authenticated, authorized per decision |
| Administrator | Admin workspaces | authenticated + MFA when required |
| Source site | Read-only HTTP GET by ingestion | untrusted content; may change or fail |
| Mail provider / Amazon Kindle address | Outbound mail from notify | untrusted delivery |
| Object/artifact store | Content-addressed blobs | trusted storage |

## Trust boundaries

1. **Internet ↔ gateway**: everything crossing is untrusted; the gateway is the only public listener.
2. **Gateway ↔ services**: authenticated with service credentials; services never trust a user identity header that did not come from the gateway's signed session assertion.
3. **Services ↔ services**: only through contracts; capability tokens for bytes.
4. **Ingestion ↔ source site**: scraped content is hostile input; parsed and sanitized before leaving ingestion.

## What keeps working when something is down

| Down | Still works | Degrades |
|---|---|---|
| ingestion | Everything user-facing | New books stop |
| notify | Everything; mail queues in outbox | Invitations/Kindle delayed |
| access | Public search/browse/preview; already-issued capabilities until expiry (≤ 5 min) | New reads, admin actions fail closed |
| identity | Public pages; anonymous users | Login, new sessions fail; existing sessions keep working until expiry if cached assertion valid (≤ 5 min) |
| content | Search, browse, metadata | Preview text, reading, downloads |
| library | Search, browse, reading (without saving progress/annotations) | Progress/annotations queued in client |
| search index | Browse by listing (Postgres) | Text search returns a clear error, not wrong results |
| catalog | Static pages cached at edge for a short TTL | Search/browse |
