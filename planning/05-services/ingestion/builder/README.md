# Builders — EPUB, HTML, preview, cover

Status: DRAFT

Pure, deterministic functions of `CanonicalDocument` (crate `domain-builders`, executed by the content service).

## Page order (fixed; empty pages omitted)

| # | Page | Condition |
|---|---|---|
| 1 | Cover | always (source image or generated) — picture page |
| 2 | Title page | always |
| 3 | Book information (বই বিষয়ক তথ্য) | only if key-value info exists |
| 4 | Dedication (উৎসর্গ) | only if a dedication exists |
| 5 | Front sections | 0..n, only with real content |
| 6 | Table of contents | always, exactly one, **content chapters only**, nested |
| 7 | Chapters | ≥ 1 |
| 8 | End sections | 0..n |

Navigation (EPUB nav/NCX, reader sidebar) lists *all* pages (1–8) with nesting; the in-book TOC page lists only 7. Both are rendered from the one `SectionTree` (INV-ING-003). The EPUB package must not add its own front TOC page beyond the nav document (spec).

## Book Information page

Key–value lines only, in this order: title, writer, translator, editor, compiler, publisher, series/type, publishing date/edition, publisher address, other KV. Labels in the book's language only (English books get English labels). Prose never appears here. A value appearing here is removed from front sections (INV-ING-008).

## Cover

1. If the source has a cover image: validate (decodes, ≥ 600×800 or flagged), normalize format, keep original hash.
2. Else generate: portrait 1600×2400 (2:3), dark-mode card palette from the design tokens, title and author text laid out with a real shaper (`rustybuzz` + a pinned Bengali-capable font such as Noto Serif Bengali, with Latin fallback), wrapped by measured width, min contrast 4.5:1; series line if present; rendered through `resvg`/`tiny-skia`. Glyph coverage check: any `.notdef` glyph aborts the build (no tofu, INV-CON-008).
3. Cover is a picture page; the cover image is also the EPUB `cover-image` and the catalog thumbnail source (generated sizes at build).

## EPUB 3 structure

`mimetype` first and uncompressed; `META-INF/container.xml`; `content.opf` (metadata, manifest, spine in reading order, `dc:language` = book language, `dcterms:modified` = build input timestamp fixed from the document, not the wall clock); `nav.xhtml` (`epub:type="toc"` + landmarks); XHTML chapters; one stylesheet; fonts embedded only if license allows (decision recorded in the ruleset assets list). Reproducible ZIP: fixed entry order, fixed timestamps (1980-01-01), fixed compression level, no extra fields (INV-CON-002).

## HTML / chapters

Chapter HTML is the same XHTML body used in the EPUB, sanitized (`SafeHtml`), with `data-section-id` and `data-block-id` attributes, so the reader can anchor and highlight without parsing the EPUB.

## Preview

`PreviewArtifact` per [policy](../../content/domain-model.md): cover, metadata, summary, TOC, first N characters of the first body chapter cut at a paragraph boundary; plus the policy hash. Built from `PublicDocument` projection only.

## Verification at build

1. Re-open the produced EPUB with the audit reader: spine order = tree leaves; nav links = TOC page links; no blank pages; all internal hrefs resolve; images present.
2. `epubcheck` in CI on all gold outputs (not in production runtime).
3. Hash recorded; second build in CI must match.

## Language-aware labels

Label tables per language (`labels_bn`, `labels_en`) in the ruleset; a lint ensures no Bengali label string appears in an English book build and vice versa.
