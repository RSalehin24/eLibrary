# ingestion — domain model

Status: DRAFT

## Persistent entities

| Entity | Key fields | Constraints |
|---|---|---|
| `Source` | `id`, `kind` (LearnDash\|Epub), `host`, `adapter_version`, `politeness{rps, concurrency}`, `enabled` | one row per source site |
| `SourceCatalogEntry` | `id`, `source_id`, `canonical_url`, `title_hint`, `author_hint`, `series_hint`, `category_hint`, `seen_at`, `state` (Listed\|Known\|Imported\|Incomplete\|Ignored) | `UNIQUE(source_id, canonical_url)` |
| `Snapshot` | `id`, `source_key`, `taken_at`, `manifest_hash`, `page_count`, `completeness_evidence_hash` | write-once; blobs content-addressed; `source_key` = hash of canonical URL |
| `SnapshotPage` | `snapshot_id`, `url`, `kind` (landing\|toc_page\|lesson\|topic), `http_status`, `body_hash`, `fetched_at`, `locked?` | |
| `Ruleset` | `version` (semver), `hash`, `status` (Candidate\|Promoted\|Retired), `gold_report_hash`, `normalizer_version` | immutable once Promoted |
| `Job` | `id`, `source_key`, `kind` (Create\|Reprocess\|Sync), `state`, `epoch`, `attempts`, `lease_until`, `step`, `cursor`, `ruleset_version`, `requested_by`, `created_at` | partial unique: one active job per `source_key` (INV-ING-010) |
| `JobStepResult` | `job_id`, `step`, `epoch`, `output_hash`, `evidence_hash` | idempotent key `(job_id, step, epoch)` |
| `DocumentDraft` | `id`, `job_id`, `doc_hash`, `snapshot_id`, `ruleset_version`, `validation_status`, `confidence_summary` | |
| `ReviewItem` | `id`, `job_id`, `kind`, `payload`, `state` (Open\|Resolved\|Dismissed), `resolution`, `resolved_by` | kinds below |
| `Schedule` | `id`, `kind` (CatalogSync\|IncompleteRecheck\|Canary), `frequency`, `next_run`, `last_run`, `enabled`, `revision` | |
| `GoldReport` | `ruleset_version`, `metrics`, `per_book`, `generated_at` | |
| `AuditEntry` | INSERT-only | |

## Review item kinds (replaces on-hold / failed / duplicate pages)

| Kind | Raised when | Resolution actions |
|---|---|---|
| `IncompleteSource` | a TOC leaf is neither fetched nor recorded empty | Retry fetch · Mark leaf empty-at-source (with evidence) · Cancel |
| `LockedSource` | source returned a locked placeholder | Cancel · Retry later · (D-03) provide sanctioned access |
| `LowConfidenceEntity` | entity confidence below threshold or competing candidates | Choose candidate · Type value · Mark absent |
| `AmbiguousStructure` | inferred chapters below threshold / TOC inconsistent | Accept inferred · Adjust boundaries (UI) · Cancel |
| `DuplicateCandidate` | policy returned NeedsReview or non-exact match | Link as new edition · Link as new translation · Treat as new work · Refuse duplicate |
| `ConservationFailure` | validator found unaccounted blocks (bug) | Escalate (creates invariant_violation) |
| `SourceDrift` | structural fingerprint changed | Pause adapter · Accept new fingerprint after canary pass |
| `BuildFailed` | content build failed | Retry · Inspect |

## Value types

`BlockId`, `SourceKey`, `SnapshotHash`, `RulesetVersion`, `Confidence(0.0..=1.0)`, `Evidence{block_ids, extractor, rule_id, confidence}`, `ReasonCode` (closed enum for drops/reviews).
