# Limits (every resource is bounded)

Status: DRAFT (values marked provisional await the P0 baseline, O-7; values not in the NFR set are assistant proposals)

Each limit is a named constant in `platform-config`, validated at startup, enforced in
code, and tested at limit−1, limit, limit+1 (INV-PLT-008). Values are initial; change
through this table.

| Area | Limit | Value | On exceed |
|---|---|---|---|
| HTTP | request body (JSON) | 1 MiB (provisional, O-7) | 413 `body_too_large` |
| HTTP | internal artifact upload (ingestion to catalog; no manual upload, D-42) | 50 MiB (the Kindle mail limit) | 413 |
| HTTP | profile image | 2 MiB (provisional) | 413 / 422 `invalid_image` |
| HTTP | header size / count | 16 KiB / 100 | 431 |
| HTTP | request timeout (read endpoints / write / admin export) | 5 s / 15 s / 120 s | 504 `timeout` |
| HTTP | per-IP rate, anonymous | 20 req/s burst 60 | 429 + `Retry-After` |
| HTTP | login attempts | 5 / 15 min per account, 20 / 15 min per IP | 429 uniform |
| Search | query length | 200 chars | 400 |
| Lists | public page size (default / max) | 24 / 100 (provisional, O-7) | 422 |
| Search | facet values returned | 100 | truncated flag |
| Lists | admin page size | 100 (provisional, O-7) | 422 |
| Exports | CSV rows | 5,000 (provisional, O-7) | 422 `export_too_large` |
| Accounts | Kindle addresses | 5 | 422 |
| Reader | highlights per book per account | 5,000 | 422 |
| Reader | note length | 10,000 chars | 422 |
| Sessions | idle / absolute | 12 h / 30 d | expiry |
| Reading ticket | TTL | 15 min (900 s) | expiry; reopen |
| Reader | opens per user | 30 / hour | 429 |
| Links | password link TTL | 24 h (setup 7 d) | expiry |
| Passwords | length (characters) | 12 to 128, plus a built-in deny list of common choices (provisional, owner may change; `domain-credentials`) | validation at creation, not at sign-in |
| TOTP | code, step, drift | 6 digits, 30 s step, one step either side accepted; the last accepted step only increases | `domain-credentials`, INV-IDN-005 |
| Acquisition | concurrent requests per source host | 2 | queued |
| Acquisition | delay between pages (default) | 0.5 s | delay |
| Acquisition | requests per automation run / attempts per request | 50 / 3 | stop run / failed |
| Acquisition | per-page bytes / per-book pages | 5 MiB / 5,000 | job → Review |
| Acquisition | fetch retries (per URL) | 4, exponential 2 s→60 s, jitter | mark failed |
| Ingestion | job attempts | 3 | Failed |
| Ingestion | job lease / heartbeat | 120 s visibility timeout, heartbeat every 30 s | lease expiry, job re-queued |
| Ingestion | concurrent jobs (global / per source) | 2 / 2 | queued |
| Ingestion | block count per document | 200,000 | job → Review |
| Builders | EPUB size | 50 MiB | build fails typed |
| Gateway | open SSE streams (total / per user) | 20 / 3 | 429 |
| Gateway | per-upstream concurrency | 64 | 503 |
| Kindle | requests per user | 10 / hour | 429 `rate_limited` |
| Events | pull batch / retention | 500 / 30 d and only past all consumer cursors | alert on cursor lag > 5 min |
| Audit | retention | 1 year (D-40) | pruned by job |
| DB | statement timeout | 5 s (read) / 30 s (write) | error |
| DB | pool size per service | 10 | queued, then 503 |
| Memory | per-request allocation guard | 64 MiB via bounded readers | abort |
