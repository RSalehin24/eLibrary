Status: DRAFT

# X1 Cross-cutting issues register (legacy eLibrary)

Source: digests D1..D7 (Issues, Keep/Change/Drop and Open-questions sections). Treated as data. Verification flags are copied from the digests and never upgraded: V = VERIFIED (digest author read the code), U = UNVERIFIED (report/doc only); "V/U" = part verified. Evidence is file:line exactly as cited by the digest (paths are as the digest wrote them, often unqualified). No secret values are reproduced. Source IDs: D1-In, D2-In, D3-I-X (letters), D4-In (D4-In), D5-In, D6-In, D7-I-n.

Severity scale: critical / high / medium / low (D1/D2/D3/D5/D6 H/M/L mapped directly; D4 and D7 use their own critical).

Categories: security, data-integrity, correctness, reliability, operability, UX, accessibility, maintainability, test-gap. Within a category rows are sorted by severity.

## 1. Register

### 1.1 Security

| ID | Title | Sev | Sources | Ver | Evidence | Design lesson for the rebuild |
|---|---|---|---|---|---|---|
| X1-001 | Any authenticated user can POST `books/<slug>/my-books/` and become "owner", bypassing read-once, preview, download, cover, reader and Kindle gates (also reaches drafts/rejected books) | critical | D4-I1 (related D4-I12, D6-I10, D2-I31) | V | views/books.py:94-106; permissions.py:39-99 | Entitlement is derived only from an explicit grant record written by an authorised actor; a user-controlled shelf/bookmark must never imply access. |
| X1-002 | Unsafe configuration defaults: insecure SECRET_KEY fallback, DEBUG on unless production, eager tasks outside production, DRF default AllowAny, committed demo password default, placeholder admin password/email, postgres/postgres | critical | D2-I2, D7-I-2, D7-I-25 | V (D2-I2, D7-I-2); AllowAny per-view override U (D7-I-25) | settings.py:74, :108, :250, settings.py:~203; compose :4, :26 | Secrets are required inputs with no defaults, startup refuses on missing/weak values, and the default permission is deny. |
| X1-003 | Reader token is the sole credential for manifest/EPUB/HTML routes: unauthenticated, no re-check of user active/grant/read-once, in URL query (history/logs), 2 h and extended on each launch, not revoked when access is revoked, no throttle | high | D4-I3, D6-I2 | V (AllowAny, launch URL); revocation gap U | reader.py:80,124,166; reader.py:72-73; models.py | Content routes take a short-lived, audience-bound, revocable credential in a header/cookie (never URL) and re-check entitlement on each fetch. |
| X1-004 | Scraped HTML is stored/served unsanitised (Jinja2 autoescape off, `\| safe`, danda-split writes unescaped HTML, preview/HTML download from API origin with no CSP/nosniff, EPUB iframe unsandboxed, `qr_svg` via dangerouslySetInnerHTML, profile image upload without type/size validation incl. SVG) | high | D1-I5, D2-I24, D4-I4, D6-I3, D5-I7 | U | not cited with lines | Allow-list sanitise at ingestion and again at render; serve content from a separate sandboxed origin with CSP and nosniff; validate uploads by bytes. |
| X1-005 | Test backdoor in production: remote-page payload injection allowed when env var set OR pytest in sys.modules OR PYTEST_CURRENT_TEST; test seams change production control flow | high | D3-I-U, D3-I-AE, D2-I11 | V (D3-I-U); seams U | checkpoint_and_runtime_adapters.py:231-236 | Test-only behaviour is injected via dependency substitution in tests, never by environment sniffing in production code. |
| X1-006 | Anonymous submission endpoints (create/detail/status/confirm-candidate/action-links) protected only by UUID secrecy + 40/h throttle; action-links issues preview tokens/downloads to any UUID holder; guests see others' public submissions | high | D2-I3 | V (AllowAny lines) | AllowAny lines (file not named by digest) | Invite-only means every intake endpoint requires an authenticated identity and ownership check; no capability-by-UUID. |
| X1-007 | Demo login: GET with side effects, no credentials, ignores is_active and TOTP, shared account with committed default password | high | D4-I5 (D5-Q7, D7-Q9) | V | auth_and_password_views.py:160-184; settings.py:107-108 | No shared or credential-less login path; if a demo is required it is a separate, isolated, data-free deployment. |
| X1-008 | `is_staff` and `admin:full_control` are wildcards (staff also bypasses read-once; full_control grantable via API); three inconsistent client/server permission models; `/access` nav vs page mismatch; "Raw Provenance" staff card without check | high | D4-I6, D5-I3, D5-I4 | V (D4-I6 file, D5-I3); D5-I4 U | permissions.py:27-36; capabilities.js:6-11; navigation.js:107-112,129-135; AccessPage.jsx:54-60 | One server-side policy (explicit roles/scopes, no wildcard flags) published to the client as data, never re-implemented. |
| X1-009 | Catalog list/detail/exports/reference lists show every non-deleted book regardless of state/review_state to every logged-in user, with `primary_source` URL on rows | high | D4-I2 | V | shared.py:325-356 | Reader-facing queries are scoped to published state by construction; operator views are a separate surface. |
| X1-010 | Soft-deleted books remain downloadable/readable/Kindle-sendable and keep tokens (access views lack `deleted_at` filter; metadata edit/review views also include deleted) | high | D4-I7 | V (access); U (metadata) | access views (Book lookup by slug, file not named) | A tombstoned entity is invisible to every read path via one shared repository filter and revokes outstanding tokens. |
| X1-011 | `/media/` served unauthenticated by nginx from a host path (conflicts with `is_protected` assets); `chmod o+x` on parent dirs | high | D7-I-21 | U | note 15 sec 2.10 (no line) | All stored files are fetched only through an authenticated content service (no public static path). |
| X1-012 | Scraper POSTs LearnDash mark-complete for every lesson, mutating the logged-in third-party source account; browser impersonation to evade Cloudflare (ToS risk) | high | D1-I1 (D1 C2/D1/D6) | V | book_manifest.py:1416-1453 (calls :1426, :1453) | Acquisition is read-only against the source; any account-mutating step is explicit, off by default and audited. |
| X1-013 | Deploy/secret exposure: admin password printed to terminal; sudo/SSH passwords accepted in config; StrictHostKeyChecking=no mode; secrets copied to laptop during host move | high | D7-I-3, D7-I-12, D7-I-9 | V (I-3, I-9 defaults); I-12 lines U | remote_deploy_flow.sh:182-186; config.sh:201 | Secrets live in a secret store/injected env, are never printed or copied, and SSH host keys are always verified. |
| X1-014 | No route-level role guard in the SPA; every protected route is URL-reachable and relies on server 403 | high | D5-I2 | V | AppRoutes.jsx:37-72 | Route guards derive from the server-published capability set; the server remains authoritative. |
| X1-015 | Source-site credentials/cookie handling: third-party cookies on disk, manual single login cookie with no expiry handling, cookie on the CLI (`--cookie-header`), unclear how auth is supplied (cookie file vs email/password settings) | medium | D1 security summary, D1-I24, D3-I-Y, D7-I-20, D4-I29 (D1-Q10, D2-Q10) | U | login_source_session (no caller in R1 files) | Source credentials are a managed secret with rotation/expiry detection, never in files, argv or logs. |
| X1-016 | DNS-over-HTTPS fallback uses `verify=False` against 1.1.1.1; poisoned answers feed direct-IP fetches | medium | D2-I1 | V | resolution_support_network.py:130 | No TLS-verification bypass anywhere; drop DoH/direct-IP fallback or make it opt-in with verification. |
| X1-017 | Account-recovery/2FA weaknesses: reset request reveals existence (404, documented as intentional AU17), validate/confirm/resend unthrottled, no per-user OTP limit, reset confirm length-only, 2fa disable/setup need no re-auth, secret returned raw, reset/invite links built from Host header (poisoning), password generator modulo bias, no CSRF on login | medium | D4-I8, D4-I9, D4-I11, D4-I32, D5-I5, D5-I6, D5-I9 | U | none cited | Uniform responses, per-account and per-IP limits, re-authentication for 2FA changes, base URL from config only. |
| X1-018 | Single coarse `processing.manage` guards reads, SSE, bulk deletes and book deletion; `actor` accepted and ignored; bulk `ids` unbounded, no rate limit/idempotency keys | medium | D3-I-V, D3-I-W | U | none cited | Per-action scopes, actor recorded on every command, bounded and idempotent bulk APIs. |
| X1-019 | Search returns other users' submission input text as catalog hits unless `ownership=mine` | medium | D4-I15 | U | none cited | Search indexes are per-audience; user-private data is never in the shared index. |
| X1-020 | Read-once and content protection are incoherent: consumed by HTML download, staff never limited, never reset, relaunch blocked in live session; "read" streams the whole EPUB so `download:file` cannot protect content and offline copies bypass read-once | medium | D4-I10, D6-I4 | V partial (permissions.py:48-62); rest U; D6-I4 inference from VERIFIED routes | permissions.py:48-62 | Decide whether read-vs-download separation is a real requirement; if so serve chapters, not the file, with an explicit entitlement interface. |
| X1-021 | Cover download: operator-precedence bug, `srcset` None crash, extension guessed, host unrestricted (SSRF-ish), `cover_source_url` can hold a local filename | medium | D1-I11 | U | none cited | Fetch only from allow-listed hosts, validate image type by bytes, store checksum. |
| X1-022 | CSV formula injection and `\r` quoting unescaped in exports | low | D4-I25, D5-I8 | U | none cited | Export layer neutralises leading `= + - @` and quotes control characters. |
| X1-023 | Dangerous operator commands: `seed_e2e_data` hard-coded test password and no prod guard; `repair_source_site_metadata` destructive by default; `seed_superadmin` exits 0 on missing password | low | D4-I29 | U | none cited | Destructive tooling is guarded by environment checks and requires explicit confirmation flags. |

