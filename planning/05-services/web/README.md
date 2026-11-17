# web

Status: DRAFT

Everything the user sees. Decisions pending: [D-02](../../04-architecture/open-decisions.md), [ADR-0014](../../04-architecture/adr/0014-frontend-technology.md).

| | |
|---|---|
| Responsibilities | pages, navigation, forms, reader UI, admin workspaces, SEO, theming, i18n |
| Non-responsibilities | business rules, authorization (UI only reflects `abilities_hint`), data storage |
| Requirements | REQ-WEB-001…009 |
| Talks to | gateway only, through generated clients |

## Structure

| Area | Rendering | Notes |
|---|---|---|
| Public (home, search, book, taxonomy, auth) | server-rendered, minimal JS | SEO, speed, works without JS for browsing and search |
| Reader | client-side island | implements `ReaderHost` below |
| Account (shelf, notes, profile) | SSR shell + islands | |
| Admin (Sources, Jobs, Review, Catalog, Accounts & Access, Audit) | SSR shell + islands, SSE for jobs | |

## `ReaderHost` interface (stable boundary)

```
load_index(book) → SectionIndex
load_section(book, section_id) → ChapterHtml
report_position(book, anchor, percent)
create_annotation(anchor, kind, note?) / resolve_annotation(anchor) → Location | Orphaned
settings: font_family, size, line_height, theme (light|dark|sepia), margins — persisted per account (fallback localStorage)
events: opened, closed, section_changed, capability_expiring
```
The implementation behind it may be Rust/WASM or TypeScript (spike S-02). It receives only chapter HTML and the section index — never the EPUB (ADR-0016).

## Page state discipline

Every page is a total function from `PageState` (Loading | Empty | Ready(data) | Error(code) | Forbidden | NotFound | Offline) to markup; adding a state is a compile error everywhere (INV-WEB-001).

## Related

[UX principles](../../08-ux/principles.md) · [route map](../../08-ux/route-map.md) · [design system](../../08-ux/design-system.md) · [Bengali typography](../../08-ux/bangla-typography.md)
