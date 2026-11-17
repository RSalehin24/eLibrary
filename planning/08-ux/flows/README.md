# Key user flows

Status: DRAFT

Each flow lists steps, the service interactions, and failure branches. These become the E2E journeys ([test strategy](../../09-testing/strategy.md)).

## F1 — Discover → preview → sign in → read (the new public/private split)

1. Visitor opens `/` → searches "হুমায়ূন" → `GET /api/catalog/search`.
2. Opens a book page (`/books/{slug}`) → reads credits, summary, TOC, preview excerpt (content `PreviewArtifact`).
3. Presses **Read**. Not signed in → `/login?next=/read/{slug}`. After sign-in (and TOTP if required) → back to `/read/{slug}`.
4. Library `open` → access `decide(Read)` → Allow → capability → chapters stream.
5. Branches: Deny(`NoGrant`) → page explains "ask an administrator" with the book title; Deny(`ReadOnceConsumed`) → explains read-once; access down → fail-closed message with retry; capability expiry → silent renew; artifact set changed → reload with notice.

## F2 — Reading session

Open → restore progress (section + offset) → read → highlight (select → color → optional note) → anchor created → autosave progress every 15 s or on section change (debounced, revisioned) → close. Offline blip: queue writes locally, replay with revisions.

## F3 — Admin creates a book from a source URL

1. `/admin/jobs/new` → paste URL → duplicate precheck (catalog classify) shows "already exists / new edition / new" before starting.
2. Job runs; the job page streams steps; completeness and conservation summaries appear.
3. Outcomes: Published (link to book) · Review items (go to Review) · Failed (reason code with action).

## F4 — Review queue resolution

Open item → evidence view (blocks highlighted in source order) → pick action (typed per kind) → resolve → job resumes. Keyboard: `j/k` next/prev, `1..9` choose candidate, `Enter` confirm.

## F5 — Reprocess with diff

Choose books + ruleset → diff run → per-book summary (tree changes, entity changes, text delta, anchor impact) → select → apply → new artifact sets → annotation re-anchor progress.

## F6 — Invite and activate account

Admin invites → mail → link → set password → (optional TOTP setup) → library. Branches: link expired → request new; superseded → "a newer link was sent".

## F7 — Send to Kindle

First use: profile shows our sender address and the Amazon approved-sender step with a "I added it" confirmation. Then: book page / reader menu → choose address (or add) → preflight message (size/format) → sent confirmation + history `/sent`; failure shows reason code text.

## F8 — Curate catalog

Search admin list → open book → edit fields (overrides marked) → save with revision → conflict dialog shows differences → merge agents (preview of affected credits).
