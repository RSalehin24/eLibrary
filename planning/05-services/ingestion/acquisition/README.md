# Acquisition

Status: DRAFT (reconciled with the Postgres-queue design, D-03, D-30, D-31; tables and job semantics: [domain model](../domain-model.md), [state machines](../state-machines.md))

The only impure stage. Everything it fetches is kept as files in the scrape cache; everything after it is a pure, reproducible function of that cache. Requirements: REQ-ING-010, 011, 012, 018, 027.

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

`SourceClient` exposes only `get(url) -> Response`. There is no way to issue POST, PUT or DELETE or to submit a form (D-03, INV-ING-010): the type has no such method, and a lint forbids constructing another HTTP client in the crate. A future non-GET action needs a new owner decision, not a code change. The legacy "mark complete" form submission is gone.

Access uses only the owner's own account via a cookie the owner supplies (D-99); go-live gate G6 is no longer blocked on the source's permission. CI and tests still use fixtures only.

## Fetch policy

| Aspect | Rule |
|---|---|
| Host allow-list | only configured source hosts (and allow-listed image hosts); redirects are re-checked; TLS verification cannot be disabled; no DNS or direct-IP fallback |
| Politeness | one in-flight request per source host, 0.5 s delay between pages plus jitter (setting `page_delay_ms`), honours `Retry-After`; bounded concurrency from settings |
| User-Agent | honest, names the project and a contact address; no evasion of bot protection. When the source challenges the client the operator supplies a fresh cookie (credential flow) and nothing else |
| Retries | typed, never by text. Network error and timeout are `retryable`; 429 is `rate_limited` with retry-after; other 4xx and a changed layout are `permanent`; 401, 403 or a login page is `auth_required` and parks the request in `awaiting_credential`. Default 3 attempts per request, back-off by re-queueing, never by sleeping |
| Bounds | per page 5 MiB, per book 5,000 pages, TOC pagination loop detection by page signature, 50 requests per automation run, timeouts per request (so one unit of work stays well under the lease length) |
| Cancel | the cancel flag is read before every page; the cursor (next page index) is persisted so retry resumes |
| Output | page bodies and images written atomically as files `/data/ingestion/scrape/<request_id>/<sha256>`, metadata row `scrape_pages`; removed by retention (7 days after a terminal state, 30 days at the latest); no body in any row |

## Source credential (REQ-ING-011)

One explicit credential: a cookie file in a read-only secret mount shared by `ingestion-api` and `ingestion-worker` (Netscape or header format, parsed by the adapter). It is rotated by replacing the file, with no rebuild. The database stores only status and expiry (`credential_status`); the console shows `valid`, `expiring` (3 days before `expires_at`, provisional), `expired` or `missing`. The cookie is sent on GETs only to allow-listed hosts and never appears in argv, logs, a response, the database or the browser. A probe job (`check_credential`, daily and on `POST /credential/check`) issues one authenticated GET. State machine: [state machines](../state-machines.md) section 8.

## Scrape cache and resume

Pages are keyed by `(request_id, url_key)` and reused on retry; a changed `sha256` for the same URL within one run is recorded, not overwritten. Reprocessing runs on the cache while it exists (30 days at most); afterwards the request is re-scraped. Raw pages are third-party content: they stay on the ingestion volume, are never committed and never served.

## Locked chapters (the legacy "mark complete" problem)

Some chapters render only after earlier chapters were marked complete on the source site; the legacy code submitted a form to do that. New behaviour:

1. Detect lock placeholders (adapter markers) and record `leaf_state = locked`.
2. Never change source state. The request proceeds with what exists and raises a `LockedSource` review item when any TOC leaf is locked; it is not built until resolved.
3. Resolution paths: a credential whose account has the chapters unlocked, a sanctioned export or API from the source (to be agreed with the source, OPEN-1), or accepting that the book cannot be created yet. There is no upload path (D-42).

## Completeness evidence (REQ-ING-018)

```
expected_leaves = every leaf in every TOC page (all pages; count cross-checked with the declared page count)
fetched_leaves  = leaves with HTTP 200 and non-chrome body
empty_at_source = leaves with HTTP 200 and chrome-only body, with the page hash as evidence
missing         = expected - fetched - empty_at_source   // must be empty to proceed
```

The legacy "pin the last chapter title" workaround is replaced by a general check: the last TOC leaf and the declared TOC page count must both match the fetched set. A bot-block page served with status 200 (sentinel title) is a page error, not content, and a placeholder is not counted as fetched.

## Images and covers (REQ-ING-027)

Images referenced by pages and the cover image are fetched in the same scrape with the same allow-list, GET only; the type is validated by magic bytes and size, and a missing image is a validation issue, not a silent drop.

## Drift detection

`StructureFingerprint` is the hash of the sorted CSS-class tokens and landmark paths the adapter relies on (TOC container, entry-content, pagination controls). A change from the last known good raises a `SourceDrift` review item and holds new scrape jobs of that adapter (running ones finish) instead of failing every book. A canary fixture per structure shape must pass before the hold lifts.

## Adapter tests

Fixture-based (synthetic or operator-owned pages kept outside git, never third-party book text in the repository): listing, paginated TOC, lesson and topic pages, locked placeholder, empty-at-source, cover, plus the fault set (404, 5xx, timeout, truncation, redirect loop, 429, 200 sentinel). See [test plan](../test-plan.md) TST-ING-038, 042.
