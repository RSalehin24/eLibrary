# Open decisions (need the owner's answer)

Status: DRAFT

Each decision blocks a named gate. A recommendation is given so a "yes" is enough. Answered decisions move to [DECISIONS](../DECISIONS.md). Questions are asked as selectable questions (see CLAUDE.md).

| ID | Decision | Options | Recommendation | Blocks |
|---|---|---|---|---|
| OD-01 | PostgreSQL FTS quality for Bengali (ADR-0020 replaced the embedded engine) | (a) FTS plus normalization plus `pg_trgm` for typos, confirmed by a spike on the gold corpus; (b) re-open an embedded engine | (a): matches the brief, no extra component; spike confirms thresholds | search design gate |
| OD-02 | Annotation anchors (ADR-0015) refer to a reading copy `(book_id, version)` instead of an artifact set; re-anchoring on `book.version_changed` | (a) keep re-anchoring, adapt to reading copies; (b) drop re-anchoring and mark annotations stale on a new version | (a): protects user highlights; cost is small at this scale | reader design gate |
| OD-03 | Models for the pull-based outbox (`Outbox.tla` models push delivery) | (a) adapt the model to cursor pull; (b) drop the model | (a): the idempotency and duplicate-tolerance claims depend on it | correctness gate |
