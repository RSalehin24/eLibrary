# Feature register: keep / change / drop / new

Status: DRAFT

Every legacy capability from the [X2 capability map](../_replan/analysis/X2-capability-map.md) (CAP-01..CAP-28) and the extra legacy features it lists gets a verdict and a target service among gateway (GWY), identity (IDN), catalog (CAT), reader (RDR), ingestion (ING), notify (NTF), web (WEB), platform (PLT). Verdicts follow [new architecture](../_replan/new-architecture.md) and decisions D-01, D-03, D-12, D-28, D-30, D-32. Nothing is silently dropped. Legacy defect ids are in the [X1 register](../_replan/analysis/X1-issues-register.md).

## Capabilities

| Cap | Capability | Verdict | Target | Delta and reason |
|---|---|---|---|---|
| CAP-01 | Source catalog mirror, incomplete-book tracking | Change | ING | One mirror (was two: SourceCatalogEntry and BookRecord). Source fields and workflow state stored separately; empty incomplete list is a no-op (X1-024..X1-026, X1-106) |
| CAP-02 | Request intake and title resolution | Change | ING | One request model; operator-only (`operate`), no anonymous or UUID-capability endpoints (X1-006); exact normalized matching, no auto-resolve by substring (X1-046, X1-050) |
| CAP-03 | Source acquisition (crawl, fetch) | Change | ING | GET-only, no mark-complete (D-03, X1-012); one fetcher; TLS always verified (X1-016); bounded concurrency, 0.5 s delay, 3 attempts, 50 requests per run |
| CAP-04 | Source credential custody | Change | ING | Cookie in a read-only secret file; status and expiry shown in the console; rotatable without rebuild (X1-015) |
| CAP-05 | Curation (normalize, structure, validate, version) | Change | ING | One authoritative curated document; Bengali-correct normalization; no silent drops; derived artifacts regenerable (X1-029, X1-035, X1-046) |
| CAP-06 | Duplicate detection and review | Change | ING | One matcher: exact normalized key plus author, category, edition; near-matches to a human; explicit review state (X1-049, X1-052) |
| CAP-07 | Book build (EPUB, cover) and structure audit | Change | ING | Escaping on, sanitize, images and fonts packaged, nav plus NCX, audit as a gate (X1-004, X1-047). Single-file HTML book dropped: reader builds from EPUB |
| CAP-08 | Publish and book lifecycle | Change | CAT (with ING publish call) | One state machine draft, published, archived; automatic atomic publish when all gates pass (D-49); failed build never visible (X1-028, X1-031, X1-032) |
| CAP-09 | Job orchestration, scheduling, automation | Change | ING | PostgreSQL queue, leases, typed errors, per-page cancel, stored `next_due`; no inline execution (X1-051, X1-065..X1-068) |
| CAP-10 | Operator console live status | Change | ING + WEB | One SSE stream with versioned snapshot on reconnect; derived read model, no stored projections (X1-030, X1-071) |
| CAP-11 | Metadata editing and review | Keep | CAT | Needs `manage_catalog`; transition rules; one writer of state; version history kept; revert optional (X1-037, X1-053) |
| CAP-12 | Authentication and account security | Keep | IDN | Argon2, opaque sessions, TOTP, reset by mail; throttle every auth route; generic reset response (X1-017) |
| CAP-13 | User administration and invitation | Keep | IDN | Invite, disable, delete on request, require TOTP; mail via notify; one grant path (X1-041) |
| CAP-14 | Entitlements (grants, read-once) | Change | IDN | Explicit scopes and grants, no wildcards, ownership never grants access, one decision point (X1-001, X1-008, X1-020, X1-034) |
| CAP-15 | Taxonomy and identifiers | Change | CAT | Contributors, series, categories; Unicode slugs; surrogate ids; no structured catalog codes: UUID and unique slug only (D-36, X1-036) |
| CAP-16 | Browse, search, export | Change | CAT + WEB | Published-only reader view; PostgreSQL FTS with Bengali normalization; CSV only, formula-injection safe (X1-009, X1-022). XLSX and PDF dropped |
| CAP-17 | Shelf, saved filters, per-user lists | Change | CAT + WEB | Shelf is a list only; mutations need `browse` and a signed-in session (D-30); saved filters kept, owned by catalog per user (D-43) |
| CAP-18 | Physical (manual) books registry | Drop (v1) | none | Deferred to v1.1 as an optional catalog module (D-01); legacy data not migrated (D-32) |
| CAP-19 | Reading delivery (launch, session, package) | Change | RDR | Reading copy plus 15-minute ticket bound to user, book, version; whole-book package; no token in URL (D-28, X1-003, X1-004) |
| CAP-20 | Preview and file download | Change | CAT | Preview built at publish time (D-05), served only to signed-in users with `preview` (D-34); EPUB download needs `download`; files streamed only by services after a check; deleted books not served (X1-010, X1-011) |
| CAP-21 | Reading progress and annotations | Change | RDR | One route family, session plus ticket, ownership checked on every mutation; anchors survive rebuilds; duplicates are 409 not 500 (X1-038, X1-056..X1-058) |
| CAP-22 | Kindle delivery | Change | NTF (request from CAT) | Asynchronous mail job with retries, size and rate limits, delivery status on the Files tab (X1-042, X1-075) |
| CAP-23 | Notifications (mail, in-app) | Change | NTF + ING | Mail outbox for invite, reset, Kindle; operator live notices over SSE; notify requester and failure alerts (M8) |
| CAP-24 | Audit trail | New | IDN (auth, grants) + each service | Append-only, actor on every command, 1 year (X1-084, M1); scope: auth, grants, roles, publish/unpublish/delete, operator actions, opens, downloads (D-40) |
| CAP-25 | Backup, restore, migration | Change | PLT | Monthly database and volume backup copied off host, restore drill, up to 30 days of data-loss window (D-33); migration toolkit dropped (D-32); launch runbook added (X1-080, X1-083) |
| CAP-26 | Observability | New | PLT | Structured logs, health and readiness per service, alerts on cookie expiry, stuck jobs, disk (M3) |
| CAP-27 | Configuration, secrets, deployment | Change | PLT | Secrets as files, no defaults, startup validation, memory limits, rolling restart per service (X1-002, X1-013) |
| CAP-28 | Web shell and design system | Change | WEB | Angular Material M3, minimalist, light and dark, four window classes, route guards from server capabilities (X1-014; D5-F39..F42) |

