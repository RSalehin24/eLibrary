# web

Status: DRAFT

Everything the user sees. Decided: [ADR-0014](../../04-architecture/adr/0014-frontend-technology.md) — TypeScript, Angular, Angular Material (Material Design 3).

| | |
|---|---|
| Responsibilities | pages, navigation, forms, reader UI, admin workspaces, SEO, theming, i18n |
| Non-responsibilities | business rules, authorization (UI only reflects `abilities_hint`), data storage |
| Requirements | REQ-WEB-001…011 |
| Talks to | gateway only, through the generated TypeScript client |
| Language & tooling | TypeScript (strict), Angular (standalone components, signals, strict templates — verify exact version features in S-02), Angular Material + CDK, Angular SSR with hydration, ESLint (typescript-eslint), Playwright |

## Structure

```
web/
  src/app/
    core/        generated API client (read-only, generated), session/subject, i18n, error mapping, guards
    shared/      design-system wrappers over Angular Material (the only place Material components are configured)
    features/    public (home, search, book, taxonomy, auth) · reader · library · admin (sources, jobs, review, catalog, accounts, access, audit)
  src/styles/    theme (M3 tokens), typography (Bengali), global
  e2e/           Playwright journeys
```
Rules: features import `shared/` and `core/` only; no feature imports another feature; no raw HTTP calls outside `core/`; no component styles using hard-coded colors or sizes (tokens only).

## Rendering

| Area | Rendering | Notes |
|---|---|---|
| Public (home, search, book, taxonomy, auth) | server-rendered + hydrated | SEO, speed; browse and search remain usable before hydration where practical |
| Reader | client-side feature | implements `ReaderHost` |
| Account (library, notes, profile) | SSR shell + client | |
| Admin | client-side with SSE for jobs | |

## `ReaderHost` interface (stable boundary)

```ts
interface ReaderHost {
  loadIndex(book: BookId): Promise<SectionIndex>;
  loadSection(book: BookId, section: SectionId): Promise<ChapterHtml>;
  reportPosition(book: BookId, anchor: Anchor, percent: Percent): void;
  createAnnotation(anchor: Anchor, kind: AnnotationKind, note?: string): Promise<Annotation>;
  resolveAnnotation(anchor: Anchor): Promise<Location | Orphaned>;
}
```
Settings (font family/size, line height, theme light/dark/sepia, margins) persist per account with a local fallback. It receives chapter HTML and the section index only — never the EPUB (ADR-0016). Offsets are computed over grapheme clusters.

## Page state discipline

Every page renders from `type PageState<T> = Loading | Empty | Ready<T> | Failed<ErrorCode> | Forbidden<DenyReason> | NotFound | Offline` with an exhaustive `switch` helper that fails compilation when a variant is unhandled (INV-WEB-001).

## Generated client

`xtask codegen` turns the Rust contract schema into `core/api/generated/` (types + typed client). The directory is read-only for humans; CI fails if regenerating changes it (Q3).

## Related

[UX principles](../../08-ux/principles.md) · [route map](../../08-ux/route-map.md) · [design system](../../08-ux/design-system.md) · [Bengali typography](../../08-ux/bangla-typography.md) · [coding standards §16](../../03-correctness/coding-standards.md)
