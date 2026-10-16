# Entity and book relationship administration

`/manage/entities/` links private contributor, category, series, and curated
collection lists. Lists search names and verified aliases in SQL, paginate at
1–100 records, and fetch only their displayed fields. Full editorial text is
loaded on the detail page. All responses prohibit private caching.

`/api/v1/manage/entities/<kind>/` lists and creates entities; the UUID detail
route reads, updates, reviews, and, for collections, publishes or withdraws them.
Creation requires global metadata authority. Contributor/category grants permit
editing only the exact granted entity; a book grant does not grant entity editing.
Mutations lock and reload the actor before checking authority, then compare the
expected timestamp. Names must contain letters or numbers and remain unique
after normalization within their kind. Kind-level name locks serialize concurrent
creation and renames, including collections whose legacy model permits duplicate
names. An existing entity with an unchanged legacy duplicate name may need a
distinct name before saving through this workspace.

Creation and updates take the kind lock before the entity row lock. This also
prevents a creation UUID collision against a legacy record from deadlocking
with an edit of that record.

Creation uses one UUID for the entity and immutable creation audit. Replay verifies
the actor, verb, model kind, target UUID, and original payload before returning
the current entity. Changed input or a colliding command conflicts. Updates and
commands also create audit records; existing slug history preserves public
canonical redirects after renaming.

Collections accept at most 100 unique book UUIDs in explicit order. Selection
replacement, metadata, review reset, and audit writes share one transaction.
Missing or deleted selections roll back the entire command. Detail responses
include ordered book IDs and labels in one joined query. Publication requires
a reviewed nonempty introduction and selected books. The public collection feed
continues to expose only eligible public books. Saving edits clears approval;
review must be renewed before edited collection content becomes public.

Reference searches at `/api/v1/manage/catalog-references/` return at most 100
IDs/names (the UI requests 24), plus `has_more`. Book results respect metadata
management scope. The UI debounces searches and cancels obsolete reads. Selections
persist across searches, support keyboard-accessible ordering/removal, and do not
download the entire catalog. Validation preserves drafts. Revision conflicts and
uncertain mutations block repeated writes until the current result is inspected.
Unsaved work and pending writes participate in the PWA update guard.

## Book relationships and editions

Global metadata managers reach `/manage/books/<slug>/relationships/` from the book
editor. `GET` and `PATCH` on the matching versioned API expose contributor roles,
categories, ordered series, and edition grouping. A contributor may hold several
distinct roles; duplicate contributor/role pairs and duplicate category/series
IDs are rejected. All selections have a 100-entry limit and must resolve to
existing entities. Unknown and malformed nested fields are rejected.

Relationship edits require global authority because contributor/category links
also determine scoped book permissions. They never assign ownership or grants.
Every command checks the source book's revision, records its previous relationships
in `MetadataVersion`, and clears editorial review. Invalid selections roll back
all replacements and snapshots.

An explicit `edition_of` book joins that book's existing group. If it has no group,
a new `BookGroup` is created and both books receive snapshots, new timestamps,
and review resets. Selecting a book in another group moves only the edited book;
it does not merge groups. `null` detaches only the edited book and retains the
other records. A command lock precedes book row locks to prevent reciprocal
edition requests from deadlocking. Edition names are bounded to 100 per detail,
with an explicit indication of additional members. This is administration of
existing groups; public cross-edition browsing remains separate work.

## Verification

PostgreSQL tests cover CSRF, scoped/revoked authority, immutable UUID replay,
normalized-name races, revision conflicts, publication and slug history, invalid
selection rollback, book labels without N+1 queries, contributor roles/order,
relationship snapshots, and concurrent/reciprocal edition commands. Browser
journeys cover all entity kinds, remote selection, collection publication, stale
drafts, uncertain requests, role isolation, edition attachment/detachment, and
320-pixel layouts at 200% text. No dependency was added.
