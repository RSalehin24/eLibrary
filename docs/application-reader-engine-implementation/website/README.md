# Website module: M1

Implement W01–W08 in the [task order](../shared/baseline-and-sequence.md). Entry requires F01/F02 and a verified planning review. Exit is W08; engine intelligence cannot begin while this gate is open.

| Plan | Owns | Tasks |
| --- | --- | --- |
| [Data and authorization](data/unified-books-and-authorization.md) | Unified schema, removals, admin writes, automatic intake/publication | W01–W03 |
| [Design and route matrix](interface/design-and-route-matrix.md) | Shared components, shells, localization, all 54 starting route templates | W04, W08 |
| [Behavior and failures](workflows/behavior-and-failures.md) | Catalog/personal/admin flows, race conditions, and recovery | W05–W07 |

## Gate W08

- Every retained website route, dynamic entity kind, section, dialog, and applicable state has current Bengali/English rendered evidence and complete task-flow results. The route list is a starting inventory; new findings expand it.
- Shared controls, layout, copy, responsive behavior, and accessibility meet the source plan and the interface matrix. No open visual, UX, or functional defect can be excluded by calling it unrelated after it is discovered in this audit.
- Fresh PostgreSQL initialization contains no physical records/logs, physical/digital type field, or review/approval workflow. Removed endpoints are absent; contract and client generation agree with runtime behavior.
- A non-admin, including a metadata grantee, cannot see or invoke book metadata/cover/relationship writes. Administrators can edit without unpublishing or entering review. Own-profile/annotation edits remain functional.
- Source and EPUB-upload preparation publish only usable HTML/EPUB/reader builds automatically. Pending, failure, denial, and uncertain outcomes remain truthful. Existing reader entry still works before its extraction.
- Run applicable backend tests, current website unit/lint/type/build checks, schema/migration/policy checks, permission regressions, and the [browser matrix](../shared/verification/test-strategy.md). Do not use the legacy verifier as proof of current website acceptance.
- Record the user's visual/UX acceptance separately from automated checks. If it has not occurred, W08 remains awaiting acceptance and engine work does not proceed through this gate.

Recovery before W08 is a scoped code/build correction and rerun of affected evidence. Never relax layout assertions, suppress failures, restore removed review states, or hide incomplete books as a substitute for fixing preparation.
