# ingestion - domain model

Status: DRAFT

PostgreSQL database `ingestion`, role `ingestion` (D-24). Files on volume `/data/ingestion` (`scrape/`, `docs/`, `build/`). Timestamps `timestamptz`; ids UUID unless noted. Rewritten for the single-pipeline design: kept from v1 where the analysis supports it, changed where noted. Numbers marked (provisional) are tuned at the P0 baseline (O-7).

## 1. Source mirror (what the source site lists) - REQ-ING-002

| Table | Columns | Keys / constraints |
|---|---|---|
| `mirror_entries` | `id`, `source_host`, `url_key` (canonical URL), `url`, `title_raw`, `author_raw`, `series_raw`, `category_raw`, `incomplete_flag` (source marks the book unfinished), `title_key`, `loose_key`, `title_tokens text[]`, `first_seen_at`, `last_seen_at`, `last_sync_run_id`, `missing_since?`, `listing_hash` | `UNIQUE(url_key)`; indexes `(title_key)`, `(missing_since)`, GIN on `title_tokens` |

- Written only by sync runs, and only these source-owned columns. It holds no workflow state (INV-ING-002).
- Entries that vanish get `missing_since` and are never deleted or auto-requested while missing.
- The display state of an entry is a query (latest request per `url_key`, view `mirror_status`), not a stored column: no denormalized state and no trigger (X6d).

## 2. Requests: one model, status apart from outcome - REQ-ING-001

| Table | Columns | Keys / constraints |
|---|---|---|
| `requests` | `id`, `source_kind` (`mirror`\|`url`), `mirror_entry_id?`, `url_key`, `origin` (`operator`\|`automation`), `requested_by` (account id or `automation`), `status`, `outcome?`, `step` (display only), `intent` (`create`\|`refresh_existing`\|`new_edition`), `parent_request_id?`, `edition_label?`, `target_book_id?`, `book_id` (UUID chosen by ingestion at creation; see README OPEN-5), `version_id?` (set when catalog accepts and publishes the build), `forced` (bool), `forced_reason?`, `cancel_requested`, `last_error_class?`, `last_error_code?`, `created_at`, `updated_at`, `state_version` (bigint) | partial `UNIQUE(url_key) WHERE status IN ('queued','running','awaiting_credential','needs_review')` (one active request per source URL); `CHECK` (`source_kind='mirror'` iff `mirror_entry_id` is set); `CHECK` (`outcome = 'published'` implies `version_id` is not null: "created implies a candidate exists"); indexes `(status, updated_at)`, `(mirror_entry_id, created_at desc)` |
| `request_attempts` | `request_id`, `attempt_no`, `job_id`, `started_at`, `finished_at`, `status`, `error_class?`, `error_code?` | bounded history for retries |
| `audit_log` | `id`, `actor`, `action`, `target_type`, `target_id`, `details`, `job_id?`, `at` | INSERT-only (no UPDATE or DELETE grant); written in the same transaction as the change (REQ-ING-035) |

Value lists (fixed here, mirrored by the [HTTP contract](../../07-contracts/http/ingestion.md)):

| Field | Values | Meaning |
|---|---|---|
| `status` (execution) | `queued`, `running`, `awaiting_credential`, `needs_review`, `done`, `failed`, `cancelled` | where the work is, nothing about the book |
| `outcome` (domain) | `built`, `needs_review`, `duplicate`, `failed`, `published`; null until the pipeline reaches a domain result (`submitted` retired by D-49) | what happened to the book build |

A job `succeeded` never implies an outcome: the outcome is written by the step that produced the domain fact, in the same transaction as the status change. Every status or outcome change goes through one function that compares `state_version`, appends the `audit_log` row and the console `events` row. Transitions: [state machines](state-machines.md).

## 3. Jobs (Postgres queue) - REQ-ING-004..007

| Table | Columns | Keys / constraints |
|---|---|---|
| `jobs` | `id`, `kind` (`scrape`, `curate`, `duplicate_check`, `build`, `publish`, `sync`, `check_credential`, `scheduler_tick`, `retention`), `request_id?`, `sync_run_id?`, `state` (`queued`\|`running`\|`succeeded`\|`failed`\|`cancelled`), `priority` smallint, `run_after`, `attempt`, `max_attempts` (default 3), `lease_owner?`, `lease_epoch` int, `lease_expires_at?`, `heartbeat_at?`, `cancel_requested`, `cursor` jsonb (small: next page index, step), `idempotency_key`, `error_class?` (`retryable`\|`rate_limited`\|`auth_required`\|`permanent`), `error_code?`, `retry_after?`, `created_at`, `started_at?`, `finished_at?` | `UNIQUE(idempotency_key)`; partial `UNIQUE(request_id) WHERE state IN ('queued','running')` (at most one active job per request); claim index `(priority desc, run_after) WHERE state='queued'`; reaper index `(lease_expires_at) WHERE state='running'` |
| `job_log` | `job_id`, `at`, `level`, `message`, `fields` jsonb | paged in the console; retained 30 days (provisional), carries the job correlation id |

