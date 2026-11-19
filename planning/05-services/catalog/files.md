# catalog - files, downloads, preview and Kindle

Status: DRAFT

Catalog is the only service with the EPUB and cover files (REQ-CAT-020). Reader derives its copy by streaming the EPUB; notify streams it for a Kindle send; nobody shares the volume.

## Blob store (INV-CAT-020, 021)

- Path `/data/catalog/blobs/ab/cd/<sha256>`; content addressed, write-once.
- Write: stream to a temp file, hash, fsync, rename, then insert the `assets` row in the same request/transaction as the version. The row is the only way a blob is reachable.
- A blob without a row is swept after 24 h. A row whose blob is missing or fails its hash blocks publish and restore of that version and is reported by the verify job (periodic, bounded). A GET that finds a missing blob returns an error and changes no state (REQ-CAT-032).
- No static path, no directory listing; Caddy and the gateway never read this volume. Traversal is impossible because paths derive from the hash only.

## Validation at intake

| Asset | Checks |
|---|---|
| `epub` | magic bytes and `mimetype` entry, ZIP structure, zip-bomb limits (entry count, expanded size), size cap 50 MiB, sha256 equals the declared value |
| `cover` | by bytes: type from an allow-list (JPEG, PNG, WebP), dimensions and size caps, checksum; fetched from allow-listed hosts only (by ingestion); with no source image a generated cover shows title and author with correct Bengali shaping (REQ-CAT-028) |
| `preview` | a `PreviewArtifact` (TOC, first N characters, N from `preview_chars`, 0 allowed), re-sanitized into `SafeHtml` on intake; marked `noindex` when served |

## Serving

| Use | Scope and rule |
|---|---|
| Cover | public, `public, max-age=60`, ETag, nosniff, only for a visible book |
| Preview | signed-in with `preview`; returns only the stored `PreviewArtifact`; no code path from a full document to it (REQ-CAT-019) |
| EPUB download | `download` scope, published version only; `Range` streaming; audit row; `Content-Disposition` filename from the slug (REQ-CAT-023) |
| EPUB for reader and notify | internal service token; published versions, or the reader's pending fetch of a just-published version |

Honest limit: a user with `read` receives the whole book in the browser through the reader (D-28), so the `download` scope controls the EPUB file, not the ability to copy text. See [reader README](../reader/README.md).

## Kindle (REQ-CAT-029)

Requires `kindle` and a published version; size cap (Kindle mail limit 50 MiB); per-user rate limit (10 per hour, provisional, C-6). The request row and the `kindle.requested` event are written in one transaction; notify reads the address from identity at send time, streams the EPUB from catalog, and reports `queued`, `sent` or `failed` back; the status is shown on the Files tab. Unpublished or deleted books give `kindle_not_available`.
