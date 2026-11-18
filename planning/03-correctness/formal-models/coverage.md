# Model coverage

Status: DRAFT

Re-planned for the five-service design (ADR-0020..0024). **Edited but NOT re-checked** (no Java on the authoring machine, so no model checker was run on any of these): `alloy/access.als` (scopes, deny by default, ownership grants nothing, no wildcard role), `tla/ReadOnce.tla` (consume on ticket redemption), `tla/Outbox.tla` and `tla/Outbox.cfg` (pull cursor instead of push). `tla/JobLifecycle.tla` has only a comment change. `tools/model_mirror.py` still mirrors the old push, session and access models and must be updated before it counts as interim evidence for the edited models. Gate G2 requires TLC/Alloy runs.

Every invariant whose mechanism includes `model` must appear here with its model
(checked by `tools/check_plan.py`).

| Invariant | Model | Property / assertion | State |
|---|---|---|---|
| INV-ACC-001 | alloy/access.als | `AnonymousLimited` | edited, not re-checked |
| INV-ACC-002 | alloy/access.als | `ReadNeedsAccount`, `NoGrantNoAccess` (ownership/shelf/role grant nothing) | edited, not re-checked |
| INV-ACC-003 | alloy/access.als | `allow` is a total predicate, deny by default (every input has a result) | edited, not re-checked |
| INV-ACC-004 | alloy/access.als | `DeadGrantsIgnored` | edited, not re-checked |
| INV-ACC-005 | alloy/access.als | `Monotonic` | edited, not re-checked |
| INV-ACC-006 | tla/ReadOnce.tla | `AtMostOneUse`, `UseIffOneRedeemed` (consume on ticket redemption; copy unavailable never consumes) | edited, not re-checked |
| INV-ACC-007 | alloy/access.als | `ManagementNeedsAuthority`, `DemoReadOnly` | edited, not re-checked |
| INV-ACC-009 | alloy/access.als | `ManagementNeedsAuthority` (MfaOk clause) | edited, not re-checked |
| INV-ACC-012 | alloy/access.als | `UnpublishedHidden` | edited, not re-checked |
| INV-LIB-008 | retired | reading-session model replaced by tickets (ADR-0023); see INV-ACC-006 | retired |
| INV-ING-006 | tla/JobLifecycle.tla | `PublishedImpliesComplete`, `PublishedImpliesCurrentRunComplete` | unchecked by TLC; logic confirmed in Python mirror |
| INV-ING-010 | tla/JobLifecycle.tla | `AtMostOneActivePerUrl`, `AttemptsBounded`, `EventuallySettled` | unchecked |
| INV-ING-016 | tla/Outbox.tla + JobLifecycle.tla | `AppliedAtMostOnce`, `PublishAtMostOnce` | Outbox edited, not re-checked; JobLifecycle unchecked |
| INV-NTF-001 | tla/Outbox.tla | `AppliedAtMostOnce`, `NoLoss` (pull cursor) | edited, not re-checked |
| INV-PLT-009 | tla/Outbox.tla | `Safety`, `NoLoss` (pull cursor, crash and cursor-reset variant) | edited, not re-checked |
| INV-DSC-004 | alloy/access.als | public routes never reach unpublished books (premise); type-level proof in code | edited, not re-checked |
| INV-IDN-001 | planned: AccountLifecycle | `ActiveRequiresCredential` | planned |
| INV-IDN-002 | planned: AccountLifecycle | `LinkConsumedAtMostOnce`, `SupersededLinkDead` | planned |
| INV-IDN-004 | planned: AccountLifecycle | `AuthenticatedImpliesMfaWhenRequired` | planned |
| INV-IDN-009 | planned: AccountLifecycle | `TotpStepSingleUse` | planned |
| INV-IDN-005 | planned: AccountLifecycle | `RevokedSessionAuthenticatesNothing` | planned |
| INV-IDN-008 | planned: AccountLifecycle | `StatusTransitionsOnlyAlongGraph` | planned |
| INV-CAT-001 | planned: BookLifecycle (Draft, InReview, Published, Archived) | `StateTransitionsOnlyAlongGraph` | planned |
| INV-CON-001 | planned: Publication (catalog version row + files) | `ActivePointerReferencesCompleteSet` | planned |
| INV-LIB-001 | planned: Progress | `RevisionStrictlyIncreases` | planned |
