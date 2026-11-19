# Planned models (to be written in phase P2)

Status: DRAFT

Each is small (≤ 100 lines TLA+). Variables and properties are fixed here so the
requirement is unambiguous before the model is written.

## AccountLifecycle (identity)

Note: the first four planned models are unchanged in intent by the five-service redesign; `Publication` now concerns a catalog book version and its files, `Progress` the reader service.

- Variables: `status[acct]`, `linkState[link]` (Issued|Consumed|Superseded|Expired), `linkOf[acct]` (current link), `session[s]` (None|PasswordOk|Authenticated|Revoked), `totpRequired[acct]`, `totpOk[s]`.
- Actions: Invite, IssueLink (supersedes previous), ConsumeLink (→ Active, sets credential), Login, VerifyTotp, Logout, Suspend, Reactivate, Disable, ExpireLink.
- Properties: `ActiveRequiresCredential`; `LinkConsumedAtMostOnce`; `SupersededLinkDead` (a superseded/expired link never leads to Active); `AuthenticatedImpliesMfaWhenRequired`; `RevokedSessionAuthenticatesNothing`; `SuspendRevokesAllSessions`; `TotpStepSingleUse` (variable `lastAcceptedStep[acct]`; a verify action succeeds only for a step greater than it, and replaying a captured code at any later time fails); `StatusTransitionsOnlyAlongGraph`.

## BookLifecycle (catalog)

- Variables: `state[book]` ∈ {Draft, InReview, Published, Archived, Deleted}, `hasCredit[book]`.
- Actions: SubmitForReview, Approve (requires `hasCredit`, becomes Published), Archive, Restore, Delete (soft).
- Properties: `StateTransitionsOnlyAlongGraph`; `PublishedImpliesCredit`; `DeletedIsTerminal`.

## Publication (catalog)

- Variables: `sets` (complete/incomplete), `active[book]`, `building[book]`.
- Actions: BeginBuild, AddArtifact, Seal (marks complete), Swap (active := set only if sealed), Crash (drops incomplete).
- Properties: `ActivePointerReferencesCompleteSet`; `SealedSetsImmutable`; `ReaderSeesOneSet` (a read observes exactly one set id).

## Progress (reader)

- Variables: `rev[acct,book]`, `pos[acct,book]`, in-flight writes with client revisions (reordered, duplicated).
- Properties: `RevisionStrictlyIncreases`; `StaleWriteIsNoop`; `PositionEqualsPositionOfHighestRevision`.

## Exit criterion

All four written, analyzed with TLC, listed in [coverage](coverage.md) as `checked`
with the commit hash of the analysis.
