# Source structure, entities, canonical documents, and publication

Tasks E04–E06. Extend correct parser/export/preparation functions from `app/backend/apps/ingestion/pipeline`, `source_processing/{documents,collection_index,linked_books,export_verification,export_checkpoint,reading_preparation,asset_publication,publication}.py`, curated-document models, and access/reading preparation. Remove cross-service ORM dependencies when relocating them; do not copy the complete backend into the engine.

## Stage inputs, outputs, and invariants

| Stage | Input → durable output | Required invariant/failure behavior |
| --- | --- | --- |
| Discover | Configured source + catalog revision → source/component/page manifest | Every eligible record accounted for; provider identity in configuration. |
| Collect | Allowed manifest → immutable page/media snapshots with bytes/hash/status/order/relationships | Fetch all relevant permitted evidence. Stop/retry explicit faults; do not mistake descriptions/login pages for body. |
| Parse blocks (E04) | Snapshots → ordered block records and website-chrome candidates | Every paragraph/heading/list/poem/image/table/footnote has a source page/location/hash; no model rewrite. |
| Understand (E04) | Blocks + navigation/typography/numbering + validated local decisions → section hierarchy/reading graph | No missing, duplicated, cyclic or unsupported component order; retain true continuous works. |
| Extract/resolve (E05) | Bibliographic blocks/spans → evidence-backed work/entities/roles/aliases | No invented values or name-only merges. Ambiguous facts remain unresolved, not fabricated. |
| Canonicalize (E05) | Verified blocks/hierarchy/entities → versioned canonical document | Exact source mapping, block coverage, immutable version keys and explicit confidence/evidence. |
| Generate (E06) | Canonical document → sealed HTML/EPUB/cover/reader artifacts | One document drives both exports; exporter cannot infer new chapters or alter source text. |
| Independently verify (E06) | Frozen source evidence + actual artifacts → per-check report | Rebuild expectations from evidence, not extractor success flags or navigation-text occurrence. |
| Publish (E06) | Verified sealed manifest → durable website activation receipt | Checksums/current authority/revision; all active pointers switch atomically; automatic availability. |

Checkpoint each stage with input/output checksums and collection/parser/extractor/model/prompt/schema/generator/verifier/preparation versions. A changed upstream hash/version invalidates dependent stages. A reusable checkpoint must validate its confined artifact path, existence, byte length and checksum. A bad checkpoint is an explicit integrity defect, not an excuse to skip work.

## E04: blocks and reading structure

Block IDs are deterministic hashes of frozen page hash, stable page-local locator and occurrence index. IDs are stable within a source revision; no cross-edition migration guarantee is required. Record raw source text/HTML, safe parsed representation, source range, kind, order and component identity separately. Never merge identical repeated paragraphs merely because their text hashes match.

Use explicit source contents, link order, hierarchy, numbering, typography and neighboring patterns first. In ambiguous spans use schema-validated local decisions over referenced blocks. Preserve original chapter labels; generated neutral navigation labels are localized metadata, never inserted as source-authored prose. Detect chapters, poem titles, acts/scenes, anthology entries and nested sections; avoid classifying bold dialogue, dates, scene breaks, credits or recommendations as chapters without evidence.

Keep meaningful front matter, dedication, credits, prefaces and back matter in source reading order. Removing repeated site chrome requires exact evidence and a reason for every excluded block; meaningful repeated source text remains. A linked compilation needs complete independent component evidence before its whole book can be ready. Cycles, disconnected components, contradictory order and missing body pages classify as explicit defects/ambiguity/unavailability, never a partial ready book.

Source-marked unfinished books may publish the complete currently available source revision when boundaries/coverage are understood. A source that promises an unavailable required chapter is source-unavailable for that build. Do not equate an intentionally unfinished work with a collection omission.

## E05: bibliographic evidence and identity

Extract title/work/edition, author, translator, editor, compiler, publisher, illustrator, cover artist, category, language, series/sequence, original title and publication facts only when supported. Each fact records raw value, exact page/block/span, role evidence, normalized value and extractor/decision versions. A combined translation/editing credit yields both roles with the same evidence where justified. A publisher may be a person or organization; role and entity type are separate.

Distinguish people credited for the work from mentions in narrative/dedication/quotation/preface. Separate bibliographic facts embedded in early body pages without dropping those pages' meaningful content. Preserve original-language names; aliases require source evidence. Do not create fake missing names, rely on hardcoded confidence, fuzzy-name-only merge, or retain isolated named-author patches as the production algorithm.

