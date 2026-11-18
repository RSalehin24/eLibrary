# Invariants register

Status: DRAFT

An invariant is a statement that must hold in **every reachable state**. Each has an
enforcement mechanism (`by:`) — the strongest one that applies:

`type` compile-time · `db` database constraint · `model` TLA+/Alloy · `prop` property/model-based test ·
`gold` gold-corpus metric · `fuzz` fuzzing · `review` checklist · `drill` operational drill

Line format: `INV-ID · owner · by: <mechanisms> · statement`

Design basis: five services and no gateway ([ADR-0020](../04-architecture/adr/0020-five-services-no-gateway.md)). INV ids are stable and keep their prefixes (`ACC`, `CON`, `LIB`, `GWY`) although those services were merged; the `owner` column names the current owner. Obsolete invariants are marked RETIRED in place and keep their id. Models edited for the new design but not yet re-checked are listed in [coverage](formal-models/coverage.md).

## Identity

- **INV-IDN-001** · identity · by: model, type · No account is Active without either consuming a valid invite link or being the seeded first admin.
- **INV-IDN-002** · identity · by: model, db · A link token is consumed at most once and never after its expiry or after a newer link for the same purpose was issued.
- **INV-IDN-003** · identity · by: type · A value of type `Secret<T>` cannot be formatted, serialized to logs, or compared in non-constant time.
- **INV-IDN-004** · identity · by: model, type · A `Session<Authenticated>` can only be constructed from `PasswordOk` plus `TotpOk` when the account requires TOTP.
- **INV-IDN-005** · identity · by: model, db · After revocation, a session token authenticates nothing; token storage holds only hashes.
- **INV-IDN-006** · identity · by: prop · The response to a login/reset attempt for an unknown identifier is indistinguishable (status, body shape, timing bucket) from a known one.
- **INV-IDN-007** · identity · by: type · A `KindleEmail` is a syntactically valid address; an account holds at most 5.
- **INV-IDN-008** · identity · by: model, type · Account status changes only along Invited→Active⇄Suspended→Disabled.

- **INV-IDN-009** · identity · by: model, prop · For an account, accepted TOTP time steps are strictly increasing: a code is accepted only if its step > `last_accepted_step`.

## Authorization (identity; formerly the access service)

- **INV-ACC-001** · identity · by: model, prop · A request with no session is allowed only on declared `public` routes: sign-in, invite and reset flows, demo sign-in, catalog public browse/search metadata and published preview text.
- **INV-ACC-002** · identity · by: model, prop · `check(read)` = Allow ⇒ the user is Active AND a live explicit grant row for scope `read` (global or this book) exists AND the book version is Published. Ownership, shelf membership ("My Books") and role names grant nothing by themselves; there is no wildcard role.
- **INV-ACC-003** · identity · by: type, model · The decision function is total and deny by default; every `/api/*` route declares exactly one scope in code, and protected operations accept only a `Decision::Allow` witness they cannot construct themselves.
- **INV-ACC-004** · identity · by: model, prop · A grant with `expires_at ≤ now` or `revoked_at ≤ now` never contributes to Allow.
- **INV-ACC-005** · identity · by: model, prop · For grant sets G⊆G′ (same facts, excluding read-once consumption), Allow(G) ⇒ Allow(G′).
- **INV-ACC-006** · identity · by: model, prop · For (user, book) under `read_once`, consumed uses ≤ 1 (PK insert); a use is consumed only when a reading ticket is successfully redeemed for the book, never at open, never when the copy is missing or building; reloading with the same ticket does not consume again.
- **INV-ACC-007** · identity · by: model · For a demo session, every mutating route and every `download`/`kindle`/management scope decides Deny.
- **INV-ACC-008** · reader · by: type, prop, fuzz · A reading ticket verifies iff signature valid ∧ not expired ∧ (user, book, version) match the request ∧ the user's grant version is current; TTL ≤ 900 s; it is accepted from a header or body only, never from a URL.
- **INV-ACC-009** · identity · by: model · Management scopes (`manage_users`, `manage_catalog`, `operate`) are allowed only when the session is TOTP-complete if the account has TOTP enabled.
- **INV-ACC-010** · identity · by: prop · `check(f, G) = check(f, permute(G))` for all permutations of the grant set.
- **INV-ACC-011** · identity · by: db · A grant, role, status or demo-set mutation, its audit row and its event commit in one transaction or none commits.
- **INV-ACC-012** · identity · by: model · For a non-Published book version, `check(browse|preview|read|download|kindle)` is Deny for every user; only `manage_catalog` sees draft, in-review and archived metadata.

