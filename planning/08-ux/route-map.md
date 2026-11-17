# Route map (single source of routes)

Status: DRAFT

`Auth`: A anonymous · S signed in · M management (ability needed). `SEO`: idx indexed · noidx · n/a. Every route implements all page states.

## Public

| Path | Page | Auth | Primary action | Data | SEO |
|---|---|---|---|---|---|
| `/` | Home: search box, featured/new/continue-reading (if signed in) | A | Search | catalog | idx |
| `/search?q&…` | Results with facets, sort | A | Open book | catalog | noidx (parameters) |
| `/books/{slug}` | Book page: cover, credits, summary, TOC, **preview**, actions | A | Read preview / Read | catalog + content | idx |
| `/books/{slug}/preview` | Full-screen preview reader (cut text) | A | Sign in to read | content | noidx until D-09 |
| `/categories`, `/categories/{code}` | Taxonomy browse | A | Open book | catalog | idx |
| `/series`, `/series/{id}` | Ordered series | A | | catalog | idx |
| `/writers`, `/translators`, `/editors`, `/publishers`, `/{role}/{code}` | Agent lists and pages | A | | catalog | idx |
| `/about` | About | A | | static | idx |

## Account

| Path | Page | Auth | Primary action |
|---|---|---|---|
| `/login?next=` | Sign in (+ TOTP step) | A | Sign in (`next` validated same-origin) |
| `/demo` | Demo sign-in | A | Enter demo |
| `/reset-password`, `/reset-password/{token}`, `/create-password/{token}` | Password flows | A | Set password |
| `/library` | My library: continue reading, shelf, saved searches | S | Continue |
| `/read/{slug}` | Reader (full) | S | Read |
| `/notes` | Notes & highlights | S | Open location |
| `/profile` | Profile, Kindle addresses, language, theme | S | Save |
| `/profile/security` | Password, TOTP | S | Enable TOTP |
| `/sent` | Kindle sent history | S | |

## Admin (all `M`)

| Path | Page | Needs ability |
|---|---|---|
| `/admin` | Overview: queues, review count, health | any admin |
| `/admin/sources` | Sources workspace: health, catalog entries, schedules | ManageIngestion |
| `/admin/jobs`, `/admin/jobs/{id}` | Jobs workspace | ManageIngestion / Submit |
| `/admin/jobs/new` | Create from URL / EPUB | Submit |
| `/admin/review`, `/admin/review/{id}` | Review workspace | ManageIngestion |
| `/admin/reprocess`, `/admin/reprocess/{run}` | Diff runs | ManageIngestion |
| `/admin/catalog`, `/admin/catalog/{id}` | Catalog list/editor incl. non-published | EditMetadata |
| `/admin/agents`, `/admin/agents/{id}` | Agents, aliases, merge/split | EditMetadata |
| `/admin/exports` | Exports | EditMetadata |
| `/admin/accounts`, `/admin/accounts/{id}` | Accounts | ManageAccess |
| `/admin/access` | Grants, default policy | ManageAccess |
| `/admin/mail` | Mail/Kindle logs, templates | ManageAccess |
| `/admin/audit` | Audit | ManageAccess |
| `/admin/inventory` | Physical books | ViewInventory — **deferred to v1.1 (D-01); route not built in v1** |

## System

`/404`, `/403`, `/500`, `/offline`, `/maintenance` · `/health/*` (not a page) · `/sitemap/{n}.xml`, `/robots.txt`.

## Redirects from legacy (kept permanently)

`/books/{slug}` (same), `/library` legacy list → `/search`, `/writers|translators|editors|publishers|categories|series` (same), `/my-books` → `/library`, `/profile`, `/notes` (same), `/reader?…` → `/read/{slug}`, `/created-books` → `/library`, processing routes (`/catalog`, `/create`, `/on-hold`, `/incomplete`, `/multipage-toc`, `/reprocessing`) → `/admin/sources|jobs|review` accordingly, `/demo-login` → `/demo`.
