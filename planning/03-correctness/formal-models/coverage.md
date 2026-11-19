# Model coverage

Status: DRAFT

Re-baselined 2026-11-19 for the six-service design (ADR-0025, ADR-0026) and the invariant ids of the rebuilt [register](../invariants-register.md). **Nothing here has been model-checked**: Java and TLC/Alloy are not installed on the authoring machine, and no Python mirror exists for the new ids (`tools/model_mirror.py` mirrors the old v1 models and does not count as evidence). The four existing files carry only the older edits (tickets, pull outbox, scopes); their comments now name the new `INV-*` ids and their logic is unchanged. Gate G2 requires TLC and Alloy runs and every row below `checked` with a commit hash.

Every invariant whose mechanism includes `model` must appear here with its model (checked by `tools/check_plan.py`). The 46 invariants below are exactly those whose `by:` list contains `model`; a mechanism is never weakened to shorten this list.

States: `planned` (model not yet written; property fixed in [planned models](planned-models.md)), `edited, not re-checked` (file exists, edited, never run), `unchecked` (file exists, never run, and part of the property is missing or stale; the gap is named in the property column).

| Invariant | Model | Property / assertion | State |
|---|---|---|---|
| INV-IDN-001 | planned: AccountLifecycle | `ActiveRequiresCredential` (Active only after `ConsumeLink` or `SeedAdmin`) | planned |
| INV-IDN-002 | planned: AccountLifecycle | `LinkConsumedAtMostOnce`, `SupersededLinkDead`, `ExpiredLinkDead` | planned |
| INV-IDN-004 | planned: AccountLifecycle | `AuthenticatedImpliesMfaWhenRequired` | planned |
| INV-IDN-005 | planned: AccountLifecycle | `TotpStepSingleUse` (`lastAcceptedStep` only increases; replay fails) | planned |
| INV-IDN-006 | planned: AccountLifecycle | `SensitiveChangeNeedsFreshCredential` (TOTP disable and password change need a credential check in the same step) | planned |
| INV-IDN-007 | planned: AccountLifecycle | `RevokedSessionAuthenticatesNothing`, `ExpiredSessionAuthenticatesNothing`, `SuspendRevokesAllSessions` | planned |
| INV-IDN-009 | planned: AccountLifecycle | `StatusTransitionsOnlyAlongGraph` | planned |
| INV-IDN-012 | planned: AccountLifecycle | `GrantChangeHasActorNotSubjectAndAudit` (grant and role actions) | planned |
| INV-IDN-013 | alloy/access.als | `allow` is a total predicate; `NoGrantNoAccess` (no explicit scope or live grant gives Deny) | edited, not re-checked |
| INV-IDN-014 | alloy/access.als | `AnonymousLimited`, `ReadNeedsAccount`; logic stale: `publicScope` still contains `Preview` (D-34, D-41 say preview needs a session); fix in P2 as EntitlementDecision | unchecked |
| INV-IDN-015 | alloy/access.als | `NoGrantNoAccess` (`allow` has no shelf, ownership or submission input; `Shelf` is unused data) | edited, not re-checked |
| INV-IDN-016 | alloy/access.als | `UnpublishedHidden` (stricter than the invariant: no `manage_catalog` exemption yet; refine in P2) | edited, not re-checked |
| INV-IDN-017 | alloy/access.als | `DeadGrantsIgnored` | edited, not re-checked |
| INV-IDN-018 | alloy/access.als | `Monotonic` (`ReadOnce` is an ordinary scope in the model; the exclusion is added in P2) | unchecked |
| INV-IDN-019 | planned: EntitlementDecision | `DecisionIsFunction` (same inputs give the same result; `now` abstracted as `Live`) | planned |
| INV-IDN-020 | tla/ReadOnce.tla | `AtMostOneUse`, `UseIffOneRedeemed` (consume on redemption, not at open) | edited, not re-checked |
| INV-IDN-022 | planned: TicketLifecycle | `RedeemTwiceSameResult`, `OneOpenAuditRowPerRedemption` | planned |
| INV-IDN-023 | tla/Outbox.tla (producer extension planned) | `CursorStrictlyIncreases`, `OneEventPerCommittedChange` for `user.disabled` and `grant.changed` | planned |
| INV-IDN-025 | alloy/access.als | `ManagementNeedsAuthority` (`MfaOk` clause); logic stale: the `Demo` signature must be removed (D-35) | unchecked |
| INV-IDN-030 | planned: EntitlementDecision | `CapabilitySetEqualsAllowSet` | planned |
| INV-CAT-001 | planned: VersionLifecycle | `StateTransitionsOnlyAlongGraph` (published, archived with reason; no draft, in_review or rejected, D-49, D-56), `VersionBornPublished`, `VisibleOnlyThroughPublishOrRestore`, `FailedBuildCreatesNoVisibleVersion` | planned |
| INV-CAT-002 | planned: VersionLifecycle | `ReaderViewOnlyPublishedNonDeleted` | planned |
| INV-CAT-012 | planned: VersionLifecycle | `PublicIndexHoldsOnlyPublicFields` (projection premise; the type-level part stays in code) | planned |
| INV-CAT-021 | planned: VersionLifecycle | `SealedVersionImmutable`, `CurrentPointerReferencesOneCompleteVersion`, `PreviousFilesKeptUntilNextPublished` | planned |
| INV-CAT-022 | planned: PublishSaga | `OneVersionPerBuildIdentity` (replay, lost response, crash between call and commit) | planned |
| INV-CAT-024 | tla/Outbox.tla (producer extension planned) | `OneEventPerStateChange`, `AppliedAtMostOnce` (consumer idempotent) | planned |
| INV-CAT-029 | planned: DeliveryLifecycle | `KindleEventNeedsPublishedKindleDecision`, `DeliveryStatusStoredPerRequest` | planned |
| INV-RDR-001 | planned: ReaderCopyLifecycle | `CopyBuiltAtMostOncePerVersion`, `RedeliveredPublishedEventIdempotent` | planned |
| INV-RDR-005 | planned: TicketLifecycle | `TicketIssuedOnlyAfterReadAllow`, `ShelfNeverAllows` | planned |
| INV-RDR-007 | planned: TicketLifecycle | `RedeemRechecksIdentity` (a revoked, disabled or unpublished case is denied at once, with the event consumer stopped) | planned |
| INV-RDR-009 | tla/ReadOnce.tla | `AtMostOneUse`, `UseIffOneRedeemed` (concurrent redemptions consume once; `copyReady = FALSE` consumes nothing) | edited, not re-checked |
| INV-RDR-012 | planned: ProgressRevision | `RevisionStrictlyIncreases`, `StaleWriteIsNoop`, `PositionEqualsHighestRevision` | planned |
| INV-RDR-024 | tla/Outbox.tla | `SeenIffApplied`, `AppliedAtMostOnce` (cursor and effect in one transaction; redelivery changes nothing) | edited, not re-checked |
| INV-ING-001 | planned: RequestLifecycle | `CreatedImpliesCandidate`, `StatusAndOutcomeSeparate`, `TerminalPathRestoresOwner` | planned |
| INV-ING-003 | planned: RequestLifecycle (mirror-sync part) | `SyncIdempotent`, `SyncPhasesOnlyAlongGraph`, `ResyncNeverTouchesWorkflowState` | planned |
| INV-ING-004 | tla/JobLifecycle.tla | `AtMostOneActivePerUrl` (to rename per request), `AttemptsBounded`, `EpochMatchesAttempts`; lease expiry Running to Queued only | unchecked |
| INV-ING-007 | tla/JobLifecycle.tla | `AttemptsBounded`, `EventuallySettled`; the cancel flag per page and the page and error budgets are not yet in the model (extension in P2) | unchecked |
| INV-ING-008 | planned: RequestLifecycle | `ActionOnlyFromAllowedSource` | planned |
| INV-ING-018 | tla/JobLifecycle.tla | `PublishedImpliesComplete`, `PublishedImpliesCurrentRunComplete` (every TOC leaf fetched or recorded empty) | unchecked |
| INV-ING-029 | planned: PublishSaga | `PublishCountPerBuildIdentityIsOne`, `FailedBuildCreatesNoVersion`; also `PublishAtMostOnce` in tla/JobLifecycle.tla | planned |
| INV-ING-036 | planned: PublishSaga | `PublishOnlyAfterAllGatesPass`, `FailedGateNeverSent`, `MissingGateResultNeverSent` (epubcheck unavailable, D-57) | planned |
| INV-ING-032 | tla/Outbox.tla (console-stream variant planned) | `ReconnectGetsAllLaterEventsOrSnapshot`, `CursorStrictlyIncreases` | planned |
| INV-ING-033 | planned: RequestLifecycle (automation-run part) | `AtMostOneClaimPerSlot`, `DuplicateAndNeedsReviewNeverAutoRetried` | planned |
| INV-NTF-001 | tla/Outbox.tla + planned: DeliveryLifecycle | `AppliedAtMostOnce`, `NoLoss` (pull cursor); `AtMostOneAcceptedSend` except after a recorded unknown outcome | edited, not re-checked |
| INV-NTF-005 | planned: DeliveryLifecycle | `KindleSendNeedsIdentityAllowAtSendTime` | planned |
| INV-NTF-008 | planned: DeliveryLifecycle | `PermanentNeverAttemptedAgain`, `AttemptsBounded` | planned |
| INV-PLT-010 | tla/Outbox.tla (producer extension planned) | `OneEventPerCommittedChange`, `CursorStrictlyIncreases`; consumer side `Safety`, `NoLoss` (pull cursor, crash and cursor-reset variant) | planned |