## Catalog & discovery

- **INV-CAT-001** · catalog · by: type, model · Book version state changes only along Draft→InReview→Published→Archived, plus soft delete; approval needs `manage_catalog`; a failed build never creates a visible version.
- **INV-CAT-002** · catalog · by: db · Published ⇒ ∃ credit with role ∈ {writer, translator, editor, compiler}.
- **INV-CAT-003** · catalog · by: db · `id` and `code` never change; `slug` unique; every former slug maps to its book.
- **INV-CAT-004** · catalog · by: db, prop · A manual edit wins over any source value; an update with a stale revision is rejected, never merged silently; metadata history keeps every version.
- **INV-CAT-005** · catalog · by: db · Credits reference agents by id; two agents are distinguishable only by id; merge preserves all credits and records an undo.
- **INV-CAT-006** · catalog · by: prop · Duplicate classification outcome ∈ {ExactDuplicate, NewEdition, NewTranslation, NewWork, NeedsReview} and is a pure function of the normalized key tuple.
- **INV-CAT-007** · catalog · by: prop · `count(facet) = |results(facet filter)|` for the same snapshot.
- **INV-CAT-008** · catalog · by: prop · Export rows = list rows for the same filter and snapshot.
- **INV-CAT-009** · catalog · by: db · (Only if D-01 keeps inventory) inventory rows reference a book and have non-negative price.
- **INV-DSC-001** · catalog · by: prop · Every search result is a Published book.
- **INV-DSC-002** · catalog · by: prop · `normalize(normalize(x)) = normalize(x)`; query and index use the same function version.
- **INV-DSC-003** · catalog · by: gold · Alias lookup is symmetric between a Bengali form and its registered Latin forms.
- **INV-DSC-004** · catalog · by: model, type · The public search index and preview endpoint are built only from `PublicDocument` values, a type that cannot hold non-preview text.
- **INV-DSC-005** · catalog · by: prop, drill · Rebuilding the PostgreSQL full-text index from the book tables gives the same results as incremental maintenance.
- **INV-DSC-006** · catalog · by: prop · Bengali collation comparator is a total preorder (reflexive, transitive, total).
- **INV-DSC-007** · catalog · by: prop · Facet semantics: AND across facets, OR within.
- **INV-DSC-008** · catalog · by: prop · Under a fixed snapshot, concatenated pages = full ordered result list.
- **INV-DSC-009** · catalog · by: gold · MRR@10 and recall@20 on the judged query set meet thresholds.

## Content (catalog assets, reader copies, ingestion builder)

- **INV-CON-001** · catalog · by: db, model · A book version row and its asset files are write-once; the current-version pointer references exactly one complete version; the previous published version's files are kept until the next one is approved.
- **INV-CON-002** · ingestion · by: prop · `build(curated document, builder_version)` is a pure function; two builds are byte-identical.
- **INV-CON-003** · catalog · by: type · The public preview endpoint returns `PreviewArtifact`; no code path converts a full document to it without the allow-list filter.
- **INV-CON-004** · reader · by: type · Whole-book handlers take `Verified<ReadingTicket>`; the only constructor is `verify(ticket, key, now, request)`. The reader never serves the EPUB file and has no per-chapter content route.
- **INV-CON-005** · catalog · by: prop · Range/streamed download responses concatenate to the original bytes.
- **INV-CON-006** · reader · by: db, drill · A reading copy is replaced only atomically by a newer `Ready` copy; `Building` and `Failed` copies are never served; annotations are never deleted by a copy change.
- **INV-CON-007** · ingestion · by: prop, gold · EPUB nav document, NCX and in-book TOC links = tree leaves ∪ parents; epubcheck reports 0 errors; XML well-formedness and structure audit pass before a candidate can be published.
- **INV-CON-008** · catalog · by: gold, review · Generated cover includes the title and author text with no tofu glyphs.
- **INV-CON-009** · reader · by: type, fuzz · Stored HTML values have type `SafeHtml` (reader allow-list sanitizer; builder escaping on); the sanitizer is idempotent.

## Reader state and shelves (formerly library)

