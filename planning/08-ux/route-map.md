# Route map (single source of routes)

Status: DRAFT

The only source of routes and links (REQ-WEB-004). Every internal link is generated from the typed route table that mirrors this file; a link checker fails on a dead link and unknown paths show NotFound. Every route has an **Auth** and a **Service owner**.

- **Auth**: `A` anonymous allowed · `S` signed-in session · or the scope needed (`read`, `operate`, `manage_catalog`, `manage_users`; scopes from [REQ-IDN-011](../02-requirements/idn-identity.md)). The UI hides what the capability set denies and a `CanMatch` guard refuses the URL; the server decides ([principles](principles.md) 9).
- **Service owner**: the backend service that owns the data and the decision for the route (`web` alone means the route has no backend data). The `web` container renders every route.
- **Render**: `SSR` server-rendered and hydrated (D-39) · `CSR` client after sign-in. **SEO**: `idx` indexable metadata · `noidx`.
- Every route implements all page states ([states](screens/states.md)). The 401/403 behaviour is in [web README](../05-services/web/README.md).

## Public

| Path | Screen | Auth | Service owner | Render / SEO | Primary action |
|---|---|---|---|---|---|
| `/` | redirect to `/library` | A | web | SSR, 301 | none |
| `/library` | [Library](screens/library.md) browse and search (metadata only) | A | catalog | SSR, idx (canonical, no params) | Open a book |
| `/library?q&facet&writer&series&category&sort&view` | Library with search, facets, sort, card/list | A | catalog | SSR, noidx (canonical to `/library`) | Open a book |
| `/books/:slug` | [Book detail](screens/book-detail.md) tab Overview (`?tab=overview` default) | A | catalog | SSR, idx; preview text never in HTML | Read / Sign in to read |
| `/books/:slug?tab=metadata` | Book detail, Metadata (read-only; edit and versions for `manage_catalog`) | A (edit: `manage_catalog`) | catalog | SSR, noidx | none (edit: Save) |
| `/books/:slug?tab=files` | Book detail, Files (download, Kindle, delivery status) | S (`browse`; actions by scope) | catalog | CSR, noidx | Download / Send to Kindle |
| `/robots.txt`, `/sitemap.xml` | not pages (crawler files from published slugs) | A | web (data: catalog) | SSR | none |
| `**` | [NotFound](screens/states.md) | A | web | SSR, 404, noidx | Go to Library |

Old slugs keep working: catalog answers a permanent redirect for a renamed slug (REQ-CAT-005) and the web follows it.

## Authentication (one card shell, [Sign-in](screens/sign-in.md))

| Path | Step | Auth | Service owner | Primary action |
|---|---|---|---|---|
| `/sign-in?next=` | email and password | A (a signed-in user is sent on to `next`) | identity | Continue (`next` validated same-origin and against the route table) |
| `/sign-in/totp` | verification code (pending session) | A with pending session | identity | Verify |
| `/sign-in/totp-setup` | forced TOTP enrolment (**OPEN U-2**) | S (pending enrolment) | identity | Verify and continue |
| `/reset-password` | request a link | A | identity | Send link |
| `/reset-password/confirm` | set a new password (token handling **OPEN U-1**) | A | identity | Set password |
| `/invite` | accept an invitation and set a password (token handling **OPEN U-1**) | A | identity | Set password |

## Signed in

