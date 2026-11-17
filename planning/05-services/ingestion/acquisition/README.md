# Acquisition

Status: DRAFT

The only impure stage. Everything it fetches is kept; everything after it is reproducible.

## Source adapter interface

```rust
pub trait SourceAdapter {
    fn kind(&self) -> SourceKind;
    fn canonicalize(&self, input: &str) -> Result<CanonicalUrl, UrlError>;         // /books/<slug>/ only
    fn list_catalog(&self, cursor: Cursor) -> Result<CatalogPage, FetchError>;       // archive listing
    fn discover(&self, landing: &SnapshotPage) -> Result<Vec<TocPageRef>, FetchError>; // paginated TOC pages
    fn fingerprint(&self, page: &SnapshotPage) -> StructureFingerprint;              // drift detection
}
pub struct Http(/* GET only: no method parameter, no body */);
```
`Http` exposes only `get(url) -> Response`; there is no way to issue POST/PUT/DELETE (INV-ING-012, type-level). Any future non-GET action must be a named method on the adapter, referenced by decision D-03 in the ADR that authorizes it.

## Fetch policy

| Aspect | Rule |
|---|---|
| Politeness | ≤ 1 req/s/host sustained, concurrency 2, identified `User-Agent` with contact, honors `Retry-After`, robots/ToS gate recorded in D-03 |
| Retries | 4 attempts, exponential 2 s → 60 s with jitter; retry on 429/5xx/timeouts only; 4xx other than 429 are permanent |
| Resilience | Host fallback (www/non-www) and DNS fallback are kept **as adapter policies** with explicit logging; certificate validation is never disabled |
| Bounds | per-page 5 MiB, per-book 5,000 pages, TOC pagination loop detection by page signature |
| Auth | The adapter may hold a read-only session cookie for pages requiring a logged-in viewer (stored as a secret, never logged). Refresh is manual (an admin saves it). It must not submit forms. |
| Output | `SnapshotPage` rows + blobs; response headers kept; `fetched_at` from injected clock |

## Locked chapters (the legacy "mark complete" problem)

Some chapters render only after earlier chapters are marked complete. New behavior:

1. Detect lock placeholders (adapter-specific markers) → record `locked=true` on the `SnapshotPage`.
2. **Do not** mutate source state. The job proceeds with what is available and raises `LockedSource` review when any TOC leaf is locked.
3. Resolution paths (decision D-03): obtain sanctioned access (account with chapters unlocked, source-provided export or API), or accept that the book cannot be created yet.

## Completeness evidence

Produced here, consumed by validation (INV-ING-006):

```
expected_leaves = every leaf in every TOC page (all pages of the paginated TOC, count cross-checked with the source's declared page count)
fetched_leaves  = leaves with HTTP 200 and non-chrome body
empty_at_source = leaves with HTTP 200 and chrome-only body, with the page hash as evidence
missing         = expected − fetched − empty_at_source   // must be ∅ to proceed
```

The "pin the last chapter title" workaround is replaced by a general check: the **last TOC leaf** and **the declared TOC page count** must both match the fetched set.

## Drift detection

`StructureFingerprint` = hash of the sorted list of CSS-class tokens and landmark paths the adapter relies on (e.g. TOC container, entry-content, pagination controls). Each snapshot is compared with the adapter's last-known-good; a change raises `SourceDrift` and pauses *new* jobs of that adapter (running ones finish), instead of failing every book. Canary jobs (one fixture book per structure type, run daily) must pass before the pause lifts.

## EPUB intake (manual)

An uploaded EPUB becomes a snapshot of kind `Epub` (zip hash, member list). A different front-end adapter parses its XHTML spine/nav into the same Block IR; from there the pipeline is identical (INV-ING-013).