### 1.2 Data integrity

| ID | Title | Sev | Sources | Ver | Evidence | Design lesson for the rebuild |
|---|---|---|---|---|---|---|
| X1-024 | Empty incomplete-candidate list resolves every incomplete record to "Uncategorized"/CREATED (empty `incomplete_remote_urls` makes all records stale) | high | D3-I-B | V | sync_runner.py:11-16; incomplete_resolution.py:72-97; automation_advancement.py:189-203 | Destructive bulk transitions require a non-empty, positively identified input set; empty means no-op. |
| X1-025 | "Resolved" means "left the incomplete archive"; request+record marked CREATED with no Book, so `created` does not imply a readable book | high | D3-I-C | V (logic) | incomplete_resolution.py:3-53 | State names are tied to an invariant (CREATED implies a Book exists) enforced by a constraint. |
| X1-026 | Catalog re-sync overwrites `resolved_from_incomplete`, `category`, `linked_book`, `book_creation_state`; resolved incomplete books are un-resolved; any record with a request counts as "updated" every sync | high | D3-I-D | U | catalog_record_sync.py:27-46,81-94 | Source-owned and operator-owned fields live in separate columns/tables; sync writes only source-owned fields. |
| X1-027 | Destructive re-scrape overwrote published content (only accidental versioning saved it); migration 0019 destroys alternate sources | high | D7-I-15 | V | T13 script; migration 0019 per note 17 | Published content is immutable and versioned; reprocessing produces a new version and promotes it explicitly. |
| X1-028 | Persistence not atomic across Book/BookSource/relations/document rows; evidence-to-section link always None; row-by-row inserts; title never refreshed; soft-deleted book revived by title match; same-titled books share output folder and may merge | high | D1-I9, D1-I10, D2-I31 | U | none cited | One transaction per aggregate; match on normalised source URL first; title-only collisions go to a human; no implicit revival. |
| X1-029 | Silent data loss in scraping: HTML truncated mid-tag, nodes beyond max_nodes/depth dropped, `max_lesson_pages` doubles as topic cap, container-lesson text lost, tiny legacy limits (48 nodes / 2 lesson pages / 12000 chars) | high | D1-I7, D3-I-AF | U | none cited | Limits are explicit config recorded on the job; any omission becomes a validation error, never a silent drop. |
| X1-030 | Dual-write denormalised state: status in 5+ columns, `book_creation_state` mirrored by code AND Postgres triggers that silently override writes; UI projections and version counters stored in the system of record; three-way record split | high | D7-I-6, D7-I-7, D7-I-8, D3-I-AA, D3-I-AB | V via migrations (0004 triggers; 0003 not re-read); D3 U | migration 0004; note 17 | One authoritative state per aggregate; projections are rebuildable read models, not source data; no triggers carrying business rules. |
| X1-031 | Job status is not outcome: SUCCEEDED for unresolved/duplicate/needs-review; stale-exhausted `fail_processing_job` leaves reprocess book stuck PROCESSING (no book handling in function body) | medium | D2-I12 (U), D2-I15 (V) | V (I15) / U (I12) | fail_processing_job body, lines 12-40 (file not named) | Separate "executed" from "outcome"; every terminal path restores owning-entity state. |
| X1-032 | Asset handling not atomic: old file deleted before new saved, revoke(terminate) mid-write, `sync_assets` retry/restore overrides NEEDS_REVIEW; GET `missing_asset_response` mutates state (marks FAILED, queues reprocess) on transient storage error; manifest picks first EPUB asset regardless of status | medium | D2-I16, D2-I17, D4-I22, D6-I11 | V (D6-I11 line 84 no status filter); rest U | line 84 (reader manifest); D4 no line | Write-new-then-swap; GETs are side-effect free; only READY assets are selectable. |
| X1-033 | `_finalize_processing_request` on DELETED soft-deletes the book even when it was a pre-existing target being rebuilt | medium | D3-I-H | U | request_processing_persistence.py:243-247 | Requests never own deletion rights over books they did not create. |
| X1-034 | Schema looseness: enums are free text with `choices`, no CHECK; PermissionGrant has no uniqueness or target validity; grants not editable, duplicates and expired rows linger | medium | D7-I-14, D4-I19, D4-I18 | V via migrations; D4 U | migrations | Constraints (CHECK/UNIQUE/FK) in the schema for every invariant. |
| X1-035 | Full book HTML duplicated in Book, CuratedBookDocument JSON, CuratedSection and assets rows; slimming-by-key-deletion | medium | D7-I-13, D1 Drop D7 | V via migrations | migrations | One canonical stored representation; large bodies in object storage by content address. |
| X1-036 | Catalog codes unstable (change with category/author), max+1 table scan with race, 65535/4095 capacity, weak 4-bit check, scramble constants in source; algorithm copy-pasted x3; obfuscation not security | medium | D4-I16, D7-I-24 | U | R10 sec 4.1 | Use stable surrogate IDs; if labels are needed, issue them from a sequence and keep them immutable. |
| X1-037 | Metadata edit: no transition rules/locking, direct write of state/review_state, not transactional, two versions per edit, no revert, publisher in two places, PUT silently partial | medium | D4-I17 | U | none cited | Edits are commands through a state machine with optimistic concurrency and a single source for each field. |
| X1-038 | Duplicate-insert bugs return 500 instead of 400 (SavedFilter, Bookmark unique-together fields omitted from serializers); retry view `.get(pk)` 500s | medium | D4-I13, D6-I9, D2-I19 | V (submissions.py:274 for retry view); rest U | submissions.py:274 | Uniqueness conflicts map to typed 409/422 errors by contract, covered by tests. |
| X1-039 | `next_request_id` check-then-create race produces duplicate ids; ids derived strings | medium | D3-I-K | U | request_queue_runtime.py:3-9 | Surrogate keys from the database; human-readable ids derived, not authoritative. |
| X1-040 | Price 0 maps to "" on edit, turning a free book into "no price" | medium | D5-I17 | U | none cited | Distinguish zero from null in the contract; generated client types preserve it. |
| X1-041 | User deletion cascades annotations/progress/Kindle history with no export or retention rule | medium | D4-I23 (D4-Q15) | U | none cited | Define retention/erasure and export policy per data class up front. |
| X1-042 | Kindle history has no address/status/error, `kindle_emails` JSON unvalidated, one send record per (user, book); `ReadingSession.last_opened_at` auto_now conflates progress save with open and duplicates BookOpeningRecord | medium | D7-I-16, D7-I-17 | V via migrations | migrations | Delivery is an event log with address, status, error; open and progress are distinct facts. |
| X1-043 | Backfill command bug: offset paging over a shrinking filter skips rows; `bulk_update` of `updated_at`; `.only()` with `select_related`; cross-app import | medium | D3-I-Q | U | none cited | Data migrations are keyset-paged, idempotent and tested on a snapshot. |
| X1-044 | Crawler cache aliasing (shared children lists, mutated cached dicts); cache sets None on final failure even with cache=False; evidence rows duplicated for repeated images | low | D1-I8, D1-I21, D1-I22 | U | none cited | Treat cached/parsed structures as immutable values. |

