use contracts_http::Scope;
use contracts_ids::{BookId, TicketId};
use domain_access::{
    AccountStatus, BookFacts, Decision, DecisionInput, DenyReason, Grant, ReadOnceStatus, Role,
    Subject, UserFacts, decide, role_scopes,
};
use platform_time::Instant;
use proptest::prelude::*;
use uuid::Uuid;

const MANAGEMENT: [Scope; 3] = [Scope::Operate, Scope::ManageCatalog, Scope::ManageUsers];

fn book(n: u128) -> BookId {
    BookId::from_uuid(Uuid::from_u128(n))
}
fn ticket(n: u128) -> TicketId {
    TicketId::from_uuid(Uuid::from_u128(n))
}
#[allow(clippy::expect_used)] // why: test helper; every input used here is a valid timestamp.
fn at(seconds: i64) -> Instant {
    Instant::from_unix_seconds(seconds).expect("valid test timestamp")
}

fn scope() -> impl Strategy<Value = Scope> {
    proptest::sample::select(Scope::ALL.to_vec())
}
fn status() -> impl Strategy<Value = AccountStatus> {
    proptest::sample::select(vec![
        AccountStatus::Invited,
        AccountStatus::Active,
        AccountStatus::Suspended,
        AccountStatus::Disabled,
    ])
}
fn role() -> impl Strategy<Value = Role> {
    proptest::sample::select(vec![Role::Reader, Role::Operator, Role::Admin])
}
fn user() -> impl Strategy<Value = UserFacts> {
    (status(), role(), any::<bool>()).prop_map(|(status, role, mfa_satisfied)| UserFacts {
        status,
        role,
        mfa_satisfied,
    })
}
fn subject() -> impl Strategy<Value = Subject> {
    prop_oneof![Just(Subject::Anonymous), user().prop_map(Subject::User)]
}
fn grant() -> impl Strategy<Value = Grant> {
    (
        scope(),
        proptest::option::of(1u128..3),
        proptest::option::of(0i64..200),
        any::<bool>(),
    )
        .prop_map(|(scope, book_n, expiry, revoked)| Grant {
            scope,
            book: book_n.map(book),
            expires_at: expiry.map(at),
            revoked,
        })
}
fn facts() -> impl Strategy<Value = Option<BookFacts>> {
    proptest::option::of((1u128..3, any::<bool>(), any::<bool>()).prop_map(
        |(n, published, deleted)| BookFacts {
            id: book(n),
            published,
            deleted,
        },
    ))
}
fn read_once() -> impl Strategy<Value = (ReadOnceStatus, Option<TicketId>)> {
    (
        prop_oneof![
            Just(ReadOnceStatus::Unused),
            (1u128..3).prop_map(|n| ReadOnceStatus::ConsumedBy(ticket(n)))
        ],
        proptest::option::of((1u128..3).prop_map(ticket)),
    )
}

#[derive(Debug, Clone)]
struct Case {
    subject: Subject,
    scope: Scope,
    book: Option<BookFacts>,
    grants: Vec<Grant>,
    now: i64,
    read_once: ReadOnceStatus,
    ticket: Option<TicketId>,
}

fn case() -> impl Strategy<Value = Case> {
    (
        subject(),
        scope(),
        facts(),
        proptest::collection::vec(grant(), 0..4),
        0i64..200,
        read_once(),
    )
        .prop_map(
            |(subject, scope, book, grants, now, (read_once, ticket))| Case {
                subject,
                scope,
                book,
                grants,
                now,
                read_once,
                ticket,
            },
        )
}

fn run(case: &Case) -> Decision {
    decide(&DecisionInput {
        subject: case.subject,
        scope: case.scope,
        book: case.book,
        grants: &case.grants,
        now: at(case.now),
        read_once: case.read_once,
        ticket: case.ticket,
    })
}

