# Open decisions (need the owner's answer)

Status: DRAFT

Each decision blocks a named gate. A recommendation is given so a "yes" is enough. Answered decisions move to [DECISIONS](../DECISIONS.md). Questions are asked as selectable questions (see CLAUDE.md). Source: `_replan/open-points.md` (raised by plan writers 2026-11-19); not decided here.

| ID | Decision | Options | Recommendation | Blocks |
|---|---|---|---|---|
| O-1 | Add a `user.deleted` event (account deletion by an admin, D-30) to the event list | (a) add it; (b) rely on `user.disabled` plus resynchronization | (a): consumers must remove the user's reading state and shelves | events and data-ownership design |
| O-2 | Who sets security headers (CSP, HSTS, frame, referrer) | (a) gateway for API responses, `web` for pages, Caddy only HSTS; (b) Caddy for all | (a) | gateway, web and Caddy design |
| O-3 | Work/edition grouping | (a) not modelled, only the human "new edition" action; (b) model works and editions | (a): not needed at this scale | catalog data model |
| O-4 | Scope guarding CSV export and book deletion | (a) `manage_catalog`; (b) new dedicated scopes | (a) | scope table (X3) and catalog contract |
| O-5 | Search relevance gate (MRR/recall on the gold corpus) strength | (a) SHOULD; (b) MUST | (a): at this scale | search design, test plan |
| O-7 | NFR numbers (latency, 10 rps, 8 GB, 100 GB, 1 MB body, 100-row page, 5,000-row CSV, 90 s start) | (a) accept as provisional until the P0 baseline; (b) fix now | (a) | non-functional requirements |
