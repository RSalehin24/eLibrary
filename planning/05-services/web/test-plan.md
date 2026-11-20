# web - test plan

Status: DRAFT

Levels: `unit` (Angular runner, real units, schema-generated mocks), `type`, `e2e` (Playwright on the Compose stack, hermetic, no fixed sleeps), `static`. Every acceptance criterion of REQ-WEB maps to a row. Journeys and environments: [testing strategy](../../09-testing/strategy.md).

| ID | Level | Behaviour | REQ |
|---|---|---|---|
| TST-WEB-001 | type, e2e | `PageState` has Loading, Empty, Ready, Error, Forbidden, NotFound, Offline; a missing variant fails compilation; each state rendered in the matrix | REQ-WEB-001 |
| TST-WEB-002 | unit, e2e | 401 goes to sign-in and keeps the target; 403 keeps the session and shows the reason; `mfa_required` goes to TOTP | REQ-WEB-002, 020 |
| TST-WEB-003 | unit, e2e | guards and navigation built from capabilities, per role (reader, operator, admin); direct URL refused | REQ-WEB-003, 014 |
| TST-WEB-004 | e2e | link checker over the typed route table; unknown route gives NotFound | REQ-WEB-004 |
| TST-WEB-005 | e2e, review | minimalist rules; screenshot checks at the three widths in both themes | REQ-WEB-005, 006 |
| TST-WEB-006 | e2e | theme: System, Light, Dark; applied before first paint; follows `prefers-color-scheme`; persists | REQ-WEB-007 |
| TST-WEB-007 | e2e | automated contrast checks (4.5:1 text, 3:1 UI) in both themes on every screen | REQ-WEB-008 |
| TST-WEB-008 | e2e | 360 to 1920 px, no horizontal scroll, orientation change keeps form state; window classes compact, medium, expanded, large | REQ-WEB-009 |
| TST-WEB-009 | e2e | axe, keyboard operation, focus visible, dialogs trap focus, 200% text scale, reduced motion | REQ-WEB-010, NFR-008 |
| TST-WEB-010 | unit, static | `bn` and `en` catalogs have identical keys (build fails otherwise); no hard-coded text | REQ-WEB-011, NFR-010 |
| TST-WEB-011 | e2e | Bengali rendering: conjuncts and vowel signs intact, self-hosted fonts, no uppercase transform | REQ-WEB-012 |
| TST-WEB-012 | static, CI | codegen produces no diff; `any`, non-null assertion and unchecked cast only in the generated boundary; no HTTP call outside `core/` | REQ-WEB-013, 023 |
| TST-WEB-013 | e2e | Library: filters and sort in the URL, chips, card/list toggle, saved filters, Bengali-aware sort | REQ-WEB-015 |
| TST-WEB-014 | e2e | Book detail: tabs, scope-gated download and Kindle actions, honest read-limit notice, Read opens through a ticket | REQ-WEB-016 |
| TST-WEB-015 | e2e | Import workspace: bucket rail, confirm dialogs, snackbar results, live SSE update and reconnect with snapshot | REQ-WEB-017 |
| TST-WEB-016 | e2e | Users and access: batched atomic grants, per-user drawer, audit view | REQ-WEB-018 |
| TST-WEB-017 | e2e | Settings: re-authentication stepper for TOTP, preferences, own data export | REQ-WEB-019 |
| TST-WEB-018 | unit, e2e | CSRF refresh and one retry; backoff on 429, 503, 504; no health poll; form state kept | REQ-WEB-020 |
| TST-WEB-019 | type, e2e | ticket held in memory only (not in URL, storage, logs); header `X-Reader-Ticket`; one refresh on `ticket_expired`; progress flushed on `visibilitychange` and `pagehide` | REQ-WEB-021 |
| TST-WEB-020 | e2e | first HTML of public pages carries title, canonical, meta, structured metadata; preview is `noindex`; SSR keeps no cross-request user state; SSR failure shows a typed page | REQ-WEB-022, 024 |

Security headers on pages are **OPEN (O-2)**.