## Known gaps in the existing files (logic left as is; to fix in P2, not in this rewrite)

| File | Gap |
|---|---|
| alloy/access.als | `publicScope` includes `Preview` (D-34 and D-41: preview needs a session); `Demo` signature and `DemoReadOnly` remain (D-35 dropped the demo account); no `manage_catalog` exemption for unpublished books; role-to-scope table (D-45) is not modelled; `ReadOnce` is an ordinary scope |
| tla/JobLifecycle.tla | exclusion is per URL, the register says per request; no cancel flag, page budget or error budget; `Review` state predates the single-request pipeline |
| tla/Outbox.tla | consumer side only; no producer atomicity (`OneEventPerCommittedChange`), no console reconnect variant |
| tla/ReadOnce.tla | no identity re-check at redemption and no ticket expiry (planned in TicketLifecycle) |

## Retired rows

The v1 ids `INV-ACC-*`, `INV-LIB-*`, `INV-CON-*` and `INV-DSC-*` no longer exist; their content moved into the IDN, RDR, CAT and ING rows above.

## Renamed ids (v1 to the six-service ids)

The v1 requirement files `acc-access`, `con-content`, `dsc-discovery`, `lib-library`, `ntf-gwy-web` and `plt-mig` were split by service in the 2026-11-19 re-plan (D-31, D-32). Old ids still appear in `DECISIONS.md` and in older notes; read them with this table. A one-to-one id list is in git history (`git show HEAD:planning/02-requirements/<old file>`); this table maps by topic.

