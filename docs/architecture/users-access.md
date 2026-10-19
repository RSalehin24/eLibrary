# Users and scoped access

The new `/manage/users-access/` workspace provides bounded account search,
account activation/name/TOTP policy changes, and account/book/category/writer
grants. Django owns every authorization and write; the frontend uses the
generated `/api/v1/` contract. Existing `/api/` contracts remain unchanged.

Account lists restore case-insensitive name/email ascending and descending sorts,
active-first ordering and permission/status keyword search. All orders use a stable
ID tie-breaker and preserve query/status filters across bounded pages. Permission
search matches effective global grants, excluding expired or scoped grants.

The Add Reader form defaults to emailed setup. Super administrators can instead
set an initial password, preserving the previous account-creation workflow without
requiring mail. Passwords require 12–4,096 characters and matching confirmation;
literal spaces are preserved. The optional generator uses 24 bytes from the
browser's cryptographic random source, plus a nonnumeric prefix, and copying
requires an explicit click. The server applies the same configured Django
strength validators as password reset, including common/numeric/identity checks.
`POST /api/v1/manage/users/` rechecks active superuser authority under a row lock,
creates an ordinary account (active by default, optionally initially disabled)
using the existing user manager and password
hasher, and creates no grants, mail jobs or delivery requests. The existing TOTP
setup gate still applies when requested. Access managers retain mailed setup.

A client-generated UUID identifies a direct creation. Its audit receipt stores
only actor/target identifiers, never names, emails, passwords or password hashes.
Identical retries reuse the account while its original fields and password still
match; changed requests or changed credentials return a conflict and never reset
the account. Unknown identity/privilege fields are rejected. Creation uses real
CSRF protection and private, no-store responses.

## Authorization

A global, active `access:manage` grant, global full control, or the retained
staff/superuser policy enables the workspace. Scoped access-management grants
do not authorize it. Every write locks and rechecks the current actor and target.
Accounts are locked in ID order to avoid opposite-order write deadlocks.

- Managers can edit other ordinary accounts and issue the existing manageable
  global/scoped permissions. Administrative scopes are restricted to account
  targets; only the existing six scoped permissions apply to books/categories/writers.
- Own-account changes use Profile. This workspace cannot edit its actor.
- Superuser accounts remain protected. Only a superuser can manage another
  staff/full-control account's ordinary fields and manageable grants.
- Existing-account email/password changes, staff flags, superuser flags, and
  full-control grants are excluded from these forms. Unknown write fields are
  rejected. The separate superadministrator initial-password creation is the
  explicit exception described above.
- Grant creation does not create `UserBook` ownership or consume read-once access.
- Permission updates preserve their account, scope, and target identity. Managers
  can revoke/reactivate grants or edit comments/expiry; changing identity requires
  a separate grant. Database foreign keys and `permission_grant_single_target`
  prevent a grant from linking multiple target types.

## Writes and concurrent changes

Account and grant updates require `expected_updated_at`; stale writes return
`409 state_conflict`. Account locks serialize duplicate/opposing grant decisions,
including concurrent read-once/durable-read requests. Active identical targets
are rejected, while revoked/expired grants remain visible for review.

Creation supplies a client-generated grant UUID. Identical retries return the
original grant; collisions with different requests return a conflict, including
requests from different administrators/accounts. Mutations are not automatically
replayed. The interface preserves drafts and disables uncertain writes until
the operator explicitly reloads the current state.

Audit records contain actor and target IDs and the action, without names,
email addresses, notes, credentials, or tokens. Grant expiry uses the server's
current time; the interface distinguishes effective, expired, and revoked grants.
Dates use Asia/Dhaka. Expiry inputs show a date and explicit 12-hour AM/PM time,
independently of the browser's time zone. Leaving the date blank removes expiry.

## Multiple permissions

The account workspace exposes multi-select books, categories or writers and
multiple permission checkboxes alongside the retained single-grant form. Search
keeps selected targets, with at most 20 targets and 100 resulting grants per
submission. Read-once and durable-read selections are mutually exclusive. The
account identity and resulting scope/target count are visible before submission.

`POST /api/v1/manage/users/<id>/grants/bulk/` accepts up to 100 entries with
distinct client-generated grant UUIDs. It reuses single-grant validation, account
locks, permission checks and privacy-preserving audits. Each entry commits
independently; an invalid or conflicting item does not undo successful items.
The response preserves input order and reports created, previously saved or
rejected results individually. Protected-account and envelope errors write
nothing. Identical UUID retries return the original record, including a revoked
record, without reactivating it. Changing an existing UUID's identity or data
returns a conflict. An uncertain response retains the selection and stops
automatic resubmission.

## Reads and presentation

Account and grant lists default to 50 records and cap at 100, with deterministic
ID tie-breakers and page envelopes. Account summaries annotate grant counts,
confirmed TOTP, and protected status in the query. Grant relationships are fetched
together. The checked 100-record grant/reference pages retain fixed query counts.

Reference selectors fetch at most 24 matching books, categories, or writers per
read. They debounce by 250 ms, cancel obsolete requests, reset an obsolete target,
and require an explicit selection. Deleted books and non-author contributors are
excluded. Narrow screens use cards, native disclosures, and full-width fields.
Account and grant drafts participate in app-update and unload guards. An unrelated
query refresh cannot silently replace a form's original revision.

All pages and API responses are private, `no-store`, and `noindex`. Passwords,
Kindle addresses, profile images, setup nonces, and authenticator secrets are
excluded from account summaries. Account changes across tabs clear private state
through the shared account boundary.

## Verification and remaining work

The focused PostgreSQL run passed 35 new access cases and 20 retained authentication
cases. It exercises real CSRF, revisions, protected accounts, unknown privilege
fields, grant identity, reactivation, expiry, deleted targets, query bounds,
database constraints, audit privacy, and four concurrent write scenarios.
Chromium checks cover the phone workflow, independent ownership, stale edits,
uncertain outcomes, obsolete searches, and unfinished app-update guards.
The combined platform run passed 464 backend cases and all 82 Chromium journeys.
Strict TypeScript, ESLint, mypy (127 files), Ruff/formatting, OpenAPI validation,
fresh test-database migrations, architecture checks, and the production build passed.
All eight specified widths and 200% text at 320 pixels passed; phone and desktop
access screenshots were inspected. The 18 pre-existing file-size violations and
broader legacy-suite failures remain recorded in the foundation document.

Queued invitation creation/resend, private outcomes, and anonymous reset requests
are implemented in [account mail](account-mail.md). Live broker verification
remains part of external acceptance. The bulk-grant increment passed 41 focused
PostgreSQL access regressions and four deterministic web helper tests; its
integrated browser evidence belongs in the implementation handoff. This increment
does not mark the Users & Access section or administration phase complete. It
does not authorize external mail delivery, production deployment, or account deletion.
The [password-link confirmation/setup](password-links.md) increment supplies the
receiving step and required-TOTP gate.
