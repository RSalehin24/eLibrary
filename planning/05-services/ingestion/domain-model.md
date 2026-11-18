# ingestion — domain model

Status: DRAFT

PostgreSQL schema `ingestion`, role `ingestion`. Files on volume `/data/ingestion` (`scrape/`, `docs/`, `build/`). Dedicated database per D-24. Timestamps `timestamptz`; ids UUID unless noted.

## Source mirror (what the source site lists)

| Table | Columns | Keys / constraints / indexes |
|---|---|---|
| `mirror_entries` | `id`, `source_host`, `url_key` (normalized canonical URL), `url`, `title_raw`, `author_raw`, `series_raw`, `category_raw`, `incomplete_flag` (source marks the book unfinished), `title_key`, `loose_title_key`, `first_seen_at`, `last_seen_at`, `last_sync_run_id`, `missing_since?`, `listing_hash` | `UNIQUE(url_key)`; indexes `(title_key)`, `(missing_since)`, and a GIN index on `title_tokens text[]` (loose-key tokens) for the title resolver (no extension needed). Written only by sync runs; never holds workflow state. Entries that vanish get `missing_since`, never deleted (and never auto-requested while missing). |

Display state of an entry is a query: latest request for `url_key` (view `mirror_status`), not a stored column; this removes the denormalized state and the trigger of the legacy (X6d).

## Requests (local workflow)

| Table | Columns | Keys / constraints |
|---|---|---|
| `requests` | `id`, `source_kind` (`mirror`\|`url`\|`epub_upload`), `mirror_entry_id?`, `url_key?`, `upload_path?`, `origin` (`operator`\|`automation`\|`sync_run`), `requested_by` (account or `automation`), `state`, `phase`, `parent_request_id?` (new edition / refresh chain), `intent` (`create`\|`refresh_existing`\|`new_edition`), `edition_label_hint?`, `target_book_id?`, `book_id?` (shell from catalog), `version_id?`, `forced` (bool), `forced_reason?`, `cancel_requested` (bool), `attempt_no`, `last_error_code?`, `last_error_message?`, `created_at`, `updated_at`, `state_version` (bigint) | partial `UNIQUE(url_key) WHERE state IN active` (one active request per source URL, INV-ING-010); `CHECK` source_kind matches present column; index `(state, updated_at)`, `(mirror_entry_id, created_at desc)`; every state change goes through one function that compares `state_version` and appends an outbox event |
| `request_attempts` | `request_id`, `attempt_no`, `started_at`, `finished_at`, `outcome`, `error_code?` | history for retries |
| `audit_log` | `id`, `actor`, `action`, `target_type`, `target_id`, `details`, `at` | INSERT-only; every operator action, forced generation, credential change, automation change |

`state` in `queued`, `running`, `needs_review`, `awaiting_credential`, `in_catalog_review`, `published`, `failed`, `cancelled`, `rejected_duplicate`; `phase` (display only) in `scrape`, `curate`, `duplicate_check`, `build`, `publish`. Details in [state machines](state-machines.md).

## Jobs (Postgres queue)

| Table | Columns | Keys / constraints |
|---|---|---|
| `jobs` | `id`, `kind` (`scrape`, `curate`, `duplicate_check`, `build`, `publish`, `sync`, `check_credential`, `scheduler_tick`), `request_id?`, `sync_run_id?`, `state` (`queued`\|`running`\|`succeeded`\|`failed`\|`cancelled`), `priority` (smallint), `run_after`, `attempt`, `max_attempts` (default 3), `lease_owner?`, `lease_epoch` (int, +1 on each claim), `lease_expires_at?`, `heartbeat_at?`, `cancel_requested` (bool), `cursor` (jsonb, small: page index, step), `idempotency_key`, `error_class?` (`retryable`\|`permanent`), `error_code?`, `error_message?`, `retry_after?`, `created_at`, `started_at?`, `finished_at?` | `UNIQUE(idempotency_key)`; partial `UNIQUE(request_id) WHERE state IN ('queued','running')` (one active job per request); claim index `(priority desc, run_after) WHERE state='queued'`; reaper index `(lease_expires_at) WHERE state='running'`; CHECK: `request_id` xor `sync_run_id` except tick/credential kinds |
| `job_log` | `job_id`, `at`, `level`, `message`, `fields` (jsonb) | paged in the console; TTL 30 days |

Claim statement (the only way a job starts):

