# Source content: rights, attribution, behavior

Status: DRAFT · Decision D-03 (blocking for ingestion go-live)

This is a business/legal question the plan cannot answer. It is recorded so the engineering follows whatever is decided.

## Facts from the legacy system

- It ingests books from a third-party site and republishes them (EPUB/HTML) to an authenticated audience.
- It stored a logged-in session cookie for the source and submitted LearnDash "mark complete" requests to unlock sequential chapters (state-changing actions on the source).

## Questions to resolve (owner)

1. Does the source owner permit ingestion and republication? In what form (written permission, license, public-domain works only)?
2. May we use an account on the source? May we perform any action other than GET? (Default in this plan: **no**.)
3. Required attribution and link-back text for each book?
4. Takedown process and SLA?
5. Is the preview (excerpt) public use acceptable? (D-05, D-09)

## Engineering stance until answered

- Acquisition is GET-only ([acquisition](../05-services/ingestion/acquisition/README.md)); locked chapters raise `LockedSource` reviews.
- Provenance is stored per book (source URL, snapshot hash, fetched-at, ruleset); attribution fields exist in the catalog (`source_attribution`).
- Per-source switch to unpublish all of a source's books without deleting data (reversible).
- Gold corpus and snapshots are access-controlled and never published or used for external services.
- Public preview text is `noindex` until D-09.
- No third-party AI service receives book text (also removes a class of disclosure risk).
