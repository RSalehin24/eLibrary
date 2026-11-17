# content — state machines

Status: DRAFT

## Artifact set

```
 (none) ──put_document──► Building ──all blobs hashed & verified──► Sealed ──superseded & holds released──► Retired
              │
              └──build error / timeout 24h──► (deleted)
```

- `Building → Sealed` is one transaction that checks the five hashes exist in `Blob`.
- `Sealed` rows are immutable (DB trigger rejects UPDATE of any column except `state→Retired`).
- Idempotency: `(book_id, doc_hash, builder_version)` unique — re-submitting returns the existing set.

## Active pointer (Publication model)

```
 ptr = none ──activate(S)──► ptr = S ──activate(S′)──► ptr = S′
```
`activate(S)` requires `S.state = Sealed`; readers fetch `(ptr)` once per request and use the set id throughout (single read ⇒ one consistent set: INV-CON-001, `ReaderSeesOneSet`).

## Build pipeline

`Validate(doc) → SectionTree → Preview → Chapters → Section index → EPUB → Cover → Verify (epubcheck-equivalent audit + hashes) → Seal`.
A failure at any stage records `build_failed(stage, reason)` and leaves no artifact set visible.

## Retention hold

`Held → Releasable` when all holds expire/clear; deletion is a two-pass sweep.
