# Builder - EPUB, preview, cover

Status: DRAFT (reconciled: runs in the ingestion worker as the `build` job; output is a candidate sent to catalog by the `publish` job)

Pure, deterministic functions of the curated document and the builder version. The build runs in `ingestion-worker`; there is no `content` service. The output is a candidate on the ingestion volume and is never visible until catalog approves it ([orchestration](../orchestration/README.md)).

## Page order (fixed; empty pages omitted)

| # | Page | Condition |
|---|---|---|
| 1 | Cover | always (source image or generated), picture page |
| 2 | Title page | always |
| 3 | Book information (বই বিষয়ক তথ্য) | only if key-value info exists |
| 4 | Dedication (উৎসর্গ) | only if a dedication exists |
| 5 | Front sections | 0..n, only with real content |
| 6 | Table of contents | always, exactly one, content chapters only, nested |
| 7 | Chapters | at least 1 |
| 8 | End sections | 0..n |

Navigation (nav document and NCX) lists all pages 1-8 with nesting; the in-book TOC page lists only 7. Both come from the one `SectionTree` (INV-ING-003, INV-CON-007). The package adds no front TOC page beyond the nav document.

## Book Information page

Key-value lines only, in this order: title, writer, translator, editor, compiler, publisher, series/type, publishing date/edition, publisher address, other. Labels in the book's language only (English books get English labels, checked by a lint on the label tables `labels_bn`/`labels_en`). Prose never appears here. A value shown here is removed from front sections (INV-ING-008).

## Rules for the writer

| Concern | Rule |
|---|---|
| Escaping | XHTML is produced by a templating step with HTML escaping always on; titles, metadata and attribute values are escaped; scraped text is never concatenated into markup |
| Sanitizing | every section's HTML passes the allow-list sanitizer (`SafeHtml`): no script, event handlers, external loads, unknown URL schemes; idempotent (INV-CON-009) |
| Images | images fetched during scrape are validated by magic bytes and size, packaged under `OEBPS/images/`, links rewritten; a missing image is a validation issue, never a silent drop; no external URLs remain |
| Fonts | Noto Serif Bengali regular and bold (SIL OFL, embedding allowed; licence file kept with the asset) embedded under `OEBPS/fonts/` and referenced by `@font-face`; the generated cover uses the same font |
| OPF | complete: `dc:identifier` (`urn:uuid:` UUIDv5 over book id and doc hash), title, `dc:language`, creators with roles, publisher, date, series metadata, `dcterms:modified` fixed from the document (not the wall clock), cover-image property |
| Navigation | both the EPUB 3 `nav.xhtml` (`epub:type="toc"` plus landmarks) and an NCX file, generated from the same tree (Kindle compatibility) |
| Structure | `mimetype` first and stored; `META-INF/container.xml`; one stylesheet; reproducible ZIP: fixed entry order, fixed timestamps, fixed compression level, no extra fields (INV-CON-002) |
| Chapter markup | the same sanitized XHTML body as in the EPUB, carrying stable `data-section-id`; the reader parses the EPUB itself (D-28) |

## Validation gate (audit)

The in-process audit must pass before the artifact becomes `built`; otherwise `audit_failed`, a `BuildFailed` review item and no publish:

1. ZIP structure; XML well-formedness of every XHTML, OPF, nav and NCX.
2. Manifest, spine and files consistent; spine order equals tree leaves; nav links equal TOC-page links equal the tree; NCX equals nav.
3. All referenced images and fonts present; no external URLs; filename safety; no blank page; no empty chapter above the single configured threshold; every internal href resolves.
4. Cover glyph coverage: any `.notdef` glyph aborts the build (no tofu, INV-CON-008).

`epubcheck` runs in CI on all gold outputs (not at runtime), and a second CI build must be byte-identical.

## Cover

1. A source cover image is used when it decodes and meets the minimum size (otherwise flagged); format normalized, original hash kept.
2. Otherwise a portrait cover (2:3) with title and author is generated with the embedded Bengali font and a text shaper, contrast at least 4.5:1, series line if present. Any shaping or rasterisation crate needs owner approval (dependency policy); the generated-cover method is therefore an open item (reported to the owner, not decided here).

## Preview

A `preview` HTML asset built from the allow-list: cover reference, metadata, summary, TOC and the first N characters of the first chapter cut at a paragraph boundary. Catalog re-sanitizes it on intake.

## Output and hand-off

Written to `/data/ingestion/build/`, recorded in `build_artifacts` with `build_hash` (the catalog `Idempotency-Key`). Only the `publish` job sends it, and only when the state is `built`.
