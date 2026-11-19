# Formal models

Status: DRAFT

Re-baselined 2026-11-19 for the six-service design. **Checked 2026-11-20** with TLC 2.19 (`tla2tools.jar` 1.7.4) and Alloy 6.2.0 on Java 27 (D-69); run all with `deploy/scripts/check-models.sh` (gate Q8, about 4 s).

| Model | Tool | Covers | State |
|---|---|---|---|
| [tla/JobLifecycle.tla](tla/JobLifecycle.tla) | TLC | ingestion job lifecycle, leases, fencing, publish-once | **checked**: `MCJobLifecycle` (3 jobs, 2 URLs, 2 attempts): 37,296 distinct states, Safety and EventuallySettled hold; per-request exclusion and cancel flag still to add |
| [tla/ReadOnce.tla](tla/ReadOnce.tla) | TLC | read-once consumed on ticket redemption, multi-device race | **checked**: 2,450 distinct states, no error |
| [tla/Outbox.tla](tla/Outbox.tla) | TLC | outbox, pull cursor, idempotent consumer, crash and cursor reset (consumer side) | **checked**: Safety (193 states) and Safety with cursor reset (`OutboxReset.cfg`, 373 states), NoLoss under strong fairness of `Apply` (the first run found a crash loop that weak fairness allowed: model assumption fixed and documented); producer extension planned |
| [alloy/access.als](alloy/access.als) | Alloy 6 | scope-based deny-by-default policy | **checked** and brought up to date (no Demo, `public` and `session` scopes, preview needs a session): 8 assertions, no counterexample within scope 6; a mutation test (TOTP condition removed) makes `ManagementNeedsAuthority` fail, so the checks are not vacuous |
| planned | TLC and Alloy | AccountLifecycle, EntitlementDecision, TicketLifecycle, VersionLifecycle, PublishSaga, ReaderCopyLifecycle, ProgressRevision, RequestLifecycle, DeliveryLifecycle, Outbox and JobLifecycle extensions | see [planned-models](planned-models.md); all 46 `model` invariants are in [coverage](coverage.md) |

**What this is and is not.** Each result is exhaustive only within the model's bounds (three events or jobs, two attempts, Alloy scope 6). A passing run shows the model satisfies its properties, not that the Rust code does: the code is tied to the models by property tests and trace replay (planned, P2/P3). Gate **G2** also needs the nine planned models and extensions below, and counterexamples resolved in the model or the requirement.

## How to run (Linux)

```
deploy/scripts/check-models.sh       # all models; verifies pinned jar checksums; fails on any counterexample
# by hand (from planning/03-correctness/formal-models/tla; -deadlock because the models reach terminal states):
java -cp tla2tools.jar tlc2.TLC -config Outbox.cfg -workers 4 -deadlock Outbox.tla
java -cp tla2tools.jar tlc2.TLC -config MCJobLifecycle.cfg -workers 4 -deadlock MCJobLifecycle.tla
# Alloy: `exec` writes a directory per run; -f recreates it; a `check` printed SAT is a counterexample, UNSAT means none
java -jar org.alloytools.alloy.dist.jar exec -f -o <outdir> alloy/access.als
```

TLC config files cannot hold function values, so `JobLifecycle` is checked through the wrapper module `MCJobLifecycle.tla` (it defines `UrlOf`). The jars live under `tools/` (git-ignored) and are pinned by SHA-256 in `check-models.sh`.

## Interim evidence

`planning/tools/model_mirror.py` re-implemented the three earlier TLA+ models and the Alloy policy (it mirrors the v1 push outbox, session and access models and is out of date for every model edited since; it covers none of the planned models) in Python and checks their properties by explicit-state search (jobs up to 4 jobs × 2 attempts = 1,016,064 states). All properties hold; every deliberately broken variant is detected, including removed fencing (finding F-1, fixed with a ghost per-run outcome). Details: [verification log](../verification-log.md). This validates the *logic* only; TLC/Alloy remain required at G2.

## Rules

0. **Sensitivity:** every model must come with at least one deliberately broken variant that its properties detect (mirror or TLC); a property that no mutation can break is vacuous and must be strengthened.

1. A model change and its invariant-register entry change in the same pull request.
2. Bounds (constants in `.cfg`) are documented here; raising them is allowed, lowering is not.
3. A counterexample is a bug in either the model or the requirement; decide which, record it in an ADR if the requirement changes.
4. Model-based tests in the implementation replay TLC traces (JSON-exported) against the Rust state machines.

## Bounds used

| Model | Bounds | Rationale |
|---|---|---|
| JobLifecycle | 3 jobs, 2 URLs (two jobs share one), MaxAttempts 2 | smallest scope showing URL exclusion, expiry, zombie holders |
| ReadOnce | 2 accounts, 3 devices | smallest scope with a multi-device ticket-redeem race |
| Outbox | 3 events | duplicate pulls, crash, ordering by cursor |
| planned models | set when each is written (P2); smallest scope that shows the race | recorded here at G2 |
| access | 6 atoms per signature | small-scope hypothesis |
