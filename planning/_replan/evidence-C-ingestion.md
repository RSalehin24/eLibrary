# Evidence C — legacy ingestion and EPUB pipeline

Status: DRAFT

Source: read-only subagent survey of `archive/app/backend/apps/{ingestion,processing,catalog}` and `archive/docs`.

- **Stages:** source catalog sync → submission/resolution (URL/title/CSV → canonical URL, duplicate review) → scrape (TOC, lessons, multi-page TOC) → curate (normalize, entities/sections, classify, manifest, validate → VALIDATED / REVIEW_REQUIRED / INVALID) → persist (Book + GeneratedAsset) → build EPUB/HTML (+ structure audit).
- **Source access:** requests session with retries, 30 s timeout, host/DNS fallbacks. Cloudflare blocks scripted login, so a WordPress login **cookie is captured by hand** from a browser into a file; multi-page TOCs are truncated without it. Scrape caps: 320 nodes, depth 6, 20 lesson pages, 120k chars.
- **Orchestration:** Celery + Redis plus a custom "Central Job Engine" (Redis pub/sub, worker registry, heartbeats, stale detector: 20 min, 3 attempts). Job states queued/processing/succeeded/failed/cancelled; submission and request states are separate state machines (10 and 8 states). Progress JSON with checkpoint for pause/resume; per-chapter JSONL scrape cache survives worker restarts.
- **Storage:** raw scrape JSON on `Book`; `CuratedBookDocument` (+ entities, sections, evidence, confidence); `GeneratedAsset` (EPUB/HTML/cover, checksum, size, protected flag) unique per (book, type).
- **Review UI needs:** four queue routes plus reprocessing; row actions (open, review, start, stop, resume, retry, recreate, requeue, delete, force-generate, confirm new/new-edition); bulk select, filters, SSE live updates, per-row error reasons, progress/checkpoint.
- **Failure modes:** REVIEW_REQUIRED (dead TOC leaf, duplicate content path, source chrome in body, non-200 page, empty item, missing TOC) skips asset generation and needs Force Generate; extraction heuristics are the main complexity (preamble, dedication, book info in prose, multiple/nested TOCs, artificial splits, Bengali labels on English books); worker memory kills; background sync can keep running; ad-hoc recovery scripts exist.
- **Sizes:** no durations stated; catalog has "thousands" of source rows.
