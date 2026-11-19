# Planned models (written in phase P2)

Status: DRAFT

Each is small (about 100 lines of TLA+, or one Alloy module). Variables, actions and properties are fixed here so the requirement is unambiguous before the model is written. The invariants each model covers are listed in [coverage](coverage.md). Rule 0 of the [README](README.md) applies: every model gets at least one deliberately broken variant that its properties detect. Nothing is checked yet (no Java on the authoring machine).

Models marked **extension** change an existing file; the rest are new files. Names follow the six-service design (D-31); the v1 names `BookLifecycle`, `Publication` and `Progress` are replaced by `VersionLifecycle`, `PublishSaga` and `ProgressRevision`.

## AccountLifecycle (identity)

- Variables: `status[user]` (invited, active, suspended, disabled), `linkState[link]` (Issued, Consumed, Superseded, Expired), `linkOf[user]`, `session[s]` (None, PasswordOk, Authenticated, Revoked, Expired), `totpRequired[user]`, `lastAcceptedStep[user]`, `grants`, `audit`.
- Actions: Invite, IssueLink (supersedes the previous), ConsumeLink (to active, sets the credential), SeedAdmin (host command, D-38), Login, VerifyTotp, Logout, Suspend, Reactivate, Disable, ExpireLink, ExpireSession, ChangePassword and DisableTotp (each takes a credential check as a precondition), Grant and RevokeGrant (actor differs from subject; audit row in the same step).
- Properties: `ActiveRequiresCredential`; `LinkConsumedAtMostOnce`; `SupersededLinkDead`; `ExpiredLinkDead`; `AuthenticatedImpliesMfaWhenRequired`; `RevokedSessionAuthenticatesNothing`; `ExpiredSessionAuthenticatesNothing`; `SuspendRevokesAllSessions`; `TotpStepSingleUse` (a verify succeeds only for a step greater than `lastAcceptedStep`); `SensitiveChangeNeedsFreshCredential`; `GrantChangeHasActorNotSubjectAndAudit`; `StatusTransitionsOnlyAlongGraph`.

## EntitlementDecision (identity; Alloy, extends `alloy/access.als`)

- Replaces the stale parts of `access.als` (see the gap table in [coverage](coverage.md)): roles map to scopes (D-45), `Demo` removed (D-35), `Preview` and `Read` separate (D-41), anonymous subjects get only `browse` on published metadata (D-34), `manage_catalog` sees unpublished versions, `ReadOnce` carries a consumed flag, and a `capabilities` function.
- Properties: everything already in the file (`AnonymousLimited`, `ReadNeedsAccount`, `NoGrantNoAccess`, `DeadGrantsIgnored`, `Monotonic` for every scope except `read_once`, `ManagementNeedsAuthority`, `UnpublishedHidden` for non-`manage_catalog` subjects) plus `DecisionIsFunction` and `CapabilitySetEqualsAllowSet`.

## TicketLifecycle (identity mints and verifies, reader redeems)

- Variables: `ticket[t]` (None, Issued, Redeemed, Expired, Revoked), `grantVersion`, `bookState`, `userState`, `copyReady`, `uses[user,book]`, `audit`, per-device tickets (extends `tla/ReadOnce.tla`).
- Actions: Open (needs a `read` Allow and the read-once rule), Redeem (identity `verify` at that moment), Reload (same ticket, same result), Expire, RevokeGrant, DisableUser, Unpublish, CopyChanges.
- Properties: `TicketIssuedOnlyAfterReadAllow`; `ShelfNeverAllows`; `RedeemRechecksIdentity` (a revoked, disabled or unpublished case is denied at once); `RedeemTwiceSameResult`; `OneOpenAuditRowPerRedemption`; plus the existing `AtMostOneUse` and `UseIffOneRedeemed`. P-3 (OPEN): whether a ticket bound to a superseded version is rejected by identity or answered `copy_unavailable` by the reader decides one guard here.

## VersionLifecycle (catalog)

- Variables: `state[version]` (published, archived; no draft, in_review or rejected, D-49, D-56), `deleted[book]`, `current[book]` (pointer), `files[version]` (complete or not), `archivedReason`, `publicIndex`.
- Actions: Intake (from ingestion with gate-passing artifacts: the version is created `published` in one step, D-56), Archive (superseded or unpublished), Delete (soft), Restore, Crash (drops an incomplete file set), BuildPublicDocument.
- Properties: `StateTransitionsOnlyAlongGraph`; `VersionBornPublished`; `VisibleOnlyThroughPublishOrRestore`; `FailedBuildCreatesNoVisibleVersion`; `ReaderViewOnlyPublishedNonDeleted`; `SealedVersionImmutable`; `CurrentPointerReferencesOneCompleteVersion`; `PreviousFilesKeptUntilNextPublished`; `PublicIndexHoldsOnlyPublicFields`. The rejected-state question (old P-1) is moot: there is no rejection or draft (D-49, D-56).

