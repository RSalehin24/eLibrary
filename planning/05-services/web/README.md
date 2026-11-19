# web

Status: DRAFT (six-service design; D-02, D-16, D-25, D-26, D-39)

Everything the user sees: an Angular application on Angular Material (Material Design 3), server-side rendered on a Node server, talking to the backend only through the gateway with a client generated from the Rust contracts. Requirements: [WEB](../../02-requirements/web-ui.md). The reader renderer is specified with the [reader](../reader/README.md).

| | |
|---|---|
| Responsibilities | pages, navigation, forms, reader UI host, operator and admin workspaces, SEO of public pages, theming, bn/en i18n |
| Non-responsibilities | business rules, authorization (the UI only reflects `/me/capabilities`; the server is the authority), data storage (only theme and language choice persist client-side), file serving |
| Requirements | REQ-WEB-001...024 (table below) |
| Talks to | gateway only (generated TypeScript client); never to a service directly, never to `/internal/*` |
| Tech | strict TypeScript, Angular (standalone components, signals, strict templates; exact version features verified in spike S-02), Angular Material and CDK, Angular SSR, ESLint (typescript-eslint), Playwright; npm set approved as one batch after S-02 (D-20) |
| Container | `web`: Node SSR server (D-39), non-root, read-only root filesystem, behind Caddy; not static files |

## Screens (new-architecture section 8, REQ-WEB-014)

| Screen | Scope needed | Content |
|---|---|---|
| Sign-in and auth card shell | public | one card with steps: sign-in, TOTP, reset request and confirm, invite acceptance |
| Library | `browse` (public for metadata) | browse, search, filters, My Books and Sent-to-Kindle chips, facet tab bar, card/list toggle, saved filters, one filter sheet, filters and sort in the URL, Bengali-aware sorting |
| Book detail | `browse`; preview and Read need sign-in | tabs overview, metadata, files; Files shows download and Kindle with delivery status only when scopes allow; honest read-limit notice; Read opens the reader through a ticket |
| Reader | `read` | purpose-built renderer for the whole-book package; reading modes, typography, themes light, dark, sepia |
| Import workspace | `operate` (publishing is automatic, D-49) | catalog sync, requests, duplicate review, jobs, source credential status; bucket rail over one table component and one live stream (SSE) |
| Users and access | `manage_users` | invites, accounts, grants in a per-user detail drawer, batched atomic requests, audit view |
| Settings | session | theme (System, Light, Dark), language, profile and image, TOTP stepper dialog with re-authentication, own data export |

Navigation items are built only from the capability set; a missing capability hides the item and a route guard refuses the direct URL (REQ-WEB-003, 014).

## Structure

```
web/
  src/app/
    core/        generated client (read-only), session and capability store, i18n, error mapping, route table, guards, theme service, ticket store
    shared/      design-system compositions over Angular Material (the only place Material components are configured), PageState helpers, data table, confirm dialog
    features/    auth · library · book · reader · import · admin · settings
  src/styles/    M3 token schemes (light, dark, sepia), typography
  server.ts      SSR entry, request-scoped state only
  e2e/           Playwright journeys (hermetic)
```

Rules: features import `shared/` and `core/` only; no feature imports another feature; no HTTP call outside `core/`; no hard-coded colour or size, tokens only; one typed route table is the only source of routes and links (REQ-WEB-004); `any`, non-null assertions and unchecked casts only inside the generated boundary (REQ-WEB-013).

## State discipline (REQ-WEB-001, 002)

Every page renders from `PageState<T> = Loading | Empty | Ready<T> | Failed<ErrorCode> | Forbidden<DenyReason> | NotFound | Offline` with an exhaustive `match` helper so a missing variant fails compilation. Server state lives in resource signals per feature; UI-only state in component signals; no global mutable store besides session, capabilities and theme. Forms keep state across orientation change and reconnect.

## 401 versus 403 (REQ-WEB-002, 003, 020)

| Status | Client behaviour |
|---|---|
| 401 `unauthenticated` | clear session state, go to sign-in, keep the target route for return |
| 403 `forbidden` | inline "not allowed" with the reason mapped to text; the session stays |
| 403 `mfa_required` | go to the TOTP step |
| 403 `csrf_invalid` | refresh the session response (new token) and retry once |
| 429 / 503 / 504 | retry with backoff for reads; show the typed message; form state kept; no browser health poll and no forced reload |

Mutations use the cookie plus the `X-CSRF-Token` delivered with the session response, so no extra GET precedes a mutation.

## Generated client (REQ-WEB-013, 023)

`xtask codegen` turns the Rust contract schema into `core/api/generated/` (types and typed client). The directory is read-only for humans; CI fails if regeneration changes it. API mocks in tests come from the same schema; tests import real units; end-to-end tests are hermetic with no fixed sleeps; every acceptance criterion maps to a test.

## Rendering and SSR (REQ-WEB-022, 024)

