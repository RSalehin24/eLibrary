# Model coverage

Status: DRAFT

Every invariant whose mechanism includes `model` must appear here with its model
(checked by `tools/check_plan.py`).

| Invariant | Model | Property / assertion | State |
|---|---|---|---|
| INV-ACC-001 | alloy/access.als | `AnonymousLimited` | unchecked |
| INV-ACC-002 | alloy/access.als | `ReadNeedsAccount` | unchecked |
| INV-ACC-003 | alloy/access.als | `allow` is a total predicate (every input has a result) | unchecked |
| INV-ACC-004 | alloy/access.als | `DeadGrantsIgnored` | unchecked |
| INV-ACC-005 | alloy/access.als | `Monotonic` | unchecked |
| INV-ACC-006 | tla/ReadOnce.tla | `AtMostOneOpening`, `PreparingNeverConsumed` | unchecked |
| INV-ACC-007 | alloy/access.als | `ManagementNeedsAuthority` | unchecked |
| INV-ACC-009 | alloy/access.als | `ManagementNeedsAuthority` (MfaOk clause) | unchecked |
| INV-ACC-012 | alloy/access.als | `UnpublishedHidden` | unchecked |
| INV-LIB-008 | tla/ReadOnce.tla | `AtMostOneLiveSession` | unchecked |
| INV-ING-006 | tla/JobLifecycle.tla | `PublishedImpliesComplete`, `PublishedImpliesCurrentRunComplete` | unchecked by TLC; logic confirmed in Python mirror |
| INV-ING-010 | tla/JobLifecycle.tla | `AtMostOneActivePerUrl`, `AttemptsBounded`, `EventuallySettled` | unchecked |
| INV-ING-016 | tla/Outbox.tla + JobLifecycle.tla | `AppliedAtMostOnce`, `PublishAtMostOnce` | unchecked |
| INV-NTF-001 | tla/Outbox.tla | `AppliedAtMostOnce`, `NoLoss` | unchecked |
| INV-PLT-009 | tla/Outbox.tla | `Safety`, `NoLoss` | unchecked |
| INV-DSC-004 | alloy/access.als | public actions never reach unpublished books (premise); type-level proof in code | unchecked |
| INV-IDN-001 | planned: AccountLifecycle | `ActiveRequiresCredential` | planned |
| INV-IDN-002 | planned: AccountLifecycle | `LinkConsumedAtMostOnce`, `SupersededLinkDead` | planned |
| INV-IDN-004 | planned: AccountLifecycle | `AuthenticatedImpliesMfaWhenRequired` | planned |
| INV-IDN-009 | planned: AccountLifecycle | `TotpStepSingleUse` | planned |
| INV-IDN-005 | planned: AccountLifecycle | `RevokedSessionAuthenticatesNothing` | planned |
| INV-IDN-008 | planned: AccountLifecycle | `StatusTransitionsOnlyAlongGraph` | planned |
| INV-CAT-001 | planned: BookLifecycle | `StateTransitionsOnlyAlongGraph` | planned |
| INV-CON-001 | planned: Publication | `ActivePointerReferencesCompleteSet` | planned |
| INV-LIB-001 | planned: Progress | `RevisionStrictlyIncreases` | planned |
