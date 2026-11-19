# Lessons learned (main branch + `reyan-new-version`)

Status: DRAFT

## From `main`

1. **Boundaries by folder are not boundaries.** Six apps, one database and free imports produced cycles; the "common" app depends on the domains it serves.
2. **State duplicated for the UI becomes a second source of truth.** `processing` mirrors `ingestion` and keeps projection tables.
3. **Heuristics without an oracle only grow.** The contributor-name validator accretes negative rules from "the persisted-bad-row corpus"; no gold set says when it is right.
4. **Silent drops hide bugs.** Unclassified front-matter text is discarded by design.
5. **Order-dependent mutation.** The soup is `decompose()`d as passes run; results depend on pass order.
6. **Percentage tolerance is not completeness.** 5%/33% missing chapters is accepted; one book is special-cased.
7. **Side effects on the source site** (mark-complete) make scraping non-idempotent and legally/ethically fragile.
8. **Anchors that break on rebuild.** CFI highlights cannot survive regenerated chapters.
9. **Search was an afterthought** (`icontains`).
10. **Three implementations of one rule** (duplicate matching).

## From `reyan-new-version` (+1,484 files / ~124k lines, not accepted)

1. **Scope exploded in one branch**: framework swap, PWA, new broker, reader and engine extraction, local inference, schema removals — all before UI acceptance.
2. **Verification theatre**: hundreds of test counts and screenshots, but its own gate (W08, user acceptance of UX) never passed; reader and engine were "not started".
3. **Handover documents longer than the decisions they record** (1,700-line handoff).
4. **Good ideas to keep**: service ownership table; no cross-service foreign keys; opaque IDs; private versioned contract; the website never owns engine checkpoints; reader/engine failure must not break browsing.
5. **Schema removals without an environment decision** made the work unmergeable.

## Rules we adopt because of this

| Rule | Mechanism |
|---|---|
| Plan before code; gates block progress | [12-roadmap/gates.md](../12-roadmap/gates.md) |
| One phase = one deliverable that a person can use | roadmap exit criteria are user-visible |
| UX acceptance is a gate *before* more services are built on top | G4 requires user sign-off on public pages |
| Never accept a heuristic without a gold-set metric | REQ-ING-011 |
| Never drop data silently | INV-ING-002 |
| One implementation per rule, in one crate | architecture rule R-1 |
| Docs stay short; decisions are ADRs | [04-architecture/adr](../04-architecture/adr/) |
