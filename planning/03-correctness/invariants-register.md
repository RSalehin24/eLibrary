# Invariants register

Status: DRAFT

An invariant is a statement that must hold in **every reachable state**. Each has an
enforcement mechanism (`by:`) - the strongest one that applies:

`type` compile-time · `db` database constraint · `model` TLA+/Alloy · `prop` property/model-based test ·
`gold` gold-corpus metric · `fuzz` fuzzing · `review` checklist · `drill` operational drill ·
`e2e` end-to-end test · `unit` unit test · `metric` measured target (load/latency/size) · `static` static analysis or config lint

Line format: `INV-ID · owner · by: <mechanisms> · statement`

Design basis: six Rust services (gateway, identity, catalog, reader, ingestion, notify), D-31; ids are `INV-<PREFIX>-NNN` with the prefixes IDN, GWY, CAT, RDR, ING, NTF, WEB, PLT, NFR. Rebuilt 2026-11-19 from the requirement files in `../02-requirements/`.

## Identity (incl. authorization)

- **INV-IDN-001** · identity · by: model, type · No account is Active without consuming a valid invite link or being the seeded first admin.
- **INV-IDN-002** · identity · by: model, db · A link token is consumed at most once and never after its expiry or after a newer link for the same account and purpose was issued.
- **INV-IDN-003** · identity · by: type · A value of type `Secret<T>` cannot be formatted, serialized to logs, or compared in non-constant time.
- **INV-IDN-004** · identity · by: model, type · A session of an account with required TOTP exists only after a valid second factor was accepted for it.
- **INV-IDN-005** · identity · by: model, db · The last accepted TOTP time step per account only increases.
- **INV-IDN-006** · identity · by: model, e2e · No TOTP disable or password change is applied without a fresh credential check in the same request.
- **INV-IDN-007** · identity · by: model, db · A revoked or expired session never yields an authorization Allow.
- **INV-IDN-008** · identity · by: prop, e2e · The response body, status and timing class of a reset or sign-in request do not depend on whether the account exists.
- **INV-IDN-009** · identity · by: model, db · Every stored status change is in the allowed transition relation.
- **INV-IDN-010** · identity · by: type, db · The set of scopes a subject holds is the union of its role scopes and its active grants; no value matches every scope; `operator` adds `operate` and `manage_catalog`, `admin` adds `manage_users` and `manage_catalog`, and neither role holds `download` or `read_once` (D-45).
- **INV-IDN-011** · identity · by: type, db · `preview` and `read` are distinct scopes (holding one never implies the other) and the default reader role holds both. Every grant row names a valid scope, a valid target for that scope and is unique among active rows for (user, scope, book).
- **INV-IDN-012** · identity · by: model, db · A grant or role change has actor != subject and an audit row committed in the same transaction; a batch grant request applies all of its items or none (D-54).
- **INV-IDN-013** · identity · by: model, type · If no explicit role scope or active grant matches, the decision is Deny.
- **INV-IDN-014** · identity · by: model, prop · An unauthenticated subject has no scope except the public set (catalog metadata browse, search, detail; sign-in, invite acceptance, password reset); preview text needs a session.
- **INV-IDN-015** · identity · by: model, prop · No decision depends on shelf, ownership or submission data.
- **INV-IDN-016** · identity · by: model, prop · For a non-`manage_catalog` subject, Allow on a book scope implies the book version is published and not deleted.
- **INV-IDN-017** · identity · by: model, prop · A grant with expires_at <= now, or revoked, contributes no scope.
- **INV-IDN-018** · identity · by: model, prop · decide(S + grant) >= decide(S) for every scope other than read_once.
- **INV-IDN-019** · identity · by: model, prop · decide is a pure function of (roles, grant set, subject state, book state, now).
- **INV-IDN-020** · identity · by: model, prop · Per (user, book) at most one ticket redemption is counted as an opening while read_once is the only read scope; every redemption is decided by an identity `verify` call at that moment, so a revoked, disabled or unpublished case is denied at once.
- **INV-IDN-021** · identity · by: type, prop, fuzz · A ticket verifies (through identity, at every redemption) only for its user, book, version, before its expiry and while its grant version equals the current one; tickets are stored only as hashes.
- **INV-IDN-022** · identity · by: model, prop · Redeeming a ticket twice yields the same result and one audit row of kind open.
- **INV-IDN-023** · identity · by: model, prop · Every committed user disable or grant change has exactly one event with a monotonically increasing cursor.
- **INV-IDN-024** · identity · by: type, e2e · The route table of a running service has no entry without a declared scope or `public`.
- **INV-IDN-025** · identity · by: model, e2e · A management Allow requires session.totp_done when the account requires TOTP.
- **INV-IDN-028** · identity · by: type · Every stored Kindle address parses as KindleEmail and a user has at most 5.
- **INV-IDN-029** · identity · by: db, e2e · Every security-relevant identity state change has an audit row in its transaction, and the audit table has no UPDATE or DELETE privilege; rows older than 1 year are removed only by the retention job.
- **INV-IDN-030** · identity · by: model, e2e · The capability set equals the scopes identity would Allow for the same subject.
- **INV-IDN-031** · identity · by: review, e2e · Account deletion leaves no user row, session, grant or Kindle address in identity.
- **INV-IDN-032** · identity · by: review, static · A production build contains no route or command that creates a user with a fixed credential.
- **INV-IDN-033** · identity · by: e2e, review, static · No account, route or credential exists that bypasses sign-in for an admin; `admin-reset` is a host command only (not reachable over HTTP), is audited, and the last active admin cannot be demoted or disabled and no admin changes themselves.
- **INV-IDN-034** · identity · by: type, unit, e2e, fuzz · A stored profile image has an allow-listed type, is within the size limit and passed re-encoding or validation; it is returned only to its owner or an admin, and never on an unauthenticated route.

