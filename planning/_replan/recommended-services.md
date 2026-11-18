# Recommended service list (step 5 — awaiting owner choice)

Status: DRAFT

**Recommendation: C2** (weighted 4.25 vs 3.7 for the previous plan). Evidence: [A](evidence-A-backend.md) · [B](evidence-B-frontend.md) · [C](evidence-C-ingestion.md) · [D](evidence-D-reader.md) · [E](evidence-E-operations.md) · [F](evidence-F-data-features.md); [capabilities](capabilities.md); [scoring](candidates-and-scoring.md).

| Container | Role | Owns |
|---|---|---|
| `edge` | Caddy: TLS, HTTP/2 | certificates |
| `web` | Angular Material, responsive, SSR, bn/en | nothing |
| `gateway` | routing, rate limits, CSRF, session assertion | nothing |
| `accounts` | login, 2FA, password links, sessions, grants/scopes, capability signing, demo | users, grants |
| `catalog` | books, agents, series, categories, physical books, metadata review, search, exports | metadata |
| `content` | EPUB/HTML/cover/preview custody, downloads | artifacts |
| `reader` | opens the EPUB, serves chapters/TOC to the reading UI; progress, bookmarks, highlights, notes, shelf, saved filters | reading state |
| `ingestion` | source sync, submissions, scrape, curate, validate, build, jobs, review queues + live progress | jobs, drafts |
| `notify` | mail and Kindle delivery, send log | mail log |
| `postgres` | one database + role per service | — |

Open design question for `reader` (Q-R1): server-side EPUB parsing with chapters to the browser (keeps read-only enforceable; recommended), a browser-side EPUB renderer as in the legacy app (every reader receives the whole file; needs an epub.js-class dependency, needs approval), or both.

If chosen, step 6 rewrites the plan on this list; the previous plan is kept under `planning/_v1/` as reference.
