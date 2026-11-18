Status: DRAFT

# D7 - Legacy operations, runtime topology and data model (synthesis)

Sources: feature notes 14a, 15, 17, 18 (read in full) plus spot verification in `/home/reyan/Documents/eLibrary/archive`. Markers: VERIFIED = I confirmed it in code (file:line, paths relative to `archive/`); UNVERIFIED = taken from the notes only. No `.env` file was opened; env files exist at `deploy/env/`, `local/env/`, `local-production/env/`, `migration/env/` (names only). Nothing was run. Note-IDs in brackets (S1, M20, T8.2...) point back to the feature notes.

## 1. Purpose and scope

Purpose: give the designers of the Rust/Compose rebuild a faithful picture of how the legacy Django system was run (topology, deploy, backup/restore, host move), what its database looked like at the last migration, what its scripts reveal about pain, and which parts to keep, change or drop.

In scope: Compose environments, Celery/Redis/Postgres usage, deploy/migration/log/test tooling, 58 Django migrations (6 apps: accounts, access, catalog, common, ingestion, processing), helper and diagnostic scripts, e-mail templates, config/secrets handling. Out of scope: scraper/EPUB internals, front-end, auth flows (owned by other reports). Model classes were not read; the schema is derived from migrations (final state) and so scope semantics are inferred.

Headline findings:
1. One VM, one Compose stack, shell-script ops over SSH; no backups, no CI, no log shipping, no monitoring.
2. The schema has 43 models, two parallel book pipelines (ingestion vs processing), a three-way record split of one book, and Postgres triggers + DB-stored UI projections compensating for derived-state drift.
3. Full book HTML lives in DB rows; secrets default to insecure values; bootstrap admin password is printed to the terminal.

## 2. Runtime topology

### 2.1 Containers (production `deploy/compose/docker-compose.yml`)
| Service | Image / command | Role | Notes |
|---|---|---|---|
| postgres | `postgres:16-alpine` | sole DB | named volume `postgres_data`; healthcheck `pg_isready` |
| redis | `redis:7-alpine`, `command: ["redis-server"]` | Celery broker + result backend + engine state + (UI SSE/checkpoint mirror) | named volume `redis_data`; bare server, no maxmemory (VERIFIED deploy/compose/docker-compose.yml:68-69) |
| backend-init | backend image, one-shot | `manage.py migrate` + `seed_superadmin`; others wait `service_completed_successfully` | |
| backend | gunicorn on 8000 | Django REST API (+ admin, static) | published `127.0.0.1:${BACKEND_PORT:-8000}:8000` (VERIFIED :121-122); healthcheck GET `/api/csrf/` (:129) |
| worker | `celery -A config worker --concurrency=${CELERY_WORKER_CONCURRENCY:-2} --queues=celery` | general tasks | VERIFIED :157 |
| processing-worker | same, `--queues=processing --hostname=processing@%h`, concurrency default 1 | scraping/EPUB heavy tasks | VERIFIED :182 |
| engine | `python manage.py run_engine` | "Central Job Engine": Redis-backed job coordinator that watches worker heartbeats (`--heartbeat-timeout 15`, `--check-interval 2`) and reclaims stale workers | VERIFIED :199-206 and apps/ingestion/management/commands/run_engine.py:1-60; undocumented in all docs (note 15 sec 5.2) |
| beat | `celery -A config beat` | schedule | |
| frontend | nginx 1.27-alpine serving Vite build | SPA; assets immutable 1y, index.html no-store, SPA fallback | published `127.0.0.1:${FRONTEND_PORT:-4173}:80` (:250-251) |

Networks: `public`, `internal` (`internal: true`). DNS 1.1.1.1/8.8.8.8 pinned on app containers (needed because source-site DNS resolution failed in some hosts; worker has a DNS check at deploy). App storage: bind mount `app/backend/storage` -> `/app/storage` (deploy/local) or named volume `local_prod_storage` (local-production). Restart policy `unless-stopped` (VERIFIED :46,68,107,153,178,203,224,249).

Edge: NOT in Compose. Host-level nginx (nginx.org apt package pinned, default 1.29.4) + certbot (webroot, systemd timer or cron every 12 h), Cloudflare in front for DNS. Routing: `/api/` and `/admin/` -> backend port; `/static/` and `/media/` served by nginx from host-visible storage dirs (`/media/` unauthenticated, 1 h cache); `/` -> frontend container. No HSTS, no OCSP stapling, no security headers (note 15 sec 2.10, UNVERIFIED in code). The brief's target stack (Caddy as edge container) removes the whole host-nginx/certbot/chmod-o+x scripting.

