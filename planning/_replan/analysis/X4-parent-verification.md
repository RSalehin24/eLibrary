# X4 - Parent verification of severe UNVERIFIED claims

Status: DRAFT (in progress; batches of 3 items, parent read the code directly)

Scope: items from `X1-issues-register.md` section 4. Code root: `archive/app/backend`. Result values: CONFIRMED, PARTLY (with the nuance), REFUTED, OPEN.

## Batch 1

| X1 ID | Claim | Result | Evidence (file:line) | Nuance / change to the register |
|---|---|---|---|---|
| X1-001 | Ownership (`UserBook`) can be created by routes other than the My Books endpoint | CONFIRMED | `catalog/views/books.py:102` (`get_or_create` for `request.user`, any logged-in user); `ingestion/models/submissions.py:42-44` (`BookSubmission.save()` creates `UserBook` for the submitter when `linked_book`/`submitter` changes) | Two creation routes. The submitter route is plausible intent; the self-service route is the hole (owners bypass gates, see D4 / X3 L-list). |
| X1-002 | DRF default permission is `AllowAny`; per-view overrides may be missing | PARTLY | `config/settings.py:203-205` default `AllowAny`. All class-based views in `views/`, `view_modules/` declare `permission_classes` (105 declarations). Only 2 classes lack one: `ProcessingCatalogAutomationView`, `ProcessingIncompleteAutomationView`, and both inherit `ProcessingAutomationView` with `CanManageProcessing` (`processing/view_modules/sync_action_and_automation_views.py:106-107`) | Not a live exposure today. It is a fail-open default: any new view without an explicit class is public. Downgrade from critical to high (latent). Rebuild: deny by default. |
| X1-003 | Reader token routes do not re-check grants; revocation does not invalidate live tokens | CONFIRMED | `access/views/reader.py:80,124,166` are `AllowAny`; `access/views/shared.py:45-49` `get_token_preview_session` accepts any non-expired token; `access/models.py:140-142` `is_active` is only `expires_at > now`; no field or code path deactivates or deletes `PreviewAccessSession` (search of non-test code found none); relaunch extends expiry (`reader.py:66`) | Manifest, EPUB and HTML are served to whoever holds the token for its lifetime. Progress/bookmark/highlight routes are stricter: they require login and an owner match (`access/views/shared.py:52-59`, used in `sessions.py`). Token appears in the launch URL. |

## Batch 2

| X1 ID | Claim | Result | Evidence | Nuance |
|---|---|---|---|---|
| X1-010 | Metadata edit/review views lack the `deleted_at` filter | CONFIRMED | `catalog/views/details.py:82` (`BookMetadataUpdateView.get_queryset`), `:97-104` (`MetadataReviewListCreateView.get_book`), `catalog/views/assets.py:18,47`: no `deleted_at` filter. The filter exists only at `details.py:38`, `shared.py:355`, `books.py:98`, `references.py:28` | Soft-deleted books can be edited/reviewed and their assets reached. |
| X1-065 | `task_postrun` publishes "worker done" for any Celery task with a positional first argument | CONFIRMED | `ingestion/signals.py:242-264`: `job_id = args[0]` with no task-name filter; publishes `CH_WORKER_DONE` with status from the Celery state | Any task whose first argument is truthy (a non-job value) produces a bogus completion event for the engine. The remaining parts of X1-065/066 (non-atomic `find_idle_worker`/assign, lost pub/sub messages) are consistent with `engine/engine.py:206,232` and `worker_registry.py:97` but not proven here. |
| X1-011 | `/media/` is served without authentication | PARTLY | `deploy/scripts/setup-host-nginx.sh:121-122,197-198`: `location /media/ { alias .../storage/media/; }` with no auth check; `GeneratedAsset.file` uploads to `generated/<book.slug>/<filename>` under `MEDIA_ROOT` (`catalog/models/utils.py:18-19`, `settings.py:227`); the `is_protected` flag exists (`catalog/models/books.py:208`) but nginx does not consult it | Generated books are reachable by URL without login if slug and file name are known. Slugs are visible in the catalog and previews; file-name predictability not checked. Also `config/urls.py:17` serves media through Django in debug. |

## Batch 3

| X1 ID | Claim | Result | Evidence | Nuance |
|---|---|---|---|---|
| X1-026 | Catalog re-sync overwrites locally derived fields | CONFIRMED | `processing/service_modules/catalog_record_sync.py:35-46,81-90`: for an existing record, every field in `defaults` that differs is set from the remote payload, including `book_creation_state`, `linked_book`, `resolved_from_incomplete`, `was_incomplete`, `category` | Local state is overwritten by remote payload data on every sync; effect depends on what the payload contains for these keys (`bookCreationState` is taken from the payload if valid, else recomputed from `linked_book`). Rebuild: keep source-mirror fields and local workflow state in separate stores. |

## Not yet checked (still UNVERIFIED)

X1-004, X1-014, X1-017, X1-020, X1-028/029, X1-032, X1-033, X1-037/038, X1-052, X1-054/055, X1-067, X1-068, X1-072, X1-081/083, X1-013, X1-110 (see X1 section 4 for file hints).

## Register changes implied
- X1-002: critical -> high (latent), per above.
- X1-003, X1-010, X1-001: now CONFIRMED.
- X1-011: PARTLY; needs file-name predictability check.
