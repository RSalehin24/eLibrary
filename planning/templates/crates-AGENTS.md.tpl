# crates/AGENTS.md — Rust addendum  [template: copy to crates/AGENTS.md in phase P1]

Applies on top of the root AGENTS.md. Full text: `planning/03-correctness/coding-standards.md` and `planning/03-correctness/type-driven-design.md`.

- Newtypes for ids/units; parse at the edge; typestate for lifecycles; witness types for authorization; `Secret<T>` for secrets; `SafeHtml` for HTML.
- No `unwrap`/`expect`/`panic`/indexing/`todo` in non-test code; no `unsafe` (forbid) outside listed crates.
- Closed error enums per crate; no `anyhow` in libraries; map to HTTP in one exhaustive function.
- Functions ≤ ~20 lines, ≤ 3 parameters (use a struct), ≤ 2 nesting levels, no bool flag params.
- Domain crates are pure: no I/O, clock, randomness, globals. Inject `Clock`, `Rng`, stores.
- Every external I/O has a timeout; every queue/channel/body/list is bounded and listed in the limits table.
- Tests: example + property + failure paths; deterministic; every bug gets a regression test; invariant ids in test names.
- Public API documented; `#[non_exhaustive]` on growing public types in contract crates.
- Dependencies only if approved in the register.
