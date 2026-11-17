# Threat model (STRIDE, per trust boundary)

Status: DRAFT

Assets: accounts and credentials; full book text (licensed content); personal reading data; admin capabilities; signing keys; availability.

| ID | Threat | Boundary | Category | Mitigation | Invariant / test |
|---|---|---|---|---|---|
| T-01 | Scraping the full text through preview/search endpoints | internet↔gateway | Info disclosure | preview is a separate artifact; index uses PublicDocument; leak canary test; rate limits | INV-CON-003, INV-DSC-004 |
| T-02 | Reading without account or grant | internet↔content | Elevation | capability required; short TTL; offline verify; access decide | INV-CON-004, INV-ACC-002 |
| T-03 | Capability theft/replay | client | Spoofing | bound to subject/book/set/action; ≤ 300 s; HTTPS only; not in URLs for chapters (header); EPUB link single-use token variant | INV-ACC-008 |
| T-04 | Credential stuffing/brute force | internet↔identity | Spoofing | throttling, uniform responses, Argon2id, TOTP, breached-password check | INV-IDN-006 |
| T-05 | Account enumeration | identity | Info disclosure | uniform responses/timing | INV-IDN-006 |
| T-06 | Session hijack | client | Spoofing | HttpOnly Secure SameSite cookies, token hashes at rest, rotation, revocation | INV-IDN-005 |
| T-07 | CSRF on state-changing endpoints | browser | Tampering | CSRF token + Origin check + SameSite | INV-GWY-002 |
| T-08 | XSS via scraped HTML/annotations | content/web | Tampering | `SafeHtml`, CSP (no inline script), output encoding, sanitizer fuzzing | INV-CON-009 |
| T-09 | SSRF via submitted URLs | ingestion | Tampering | canonicalize to configured source hosts only; block private IP ranges after DNS resolution; no redirects off-host | INV-ING-012 |
| T-10 | Malicious EPUB upload (zip bomb, XXE, path traversal) | ingestion | DoS/Tampering | size/entry/ratio limits, no external entities, path normalization, sandboxed parsing in a separate process | fuzz |
| T-11 | Privilege escalation via mis-scoped grants | access | Elevation | pure `decide`, Alloy checks, audit, MFA for management | INV-ACC-003/009 |
| T-12 | Insecure direct object reference (library data) | library | Info disclosure | owner from session, RLS, 404 for others | INV-LIB-003 |
| T-13 | Service impersonation inside the host | internal | Spoofing | per-service keys, audience-bound tokens, allow-list routes, private network | service-auth |
| T-14 | Poisoned source content producing wrong catalog data | source↔ingestion | Tampering | evidence, review thresholds, publish gate, audit of changes | INV-ING-007 |
| T-15 | DoS on public search/page | internet | DoS | rate limits, caching, bounded queries, timeouts | INV-PLT-005 |
| T-16 | Mail abuse (using invite/reset to spam) | notify | Abuse | per-address and global caps, admin-only invites, uniform reset | limits |
| T-17 | Secrets leak in logs/events | all | Info disclosure | `Secret<T>`, log redaction tests | INV-IDN-003 |
| T-18 | Supply-chain compromise | build | Tampering | lockfile, `cargo deny/audit`, minimal deps, reproducible builds, signed releases | Q5 |
| T-19 | Backup theft | ops | Info disclosure | encrypted offsite backups (age), key separate | INV-PLT-008 |
| T-20 | Insider (admin) misuse | admin | Repudiation | append-only audit, MFA, grant review, export logging | INV-PLT-006 |
| T-21 | Legal takedown / rights claim | business | — | per-source unpublish, attribution, provenance records | D-03 |

Review cadence: at every gate and on each new public route or data class.
