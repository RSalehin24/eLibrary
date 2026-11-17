# ingestion — API contract

Status: DRAFT · Source of truth: `contracts-ingestion`

All routes are admin routes behind `Allow<…>` witnesses.

| Method & path | Action | Purpose |
|---|---|---|
| `POST /admin/ingestion/jobs` | `Submit` | create from source URL(s) or request EPUB upload slot; idempotent per `source_key` (returns the active job if present) |
| `POST /admin/ingestion/uploads` | `Submit` | EPUB intake (streamed, size-bounded); returns job |
| `GET /admin/ingestion/jobs?state&kind&q&after` | `ManageIngestion` | Jobs workspace list |
| `GET /admin/ingestion/jobs/{id}` | `ManageIngestion` | detail: steps, evidence summary, logs (paged) |
| `POST /admin/ingestion/jobs/{id}/cancel` `/retry` | `ManageIngestion` | allowed transitions only |
| `GET /admin/ingestion/jobs/stream` | `ManageIngestion` | server-sent events of state changes (replay from `Last-Event-ID`) |
| `GET /admin/ingestion/sources`, `PATCH …/{id}` | `ManageIngestion` | Sources workspace: politeness, enable/disable |
| `GET /admin/ingestion/catalog?state&q&after` | `ManageIngestion` | source catalog entries |
| `POST /admin/ingestion/catalog/refresh` | `ManageIngestion` | start/stop catalog sync (job kind Sync) |
| `POST /admin/ingestion/catalog/import` | `ManageIngestion` | create jobs for selected entries (bounded batch ≤ 200) |
| `GET /admin/ingestion/schedules`, `PATCH …/{id}` | `ManageIngestion` | schedules (`If-Match` revision) |
| `GET /admin/ingestion/review?kind&state&after` | `ManageIngestion` | Review workspace |
| `GET /admin/ingestion/review/{id}` | `ManageIngestion` | item with side-by-side evidence (blocks highlighted) |
| `POST /admin/ingestion/review/{id}/resolve` | `ManageIngestion` | `{action, payload}` validated per kind |
| `POST /admin/ingestion/reprocess` | `ManageIngestion` | for book ids/filters with a ruleset version → creates a **diff run** (no publish) |
| `GET /admin/ingestion/reprocess/{run}/diff` | `ManageIngestion` | structured diff |
| `POST /admin/ingestion/reprocess/{run}/apply` | `ManageIngestion` | apply selected books after reviewing diff |
| `GET /admin/ingestion/rulesets`, `GET …/{v}/report` | `ManageIngestion` | versions and gold reports |

## Internal

`POST /internal/events/{type}` inboxes (e.g. `ArtifactSetSealed`, `BookPublished` for saga continuation) · `GET /internal/contract`.

## SSE events (job stream)

`{job_id, state, step, progress{done,total}, review_open_count, at}`; delivery is best-effort display only; state of record is `GET`.
