# Requirements — Notify (NTF), Gateway (GWY), Web (WEB)

Status: DRAFT

## Notify — [service](../05-services/notify/README.md)

- **REQ-NTF-001** · MUST · inv: INV-NTF-001 · verify: model, prop · Invitation and reset emails are sent once per issued link (idempotent by event id); transient failures retry with backoff; failures never block account creation.
- **REQ-NTF-002** · MUST · inv: INV-NTF-002 · verify: prop, e2e · A Kindle send requires an Allow decision for `SendToKindle`, a Kindle address on the account whose owner confirms that our sender address is on their Amazon "Approved Personal Document E-mail List" (Amazon rejects mail from other senders), a passing size/format preflight (total ≤ 50 MB per email; EPUB is accepted and converted by Amazon; DRM-free), and records one history entry per attempt.
- **REQ-NTF-003** · SHOULD · inv: INV-NTF-003 · verify: unit · Templates exist in Bengali and English and are selected by account language.
- **REQ-NTF-004** · MUST · inv: INV-NTF-004 · verify: type, unit · Links, tokens and addresses never appear in logs or error messages.

## Gateway — [service](../05-services/gateway/README.md)

- **REQ-GWY-001** · MUST · inv: INV-GWY-001 · verify: e2e, review · Internal service APIs are unreachable from the public edge; only routes in the [public route table](../05-services/gateway/routing-table.md) are exposed.
- **REQ-GWY-002** · MUST · inv: INV-GWY-002 · verify: e2e · Cookie-authenticated mutations require a CSRF token and SameSite cookies; cross-origin requests are rejected.
- **REQ-GWY-003** · MUST · inv: INV-GWY-003 · verify: e2e · Every request has a request id propagated to all services and logs.
- **REQ-GWY-004** · MUST · inv: INV-PLT-005 · verify: e2e · Rate limits apply per address and per subject, stricter for anonymous and authentication endpoints.
- **REQ-GWY-005** · MUST · inv: INV-GWY-004 · verify: e2e · Security headers (CSP, HSTS, frame, referrer, content-type) are set on every response.

## Web — [service](../05-services/web/README.md)

- **REQ-WEB-001** · MUST · inv: INV-WEB-001 · verify: type, review · Every page models its state as an exhaustive enum (Loading, Empty, Ready, Error, Forbidden, NotFound, Offline); a missing state is a compile error.
- **REQ-WEB-002** · MUST · inv: INV-WEB-002 · verify: e2e · The route table in [route map](../08-ux/route-map.md) is the only source of routes; a link checker fails on any dead internal link.
- **REQ-WEB-003** · MUST · inv: INV-WEB-003 · verify: e2e, review · WCAG 2.2 AA: keyboard operable, visible focus, contrast, screen-reader labels, reduced motion.
- **REQ-WEB-004** · MUST · inv: INV-WEB-004 · verify: review · Bengali typography follows [the typography guide](../08-ux/bangla-typography.md) (font stack, line height, no letter-spacing, correct conjunct rendering).
- **REQ-WEB-005** · MUST · inv: INV-WEB-005 · verify: e2e · Layouts work from 360 px to 1920 px with no horizontal page scroll.
- **REQ-WEB-006** · SHOULD · inv: INV-WEB-006 · verify: e2e · Light, dark and sepia themes follow tokens; user choice persists.
- **REQ-WEB-007** · MUST · inv: INV-WEB-007 · verify: e2e · Public pages are server-rendered, with sitemap, canonical URLs, Open Graph and structured data.
- **REQ-WEB-008** · MUST · inv: INV-WEB-008 · verify: review · Administration has exactly three ingestion workspaces — Sources, Jobs, Review — plus Catalog, Accounts & Access, Audit.
- **REQ-WEB-009** · SHOULD · inv: INV-WEB-009 · verify: unit · UI strings come from catalogs for `bn` and `en`; missing keys fail the build.
- **REQ-WEB-010** · MUST · inv: INV-WEB-010 · verify: review, e2e · The UI follows Google Material Design 3 through Angular Material and CDK: components come from the library or from CDK primitives in `shared/`, themes are generated M3 schemes (light, dark, sepia), and no second UI component library is used without owner approval ([design system](../08-ux/design-system.md)).
- **REQ-WEB-011** · MUST · inv: INV-WEB-011 · verify: type, e2e · The web app is strict TypeScript; all wire types and the API client are generated from the Rust contract schema; `any`, non-null assertions and unchecked casts do not appear outside the documented generated boundary ([coding standards §16](../03-correctness/coding-standards.md)).
