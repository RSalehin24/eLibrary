# Screen specifications

Status: DRAFT

One file per screen is added here during phase P4/P5/P6 **before** the screen is built. Template:

```
# <screen> — <route>
Purpose (1 sentence) · Primary action · Audience/abilities
Data (services/endpoints) · States: loading / empty / ready / error / forbidden / notfound / offline
Layout notes (mobile / desktop) · Copy keys (bn/en) · Analytics events (if any)
Accessibility notes · Test journeys (TST ids)
```

## Priority list (order of design)

1. Book page (`/books/{slug}`) — the key conversion/understanding screen: cover, credits, summary, TOC, preview, access explanation.
2. Search results (`/search`) — facets, sort, empty state with query suggestions.
3. Home (`/`).
4. Reader (`/read/{slug}`) — chapter navigation, settings panel, annotation panel, progress.
5. Login / password / TOTP.
6. Library, notes.
7. Admin: Review item, Job detail, Sources, Catalog editor, Access.

Clickable prototypes for 1–4 are produced and signed off before service depth (gates G4/G5).