## PublishSaga (ingestion to catalog)

- Variables: `gates[b]` (pass or fail per gate), `build[b]` (Built, Sent, Acked), `catalogVersion[(book, buildId)]`, `network` (lost request, lost response, duplicate), crash points.
- Actions: Build, GateCheck, Send (idempotent on the build identity), Ack, Retry, CrashAfterSend, CrashBeforeCommit, CatalogCommit.
- Properties: `OneVersionPerBuildIdentity`; `PublishCountPerBuildIdentityIsOne`; `FailedBuildCreatesNoVersion`; `PublishOnlyAfterAllGatesPass`; `FailedGateNeverSent`; `MissingGateResultNeverSent` (epubcheck cannot run, D-57); `VersionVisibleOnlyAfterCatalogCommit`.

## ReaderCopyLifecycle (reader)

- Variables: `copy[(book, version)]` (None, Building, Ready, Failed), `eventLog`, `cursor`, workers.
- Actions: DeliverBookPublished (duplicate and reordered), StartBuild, FinishBuild, FailBuild, ReplaceByNewer, CatalogUnreachable.
- Properties: `CopyBuiltAtMostOncePerVersion`; `RedeliveredPublishedEventIdempotent`; `OnlyReadyCopyServed`; `ReplaceIsAtomic`.

## ProgressRevision (reader)

- Variables: `rev[user,book]`, `pos[user,book]`, in-flight writes with client revisions (reordered, duplicated).
- Properties: `RevisionStrictlyIncreases`; `StaleWriteIsNoop`; `PositionEqualsHighestRevision`.

## RequestLifecycle (ingestion)

- Variables: `status[req]` and `outcome[req]` (separate), `candidate[req]`, mirror `syncPhase` and checkpoint, workflow state (separate from mirror fields), automation `nextDue` slots and `claimedBy`.
- Actions: every action of the state-machine table with its allowed source states (including bulk with per-item result), Sync (two phases with a checkpoint), Resync, ClaimSlot, Finish with outcome (created, duplicate, needs_review, failed, cancelled).
- Properties: `CreatedImpliesCandidate`; `StatusAndOutcomeSeparate`; `TerminalPathRestoresOwner`; `ActionOnlyFromAllowedSource`; `SyncIdempotent`; `SyncPhasesOnlyAlongGraph`; `ResyncNeverTouchesWorkflowState`; `AtMostOneClaimPerSlot`; `DuplicateAndNeedsReviewNeverAutoRetried`. Open question I-6 (wording of `awaiting_credential`) is aligned in the state-machine file, not here.

## DeliveryLifecycle (catalog request, notify delivery)

- Variables: `kindleRequest[r]`, `delivery[d]` (Pending, Sent, Unknown, Failed, Permanent), `attempts[d]`, `identityAllow` at request and at send, `eventId`.
- Actions: RequestKindle (published version, size and rate limit, identity Allow), Attempt, Accept, Timeout (unknown outcome, recorded), Retry, GiveUp, StatusCallback (idempotent).
- Properties: `KindleEventNeedsPublishedKindleDecision`; `DeliveryStatusStoredPerRequest`; `KindleSendNeedsIdentityAllowAtSendTime`; `PermanentNeverAttemptedAgain`; `AttemptsBounded`; `AtMostOneAcceptedSend` except after a recorded unknown outcome.

## Extensions of existing models

- **Outbox (producer side)**: add the producer transaction (state change and `events` row in one step, crash before commit) and a strictly increasing cursor. Properties: `OneEventPerCommittedChange`, `CursorStrictlyIncreases`. Covers the producer-side invariants of identity, catalog, ingestion and the platform.
- **Outbox (console-stream variant)**: a client with `Last-Event-ID`, reconnect, a versioned snapshot after a gap. Property: `ReconnectGetsAllLaterEventsOrSnapshot` (INV-ING-032).
- **JobLifecycle**: rename per-URL exclusion to per request, add the cancel flag checked per page, page budget and error budget; keep `PublishAtMostOnce`.

## Exit criterion

All models written, analyzed with TLC or Alloy, every row of [coverage](coverage.md) `checked` with the commit hash of the analysis; every model has a mutation that its properties catch. Java for TLC and Alloy needs the owner's approval (dependency batch at P1; used earlier only in spike S-04).
