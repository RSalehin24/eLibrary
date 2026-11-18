# Frontend

This folder contains the React and Vite application code.

## Local Development

Use the repo-level guide in [docs/operations/local-development.md](../../docs/operations/local-development.md). The preferred workflow runs the frontend through the Docker development overlay with Vite hot reload.

## Runtime Notes

- App code: `app/frontend/src/`
- Browser tests: `tests/frontend/e2e/`
- Browser config: `tests/frontend/playwright.config.js`
- Vite config: `app/frontend/vite.config.js`

## Routes

### Public Routes

| Route                      | Page              | Notes                                        |
| -------------------------- | ----------------- | -------------------------------------------- |
| `/login`                   | Login             | Email/password sign-in                       |
| `/reset-password`          | Password Reset    | Self-service password reset request          |
| `/reset-password/confirm`  | Password Link     | Password reset link confirmation             |
| `/create-password`         | Password Creation | Invite-link password setup                   |

### Protected Routes

| Route               | Page               | Notes                                                           |
| ------------------- | ------------------ | --------------------------------------------------------------- |
| `/`                 | Home Redirect      | Redirects to user-specific home path                            |
| `/home`             | Home               | Landing dashboard                                               |
| `/library`          | Library            | Searchable book catalog                                         |
| `/categories`       | Categories         | Browse by category                                              |
| `/series`           | Series             | Browse by series                                                |
| `/writers`          | Writers            | Browse by writer/translator/editor                              |
| `/translators`      | Translators        | Browse by translator (reuses WriterPage)                        |
| `/editors`          | Editors            | Browse by editor (reuses WriterPage)                            |
| `/publishers`       | Publishers         | Browse by publisher (reuses WriterPage)                         |
| `/books/:slug`      | Book Detail        | Metadata, EPUB/HTML actions, Kindle delivery                    |
| `/reader`           | Reader             | In-browser HTML reader                                          |
| `/catalog`          | Catalog Processing | Source catalog sync, automation, catalog records                |
| `/create`           | Create Processing  | Book creation pipeline: requests → queue → processing → created |
| `/on-hold`          | On Hold            | Paused, failed, duplicate, and deleted requests                 |
| `/incomplete`       | Incomplete         | Incomplete book automation and resolved records                 |
| `/multipage-toc`    | Multi-Page TOC     | Multi-page table of contents processing                         |
| `/reprocessing`     | Reprocessing       | Book reprocessing queue                                         |
| `/manual-books`     | Manual Books       | Operator-created books without a source URL                     |
| `/my-books`         | My Books           | Books owned or created by the current user                      |
| `/kindle-sent`      | Kindle Sent        | Books sent to Kindle                                            |
| `/access`           | Users & Access     | User management and per-book permission grants                  |
| `/profile`          | Profile            | User profile and settings                                       |
| `/notes`            | Notes              | Saved reading notes                                             |
| `/two-factor-setup` | TOTP Setup         | Forced two-factor authentication setup gate                     |

### Redirect-Only Routes

| Route                        | Redirects To   | Notes              |
| ---------------------------- | -------------- | ------------------ |
| `/created-books`             | `/my-books`    | Legacy alias       |
| `/processing`                | `/catalog`     | Legacy alias       |
| `/processing-catalog-books`  | `/catalog`     | Legacy alias       |
| `/processing-automation`     | `/catalog`     | Legacy alias       |
| `/processing-my-requests`    | `/create`      | Legacy alias       |
| `/processing-failed-requests`| `/on-hold`     | Legacy alias       |
| `/processing-duplicate-requests` | `/on-hold` | Legacy alias       |
| `/processing-incomplete-check` | `/incomplete` | Legacy alias     |
| `/queue`                     | `/create`      | Legacy alias       |
| `/compilers`                 | `/editors`     | Alias              |

Any unmatched path redirects to `/`.

## Container Targets

- [local/docker/frontend.Dockerfile](../../local/docker/frontend.Dockerfile): local Vite development image
- [deploy/docker/frontend.Dockerfile](../../deploy/docker/frontend.Dockerfile): production build and Nginx runtime image
