# ADR-0009 — Ingestion as a pure, staged pipeline over immutable snapshots

Status: REVIEW

## Context
The legacy pipeline mutates a parsed HTML tree in order-dependent passes, drops unclassified text silently, and cannot be re-run deterministically.

## Decision
Stages: acquire (impure) → snapshot → block IR → section tree → classification (labels with evidence) → entity resolution → validation → canonical document. Every stage after the snapshot is a pure function `(input, ruleset) → output` with a conservation check. Ruleset changes are evaluated on the [gold corpus](../../06-data/gold-corpus/README.md) before promotion. Details: [ingestion design](../../05-services/ingestion/README.md).

## Consequences
+ Reprocessing is free and diffable; each stage is testable alone; conservation and determinism are provable properties.
− More explicit data structures than regex passes; initial effort higher (offset by the gold corpus giving a measurable target).
