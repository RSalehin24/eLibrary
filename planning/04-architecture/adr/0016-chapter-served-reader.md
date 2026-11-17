# ADR-0016 — Reader consumes chapters, not the EPUB file

Status: DRAFT

## Context
"Read requires an account" is unenforceable once the whole EPUB is delivered to the browser. The legacy reader parses EPUB client-side.

## Decision (pending D-06)
`content` serves sanitized chapter HTML and a section index under short-lived capabilities; the reader renders chapters and never receives the EPUB unless the account has a Download grant. Pagination is layout-time in the browser. Offline reading is out of v1.

## Consequences
+ Read-once and revocation are enforceable per chapter; smaller payloads.
− Loses offline EPUB-in-browser behavior; the legacy third-party reader runtime is not reused.