### 1.3 Correctness

| ID | Title | Sev | Sources | Ver | Evidence | Design lesson for the rebuild |
|---|---|---|---|---|---|---|
| X1-045 | Live catalog automation never creates requests in the same run (begin_catalog_request_creation then immediate finalize); second run recovers; untested (tests use snapshot pages) | high | D3-I-A | V | sync_runner.py:194-199; sync_completion.py:27-114,180-190; automation_commands.py:187-193 | Sync phases are an explicit state machine with a test per transition against live-shaped input. |
| X1-046 | Bengali text handling defects: `extract_core_title` literals lack vowel signs/virama so matching never fires, `is_section_duplicate` dead; substring matching (login/chapter/vol/part/row/road) gives false positives; possible non-NFC literals; error strings as control flow | medium | D1-I2, D1-I12, D2-I23, D3-I-T | V (text.py:85-94 literals); rest U | text.py:85-94 | Normalise Unicode (NFC) at one entry point, token-boundary matching, versioned rule tables with gold-corpus tests, typed errors. |
| X1-047 | Completeness gates inconsistent: 1/3 gate in EPUB vs 5% (n>=10) in manifest, placeholders counted as fetched; redundant `> 0.95 or > 1/3` | medium | D1-I3 | V (epub_book.py); classification counting U | epub_book.py:276-294 | One configured threshold shared by classification and build. |
| X1-048 | Language/digit/label inconsistencies: Bengali digits on English titles, language detected differently across EPUB/manifest/HTML, hard-coded Bengali defaults for English books | medium | D1-I13, D1-I14, D1-I15 | U | none cited | Language is a stored, overridable field used by all renderers; label tables keyed by language. |
| X1-049 | Duplicate detection is O(N books) in Python with no source filter; near-duplicate rules written 4 times with different semantics; unused edition-aware classifier | medium | D2-I13 | U | none cited | One indexed, edition-aware duplicate service with explicit semantics. |
| X1-050 | Title resolver flaws: empty catalog title scores 0.78, a single close match never auto-resolves, unbounded synchronous refresh crawl in request path, up to 3 live fetches in-request | medium | D2-I22 | U | none cited | Resolution runs as a background job; scoring has defined thresholds and tests. |
| X1-051 | Scheduler flaws: check-then-create race, settings edit re-arms slot (second run same day), next date drift, manual runs unlocked, duplicate/needs_review retried every 6 h, model vs service defaults differ (daily/02:00 vs weekly/03:00), unvalidated interval/time (500) | medium | D2-I27, D2-I28, D3-I-P | U | none cited | Store `next_due`, lock the claim, validate schedule input, exclude non-retryable outcomes. |
| X1-052 | `new_edition` is functionally "new" plus an orphan BookGroup (depends on a submission the pipeline never creates; `target_book_group_id` never written) | medium | D3-I-F | U | request_action_dispatch.py:30-47 | Model edition grouping explicitly or leave it out. |
| X1-053 | No state guards: pause a CREATED request, resume a DELETED, delete anything; confirm-duplicate publishes before=after; metadata edits write state directly | medium | D3-I-I, D3-I-J, D4-I17 | U | none cited | Transition table enforced in one place. |
| X1-054 | Resume/checkpoint semantics: docs say restart page 1 and reconcile, code continues from saved page; paused-at-finalize checkpoint lacks `curatedResult` so resume re-scrapes; `source-metadata` checkpoint never read; Redis mirror write-only | medium | D3-I-G, D3-I-L, D3-Open15 | U | request_processing_persistence.py:248-257 | Pick one resume contract, persist step outputs, test it. |
| X1-055 | "Latest request" ordering by `updated_at` is perturbed by heartbeats/any touch; heartbeat keeps updating while the main thread hangs so hung work is never recovered | medium | D3-I-M, D2-I6 | U | processing_state_queries.py:133-153; request_processing_pipeline.py:14-17 | Order by monotonic sequence; heartbeat only from the work thread. |
| X1-056 | Reader: initial progress POST uses `window.location` (undefined local `location`) | medium | D6-I5 | V | book-initialization-methods.js:147 | Reader progress contract covered by integration tests. |
| X1-057 | Reader resume restores chapter only; pending debounced progress lost on close; `progress_percent` not range-validated; `last_location` max 255 (CFIs can exceed); location label is TOC index | medium | D6-I6, D6-I19 | U; field defs V | models.py:155-156 | Progress anchor scheme sized and validated by contract; flush on unload. |
| X1-058 | Owner without grants can launch reader but gets 403 on bookmark/highlight/session slug endpoints (no owner rule in `ensure_book_reader_access`) | medium | D4-I12, D6-I10 | V | views/shared.py:237-249 | One entitlement check used by every endpoint touching a book. |
| X1-059 | Role+name filters (author/translator/editor) use chained `.filter()` on multi-valued joins so role and name match different contributors | medium | D4-I14 | U | none cited | Contributor facets query a (role,name) pair on one row. |
| X1-060 | EPUB output: minimal metadata (no stable identifier/date/series/translator), random UUID per build, NCX+nav both added (contradicts spec), spec/code divergences (TOC not always present, back sections in TOC, named sections dropped) | medium | D1-I17, D1-I18 | U | none cited | Identifier derived from book id+version; audit enforces the chosen spec. |
| X1-061 | Admin user-management quirks: superusers editable by superusers, `global_scopes` omittable, keyword hack in user search, `sync_global_grants` leaves expired/duplicate grants, reference endpoint unpaginated | medium | D4-I18, D4-I19 | U | none cited | Explicit admin policy and tests. |
| X1-062 | Sepia theme choice overwritten by app-theme effect | low | D6-I8 | V | useReaderBoot.js:46-51; lines 103-109 | Reader theme state has one owner. |
| X1-063 | Slug changes on rename without redirects, slug fallback scans all books; pagination contract changes shape by `page`/`limit` with differing defaults (10 vs 60) | low | D4-I24, D4-I26, D5 Q5 | U | none cited | Stable ids in URLs; one pagination envelope. |
| X1-064 | Minor logic defects: bulk retry aborts batch on PermissionDenied, URL intake loses later entries, swallowed errors in `capture_source_page_metadata`, missing vs deleted conflation, duplicated section KeyError, `_ratio` oddities | low | D2-I20, D2-I21, D3-I-R, D3-I-S, D1-I23 | U | none cited | Per-item results in bulk commands; no blanket exception swallowing. |

