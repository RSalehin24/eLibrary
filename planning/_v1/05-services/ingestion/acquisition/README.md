# Acquisition

Status: DRAFT (reconciled with the Postgres-queue ingestion design, D-27/D-29; tables and job semantics: [domain model](../domain-model.md), [state machines](../state-machines.md))

The only impure stage. Everything it fetches is kept as files in the scrape cache; everything after it is a pure, reproducible function of that cache.

## Source adapter interface

```rust
pub trait SourceAdapter {
    fn kind(&self) -> SourceKind;
    fn canonicalize(&self, input: &str) -> Result<UrlKey, UrlError>;                   // /books/<slug>/ only
    fn list_catalog(&self, cursor: Cursor) -> Result<CatalogPage, JobError>;            // archive listing (sync job)
    fn discover(&self, landing: &ScrapedPage) -> Result<Vec<TocPageRef>, JobError>;    // paginated TOC pages
    fn fingerprint(&self, page: &ScrapedPage) -> StructureFingerprint;                  // drift detection
}
pub struct SourceClient(/* GET only: no method parameter, no body, no form encoder */);
```

`SourceClient` exposes only `get(url) -> Response`. There is no way to issue POST/PUT/DELETE or to submit a form (D-03, INV-ING-012, enforced by type: the type has no such method, and a lint forbids constructing another HTTP client in the crate). A future non-GET action would need a new decision, not a code change.

## Fetch policy

| Aspect | Rule |
|---|---|
| Politeness | one in-flight request per source host (semaphore), 0.5 s delay between pages plus jitter, honors `Retry-After`; defaults come from settings |
| User-Agent | honest, names the project and a contact address; no evasion of bot protection; when the source challenges the client the operator supplies a fresh cookie (credential flow), nothing else |
| Retries | typed, no text matching. Network error, timeout, 429, 5xx are `JobError::Retryable` (job requeued with exponential backoff and jitter, default 3 attempts per request); other 4xx are `Permanent`; 401/403/login page is `Permanent(auth_required)` and moves the request to `awaiting_credential` |
| Resilience | host fallback (www/non-www) is an adapter policy, logged; certificate validation is never disabled |
| Bounds | per page 5 MiB, per book 5,000 pages, TOC pagination loop detection by page signature; 50 requests per automation run (see [orchestration](../orchestration/README.md)) |
| Credential | one explicit cookie in a read-only secret file mounted into `ingestion-api` and `ingestion-worker` (rotatable without a rebuild); only status and expiry are stored in the database; never logged or returned by an API. The adapter sends it on GETs only |
| Cancel | the cancel flag is read before every page; the cursor (next page index) is persisted so a retry resumes |
| Output | page bodies and images written atomically as files `/data/ingestion/scrape/<request_id>/<sha256>`; metadata row `scrape_pages`; raw pages are deleted after 30 days (retention default); nothing is stored in a request or job row |

## Locked chapters (the legacy "mark complete" problem)

Some chapters render only after earlier chapters were marked complete on the source site. The legacy code did this by submitting a form on the source (a write to a third party). New behavior:

1. Detect lock placeholders (adapter markers) and record `leaf_state = locked` on the page row.
2. Never change source state. The request proceeds with what is available and raises a `LockedSource` review item when any TOC leaf is locked.
3. Resolution paths: the operator supplies a credential whose account has the chapters unlocked, uploads an EPUB, or accepts that the book cannot be created yet.

## Completeness evidence

Produced here, consumed by validation (INV-ING-006):

```
expected_leaves = every leaf in every TOC page (all pages; count cross-checked with the declared page count)
fetched_leaves  = leaves with HTTP 200 and non-chrome body
empty_at_source = leaves with HTTP 200 and chrome-only body, with the page hash as evidence
missing         = expected - fetched - empty_at_source   // must be empty to proceed
```

The legacy "pin the last chapter title" workaround is replaced by a general check: the last TOC leaf and the declared TOC page count must both match the fetched set. A Cloudflare-style 200 with a sentinel title is a page error, not content.

## Drift detection

`StructureFingerprint` is the hash of the sorted CSS-class tokens and landmark paths the adapter relies on (TOC container, entry-content, pagination controls). A change against the last known good raises a `SourceDrift` review item and holds new scrape jobs of that adapter (running ones finish) instead of failing every book. A daily canary request on a fixture book per structure shape must pass before the hold lifts.

## EPUB intake (manual)

An uploaded EPUB (`source_kind = epub_upload`) is stored under the request's scrape directory; a different front-end adapter parses its XHTML spine and nav into the same Block IR; from there the pipeline is identical (INV-ING-013).