## Other legacy features not carried as a capability row

| Feature | Verdict | Target | Note |
|---|---|---|---|
| Email login, invite-only accounts | Keep | IDN | CAP-12 |
| Demo auto-login by GET | Drop | none | Demo account dropped (D-35, X1-007) |
| Public search and preview | New | CAT | Public = metadata, covers and summaries only (D-34); preview text and reading need sign-in; metadata may be indexed (D-09) |
| Profile (name, photo, password, Kindle addresses) | Keep | IDN | Photo upload kept (D-44): type allow-list, size limit, re-encoded or validated, SVG refused, served only to owner and admins (X1-004) |
| "Log out everywhere", session list | New | IDN | M13 |
| Force Generate on review-required | Drop | ING | Replaced by explicit resolution actions in duplicate review |
| Multi-page TOC, on-hold, incomplete, reprocessing as separate pages | Change | WEB | One Import workspace: catalog sync, requests, review, jobs |
| Reprocess a book | Change | ING | Produces a new build; the published one stays until the new build passes every gate and is published automatically |
| Manual EPUB upload | Drop (v1) | none | Scrape pipeline only; manual metadata edit stays (D-42) |
| `/admin` Django admin | Drop | none | Replaced by Users and access, Import workspace |
| Sepia reading theme | Keep | RDR + WEB | One of the reading modes beside light and dark |
| In-book search | New | RDR | Only if cheap (new architecture section 5.7) |
| JSON export of own reading data | New | RDR | D-30 |
| Per-user erasure on admin request | New | IDN | D-30 |
| Throwaway `check_*.py` scripts, `seed_e2e_data` with fixed password | Drop | none | X1-023; tests use fixtures |

## Open questions for the owner

- OQ-2 Resolved by D-43: saved filters are kept and owned by catalog per user.
- OQ-3 Resolved by D-40: audit covers auth, grants, roles, publish/unpublish/delete, operator actions, opens and downloads; 1 year.
- OQ-4 Resolved by D-42: no manual EPUB upload in v1.
