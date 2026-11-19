# reader - test plan

Status: DRAFT

Every REQ-RDR id has at least one row. Fuzz and mutation suites run in CI with bounded time and memory (`ulimit`, timeouts) and fixed seeds.

| ID | Level | What | REQ | INV |
|---|---|---|---|---|
| TST-RDR-001 | model, prop | Build idempotency: redelivered `book.published` and concurrent workers build one copy per `(book_id, version_id)`; unit: OPF, spine, TOC (nav and NCX), images, fonts from fixture EPUBs, Bengali text preserved | REQ-RDR-001 | INV-RDR-001 |
| TST-RDR-002 | prop | Determinism: `parse(epub, parser_version)` run twice gives byte-identical packages; reordered ZIP entries still give the same package | REQ-RDR-002 | INV-RDR-002 |
| TST-RDR-003 | type, fuzz | Sanitizer fuzzing (coverage-guided, plus a corpus of known XSS vectors): no script, handler, external load, `javascript:`/`data:` or unknown scheme survives; idempotent; no panic or unbounded memory; compile-fail: the package writer rejects a plain `String` | REQ-RDR-003 | INV-RDR-003 |
| TST-RDR-004 | unit, e2e | Link rewriting: internal links resolve to section ids, resources to package ids, no external URL remains; ticket in a URL query is rejected and never logged | REQ-RDR-003, 006 | INV-RDR-003, 006 |
| TST-RDR-005 | db, drill | Copy states: only Ready is served; replace is atomic (concurrent open sees old or new); unpublish makes the copy Withdrawn; a copy change deletes no annotation; drill: delete the volume, startup rebuilds from catalog | REQ-RDR-004 | INV-RDR-004 |
| TST-RDR-006 | model, e2e | Open decides through identity: no `read` scope, unpublished, deleted or not-found book gives no ticket; shelf membership never changes the decision (random grants x shelf x state); `preview` alone is denied | REQ-RDR-005 | INV-RDR-005 |
| TST-RDR-007 | type, e2e | Ticket contract: TTL 15 min with a fake clock (14:59 valid, 15:00 invalid); bound to user, book and version (wrong ones rejected); header only; compile-fail: the book handler takes only `Verified<ReadingTicket>`; no local signature check exists | REQ-RDR-006 | INV-RDR-006 |
| TST-RDR-008 | model, e2e | Revocation: `grant.changed`, `user.disabled`, `book.unpublished` make the next redeem fail even with the event consumer stopped (identity verify is authoritative) | REQ-RDR-007 | INV-RDR-007 |
| TST-RDR-009 | type, e2e | One package response for the whole book; no per-chapter or EPUB route exists (route table scan); response has CSP, nosniff, `private, no-store` | REQ-RDR-008, 025 | INV-RDR-008, 025 |
| TST-RDR-010 | model, db, e2e | Read-once: open does not consume; redeem consumes once; reload with the same ticket works; new ticket denied; Building or missing copy never consumes; two devices race: exactly one consumes; applies to every role; model [ReadOnce](../../03-correctness/formal-models/tla/ReadOnce.tla) re-checked | REQ-RDR-009 | INV-RDR-009 |
| TST-RDR-011 | review | Honest-limit wording present in README, API docs, in-app help and ADR-0023; no text promises DRM or copy prevention | REQ-RDR-010 | INV-RDR-010 |
| TST-RDR-012 | db, e2e | Audit: every open, redemption and denial writes one `opens` row without the ticket secret; rate limits give 429 with `Retry-After`; service role cannot UPDATE or DELETE `opens` | REQ-RDR-011 | INV-RDR-011 |
| TST-RDR-013 | model, db, prop | Progress: stale revision never overwrites; percent bounded; locator bound; PUT idempotent; section plus offset stored; the `Progress` model for reordered and duplicated writes | REQ-RDR-012 | INV-RDR-012 |
| TST-RDR-014 | db, e2e | Bookmarks: create twice gives one row (`created: false`), delete twice is idempotent, delete works without a ticket, jump data returned | REQ-RDR-013 | INV-RDR-013 |
| TST-RDR-015 | unit, e2e | Highlights and notes: create, edit (`If-Match`), recolour, delete; five colours from one definition; keyboard-only path, labelled dialog, retryable error state | REQ-RDR-014 | INV-RDR-014 |
| TST-RDR-016 | prop, mutation | Anchor re-anchoring mutation tests: apply random mutations to the section text (whitespace, markup wrapping, small edits, paragraph insertion, chapter split and merge, quote deleted) and assert: placed or orphaned, never an error, never a deletion; at least 99 percent placed on non-semantic mutations; idempotent | REQ-RDR-015 | INV-RDR-015 |
| TST-RDR-017 | e2e, db | Cross-account: A cannot read or change B's progress, bookmarks, highlights (table-driven over all routes; other owners' ids give 404); RLS rejects cross-owner SQL even with a handler bug; routes need session plus ticket where declared | REQ-RDR-016 | INV-RDR-016 |
| TST-RDR-018 | unit, e2e | Export: JSON has all and only the owner's reading data; deleting the account removes it (internal erase route or event per O-1) | REQ-RDR-017 | INV-RDR-017 |
| TST-RDR-019 | e2e | Notes page: deep links open the exact section and offset or show the orphan state; links use the typed route table | REQ-RDR-018 | INV-RDR-018 |
| TST-RDR-020 | unit | Markdown and JSON notes export contains exactly the owner's notes and highlights (SHOULD) | REQ-RDR-019 | INV-RDR-019 |
| TST-RDR-021 | e2e, review | Themes and typography: light, dark, sepia follow the app by default and then the user's choice (one state owner); CSS variables only, no `!important` on book content; preferences stored per user in the reader service (D-48), round-trip tested | REQ-RDR-020 | INV-RDR-020 |
| TST-RDR-022 | e2e, review | WCAG AA: keyboard path for every action, zoom not hijacked, Esc leaves immersive mode, targets at least 48 px, reduced motion, location announced (axe plus manual review) | REQ-RDR-021 | INV-RDR-021 |
| TST-RDR-023 | type, e2e | Exhaustive reader state enum: copy building, forbidden, not found, ticket expired (one silent re-open, then a message), offline, error, each with a retry; no blank page or browser alert | REQ-RDR-022 | INV-RDR-022 |
| TST-RDR-024 | unit, e2e | In-book search returns positions within the opened version's text layer and the result jumps to them (SHOULD) | REQ-RDR-023 | INV-RDR-023 |
| TST-RDR-025 | unit | Cross-implementation fixtures: the text layer and offsets computed in Rust equal the browser's for the same sanitized sections (Bengali, ZWJ, combining marks, emoji) | REQ-RDR-015, 023 | INV-RDR-015, 023 |
| TST-RDR-026 | contract, prop | Event consumer: duplicates and replays leave state unchanged; crash between effect and cursor re-applies safely (one transaction); lost cursor resyncs from `GET /internal/books` | REQ-RDR-024 | INV-RDR-024 |
| TST-RDR-027 | fault | Catalog unreachable during build: retries, `copy_unavailable` on open, nothing half-built served, rebuild later succeeds; identity unreachable fails closed and consumes nothing | REQ-RDR-001, 004, 009 | INV-RDR-001, 004 |
| TST-RDR-028 | prop, e2e | GET handlers perform no state change beyond the audit row: a missing copy changes no entitlement or catalog state | REQ-RDR-025 | INV-RDR-025 |
| TST-RDR-029 | fuzz | Hostile EPUB corpus (zip bomb, traversal names, huge nesting, malformed XHTML, huge fonts): build ends in Failed with a typed code within limits | REQ-RDR-003, 004 | INV-RDR-003, 004 |
| TST-RDR-030 | e2e | Unpublished, archived, deleted or withdrawn book: open returns not found; a stale ticket after unpublish fails | REQ-RDR-005, 007 | INV-RDR-005, 007 |
| TST-RDR-031 | db, e2e | Preferences: a user reads and replaces only their own `preferences` row; another user is denied; the values apply after sign-in on a second device; invalid values give `validation_failed` | REQ-RDR-026 | INV-RDR-026 |
