# Reader

Status: DRAFT

**Purpose**: read one book in the browser, comfortably, in light, dark or sepia, and annotate it.
**Primary action**: read (turn or scroll); annotate is secondary.
**Routes**: `/books/:slug/read` (`?at=` an anchor or highlight id from the Notes deep link). **Auth**: `read` plus a reading ticket. **Service owner**: reader (ticket minting and verification: identity). **Requirements**: REQ-WEB-021; REQ-RDR-005..025; D-28, D-37, D-46, D-48. Flows: [open and read](../flows/open-and-read.md), [annotate](../flows/annotate.md).

## Data

`POST /books/{slug}/open` returns the ticket; `GET /tickets/{ticket_id}/book` (secret in `X-Reader-Ticket`) returns the whole package; `GET /books/{slug}/copy` for the building state; progress, bookmarks, highlights and notes endpoints; `GET/PUT /me/preferences`; optional `GET /tickets/{ticket_id}/search` ([reader contract](../../07-contracts/http/reader.md)). The ticket lives only in memory, is refreshed once on expiry and never appears in a URL, storage or log. Unsaved progress is flushed on `visibilitychange` and `pagehide`.

## Reading modes

The renderer is purpose-built for the sanitized whole-book package; v1 has exactly two modes, scroll and paged (D-52; no two-page spread):

| Mode | Behaviour |
|---|---|
| Scroll | continuous vertical flow of the current section with section boundaries; default on compact |
| Paged | one page of columns at a time by tap zone, arrow key, swipe or button; page count derived from layout |

Every gesture has a button and key equivalent (arrows, space, PageUp and PageDown, Home and End). Position is a section plus offset, so changing mode, size or rotation keeps the place. Immersive mode hides chrome (key `F`, tap on a non-interactive area); Esc leaves it; browser zoom is never hijacked.

## Controls

Top bar (auto-hides, comes back on tap or key): back to the book, title and section, contents (TOC tree with the current item and ancestors open), search (SHOULD, when enabled), bookmarks, notes, display settings. Bottom: progress as percent and section, slider for position (labelled).

Display settings: theme (Follow app, Light, Dark, Sepia), font size 14-28, family (serif Noto Serif Bengali, sans), line height, margins, alignment (left, justified without hyphenation). Bengali defaults: serif, 18 px, line height 1.8, measure 60-75 characters. Preferences are stored per user (D-48; location **OPEN O-6**, recommended reader service) and applied before the first paint of the page.

Theming uses CSS variables on the sanitized container; no forced overrides of publisher markup (REQ-RDR-020). Annotation colours are the five tokens, defined once.

## Annotating

Selecting text (pointer, touch, or keyboard selection) opens an annotation popover on medium and larger windows and a **bottom sheet on compact**: five colours, note, save as quote, copy, bookmark. The note field opens in a labelled dialog or the sheet's text area (focus trapped, `Ctrl/Cmd+Enter` saves, Esc cancels). Existing highlights open the same surface to edit text, recolour or delete (confirm for notes with text). Notes list and bookmarks list open as a bottom sheet on compact, a side sheet on medium, a supporting pane on expanded and large. Orphaned annotations (their text no longer exists in a new version, D-46) stay listed with an "Orphaned" chip and a manual re-place action.

## States

| State | Behaviour |
|---|---|
| Loading | "Opening" with progress; ticket, then package; skeleton lines |
| Empty | a book with no readable sections: "This book has no readable text" with link back (should not happen after the gate) |
| Ready | reading surface |
| Error | package or render failure: message with Retry and Back; never blank, never `alert` |
| Forbidden | no `read`: "You do not have access to read this book" (reason: no grant, read-once used, book not published); sign-in expired (401): sign-in and return to the same place |
| NotFound | slug unknown or unpublished |
| Offline | reading continues from memory; annotation writes queue with retry and a visible "not saved" marker; progress resumes with revisions |

Special states: copy still building ("Preparing the book, this can take a minute", polite retry); ticket expired (one silent re-open, then a message); read-once consumed (explained, with ask-an-administrator); `copy_unavailable` after a new version (re-open once).

## Layout

| Class | Layout |
|---|---|
| compact | full-bleed; scroll default; chrome hides; notes and settings as bottom sheets; tap zones with button equivalents |
| medium | full-bleed; side sheet for notes and contents |
| expanded | centered measure; supporting pane for notes and contents |
| large | centered measure (not wider than reading comfort), one column or page |

Safe-area insets respected; orientation change keeps the position. App navigation is hidden in the reader.

## Copy keys

| Key | en | bn |
|---|---|---|
| `ux.reader.contents` | Contents | সূচিপত্র |
| `ux.reader.settings` | Display | প্রদর্শন |
| `ux.reader.theme.follow` | Follow app | অ্যাপ অনুযায়ী |
| `ux.reader.theme.sepia` | Sepia | সেপিয়া |
| `ux.reader.highlight` | Highlight | হাইলাইট |
| `ux.reader.addNote` | Add a note | নোট যোগ করুন |
| `ux.reader.bookmark` | Bookmark | বুকমার্ক |
| `ux.reader.progress` | {percent}% read | {percent}% পড়া হয়েছে |
| `ux.reader.building` | Preparing the book | বইটি প্রস্তুত করা হচ্ছে |
| `ux.reader.orphaned` | Orphaned | অনাথ (স্থান হারানো) |
| `ux.reader.notSaved` | Not saved, will retry | সংরক্ষিত হয়নি, আবার চেষ্টা হবে |
| `ux.reader.forbidden` | You do not have access to read this book | এই বইটি পড়ার অনুমতি আপনার নেই |

Analytics: none (opens are audited server-side by the reader, not tracked in the UI).

## Accessibility

All actions by keyboard (section and page stepping, TOC, annotate); location changes announced politely; targets 48 px; reduced motion removes page animation; themes meet contrast including sepia and highlight tints; the notes list is navigable as text; the reading surface is a labelled region with `lang` from the book.

## Open

P-3 (ticket for superseded version), U-10 (in-book search shown or not: SHOULD, REQ-RDR-023).
