# Re-plan: derive the service list from the archived application

Status: DRAFT

Purpose: replace the current service split (identity, access, catalog, content, library, ingestion, notify + gateway) with the **best** split, derived from evidence in the archived application and the owner's requirements. The current plan is an **input to mine, not a constraint**: every item is re-justified or dropped.

## 1. Fixed requirements (owner, not up for re-derivation)

| # | Requirement | Source |
|---|---|---|
| F1 | New project from the ground up; legacy lives in `archive/` | 2026-11-18 |
| F2 | Backend in Rust; microservice style | D-11 |
| F3 | Web UI uses Material (Angular Material, M3); responsive for mobile, tablet, desktop | D-02/D-16/D-25 |
| F4 | Developed in Docker Compose and deployed as a Compose stack, **each service its own container** | D-22 |
| F5 | The reader is **its own service**, and it is an **EPUB reader** (exact meaning: open question Q-R1) | 2026-11-18 |
| F6 | One developer, part-time: operational surface must stay small (C-2) | charter |
| F7 | No dependency without approval; commit only when asked | CLAUDE.md |
| F8 | Minimalist aesthetic, light and dark mode both first-class (every screen incl. reader); follows OS preference with a persisted manual toggle; M3 design tokens drive both themes; WCAG AA contrast | 2026-11-18 |

ANSWERED 2026-11-19 (D-28): the reader service renders and serves the whole book given the EPUB. Was: open question Q-R1 (asked): does "EPUB reader" mean (1) the service parses the EPUB server-side and serves chapters, (2) the browser renders the EPUB itself, or (3) both. It decides whether D-06/ADR-0016 survive. Answer before step 4.

## 2. Method (each step produces a file in `planning/_replan/`; nothing in the old plan is edited until step 6)

| Step | Work | Output | Done when |
|---|---|---|---|
| 1 Evidence harvest | Read-only subagents (Explore, one per area, disjoint) survey `archive/`: **A** backend domains, models, migrations, APIs; **B** frontend pages, flows, state; **C** EPUB/ingestion pipeline and the source adapter; **D** reader (embedded runtime, vendored reader, tokens, progress, highlights); **E** deployment, Celery/Redis jobs, tests, logs/ops; **F** real data volumes and usage from the database dump/fixtures, if any | `evidence-A…F.md` (≤ 1 page each: what exists, what hurt, sizes, file refs) | every claim has a file path |
| 2 Capability map | Merge evidence + F1–F7 + the old requirements (REQ-*) into one list of **capabilities** (not services), each with: data it owns, who writes/reads it, change rate, security sensitivity, load profile (read-heavy / bursty / long-running), failure blast radius | `capabilities.md` | every legacy feature and every REQ maps to a capability or is explicitly dropped with a reason |
| 3 Candidate splits | Generate at least 3 independent service lists from the map: **minimal** (≈ 4 services), **domain-driven** (≈ 6–8), **fine-grained** (≈ 10+). Each includes the reader as a service (F5). Old split is scored as one more candidate | `candidates.md` | each candidate lists services, owned data, sync/async edges |
| 4 Scoring | Score each service boundary on: data ownership clarity, independent change, failure isolation, scaling difference, security boundary, test/deploy cost on one host (memory per container, build time, Compose size), chatty-call count on the main journeys (browse → read → annotate; ingest → publish). Hard fail: a boundary that needs a distributed transaction on a core journey, or a service with no data and no isolation reason | `scoring.md` | scores shown with the evidence; weights stated up front |
| 5 Recommendation + owner choice | Present the best list (with the runner-up) and the container/memory budget. Owner picks through the selectable question (CLAUDE.md rule) | `recommended-services.md`, DECISIONS entry | owner decision recorded |
| 6 Re-plan | Regenerate the plan on the chosen list: old plan moves to `planning/_v1/` (read-only reference); new tree is rebuilt in parallel by `plan-writer` agents per service, reusing what survives scoring (requirements wording, invariants, TLA+/Alloy models, ingestion design, UX docs, gold-corpus method), re-mapped to the new owners | new `02…12` folders, new service READMEs/contracts/state machines, updated traceability | `check_plan.py` 0 errors; `plan-reviewer` consistency pass per service; INCONSISTENCIES logged |
| 7 Close | Summary in README/STATUS; list of what was kept, changed, dropped (with reasons) | `STATUS.md`, `_replan/delta.md` | owner reviews the delta |

## 3. Scoring weights (proposed; owner may change before step 4)

Data ownership 25 % · failure isolation 20 % · independent change 15 % · one-developer operability (container count, memory, build time) 20 % · journey chattiness 10 % · scaling difference 10 %.

## 4. Guardrails

- The old plan is read as data; a decision survives only if the evidence or a fixed requirement supports it.
- Subagents are read-only and disjoint, return ≤ 8 lines plus a file path; the parent writes `_replan/` and merges.
- Memory caps and timeouts per CLAUDE.md for any measurement on the dump.
- No new dependencies or installs in this effort (it is analysis and documents only).
- Plan-check hook applies; `_replan/` files carry `Status:` lines.

## 5. Cost

Steps 1–5: about 6 read-only subagents plus the parent (medium). Step 6 is the large step (rewrites most of `planning/`), about one plan-writer per service plus reviewers. Steps 1–5 finish before anything is rewritten, so you can stop after the recommendation.