| Path | Screen | Auth | Service owner | Render / SEO | Primary action |
|---|---|---|---|---|---|
| `/library?scope=mine` | Library, My Books chip | S (`browse`) | catalog | CSR, noidx | Open a book |
| `/library?scope=kindle` | Library, Sent to Kindle chip (cross-book list **OPEN U-5**) | S (`kindle`) | catalog | CSR, noidx | Open a book |
| `/books/:slug/read` (`?at=` location) | [Reader](screens/reader.md) | `read` | reader (ticket: identity) | CSR, noidx | Read |
| `/notes` | [Notes](screens/notes.md) across books (placement **OPEN U-7**) | S | reader | CSR, noidx | Open location |
| `/settings` | [Settings](screens/settings.md): section list (compact), first section (larger) | S | identity (reader preferences: reader) | CSR | Save |
| `/settings/profile` | name, language, profile image | S | identity | CSR | Save |
| `/settings/appearance` | theme System/Light/Dark, language | S (theme also for visitors in the top bar) | web (persisted locally and in cookie) | CSR | Choose |
| `/settings/security` | password, TOTP stepper (re-authentication) | S | identity | CSR | Change password / Enable TOTP |
| `/settings/kindle` | Kindle addresses (up to 5) | `kindle` | identity | CSR | Save |
| `/settings/data` | export own data | S | identity, reader | CSR | Export |

## Operator and catalog management

| Path | Screen | Auth | Service owner | Primary action |
|---|---|---|---|---|
| `/import` | redirect to `/import/requests` | `operate` | web | none |
| `/import/mirror` | [Import](screens/import-workspace.md): catalog sync, source listing, credential status, automation | `operate` | ingestion | Start sync |
| `/import/requests` | requests table and create | `operate` | ingestion | New request |
| `/import/requests/:id` | request detail: document summary, builds, diff, log | `operate` | ingestion | Retry / Reprocess |
| `/import/review` | requests needing review | `operate` | ingestion | Open review |
| `/import/review/:requestId` | resolve REVIEW items | `operate` | ingestion | Resolve |
| `/import/duplicates` | open duplicate reviews | `operate` | ingestion | Open review |
| `/import/duplicates/:id` | resolve one duplicate review | `operate` | ingestion (match data: catalog) | Resolve |
| `/import/jobs` | jobs with live progress | `operate` | ingestion | none (Cancel/Retry per row) |
| `/import/jobs/:id` | job attempts and logs | `operate` | ingestion | Retry |
| `/import/activity` | operator-action audit | `operate` | ingestion | none |
| `/manage` | [Catalog management](screens/catalog-management.md): all states (published, archived, deleted), CSV export | `manage_catalog` | catalog | Edit |
| `/manage/contributors` | contributors, aliases, merge, split | `manage_catalog` | catalog | Merge |

Editing, versions, unpublish and delete happen in Book detail, tab Metadata (one detail screen, no second book page).

## Administration

| Path | Screen | Auth | Service owner | Primary action |
|---|---|---|---|---|
| `/admin` | redirect to `/admin/users` | `manage_users` | web | none |
| `/admin/users` | [Users and access](screens/users-access.md) list, invite | `manage_users` | identity | Invite |
| `/admin/users/:id` | user detail (drawer on expanded, full screen on compact): status, role, grants, read-once | `manage_users` | identity | Add grant |
| `/admin/audit` | [Audit viewer](screens/audit.md) | `manage_users` (**OPEN C-1**) | identity | Filter |

## Navigation per window class

One nav config; the items below are shown only when the capability set allows them. Destinations: Library · Notes · Import (`operate`) · Manage (`manage_catalog`) · Users (`manage_users`, with Audit as a tab) · Settings. Visitors see Library and Sign in.

| Class | Pattern |
|---|---|
| compact | top app bar + bottom navigation bar (at most 5; a sixth destination moves into a "More" item) |
| medium | navigation rail |
| expanded | navigation rail, labels beside icons on demand |
| large | permanent navigation drawer |

The reader is full-bleed on every class and hides the app navigation.

## Not routes (states and non-pages)

`Forbidden`, `Offline`, `Failed`, `Loading`, `Empty` are page states rendered in place ([states](screens/states.md)); there is no `/403`, `/500` or `/offline` URL. Health, internal and `/api/*` paths are never web routes. There is no demo route (D-35), no manual upload route (D-42) and no inventory route (D-01).

## Legacy URLs

The legacy app is not migrated (D-32); no legacy-redirect table is kept. Catalog slugs are re-created by ingestion, so legacy book URLs are not guaranteed to resolve (**OPEN U-8**: whether to redirect anything).