## Gateway

- **INV-GWY-001** · gateway · by: review, e2e · The set of publicly reachable paths equals the route table; `/internal/*` is never routed.
- **INV-GWY-002** · gateway · by: e2e, type · A request reaches an upstream service only after an identity Allow or on a listed public route.
- **INV-GWY-003** · gateway · by: type, review · The public allow-list equals the list in the architecture brief and has no preview or reading route.
- **INV-GWY-004** · gateway · by: e2e, fuzz · No upstream request carries an identity header that identity did not produce.
- **INV-GWY-005** · gateway · by: e2e · A cookie-authenticated POST, PUT, PATCH or DELETE without a valid CSRF token is rejected before reaching a service.
- **INV-GWY-006** · gateway · by: e2e · The request id seen by a service equals the one in the gateway log and response.
- **INV-GWY-007** · gateway · by: prop, e2e · The rate-limit table never exceeds its configured size and a limited key cannot exceed its quota per window.
- **INV-GWY-008** · gateway · by: review, type · The gateway crate depends on no domain or storage crate.
- **INV-GWY-009** · gateway · by: e2e · Every response carries the required security headers.
- **INV-GWY-010** · gateway · by: prop, e2e · No request or response is buffered above the configured bound.
- **INV-GWY-011** · gateway · by: e2e, review · The gateway and Caddy configuration contain no file-system root for book assets.
- **INV-GWY-012** · gateway · by: e2e · Every gateway-generated error body is a typed envelope with a request id.
- **INV-GWY-013** · gateway · by: e2e · A stream is closed when its session is revoked or exceeds its idle bound.
- **INV-GWY-014** · gateway · by: e2e · Health endpoints are not reachable from the public edge.

## Catalog

