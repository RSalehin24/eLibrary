# ADR-0018 — Dependencies require owner approval; standard library first

Status: REVIEW

## Context
Owner rule: no new dependencies without approval; prefer the standard library. A Rust web/search/crypto stack cannot be built on `std` alone (no async runtime, HTTP, database client, Unicode normalization, crypto).

## Decision
Keep the rule, add a visible process: the [dependency register](../dependency-policy.md) lists every proposed crate and tool with justification; nothing is added until marked APPROVED by the owner and recorded in DECISIONS.md. Phase P1 begins with one approval session for the foundational set (runtime, HTTP, serialization, database, tracing, test tooling); later areas (search, frontend, shaping) are approved after their spikes. Once code exists, CI check Q10 (`xtask`, to be written in P1) fails when a lockfile dependency is not APPROVED in the register.

## Consequences
+ Minimal, deliberate dependency surface; supply-chain risk reduced; consistent with owner's policy.
− Approval sessions are a scheduled step in the roadmap; spikes use throwaway code outside the workspace with approved-for-spike crates only.