/// A signed-in user who may see every book: a role or a live grant provides `manage_catalog`.
fn has_catalog_authority(case: &Case) -> bool {
    let Some(user) = user_of(case) else {
        return false;
    };
    let live_grant = case.grants.iter().any(|g| {
        g.scope == Scope::ManageCatalog
            && !g.revoked
            && g.expires_at.is_none_or(|e| at(case.now) < e)
            && (g.book.is_none() || g.book == case.book.map(|b| b.id))
    });
    role_scopes(user.role).contains(&Scope::ManageCatalog) || live_grant
}

fn user_of(case: &Case) -> Option<UserFacts> {
    match case.subject {
        Subject::User(user) => Some(user),
        Subject::Anonymous => None,
    }
}

proptest! {
    #[test]
    fn anonymous_only_ever_gets_the_public_scope(case in case()) {
        let anonymous = case.subject == Subject::Anonymous;
        prop_assert!(!anonymous || !run(&case).is_allowed() || case.scope == Scope::Public);
    }

    #[test]
    fn inactive_accounts_are_denied_everything(case in case()) {
        let inactive = user_of(&case).is_some_and(|user| user.status != AccountStatus::Active);
        prop_assert!(!inactive || run(&case) == Decision::Deny(DenyReason::AccountInactive));
    }

    #[test]
    fn management_allow_needs_a_completed_second_factor(case in case()) {
        let management = MANAGEMENT.contains(&case.scope);
        let allowed = run(&case).is_allowed();
        prop_assert!(!(management && allowed) || user_of(&case).is_some_and(|user| user.mfa_satisfied));
    }

    #[test]
    fn nothing_matching_means_deny(case in case()) {
        let reader = Subject::User(UserFacts { status: AccountStatus::Active, role: Role::Reader, mfa_satisfied: true });
        let needs_grant = [Scope::Download, Scope::ReadOnce, Scope::Operate, Scope::ManageCatalog, Scope::ManageUsers];
        let bare = Case { subject: reader, grants: vec![], ..case };
        prop_assert!(!needs_grant.contains(&bare.scope) || !run(&bare).is_allowed());
    }

    #[test]
    fn invisible_books_need_catalog_authority(case in case()) {
        let book_scopes = [Scope::Public, Scope::Browse, Scope::Preview, Scope::Read, Scope::ReadOnce, Scope::Download, Scope::Kindle];
        let hidden = case.book.is_some_and(|facts| facts.deleted || !facts.published);
        let allowed_on_hidden = hidden && book_scopes.contains(&case.scope) && run(&case).is_allowed();
        prop_assert!(!allowed_on_hidden || has_catalog_authority(&case));
    }

    #[test]
    fn dead_grants_change_nothing(case in case()) {
        let live: Vec<Grant> = case.grants.iter().copied()
            .filter(|g| !g.revoked && g.expires_at.is_none_or(|e| at(case.now) < e)).collect();
        let only_live = Case { grants: live, ..case.clone() };
        prop_assert_eq!(run(&case).is_allowed(), run(&only_live).is_allowed());
    }

    #[test]
    fn adding_a_grant_never_turns_allow_into_deny(case in case(), extra in grant()) {
        let mut grants = case.grants.clone();
        grants.push(extra);
        let widened = Case { grants, ..case.clone() };
        prop_assert!(!run(&case).is_allowed() || run(&widened).is_allowed());
    }

    #[test]
    fn order_of_grants_does_not_matter(case in case()) {
        let mut reversed = case.grants.clone();
        reversed.reverse();
        let flipped = Case { grants: reversed, ..case.clone() };
        prop_assert_eq!(run(&case), run(&flipped));
    }
}

fn reader() -> Subject {
    Subject::User(UserFacts {
        status: AccountStatus::Active,
        role: Role::Reader,
        mfa_satisfied: true,
    })
}

fn input_for(scope: Scope) -> Case {
    let visible = BookFacts {
        id: book(1),
        published: true,
        deleted: false,
    };
    Case {
        subject: reader(),
        scope,
        book: Some(visible),
        grants: vec![],
        now: 100,
        read_once: ReadOnceStatus::Unused,
        ticket: None,
    }
}