- **INV-CAT-001** · catalog · by: type, model · A version is created `published` (no `draft` or `in_review` state, D-49, D-56) and changes state only to `archived` (reason `superseded` or `unpublished`) or back by restore, plus soft delete; unpublish, delete and restore need `manage_catalog`; a version is created only through the publish call or restore, and a failed build never creates a visible version.
- **INV-CAT-002** · catalog · by: model, prop · Every reader-facing query is scoped to published, non-deleted versions; the reader view type has no source-URL field.
- **INV-CAT-003** · catalog · by: db, prop · A tombstoned book is excluded from every read path by one shared repository filter, emits `book.unpublished`, and its files, shelf entries and Kindle requests no longer resolve.
- **INV-CAT-004** · catalog · by: db · Published ⇒ ∃ credit with role ∈ {writer, translator, editor, compiler}.
- **INV-CAT-005** · catalog · by: db, prop · `id` never changes; `slug` is unique; every former slug maps to its book; there is no catalog code (D-36).
- **INV-CAT-006** · catalog · by: db, prop · A manual edit wins over any source value; an update with a stale revision is rejected, never merged; metadata history keeps every version; source-owned and operator-owned fields are separate columns; zero and null are distinct.
- **INV-CAT-007** · catalog · by: db, prop · Credits reference agents by id; two agents differ only by id; merge preserves all credits and records an undo; a contributor facet filters one (role, name) credit row.
- **INV-CAT-008** · catalog · by: prop · `count(browse facet) = |results(same filter)|` for the same snapshot.
- **INV-CAT-009** · catalog · by: prop · Every search result is a published, non-deleted book.
- **INV-CAT-010** · catalog · by: prop, unit · `normalize(normalize(x)) = normalize(x)`; query and index use the same function version.
- **INV-CAT-011** · catalog · by: prop · Alias lookup is symmetric between a Bengali form and its registered Latin forms.
- **INV-CAT-012** · catalog · by: type, model · The public search index and preview endpoint are built only from `PublicDocument` values, which cannot hold preview text, non-preview text or user-private data.
- **INV-CAT-013** · catalog · by: prop, drill · Rebuilding the full-text index from the book tables gives the same results as incremental maintenance.
- **INV-CAT-014** · catalog · by: prop · The Bengali collation comparator is a total preorder (reflexive, transitive, total) and sorting is stable.
- **INV-CAT-015** · catalog · by: prop · Facet semantics: AND across facets, OR within a facet; counts equal result sizes.
- **INV-CAT-016** · catalog · by: prop · Under a fixed snapshot, concatenated pages equal the full ordered result list; page size and window are bounded.
- **INV-CAT-017** · catalog · by: fuzz, review · Public endpoints bound query length and result window and expose only public data.
- **INV-CAT-018** · catalog · by: prop · MRR@10 and recall@20 on the judged query set meet the thresholds before an analyzer change merges.
- **INV-CAT-019** · catalog · by: type · The preview endpoint requires a session with `preview` and returns only the stored `PreviewArtifact`; no code path converts a full document to it.
- **INV-CAT-020** · catalog · by: type, db · Asset files are write-once and sha256-addressed on the catalog volume; no file is reachable except through a catalog handler that checked scope and state.
- **INV-CAT-021** · catalog · by: db, model · A version row and its assets are write-once; the current-version pointer references exactly one complete version; the previous version's files are kept until the next is published.
- **INV-CAT-022** · catalog · by: model, db · `POST /internal/books/{id}/versions` is idempotent on the build identity; artifacts and version row commit atomically; the new version is published in the same transaction (D-49).
- **INV-CAT-023** · catalog · by: type, prop · A download handler takes a verified `download` decision for a published version; ranged responses concatenate to the original bytes.
- **INV-CAT-024** · catalog · by: model, prop · Each publication state change writes its event in the same transaction; events are readable by cursor and consumers are idempotent.
- **INV-CAT-025** · catalog · by: db · (user, book) is unique in the shelf; a shelf entry never grants access; mutation requires `browse`, a session and a session.
- **INV-CAT-026** · catalog · by: prop · `apply(save(filter)) = filter`; a duplicate save is a typed 409.
- **INV-CAT-027** · catalog · by: prop · Export rows = list rows for the same filter and snapshot; no exported cell starts with `=`, `+`, `-`, `@` unescaped.
- **INV-CAT-028** · catalog · by: unit, review · A stored cover passed byte-level image validation from an allow-listed host; a generated cover contains title and author text with no tofu glyphs.
- **INV-CAT-029** · catalog · by: model · A `kindle.requested` event exists only after a `kindle` decision for a published version within size and rate limits; delivery status is stored per request.
- **INV-CAT-030** · catalog · by: unit · Uniqueness and state conflicts return typed 409/422 with stable code and field path; absent or deleted resources return 404.
- **INV-CAT-031** · catalog · by: db · Every state-changing command (and every EPUB download) writes an append-only audit row with the actor in the same transaction.
- **INV-CAT-032** · catalog · by: prop · A GET handler performs no write to catalog state.
- **INV-CAT-033** · catalog · by: db, prop, type · A saved filter belongs to exactly one user and is readable and changeable only by that user; each user has at most a configured number of saved filters; its parameters are JSON validated against a schema before storing and before applying.
- **INV-CAT-034** · catalog · by: db, e2e · The `GET /me/export` body contains all and only the caller's own catalog rows (saved filters, shelf entries) and nothing of another user; the call writes no catalog state other than its audit row.

