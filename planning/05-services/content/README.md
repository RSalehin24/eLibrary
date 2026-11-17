# content

Status: DRAFT

Holds the book itself: immutable, content-addressed, access-controlled bytes.

| | |
|---|---|
| Owns | published canonical documents, artifact sets (EPUB, chapter HTML, section index, preview, cover), build records, retention |
| Does not own | book metadata (catalog), grants (access), ingestion drafts |
| Requirements | REQ-CON-001…009, REQ-DSC-004 (PublicDocument), REQ-ING-003 (builders) |
| Emits | `ArtifactSetSealed`, `ArtifactSetActivated`, `ArtifactSetRetired` |
| Consumes | `BookPublished` (activate), `BookArchived` (hide), `AnnotationReanchorDone` (retention) |
| Calls | none (verifies capabilities offline) |
| Called by | web (via gateway) for preview/chapters/EPUB, ingestion (put document), library (section index), notify (EPUB) |

## Module split (leak-proofing)

```
content/
  public/    PreviewArtifact + cover handlers        (reads ONLY the `preview` and `cover` stores)
  protected/ chapter, section-index, EPUB handlers   (require Verified<Capability>)
  build/     deterministic builders (domain-builders), sealing
  store/     content-addressed blob store, artifact-set tables
```
`public/` has no compile-time path to `protected/` types (separate crates or `pub(crate)` seams) — INV-CON-003.

## Build

`put_document(book_id, doc_hash, CanonicalDocument)` → validates schema version and conservation record → runs builders → writes blobs → writes `ArtifactSet` (state `Building`→`Sealed` in one transaction after all blobs are verified by hash) → emits `ArtifactSetSealed`. Activation is a separate pointer swap (`Publication` model).

## Delivery

| Resource | Auth | Cache |
|---|---|---|
| Preview JSON/HTML, cover image | public | immutable, long-lived by hash |
| Section index, chapter HTML | capability(Read) | `private, no-store` |
| EPUB | capability(Download) | `private, no-store`, range supported |

See [domain model](domain-model.md) · [API](api-contract.md) · [state machines](state-machines.md) · [tests](test-plan.md) · builders: [ingestion/builder](../ingestion/builder/README.md).
