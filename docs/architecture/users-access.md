# Users and scoped access

The new `/manage/users-access/` workspace provides bounded account search,
account activation/name/TOTP policy changes, and account/book/category/writer
grants. Django owns every authorization and write; the frontend uses the
generated `/api/v1/` contract. Existing `/api/` contracts remain unchanged.

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
- Email, passwords, staff flags, superuser flags, and full-control grants are
  excluded from these forms. Unknown write fields are rejected.
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
Dates are displayed in UTC and edited with explicitly labelled local-time inputs.

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
and bulk outcomes remain part of the accepted administration work. This increment
does not mark the Users & Access section or administration phase complete. It
does not authorize external mail delivery, production deployment, or account deletion.
The [password-link confirmation/setup](password-links.md) increment supplies the
receiving step and required-TOTP gate.
