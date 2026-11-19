# reader - the reading copy

Status: DRAFT (pipeline per ADR-0023; the CSS and text-layer policies are proposals, see Open items)

A reading copy is the derived, sanitized, whole-book form of one EPUB version. It is regenerable from catalog, so it is not backed up (D-33).

## Pipeline (REQ-RDR-001, 002; INV-RDR-001, 002)

1. **Fetch.** Stream `GET /internal/books/{id}/versions/{version_id}/epub` from catalog into a bounded temporary file (size cap 50 MiB). Verify sha256 against the event's `epub_sha256`.
2. **Unpack safely.** Open the ZIP with limits (entry count, expanded size, ratio); reject path traversal, absolute paths and duplicate names; read `META-INF/container.xml`, the OPF, the spine, manifest and the navigation (EPUB 3 nav document, else NCX).
3. **Sections.** Each spine XHTML document becomes a section. `section_id` is derived from the version-independent source identity: UUIDv5 over the book id and the normalized spine item path (ADR-0015), not the ordinal position, so it survives rebuilds that keep file names.
4. **Sanitize** every XHTML document into `SafeHtml` ([below](#sanitizer)).
5. **Rewrite links.** Internal hrefs become `#section:<section_id>[#fragment]`; image, font and CSS references become package resource ids; any other scheme is removed (external navigation is dropped to plain text, or an inert marked link, as a presentation choice in web).
6. **Resources.** Images (JPEG, PNG, GIF, WebP, SVG only after sanitization or rasterization policy), fonts (WOFF, WOFF2, OpenType, TrueType) and reduced CSS are stored with media type verified by bytes and sha256.
7. **Text layer.** For each section compute the text layer used by anchors and in-book search ([anchors](anchors.md)).
8. **Write the package** atomically (temp file, fsync, rename), compute `content_hash`, then in one transaction mark the copy Ready and replace the previous Ready copy.

Determinism: output is a pure function of the EPUB bytes and `parser_version` (stable ordering, no timestamps or random ids in the package); two runs are byte-identical. A parser change bumps `parser_version` and triggers rebuilds of Ready copies in the background.

## Sanitizer (REQ-RDR-003; INV-RDR-003)

- Allow-list of elements (structural text, headings, lists, tables, `img`, `figure`, `a`, `span`, `div`, `blockquote`, `ruby`, `sup`/`sub`, `br`, `hr`) and of attributes per element (`href` on `a`, `src` and `alt` on `img`, `lang`, `dir`, `id`, `class`, `epub:type` mapped to `data-` attributes). Everything else is dropped; unknown elements are unwrapped keeping their text.
- Removed outright: `script`, `style` blocks, `iframe`, `object`, `embed`, `form`, `link`, `meta`, `base`, `audio`/`video` sources, all `on*` handlers, `srcset` and `xlink:href` to external hosts, `javascript:`, `data:` (except package images already rewritten) and unknown URL schemes.
- No external loads: every `src` and `href` ends up as a package resource id or an in-book anchor.
- Output is serialized by the sanitizer, never by string concatenation of input; the sanitizer is idempotent (`sanitize(sanitize(x)) = sanitize(x)`) and returns `SafeHtml`, the only type the package writer takes.
- Parsing is bounded (depth, node count, attribute length) so hostile input fails the build, never panics or exhausts memory (a 64 MiB per-request allocation guard applies).

## Package contract (REQ-RDR-008, 025)

One response, shape in the [HTTP contract](../../07-contracts/http/reader.md): `{book_id, version_id, parser_version, manifest, toc, chapters[{id, title, html}], resources[{id, media_type, sha256, data}]}`. Served only after identity verification with redemption; `private, no-store`, nosniff and a CSP that forbids script and external loads. No per-chapter route, no EPUB route.

## Rendering contract with web

Web renders the package with its own renderer (REQ-RDR-020, 021, 022). Theming uses CSS variables on the container; web never forces `!important` colours on book content. Publisher CSS policy (proposal): external and embedded stylesheets are not kept; a reduced inline-style allow-list (text alignment, indent, weight, style, margins, in relative units) is retained. Fonts embedded in the EPUB are kept for Bengali fidelity; web provides Bengali-tuned defaults.

## Open items (not decided here)

1. CSS policy above (drop publisher stylesheets, keep a small inline allow-list) is a proposal; the owner or the web design may prefer scoped publisher CSS.
2. Text layer definition (below) must be identical in the Rust build and in the browser renderer; it is proposed as: the concatenation of text nodes of the sanitized section in document order, NFC normalized, with `<br>` as one newline and block boundaries as one newline, offsets in UTF-16 code units. A cross-implementation fixture test is required (TST-RDR-025).
3. Package size bound and per-section size bound (limits rows to be added).
4. Whether image-based SVG is allowed (rasterize or drop).
