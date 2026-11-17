# Invariants register

Status: DRAFT

An invariant is a statement that must hold in **every reachable state**. Each has an
enforcement mechanism (`by:`) — the strongest one that applies:

`type` compile-time · `db` database constraint · `model` TLA+/Alloy · `prop` property/model-based test ·
`gold` gold-corpus metric · `fuzz` fuzzing · `review` checklist · `drill` operational drill

Line format: `INV-ID · owner · by: <mechanisms> · statement`

## Identity

- **INV-IDN-001** · identity · by: model, type · No account is Active without either consuming a valid setup link or being the seeded superadmin.
- **INV-IDN-002** · identity · by: model, db · A link token is consumed at most once and never after its expiry or after a newer link for the same purpose was issued.
- **INV-IDN-003** · identity · by: type · A value of type `Secret<T>` cannot be formatted, serialized to logs, or compared in non-constant time.
- **INV-IDN-004** · identity · by: model, type · A `Session<Authenticated>` can only be constructed from `PasswordOk` plus `TotpOk` when the account requires TOTP.
- **INV-IDN-005** · identity · by: model, db · After revocation, a session token authenticates nothing; token storage holds only hashes.
- **INV-IDN-006** · identity · by: prop · The response to a login/reset attempt for an unknown identifier is indistinguishable (status, body shape, timing bucket) from a known one.
- **INV-IDN-007** · identity · by: type · A `KindleEmail` is a syntactically valid address; an account holds at most 5.
- **INV-IDN-008** · identity · by: model, type · Account status changes only along Invited→Active⇄Suspended→Disabled.

- **INV-IDN-009** · identity · by: model, prop · For an account, accepted TOTP time steps are strictly increasing: a code is accepted only if its step > `last_accepted_step`.

## Access

- **INV-ACC-001** · access · by: model, prop · For Anonymous, `decide` returns Allow only for {Search, ViewMetadata, ViewPreview}.
- **INV-ACC-002** · access · by: model, prop · `decide(Read)` = Allow ⇒ subject is an Active account AND (matching live grant OR ownership OR default-grant policy).
- **INV-ACC-003** · access · by: type, model · `decide` is total; protected operations accept only a `Decision::Allow` witness type they cannot construct themselves.
- **INV-ACC-004** · access · by: model, prop · A grant with `expires_at ≤ now` or `revoked_at ≤ now` never contributes to Allow.
- **INV-ACC-005** · access · by: model, prop · For grant sets G⊆G′ (same facts, excluding read-once consumption), Allow(G) ⇒ Allow(G′).
- **INV-ACC-006** · access · by: model, prop · For (account, book) under read-once, the number of consumed openings ≤ 1, and an opening is consumed only when a reading session reaches `Prepared`.
- **INV-ACC-007** · access · by: model · For a demo or non-managing session, every mutating admin action decides Deny.
- **INV-ACC-008** · access · by: type, prop, fuzz · A capability verifies iff signature valid ∧ not expired ∧ (subject, book, artifact set, action) match the request; TTL ≤ 300 s.
- **INV-ACC-009** · access · by: model · Management Allow ⇒ session.mfa_ok when the account requires TOTP.
- **INV-ACC-010** · access · by: prop · `decide(f, G) = decide(f, permute(G))` for all permutations.
- **INV-ACC-011** · access · by: db · A grant mutation and its audit row commit in one transaction or neither commits.
- **INV-ACC-012** · access · by: model · For non-Published books, `decide(ViewMetadata|ViewPreview|Read)` is Deny unless subject has metadata/management grants.

## Catalog & discovery

- **INV-CAT-001** · catalog · by: type, model · Book state changes only along Draft→Published⇄Archived→Deleted.
- **INV-CAT-002** · catalog · by: db · Published ⇒ ∃ credit with role ∈ {writer, translator, editor, compiler}.
- **INV-CAT-003** · catalog · by: db · `id` and `code` never change; `slug` unique; every former slug maps to its book.
- **INV-CAT-004** · catalog · by: db, prop · An override value wins over any source value; an update with a stale revision is rejected, never merged silently.
- **INV-CAT-005** · catalog · by: db · Credits reference agents by id; two agents are distinguishable only by id; merge preserves all credits and records an undo.
- **INV-CAT-006** · catalog · by: prop · Duplicate classification outcome ∈ {ExactDuplicate, NewEdition, NewTranslation, NewWork, NeedsReview} and is a pure function of the normalized key tuple.
- **INV-CAT-007** · catalog · by: prop · `count(facet) = |results(facet filter)|` for the same snapshot.
- **INV-CAT-008** · catalog · by: prop · Export rows = list rows for the same filter and snapshot.
- **INV-CAT-009** · catalog · by: db · (Only if D-01 keeps inventory) inventory rows reference a book and have non-negative price.
- **INV-DSC-001** · catalog · by: prop · Every search result is a Published book.
- **INV-DSC-002** · catalog · by: prop · `normalize(normalize(x)) = normalize(x)`; query and index use the same function version.
- **INV-DSC-003** · catalog · by: gold · Alias lookup is symmetric between a Bengali form and its registered Latin forms.
- **INV-DSC-004** · catalog · by: model, type · The public index is built only from `PublicDocument` values, a type that cannot hold non-preview text.
- **INV-DSC-005** · catalog · by: prop, drill · rebuild(events) produces the same results as incremental indexing.
- **INV-DSC-006** · catalog · by: prop · Bengali collation comparator is a total preorder (reflexive, transitive, total).
- **INV-DSC-007** · catalog · by: prop · Facet semantics: AND across facets, OR within.
- **INV-DSC-008** · catalog · by: prop · Under a fixed snapshot, concatenated pages = full ordered result list.
- **INV-DSC-009** · catalog · by: gold · MRR@10 and recall@20 on the judged query set meet thresholds.

