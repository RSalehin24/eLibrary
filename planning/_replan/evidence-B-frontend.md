# Evidence B — legacy frontend (React)

Status: DRAFT

Source: read-only survey of `archive/app/frontend/src` (subagent report, facts only; not independently re-verified).

- **Routes:** public login/demo/password-reset; browse (`/home`, `/library`, `/categories`, `/series`, writers/translators/editors/publishers all one `WriterPage`, `/books/:slug`); personal (`/my-books`, `/kindle-sent`, `/notes`, `/profile`, `/reader`); admin (`/access`, `/manual-books`); six processing screens (`/catalog`, `/create`, `/on-hold`, `/incomplete`, `/multipage-toc`, `/reprocessing`); many legacy redirect aliases.
- **API groups called:** `/auth/*` (login, 2FA, password reset, users), `/access/*` (grants, bookmarks, send-to-kindle), `/catalog/*` (books, agents, series, categories, manual-books, metadata-reviews, export), `/processing/*` + `/ingestion/jobs/*` (SSE streams), reader launch/manifest/assets.
- **Roles:** superuser / staff / capabilities (`processing:manage`, `metadata:edit`, `source_records:view`, `send:kindle`, `access:manage`, `admin:full_control`). Only authentication and 2FA are enforced at route level; capability gating is in nav and pages (processing/access URLs render for any signed-in user unless the page or backend blocks them — unverified).
- **Responsive:** plain CSS, ~12.5k lines in ~30 files split by breakpoint (max-width 640/768/980 px etc.), JS mobile nav panel, reader topbar hide button; vendored reader has its own responsive CSS.
- **Theming:** light/dark/system, default dark; `dark-mode.css` 1,806 lines of overrides.
- **i18n:** none. Strings hard-coded English, `lang="en"`; Bengali only via font stack and a few matched strings.
- **Pain points:** cascade-by-file-order overrides, fix-up files, `!important` in 16 files, duplicated skeleton CSS, four contributor routes on one page, overlapping book-list pages (Home/Library/CreatedBooks/ManualBooks) with separate export helpers, large pages (Reprocessing 709, Notes 694, ManualBooks 680 lines), two nav helpers that disagree.

Implications for the service split: a physical/manual-books module and Kindle sending exist as features; the admin surface is dominated by processing; the reader is launched from a separate token flow.