Identity key is supported work/contributor evidence, never title/name alone. Equal normalized names are candidate matches; merge only with corroborating current-source identity evidence, otherwise keep separate identities and explain uncertainty. Respect admin metadata/cover overrides during automatic regeneration. Confidence is calibrated by held-out results and evidence validity; model self-confidence is a diagnostic, not a publication permit.

Resolved engine entities carry a stable `entity_id` plus source-identity evidence in metadata/provenance. The website uses a unique `(engine_issuer, entity_id)` binding to its own contributor/series ID; the same display/normalized name may belong to multiple independently evidenced identities. Existing website IDs in administrator overrides stay authoritative. Publication reuses a binding rather than doing `get_or_create(name=...)`; an unbound equal-name candidate requires corroborating evidence before reuse. W01 removes the conflicting name-only uniqueness/validation, so E05/E06 cannot fail or silently merge to fit the website schema. Test homonyms, aliases for one identity, series with the same name and concurrent binding creation.

Canonical schema version 1 contains `document_id`, `schema_version`, `source_revision`, `source_manifest_sha256`, `versions`, `metadata`, `entities`, `blocks`, `sections`, `reading_order`, `exclusions`, and `validation`. Sections have ID, parent, front/body/back role, original/neutral label provenance, ordered block IDs and component identity. Reading order is an acyclic ordered sequence of retained sections/blocks; every retained block occurs exactly as its source occurrence requires. Exclusions retain block IDs and evidence. Validate referential integrity, bounded depth/size, role evidence, full coverage and order before exporting.

## E06: generation and independent verification

Export HTML and EPUB from the same canonical sections and exact retained source text. Normalize only HTML entity decoding and CRLF→LF for comparison; prose whitespace normalization is explicit and source-mapped, while poetry/stanza/table/meaningful spacing is preserved. Do not strip Bengali joiners/combining characters, punctuation or meaningful repetition. Keep all media/footnotes and internal targets or report an explicit unavailable resource.

EPUB output has correct container/package/manifest/spine, metadata/language/roles, hierarchy and working navigation targets. A valid EPUB navigation document is required; do not create duplicate visible contents pages or treat a historical “no TOC” instruction as permission to omit mandatory package navigation. The exporter does not run late chapter inference. Reader-resource preparation uses the exact EPUB checksum and preparation-policy version.

The independent verifier reads frozen evidence and actual artifacts. It must not use the extractor's chosen section list as its only source of expectations. Shared low-level safe archive parsing is acceptable; reusing the same heuristic to both choose and prove a chapter boundary is not independent verification.

Verification reconstructs these expectations:

- Source page/component coverage, retained/excluded blocks and legitimate repeated occurrences.
- Exact actual EPUB spine traversal and HTML body sequence; exclude nav/metadata documents as evidence of body text. Detect missing, duplicated and reordered content even when every text fragment appears elsewhere in the ZIP.
- Section boundaries/hierarchy/front-body-back classification, labels, TOC/footnote/backlinks, asset presence/media types, metadata and supported entity-role source spans.
- Usable HTML/EPUB/reader artifacts, checksums, safe archive/resources, actual reader chapter/contents opening and consistent preparation version.

Test adversarial fixtures: swapped spine with unchanged nav, body copied only into nav, duplicated/omitted prose, repeated genuine paragraphs, changed credit role, bold non-heading, continuous work, anthology/poetry/drama, component omission, bad fragment, missing cover/media, unsafe file, and a canonical document falsely asserting success. Verification failure never bypasses to publish or asks an administrator to approve.

Seal verified artifacts and hand off through [private engine v1](../../shared/contracts/private-engine-v1.md). Website copies into its own protected staging and validates safety/checksums before an atomic DB pointer switch and receipt. A first failed build stays unavailable; a failed replacement leaves the valid active build intact. All read/download/HTML/Kindle surfaces agree on active build. Admin edits/archives/revocation race with generation through explicit revision/authority checks. Publish is idempotent; uncertain acknowledgment is reconciled by receipt, never duplicate book creation.

Before generation, obtain the website's reserved identity and immutable metadata/cover context. Apply source-versus-admin precedence and fetch approved override cover bytes as defined in the [publication lifecycle](../../shared/contracts/publication-context-and-lifecycle.md). Record context/book IDs in the sealed manifest; a source title is never a deduplication key. Current catalog and file metadata alignment, transferred artifact pinning, active reader/delivery leases and cleanup follow that same contract.

E04/E05 close with deterministic source fixtures, full block accounting and reference-case evidence. E06 also requires meaningful fault-injection/backend/reader tests, schema consistency, actual generated-file inspection and package-spine checks. Real semantic acceptance remains E08; an integration canary alone is insufficient.