### 1.4 Reliability

| ID | Title | Sev | Sources | Ver | Evidence | Design lesson for the rebuild |
|---|---|---|---|---|---|---|
| X1-065 | Two dispatch mechanisms (engine pub/sub and Celery) can run the same job; engine recovery re-queues jobs already in the broker; `task_postrun` marks workers idle and overwrites ProcessingJob.status (incl. user-cancelled); non-atomic find_idle/assign, no leader lock; QUEUED jobs with empty task_id redispatched mid-create | high | D2-I4, D2-I5, D2-I7(double), D2-I18 | U | none cited | One durable queue with leases and idempotent job keys; a single dispatcher. |
| X1-066 | Pub/sub is fire-and-forget: lost assigned/done/register leaves job stuck forever; no ack/lease | high | D2-I6 | U | none cited | At-least-once delivery with visibility timeout and idempotent completion. |
| X1-067 | Dispatch failure falls back to running the whole job synchronously in the request thread (may double-process; runner short-circuits SUCCEEDED/CANCELLED only); blocking `time.sleep` up to 120 s in workers/ticker; hours-long curation run inline | high | D2-I7, D2-I26, D3-I-N | V (fallback) / U (double) | none cited | Request handlers only enqueue; queue down returns 503/queued. |
| X1-068 | Catalog refresh unbounded and uncancellable: `refresh_catalog_parallel` has no max pages, swallows all exceptions, no pause/cancel check, loops forever when source down; "stop" does not stop the fetch; `refresh_max_pages` stored but not passed | high | D3-I-E, D3-I-AJ, D2-I26 | U | catalog_record_sync.py:240-264 | Long jobs have budgets, checkpoints and real cancellation. |
| X1-069 | Head-of-line blocking and stale workers: one job with no capable worker blocks queue, requeue loses order, stale workers never expire, 2 s rescan | medium | D2-I8 | U | none cited | Capability-aware queue with TTL-based worker registry. |
| X1-070 | Cancel is cooperative with few check points; `revoke(terminate=True)` can kill mid-write; pause/delete of PROCESSING request noticed only at 2 checkpoints | medium | D2-I16, D3-I-I | U | none cited | Cancel checks between all stages; side effects idempotent. |
| X1-071 | SSE design: one blocked worker thread and 1 s DB polling per connection, broadcast without per-user filtering, no heartbeat/backoff/replay/max duration, no outbox (crash loses notifications), integer versions without epoch, 7-ref client state machine | medium | D2-I29, D3-I-X, D3-I-AB, D5-I25 | U | none cited | Outbox + one shared fan-out with per-user filtering and replayable cursor. |
| X1-072 | Request reuse across users: a request can attach to another's, sync overwrites dependents' review state/error, retry permission uses dependent's submitter | medium | D2-I14 | U | none cited | Reuse is explicit and scoped; never silently cross-user. |
| X1-073 | Scrape cache deleted only on success (leaks JSONL), stale pages reused on retry, concurrency assumption (1) vs setting (5), no locking | medium | D3-I-O | U | none cited | Cache keyed by content/version with TTL and ownership. |
| X1-074 | Fragility to source markup/Cloudflare: 200 challenge pages recognised only by sentinel titles; non-200 reason not surfaced | medium | D1-I20 | U | none cited | Source adapter isolated behind fixtures; failure reasons surfaced to operator. |
| X1-075 | Kindle send is synchronous, loads whole EPUB in memory, no 50 MB cap, no throttle, API-key vs SMTP confusion | medium | D4-I20 | U | none cited | Delivery is an async job with size and rate limits and status. |
| X1-076 | Performance hot spots: N+1 (`has_epub_asset`, latest request per record), whole EPUB zip re-read per resource, whole HTML in memory per preview, unbounded exports and state lists, 6-join `q` search, in-memory slow paths | medium | D4-I27, D6-I12, D2-I30, D3-I-AC | U | none cited | Paginate everywhere; stream; indexed search. |
| X1-077 | Bulk operations are non-transactional (partial failure leaves mixes; grants N x M POSTs; `Promise.all` abandons selection) | medium | D3-I-W, D5-I14, D5-I11 | U | none cited | Bulk commands are server-side, per-item results, idempotent. |
| X1-078 | CSRF handling: extra GET /csrf/ before every mutation, 6 s health poll for session lifetime, forced page reload on recovery losing form state | medium | D5-I23, D5-I24 | V (D5-I23); D5-I24 U | csrf.js:10-19 | Token-based auth without per-mutation round trip. |
| X1-079 | Background chatter: per-minute beat polling of DB (5 tasks), 5 s heartbeat through broker, Redis down costs up to 0.5 s per save, shared Redis DB 0 | low | D7-I-22, D3-I-AG, D2-I35 | V (celery.py:26-55); rest U | celery.py:26-55 | Event-driven scheduling; separate stores per concern. |

### 1.5 Operability

