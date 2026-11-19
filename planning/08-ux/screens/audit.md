# Audit viewer

Status: DRAFT

**Purpose**: read the append-only audit trail to answer who did what and when.
**Primary action**: Filter.
**Routes**: `/admin/audit` (accounts and access, identity) and `/import/activity` (operator actions, ingestion). **Auth**: `manage_users` for identity (who may read it is **OPEN C-1**); `operate` for ingestion. **Service owner**: identity, ingestion. **Requirements**: REQ-IDN-029, REQ-ING-035; D-40 (1 year retention).

## Data

`GET /audit` on identity (filter actor, subject, action, period) and `GET /audit` on ingestion. Catalog and reader keep audit rows (publish, delete, downloads, opens: REQ-CAT-031, REQ-RDR-011) but their contracts expose no read route, so those events are not viewable yet (**OPEN U-4**).

## Content

One table component, read only: time (viewer's time zone), actor, action, subject, outcome; filters for actor, subject, action and period in the URL; keyset load more; row detail shows the typed fields (never secrets, tokens or reset links). No edit or delete controls exist anywhere.

## States

| State | Behaviour |
|---|---|
| Loading | skeleton rows |
| Empty | "No events match these filters" with Clear filters |
| Ready | table |
| Error | banner with Retry |
| Forbidden | missing scope: forbidden state, session stays |
| NotFound | not applicable |
| Offline | banner; last data stays |

## Layout

compact: list of cards with the detail in a sheet; medium: table; expanded and large: dense table with sticky header and a detail drawer.

## Copy keys

| Key | en | bn |
|---|---|---|
| `ux.audit.title` | Audit log | অডিট লগ |
| `ux.audit.filter.actor` | Actor | কর্তা |
| `ux.audit.filter.action` | Action | কাজ |
| `ux.audit.filter.period` | Period | সময়কাল |
| `ux.audit.empty` | No events match these filters | এই ফিল্টারে কোনো ঘটনা নেই |

Analytics: none. Accessibility: table headers, time in text with machine-readable `<time>`, filters in a labelled form, results count announced.
