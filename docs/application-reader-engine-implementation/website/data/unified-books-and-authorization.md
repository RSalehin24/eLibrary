# Unified books, administrator writes, and automatic readiness

Tasks W01–W03. Apply [data/state rules](../../shared/contracts/data-and-state.md) and [service ownership](../../shared/contracts/service-boundaries.md).

## Existing code to read and extend

Start with `app/backend/apps/catalog/models/{books,choices,personal,editorial}.py`, `editorial/{creation,service,epub_uploads,source_publication,relationships}.py`, catalog serializers/discovery/exports/views, `apps/common/{models,permissions}.py`, `apps/accounts/workspaces.py`, `apps/access/models.py`, API URL modules, and source publication code. Website callers include `src/api/{editorial,book-creation,book-lifecycle,book-relationships,reading}.ts`, form/action components, filter state, navigation, and fixture generators. Search all occurrences before removing a field; prefixes and display labels differ (`manual`, `physical`, `record_type`, `needs_review`, and `review_state`).

## W01: remove the concepts across all layers

1. Record a field/endpoint/permission/caller inventory, including exports, saved filters, sitemap eligibility, old served APIs, commands, task inputs, raw JSON assumptions, fixtures, and documentation. Inspect every physical-only model dependency before removing its record/table.
2. Remove physical records and physical-only logs through a scoped clean development rebuild where needed. Remove the active record-type field and enum. Do not convert a physical record into an empty book. Preserve useful publisher/language/edition/structure facts under ordinary bibliographic names.
3. Remove book/entity editorial-review timestamps where they gate a product review workflow, metadata review records, review enums/states/routes/buttons/badges/filters, and publication predicates based on approval. Shared lifecycle enums may have other consumers: replace their review transitions coherently rather than leaving invalid states.
4. Keep automatic content-integrity/source-quality checks and ordinary indexing eligibility. Public listing, entity counts, sitemap/SEO, access, and exports depend on published availability and safe metadata, never on a review flag. Do not delete a class merely because its historical module name contains `editorial`.
5. Generate new migrations using Django after checking relations and constraints. Preserve existing migration files and policy baselines. Apply the complete graph to empty PostgreSQL, inspect actual resulting tables/columns/choices, and regenerate schema/client outputs using repository tools.
6. Update tests for explicitly removed behavior to assert its absence, and keep meaningful retained coverage. A physical-log test becomes an absence/404 regression; a review test becomes automatic-readiness/no-review regression. Never simply skip/delete failing suites to get a green count.

W01 must already update existing successful preparation/publication paths to the replacement lifecycle while removing review fields. A staged schema removal that leaves source creation/import broken until W03 is not an acceptable intermediate change. W03 extends and verifies complete intake/failure behavior; it is not permission to leave W01 unusable.

Entity identity must also support the required evidence-based engine: `Contributor` and `Series` currently make both name and normalized name unique and `entity_service.require_unique_entity_name` rejects equal names. Replace name-only identity/uniqueness for these kinds with immutable IDs and unique source/entity bindings; keep normalized names indexed for candidate lookup. Generate the migration and update serializers, creation validation, selectors, catalog-code/slug allocation and tests together. Same-name different people/series stay separate; do not append invented text to their names or merge them to satisfy a constraint. Categories remain a controlled taxonomy within a provider/namespace, and reading lists keep their own identity; equal display text alone never proves a contributor/series identity. A repeated same supported identity is reused idempotently. Expose existing distinguishing bibliographic evidence in selection results where available.

**W01 exit:** schema, route registry, serializers, generated clients, fixtures, UI, and current docs agree. Searches may still find historical migrations, historical reports, parity-removal records, and negative tests; classify those explicitly. They must not create active features. Do not hand-edit generated files or erase historical migrations just to obtain zero search matches.

## W02: define administrator once

For book cover/metadata/relationship mutation, administrator means an authenticated, active account with completed required TOTP and either `is_staff`, `is_superuser`, or a current **global** `admin:full_control` grant. A book/category/contributor-scoped full-control grant does not turn its recipient into an administrator. A global/scoped `metadata:edit` grant alone does not qualify. This narrows the existing metadata behavior as required by the product specification.

Implement a focused shared policy and use it for server-provided `can_edit_book`, route access, and every mutation service. Recheck under the current actor/grant lock before committing. Do not use the broad `user_has_scope(..., book=...)` shortcut to decide administrator identity. Include direct multipart cover replacement/removal, EPUB replacement metadata changes, relationship/order/edition links, bulk writes, legacy APIs, management commands that take a user, and queued write/publication authorization. Automated extraction uses its separately authorized service workflow.

