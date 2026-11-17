# Requirements — Content (CON)

Status: DRAFT · Service: [content](../05-services/content/README.md)

- **REQ-CON-001** · MUST · inv: INV-CON-001 · verify: db, model, prop · Artifact sets are immutable and content-addressed. Publishing a new set is an atomic pointer swap; readers see either the old or the new set, never a mix.
- **REQ-CON-002** · MUST · inv: INV-CON-002 · verify: prop, gold · EPUB, chapter HTML and Preview are derived deterministically from the canonical document: same input and builder version produce byte-identical output.
- **REQ-CON-003** · MUST · inv: INV-CON-003 · verify: type, prop · The Preview artifact is built at publish time from an allow-list (metadata, summary, TOC, first N characters of the first chapter). Public endpoints can only serve the Preview artifact, never the full document.
- **REQ-CON-004** · MUST · inv: INV-CON-004 · verify: type, e2e · Full chapters, the EPUB and downloads are served only with a valid capability for that action and artifact set.
- **REQ-CON-005** · SHOULD · inv: INV-CON-005 · verify: prop · Byte-range requests return correct partial content for media and downloads.
- **REQ-CON-006** · MUST · inv: INV-CON-006 · verify: db, drill · The previous artifact set is retained until all annotations are re-anchored to the new one and a minimum retention (30 days) has passed.
- **REQ-CON-007** · MUST · inv: INV-CON-007 · verify: prop, gold · Every EPUB passes epubcheck and the structure audit; navigation and in-book TOC are generated from the same tree so they cannot differ; page order follows the [fixed order](../05-services/ingestion/builder/README.md).
- **REQ-CON-008** · MUST · inv: INV-CON-008 · verify: gold, review · Covers use the source image when present; otherwise a generated cover shows title and author with correct Bengali shaping, portrait ratio, readable contrast.
- **REQ-CON-009** · MUST · inv: INV-CON-009 · verify: type, fuzz · All HTML passes through a `SafeHtml` sanitizer type; scripts, inline handlers, external loads and unknown URL schemes cannot appear in stored output.
