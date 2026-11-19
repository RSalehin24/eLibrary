# ADR-0014 — Frontend: TypeScript with Angular and Angular Material (Material Design 3)

Status: ACCEPTED

## Context
The owner wants Google's Material UI. Findings (2026-11-17 web check; see [DECISIONS](../../DECISIONS.md) D-02/D-16): Angular Material is Google-maintained and provides Material Design 3 theming (official guide: Sass theming APIs from v19); Google's framework-agnostic Material Web components are in maintenance mode; MUI (React) still implements Material Design 2 officially; no Material 3 library for Rust UI frameworks was found; Flutter web renders to a canvas (poor for SEO, screen readers and Bengali text selection).

## Decision
- UI language: **TypeScript (strict)**; framework: **Angular**; components and design language: **Angular Material + CDK, Material Design 3** (themes via the library's theming API, tokens mapped in [design system](../../08-ux/design-system.md)).
- Rust remains the language of all backend and shared domain code (ADR-0001). The UI consumes **TypeScript types and clients generated from the Rust contract schema** (ADR-0004); hand-written wire types are forbidden.
- Public pages are server-side rendered (D-39): the `web` container is an Angular SSR server on Node, not static files. Account pages use the same app with hydration; verify configuration and version in spike S-02.
- The reader implements the `ReaderHost` interface (see [web](../../05-services/web/README.md)) as an Angular feature; it receives the whole rendered book from the reader service under a reading ticket and renders it in the browser ([ADR-0023](0023-reader-renders-whole-book.md); ADR-0016 is superseded).
- Page states are discriminated unions with exhaustiveness checks (`never`), preserving INV-WEB-001 at compile time.

## Verified facts (2026-11-17; evidence in the [verification log](../../03-correctness/verification-log.md))
- angular.dev release table: Angular **v22** is Active (released 2026-06-03), v21 LTS, v20 LTS ending 2026-11-28 → use **v22**.
- `@angular/material` 21.2.6 package listing contains M3 style files (`_m3-*.scss`) for button, card, dialog, chips, badge, etc.; component folders include bottom-sheet, sidenav, toolbar, button-toggle, datepicker, timepicker, tree, stepper. **Not present:** navigation rail, navigation bar, side sheet, search (and no breadcrumb) → built in `shared/`.
- Angular CLI default unit-test runner is **Vitest** (+ jsdom); Karma still supported.
- SSR and hydration pages carry no "developer preview" label; hydration documents caveats (custom/noop Zone.js unsupported, invalid HTML, direct DOM manipulation).
- Not verified: Angular Material's official docs pages (client-rendered, unreadable), "Material 3 Expressive" support, zoneless status.

## Consequences
+ Real Material 3 maintained by Google; strong accessibility primitives (CDK); mature SSR; large pool of documentation.
+ Contract drift stays impossible: generated types fail the build on mismatch.
− Second language and toolchain (Node, TypeScript, Angular CLI), and Node is also a runtime container (SSR); npm dependency tree is large — every package goes through the [dependency register](../dependency-policy.md) with the lockfile managed by the package manager.
− Angular major-version churn: pin versions, upgrade deliberately, one major at a time.
− Component or Expressive-style gaps are possible; spike S-02 compares the component list with the screen inventory and Bengali typography before gate G4. A gap is handled by composing from CDK + tokens inside the design system, never by adding a second UI library without approval.
− Reopen this ADR if S-02 shows blocking gaps (accessibility, Bengali selection/anchoring, performance budgets).
