# Requirements — Ingestion & book creation (ING)

Status: DRAFT · Service: [ingestion](../05-services/ingestion/README.md)

Derived from the legacy [EPUB pipeline specification](../../docs/epub-pipeline-specification.md) and the code survey.

- **REQ-ING-001** · MUST · inv: INV-ING-001 · verify: db, prop, drill · Snapshots are immutable and content-addressed. Everything downstream is a pure function of (snapshot, ruleset version) and can be recomputed bit-for-bit.
- **REQ-ING-002** · MUST · inv: INV-ING-002 · verify: prop, gold · Conservation: every input block ends in exactly one output location, or is recorded as dropped with a reason code. No block is lost silently.
- **REQ-ING-003** · MUST · inv: INV-ING-003 · verify: type, prop, gold · Reading order is a total order over leaf sections. The in-book TOC and the navigation are generated from the same tree. Page order is Cover, Title, Book Info, Dedication, Front sections, TOC, Chapters, End sections; empty pages are omitted.
- **REQ-ING-004** · MUST · inv: INV-ING-004 · verify: prop, gold · For books with a source TOC, that TOC is authoritative: no chapter is invented or merged, nesting is preserved, a parent is never replaced by its children, and `/books/…` links are never treated as chapters.
- **REQ-ING-005** · MUST · inv: INV-ING-005 · verify: gold · For single-page books, chapters are inferred from headings, numerals and Bengali boundary patterns, and every inferred boundary carries evidence and confidence.
- **REQ-ING-006** · MUST · inv: INV-ING-006 · verify: model, prop · A book is published only if every TOC leaf was fetched, or is explicitly recorded as empty at the source. There is no percentage tolerance and no per-book exception list.
- **REQ-ING-007** · MUST · inv: INV-ING-007 · verify: prop, gold · Every extracted entity (title, writer, translator, editor, publisher, series, category, date, edition, dedication) carries evidence and confidence. Below the ruleset threshold the item goes to the Review queue; nothing guessed is auto-published.
- **REQ-ING-008** · MUST · inv: INV-ING-008 · verify: prop, gold · A fact appears once: text promoted to Book Info is removed from front sections; a dedication is never also a front section; residual text with no new information is dropped with a recorded reason.
- **REQ-ING-009** · MUST · inv: INV-ING-009 · verify: gold, unit · The book language is detected; labels, nav titles and Book Info keys use that language only (no Bengali labels on an English book). Unnamed front sections are labeled "অন্যান্য"/"Others" in navigation only, numbered when several.
- **REQ-ING-010** · MUST · inv: INV-ING-010 · verify: model, prop · A job moves through the lifecycle in [state machines](../05-services/ingestion/state-machines.md). At most one active job per source URL; every step is idempotent; an expired lease returns the job to the queue; no state skips.
- **REQ-ING-011** · MUST · inv: INV-ING-011 · verify: gold · Rulesets are versioned. A new ruleset is promoted only if gold-set metrics do not regress. Reprocessing shows a structured diff (sections, entities, text) before it replaces a published build.
- **REQ-ING-012** · MUST · inv: INV-ING-012 · verify: type, review · Acquisition is read-only, rate-limited and polite (backoff, concurrency cap, identified client). It never submits state-changing requests to the source unless decision D-03 explicitly authorizes a named, documented action.
- **REQ-ING-013** · SHOULD · inv: INV-ING-013 · verify: gold, e2e · Manual EPUB intake (administrator upload) produces the same canonical document and goes through the same validation, review and build path.
- **REQ-ING-014** · SHOULD · inv: INV-ING-014 · verify: prop, e2e · Catalog sync lists the source archive, detects new, changed and unfinished books, and creates jobs without duplicating existing ones.
- **REQ-ING-015** · MUST · inv: INV-ING-015 · verify: prop, gold · Duplicate handling follows the five-case policy: same title/different works; same title+author/different publisher; different translator; same publisher/different edition → offer "new edition"; exact duplicate → refuse.
- **REQ-ING-016** · MUST · inv: INV-ING-016 · verify: model, prop · Publishing emits exactly one effective `BookPublished` per (book, artifact set) — delivered at-least-once, applied exactly-once by idempotent consumers.