## Reader

- **INV-RDR-001** · reader · by: model, prop · A reading copy is built at most once per `(book_id, version)`; building is idempotent under redelivered `book.published`.
- **INV-RDR-002** · reader · by: prop · `parse(epub, parser_version)` is a pure function; two runs are byte-identical.
- **INV-RDR-003** · reader · by: type, fuzz · Stored HTML values have type `SafeHtml` (allow-list sanitizer); the sanitizer is idempotent; stored output has no script, inline handler, external load or unknown URL scheme.
- **INV-RDR-004** · reader · by: db, drill · Only a Ready copy of a published, non-deleted book is served; a copy is replaced atomically by a newer Ready copy; annotations are never deleted by a copy change.
- **INV-RDR-005** · reader · by: model · A ticket is issued only after a `read` Allow for a published version and the read-once rule; a shelf entry never produces an Allow.
- **INV-RDR-006** · reader · by: type · Book handlers take `Verified<ReadingTicket>`; its only constructor calls identity's internal `verify` (no local signature verification, D-37); a ticket is bound to user, book and version, expires within 15 minutes and is never read from a URL.
- **INV-RDR-007** · reader · by: model · Every redemption is checked by identity at that moment (active state, grants, published state), so `user.disabled`, `grant.changed` and `book.unpublished` make earlier tickets unredeemable immediately.
- **INV-RDR-008** · reader · by: type · The reader has no route that returns the EPUB file or a single chapter; the book route returns the whole package.
- **INV-RDR-009** · reader · by: model, db · A read-once entitlement is consumed by one atomic insert on successful redemption only; concurrent redemptions consume it once; a missing copy consumes nothing.
- **INV-RDR-010** · reader · by: review · Reader records and UI text state the no-DRM limit and list the controls (entitlement, short tickets, rate limits, audit).
- **INV-RDR-011** · reader · by: db · Each ticket issue and redemption writes one append-only audit row; per-user rate limits apply to both.
- **INV-RDR-012** · reader · by: model, db · Progress revision strictly increases; an update with revision ≤ stored is a no-op; percent is within 0..100; locator length bound exceeds the maximum anchor length.
- **INV-RDR-013** · reader · by: db · (user, book, location) bookmarks are unique; a duplicate create returns the existing row.
- **INV-RDR-014** · reader · by: unit · Annotation create, edit, recolour and delete are reachable by keyboard; colours come from one defined set.
- **INV-RDR-015** · reader · by: prop · Server re-anchoring (D-46) places an annotation or marks it Orphaned (kept, flagged `orphaned`); resolving an anchor returns a location or Orphaned, never an error; no annotation is deleted by a version change.
- **INV-RDR-016** · reader · by: type, db · Every personal-data query is parameterized by the user id from the verified identity header; row-level policy forbids other owners; these routes also require the session.
- **INV-RDR-017** · reader · by: unit · The `GET /me/export` JSON contains all and only the owner's reading data (preferences included); admin deletion of an account removes all of it.
- **INV-RDR-018** · reader · by: e2e · A notes deep link resolves to a location or the orphan state.
- **INV-RDR-019** · reader · by: unit · Markdown and JSON note exports contain exactly the owner's notes and highlights.
- **INV-RDR-020** · reader · by: e2e, review · Reader theme state has one owner; theming uses CSS variables only and sets no `!important` override on book content.
- **INV-RDR-021** · reader · by: e2e, review · Every reader action has a keyboard path; zoom shortcuts are not intercepted; targets ≥ 48 px.
- **INV-RDR-022** · reader · by: type, e2e · Reader state is an exhaustive enum covering building, forbidden, not found, expired ticket, offline and error with a retry action.
- **INV-RDR-023** · reader · by: unit · Search results are positions inside the reading copy of the opened book version.
- **INV-RDR-024** · reader · by: model, prop · Event cursors advance only after the event is applied; redelivered events change nothing.
- **INV-RDR-025** · reader · by: prop · A GET handler performs no write to reader state other than the audit row; package responses carry the CSP and nosniff headers.
- **INV-RDR-026** · reader · by: db, e2e · A preference row belongs to exactly one user, is readable and writable only by that user, and survives sign-out and a new device (D-48).

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
- **INV-ING-023** · ingestion · by: prop · Duplicate outcome ∈ {exact_duplicate, new_edition, new_work, needs_review} and is a pure function of (normalized title key, author, category, edition, translators; a translator difference ⇒ new_work, D-92); no outcome merges automatically.
- **INV-ING-024** · ingestion · by: type, fuzz · Template escaping is always on; chapter HTML has type `SafeHtml`; `build(curated document, builder_version)` is pure and byte-identical across runs.
- **INV-ING-025** · ingestion · by: prop, review · Every `<img>` and font reference in the XHTML resolves to a packaged file; the OPF has identifier derived from (book id, version), title, language and creator roles; nav and NCX both exist.
- **INV-ING-026** · ingestion · by: prop, review · A publishable build exists only after XML well-formedness, structure audit and epubcheck (run in the ingestion worker before publish, D-47) report 0 errors; nav, NCX and TOC links = tree leaves ∪ parents.
- **INV-ING-027** · ingestion · by: type, prop · A stored cover is image-validated by bytes from an allow-listed host; the generated cover contains title and author text.
- **INV-ING-028** · ingestion · by: type, prop · The preview artifact is built only from the allow-list type; its text length ≤ N from the book's setting.
- **INV-ING-029** · ingestion · by: model · Effective publish count per (book, build identity) = 1; the version is published by that call (no approval step, D-49); a failed build creates no version.
- **INV-ING-030** · ingestion · by: prop, review · A ruleset is promotable only if every gold metric ≥ the current metric; reprocessing never edits a published version.
- **INV-ING-031** · ingestion · by: review, e2e · No route or command accepts an uploaded EPUB or book file; every curated document originates from a scrape, and the only manual edit is of metadata.
- **INV-ING-032** · ingestion · by: model, e2e · Each console event has a monotonic id from the outbox; a reconnect with `Last-Event-ID` receives all later events or a versioned snapshot.
- **INV-ING-033** · ingestion · by: model, unit · At most one run is claimed per `next_due` slot (lock); schedule input is validated; duplicate and needs_review outcomes are never auto-retried.
- **INV-ING-034** · ingestion · by: db, drill · Expired raw pages and attempt logs are removed by retention jobs; previous-version files are kept until the next version is published.
- **INV-ING-035** · ingestion · by: db · Every state change and operator command writes an append-only audit row with the actor in the same transaction; log lines carry the job id.
- **INV-ING-036** · ingestion · by: model, e2e · Catalog publish is called for a build only when every gate result is pass (validation, structure audit, epubcheck 0 errors, exact-key duplicate rule); a build with any failed or missing gate result is never sent, so a failed gate never publishes; epubcheck that cannot run counts as a missing result and the build stays in review or retry (fail closed, D-57); publishing needs no human action (D-49).

