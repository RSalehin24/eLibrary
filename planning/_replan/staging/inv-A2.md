# Staged invariants (wave A2): IDN, GWY, NTF, PLT, NFR

Status: DRAFT

For merge into the invariants register by the parent. Format: `- **INV-X-NNN** · <service> · by: <mechanism> · <statement>`.

## IDN

- **INV-IDN-001** · identity · by: model, type · No account is Active without consuming a valid invite link or being the seeded first admin.
- **INV-IDN-002** · identity · by: model, db · A link token is consumed at most once and never after its expiry or after a newer link for the same account and purpose was issued.
- **INV-IDN-003** · identity · by: type · A value of type `Secret<T>` cannot be formatted, serialized to logs, or compared in non-constant time.
- **INV-IDN-004** · identity · by: model, type · A session of an account with required TOTP exists only after a valid second factor was accepted for it.
- **INV-IDN-005** · identity · by: model, db · The last accepted TOTP time step per account only increases.
- **INV-IDN-006** · identity · by: model, e2e · No TOTP disable or password change is applied without a fresh credential check in the same request.
- **INV-IDN-007** · identity · by: model, db · A revoked or expired session never yields an authorization Allow.
- **INV-IDN-008** · identity · by: prop, e2e · The response body, status and timing class of a reset or sign-in request do not depend on whether the account exists.
- **INV-IDN-009** · identity · by: model, db · Every stored status change is in the allowed transition relation.
- **INV-IDN-010** · identity · by: type, db · The set of scopes a subject holds is the union of its role scopes and its active grants; no value matches every scope.
- **INV-IDN-011** · identity · by: type, db · Every grant row names a valid scope, a valid target for that scope and is unique among active rows for (user, scope, book).
- **INV-IDN-012** · identity · by: model, db · A grant or role change has actor != subject and an audit row committed in the same transaction.
- **INV-IDN-013** · identity · by: model, type · If no explicit role scope or active grant matches, the decision is Deny.
- **INV-IDN-014** · identity · by: model, prop · An unauthenticated subject has no scope except the public set.
- **INV-IDN-015** · identity · by: model, prop · No decision depends on shelf, ownership or submission data.
- **INV-IDN-016** · identity · by: model, prop · For a non-`manage_catalog` subject, Allow on a book scope implies the book version is published and not deleted.
- **INV-IDN-017** · identity · by: model, prop · A grant with expires_at <= now, or revoked, contributes no scope.
- **INV-IDN-018** · identity · by: model, prop · decide(S + grant) >= decide(S) for every scope other than read_once.
- **INV-IDN-019** · identity · by: model, prop · decide is a pure function of (roles, grant set, subject state, book state, now).
- **INV-IDN-020** · identity · by: model, prop · Per (user, book) at most one ticket redemption is counted as an opening while read_once is the only read scope.
- **INV-IDN-021** · identity · by: type, prop, fuzz · A ticket verifies only for its user, book, version, before its expiry and while its grant version equals the current one.
- **INV-IDN-022** · identity · by: model, prop · Redeeming a ticket twice yields the same result and one audit row of kind open.
- **INV-IDN-023** · identity · by: model, prop · Every committed user disable or grant change has exactly one event with a monotonically increasing cursor.
- **INV-IDN-024** · identity · by: type, e2e · The route table of a running service has no entry without a declared scope or `public`.
- **INV-IDN-025** · identity · by: model, e2e · A management Allow requires session.totp_done when the account requires TOTP.
- **INV-IDN-026** · identity · by: model, e2e · A session with role demo is Denied every mutating route and every scope outside the demo set.
- **INV-IDN-027** · identity · by: model · No row owned by the demo account is readable through another demo session.
- **INV-IDN-028** · identity · by: type · Every stored Kindle address parses as KindleEmail and a user has at most 5.
- **INV-IDN-029** · identity · by: db, e2e · Every security-relevant identity state change has an audit row in its transaction, and the audit table has no UPDATE or DELETE privilege.
- **INV-IDN-030** · identity · by: model, e2e · The capability set equals the scopes identity would Allow for the same subject.
- **INV-IDN-031** · identity · by: review, e2e · Account deletion leaves no user row, session, grant or Kindle address in identity.
- **INV-IDN-032** · identity · by: review, static · A production build contains no route or command that creates a user with a fixed credential.

## GWY

- **INV-GWY-001** · gateway · by: review, e2e · The set of publicly reachable paths equals the route table; `/internal/*` is never routed.
- **INV-GWY-002** · gateway · by: e2e, type · A request reaches an upstream service only after an identity Allow or on a listed public route.
- **INV-GWY-003** · gateway · by: type, review · The public allow-list equals the list in the architecture brief.
- **INV-GWY-004** · gateway · by: e2e, fuzz · No upstream request carries an identity header that identity did not produce.
- **INV-GWY-005** · gateway · by: e2e · A cookie-authenticated POST, PUT, PATCH or DELETE without a valid CSRF token is rejected before reaching a service.
- **INV-GWY-006** · gateway · by: e2e · The request id seen by a service equals the one in the gateway log and response.
- **INV-GWY-007** · gateway · by: prop, e2e · The rate-limit table never exceeds its configured size and a limited key cannot exceed its quota per window.
- **INV-GWY-008** · gateway · by: review, type · The gateway crate depends on no domain or storage crate.
- **INV-GWY-009** · gateway · by: e2e · Every response carries the required security headers.
- **INV-GWY-010** · gateway · by: prop, e2e · No request or response is buffered above the configured bound.
- **INV-GWY-011** · gateway · by: e2e, review · The gateway and Caddy configuration contain no file-system root for book assets.
- **INV-GWY-012** · gateway · by: e2e · Every gateway-generated error body is a typed envelope with a request id.
- **INV-GWY-013** · gateway · by: e2e · A stream is closed when its session is revoked or exceeds its idle bound.
- **INV-GWY-014** · gateway · by: e2e · Health endpoints are not reachable from the public edge.

