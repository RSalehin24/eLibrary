# Reader commands, canvas, locations, and persistence

Tasks R02/R03. Reuse existing renderer, gesture, CFI/text/media-position, frame-binding, search, progress-writer, and annotation code; verify each behavior against current books and the retained reader.

## R02: reading layout and preferences

The canvas fills the available viewport width by default; width 0 means no artificial maximum column. Retain optional 640/800/1040px widths clamped to available space. Retain current font choices (serif/sans/publisher), paper/sepia/dark themes, 14–40px font-size range with 2px steps, and 1.4–2.4 line-height range with 0.1 steps. Defaults match `reader-preferences.ts`: 20px, paper, scroll, serif, line height 1.9, full width. Load valid current-application preferences; absent/corrupt/unsupported storage falls back to these defaults. Single-character shortcuts default enabled with the documented disable setting. No old application preference migration is required.

Place A−, A+, contents, fullscreen/focus, settings and search in predictable compact primary controls, with secondary commands in a labelled tools menu. Keep title/return/language compact; no website navigation, long explanation, or permanent large pagination block. Scroll, single-page and two-page spread views remain available; narrow spread can collapse to one visible page while retaining the selected preference. Page totals are meaningful only after current layout measurement; show an honest loading/unknown state during recalculation.

With panels closed, ordinary desktop/portrait reading gets at least 80% of viewport height. For landscape expect at least 70%; for 200% text expect at least 60%, with every control still reachable and scrollable panels when necessary. Record actual dimensions and an explanation of browser safe areas. The canvas element includes safe-area padding; content/tools never overlap cutouts. Fullscreen at idle still requires at least 98% canvas height in every supported orientation.

Native fullscreen is preferred; unsupported/denied fullscreen offers focus mode through the same command and visible feedback. Reveal temporary chrome by pointer movement toward the top, an unselected center tap, or keyboard focus/command. Hide it after 2.5 seconds of inactivity, except while focus is inside controls or a panel/dialog is open. At idle no Show Controls/Exit/page buttons remain over text. The first reveal tap does not also turn a page or dismiss a selection. Esc closes the topmost panel first, then exits native fullscreen/focus; returning focus goes to the invoking control/canvas without changing passage.

## Single command registry

Each registry entry contains stable ID, bilingual label/help, bindings, enabled predicate, disabled reason, handler, mode capability, and toolbar/menu placement. Toolbar, keyboard dispatch, help, settings, and both reading modes read that entry; there are no duplicate handlers with drifting behavior.

| Command | Binding | Conditions/result |
| --- | --- | --- |
| Fullscreen/focus | `F` | Toggle mode; preserve passage; denied native request has focus-mode recovery. |
| Close panel/leave mode | `Esc` | Topmost modal/panel first; don't erase unsaved annotation drafts silently. |
| Contents | `T` | Nested current chapter/ancestors, collapse/expand and exact target. |
| Settings | `S` | Typography, theme, width, view and shortcut preference. |
| Search | `/` | Focus search; all-chapter mode; never hijack typing. |
| Shortcut help | `?` | Registry-generated labels, bindings and disabled reasons. |
| Increase/decrease font | `Ctrl/⌘ +`, `Ctrl/⌘ −` | Same handlers as A+/A−; clamp at range boundaries. |
| Paper/sepia/dark | `Ctrl/⌘ 1/2/3` | Immediate theme and visible current choice. |
| Cycle view | `V`, reverse `Shift+V` | scroll → single → spread, reverse cycle. |
| Cycle font | `G`, reverse `Shift+G` | serif → sans → publisher. |
| Cycle width | `W`, reverse `Shift+W` | full → 640 → 800 → 1040, clamped to viewport. |
| Line spacing | `L`, reverse `Shift+L` | Increase/decrease within 1.4–2.4. |
| Previous/next page | Arrows, Page Up/Down, existing Space/Shift+Space | Real current-view page movement, chapter boundaries and no extra blank page. |
| Previous/next chapter | `[`, `]` | Valid adjacent spine target; boundary disables action. |
| Bookmark | `B` | Current verified location, enabled only when mode persistence supports it. |
| Annotations | `A` | Mode-supported annotations; no account action in local mode. |
| Highlight | `H` | Valid active text selection and supported annotation persistence. |

