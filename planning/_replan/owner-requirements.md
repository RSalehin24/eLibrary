# Owner requirements (single list)

Status: ACTIVE

One place for the owner's requirements for the rebuild and re-plan. Each is separate. IDs match `REPLAN.md` (F1-F8) and `DECISIONS.md`.

## Product and architecture

| ID | Requirement | Source |
|---|---|---|
| R-01 | New project from the ground up; the legacy app lives in `archive/` as read-only reference (F1, D-13, D-22) | 2026-11-18 |
| R-02 | Backend in Rust, microservice style (F2, D-11) | 2026-11-17 |
| R-03 | Each service runs in its own container | 2026-11-18 |
| R-04 | Developed in Docker Compose and deployed as a Docker Compose stack (F4, D-22) | 2026-11-18 |
| R-05 | The EPUB reader is its own service (F5). Answered 2026-11-19 (D-28): the reader service renders and serves the whole book given the EPUB (owner's words). Open detail: whether rendering is server-side HTML or the EPUB is passed whole to a browser renderer; resolve in the reader design. | 2026-11-18 |

## Frontend and design

| ID | Requirement | Source |
|---|---|---|
| R-06 | Material UI: Angular Material, Material Design 3 (F3, D-02, D-16, D-25) | 2026-11-17/18 |
| R-07 | Responsive on mobile, tablet and desktop (F3, D-25) | 2026-11-18 |
| R-08 | Minimalist aesthetic: restrained colour, generous whitespace, little visual noise (F8, D-26) | 2026-11-18 |
| R-09 | Light and dark mode, both first-class on every screen including the reader. Follows the OS preference by default, with a persisted manual toggle. M3 design tokens drive both themes. WCAG AA contrast. (F8, D-26) | 2026-11-18 |

## Re-plan method

| ID | Requirement | Source |
|---|---|---|
| R-10 | Understand the archived app by reading all of it, down to the smallest feature and action. Verify subagent claims against the code. Tell the owner when done. | 2026-11-18 |
| R-11 | Derive the best service list from the archived app plus these requirements. Existing planning content is reused where evidence supports it, but must not drive the result. | 2026-11-18 |
| R-12 | Then recreate the planning on the chosen service list. The old plan moves to `planning/_v1/`; write `_replan/delta.md` (kept, changed, dropped, with reasons). | 2026-11-18 |
| R-13 | Do not copy the old app's defects (see `REPLAN.md` and the `_replan/features/` reports) | 2026-11-18 |

## Standing rules (from `CLAUDE.md`)

- Ask decisions with `AskUserQuestion`, recommended option first.
- No new dependencies without approval.
- Commit only when asked.
- Keep `check_plan.py` at 0 errors.

## Decisions recorded 2026-11-19

- D-27: 5 services, no gateway (identity, catalog, reader, ingestion, notify).
- D-28: reader renders and serves the whole book given the EPUB.
- D-29: small scale (under 5,000 books, under 50 users).
