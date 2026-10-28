# Reader module: M2

Implement R01–R05 after W08 website acceptance. Define interfaces during F02; extract the service only in this milestone. The website owns authentication and personal records throughout.

| Plan | Tasks and responsibility |
| --- | --- |
| [Service extraction and offline](service/extraction-and-offline.md) | R01 build/proxy/session boundary; R04 rich media, local EPUB, privacy, PWA |
| [Commands, layout, and reading state](experience/commands-layout-and-state.md) | R02 layout/registry/fullscreen; R03 anchors/progress/search/annotations |

## Existing implementation to preserve

Read `app/web/src/components/{book-reader,local-book-reader,reader-frame,reader-contents,reader-search,reader-annotations,reader-settings}.tsx`, `src/lib/reader-*`, `src/lib/{progress-writer,reading-progress,update-coordinator,account-channel}.ts`, and `src/lib/local-epub`. Backend access/reading, annotation, protected-resource, and preparation code stays website-owned unless extracted as pure reusable preparation logic for the engine.

Use the retained `app/frontend/public/epub-reader` as the rich-feature reference, alongside the capability register. Do not copy its bundled third-party files into another hand-maintained fork. Reuse correct first-party behavior and existing dependencies.

## R05 acceptance

- Reader has an independent build/configuration/start/health/test artifact, same-origin routing, distinct assets, and no separate account database. Website→reader→website, deep links, refresh, back, and new tabs all work.
- At ordinary desktop and portrait-phone sizes, canvas height is at least 80% of visual viewport height with normal controls and panels closed. In fullscreen after controls hide, canvas is at least 98%. Landscape/enlarged-text expectations are defined in the experience plan and recorded separately.
- Primary A−/A+, contents, fullscreen, settings, and search are discoverable. Every command uses one registry and has a keyboard path/help. Actual events work in chapter frames, toolbar, dialogs, and fullscreen without hijacking typing/media/browser controls.
- Every typography/view/orientation/resize change preserves the verified current passage. Search/contents/Notes links reach exact expected targets, and saved new activity resumes after reopening.
- Concurrent progress, failed writes, logout/account changes, revoked access, read-once sessions, and active-build replacement follow the shared contracts. Nothing silently reports Saved after a failed/uncertain request.
- Scroll/single/spread, nested contents, poetry, images/tables/footnotes/internal/external links and media pass feature comparison. No authored script, unrelated authenticated request, unsafe path/archive, or cross-account resource succeeds.
- Device-local files remain local and work with the installed public offline shell. Cache inspection contains no private library content. Update/reload waits for drafts/mutations/progress; an update accepted in one tab does not reload another tab.
- Relevant unit/backend/browser checks and all five simulator profiles pass with current rendered evidence and user visual/UX acceptance. Physical devices and external services retain separate unverified status unless actually tested.

R05 remains open for any identified functional, security, visual, or UX issue. A layout ratio alone does not establish an enjoyable or complete reading experience.