Claim (the only way a job starts):

```sql
UPDATE jobs SET state='running', lease_owner=$w, lease_epoch=lease_epoch+1,
       lease_expires_at=now()+interval '120 seconds', heartbeat_at=now(),
       attempt=attempt+1, started_at=coalesce(started_at,now())
 WHERE id=(SELECT id FROM jobs WHERE state='queued' AND run_after<=now()
           ORDER BY priority DESC, run_after, id FOR UPDATE SKIP LOCKED LIMIT 1)
RETURNING *;
```

Every executor write carries `AND lease_epoch=$epoch` (fencing): a zombie's writes touch zero rows and it stops. Heartbeats are made by the working thread itself, between pages and at step boundaries (no separate timer thread that could keep a hung job alive); each unit of work between heartbeats is bounded well under the lease length.

Typed errors (REQ-ING-006), a closed Rust enum, never derived from message text:

| Class | Examples | Effect |
|---|---|---|
| `retryable` | network, timeout, 5xx, `catalog_unavailable` | requeue with `run_after = now + base*2^attempt + jitter` (base provisional 30 s) while `attempt < max_attempts`; then `failed`. A worker never sleeps to back off |
| `rate_limited` | 429 with `Retry-After` | requeue with `run_after = now + retry_after` (bounded); counts as an attempt |
| `auth_required` | 401/403/login page, expired cookie | job `failed`; request status `awaiting_credential` (resumable when the credential is valid again) |
| `permanent` | `locked_source`, `source_changed`, `invalid_document`, `audit_failed`, `catalog_rejected`, `unsupported` | job `failed`; request `needs_review` (with a review item) or `failed` |

## 4. Scrape cache (files) - REQ-ING-012

| Table / path | Content |
|---|---|
| `scrape_pages` (`request_id`, `url_key`, `kind` landing\|toc\|lesson\|topic\|image, `http_status`, `sha256`, `size_bytes`, `path`, `leaf_state` text\|empty_at_source\|unreachable\|locked, `fetched_at`); PK `(request_id, url_key)` | metadata only |
| `/data/ingestion/scrape/<request_id>/<sha256>` | page bodies and images as files, written atomically (temp file + rename), reused on retry |

No page body is ever stored in a table row, a request row or a job column. Files are removed by the `retention` job: when the request is terminal for 7 days (provisional) and in every case 30 days after `fetched_at` (REQ-ING-012, REQ-ING-034). A request is reprocessable from its cache only while the cache exists; afterwards it must be re-scraped.

## 5. Curated document (one authoritative copy) - REQ-ING-013

| Table | Columns | Constraints |
|---|---|---|
| `curated_documents` | `id`, `request_id`, `version_no`, `doc_path` (JSON under `docs/`), `doc_hash`, `ruleset_version`, `ruleset_hash`, `normalizer_version`, `validation_status` (`ready`\|`needs_review`\|`invalid`), `issues` jsonb (`[{code, severity, evidence}]`), `forced`, `created_at` | `UNIQUE(request_id, version_no)`; write-once (no UPDATE grant); the document holds metadata with evidence and confidence, the section tree, sanitized section HTML, asset refs and the language; EPUB, preview and cover are derived artifacts regenerated from it, so there is no fourth copy of the text |
| `review_items` | `id`, `request_id`, `kind`, `payload`, `state` (`open`\|`resolved`\|`dismissed`), `resolution`, `resolved_by`, `resolved_at` | kinds: `IncompleteSource`, `LockedSource`, `LowConfidenceEntity`, `AmbiguousStructure`, `ConservationFailure`, `SourceDrift`, `BuildFailed`, `CatalogRejected`; resolution actions validated per kind. Duplicates use `duplicate_reviews`, not a review item. A resolution is stored as an override input and replayed by every later run |

## 6. Duplicate review - REQ-ING-023

