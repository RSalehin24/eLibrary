# Verification log

Status: DRAFT

Entries are dated. Sections 1 to 4 record what was checked on 2026-11-17 (v1 plan; kept as written, they were not re-verified in the 2026-11-19 rewrite). What was checked on 2026-11-17, against what source, with what result. "Verified" means read from the primary source or executed. Anything not listed here is **not verified**.

## 1. Executed checks

| Check | Method | Result |
|---|---|---|
| Plan integrity | `python3 planning/tools/check_plan.py` | 0 errors (negative test on a broken copy caught 8 injected faults) |
| Legacy facts in discovery docs | re-measured with `ls`/`wc` | **3 errors found and fixed**: pages 20 (not 21), feature folders 10 (not 9), CSS files 64 (not "3 bundles"); reader runtime 35,032 lines in `src/embedded-reader` + 32,899 in `public/epub-reader` (not "≈ 40k"). Confirmed: 481 backend test functions, 20,112 ingestion lines, 72,496 frontend lines, 12 permission scopes |
| Model logic (Python mirrors — **not TLC/Alloy**) | `planning/tools/model_mirror.py`, explicit-state BFS + SCC fairness check for liveness | see §2 |

## 2. Model mirror results (logic only; TLA+/Alloy syntax still unchecked)

| Model | Bounds | Result | Sensitivity (a deliberately broken variant must fail) |
|---|---|---|---|
| JobLifecycle (with ghost per-run outcome, after fixing F-1) | 3 jobs / 2 attempts: 37,296 states; **4 jobs / 2 attempts: 1,016,064 states** (earlier abstraction: 4 jobs / 3 attempts 230,400) | all safety properties hold; `EventuallySettled` holds under weak fairness | removing URL exclusion → `AtMostOneActivePerUrl`; publishing without completeness → `PublishedImpliesComplete` + `PublishedImpliesCurrentRunComplete`; **removing fencing → `PublishedImpliesCurrentRunComplete`** |
| ReadOnce | 2 accounts, 3 devices: 100 states | all four safety properties hold | removing the `Busy` guard → `AtMostOneOpening`, `AtMostOneLiveSession`, `PreparingNeverConsumed`, `ActiveOrClosedMeansConsumed` |
| Outbox | 3 events: 343 states | `AppliedAtMostOnce`, `SeenIffApplied`, `NoEffectWithoutCommit` hold; `NoLoss` holds under weak fairness | removing consumer dedupe → `AppliedAtMostOnce`, `SeenIffApplied` |
| Access policy (mirror of `access.als`) | randomized, 8,000 samples × all actions/books/subjects (2 accounts, 2 books) | `AnonymousLimited`, `ReadNeedsAccount`, `DeadGrantsIgnored`, `Monotonic`, `ManagementNeedsAuthority`, `UnpublishedHidden` hold | publishing-bypass mutant → `AnonymousLimited`, `UnpublishedHidden` |

**Findings**
- **F-1 (model weakness) — FOUND AND FIXED.** The first `JobLifecycle` carried a fencing `epoch`, but removing the epoch check changed nothing observable (no worker identity, no stale-result variable), so the spec did not demonstrate zombie protection. Fix: a ghost variable `outcome[job][epoch]` holds the true result of each run; a worker of run *e* reports that run's outcome; the new property `PublishedImpliesCurrentRunComplete` fails when fencing is removed (verified in the mirror) and holds with fencing. `JobLifecycle.tla` was updated the same way (still unchecked by TLC). Rule added: **every model needs at least one mutation its properties detect**.
- **F-2 (TLC usage).** The models reach terminal states with no enabled action, so TLC reports deadlock unless run with `-deadlock` (flag verified) or given a stuttering disjunct.
- **F-3 (harness).** A first mirror run consumed ~80% of RAM because the *broken* outbox variant counted applications without bound. Fixed with a capped counter, a state-count guard and an OS memory cap (`ulimit -v`). Later runs, including the 230,400-state run, stayed near 4 GB of 30 GB.

## 3. Verified from primary sources