- **INV-LIB-001** · reader · by: model, db · Progress revision strictly increases; an update with revision ≤ stored is a no-op.
- **INV-LIB-002** · reader · by: prop · Re-anchoring (client-side, by quote) places an annotation or reports it unplaced; no annotation is deleted by a version change.
- **INV-LIB-003** · reader · by: type, db · Every personal-data query is parameterized by the user id from the verified identity header; row-level policy forbids other owners.
- **INV-LIB-004** · catalog · by: db · (user, book) unique in shelf; a shelf entry never grants access.
- **INV-LIB-005** · reader · by: prop · Resolving an anchor returns a location or `Orphaned`, never an error.
- **INV-LIB-006** · catalog · by: prop · `apply(save(filter)) = filter` (applies only if saved filters are kept).
- **INV-LIB-007** · reader · by: unit · Export (JSON, owner only) contains all and only the owner's reading data.
- **INV-LIB-008** · reader · by: review · RETIRED (ADR-0023): the reading-session model is replaced by tickets; the multi-device read-once race is covered by INV-ACC-006 (atomic PK insert) and the ReadOnce model.

## Ingestion

- **INV-ING-001** · ingestion · by: db, prop · A scrape cache file and the curated document are write-once per run; derived data carries (source hash, ruleset version); raw pages are kept 30 days.
- **INV-ING-002** · ingestion · by: prop, gold · Σ blocks(input) = Σ blocks(output) + Σ blocks(dropped with reason), as multisets of `BlockId`.
- **INV-ING-003** · ingestion · by: type, prop · TOC and nav are rendered from one `SectionTree`; reading order is a bijection leaves→1..n.
- **INV-ING-004** · ingestion · by: prop, gold · With a source TOC, section tree ≅ source TOC (same shape and titles up to normalization).
- **INV-ING-005** · ingestion · by: gold · Every inferred chapter boundary has ≥ 1 evidence item.
- **INV-ING-006** · ingestion · by: model, prop · Publish ⇒ ∀ TOC leaves: fetched ∨ empty-at-source(recorded).
- **INV-ING-007** · ingestion · by: prop · Auto-publish ⇒ all entities have evidence and confidence ≥ ruleset threshold.
- **INV-ING-008** · ingestion · by: prop, gold · No normalized text block appears in two output sections of different types.
- **INV-ING-009** · ingestion · by: gold · Label language = book language for all generated labels.
- **INV-ING-010** · ingestion · by: model, prop · Job lifecycle obeys the state machine; claim is `FOR UPDATE SKIP LOCKED` with a heartbeat lease; ≤ 1 active job per request/source URL; lease expiry only moves Running→Queued; retry vs permanent failure is decided by the typed error, never by text.
- **INV-ING-011** · ingestion · by: gold · A ruleset is promotable only if every gold metric ≥ the current ruleset's metric − ε(0).
- **INV-ING-012** · ingestion · by: type · The acquisition client only exposes `get`; no form submission is representable (D-03); the source cookie is read from a secret file and only its status and expiry are stored.
- **INV-ING-013** · ingestion · by: gold · Manual intake canonical documents pass the same validator.
- **INV-ING-014** · ingestion · by: prop · Source mirror sync is idempotent (no extra jobs) and never overwrites local workflow state.
- **INV-ING-015** · ingestion · by: prop, gold · Duplicate policy matches the five-case decision table on all labeled pairs.
- **INV-ING-016** · ingestion · by: model · Effective publish count per (book, version) = 1: catalog `POST /internal/books/{id}/versions` is idempotent on the build identity, and a retry after a crash creates no second version.

## Notify, Edge (Caddy; ids keep the GWY prefix), Web

