# Delta: previous plan (`_v1/`) to the rewritten plan

Status: DRAFT

What was kept, changed and dropped, with the reason. Decisions are in [DECISIONS](../DECISIONS.md) (D-22..D-57); evidence in `analysis/`. `_v1/` is the plan as it stood when the rewrite began.

## Kept (supported by the analysis or still required)

| Item | Why |
|---|---|
| Rust backend, microservices, one database per service, forward-only migrations | D-11; ownership by credentials |
| Engineering philosophy, working agreement, coding standards, dependency approval rule | owner rules (D-14, D-17..D-21) |
| Requirement → invariant → mechanism discipline and `check_plan.py` | catches drift; extended with `metric`, `static` verify methods (I-23) |
| Angular + Angular Material M3, Bengali typography, generated TS client | D-02, D-16, D-25 |
| Idempotency, bounds, typed errors, audit, clock injection, startup validation | defects X1 showed the old app lacked |
| Ingestion sub-designs (acquisition, block IR, structure, classification, entities, builder, rulesets), revised | pipeline logic is the product's core; re-based on the traced legacy behaviour |
| Gold-corpus method (now 120 books), formal-model approach (TLA+/Alloy, unchecked: no Java) | measurement and concurrency evidence |
| Runbooks key-compromise, outbox-stuck, source-drift | still apply |

## Changed

| From (v1) | To | Reason |
|---|---|---|
| 7 services + gateway (identity, access, catalog, content, library, ingestion, notify) | **6 services**: gateway, identity (incl. access and grants), catalog (incl. files), reader (incl. reading state), ingestion, notify (D-31) | legacy seams: access ≈ identity; library state belongs with the reader; content custody splits between catalog (EPUB, cover) and reader (reading copy) |
| Reader as part of library/content | **Own service**: parses and sanitises the EPUB once, serves the whole book against a 15-minute ticket minted and verified by identity (D-28, D-37, D-46, D-48) | legacy reader sent the whole EPUB by URL token with no revocation |
| Systemd or Compose, symlink releases, host Nginx/Certbot | **Docker Compose, one container per component, 10 containers**, Caddy for HTTPS only, release by image digest (D-22, D-23, D-31) | owner requirement |
| Public search and preview | **Public metadata only**; preview and reading need sign-in (D-34) | invite-only product; avoids publishing scraped text |
| Nightly backups, WAL archiving | **Monthly full backup, restore drill, RPO 30 days** (D-33) | owner choice; data-loss risk recorded (R-17) |
| Static web app | **Angular SSR on Node** for public pages (D-39) | owner choice |
| Roles with `demo`, one `preview` right | roles reader/operator/admin, scopes `browse preview read read_once download kindle operate manage_catalog manage_users` (D-41, D-45) | X3 roles analysis |
| Catalog version review/approval | **Automatic publishing**, no approval; failed gates stay in the ingestion review queue; versions born `published`; gate fails closed (D-49, D-56, D-57) | owner choice; risk R-24 |
| Redis/Celery/custom engine, three orchestration layers | **One Postgres jobs queue** with leases, typed errors, one request model (ADR-0021) | legacy X1-106, 065-068 |
| Requirement prefixes ACC DSC CON LIB MIG | IDN GWY CAT RDR ING NTF WEB PLT NFR (215 requirements) | new service map; renamed-ids table in `coverage.md` |
| Reader preferences, audit, profile image, saved filters left open | decided: reader service, broad audit 1 year, profile image kept, saved filters kept, per-user export (D-40, D-43, D-44, D-48, D-55) | owner answers |
| Epub validator in CI | **epubcheck in the ingestion worker** (needs a Java runtime, to approve) (D-47) | owner choice |

## Dropped

| Item | Reason |
|---|---|
| Legacy data migration (ETL, cutover runbook, ADR-0013) | D-32 fresh start; D-50 old app shut down |
| Demo account | D-35 |
| Structured catalog codes | D-36 (unstable in legacy) |
| Manual EPUB upload, XLSX/PDF export | D-42; non-goals |
| Publish approval screens and routes | D-49 |
| Direct notify send routes | D-53 |
| Separate `access`, `content`, `library` services and the `processing` projection layer | merged or removed (see above) |
| Tantivy / separate search engine | D-29: PostgreSQL full-text search |
| Legacy defects (self-granted ownership, URL tokens, `AllowAny` defaults, mark-complete submissions, vowel-stripped Bengali lists, unescaped HTML, exec-assembled modules) | design rules in `new-architecture.md` section 7 |

## Not done in this rewrite

No facts were re-verified against external sources; formal models are unchecked; all numeric targets are provisional until the P0 baseline; no code exists; D-03 source permission and tool installs (Docker, Rust, Node, Java) remain owner actions. Open points: [open-points](open-points.md).
