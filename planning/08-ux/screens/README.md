# Screen specifications

Status: DRAFT

One file per screen. Routes, auth and service owner are in the [route map](../route-map.md); principles in [principles](../principles.md). Rewritten for the six-service design; the v1 per-page list (21 pages, ten processing screens) is replaced by the seven merged screens of [new-architecture section 8](../../_replan/new-architecture.md) plus the notes, catalog-management and states specs.

## Template (every spec)

Purpose · Primary action · Routes, auth, service owner, requirements · Data (endpoints) · States (the seven `PageState` variants) · Layout (compact, medium, expanded and large) · Actions · Copy keys (bn and en) · Analytics: none · Accessibility notes · Open points.

Copy keys are `ux.<screen>.<element>`; `bn` and `en` catalogs must have identical key sets (REQ-WEB-011). Bengali strings here are drafts for editorial review. Error text comes from catalogs keyed by error code ([states](states.md)).

## Index

| Screen | Spec | Requirements |
|---|---|---|
| Sign-in and auth shell | [sign-in](sign-in.md) | WEB-002, 014, 020; IDN-001..008 |
| Library | [library](library.md) | WEB-015, 022; CAT-008, 009, 025, 026 |
| Book detail | [book-detail](book-detail.md) | WEB-016, 022; CAT-019..023, 029 |
| Reader | [reader](reader.md) | WEB-021; RDR-005..025 |
| Notes (placement OPEN U-7) | [notes](notes.md) | RDR-018, 019 |
| Import workspace | [import-workspace](import-workspace.md) | WEB-017; ING-001..036 |
| Catalog management | [catalog-management](catalog-management.md) | CAT-001, 006, 007, 027 |
| Users and access | [users-access](users-access.md) | WEB-018; IDN-010..012, 031 |
| Audit viewer | [audit](audit.md) | IDN-029; ING-035 |
| Settings | [settings](settings.md) | WEB-019; IDN-004, 006, 028, 034; RDR-017 |
| Error, empty, forbidden, offline states | [states](states.md) | WEB-001, 002, 004, 020 |

Flows that cross screens are in [flows](../flows/README.md).

## Priority for prototypes

1. Library and Book detail. 2. Reader. 3. Sign-in shell. 4. Import workspace. 5. Users and access, Settings.
