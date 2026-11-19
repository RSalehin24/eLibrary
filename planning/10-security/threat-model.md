# Threat model (STRIDE, per trust boundary)

Status: DRAFT

Rewritten for the six-service design (D-31): browser, Caddy, `web`, `gateway`, `identity`, `catalog`, `reader`, `ingestion-api`/`ingestion-worker`, `notify`, one PostgreSQL. Kept from v1: the STRIDE table form. Changed: capability tokens and access service are gone (identity decides and mints reading tickets, D-37); no uploads (D-42); no demo (D-35); no library service.

Assets: accounts and credentials; third-party book text (licensed content, see [legal](legal-source-content.md)); personal reading data; admin and operator capabilities; keys and the source-site cookie; availability; backups.

Trust boundaries: internet to Caddy/`web`/`gateway`; `gateway` to services; service to service; services to PostgreSQL and volumes; `ingestion-worker` to the source site; `notify` to SMTP; host to offsite backup.

Every item needs a mitigation or a signed acceptance (REQ-NFR-007, INV-NFR-007). Review cadence: at every gate and on each new public route or data class.

## Threats

| ID | Threat | Boundary | Category | Mitigation | Invariants / tests |
|---|---|---|---|---|---|
| T-01 | Scraping full text through public routes | internet to gateway | Info disclosure | public = metadata only (D-34); search index and public routes built from `PublicDocument`; preview text and reading need a session; rate limits; no canary-free preview | INV-CAT-002, INV-CAT-012, INV-CAT-017, INV-GWY-003 |
| T-02 | Reading or downloading without account, scope or published state | client to reader/catalog | Elevation | deny by default; every route declares a scope; identity checks scope and book state at every open and redemption | INV-IDN-013, INV-IDN-016, INV-RDR-005, INV-CAT-023 |
| T-03 | Reading ticket theft or replay | client | Spoofing | opaque ticket stored hashed by identity; bound to user, book, version and grant version; 15 min; header or body, never URL; every redemption verified by identity so revocation is immediate (D-37) | INV-IDN-021, INV-IDN-022, INV-RDR-006, INV-RDR-007 |
| T-04 | Credential stuffing and brute force | internet to identity | Spoofing | per-account and per-IP throttle (limits), Argon2id, TOTP, uniform responses; soft lockout | INV-IDN-004, INV-IDN-005, INV-GWY-007 |
| T-05 | Account enumeration (sign-in, reset, invite) | identity | Info disclosure | uniform body, status and timing class | INV-IDN-008 |
| T-06 | Session hijack or fixation | client | Spoofing | opaque server-side session, HttpOnly Secure SameSite=Lax cookie, rotation at sign-in, revocation on disable | INV-IDN-007, INV-GWY-013 |
| T-07 | CSRF on state-changing routes | browser | Tampering | gateway CSRF token and Origin check plus SameSite | INV-GWY-005 |
| T-08 | XSS from scraped HTML, annotations or profile images | reader/web/identity | Tampering | `SafeHtml` allow-list sanitizer, CSP and nosniff, SVG refused, image re-encoding, no publisher scripts or styles | INV-RDR-003, INV-RDR-025, INV-ING-024, INV-IDN-034, INV-GWY-009 |
| T-09 | SSRF and off-host fetch from scraping | ingestion-worker | Tampering | host allow-list, redirects re-checked, TLS verification cannot be disabled, worker egress only to the source | INV-ING-010 |
| T-10 | Malicious or malformed EPUB/page content (zip bomb, XXE, path traversal) in build or reader parse | ingestion, reader | DoS / Tampering | no EPUB upload (D-42) so only our own builds reach the reader; size, entry and ratio limits in both parsers; no external entities; epubcheck in the worker (D-47) | INV-ING-031, INV-ING-026, INV-RDR-002, INV-PLT-008 |
| T-11 | Privilege escalation through grants or roles | identity | Elevation | scopes are explicit rows, no wildcard; actor != subject; admin cannot change self or remove the last admin; management Allow needs TOTP where required; audited | INV-IDN-010, INV-IDN-012, INV-IDN-025 |
| T-12 | IDOR on personal data (progress, notes, shelf, saved filters, preferences) | reader, catalog | Info disclosure | owner id taken from the verified identity header; row-level policy; 404 for others | INV-RDR-016, INV-CAT-033, INV-RDR-026 |
| T-13 | Service impersonation or forged identity headers inside the host | internal | Spoofing | per-service internal tokens (60 s), caller-to-route allow-list, headers accepted only from the gateway, `db` network internal, one role per database | INV-PLT-020, INV-GWY-004, INV-PLT-002 |
| T-14 | Poisoned or drifted source content producing wrong catalog data | source to ingestion | Tampering | completeness evidence, drift fingerprint and canaries, duplicate review, epubcheck and the other gates before an automatic publish (D-49, a defect that passes all gates is public until unpublished: R-24), `manage_catalog` unpublish, audited | INV-ING-018, INV-ING-026, INV-CAT-001 |
| T-15 | DoS on public search or pages | internet | DoS | gateway rate limits, bounded queries and pages, timeouts, per-container memory limits | INV-GWY-007, INV-PLT-008, INV-CAT-017 |
| T-16 | Mail abuse via invites, resets or Kindle sends | notify | Abuse | admin-only invites, per-address and per-user caps (Kindle 10/h), Kindle send only after identity Allow, uniform reset | INV-NTF-005, INV-NTF-007 |
| T-17 | Secrets in logs, events, images or repository | all | Info disclosure | `Secret<T>`, secrets as read-only files, log redaction tests, secret scanning in CI | INV-IDN-003, INV-PLT-016, INV-NTF-004, INV-ING-011 |
| T-18 | Supply-chain compromise (crates, npm, base images, Java runtime in the worker) | build | Tampering | approved dependency register only, lockfiles, `cargo deny/audit`, base images pinned by digest, image scan | INV-PLT-013, Q5, Q10, Q11 |
| T-19 | Backup theft or tampering | ops | Info disclosure | offsite copy encrypted before leaving the host; key stored apart from the backup | INV-PLT-015 |
| T-20 | Insider (admin or operator) misuse | admin | Repudiation | append-only audit with 1-year retention (D-40), actor != subject rules, host-only admin recovery; audit read needs `manage_users` (open C-1) | INV-PLT-009, INV-IDN-012, INV-IDN-029, INV-ING-035 |
| T-21 | Legal takedown or rights claim; source withdraws permission | business | n/a | provenance per book, unpublish and tombstone, takedown runbook text in [legal](legal-source-content.md); D-03 permission outstanding | D-03, INV-CAT-003 |
| T-22 | Source-site cookie stolen or abused | ingestion, host | Info disclosure / Spoofing | read-only secret file, sent only to allow-listed hosts on GET, never in argv, logs, DB or responses; expiry visible; rotation runbook | INV-ING-011, INV-ING-010 |
| T-23 | Admin lock-out or lost last admin | identity, host | DoS | host command `admin-reset` (D-38), dry-run default, audited, sets a setup link and never a password; no HTTP route | INV-IDN-033, INV-IDN-032 |
| T-24 | Whole-book copying by a legitimate reader | reader | Info disclosure | accepted residual risk (no DRM): entitlements, 15-min tickets, per-user open limit (30/h), audit of every open; records and UI state the limit | INV-RDR-010, INV-RDR-011 |
| T-25 | Direct file access around checks (`/media`-style) | caddy, gateway | Info disclosure | Caddy and gateway have no file root; only services stream files after a check | INV-GWY-011, INV-CAT-020 |
| T-26 | Lost data after disk failure or operator error | ops | DoS | monthly backup, offsite, scripted restore drill; the loss window is stated in [backup](../11-operations/backup-restore.md) (accepted, D-33) | INV-PLT-015, INV-NFR-004 |
| T-27 | Missing or dropped security headers (HSTS, CSP, nosniff) | gateway, web, caddy | Tampering | headers on every response; which component sets which is OPEN (O-2) | INV-GWY-009 |
| T-28 | Account deletion leaves personal data in other services | identity, reader, catalog | Info disclosure | erase propagation; mechanism is OPEN (O-1: `user.deleted` event or internal erase route) | INV-IDN-031, INV-RDR-017 |

