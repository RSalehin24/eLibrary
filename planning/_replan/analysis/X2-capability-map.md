Status: DRAFT

# X2. Capability map of the eLibrary product (input to service-boundary design)

Sources: digests D1..D7 (Purpose, Features, Data, Interfaces/States sections) and `owner-requirements.md`. Feature IDs are digest IDs (D1-F#, D2-F#, D3-F#, D4-F#, D5-F#, D6-F#); "BR" = business rule in the same digest. This map describes the PRODUCT as capabilities, not legacy app boundaries and not services. Nothing here names a service. Claims are taken from the digests (themselves tagged VERIFIED/UNVERIFIED); where a digest marks a claim UNVERIFIED it stays so.

Product in one paragraph: a private, invite-only Bengali ebook library. One operator mirrors a single external source website, builds EPUB/HTML/cover assets per book through a scrape-curate-build pipeline, and publishes them into a catalog. Invited readers browse and search, keep a personal shelf, read in a web reader (with highlights, notes, bookmarks, progress), download, and send EPUBs to Kindle. A superadmin invites users and grants scoped rights. Owner requirements that shape every capability: Rust microservices each in its own container (R-02, R-03), Docker Compose (R-04), EPUB reader as its own service (R-05, Q-R1 open), Angular Material M3, responsive, light and dark (R-06..R-09), no copying of legacy defects (R-13).

Reading key for the per-capability fields:
- Change rate: how often the RULES change (H = weekly, because tied to the source site or product tuning; M = monthly; L = rarely, stable domain).
- Load: B burst, S steady, LR long-running, CPU, IO.
- Failure impact: what users (operator or reader) lose if the capability is down.
- Dep sync / async: needs an immediate answer (sync) vs can consume an event, queue item or poll (async).

---

## A. Operator pipeline

### CAP-01 Source catalog mirror and incomplete-book tracking
- Does (for the operator): keeps a local, searchable mirror of the single source website's book index (title, author line, URL, category, series), refreshes it by crawling the archive listing (live or from snapshot), flags books the source lists as "incomplete/unfinished" and later detects that they left that list (resolved), and lets the operator select mirror rows to turn into build requests. Also feeds title resolution (CAP-02) and scheduled bulk curation (CAP-09).
- Legacy features: D2-F11, D2-F12, D2-F33, D2-F37, D2-F38; D3-F1..F21, D3-F22..F27 (two-phase sync), D3-F28..F37 (incomplete flow), D3-F63 (reset); D5-F33, D5-F35.
- Owns (entities): source catalog entry (URL unique, title, author line, normalised forms, raw category/series), catalog record (mirror row with category, contributors strings, incomplete flags, derived "creation state"), sync run state (singleton per scope, checkpoint, counters), incomplete-resolution result.
- Writers / readers: written by the crawler (system) and by the operator (select, delete); read by CAP-02 (title match), CAP-09 (curation runs), CAP-10 (console), operator UI.
- Change rate: H (source markup, category keywords, archive URLs change; fragile selectors, D1 section 6).
- Sensitivity: low (public site metadata); crawl uses the source credential only indirectly (CAP-04).
- Load: LR (thousands of records, pages of 100, up to 250 incomplete pages), IO-heavy, polite rate limit; bursty when scheduled.
- Failure impact: operator cannot discover or select new books and title resolution degrades to ambiguous; readers unaffected.
- Dep sync: none required. Dep async: CAP-09 (scheduling, run control), CAP-03 (shared fetcher behaviour), CAP-04 (cookie for gated pages).
- Legacy duplication: DOUBLE. Catalog mirror existed as SourceCatalogEntry (ingestion) AND BookRecord (processing), each with its own crawler, own automation settings and own refresh state (D2-F33, D2-F36 vs D3-F1..F27, D3-F38). Derived "creation state" was kept in sync by DB triggers (D7 4.2). Both refresh paths set different defaults (D3-F38 vs model defaults).

### CAP-02 Book request intake and title resolution
- Does (for operator, and for any user who submitted by URL/title): accepts a request as a source URL, free-text Bengali title, CSV or batch; validates the URL against the source allow-list; resolves a title to a source URL by scored candidate matching with human confirmation when ambiguous; reuses an equivalent earlier request instead of re-building (dedup tree); retry, delete, bulk actions; creates build requests from catalog selections or automation.
- Legacy features: D2-F1..F9, D2-F10, D2-F13, D2-F7; D2-F25; D3-F43..F46 (request creation, selectability); D5-F34 (queue UI).
- Owns: request (input, normalised input, resolved URL, resolution status, confidence, origin user/curation/automation, status, canonical-request link), title-resolution attempt, match candidate.
- Writers / readers: written by users (submit), operator, CAP-09 automation; read by CAP-09 (dispatch), CAP-06, CAP-10, requester (own status).
- Change rate: M (matching tiers, allow-list stable; UX around candidates changes).
- Sensitivity: medium. Legacy allowed anonymous submission with 40/hour throttle and exposed a preview token to anonymous (D2 section 3); a rebuild must decide who may submit (private invite-only product).
- Load: S, bursts on bulk imports (200+ ids).
- Failure impact: no new books can be requested; existing library unaffected.
- Dep sync: CAP-01 (catalog lookup for resolution), CAP-14 (who is allowed to submit). Dep async: CAP-09 (job dispatch), CAP-06 (dedup verdicts), CAP-23 (notify requester when ready).
- Legacy duplication: DOUBLE. Two request models for one concept: BookSubmission (ingestion, with job and dedup tree) and BookCreationRequest (processing, with checkpoints and pause/resume), bound by a nullable OneToOne (D7 4.5). Two sets of statuses, retry rules (3 attempts both), stale recovery (20 min both), two duplicate regimes, "origin" enum copied (D7 4.5). Request-level dedup tree and record-level duplicate flags both existed (D2-F8/F9 vs D3-F57/F58).

### CAP-03 Source acquisition (crawl and fetch)
- Does (for the pipeline): given a canonical source book URL, fetches the landing page and the full table of contents (paginated, nested, sectioned), then every leaf chapter, with retries, polite pacing, host and DNS fallback, REST fallback for empty bodies, optional "mark complete" unlock of sequential lessons, resumable page cache, completeness gate (expected vs fetched), and a structured fetch log. Produces a raw "manifest/source snapshot" for curation.
- Legacy features: D1-F1..F25, D1-F29..F32, D2-F14, D3-F51 (fetch steps), D3-F52, D3-F53, D3-F59.
- Owns: fetch log (per URL status), page cache (resumable, disk/object), source manifest (raw pages and TOC tree, structure classification, completeness verdict). Third-party copyrighted content, never committed (project rule).
- Writers / readers: written by workers only; read by CAP-05 (curation).
- Change rate: H (selectors for the source theme, pager AJAX, rate-limit behaviour).
- Sensitivity: HIGH for outbound behaviour: authenticated session cookie, SSRF surface (cover URL host not restricted in R1, D1 BR1), mutates source-site account progress (mark-complete, D1-F22).
- Load: LR (15-20+ minutes per book, up to ~5 requests per chapter at 0.5 s spacing), IO-heavy, memory up to 2-4 GB for large books in legacy (D7 2.4); CPU light.
- Failure impact: operator cannot import new or reprocess books; published library unaffected.
- Dep sync: CAP-04 (cookie). Dep async: CAP-09 (scheduled/queued execution, cancel, heartbeat), CAP-05 (hands over snapshot).
- Legacy duplication: DOUBLE. Two acquisition implementations (`scraper.py` recursive and `book_manifest.py` manifest-first) with a bridge (D1 section 1); two URL normalisers with different failure semantics (D1-F1); two fetch/DNS stacks (D1-F4 vs D2-F14); three scrape-limit profiles (D3 5.3). A third inline-TOC detector exists for books without LearnDash lessons (D1-F19).

### CAP-04 Source-site credential custody
- Does (for the operator): holds the source-site login state (a session cookie harvested out of band because the source is behind Cloudflare), checks its age, supplies it to CAP-03, and surfaces an actionable "sign-in required" condition when the cookie is expired or the TOC is incomplete.
- Legacy features: D1-F6; D3-F53 (sign-in message); D7 3.4 (manual Firefox cookie capture, scp).
- Owns: one secret document (cookie state), expiry metadata.
- Writers / readers: operator writes (upload/refresh); CAP-03 reads.
- Change rate: L (but expiry ~yearly forces manual action).
- Sensitivity: HIGH (live login cookie; legacy stored it as a file in the storage directory and scp'd it).
- Load: negligible.
- Failure impact: scrapes of gated content fail with a user-visible error; nothing else.
- Dep sync: none. Dep async: none (read by CAP-03 at fetch time).
- Legacy duplication: none, but handled twice at deploy/ops layer (env email/password settings AND file cookie, D2 section 6).

### CAP-05 Curation (normalise, structure, validate, version)
- Does (for the operator and downstream build): turns the raw snapshot into a structured, validated "curated document": contributors and roles, series and categories, book-info block, dedication, front/back matter, chapter tree with stable section IDs, evidence and confidence, structure classification, and a status (validated / review required / invalid). Keeps append-only versions per source URL. Quality rules are Bengali-specific (labels, honorifics, dedication headings, chapter-heading scoring).
- Legacy features: D1-F12, D1-F26..F28, D1-F33..F36, D1-F41; D2-F28..F32; D3-F51 (normalise step), D3-F54 (force-mode chrome stripping).
- Owns: curated document versions (document JSON, entities, sections, evidence, validation summary), normalisation rule tables (role vocabulary, label lists, key order), regression fixtures (13 spec books, 300-URL harness knowledge in tests, D7 section 8).
- Writers / readers: written by workers; read by CAP-07 (build), CAP-08 (persist), CAP-11 (review UI), CAP-16 (contributors, TOC display), CAP-19 (reading package).
- Change rate: H (rules are added per new anomaly; dedication/front-matter heuristics are the hardest, D7 section 6).
- Sensitivity: low technically; content is third-party copyrighted.
- Load: CPU-heavy per book (parsing, scoring), bounded memory; batch-friendly.
- Failure impact: no new or reprocessed books; library unaffected.
- Dep sync: none (pure function of snapshot + rule tables). Dep async: CAP-03 (input), CAP-06 (duplicate check needs normalised title/contributors).
- Legacy duplication: HEAVY. Section derivation was done in curation AND again in the EPUB builder (D1-F37, D1 section 7.5 "derive sections (again)"); contributor/role normalisation exists in the ingestion normaliser, in catalog display logic (D4-F41), and four times in the frontend (D5 section 5, export). Three copies of the content in the DB: Book columns, curated JSON, curated section rows, plus rendered assets (D7 4.3). Two curation paths: `curate_book_document` and legacy `scrape_book` + `curate_scraped_book_data` (D3-F51). CLI curation had a quality gate not wired in runtime (D2-F32).

### CAP-06 Duplicate detection and review
- Does (for the operator): decides whether an incoming book already exists (exact source URL, exact title with contributor overlap, fuzzy metadata), distinguishes "same work, new edition" from a true duplicate, and gives the operator a queue to confirm, dismiss, mark "new", or "new edition" (grouping editions of one work).
- Legacy features: D2-F21, D2-F22, D2 section 4.2; D3-F45 (selectability with duplicate exception), D3-F57, D3-F58, D3-F64 (new / new_edition / confirm_duplicate); D1-F36 (group hint).
- Owns: duplicate review (verdict, evidence, status), edition group (canonical title), "confirmed not duplicate" flags.
- Writers / readers: written by pipeline workers and the operator; read by CAP-02, CAP-08, CAP-10.
- Change rate: M (thresholds, rules about editions/translators tuned over time).
- Sensitivity: low.
- Load: S, CPU-light but legacy scanned ALL non-deleted books with no source filter (D2 4.2) so scales with library size.
- Failure impact: pipeline cannot decide; if it fails open, duplicate books enter the library; if it fails closed, new imports stall in review.
- Dep sync: CAP-15/CAP-16 (read existing books/contributors). Dep async: CAP-02, CAP-08 (verdict feeds the lifecycle).
- Legacy duplication: DOUBLE. Duplicate logic in the ingestion job (3 detectors) and again in processing (source-URL claim, exact title, optional metadata check disabled by default, D3 BR-16); duplicate review table in ingestion vs duplicate flags/links on records and requests in processing; the edition-aware classifier existed but was unused (D2 4.2 item 4).

### CAP-07 Book build (EPUB, HTML, cover) and structure audit
- Does (for readers and Kindle): from a curated document builds the deliverables: EPUB 3 with fixed spine order, nested navigation, labelled front/back pages, generated 1200x1800 cover when none is available; single-file HTML book; filename safety; an offline structure auditor (zip/OPF/spine/nav consistency) used by the regression harness. Gate: refuse build when more than a third of chapters are empty placeholders.
- Legacy features: D1-F37..F45; D2-F19 (required assets HTML+EPUB, cover optional, checksum); D3-F54 (export step), D3 section 6.5 (EPUB output contract).
- Owns: generated asset files and records (type, status, size, sha256, content type, path), bundled fonts/templates.
- Writers / readers: written by workers; read by CAP-08 (register), CAP-19/20/22 (serve, deliver).
- Change rate: M (templates, labels, nav rules; EPUB spec stable).
- Sensitivity: low technically; outputs are third-party copyrighted.
- Load: CPU-heavy and memory-heavy per book (image generation, zip), burst on bulk reprocess; LR seconds to minutes.
- Failure impact: new/reprocessed books stay unpublished or need review; existing assets still served.
- Dep sync: none. Dep async: CAP-05 (curated document), CAP-08 (asset registration), CAP-09 (job).
- Legacy duplication: section derivation duplicated with CAP-05 (see above); HTML preview later re-normalised AGAIN at serve time (D4-F21) so front-matter promotion and dedication cleanup exist in the builder and in the serving path; unused template (toc) retained (D1 section 6).

### CAP-08 Publish and book lifecycle
- Does (for operator and readers): persists the curated result as a catalog book (upsert by source URL/title, revival of soft-deleted), registers assets, applies the review gate (validated -> ready; otherwise needs review, no assets), handles reprocess (previous state saved and restored), soft delete, self-healing when a stored asset is missing, and the single lifecycle state machine (draft, processing, needs_review, ready, published, archived, deleted) with a separate review state. Decides when a book becomes visible to readers.
- Legacy features: D1-F36; D2-F15 (persist step), D2-F16, D2-F17, D2-F18, D2-F19; D3-F54..F56, D3-F61; D4-F23, D4-F36, D4 section 7.7/7.8; D5-F25.
- Owns: book lifecycle state, review state, asset status per (book, type), book-source link (normalised source URL unique), reprocess bookkeeping.
- Writers / readers: written by pipeline, operator, and the self-heal path (any reader hitting a missing file in legacy); read by everyone downstream (CAP-16, 19, 20, 22).
- Change rate: M.
- Sensitivity: medium (visibility gate; legacy showed draft/needs_review/rejected books to every user, D4 4.11).
- Load: S, short transactions; BURST on bulk reprocess.
- Failure impact: pipeline outputs cannot be published; readers still see existing books.
- Dep sync: CAP-06 (verdict), CAP-07 (assets). Dep async: CAP-09 (job completion events), CAP-23 (notify), CAP-24 (audit).
- Legacy duplication: HEAVY. Lifecycle state stored in at least seven places (Book.state, Book.review_state, BookSubmission.status, BookCreationRequest.state, BookRecord.book_creation_state, ProcessingJob.status, CuratedBookDocument.status; D7 4.4). Persistence implemented twice (`persist_curated_book_with_hooks` and `persist_curated_book`/`persist_scraped_book`, D1-F36 vs D3-F54). Persistence was not transactional (D1 7.6).

### CAP-09 Job orchestration, scheduling and automation
- Does (for the operator): runs the long, retry-prone work: queueing, capability routing to workers, FIFO dispatch, heartbeats, cancel/pause/resume, bounded retries, stale-work recovery, resume from checkpoint, and scheduled automations (daily/weekly/monthly catalog refresh, curation runs over the whole mirror, incomplete reconciliation). Exposes run history, per-job logs and bulk stop/resume/delete.
- Legacy features: D2-F4, D2-F23..F27, D2-F34..F36, D2-F39, D2-F40; D3-F7..F18 (sync control), D3-F38..F42, D3-F47..F50, D3-F60..F62; D5-F37.
- Owns: job (type, status, attempts, cancel flag, worker, payload), job log, curation run (summary counters), automation settings (singletons), worker registry/heartbeats, sync checkpoints.
- Writers / readers: written by the engine, workers, operator; read by operator console, CAP-10.
- Change rate: M.
- Sensitivity: medium (operator-only; controls expensive external crawling).
- Load: S control plane; the work it dispatches is LR; BURST on automation start.
- Failure impact: nothing new gets built or refreshed; stuck jobs un-recovered; reader side unaffected.
- Dep sync: none inward. Dep async: every pipeline capability (CAP-01, 02, 03, 05, 07, 08) as handlers; CAP-10 (events out), CAP-23 (failure/finish alerts).
- Legacy duplication: HEAVY and the worst. Three overlapping execution mechanisms for one job: Celery task, custom Redis "central job engine" (FIFO, heartbeat, DB recovery), and an inline fallback that runs the pipeline inside the web request when dispatch fails (D2 7.3); a pipeline "ticker" and "runtime tick" for no-worker mode (D3-F49, D3-F62); stale recovery implemented twice (jobs: 20 min, requests: 20 min, syncs: 20 min; D2-F24, D3-F60); two automation settings tables (D2-F36 vs D3-F38) with different defaults; per-minute DB polling for "is it due" (D7 2.2). Pause/resume model in processing vs cancel_requested model in ingestion.

### CAP-10 Operator console live status
- Does (for the operator): provides an always-current view of pipeline state: overview counters, per-bucket tables (queue, processing, created, paused, failed, duplicate, deleted, incomplete, multi-page TOC, empty chapters, reprocessing jobs), server-side search/filter/pagination, push notification of what changed, and batched "N books created" notices.
- Legacy features: D3-F19, D3-F65..F71; D2-F26, D2-F27; D5-F32..F38, D5 section 7.
- Owns: no source-of-truth data. Legacy persisted read-model tables (UI projection payloads, per-domain version counters) inside the system of record (D7 4.3). In a rebuild this is a derived read model.
- Writers / readers: derived from CAP-02/05/08/09 events; read by the operator UI only.
- Change rate: H (UI cards change with pipeline understanding).
- Sensitivity: medium (operator-only; exposes URLs, errors, provenance).
- Load: S with fan-out; SSE connection held per operator tab; polling fallback every 15 s in legacy.
- Failure impact: operator flies blind or must poll; no data loss.
- Dep sync: none. Dep async: events from CAP-02, 08, 09, 01.
- Legacy duplication: two push channels with separate SSE streams and wire formats (processing "versions" stream vs ingestion "job-update" stream, D5 section 7); two UI vocabularies of states; page-level `canLoadProcessingState` vs nav rules (D5 section 4).

### CAP-11 Metadata editing and review (operator)
- Does (for the operator): edit title, summary, contributors by role, series, categories, book-info/dedication/main content, TOC; every edit snapshots before/after; review records (pending/needs-review/approved/rejected); replace the EPUB by upload or regenerate it; soft-delete a book. Slug and catalog code consequences are propagated.
- Legacy features: D4-F33..F36; D5-F23..F25.
- Owns: metadata version snapshots, metadata review records.
- Writers / readers: written by operator (or scoped editors); read by operator.
- Change rate: M.
- Sensitivity: medium (alters what readers see; scoped by book/category/writer in legacy).
- Load: S.
- Failure impact: operator cannot correct metadata; reading unaffected.
- Dep sync: CAP-14 (scoped edit permission), CAP-15 (relations, slug, codes), CAP-08 (state). Dep async: CAP-07 (regenerate), CAP-24 (audit).
- Legacy duplication: book `state` and `review_state` writable by direct PATCH and via the review API and via self-heal (D4 4.13), three writers of the same field. No snapshot revert API.

---

## B. Identity and access

### CAP-12 Authentication and account security
- Does (for every user): email + password login, TOTP second factor with admin-enforced enrolment, session handling and logout, password reset by email, first-password set from an invite, profile (name, photo, password change), brute-force throttling, CSRF/session safety, "fence" that blocks everything until required 2FA is enrolled. (Demo login is a legacy feature; see section on decisions.)
- Legacy features: D4-F1, D4-F2, D4-F3, D4-F5..F9, D4-F11, D4-F12; D5-F1..F8, D5-F3.
- Owns: user credential record (email, password hash, TOTP devices, nonce for link invalidation, flags: active, totp_required, email_setup_pending), sessions, profile (name, image).
- Writers / readers: users write their own; CAP-13 writes on invite/disable; all services read identity (who is calling).
- Change rate: L (security rules stable), but policy tweaks occasionally (password length, throttles).
- Sensitivity: HIGHEST (credentials, TOTP secrets, session tokens, personal data).
- Load: S; burst at peaks of logins; password hashing is CPU-bound by design.
- Failure impact: nobody can log in; reader tokens already issued may still work; whole product effectively down for users.
- Dep sync: CAP-23 (send reset/invite mail; async acceptable), CAP-24 (audit login events). Dep async: CAP-23.
- Legacy duplication: link-token mechanism shared between invite and reset (intentional); three different "can this user do X" evaluations client-side (D5 section 4: hasCapability, navigation.js, AccessPage); throttle sets defined in settings but demo-login, resets validate/confirm and Kindle send unthrottled (D4 4.10). Demo login mints a shared user with no credentials by GET (D4-F3).

### CAP-13 User administration and invitation
- Does (for the superadmin): list/search/filter users, create with or without password, send and resend invite emails, activate/deactivate, delete, require 2FA, assign account-level capabilities in one form.
- Legacy features: D4-F4, D4-F5 (admin side), D4-F14; D5-F29, D5-F31.
- Owns: no separate data (operates on CAP-12 users and CAP-14 grants); invite state is on the user.
- Writers / readers: superadmin writes; superadmin reads.
- Change rate: L.
- Sensitivity: HIGH (privilege assignment, account deletion).
- Load: very low.
- Failure impact: cannot onboard or manage users; existing sessions unaffected.
- Dep sync: CAP-12, CAP-14. Dep async: CAP-23 (invite mail; legacy rolled back user creation if the mail failed, D4 4.10).
- Legacy duplication: account-level capability sets were synced as "global grants" by a separate rule path (D4 4.2 `sync_global_grants`) in addition to the grants API, with different allowed scope sets (10 vs 12).

### CAP-14 Entitlements (scoped grants, ownership, read-once)
- Does (for the system, administered by the superadmin): answers "may user U do action A on book B?": 12 legacy scopes, optional narrowing to a book, category or writer, expiry, mutual exclusion of read-once and read-durable, an implicit-right "ownership" rule, the read-once ledger (one opening per book), and capability lists for the UI. Single decision point used by catalog, reading, download, Kindle, metadata and operator consoles.
- Legacy features: D4-F13..F18; D5-F30; D4 sections 4.1..4.4; D6 4.4.
- Owns: permission grants, read-once opening records, the owner (My Books-as-entitlement) link if kept.
- Writers / readers: superadmin writes grants; reading/download paths write the opening record; every request path reads.
- Change rate: M (new scopes appear: 4 of 12 scopes had meaning changes or renames in the schema history, D7 5 item 4).
- Sensitivity: HIGH (privilege boundary).
- Load: very high read rate (every request), tiny data; latency-sensitive; cacheable.
- Failure impact: if sync dependency fails closed, all protected reading/download stops; this is the most widely depended-upon capability.
- Dep sync: CAP-12 (identity), CAP-15 (category/contributor membership of a book for scoped checks). Dep async: CAP-24 (audit changes).
- Legacy duplication: rules evaluated in `user_has_scope`, in per-view inline checks for scoped metadata edit (D4 4.13), in `ensure_book_reader_access` (which does NOT honour ownership; D4 4.3), and in the frontend three times (D5 4). Ownership rule is a defect: any authenticated user could grant themselves full access by POST my-books with no permission check (D4-I1, D4 4.3). Read-once record and reading-session overlap (D7 4.1 access).

---

## C. Catalog

### CAP-15 Catalog taxonomy and identifiers
- Does (for catalog, operator and search): canonical writers/translators/editors/publishers (contributors with roles), series, categories; Unicode-aware normalisation (Bangla punctuation, combining signs); unicode slugs with collision handling and legacy-slug fallback; structured 10-character catalog codes for books, writers, series, categories; noise filtering of contributor names; reference lists with book counts.
- Legacy features: D4-F31, D4-F39, D4-F40, D4-F41; D2-F31 (series/category split); D5-F10, D5-F12.
- Owns: contributor, series, category entities and book relations (role, order, raw value), slug and code allocators.
- Writers / readers: written by CAP-08 on publish and CAP-11 on edit; read by CAP-16, CAP-06, CAP-14 (scoped grants), CAP-11.
- Change rate: L for model, M for noise-filter and normalisation rules.
- Sensitivity: low.
- Load: S read-heavy; code allocation needs serialisation (legacy: max+1 scan, no lock, unique constraint only).
- Failure impact: browse filters, slugs and permissions-by-category break; core listing may still work from denormalised fields.
- Dep sync: none. Dep async: CAP-08/11 changes propagate to CAP-16 indexes.
- Legacy duplication: contributor and role normalisation implemented in ingestion (D2-F28), in catalog display (D4-F41), and four times in the frontend (D5 section 5). Catalog code algorithm implemented three times by copy-paste across migrations (D7 5 item 3). Book code embeds category/author sequences, so it is not stable when those change (D4 4.12); whether the rebuild needs this at all is a product question.

### CAP-16 Catalog browse, search and export
- Does (for readers and the operator): list and search the catalog (title, code, contributor, series, category), filter by role/ownership/record type/state, faceted cross-filtering, sorting, paging or infinite scroll, per-book detail (hero, contributors, TOC with empty-chapter indicators, dedication, provenance for staff), property browse tables (categories, writers, ...), and CSV/PDF/label-sheet export of any filtered result. Per-user flags (in my books, sent to Kindle) annotate each row.
- Legacy features: D4-F29, D4-F30, D4-F31, D4-F38; D5-F9, D5-F10, D5-F12, D5-F14, D5-F15, D5-F22, D5-F28.
- Owns: no source-of-truth (a read model over CAP-08/15 data, with search indexes). Saved searches live in CAP-17.
- Writers / readers: derived; read by all users.
- Change rate: M (new filters, sort orders).
- Sensitivity: medium. Legacy listed every non-deleted book regardless of state, including drafts and rejected (D4 4.11); a rebuild needs an explicit visibility rule. Source URLs/provenance restricted by scope.
- Load: S, read-heavy, latency-sensitive; large exports are BURST/CPU (legacy client built PDF in the browser from 100-item pages, D5 section 5).
- Failure impact: readers cannot find or open books; the product looks down even though reading by direct link could work.
- Dep sync: CAP-14 (visibility, source-record gate), CAP-15, CAP-17 (per-user flags). Dep async: CAP-08 (index updates).
- Legacy duplication: three code paths for the same catalog-entries list in ingestion (D2 #22); client export reimplemented per page (catalog/manual: CSV, PDF, Excel); facet endpoints returned two different shapes (D5 section 6); record-type vocab differs across screens.

### CAP-17 Personal library: shelf, saved filters, per-user lists
- Does (for each reader): "My Books" shelf (add/remove, date added, sort), saved filters, the user's list of Kindle-sent books, continue-reading list. The shelf is a personal bookmark list, not an entitlement (legacy conflated the two).
- Legacy features: D4-F28, D4-F37, D4-F16 (ownership half); D5-F11, D5-F13, D5-F9 (My Books and Kindle views).
- Owns: user-book membership, saved filter (target, name, params).
- Writers / readers: the user; read by CAP-16 (row flags).
- Change rate: L.
- Sensitivity: low (personal preference data).
- Load: S.
- Failure impact: shelf and saved filters unavailable; browsing works.
- Dep sync: CAP-16. Dep async: none.
- Legacy duplication: "owner" meaning appears three times: user imported the book (D4 4.3 intended), user added it to My Books (any user, any book), and a processing-created link via submission save side-effect (D2 section 5 BookSubmission.save creates UserBook).

### CAP-18 Physical (manual) books registry
- Does (for the operator and permitted users): records physical books the library owns (title, writer/translator/editor, category, series, publisher, compilation, binding, price, language, summary), batch-entry composer, edit, list with filters, exports (CSV, PDF, Excel with grouping); a personal reading log per physical book.
- Legacy features: D4-F32; D5-F21, D5-F26, D5-F27, D5-F28 (manual export).
- Owns: manual book records (stored as books with record type manual in legacy).
- Writers / readers: users with the physical-books scope; read by the same plus catalog filters.
- Change rate: L.
- Sensitivity: low.
- Load: very low.
- Failure impact: physical list unavailable only.
- Dep sync: CAP-14, CAP-15. Dep async: none.
- Legacy duplication: stored in the same book table as digital books with a `record_type` discriminator and a duplicate of contributor handling (publisher stored both as a column and as a contributor, D4 4.12); personal reading log stored ONLY in browser localStorage (D5-F21), so it is neither shared nor backed up; Excel/PDF/CSV exports duplicated with CAP-16.

---

## D. Reading, preview, download

### CAP-19 Reading delivery (launch, session, content package)
- Does (for readers): authorises opening a book, creates a short-lived reading session, and serves what the web reader needs: a manifest (book, TOC, URLs, saved position, annotations) and the book content. The product requirement is that this is its own service (R-05); what "content" means (whole EPUB streamed to browser, server-parsed sanitised chapters, or both) is the open question Q-R1 (D6 section 5.2; D6 recommends hybrid: server-produced reading package, thin Angular renderer, original EPUB separately gated for download).
- Legacy features: D4-F19; D2-F20 (action links); D6-F1..F14 (layout, TOC, themes, fonts, typography), D6 section 3 (lifecycle), D6 4.2; D5-F16.
- Owns: reading session/token (expiry 2 h, launch count), reading package or cached chapters (if hybrid), reader-side preferences if stored server-side.
- Writers / readers: written on launch and by CAP-07 (package invalidation on reprocess); read by the reader client.
- Change rate: M (reader UX evolves; content format fixed once chosen).
- Sensitivity: HIGH (delivers the copyrighted book; legacy token-in-URL and no re-check of grants on token endpoints; stored-XSS via unsanitised book HTML; D6 section 4.3, 5.2).
- Load: S per reader; BURST on popular launches; CPU if server parses/sanitises on first open; IO for large EPUB; legacy per-resource route read the whole zip per call.
- Failure impact: nobody can read online (HTML preview and download may remain); central to the product value.
- Dep sync: CAP-14 (entitlement decision, read-once check/record), CAP-12 (session identity), CAP-08 (asset ready, book visible). Dep async: CAP-07 (package build), CAP-21 (annotations returned in manifest; legacy inlined them).
- Legacy duplication: two credential schemes in one flow (session cookie + URL token); slug-based and token-based twins of the progress/bookmark/highlight endpoints (D6 4.2); reader code duplicated byte-for-byte in `src/embedded-reader` and `public/epub-reader` (D6 section 5.1); theme mapping duplicated in three files (D6 5.1); ownership honoured on launch but not on annotations (D4 4.3).

### CAP-20 Preview and file download
- Does (for readers): serve the cover image, a normalised HTML preview, and file downloads (EPUB, HTML) under per-type permission rules, with a readable filename, and the missing-file recovery signal to CAP-08.
- Legacy features: D4-F20, D4-F21, D4-F23; D5-F19.
- Owns: nothing (serves CAP-07 assets); cover and download access log if audited.
- Writers / readers: read by users and by CAP-19 (cover).
- Change rate: M.
- Sensitivity: HIGH (full-book exfiltration; legacy HTML served unsanitised from the API origin with no CSP, D4 4.6).
- Load: S, IO-heavy (large files), range requests desirable; cacheable per version for covers.
- Failure impact: no downloads/previews/covers; covers missing degrade the catalog UI.
- Dep sync: CAP-14, CAP-08 (asset state), storage. Dep async: CAP-24.
- Legacy duplication: preview HTML normalisation at serve time duplicates builder logic (see CAP-07); soft-deleted books still reachable via these endpoints because lookup lacks the deleted filter (D4 4.6).

### CAP-21 Reading progress and annotations
- Does (for readers): remembers last position and percent per book; bookmarks; highlights in five colours; quotes; notes with tags; edit/delete; "My Notes" cross-book view with server-side text search and filters.
- Legacy features: D4-F24..F27; D5-F17, D5-F18; D6-F16..F27 (client behaviours), D6 4.1.
- Owns: reading position (per user/book), bookmark, highlight/quote/note (anchor, text, note, colour, kind, tags).
- Writers / readers: the user via the reader or notes page; read by CAP-19 (manifest), CAP-16 (continue reading), notes page.
- Change rate: M (anchor scheme depends on the reading-content decision; migration of legacy CFI anchors is an open question, D6 5.2).
- Sensitivity: HIGH personal data (reading history, private notes).
- Load: S, frequent small writes (progress debounced at 350 ms), sync-latency tolerant.
- Failure impact: loses saved position and annotation sync; reading itself may continue.
- Dep sync: CAP-12 (identity), CAP-19 (session/book binding). Dep async: none.
- Legacy duplication: two route families (slug-based and token-based) with different access rules; bookmark delete/update without re-check of book access (D4 4.8); reading-session and read-once record overlap (D7 4.1); unique duplicate bookmark yields 500 (D6 4.1). Initial-progress bug posts the page URL as location (D6 section 3).

### CAP-22 Kindle delivery
- Does (for readers): store the user's Kindle addresses (only `@kindle.com`), email the book's EPUB to each, report per-address result, record last-sent time, show the sender address to whitelist at Amazon.
- Legacy features: D4-F10, D4-F22; D5-F20; D5-F9 (kindle-sent view).
- Owns: kindle addresses (on the user in legacy), send log (last sent per user/book).
- Writers / readers: users; the delivery worker.
- Change rate: L.
- Sensitivity: medium-high (personal addresses; outbound mail with a copyrighted attachment; whole-file read into memory).
- Load: BURST/IO (attachment up to megabytes, one message per address, synchronous in legacy); needs async with retry.
- Failure impact: Kindle delivery fails; other reading paths unaffected.
- Dep sync: CAP-14 (send:kindle), CAP-20 (asset fetch). Dep async: CAP-23 (SMTP transport), CAP-24.
- Legacy duplication: SMTP forced even when a mail API backend was configured (D4 4.7), so mail transport existed in two configurations; no rate limit, no size check.

---

## E. Cross-cutting

### CAP-23 Notifications (email and in-app)
- Does: sends transactional emails (invite, password reset, Kindle documents), delivers in-app toasts and operator notices (batched "N books created"), and carries brand/language templating. A rebuild also needs notify-on-ready to a requester and failure alerts to the operator.
- Legacy features: D4-F5 (mails), D4-F22 (transport); D5-F38, D5-F39; D3-F70 (notification summary).
- Owns: email templates, delivery log (not kept in legacy), notification preferences (only the mute switch in legacy).
- Writers / readers: written by other capabilities; read by recipients.
- Change rate: M (copy and templates).
- Sensitivity: medium (reset/invite links are credentials; reset enumeration was deliberate, D4 4.10).
- Load: BURST (bulk invites), IO.
- Failure impact: no invites or resets (blocks onboarding and recovery); Kindle delivery blocked; in-app toasts degrade quietly.
- Dep sync: none. Dep async: consumes events from CAP-12, 13, 22, 08, 09.
- Legacy duplication: 90 percent duplicated HTML templates, English only, brand hard-coded (D7 section 6); toast sound/dedup logic in the client only.

### CAP-24 Audit trail
- Does: records who did what to which object and when (logins, grants, user create/delete, metadata edits, publish, delete, downloads, Kindle sends, operator actions), with request id, IP and user agent, append-only and queryable by the superadmin.
- Legacy features: D4 section 5 (AuditLog model: no code in accounts/access/catalog wrote to it), D2 audit verbs (three: submission.created, fulfilled_from_database, processed), D7 4.1 common.
- Owns: audit events.
- Writers / readers: every capability writes; superadmin reads.
- Change rate: L.
- Sensitivity: HIGH (integrity matters; contains personal data).
- Load: S write-heavy, append-only, BURST during bulk operations.
- Failure impact: writes must not block the action; if lost, forensic gaps. Reading downtime only affects admin investigation.
- Dep sync: none (fire-and-forget with durable delivery). Dep async: events from all capabilities.
- Legacy duplication: not really implemented; ProcessingLog (per job), MetadataVersion (per edit) and PermissionGrant history substituted for audit in different ways.

### CAP-25 Backup, restore and migration
- Does: scheduled consistent backups of the database and stored assets, offsite copy, integrity manifest (checksums, row counts), restore drill, and a controlled host-to-host migration (drain, freeze, snapshot, restore, verify).
- Legacy features: D7 3.2 (none), D7 3.3 (migration toolkit, ~2k lines of bash).
- Owns: backup artifacts and manifests.
- Writers / readers: ops automation; ops.
- Change rate: L.
- Sensitivity: HIGH (dumps contain password hashes, TOTP keys, personal data, copyrighted books; encryption needed).
- Load: LR/BURST, IO-heavy, off-peak.
- Failure impact: invisible until disaster; then data loss. Legacy recovery was accidental via curated-document versions (D7 3.2).
- Dep sync: none. Dep async: CAP-27 (scheduling), CAP-26 (alert on failure).
- Legacy duplication: none for backup (absent); migration toolkit has its own env, SSH and compose logic.

### CAP-26 Observability (logs, metrics, health, alerts)
- Does: structured logs with request/correlation ids across services, metrics (queue depth, job duration, error rates, scrape success), real readiness/liveness checks (not a CSRF endpoint), alerting on stuck jobs, expired source cookie, failed backups, disk/memory pressure.
- Legacy features: D7 section 8 (plain console logs, no metrics, no tracing), health via `/api/csrf/` (D7 2.1).
- Owns: telemetry streams.
- Writers / readers: all services write; operator reads.
- Change rate: L.
- Sensitivity: medium (logs must not contain tokens or personal data).
- Load: S, volume-proportional.
- Failure impact: operations blind; no direct reader impact.
- Dep sync: none. Dep async: from all.
- Legacy duplication: none (absent). Worker liveness checked by Celery heartbeat AND the engine stale detector (D7 2.1).

### CAP-27 Configuration, secrets and deployment
- Does: typed configuration validated at start (fail on missing/insecure secrets), secret storage and rotation, reproducible image build and tagged release, Compose stack for dev and production (owner requirement R-04), edge TLS, migrations as a gated step with backup first, rollback, zero-surprise first-admin bootstrap (no password printing).
- Legacy features: D7 sections 2, 3.1, 7; D4-F11 (seed superadmin).
- Owns: environment definitions, image tags.
- Writers / readers: owner/ops.
- Change rate: M.
- Sensitivity: HIGH (secrets).
- Load: n/a.
- Failure impact: can't deploy or recover; running system unaffected.
- Dep sync: none. Dep async: CAP-25.
- Legacy duplication: three near-identical Compose files (dev, local-production, production) plus host nginx/certbot outside Compose and a separate migration toolkit with its own env handling (D7 2.3, 3.3).

### CAP-28 Web client shell and design system
- Does (for all users): single Angular Material M3 application shell: routing and guards driven by ONE server-provided permission set, session bootstrap, responsive layout for mobile/tablet/desktop, light/dark first-class on every screen including the reader (OS preference default, persisted toggle, WCAG AA), minimalist look, backend-down handling, toast system, generated types from the Rust contracts.
- Legacy features: D5-F39..F42, D5 sections 4/5/7; D6 section 6 (design language to replace, not keep).
- Owns: client-only preferences (theme, muted alerts).
- Writers / readers: user; the app.
- Change rate: H.
- Sensitivity: low (but route-guard correctness matters, D5 section 4).
- Load: S; static assets cacheable.
- Failure impact: nobody can use the product; static serving is trivial to keep up.
- Dep sync: all APIs via the gateway. Dep async: push channels from CAP-10.
- Legacy duplication: three client-side authorisation sources (D5 section 4); theme tokens defined four times and a 1806-line dark-mode override sheet (D6 section 6); contributor normalisation duplicated four times in the client (D5 section 5); every plain 403 treated as session expiry (D5 section 7).

---

## Capability dependency matrix

Reading: row depends on column. `S` = needs an immediate answer (synchronous call); `A` = asynchronous (event, queue, poll, eventual read model); blank = none. Only capabilities with dependencies appear; infra capabilities (CAP-24..27) are consumers of events from everyone and are not repeated in every row. Every capability also depends on identity (CAP-12) for the caller; omitted from rows except where it is the primary dependency.

| Row \ Col | 01 | 02 | 03 | 04 | 05 | 06 | 07 | 08 | 09 | 10 | 11 | 12 | 14 | 15 | 16 | 17 | 19 | 20 | 21 | 23 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 01 Source catalog mirror | | | S fetch | S | | | | | A | | | | | | | | | | | |
| 02 Request intake | S | | | | | A | | | A | | | | S | | | | | | | A |
| 03 Acquisition | | | | S | | | | | A | | | | | | | | | | | |
| 05 Curation | | | A | | | A | | | A | | | | | | | | | | | |
| 06 Duplicate review | | A | | | A | | | A | | | | | | S | S | | | | | |
| 07 Build | | | | | A | | | A | A | | | | | | | | | | | |
| 08 Publish and lifecycle | | | | | A | S | S | | A | | | | | A | | | | | | A |
| 09 Orchestration | A | A | A | | A | A | A | A | | | | | | | | | | | | A |
| 10 Operator console | A | A | | | | | | A | A | | | | S | | | | | | | |
| 11 Metadata review | | | | | | | A | S | | | | | S | S | | | | | | |
| 13 User admin | | | | | | | | | | | | S | S | | | | | | | A |
| 14 Entitlements | | | | | | | | | | | | S | | S | | | | | | |
| 15 Taxonomy | | | | | | | | A | | | A | | | | | | | | | |
| 16 Browse/search | | | | | | | | A | | | | S | S | S | | S | | | | |
| 17 Personal library | | | | | | | | | | | | S | | | S | | | | | |
| 18 Physical books | | | | | | | | | | | | S | S | S | | | | | | |
| 19 Reading delivery | | | | | | | A | S | | | | S | S | | | | | | A | |
| 20 Preview/download | | | | | | | | S | | | | S | S | | | | S | | | |
| 21 Progress/annotations | | | | | | | | | | | | S | | | | | S | | | |
| 22 Kindle | | | | | | | | S | | | | S | S | | | | | S | | A |
| 12 Authentication | | | | | | | | | | | | | | | | | | | | A |

Findings read off the matrix:
1. The only capability needed synchronously by almost every user-facing path is CAP-14 (entitlements) plus identity (CAP-12). They are read-hot, tiny, and cache-friendly, which makes them the natural "decision point" and the hardest to keep available.
2. The operator pipeline (CAP-01..03, 05..09) is connected almost entirely by ASYNC edges; nothing on the reader side needs it synchronously. A failure there never takes down reading.
3. CAP-08 (publish) is the single seam between the two halves: it is the writer of book/asset state that CAP-16, 19, 20, 22 read. Treat it as the contract boundary between the "producing" half and the "serving" half.
4. CAP-06 (duplicate review) has SYNC reads of the existing library (CAP-15/16). In the legacy app that scan was unbounded; the rebuild should serve it from an indexed read model.
5. CAP-19 (reading delivery) has sync dependencies on CAP-14, CAP-12 and CAP-08, async on CAP-21 and CAP-07; it is the capability most affected by the open Q-R1 decision.
6. No cycle among synchronous edges; the only candidate cycle (08 <-> 11 <-> 15) is broken if 15 is written through 08/11 events and read synchronously by 16/14.

---

## Capabilities missing or implicit in the legacy app that a rebuild needs

| # | Missing capability | Why it is needed | Legacy evidence |
|---|---|---|---|
| M1 | Audit trail (CAP-24) | Private invite-only product with grants, deletions, downloads of copyrighted books; must answer who changed or took what. | AuditLog model existed, nothing in accounts/access/catalog wrote to it; only three ingestion verbs (D4 5, D2 5). |
| M2 | Backups and tested restore (CAP-25) | Single VM, single DB with the only copy of curated content and user data. | "No backups" (D7 3.2); recovery was accidental via version history (D7 6). |
| M3 | Observability: structured logs, metrics, readiness, alerts (CAP-26) | Long-running scrapes, stuck jobs, expiring source cookie, disk growth. | Plain console logs, no metrics/tracing, CSRF endpoint as health (D7 section 8). |
| M4 | Typed config and secret management (CAP-27) | Insecure defaults silently accepted; admin password printed. | D7 section 7. |
| M5 | Explicit book visibility and publication rule | Drafts, needs_review and rejected books were visible to every user. | D4 4.11 (query excluded only soft-deleted). |
| M6 | Reading-vs-download separation and content sanitisation | Reader hands the whole EPUB to the browser, preview HTML served unsanitised without CSP, token in URL. | D6 sections 4.3, 4.4, 5.2; D4 4.6. |
| M7 | Uniform authorisation model (policy decision point) | Scoped checks inlined per view; ownership not honoured everywhere; self-grant loophole via My Books; staff vs superuser vs capability drift. | D4 4.2, 4.3, D4-I1; D5 section 4. |
| M8 | Notification on completion and failure | Requesters and operator had no push when a book became ready or a job failed (only batched toast for operator). | D5-F38; D3-F70. |
| M9 | Source-credential lifecycle (CAP-04) | Expiry manifested as user-visible scrape failures; manual cookie harvesting. | D7 3.4; D3-F53. |
| M10 | Data lifecycle and retention policy | No cleanup for submissions, attempts, logs, jobs, catalog entries, engine keys; reader opening records permanent; manual reading logs only in browser. | D2 section 5 retention; D4 4.4; D5-F21. |
| M11 | Idempotent, transactional publish with outbox | Persistence not in one transaction; UI notifications lost between commit and hook; duplicate execution across engine and Celery. | D1 7.6; D3 7.8; D2 7.5. |
| M12 | Rate limiting and abuse protection across all auth and send endpoints | Several endpoints unthrottled (demo-login, reset validate/confirm, 2FA confirm, resend, Kindle send). | D4 4.10. |
| M13 | Per-user session management | No "log out everywhere", no session list; revocation did not kill tokens. | D4 5 sessions; D6 4.3. |
| M14 | Release and rollback process (CI, registry, tagged images, gated migrations) | Builds on the production host, full teardown on every deploy, no CI. | D7 3.1. |
| M15 | Internationalisation and brand configuration | English-only emails, hard-coded brand, Bengali-only heuristics. | D7 section 6. |
| M16 | Search index (beyond icontains) with Bengali normalisation | Legacy fuzzy matching via regex and normalised columns; no in-book search. | D4 4.11; D6-F15. |
| M17 | Contract-first API with generated TypeScript types and versioning | Legacy response shapes drifted (array vs paged, two facet shapes). | D5 section 6; D4 4.11. |
| M18 | Reader-content safety review of third-party scripts in EPUBs | Book content is untrusted input; sandbox/CSP not present. | D6 5.2. |

---

## Draft cohesion groups (no services named)

Clustering rationale: capabilities that share the same data, are written together, and change for the same reasons (and that would be damaged by being split) are grouped. The "seam" column says where a boundary is cheap or expensive. These are candidate groupings to be decided later, not final.

| Group | Capabilities | Data ownership (core entities) | Change rate | Load / runtime character | Sensitivity | Coupling to rest | Notes |
|---|---|---|---|---|---|---|---|
| G1 Source intelligence | CAP-01, CAP-03, CAP-04 | source catalog entry, catalog record, fetch log, page cache, source cookie | HIGH (tracks source site) | LR, IO-heavy, polite pacing; cookie custody is a tiny high-sensitivity piece | High for cookie, outbound SSRF | Async only; hands snapshots down | Changes are driven by one external site; isolating them contains breakage. Cookie custody may separate for secret handling. |
| G2 Content curation and build | CAP-05, CAP-07 (and read-only fixtures) | curated document versions, normalisation rule tables, generated assets | HIGH for rules (CAP-05), MEDIUM (CAP-07) | CPU- and memory-heavy per book, bursty on bulk reprocess | Low technically (third-party content) | Input snapshot (G1), output assets (G4) | Both derive deliverables from the same curated document and share Bengali structure knowledge; legacy derived sections twice, so keep section derivation in one place. |
| G3 Pipeline control | CAP-02, CAP-06, CAP-09, CAP-10 (derived read model) | request, title-resolution attempt, candidate, duplicate review, edition group, job, log, run, automation settings, worker registry | MEDIUM | Control plane S; bursty on automations; SSE fan-out | Medium (operator-only) | Orchestrates G1, G2, G4; events out to G7 | Legacy had two implementations of this whole group (D7 4.5); the rebuild must have exactly ONE request/job/state-machine owner. The operator console read model is derived and can be rebuilt. |
| G4 Library of record | CAP-08, CAP-11, CAP-15, CAP-18 | book, lifecycle and review state, asset registry, book source, contributors/series/categories, slugs/codes, metadata versions/reviews, manual books | MEDIUM (L for core model) | S, write-light read-heavy; transactional integrity matters | Medium (visibility rule) | Writer for G5/G6; read by everyone | The single place that decides what exists and what state it is in; the contract between the producing half (G1-G3) and the serving half (G5-G7). |
| G5 Discovery | CAP-16, CAP-17 | read model/search index over G4, shelf, saved filters, per-user flags | MEDIUM | Read-heavy, latency-sensitive, cacheable; export is bursty/CPU | Medium (visibility) | Reads G4 (async) and G8 (sync) | Derived from G4; can lag slightly. Personal lists are low-sensitivity user data attached to identity. |
| G6 Reading experience | CAP-19, CAP-20, CAP-21, CAP-22 | reading session/token, reading package (if hybrid), reading position, bookmarks, highlights/notes, kindle addresses and send log | MEDIUM (reader UX), anchor scheme tied to Q-R1 decision | S per reader, bursty launches, IO-heavy files; Kindle delivery is async/bursty | HIGH (copyrighted content delivery, private notes, personal addresses) | Sync on G8 (who may), sync on G4 (what), async from G2 (package) | Closest to the owner requirement that "the EPUB reader is its own service". Annotations and progress share anchors with the reader content and belong with it; Kindle send shares the file-delivery gate but is async work. |
| G7 Identity and entitlements | CAP-12, CAP-13, CAP-14 | user, credentials, TOTP, sessions, grants, read-once ledger | LOW (security core), MEDIUM (scopes) | Read-hot, tiny, latency-critical; hashing is CPU-bound | HIGHEST | Synchronously needed by almost every request path | Strongest data-ownership and sensitivity case for isolation; availability of this group gates the whole product. Admin UI for users sits with it. |
| G8 Communication | CAP-23 | email templates, delivery log, notification preferences | MEDIUM (copy) | Bursty IO, retry-heavy | Medium (links are credentials) | Async consumer of events from G3, G4, G6, G7 | Natural queue-driven consumer; Kindle SMTP transport can share it. |
| G9 Platform and operations | CAP-24, CAP-25, CAP-26, CAP-27 | audit events, backup artifacts, telemetry, config/secrets, release process | LOW | Append-heavy / scheduled / infra | HIGH (audit integrity, secrets, dumps) | Consumes events from everyone; no one depends on it synchronously | The four missing-in-legacy capabilities; audit is the one with a real data-ownership boundary, the others are platform concerns that exist per deployment, not per feature. |
| G10 Client | CAP-28 | none of record; client preferences | HIGH | Static, cacheable | Low | Calls every public API | Owns the permission-driven navigation and the M3 design system; not a service in the backend sense but an independently released deliverable. |

Observations to carry into the boundary design:
1. Two groups carry the legacy "two-pipelines" damage: G3 and the G1/G2 pair (duplicate crawlers, duplicate request models, duplicate lifecycle). The rebuild must collapse each into exactly one owner.
2. The boundary between G4 and G5 is a read-model seam (cheap, async); the boundary between G4 and G6 is a sync permission-and-state check (cheap if reads are cached).
3. The boundary between G1/G2/G3 (producing half) and G4..G6 (serving half) is async; the producing half can be stopped without any user-visible effect except new imports.
4. G7 and G9 (audit) are the groups where data ownership and sensitivity argue for isolation even though their load is small; G1 and G2 are the groups where change rate and resource profile argue for isolation.
5. CAP-19 is the group member whose internals depend on the unanswered owner question Q-R1; CAP-21's anchor scheme and CAP-07's package output inherit that decision.
6. Candidates to merge or drop rather than rebuild: demo login (D4-F3), "My Books as entitlement", client-side `localStorage` physical reading log (move to server or drop), per-minute DB-polling schedulers (compute next run instead), UI projection tables (derive), triggers (derive state in one place).

Not read / not covered: digest Issues sections and Keep/Change/Drop sections, and the `features/` reports (by instruction). Scale numbers (library size, user count) are not stated in the digests except scattered hints (thousands of catalog records, 13 reference books, a 300-book regression set) and need an owner answer before sizing groups for load.
