# Public route table

Status: DRAFT

The complete set of externally reachable routes (INV-GWY-001). CI compares the gateway's compiled route set with this table. `Auth`: A = anonymous OK, S = session, M = management (witness required downstream).

| Prefix / path | Method(s) | Service | Auth | Cache |
|---|---|---|---|---|
| `/` , `/search`, `/books/{slug}`, `/categories`, `/series`, `/writers`, `/translators`, `/editors`, `/publishers`, `/login`, `/reset-password`, `/create-password`, `/about` | GET | web | A | public (SSR) |
| `/library`, `/read/{slug}`, `/notes`, `/profile`, `/shelf` | GET | web | S | none |
| `/admin/**` | GET | web | M | none |
| `/api/auth/login`, `/api/auth/totp/verify`, `/api/auth/logout`, `/api/auth/session`, `/api/auth/demo`, `/api/auth/password/forgot`, `/api/auth/links/**` | GET/POST | identity | A/S | none |
| `/api/me/**` (profile, password, totp) | GET/POST/PATCH | identity | S | none |
| `/api/admin/accounts/**` | * | identity | M | none |
| `/api/me/abilities`, `/api/admin/grants/**`, `/api/admin/default-policy`, `/api/admin/access/references`, `/api/reading/heartbeat` | * | access | S/M | none |
| `/api/catalog/search`, `/api/catalog/books`, `/api/catalog/books/{slug}`, `/api/catalog/books/{slug}/preview`, `/api/catalog/agents/**`, `/api/catalog/categories`, `/api/catalog/series/**` | GET | catalog | A | public 60 s |
| `/sitemap/{n}.xml`, `/robots.txt` | GET | catalog / web | A | public 1 h |
| `/api/admin/books/**`, `/api/admin/agents/**`, `/api/admin/exports/**`, `/api/admin/audit` | * | catalog | M | none |
| `/api/content/books/{id}/preview`, `/api/content/books/{id}/cover` | GET | content | A | public immutable |
| `/api/content/books/{id}/sections/**`, `/api/content/books/{id}/assets/**`, `/api/content/books/{id}/epub` | GET | content | capability | none |
| `/api/library/**` | * | library | S | none |
| `/api/admin/ingestion/**` | * | ingestion | M | none |
| `/api/admin/mail/**`, `/api/admin/kindle/**`, `/api/admin/templates/**` | * | notify | M | none |
| `/health/live`, `/health/ready` | GET | gateway | A | none |

Not exposed: any path containing `/internal/`, `/metrics`, service health detail, database or queue endpoints.

Rule: adding a public route requires a row here, a contract entry, a rate-limit class, and an authorization note.
