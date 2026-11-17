# Planned models (to be written in phase P2)

Status: DRAFT

Each is small (≤ 100 lines TLA+). Variables and properties are fixed here so the
requirement is unambiguous before the model is written.

## AccountLifecycle (identity)

- Variables: `status[acct]`, `linkState[link]` (Issued|Consumed|Superseded|Expired), `linkOf[acct]` (current link), `session[s]` (None|PasswordOk|Authenticated|Revoked), `totpRequired[acct]`, `totpOk[s]`.
- Actions: Invite, IssueLink (supersedes previous), ConsumeLink (→ Active, sets credential), Login, VerifyTotp, Logout, Suspend, Reactivate, Disable, ExpireLink.
- Properties: `ActiveRequiresCredential`; `LinkConsumedAtMostOnce`; `SupersededLinkDead` (a superseded/expired link never leads to Active); `AuthenticatedImpliesMfaWhenRequired`; `RevokedSessionAuthenticatesNothing`; `SuspendRevokesAllSessions`; `StatusTransitionsOnlyAlongGraph`.

## BookLifecycle (catalog)

- Variables: `state[book]` ∈ {Draft, Published, Archived, Deleted}, `hasCredit[book]`.
- Actions: Publish (requires `hasCredit`), Archive, Restore, Delete.
- Properties: `StateTransitionsOnlyAlongGraph`; `PublishedImpliesCredit`; `DeletedIsTerminal`.

## Publication (content)

- Variables: `sets` (complete/incomplete), `active[book]`, `building[book]`.
- Actions: BeginBuild, AddArtifact, Seal (marks complete), Swap (active := set only if sealed), Crash (drops incomplete).
- Properties: `ActivePointerReferencesCompleteSet`; `SealedSetsImmutable`; `ReaderSeesOneSet` (a read observes exactly one set id).

## Progress (library)

- Variables: `rev[acct,book]`, `pos[acct,book]`, in-flight writes with client revisions (reordered, duplicated).
- Properties: `RevisionStrictlyIncreases`; `StaleWriteIsNoop`; `PositionEqualsPositionOfHighestRevision`.

## Exit criterion

All four written, analyzed with TLC, listed in [coverage](coverage.md) as `checked`
with the commit hash of the analysis.
