# Glossary (ubiquitous language)

Status: DRAFT

Use these words exactly in code, contracts and UI copy. Authoritative design: [new architecture](../_replan/new-architecture.md). Services: gateway, identity, catalog, reader, ingestion, notify.

## People, identity, access

| Term | Meaning |
|---|---|
| **Visitor** | Anyone without a session; may use public routes only (catalog metadata browse, search and detail with covers and summaries; sign-in, invite acceptance, password reset). Preview text and reading require sign-in (D-34). |
| **User** | An account in identity, created by invitation. |
| **Role** | Named bundle of default scopes: `reader`, `operator`, `admin`. Roles are not wildcards. |
| **Scope** | One named permission: `browse`, `preview`, `read`, `read_once`, `download`, `kindle`, `operate`, `manage_catalog`, `manage_users`. |
| **Grant** | An explicit row (user, scope, optional book, optional expiry, granted_by) in identity. Access exists only through grants and role defaults. |
| **Entitlement** | The result of an identity decision that a user may use a scope on a book now (includes publication state and expiry). |
| **Deny by default** | No scope declared, no access. Every `/api/*` route declares its scope in code; a route without one is rejected at startup. |
| **Invite** | A single-use, expiring link that lets a person set a password and activate an account. |
| **Session** | Opaque server-side session in identity, carried by a cookie. |
| **Read-once** | Scope allowing one successful reading of a book; consumed when a ticket is redeemed for the book. |
| **Audit log** | Append-only record of who did what (auth events, grants, roles, publish, unpublish, delete, operator actions, book opens, downloads), kept 1 year (D-40). |
| **Internal service token** | Credential a service presents on service-to-service calls; services also trust identity headers only from the gateway. |

## Catalog

| Term | Meaning |
|---|---|
| **Book** | A catalog entry with stable id and slug; what users see. |
| **Version** | One build of a book's files and metadata. States: draft, published, archived. |
| **Published version** | The version readers see and read; only published versions are visible to readers. |
| **Publication workflow** | draft, published, archived; soft delete; publishing is automatic when every gate passes (D-49); edit, unpublish and delete need `manage_catalog`. |
| **Metadata** | Title, contributors with roles (writer, translator, editor, compiler, publisher), series, categories, summary. |
| **Metadata version history** | Snapshot of every metadata edit. |
| **Asset** | A registered file of a version (EPUB, cover) on the catalog volume. |
| **Shelf (My Books)** | A user's personal list of books. Never grants access. |
| **Preview** | Published excerpt, shown only to signed-in users with the `preview` scope (D-34): cover, metadata, summary, TOC and a configured number of characters of the first chapter (D-05). |
| **Search index** | PostgreSQL full-text index with Bengali normalization, owned by catalog. |
| **Kindle request** | A request by a user to send a book's EPUB to one of their Kindle addresses; executed by notify. |

## Reader

| Term | Meaning |
|---|---|
| **Reading copy** | The parsed and sanitized rendering of one published version (OPF, spine, TOC, XHTML, images, fonts) stored by reader, keyed by (book, version). |
| **Reading ticket** | Token bound to user, book and version, valid 15 minutes, sent in a header or body (never a URL), issued by `open` after the `read` check; the reader verifies it by asking identity every time, so revocation is immediate (D-37). |
| **Open** | `POST /api/reader/books/{slug}/open`: checks the scope and returns a ticket. |
| **Whole-book package** | The single response carrying manifest, TOC, chapters and resources that the browser renders. |
| **Reading session / progress** | Per-user last position and percent for a book. |
| **Bookmark, highlight, note** | Per-user annotations anchored in the reading copy; require the session in addition to the ticket. |
| **Anchor** | Position in a reading copy that survives rebuilds: section id plus text quote plus offsets. |
| **Honest limit** | The reader serves the whole book, so an entitled reader can copy it; controls are entitlements, short tickets, rate limits and audit, not DRM. |

## Ingestion

| Term | Meaning |
|---|---|
| **Source** | The one external website the library mirrors and scrapes. |
| **Source mirror** | Ingestion's local copy of the source's book listing (title, author line, URL, category, series, incomplete flag). Source fields only; workflow state is stored separately so a re-sync never overwrites it. |
| **Request** | The single intake record for one wanted book (from a mirror row, URL or title), with state and history. Replaces the legacy submission and creation-request pair. |
| **Job** | A unit of work in the PostgreSQL `jobs` table, claimed with `FOR UPDATE SKIP LOCKED`, with lease, heartbeat, attempt counter and typed outcome. |
| **Lease / visibility timeout** | Time a worker owns a job before another may reclaim it. |
| **Typed error** | `retryable` or `permanent`; retry is never decided from error text. |
| **Cancel flag** | Cooperative stop checked per page. |
| **Source credential** | The single rotatable source-site cookie, a read-only secret file; only its status and expiry are in the database. |
| **Scrape cache** | Fetched source pages stored as files, retained 30 days. |
| **Curated document** | The one authoritative structured, validated representation of a book (metadata, section tree, evidence); EPUB and previews are derived and regenerable. |
| **Duplicate review** | An explicit state where a human decides on a near-match; matching is exact normalized key plus author, category and edition; never auto-merged. |
| **Candidate (build)** | A built EPUB set that is invisible until published. |
| **Structure audit** | Well-formedness and EPUB structure gate that every build must pass. |
| **Publish** | Ingestion calls catalog `POST /internal/books/{id}/versions`; catalog publishes it in the same transaction; there is no approval step (D-49). |
| **Gold corpus** | Human-labeled source books with expected curated documents; test oracle; never committed. |

## Platform

| Term | Meaning |
|---|---|
| **Gateway** | Rust service that routes `/api/*`, calls identity `/internal/authorize`, applies rate limits and CSRF. |
| **Event / outbox** | A change record written in the producer's transaction to an `events` table, read by consumers via `GET /internal/events?after=<cursor>`; consumers are idempotent. |
| **Cursor** | A consumer's stored position in a producer's event stream. |
| **Notify outbox** | Mail records with template, status and retries in notify. |
| **Window class** | Responsive layout class: compact, medium, expanded, large. |
| **Design token** | Material Design 3 token that drives light and dark themes. |
| **Gate** | Exit criterion for a roadmap phase; later work is blocked until it passes. |
| **Launch runbook** | Procedure for the first production start (replaces the legacy cutover; no data migration, D-32). |
