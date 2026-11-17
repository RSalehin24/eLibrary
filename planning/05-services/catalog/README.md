# catalog

Status: DRAFT

What books exist, who made them, how to find them. Public by default.

| | |
|---|---|
| Owns | works, books, agents, credits, series, categories, overrides, redirects, search index (derived), exports |
| Does not own | files/artifacts (content), grants (access), user data (library), ingestion drafts (ingestion) |
| Requirements | REQ-CAT-001…009, REQ-DSC-001…010 |
| Emits | `BookDraftUpserted`, `BookPublished`, `BookArchived`, `BookMetadataChanged`, `AgentMerged`, `AgentSplit` |
| Consumes | `ArtifactSetSealed` (content) |
| Calls | access (`decide` for admin routes only) |
| Called by | gateway/web, ingestion (commands), library (book refs), access (book facts via events) |

## Public by construction

Handlers for search, browse, book detail and agent pages **do not call access**: they read
only Published rows, so no decision is needed. This keeps public pages up when access is down
and removes a whole class of "forgot the check" bugs. Admin routes require `Allow<…>` witnesses.

## Modules

| Module | Responsibility |
|---|---|
| `books` | lifecycle, credits, overrides, revisions, redirects |
| `agents` | people/organizations, aliases, merge/split |
| `taxonomy` | categories, series (ordered) |
| `search` | analyzer, index projection, query API — see [search](search.md) |
| `duplicates` | duplicate-policy queries used by ingestion — `domain-entities` |
| `exports` | CSV/XLSX/PDF of filtered lists |
| `inventory` | (only if D-01 = keep) physical books |

See [domain model](domain-model.md) · [API](api-contract.md) · [state machines](state-machines.md) · [tests](test-plan.md).