## Notify

- **INV-NTF-001** · notify · by: model, prop · No event id leads to two accepted sends except after a recorded unknown outcome.
- **INV-NTF-002** · notify · by: prop, e2e · A producer's transaction outcome does not depend on notify availability.
- **INV-NTF-003** · notify · by: unit · Every template renders with both locales and escapes its parameters.
- **INV-NTF-004** · notify · by: type, unit · No log line or error text contains a full link, token or address.
- **INV-NTF-005** · notify · by: model, e2e · A Kindle mail is sent only after an identity Allow for the user at send time.
- **INV-NTF-006** · notify · by: prop, e2e · Every sent Kindle mail passed preflight.
- **INV-NTF-007** · notify · by: prop, e2e · No user exceeds the Kindle send quota per window; memory per send is bounded by the size cap.
- **INV-NTF-008** · notify · by: model, prop · A delivery in permanent state is never attempted again and attempts never exceed the maximum.
- **INV-NTF-009** · notify · by: db, e2e · Every send attempt has exactly one delivery log row.
- **INV-NTF-010** · notify · by: e2e · No request path of another service awaits SMTP.
- **INV-NTF-011** · notify · by: review, static · Notify has no route reachable through the gateway and no route that sends a message directly: it works from events only (D-53).
- **INV-NTF-012** · notify · by: db · No delivery log row exceeds the retention window plus one job interval.

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
- **INV-WEB-014** · web · by: review · The navigation entries equal the screen list for the user's scopes; no screen offers an approve or reject action for a book version (retired by D-49).
- **INV-WEB-015** · web · by: e2e · Library filters and sort round-trip through the URL; anonymous users cannot reach shelf or Kindle actions.
- **INV-WEB-016** · web · by: e2e · Files-tab actions render only when the corresponding scope is present.
- **INV-WEB-017** · web · by: e2e · Displayed job and request state equals the last server-confirmed state; every bulk command shows per-item results.
- **INV-WEB-018** · web · by: e2e · A grant change in the UI is one atomic request; the user detail drawer lists all of that user's grants.
- **INV-WEB-019** · web · by: e2e · Changing TOTP requires a successful re-authentication in the same flow.
- **INV-WEB-020** · web · by: unit, e2e · A mutation performs no preliminary GET; the client sends no periodic health request.
- **INV-WEB-021** · web · by: type, e2e · The reading ticket value is held only in memory and never appears in a URL, storage or log.
- **INV-WEB-022** · web · by: review, e2e · Public page HTML is rendered on the server (Angular SSR) and already contains title, canonical, meta tags and structured metadata with metadata only; preview text is never in public HTML and is marked noindex.
- **INV-WEB-023** · web · by: unit, e2e · No test reads source files as text; mocks derive from the generated schema.
- **INV-WEB-024** · web · by: review, e2e · The `web` container runs the Node SSR server; the generated TypeScript client is the only way the app and the server renderer call the API, and the SSR server holds no secret beyond the public API origin.

