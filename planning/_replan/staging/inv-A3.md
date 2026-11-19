# Staged invariants A3 (CAT, RDR, ING, WEB) - merge into invariants-register.md

Status: DRAFT

## Catalog

- **INV-CAT-001** · catalog · by: type, model · Version state changes only along draft→in_review→published→archived plus soft delete; approval needs `manage_catalog`; a failed or unapproved build never creates a visible version.
- **INV-CAT-002** · catalog · by: model, prop · Every reader-facing query is scoped to published, non-deleted versions; the reader view type has no source-URL field.
- **INV-CAT-003** · catalog · by: db, prop · A tombstoned book is excluded from every read path by one shared repository filter, emits `book.unpublished`, and its files, shelf entries and Kindle requests no longer resolve.
- **INV-CAT-004** · catalog · by: db · Published ⇒ ∃ credit with role ∈ {writer, translator, editor, compiler}.
- **INV-CAT-005** · catalog · by: db, prop · `id` never changes; `slug` is unique; every former slug maps to its book; a catalog code is immutable, sequence-issued and never used for authorization.
- **INV-CAT-006** · catalog · by: db, prop · A manual edit wins over any source value; an update with a stale revision is rejected, never merged; metadata history keeps every version; source-owned and operator-owned fields are separate columns; zero and null are distinct.
- **INV-CAT-007** · catalog · by: db, prop · Credits reference agents by id; two agents differ only by id; merge preserves all credits and records an undo; a contributor facet filters one (role, name) credit row.
- **INV-CAT-008** · catalog · by: prop · `count(browse facet) = |results(same filter)|` for the same snapshot.
- **INV-CAT-009** · catalog · by: prop · Every search result is a published, non-deleted book.
- **INV-CAT-010** · catalog · by: prop, unit · `normalize(normalize(x)) = normalize(x)`; query and index use the same function version.
- **INV-CAT-011** · catalog · by: prop · Alias lookup is symmetric between a Bengali form and its registered Latin forms.
- **INV-CAT-012** · catalog · by: type, model · The public search index and preview endpoint are built only from `PublicDocument` values, which cannot hold non-preview text or user-private data.
- **INV-CAT-013** · catalog · by: prop, drill · Rebuilding the full-text index from the book tables gives the same results as incremental maintenance.
- **INV-CAT-014** · catalog · by: prop · The Bengali collation comparator is a total preorder (reflexive, transitive, total) and sorting is stable.
- **INV-CAT-015** · catalog · by: prop · Facet semantics: AND across facets, OR within a facet; counts equal result sizes.
- **INV-CAT-016** · catalog · by: prop · Under a fixed snapshot, concatenated pages equal the full ordered result list; page size and window are bounded.
- **INV-CAT-017** · catalog · by: fuzz, review · Public endpoints bound query length and result window and expose only public data.
- **INV-CAT-018** · catalog · by: prop · MRR@10 and recall@20 on the judged query set meet the thresholds before an analyzer change merges.
- **INV-CAT-019** · catalog · by: type · The preview endpoint returns only the stored `PreviewArtifact`; no code path converts a full document to it.
- **INV-CAT-020** · catalog · by: type, db · Asset files are write-once and sha256-addressed on the catalog volume; no file is reachable except through a catalog handler that checked scope and state.
- **INV-CAT-021** · catalog · by: db, model · A version row and its assets are write-once; the current-version pointer references exactly one complete version; the previous version's files are kept until the next is approved.
- **INV-CAT-022** · catalog · by: model, db · `POST /internal/books/{id}/versions` is idempotent on the build identity; artifacts and version row commit atomically; the new version is in_review.
- **INV-CAT-023** · catalog · by: type, prop · A download handler takes a verified `download` decision for a published version; ranged responses concatenate to the original bytes.
- **INV-CAT-024** · catalog · by: model, prop · Each publication state change writes its event in the same transaction; events are readable by cursor and consumers are idempotent.
- **INV-CAT-025** · catalog · by: db · (user, book) is unique in the shelf; a shelf entry never grants access; mutation requires `browse`, a session and a non-demo account.
- **INV-CAT-026** · catalog · by: prop · `apply(save(filter)) = filter`; a duplicate save is a typed 409.
- **INV-CAT-027** · catalog · by: prop · Export rows = list rows for the same filter and snapshot; no exported cell starts with `=`, `+`, `-`, `@` unescaped.
- **INV-CAT-028** · catalog · by: unit, review · A stored cover passed byte-level image validation from an allow-listed host; a generated cover contains title and author text with no tofu glyphs.
- **INV-CAT-029** · catalog · by: model · A `kindle.requested` event exists only after a `kindle` decision for a published version within size and rate limits; delivery status is stored per request.
- **INV-CAT-030** · catalog · by: unit · Uniqueness and state conflicts return typed 409/422 with stable code and field path; absent or deleted resources return 404.
- **INV-CAT-031** · catalog · by: db · Every state-changing command writes an append-only audit row with the actor in the same transaction.
- **INV-CAT-032** · catalog · by: prop · A GET handler performs no write to catalog state.

