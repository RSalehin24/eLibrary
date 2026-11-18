# Error: Curated Document Requires Review

**Error message:** `Curated document requires review before asset generation.`

## What it means

Every book submitted for processing passes through the **curation and validation pipeline**. That pipeline scrapes the source site, structures the raw content into a curated document, and then runs `validate_document` to check its quality.

If validation finds non-fatal problems the pipeline marks the curated document as **`REVIEW_REQUIRED`** (as opposed to `VALIDATED` or `INVALID`). The book record **is persisted to the database**, but EPUB/HTML asset generation is skipped and the processing request transitions to the **Failed** state with this error message.

## Why review is required

The validation check produces a list of errors. Any of the following will trigger `REVIEW_REQUIRED`:

| Error                                                                                               | Example message                                            |
| --------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| **Dead TOC leaf** — a TOC entry has `has_content: true` but no scraped body was found for it        | `Dead TOC leaf without content: ভূমিকা / প্রথম অধ্যায়.`   |
| **Duplicate content path** — two or more chapters share the same path/title combination             | `Duplicate content path: তৃতীয় অধ্যায়.`                  |
| **Source chrome in body section** — navigation/ads text leaked into the chapter body                | `Source chrome found in body section s-3: login.`          |
| **Source page fetch error** — one or more chapter pages returned a non-200 status or failed to load | `Source page was not fetched: https://…/chapter-5/ (404).` |
| **Empty content item** — a chapter has a title but its scraped body is empty                        | `Content item has no body: সপ্তম পরিচ্ছেদ.`                |
| **Missing TOC for structured content** — scraped chapters exist but no TOC was generated            | `Structured content is missing a generated TOC.`           |
| **Invalid content item** — a content_item entry is malformed                                        | `Content item 3 is not structured.`                        |
| **Content item missing path** — a chapter entry has no title or path                                | `Content item 5 is missing a title/path.`                  |

The errors differ from **hard failures** (`INVALID`) which block even the book record from being created:

- Missing title
- Missing canonical URL
- Missing body content (no body sections at all)

Warnings (low-confidence sections, unassigned main content) do **not** trigger `REVIEW_REQUIRED` and do not block asset generation.

## How the exact errors are shown

When a request fails with this error, the **On Hold → Failed** tab shows the specific validation errors in the "Error Reason" column instead of the generic message. Multiple errors are separated by `•`.

## How to fix it

### Option 1 — Force Generate (recommended for most cases)

Use the **Force Generate** button on the Failed tab. This skips re-scraping and generates EPUB/HTML directly from the already-stored book data, applying automatic mitigations:

- **Source chrome removal** — blocks matching navigation/login patterns are stripped from BODY sections before export.
- **Duplicate path disambiguation** — chapters with identical paths are either renamed (distinct chapters sharing a title) or merged (inline-extraction duplicates) using the same logic as the normal pipeline.

After force generation the request moves to **Created**.

> **Note:** Force Generate does not fix source page fetch errors (missing chapter pages stay missing) or empty content items. For those cases use Option 2.

### Option 2 — Retry

The **Retry** action clears the saved state and re-runs the full pipeline from scratch (re-scraping the source site). Use this when:

- The source site was temporarily unavailable (fetch errors)
- The source site was recently fixed/updated

### Option 3 — Delete

If the content quality is fundamentally unacceptable (e.g. the source site has no real book content), delete the request.

## Pipeline flow (reference)

```
submit URL
    ↓
scrape source pages (LearnDash TOC + chapter content)
    ↓
build curated document
    ↓
validate_document()
    ↓ VALIDATED                  ↓ REVIEW_REQUIRED          ↓ INVALID
persist book record          persist book record        persist book record
generate EPUB/HTML           skip asset generation      skip asset generation
→ Created                    → Failed (this error)      → Failed (different error)
```

## Preventing future occurrences

- **Source chrome** — common on sites that render navigation inside the main content area. The `SOURCE_CHROME_PATTERNS` list in `curated_validation.py` controls what is detected. Add new patterns there if new chrome variants are found.
- **Dead TOC leaves** — usually happen when the source site has incomplete content (chapters listed in the TOC but not yet published). Nothing can be done programmatically; the source site must have the content.
- **Duplicate paths** — happen when multiple chapters share the same title (e.g. multiple "অধ্যায় এক" entries). The normal pipeline already runs `disambiguate_duplicate_content_paths` during scraping. If duplicates appear in a stored document it means the scrape pre-dates that fix; Force Generate will resolve them.
- **Fetch errors** — transient network issues or access-controlled chapters. Retry after the source site is accessible.
