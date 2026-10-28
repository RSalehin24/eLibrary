# বাংলা পাঠাগার: website, ebook reader, and book-creation plan

**Prepared:** 21 October 2026

**Status:** Planning document. Implementation and acceptance remain outstanding.

**Delivery order:** Website → standalone ebook reader → intelligent curation and book-creation engine.

**Revised product decisions:** One book model, no physical-book features, no review/check workflow, admin-only cover and metadata editing, and a clean development rebuild wherever useful. These decisions supersede the earlier preservation and migration requirements.

This document brings the reported problems, additional investigation areas, product decisions, implementation work, and acceptance criteria into one place. Earlier implementation reports are historical evidence; they do not establish acceptance of this revision. Existing working-tree changes must be checked against this plan before being marked complete.

The objective is a complete, consistent product with usable admin and reader workflows, followed by a source-grounded engine that understands book structure and bibliographic credits. Passing a build or loading a page is not sufficient evidence of completion.

## Contents

1. [Decisions and boundaries](#1-decisions-and-boundaries)
2. [Three independent services](#2-three-independent-services)
3. [Issue register and audit method](#3-issue-register-and-audit-method)
4. [Plan A: website and admin experience](#4-plan-a-website-and-admin-experience)
5. [Plan B: standalone ebook reader](#5-plan-b-standalone-ebook-reader)
6. [Plan C: intelligent curation and book creation](#6-plan-c-intelligent-curation-and-book-creation)
7. [Delivery sequence and acceptance gates](#7-delivery-sequence-and-acceptance-gates)
8. [Complete page inventory](#8-complete-page-inventory)
9. [New-session handoff](#9-new-session-handoff)

## 1. Decisions and boundaries

| Decision | Required behavior |
| --- | --- |
| Three independent services | Website, reader, and creation engine have independent builds, configuration, health checks, tests, and releases, in the same repository. |
| No spending | No paid APIs, subscriptions, purchased hosting, or additional hardware. Use available infrastructure and local inference. Do not fall back to paid services. |
| Implementation order | Finish the website and reader acceptance gates before implementing the intelligent engine. Define their interfaces early to prevent rework. |
| Languages | Bengali and English throughout the interface. Preserve book text, titles, and credited names in their original language. |
| Source | Automated creation uses one configured source website. Its identity belongs in configuration, not provider-specific names in application code or navigation. |
| Book model | Everything is a book. Remove the physical/digital distinction from storage, APIs, filters, exports, forms, labels, and documentation. Remove physical-book records and physical-only reading logs/features. |
| Manual import | Keep EPUB upload as another way to add a book. Do not label the resulting record a digital book or require a type selection. |
| Publication | Books become available automatically after preparation succeeds. There are no review/check/approve pages, buttons, badges, pending-review states, or manual publication gates. Automatic correctness enforcement runs inside the engine. |
| Book editing | Only administrators can see or use Edit for book covers and metadata. Enforce this on every relevant API as well as in the interface. Readers can still manage their own profiles and annotations. |
| Incomplete source books | The source website's unfinished classification is separate from collection, extraction, generation, or application defects. |
| Administration | Admin users primarily enter Admin and can switch to their personal Reader View with the same account. Switching view never changes permissions. |
| Time | Use Asia/Dhaka and a 12-hour clock, with correct localized dates, digits, and day periods. |
| Presentation | No underlined navigation or decorative heading counters. The logo includes বাংলা পাঠাগার without a repeated adjacent name. |
| Development data | No requirement to migrate or retain existing IDs, accounts, grants, books, files, source records, old editions, notes, highlights, bookmarks, progress, checkpoints, or queue messages. Rebuild development data whenever that produces a cleaner application. |
| Completion | Deliver a polished, consistent visual design and intuitive, complete admin and reader experiences. Observable defects or unfinished flows mean the work is incomplete even if automated tests pass. |

New dependencies remain subject to [AGENTS.md](../AGENTS.md). The local model and runtime below are proposed dependencies; this document does not install them or authorize paid resources.

### Clean development rebuild

The user authorizes clearing or rebuilding this application's development databases, generated files, obsolete records, checkpoints, and queues when needed. A fresh schema and clean initialization are acceptable. Do not add migration bridges, historical archives, compatibility layers, or backup/restore work merely to carry disposable development data forward. Remove the old physical-book records rather than converting them into empty books.

Current product behavior still needs to work: newly created books must match their source, permissions must be enforced, and users must be able to save and resume new reading activity. Source evidence needed to create the current book and checkpoints needed to resume an active job are operational tools, not obligations to retain old development data. Historical generated editions and old identifiers are not release requirements.

Resetting development data must not affect unrelated applications, external services, or credentials. Do not send external email or Kindle messages merely because a clean rebuild is permitted.

### What completion means

Completion means the finished product has a coherent, polished visual design and intuitive UX across the entire website and reader: consistent typography, spacing, controls, navigation, content hierarchy, responsive behavior, and complete task flows. Every page, section, interaction, and supported state must meet that standard. A mockup, an attractive landing page, or a passing test suite does not establish completion.

All identified visual, functional, and UX issues must be resolved. The inventory must expand when exploration finds another page, state, or defect; it cannot be used to exclude an inconvenient finding. A newly discovered issue reopens the relevant acceptance gate. Final acceptance includes rendered-page inspection, realistic end-to-end use, and the user's visual and UX acceptance.

Record implementation and verification evidence for every requirement. Functional and security checks must pass. Do not close an issue by replacing screenshots, weakening assertions, hiding errors, skipping difficult books, or lowering the design standard. There is no data-preservation acceptance gate.

## 2. Three independent services

| Service | Owns | Interfaces and boundaries |
| --- | --- | --- |
| **Website** | Public catalog, accounts, permissions, personal library, annotations, Kindle workflows, publication records, and admin interface. | Unified book APIs, admin-only cover/metadata editing, engine commands, and automatic acceptance of prepared book builds. |
| **Ebook reader** | Reading interface, EPUB rendering, typography, navigation, search, fullscreen, gestures, and device-local EPUB reading. | Website APIs for authorized sessions, resources, progress, and annotations. No separate account database. |
| **Curation and creation engine** | Source discovery, collection, snapshots, entity extraction, structural understanding, jobs, schedules, validation, generation, and update detection. | Private versioned command/status/artifact interfaces and idempotent publication handoff to the website. |

### Integration requirements

- Define clear public URLs for the clean application. Route reader and local-reader pages to the reader service through the same-origin proxy; give reader build assets a distinct prefix. Old development URLs do not require compatibility redirects.
- Use full document navigation at service boundaries so one application's client router does not attempt to render another application's pages.
- Retain website session authentication and account isolation. Do not introduce bearer credentials into reader URLs.
- Give the engine its own logical database and storage ownership. Reference current website accounts and books through IDs and revisioned contracts, not cross-service ORM joins. These IDs need not match old development records.
- Authenticate private service calls with scoped, short-lived credentials. Recheck current authority at protected processing boundaries and before publication.
- Define unified book schemas and private engine contracts. Remove obsolete type/review fields and endpoints, update every caller together, and generate client types from the actual schemas. Do not maintain compatibility for removed development features.
- Transfer generated artifacts with checksums. Activate complete, correct book builds atomically. Do not require previous builds, old editions, or their migration.
- Use durable outbox/inbox records and idempotency keys so retries cannot create duplicate jobs, books, or publications.
- Share existing infrastructure where appropriate. Independently deployable product services can contain API, worker, scheduler, and inference processes.
- Clear obsolete development checkpoints, queue messages, records, and artifacts when required for a clean initialization. Test the new application from a fresh start rather than making old state a release dependency.

## 3. Issue register and audit method

### Initial issue register

“Reported” means the user encountered the problem and current behavior needs rechecking. “Confirmed” refers to inspected implementation or planning-time evidence. Neither status implies that an earlier attempted fix has been accepted.

| ID | Issue or concern | Evidence/status | Workstream |
| --- | --- | --- | --- |
| WEB-01 | Different pages use competing control, typography, spacing, and alignment rules. | Confirmed styling structure; repeatedly reported visually. | Shared design system. |
| WEB-02 | Header wraps or breaks; admin and general navigation are not consistently distinguished. | Reported; existing changes need fresh acceptance. | Both shells and responsive navigation. |
| WEB-03 | Important admin actions and destinations are hard to discover. | Reported. | Navigation and task hierarchy. |
| WEB-04 | Cards have unequal heights and inconsistent metadata/action placement. | Confirmed wrapper/stretch problem; attempted fix remains unverified. | Shared book cards. |
| WEB-05 | Search, sort, and Filter controls have different heights and font metrics. | Confirmed rendered measurements. | Shared browse controls. |
| WEB-06 | Export headings, buttons, and instructions occupy disproportionate space. | Confirmed component structure; compact disclosure needs acceptance. | Export controls. |
| WEB-07 | Filters include unwanted book-type and added/request-date fields or excessive empty space. | Reported; search saved filters and old URLs too. | All browsing and administrative lists. |
| WEB-08 | Notes has broken alignment, spacing, or card layouts. | Reported; previous repairs require current-state verification. | Notes views, toolbar, and annotation cards. |
| WEB-09 | Automation and Users & Access lack coherent layout and clear workflows. | Reported; previous repairs require current-state verification. | Administrative lists and forms. |
| WEB-10 | Unfinished Books misses the compact source-page container and has a confusing hierarchy. | Confirmed container mismatch; attempted fix remains unverified. | Unfinished workspace. |
| WEB-11 | Book details do not reliably expose covers, Read, Save, Kindle, HTML, and EPUB actions. | Reported; test ready, unavailable, and denied states independently. | Book details and list actions. |
| WEB-12 | Pagination lacks usable numbers or loses filter/page context. | Reported; prior URL-cleanup defect requires regression coverage. | Shared pagination. |
| WEB-13 | Bengali wording is unnatural or mixed with English interface text; time formatting is inconsistent. | Reported. | Translation and date audit. |
| WEB-14 | Authors, categories, series, and reading lists lack useful lists or related-book links. | Reported; include public and personal visibility rules. | Directories and entity details. |
| WEB-15 | Physical-book features and the physical/digital type distinction remain in the application. | User requires full removal, including records, logs, schema fields, APIs, filters, and labels. | Unified book model and clean initialization. |
| WEB-16 | Review/check/approve workflows and labels remain or are implied. | User requires their removal; automatic preparation must not become an admin checking task. | Lifecycle model and all book surfaces. |
| WEB-17 | Cover/metadata editing can be exposed or granted to non-admin users. | Required authorization audit. | Admin-only Edit controls and APIs. |
| READ-01 | Text is confined to a narrow central column instead of using available screen space. | Confirmed former 800px default; full-width change needs acceptance. | Reader canvas and width preferences. |
| READ-02 | Font-size actions are hidden inside Settings. | Confirmed; toolbar changes need acceptance. | Primary reading controls. |
| READ-03 | Excessive header, toolbar, and pagination content takes space from the book. | Reported and evident in the layout structure. | Reader chrome and fullscreen. |
| READ-04 | Fullscreen shows unwanted persistent controls or lacks intuitive access to tools. | Reported; test idle and deliberately revealed states. | Immersive interactions. |
| READ-05 | Settings and actions lack a complete, discoverable shortcut system. | Confirmed limited command coverage. | Shared command registry. |
| READ-06 | Rich EPUB behavior may differ from the previous reader. | Requires feature-by-feature comparison. | Views, gestures, media, contents, and annotations. |
| READ-07 | Reflow and chapter navigation can lose the current reading passage. | Required regression area for the new application; no historical position migration is required. | Anchors and current reading progress. |
| ENG-01 | A valid file can still be poorly chaptered or semantically misstructured. | Confirmed gap between text integrity and structural understanding. | Canonical document planning. |
| ENG-02 | Canonical export deliberately skips late chapter inference. | Confirmed code path; structural inference must happen earlier. | Pre-canonical structuring. |
| ENG-03 | Export verification checks text occurrence without fully proving EPUB spine order. | Confirmed verifier behavior. | Independent order-aware verification. |
| ENG-04 | Contributor extraction relies on heuristics, fixed confidence values, and a few specific corrections. | Confirmed implementation. | Evidence-based entity extraction and resolution. |
| ENG-05 | Source headings, numbering, typography, and contextual boundaries may remain inside one body section. | Corpus investigation candidates; not all single-flow works require splitting. | Chapter intelligence. |
| ENG-06 | Collection failures, unavailable source content, and application defects are hard to distinguish. | Reported; retain real causes and recovery paths. | Classification and recovery. |
| ENG-07 | Administrators cannot easily identify which unfinished works actually changed. | Reported; compare body, structure, and metadata changes. | Update detection and presentation. |
| ENG-08 | “Prepared” can be shown without proving usable HTML, EPUB, and reader resources. | Reported; enforce end-to-end readiness. | Publication gate. |
| QA-01 | Earlier reports and passing layout tests overstate visual or functional acceptance. | Confirmed mismatch between recorded claims and unresolved feedback. | Evidence and completeness reporting. |
| QA-02 | Unreported defects may exist in pages, dialogs, forms, and failure states. | Explicit investigation requirement. | Full inventory audit. |
| QA-03 | Preservation and migration obligations distract from a clean development application. | User explicitly removes these obligations and permits rebuilding development state. | Architecture, initialization, and release criteria. |

### Audit every portion of every page

For each route and dynamic variant, inspect its shell, heading, local navigation, search, filters, result summary, cards/table, actions, forms, dialogs, feedback, pagination, exports, and footer. Mark absent portions as not applicable rather than silently omitting them.

For each applicable portion, inspect populated, loading, empty, no-match, failed, unavailable, stale, saving, success, permission-denied, and disabled states. Include keyboard focus, pointer interaction, touch behavior, translated labels, enlarged text, delayed data, and image failures.

Each issue record must contain reproduction steps, affected route/state, screenshot, expected behavior, root cause, implementation task, regression check, and accepted evidence. Status transitions are **investigate → confirmed → implemented/unverified → verified**. Record the regression demonstrating the original failure and the corrected behavior.

### Previous-version completeness report

Use the pinned previous-version baseline recorded in [feature parity](operations/feature-parity.md), the retained frontend, and the previous embedded reader as functional references. Record each capability as present, missing, incomplete, intentionally removed/changed by the user, or verified. Physical-book functionality, physical/digital classification, review workflows, and historical-data migration must be marked intentionally removed. Include each remaining capability's destination and interaction evidence. Do not use one overall completion percentage to hide feature gaps.

## 4. Plan A: website and admin experience

### A1. Establish one design system

- Use a shared 4/8/12/16/24/32px spacing scale with clear separation between sections and smaller gaps inside related controls.
- Standardize typography, border treatment, surface colors, content widths, control padding, focus rings, and responsive breakpoints.
- Give controls a 44px minimum target. Related toolbar controls must align and have matching normal-size heights. At enlarged text sizes, permit growth without clipping.
- Define primary, secondary, destructive, and icon-only actions. Use consistent icons and accessible names; expose text where an icon alone would be unclear.
- Reuse components for headings, toolbars, filters, cards, tables, tabs, disclosures, forms, dialogs, feedback, exports, and pagination. Remove conflicting overrides rather than adding another patch layer.
- Keep primary content near the beginning of the page. Instructions, exports, technical identifiers, and secondary controls must not dominate it.
- Maintain a calm library presentation with the combined বাংলা পাঠাগার wordmark and consistent active navigation.

### A2. Page and section work

| Page family | Required audit and resulting behavior |
| --- | --- |
| General-user shell | Stable logo/header; My Books, Browse, Notes, and Kindle navigation; account/language controls; mobile safe areas; active section; footer without overlap. |
| Admin shell | Permission-filtered sidebar, labelled mobile drawer, visible account actions, correct default destination, same-account Reader View, and clear return to Admin. |
| Home and My Books | Useful signed-in landing, Continue Reading, owned/saved/recent/granted views, clear membership actions, accurate counts, and meaningful empty/error states. |
| Catalog and search | Compact title/search/sort row, consistent control sizes, optional useful facets, preserved conditions, working clear/reset behavior, and prompt result placement. |
| Book cards | Equal heights within a row, consistent cover treatment, readable title/credits, aligned footer actions, saved state, Kindle, and progress inside the card. Do not truncate content merely to force equal height. |
| Book tables | Readable columns, stable action positions, consistent row density, sensible horizontal scrolling or mobile transformation, and no moving links after account data loads. |
| Public book details | Prominent cover, title and credits; Read/Continue, Save, Kindle, EPUB, and new-tab HTML; linked metadata; clear progress, notes, and availability. Admins alone see Edit for the cover and book information. No type or review labels. |
| Personal book details | The same reading hierarchy with account-specific notes/progress and preserved personal-library context. |
| Other editions | Where bibliographic editions are relevant, show their current identity, links, and access. Do not build a historical generated-file archive or migrate old edition data. |
| Authors and contributors | Author-first directory, explicit other roles, clean names, accurate linked-book counts, and working related-book links. |
| Categories, series, reading lists | Consistent directory/detail layouts, clear terminology, compact search and sorting, meaningful counts, and linked results. Use পাঠতালিকা / Reading Lists for curated lists. |
| Notes | Four reachable views; aligned search/color controls; consistent book groups and annotation cards; separate editing and exact reader navigation; distinct empty, no-match, and retry states. |
| Kindle | Discoverable send controls, understandable recipient selection and confirmation, operation details, history, explicit resend, compact filters, and honest uncertain-delivery status. |
| Profile and security | Coherent identity/photo/password/recipient/security sections, clear validation and feedback, accessible file selection, and conditional two-factor steps. |
| Login and password flows | Usable labels, validation, pending states, password setup/reset recovery, and two-factor entry only when required by the authenticated flow. |
| Help, About, Contact | Consistent text hierarchy, usable content width, accurate guidance, working links, and bilingual interface copy. |
| Physical-book removal | Remove physical-book records, physical-only reading logs, inventory pages, navigation, creation choices, APIs, schema fields, exports, fixtures, and related code. All remaining records are books with no physical/digital type. |
| Admin overview | Prioritized operational information, real totals, actionable problems, and clear next destinations; avoid an undifferentiated wall of statistics. |
| Book Creation/source catalog | Visible Fetch All, Process All, Upload EPUB, and Scheduling; understandable selection scope, real progress, current states, and useful next steps. |
| Source detail | Clear source identity, linked book, source structure/update information, generated files, reader launch, and relevant recovery controls. No review/check action or pending-review state. |
| Unfinished Books | Consistent source workspace; clear distinction between source-incomplete works and broken processing; all/updated scopes, last synchronization, actual changes, and regeneration progress. |
| Managed books | Compact search/table, covers, linked credits/categories, preparation/availability states, and direct admin Edit/Files actions. No type field, review/check/approve action, or pending-review state. |
| Manual EPUB import | Coherent file/metadata flow, validation, preparation progress, recoverable failures, and a useful completed-book destination. Never describe a record without ready files as a prepared book. |
| Book editor and relationships | Admin-only cover replacement and metadata editing, logical metadata/files sections, clear save actions, intact unsaved forms during normal use, linked entities, and accurate files. No review or approval step after an edit. Historical revision storage is not required. |
| Creation result | Explain the result and next action before technical identifiers; provide actual file, reading, and management destinations. |
| Managed entities | Consistent hub/list/create/edit layouts for every entity kind, contributor roles, linked counts, duplicate handling, and provenance. |
| Processing list and detail | Understandable stages and queue positions, real states, actionable causes, pause/resume/cancel/recovery, and optional technical details. Distinguish queueing completion from book completion. |
| Schedules | Direct Run Now/settings/history, clear task/scope/timing/enabled state, truthful next run, complete reset behavior, and readable execution outcomes. |
| Users, access, invitations, mail | Searchable account directory, coherent detail sections, understandable grants and expiry, correct self-edit restrictions, security, invitations, and mail uncertainty. |
| Missing and removed pages | Useful not-found/unavailable pages with a next action. Remove obsolete physical-book routes; do not add historical compatibility requirements. |

### A3. Rules that apply everywhere

- Remove the physical/digital book type entirely: model fields, enums, serializers, API parameters, facets, saved filters, exports, labels, and forms. Update tests to assert its absence. Scheduling and permission-expiry dates remain functional; added/request-date browsing filters remain removed.
- Literary categories, genres, series, language, and bibliographic edition information remain ordinary book metadata; they must not be confused with the removed physical/digital classification.
- Use real numbered pagination with boundaries, neighbors, ellipses, totals, and retained valid conditions.
- Place exports after results behind one compact Download list disclosure. Export all matching records, not just the visible page.
- Use natural Bengali reviewed against page purpose. Translate interface labels without translating the source book's text or inventing translated contributor names.
- Remove every review/check/approve workflow, badge, filter, required-review state, and user-facing manual-quality instruction. Source/file correctness remains automatic engine behavior. Show preparation, availability, and real processing problems without asking an admin to check each book.
- Expose book Edit only to administrators and enforce administrator authorization on cover/metadata writes. Readers' own profile and annotation editing remain available.
- Remove editorial review fields and their dependencies from schemas, APIs, query conditions, and publication logic. Saving valid cover/metadata edits must not create a review task, unpublish a book, or hide it until approval.
- Test long titles, many credits, missing metadata/covers, saved-state changes, delayed responses, double submission, stale revisions, and expired permissions.

### A4. Website acceptance gate

Every page in the inventory must pass its applicable section/state checks in both languages. At 1366×900, normal catalog results must begin within 320px and a normal admin list must show at least eight ordinary rows where applicable. At 390×844, ordinary browse results must begin within 390px. Exceptional empty/error forms have separate recorded expectations.

The finished website must look and behave as one polished product. Resolve horizontal overflow, clipped labels, overlap, inconsistent controls, unequal cards, poor spacing, unclear hierarchy, inaccessible actions, dead links, and incomplete submission states wherever found. Inspect every section and complete realistic admin and reader tasks; passing geometry assertions alone does not satisfy this gate.

Fresh initialization must contain no physical-book records/features, no physical/digital type fields, and no review/check/approve workflow. Non-admin users must neither see book Edit nor succeed at cover/metadata writes.

## 5. Plan B: standalone ebook reader

### B1. Reading-first layout

- Extract the reader application while retaining working EPUB, security, resource, annotation, and position logic.
- Fill the available viewport with the reading canvas. Default to full-width content, save preferences created in the new application, and keep narrower widths optional. No old preference migration is required.
- Give A−, A+, contents, fullscreen, settings, and search predictable primary controls. Use a labelled tools menu for secondary actions.
- Keep the title, return action, language, and tools compact. Do not use large site navigation, explanatory paragraphs, or permanent pagination blocks as the reading layout.
- In fullscreen, hide persistent chrome. Reveal temporary controls through deliberate pointer/touch/keyboard interaction; do not leave Show Controls, Exit Fullscreen, or page buttons over the book at rest.
- Retain scrolling, single-page, and two-page views. Show progress and chapter information unobtrusively.
- Keep all tools accessible on small screens without an oversized permanent toolbar or controls disappearing beyond the viewport.

### B2. Reader feature inventory

| Area | Required behavior and edge cases |
| --- | --- |
| Opening | Correct prepared edition, cover/title/body order, loading, invalid EPUB, unavailable files, expired access, and retry guidance. |
| Contents | Nested hierarchy, current chapter, ancestor expansion, collapse controls, keyboard operation, exact navigation, and long titles. |
| Typography | Font size, family, line spacing, width, theme, and view changes with immediate feedback and persisted preferences. |
| Page navigation | Real page turns, chapter boundaries, keyboard/touch gestures, orientation changes, correct labels, and no false page totals. |
| Search | All-chapter search, clear results, exact match navigation, cancellation, no match, and partial/unavailable chapter errors. |
| Annotations | Accurate bookmarks, highlights, quotations and notes; editing/deletion; selection preservation; exact links from Notes. |
| Progress | Resume the real passage, retry failed saves, preserve the latest position, and handle multiple tabs/sessions predictably. |
| Fullscreen | Native fullscreen and focus fallback, discoverable gestures/keys, hidden idle chrome, usable temporary tools, and preserved reading position. |
| Rich content | Images, poetry, tables, footnotes, internal/external links, audio/video, safe media seeking, and no autoplay. |
| Local EPUB | Device-only import, offline shell, matching reading controls, malformed archives, resource cleanup, and no accidental upload. |
| Current reading locations | Save and restore text/media positions and annotations created in the new application. Imported old progress, historical CFIs, and edition-migration bridges are not requirements. |
| Accessibility | Consistent names, focus restoration, keyboard reachability, readable themes, enlarged text, reduced motion, and meaningful errors. |

### B3. One command registry

Toolbar actions, shortcuts, help, translated labels, enabled states, and command handlers must use one registry shared by the library and local readers. Unavailable local-reader/account actions must not appear functional.

| Action | Default key |
| --- | --- |
| Fullscreen / focus mode | `F` |
| Close active panel or leave fullscreen | `Esc` |
| Contents | `T` |
| Settings | `S` |
| Search book | `/` |
| Shortcut help | `?` |
| Larger / smaller text | Existing `Ctrl/⌘ +` and `Ctrl/⌘ −` |
| Paper / sepia / dark theme | Existing `Ctrl/⌘ 1/2/3` |
| Cycle reading view | `V`; reverse with `Shift+V` |
| Cycle font | `G`; reverse with `Shift+G` |
| Cycle width | `W`; reverse with `Shift+W` |
| Increase / decrease line spacing | `L` / `Shift+L` |
| Previous / next page | Arrow keys, Page Up/Down, and existing Space behavior |
| Previous / next chapter | `[` / `]` |
| Bookmark current position | `B` |
| Open annotations | `A` |
| Highlight selected text | `H` |

Activate reader commands only in the reader context. Protect form editing, media controls, text selection, and unrelated browser shortcuts. Provide a setting to disable single-character bindings and show current shortcuts beside their actions and in help. Test actual keyboard events in the reading document, toolbar, dialogs, and fullscreen.

### B4. Reader acceptance gate

- At normal portrait phone and desktop sizes, at least 80% of viewport height remains available for reading with normal controls shown. Record separate landscape and enlarged-text expectations.
- After fullscreen controls hide, the reading canvas uses at least 98% of the viewport.
- A−/A+ work without opening Settings. Every setting has a discoverable keyboard path and documented shortcut.
- Changing size, font, line spacing, width, theme, view, orientation, or viewport preserves the current passage.
- Contents and search reach the correct chapter/passage. Reader links from Notes restore the verified target.
- Fullscreen tools remain usable without persistent idle buttons or obscured content.
- No authored scripts, unsafe archive paths, unrelated authenticated network requests, or cross-account resources become accessible.
- Local reading remains offline and device-only. Existing library permission and read-once rules remain intact.

## 6. Plan C: intelligent curation and book creation

### C1. Planning-time findings

The read-only census on 21 October 2026 inspected 4,171 source catalog records, including 60 source-marked unfinished works. It counted 27,195 cached source pages and 2,238 curated documents. Processing continues, so these are a moving snapshot rather than a completeness percentage.

Among curated documents, 327 had one body section; 190 such sections exceeded 20,000 HTML characters, and 101 contained heading or bold markup. These need semantic investigation. A single body section is not inherently wrong: some works are genuinely continuous.

Two implementation gaps are confirmed:

1. Canonical exports intentionally skip late chapter inference to protect verified source text. Improved structure must therefore be established **before canonicalization**, not improvised by the exporter.
2. Existing export checks look for body-text occurrences across HTML/XHTML. This does not independently establish correct EPUB spine order, complete section classification, or good chapter boundaries.

### C2. Audit the entire source corpus

Freeze a catalog revision and account for every source record. Inspect all relevant reading pages, contents pages, linked components, collected content, and bibliographic evidence. Reuse immutable cached source pages when valid; fetch missing or changed material through the controlled source transport.

For every book, record collection coverage, layout family, hierarchy, source/body flow, front/back matter, credits, ambiguities, incompleteness, update evidence, current output, and discrepancies. Finish with a reasoned classification: understood, structurally ambiguous, source-unavailable, or defective. No book may silently disappear from the audit.

Build a source-grounded 300-book reference corpus spanning every observed layout and difficult case, including novels, anthologies, poetry, drama, linked compilations, long unchaptered pages, nested/paginated contents, mixed credits, and incomplete sources. Use 200 for development and reserve 100 for held-out evaluation. Keep related works/editions in the same split. Engineering evaluation establishes the expected entities, boundaries, and reading order outside the product interface. The application exposes no review/check/approve workflow.

### C3. Processing stages

| Stage | Required result |
| --- | --- |
| Discover | Versioned complete catalog, source identity, update scope, and explicit collection status. |
| Collect | All relevant allowed pages in source order, immutable snapshots, page hashes, and component relationships. |
| Parse source blocks | Stable IDs and locations for paragraphs, headings, lists, poetry, images, tables, footnotes, and other content. |
| Understand structure | Source-grounded chapter/section hierarchy, front/body/back roles, component boundaries, and reading order. |
| Extract entities | Bibliographic entities and contributor roles supported by exact source spans and evidence. |
| Resolve identities | Canonical identities and aliases supported by the current source evidence; no name-similarity-only merging. |
| Canonicalize | One versioned document containing blocks, hierarchy, entities, source mappings, and confidence/validation evidence. |
| Generate | HTML, valid EPUB metadata/navigation/spine, covers, and reader resources from that same document. |
| Verify | Independent source coverage, entity evidence, chapter/section structure, file contents, reading order, links, and reader readiness. |
| Publish | Automatic atomic activation after internal preparation succeeds, with an idempotent website handoff and no manual review or approval. |
| Monitor | Material source-change detection, understandable update summaries, safe regeneration, and version-aware recovery. |

### C4. Intelligence without paid APIs

Use deterministic evidence first: explicit source navigation, labels, typography, numbering, neighboring blocks, and repeated structural patterns. Use local model inference for ambiguous decisions.

The initial benchmark candidate is [Qwen3-4B GGUF, Q4_K_M](https://huggingface.co/Qwen/Qwen3-4B-GGUF), served privately through [llama.cpp](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md). Pin model/runtime revisions and checksums before installation. These are candidates to evaluate, not a claim that this model already meets the required Bengali extraction accuracy.

Default execution policy:

- One inference worker, bounded context windows, overlapping neighboring source context, and a carried-forward outline.
- Structured, schema-validated decisions containing source block IDs and evidence references.
- Cache decisions by source content, extractor, model, prompt, and schema versions.
- No model execution on ordinary website or reader request paths.
- No paid endpoint, free-tier dependency, or automatic cloud fallback.
- Resource preflight and explicit waiting states when memory/disk are insufficient. Available planning-time hardware was 8 GB RAM with approximately 12 GB free disk.
- Benchmark accuracy, peak memory, latency, and projected full-catalog runtime before enabling corpus-wide inference.

The model proposes labels, relationships, and boundaries. It must not rewrite, summarize, translate, invent, or silently discard the book's text. A source-content prompt cannot become an instruction to execute tools, access credentials, or change policy.

### C5. Chapter and reading-flow intelligence

- Recognize Bengali/English chapter conventions, numbered boundaries, bold paragraph headings, acts/scenes, poem titles, anthology entries, and nested sections inside long pages.
- Distinguish real chapters from scene breaks, dialogue, dates, credits, ordinary bold prose, repeated navigation, and unrelated recommendations.
- Preserve source hierarchy and component-book order. Linked compilations require independently complete component evidence.
- Preserve body reading order when separating metadata, dedication, prefaces, and back matter.
- Keep genuinely continuous works continuous. Do not divide text merely to increase chapter counts.
- Use original headings where available. Any necessary generated navigation label must be neutral, localized, and separate from source-authored body text.
- Keep every block accounted for. Remove repeated website chrome only with evidence; preserve meaningful repetition inside the work.
- Use source-block mappings for accurate navigation and positions in the current book. Historical annotation migration and retaining old book generations are not requirements.

### C6. Entity extraction and curation intelligence

- Extract work/edition identity, authors, translators, editors, publishers, illustrators, cover artists, series and sequence, categories, language, original title, edition, and publication facts when supported.
- Handle combined roles such as translation and editing by the same person.
- Distinguish a person credited for the book from someone mentioned in a dedication, introduction, quotation, or narrative.
- Distinguish publisher role from entity type; a publisher need not always be an organization.
- Separate bibliographic facts from prose even when they appear inside the first reading page or an unlabelled block.
- Use raw values, exact source spans, role evidence, normalized forms, and aliases to establish correct current entities. Do not require old resolution histories or migrated development evidence.
- Do not fabricate missing names or merge people solely through fuzzy name matching.
- Replace isolated special-case corrections with reusable evidence-based rules. Correct extraction must be reproducible from the source in a fresh installation without depending on historical manual patches.
- Calibrate confidence against the held-out reference set. Model self-confidence or hardcoded confidence values alone do not justify publication.

### C7. Independent validation and publication

Verification must rebuild expectations from source evidence rather than merely accepting the extractor's own success flag.

- Account for all retained source blocks and detect missing, duplicated, reordered, or incorrectly relocated content.
- Verify EPUB body order by traversing the actual package spine. Navigation documents cannot count as body-text evidence.
- Check section boundaries, front/body/back classification, contents targets, assets, metadata, entity provenance, and exported text.
- Preserve poetry, tables, footnotes, images, internal links, and meaningful repetition.
- Produce valid EPUB navigation without duplicate visible contents pages. Reconcile older documentation against valid format requirements rather than generating invalid packages.
- Require real HTML/EPUB artifacts and prepared reader resources before reporting readiness.
- Activate complete replacements atomically after internal preparation succeeds. Do not require retention of previous editions or old development personal data.
- Publish source books automatically when ready. Resolve structural ambiguity through automated analysis/recovery; do not introduce a review/check/approve task or fabricate a success state.

### C8. Updates, faults, and recovery

- Compare source body, hierarchy, credits, covers, and completion status; a table-of-contents comparison alone is insufficient.
- Show last synchronization time, changed portions, source completion changes, queued rebuilds, and currently available books in the unfinished workspace. Do not expose a Check or Review action.
- Keep source unavailability, source-marked incompleteness, uncertain structure, transient transport faults, and application defects distinct.
- Recollect affected pages or rerun affected stages while reusing valid cached work.
- Implement current-job idempotency, bounded retries, resumable work, stop requests, revision/authority enforcement, and worker fencing. These runtime guarantees do not require importing old IDs, attempts, checkpoints, or queue messages.
- Retry availability failures with pacing; do not repeatedly rerun an unchanged application defect or bypass verification to clear it.
- Repair recurring application defects at their cause and add regression fixtures before version-aware recovery.

### C9. Engine acceptance gate

Account for the entire frozen catalog and report every unresolved/unavailable record. Every reference and held-out book must have its expected source content, reading order, chapter boundaries, and supported entities/roles correctly represented. Resolve identified extraction and structure defects before acceptance; aggregate scores cannot excuse a known incorrect book. Report source coverage, entity precision/recall, and chapter-boundary F1 by layout, role, and language, alongside individual case outcomes.

Run real local inference for semantic evaluation; mocked responses establish integration behavior only. Record throughput and resource requirements. Do not lower thresholds, hide ambiguous cases, or claim full-catalog correctness from benchmark results alone.

## 7. Delivery sequence and acceptance gates

| Milestone | Deliverables | Exit condition |
| --- | --- | --- |
| M0: baseline | Consolidated issue register, previous-version capability matrix, complete route/section/state inventory, current screenshots, clean-start design, and service contracts. | All reported issues mapped, removals specified, and uninspected areas explicitly recorded. |
| M1: website | Unified book model, removal of physical records/features and review workflows, admin-only book editing, shared components, bilingual shells/pages, and complete user/admin flows. | Polished, consistent website and complete task flows accepted; no open visual/UX issues or obsolete book-type/review features. |
| M2: reader | Independent reader service, reading-first canvas, full controls/shortcuts, rich EPUB behavior, local/offline reading, and working new reading sessions. | Polished reader and complete reading flows accepted; reader and service-integration gates pass. |
| M3: corpus understanding | Engine service separation, complete source corpus inventory, structural taxonomy, reference corpus, and local inference benchmark. | Every source record accounted for; benchmark results and runtime limits recorded. |
| M4: intelligent engine | Evidence-based extraction, canonical structure, file generation, independent verification, updates, and recovery. | Engine quality, integrity, and failure-handling gates pass. |
| M5: clean release | Fresh application initialization, development data/queue/artifact reset where needed, source-generated books, realistic end-to-end use, and final completeness report. | The clean application meets the visual, UX, functional, and security standard; publication and reading work; all identified issues are resolved. |

### Verification matrix

- Build, lint, strict type checks, appropriate backend/unit tests, generated schema consistency, migrations, architecture/file-size policies, and whitespace checks.
- Bengali and English at 320, 390, 820, 1366, and 1920px; relevant portrait/landscape layouts and 200% text.
- Chromium, Firefox, WebKit, Android, and iPhone simulation. Keep physical-device and external delivery claims separate from simulator evidence.
- Every applicable page/section state, including long content, delayed hydration, missing images, failed requests, stale revisions, expired access, keyboard focus, and repeated submissions.
- Measured control alignment, spacing, minimum targets, card heights, content budgets, contrast, focus, and layout stability.
- Rendered screenshot inspection and complete task execution. Do not automatically replace reference screenshots to accept a regression.
- Fresh-start coverage: no physical-book records/logs, physical/digital type fields, or review/check/approve workflows; admin-only book Edit, cover replacement, and metadata writes enforced in both UI and API.
- Actual reader shortcuts, current reading-position persistence, annotations, offline behavior, archive isolation, and protected resource access.
- Real corpus/model evaluation, source coverage, EPUB spine verification, deterministic fixtures, restart/resume behavior, and publication canaries.

### Final report

For every capability and issue, report its final behavior, implementation status, accepted evidence, and any remaining limitation. Include source audit totals, unresolved reasons, semantic evaluation results, interface screenshots, service readiness, clean-initialization results, and complete user/admin task outcomes. Historical checks and overlapping test runs must not be presented as fresh or unique evidence.

Do not report the application complete while any identified visual, UX, or functional issue remains, any required work is unfinished, or the user has not accepted the visual/UX result. Passing tests or accepting a limited page inventory does not override this condition. Do not claim external Kindle delivery or physical-device behavior from simulations.

## 8. Complete page inventory

This inventory starts from the 54 existing page route templates, not 54 mandatory pages in the clean product. Remove the physical-book page and obsolete development-compatibility routes; verify their associated features and data are absent. Audit all four managed entity kinds—contributors, categories, series, and reading lists—where a dynamic kind appears. Expand every retained/new route into the section/state matrix above, including dialogs, menus, not-found/error boundaries, and operational surfaces. Add any newly discovered portion rather than limiting completion to this starting list.

| Area | Page route templates |
| --- | --- |
| Entry and catalog | `/`; `/catalog/` |
| Public book | `/books/[slug]/`; `/books/[slug]/editions/` |
| Contributors | `/contributors/`; `/contributors/[slug]/` |
| Categories | `/categories/`; `/categories/[slug]/` |
| Series | `/series/`; `/series/[slug]/` |
| Reading lists | `/collections/`; `/collections/[slug]/` |
| Personal library | `/my-books/`; `/my-books/[slug]/` |
| Remove physical inventory | `/physical-books/`: remove this page and its navigation, APIs, records, physical-only logs, and type fields. |
| Personal workspace | `/notes/`; `/profile/` |
| Reader | `/reader/`; `/reader/[identifier]/`; `/local-reader/` |
| Kindle | `/kindle/`; `/kindle/books/[slug]/`; `/kindle/operations/[identifier]/` |
| Authentication | `/login/`; `/create-password/`; `/reset-password/`; `/reset-password/confirm/` |
| Information | `/help/`; `/about/`; `/contact/` |
| Remove development compatibility | `/[legacy]/`: no requirement to carry obsolete development URLs into the clean application. |
| Admin entry | `/manage/`; `/manage/overview/` |
| Admin books | `/manage/books/`; `/manage/books/new/`; `/manage/books/[slug]/`; `/manage/books/[slug]/relationships/`; `/manage/book-creations/[identifier]/` |
| Admin entities | `/manage/entities/`; `/manage/entities/[kind]/`; `/manage/entities/[kind]/new/`; `/manage/entities/[kind]/[identifier]/` |
| Sources | `/manage/sources/`; `/manage/sources/[identifier]/`; `/manage/unfinished/` |
| Processing | `/manage/jobs/`; `/manage/jobs/[identifier]/` |
| Schedules | `/manage/automations/`; `/manage/automations/new/`; `/manage/automations/[identifier]/` |
| Users and access | `/manage/users-access/`; `/manage/users-access/[identifier]/`; `/manage/users-access/invite/`; `/manage/users-access/mail/[identifier]/` |

### Related evidence

- [Previous-version completeness register](operations/feature-parity.md)
- [Existing interface implementation report](operations/interface-redesign.md)
- [Existing sitewide UI review](operations/sitewide-ui-review.md)
- [Source processing architecture](architecture/source-processing.md)
- [Protected reader architecture](architecture/reader-access.md)
- [Earlier EPUB pipeline requirements](epub-pipeline-specification.md)

These references support investigation. Their older completion claims do not close the acceptance gates in this document. Their physical-book, review, compatibility, preservation, and migration requirements are superseded by the revised decisions above.

## 9. New-session handoff

### Readiness and remaining investigation

This plan is ready to start implementation. It establishes product decisions, workstreams, page coverage, and acceptance gates. It does not establish that all pages have already been visually inspected, every source book has been semantically understood, or the proposed local model achieves the required accuracy. Those are explicit implementation deliverables. Neither a strong plan nor prior passing tests establishes a finished product.

Use this document as the current product specification. Follow AGENTS.md for coding and workspace rules. The revised decisions in section 1 supersede conflicting requirements in older plans and handoffs; older documents are supporting references, not a reason to restore physical-book features, review workflows, or preservation work.

### Open the same workspace

Start the new session in `/Users/rsalehin24/Documents/elibrary`. This planning document and substantial earlier implementation changes are in the existing working tree and are not necessarily committed. A fresh checkout or different worktree may not contain them. Do not commit or push unless requested.

Development-data resets are authorized within the scope described in section 1. That authorization does not mean discarding uncommitted source work indiscriminately. Inspect existing changes, reuse correct implementation, and replace code where the revised product requires it.

### Starting sequence

1. Read AGENTS.md and this document. Inspect the current code, repository status, available runtimes, and service configuration. Do not restart product planning or ask again whether development-data resets are allowed.
2. Establish the M0 issue/feature/route baseline and proceed into M1 implementation. Inspect real populated pages in both languages; do not make a large mockup and call it the application.
3. Remove the physical/digital distinction and physical-book features, remove editorial review workflows, and enforce admin-only cover/metadata editing across the schema, APIs, interface, fixtures, and tests. Use a clean development initialization where it simplifies the result.
4. Establish shared layouts and controls using catalog, book details, My Books, source creation, unfinished books, schedules, and users/access as representative pages. Apply the same system to every remaining page and state; resolve spacing and hierarchy through shared components.
5. Complete the website gate, then the standalone reader gate. Define service contracts as needed, but implement engine intelligence only after these product surfaces meet their acceptance criteria.
6. Complete the source corpus investigation and local-model benchmark before claiming intelligent extraction or starting a full-catalog inference run. Build the engine against the results, not assumptions about model quality.
7. Maintain an implementation checklist tied to issue IDs, actual test results, visual evidence, and remaining work. Report completed milestones accurately and continue through the agreed sequence.

### Runtime and verification context

- The current website is `app/web` (Next.js/React/TypeScript); the backend is `app/backend` (Django/PostgreSQL/Celery). The previous frontend and embedded reader remain references in `app/frontend`.
- Last-known development endpoints are website `http://localhost:3000`, API port 8000, isolated browser proxy port 3001, and reference API port 8002. Discover current processes and configuration rather than trusting historical process IDs.
- Preview data previously used `bangla_library_preview`; isolated browser fixtures used `bangla_library`. Keep fixture seeding separate from the user-facing catalog even when a clean reset is authorized.
- Stop the relevant application writers before resetting their development state. Identify this application's databases, queues, and storage before clearing them; unrelated resources are outside scope.
- Approved Playwright tooling is already listed in `app/web/package.json`. Browser and dependency limitations are recorded in [verification tooling](architecture/verification-tooling.md). Approval for Playwright, compatible ESLint, and the recorded development type stubs must not be requested again.
- The local inference model/runtime is a proposal, not an installed or benchmarked dependency. Follow AGENTS.md before adding new dependencies. No paid endpoint or additional purchase is authorized.
- Use package scripts and the [test documentation](../tests/README.md). Engine integration tests require an isolated Redis server; a different logical database does not isolate Redis Pub/Sub. Do not run tests that interfere with an active preview worker.
- Serve an immutable completed web build during browser acceptance. Do not rebuild generated service-worker artifacts while PWA/update tests are using them. Keep global discovery/scheduling tests and fixture seeding appropriately serialized.
- Earlier partial card, control, export, unfinished-page, and reader fixes exist in the working tree. They are provisional, may not be served by the current running build, and do not satisfy the revised plan without fresh verification.

### Copy into the new session

```text
Implement docs/application-reader-engine-plan.md in this workspace.
Read AGENTS.md and the full plan first; its revised product decisions supersede older conflicting plans.
Start with M0 and proceed into M1, then finish the website and standalone reader before engine intelligence.
Use one book model, remove physical-book records/features and all review workflows, and restrict cover/metadata editing to admins.
Development data and queues may be reset as needed for a clean application. No paid services or purchases.
Inspect the existing working tree, reuse correct code, and verify actual pages and task flows in Bengali and English.
Maintain the issue checklist and evidence; do not declare completion with unresolved visual, UX, or functional issues.
```
