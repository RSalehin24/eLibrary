# Catalog management

Status: DRAFT

**Purpose**: operator and admin view of every book in every state: published, archived and deleted books, CSV export, contributors (aliases, merge, split). Edit, unpublish and delete are manual actions under `manage_catalog`; there is no approval queue because publishing is automatic (D-49, which resolves U-3 and the admin-without-`operate` conflict).
**Primary action**: Edit (open the book's Metadata tab).
**Routes**: `/manage`, `/manage/contributors`. **Auth**: `manage_catalog`. **Service owner**: catalog. Editing a book is the Metadata tab of [Book detail](book-detail.md) (one detail screen, no second book page). Flow: [automatic publish](../flows/auto-publish.md).

## Data

`GET /manage/books` (state, q, facets, paged), `GET /manage/books/export.csv` (scope **OPEN O-4**), `GET /manage/agents`, `GET /manage/agents/{id}`, `POST /manage/agents/{id}/aliases`, `POST /manage/agents/merge`, `POST /manage/agents/{id}/split` ([catalog contract](../../07-contracts/http/catalog.md)).

## Content

- **Books** (`/manage`): state chips as filter (Published, Archived, Deleted), search, the shared table component, row opens `/books/:slug?tab=metadata`. Rows show the current version, build hash (short) and published time. Export CSV applies the current filter (streamed; cells starting `=`, `+`, `-`, `@` are neutralised by the server; the 5,000-row cap shows a clear message `export_too_large`).
- **Contributors** (`/manage/contributors`): one list for writers, translators, editors, compilers, publishers (a role filter, not four pages). Detail drawer: aliases (Bengali and Latin forms), credits, Merge (choose the kept record; preview of affected credits; confirm), Split (reverses). Audited and reversible.

## States

| State | Behaviour |
|---|---|
| Loading | skeleton rows |
| Empty | "No books match" |
| Ready | table |
| Error | banner with Retry; `conflict` on merge explains |
| Forbidden | no `manage_catalog`: nav item absent, route shows forbidden |
| NotFound | missing agent or book |
| Offline | banner; actions disabled |

## Layout

Same table pattern as Import: compact list of cards, medium compact table with sheet, expanded and large dense table with drawer.

## Copy keys

| Key | en | bn |
|---|---|---|
| `ux.manage.title` | Manage catalog | ক্যাটালগ ব্যবস্থাপনা |
| `ux.manage.export` | Export CSV | CSV এক্সপোর্ট |
| `ux.manage.contributors` | Contributors | অবদানকারী |
| `ux.manage.merge` | Merge | একত্র করুন |
| `ux.manage.merge.confirm` | Merge {n} records into “{name}”? | {n}টি রেকর্ড “{name}”-এ একত্র করবেন? |

Analytics: none. Accessibility: as the table pattern in [Import](import-workspace.md); merge preview is a text list, not colour coding.
