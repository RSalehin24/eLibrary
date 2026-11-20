# Source content: rights, attribution, behavior

Status: DRAFT · D-03 stance decided; D-99 (2026-11-20) replaced the written-permission blocker with the owner's own account and an accepted risk, so G6 is no longer blocked on it

This records the legal facts and the engineering stance. The plan cannot grant permission; the owner must obtain it. The engineering follows what is decided.

## What the system does with the source

- Ingestion mirrors the source site's catalog listing, scrapes books on an operator's request, builds EPUBs and serves them to signed-in readers of this private, invite-only library.
- The legacy system also stored a logged-in cookie and submitted "mark complete" forms on the source. That is **removed** (D-03).

## Decisions in force

| Rule | Source |
|---|---|
| ~~Obtain the source's written permission before go-live~~ replaced by **the owner's own account only**: the owner logs in to the source in a browser and supplies the cookie; the owner accepts the residual risk of copying into a private shared library | D-03, D-99, gate G6 |
| **Gold-corpus labelling may start before permission, for private research only**: GET-only fetches by the owner, pages and labels stay outside the repository and are never committed, shared or published. Permission remains the blocker for ingestion go-live (G6) and for any publication | D-51 |
| Acquisition is **GET only**: the HTTP client type has no other method and no form encoder; a future non-GET action needs a new owner decision, not a code change | D-03, INV-ING-010 |
| Locked chapters wait for an export, an API or sanctioned access from the source; the system never changes source state | D-03 |
| **Nothing scraped is published to the open web**: scraped text is shown only to signed-in readers; raw pages stay on the ingestion volume and are never served or committed | D-34, INV-ING-012 |
| **Public pages show metadata only** (title, contributors, summary, cover, categories). No preview text and no book text are public; search engines may index metadata only | D-34, D-09 |
| No manual upload of third-party files in v1 | D-42 |
| No third-party AI or external service receives book text | this plan |
| The gold corpus and snapshots are access-controlled, never published and never committed | CLAUDE.md |
| Honest User-Agent with a contact address; no evasion of bot protection; polite delay and concurrency cap | new-architecture section 10 |

## Residual legal risk (D-51)

Labelling before permission means pages from the source are copied without the source's consent. That is a real exposure: the source could regard the copies as infringement or a terms breach even when they are private and GET-only. The plan reduces it (small sample, polite GET-only fetches, no sharing, no publication, deletion on request, see below) but cannot remove it. The owner accepted this risk in D-51; it ends only when written permission is obtained or the copies are deleted.

## Residual legal risk (D-99)

Go-live now rests on the owner's own entitlement to read the books with their account, not on the source's consent to copy them into a library other invited readers use. The source may regard that as a terms breach or infringement. The owner accepted this risk in D-99. Mitigations: private invite-only library, signed-in readers only, no published text, GET-only, polite rate, honest User-Agent, prompt takedown. Account risk: the source may flag or ban the personal account.

## Questions to put to the source if the owner wants consent later (OPEN actions, not decisions)

1. Written permission for ingestion and for republishing inside this private library: scope, duration, conditions.
2. May an account on the source be used (the cookie)? Which account? Is GET-only access sufficient for the locked chapters, or is an export or API available?
3. Required attribution and link-back text per book (catalog keeps `source_attribution` and the source URL, never shown to readers without the field being intended).
4. Takedown contact, process and response time.
5. Is the public metadata and cover display acceptable to the source?

## Provenance and attribution

Every book stores its source URL, the fetch time, snapshot hash and ruleset version (ingestion), and attribution text (catalog). Reader-facing views carry attribution but not the source URL (INV-CAT-002).

## Takedown handling

On a rights claim or withdrawn permission:

1. **Unpublish the affected book** (catalog, `manage_catalog`): emits `book.unpublished`; reading copies stop being served and tickets stop verifying immediately (INV-RDR-007). Delete (tombstone) if the claim requires withdrawal; files, shelf entries and Kindle requests of a tombstoned book are removed (INV-CAT-003).
2. **Stop the source**: pause the source's automation and, if permission is withdrawn, clear the cookie file ([key-compromise](../11-operations/runbooks/key-compromise.md) step for the cookie).
3. **Remove cached copies**: scrape cache for the source's books (retention job or manual purge); previous-version files on the catalog volume; the owner's private gold-corpus pages for that source (D-51).
4. **Backups**: monthly backups still hold the content until they age out; record the claim and the date, and delete the affected backup sets when the claimant requires it. Stated plainly so it is not discovered later.
5. **Record** the claim, the actions and dates in the audit trail (unpublish and delete are audited, D-40).

A per-source "unpublish all" switch (reversible, no data deleted) is a catalog design item; if it is not in the catalog contract it is listed as a gap (not decided here).

## Honest limits (no DRM)

The reader serves the whole rendered book to a signed-in reader with a valid ticket (D-28), so a determined reader can copy the text. Controls reduce and trace exposure but are not DRM: entitlements and grants, short 15-minute tickets verified by identity, per-user open limits, audit of every open and download, `read_once` by explicit grant. A downloaded EPUB (`download` scope, explicit grant) is a plain file. Records and the UI must say this (INV-RDR-010). Third-party content rights are the owner's responsibility, not something the software enforces.