## Content

- **INV-CON-001** · content · by: db, model · An artifact set row is never updated; the active pointer references exactly one complete set.
- **INV-CON-002** · content · by: prop · `build(doc, builder_version)` is a pure function; two builds are byte-identical.
- **INV-CON-003** · content · by: type · The preview endpoint's return type is `PreviewArtifact`; no code path converts `FullDocument` to it without the allow-list filter.
- **INV-CON-004** · content · by: type · Full-text handlers take `Verified<ReadCapability>`; the only constructor is `verify(token, key, now, request)`.
- **INV-CON-005** · content · by: prop · Range responses concatenate to the original bytes.
- **INV-CON-006** · content · by: db, drill · A set referenced by any non-orphaned anchor set or younger than retention is not deletable.
- **INV-CON-007** · content · by: prop, gold · EPUB nav links = in-book TOC links = tree leaves ∪ parents; epubcheck reports 0 errors.
- **INV-CON-008** · content · by: gold, review · Generated cover includes the title and author text with no tofu glyphs.
- **INV-CON-009** · content · by: type, fuzz · Stored HTML values have type `SafeHtml`; the sanitizer is idempotent.

## Library

- **INV-LIB-001** · library · by: model, db · Progress revision strictly increases; an update with revision ≤ stored is a no-op.
- **INV-LIB-002** · library · by: prop · After re-anchoring, every annotation is `Anchored`, `Reanchored` or `Orphaned`; none is deleted by re-anchoring.
- **INV-LIB-003** · library · by: type, db · Every personal-data query is parameterized by `OwnerId` from the session; row-level policy forbids other owners.
- **INV-LIB-004** · library · by: db · (account, book) unique in shelf.
- **INV-LIB-005** · library · by: prop · Resolving an anchor returns a location or `Orphaned`, never an error.
- **INV-LIB-006** · library · by: prop · `apply(save(filter)) = filter`.
- **INV-LIB-007** · library · by: unit · Export contains all and only the owner's annotations.
- **INV-LIB-008** · library · by: model · At most one active reading session per (account, book, device class); sessions expire without heartbeat.

## Ingestion

- **INV-ING-001** · ingestion · by: db, prop · A snapshot row and its blobs are write-once; derived data carries (snapshot hash, ruleset version).
- **INV-ING-002** · ingestion · by: prop, gold · Σ blocks(input) = Σ blocks(output) + Σ blocks(dropped with reason), as multisets of `BlockId`.
- **INV-ING-003** · ingestion · by: type, prop · TOC and nav are rendered from one `SectionTree`; reading order is a bijection leaves→1..n.
- **INV-ING-004** · ingestion · by: prop, gold · With a source TOC, section tree ≅ source TOC (same shape and titles up to normalization).
- **INV-ING-005** · ingestion · by: gold · Every inferred chapter boundary has ≥ 1 evidence item.
- **INV-ING-006** · ingestion · by: model, prop · Publish ⇒ ∀ TOC leaves: fetched ∨ empty-at-source(recorded).
- **INV-ING-007** · ingestion · by: prop · Auto-publish ⇒ all entities have evidence and confidence ≥ ruleset threshold.
- **INV-ING-008** · ingestion · by: prop, gold · No normalized text block appears in two output sections of different types.
- **INV-ING-009** · ingestion · by: gold · Label language = book language for all generated labels.
- **INV-ING-010** · ingestion · by: model, prop · Job lifecycle obeys the state machine; ≤ 1 active job per source URL; lease expiry only moves Running→Queued.
- **INV-ING-011** · ingestion · by: gold · A ruleset is promotable only if every gold metric ≥ the current ruleset's metric − ε(0).
- **INV-ING-012** · ingestion · by: type · The acquisition client only exposes `get`; any non-GET request type is unrepresentable unless D-03 adds a named action.
- **INV-ING-013** · ingestion · by: gold · Manual intake canonical documents pass the same validator.
- **INV-ING-014** · ingestion · by: prop · Catalog sync is idempotent: syncing twice creates no extra jobs.
- **INV-ING-015** · ingestion · by: prop, gold · Duplicate policy matches the five-case decision table on all labeled pairs.
- **INV-ING-016** · ingestion · by: model · Effective `BookPublished` count per (book, artifact set) = 1.

