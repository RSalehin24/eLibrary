# catalog — API contract

Status: DRAFT · Source of truth: `contracts-catalog`

## Public (anonymous allowed)

| Method & path | Purpose | Notes |
|---|---|---|
| `GET /catalog/search?q&facets&sort&after` | search | keyset pagination, snapshot token |
| `GET /catalog/books?facets&sort&after` | browse list | Postgres-backed listing, same facet semantics |
| `GET /catalog/books/{slug}` | book page data | 301 for old slugs; Published only; includes `abilities_hint` for the viewer when authenticated |
| `GET /catalog/books/{slug}/preview` | preview document | proxied from content `PreviewArtifact` |
| `GET /catalog/agents?role&q&after` , `GET /catalog/agents/{code}` | writers/translators/editors/publishers pages | |
| `GET /catalog/categories`, `/series`, `/series/{id}` | taxonomy browse | ordered series |
| `GET /sitemap/{n}.xml` | sitemap batches | Published only |

## Authenticated / admin

| Method & path | Auth | Purpose |
|---|---|---|
| `PATCH /admin/books/{id}` | `EditMetadata` | field overrides with `If-Match: revision` |
| `POST /admin/books/{id}/archive` `/restore` `/delete` | `EditMetadata` | lifecycle |
| `POST /admin/agents/merge`, `POST /admin/agents/{id}/split` | `EditMetadata` | with preview of affected credits |
| `POST /admin/books/{id}/link-edition` | `EditMetadata` | attach to a Work |
| `GET /admin/books` (+filters incl. state/source) | `EditMetadata` | includes non-published |
| `POST /admin/exports` → `GET /admin/exports/{id}` | `EditMetadata` | CSV/XLSX/PDF jobs with row cap |
| `GET /admin/audit?…` | `ManageAccess` | audit viewer |

## Internal

| Route | Caller | Purpose |
|---|---|---|
| `PUT /internal/books/by-source/{source_key}` | ingestion | upsert Draft (idempotent) |
| `POST /internal/books/{id}/publish` | ingestion | publish with `artifact_set_id`, `expected_revision` |
| `POST /internal/agents/resolve` | ingestion | candidates for names with scores; **no auto-create** |
| `POST /internal/duplicates/classify` | ingestion | five-case classification for a key tuple |
| `GET /internal/books/{id}/facts` | access/library | state, categories, writers |
| `GET /internal/contract` | all | handshake |

## Behavior guarantees

- Public GETs are cacheable (`ETag`, `Cache-Control: public, max-age=60, stale-while-revalidate=300`); responses vary only by `Accept-Language`.
- A Draft/Archived/Deleted book returns 404 on public routes (indistinguishable from nonexistent).