## Legacy loopholes (X3 L1-L17) and where each is closed

| Legacy | Defect (short) | Closed by | Threat / invariants |
|---|---|---|---|
| L1 | Any user shelves any book and becomes owner | shelf and ownership never grant access | T-02; INV-IDN-015, INV-CAT-025 |
| L2 | `is_staff` and `admin:full_control` wildcards | explicit scopes, no wildcard, roles reader/operator/admin | T-11; INV-IDN-010 |
| L3 | Demo login without credentials | demo dropped (D-35); no fixed-credential route in production builds | T-23; INV-IDN-032 |
| L4 | Token-only reader routes, token in URL, no revocation | header/body ticket verified by identity at each redemption | T-03; INV-IDN-021, INV-RDR-007 |
| L5 | Anonymous ingestion and token minting | every ingestion route needs `operate`; no anonymous submission | T-09; INV-ING-009, INV-GWY-002 |
| L6 | Draft or failed-gate books visible | only published versions visible | T-02; INV-CAT-002, INV-IDN-016 |
| L7 | Deleted books still downloadable | tombstone removes every read path, emits `book.unpublished` | T-21; INV-CAT-003 |
| L8 | Inconsistent annotation rules, no export/erasure | one owner rule from the identity header; own-data export and admin deletion | T-12, T-28; INV-RDR-016, INV-RDR-017 |
| L9 | Read-once weaknesses | consumed once at successful redemption; admin reset audited | INV-RDR-009, INV-IDN-020 |
| L10 | UI and server disagree on capabilities | one resolved capability set; server stays authority | INV-IDN-030 |
| L11 | Coarse processing scope, cross-user effects, 500 on invisible ids | one `operate` policy; invisible ids give 404 | INV-ING-008, INV-ING-009 |
| L12 | Weak grant administration | grants editable, no self-change, no last-admin removal, audited | T-11; INV-IDN-012 |
| L13 | Unauthenticated worker bus, test hooks, destructive seed commands | service tokens, no bus, no test routes in production, dry-run commands | T-13; INV-PLT-020, INV-IDN-032, INV-ING-005 |
| L14 | Missing-asset self-heal on GET | GET handlers write nothing | INV-CAT-032, INV-RDR-025 |
| L15 | Unsanitised HTML, unvalidated uploads | `SafeHtml`, CSP, image validation, SVG refused | T-08; INV-RDR-003, INV-IDN-034 |
| L16 | Audit log never written | append-only audit in the same transaction, scope D-40, 1 year | T-20; INV-PLT-009 |
| L17 | Enumeration, unthrottled OTP/reset, no re-auth for 2FA | uniform responses, throttles, fresh credential check | T-04, T-05; INV-IDN-006, INV-IDN-008 |

Ops-side legacy defects (X1-013, X1-080..083): secrets as files without defaults ([secrets](secrets-and-keys.md)), backups and restore drill ([backup](../11-operations/backup-restore.md)), rolling release ([environments](../11-operations/environments-and-ci.md)).

## Accepted residual risks (need the owner's signature when the plan is accepted)

1. Whole-book reading equals copying (T-24).
2. Up to 30 days of data can be lost between monthly backups (T-26, D-33).
3. Ingestion cannot go live without the source's written permission (T-21, D-03).
