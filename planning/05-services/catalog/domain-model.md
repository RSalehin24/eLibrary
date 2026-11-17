# catalog — domain model

Status: DRAFT

## Bibliographic model (see [entities design](../ingestion/entities/README.md))

```
Work ──< Translation? ──< Book (published edition) >── Credit >── Agent
                              │
                              ├── BookSeries(series, ordinal)
                              └── BookCategory(category)
```

| Entity | Key fields | Constraints |
|---|---|---|
| `Work` | `id`, `canonical_title`, `original_language` | groups editions/translations (replaces legacy `BookGroup`) |
| `Book` | `id`, `work_id`, `code`, `slug`, `title`, `subtitle?`, `language`, `edition_label?`, `publisher_agent_id?`, `first_published?`, `summary?`, `state`, `active_artifact_set_id?`, `source_key?`, `revision` | `UNIQUE(code)`, `UNIQUE(slug)`, `UNIQUE(source_key)` where present; Published ⇒ credit rule (INV-CAT-002) and `active_artifact_set_id` not null |
| `Agent` | `id`, `kind` (Person\|Organization), `display_name`, `code`, `revision` | identity is the id only |
| `AgentAlias` | `agent_id`, `alias`, `script` (Bengali\|Latin), `exact_key`, `fuzzy_key` | `UNIQUE(exact_key, agent_id)`; alias lookup feeds search |
| `Credit` | `book_id`, `agent_id`, `role`, `ordinal`, `raw_value?` | roles: writer, translator, editor, compiler, illustrator, cover_artist, publisher |
| `Series` / `BookSeries` | name, ordinal (decimal) | `UNIQUE(series_id, ordinal)` when ordinal present |
| `Category` / `BookCategory` | name, `code`, optional parent (tree, depth ≤ 3) | acyclic (check constraint via path) |
| `FieldOverride` | `book_id`, `field`, `value`, `set_by`, `set_at`, `source_value_hash` | wins over source value (INV-CAT-004); flagged `stale` when the source value later changes |
| `SlugRedirect` | `old_slug` → `book_id` | permanent |
| `MergeRecord` | `from_agent`, `into_agent`, `moved_credits[]`, `at`, `by` | enables split/undo |
| `book_projection_for_search` | derived | rebuildable |

## Provenance

Every metadata field stores `(value, provenance)` where provenance ∈ {`source(job_id, evidence_id)`, `admin(account, at)`}. Re-ingestion updates `source` values only; `admin` values are overrides.

## Invariants (selected)

INV-CAT-001 (state graph), 002 (credit rule), 003 (stable ids/slugs), 004 (override and revision), 005 (agent identity), 006 (duplicate classification), 007 (count = results), 008 (export = list). DB-enforced where possible; the rest by property tests.
