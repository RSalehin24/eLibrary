# identity - test plan

Status: DRAFT

Levels: model (TLA+/Alloy, [formal models](../../03-correctness/formal-models)), type (compile-fail), prop, fuzz, unit, db, e2e (Compose stack with a mail sink), contract. Clock and randomness are injected.

| ID | Level | What | Maps to |
|---|---|---|---|
| TST-IDN-001 | model | account lifecycle: status graph, link single-use, supersede, no Active without link or seed | REQ-IDN-001, 009; INV-IDN-001, 009 |
| TST-IDN-002 | prop | random sequences of issue, consume, expire, resend, suspend never leave the allowed link and status states | REQ-IDN-002; INV-IDN-002 |
| TST-IDN-003 | unit | two concurrent consumes of one link: exactly one succeeds; reused, expired, superseded give the identical response | REQ-IDN-002; INV-IDN-002 |
| TST-IDN-004 | type | `Secret<T>` has no Display or Debug; formatting and logging fail to compile; compare is constant-time | REQ-IDN-003; INV-IDN-003 |
| TST-IDN-005 | unit | Argon2id parameters, minimum length, deny list; reset confirm applies the rules | REQ-IDN-003 |
| TST-IDN-006 | e2e | invite, mail sink, accept, sign in, TOTP setup and confirm, sign in with TOTP | REQ-IDN-001, 004 |
| TST-IDN-007 | model | no authenticated session exists for a TOTP-required account before the second factor | REQ-IDN-004; INV-IDN-004 |
| TST-IDN-008 | prop+unit | TOTP replay rejected; same or earlier step rejected; concurrent verifications accept once; failures counted | REQ-IDN-005; INV-IDN-005 |
| TST-IDN-009 | e2e | disabling TOTP, revealing the secret and changing password without fresh credentials are refused | REQ-IDN-006; INV-IDN-006 |
| TST-IDN-010 | prop | revoked or expired session never yields Allow (random times, injected clock) | REQ-IDN-007; INV-IDN-007 |
| TST-IDN-011 | e2e | logout, suspend, disable, delete and password change revoke the next request | REQ-IDN-007 |
| TST-IDN-012 | prop | sign-in, reset, invite acceptance, TOTP verify: known and unknown accounts give equal status, body shape and timing class; throttles per account and address | REQ-IDN-008; INV-IDN-008 |
| TST-IDN-013 | unit | status transition function exhaustive: only Invited, Active, Suspended, Disabled edges; each audited and evented | REQ-IDN-009; INV-IDN-009 |
| TST-IDN-014 | type+unit | role and scope enums closed; no role holds every scope; adding a scope without updating the table fails the test; `is_staff` and `admin:full_control` unrepresentable | REQ-IDN-010, 011; INV-IDN-010 |
| TST-IDN-015 | db | grant `CHECK`s: unknown scope, book on non-book scope, duplicate active grant, self-grant rejected | REQ-IDN-011, 012; INV-IDN-011 |
| TST-IDN-016 | e2e | admin cannot grant or edit own role or status; cannot demote or disable last active admin | REQ-IDN-012; INV-IDN-012 |
| TST-IDN-017 | db | grant, role and status mutation commit with their audit row (fault injection between them) | REQ-IDN-012, 029; INV-IDN-012 |
| TST-IDN-018 | model | `access` model against the scope table: anonymous limited, dead grants ignored, monotonic, management needs authority, unpublished hidden | REQ-IDN-013..019 |
| TST-IDN-019 | prop | `decide` total, never panics, Deny when nothing matches | REQ-IDN-013; INV-IDN-013 |
| TST-IDN-020 | e2e | anonymous reaches only the closed public set; preview text, read, download, Kindle and management denied | REQ-IDN-014; INV-IDN-014 |
| TST-IDN-021 | prop+unit | shelf, import and ownership data never change a decision; default grants of a new reader come from configuration; `download` and `read_once` need a grant | REQ-IDN-015; INV-IDN-015 |
| TST-IDN-022 | prop | non-`manage_catalog` Allow implies published and not deleted for every role and grant mix | REQ-IDN-016; INV-IDN-016 |
| TST-IDN-023 | prop | expired and revoked grants contribute nothing; suspended or disabled user denied all scopes | REQ-IDN-017; INV-IDN-017 |
| TST-IDN-024 | prop | adding a grant never turns Allow into Deny except read-once | REQ-IDN-018; INV-IDN-018 |
| TST-IDN-025 | prop | permuting grants and roles never changes the decision; identical inputs give identical output | REQ-IDN-019; INV-IDN-019 |
| TST-IDN-026 | model | read-once: consumed on redemption only, once per user and book, not at open, not on missing copy | REQ-IDN-020; INV-IDN-020 |
| TST-IDN-027 | e2e | two concurrent redemptions: one consumes; retry with the same ticket allowed; other ticket gets `read_once_consumed`; admin reset restores | REQ-IDN-020, 022 |
| TST-IDN-028 | fuzz+type | ticket verify input (ids, secret, lengths, encodings) never panics; secret type not loggable | REQ-IDN-021; INV-IDN-021 |
| TST-IDN-029 | unit | ticket lifetime never exceeds 15 minutes; no route accepts a ticket in a URL; only hash stored | REQ-IDN-021 |
| TST-IDN-030 | prop | ticket rejection matrix: other user, book, version, expired, issued before `grant.changed` or `user.disabled`, book unpublished | REQ-IDN-022; INV-IDN-022 |
| TST-IDN-031 | contract+prop | `/internal/events`: ordered, no duplicates inside a page, empty page keeps cursor, restart from cursor reproduces; consumers idempotent | REQ-IDN-023; INV-IDN-023 |
| TST-IDN-032 | e2e | route without scope declaration refuses start; unknown path at `/internal/authorize` gives 403; forwarded scopes honoured | REQ-IDN-024; INV-IDN-024 |
| TST-IDN-033 | e2e | admin or operator with TOTP incomplete is denied every management scope | REQ-IDN-025; INV-IDN-025 |
| TST-IDN-034 | unit | `KindleEmail` validation; limit 5; owner only and only with `kindle` | REQ-IDN-028; INV-IDN-028 |
| TST-IDN-035 | db | `audit_log` rejects UPDATE and DELETE for the service role; retention job removes only rows older than 1 year | REQ-IDN-029; INV-IDN-029 |
| TST-IDN-036 | e2e | every audited action in REQ-IDN-029 writes a row with actor, subject, request id, address, user-agent hash | REQ-IDN-029 |
| TST-IDN-037 | e2e | `/me/capabilities` equals the effective set; 401 vs 403 distinct and 403 keeps the session | REQ-IDN-030; INV-IDN-030 |
| TST-IDN-038 | e2e | admin list bounded and searchable; resend supersedes; delete removes account and image; own export JSON; deletion announcement (**OPEN O-1**) | REQ-IDN-031; INV-IDN-031 |
| TST-IDN-039 | review+e2e | production build has no seed, test or advance route; seed refuses when an admin exists, defaults to dry-run, sets no password | REQ-IDN-032; INV-IDN-032 |
| TST-IDN-040 | e2e+static | `admin-reset` works only as host command, dry-run default, audited, sets a setup link; no HTTP route; self and last-admin rules stay | REQ-IDN-033; INV-IDN-033 |
| TST-IDN-041 | fuzz+e2e | profile image: SVG and mismatched type refused, size limit at limit-1/limit/limit+1, re-encode or strict validation, never on a public route, deleted with the account | REQ-IDN-034; INV-IDN-034 |
| TST-IDN-042 | fuzz | token, email, cookie and JSON parsers do not panic | REQ-PLT-007 |
| TST-IDN-043 | db+e2e | `POST /grants/batch`: several scopes granted or revoked atomically (one invalid item leaves nothing changed), self-grant refused, duplicate refused, one `grant.changed` per request | REQ-IDN-011; REQ-WEB-018 |
