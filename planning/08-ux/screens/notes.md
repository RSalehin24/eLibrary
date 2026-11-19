# Notes

Status: DRAFT

**Purpose**: list the user's highlights, notes and quotes across all books and jump to the exact place.
**Primary action**: open a note's location in the reader.
**Route**: `/notes`. **Auth**: signed in. **Service owner**: reader. **Requirements**: REQ-RDR-018, 019, 017. Placement as a top-level destination versus a Library scope is **OPEN U-7** (REQ-WEB-014 does not list it).

## Data

`GET /me/notes` (deep-link data `{slug, anchor, anchor_state}`, orphans listed), `GET /me/annotations/export?format=md|json` (SHOULD), `PATCH/DELETE /highlights/{id}`, `DELETE /bookmarks/{id}`.

## Content

Tabs: All, Highlights, Notes, Quotes, Bookmarks; filter chips by colour; text search over note text; group by book. Each row: quote or bookmark label, note, book title, section, colour chip, orphan chip when the anchor cannot be placed. Orphans stay visible and are never deleted automatically.

## States

| State | Behaviour |
|---|---|
| Loading | skeleton rows |
| Empty | "No notes yet. Select text in a book to highlight it." |
| Ready | list |
| Error | inline banner with Retry |
| Forbidden | not applicable (own data); a book the user can no longer read shows the note with an unavailable chip and no Open action |
| NotFound | deleted note: row disappears, snackbar |
| Offline | banner; list from memory |

## Layout

| Class | Layout |
|---|---|
| compact | list with drill-in to the note, tabs scroll |
| medium | list with a side sheet detail |
| expanded, large | master-detail: list left, note and book context right |

## Actions

Open location (`/books/:slug/read?at=`), edit note, recolour, delete (confirm for notes with text), export (Markdown or JSON, own data), re-place an orphan manually.

## Copy keys

| Key | en | bn |
|---|---|---|
| `ux.notes.title` | Notes | নোট |
| `ux.notes.empty` | No notes yet | এখনো কোনো নোট নেই |
| `ux.notes.open` | Open in book | বইয়ে খুলুন |
| `ux.notes.export` | Export | এক্সপোর্ট |
| `ux.notes.orphaned` | Place not found | স্থান পাওয়া যায়নি |

Analytics: none. Accessibility: list with headings per book, colour never the only signal (text label on the chip), keyboard row actions in a menu.
