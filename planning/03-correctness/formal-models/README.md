# Formal models

Status: DRAFT

| Model | Tool | Covers | State |
|---|---|---|---|
| [tla/JobLifecycle.tla](tla/JobLifecycle.tla) | TLC | ingestion job lifecycle, leases, fencing, publish-once | written, **unchecked** |
| [tla/ReadOnce.tla](tla/ReadOnce.tla) | TLC | read-once consumption across devices | written, **unchecked** |
| [tla/Outbox.tla](tla/Outbox.tla) | TLC | outbox, at-least-once relay, idempotent consumer | written, **unchecked** |
| [alloy/access.als](alloy/access.als) | Alloy 6 | authorization policy properties | written, **unchecked** |
| planned | TLC | account/link/session lifecycle, book lifecycle, artifact publication, progress revisions | see [planned-models](planned-models.md) |

**Honesty note.** These files were written on a machine without Java, so none has
been run. Gate **G2** requires: every model analyzed, every property satisfied or a
counterexample resolved (fix model *or* spec), and CI job Q8 green. Until then they are
specifications, not evidence.

## How to run (Linux)

```
# TLC (needs Java 17+): download tla2tools.jar once
java -cp tla2tools.jar tlc2.TLC -config JobLifecycle.cfg JobLifecycle.tla -workers auto
# Alloy 6 (CLI): java -jar alloy.jar exec -f -o out access.als
```

## Rules

1. A model change and its invariant-register entry change in the same pull request.
2. Bounds (constants in `.cfg`) are documented here; raising them is allowed, lowering is not.
3. A counterexample is a bug in either the model or the requirement; decide which, record it in an ADR if the requirement changes.
4. Model-based tests in the implementation replay TLC traces (JSON-exported) against the Rust state machines.

## Bounds used

| Model | Bounds | Rationale |
|---|---|---|
| JobLifecycle | 3 jobs, 2 URLs (two jobs share one), MaxAttempts 2 | smallest scope showing URL exclusion, expiry, zombie holders |
| ReadOnce | 2 accounts, 3 devices | smallest scope with a multi-device race |
| Outbox | 3 events | duplicates, redelivery, ordering |
| access | 6 atoms per signature | small-scope hypothesis |
