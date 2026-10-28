# Entity and book relationship administration

The current [product specification](../application-reader-engine-plan.md) removes
editorial approval and restricts existing-book bibliographic edits to administrators.
[Implementation progress](../application-reader-engine-progress/README.md) records
actual verification and pending acceptance.

## Entity workspace and identity

`/manage/entities/` opens the contributor list, with shared category, series and
reading-list tabs. Lists search names and aliases, paginate at 1–100 records and
load full descriptions only on detail pages. Responses prohibit private caching.
Creation requires current global metadata-creation authority. Contributor/category
grants permit access to the exact granted entity; a book grant does not grant
entity editing.

Contributor and series display names are not unique identities. Separate current
records can have the same normalized name while retaining different UUIDs, slugs
and catalog numbers. A source namespace and key can bind one contributor or series
through `EntitySourceBinding`; the database enforces one target and a unique
namespace/key pair. Repeated binding use is idempotent. A display-name-only match
does not merge unrelated people or series. Category and reading-list name validation
retains its existing taxonomy/list rules.

Creation UUIDs are checked against immutable audits before replay. Actor, model
kind, target and original input must match. Changed input conflicts. Kind locks
precede entity row locks. Mutations reload current authority and compare
`expected_updated_at` before saving.

A non-admin cannot mutate a contributor, category or series linked to a book, even
through an otherwise authorized entity endpoint. Link creation and entity edits use
the same kind locks to close the attachment race. An administrator's linked edit
advances affected book revisions, preserves relationship overrides and marks file
metadata as potentially different. Authorized reading-list description, membership
and ordering remain ordinary list curation.

## Reading lists

Reading lists accept at most 100 unique book UUIDs in explicit order. Membership,
metadata and audit writes commit together. Missing or deleted selections roll back
the command. Publishing a list requires an introduction and a selection of books;
public contents expose only eligible public books. No review endpoint or approval
step remains.

Public contributor/category/series directories include names associated with public
books. Contributor role filtering applies to the role on that same book. Signed
cursors are bound to the directory and role; drafts do not leak through public
counts or linked-book lists.

## References, relationships and editions

`/api/v1/manage/catalog-references/` returns bounded IDs/names and catalog numbers
where available, with `has_more`. The UI requests 24 results, debounces queries and
cancels obsolete reads. Catalog numbers distinguish equal names in selection lists;
commands send explicit UUIDs. Book-reference searches for relationship changes
require administrator access.

Administrators edit contributor roles, categories, ordered series and edition groups
at `/manage/books/<slug>/relationships/` and its versioned API. Duplicate UUID/role
pairs, duplicate category/series IDs, malformed nested fields, unavailable selections
and more than 100 entries are rejected. Changes record the previous relationships,
advance the catalog revision and preserve overrides. They do not grant ownership
or access. Permission applicability is queried from current relationships.

An explicit `edition_of` selection joins the chosen book's group, creating a group
if necessary. It never guesses a group from equal names or merges existing groups.
`null` detaches only the edited book. A command lock precedes book locks to prevent
reciprocal edition edits from deadlocking. Detail responses bound related editions
to 100 and indicate additional members. Public edition browsing applies publication
and access filtering independently.

Backend and browser checks cover role denial, scoped listing, current-actor reload,
UUID replay, name identity, bounded queries, stale commands, atomic relationship
replacement, concurrent edits and explicit edition attachment/detachment. Current
results and visual acceptance remain in the implementation evidence record.
