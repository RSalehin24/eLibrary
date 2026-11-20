# Open points awaiting the owner (not decided)

Status: ACTIVE

Raised by writers; each is asked with `AskUserQuestion` when the wave that needs it runs. Recommendation in brackets.

| # | Point | Recommendation |
|---|---|---|

## Design questions to settle in the service designs (re-added; Wave B1 had dropped them)

| # | Question | Where it is resolved |
|---|---|---|

## Raised by contract writer B2 (not decided)

| # | Point | Recommendation |
|---|---|---|

## Raised by service writer C1 (not decided)

| # | Point | Recommendation |
|---|---|---|
| O-8 | Role-to-scope table: operator = reader + operate + manage_catalog; admin = reader + manage_users + manage_catalog (carried from v1, unconfirmed) | confirm; owner decision |

## Raised by service writer C2 (not decided)

| # | Point | Recommendation |
|---|---|---|
| P-2 | Annotations on a new version (Q-2): A server re-anchoring, B lazy client re-anchoring, C pin readers to the version they annotated | A (server re-anchoring); ADR-0015 then needs the update described in `reader/anchors.md` |

## Raised by service writer C3 (not decided)

| # | Point | Recommendation |
|---|---|---|
| I-1 | epubcheck needs a Java runtime: run it in the worker container, or only in CI | CI only (keep Java out of the runtime image); the in-process structure audit stays the runtime gate |
| I-2 | Generated cover method; crates for HTTP, HTML, sanitizer, ZIP, XML | decide in the dependency batch (P1) |

## Answered 2026-11-19 (moved to DECISIONS)

O-8 role scopes = D-45 · P-2/Q-2 annotations = D-46 · I-1 epubcheck = D-47 · O-6 reader preferences = D-48 · U-3 approval surface = D-49 (no manual approval; the whole publish process is automatic) · U-6 reader modes = D-52 (scroll and paged) · D-50 (old app shut down) and D-51 (gold labelling before permission, private research only) close the roadmap questions on the old host and on P0 labelling

Answered later the same day: C-5 notify direct routes = D-53 (events only) · U-12 identity batch grants = D-54 · export per service = D-55 · P-1 version states is moot: D-56 (versions are born `published`, no `draft` or `in_review`) · D-57 (publish gate fails closed when epubcheck cannot run)

Answered 2026-11-20: O-1 = D-76 · O-2 = D-77 · O-3 = D-78 · O-4 = D-79
Answered 2026-11-20 (cont.): O-5 = D-80 · O-7 = D-81 · O-9 = D-82 · O-10 = D-83
Answered 2026-11-20 (cont.): C-1 = D-84 · C-2 = D-85 · C-3 = D-86 · C-4 = D-87
Answered 2026-11-20 (cont.): C-6 = D-88 · P-3 = D-89 · P-4 = D-90 · P-5 = D-91
Answered 2026-11-20 (cont.): I-3 = D-92 · I-4 = D-93 · I-5 = D-94 · I-6 = D-95
Answered 2026-11-20 (cont.): I-7 = D-96 · Q-4 = D-97 · O-6, Q-1, Q-2, Q-3 pruned (D-48, S-01, D-46, formal-models)