| Area | Rendering |
|---|---|
| Library browse, search, book detail (metadata only) | server-rendered and hydrated: title, canonical URL, meta tags and structured metadata in the first HTML; indexable |
| Preview text, reader, settings, admin, import | client-side after sign-in; preview marked `noindex` (D-34, D-09) |
| Auth screens | server-rendered shell, client forms |

SSR runs with request-scoped state only (no cross-request cache of user data) and forwards no cookie to public metadata calls. Who sets security headers on pages is **OPEN (O-2)**.

## Reading ticket (REQ-WEB-021)

The ticket lives only in memory in `core/ticket`, never in a URL, storage or log; it is sent in the `X-Reader-Ticket` header; refreshed once on expiry (`ticket_expired`); unsaved progress flushed on `visibilitychange`/`pagehide`. Reader preferences (font, theme) are stored per user; where (reader service or identity) is **OPEN (O-6)**.

## Responsive and visual rules (REQ-WEB-005..010, 012)

- Window classes: compact (under 600 px), medium (600-839), expanded (840-1199), large (1200 and up), from the CDK `BreakpointObserver` into a `WindowClass` signal; navigation bottom bar, rail, drawer; tables collapse to lists on compact; no horizontal page scroll from 360 to 1920 px; components never read `window.innerWidth`. SSR renders compact and hydrates without layout shift.
- Themes: one M3 token set drives light, dark and sepia (sepia only in the reader); default follows `prefers-color-scheme`; a persisted choice (System, Light, Dark) is applied before first paint from a cookie or an inline script; "System" always resolves to a concrete value; no per-component override; every colour is a token, contrast meets WCAG 2.2 AA (4.5:1 text, 3:1 UI).
- Minimalist: flat tonal surfaces, whitespace, elevation only on overlays, error colour only for failure or destruction, no gradients, glass blur or entrance animation, no emoji labels.
- Accessibility: keyboard operable, visible focus, 48 px targets, labels, focus-trapped dialogs, live regions, reduced motion, 200% text scale.
- Typography: self-hosted Noto Sans Bengali (UI) and Noto Serif Bengali (reading), line height 1.6-1.75, no uppercase transform, no positive letter spacing.

## i18n (REQ-WEB-011)

`bn` and `en` message catalogs with identical key sets (a missing key fails the build); default from `Accept-Language`, fallback Bengali; the language choice persists; times shown in the viewer's zone or configured zone (REQ-PLT-011); error messages come from catalogs keyed by error code.

## Failure behaviour

Gateway 503 and offline give `Offline` or `Failed` states with retry; SSE loss reconnects with backoff and a versioned snapshot; SSR failure of a public page falls back to the client shell with a typed error page, never a fake "application restarted" message.

## Requirements covered

| REQ | Where in this design | Tests |
|---|---|---|
| REQ-WEB-001 | State discipline | typecheck, review; e2e state matrix |
| REQ-WEB-002 | 401 versus 403 | unit, e2e sign-in redirect and 403 keeps session |
| REQ-WEB-003 | Screens, capability store, guards | unit guard tests, e2e per role |
| REQ-WEB-004 | Structure (route table) | link checker e2e, NotFound |
| REQ-WEB-005 | Visual rules | review, e2e |
| REQ-WEB-006 | Visual rules | review, screenshot checks |
| REQ-WEB-007 | Themes | e2e theme and first-paint tests |
| REQ-WEB-008 | Themes | automated contrast checks both themes |
| REQ-WEB-009 | Responsive | e2e 360 to 1920 px, orientation |
| REQ-WEB-010 | Accessibility | e2e a11y, keyboard, 200% scale |
| REQ-WEB-011 | i18n | build check on keys, unit |
| REQ-WEB-012 | Typography | review, bn rendering e2e |
| REQ-WEB-013 | Generated client | codegen no-diff, static lint |
| REQ-WEB-014 | Screens | review |
| REQ-WEB-015 | Library | e2e filters in URL, chips, toggle |
| REQ-WEB-016 | Book detail | e2e tabs, scope-gated actions, read notice |
| REQ-WEB-017 | Import workspace | e2e bucket rail, confirm, snackbar results |
| REQ-WEB-018 | Users and access | e2e batched grants, drawer |
| REQ-WEB-019 | Settings | e2e re-auth stepper, preferences |
| REQ-WEB-020 | 401 versus 403 (CSRF, backoff) | unit, e2e |
| REQ-WEB-021 | Reading ticket | type test, e2e expiry refresh, page-hide flush |
| REQ-WEB-022 | Rendering and SSR | e2e first-HTML checks, noindex on preview |
| REQ-WEB-023 | Generated client | review, CI |
| REQ-WEB-024 | Container, Rendering | review, e2e |

The detailed test rows for the web live in the [testing strategy](../../09-testing/strategy.md); there is no separate web test-plan file.

## Related

[UX principles](../../08-ux/principles.md) · [route map](../../08-ux/route-map.md) · [design system](../../08-ux/design-system.md) · [Bengali typography](../../08-ux/bangla-typography.md) · [accessibility](../../08-ux/accessibility.md) · [coding standards](../../03-correctness/coding-standards.md) · [HTTP conventions](../../07-contracts/http/README.md)