| ID | Title | Sev | Sources | Ver | Evidence | Design lesson for the rebuild |
|---|---|---|---|---|---|---|
| X1-080 | No backup, restore or restore drill for Postgres or file storage; single VM | critical | D7-I-1 | V | grep of deploy/ and local-production/ finds no backup/pg_dump | Backup, offsite copy and a scripted restore drill are release gates. |
| X1-081 | Deploy = `down` then `up --build` on the prod host: downtime each release, no rollback; local uncommitted files overlaid onto the branch | high | D7-I-4 | V (down/up); overlay U | environment_and_domain_checks.sh:290-291 | Immutable artifacts, rolling/blue-green deploy, tested rollback. |
| X1-082 | Documented resource limits and Redis maxmemory not applied; processing OOM risk on a small host (2-4 GB per large scrape) | high | D7-I-5 | V | no deploy:/mem_limit/maxmemory in compose | Limits declared and tested; heavy work isolated in its own worker. |
| X1-083 | Host move: full downtime, 15 min drain, whole-cluster dump, staging kept by default; source stack restarted after move (two live copies, duplicate schedules/email); `--dry-run` marks phases done | high | D7-I-9, D7-I-10, D7-I-11 | V (I-9, I-10 defaults); I-11 U | config.sh:201; edge_verify_and_entrypoint.sh:69; config:198 | Migration is a restore from backup into a clean stack, rehearsed. |
| X1-084 | Audit coverage: `AuditLog` model never written; only 3 verbs elsewhere; no actor on cancel/delete/retry/reprocess/duplicate-resolve/stale recovery; no audit of grants, logins, downloads, Kindle sends, TOTP, user deletion, reader opens | medium | D4-I21, D2-I25, D3-I-V, D6-I18 | V (D2-I25 R03 lists writes); D4 U | none cited | Append-only audit event on every state change with actor, from day one. |
| X1-085 | Observability: health check is the CSRF endpoint, unstructured logs (print in builders), no metrics, no job correlation | medium | D7-I-23, D1-I19 | V (D7); D1 U | settings.py:280; compose | Real health/readiness, structured logs with correlation ids, basic metrics. |
| X1-086 | Docs contradict code (limits, services, workers, migration phases, auth flow allow-list, stale processing docs, unknown `/multipage-toc` `/reprocessing` pages, TOTP issuer names) | medium | D7-I-19, D3-I-AK, D3-I-AN, D4-I30, D5-I21 | V (limits, engine, middleware.py:5-16); rest per notes | middleware.py:5-16 | Docs generated from or checked against code/contracts. |
| X1-087 | `engine` container undocumented; migration restore never starts it | medium | D7-I-18 | V (compose); restore omission U | compose :199 | Every runtime component is declared in one topology doc and compose file. |
| X1-088 | No retention/TTL: logs, attempts, stale engine entries, expired preview sessions, scrape caches, deleted requests kept forever; hard-delete cascade implicit | medium | D2 Change (lifecycle), D2-I8, D2-I32, D3-Open14 | U | none cited | Per-table retention policy implemented as jobs. |
| X1-089 | Repo hygiene: debug scripts with real third-party titles/URLs, hard-coded brand/host/repo names | low | D7-I-26 | V (notes) | none cited | Keep third-party content and hosts out of the repo. |

### 1.6 UX

| ID | Title | Sev | Sources | Ver | Evidence | Design lesson for the rebuild |
|---|---|---|---|---|---|---|
| X1-090 | Any 401/403 triggers "application has restarted, log in again" and clears the client session, so a legitimate permission-denied logs the user out | high | D5-I1 | V | src/api/runtime.js:115-127; SessionRestartHandler.jsx:12-23 | Distinguish unauthenticated (401) from forbidden (403) in the client error model. |
| X1-091 | Dark-mode bug: `index.html` hard-codes `data-theme="dark"`, "system" removes it so component overrides and tokens disagree; dark flash for light users | high | D6-I1 | V (attribute handling); visual result U | index.html:2; hooks/useTheme.js:10-11,19-21 | Theme tokens are the single mechanism (data-theme or media, not both); set pre-paint. |
| X1-092 | Broken deep links: `/books/{slug}/read` used in NotesPage and BookReaderSections but no route exists, `*` redirects to `/` | high | D5-I10 | V (NotesPage); R11 four places U | NotesPage.jsx:617; AppRoutes.jsx:127 | Typed route table shared by navigation and links; link tests. |
| X1-093 | Reader failures silent: manifest fetch, 401/403, missing EPUB, render error leave blank page; saves use `window.alert`; 2 h token expiry has no refresh | medium | D6-I7 | U | none cited | Every async path has loading, error and retry states. |
| X1-094 | Reader fragility: bookmark button dies after re-boot, listener leaks, text-based dedup mis-merges, quote decoration mutates book DOM, `endsWith` href matching | medium | D6-I13 | U | none cited | Annotations anchored by stable range anchors, not by DOM text. |
| X1-095 | Heavy reader theme enforcement (`!important` on every element, mutation observer, timed repaint) overrides publisher styling and costs CPU | medium | D6-I16 | U | none cited | Theme via CSS variables on a sanitised content container. |
| X1-096 | Destructive actions without confirmation (delete also deletes linked book, reprocessing stop/delete, bulk deletes) and failed actions give no feedback (unhandled rejection; regenerate clears selection on failure) | medium | D5-I13, D5-I11, D5-I12 | U | none cited | Confirm destructive actions; uniform command-result handling. |
| X1-097 | Physical-book reading log kept only in localStorage (lost across devices) | medium | D5-I16 | U | none cited | User data is server-side. |
| X1-098 | ManualBooksPage "Done" silently creates a book from a half-filled form; blur hack; filters not in URL | medium | D5-I22 | U | none cited | Explicit save/submit semantics; URL-addressable filters. |
| X1-099 | CSS debt: tokens duplicated 4x, 1806-line dark sheet, undefined tokens, ~35 `!important`, red/green overload, glass blur, ten breakpoints | medium | D6-I17 | U | none cited | One token set and a small breakpoint scale in the Material 3 theme. |
| X1-100 | Processing UI gaps: selection not locked during actions, locks released early, no origin filter on On Hold, optimistic stop shows stopped while fetching continues, notification/sound requirements without backend | medium | D3-I-AJ, D3-I-AK | U | audit 08 section 5 | UI state follows server-confirmed state only. |
| X1-101 | Minor UI defects: "Search categorys", tab counts/filters lost, `apiFetch` drops falsy bodies, emoji icons, native confirm mixed with dialogs, `humanizeError` unused, keystroke requests without debounce, absolute server URLs rewritten by client, wrong time zone handling (Asia/Dhaka hard-coded), English UI strings in service layer | low | D5-I15,I18,I19,I20,I26,I30,I31,I32, D3-I-AI | U | none cited | Shared UI primitives and i18n/time-zone policy from the start. |
| X1-102 | Exports: image-only PDF (not searchable/accessible), Excel sheet names not de-duplicated, hand-written zip, `slugifyFilename` collapses Bengali names, `localeCompare` without locale, PDF fonts depend on host files (Bengali tofu), no row cap | low | D5-I29, D4-I25 | U | none cited | Server-side exports with embedded Bengali fonts and locale-aware sort. |

### 1.7 Accessibility

| ID | Title | Sev | Sources | Ver | Evidence | Design lesson for the rebuild |
|---|---|---|---|---|---|---|
| X1-103 | Reader accessibility: annotations unreachable by keyboard, note modal lacks dialog semantics, Ctrl/Cmd +/- hijacks zoom, `user-scalable=no` after fullscreen exit, Esc does not leave immersive, emoji labels, sub-44 px targets, low muted contrast, `outline:none`, conflicting reduced-motion rules, uppercase+tracking labels harmful to Bengali | medium | D6-I14, D6-I17 | U | none cited | WCAG checks (keyboard, focus, contrast, target size, reduced motion) in CI; Bengali typography rules. |
| X1-104 | App accessibility: TagInput lacks listbox semantics; sound alert has no visual-only alternative; ScrollToTop on three routes only | low | D5-I33 | U | none cited | Use Angular Material/CDK accessible primitives. |

