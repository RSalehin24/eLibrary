# Plan rewrite — method and progress

Status: ACTIVE

Rewrites `planning/00…12` on the six-service architecture ([new-architecture.md](new-architecture.md), D-31) and the owner requirements ([owner-requirements.md](owner-requirements.md)). The previous plan is copied read-only to `planning/_v1/` (input for reuse, never authority). Evidence: `analysis/` (X1 issues, X2 capabilities, X3 permissions, D1–D7 digests).

## Rules for every writer
1. Follow `new-architecture.md`; do not re-derive it. If it is silent or wrong, list an **open question** in the report; never decide it.
2. Services and prefixes: **GWY** gateway · **IDN** identity (incl. access/grants) · **CAT** catalog (incl. search, shelf, files) · **RDR** reader (incl. progress, annotations) · **ING** ingestion · **NTF** notify · **WEB** web · **PLT** platform · **NFR** non-functional · **OPS** operations. No `MIG` (D-32: fresh start).
3. Each requirement: ID, MUST/SHOULD, invariant, verification, and the legacy defect or feature it answers (X1/X3 id) where one exists.
4. Reuse `_v1` text only where the analysis supports it; note "kept from v1" or "changed" for the delta.
5. Do not copy legacy defects (see new-architecture §7). Acquisition is GET-only (D-03).
6. Edit only your files. The parent edits STATUS, DECISIONS, INCONSISTENCIES, traceability, indexes and `delta.md`.
7. At most 3 agents run at once (owner rule). Each writes incrementally.

## Waves

| Wave | Content | State (2026-11-19) |
|---|---|---|
| 0 | `_v1` copy, D-32, this file, STATUS | DONE |
| A | 00-charter, 01-discovery, 02-requirements (212 REQ), invariants register | DONE (+ passes applying D-33..D-44) |
| B | 04-architecture (ADRs 0025/0026, topology, data ownership, events), 07-contracts (6 services) | DONE |
| C | 05-services: gateway, identity, notify, web, catalog, reader, ingestion | DONE |
| D1 | D-45..D-48 applied across requirements, ADRs, services, contracts | DONE |
| D2 | 08-ux (screens, flows, design system) | DONE |
| D3 | 09-testing, 06-data (legacy-migration deleted) | DONE |
| E | 10-security, 11-operations (launch runbook replaces cutover; backups monthly D-33), 12-roadmap, 03-correctness (formal-models coverage: 39 `model` invariants unlisted) | DONE |
| F | coherence review (plan-reviewer x3), traceability regen, ADR-0015 to ACCEPTED, `delta.md`, README, STATUS | DONE (reviews R1-R3, fix passes A-B, delta.md) |

Plan check at this point: 0 errors expected after wave E (formal-model coverage gaps closed); wave F verifies. Open points: `open-points.md`. Next owner questions are asked when a wave needs them.

## Owner decision points expected
Reader presentation details (open detail of D-28), roles/scopes (X3 Q-X3-*), source permission (D-03), tooling installs (Docker, Rust, Node, Java), dependency batch. Writers return open questions; the parent asks them with `AskUserQuestion`.