- **INV-NTF-001** · notify · by: model, prop · Per (event id, kind) at most one successful send is recorded; the consumer cursor and the effect commit together.
- **INV-NTF-002** · notify · by: prop · Kindle send ⇒ `kindle` check Allow at catalog ∧ address ∈ the user's addresses ∧ size ≤ limit; delivery status is reported back.
- **INV-NTF-003** · notify · by: unit · Every template key exists in both languages.
- **INV-NTF-004** · notify · by: type · Mail payloads use `Secret`-wrapped link types.
- **INV-GWY-001** · edge · by: review, e2e · RENAMED scope (no gateway; Caddy): the routes exposed by Caddy equal the public route table; `/internal/*` and file volumes are never routed; every `/api/*` route has a declared scope or `public`.
- **INV-GWY-002** · identity · by: e2e · A cookie-authenticated mutation without a valid CSRF token/Origin check is rejected (enforced in `/internal/authorize` on the forwarded method).
- **INV-GWY-003** · edge · by: e2e · Every response and log line contains the request id assigned by Caddy.
- **INV-GWY-004** · edge · by: e2e · Required security headers are present on every response (Caddy), and client-supplied identity headers are stripped before forwarding.
- **INV-WEB-001** · web · by: type · Page state is an exhaustive enum; `match` without all arms does not compile.
- **INV-WEB-002** · web · by: e2e · All internal `href`s resolve to a route in the route map.
- **INV-WEB-003** · web · by: e2e, review · Automated a11y scan reports zero serious/critical violations.
- **INV-WEB-004** · web · by: review · Typography checklist passes on a Bengali sample set.
- **INV-WEB-005** · web · by: e2e · No horizontal overflow at 360 (mobile), 768 (tablet), 1280 (desktop), 1920 px.
- **INV-WEB-006** · web · by: e2e · Every color used comes from a theme token.
- **INV-WEB-007** · web · by: e2e · Public page HTML contains title, canonical, OG tags and meaningful content without JS.
- **INV-WEB-008** · web · by: review · Admin navigation matches the workspace list.
- **INV-WEB-009** · web · by: unit · `bn` and `en` catalogs have identical key sets.

- **INV-WEB-010** · web · by: review, e2e · Every UI component resolves to an Angular Material/CDK component or a documented `shared/` composition; visual snapshots match the approved Material 3 themes.
- **INV-WEB-011** · web · by: type, e2e · Regenerating the TypeScript client from the Rust schema produces no diff; compilation with strict flags passes; lint rules forbidding `any`/`!`/casts pass.
- **INV-WEB-012** · web · by: e2e, review · At 360, 768 and 1280 px the navigation component is bar, rail and drawer respectively, all interactive targets are ≥ 48 px, and Playwright journeys (browse, read, annotate, admin review) pass at all three; rotating keeps position and form state.

## Platform & Migration

- **INV-PLT-001** · all · by: unit, e2e · `main` returns `Err(StartupError)` rather than serving when preconditions fail, including a route without a declared scope, a secret file broader than 0400, or an unreadable key (fail closed).
- **INV-PLT-002** · all · by: type · Request/response/event types are imported from `contracts-*`; no service defines its own wire type.
- **INV-PLT-003** · all · by: prop · Applying the same mutation with the same key twice leaves state as after once.
- **INV-PLT-004** · all · by: fuzz, review · `clippy::unwrap_used`, `expect_used`, `indexing_slicing`, `panic` are `deny` in non-test code.
- **INV-PLT-005** · all · by: prop · Each bound in the limits table is enforced and tested at limit±1.
- **INV-PLT-006** · all · by: db · Audit table has INSERT-only privileges for service roles.
- **INV-PLT-007** · all · by: e2e · Every service exposes `/health/live`, `/health/ready`, `/metrics`.
- **INV-PLT-008** · all · by: drill · Restore from backup reproduces a consistent system within RTO.
- **INV-PLT-009** · all · by: model, prop · A producer's `events` row and its state change commit atomically; a consumer pulls with a stored cursor, applies each event id at most once and advances the cursor in the same transaction; a lost cursor resynchronizes from the owner's listing.
- **INV-PLT-010** · all · by: type · No `SystemTime::now()` outside the `SystemClock` implementation.
- **INV-PLT-011** · all · by: type, review · No function exceeds the configured length/parameter/nesting thresholds without a dated waiver; bool flag parameters do not appear in signatures.
- **INV-PLT-012** · all · by: review, drill · Every dependency in a lockfile has an `APPROVED` register entry; the register has no entry without a lockfile reason or a planned phase.
- **INV-PLT-013** · all · by: type · `missing_docs` is denied in `contracts-*` and `domain-*`; doctests compile and pass.
- **INV-PLT-014** · all · by: e2e, review · `compose config` shows nine containers (caddy, web, identity, catalog, reader, ingestion-api, ingestion-worker, notify, postgres); only Caddy publishes ports; each service role connects only to its own database; each container is non-root with a read-only root filesystem and resource limits; no Redis, Celery or broker.
- **INV-MIG-001** · migration · by: drill · Reconciliation diff = ∅ after accounting for documented exclusions.
- **INV-MIG-002** · migration · by: e2e · Every legacy slug and code resolves (200 or 301).
- **INV-MIG-003** · migration · by: unit · A legacy PBKDF2 hash verifies; on success the stored hash becomes Argon2id.
- **INV-MIG-004** · migration · by: drill · Rollback rehearsal restores legacy as primary with data parity.