| Table | Columns | Constraints |
|---|---|---|
| `duplicate_reviews` | `id`, `request_id`, `classification` (`exact_duplicate`\|`new_edition`\|`new_work`\|`needs_review`), `candidates` jsonb (`[{book_id, title, evidence[]}]` exact matches first, then near matches), `state` (`pending`\|`resolved`), `decision?` (`create_new`\|`create_as_new_edition`\|`confirm_duplicate`\|`discard`), `target_book_id?`, `edition_label?`, `decided_by?`, `decided_at?`, `note?` | partial `UNIQUE(request_id) WHERE state='pending'`; classification `exact_duplicate` or `needs_review` always creates a pending row; `new_work` and `new_edition` also create one unless the evidence is complete (author present with confidence >= threshold, category present), in which case the request continues with the class recorded on the request; incomplete evidence downgrades the class to `needs_review` |

Classification is the rule in section 9; near matches never change the classification, they only appear in `candidates` for the human.

## 7. Build artifacts (candidates) - REQ-ING-024..026

| Table | Columns | Constraints |
|---|---|---|
| `build_artifacts` | `id`, `request_id`, `doc_hash`, `builder_version`, `book_id`, `epub_path`, `epub_sha256`, `cover_path`, `preview_path`, `audit_report` jsonb, `state` (`built`\|`audit_failed`\|`sent`\|`accepted`), `build_hash` (= sha256 of doc_hash + builder_version + book_id) | `UNIQUE(doc_hash, builder_version, book_id)`; `build_hash` is the catalog `Idempotency-Key`; the EPUB identifier is `urn:uuid:` UUIDv5 over `(book_id, version)`; a rebuild of the same inputs is byte-identical |

## 8. Sync, automation, credential status, events

| Table | Columns | Constraints |
|---|---|---|
| `sync_runs` | `id`, `kind` (`catalog`\|`incomplete`), `trigger` (`manual`\|`automation`), `phase` (`fetching`\|`reconciling`\|`creating_requests`\|`done`\|`failed`\|`cancelled`), `page_cursor`, `last_page_signature`, `pages_done`, `fetched_count`, `upserted_count`, `created_requests_count`, `create_cursor` jsonb, `consecutive_errors`, `error_budget`, `page_budget`, `listing_ok`, `requested_by`, `cancel_requested`, `started_at`, `finished_at?`, `last_error_code?` | partial `UNIQUE(kind) WHERE phase NOT IN ('done','failed','cancelled')`: one active run per kind, which also makes manual and automation runs mutually exclusive |
| `automation_settings` | `kind` PK (`catalog`\|`incomplete`), `enabled`, `interval` (`daily`\|`weekly`\|`biweekly`\|`monthly`), `time_of_day`, `timezone` (IANA name, required), `mode` (`pending`\|`all`), `max_attempts_per_request` (default 3), `max_requests_per_run` (default 50), `max_open_requests`, `page_delay_ms` (default 500), `next_due_at`, `last_started_at?`, `last_success_at?`, `last_failure_at?`, `cooldown_until?`, `active_run_id?`, `revision` | one default set in code and migration; disabled by default |
| `credential_status` | `source_host` PK, `state` (`missing`\|`valid`\|`expiring`\|`expired`), `expires_at?`, `file_fingerprint` (mtime + length of the secret file, never content), `last_checked_at?`, `last_ok_at?`, `last_failure_code?` | contains no secret. The cookie itself lives only in a read-only secret file mounted into both ingestion containers (D-30); it is never in a row, argv, log, response or the browser (REQ-ING-011) |
| `events` | `id` bigserial, `type`, `request_id?`, `payload`, `created_at` | outbox for the console, written in the transaction of the change; `NOTIFY ingestion_events` fires after insert; retained 7 days |
| `event_cursors` | `source` PK, `last_id` | cursor into catalog events |

## 9. Bengali normalization and matching - REQ-ING-022, REQ-ING-023

Shared crate `bn-text` (ingestion and catalog use one implementation; placement in the workspace is a build detail). It fixes two legacy defects (X1-046): punctuation was deleted instead of separating words, and word lists lost their vowel signs.

| Function | Steps | Use |
|---|---|---|
| `exact_key(s)` | (1) Unicode NFC (nukta letters ড় ঢ় য় converge to base + nukta); (2) remove ZWJ and ZWNJ; (3) fold Bengali digits ০-৯ to 0-9; (4) lowercase Latin; (5) every character that is not a letter, number or combining mark (hyphen, danda "।", quotes, brackets) becomes one space; (6) collapse and trim. Vowel signs, hasanta and nukta are always kept | identity of titles, names, categories, editions; the only key used for an automatic decision |
| `loose_key(s)` | `exact_key` then fold spelling variants: ী to ি, ূ to ু, ণ to ন, শ and ষ to স, ৎ to ত | listing near matches for a human and search recall; never an automatic decision |
| `tokens(s)` | split `exact_key` on spaces | whole-token comparison |