#[test]
fn the_reader_defaults_work_and_grant_only_scopes_need_a_grant() {
    for allowed in [
        Scope::Browse,
        Scope::Preview,
        Scope::Read,
        Scope::Kindle,
        Scope::Public,
        Scope::Session,
    ] {
        assert_eq!(run(&input_for(allowed)), Decision::Allow, "{allowed:?}");
    }
    for denied in [
        Scope::Download,
        Scope::ReadOnce,
        Scope::Operate,
        Scope::ManageUsers,
    ] {
        assert_eq!(
            run(&input_for(denied)),
            Decision::Deny(DenyReason::NoScope),
            "{denied:?}"
        );
    }
}

#[test]
fn expired_grant_gives_grant_expired_and_revoked_gives_no_scope() {
    let expired = Grant {
        scope: Scope::Download,
        book: None,
        expires_at: Some(at(50)),
        revoked: false,
    };
    let mut case = input_for(Scope::Download);
    case.grants = vec![expired];
    assert_eq!(run(&case), Decision::Deny(DenyReason::GrantExpired));
    case.grants = vec![Grant {
        revoked: true,
        ..expired
    }];
    assert_eq!(run(&case), Decision::Deny(DenyReason::NoScope));
    case.grants = vec![Grant {
        expires_at: Some(at(150)),
        ..expired
    }];
    assert_eq!(run(&case), Decision::Allow);
}

#[test]
fn a_book_grant_does_not_cover_another_book() {
    let other_book = Grant {
        scope: Scope::Download,
        book: Some(book(2)),
        expires_at: None,
        revoked: false,
    };
    let mut case = input_for(Scope::Download);
    case.grants = vec![other_book];
    assert_eq!(run(&case), Decision::Deny(DenyReason::NoScope));
    case.grants = vec![Grant {
        book: Some(book(1)),
        ..other_book
    }];
    assert_eq!(run(&case), Decision::Allow);
}

#[test]
fn unpublished_deleted_and_unknown_books_are_hidden_from_readers_but_not_from_catalog_managers() {
    let mut case = input_for(Scope::Read);
    case.book = Some(BookFacts {
        id: book(1),
        published: false,
        deleted: false,
    });
    assert_eq!(run(&case), Decision::Deny(DenyReason::BookNotPublished));
    case.book = Some(BookFacts {
        id: book(1),
        published: true,
        deleted: true,
    });
    assert_eq!(run(&case), Decision::Deny(DenyReason::BookDeleted));
    case.book = None;
    assert_eq!(run(&case), Decision::Deny(DenyReason::BookNotPublished));
    case.subject = Subject::User(UserFacts {
        status: AccountStatus::Active,
        role: Role::Operator,
        mfa_satisfied: true,
    });
    case.book = Some(BookFacts {
        id: book(1),
        published: false,
        deleted: false,
    });
    assert_eq!(run(&case), Decision::Allow);
}

#[test]
fn read_once_is_spent_for_other_tickets_but_not_the_same_one() {
    let grant = Grant {
        scope: Scope::ReadOnce,
        book: Some(book(1)),
        expires_at: None,
        revoked: false,
    };
    let mut case = input_for(Scope::ReadOnce);
    case.grants = vec![grant];
    case.read_once = ReadOnceStatus::ConsumedBy(ticket(1));
    case.ticket = Some(ticket(2));
    assert_eq!(run(&case), Decision::Deny(DenyReason::ReadOnceConsumed));
    case.ticket = Some(ticket(1));
    assert_eq!(run(&case), Decision::Allow);
}

#[test]
fn the_role_table_is_as_decided_in_d45() {
    for role in [Role::Reader, Role::Operator, Role::Admin] {
        let scopes = role_scopes(role);
        assert!(scopes.len() < Scope::ALL.len(), "no role holds every scope");
        assert!(!scopes.contains(&Scope::Download) && !scopes.contains(&Scope::ReadOnce));
    }
    assert!(role_scopes(Role::Operator).contains(&Scope::Operate));
    assert!(!role_scopes(Role::Operator).contains(&Scope::ManageUsers));
    assert!(role_scopes(Role::Admin).contains(&Scope::ManageUsers));
    assert!(!role_scopes(Role::Admin).contains(&Scope::Operate));
}