## Reader

- **INV-RDR-001** · reader · by: model, prop · A reading copy is built at most once per `(book_id, version)`; building is idempotent under redelivered `book.published`.
- **INV-RDR-002** · reader · by: prop · `parse(epub, parser_version)` is a pure function; two runs are byte-identical.
- **INV-RDR-003** · reader · by: type, fuzz · Stored HTML values have type `SafeHtml` (allow-list sanitizer); the sanitizer is idempotent; stored output has no script, inline handler, external load or unknown URL scheme.
- **INV-RDR-004** · reader · by: db, drill · Only a Ready copy of a published, non-deleted book is served; a copy is replaced atomically by a newer Ready copy; annotations are never deleted by a copy change.
- **INV-RDR-005** · reader · by: model · A ticket is issued only after a `read` Allow for a published version and the read-once rule; a shelf entry never produces an Allow.
- **INV-RDR-006** · reader · by: type · Book handlers take `Verified<ReadingTicket>`; its only constructor is `verify(ticket, key, now, request)`; a ticket is bound to user, book and version, expires within 15 minutes and is never read from a URL.
- **INV-RDR-007** · reader · by: model · Redemption re-checks active state, grant version and published state; `user.disabled`, `grant.changed` and `book.unpublished` make earlier tickets unredeemable.
- **INV-RDR-008** · reader · by: type · The reader has no route that returns the EPUB file or a single chapter; the book route returns the whole package.
- **INV-RDR-009** · reader · by: model, db · A read-once entitlement is consumed by one atomic insert on successful redemption only; concurrent redemptions consume it once; a missing copy consumes nothing.
- **INV-RDR-010** · reader · by: review · Reader records and UI text state the no-DRM limit and list the controls (entitlement, short tickets, rate limits, audit).
- **INV-RDR-011** · reader · by: db · Each ticket issue and redemption writes one append-only audit row; per-user rate limits apply to both.
- **INV-RDR-012** · reader · by: model, db · Progress revision strictly increases; an update with revision ≤ stored is a no-op; percent is within 0..100; locator length bound exceeds the maximum anchor length.
- **INV-RDR-013** · reader · by: db · (user, book, location) bookmarks are unique; a duplicate create returns the existing row.
- **INV-RDR-014** · reader · by: unit · Annotation create, edit, recolour and delete are reachable by keyboard; colours come from one defined set.
- **INV-RDR-015** · reader · by: prop · Re-anchoring places an annotation or marks it Orphaned; resolving an anchor returns a location or Orphaned, never an error; no annotation is deleted by a version change.
- **INV-RDR-016** · reader · by: type, db · Every personal-data query is parameterized by the user id from the verified identity header; row-level policy forbids other owners; these routes also require the session.
- **INV-RDR-017** · reader · by: unit · The JSON export contains all and only the owner's reading data; admin deletion of an account removes all of it.
- **INV-RDR-018** · reader · by: e2e · A notes deep link resolves to a location or the orphan state.
- **INV-RDR-019** · reader · by: unit · Markdown and JSON note exports contain exactly the owner's notes and highlights.
- **INV-RDR-020** · reader · by: e2e, review · Reader theme state has one owner; theming uses CSS variables only and sets no `!important` override on book content.
- **INV-RDR-021** · reader · by: e2e, review · Every reader action has a keyboard path; zoom shortcuts are not intercepted; targets ≥ 48 px.
- **INV-RDR-022** · reader · by: type, e2e · Reader state is an exhaustive enum covering building, forbidden, not found, expired ticket, offline and error with a retry action.
- **INV-RDR-023** · reader · by: unit · Search results are positions inside the reading copy of the opened book version.
- **INV-RDR-024** · reader · by: model, prop · Event cursors advance only after the event is applied; redelivered events change nothing.
- **INV-RDR-025** · reader · by: prop · A GET handler performs no write to reader state other than the audit row; package responses carry the CSP and nosniff headers.

