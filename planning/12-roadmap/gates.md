# Phase exit gates

Status: DRAFT

A gate is a checklist of **evidence**. Work in the next phase (except the explicitly parallel tracks in [phases](phases.md)) does not start until the gate passes. The owner signs each gate in `gate-log.md` (date, commit, evidence links).

| Gate | After | Evidence required |
|---|---|---|
| **G0 Foundations** | P0 | (1) Decisions D-05, D-07, D-08, D-10 answered (D-01, D-02, D-04, D-16 already decided; D-03 stance decided, written permission still to be obtained); spike S-02 confirms the Angular Material choice or ADR-0014 is reopened; D-03 answered or ingestion go-live explicitly blocked; (2) gold corpus: ≥ 140 dev books labeled, 60 holdout labeled, label guidelines written; (3) spikes S-01…S-07 closed with ADR updates; (4) risk register reviewed; (5) `check_plan.py` passes; (6) requirement list approved by the owner |
| **G1 Platform** | P1 | Foundational dependency set approved by the owner and recorded; lint names/thresholds verified against the installed toolchain and enforced (shape rules from the owner's AGENTS.md); `CLAUDE.md`/`crates/AGENTS.md` seeded; Workspace builds; lint set (T-9) on; dependency-rule check (Q6) green; CI Q1–Q7 green; `domain-text` property tests + collation; `platform-*` crates with tests; startup-check framework (INV-PLT-001) demonstrated by a sample service; contract codegen + diff works |
| **G2 Models** | P2 | TLC passes JobLifecycle, ReadOnce, Outbox, AccountLifecycle, BookLifecycle, Publication, Progress; Alloy `access.als` assertions hold; coverage.md all `checked` with commit hash; any counterexample resolved and recorded; Q8 in CI |
| **G3 Identity & access** | P3 | All IDN/ACC requirements implemented with passing TST-IDN-*/TST-ACC-*; `decide` passes Alloy-mirrored property tests (≥ 1M cases) and Kani bounded proof; capability fuzzing clean; walking skeleton: invite → set password → TOTP → login → grant → `decide` via gateway; demo account verified read-only; security review of auth flows (threat model T-03…T-07, T-11) |
| **G4 Public discovery** | P4 | Material 3 theme (light/dark/sepia) generated from the signed-off seed colors, component coverage table complete, generated TS client in CI; Clickable prototypes of book page, search, home **signed off by the owner**; catalog + search + web public pages live in staging with ≥ 200 migrated/seed books; DSC thresholds met (MRR@10 ≥ 0.85, recall@20 ≥ 0.95); leak canary test green; a11y scan 0 serious/critical; Lighthouse budgets met; SEO checks; D-09 applied |
| **G5 Reading** | P5 | Reader prototype signed off by the owner; content + library implemented; read-once race test; capability expiry/renewal; re-anchor ≥ 99% on mutation set; EPUB determinism and epubcheck on gold outputs; cross-browser reader journeys green; screen-reader check of reader journey |
| **G6 Ingestion** | P6 | Gold dev+holdout metrics meet targets (rulesets README), conservation 100%, determinism 100%, epubcheck 0 errors; promotion gate demonstrated (bad ruleset rejected); fault-injection FI-01/02/12 green; Review workspace usable (owner sign-off); duplicate policy 100% on labeled pairs; D-03 resolved; canaries running |
| **G7 Completeness** | P7 | Remaining requirements implemented; every REQ has passing verification (generated report `unverified = 0`); exports; Kindle via sink and one real send; audit viewer; inventory if kept |
| **G8 Hardening** | P8 | Load targets met; FI-01…FI-18 pass; security review of all T-IDs; pen-test checklist; restore drill within RTO; migration rehearsals ×2 with empty reconciliation; rollback rehearsed; runbooks exercised; final a11y audit (manual SR on five journeys); documentation current |
| **G9 Cutover** | P9 | Cutover runbook executed; 30-day stability; decommission sign-off |

## Rules

- A gate cannot be waived silently: a waiver is a dated entry in [waivers](waivers.md) with owner and expiry ≤ 30 days.
- Evidence is reproducible: each item links to a CI run, report, or file in the repository.
- If a gate fails twice, stop and re-plan the phase (scope reduction first, not gate relaxation).
