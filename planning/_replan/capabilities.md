# Capability map (step 2)

Status: DRAFT

Built from evidence A–F plus the fixed requirements F1–F7 ([REPLAN](../REPLAN.md)). A capability is something the product must do; services are chosen from these in step 3. "Legacy" = where it lived in the archive.

| # | Capability | Owns (data) | Load / sensitivity | Legacy home | Verdict |
|---|---|---|---|---|---|
| 1 | Authentication: accounts, password setup/reset links, TOTP, sessions, demo login | users, credentials, TOTP, sessions, Kindle addresses | low load, **very high sensitivity** | accounts | keep |
| 2 | Authorization: grants/scopes (global or per book/category/contributor, expiry), read-once, signed capabilities | grants, read-once openings | per-request decisions, high sensitivity | access + common/permissions | keep; same users and admin screen as #1 |
| 3 | Catalog: books, contributors, series, categories, metadata versions/reviews, manual (physical) books, exports | metadata | read-heavy, public | catalog | keep |
| 4 | Search and browse | derived index | read-heavy, public; legacy was plain `icontains`, no index | catalog views | keep, improve |
| 5 | Artifact custody: EPUB, HTML, cover, preview, checksums, downloads | files | large, immutable, access-controlled | catalog GeneratedAsset + access downloads | keep |
| 6 | **Reading**: open an EPUB, serve it to the reading UI, chapters/TOC, themes, font | reading sessions | bursty, protected | access reader + vendored epub.js | **new separate service (F5)** |
| 7 | Personal reading state: progress, bookmarks, highlights, notes, my books (shelf), saved filters | per-user private data | frequent small writes, private | access + catalog UserBook + common | keep; lives with the reader |
| 8 | Ingestion: source catalog sync, submissions/resolution, duplicate review, scrape, curate, validate | submissions, jobs, curated documents, evidence | heavy, long-running, hostile input | ingestion + processing | keep, **merge `processing` into it** (it duplicated records, requests and sync) |
| 9 | Artifact building: canonical document → EPUB/HTML/cover/preview | none (derives artifacts) | CPU-bound, deterministic | ingestion/pipeline | keep as pure library used by ingestion |
| 10 | Review and job operations UI data (queues, SSE progress, actions) | read model of #8 | live updates | processing projection | fold into #8 (no separate projection service) |
| 11 | Mail and Kindle delivery, mail log | templates, send log | side effects, at-least-once | accounts/kindle + access/assets | keep |
| 12 | Audit trail | append-only events | write-heavy, no viewer in legacy | common AuditLog | keep, add viewer |
| 13 | Edge: TLS, routing, rate limits, CSRF, session → identity assertion | none | all traffic | host Nginx + Django middleware | keep (Caddy + thin gateway) |
| 14 | Web UI (public, reader, personal, admin; responsive; bn/en) | none | — | React SPA | rebuild (Angular Material) |
| 15 | Backup, restore, migration of legacy data | — | — | migration/*.sh | keep, Compose-based |

Dropped from legacy with reasons: standalone/duplicate `public/epub-reader` and its GitHub Pages deploy (duplicate); token-vs-slug duplicate reader API families (one family); `processing` UI projection service (read model belongs to ingestion); Redis and Celery (replaced by Postgres queues + task groups, to be re-justified in the architecture step); stray repair scripts (become admin operations or runbooks).