### 1.8 Maintainability

| ID | Title | Sev | Sources | Ver | Evidence | Design lesson for the rebuild |
|---|---|---|---|---|---|---|
| X1-105 | `exec()`-composed modules (scraper.py, submissions facades, services.py/views.py of processing, accounts/views.py, seed command): no imports, unlintable, hidden name collisions, circular dependencies | high | D1-I6, D2-I10, D3-I-Z, D4-I28 | V (submissions.py:16); rest U | submissions.py:16 | Real modules with explicit dependencies; each service owns its crate boundary. |
| X1-106 | Two parallel orchestration layers and ingestion models (ProcessingJob/submission path vs processing request vs CuratedBookDocument CLI path): duplicate catalog sync, stale recovery, job/retry notions, scrape limits; circular app coupling; legacy job-family concepts in docs | high | D2-I33, D3-I-AL, D3-I-AM, D7-I-6 | U (D2/D3); D7 V via migrations | none cited | One pipeline, one orchestrator, one job model; shared tables owned by exactly one service. |
| X1-107 | Pervasive duplication: front/back derivation in manifest/EPUB/HTML, boundary mining run twice, near-duplicate rules x4, reader tree copied twice (1.3 MB each), 52-line import header x8, Home/MyBooks/Kindle pages, Category/Series/Writer pages (95%), contributor normalisation x4, three generations of progress JSON, duplicated heartbeat/recovery paths, table builders twice | medium | D1-I16, D2-I13, D3-I-AD, D5-I28, D6-I15 | V (duplicate trees `du`); rest U | du of reader trees | Derive once at ingestion and store canonical; shared components and libraries. |
| X1-108 | Dead and unused code: unreachable warnings, unused functions/templates/constants, `api.py`, `reassign_job`, legacy persist paths, dead React pages/helpers, unused serializers | low | D1-I22, D2-I9, D2-I34, D3-I-AF, D3-I-AH, D5-I27 | U | none cited | Do not port; delete during rebuild and keep coverage honest. |
| X1-109 | Import-time evaluation: `_LD_AJAX_URL` and `INCOMPLETE_CATALOG_URL` computed from settings at import (empty host gives `https:///...`) | low | D1-I4, D3-I-S | V (D1-I4) | book_manifest.py:1185 | Read configuration at call time through a typed config object. |

### 1.9 Test gaps

| ID | Title | Sev | Sources | Ver | Evidence | Design lesson for the rebuild |
|---|---|---|---|---|---|---|
| X1-110 | Frontend unit tests mostly test inlined copies of code, five are source-grep tests: no regression protection | high | D5-I34 | U | E204, E151, U1-U2 | Tests import the real units; no grep-based assertions. |
| X1-111 | Untested flows: Kindle send, annotations, reader progress/bookmarks, restricted-route access for non-admin, scope effects, metadata edit/review, TOTP login step, reset-then-login, session expiry, manual book edit/delete, saved filters, export content, Bangla UI; live catalog sync path (only snapshot tests) | medium | D5-I35, D3-I-A | U | none cited | Each acceptance criterion maps to an automated test. |
| X1-112 | E2E suite flaky by design (fixed sleeps, shared mutable live state, login retried 3x, pixel assertions, mock contracts drifted) | medium | D5-I36 | U | E200-E202 | Hermetic E2E with generated contracts and no sleeps. |
| X1-113 | Fixture/doc mismatch: test CT14 says any logged-in user can create manual books, code requires physical_books:view; gold corpus/300-book harness not available in repo | low | D4-I31, D1-Q12 | V (D4-I31) | views/books.py:79 | Tests are the executable spec; gold corpus held outside git with a documented location. |

## 2. Top 25 issues that most influence service boundaries and architecture

| Rank | Register ID(s) | Boundary / architecture implication |
|---|---|---|
| 1 | X1-106 | One ingestion pipeline and one orchestrator; processing and ingestion must not both own catalog sync, stale recovery or scrape limits. |
| 2 | X1-065, X1-066, X1-067 | A single durable queue with leases/idempotent keys, owned by the ingestion service; request handlers only enqueue. |
| 3 | X1-030 | Each service owns its authoritative state; no triggers or dual-written mirrors; UI projections are rebuildable read models (notify/gateway side). |
| 4 | X1-001, X1-058, X1-008 | Access service is the single entitlement authority (explicit grants, no ownership-by-shelf, no wildcard flags); all services call it, none re-implement it. |
| 5 | X1-003 | Content/reader routes need a revocable, audience-bound credential issued by access and verified by content; not a URL token. |
| 6 | X1-004 | Content service stores only sanitised content and serves it from a separate sandboxed origin. |
| 7 | X1-011, X1-080 | All files behind an authenticated content service with a defined storage backend and backup/restore as a platform duty. |
| 8 | X1-020 | Decision on read vs download decides whether the reader streams chapters (content service API) or the whole EPUB. |
| 9 | X1-027, X1-035 | Immutable versioned book content with one canonical representation; reprocessing produces versions (content/catalog boundary). |
| 10 | X1-028 | Transactional aggregates per service; no cross-service multi-row writes that can half-persist. |
| 11 | X1-009, X1-010 | Catalog exposes a published-only reader view separate from the operator view; tombstones honoured by every consumer. |
| 12 | X1-006 | Invite-only means no anonymous intake or UUID-capability endpoints; submissions are owned by authenticated users. |
| 13 | X1-012, X1-074, X1-015 | Source acquisition is a read-only adapter behind a fixture-tested interface with managed credentials. |
| 14 | X1-024, X1-025, X1-026 | Catalog sync: source-owned vs operator-owned fields split; CREATED implies a Book; empty input is a no-op. |
| 15 | X1-068 | Long-running jobs need budgets, checkpoints and true cancellation inside the queue contract. |
| 16 | X1-071 | Notify service with an outbox, shared fan-out and per-user filtering instead of per-connection polling. |
| 17 | X1-072 | Request reuse/dedup rules decide whether submissions are per-user or shared aggregates. |
| 18 | X1-084 | Cross-cutting append-only audit event stream with actor on every command. |
| 19 | X1-031 | Job execution status and domain outcome are separate fields in the ingestion contract. |
| 20 | X1-036 | Stable surrogate ids across services; catalog codes only as immutable labels. |
| 21 | X1-042, X1-075 | Kindle/email delivery becomes an async notify job with its own event log, size and rate limits. |
| 22 | X1-105 | Real module/crate boundaries; no runtime code stitching. |
| 23 | X1-083, X1-081 | Deployment and migration are restore-from-backup into a clean stack with rolling deploy; shapes the infra boundary. |
| 24 | X1-002, X1-013 | Platform secrets service/injection with no defaults and startup validation per service. |
| 25 | X1-018, X1-051 | Per-action operator scopes and a lock-protected, stored `next_due` scheduler inside ingestion. |

## 3. Conflicts between digests (same fact stated differently)