| Actor | Existing book metadata/cover writes | Own profile/annotations | Source/jobs/access/entity administration |
| --- | --- | --- | --- |
| Anonymous/inactive/TOTP-blocked | Deny | Existing authentication/TOTP rules | Deny according to existing boundary |
| Reader, owner, read/download/Kindle grantee | Deny | Allow own authorized records | Existing grants only |
| Global/scoped metadata editor, non-admin | Deny | Allow own authorized records | Retain authorized entity management and intake rights; no indirect book edit |
| Active staff/superuser or global full-control administrator | Allow with revision/input validation | Same ownership boundaries for personal data | Existing administrative permissions |

Reader View changes navigation only; it never grants or removes authority. Non-admin management users may retain their authorized jobs/entities sections but never get a book editor through those links. Initial manual intake may retain its existing global creation permission; providing validated metadata for a new intake does not grant subsequent edits to an existing book. Upload replacement of an existing book, including through a guessed creation result, requires administrator authority.

Close indirect writes too: changing a linked contributor/category/series name, alias or other field presented as book metadata requires administrator authority, even through an entity endpoint. A non-admin may keep existing authority to inspect entities or edit an unlinked entity; locking/rechecking links prevents an entity becoming attached between the check and write. Reading-list description/membership/order remains ordinary authorized list curation, not an existing book's bibliographic edit. Book contributor-role/category/series/edition associations stay admin-only. An administrator's linked-entity change increments affected books' revisions and invalidates affected caches/build metadata; relationship changes also recompute grant applicability rather than trusting cached authority.

**W02 regression matrix:** anonymous, inactive, TOTP-blocked, ordinary reader, owner, scoped/global metadata editor, scoped full-control grantee, expired/revoked grant, staff, superuser, global full control. Test UI capability/visibility plus direct JSON, multipart, relationship and alternate served API writes. Test revocation between form load and commit and before a queued job publishes. A denied write leaves metadata, file pointers, and publication state unchanged.

## W03: one automatic completion rule

Reuse source generation/preparation and EPUB-upload services. A new record starts unpublished/pending, never needs review. Validate archive safety, metadata input, HTML/EPUB generation, checksums, reader preparation, and authorized ownership before atomically activating it. Successful creation shows actual Read/HTML/EPUB destinations. Its operation is not succeeded at upload acceptance or task dispatch.

Uploaded EPUB lacks source-site evidence; validate its own package, body/navigation/resources, permitted metadata, and prepared renderer instead of fabricating source completeness. Respect existing upload/resource limits. A missing cover gets a deterministic title/credits fallback. Reject wrong types, encrypted/malformed/oversized archives, unsafe paths, and scripted resources with useful recoverable errors.

Produce its HTML from the validated EPUB's ordered retained spine content and safe resource map, reusing preparation/sanitization logic. Rewrite package-relative IDs/links/resources into confined HTML targets; do not build an HTML placeholder or count EPUB upload alone as HTML readiness. Preserve cover/title/body order, meaningful front/back matter, poetry/tables/media and navigation targets; verify both outputs against that uploaded package. If conversion cannot preserve a required resource/content structure, fail with a typed preparation cause instead of silently omitting it.

For an admin metadata save, validate whitelisted fields and `expected_updated_at` and preserve live availability. Cover replacement validates actual image bytes/MIME/limits before committing a new pointer; a failed write keeps the previous valid cover. A linked file's embedded metadata may update through background regeneration, but UI metadata save does not pretend that the EPUB bytes have already changed. Mark build metadata alignment honestly and keep authoritative overrides on regeneration.

Before E01 separation, website source workflows continue through the existing backend with the same contract semantics. Introduce the command/status seam once; do not build a competing placeholder engine. M1 uses deterministic existing preparation, not new model inference. E01 later moves ownership behind the seam.

**W03 regressions:** empty record never Prepared; valid upload/source automatically available; broken HTML/EPUB/reader file prevents readiness; duplicate intake returns the same outcome; same key/changed body conflicts; interrupted/failed replacement leaves active pointers consistent; metadata save creates no review task; stale edits preserve draft; concurrent preparation and metadata edit cannot overwrite admin fields; archive/revocation prevents activation; all actions use the same active build.

Use `tests/backend/catalog_management/`, `tests/backend/access/`, `tests/backend/processing/` and current `tests/web/e2e/{uploads,book-lifecycle,book-details,book-list-actions}.spec.mjs` as existing coverage seams. Add focused cases there rather than duplicating fixture frameworks. Run fresh-schema, schema/client, type, backend, and relevant browser gates before W03 closes.