## Ingestion

- **INV-ING-001** · ingestion · by: model, db · A request's execution status and domain outcome are separate fields; `created` ⇒ a book candidate exists (constraint); every terminal path restores the owning entity's state.
- **INV-ING-002** · ingestion · by: db, prop · Sync writes only source-owned columns; workflow state is never written by sync; an empty or failed fetch resolves nothing.
- **INV-ING-003** · ingestion · by: model, prop · Mirror sync is idempotent; sync phases follow a typed state machine with one transition function per edge.
- **INV-ING-004** · ingestion · by: model, prop, db · Claim is `FOR UPDATE SKIP LOCKED` with a heartbeat lease; ≤ 1 active job per request; lease expiry only moves Running→Queued; completion is idempotent.
- **INV-ING-005** · ingestion · by: type, e2e · No handler runs pipeline work; production code contains no test-detection branches.
- **INV-ING-006** · ingestion · by: type · Failure type ∈ {retryable, rate_limited, auth_required, permanent}; retry is decided by that value, never by message text.
- **INV-ING-007** · ingestion · by: model, prop · Every step is idempotent; the cancel flag is checked before each page fetch; each job has a page budget and an error budget.
- **INV-ING-008** · ingestion · by: model, unit · An action runs only from a state in its allowed-source-state table; bulk actions return per-item results and are bounded.
- **INV-ING-009** · ingestion · by: type · Every route declares a scope or fails startup; the actor is recorded on every command; no endpoint authorizes by possession of an id.
- **INV-ING-010** · ingestion · by: type · The acquisition client exposes only `get`; fetches are limited to allow-listed hosts; TLS verification cannot be disabled.
- **INV-ING-011** · ingestion · by: type, unit · The source cookie is read from a secret file; only its status and expiry are stored and never appear in argv, logs or responses.
- **INV-ING-012** · ingestion · by: db, drill · Scrape cache files exist only for non-terminal requests or within 30 days; no cache content is stored in a request row.
- **INV-ING-013** · ingestion · by: db, prop · The curated document is write-once per run; derived data carries (source hash, ruleset version) and is regenerable.
- **INV-ING-014** · ingestion · by: prop · Σ blocks(input) = Σ blocks(output) + Σ blocks(dropped with reason), as multisets of `BlockId`.
- **INV-ING-015** · ingestion · by: type, prop · TOC, nav and NCX are rendered from one `SectionTree`; reading order is a bijection leaves→1..n.
- **INV-ING-016** · ingestion · by: prop · With a source TOC, the section tree ≅ the source TOC (same shape and titles up to normalization).
- **INV-ING-017** · ingestion · by: prop · Every inferred chapter boundary has ≥ 1 evidence item.
- **INV-ING-018** · ingestion · by: model, prop · Build ⇒ ∀ TOC leaves: fetched ∨ empty-at-source(recorded); one threshold constant is used by classification and build; a limit-caused omission is a validation error.
- **INV-ING-019** · ingestion · by: prop · Auto-publication of an entity requires evidence and confidence ≥ the ruleset threshold.
- **INV-ING-020** · ingestion · by: prop · No normalized text block appears in two output sections of different types.
- **INV-ING-021** · ingestion · by: unit · Label, digit and key language equals the stored book language for all generated text.
- **INV-ING-022** · ingestion · by: unit, prop · One normalization function is the only entry to matching; rule tables are versioned and match at token boundaries.
- **INV-ING-023** · ingestion · by: prop · Duplicate outcome ∈ {exact_duplicate, new_edition, new_work, needs_review} and is a pure function of (normalized title key, author, category, edition); no outcome merges automatically.
- **INV-ING-024** · ingestion · by: type, fuzz · Template escaping is always on; chapter HTML has type `SafeHtml`; `build(curated document, builder_version)` is pure and byte-identical across runs.
- **INV-ING-025** · ingestion · by: prop, review · Every `<img>` and font reference in the XHTML resolves to a packaged file; the OPF has identifier derived from (book id, version), title, language and creator roles; nav and NCX both exist.
- **INV-ING-026** · ingestion · by: prop, review · A candidate exists only after XML well-formedness, structure audit and epubcheck report 0 errors; nav, NCX and TOC links = tree leaves ∪ parents.
- **INV-ING-027** · ingestion · by: type, prop · A stored cover is image-validated by bytes from an allow-listed host; the generated cover contains title and author text.
- **INV-ING-028** · ingestion · by: type, prop · The preview artifact is built only from the allow-list type; its text length ≤ N from the book's setting.
- **INV-ING-029** · ingestion · by: model · Effective publish count per (book, build identity) = 1; the version is in_review until approval; a failed build creates no version.
- **INV-ING-030** · ingestion · by: prop, review · A ruleset is promotable only if every gold metric ≥ the current metric; reprocessing never edits a published version.
- **INV-ING-031** · ingestion · by: prop · Manual intake documents pass the same validator as scraped ones.
- **INV-ING-032** · ingestion · by: model, e2e · Each console event has a monotonic id from the outbox; a reconnect with `Last-Event-ID` receives all later events or a versioned snapshot.
- **INV-ING-033** · ingestion · by: model, unit · At most one run is claimed per `next_due` slot (lock); schedule input is validated; duplicate and needs_review outcomes are never auto-retried.
- **INV-ING-034** · ingestion · by: db, drill · Expired raw pages and attempt logs are removed by retention jobs; previous-version files are kept until the next version is approved.
- **INV-ING-035** · ingestion · by: db · Every state change and operator command writes an append-only audit row with the actor in the same transaction; log lines carry the job id.

