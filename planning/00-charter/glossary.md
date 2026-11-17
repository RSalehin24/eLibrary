# Glossary (ubiquitous language)

Status: DRAFT

Use these words exactly. Code, contracts and UI copy must match.

| Term | Meaning |
|---|---|
| **Source** | An external site we ingest from (today: one LearnDash-based Bengali ebook site). |
| **Source book** | A book page on a source, identified by canonical URL. |
| **Snapshot** | Immutable, content-addressed capture of every fetched source page for one fetch run. |
| **Block** | Smallest unit of the intermediate representation: heading, paragraph, list item, quote, image, separator, table row. Has a stable `BlockId`. |
| **Ruleset** | Versioned bundle of lexicons, patterns and thresholds used to interpret a snapshot. |
| **Canonical document** | The structured, validated representation of one book: ordered sections with typed roles, entities, evidence. The only input to builders. |
| **Section** | Cover, title page, book info, dedication, front section, table of contents, chapter (nested), end section. |
| **Evidence** | Pointer to blocks that justify a fact, plus extractor name and confidence. |
| **Work** | The abstract creation ("Three Musketeers"). |
| **Translation** | A Work rendered into a language by specific translator(s). |
| **Book** | A published edition: a specific publisher/edition of a Work or Translation. What users see. |
| **Agent** | A person or organization that can be a contributor or publisher. Names are aliases, not identity. |
| **Credit** | Agent + role on a Book. Roles: writer, translator, editor, compiler, illustrator, cover artist, publisher. |
| **Artifact set** | Immutable bundle produced by a build: canonical document, EPUB, chapter HTML, preview, cover. Content-addressed. |
| **Preview** | Public, build-time-derived subset of text and metadata. Contains only what may be shown to anonymous visitors. |
| **Grant** | Permission to perform a scope within a target (global, category, author, book). |
| **Capability** | Short-lived signed token authorizing one action on one artifact set for one subject. |
| **Subject** | Anonymous visitor or Account. |
| **Reading session** | Server-tracked period in which an account has a book open. |
| **Anchor** | Position in a book stable across rebuilds: section id + text quote + offsets. |
| **Review item** | Ingestion result that needs a human decision (duplicate, low confidence, incomplete). |
| **Gold corpus** | Human-labeled set of source books with expected canonical documents; the ruleset's test oracle. |
| **Gate** | Exit criterion for a roadmap phase. Work past a gate is blocked until it passes. |
