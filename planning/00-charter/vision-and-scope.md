# Vision and scope

Status: DRAFT

## Vision

A calm, fast, trustworthy Bangla (and English) digital library: anyone can
**discover** books and read a **preview** without an account; signed-in readers
**read** in a first-class reader; administrators **grow the library** from
source sites and manual uploads with confidence that what they publish is
structurally correct.

## Users

| Persona | Needs | Key surfaces |
|---|---|---|
| Visitor (anonymous) | Find a book, see who wrote it, read a preview, decide to sign in | Search, book page, preview |
| Reader (account) | Read comfortably, keep place, highlight, send to Kindle | Reader, shelf, notes |
| Curator (admin) | Add books, fix metadata, resolve duplicates, trust the result | Sources, Jobs, Review queue, catalog editor |
| Access manager | Invite people, grant/revoke abilities | Accounts & access |
| Operator (you) | Deploy, observe, recover | Runbooks, dashboards |

## In scope (v1)

1. Public search, browse (category, series, writer, translator, editor, publisher), book page, preview.
2. Invite-only accounts, password links, TOTP, sessions, demo read-only access.
3. Fine-grained access (grants by global/category/author/book scope), read-once, download, Kindle.
4. Reader with progress, bookmarks, highlights, notes; notes page.
5. Ingestion: source catalog sync, book creation from a source URL, manual EPUB intake,
   deterministic EPUB/HTML/preview/cover generation, duplicate/edition handling,
   review queue, reprocessing with diff.
6. Catalog administration: metadata overrides, entity merge/split, exports (CSV/XLSX/PDF).
7. Operations: observability, backups, migration from the legacy system.

## Out of scope (v1)

Social features, payments, recommendations, native mobile apps, PWA/offline
reading (kept as a v2 candidate), user-generated books other than admin EPUB
intake, multi-tenant libraries.

## Deliberate changes from the legacy system

| Legacy | New |
|---|---|
| Everything requires login | Search, browse, preview are public |
| 6 Django apps, one DB, import cycles | Independent services, one DB each, contract-only coupling |
| `processing` app duplicating `ingestion` state + UI projection tables | One job model; UI reads it directly |
| 10+ processing pages (catalog, create, on-hold, incomplete, multipage-toc, reprocessing…) | 3 admin workspaces: Sources, Jobs, Review |
| Regex pass pipeline that silently drops unclassified text | Conservation-checked pipeline with evidence and a review queue |
| Scraper mutates the source site ("mark complete") | Read-only acquisition unless decision D-03 explicitly allows otherwise |
| CFI-only annotation anchors | Section id + text-quote + position anchors with re-anchoring |
| Celery + Redis (+ RabbitMQ in the failed branch) | Postgres-backed outbox and queues |
