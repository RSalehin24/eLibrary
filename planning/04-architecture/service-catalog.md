# Service catalog

Status: DRAFT

Seven domain services, one gateway, one web app. Each is a separate Rust crate/binary
with its own database. See [ADR-0002](adr/0002-independent-services.md).

| Service | Owns (source of truth) | Never owns | Public via gateway | Sync deps | Emits events |
|---|---|---|---|---|---|
| **identity** | accounts, credentials, TOTP, password links, sessions, Kindle addresses | roles/grants, books | login, logout, session, profile, password links, 2FA, account admin | — | `AccountInvited`, `AccountActivated`, `AccountSuspended`, `SessionRevoked`, `PasswordLinkIssued` |
| **access** | grants, scopes, default-grant policy, read-once openings, demo flag, signing keys | accounts' credentials, books | grants admin, "my abilities" | identity (subject facts) | `GrantChanged`, `OpeningConsumed` |
| **catalog** | works, books, agents (people/orgs), credits, series, categories, overrides, redirects, search index (derived), exports | files, user data | search, browse, book detail, agents, admin edit, exports | access (`decide` for admin) | `BookPublished`, `BookArchived`, `BookMetadataChanged`, `AgentMerged` |
| **content** | canonical documents (published), artifact sets (EPUB/HTML/preview/cover), builds | metadata truth, access decisions | preview, cover, chapters + EPUB (with capability) | — (verifies capabilities offline) | `ArtifactSetSealed`, `ArtifactSetActivated` |
| **library** | reading progress, sessions, bookmarks, highlights, notes, shelf, saved filters | books, grants | progress, annotations, notes page, shelf | access (`decide`), content (sections for re-anchor) | `AnnotationOrphaned` (analytics only) |
| **ingestion** | sources, source catalog entries, snapshots, jobs, canonical-document drafts, rulesets, review items, gold-corpus metrics | published books | admin Sources / Jobs / Review | catalog (commands), content (commands), access (`decide`) | `JobStateChanged`, `ReviewRequested`, `DocumentValidated` |
| **notify** | mail templates, outbound mail log, Kindle send log | accounts, books | none (event-driven; admin view via API) | content (EPUB via service capability), identity (addresses) | `MailSent`, `MailFailed`, `KindleSent` |
| **gateway** | routing, rate limits, CSRF, session assertion minting | any business data | everything | identity, others by route | — |
| **web** | pages, UI state | any data | all pages | gateway only | — |

## Why this split (and what was rejected)

- **identity vs access** — authentication changes rarely; authorization changes with product rules and needs formal checking. Separate failure and review surfaces.
- **catalog vs content** — metadata is small, public, read-heavy and searchable; content is large, immutable, access-controlled. Different scaling and different leakage risks.
- **library separate** — private per-user data with different retention/privacy rules; must not be coupled to the catalog.
- **ingestion separate** — heavy, hostile-input, failure-prone; must never take down browsing.
- **notify separate** — side effects with third parties, strictly at-least-once.
- **Rejected: `search` as its own service** — it is a rebuildable projection of catalog; running it inside catalog removes a network hop and a consistency problem. It is isolated as a module with its own storage ([search design](../05-services/catalog/search.md)). Revisit if it needs independent scaling.
- **Rejected: separate `processing` UI-projection service** — the legacy duplication of ingestion state.

## Consolidation escape hatch

If operations toil exceeds the threshold in [risk R-08](../03-correctness/risk-register.md),
`notify` and `identity`+`access` may be co-deployed as one process. Code and database
boundaries stay unchanged; only the binary composition changes.