### 2.2 Celery / Redis / Postgres usage
- Two Celery queues: `celery` (default; email, catalog sync, Kindle - docs contradict each other about which tasks go where, note 15 sec 5.3) and `processing` (book scraping/EPUB generation).
- Reliability settings (VERIFIED app/backend/config/celery.py:20-24): `worker_max_tasks_per_child=50`, `worker_max_memory_per_child=400_000` KB (~400 MB), `prefetch_multiplier=1`, `task_acks_late=True` (redelivery on crash/redeploy). No task `time_limit` (UNVERIFIED beyond note 15).
- Beat schedule (VERIFIED celery.py:26-55): catalog-automation scheduler (every minute), processing runtime tick (60 s), processing automation scheduler (every minute), processing maintenance (every minute), recover stale jobs (every minute), worker heartbeat (every 5 s). Six periodic tasks, three of them per-minute DB polls "is it due?" rather than computed next-run times.
- Redis holds: broker queues, results, the engine's worker-heartbeat/job state, catalog-sync checkpoints mirrored from DB, SSE invalidation pushes. Migration toolkit copies a Redis RDB and asserts queue lengths zero first (T5, T8.5). Redis persistence is default.
- Postgres: single DB `bangla_library` (default), user `postgres`; `CONN_MAX_AGE=60`, `CONN_HEALTH_CHECKS=True` (VERIFIED settings.py:172-178). Default DATABASE_URL is `postgresql://postgres:postgres@postgres:5432/bangla_library` (VERIFIED settings.py:172-176). Superuser used by the app.
- Ingestion falls back to inline processing if Celery/Redis dispatch fails (note 15 sec 3) - a hidden second execution mode.
- Cookie auth: SessionAuthentication + CSRF; `django_otp` TOTP plugin (VERIFIED settings.py:129-130, so TOTP device tables are from `django_otp`, answering note 17's open point); `RequireTotpSetupMiddleware`.

### 2.3 Environments and how they differ
| Aspect | `local/` (dev) | `local-production/` | `deploy/` (prod) |
|---|---|---|---|
| Purpose | live-reload dev, `docker compose up --watch` | prod-like stack on the owner's machine | real server |
| Entry | `local/scripts/dev.sh`, `./run_local.sh` | `local-production/deploy.sh` | `deploy/scripts/deploy.sh` (SSH from laptop) |
| Services | + `engine`; no backend-init in docs | project `elibrary-local-prod`, DB `bangla_library_local_prod` | backend-init + all |
| Ports | 5173 (Vite) / 8000, bound to LAN IP (0.0.0.0) unless `LOCALHOST_ONLY=1` | 8001 / 8002 | 127.0.0.1 only, host nginx in front |
| Backend | `runserver --noreload` (docs wrongly say autoreload) | gunicorn | gunicorn |
| Celery | `--pool=solo --concurrency=1 --max-tasks-per-child=1` (to stop prefork SIGKILL) | processing concurrency 2 | worker 2, processing 1 |
| Storage | bind mount | named volume | bind mount |
| Healthcheck | `/api/health/` | `/api/csrf/` | `/api/csrf/` |
| Cookies | Secure=0 | Secure=0 | Secure on (derived from https public URLs, VERIFIED settings.py:233-234) |
| Extra | macOS-only helpers (`dockerctl`, Colima, `clear_docker.sh` that wipes ALL docker state, `caffeinate`) | wake-lock | host nginx/certbot/TLS |
The three Compose files are near-duplicates (copy-paste, divergent healthcheck, volumes, ports); no shared base/override.

### 2.4 Resource limits: documented but absent
Docs claim per-service memory/CPU limits and `REDIS_MAXMEMORY=256mb`. VERIFIED absent: grep of the three compose files for `deploy:`, `mem_limit`, `cpus`, `maxmemory` finds nothing; Redis is bare. Memory safety rests solely on Celery per-child recycling and the sizing guidance (processing child ~400 MB, large books 2-4 GB per scrape). Page cache of fetched pages at `<storage>/processing/scrape_cache/` lets an OOM-killed scrape resume.

## 3. Deploy, backup, restore, migration, operations

### 3.1 Deploy (`deploy/scripts/deploy.sh`, `deploy_steps/*.sh`) - manual, SSH-driven
What exists (8 phases, note 15 sec 2.2): preflight (DNS A record = `DEPLOY_IP`, SSH, sudo) -> remote git clone/fetch + `git reset --hard origin/<branch>` -> overlay local uncommitted workspace via tar stream (so deployed code can differ from any branch) -> env sync (push non-empty keys / preserve / prompt) -> install Docker (apt, optional pinned version) -> `compose down --remove-orphans` then `up -d --build --force-recreate` (VERIFIED deploy/scripts/deploy_steps/environment_and_domain_checks.sh:290-291: full teardown = downtime on every deploy) -> host nginx + certbot setup -> HTTPS probes (20 x 3 s). Images are built ON the production host from source; no registry, no tags, no rollback. First deploy prints super admin email AND password once (VERIFIED remote_deploy_flow.sh:182-186 calling `print_super_admin_credentials`, automation/lib/common.sh:85). Config-only changes: live `celery control pool_grow N` or full redeploy.
Manual: owner types secrets into env files; the optional 5 s "edit env now?" prompts; the owner must point DNS; copy `source_site_auth.json` (scp).
Missing: zero-downtime/rolling deploy, rollback, image registry, migrations as a separate gated step with backup first, CI, smoke tests post-deploy beyond two probes, staging environment (an ad hoc `.test.env` name exists).

### 3.2 Backup / restore - none
VERIFIED: grep for `pg_dump`/`backup` in `deploy/` and `local-production/` scripts and compose returned nothing; the only dump code is in `migration/`. No scheduled `pg_dump`, no volume snapshot, no offsite copy, no storage backup, no restore drill. Content recovery in practice was via the CuratedBookDocument version history (T13). Redis default persistence only.

### 3.3 Host-to-host migration toolkit (`migration/`, 15 files, ~2k lines of bash)
Phases preflight -> snapshot -> restore -> verify with `.phase-<name>.done` markers and `--resume`; configuration inherited from `.host.env`. Snapshot: freeze writes (stop beat, frontend, backend), drain Celery (inspect active/reserved/scheduled and Redis `LLEN` of both queues up to 900 s), stop workers, tar app + storage, `pg_dumpall --globals-only` + `pg_dump --clean --if-exists --create`, Redis SAVE+RDB, manifest with per-table counts, row-count hash, Redis stats, storage count/bytes, SHA-256 of each artefact. Restore: upload, verify checksums, `compose down --volumes`, restore SQL with `ON_ERROR_STOP`, replace RDB, extract storage, compare counts before start, run backend-init, start services. Verify: health, re-compare, optional nginx/certbot.
Good ideas to carry as requirements: drain-before-freeze; checksum manifest; row-count comparison before start; resumable phases; abort on mismatch; failure trap restarting the source.
Defects: see Issues I-9..I-12 (VERIFIED defaults: `KEEP_STAGING` defaults to 1 at configuration_and_arguments.sh:201; `KEEP_SOURCE_DOWN_ON_SUCCESS` defaults to 0 at :198 and `finalize_success` restarts the frozen source when it is 0, edge_verify_and_entrypoint.sh:69; so after a successful host move BOTH stacks run unless the operator intervenes). Downtime = whole freeze + dump + transfer + restore.

### 3.4 Other operations
- Logs: `logs/scripts/show-logs.sh` (local file tail; remote via SSH `docker compose logs -f`; frontend remote = host nginx logs). No rotation, no shipping.
- Source-site auth: manual Firefox cookie capture (`save-source-site-auth.sh/.py`, pip-installs `browser-cookie3`), writes Playwright-style storage JSON to `app/backend/storage/source_site_auth.json`, scp'd to server; expiry (~1 year) surfaces as a user-visible scrape failure. Login is never automated (Cloudflare). Manual, fragile, secret-bearing.
- Bulk data repair is done by running one-off Python inside the container (T12, T13).
- Env tooling: `generate-env.sh` only scaffolds templates; `env_tools.py` merge/scaffold/shell-export.

## 4. Complete data model as of the latest migration

Source: note 17 (all 58 migrations read there); trigger SQL VERIFIED in `app/backend/apps/processing/migrations/0004*.py`. Conventions: every table except those marked "bigint" has `id uuid` pk, `created_at`, `updated_at`. "FK c" = CASCADE, "FK sn" = SET NULL. Domain labels: ACC accounts, AX access, CAT catalog, ING ingestion, PRC processing, CMN common. Only constraint/index facts that the migrations state are listed; other indexes are Django FK defaults.

### 4.1 Tables
**accounts**
- `accounts_user` (bigint pk; ACC): AbstractUser columns (password, last_login, is_superuser, first_name, last_name, is_staff, is_active, date_joined, groups M2M, user_permissions M2M); `email` unique (login id); `full_name`; `totp_required` bool; `profile_image` file; `email_setup_pending` bool; `password_setup_nonce` int (single-use link invalidation); `kindle_emails` JSON list (no table, no verification state). TOTP devices live in `django_otp` tables (VERIFIED settings.py:129-130), not in these migrations.

**catalog**
- `catalog_book` (CAT): `deleted_at` (soft delete); title(255); slug unicode unique; summary; `state` draft|processing|needs_review|ready|published|archived|soft_deleted (indexed); `review_state` pending|needs_review|approved|rejected (indexed); `source_site`; `raw_scraped_metadata` JSON; `raw_scrape_payload` JSON; `main_content_html`, `book_info_html`, `dedication_html` text; `toc` JSON; `content_items` JSON; `cover_source_url`; `metadata_last_reviewed_at`; `normalized_title` (idx); `catalog_code` char10 unique null idx; `record_type` digital|manual (idx); manual fields (`manual_binding`, `manual_is_compilation`, `manual_price` dec(10,2), `manual_publisher`, `manual_language` default 'bn'); `edition`, `normalized_edition` (idx); `group` FK BookGroup sn; `empty_chapters_count`. M2M through BookCategory/BookContributor/BookSeries. No unique natural key on title (dropped in 0011).
- `catalog_category`, `catalog_contributor`, `catalog_series`: name (unique for category), slug unicode unique, `normalized_name` unique idx, `catalog_code` char10 unique null.
- `catalog_bookcategory`: book FK c, category FK c, raw_value; unique(book, category). `catalog_bookcontributor`: book, contributor FK c, `role` author|translator|compiler|editor|illustrator|cover_artist|publisher|other, raw_value, sort_order; unique(book, contributor, role). `catalog_bookseries`: book, series FK c, sort_order, raw_value; unique(book, series).
- `catalog_booksource`: book FK c; `source_url`; `normalized_source_url` unique; `source_type`; `source_title`; `is_primary` (vestigial); `raw_metadata`; unique_together(book) = exactly one source per book.
- `catalog_generatedasset`: book FK c; `asset_type` html|epub|cover; `status` pending|ready|failed; `file` (max 500); `storage_path`; `legacy_path`; `content_type`; `file_size`; `checksum`; `is_protected`; `source_job` FK ProcessingJob sn; unique(book, asset_type) - so exactly one current EPUB per book, no versions.
- `catalog_metadatareview` (book FK c, state, notes, requested_by, reviewer sn); `catalog_metadataversion` (book FK c, `snapshot` JSON, source, notes, created_by sn).
- `catalog_userbook` (user FK c, book FK c; unique(user, book)) = reader's personal shelf ("My Books"). `catalog_userbookkindlesend` (same shape, unique(user, book); only timestamps).
- `catalog_bookgroup` (canonical_title, normalized_canonical_title idx, note) groups editions of one work.
- `catalog_curatedbookdocument`: source_url idx, canonical_url, `version` int, `status` draft|validated|review_required|invalid (idx), structure_type, title, validation_summary JSON, source_snapshot JSON, `document` JSON (whole curated projection incl. sections/entities), book FK sn, source_job FK sn; unique(source_url, version). Children (all FK c to document): `catalog_curatedentity` (entity_type work|person|organization|series|category|asset|publication_event|metadata, role, value, normalized_value idx, source_url, source_location, evidence_text, confidence, payload); `catalog_curatedsection` (section_id, section_type cover|title_page|book_info|dedication|front_matter|generated_toc|body|back_matter, title, path JSON, html, confidence, sort_order, payload; unique(document, section_id)); `catalog_curatedevidence` (entity FK c null, section FK c null, value, extractor, confidence, payload...).

**access**
- `access_permissiongrant`: user FK c; `scope` char32 (12 values: submit:create, preview:html, read:durable, download:file, metadata:edit, physical_books:view, processing:manage, access:manage, source_records:view, admin:full_control, send:kindle, read:once); is_active; expires_at; notes; nullable targets `book` / `category` / `contributor` FK c; granted_by sn. No unique, no check tying scope to target. (Release note lists 11 scopes and omits `physical_books:view`; minor drift.)
- `access_previewaccesssession`: `token` unique (generated), `expires_at`, `launch_count`, book FK c, user FK c NULLABLE, source_submission FK sn.
- `access_readingsession`: last_location, progress_percent, `last_opened_at` auto_now, book/user FK c, preview_session sn; unique(user, book).
- `access_bookmark` (location, label, note, chapter_href, chapter_label, preview_text; unique(user, book, location)); `access_highlight` (cfi_range 1024, chapter_*, text, note, color yellow|green|blue|pink|underline, tags JSON, `kind` highlight|quote; indexes (user,-created_at), (user,book), (user,kind)); `access_bookopeningrecord` (user, book FK c; unique(user, book); read-once tracking marker, overlaps readingsession).

**ingestion**
- `ingestion_sourcecatalogentry`: source_url unique, title, author_line, normalized_title idx, normalized_display idx, raw_data JSON, last_seen_at - scraped index of the whole source site.
- `ingestion_booksubmission`: input_type url|title|csv; original_input; normalized_input; resolved_url; resolution_status (6); resolution_confidence; `status` draft|pending_resolution|queued|processing|needs_review|ready|failed|cancelled|duplicate|deleted (idx); review_state; raw_payload JSON; error_message; `origin` user|curation|automation (idx); FKs: submitter sn, linked_book sn, duplicate_of_book sn, canonical_submission self sn.
- `ingestion_processingjob`: job_type resolution|ingestion|reprocess (idx); status queued|processing|succeeded|failed|cancelled (idx); task_id; queue_name; retry_count; payload JSON; last_error; started_at; finished_at; cancel_requested; worker_hostname; submission FK c; book FK sn. `ingestion_processinglog`: job FK c, level, message, details JSON.
- `ingestion_titleresolutionattempt` (submission FK c, query, normalized_query, status, confidence, resolved_url, raw_results JSON, error); `ingestion_matchcandidate` (attempt FK c, rank, title, author, url, confidence, metadata, is_selected); `ingestion_duplicatereview` (submission FK c, existing_book FK c, detected_by, status pending|confirmed|dismissed|merged, notes, raw_evidence).
- Singletons: `ingestion_catalogautomationsettings` (singleton_key unique; enabled; daily_run_time; mode pending|all; refresh_max_pages 80; frequency 8 values; updated_by sn); `ingestion_catalogcurationrun` (trigger manual|scheduled, mode, status, refresh flags, task_id, queue_name, retry_count, summary JSON, last_error, timestamps, cancel_requested, requested_by sn); `ingestion_sourcecatalogrefreshstate` (singleton; status idle|queued|processing|succeeded|failed; counters; task_id; requested_by sn).

**processing** (second pipeline)
- `processing_bookrecord` (string pk): name, `url` unique, category (denormalised string), writer, translator, composer, publisher (strings); `book_creation_state` (9 values, idx, DERIVED + trigger-enforced); was_incomplete, resolved_from_incomplete, will_resolve_to_category, is_duplicate; duplicate_of_record self sn; linked_book FK sn; source_catalog_entry FK sn.
- `processing_bookcreationrequest` (string pk): `state` (8 values, idx); progress JSON; error_message; is_resumed; is_confirmed_not_duplicate; duplicate_confirmed; pipeline_outcome; book_record FK c; duplicate_of_record / duplicate_of_request self sn; linked_book sn; `origin`; `submission` OneToOne BookSubmission sn; force_generate; has_multi_page_toc (idx); source_toc_page_count; fetched_toc_page_count.
- `processing_processingautomationsettings` (bigint; kind catalog|incomplete unique; enabled; interval free text; time; saved; last_run_at; status_message). `processing_processingsyncstate` (bigint; singleton_key unique, keys `catalog`/`incomplete`; status idle|syncing|pausing|paused; progress JSON; remote_pages JSON; page_index; counters; message; task_id; queue_name; last_error).
- `processing_processinguidomainversion` (bigint; domain unique; version bigint) and `processing_processinguiprojection` (bigint; key unique; payload JSON) = DB-stored read-model cache + change counters for the admin UI.

**common**
- `common_auditlog`: actor FK sn, verb, target_type, target_id (string, no FK), request_id, remote_addr, user_agent, payload JSON (carries updated_at although append-only). `common_savedfilter`: owner FK c, target catalog|queue, name, params JSON; unique(owner, target, name).

Counts: ACC 1, CAT 19 (book, category, contributor, series, 3 through, booksource, generatedasset, metadatareview, metadataversion, userbook, kindlesend, bookgroup, curateddoc, entity, section, evidence), AX 6, ING 11, PRC 4, CMN 2 = 43 plus Django auth M2M and django_otp/session/etc.

### 4.2 Postgres triggers (VERIFIED, processing/migrations/0004*.py)
- Function `processing_sync_book_record_state(target_record_id text)` (:4-50) sets `processing_bookrecord.book_creation_state` to the state of the latest request (updated_at desc, created_at desc, id asc), else `created` if `linked_book` set, else clamps to allowed list; also sets `updated_at = NOW()` (:41-45).
- `processing_bookcreationrequest_sync_record_state_trigger` (:53-79): fires on request INSERT/UPDATE OF state,book_record_id,updated_at,created_at / DELETE and calls the sync function.
- `processing_bookrecord_enforce_creation_state_trigger` (:83-125): BEFORE INSERT/UPDATE OF book_creation_state,linked_book_id; overwrites the incoming value with the derived one, so application writes to that column are silently discarded.
- Reversible via DROP (:128-136). Postgres-only (plpgsql). These are the only triggers in the schema. Cause: denormalised state kept drifting. Rebuild: derive the state in a query/view or a single owner of the state machine; do not carry triggers.

### 4.3 Projection and read-model tables
- `processing_processinguiprojection` + `processing_processinguidomainversion`: materialised JSON card payloads (camelCase shapes of the Angular/JS UI hard-coded in migration 0003, 366 lines, 18 domains such as catalog-*, create-*, on-hold-*, incomplete-*) and per-domain monotonic versions for optimistic concurrency/ETag/SSE invalidation. A read-model cache inside the system of record.
- `catalog_curatedbookdocument.document` JSON + `catalog_curatedsection/entity/evidence`: a normalised and a JSON copy of the same curated projection (toc, content_items, main_content, dedication, front_sections, book_info).
- `catalog_book.main_content_html/book_info_html/dedication_html/toc/content_items`: a third copy of the content, and `GeneratedAsset` files a fourth (rendered HTML/EPUB).
- Denormalised strings: `normalized_*` columns (catalog), `BookRecord.category/writer/...` strings, `catalog_code` obfuscated codes.

### 4.4 The three-way record split
One book is represented by (1) `processing_bookrecord` (+ `BookCreationRequest`): the work-queue/catalog-listing identity keyed by source URL, with state; (2) `catalog_curatedbookdocument`: versioned parse result of the scrape; (3) `catalog_book`: the published library entity with assets and M2M metadata. Linking: BookRecord.linked_book -> Book; CuratedBookDocument.book -> Book (sn); BookCreationRequest.linked_book -> Book; no FK from record to curated document (joined by `source_url` string). Plus `ingestion_booksubmission` (4) and `ingestion_sourcecatalogentry` (5) in the other pipeline. Operators needed a script to trace one book across them (T23, which also contains a field-name bug: `b.source_urls.values_list('url', ...)` vs real field `source_url`). Lifecycle state is stored in at least five places: Book.state, Book.review_state, BookSubmission.status, BookCreationRequest.state, BookRecord.book_creation_state (+ ProcessingJob.status, CuratedBookDocument.status).

### 4.5 Two parallel book pipelines mapped onto tables
| Concern | Pipeline A: ingestion | Pipeline B: processing |
|---|---|---|
| Intake | `BookSubmission` (url/title/csv input, resolution) + `TitleResolutionAttempt` + `MatchCandidate` | `BookRecord` (rows from catalog sync of the source site) |
| Work unit | `ProcessingJob` (+ `ProcessingLog`) | `BookCreationRequest` (progress JSON, pause/resume) |
| Duplicates | `DuplicateReview`, `duplicate_of_book`, `canonical_submission` | `duplicate_of_record`, `duplicate_of_request`, `is_duplicate`, `duplicate_confirmed` |
| Automation | `CatalogAutomationSettings`, `CatalogCurationRun`, `SourceCatalogRefreshState` | `ProcessingAutomationSettings`, `ProcessingSyncState`, UI projection/version tables |
| Source index | `SourceCatalogEntry` (shared) | FK `BookRecord.source_catalog_entry` |
| Link | `BookCreationRequest.submission` OneToOne -> BookSubmission | |
| Output | `GeneratedAsset.source_job` -> ProcessingJob; `CuratedBookDocument.source_job` | `linked_book` |
Both can create Books; both have queue/cancel/retry state, pause/resume vs cancel_requested, and "origin" fields with the same values (user/curation/automation). Two overlapping name `ProcessingJob` (ingestion) vs `processing` app. Evidence of organic growth: pipeline A was in the initial schema (March 21); B depends on catalog/0011 and ingestion/0008 (so came later; exact date UNVERIFIED) and was bound to A by a nullable OneToOne.

## 5. Schema history and churn

58 migrations in about 3.5 months (2026-03-21 to 2026-07-06): catalog 23, ingestion 10, access 12, processing 6, accounts 5, common 2 (note 17 coverage; tests/policy/existing_migrations.txt lists 44 as grandfathered, UNVERIFIED which is newer). What the churn reveals:
1. Bengali text broke ASCII-oriented normalisation/slugs: `normalized_*` columns added (0003), data repaired next day by an N+1 RunPython (0004). URL columns widened to 1000 because percent-encoded Bengali URLs overflow 200 chars (catalog/0005, ingestion/0004). Lesson: Unicode normalisation and URL length are day-one requirements.
2. A unique (source, normalized_title) constraint was added and removed within 6 days (0003 -> 0011): titles collide across editions/sources; hence `edition`, `BookGroup` (0015).
3. Catalog codes (`catalog_code`, obfuscated 50-bit codes) implemented three times by copy-paste (0006, 0007 "rehash", 0014 for series) with an in-place column type change; the algorithm depends on created_at ordering at migration time.
4. Permission scopes: renamed in place (`preview:read_once` -> `preview:html`), `read:once` re-added with a new meaning, `physical_books:view` added; four migrations that changed only `choices`. Scopes are free text in DB.
5. Kindle: `last_kindle_sent_at` on Book added (0020), replaced by per-user `UserBookKindleSend` (0021), column dropped (0022); the new table had no UUID default until 0023 (bug).
6. Book-source model went from many-per-book to exactly one (0019), with a data-destroying dedupe.
7. UI state moved into the database (processing/0003-0006): projections, domain versions, singleton sync states; plus triggers (0004) to repair drifted derived state. Indicates a polling/SSE UI that was too slow to compute live, and an inconsistent state model.
8. Late indexes on hot filters (catalog/0018, ingestion/0009): performance found in production.
9. Rebrand of defaults from the named source site to generic `source_site*` (0023, Jun 30) without rewriting existing rows; generated by Django 4.2.30 while all others were 5.2.12 (environment drift).
10. Circular catalog <-> ingestion coupling forced split `0001/0002_initial` in three apps.
11. Reverse of nearly every data migration is a noop; 0019 deletes data; there is no migration test beyond running on Postgres.
Net: roughly 1 migration every 2 days; the domain model was discovered incrementally, which is the best argument for designing aggregates and state machines up front in the rebuild.

## 6. Scripts and tools inventory

| Script | Does | Pain it reveals |
|---|---|---|
| `scripts/verify.sh` (tests) | policy checks -> up stack -> stop workers -> seed e2e -> pytest -> node unit -> build -> Playwright `--workers=1` | tests need full live Docker stack; workers stopped so synthetic rows are not consumed (S2, S3) |
| `test-processing-live.sh`, `regression_curate_300.sh/.py` | live-site tests / 300-URL EPUB regression, resumable JSON state | non-hermetic; depends on third-party site (S6, T14) |
| `tests/verify_e2e_reprocessing.py` | reprocess 15 books, poll job status up to 300 s | selects books by real source-site name (S7) |
| `tests/policy/check-file-size`, `check-architecture` | 300-line cap; ban `part_N` splits, `apiFetch` placement, transport imports | pushed code into `*_cases/` aggregators and grandfather lists (46 large files, 44 migrations) (S9-S11); policy was a symptom of generated/AI split files |
| `deploy/scripts/deploy.sh` + steps, `install-docker.sh`, `install-nginx.sh`, `setup-host-nginx.sh`, `generate-env.sh` | see 3.1 | builds on prod, downtime, passwords printed |
| `migration/*` | host move | see 3.3 |
| `local/scripts/dev.sh`, `dockerctl`, `ensure-dockerctl`, `clear_docker.sh`, `run_local.sh` | dev stack, macOS Colima mgmt, destroy all Docker state | macOS-centric; `clear_docker.sh` destructive; drop |
| `local-production/deploy.sh` | prod-like single machine | third Compose copy |
| `logs/scripts/show-logs.sh` | tail local/remote logs | no centralised logs |
| `save-source-site-auth.sh/.py` | harvest login cookie from Firefox | manual, secret file, expiry outage |
| `automation/lib/common.sh`, `env_tools.py` | shared bash (timed prompts, compose detection, credential printing) and env merge/shell-export | home-grown config management; `$`-safe quoting is a valid learned requirement (S8) |
| `app/backend/scripts/force_create_failed.py` | bulk force-generate all failed requests | failures common, UI lacked bulk retry (T12) |
| `recover_kabitasamagra4.py` | recover one book whose re-scrape lost 102 items from an older CuratedBookDocument | destructive re-scrape overwrote good content; versions were accidental backups (T13) |
| `regression_curate_300.py`, `source_site_live_validation.py`, `source_site_semantic_validation.py` | scrape-and-audit harnesses; detectors for dup blocks, nav junk, bad contributors, TOC after content, blank pages | real quality rules, to convert into fixtures/acceptance tests (T14-T16, T34) |
| `check_books*.py`, `check_db_books.py`, `check_gita.py`, `check_refs.py`, `diagnose_curation.py` | throwaway debuggers left in repo root | dedication detection hardest heuristic; cross-record tracing; embed real third-party titles/URLs |
| `templates/registration/*` (invite, password reset; txt+html+subject) | e-mails, brand "RSalehin24 Library" hardcoded, English only, 90% duplicated HTML | need base layout, i18n, brand from config |
Domain constraints confirmed: Bengali font rendering needs `fonts-noto-core` + `libraqm0` in the Python image; images built on host; node 22 build stage.

## 7. Configuration and secrets handling

Mechanism: plain `KEY=VALUE` env files scaffolded from `*.example`, merged by shell scripts, injected into containers via a Compose `x-app-environment` anchor and read in `config/settings.py` with `env()`/`env_bool`/`env_list`. No secret manager, no typed validation, no startup failure on missing/insecure secrets.

Setting names (no values): APP_ENV, TIME_ZONE, DJANGO_SECRET_KEY, DJANGO_DEBUG, LOG_LEVEL, DATABASE_URL, DB_CONN_MAX_AGE, CELERY_BROKER_URL, CELERY_RESULT_BACKEND, CELERY_TASK_ALWAYS_EAGER, PUBLIC_BASE_URL, PUBLIC_API_ORIGIN, FRONTEND_BASE_URL, BACKEND_PORT, FRONTEND_PORT, VITE_API_BASE_URL, DEFAULT_FROM_EMAIL, EMAIL_BACKEND, BREVO_API_KEY, BREVO_SENDER_EMAIL, ACCOUNT_INVITE_FROM_EMAIL, EMAIL_HOST/PORT/HOST_USER/HOST_PASSWORD/USE_TLS, SUPER_ADMIN_EMAIL, SUPER_ADMIN_PASSWORD, DJANGO_ALLOWED_HOSTS, DJANGO_CORS_ALLOWED_ORIGINS, DJANGO_CSRF_TRUSTED_ORIGINS, DJANGO_CORS_ALLOW_CREDENTIALS, DJANGO_USE_X_FORWARDED_HOST, DJANGO_SECURE_PROXY_SSL_HEADER, SESSION_COOKIE_SECURE/SAMESITE, CSRF_COOKIE_SECURE/SAMESITE, RUNTIME_STORAGE_DIR, SOURCE_SITE_HOST, SOURCE_SITE_FALLBACK_HOSTS, SOURCE_SITE_EMAIL, SOURCE_SITE_PASSWORD, SOURCE_SITE_AUTH_STATE_PATH, CONTAINER_DNS(_FALLBACK), POSTGRES_DB/USER/PASSWORD, GUNICORN_*, CELERY_WORKER_CONCURRENCY, CELERY_PROCESSING_CONCURRENCY, CELERY_WORKER_PREFETCH_MULTIPLIER, CELERY_WORKER_MAX_TASKS_PER_CHILD, HOST_BIND_IP, DEPLOY_* (host keys), TARGET_*/SOURCE_* (migration keys incl. *_SSH_PASSWORD, *_SUDO_PASSWORD).

Unsafe defaults (VERIFIED unless noted):
- `DJANGO_SECRET_KEY` falls back to a public "development-only-insecure" string, both in compose (docker-compose.yml:4) and in code (settings.py:74). A production start with the var missing succeeds silently.
- `SUPER_ADMIN_PASSWORD` default `changeme` (compose :26); admin password printed in clear to terminal on first deploy, `dev.sh up` and `local-production/deploy.sh` (common.sh:85; remote_deploy_flow.sh:182).
- Postgres `postgres:postgres` default superuser credentials (settings.py:172-176); app connects as superuser.
- `DJANGO_ALLOWED_HOSTS` default includes `nginx`, which does not exist in Compose (compose :27); `DEBUG` defaults on unless APP_ENV=production (settings.py:73).
- `DEFAULT permission_classes = AllowAny` in DRF settings (settings.py:~203; authorisation is enforced per view, so a forgotten view is open). Marked UNVERIFIED as to per-view overrides.
- Dev stack binds to 0.0.0.0 (LAN) by default; Celery results/Redis unauthenticated (no password in default Compose; internal network only).
- Secrets at rest/in motion: `.app.env` copied into migration bundles on laptop (KEEP_STAGING=1 default) and /tmp on target; `pg_dumpall --globals-only` contains role hashes; sudo password piped into a remote command line (ssh.sh:~173, UNVERIFIED line); `StrictHostKeyChecking=no` mode available.
- `source_site_auth.json` is a live login cookie stored in the storage dir and scp'd around.
- Hostnames/identifiers hard-coded: owner production host, GitHub repo SSH URL (default `REPO_SSH`), source-site domain in scripts, brand name in e-mail templates; do not carry over.
- Good practice worth keeping: shlex-quoted shell export so `$` in secrets is literal; secure cookies derived from https public URL; `HttpOnly` session cookie.

## 8. Observability, logging, error handling, testing

- Logging (VERIFIED settings.py:280-297): one console handler, plain text format `%(asctime)s %(levelname)s %(name)s %(message)s`, root level from `LOG_LEVEL`. No JSON, no request/correlation id in the format (AuditLog has a `request_id` column but logs do not), no per-service config, no rotation/shipping. Gunicorn access log to stdout. Local runs also tee to `logs/local/<svc>/*.log`.
- Metrics/tracing/alerting: none found. Health: `/api/csrf/` (and `/api/health/` locally) used as health endpoint (a CSRF endpoint is not a readiness check; no DB/Redis check, UNVERIFIED). Worker liveness via a 5 s Celery heartbeat task plus the `engine`'s stale-worker detector.
- Error handling in pipeline: job status + `last_error`, `ProcessingLog` rows, request `error_message`, curated `validation_summary` with VALIDATED/REVIEW_REQUIRED/INVALID gate; `task_acks_late` redelivery; stale-job recovery every minute; inline fallback when broker dispatch fails. Failures reach users as strings (e.g. "Sign-in required: ..."). Scripts show connection resets between items (T12).
- Testing: pytest (inside container, needs Postgres because of trigger migrations, marker `live` for network tests); frontend `node --test`; Playwright e2e against the real Docker stack, 1 worker, chromium only, trace on retry; seed data prefix "E2E "/`@e2e.local`; policy checks as gate; no CI (stated limitation); live tests depend on the third-party site; 13 reference "spec books" with rule checks (cross-book links, TOC non-empty, dedication not duplicated, English book has no Bengali labels). Test files split into `*_cases/` dirs to meet the 300-line cap.
- Quality knowledge captured in tests (LP1-LP11, SB rules): dedication/front-matter extraction rules for Bengali labels (উৎসর্গ, অনুবাদ vs অনুবাদক), cover data-URI inlining, preview single-open lock key `ebook_preview_lock:`. These are acceptance fixtures for the rebuild's parser.

## 9. Issues

| # | Issue | Severity | Status |
|---|---|---|---|
| I-1 | No backup, restore, or restore drill for Postgres or the file storage; single VM | Critical | VERIFIED (grep of deploy/ and local-production/ finds no backup/pg_dump) |
| I-2 | Insecure secret defaults (SECRET_KEY, admin `changeme`, postgres/postgres); no startup refusal | Critical | VERIFIED compose :4,:26, settings.py:74 |
| I-3 | Admin password printed to terminal on deploy/dev | High | VERIFIED remote_deploy_flow.sh:182-186 |
| I-4 | Deploy = `down` then `up --build` on the prod host; downtime every release; no rollback; local uncommitted files overlaid onto the branch | High | VERIFIED environment_and_domain_checks.sh:290-291; overlay UNVERIFIED in code |
| I-5 | Documented resource limits/Redis maxmemory not applied; processing OOM risk on a small host | High | VERIFIED no `deploy:`/mem_limit/maxmemory |
| I-6 | Two parallel pipelines + three-way record split; state in 5+ columns | High | VERIFIED via migrations (note 17) |
| I-7 | Postgres triggers silently override application writes; Postgres-only migrations | Medium | VERIFIED 0004 |
| I-8 | UI projections and version counters stored in the system-of-record DB | Medium | VERIFIED via note 17 (0003 not re-read) |
| I-9 | Host-move: full downtime, 15 min drain, whole-cluster dump scaling with book HTML; secrets copied to laptop; staging kept by default | High | VERIFIED defaults config.sh:201 |
| I-10 | After successful move the source stack is restarted by default (two live copies; duplicate schedules/e-mail) | High | VERIFIED edge_verify_and_entrypoint.sh:69, config:198 |
| I-11 | `--dry-run` marks phases done so later `--resume` skips real work | Medium | UNVERIFIED (inferred, note 18 T8.4) |
| I-12 | Sudo/SSH passwords accepted in config; `StrictHostKeyChecking=no` mode | Medium | UNVERIFIED lines |
| I-13 | Full book HTML duplicated in rows (Book, CuratedBookDocument JSON, CuratedSection, assets) | Medium | VERIFIED via migrations |
| I-14 | Enums are free text with `choices` only; no CHECK; PermissionGrant has no uniqueness or target validity | Medium | VERIFIED via migrations |
| I-15 | Destructive re-scrape overwrote published content; only accident-versioning saved it; migration 0019 destroys alternate sources | High | VERIFIED (T13 script; 0019 per note 17) |
| I-16 | Kindle delivery history has no address, status or error; `kindle_emails` JSON unvalidated; one send record per (user, book) | Medium | VERIFIED via migrations |
| I-17 | `ReadingSession.last_opened_at` auto_now conflates progress save with open; duplicates BookOpeningRecord | Low | VERIFIED via migrations |
| I-18 | `engine` container undocumented; migration restore never starts it | Medium | VERIFIED compose :199; restore omission UNVERIFIED |
| I-19 | Docs contradict code (limits, services, workers, migration phases) | Medium | VERIFIED (limits, engine); others per note 15 sec 5 |
| I-20 | Single manual source-site login cookie; expiry halts multi-page TOC scraping | Medium | per note 15, UNVERIFIED in code |
| I-21 | `/media/` served unauthenticated by nginx from host path; `chmod o+x` on parents of app dir | High (private library) | UNVERIFIED in code (note 15 sec 2.10); also conflicts with `is_protected` assets |
| I-22 | Per-minute beat polling of DB for due automations (5 tasks), a 5 s heartbeat task through the broker | Low | VERIFIED celery.py:26-55 |
| I-23 | Health check is the CSRF endpoint; logs unstructured; no metrics | Medium | VERIFIED (compose, settings.py:280) |
| I-24 | Copy-pasted catalog-code algorithm x3; obfuscation not security; unstable across re-imports | Low | per note 17 |
| I-25 | DRF default permission `AllowAny` | Medium | UNVERIFIED (settings.py:~203 from grep; per-view override not checked) |
| I-26 | Repo hygiene: debug scripts with real third-party titles/URLs, hard-coded brand/host/repo names | Low | VERIFIED (notes) |

## 10. Keep / change / drop for the rebuild

### Keep (as requirements or patterns)
- Compose topology idea: one container per concern, healthchecks with `service_healthy` gating, an init/migrate one-shot, internal vs public networks, loopback-only published ports. Reason: matches the brief; cheap and understood.
- Late-ack + redelivery + stale-job recovery semantics, per-worker memory recycling, resumable scrapes via page cache: translate to Rust job queue with leases/heartbeats (the `engine` concept) persisted in Postgres.
- Row-count + checksum verified restore, drain-before-freeze, abort on mismatch, resumable phases: as the restore-drill spec.
- Curated-document quality gate (VALIDATED/REVIEW_REQUIRED/INVALID), explicit error reasons, Force Generate semantics, versioned curated documents.
- Soft delete on Book; unique per-(user, book) shelf/bookmark rows; unique reading session; highlight kinds/colours/tags; `PermissionGrant` expiry and target scoping; `AuditLog` with request id; saved filters; invite nonce (single-use set-password links); mandatory TOTP.
- Spec books / regression harness / semantic detectors as fixtures (kept outside source per project rule on third-party content).
- Bengali font stack requirement (Noto + raqm), UTF-8 normalisation (NFKC, letters/marks/numbers) done once and tested.
- Edge-case knowledge: URL max 1000, Postgres 16, DNS pinning/fallback for the source site.

### Change
- Edge: Caddy container with automatic TLS replaces host nginx + certbot + chmod hacks; one Compose file with env overlays (dev/prod) instead of three copies.
- Deploy: build images in CI/registry, tag, `docker compose pull && up -d` per service (no global `down`), run schema migration as an explicit gated step after a backup; rollback by tag.
- Secrets: Docker/Compose secrets or env injected at deploy; startup refuses missing/insecure values; bootstrap admin via one-time setup link, never printed; role per service with least privilege (one Postgres schema/role per service in the single DB container).
- Backup: scheduled `pg_dump`/WAL archive + storage snapshot to offsite, encrypted, restore drill automated; this also replaces the host-move toolkit (restore on new host is the move; DB dump + object/blob storage).
- State model: one pipeline, one state machine owned by one service, state derived not duplicated; no triggers; no UI projection tables (use queries/materialised views or cache outside the system of record).
- Content: versioned immutable ingestion results with atomic promotion and a count/validation gate; store book HTML once (blob store/files), metadata in tables.
- Enums: Postgres enums or CHECK constraints; unique constraints on grants; scope-to-target validation.
- Kindle: send log table (user, book, address, status, error, attempts, timestamps) plus verified-address table.
- Config: typed, validated, documented; resource limits actually set in Compose (mem_limit/cpus, Redis maxmemory if Redis is kept; consider whether Redis is needed at all versus Postgres queue).
- Logging: structured JSON with correlation id to stdout; health vs readiness endpoints; basic metrics.
- Source-site auth: a managed secret/credential record with expiry alert and an upload endpoint, not a file scp.
- Tests: hermetic by default (recorded fixtures), live-site tests opt-in; real CI.

### Drop
Triggers (processing/0004); `ProcessingUiProjection`/`DomainVersion`; `BookOpeningRecord` or `ReadingSession.last_opened_at` duplication (keep one); three singleton idioms; `BookSource.is_primary`; second pipeline (ingestion vs processing duplication); obfuscated catalog-code algorithm (use plain sequence/ULID, if codes are even needed); macOS tooling (`dockerctl`, Colima, `caffeinate`, `clear_docker.sh`); `local-production` Compose; host-nginx scripts; line-cap/part-split policy scripts as designed (the rebuild has its own lint rules); debug scripts in repo root; the `/demo-login` unauthenticated demo (UNVERIFIED relevance, note 15 sec 3); in-process inline-fallback mode; brand/host constants.

### Proposed table-to-domain ownership (input for service boundaries)
Rule: a table belongs to the service that is the only writer; cross-service references are by id (no cross-schema FK), read via API or events. Services follow the project facts: identity, access, catalog, content, library, ingestion, notify (+ gateway).

| Legacy table(s) | Proposed owner | Notes |
|---|---|---|
| accounts_user (core), django_otp devices, sessions, invite nonce | identity | `kindle_emails` moves out to notify |
| access_permissiongrant | access | add unique + target validation; targets referenced by id |
| access_previewaccesssession | access | token issuance; content service validates |
| common_auditlog | access (or separate audit module written by all via events) | append-only, no updated_at |
| catalog_book (metadata part), category, contributor, series, bookcategory/contributor/series, bookgroup, booksource (source URL), metadatareview, metadataversion, catalog_code | catalog | owns identity and metadata of a work/edition; state = published/archived only |
| catalog_book content columns (main_content_html, book_info_html, dedication_html, toc, content_items), catalog_generatedasset (html/epub/cover), curated document/section/entity/evidence | content | immutable versions, assets, EPUB build outputs, quality gate results |
| access_readingsession, bookmark, highlight, bookopeningrecord, catalog_userbook, common_savedfilter | library | per-user shelf, progress, annotations, read-once marker |
| catalog_userbookkindlesend, accounts_user.kindle_emails (new: verified addresses, send log) | notify | owns Kindle delivery and e-mail (invite/reset templates, Brevo/SMTP) |
| ingestion_booksubmission, titleresolutionattempt, matchcandidate, duplicatereview, processingjob, processinglog, sourcecatalogentry, catalogautomationsettings, catalogcurationrun, sourcecatalogrefreshstate; processing_bookrecord, bookcreationrequest, processingautomationsettings, processingsyncstate | ingestion (merged into ONE job/request model) | holds source URL identity, requests, runs, schedules, source cookie secret; emits "book ready" with content id to content/catalog |
| processing_processinguiprojection, processing_processinguidomainversion | drop | |
Boundary notes: (a) Book is currently one table straddling catalog (identity/metadata), content (HTML, assets), and ingestion state (state, review_state) - the rebuild must split it, joined by a stable book id. (b) Catalog <-> ingestion circularity (Book <- Submission, Asset -> Job) is removed by letting ingestion publish a result event and catalog/content own their own rows. (c) ReadingSession/Highlight reference book ids only; deletion of a book is a soft-delete event consumed by library. (d) PermissionGrant targets (book/category/contributor) need catalog ids; access must tolerate dangling ids (grants keyed by id, validated on write via catalog API).

## 11. Open questions

1. Is Redis needed in the rebuild? Candidates: Postgres-backed queue with `SKIP LOCKED` + leases (fewer containers, transactional with state) versus keep Redis for SSE fan-out/rate limits. Legacy used it for broker, results, engine state, checkpoints.
2. Where do book files live: Postgres large objects, a volume, or an S3-compatible container (MinIO adds a container)? Needed to decide backup mechanism. The legacy served `/media/` unauthenticated: confirm the rebuild must authenticate every download/read.
3. Backup target and RPO/RTO: offsite (which provider), encryption key custody, frequency, retention?
4. One Postgres container: single database with schema-per-service and per-service roles, or database-per-service in the same cluster? (Affects migration tooling and cross-service reads.)
5. Does the rebuild keep the DB-stored automation/singleton settings, or move schedules into the ingestion service config table with computed next-run?
6. What are the 11 vs 12 permission scopes in the rebuild; how do grants target categories/contributors with ids owned by catalog?
7. Do catalog codes (10-char obfuscated) have a business use (shown to readers, used in saved filters, CSV exports)? If not, drop.
8. Required semantics of "Read Once" and preview sessions (anonymous previews allowed? legacy allowed null user).
9. Is the demo account (/demo-login) required? Not in the release scope; UNVERIFIED.
10. Kindle: need verified addresses, retry policy, and send history shown to users? (Legacy kept only a boolean-like record.)
11. Source-site authentication (login cookie) remains a manual operator task: acceptable, or should the operator UI accept a pasted cookie with expiry reminder?
12. Data migration: will legacy data be imported into the new schema (users, shelves, highlights, books) or rebuilt from scratch? If imported, the legacy `catalog_code`, slug, grants and TOTP devices need explicit mapping.
13. Untested here: whether `processing/0003` seeded data and `access/0009` rename left inconsistent rows in production, and whether models drifted from migrations (note 17 unverified list); `django_otp` table list not enumerated.
14. Hosting target for the new stack (single VM size): needed to size the processing worker (legacy: 2-4 GB per large book scrape, ~400 MB child ceiling).