| Claim | Source | Result |
|---|---|---|
| Angular release status | angular.dev/reference/releases | v22 Active (2026-06-03), v21 LTS, v20 LTS until 2026-11-28; docs build 22.2.6 |
| Angular default unit-test runner | angular.dev/guide/testing | Vitest + jsdom; Karma still supported |
| SSR/hydration | angular.dev/guide/ssr, /hydration | no "developer preview" label; caveats documented |
| Angular compiler options | angular.dev/reference/configs/angular-compiler-options | `strictTemplates` (default true), `strictInjectionParameters` exist; `strictInputAccessModifiers` not present |
| Angular Material M3 content | published package listing of `@angular/material` 21.2.6 (jsDelivr) | `_m3-*.scss` files present; 40 top-level folders; **no** navigation rail/bar, side sheet, search; FAB lives inside `button/` |
| clippy config keys & defaults | doc.rust-lang.org/clippy/lint_configuration.html | `too-many-arguments-threshold` 7, `too-many-lines-threshold` 100, `cognitive-complexity-threshold` 25, `excessive-nesting-threshold` 0, `type-complexity-threshold` 250 |
| `integer_arithmetic` | clippy lint index | removed; past name of `arithmetic_side_effects` (restriction) → **plan corrected** |
| Cargo workspace lints | Cargo reference (workspaces, manifest) | `[workspace.lints.*]` + member `[lints] workspace = true`, Rust ≥ 1.74; lints apply to members only |
| ESLint rules/options | eslint.org/docs/latest/rules/* | `max-params` (default 3), `max-lines-per-function` (50; `skipBlankLines`, `skipComments`), `max-depth` (4), `complexity` (20); `no-magic-numbers` is frozen |
| typescript-eslint presets | typescript-eslint.io/rules/* | `no-explicit-any` recommended; `no-non-null-assertion` strict; `no-unsafe-assignment` and `no-unnecessary-type-assertion` recommended-type-checked; `consistent-type-assertions` stylistic; `ban-ts-comment` recommended; `switch-exhaustiveness-check` in no preset |
| TypeScript options | typescriptlang.org/tsconfig | all six options exist |
| Crates exist | docs.rs for 46 crates | all exist, none yanked/deprecated at latest; flags in [dependency policy](../04-architecture/dependency-policy.md) (rustybuzz stale, jiff 1.0 new, pasetors unaudited, etc.) |
| `uuid` v7/v5 | docs.rs features | present |
| PASETO v4 | paseto-spec protocol versions | v4.public = Ed25519; v4.local = XChaCha20 + BLAKE2b-MAC |
| `pasetors` / `rusty_paseto` | docs.rs | both support v4.public |
| RFC 6238 | rfc-editor.org | 30 s step default, HMAC-SHA-1 default, no default digit count, replay of an accepted OTP MUST be rejected → **REQ-IDN-010 added** |
| PostgreSQL `SKIP LOCKED` | postgresql.org SELECT docs | exists; documented as suitable for queue-like tables |
| TLC options | Lamport "current-tools" PDF | `-config`, `-workers num|auto`, `-deadlock` exist |
| Alloy | alloytools.org, GitHub README, forum | 6.2.0 (2025-01-09), Java 17+, `exec` with `-c/--command`, `-o/--output`, `-t` |
| Window size classes | Android adaptive-layout docs (m3 page 404) | compact <600, medium 600–839, expanded 840–1199, large 1200–1599, XL ≥1600 |
| Noto Serif Bengali license | notofonts repo, Fontsource (secondary) | SIL OFL 1.1 |
| Kindle email limits | third-party guides (Amazon page returned 503) | 50 MB total/email, 25 attachments, approved-sender list required, EPUB converted → **plan updated; re-verify on Amazon before P7** |
| M3 Angular theming API | secondary sources (official page unreadable) | `mat.theme()` emits CSS variables; density 0…−5 → confirm in S-02 |

## 4. Not verified (and when)

| Item | Why | When |
|---|---|---|
| TLA+/Alloy syntax and exhaustive checking | no Java installed (approval needed) | S-04 / G2 |
| Angular Material official docs (theming, per-component M3 coverage, Expressive, zoneless) | client-rendered site unreadable | S-02 |
| `excessive_nesting` lint group/behavior; group membership of other clippy lints | index read only partially | G1 |
| `icu_collator` Bengali data actually baked in | not listed in docs | S-01 |
| Rust crates' downloads/maintainer health beyond latest-release date | crates.io/lib.rs unreadable | at dependency approval (D-17) |
| Whether Kindle limits changed | Amazon page 503 | before P7 |
| Performance, relevance and accuracy targets | need data and code | gold baseline / G4–G6 |
| All requirements' implementations | no code exists | per gate |

## 5. Entry 2026-11-19 (six-service rewrite of the roadmap and correctness documents)

**No facts were re-verified in this rewrite.** The work was editorial: re-baselining the roadmap and correctness documents on the owner decisions D-22 to D-48 and the new architecture brief.

| Item | State |
|---|---|
| Entries in sections 1 to 4 (2026-11-17) | carried over unchanged; still valid only for what they say; the Python mirrors cover the **v1** models, not the models edited since or the planned ones |
| Formal models | none run: Java is not installed. `coverage.md` lists all 46 invariants whose mechanism includes `model` with state `planned`, `edited, not re-checked` or `unchecked`; the `.tla` and `.als` files received comment-only id renames and their logic is unchanged |
| Tool, flag and lint names in [coding standards](coding-standards.md), [type-driven design](type-driven-design.md) | carried over from 2026-11-17; **verify at gate G1 and spike S-02** |
| New claims added (Compose rules, Java in the worker, SSR rules) | design statements, not verified; sources are the decisions D-22, D-39, D-47 and [deployment topology](../04-architecture/deployment-topology.md) |
| Estimates in [phases](../12-roadmap/phases.md) | planning figures, not measurements |
| Plan checker | not run by the writer of this entry (other writers were editing concurrently); the parent runs it at the end of the wave |

Still not verified (additions to section 4): epubcheck and Java runtime size and memory in the worker image (S-04); Angular SSR memory and first byte on Node (S-02); PostgreSQL full-text quality on Bengali (S-01); whole-book serving at 5 MB (S-08); backup and restore timings (S-09).