## NTF

- **INV-NTF-001** · notify · by: model, prop · No event id leads to two accepted sends except after a recorded unknown outcome.
- **INV-NTF-002** · notify · by: prop, e2e · A producer's transaction outcome does not depend on notify availability.
- **INV-NTF-003** · notify · by: unit · Every template renders with both locales and escapes its parameters.
- **INV-NTF-004** · notify · by: type, unit · No log line or error text contains a full link, token or address.
- **INV-NTF-005** · notify · by: model, e2e · A Kindle mail is sent only after an identity Allow for the user at send time.
- **INV-NTF-006** · notify · by: prop, e2e · Every sent Kindle mail passed preflight.
- **INV-NTF-007** · notify · by: prop, e2e · No user exceeds the Kindle send quota per window; memory per send is bounded by the size cap.
- **INV-NTF-008** · notify · by: model, prop · A delivery in permanent state is never attempted again and attempts never exceed the maximum.
- **INV-NTF-009** · notify · by: db, e2e · Every send attempt has exactly one delivery log row.
- **INV-NTF-010** · notify · by: e2e · No request path of another service awaits SMTP.
- **INV-NTF-011** · notify · by: review, static · Notify has no route reachable through the gateway.
- **INV-NTF-012** · notify · by: db · No delivery log row exceeds the retention window plus one job interval.

## PLT

- **INV-PLT-001** · all · by: review, e2e · The Compose file lists every runtime component, with limits, and only caddy publishes host ports.
- **INV-PLT-002** · all · by: review, e2e · A service role has no privilege on another service's database.
- **INV-PLT-003** · all · by: unit, e2e · `main` returns a typed startup error rather than serving when a precondition fails.
- **INV-PLT-004** · all · by: e2e · Readiness is false whenever the service cannot reach its database.
- **INV-PLT-005** · all · by: type · No service defines its own wire type.
- **INV-PLT-006** · all · by: prop · Applying a mutation twice with the same key leaves state as after once.
- **INV-PLT-007** · all · by: fuzz, static · Request handling code contains no panicking construct.
- **INV-PLT-008** · all · by: prop, e2e · No collection or loop driven by input or a remote system is unbounded.
- **INV-PLT-009** · all · by: db, e2e · Audit tables have no UPDATE or DELETE privilege for any service role.
- **INV-PLT-010** · all · by: model, prop · Every committed change that defines an event has exactly one outbox row with an increasing cursor.
- **INV-PLT-011** · all · by: type · No domain code calls the system clock directly.
- **INV-PLT-012** · all · by: type, review · No function exceeds the shape caps without a dated waiver.
- **INV-PLT-013** · all · by: review · Every locked dependency appears in the dependency register.
- **INV-PLT-014** · all · by: review · Every lint suppression in code has a matching unexpired waiver.
- **INV-PLT-015** · all · by: drill · The latest backup restores into an empty stack that passes the smoke checks.
- **INV-PLT-016** · all · by: review, static · No secret value appears in an image, an environment listing, a log or the repository.
- **INV-PLT-017** · all · by: review, e2e · No request handler invokes pipeline steps directly.
- **INV-PLT-018** · all · by: type · No retry decision pattern-matches an error message.
- **INV-PLT-019** · all · by: e2e, metric · Every log line has a request id or a job id.
- **INV-PLT-020** · all · by: type, e2e · Every internal route rejects requests without a valid service token.
- **INV-PLT-021** · all · by: db · No row older than its retention window plus one job interval exists.
- **INV-PLT-022** · all · by: e2e, drill · A release leaves the previous image runnable until the new one is healthy.
- **INV-PLT-023** · all · by: db · Every enum-valued column has a CHECK or enum type and no status is stored in two places.

## NFR

- **INV-NFR-001** · all · by: metric, e2e · Measured monthly availability is at least 99.5%.
- **INV-NFR-002** · all · by: metric · Load-test percentiles stay within the stated limits.
- **INV-NFR-003** · all · by: metric · The load test at the stated capacity passes all latency targets.
- **INV-NFR-004** · all · by: drill · The restore drill finishes within the RTO and restores data younger than the RPO.
- **INV-NFR-005** · all · by: metric, review · No container exceeds its memory limit under the capacity test, and image and page sizes stay within the stated limits.
- **INV-NFR-006** · all · by: review · Requests above these limits are rejected with a typed error.
- **INV-NFR-007** · all · by: review, e2e · Each threat-model item has a mitigation or a signed acceptance.
- **INV-NFR-008** · all · by: e2e · Automated a11y scans and manual checks pass in both themes.
- **INV-NFR-009** · all · by: e2e · The e2e matrix passes on every listed browser and width.
- **INV-NFR-010** · all · by: unit · The string catalogs have identical key sets.
- **INV-NFR-011** · all · by: review, static · The dependency graph has no service-to-service edge except contracts.
- **INV-NFR-012** · all · by: prop · Running a build twice on the same input gives byte-identical artifacts except documented timestamps.
- **INV-NFR-013** · all · by: metric · The reconciliation count after drain is zero.
- **INV-NFR-014** · all · by: metric · Time to ready stays within the stated limits.
