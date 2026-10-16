# Catalog record entry and publication metadata

Global metadata managers and administrators can create records at
`/manage/books/new/`. Book-scoped editors keep their existing editing rights and
cannot create arbitrary catalog records. The backend supplies the workspace's
`can_create_books` flag; UI visibility never grants permission.

The management overview now exposes source import and manual entry directly.
Automated creation uses the single configured website; its hostname comes from
deployment configuration, with only its `www` alias accepted. Manual records
and EPUB uploads remain available alongside that workflow.

`POST /api/v1/manage/books/` accepts an explicit request UUID, title, record type
(`digital` or `manual`), optional summary, edition, language code, publisher,
price, binding, and compilation status. Prices use decimal values with two
places, never floating-point arithmetic. Language codes and field sizes are
validated. Unknown publication/review/ownership fields are rejected.

New records enter `needs_review`, have no editorial approval, and are ineligible
for indexing by default. Creation never inserts `UserBook` ownership or an
access grant. The existing edit, review, publish, and withdraw workflow applies
afterward. Record type remains fixed after creation; editions and publication
fields can be edited with the other revision-checked metadata.

The request UUID also identifies the new record and immutable creation audit.
Replaying the same creator's original command returns its current record,
including renamed slugs. Different input or another creator using that UUID
returns a conflict. `GET /api/v1/manage/book-creations/<uuid>/` allows the creator
to inspect an uncertain result without resubmitting it. The form retains its
request UUID, preserves validation drafts, and blocks uncertain resubmission.

Creation locks the current actor, then the normalized title before assigning a
slug. Source-to-book publication shares that title lock. Concurrent requests
for distinct editions of the same title receive separate records/slugs; repeated
requests produce one record and audit. UUID collisions roll back atomically.
Editorial mutations lock and reload the actor before checking book permissions,
so removed administrative authority cannot survive as a stale request object.

Catalog-code allocation also holds a shared PostgreSQL advisory lock until the
model save commits. This protects distinct concurrent model creations, including
source workers and setup tools that do not enter the metadata administration
service. Books, contributors, categories and series retain their existing code
format and assigned values. Deterministic tests gate the first allocation while
a competing transaction attempts another, then require two distinct valid codes.

Publication-field edits preserve the previous values in `MetadataVersion`, reset
review, and use the same timestamp conflict checks as editorial text. Decimal
snapshot values are JSON-safe strings. A successful refresh preserves the
editor component and its confirmation message; an unrelated revision cannot
silently erase an unfinished draft.

## Manual EPUB uploads

After creating a digital record, open its editor and use **EPUB আপলোড**.
`POST /api/v1/manage/books/<slug>/epub/` accepts multipart `file` and
`expected_updated_at`. Uploads are limited to 24 MiB, below the production
proxy's 32 MiB request limit. The local Next proxy also accepts 32 MiB so it does
not truncate valid uploads above its previous 10 MiB default.

The existing EPUB archive and manifest validators reject invalid paths,
encrypted/special entries, excessive expansion, unsafe XML, and missing readable
chapters. The service reloads and locks the actor and book, rechecks scoped
metadata permission and the book revision, and rejects unfinished source work
or paper records. Files use new private names; replacement preserves previous
bytes and prepared reader sessions. Successful uploads record an audit, clear
editorial approval, and return the record to review without granting ownership.
Concurrent uploads using the same revision produce one success and one conflict.

Use **পড়ার জন্য প্রস্তুত করুন** under reading assets, inspect the persisted job,
then review and publish the book. Reader preparation sanitizes document bodies
and verifies resource contents through the existing worker. The form preserves
failed selections, blocks uploading over unfinished metadata, and never replays
an uncertain upload. A dispatcher and processing worker must be running to
complete preparation jobs; accepting the upload alone does not start a worker.

Verification covers creation and validation, CSRF, privacy and authorization,
duplicate commands, concurrent editions and UUID collisions, revoked authority,
decimal snapshots, and stale edits. Browser journeys cover 320-pixel forms with
200% text, paper-book entry/editing, ownership isolation, scoped-account denial,
and uncertain commands. [Entity and relationship administration](catalog-entities.md)
adds author/category/series/collection editors, remote relationship selectors,
and explicit edition grouping. Public cross-edition browsing and the remaining
physical-book reader workspace are outstanding parts of the accepted plan.