```sql
UPDATE jobs SET state='running', lease_owner=$w, lease_epoch=lease_epoch+1,
       lease_expires_at=now()+interval '120 seconds', heartbeat_at=now(), attempt=attempt+1, started_at=coalesce(started_at,now())
 WHERE id=(SELECT id FROM jobs WHERE state='queued' AND run_after<=now()
           ORDER BY priority DESC, run_after, id FOR UPDATE SKIP LOCKED LIMIT 1)
RETURNING *;
```

Every write by the executor includes `AND lease_epoch=$epoch` (fencing); a zombie's writes affect zero rows and it stops.

Typed errors in code: `JobError::Retryable{code, retry_after?}` (network, 5xx, timeout, `rate_limited` with Retry-After), `JobError::Permanent{code}` (`auth_required`, `locked_source`, `source_changed`, `invalid_document`, `build_failed`, `catalog_rejected`, `unsupported`). Retry decisions use only the class, never the message text. Retryable with `attempt < max_attempts` requeues with `run_after = now + base*2^attempt + jitter` (no sleeping workers); otherwise the job fails permanently. `auth_required` is permanent for the job but moves the request to `awaiting_credential` (resumable).

## Scrape cache (files)

| Table / path | Content |
|---|---|
| `scrape_pages` (`request_id`, `url_key`, `kind` landing\|toc\|lesson\|topic\|image, `http_status`, `sha256`, `size_bytes`, `path`, `leaf_state` text\|empty_at_source\|unreachable\|locked, `fetched_at`) PK `(request_id, url_key)` | metadata only |
| `/data/ingestion/scrape/<request_id>/<sha256>` | page bodies and images as files; written atomically; reused on retry; deleted when the request reaches a terminal state + TTL (default 7 days) |

No page body is ever stored in a table row or a request/job JSON column.

## Curated document (one authoritative copy)

| Table | Columns | Constraints |
|---|---|---|
| `curated_documents` | `id`, `request_id`, `version_no`, `doc_path` (JSON file under `docs/`), `doc_hash`, `ruleset_version`, `normalizer_version`, `validation_status` (`ready`\|`needs_review`\|`invalid`), `issues` (jsonb list of `{code, severity, evidence}`), `forced`, `created_at` | `UNIQUE(request_id, version_no)`; append-only; the document holds metadata with evidence and confidence, section tree, sanitized section HTML, asset refs, language; the EPUB, preview and cover are derived artifacts regenerated from it (no fourth copy of the text) |
| `review_items` | `id`, `request_id`, `kind`, `payload`, `state` (`open`\|`resolved`\|`dismissed`), `resolution`, `resolved_by`, `resolved_at` | kinds: `IncompleteSource`, `LockedSource`, `LowConfidenceEntity`, `AmbiguousStructure`, `ConservationFailure`, `SourceDrift`, `BuildFailed`, `CatalogRejected`; resolution actions validated per kind. Duplicates are NOT a review item kind: they use `duplicate_reviews`. |

## Duplicate review

| Table | Columns | Constraints |
|---|---|---|
| `duplicate_reviews` | `id`, `request_id`, `classification` (`exact_duplicate`\|`new_edition`\|`new_translation`\|`new_work`\|`needs_review`), `candidates` (jsonb: `[{book_id, title, evidence[]}]`), `state` (`pending`\|`resolved`), `decision?` (`new_work`\|`new_edition`\|`new_translation`\|`refresh_existing`\|`confirm_duplicate`), `target_book_id?`, `edition_label?`, `decided_by?`, `decided_at?`, `note?` | partial `UNIQUE(request_id) WHERE state='pending'`; `exact_duplicate` and `needs_review` always create a pending row; `new_*` classifications proceed automatically without a pending row only when evidence is complete (author present with confidence, category present), otherwise the class is downgraded to `needs_review` |

## Build artifacts (candidates)

| Table | Columns | Constraints |
|---|---|---|
| `build_artifacts` | `id`, `request_id`, `doc_hash`, `builder_version`, `book_id`, `epub_path`, `epub_sha256`, `cover_path`, `preview_path`, `audit_report` (jsonb), `state` (`built`\|`audit_failed`\|`sent`\|`accepted`), `build_hash` (= sha256 of doc_hash + builder_version + book_id) | `UNIQUE(doc_hash, builder_version, book_id)`; `build_hash` is the catalog `Idempotency-Key`; the EPUB identifier is `urn:uuid:` UUIDv5 over `(book_id, doc_hash)`; deterministic build means a rebuild of the same inputs is byte-identical (INV-CON-002) |