Rules: idempotent; the key stores `normalizer_version`; no word list is compared by substring, only by whole-token equality after `exact_key`.

Lexicon (the tested replacement of the legacy lists, owned by [rulesets](rulesets/README.md)): UTF-8 NFC files with full vowel signs and viram, one token or phrase per line, with at least one positive and one negative example per entry (the negative is a longer word that contains the entry, such as প্রথমা versus প্রথম). CI fails when an entry is not NFC, contains ZWJ/ZWNJ, or differs from its approved spelling in the golden file. Author-role words (লেখক, অনুবাদক, সম্পাদক, সংকলক, রূপান্তর, মূল, রচনা), ordinals (প্রথম, দ্বিতীয়, তৃতীয়) and honorifics (ডক্টর, ডঃ, ড., অধ্যাপক, জনাব, মৌলভী, মো:) are examples; ordinals map to digits only as a whole token; honorifics go to a separate `honorific` field and never cause rejection.

Author parsing: the raw string is always kept. Split on `, ; |` and newline, and on " ও ", " and ", " & " only when every part passes the structural check (at least 2 letters, no digits, at most 8 words). A part that fails the check stays one name with low confidence. A missing or low-confidence author makes the duplicate result `needs_review`, never "new book". Latin and Bengali spellings of one person connect only through catalog agent aliases.

### Duplicate rule (decision procedure)

Two books are the same only on **exact normalized title key + author + category + edition**. The first decisive step wins.

1. **Source identity**: `url_key` equals a catalog `book_sources` key or an active request: `exact_duplicate` (the operator may `confirm_duplicate` or `discard`; reprocessing an existing book is the `reprocess` action, not a duplicate decision).
2. **Exact key**: `title_key` equals a catalog book's title key; then compare by `exact_key` set equality or overlap:

| Author overlap | Category overlap | Edition (publisher + label) | Translators | Class |
|---|---|---|---|---|
| >= 1 shared | >= 1 shared | same, or both absent | equal sets | `exact_duplicate` |
| >= 1 shared | any | differs | equal sets | `new_edition` |
| both sides have authors, none shared | any | any | any | `new_work` |
| >= 1 shared | any | any | sets differ | `needs_review` (README OPEN-9) |
| missing or low confidence on either side | any | any | any | `needs_review` |

3. Series and volume digits are part of the key ("খণ্ড ১" never matches "খণ্ড ১০"); a collection never matches its component by containment.
4. **Near matches** (equal `loose_key` with different `exact_key`; or equal title key not already an exact candidate) are listed in `candidates` with evidence side by side. There is no similarity threshold and no automatic action on them.
5. A match against a soft-deleted catalog book is `needs_review` (`matches_deleted_book`); there is no resurrection by title.
6. No candidate at all with complete author and category: `new_work`.

The comparison runs over catalog rows through `POST /internal/books/match` (pure over catalog data; open point C-3); ingestion supplies the keys and owns the review state. An exact duplicate is refused for `create_new`.

## 10. Validation (curated document) - REQ-ING-018, REQ-ING-019

Each check is a typed issue: missing title, missing body, missing canonical URL, duplicate section paths, dead TOC leaves, source chrome in body, non-200 or sentinel-title pages (a bot-block page served with 200), empty chapter above the single configured threshold (one constant shared by classification and build), conservation, completeness (every TOC leaf fetched or recorded empty at source, no percentage tolerance), language set (detected once, overridable). A limit that caused an omission is an error, never a silent drop. Severity `error` yields `invalid` or `needs_review` by kind; `forced` may proceed past `needs_review` only, never past the audit gate, unfetched leaves without `empty_at_source` evidence, or a pending duplicate review.

## 11. Retention - REQ-ING-034

| Data | Rule |
|---|---|
| Raw scraped pages and images | 30 days after fetch, or earlier 7 days after the request is terminal (provisional) |
| `job_log`, `request_attempts` | `job_log` 30 days (provisional); attempts bounded per request |
| `events` outbox | 7 days (older `Last-Event-ID` gets `reset` and a snapshot) |
| Build files | candidate files of superseded builds removed on terminal states; the files of the previous published version are kept until the next version is published (catalog owns published files) |
| `audit_log` | follows the global audit retention (1 year, D-40) |

Retention is a `retention` job (daily, idempotent), never a handler.

## 12. Value types

`UrlKey`, `ExactKey`, `LooseKey`, `BlockId`, `Sha256`, `RulesetVersion`, `Confidence(0.0..=1.0)`, `Evidence{block_ids, extractor, rule_id, confidence}`, `ReasonCode` (closed enum), `SafeHtml`, `JobError`, `Lease{owner, epoch}`.
