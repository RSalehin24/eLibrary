/* Access policy model (Alloy 6).
   Covers INV-ACC-001, 002, 003, 004, 005, 007, 009, 012 and INV-DSC-004's
   data-flow premise (public actions never touch unpublished books).
   The Rust function `access::decide` must implement exactly `allow`, and the
   property tests in 05-services/access/test-plan.md replay these cases.
   STATUS: written, NOT YET ANALYZED (no Java on the authoring machine).
   Must pass `check` commands below at gate G2. */
module access

abstract sig Action {}
one sig Search, ViewMetadata, ViewPreview, Read, Download, SendToKindle,
        EditMetadata, ManageAccess extends Action {}

abstract sig Subject {}
one sig Anonymous extends Subject {}
sig Account extends Subject {}

/* Facts about accounts and books (inputs to the decision). */
sig Active, MfaOk, Admin in Account {}
sig Book {}
sig Published in Book {}

/* Grants. `on` is the already-expanded set of books the grant covers
   (global/category/author/book targets are expanded outside the model). */
sig Grant { holder: one Account, act: one Action, on: set Book }
sig Live in Grant {}   // not expired and not revoked at the evaluation time

pred publicAction[a: Action] { a in Search + ViewMetadata + ViewPreview }

pred privileged[s: Subject] { s in Active & Admin & MfaOk }

pred allow[s: Subject, a: Action, b: Book, G: set Grant] {
    // 1. public actions on published books, for everyone
    (publicAction[a] and b in Published)
    // 2. a live grant for exactly this action; unpublished books are reachable only for management actions
    or (s in Active and some g: G & Live |
          g.holder = s and g.act = a and b in g.on and (b in Published or a in EditMetadata + ManageAccess))
    // 3. metadata editors may view metadata/preview of unpublished books they are granted
    or (s in Active and a in ViewMetadata + ViewPreview and some g: G & Live |
          g.holder = s and g.act = EditMetadata and b in g.on)
    // 4. fully privileged administrators
    or privileged[s]
}

/* INV-ACC-001: anonymous subjects only get public actions on published books. */
assert AnonymousLimited {
    all a: Action, b: Book, G: set Grant |
        allow[Anonymous, a, b, G] implies (publicAction[a] and b in Published)
}

/* INV-ACC-002: reading is never allowed for anonymous subjects. */
assert ReadNeedsAccount {
    all b: Book, G: set Grant | not allow[Anonymous, Read, b, G]
}

/* INV-ACC-004: dead (expired/revoked) grants have no effect. */
assert DeadGrantsIgnored {
    all s: Subject, a: Action, b: Book, G: set Grant |
        allow[s, a, b, G] iff allow[s, a, b, G & Live]
}

/* INV-ACC-005: monotonicity. */
assert Monotonic {
    all s: Subject, a: Action, b: Book, G1, G2: set Grant |
        (G1 in G2 and allow[s, a, b, G1]) implies allow[s, a, b, G2]
}

/* INV-ACC-007 / 009: management and mutation need privileged status or a live grant. */
assert ManagementNeedsAuthority {
    all s: Account, b: Book, G: set Grant |
        allow[s, ManageAccess, b, G] implies
            (privileged[s] or (s in Active and some g: G & Live | g.holder = s and g.act = ManageAccess and b in g.on))
}

/* INV-ACC-012: unpublished books are invisible except to metadata editors and administrators. */
assert UnpublishedHidden {
    all s: Subject, b: Book - Published, G: set Grant, a: ViewMetadata + ViewPreview + Read |
        allow[s, a, b, G] implies
            (privileged[s] or (s in Active and some g: G & Live |
                g.holder = s and g.on & b != none and (g.act = EditMetadata or g.act = a)))
}

check AnonymousLimited      for 6
check ReadNeedsAccount      for 6
check DeadGrantsIgnored     for 6
check Monotonic             for 6
check ManagementNeedsAuthority for 6
check UnpublishedHidden     for 6
run { some Published and some Live and some Admin } for 4
