# Open decisions (need the owner's answer)

Status: DRAFT

Each decision blocks a named gate. A recommendation is given so a "yes" is enough. Answered decisions move to [DECISIONS](../DECISIONS.md) (this file keeps only open questions; ids D-05…D-10, D-17…D-21).

| ID | Decision | Options | Recommendation | Blocks |
|---|---|---|---|---|
| D-05 | What is in the public preview? | metadata + TOC only · + first N characters · + first chapter | Cover, metadata, summary, TOC, first 3,000 characters of the first chapter (configurable per book, 0 allowed) | start of P4 |
| D-06 | Reader delivery | chapter HTML served by content (no EPUB in the browser) · EPUB parsed in browser | Chapter-served in v1; EPUB download only with Download grant | start of P5 |
| D-07 | Hosting target | single Linux VPS · home server + tunnel · managed cloud | Single Linux host, systemd or Compose, Postgres local with WAL archiving, offsite backups | start of P1 |
| D-08 | UI languages and default | bn+en, bn default · bn only · en default | bn + en, default from `Accept-Language`, fallback bn | start of P4 |
| D-09 | Search-engine indexing of preview text | index metadata + preview · index metadata only · noindex all until D-03 | Index metadata; `noindex` on preview text until D-03 is resolved | G4 |
| D-10 | Keep the demo account? | keep with strict limits · drop | Keep as a dedicated account with only public-equivalent read of a curated set | start of P3 |
| D-17 | Approve the foundational Rust dependency set (runtime, HTTP, serialization, database, tracing, test tooling) | approve as one reviewed batch at the start of P1 · approve crate by crate on demand · pre-approve now from the register | Approve as one reviewed batch at P1 start, after versions and maintenance are verified (I-01) | start of P1 |
| D-18 | Accept the mapping of OOP/SOLID wording to Rust (traits, composition, enums, conformance suites; no inheritance) | accept the mapping · require a stricter trait-per-type style · rewrite the rules for Rust | Accept the mapping (I-03) | start of P1 |
| D-19 | Shape thresholds for functions | target 20 lines with a hard cap of 30, 3 parameters, 2 nesting levels · hard 20-line cap · 20-line target with no cap | Target 20, hard cap 30, ≤ 3 parameters, ≤ 2 nesting — verified lint support first (I-04) | G1 |
| D-20 | Approve the frontend npm package set (Angular, Angular Material/CDK, tooling) | approve as one batch after spike S-02 · approve now · package by package | Approve as one batch after S-02 confirms versions and component coverage (I-10) | start of P4 |
| D-21 | Track `AGENTS.md` in the new codebase (it is git-ignored in the legacy repo) | track it in the new repo · keep it ignored and carry the rules in CLAUDE.md · symlink to the owner's master copy | Track it in the new repo so rules travel with the code (I-05) | start of P1 |
