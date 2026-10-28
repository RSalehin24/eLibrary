# Implementation evidence

**28 October transfer checkpoint:** read the detailed
[machine handover](handover/README.md) before continuing. No task serving/test
processes were found and Docker was unavailable on inspection. The latest full
Chromium run finished with **51/59 specs passing; 249 journeys passed, 8 failed**.
Current source has 60 specs and additional changes needing a new build. This is
not a completed website or whole-project acceptance.

Implementation began on 21 October 2026 after the user requested “Implement”.
The reviewed [plans](../application-reader-engine-implementation/README.md) remain
the requirement baseline. This directory records actual work separately from their
fingerprints. No milestone has received user visual/UX acceptance.

| Task | Current state |
| --- | --- |
| F01/F02 | Baseline inventory and contract/runtime walkthrough recorded |
| W01 | Unified schema and physical/review removals implemented; backend verification passes |
| W02 | Administrator-only writes, indirect entity protection and explicit entity identity implemented; backend and core browser checks pass |
| W03 | Automatic EPUB/HTML/reader preparation and publication, first-intake replay and atomic cover replacement implemented; backend and core browser checks pass |
| W04–W07 | Existing website capabilities retained and updated; expanded layout/task-flow verification in progress |
| W08 | Open: finish browser/state matrix, rendered inspection and user visual/UX acceptance |
| R01–R05 | Not started; website acceptance is their prerequisite |
| E01–E08 | Not started; independent reader acceptance is their prerequisite |
| REL01/REL02 | Not started; no release or whole-application acceptance claimed |

## Implemented behavior

Books use ordinary publisher, language, edition and compilation fields. Physical
classification/inventory/logs, editorial approval fields/models/states/routes,
manual book publication and obsolete page aliases are removed. Empty intake stays
unpublished. New migrations were generated and applied to empty PostgreSQL.
Historical migrations and the original specification/PDF are preserved.

Existing-book metadata, cover, files and relationship writes share the active,
TOTP-ready staff/superuser/global-full-control administrator policy. Scoped metadata
users retain authorized listings/exports and entity workspaces. They receive no
book edit/file controls and cannot mutate books indirectly through linked entities.
Linked administrator edits advance book revisions and preserve overrides.

Equal contributor or series names can represent distinct UUIDs/slugs/catalog numbers.
Source namespace/key bindings provide explicit reusable identity. Reference selectors
show catalog numbers and submit UUIDs; same-name selection has backend and browser
regressions.

Initial creation and EPUB intake retain stable request identities. Successful upload
prepares reader resources and ordered EPUB-derived HTML before atomically activating
files and publishing. Invalid/scripted/unsupported resources, stale revisions, revoked
permissions and storage/persistence failure preserve the previous edition. An initial
creator gains no later book-edit authority or ownership. Cover upload/removal validates
actual image data, commits with the revision/audit/override, and survives source
regeneration. Saved catalog information does not claim that embedded file metadata
has already changed; the editor displays `file_metadata_may_differ`.

Website callers, generated OpenAPI/TypeScript, fixtures and retained tests have moved
with these contracts. Test cases for removed behavior assert its absence; unrelated
search, permission, rollback, pagination, reader and personal-data checks remain.
The reader title now wraps, and the header wraps controls instead of compressing the
title to a few pixels at enlarged phone text. The expanded matrix also found a Kindle
filter-grid minimum-width defect; its corrected complete layout run passed.

## Executed checks

- Full non-live backend/tooling/plan/performance run: **1,974 passed, 13 live cases
  deselected**, with `-W error`. The actual Redis engine integration uses a dedicated
  local Redis instance. Log: ignored
  `test-artifacts/foundation/implementation-backend-final.log`.
- Website: **149 unit tests passed**, ESLint passed, production build/strict generated
  types passed for the preceding source. Latest linked-entity capability,
  contributor-label and guidance edits need a fresh unit/lint/type/build run.
- Mypy: **293 source files passed**, including new/replaced modules without reducing
  its previous scope. Changed non-generated Python passed Ruff check/format.
- OpenAPI validation and generated TypeScript passed; the preceding repeated
  generation produced identical bytes. The latest `can_edit` generation succeeded,
  but its repeated-generation identity still needs checking. Retired book
  fields/routes are absent from the generated contract.
- Django system check and migration drift check passed. Empty browser-reference
  initialization applied every migration; fresh-schema regressions also pass.
- Planning verification passes **347 exact requirement mappings**, 25 acyclic tasks,
  54 starting route obligations, 140 links, 18 evidence paths, 18 closed planning
  findings and 28 reviewed fingerprints. Its **30 tests** include missing/extra-route
  rejection while allowing exactly the two planned page removals.
- Architecture/file-size policies and whitespace checks pass. No policy exemptions,
  test skips, type/lint suppressions or new dependencies were added.

Browser evidence is under ignored `test-artifacts/foundation/implementation-browser-*`.
Fresh fixtures are generated per specification. Current Chromium passes cover uploads,
uncertain writes, administrator denial, automatic EPUB publication/reader launch,
metadata saves/canonical redirects/conflicts, explicit relationships/same-name IDs,
all four entity kinds, creation/lifecycle, exports, personal library, removed physical
logs/aliases and scoped workspaces. Earlier failed/interrupted runs remain evidence;
they are not counted as passes. The corrected complete layout run checked **1,340
route/language/width/text-scale combinations**, with all eight families passing.
The later full workflow run has eight failures; see the handover's exact
[failure list and freshness notes](handover/verification-and-next-steps.md).

The layout matrix now uses 320/390/820/1366/1920px at normal and 200% text in Bengali
and English. Screenshots include concrete routes and all four managed entity kinds.
Automated geometry and selected rendered inspection do not constitute user visual
acceptance or full adverse-state/browser coverage.

## Baseline and environment

F01 captured [54 starting routes](baseline-routes.csv) and [35 original issues](baseline-issues.csv).
The original layout run passed seven families and failed the reader title at 320px.
Its screenshots/logs remain under `implementation-baseline-layout/`. Historical
[feature parity](../operations/feature-parity.md) is reference evidence; retained
features need current results. Intentionally removed features are identified there.

During the 21 October runs only the application's foundation PostgreSQL container
ran, on 55432. The disposable
`bangla_library` browser reference was rebuilt empty; pytest uses `test_bangla_library`.
The separate `bangla_library_preview` database was neither reset nor synthetically
seeded. Reference media is isolated under ignored implementation artifacts. Redis
on 56380 is reserved for tests; the host's unrelated Redis remains untouched.
Processing, scheduler, broker and delivery workers remain stopped. Mail configuration
uses loopback and synthetic recipients; no external email or Kindle delivery was sent.

Reference API 8002 and website 3001 used the preceding immutable production build,
with the API origin and HTTPS canonical URL supplied at both build and startup.
An initial browser attempt omitted startup settings and was discarded. The in-app
browser connection failed initialization; maintained Playwright tests and local
screenshot inspection are the available browser tools. Private fixture/log files
remain ignored. No commit, push, dependency installation or deployment occurred.

## Remaining gates

Finish the current website browser/state/profile matrix, responsive/keyboard/visual
inspection and W08 user acceptance before extracting the reader. Reader service,
revisioned progress/commands/local-offline work, independent engine transport/data,
real local inference, the complete source-corpus benchmark and integrated release
work remain outstanding. Live-source accuracy, physical devices and actual external
Kindle arrival are not established by synthetic or loopback checks. This is an
implementation checkpoint, not a guarantee that no further defects can arise.
