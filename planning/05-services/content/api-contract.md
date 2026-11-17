# content — API contract

Status: DRAFT · Source of truth: `contracts-content`

## Public

| Method & path | Auth | Response |
|---|---|---|
| `GET /content/books/{book_id}/preview` | anonymous | `PreviewArtifact` JSON (sections: title, metadata echo, summary, toc, excerpt HTML) |
| `GET /content/books/{book_id}/cover` | anonymous | image, `Cache-Control: public, immutable`, `ETag: <hash>`; `?w=` limited set of widths pre-generated at build |

## Protected (capability required, `Authorization: Capability <token>` or `?cap=` for EPUB downloads)

| Method & path | Action | Response |
|---|---|---|
| `GET /content/books/{book_id}/sections` | Read | section index (tree) |
| `GET /content/books/{book_id}/sections/{section_id}` | Read | sanitized chapter HTML + prev/next ids |
| `GET /content/books/{book_id}/epub` | Download | EPUB bytes, `Content-Disposition`, range |
| `GET /content/books/{book_id}/assets/{hash}` | Read | images/fonts inside chapters |

All protected responses: `Cache-Control: private, no-store`. A capability for artifact set A used against active set B returns `409 artifact_set_changed` with the new set id so the client re-requests a capability.

## Internal

| Route | Caller | Purpose |
|---|---|---|
| `PUT /internal/documents/{book_id}/{doc_hash}` | ingestion | submit canonical document; idempotent; returns `build_id`, `artifact_set_id` (maybe still Building) |
| `GET /internal/artifact-sets/{id}` | ingestion/catalog | state + hashes |
| `POST /internal/books/{book_id}/activate` | catalog | pointer swap `{artifact_set_id, expected_revision}` |
| `GET /internal/books/{book_id}/section-index?set=` | library | for re-anchoring |
| `GET /internal/books/{book_id}/epub` | notify | service capability |
| `GET /internal/contract` | all | handshake |

## Errors

`capability_invalid`, `capability_expired`, `capability_wrong_book`, `artifact_set_changed`, `document_schema_unsupported`, `conservation_failed`, `build_failed(stage)`.
