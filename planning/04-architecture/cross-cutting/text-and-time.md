# Text, Unicode and time

Status: DRAFT

## Text pipeline (`domain-text`)

Single implementation of normalization used by ingestion, catalog, search and library.

| Step | Rule |
|---|---|
| 1 | Decode UTF-8 strictly; reject invalid sequences at the edge |
| 2 | Unicode NFC for storage and display text |
| 3 | For matching keys: NFKC, case-fold, collapse whitespace, strip punctuation (keep letters, marks, digits) |
| 4 | Fold digits: Bengali ↔ ASCII to ASCII for keys only |
| 5 | ZWJ/ZWNJ: preserved in display text; removed in matching keys |
| 6 | Spelling-variant folding for matching keys (table, versioned): ই/ঈ, উ/ঊ (and signs ি/ী, ু/ূ), শ/ষ/স, ন/ণ, য়/য with nukta forms, ্য variants — applied **only** in the `fuzzy_key`, never in `exact_key` |
| 7 | Keys carry the normalizer version; changing it triggers a reindex job |

Types: `DisplayText` (NFC), `ExactKey`, `FuzzyKey`, all non-interchangeable. Property tests:
idempotency, NFC stability, round-trip of display text, folding never lengthens keys.

## Collation

CLDR `bn` collation (via ICU4X `icu_collator`) for sorting; sort keys stored as `bytea` where
lists need DB-side ordering. A single comparator is shared between catalog listing and search.

## Time

- Stored: `timestamptz` UTC. Domain code receives `Instant` from `Clock`.
- Displayed: viewer zone, default Asia/Dhaka (UTC+6, no DST), locale-aware digits (bn uses Bengali digits in UI chrome, ASCII in data tables and exports unless chosen).
- Durations and TTLs are `Duration` newtypes; never raw integers of unknown unit.