1. DRF default `AllowAny`: D2-I2 lists it as VERIFIED (AllowAny lines); D7-I-25 marks it UNVERIFIED (settings.py:~203 from grep, per-view override not checked). Kept as unverified in X1-002.
2. Demo password location: D2-I2 cites settings.py:108; D4-I5 cites settings.py:107-108; D7-I-2 cites different defaults (admin changeme, postgres/postgres) in compose :4,:26 and settings.py:74. Probably consistent, line ranges differ slightly.
3. Source-site authentication mechanism: D1-Q10 says cookie-file harvest via `login_source_session`; D2-Q10 says SOURCE_SITE_EMAIL/PASSWORD plus auth-state file; D3-I-Y and D7-I-20 say a single manual login cookie. D1-I24 says `login_source_session` has no caller in R1 files.
4. Owner of catalog refresh: D2 attributes `TitleResolver.refresh_catalog` and ingestion's automation task; D3 documents `refresh_catalog_parallel` in processing and says both exist (I-AL). D2-Q4 asks what `refresh_catalog_parallel` does while D3 describes it.
5. Where the Postgres triggers live: D7-I-7 verifies them in migration 0004; D3 refers to "14h PR6" triggers; D3-Q10 asks whether they are a contract. Same mechanism, different citations.
6. Read vs download: D4 models `download:file` and read-once as separable gates; D6-I4 states read equals download in practice (whole EPUB streamed), so the gate cannot protect content.
7. Account enumeration on password reset: D4-I8 says documented as intentional (AU17); D5-I5 treats it as a defect (E34). D4-Q4 asks the owner.
8. Staff handling: D4-I6 says `is_staff` is a wildcard bypass; D5-I3 says `primaryNavigation` ignores staff for Kindle and `/access` requires superuser only; D4-Q7 says `is_staff` is an accidental wildcard with no UI to set it.
9. Auto-request eligibility: D3-I-D says code and UC-03 allow never-requested records only (and NOT_CREATED), while processing_pages.txt also includes records whose last request failed/deleted.
10. Resume semantics: D3-I-L says docs state restart at page 1 and reconcile while code and test PA9 continue from the saved page; D3-Q15 asks which is wanted.
11. Scrape concurrency/worker assumptions: D2 gives 5 workers x 1 job, 20 min stale window; D3-I-O says a code comment assumes concurrency 1 while the setting defaults to 5; D7-I-19 says docs contradict code on limits and workers.
12. Kindle addresses: D5-Q3 asks if `free.kindle.com` is valid; D4-Q11 says kindle.com subdomains are rejected today.
13. Manual-book creation permission: D4-I31 states tests say any user, code requires `physical_books:view` (D4-Q14).
14. Guest/preview sessions: D4 and D7-Q8 note anonymous previews allowed (null user); D6-Q7 says the model allowed null user but nothing created such sessions.
15. Ownership creation paths: D4-I1 says the My Books endpoint creates ownership; D2-I31 says `BookSubmission.save()` also creates `UserBook` as a side effect; D4-Q17 lists the UserBook signal as unverified. Ownership may be created by two routes.
16. Pagination: D4-I26 (default limits 10 vs 60); D5-Q5 (contributor facet bare array vs `{entries,pagination}`; `resolved` vs `completed`). Different layers of the same inconsistency.
17. Duplicate detection / entity recognition ownership: D1-Q7 says they live outside D1 (spec sections 11, 12); D2-I13 covers the duplicate scan, so ownership of the rules is split across digests.
18. Tests: D5-I34 says unit tests copy code; D4-I31/CT14 treat a test fixture as the contract; D3 says tests use snapshot pages for the live path. No contradiction of fact, but different claims about which artefact is authoritative.

## 4. UNVERIFIED items severe enough for a parent code check

Hints are paths/identifiers as cited by the digests; search the legacy tree under `archive/`.