## Sync, automation, credential

| Table | Columns | Constraints |
|---|---|---|
| `sync_runs` | `id`, `kind` (`catalog`\|`incomplete`), `trigger` (`manual`\|`automation`), `phase`, `page_cursor` (int), `last_page_signature`, `pages_done`, `fetched_count`, `upserted_count`, `created_requests_count`, `create_cursor` (jsonb), `consecutive_errors`, `error_budget`, `listing_ok` (bool), `requested_by`, `cancel_requested`, `started_at`, `finished_at?`, `last_error_code?` | partial `UNIQUE(kind) WHERE phase NOT IN terminal` (one active run per kind) |
| `automation_settings` | `kind` (PK: `catalog`\|`incomplete`), `enabled`, `interval` (`daily`\|`weekly`\|`biweekly`\|`monthly`), `time_of_day`, `timezone`, `mode` (`pending`\|`all`), `max_requests_per_run`, `max_open_requests`, `next_due_at`, `last_started_at?`, `last_success_at?`, `last_failure_at?`, `cooldown_until?`, `active_run_id?`, `revision` | defaults: disabled; one default set in code and migration (no conflicting defaults) |
| `source_credentials` | `id`, `source_host`, `kind` (`cookie`), `secret` (write-only column, never returned by any API or log), `expires_at?`, `state` (`absent`\|`valid`\|`expiring`\|`expired`\|`rejected`), `set_by`, `set_at`, `last_checked_at?`, `last_ok_at?`, `last_failure_code?` | partial `UNIQUE(source_host) WHERE state <> 'absent'` (one active credential per host); API returns only status fields; storage encryption open (README) |
| `events` | `id` (bigserial), `type`, `request_id?`, `payload`, `created_at` | outbox for console SSE; `NOTIFY ingestion_events` after commit-time insert; retained 7 days |
| `event_cursors` | `source` (PK), `last_id` | cursor into catalog events |

## Bengali normalization (shared crate `bn-text`, used by ingestion and catalog)

Fixes the legacy keys (X6b): punctuation was deleted instead of separating words, and the word lists had lost their vowel signs.

| Function | Steps | Use |
|---|---|---|
| `exact_key(s)` | (1) NFC (nukta letters ড় ঢ় য় converge to base + nukta); (2) remove ZWJ/ZWNJ; (3) fold Bengali digits ০-৯ to 0-9; (4) lowercase Latin; (5) every character that is not Unicode letter, number or mark (so including hyphen, danda "।", quotes, brackets) becomes one space; (6) collapse and trim. Combining marks (vowel signs, hasanta, nukta) are always kept. | identity of titles, names, categories, editions; the only key used for automatic decisions |
| `loose_key(s)` | `exact_key` then fold spelling variants: ী to ি, ূ to ু, ণ to ন, শ and ষ to স, ৎ to ত | search recall and fuzzy suggestions only; never an automatic decision |
| `tokens(s)` | split `exact_key` on spaces | whole-token comparisons |

Rules: idempotent; folding never lengthens; the key stores `normalizer_version`; no word list is ever compared by substring, only by whole-token equality after `exact_key`. Word lists are data files with golden tests and are written with full vowel signs: author-role indicators লেখক, অনুবাদক, সম্পাদক, রূপান্তর, মূল, অনুবাদ, রচনা, সংকলন (title-author splitting only on a whole token); ordinal words (প্রথম, দ্বিতীয়, তৃতীয়, ...) map to digits only as a whole token, so প্রথমা is never altered; honorifics (ডক্টর, ডঃ, ড., অধ্যাপক, জনাব, মৌলভী, মো:) are stripped into a separate `honorific` field and never cause rejection.

## Author and entity parsing

The raw string is always kept. Split on `, ; |` and newline, and on " ও ", " and ", " & " only when every part passes the structural check (>= 2 letters, no digits, <= 8 words). A part that fails the check stays one name with `confidence = low`. A missing or low-confidence author yields `needs_review` in the duplicate check, never "new book". Latin and Bengali spellings of one person are matched only through catalog agent aliases (`/internal/agents/resolve`), not by key.

## Matching rules (duplicate check, REQ-ING-015, INV-ING-015)

Staged; the first decisive stage wins; fuzzy is a suggestion only.

