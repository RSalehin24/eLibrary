/* Authorization model (Alloy 6) for identity's decision function.
   Covers INV-IDN-013 to INV-IDN-018 and INV-IDN-025. Updated 2026-11-20 to the
   current design: no demo account (D-35), anonymous subjects get only `public`
   (preview needs a session, INV-IDN-014), plus the `session` scope.
   Design (ADR-0024): deny by default; explicit grants only; ownership and
   "My Books" grant nothing; there is no wildcard or admin-bypass role.
   The Rust decision in identity must implement exactly `allow`; the property
   tests in 05-services/identity/test-plan.md replay these cases.
   STATUS: analyzed with Alloy 6.2.0 on 2026-11-20: every `check` below has no
   counterexample within scope 6 (UNSAT) and the `run` is satisfiable. */
module access

abstract sig Scope {}
one sig Public, Browse, Preview, Read, ReadOnce, Download, Kindle,
        Operate, ManageCatalog, ManageUsers, Session extends Scope {}

abstract sig Subject {}
one sig Anonymous extends Subject {}
sig User extends Subject {}

/* Facts about users and books (inputs to the decision). */
sig Active, MfaOk in User {}   // MfaOk: TOTP-complete when the account requires TOTP
sig Book {}
sig Published in Book {}

/* Ownership and shelf membership exist as data but are NOT inputs to `allow`. */
sig Shelf { owner: one User, entries: set Book }

/* Grants. `covers` is the already-expanded set of books the grant applies to
   (global grants are expanded outside the model). Account-wide scopes ignore the book. */
sig Grant { holder: one User, scope: one Scope, covers: set Book }
sig Live in Grant {}   // not expired and not revoked at the evaluation time

pred publicScope[s: Scope]    { s in Public }   // catalog metadata of published books, no session
pred bookScope[s: Scope]      { s in Public + Browse + Preview + Read + ReadOnce + Download + Kindle }
pred managementScope[s: Scope] { s in Operate + ManageCatalog + ManageUsers }

pred granted[s: User, sc: Scope, b: Book, G: set Grant] {
    some g: G & Live | g.holder = s and g.scope = sc and b in g.covers
}

pred allow[s: Subject, sc: Scope, b: Book, G: set Grant] {
    // 1. public routes: catalog metadata of published books, for everyone
    (publicScope[sc] and b in Published)
    // 2. `session`: any signed-in (active) user, own data only, no grant needed
    or (sc = Session and s in Active)
    // 3. otherwise only an Active user with a live explicit grant for exactly this scope
    or (s in Active and granted[s, sc, b, G]
        and (bookScope[sc] implies b in Published)            // only published versions are visible
        and (managementScope[sc] implies s in MfaOk))         // management needs TOTP-complete session
}

/* INV-IDN-014: anonymous subjects only get the public scope on published books. */
assert AnonymousLimited {
    all sc: Scope, b: Book, G: set Grant |
        allow[Anonymous, sc, b, G] implies (publicScope[sc] and b in Published)
}

/* INV-IDN-014: reading and preview text are never allowed for anonymous subjects. */
assert ReadNeedsAccount {
    all b: Book, G: set Grant | not allow[Anonymous, Read + Preview, b, G]
}

/* `session` is only for signed-in active users. */
assert SessionNeedsActiveUser {
    all s: Subject, b: Book, G: set Grant |
        allow[s, Session, b, G] implies s in Active
}

/* INV-IDN-013/015: ownership, shelves and role names grant nothing; with no live grant
   the decision equals the public rule (deny by default, no wildcard). */
assert NoGrantNoAccess {
    all s: User, sc: Scope, b: Book, G: set Grant |
        not granted[s, sc, b, G] implies
            (allow[s, sc, b, G] iff ((publicScope[sc] and b in Published) or (sc = Session and s in Active)))
}

/* INV-IDN-017: dead (expired/revoked) grants have no effect. */
assert DeadGrantsIgnored {
    all s: Subject, sc: Scope, b: Book, G: set Grant |
        allow[s, sc, b, G] iff allow[s, sc, b, G & Live]
}

/* INV-IDN-018: monotonicity in the grant set. */
assert Monotonic {
    all s: Subject, sc: Scope, b: Book, G1, G2: set Grant |
        (G1 in G2 and allow[s, sc, b, G1]) implies allow[s, sc, b, G2]
}

/* INV-IDN-025: management needs an explicit live grant, an Active user and a
   TOTP-complete session. */
assert ManagementNeedsAuthority {
    all s: Subject, sc: Scope, b: Book, G: set Grant |
        (managementScope[sc] and allow[s, sc, b, G]) implies
            (s in Active & MfaOk and granted[s, sc, b, G])
}

/* INV-IDN-016: unpublished books are visible to no one through book scopes. */
assert UnpublishedHidden {
    all s: Subject, b: Book - Published, G: set Grant, sc: Scope |
        bookScope[sc] implies not allow[s, sc, b, G]
}

check AnonymousLimited         for 6
check ReadNeedsAccount         for 6
check NoGrantNoAccess          for 6
check DeadGrantsIgnored        for 6
check Monotonic                for 6
check ManagementNeedsAuthority for 6
check SessionNeedsActiveUser   for 6
check UnpublishedHidden        for 6
run { some Published and some Live and some Active & MfaOk } for 4