| Register ID | Sev | What to check | File / grep hint |
|---|---|---|---|
| X1-065, X1-066 | high | Double dispatch, `task_postrun` publishing `done` for any Celery task with a first arg, non-atomic find_idle/assign, lost pub/sub messages | ingestion engine modules (R14g engine contract); grep `task_postrun`, `find_idle`, `dispatch_job`, `job:reassigned` |
| X1-067 | high | Dispatch-exception fallback runs the whole job inline; runner short-circuits only SUCCEEDED/CANCELLED | `queue_submission`, the runner, `advance_pipeline_once`, `queue_processing_request` |
| X1-004 | high | Autoescape off / `\| safe` in EPUB/HTML templates; preview/HTML-download views; CSP/nosniff headers; profile image upload validation | ingestion/epub templates, `reader.py` HTML route, access views for download, security middleware settings, user profile serializer |
| X1-003 | high | Whether token routes re-check grant/active/read-once and whether revocation invalidates live tokens | `reader.py:80,124,166`, reader token model in `models.py` |
| X1-011 | high | nginx `/media/` location and `is_protected` assets; `chmod o+x` | `deploy/` and `local-production/` nginx conf, remote deploy scripts |
| X1-026 | high | Catalog re-sync overwrite of `resolved_from_incomplete`, `category`, `linked_book`, `book_creation_state` | `catalog_record_sync.py:27-46,81-94` |
| X1-028, X1-029 | high | Persist atomicity, title-match revival, truncation/limits behaviour | `persist_scraped_book` / `persist_*`, scraper HTML truncation, `DEFAULT_SCRAPE_LIMITS`, `max_nodes` |
| X1-068 | high | `refresh_catalog_parallel` page cap, exception swallowing, cancel behaviour | `catalog_record_sync.py:240-264`, `cancel_source_catalog_refresh` in ingestion/services/curation.py |
| X1-110 | high | Whether frontend tests import real code or copies | `src/**/*.test.*`, grep for source-reading tests (E204, E151) |
| X1-010 | high | Metadata edit/review views lack the `deleted_at` filter (access views verified) | catalog metadata views (D4 Q17 hint) |
| X1-014 | high | Route table (verified) plus whether BookReaderSections links exist at four places | `BookReaderSections` (R11), grep `/books/.*/read` |
| X1-072 | medium | Cross-user request attach and retry permission | submissions services (D1 global request reuse, `sync` of dependents) |
| X1-017 | medium | Unthrottled reset/validate/confirm; Host-built reset links; 2FA disable without re-auth | `auth_and_password_views.py`, `FRONTEND_BASE_URL` use |
| X1-033 | medium | DELETED finalize soft-deletes pre-existing book | `request_processing_persistence.py:243-247` |
| X1-032 | medium | `missing_asset_response` side effects on GET; asset swap order | access/reader views; `sync_assets` |
| X1-037, X1-038 | medium | Grant serializer validation (R09 #27), unique-together serializer omission | grant and Bookmark/SavedFilter serializers |
| X1-020 | medium | Where read-once is recorded in launch/download views | launch and download views (D4 Q17) |
| X1-001 | critical | Confirm UserBook creation signal in ingestion | `ingestion/models/submissions.py` (UserBook signal) |
| X1-002 | critical | Per-view permission overrides vs REST_FRAMEWORK default | `settings.py:~203` and view `permission_classes` |
| X1-052 | medium | `new_edition` flow dependence on submission | `request_action_dispatch.py:30-47` |
| X1-054, X1-055 | medium | Checkpoint contents; latest-request ordering | `request_processing_persistence.py:248-257`, `processing_state_queries.py:133-153` |
| X1-081, X1-083 | high | Local overlay of uncommitted files; dry-run phase marking | deploy scripts (`environment_and_domain_checks.sh`, migration scripts T8.4) |
| X1-013 | high | Sudo/SSH password support and StrictHostKeyChecking=no lines | host-move config and scripts |

## 5. Consolidated open questions (deduplicated)

Source tags in brackets.

Product scope and policy
1. Do anonymous/public submissions, guest preview tokens and the demo account exist in the rebuild, given the app is invite-only? If a demo stays, what may it do? [D2-1, D4-5, D5-7, D6-7, D7-8, D7-9]
2. Who may submit requests (any reader, operator only) and is cross-user request reuse acceptable? [D2-5]
3. How do invited users get access: explicit grants for each, or a default policy (e.g. read for all approved books)? Is My Books intended to imply ownership? [D4-1, D4-2]
4. May non-privileged readers ever see draft/needs_review/rejected books; one shared catalog view or two? [D4-3]
5. Keep intentional account enumeration on password reset? [D4-4]
6. Exact Read Once rule, who can reset it, whether HTML consumes it, and whether Read Once survives at all. [D4-6, D6-4, D7-8]
7. Is read-vs-download separation a real content-protection requirement (decides whether the full EPUB may reach the browser)? [D6-2]
8. Should `is_staff` exist as a role separate from superadmin (editor, metadata-only, processing-only)? Who is the single/multiple operator, and does `actor` matter? Are per-category/per-writer grants used? [D4-7, D4-9, D3-7, D5-8, D4-13]
9. Are profile images needed in a private library? [D4-16]
10. Kindle: allowed domains, size limit, daily limit, verified addresses, retry policy, send history visibility. [D4-11, D5-3, D7-10]
11. Is the HTML single-file book / HTML preview (named window, cross-tab lock) still required, or EPUB-only with an in-app preview route? [D1-2, D5-6, D6-8]
12. Notifications and sounds, 2- or 3-minute batching: in scope and where do they run? [D3-5, D5-11]
13. Bengali UI localisation; Bengali font hosting and numeral policy; time zone for display and automation. [D5-12, D6-10, D3-12, D5-9]
14. Are catalog codes used on labels or shown to users (stable, printable) or can they be dropped? [D4-8, D7-7]
15. Physical-book reading log: keep and move server-side? Saved filters: live feature? [D5-10, D5-4]
16. Client-side PDF/Excel export: keep, and who consumes it? [D5-13]
17. Category-based "unfinished" tagging convention: preserve? [D2-8]
18. Are Reprocessing and Multipage TOC separate concepts, or merged? `force_generate` as an escape hatch? Does a "reprocessing queue" exist? [D3-4, D5-8]
19. Is scheduled automation needed or manual only; catch-up of missed runs; weekly/monthly semantics? [D2-12, D3-12]
20. What should "resolved incomplete" mean; who writes `will_resolve_to_category` and `empty_chapters_count`? Should live catalog automation create requests in the same run and which eligibility rule? [D3-1, D3-2, D3-3]
21. Should DuplicateReview support merge and NEW_EDITION grouping (BookGroup)? What do readers see for NEEDS_REVIEW and DUPLICATE and who resolves them? [D2-6, D2-7]
22. Should completeness failures block publication; which failures block (INVALID) vs allow review? [D1-11]

Acquisition and legal
23. Does the owner permit the mark-complete side effect or any authenticated crawl; is there an agreement with the source site (ToS/robots)? Is Cloudflare handling an owner decision? [D1-1]
24. How is source-site auth supplied and rotated (cookie vs credentials); should expiry be detected proactively; may the operator UI accept a pasted cookie? [D1-10, D2-10, D3-9, D7-11]
25. Retention: raw source pages/snapshots (copyright), submissions, logs, attempts, scrape caches, assets of deleted books, annotations on user deletion (export first?). [D1-8, D2-9, D3-14, D4-15]
26. Which legacy crawler is authoritative for edge cases (inline-TOC, single-page books); logic in `services/normalization`, `texts_are_similar`, `normalize_text`, scrape limits not read by any digest. [D1-3, D2-3]
27. Must the TOC page exist in every book; should NCX be omitted (test on target readers); what is the exact dark-mode cover palette? [D1-4, D1-5, D1-6]
28. Which service owns duplicate detection and entity recognition? [D1-7]
29. Is the gold corpus / 300-book regression harness available outside the repo? [D1-12]
30. Intended semantics of the `bookmark` tab/locked pages (sequential progression vs paywall). [D1-9]

Architecture and platform
31. Which orchestrator owns scraping jobs: separate request model or folded into ingestion job model; how is SourceCatalogEntry shared? What is the "pipeline" handler / BookCreationRequest second job type? [D3-6, D2-4]
32. Queue technology: Redis needed or Postgres `SKIP LOCKED` with leases; "inline fallback when the queue is down" or 503; expected scale (catalog size, books/day, workers, bulk size 200+, 15-20 min items, source rate limits). [D7-1, D2-2, D2-11, D3-8]
33. Postgres layout: single DB with schema-per-service and per-service roles, or database-per-service in one cluster? Where do book files live (volume, S3-compatible), and must every download/read be authenticated? [D7-4, D7-2]
34. Are the Postgres triggers (14h PR6) a contract other services rely on, or an implementation detail to drop? Do test-only endpoints `sync/advance`, `pipeline/advance` exist in production routes; where does the beat schedule live? [D3-10, D3-11]
35. Should catalog sync be pausable mid-fetch (true cancellation); resume from checkpoint vs restart from page 1 and reconcile? [D3-13, D3-15]
36. Reader architecture: option A/B/C and epub.js dependency approval vs custom renderer; reader service database ownership; session lifetime (2 h, sliding, tied to user session), token transport (URL vs cookie/header); reader host contract; embedded library vs service. [D6-1, D6-9, D6-7, D4-10, D5-1]
37. Must legacy highlights, bookmarks, progress be migrated (CFI anchors will not map)? Will legacy data (users, shelves, books, catalog_code, slug, grants, TOTP devices) be imported or rebuilt? [D6-3, D7-12]
38. Reader feature scope for v1: in-book search, paginated mode, font controls, offline/PWA, annotation tags, shared/exported notes, 3 themes and auto theme follow. [D6-5, D6-6, D6-11]
39. Hosting target (VM size) to size the processing worker (2-4 GB per large scrape, ~400 MB child ceiling); backup target, RPO/RTO, key custody, frequency, retention. [D7-14, D7-3]
40. Where do DB-stored automation/singleton settings live; permission scope inventory (11 vs 12) and how grants target ids owned by catalog; `source_records:view` separate scope or folded into an editor role? [D7-5, D7-6, D4-13]
41. Authoritative manual-book creation permission (tests vs code); role of `PermissionDenied`/`CanManageProcessing` and scope names defined in apps.common. [D4-14, D2-13]
42. Unverified items the digests asked to check before design freeze: grant serializer validation, `sync_global_grants`, read-once recording, metadata deleted filter, UserBook signal, whether AuditLog was written by other apps, BackendStatusModal polling, `useBookDetailData` polling, `utils/exportSession` storage type, expired-token browser behaviour, epub.js resource loading, processing/0003 seed data vs access/0009 rename drift, `django_otp` tables, 16a two-column grid and responsive breakpoints (821-1024 px, 981 px). [D4-17, D4-12, D5-14, D5-15, D6-12, D7-13]

Coverage caveat: only the Issues, Keep/Change/Drop (as needed) and Open-questions sections of each digest were read; the other digest sections were not consulted, so facts present only elsewhere may be missing.

