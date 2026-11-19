# Requirements - Notify (NTF)

Status: DRAFT · Service: [notify](../05-services/notify/README.md)

Line format: `REQ-ID · priority · inv: <invariants> · verify: <methods> · statement`

- **REQ-NTF-001** · MUST · inv: INV-NTF-001 · verify: model, prop · Notify consumes `email.requested` and `kindle.requested` from the producers' outbox endpoints with a stored cursor; each request is handled idempotently by event id, so one issued link or one Kindle request yields at most one send unless a retry follows an unknown outcome (documented at-least-once).
- **REQ-NTF-002** · MUST · inv: INV-NTF-002 · verify: e2e, prop · Invitation and password reset mails are sent once per issued link; a mail failure never blocks or rolls back account creation or the reset request.
- **REQ-NTF-003** · SHOULD · inv: INV-NTF-003 · verify: unit · Templates exist in Bengali and English, are selected by the account language, and escape every interpolated value.
- **REQ-NTF-004** · MUST · inv: INV-NTF-004 · verify: type, unit · Links, tokens and addresses never appear in logs or error messages; the delivery log stores a masked address.
- **REQ-NTF-005** · MUST · inv: INV-NTF-005 · verify: model, e2e · A Kindle send is queued asynchronously and requires an Allow for the `kindle` scope from identity both when requested and when sent (account still Active), a Kindle address on the account, and the book being published (answers X1-075).
- **REQ-NTF-006** · MUST · inv: INV-NTF-006 · verify: prop, e2e · Kindle preflight rejects before sending: unsupported format (EPUB only), total email size above 50 MB, missing or invalid address, and an address whose owner has not confirmed that our sender is on their Amazon Approved Personal Document E-mail List; the result is recorded with a typed reason.
- **REQ-NTF-007** · MUST · inv: INV-NTF-007 · verify: prop, e2e · Kindle sending is rate-limited per user and per book and bounded in memory: at most one attachment is held per send, with a configured number of concurrent sends (answers X1-075).
- **REQ-NTF-008** · MUST · inv: INV-NTF-008 · verify: model, prop · Failures carry a typed class, `retryable` or `permanent`; retryable failures retry with exponential backoff up to a maximum attempt count and then end in a visible `failed` state; permanent failures are never retried; the decision never depends on error text.
- **REQ-NTF-009** · MUST · inv: INV-NTF-009 · verify: db, e2e · The delivery log holds one row per attempt (kind, status, error class, time, masked address, event id); Kindle status is reported back to catalog so the book's Files tab shows it (D-30) (answers X1-042).
- **REQ-NTF-010** · MUST · inv: INV-NTF-010 · verify: e2e, drill · Mail failures are isolated: an SMTP outage, a slow SMTP server or an unhealthy notify container cannot slow or fail any other service; SMTP calls have timeouts and the outbox backlog is bounded and alerted.
- **REQ-NTF-011** · MUST · inv: INV-NTF-011 · verify: review, e2e · SMTP credentials and the sender address come from secret files and configuration validated at startup; notify exposes no public route and accepts work only by pulling events (D-53): it has no route that sends a message directly.
- **REQ-NTF-012** · SHOULD · inv: INV-NTF-012 · verify: db, unit · Outbox, templates and delivery log rows older than the documented retention are deleted by a bounded job.
