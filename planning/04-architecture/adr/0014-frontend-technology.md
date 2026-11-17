# ADR-0014 — Frontend technology

Status: DRAFT

## Context
UI/UX quality is the owner's primary complaint. The reader is DOM- and text-selection-heavy. Rust UI frameworks (Leptos, Dioxus) give end-to-end types; TypeScript has the richer ecosystem for readers and accessibility tooling.

## Decision (pending D-02 and spike S-02)
Default: server-rendered Rust pages (Leptos SSR) for public/admin pages, with the reader isolated behind a narrow interface (`ReaderHost`: load chapter, report position, create/resolve anchor, theme/typography settings) so it may be implemented in TypeScript/WASM if the spike shows accessibility, text-selection or performance gaps. Whatever is chosen consumes the generated contract types.

## Consequences
+ Typed UI states (INV-WEB-001) and no contract drift.
− Smaller UI ecosystem; must verify accessibility with automated scans plus manual screen-reader checks.
