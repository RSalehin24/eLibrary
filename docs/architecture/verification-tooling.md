# Cross-browser verification tooling

The existing frontend has Playwright 1.53.0 and an installed Chromium 138
bundle. The new workspace checks can use that installation initially, but
the final browser matrix needs current supported tooling.

The user approved adding `playwright` **1.64.0** on 2026-10-16 to the new
`app/web` development dependencies and installing its matching browser bundles:

| Bundle | Upstream version | Revision |
| --- | --- | --- |
| Chromium / headless shell | 156.0.8078.4 | 1248 |
| Firefox | 157.0 | 1555 |
| WebKit | 27.2 | 2370 on this macOS 27 host |
| FFmpeg browser support bundle | Supplied by Playwright | 1013 |

The package requires Node >=20; the local runtime is Node 22. The existing
frontend's manifest and test runner remain intact. The new tests resolve
Playwright from `app/web`. No production dependency is added.

Sources checked on 2026-10-12:
[Playwright package](https://registry.npmjs.org/playwright/1.64.0),
[publisher's browser revisions](https://github.com/microsoft/playwright/blob/v1.64.0/packages/playwright-core/browsers.json).

## Lint compatibility limitation

The approved ESLint 9.39.4 pin installs and passes the framework rules, but npm
reports that it is no longer supported. ESLint 10.12.0 supports the local Node
runtime. The current `eslint-plugin-react` 7.37.5 bundled through the approved
Next.js rules only declares ESLint support through `^9.7`.

No peer checks or lint rules have been disabled, and ESLint has not been force
upgraded. On 2026-10-16 the user approved a temporary exception to the plan's
supported-tooling requirement: retain the compatible ESLint 9.39.4 pin until
the framework's React lint plugin supports ESLint 10. This exception does not
waive linting or any functional acceptance criterion.

Sources:
[ESLint 10.12.0](https://registry.npmjs.org/eslint/10.12.0),
[React lint plugin compatibility](https://registry.npmjs.org/eslint-plugin-react/7.37.5).

`npm audit` also reported five high findings along the development-only
Next.js lint dependency chain ending in `braces` 3.0.3. The publisher has no
patched release for GHSA-vfj7-8cjw-p6xm. A forced downgrade of Next.js lint
configuration is not a safe dependency update. Record this as unresolved;
do not suppress the audit result.

Source: [publisher's advisory discussion](https://github.com/micromatch/braces/issues/84).

On 2026-10-16, `npm audit --omit=dev --json` reported zero production
vulnerabilities. The unresolved development findings remain a separate limitation.

The simulator continuation rechecked the publisher registry and both audits.
`braces` 3.0.3, `micromatch` 4.0.8, and `eslint-plugin-react` 7.37.5 remain the
latest releases. The newer Next lint patch 16.4.2 still depends on `fast-glob`
3.3.1, so updating it would retain the affected chain. The development audit
still reports five high findings and the production audit reports zero. No
lockfile, peer rule, lint rule, or audit result was bypassed. Registry metadata:
[braces](https://registry.npmjs.org/braces/latest),
[Next lint plugin 16.4.2](https://registry.npmjs.org/@next/eslint-plugin-next/16.4.2).

## Browser harness

The matching macOS bundles are installed. Firefox cannot launch on this macOS 27
host because its shared app-data directory is unavailable to command-line
launches, matching [upstream issue 42768](https://github.com/microsoft/playwright/issues/42768).
Firefox therefore runs in the matching Ubuntu Noble image:
`mcr.microsoft.com/playwright:v1.64.0-noble` at digest
`sha256:06a9939e57531807f8d5fd76ce44b53165ffb7d7501d87ab10e285c20b1e971f`.
The user authorized Docker simulation and the matching browser bundles.

`tests/web/container-browser.mjs` forwards the isolated container's loopback
frontend/API ports to the host while preserving trusted origin headers. Mount
the repository read-only and ignored test artifacts read/write. Fixtures stay
private and each complete run requires new accounts and links.

General tests block service workers for deterministic network fault injection.
Reader and PWA specs explicitly allow workers and exercise the actual production
worker and local interruption proxy. This follows [Playwright's routing guidance](https://playwright.dev/docs/api/class-browsercontext#browser-context-route):
requests handled by service workers cannot reliably be intercepted by routes.
Assertions identify the expected status message because PWA availability may
produce a separate status region on the same page. No functional check is skipped.

The user also approved development-only `types-reportlab==4.4.1.20250914` and
`types-qrcode==8.2.0.20260518`; requirements and constraints record them. Missing
legacy annotations were corrected without suppressing type errors.