| Old ids | Now | Where |
|---|---|---|
| REQ-ACC-* / INV-ACC-* (roles, scopes, grants, decision, tickets, audit) | REQ-IDN-010..023, REQ-IDN-029 / INV-IDN-010..023, INV-IDN-029 | [identity](../../02-requirements/idn-identity.md) |
| REQ-ACC-001 (public set), REQ-ACC-002 (default reader policy; cited by D-04, D-12) | REQ-IDN-014, REQ-IDN-015 (with REQ-IDN-010, REQ-IDN-011 for roles and scopes) | identity |
| INV-ACC-008 (revocation lag bounded by token TTL) | removed: immediate revocation by identity `verify`; INV-RDR-007, INV-IDN-021 | [reader](../../02-requirements/rdr-reader.md), identity |
| REQ-CON-* (reading copy, tickets, serving) | REQ-RDR-001..010 / INV-RDR-001..011 | reader |
| REQ-CON-* (files, assets, EPUB custody, public preview) | REQ-CAT-0xx (files, preview, delivery) | [catalog](../../02-requirements/cat-catalog.md) |
| REQ-LIB-* (progress, bookmarks, annotations, preferences, export) | REQ-RDR-011..026 / INV-RDR-012..026 | reader |
| REQ-LIB-* (shelves, saved filters) | REQ-CAT shelves and REQ-CAT-033 | catalog |
| REQ-DSC-* / INV-DSC-* (search, browse, filters, CSV export) | REQ-CAT-0xx (search, list, export) | catalog |
| REQ-NTF-* in `ntf-gwy-web` | REQ-NTF-* | [notify](../../02-requirements/ntf-notify.md) |
| REQ-GWY-* in `ntf-gwy-web` | REQ-GWY-* | [gateway](../../02-requirements/gwy-gateway.md) |
| REQ-WEB-* in `ntf-gwy-web` | REQ-WEB-* | [web](../../02-requirements/web-ui.md) |
| REQ-MIG-*, REQ-PLT-MIG-* (legacy migration, ETL, cutover) | dropped by D-32 (nothing is migrated); launch runbook instead | [runbooks](../../11-operations/runbooks/) |
| REQ-PLT-* in `plt-mig` | REQ-PLT-001..023 | [platform](../../02-requirements/plt-platform.md) |
