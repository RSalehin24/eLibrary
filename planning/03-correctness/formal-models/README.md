# Formal models

Status: DRAFT

| Model | Tool | Covers | State |
|---|---|---|---|
| [tla/JobLifecycle.tla](tla/JobLifecycle.tla) | TLC | ingestion job lifecycle, leases, fencing, publish-once | written, **unchecked** |
| [tla/ReadOnce.tla](tla/ReadOnce.tla) | TLC | read-once consumed on ticket redemption, multi-device race | edited for tickets, **not re-checked** |
| [tla/Outbox.tla](tla/Outbox.tla) | TLC | outbox with pull cursor, idempotent consumer, crash and cursor reset | rewritten for pull, **not re-checked** |
| [alloy/access.als](alloy/access.als) | Alloy 6 | scope-based deny-by-default policy (ownership grants nothing, no wildcard) | edited, **not re-checked** |
| planned | TLC | account/link/session lifecycle, book lifecycle, artifact publication, progress revisions | see [planned-models](planned-models.md) |

**Honesty note.** These files were written on a machine without Java, so none has
been run. Gate **G2** requires: every model analyzed, every property satisfied or a
counterexample resolved (fix model *or* spec), and CI job Q8 green. Until then they are
specifications, not evidence.

## How to run (Linux)

```
# TLC: options -config <file>, -workers <num|auto>, -deadlock are VERIFIED in Lamport's official
# "current-tools" PDF. The documented entry point is `java tlc2.TLC <switches> <Spec>.tla`
# (standalone-tools page); with a jar on the classpath use: java -cp tla2tools.jar tlc2.TLC ...
# (the -cp form and the minimum Java version were NOT in the pages read: confirm in spike S-04).
java -cp tla2tools.jar tlc2.TLC -config JobLifecycle.cfg -workers auto JobLifecycle.tla
# Alloy 6.2.0 needs Java 17+ (verified). CLI: `java -jar org.alloytools.alloy.dist.jar exec ...`
# Documented options seen: -c/--command, -o/--output, -t <type>. The `-f` flag I wrote earlier is UNVERIFIED
# and removed; run `exec --help` in spike S-04 to confirm the options.
java -jar org.alloytools.alloy.dist.jar exec -o out access.als
```

Note: TLC flags `-deadlock` (disable deadlock checking) matters here: the models intentionally reach terminal states, so run with `-deadlock` or add a `Terminating` stuttering disjunct to `Next` (to decide in S-04).

## Interim evidence

`planning/tools/model_mirror.py` re-implemented the three earlier TLA+ models and the Alloy policy (it still mirrors the pre-redesign push outbox, session and access models and is out of date for the edited ones) in Python and checks their properties by explicit-state search (jobs up to 4 jobs × 2 attempts = 1,016,064 states). All properties hold; every deliberately broken variant is detected, including removed fencing (finding F-1, fixed with a ghost per-run outcome). Details: [verification log](../verification-log.md). This validates the *logic* only; TLC/Alloy remain required at G2.

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
| access | 6 atoms per signature | small-scope hypothesis |
