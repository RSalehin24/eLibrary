# Open decisions (need the owner's answer)

Status: DRAFT

Each decision blocks a named gate. A recommendation is given so a "yes" is enough. Answered decisions move to [DECISIONS](../DECISIONS.md) (this file keeps only open questions; ids D-01…D-10).

| ID | Decision | Options | Recommendation | Blocks |
|---|---|---|---|---|
| D-01 | Keep physical/manual book inventory (binding, price, language, physical books list)? | keep in v1 · keep as module after v1 · drop | Defer to v1.1 as an optional catalog module; keep legacy data in the migration archive | G0 (REQ-CAT-009) |
| D-02 | Frontend technology | Rust SSR (Leptos) · TypeScript (React/Solid) + generated client · hybrid (Rust SSR pages, TS reader) | Run spike S-02; default **Rust SSR for pages, reader behind a narrow interface** so it can be TS if the spike fails accessibility/performance | start of P4 |
| D-03 | Rights to ingest and republish source content; permission for any non-GET action on the source (e.g. "mark complete" that unlocks chapters) | written permission · public-domain only · legal review | Obtain written confirmation; acquisition stays GET-only; if locked chapters need a logged-in source account, ask the source owner for an export/API instead of mutating progress | G6 (ingestion go-live) |
| D-04 | Who may read by default? | every Active account reads published books · grants required per book/category | Active accounts get durable read of Published books via the default-grant policy; download, Kindle, edit remain grant-based | start of P3 |
| D-05 | What is in the public preview? | metadata + TOC only · + first N characters · + first chapter | Cover, metadata, summary, TOC, first 3,000 characters of the first chapter (configurable per book, 0 allowed) | start of P4 |
| D-06 | Reader delivery | chapter HTML served by content (no EPUB in the browser) · EPUB parsed in browser | Chapter-served in v1; EPUB download only with Download grant | start of P5 |
| D-07 | Hosting target | single Linux VPS · home server + tunnel · managed cloud | Single Linux host, systemd or Compose, Postgres local with WAL archiving, offsite backups | start of P1 |
| D-08 | UI languages and default | bn+en, bn default · bn only · en default | bn + en, default from `Accept-Language`, fallback bn | start of P4 |
| D-09 | Search-engine indexing of preview text | index metadata + preview · index metadata only · noindex all until D-03 | Index metadata; `noindex` on preview text until D-03 is resolved | G4 |
| D-10 | Keep the demo account? | keep with strict limits · drop | Keep as a dedicated account with only public-equivalent read of a curated set | start of P3 |
