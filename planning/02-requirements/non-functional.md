# Requirements - Non-functional (NFR)

Status: DRAFT

Line format: `REQ-ID · priority · inv: <invariants> · verify: <methods> · statement`

- **REQ-NFR-001** · MUST · inv: INV-NFR-001 · verify: metric, e2e · Availability of browse, search and reading is at least 99.5% per month outside announced maintenance, on one host, measured at the gateway.
- **REQ-NFR-002** · MUST · inv: INV-NFR-002 · verify: metric, e2e · Latency at 50 users: search p95 at most 250 ms, book detail p95 at most 300 ms, gateway plus identity authorization overhead p95 at most 25 ms, opening a book (ticket) p95 at most 300 ms, serving the whole-book package p95 at most 1.5 s for a book of up to 5 MB.
- **REQ-NFR-003** · MUST · inv: INV-NFR-003 · verify: metric, e2e · Capacity: at least 5,000 books and 50 users (20 concurrent signed-in sessions, 10 concurrent readers), 10 requests per second sustained and 30 per second in bursts, and 2 concurrent ingestion jobs, with no degradation of reading while ingestion runs.
- **REQ-NFR-004** · MUST · inv: INV-NFR-004 · verify: metric, drill · Recovery: RPO up to 30 days (monthly backups, D-33) and RTO at most 4 hours, shown by the restore drill. This accepts losing up to 30 days of reading progress, review decisions and user changes after the last backup; books can be re-ingested.
- **REQ-NFR-005** · MUST · inv: INV-NFR-005 · verify: metric, review · Memory and size: every container has a declared memory limit; the whole stack runs at idle within 4 GB and under load within 8 GB; each Rust service image is at most 100 MB and the web image at most 50 MB; the first load of the sign-in page transfers at most 500 KB compressed; the file volume plan is 100 GB with an alert at 80% use.
- **REQ-NFR-006** · MUST · inv: INV-NFR-006 · verify: review · Upload and payload limits: an EPUB sent to Kindle is at most 50 MB (the Kindle email limit; there is no EPUB upload, D-42), a profile image at most the configured size limit (REQ-IDN-034), a JSON request body at most 1 MB, a list page at most 100 rows, an export at most 5,000 rows; all are enforced server-side.
- **REQ-NFR-007** · MUST · inv: INV-NFR-007 · verify: review, e2e · Security: HTTPS only (TLS 1.2 or newer, HSTS); deny by default authorization; no secret in the repository, images or logs; every threat-model item is mitigated or accepted in writing; dependencies are reviewed at approval time and on each update.
- **REQ-NFR-008** · MUST · inv: INV-NFR-008 · verify: e2e, review · Accessibility: WCAG 2.2 AA (contrast, keyboard operation, focus, labels, reduced motion) in both light and dark themes on every screen including the reader.
- **REQ-NFR-009** · MUST · inv: INV-NFR-009 · verify: e2e · Browser and window support: the last 2 versions of Chromium, Firefox and Safari, Android Chrome and iOS Safari 16 or newer, from 360 px to 1920 px with no horizontal page scroll.
- **REQ-NFR-010** · SHOULD · inv: INV-NFR-010 · verify: unit, e2e · Internationalization: Bengali and English strings are complete with no hard-coded text; full-text search normalizes Bengali (vowel signs and conjuncts preserved).
- **REQ-NFR-011** · MUST · inv: INV-NFR-011 · verify: review · Maintainability: no service depends on another service's crate except generated contract crates; each service builds and tests alone.
- **REQ-NFR-012** · MUST · inv: INV-NFR-012 · verify: prop, e2e · Determinism: EPUB builds and curation stages give identical output for identical input and configuration.
- **REQ-NFR-013** · MUST · inv: INV-NFR-013 · verify: metric, e2e · Data integrity: projection drift is zero; after the outbox drains, the set of published books in catalog equals the set in reader reading copies, and identity grants equal the reader and catalog caches.
- **REQ-NFR-014** · SHOULD · inv: INV-NFR-014 · verify: metric, e2e · Startup and restart: the full stack becomes ready within 90 seconds on the host; a single service restarts and is ready within 15 seconds.
