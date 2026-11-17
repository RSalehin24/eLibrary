# Type-driven design rules

Status: DRAFT

Rust conventions that turn invariants into compile errors. These are binding for
all crates ([workspace layout](../04-architecture/workspace-layout.md)).

## T-1 Newtypes for every identifier and unit

`BookId(Uuid)`, `AccountId(Uuid)`, `SectionId(Uuid)`, `Sha256(String)`,
`Slug(String)`, `Percent(f32 in 0..=100)`, `Bytes(u64)`. Constructors validate; no `Deref` to the inner type.

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

Same for `Book<Draft|Published|Archived>`, `Job<…>`, `Build<…>`. Persistent
state is an enum; transitions are the *only* functions that change it.

## T-4 Witness types for authorization

```rust
pub struct Allow<A: Action> { _private: () }       // only access can mint
pub fn decide<A: Action>(f: &Facts, grants: &Grants, now: Instant) -> Result<Allow<A>, Deny>;
pub fn read_chapter(_w: Allow<Read>, cap: Verified<ReadCapability>, …) -> Chapter;
```

A handler that forgets authorization does not compile (INV-ACC-003, INV-CON-004).
Across services the witness is the signed `Capability` (verified by public key).

## T-5 Public vs full documents

`PublicDocument` and `FullDocument` are distinct types. Only
`FullDocument::to_preview(&PreviewPolicy) -> PreviewArtifact` crosses over, and the
search indexer accepts only `PublicDocument` (INV-CON-003, INV-DSC-004).

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
      wildcard_enum_match_arm, integer_arithmetic (use checked/saturating),
      unsafe_code (forbid except in explicitly listed crates)
shape (owner rules): too_many_arguments (3), too_many_lines (~20, cap 30), nesting ≤ 2
```
Exact lint names, config keys and workspace-lint syntax are **verified against the installed toolchain at gate G1** before being relied on; the full list and rationale are in [coding standards](coding-standards.md).

## T-10 Clock and randomness are dependencies

`trait Clock { fn now(&self) -> Instant; }` and `trait Rng`. Production, tests and
models inject their own. `SystemTime::now` and `rand::thread_rng` appear only in
the production implementations (INV-PLT-010).
