# catalog — state machines

Status: DRAFT

## Book

```
 Draft ──publish──► Published ◄──restore── Archived
   │                   │  └──archive──────────▲
   └─────delete────────┴───delete──► Deleted (terminal; soft)
```

| Transition | Preconditions | Effects |
|---|---|---|
| publish | credit rule; `artifact_set_id` sealed in content; expected revision | emit `BookPublished`; index; sitemap |
| archive | — | remove from index/public; keep artifacts; emit `BookArchived` |
| restore | previous state was Published | re-index |
| delete | — | remove from index; schedule artifact retention clock |

Typed: `Book<Draft>::publish(self, Sealed) -> Book<Published>`; persistent state is an enum (INV-CAT-001).

## Override lifecycle

`source value → admin override (active) → [source changes] → override flagged stale (visible to admin, still effective) → admin accepts source or keeps override`.

## Agent merge

`Active → Merged(into)` with a `MergeRecord`; credits re-pointed in one transaction; aliases union; `split` restores from the record; chained merges resolve by following `into` (depth bounded, cycles impossible because merge requires `into` to be Active).

## Search index

`Building → Serving(snapshot n) → Rebuilding(n+1, shadow) → swap → Serving(n+1)`; queries never read a half-built index.