## Platform

- **INV-PLT-001** · all · by: review, e2e · The Compose file lists every runtime component, with limits, and only caddy publishes host ports.
- **INV-PLT-002** · all · by: review, e2e · A service role has no privilege on another service's database.
- **INV-PLT-003** · all · by: unit, e2e · `main` returns a typed startup error rather than serving when a precondition fails.
- **INV-PLT-004** · all · by: e2e · Readiness is false whenever the service cannot reach its database.
- **INV-PLT-005** · all · by: type · No service defines its own wire type.
- **INV-PLT-006** · all · by: prop · Applying a mutation twice with the same key leaves state as after once.
- **INV-PLT-007** · all · by: fuzz, static · Request handling code contains no panicking construct.
- **INV-PLT-008** · all · by: prop, e2e · No collection or loop driven by input or a remote system is unbounded.
- **INV-PLT-009** · all · by: db, e2e · Audit tables have no UPDATE or DELETE privilege for any service role, and an audit row exists for each auth event, grant, role change, publish, unpublish, delete, operator action, book open and download; rows are kept 1 year.
- **INV-PLT-010** · all · by: model, prop · Every committed change that defines an event has exactly one outbox row with an increasing cursor.
- **INV-PLT-011** · all · by: type · No domain code calls the system clock directly.
- **INV-PLT-012** · all · by: type, review · No function exceeds the shape caps without a dated waiver.
- **INV-PLT-013** · all · by: review · Every locked dependency appears in the dependency register.
- **INV-PLT-014** · all · by: review · Every lint suppression in code has a matching unexpired waiver.
- **INV-PLT-015** · all · by: drill · The latest (monthly) backup restores into an empty stack that passes the smoke checks.
- **INV-PLT-016** · all · by: review, static · No secret value appears in an image, an environment listing, a log or the repository; every secret in the inventory of `10-security/secrets-and-keys.md` (service database and token keys, session/TOTP encryption key, SMTP, source cookie, backup encryption key, offsite credential, `caddy` TLS certificates) has a declared holder, storage and rotation.
- **INV-PLT-017** · all · by: review, e2e · No request handler invokes pipeline steps directly.
- **INV-PLT-018** · all · by: type · No retry decision pattern-matches an error message.
- **INV-PLT-019** · all · by: e2e, metric · Every log line has a request id or a job id.
- **INV-PLT-020** · all · by: type, e2e · Every internal route rejects requests without a valid service token.
- **INV-PLT-021** · all · by: db · No row older than its retention window plus one job interval exists.
- **INV-PLT-022** · all · by: e2e, drill · A release leaves the previous image runnable until the new one is healthy.
- **INV-PLT-023** · all · by: db · Every enum-valued column has a CHECK or enum type and no status is stored in two places.

