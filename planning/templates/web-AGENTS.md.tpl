# web/AGENTS.md — TypeScript/Angular addendum  [template: copy to web/AGENTS.md in phase P4]

Applies on top of the root AGENTS.md. Full text: `planning/03-correctness/coding-standards.md` §16 and `planning/08-ux/design-system.md`.

- Strict TypeScript; no `any`, no `!`, no unchecked casts; wire types only from `core/api/generated` (never hand-edit).
- Functions ≤ ~20 lines, ≤ 3 parameters, ≤ 2 nesting levels, no boolean flag parameters.
- Standalone, OnPush components; signals for state; presentational/container split; no logic in templates.
- Page state is a discriminated union with exhaustive handling (`assertNever`).
- Material Design 3 via Angular Material + CDK only; tokens for color/typography/shape; no hard-coded theme values, no `!important`, no extra UI library.
- No HTTP outside `core/`; no `innerHTML` except the approved sanitizing component; strict CSP.
- All strings via i18n catalogs (bn, en); Bengali typography per `planning/08-ux/bangla-typography.md`.
- Tests deterministic; Playwright journeys for flows; axe clean.
- npm packages only if approved in the register; lockfile only via the package manager.
