# Type-driven design rules

Status: DRAFT

Rebuilt 2026-11-19 for six services (D-31): authorization is decided only by identity and carried to other services as gateway headers and reading tickets, not as signed capability tokens. Kept from v1: T-1 to T-3, T-6 to T-11; changed: T-4, T-5; no Rust code exists yet and the lint names stay to be verified at gate G1.

Rust conventions that turn invariants into compile errors. These are binding for
all crates ([workspace layout](../04-architecture/workspace-layout.md)).

## T-1 Newtypes for every identifier and unit

`BookId(Uuid)`, `UserId(Uuid)`, `VersionId(Uuid)`, `SectionId(Uuid)`, `Slug(String)` (no catalog codes, D-36), `Sha256(String)`, `Percent(f32 in 0..=100)`, `Bytes(u64)`. Constructors validate; no `Deref` to the inner type.

## T-2 Parse, don't validate

Raw input types (`RawEmail`) are converted once, at the edge, to validated types
(`Email`). Internal code never accepts strings where a validated type exists.

## T-3 Typestate for lifecycles

```rust
pub struct Session<S>(Inner, PhantomData<S>);
pub struct PasswordOk; pub struct Authenticated; pub struct Revoked;
impl Session<PasswordOk> { pub fn with_totp(self, code: TotpCode, acct: &Account)
    -> Result<Session<Authenticated>, AuthError> { … } }
// No constructor produces Session<Authenticated> any other way (INV-IDN-004).
```

Same for `Version<Draft|InReview|Published|Archived>` (INV-CAT-001), `Request<…>` and `Job<…>` (INV-ING-008), `Delivery<…>` (INV-NTF-008). Persistent
state is an enum; transitions are the *only* functions that change it.

## T-4 Witness types for authorization

```rust
// Only `identity` can construct a decision (INV-IDN-013, INV-IDN-024).
pub struct Allow<S: Scope> { _private: () }
pub fn decide<S: Scope>(facts: &Facts, now: Instant) -> Result<Allow<S>, Deny>;

// Every other service accepts only what the gateway established:
pub struct Caller { user: UserId, scopes: ScopeSet }   // from gateway headers + internal service token
pub fn route<S: Scope>(_c: &Caller) -> ...             // handler declares its scope in the type
pub struct Verified<ReadingTicket>(..);                // only constructor calls identity `verify` (D-37, INV-RDR-006)
```

A handler without a declared scope does not compile, and a route table entry without `scope` or `public` stops startup (INV-IDN-024). No service verifies a signature locally: tickets are opaque and checked by identity at every redemption (INV-IDN-021).

## T-5 Public vs full documents

`PublicDocument` (metadata only, D-34) and `PreviewArtifact` and the reader's `SanitizedBook` are distinct types. The search indexer and the public routes accept only `PublicDocument`; preview text and book text have no conversion into it (INV-CAT-012, INV-CAT-002).

## T-6 Total functions, exhaustive matches

No `_ =>` wildcard on domain enums (`#![deny(clippy::wildcard_enum_match_arm)]`).
Adding a variant breaks every site that must decide.

## T-7 Secrets and sanitized output

`Secret<T>` has no `Debug`/`Display`/`Serialize`. `SafeHtml` is produced only by
`sanitize(&str) -> SafeHtml` (ammonia profile pinned in config); templates accept `SafeHtml`.

## T-8 Errors are data

Each crate has a closed `Error` enum; HTTP mapping is one exhaustive function per
service; every variant has a stable machine code in [error-catalog](../07-contracts/error-catalog.md).
No `anyhow` in library crates; no stringly-typed errors across boundaries.

## T-9 Lint set (workspace `Cargo.toml`)

```
deny: unwrap_used, expect_used, panic, indexing_slicing, todo, unimplemented,
      wildcard_enum_match_arm, arithmetic_side_effects (use checked/saturating),
      unsafe_code (forbid except in explicitly listed crates)
shape (owner rules): too_many_arguments (3), too_many_lines (~20, cap 30), nesting ≤ 2
```
Exact lint names, config keys and workspace-lint syntax are **verified against the installed toolchain at gate G1** before being relied on; the full list and rationale are in [coding standards](coding-standards.md).

## T-11 The web UI gets the same guarantees in TypeScript

Generated wire types (no hand-written DTOs); `PageState<T>` as a discriminated union with `assertNever` exhaustiveness; branded types for ids (`BookId`, `SectionId`) so ids cannot be mixed; `Result<T, ErrorCode>` instead of thrown strings; no `any`/`!`/casts outside the generated boundary ([coding standards §16](coding-standards.md)).

## T-10 Clock and randomness are dependencies

`trait Clock { fn now(&self) -> Instant; }` and `trait Rng`. Production, tests and
models inject their own. `SystemTime::now` and `rand::thread_rng` appear only in
the production implementations (INV-PLT-011).