1. **Source identity**: `url_key` equals an existing `book_sources.source_key` (catalog) or an active/published request: result `exact_duplicate` (`refresh_existing` offered).
2. **Exact key match**: `title_key` equal to a catalog book's title key. Then compare, all by `exact_key` set equality or overlap:

| Title key equal | Author overlap | Category overlap | Translators | Publisher / edition | Class |
|---|---|---|---|---|---|
| yes | >= 1 shared | >= 1 shared | equal sets (both empty or equal) | same publisher and same edition label (or both absent) | `exact_duplicate` |
| yes | >= 1 shared | any | equal sets | publisher or edition label differs | `new_edition` |
| yes | >= 1 shared | any | sets differ (one empty, or both non-empty and different) | any | `new_translation` |
| yes | both sides have authors, none shared | any | any | any | `new_work` (same title, different works) |
| yes | missing or low-confidence on either side | any | any | any | `needs_review` |
| no | | | | | no exact candidate; go to 3 |

   Series/volume digits are part of the key, so "খণ্ড ১" never matches "খণ্ড ১০"; a collection never matches its component by containment (no substring rule).
3. **Fuzzy suggestion**: token-set similarity of `loose_key` tokens above the configured threshold (default open, tuned on the gold set) plus at least one shared author loose key, or equal `loose_key` with different `exact_key`: result `needs_review` with the candidate and evidence shown side by side. Never auto-merge.
4. **Deleted books**: a match against a soft-deleted catalog book is `needs_review` (`matches_deleted_book`); there is no resurrection by title.
5. No candidate at all and complete author and category: `new_work`.

The classifier runs in catalog (`POST /internal/duplicates/classify`, pure over catalog rows); ingestion supplies the keys and owns the review state.

## Validation (curated document)

Checks (each a typed issue): missing title, missing body, missing canonical URL, duplicate section paths, dead TOC leaves, source chrome in body, non-200 or sentinel-title pages (Cloudflare 200), empty chapter above the single configured threshold (one threshold, used by classification and build alike), conservation (INV-ING-002), completeness (INV-ING-006: every TOC leaf fetched or recorded empty at source, no percentage tolerance), language set explicitly (detected once, overridable). Severity `error` makes `validation_status = invalid` or `needs_review` by kind; `forced` (see actions) can proceed past `needs_review` only.

## Build (EPUB writer)

| Concern | Rule |
|---|---|
| Templating | XHTML produced by a templating step with HTML escaping on; titles and metadata escaped; no string concatenation of scraped text |
| Sanitizing | section HTML passes the allow-list sanitizer (`SafeHtml`): no script, event handlers, external loads, unknown URL schemes; idempotent (INV-CON-009) |
| Images | referenced images downloaded during scrape (same host allow-list, GET only), type validated by bytes, size capped, packaged under `OEBPS/images/`, links rewritten; missing image = validation issue, not silent drop |
| Fonts | the chosen Bengali font is embedded (`OEBPS/fonts/`) and referenced by `@font-face` in the stylesheet; cover generated with the same font (open point: font choice) |
| OPF | complete: `dc:identifier` (UUIDv5 over book id + doc hash), title, language, creators with roles, publisher, date, series metadata, modified timestamp; nav document and (if the owner decides) NCX generated from the same section tree as the in-book TOC (INV-CON-007) |
| Page order | cover, title, TOC, book info, front sections, body, back (REQ-ING-003); labels by book language only |
| Audit gate | in-process audit must pass before the artifact is `built`: ZIP structure (mimetype first, stored), XML well-formedness of every XHTML/OPF/nav, manifest-spine-file consistency, nav links = TOC links = tree, all referenced images/fonts present, no external URLs, no empty chapter above threshold, filename safety. epubcheck runs in CI on gold books (not at runtime). Failure = `audit_failed`, request `failed` with review item `BuildFailed`; nothing is sent to catalog. |
| Covers | source image when valid; otherwise generated portrait cover with title and author, contrast >= 4.5:1, no tofu glyphs (REQ-CON-008) |
| Output | a candidate on the ingestion volume, never visible until published; `preview` HTML built from the allow-list (metadata, summary, TOC, first N characters of the first chapter at a paragraph boundary) |

## Value types

`UrlKey`, `ExactKey`, `LooseKey`, `BlockId`, `Sha256`, `RulesetVersion`, `Confidence(0.0..=1.0)`, `Evidence{block_ids, extractor, rule_id, confidence}`, `ReasonCode` (closed enum), `SafeHtml`, `JobError`, `Lease{owner, epoch}`.