Dispatch only with reader/canvas/toolbar context active. Ignore already handled events, IME composition, editable/form elements, active media controls, unsupported modifiers, unrelated browser shortcuts, and modal shortcuts owned by another dialog. Text selection blocks page-turn gestures; H can act on that selection. Bind each chapter frame exactly once and remove handlers when replaced. A setting disables single-character commands including Shift variants; modifier commands and accessible toolbar/menu paths remain. Key help shows the current state. Repeat only intentional bounded page/font actions, never bookmark or mutation submission.

Verify actual events inside chapter iframes, toolbar, open Settings/help/notes/search, selection, fullscreen and focus fallback. Test Bengali/English labels, non-Latin keyboard input, composition, reduced motion, mobile touch/swipe/pinch/double-tap/two-finger behavior retained from the reference, and browser zoom outside reader focus.

## R03: location transition order

Use one passage-capture/restore path for font/size/spacing/width/theme/view/orientation/viewport and delayed font/image layout changes:

1. Capture current build/chapter/text or media anchor and current selection, not raw scroll percentage alone.
2. Suspend position publishing and page turns while applying layout; cancel any previous restore using a transition generation.
3. After fonts and geometry settle, resolve the captured anchor in the same build and move to its verified passage.
4. Resume observation/publishing only after restoration. Keep selection/annotation targets stable and recompute page geometry honestly.

Failed resolution keeps the chapter and explains the fallback; it must not save a fabricated exact location. Old asynchronous chapter/search/resize callbacks cannot move a newly selected chapter. Starting a new navigation cancels old navigation work; success is emitted only when its current target is rendered.

## Progress, multiple sessions, and updates

Implement the exact revision/mutation-ID contract in [data and state](../../shared/contracts/data-and-state.md). Preserve the existing 2-second debounce, 15-second periodic flush, one in-flight writer, failed-save indicator and explicit retry. On failure retain the latest queued position; an older failed write never replaces newer local movement. Defer periodic/debounced writes after failure until explicit recovery. Best-effort unload is not proof that progress was saved.

No percent-based winner or timestamp from a device decides cross-tab ordering. Reconcile lost responses through the same mutation ID; distinguish uncertainty from a true stale-revision conflict. Receiving another tab's revision suspends writes until the confirmed passage is resumed or the local passage is explicitly chosen; simply copying its revision would permit a stale overwrite. Apply the explicit choices and no-broadcast fallback in the shared contract. Account switch aborts pending work; no user B request receives user A's capture.

The session uses a concrete prepared build. A new published build does not reinterpret old anchors. An open session's still-authorized leased files may finish safely; a genuinely new opening uses the active build under the shared read-once/lease rules. Old-build saves cannot replace active-build progress. If a prior location no longer resolves, show a truthful restart/chapter fallback. No old-edition migration, old-ID bridge, or mandatory historical file archive is added. Keep observation/save disabled until initial session load, target resolution and restoration succeed; a loading/error/expired page cannot enqueue the default start position during mount or unload.

## Search, contents, and annotations

- Contents retains nested hierarchy/current chapter, expands ancestors, supports collapse/keyboard and long labels, and navigates to the actual linked fragment/spine position.
- Full-book search follows actual spine order, reports partial/unavailable chapter errors separately from No matches, cancels on new query/book/unmount, and ignores late old results. Search never modifies stored progress before a result is deliberately opened.
- Result navigation and Notes links resolve a verified current-build passage, including a late annotation overlay. Open the correct chapter first, then restore the precise range/location.
- Bookmark/highlight/quote/note creation captures exact chapter/selection context before opening tools. Mutation pending disables duplicate click/shortcut submissions. Save/delete/color/kind changes honor ownership and revision, preserve drafts on conflict, and refresh only affected views.
- Closing a note panel with unsaved text requires the existing draft guard; a PWA update, toolbar action, or background refresh cannot erase it. Keep Edit and Go to passage separate.

**R02/R03 regressions:** current-passage equality across every reflow/view switch and orientation; chapter edges/page labels; no scrolling publishes during restore; exact nested TOC/search/Notes links; full event-dispatch matrix; idle fullscreen chrome; latest save after failure; timeout/duplicate ACK; two tabs writing in opposite reading directions; repeated conflict; stale build; revocation/logout; annotation late-load/selection retention; listener/object cleanup after repeated chapter changes. Extend current reader unit tests and `tests/web/e2e/{reader,reader-language,reader-bookmark-precision,personal-notes}.spec.mjs` plus backend concurrency/annotation tests.