## Non-functional

- **INV-NFR-001** · all · by: metric, e2e · Measured monthly availability is at least 99.5%.
- **INV-NFR-002** · all · by: metric · Load-test percentiles stay within the stated limits.
- **INV-NFR-003** · all · by: metric · The load test at the stated capacity passes all latency targets.
- **INV-NFR-004** · all · by: drill · The restore drill finishes within the RTO and restores data up to 30 days old (RPO).
- **INV-NFR-005** · all · by: metric, review · No container exceeds its memory limit under the capacity test, and image and page sizes stay within the stated limits.
- **INV-NFR-006** · all · by: review · Requests above these limits are rejected with a typed error.
- **INV-NFR-007** · all · by: review, e2e · Each threat-model item has a mitigation or a signed acceptance.
- **INV-NFR-008** · all · by: e2e · Automated a11y scans and manual checks pass in both themes.
- **INV-NFR-009** · all · by: e2e · The e2e matrix passes on every listed browser and width.
- **INV-NFR-010** · all · by: unit · The string catalogs have identical key sets.
- **INV-NFR-011** · all · by: review, static · The dependency graph has no service-to-service edge except contracts.
- **INV-NFR-012** · all · by: prop · Running a build twice on the same input gives byte-identical artifacts except documented timestamps.
- **INV-NFR-013** · all · by: metric · The reconciliation count after drain is zero.
- **INV-NFR-014** · all · by: metric · Time to ready stays within the stated limits.