## Notify, Gateway, Web

- **INV-NTF-001** · notify · by: model, prop · Per (event id, kind) at most one successful send is recorded.
- **INV-NTF-002** · notify · by: prop · Kindle send ⇒ Allow(SendToKindle) ∧ address ∈ account addresses ∧ size ≤ limit.
- **INV-NTF-003** · notify · by: unit · Every template key exists in both languages.
- **INV-NTF-004** · notify · by: type · Mail payloads use `Secret`-wrapped link types.
- **INV-GWY-001** · gateway · by: review, e2e · The set of exposed routes equals the public route table.
- **INV-GWY-002** · gateway · by: e2e · A cookie-authenticated mutation without a valid CSRF token is rejected.
- **INV-GWY-003** · gateway · by: e2e · Every response and log line contains the request id.
- **INV-GWY-004** · gateway · by: e2e · Required security headers are present on every response.
- **INV-WEB-001** · web · by: type · Page state is an exhaustive enum; `match` without all arms does not compile.
- **INV-WEB-002** · web · by: e2e · All internal `href`s resolve to a route in the route map.
- **INV-WEB-003** · web · by: e2e, review · Automated a11y scan reports zero serious/critical violations.
- **INV-WEB-004** · web · by: review · Typography checklist passes on a Bengali sample set.
- **INV-WEB-005** · web · by: e2e · No horizontal overflow at 360, 768, 1280, 1920 px.
- **INV-WEB-006** · web · by: e2e · Every color used comes from a theme token.
- **INV-WEB-007** · web · by: e2e · Public page HTML contains title, canonical, OG tags and meaningful content without JS.
- **INV-WEB-008** · web · by: review · Admin navigation matches the workspace list.
- **INV-WEB-009** · web · by: unit · `bn` and `en` catalogs have identical key sets.

- **INV-WEB-010** · web · by: review, e2e · Every UI component resolves to an Angular Material/CDK component or a documented `shared/` composition; visual snapshots match the approved Material 3 themes.
- **INV-WEB-011** · web · by: type, e2e · Regenerating the TypeScript client from the Rust schema produces no diff; compilation with strict flags passes; lint rules forbidding `any`/`!`/casts pass.

## Platform & Migration

- **INV-PLT-001** · all · by: unit, e2e · `main` returns `Err(StartupError)` rather than serving when preconditions fail.
- **INV-PLT-002** · all · by: type · Request/response/event types are imported from `contracts-*`; no service defines its own wire type.
- **INV-PLT-003** · all · by: prop · Applying the same mutation with the same key twice leaves state as after once.
- **INV-PLT-004** · all · by: fuzz, review · `clippy::unwrap_used`, `expect_used`, `indexing_slicing`, `panic` are `deny` in non-test code.
- **INV-PLT-005** · all · by: prop · Each bound in the limits table is enforced and tested at limit±1.
- **INV-PLT-006** · all · by: db · Audit table has INSERT-only privileges for service roles.
- **INV-PLT-007** · all · by: e2e · Every service exposes `/health/live`, `/health/ready`, `/metrics`.
- **INV-PLT-008** · all · by: drill · Restore from backup reproduces a consistent system within RTO.
- **INV-PLT-009** · all · by: model, prop · Outbox rows and state changes commit atomically; a consumer applies each event id at most once.
- **INV-PLT-010** · all · by: type · No `SystemTime::now()` outside the `SystemClock` implementation.
- **INV-PLT-011** · all · by: type, review · No function exceeds the configured length/parameter/nesting thresholds without a dated waiver; bool flag parameters do not appear in signatures.
- **INV-PLT-012** · all · by: review, drill · Every dependency in a lockfile has an `APPROVED` register entry; the register has no entry without a lockfile reason or a planned phase.
- **INV-PLT-013** · all · by: type · `missing_docs` is denied in `contracts-*` and `domain-*`; doctests compile and pass.
- **INV-MIG-001** · migration · by: drill · Reconciliation diff = ∅ after accounting for documented exclusions.
- **INV-MIG-002** · migration · by: e2e · Every legacy slug and code resolves (200 or 301).
- **INV-MIG-003** · migration · by: unit · A legacy PBKDF2 hash verifies; on success the stored hash becomes Argon2id.
- **INV-MIG-004** · migration · by: drill · Rollback rehearsal restores legacy as primary with data parity.