## Web

- **INV-WEB-001** · web · by: type · Page state is an exhaustive type; a missing arm does not compile.
- **INV-WEB-002** · web · by: unit, e2e · An HTTP 401 redirects to sign-in and clears the session; an HTTP 403 keeps the session and shows the forbidden state.
- **INV-WEB-003** · web · by: unit, e2e · Navigation, route guards and component visibility derive from the server-published scope set only.
- **INV-WEB-004** · web · by: e2e · Every internal link resolves to a route in the typed route table.
- **INV-WEB-005** · web · by: review, e2e · Every UI component resolves to an Angular Material/CDK component or a documented `shared/` composition; visual snapshots match the approved M3 themes.
- **INV-WEB-006** · web · by: e2e, review · No gradient, blur or entrance animation exists in the stylesheet set; error colour is used only for failure or destruction.
- **INV-WEB-007** · web · by: e2e, review · A single token set defines both themes; "System" resolves to a concrete light or dark value before first paint; no component overrides a token per theme.
- **INV-WEB-008** · web · by: e2e · Contrast checks pass in light and dark; every colour used comes from a theme token.
- **INV-WEB-009** · web · by: e2e · The navigation component is bottom bar, rail and drawer at compact, medium and expanded; no horizontal overflow at 360, 768, 1280 and 1920 px; rotation keeps state.
- **INV-WEB-010** · web · by: e2e, review · Automated accessibility scan reports zero serious or critical violations; interactive targets ≥ 48 px.
- **INV-WEB-011** · web · by: unit · `bn` and `en` catalogs have identical key sets.
- **INV-WEB-012** · web · by: review · The typography checklist passes on a Bengali sample set.
- **INV-WEB-013** · web · by: type, static · Regenerating the client from the Rust schema produces no diff; strict compilation and lint rules forbidding `any`, `!` and casts pass.
- **INV-WEB-014** · web · by: review · The navigation entries equal the screen list for the user's scopes.
- **INV-WEB-015** · web · by: e2e · Library filters and sort round-trip through the URL; anonymous users cannot reach shelf or Kindle actions.
- **INV-WEB-016** · web · by: e2e · Files-tab actions render only when the corresponding scope is present.
- **INV-WEB-017** · web · by: e2e · Displayed job and request state equals the last server-confirmed state; every bulk command shows per-item results.
- **INV-WEB-018** · web · by: e2e · A grant change in the UI is one atomic request; the user detail drawer lists all of that user's grants.
- **INV-WEB-019** · web · by: e2e · Changing TOTP requires a successful re-authentication in the same flow.
- **INV-WEB-020** · web · by: unit, e2e · A mutation performs no preliminary GET; the client sends no periodic health request.
- **INV-WEB-021** · web · by: type, e2e · The reading ticket value is held only in memory and never appears in a URL, storage or log.
- **INV-WEB-022** · web · by: review, e2e · Public page HTML has title, canonical and meta tags with metadata only; preview text carries `noindex`.
- **INV-WEB-023** · web · by: unit, e2e · No test reads source files as text; mocks derive from the generated schema.
